"""
auditoria_usuarios.py — Auditoría con usuarios VIRTUALES contra el backend en simulación.

Simula a N personas usando el sistema a la vez (por defecto 3000, hasta 200 al mismo tiempo) y revisa:
  - que ninguna respuesta sea un error del servidor (5xx), se caiga la conexión o tarde demasiado;
  - que los datos inválidos se rechacen con 4xx (y no se acepten);
  - las REGLAS DE SEGURIDAD en cada ciclo: nunca soltar sin categoría válida, nunca soltar en un bote lleno,
    soltar solo después de posicionar el disco, y los casos dudosos solo caen si alguien los resolvió;
  - que la máquina termine en MENÚ (no se quede trabada) y que el historial sea coherente.

Tipos de usuario (proporciones):
  60 % espectadores  — abren el panel: WebSocket + consultas (estado, botes, historial, estadísticas...)
  20 % jugadores     — "¿Le ganas a la IA?": eligen modo, colocan residuo simulado y adivinan
  10 % correctores   — corrigen casos del historial (y prueban ids y categorías inválidas)
  10 % operadores    — configuración (válida e inválida), revisiones, vaciar botes, control manual

ES UNA SIMULACIÓN: no sustituye pruebas con personas reales ni con el Arduino. La máquina procesa un residuo
a la vez; lo que se valida es que el backend y el panel aguanten a mucha gente mirando y usando a la vez,
y que con esa presión no se rompa ninguna regla de seguridad.

Uso (PowerShell, en backend/ con el venv activado):
  # 1) backend en simulación rápida, con una base de datos aparte:
  $env:SIMULACION="1"; $env:SIM_RAPIDO="1"; $env:RUTA_DB="auditoria.db"; uvicorn app.main:app --port 8010
  # 2) en otra terminal:
  python tools/auditoria_usuarios.py --url http://127.0.0.1:8010 --usuarios 3000 --concurrencia 200
Sin dependencias nuevas: usa requests y websockets (ya están en el venv).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import statistics
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import websockets

TIMEOUT_S = 10.0          # una respuesta más lenta que esto cuenta como falla
LENTO_MS = 1000.0         # se reporta como "lenta"
ESTADOS_VALIDOS = {"MENU", "ESPERA_OBJETO", "CAPTURA", "CLASIFICACION", "ESPERA_ADIVINANZA", "RETROALIMENTACION",
                   "REVISION", "VERIFICAR_BOTE", "BOTE_LLENO", "POSICIONAR", "SOLTAR", "REGISTRAR",
                   "ACTUALIZAR_NIVEL", "HOME", "PENDIENTE", "OPERADOR", "ERROR"}


# =============================================================================
# Registro de resultados
# =============================================================================
@dataclass
class Resultados:
    peticiones: int = 0
    por_ruta: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    codigos: Counter = field(default_factory=Counter)
    hallazgos: list[dict[str, Any]] = field(default_factory=list)
    tipos_usuario: Counter = field(default_factory=Counter)
    ws_abiertos: int = 0
    ws_fallidos: int = 0
    ws_mensajes: int = 0
    ciclos: int = 0
    pendientes_fase8: int = 0
    soltados: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def hallazgo(self, tipo: str, detalle: str, **extra: Any) -> None:
        with self.lock:
            self.hallazgos.append({"tipo": tipo, "detalle": detalle, **extra})


R = Resultados()
_local = threading.local()


def _sesion() -> requests.Session:
    if not hasattr(_local, "s"):
        _local.s = requests.Session()
    return _local.s


def _plantilla(ruta: str) -> str:
    """'/api/clasificaciones/57/corregir' → '/api/clasificaciones/{id}/corregir' (para agrupar tiempos)."""
    if ruta.startswith("/captures/"):
        return "/captures/{foto}"
    partes = [("{id}" if p.isdigit() else p) for p in ruta.split("?")[0].split("/")]
    return "/".join(partes)


def pedir(base: str, metodo: str, ruta: str, esperados: set[int], cuerpo: Any = None, crudo: str | None = None,
          nota: str = "") -> requests.Response | None:
    """Hace la petición, mide el tiempo y registra un hallazgo si el código no es el esperado."""
    url = base + ruta
    t0 = time.perf_counter()
    try:
        if crudo is not None:
            r = _sesion().request(metodo, url, data=crudo, headers={"Content-Type": "application/json"}, timeout=TIMEOUT_S)
        else:
            r = _sesion().request(metodo, url, json=cuerpo, timeout=TIMEOUT_S)
    except requests.RequestException as error:
        R.hallazgo("conexion", f"{metodo} {ruta}: {type(error).__name__}: {error}"[:300], nota=nota)
        return None
    ms = (time.perf_counter() - t0) * 1000
    clave = f"{metodo} {_plantilla(ruta)}"
    with R.lock:
        R.peticiones += 1
        R.por_ruta[clave].append(ms)
        R.codigos[r.status_code] += 1
    if r.status_code == 501:
        with R.lock:
            R.pendientes_fase8 += 1
    elif r.status_code >= 500:
        R.hallazgo("error_servidor", f"{metodo} {ruta} → {r.status_code}", cuerpo=cuerpo, crudo=crudo,
                   respuesta=r.text[:300], nota=nota)
    elif r.status_code not in esperados:
        R.hallazgo("codigo_inesperado", f"{metodo} {ruta} → {r.status_code} (se esperaba {sorted(esperados)})",
                   cuerpo=cuerpo, crudo=crudo, respuesta=r.text[:300], nota=nota)
    if ruta.startswith("/api/") and 200 <= r.status_code < 300:
        try:
            r.json()
        except ValueError:
            R.hallazgo("json_invalido", f"{metodo} {ruta} respondió algo que no es JSON", respuesta=r.text[:200])
    return r


# =============================================================================
# Usuarios virtuales (código bloqueante: corre en hilos)
# =============================================================================
LECTURAS = [
    ("/api/estado", {200}), ("/api/modo", {200}), ("/api/botes", {200}), ("/api/config", {200}),
    ("/api/clasificaciones?limit=25&offset=0", {200}), ("/api/clasificaciones?limit=25&dudosos=1", {200}),
    ("/api/clasificaciones?simulado=solo&limit=10", {200}), ("/api/estadisticas", {200}),
    ("/api/estadisticas?simulado=excluir", {200}), ("/api/juego/estadisticas", {200}),
    ("/api/juego/aprendizaje", {200}), ("/api/juego/sesion", {200}), ("/api/modelo/estado", {200}),
    ("/api/pruebas", {200}), ("/api/dataset/por-verificar", {200}),
]

# Datos inválidos: todos deben rechazarse con 4xx (nunca 2xx ni 5xx)
INVALIDOS = [
    ("PUT", "/api/config", {"umbral_general": 2}), ("PUT", "/api/config", {"umbral_general": "alto"}),
    ("PUT", "/api/config", {"umbral_general": None}), ("PUT", "/api/config", {"umbral_peligroso": -0.1}),
    ("PUT", "/api/config", {"angulos": {"5": 10}}), ("PUT", "/api/config", {"angulos": {"0": 999}}),
    ("PUT", "/api/config", {"angulo_home": True}), ("PUT", "/api/config", {"tiempo_revision_s": 0}),
    ("PUT", "/api/config", {"tiempo_revision_s": 10 ** 12}), ("PUT", "/api/config", {"modo_por_defecto": "turbo"}),
    ("PUT", "/api/config", {"roi": [0.5, 0.5, 0.9, 0.9]}), ("PUT", "/api/config", {"roi": "todo"}),
    ("PUT", "/api/config", {"clave_rara": 1}), ("PUT", "/api/config", {"umbral_desconocido": 0}),
    ("PUT", "/api/config", []), ("POST", "/api/modo", {"modo": "turbo"}), ("POST", "/api/modo", {}),
    ("POST", "/api/clasificaciones/999999/corregir", {"final_id": 1}),
    ("POST", "/api/clasificaciones/1/corregir", {"final_id": 7}),
    ("POST", "/api/clasificaciones/1/corregir", {"final_id": "uno"}),
    ("POST", "/api/clasificaciones/1/corregir", {"final_id": True}),
    ("POST", "/api/revision", {"accion": "explotar"}), ("POST", "/api/revision", {"accion": "resolver", "final_id": 9}),
    ("POST", "/api/juego/adivinar", {"categoria": 5}), ("POST", "/api/juego/adivinar", {}),
    ("POST", "/api/botes/9/vaciar", None), ("PUT", "/api/botes/1", {"capacidad_piezas": 0}),
    ("PUT", "/api/botes/1", {"capacidad_piezas": -5}), ("PUT", "/api/botes/1", {"umbral_aviso": 3}),
    ("POST", "/api/pruebas", {"corrida": 1, "modo": "manual", "residuo_id": 999999, "categoria_asignada": 1, "tiempo_s": 2}),
    ("POST", "/api/pruebas", {"corrida": 1, "modo": "manual", "residuo_id": 1, "categoria_asignada": 1, "tiempo_s": -3}),
    ("POST", "/api/pruebas/residuos", {"nombre": "", "categoria_real": 1}),
    ("POST", "/api/pruebas/residuos", {"nombre": "x" * 5000, "categoria_real": 1}),
    ("POST", "/api/pruebas/residuos", {"nombre": "Lata", "categoria_real": 8}),
    ("POST", "/api/juego/prueba-aprendizaje", {"alias": "", "ronda": 1, "residuos": [1]}),
    ("POST", "/api/juego/prueba-aprendizaje", {"alias": "V1", "ronda": 7, "residuos": [1]}),
    ("POST", "/api/dataset/por-verificar", {"id": "../../app/main.py", "accion": "aprobar"}),
    ("POST", "/api/manual/explotar", {}), ("POST", "/api/manual/ang", {"grados": 500}),
    ("POST", "/api/manual/pos", {"id": 9}), ("POST", "/api/sim/objeto", {"categoria_real": 9}),
    ("POST", "/api/sim/objeto", {"categoria_real": True}), ("POST", "/api/sim/tecla", {"tecla": "Z"}),
    ("POST", "/api/sim/tecla", {"tecla": ""}),
]
CRUDOS_INVALIDOS = [("PUT", "/api/config", "{no es json"), ("PUT", "/api/config", '{"umbral_general": Infinity}'),
                    ("PUT", "/api/config", '{"umbral_general": NaN}'), ("POST", "/api/modo", "null"),
                    ("POST", "/api/revision", '{"accion": "resolver", "final_id": 1'),
                    ("GET", "/api/clasificaciones?limit=-1", None), ("GET", "/api/clasificaciones?limit=99999", None),
                    ("GET", "/api/clasificaciones?offset=abc", None), ("GET", "/api/estadisticas?simulado=todo", None),
                    ("GET", "/captures/../app/main.py", None), ("GET", "/api/no-existe", None)]


def usuario_espectador(base: str, azar: random.Random) -> None:
    for ruta, esperados in azar.sample(LECTURAS, k=azar.randint(3, 8)):
        pedir(base, "GET", ruta, esperados)
        time.sleep(azar.uniform(0.05, 0.6))
    r = pedir(base, "GET", "/api/clasificaciones?limit=5", {200})
    if r is not None and r.ok:
        for caso in r.json().get("items", [])[:2]:
            if caso.get("foto"):
                pedir(base, "GET", caso["foto"], {200}, nota="foto del historial")


def usuario_jugador(base: str, azar: random.Random) -> None:
    pedir(base, "POST", "/api/modo", {200, 409}, {"modo": "adivina"})
    pedir(base, "POST", "/api/sim/objeto", {200, 409}, {"categoria_real": azar.choice([0, 1, 2, None])})
    fin = time.time() + azar.uniform(3, 8)
    while time.time() < fin:
        r = pedir(base, "GET", "/api/estado", {200})
        estado = r.json().get("estado") if r is not None and r.ok else None
        if estado == "ESPERA_ADIVINANZA":
            pedir(base, "POST", "/api/juego/adivinar", {200, 409}, {"categoria": azar.randint(0, 2)})
        elif estado == "RETROALIMENTACION":
            if azar.random() < 0.2:
                pedir(base, "POST", "/api/juego/reportar-error", {200, 409}, {})
            else:
                pedir(base, "POST", "/api/juego/continuar", {200, 409}, {})
        time.sleep(azar.uniform(0.1, 0.4))
    pedir(base, "GET", "/api/juego/sesion", {200})


def usuario_corrector(base: str, azar: random.Random) -> None:
    r = pedir(base, "GET", f"/api/clasificaciones?limit=25&offset={azar.randint(0, 50)}", {200})
    casos = r.json().get("items", []) if r is not None and r.ok else []
    for caso in azar.sample(casos, k=min(len(casos), azar.randint(1, 3))):
        # en_proceso → 409 a propósito (se resuelve con /api/revision)
        pedir(base, "POST", f"/api/clasificaciones/{caso['id']}/corregir", {200, 409}, {"final_id": azar.randint(0, 2)})
    for metodo, ruta, cuerpo in azar.sample([i for i in INVALIDOS if "corregir" in i[1] or "modo" in i[1]], k=2):
        pedir(base, metodo, ruta, {400, 404, 409, 422}, cuerpo, nota="dato inválido")


def usuario_operador(base: str, azar: random.Random) -> None:
    pedir(base, "GET", "/api/config", {200})
    for metodo, ruta, cuerpo in azar.sample(INVALIDOS, k=azar.randint(3, 6)):
        pedir(base, metodo, ruta, {400, 404, 409, 422}, cuerpo, nota="dato inválido")
    metodo, ruta, crudo = azar.choice(CRUDOS_INVALIDOS)
    pedir(base, metodo, ruta, {400, 404, 405, 409, 422}, crudo=crudo, nota="petición malformada")
    accion = azar.random()
    if accion < 0.35:  # coloca un residuo simulado (también los casos especiales)
        pedir(base, "POST", "/api/sim/objeto", {200, 409},
              {"categoria_real": azar.choice([0, 1, 2, "dudoso", "foto_mala", "desconocido", None])})
    elif accion < 0.6:  # resuelve una revisión si la hay
        r = pedir(base, "GET", "/api/estado", {200})
        if r is not None and r.ok and r.json().get("estado") == "REVISION":
            cuerpo = azar.choice([{"accion": "resolver", "final_id": azar.randint(0, 2)}, {"accion": "pendiente"}])
            pedir(base, "POST", "/api/revision", {200, 409}, cuerpo)
        else:
            pedir(base, "POST", "/api/revision", {409}, {"accion": "resolver", "final_id": 0}, nota="sin revisión activa")
    elif accion < 0.75:
        pedir(base, "POST", f"/api/botes/{azar.randint(0, 2)}/vaciar", {200, 409})
    elif accion < 0.85:
        pedir(base, "POST", f"/api/manual/{azar.choice(['home', 'led', 'light'])}", {200, 409, 503},
              {"color": "VERDE", "parpadeo": False, "on": True})
    elif accion < 0.95:  # cambio válido y regreso (los umbrales se dejan como estaban)
        pedir(base, "PUT", "/api/config", {200}, {"umbral_general": 0.6, "umbral_peligroso": 0.35})
    else:
        pedir(base, "POST", "/api/sim/retirar", {200}, {})


TIPOS = [("espectador", 0.60, usuario_espectador), ("jugador", 0.20, usuario_jugador),
         ("corrector", 0.10, usuario_corrector), ("operador", 0.10, usuario_operador)]


# =============================================================================
# WebSocket: cada espectador abre uno; un monitor revisa las reglas de seguridad
# =============================================================================
async def ws_espectador(ws_url: str, azar: random.Random) -> None:
    try:
        async with websockets.connect(ws_url, open_timeout=TIMEOUT_S, max_size=2 ** 22) as ws:
            with R.lock:
                R.ws_abiertos += 1
            hola = json.loads(await asyncio.wait_for(ws.recv(), TIMEOUT_S))
            if hola.get("tipo") != "hola" or "estado" not in hola.get("datos", {}):
                R.hallazgo("websocket", f"El primer mensaje no es 'hola' con estado: {str(hola)[:200]}")
            await ws.send(json.dumps({"tipo": "ping"}))
            fin = time.time() + azar.uniform(2, 8)
            pong = False
            while time.time() < fin:
                try:
                    m = json.loads(await asyncio.wait_for(ws.recv(), max(0.05, fin - time.time())))
                except asyncio.TimeoutError:
                    break
                with R.lock:
                    R.ws_mensajes += 1
                if not {"tipo", "ts", "datos"} <= set(m):
                    R.hallazgo("websocket", f"Mensaje sin tipo/ts/datos: {str(m)[:200]}")
                pong = pong or m.get("tipo") == "pong"
            if not pong:
                R.hallazgo("websocket", "No llegó 'pong' tras un 'ping' (2–8 s)")
    except Exception as error:  # noqa: BLE001 — cualquier falla de conexión se reporta
        with R.lock:
            R.ws_fallidos += 1
        R.hallazgo("websocket", f"No se pudo usar el WebSocket: {type(error).__name__}: {error}"[:300])


class Monitor:
    """Escucha TODOS los eventos y revisa las reglas de seguridad de cada ciclo."""

    def __init__(self) -> None:
        self.anterior: str | None = None
        self.botes: dict[int, dict[str, Any]] = {}
        self.estados = Counter()
        self.parar = asyncio.Event()

    def revisar(self, m: dict[str, Any]) -> None:
        tipo, d = m.get("tipo"), m.get("datos") or {}
        if tipo == "hola":
            for b in d.get("botes", []) or []:
                self.botes[b["id"]] = b
            self.anterior = d.get("estado")
            return
        if tipo == "bote":
            self.botes[d.get("id")] = d
            return
        if tipo != "estado":
            return
        estado = d.get("estado")
        self.estados[estado] += 1
        if estado not in ESTADOS_VALIDOS:
            R.hallazgo("seguridad", f"Estado desconocido: {estado}")
        if estado == "CAPTURA":
            R.ciclos += 1
        if estado == "SOLTAR":
            R.soltados += 1
            caso = d.get("caso_actual") or {}
            final = caso.get("final_id")
            if self.anterior != "POSICIONAR":
                R.hallazgo("seguridad", f"SOLTAR sin POSICIONAR antes (venía de {self.anterior}), caso #{caso.get('id')}")
            if final not in (0, 1, 2):
                R.hallazgo("seguridad", f"SOLTAR sin categoría válida (final_id={final}), caso #{caso.get('id')}")
            bote = self.botes.get(final)
            if bote and (bote.get("bloqueado") or bote.get("estado") == "lleno"):
                R.hallazgo("seguridad", f"SOLTAR en el bote {final} que estaba LLENO, caso #{caso.get('id')}")
            if caso.get("dudoso") and not caso.get("corregido"):
                R.hallazgo("seguridad", f"Caso dudoso #{caso.get('id')} ({caso.get('motivo_dudoso')}) "
                                        "se soltó sin que nadie lo resolviera")
            if caso.get("motivo_dudoso") == "foto_no_valida" and caso.get("pred_id") is not None:
                R.hallazgo("seguridad", f"Foto no válida con predicción (caso #{caso.get('id')})")
        self.anterior = estado

    async def correr(self, ws_url: str) -> None:
        while not self.parar.is_set():
            try:
                async with websockets.connect(ws_url, open_timeout=TIMEOUT_S, max_size=2 ** 22) as ws:
                    while not self.parar.is_set():
                        try:
                            self.revisar(json.loads(await asyncio.wait_for(ws.recv(), 1.0)))
                        except asyncio.TimeoutError:
                            continue
            except Exception as error:  # noqa: BLE001
                R.hallazgo("monitor", f"El monitor perdió el WebSocket: {type(error).__name__}: {error}"[:300])
                await asyncio.sleep(0.5)


# =============================================================================
# Orquestación de la auditoría
# =============================================================================
async def un_usuario(numero: int, base: str, ws_url: str, pool: ThreadPoolExecutor, semilla: int,
                     limite: asyncio.Semaphore) -> None:
    azar = random.Random(semilla * 100003 + numero)
    r, acumulado = azar.random(), 0.0
    nombre, funcion = TIPOS[-1][0], TIPOS[-1][2]
    for n, p, f in TIPOS:
        acumulado += p
        if r < acumulado:
            nombre, funcion = n, f
            break
    async with limite:
        with R.lock:
            R.tipos_usuario[nombre] += 1
        tareas = [asyncio.get_running_loop().run_in_executor(pool, funcion, base, azar)]
        if nombre == "espectador":
            tareas.append(ws_espectador(ws_url, azar))
        await asyncio.gather(*tareas)


def verificar_historial(base: str) -> dict[str, Any]:
    """Revisa TODO el historial al final: casos registrados coherentes y nada trabado."""
    casos, offset = [], 0
    while True:
        r = pedir(base, "GET", f"/api/clasificaciones?limit=500&offset={offset}", {200})
        if r is None or not r.ok:
            break
        datos = r.json()
        casos += datos["items"]
        offset += 500
        if offset >= datos["total"]:
            break
    estados = Counter(c["estado"] for c in casos)
    corregidos_despues = 0
    for c in casos:
        if c["estado"] == "registrado":
            if c["final_id"] not in (0, 1, 2):
                R.hallazgo("historial", f"Caso #{c['id']} registrado sin categoría final válida")
            if c.get("bote_id") is not None and c["bote_id"] != c["final_id"]:
                if c["corregido"] and c["origen"] == "panel":
                    # Lo corrigió un operador DESPUÉS de caer: el residuo físico sigue en el otro bote (el panel avisa
                    # que hay que moverlo a mano). No es una falla del software.
                    corregidos_despues += 1
                else:
                    R.hallazgo("historial", f"Caso #{c['id']}: cayó en el bote {c['bote_id']} pero su categoría es {c['final_id']}")
            if c["dudoso"] and not c["corregido"] and c["origen"] == "camara":
                R.hallazgo("historial", f"Caso dudoso #{c['id']} registrado sin resolución")
        if c.get("motivo_dudoso") == "foto_no_valida" and c.get("pred_id") is not None:
            R.hallazgo("historial", f"Caso #{c['id']}: foto no válida con predicción")
    motivos = Counter(c.get("motivo_dudoso") for c in casos if c.get("dudoso"))
    return {"total": len(casos), "estados": dict(estados), "motivos": {str(k): v for k, v in motivos.items()},
            "corregidos_despues_de_caer": corregidos_despues}


async def esperar_menu(base: str, limite_s: float = 60.0) -> str | None:
    """Al final, sin usuarios, la máquina debe volver sola a MENÚ (revisiones vencen, pendientes se retiran)."""
    fin = time.time() + limite_s
    estado = None
    while time.time() < fin:
        try:
            pedir(base, "POST", "/api/sim/retirar", {200}, {})
            estado = requests.get(base + "/api/estado", timeout=TIMEOUT_S).json().get("estado")
            if estado == "ESPERA_OBJETO":  # alguien eligió modo y se fue: se vuelve al menú como haría con '#'
                pedir(base, "POST", "/api/modo", {200, 409}, {"modo": "menu"})
        except requests.RequestException:
            estado = None
        if estado == "MENU":
            return estado
        await asyncio.sleep(1.0)
    return estado


def percentil(valores: list[float], p: float) -> float:
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, int(round(p / 100 * (len(ordenados) - 1))))]


def escribir_reporte(ruta: Path, args, duracion_s: float, historial: dict, estado_final: str | None,
                     monitor: Monitor) -> None:
    graves = [h for h in R.hallazgos if h["tipo"] in ("error_servidor", "seguridad", "historial", "conexion")]
    agrupados = Counter((h["tipo"], h["detalle"].split(" → ")[0][:90]) for h in R.hallazgos)
    todos = [ms for v in R.por_ruta.values() for ms in v]
    lineas = [
        f"# Auditoría con {args.usuarios} usuarios virtuales — SIMULADO",
        "",
        f"- Fecha: {datetime.now():%Y-%m-%d %H:%M}  ·  Backend: `{args.url}` con `SIMULACION=1` y `SIM_RAPIDO=1`",
        f"- Usuarios: {dict(R.tipos_usuario)}  ·  hasta {args.concurrencia} a la vez  ·  semilla {args.semilla}",
        f"- Duración: {duracion_s:.0f} s  ·  peticiones HTTP: {R.peticiones}  ·  "
        f"WebSockets abiertos: {R.ws_abiertos} (fallidos: {R.ws_fallidos}, mensajes: {R.ws_mensajes})",
        f"- Ciclos de la máquina: {R.ciclos}  ·  residuos soltados: {R.soltados}  ·  estado final: **{estado_final}**",
        f"- Tiempo de respuesta (todas): mediana {statistics.median(todos) if todos else 0:.0f} ms, "
        f"p95 {percentil(todos, 95):.0f} ms, p99 {percentil(todos, 99):.0f} ms, máximo {max(todos, default=0):.0f} ms",
        f"- Códigos HTTP: {dict(sorted(R.codigos.items()))}  ·  501 = función de la Fase 8 todavía pendiente "
        f"(acordado en el contrato, no es falla): {R.pendientes_fase8}",
        "",
        f"## Resultado: {'SIN HALLAZGOS GRAVES' if not graves else f'{len(graves)} HALLAZGOS GRAVES'}"
        f" ({len(R.hallazgos)} hallazgos en total)",
        "",
        "Graves = error del servidor (5xx), conexión caída, regla de seguridad rota o historial incoherente.",
        "",
        "## Hallazgos agrupados",
        "",
        "| Tipo | Detalle | Veces |",
        "|---|---|---|",
    ]
    for (tipo, detalle), n in agrupados.most_common(60):
        lineas.append(f"| {tipo} | {detalle.replace('|', '/')} | {n} |")
    if not agrupados:
        lineas.append("| — | Ninguno | 0 |")
    lineas += ["", "## Tiempos por ruta (ms)", "", "| Ruta | n | mediana | p95 | máx | lentas (>1 s) |", "|---|---|---|---|---|---|"]
    for clave, v in sorted(R.por_ruta.items(), key=lambda kv: -percentil(kv[1], 95)):
        lineas.append(f"| `{clave}` | {len(v)} | {statistics.median(v):.0f} | {percentil(v, 95):.0f} | {max(v):.0f} | "
                      f"{sum(ms > LENTO_MS for ms in v)} |")
    lineas += ["", "## Historial al terminar", "", f"- Casos: {historial['total']}  ·  por estado: {historial['estados']}",
               f"- Motivos de revisión: {historial['motivos']}",
               f"- Corregidos desde el panel DESPUÉS de caer (el residuo sigue en el otro bote; el panel pide moverlo "
               f"a mano): {historial['corregidos_despues_de_caer']}", f"- Estados vistos por el monitor: {dict(monitor.estados)}",
               "", "## Ejemplos de hallazgos (máx. 25)", "", "```json"]
    lineas += [json.dumps(h, ensure_ascii=False, default=str)[:600] for h in R.hallazgos[:25]]
    lineas += ["```", "", "_Datos SIMULADOS: usuarios virtuales contra el backend en simulación; no son mediciones con personas "
               "ni con el Arduino._", ""]
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(lineas), encoding="utf-8")
    (ruta.with_suffix(".json")).write_text(json.dumps(R.hallazgos, ensure_ascii=False, indent=1, default=str),
                                          encoding="utf-8")


async def principal(args) -> int:
    base = args.url.rstrip("/")
    ws_url = base.replace("http", "ws", 1) + "/ws/eventos"
    try:
        raiz = requests.get(base + "/", timeout=5).json()
    except requests.RequestException as error:
        print(f"No responde el backend en {base}: {error}")
        return 2
    if not raiz.get("simulacion"):
        print("El backend NO está en simulación (SIMULACION=1). Por seguridad no se audita un sistema real.")
        return 2
    monitor = Monitor()
    for b in requests.get(base + "/api/botes", timeout=5).json().get("botes", []):
        monitor.botes[b["id"]] = b
    tarea_monitor = asyncio.create_task(monitor.correr(ws_url))
    await asyncio.sleep(0.5)
    limite = asyncio.Semaphore(args.concurrencia)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.concurrencia) as pool:
        tareas = []
        for n in range(args.usuarios):
            tareas.append(asyncio.create_task(un_usuario(n, base, ws_url, pool, args.semilla, limite)))
            if n % 100 == 99:
                print(f"  {n + 1} usuarios lanzados · {R.peticiones} peticiones · {len(R.hallazgos)} hallazgos")
                await asyncio.sleep(args.rampa)
        await asyncio.gather(*tareas)
        duracion = time.time() - t0
        print("Usuarios terminados. Esperando a que la maquina vuelva a MENU...")
        estado_final = await esperar_menu(base)
        if estado_final != "MENU":
            R.hallazgo("seguridad", f"La máquina no volvió a MENÚ en 60 s (quedó en {estado_final})")
        historial = await asyncio.get_running_loop().run_in_executor(pool, verificar_historial, base)
    monitor.parar.set()
    await tarea_monitor
    salida = Path(args.salida)
    escribir_reporte(salida, args, duracion, historial, estado_final, monitor)
    graves = [h for h in R.hallazgos if h["tipo"] in ("error_servidor", "seguridad", "historial", "conexion")]
    print(f"Listo en {duracion:.0f} s: {R.peticiones} peticiones, {len(R.hallazgos)} hallazgos ({len(graves)} graves).")
    print(f"Reporte: {salida}")
    return 1 if graves else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://127.0.0.1:8010")
    parser.add_argument("--usuarios", type=int, default=3000)
    parser.add_argument("--concurrencia", type=int, default=200)
    parser.add_argument("--rampa", type=float, default=0.5, help="pausa (s) cada 100 usuarios lanzados")
    parser.add_argument("--semilla", type=int, default=2026)
    parser.add_argument("--salida", default=str(Path(__file__).resolve().parents[2] / "docs" / "resultados" / "auditoria_3000.md"))
    return asyncio.run(principal(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
