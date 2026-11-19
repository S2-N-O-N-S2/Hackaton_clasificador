"""
routes.py — Endpoints REST de la especificación §17. El formato JSON exacto está en docs/api_contrato.md.

Las rutas solo validan y traducen: TODA la lógica de estados está en orchestrator.py.
Errores: EstadoInvalido → 409, ErrorSerial → 503 (manejadores en main.py), ValueError → 400/422.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Any, Literal

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel, Field, StrictInt

from .bins import GestorBotes
from .camera import PISTAS_ESPECIALES, copiar_a_dataset
from .config import CATEGORIAS, CLAVES_CATEGORIA, CLAVES_REQUIEREN_REINICIO, IDS_CATEGORIA, Ajustes, Configuracion
from .db import BaseDatos, ahora, clasificacion_a_dict
from .game import NIVELES_REPORTABLES, Juego
from .model import GestorReentrenamiento
from .orchestrator import Estado, Orquestador
from .serial_link import EnlaceSimulado, ErrorSerial
from .voice import ErrorVoz

router = APIRouter()


@dataclass
class Contexto:
    ajustes: Ajustes
    config: Configuracion
    db: BaseDatos
    orq: Orquestador
    botes: GestorBotes
    juego: Juego
    reentrenamiento: GestorReentrenamiento


def _ctx(request: Request) -> Contexto:
    return request.app.state.ctx


def _no_implementado(fase: int) -> HTTPException:
    return HTTPException(501, f"Disponible en la Fase {fase}")


def _filtro_simulado(simulado: str) -> str:
    if simulado == "excluir":
        return " AND simulado = 0"
    if simulado == "solo":
        return " AND simulado = 1"
    if simulado != "incluir":
        raise HTTPException(400, "simulado debe ser incluir, excluir o solo")
    return ""


# ---------------------------------------------------------------------------- modelos de entrada
class ModoIn(BaseModel):
    modo: Literal["ia", "adivina", "menu"]


class CorregirIn(BaseModel):
    final_id: StrictInt  # StrictInt: true/false o "1" se rechazan (pydantic convertía true en 1)


class RevisionIn(BaseModel):
    accion: Literal["resolver", "pendiente"]
    final_id: StrictInt | None = None


class PruebaIn(BaseModel):
    corrida: StrictInt = Field(ge=1, le=2)
    modo: Literal["manual", "sistema"]
    residuo_id: StrictInt
    categoria_asignada: StrictInt | None = Field(None, ge=0, le=2)
    tiempo_s: float | None = Field(None, ge=0, le=3600, allow_inf_nan=False)


class ResiduoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    categoria_real: StrictInt = Field(ge=0, le=2)
    simulado: bool = False
    usado_en_entrenamiento: bool = False


class AdivinarIn(BaseModel):
    categoria: StrictInt


class PruebaAprendizajeIn(BaseModel):
    alias: str = Field(min_length=1, max_length=12)
    ronda: StrictInt = Field(ge=1, le=2)
    residuos: list[StrictInt] = Field(min_length=1, max_length=50)


class BoteIn(BaseModel):
    capacidad_piezas: StrictInt | None = Field(None, ge=1, le=10000)
    umbral_aviso: float | None = Field(None, ge=0, le=1, allow_inf_nan=False)


class PorVerificarIn(BaseModel):
    id: str
    accion: Literal["aprobar", "rechazar"]


class SimObjetoIn(BaseModel):
    # 0/1/2, "dudoso", "foto_mala" (fotos oscuras: prueba la revisión de calidad) o "desconocido" (objeto que
    # el modelo nunca vio: prueba la detección de objetos desconocidos). Solo simulación.
    categoria_real: StrictInt | Literal["dudoso", "foto_mala", "desconocido"] | None = None


class SimTeclaIn(BaseModel):
    tecla: str = Field(min_length=1, max_length=1)


class SimVozIn(BaseModel):
    texto: str


# ---------------------------------------------------------------------------- estado y modo
@router.get("/api/estado")
def get_estado(request: Request) -> dict[str, Any]:
    return _ctx(request).orq.estado_dict()


@router.get("/api/modo")
def get_modo(request: Request) -> dict[str, Any]:
    orq = _ctx(request).orq
    return {"modo": orq.modo, "estado": orq.estado.value}


@router.post("/api/modo")
async def post_modo(request: Request, cuerpo: ModoIn) -> dict[str, Any]:
    orq = _ctx(request).orq
    await orq.seleccionar_modo(cuerpo.modo)
    return {"modo": orq.modo, "estado": orq.estado.value}


# ---------------------------------------------------------------------------- clasificaciones
@router.get("/api/clasificaciones")
def get_clasificaciones(request: Request, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
                        dudosos: int | None = Query(None, ge=0, le=1),
                        simulado: str = "incluir") -> dict[str, Any]:
    db = _ctx(request).db
    filtro = " WHERE 1 = 1" + _filtro_simulado(simulado)
    if dudosos is not None:
        filtro += f" AND dudoso = {int(dudosos)}"
    total = db.uno(f"SELECT COUNT(*) AS n FROM clasificaciones{filtro}")["n"]
    filas = db.consultar(f"SELECT * FROM clasificaciones{filtro} ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
    return {"total": total, "items": [clasificacion_a_dict(f) for f in filas]}


@router.post("/api/clasificaciones/{id_}/corregir")
def post_corregir(request: Request, id_: int, cuerpo: CorregirIn) -> dict[str, Any]:
    ctx = _ctx(request)
    if cuerpo.final_id not in IDS_CATEGORIA:
        raise HTTPException(400, "final_id debe ser 0, 1 o 2")
    fila = ctx.db.clasificacion(id_)
    if fila is None:
        raise HTTPException(404, f"No existe la clasificación {id_}")
    if fila["estado"] == "en_proceso":
        raise HTTPException(409, "El caso sigue en proceso: resuélvanlo con /api/revision")
    ctx.db.actualizar_clasificacion(id_, final_id=cuerpo.final_id, corregido=1, origen="panel")
    copiar_a_dataset(ctx.ajustes, fila["foto"], cuerpo.final_id, verificado=True)  # decisión del operador
    ctx.db.registrar_evento("info", "api", f"Corrección #{id_}: {fila['final_id']} -> {cuerpo.final_id}")
    return clasificacion_a_dict(ctx.db.clasificacion(id_))


@router.post("/api/revision")
async def post_revision(request: Request, cuerpo: RevisionIn) -> dict[str, Any]:
    orq = _ctx(request).orq
    if cuerpo.accion == "resolver":
        if cuerpo.final_id not in IDS_CATEGORIA:
            raise HTTPException(400, "final_id debe ser 0, 1 o 2")
        orq.resolver_revision(cuerpo.final_id, "panel")
    else:
        orq.resolver_revision(None, "panel")
    return {"ok": True, "estado": orq.estado.value}


# ---------------------------------------------------------------------------- voz (§15)
@router.post("/api/voz/escuchar")
async def post_voz_escuchar(request: Request) -> dict[str, Any]:
    """Push-to-talk desde el panel (igual que la tecla A): graba `voz_segundos` y actúa. Responde al terminar."""
    orq = _ctx(request).orq
    try:
        return await orq.escuchar_voz()
    except ErrorVoz as error:
        raise HTTPException(503, str(error)) from None


@router.get("/api/voz/microfonos")
def get_voz_microfonos(request: Request) -> dict[str, Any]:
    """Micrófonos disponibles y el configurado (`microfono` en /api/config)."""
    ctx = _ctx(request)
    return {"microfonos": ctx.orq.voz.microfonos(), "configurado": ctx.config.get("microfono"),
            "voz": ctx.orq.voz.estado()}


# ---------------------------------------------------------------------------- estadísticas
def _matriz_vacia() -> list[list[int]]:
    return [[0, 0, 0] for _ in range(3)]


@router.get("/api/estadisticas")
def get_estadisticas(request: Request, simulado: str = "incluir") -> dict[str, Any]:
    ctx = _ctx(request)
    filtro = _filtro_simulado(simulado)
    filas = ctx.db.consultar(
        f"SELECT pred_id, final_id FROM clasificaciones WHERE final_id IS NOT NULL AND pred_id IS NOT NULL "
        f"AND estado != 'en_proceso'{filtro}"
    )
    matriz = _matriz_vacia()
    for f in filas:
        matriz[f["final_id"]][f["pred_id"]] += 1
    por_categoria = {}
    for c in IDS_CATEGORIA:
        conteo = sum(matriz[c])
        por_categoria[str(c)] = {"conteo": conteo, "aciertos": matriz[c][c],
                                 "precision": round(matriz[c][c] / conteo, 3) if conteo else None}
    n = len(filas)
    aciertos = sum(matriz[c][c] for c in IDS_CATEGORIA)
    resumen = ctx.db.uno(
        f"SELECT SUM(dudoso) AS dudosos, SUM(corregido) AS corregidos, "
        f"SUM(CASE WHEN motivo_dudoso = 'desconocido' THEN 1 ELSE 0 END) AS no_reconocidos, "
        f"SUM(CASE WHEN motivo_dudoso = 'foto_no_valida' THEN 1 ELSE 0 END) AS fotos_no_validas, "
        f"AVG(CASE WHEN estado = 'registrado' THEN tiempo_ciclo_ms END) AS tiempo "
        f"FROM clasificaciones WHERE 1 = 1{filtro}"
    )
    desviados = {"0": 0, "1": 0, "2": 0}
    for f in ctx.db.consultar(
        f"SELECT bote_id, COUNT(*) AS n FROM clasificaciones WHERE estado = 'registrado' "
        f"AND bote_id IS NOT NULL{filtro} GROUP BY bote_id"
    ):
        desviados[str(f["bote_id"])] = f["n"]
    return {
        "muestra": n,
        "por_categoria": por_categoria,
        "tasa_acierto": round(aciertos / n, 3) if n else None,
        "matriz_confusion": {"etiquetas": [0, 1, 2], "filas": "real", "columnas": "predicha", "valores": matriz},
        "dudosos": resumen["dudosos"] or 0,
        "corregidos": resumen["corregidos"] or 0,
        "no_reconocidos": resumen["no_reconocidos"] or 0,
        "fotos_no_validas": resumen["fotos_no_validas"] or 0,
        "tiempo_promedio_ms": round(resumen["tiempo"]) if resumen["tiempo"] is not None else None,
        "desviados_por_categoria": desviados,
        "incluye_simulados": simulado != "excluir",
    }


# ---------------------------------------------------------------------------- pruebas oficiales
@router.get("/api/pruebas")
def get_pruebas(request: Request) -> dict[str, Any]:
    db = _ctx(request).db
    residuos = db.consultar("SELECT * FROM residuos_prueba ORDER BY id")
    for r in residuos:
        r["simulado"] = bool(r["simulado"])
        r["usado_en_entrenamiento"] = bool(r["usado_en_entrenamiento"])
    registros = db.consultar("SELECT * FROM pruebas ORDER BY id")
    for r in registros:
        r["correcto"] = None if r["correcto"] is None else bool(r["correcto"])
    reales = {r["id"]: r["categoria_real"] for r in residuos}
    comparativa: dict[str, Any] = {}
    for modo in ("manual", "sistema"):
        filas = [r for r in registros if r["modo"] == modo]
        matriz = _matriz_vacia()
        for r in filas:
            if r["categoria_asignada"] in IDS_CATEGORIA:
                matriz[reales[r["residuo_id"]]][r["categoria_asignada"]] += 1
        aciertos = sum(1 for r in filas if r["correcto"])
        tiempos = [r["tiempo_s"] for r in filas if r["tiempo_s"] is not None]
        comparativa[modo] = {
            "n": len(filas), "aciertos": aciertos,
            "precision": round(aciertos / len(filas), 3) if filas else None,
            "tiempo_promedio_s": round(sum(tiempos) / len(tiempos), 2) if tiempos else None,
        }
        comparativa[f"matriz_{modo}"] = {"etiquetas": [0, 1, 2], "filas": "real", "columnas": "asignada",
                                         "valores": matriz}
    return {"residuos": residuos, "registros": registros, "comparativa": comparativa}


@router.post("/api/pruebas")
def post_prueba(request: Request, cuerpo: PruebaIn) -> dict[str, Any]:
    db = _ctx(request).db
    residuo = db.uno("SELECT * FROM residuos_prueba WHERE id = ?", (cuerpo.residuo_id,))
    if residuo is None:
        raise HTTPException(404, f"No existe el residuo de prueba {cuerpo.residuo_id}")
    if cuerpo.categoria_asignada is not None and cuerpo.categoria_asignada not in IDS_CATEGORIA:
        raise HTTPException(400, "categoria_asignada debe ser 0, 1, 2 o null")
    correcto = None if cuerpo.categoria_asignada is None else int(cuerpo.categoria_asignada == residuo["categoria_real"])
    id_ = db.ejecutar(
        "INSERT INTO pruebas(corrida, modo, residuo_id, categoria_asignada, correcto, tiempo_s, fecha_hora) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (cuerpo.corrida, cuerpo.modo, cuerpo.residuo_id, cuerpo.categoria_asignada, correcto, cuerpo.tiempo_s, ahora()),
    )
    fila = db.uno("SELECT * FROM pruebas WHERE id = ?", (id_,))
    fila["correcto"] = None if fila["correcto"] is None else bool(fila["correcto"])
    return fila


@router.post("/api/pruebas/residuos")
def post_residuo(request: Request, cuerpo: ResiduoIn) -> dict[str, Any]:
    if cuerpo.categoria_real not in IDS_CATEGORIA:
        raise HTTPException(400, "categoria_real debe ser 0, 1 o 2")
    db = _ctx(request).db
    id_ = db.ejecutar(
        "INSERT INTO residuos_prueba(nombre, categoria_real, simulado, usado_en_entrenamiento) VALUES (?, ?, ?, ?)",
        (cuerpo.nombre.strip(), cuerpo.categoria_real, int(cuerpo.simulado), int(cuerpo.usado_en_entrenamiento)),
    )
    fila = db.uno("SELECT * FROM residuos_prueba WHERE id = ?", (id_,))
    fila["simulado"], fila["usado_en_entrenamiento"] = bool(fila["simulado"]), bool(fila["usado_en_entrenamiento"])
    return fila


# ---------------------------------------------------------------------------- modelo
@router.get("/api/modelo/estado")
def get_modelo_estado(request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    return ctx.reentrenamiento.estado(ctx.orq.modelo.version)


@router.post("/api/modelo/reentrenar", status_code=202)
async def post_reentrenar(request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    try:
        await ctx.reentrenamiento.iniciar()
    except RuntimeError as error:
        raise HTTPException(409, str(error)) from None
    ctx.db.registrar_evento("info", "api", "Reentrenamiento solicitado desde el panel")
    return {"estado": "en_curso"}


# ---------------------------------------------------------------------------- configuración
def _config_dict(config: Configuracion) -> dict[str, Any]:
    return {"valores": config.todo(), "categorias": CATEGORIAS,
            "requieren_reinicio": sorted(CLAVES_REQUIEREN_REINICIO)}


@router.get("/api/config")
def get_config(request: Request) -> dict[str, Any]:
    return _config_dict(_ctx(request).config)


@router.put("/api/config")
async def put_config(request: Request, cuerpo: dict[str, Any] = Body(...)) -> dict[str, Any]:
    ctx = _ctx(request)
    antes = ctx.config.todo()
    try:
        ctx.config.actualizar(cuerpo)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    ctx.db.registrar_evento("info", "api", f"Configuración actualizada: {sorted(cuerpo)}")
    if "umbral_aviso_bote" in cuerpo:
        ctx.botes.umbral_aviso = ctx.config.get("umbral_aviso_bote")
    # Ángulos nuevos → se guardan también en la EEPROM del Arduino
    for cat, grados in ctx.config.get("angulos").items():
        if antes["angulos"].get(cat) != grados:
            try:
                await ctx.orq.calibrar_angulo(int(cat), grados)
            except ErrorSerial as error:
                ctx.db.registrar_evento("aviso", "api", f"No se pudo enviar CAL al Arduino: {error}")
    return _config_dict(ctx.config)


# ---------------------------------------------------------------------------- juego (Fase 8)
@router.post("/api/juego/adivinar")
def post_adivinar(request: Request, cuerpo: AdivinarIn) -> None:
    estado = _ctx(request).orq.estado
    if estado != Estado.ESPERA_ADIVINANZA:
        raise HTTPException(409, f"No se espera una adivinanza (estado {estado.value})")
    raise _no_implementado(8)


@router.post("/api/juego/reportar-error")
def post_reportar_error(request: Request) -> None:
    estado = _ctx(request).orq.estado
    if estado != Estado.RETROALIMENTACION:
        raise HTTPException(409, f"No hay retroalimentación activa (estado {estado.value})")
    raise _no_implementado(8)


@router.post("/api/juego/continuar")
def post_continuar(request: Request) -> None:
    estado = _ctx(request).orq.estado
    if estado != Estado.RETROALIMENTACION:
        raise HTTPException(409, f"No hay retroalimentación activa (estado {estado.value})")
    raise _no_implementado(8)


@router.get("/api/juego/sesion")
def get_sesion(request: Request) -> dict[str, Any]:
    return _ctx(request).juego.sesion()


def _niveles(texto: str) -> tuple[str, ...]:
    niveles = tuple(n.strip() for n in texto.split(",") if n.strip())
    if not niveles or any(n not in ("verificada", "alta", "media") for n in niveles):
        raise HTTPException(400, "niveles válidos: verificada, alta, media")
    return niveles


@router.get("/api/juego/estadisticas")
def get_juego_estadisticas(request: Request, niveles: str = ",".join(NIVELES_REPORTABLES)) -> dict[str, Any]:
    return _ctx(request).juego.estadisticas(_niveles(niveles))


@router.get("/api/juego/aprendizaje")
def get_aprendizaje(request: Request, niveles: str = ",".join(NIVELES_REPORTABLES)) -> dict[str, Any]:
    return _ctx(request).juego.aprendizaje(_niveles(niveles))


@router.post("/api/juego/prueba-aprendizaje")
def post_prueba_aprendizaje(cuerpo: PruebaAprendizajeIn) -> None:
    raise _no_implementado(8)


# ---------------------------------------------------------------------------- botes
@router.get("/api/botes")
def get_botes(request: Request) -> dict[str, Any]:
    botes = _ctx(request).botes
    return {"botes": botes.todos(), "vaciados": botes.vaciados(),
            "desviados_por_categoria": botes.desviados_por_categoria()}


@router.post("/api/botes/{id_}/vaciar")
async def post_vaciar(request: Request, id_: int) -> dict[str, Any]:
    ctx = _ctx(request)
    try:
        bote = ctx.botes.vaciar(id_, "panel")
    except KeyError as error:
        raise HTTPException(404, str(error)) from None
    await ctx.orq.difusor.emitir("bote", bote)
    ctx.orq.notificar_vaciado()
    return bote


@router.put("/api/botes/{id_}")
async def put_bote(request: Request, id_: int, cuerpo: BoteIn) -> dict[str, Any]:
    ctx = _ctx(request)
    try:
        bote = ctx.botes.ajustar(id_, cuerpo.capacidad_piezas, cuerpo.umbral_aviso)
    except KeyError as error:
        raise HTTPException(404, str(error)) from None
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    await ctx.orq.difusor.emitir("bote", bote)
    return bote


# ---------------------------------------------------------------------------- dataset por verificar
@router.get("/api/dataset/por-verificar")
def get_por_verificar(request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    items = []
    for clase_id, clave in enumerate(CLAVES_CATEGORIA):
        carpeta = ctx.ajustes.dir_dataset / "_por_verificar" / clave
        for archivo in sorted(carpeta.glob("*.jpg")):
            fila = ctx.db.uno("SELECT id, origen, fecha_hora FROM clasificaciones WHERE foto = ?", (archivo.name,))
            items.append({
                "id": f"{clave}/{archivo.name}", "clase_id": clase_id,
                "foto": f"/captures/{archivo.name}",
                "origen": fila["origen"] if fila else None,
                "clasificacion_id": fila["id"] if fila else None,
                "fecha_hora": fila["fecha_hora"] if fila else None,
            })
    return {"items": items}


@router.post("/api/dataset/por-verificar")
def post_por_verificar(request: Request, cuerpo: PorVerificarIn) -> dict[str, Any]:
    ctx = _ctx(request)
    clave, _, nombre = cuerpo.id.partition("/")
    if clave not in CLAVES_CATEGORIA or not nombre or "/" in nombre or "\\" in nombre or ".." in nombre:
        raise HTTPException(400, "id inválido")
    origen = ctx.ajustes.dir_dataset / "_por_verificar" / clave / nombre
    if not origen.exists():
        raise HTTPException(404, "No existe esa imagen por verificar")
    # Rechazar no borra: mueve a _rechazadas/ para poder revisarlo después
    destino_dir = ctx.ajustes.dir_dataset / (clave if cuerpo.accion == "aprobar" else f"_rechazadas/{clave}")
    destino_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(origen), str(destino_dir / nombre))
    except FileNotFoundError:  # otro operador la movió al mismo tiempo
        raise HTTPException(404, "Esa imagen ya fue revisada") from None
    ctx.db.registrar_evento("info", "api", f"Etiqueta {cuerpo.id}: {cuerpo.accion}")
    pendientes = sum(len(list((ctx.ajustes.dir_dataset / "_por_verificar" / c).glob("*.jpg")))
                     for c in CLAVES_CATEGORIA)
    return {"ok": True, "pendientes": pendientes}


# ---------------------------------------------------------------------------- control manual
@router.post("/api/manual/{accion}")
async def post_manual(request: Request, accion: str, cuerpo: dict[str, Any] | None = Body(None)) -> dict[str, Any]:
    try:
        respuesta = await _ctx(request).orq.manual(accion, cuerpo or {})
    except ValueError as error:
        raise HTTPException(400, str(error)) from None
    return {"ok": True, "respuesta_arduino": respuesta}


# ---------------------------------------------------------------------------- simulación (SIMULACION=1)
def _simulador(ctx: Contexto) -> EnlaceSimulado:
    if not ctx.ajustes.simulacion or not isinstance(ctx.orq.enlace, EnlaceSimulado):
        raise HTTPException(404, "Solo disponible con SIMULACION=1")
    return ctx.orq.enlace


@router.post("/api/sim/objeto")
async def post_sim_objeto(request: Request, cuerpo: SimObjetoIn | None = None) -> dict[str, Any]:
    ctx = _ctx(request)
    enlace = _simulador(ctx)
    categoria = cuerpo.categoria_real if cuerpo else None
    if categoria is not None and (isinstance(categoria, bool) or categoria not in (0, 1, 2, *PISTAS_ESPECIALES)):
        raise HTTPException(400, "categoria_real debe ser 0, 1, 2, 'dudoso', 'foto_mala', 'desconocido' o null")
    if enlace.objeto:
        raise HTTPException(409, "Ya hay un residuo en la bandeja")
    ctx.orq.camara.pista_siguiente = categoria
    enlace.simular_objeto()
    return {"ok": True, "simulado": True}


@router.post("/api/sim/tecla")
async def post_sim_tecla(request: Request, cuerpo: SimTeclaIn) -> dict[str, Any]:
    enlace = _simulador(_ctx(request))
    try:
        enlace.simular_tecla(cuerpo.tecla.upper())
    except ValueError as error:
        raise HTTPException(400, str(error)) from None
    return {"ok": True, "simulado": True}


@router.post("/api/sim/voz")
async def post_sim_voz(request: Request, cuerpo: SimVozIn) -> dict[str, Any]:
    """Simula que alguien DIJO `texto` (sin micrófono): misma interpretación y acciones que la voz real."""
    ctx = _ctx(request)
    if not ctx.ajustes.simulacion:
        raise HTTPException(404, "Solo disponible con SIMULACION=1")
    try:
        resultado = await ctx.orq.aplicar_voz(cuerpo.texto)
    except ErrorVoz as error:
        raise HTTPException(503, str(error)) from None
    return {**resultado, "simulado": True}


@router.post("/api/sim/retirar")
async def post_sim_retirar(request: Request) -> dict[str, Any]:
    _simulador(_ctx(request)).simular_retiro()
    return {"ok": True, "simulado": True}
