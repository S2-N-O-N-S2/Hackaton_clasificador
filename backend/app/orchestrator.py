"""
orchestrator.py — Máquina de estados del clasificador (especificación §10). LA LÓGICA VIVE SOLO AQUÍ.

Ciclo normal (modo IA):
    MENU → (OBJ) → CAPTURA → CLASIFICACION → VERIFICAR_BOTE → POSICIONAR → SOLTAR
         → REGISTRAR → ACTUALIZAR_NIVEL → HOME → MENU
Caso dudoso:
    CLASIFICACION → REVISION → (panel / teclado) → VERIFICAR_BOTE …
                             → (30 s sin respuesta o tecla C) → PENDIENTE → MENU
Falla (serial, cámara, error interno):
    cualquier estado → ERROR (trampilla cerrada, disco a HOME, LED rojo, alerta) → MENU al recuperarse

Voz (§15, push-to-talk con la tecla A o el botón del panel):
    MENU / ESPERA_OBJETO → "usar IA" / "adivinar" eligen el modo; "¿dónde tiro esta lata?" responde en la LCD,
                           muestra el bote y deja una PISTA: si luego se coloca el residuo y la cámara opina
                           distinto, el caso va a REVISION (motivo conflicto_voz).
    REVISION             → "es una cáscara de plátano" resuelve el caso (origen = voz, foto a _por_verificar/).

Estados preparados para fases siguientes (existen y se registran, pero hoy "pasan de largo"):
    ESPERA_ADIVINANZA / RETROALIMENTACION (Fase 8) y BOTE_LLENO (Fase 7).

Regla de seguridad: NUNCA se manda DROP sin una categoría válida (0, 1 o 2) y con el disco en POS_OK.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from enum import Enum
from typing import Any, Callable

from . import lcd_ui
from .bins import GestorBotes
from .camera import CamaraBase, ErrorCamara, FotoNoValida, copiar_a_dataset
from .config import CAMARA, IDS_CATEGORIA, TIEMPOS, Ajustes, Configuracion
from .db import BaseDatos, ahora, clasificacion_a_dict
from .game import Juego
from .model import Decision, ModeloBase, ModeloNoDisponible, aplicar_reglas, promediar
from .serial_link import CONECTADO, DESCONECTADO, EnlaceBase, ErrorSerial, Mensaje, TimeoutSerial
from .voice import ErrorVoz, Intencion, Voz

log = logging.getLogger("orquestador")


class Estado(str, Enum):
    MENU = "MENU"
    ESPERA_OBJETO = "ESPERA_OBJETO"
    CAPTURA = "CAPTURA"
    CLASIFICACION = "CLASIFICACION"
    ESPERA_ADIVINANZA = "ESPERA_ADIVINANZA"
    RETROALIMENTACION = "RETROALIMENTACION"
    REVISION = "REVISION"
    VERIFICAR_BOTE = "VERIFICAR_BOTE"
    BOTE_LLENO = "BOTE_LLENO"
    POSICIONAR = "POSICIONAR"
    SOLTAR = "SOLTAR"
    REGISTRAR = "REGISTRAR"
    ACTUALIZAR_NIVEL = "ACTUALIZAR_NIVEL"
    HOME = "HOME"
    PENDIENTE = "PENDIENTE"
    OPERADOR = "OPERADOR"
    ERROR = "ERROR"


ESTADOS_EN_REPOSO = {Estado.MENU, Estado.ESPERA_OBJETO, Estado.OPERADOR}
ESTADOS_CONTROL_MANUAL = {Estado.MENU, Estado.OPERADOR, Estado.ERROR}
ESTADOS_VOZ = {Estado.MENU, Estado.ESPERA_OBJETO, Estado.REVISION}  # dónde sirve hablar
PISTA_VOZ_S = 60  # la pista de voz ("¿dónde tiro…?") vale para el siguiente residuo durante 60 s


class EstadoInvalido(Exception):
    """La acción pedida no se permite en el estado actual (la API responde 409)."""


# ---------------------------------------------------------------------------
# Difusor de eventos por WebSocket (/ws/eventos)
# ---------------------------------------------------------------------------
class Difusor:
    def __init__(self) -> None:
        self.clientes: set = set()

    def agregar(self, ws) -> None:
        self.clientes.add(ws)

    def quitar(self, ws) -> None:
        self.clientes.discard(ws)

    @staticmethod
    def mensaje(tipo: str, datos: Any) -> str:
        return json.dumps({"tipo": tipo, "ts": ahora(), "datos": datos}, ensure_ascii=False, default=str)

    async def emitir(self, tipo: str, datos: Any) -> None:
        texto = self.mensaje(tipo, datos)
        for ws in list(self.clientes):
            try:
                await ws.send_text(texto)
            except Exception:  # noqa: BLE001 — cliente caído: se quita
                self.clientes.discard(ws)


# ---------------------------------------------------------------------------
# Orquestador
# ---------------------------------------------------------------------------
class Orquestador:
    def __init__(self, ajustes: Ajustes, config: Configuracion, db: BaseDatos, camara: CamaraBase,
                 modelo: ModeloBase, botes: GestorBotes, juego: Juego, voz: Voz, difusor: Difusor,
                 crear_enlace: Callable[[Callable[[Mensaje], None]], EnlaceBase]) -> None:
        self.ajustes = ajustes
        self.config = config
        self.db = db
        self.camara = camara
        self.modelo = modelo
        self.botes = botes
        self.juego = juego
        self.voz = voz
        self.difusor = difusor
        self.enlace = crear_enlace(self.al_mensaje_serial)
        self.f = ajustes.factor_tiempo  # < 1 solo en pruebas (SIM_RAPIDO=1)

        self.estado = Estado.MENU
        self.estado_desde = ahora()
        self.modo: str | None = None
        self.mensaje = ""
        self.lcd = lcd_ui.pantalla_menu()
        self.alertas: deque[dict[str, Any]] = deque(maxlen=10)

        self._caso_id: int | None = None
        self._oculto = False
        self._tarea_ciclo: asyncio.Task | None = None
        self._tarea_supervisor: asyncio.Task | None = None
        self._tareas: set[asyncio.Task] = set()
        self._resolucion: asyncio.Future | None = None
        self._bandeja_libre = asyncio.Event()
        # OBJ que llegó mientras otro ciclo terminaba (auditoría): se procesa al volver al menú
        self._objeto_esperando = False
        self._vaciado = asyncio.Event()
        self._fin_cuenta: float | None = None
        self._t_error: float | None = None
        self._espera_humana_s = 0.0
        self._marcas: list[tuple[str, float]] = []  # (estado, instante) durante el ciclo actual
        self._pista_voz: tuple[int, str | None, float] | None = None  # (categoría, objeto, instante)
        self._tarea_mostrar_bote: asyncio.Task | None = None

    # ================================================================ ciclo de vida
    async def iniciar(self) -> None:
        self.db.registrar_evento("info", "orquestador",
                                 f"Arranque (simulacion={self.ajustes.simulacion})")
        await self.enlace.iniciar()
        await self.camara.iniciar()
        if not self.modelo.cargado:
            await self._alerta("aviso", "MODELO_NO_CARGADO", self.modelo.motivo_no_cargado or "Sin modelo")
        else:
            self._lanzar(self._calentar_modelo())
        if not self.camara.disponible:
            await self._alerta("error", "CAMARA_NO_DISPONIBLE", "No se pudo abrir la cámara")
        if self.voz.disponible:  # carga Vosk en segundo plano (~1–2 s)
            self._lanzar(self._calentar_voz())
        if self.enlace.conectado:
            await self._entrar_menu()
        else:
            await self._transicion(Estado.ERROR, "Esperando al Arduino")
            self._t_error = time.monotonic()
        self._tarea_supervisor = asyncio.create_task(self._supervisor())

    async def detener(self) -> None:
        for tarea in (self._tarea_supervisor, self._tarea_ciclo, *self._tareas):
            if tarea and not tarea.done():
                tarea.cancel()
        await self.enlace.cerrar()
        self.camara.cerrar()

    async def _calentar_modelo(self) -> None:
        """Carga TensorFlow y MobileNetV2 antes del primer residuo (tarda unos segundos)."""
        try:
            await asyncio.get_running_loop().run_in_executor(None, self.modelo.calentar)
            self.db.registrar_evento("info", "modelo", f"Modelo {self.modelo.version} listo")
        except Exception as error:  # noqa: BLE001 — sin modelo el sistema no adivina
            self.modelo = ModeloNoDisponible(f"No se pudo preparar el modelo: {error}")
            await self._alerta("error", "MODELO_NO_CARGADO", str(error))

    async def _calentar_voz(self) -> None:
        """Carga el modelo de Vosk antes de la primera vez que alguien habla (~1–2 s)."""
        try:
            await asyncio.get_running_loop().run_in_executor(None, self.voz.calentar)
            self.db.registrar_evento("info", "voz", "Vosk listo")
        except Exception as error:  # noqa: BLE001 — sin voz el sistema sigue (teclado y panel)
            await self._alerta("aviso", "VOZ_NO_DISPONIBLE", f"No se pudo cargar Vosk: {error}")

    def cambiar_modelo(self, nuevo: ModeloBase) -> None:
        """Activa un modelo recién entrenado. Los ciclos siguientes ya lo usan."""
        self.modelo = nuevo
        self.db.registrar_evento("info", "modelo", f"Modelo activo: {nuevo.version}")
        self._lanzar(self._alerta("info", "MODELO_ACTIVADO", f"Modelo {nuevo.version} activado"))

    @property
    def ciclo_activo(self) -> bool:
        return self._tarea_ciclo is not None and not self._tarea_ciclo.done()

    @property
    def simulado(self) -> bool:
        return bool(self.enlace.simulado or self.camara.simulada or self.modelo.simulado)

    # ================================================================ utilidades
    async def _cmd(self, texto: str, esperar: tuple[str, ...] = ("OK",), timeout: float | None = None) -> str:
        return await self.enlace.comando(texto, esperar, timeout or TIEMPOS["timeout_cmd_s"])

    async def _cmd_suave(self, texto: str) -> None:
        """Comandos no críticos (LCD, LED, luz): si fallan se registra, pero el ciclo sigue."""
        try:
            await self._cmd(texto)
        except ErrorSerial as error:
            log.warning("Comando no crítico falló: %s", error)

    async def _mostrar(self, lineas: list[str], led: str | None = None, parpadeo: bool = False) -> None:
        self.lcd = lcd_ui.normalizar(lineas)
        await self._cmd_suave(lcd_ui.comando_lcd(self.lcd))
        if led:
            await self._cmd_suave(f"LED:{led}" + (":PARPADEO" if parpadeo else ""))

    async def _transicion(self, nuevo: Estado, mensaje: str | None = None) -> None:
        anterior = self.estado
        self.estado = nuevo
        self.estado_desde = ahora()
        if self.ciclo_activo:
            self._marcas.append((nuevo.value, time.monotonic()))
        self.mensaje = mensaje or ""
        texto = f"{anterior.value} -> {nuevo.value}" + (f": {mensaje}" if mensaje else "")
        self.db.registrar_evento("info", "orquestador", texto)
        log.info(texto)
        await self.difusor.emitir("estado", {
            "estado": nuevo.value, "anterior": anterior.value, "modo": self.modo,
            "mensaje": self.mensaje, "lcd": self.lcd, "cuenta_regresiva_s": self.cuenta_regresiva(),
            "caso_actual": self.caso_actual(),
        })

    async def _alerta(self, nivel: str, codigo: str, mensaje: str) -> None:
        alerta = {"nivel": nivel, "codigo": codigo, "mensaje": mensaje, "fecha_hora": ahora()}
        self.alertas.append(alerta)
        self.db.registrar_evento(nivel, "orquestador", f"[{codigo}] {mensaje}")
        await self.difusor.emitir("alerta", alerta)

    def _lanzar(self, corrutina) -> None:
        tarea = asyncio.create_task(corrutina)
        self._tareas.add(tarea)
        tarea.add_done_callback(self._tareas.discard)

    def cuenta_regresiva(self) -> int | None:
        if self._fin_cuenta is None:
            return None
        return max(0, round((self._fin_cuenta - time.monotonic()) / self.f))

    def caso_actual(self) -> dict[str, Any] | None:
        if self._caso_id is None:
            return None
        fila = self.db.clasificacion(self._caso_id)
        return clasificacion_a_dict(fila, oculto=self._oculto) if fila else None

    def estado_dict(self) -> dict[str, Any]:
        """Objeto de GET /api/estado (contrato §3.1)."""
        return {
            "estado": self.estado.value,
            "estado_desde": self.estado_desde,
            "modo": self.modo,
            "modo_por_defecto": self.config.get("modo_por_defecto"),
            "simulacion": self.ajustes.simulacion,
            "serial": {"conectado": self.enlace.conectado, "puerto": self.enlace.puerto,
                       "simulado": self.enlace.simulado},
            "camara": {"disponible": self.camara.disponible, "indice": self.camara.indice,
                       "simulada": self.camara.simulada},
            "modelo": {"cargado": self.modelo.cargado, "version": self.modelo.version,
                       "simulado": self.modelo.simulado},
            "voz": self.voz.estado(),
            "caso_actual": self.caso_actual(),
            "cuenta_regresiva_s": self.cuenta_regresiva(),
            "mensaje": self.mensaje,
            "lcd": self.lcd,
            "prueba_actual": None,  # Fase 8 (prueba controlada de aprendizaje)
            "alertas": list(self.alertas),
        }

    # ================================================================ mensajes del Arduino
    def al_mensaje_serial(self, mensaje: Mensaje) -> None:
        """Lo llama el enlace serial (en el bucle de asyncio) por cada mensaje espontáneo."""
        self._lanzar(self._manejar_mensaje(mensaje))

    async def _manejar_mensaje(self, mensaje: Mensaje) -> None:
        tipo = mensaje.tipo
        if tipo == CONECTADO:
            await self._alerta("info", "SERIAL_CONECTADO", f"Arduino conectado en {self.enlace.puerto}")
            await self._sincronizar_angulos()
        elif tipo == DESCONECTADO:
            await self._alerta("error", "SERIAL_DESCONECTADO", "Se perdió el enlace con el Arduino")
            if not self.ciclo_activo and self.estado != Estado.ERROR:
                await self._transicion(Estado.ERROR, "Serial desconectado")
                self._t_error = time.monotonic()
        elif tipo == "READY":
            self.db.registrar_evento("info", "serial", "READY")
            if self.ciclo_activo:
                await self._alerta("error", "ARDUINO_REINICIADO", "El Arduino se reinició durante un ciclo")
        elif tipo == "OBJ":
            self._bandeja_libre.clear()
            if self._tarea_mostrar_bote and not self._tarea_mostrar_bote.done():
                await asyncio.wait({self._tarea_mostrar_bote})  # el disco termina de mostrar el bote
            if self.estado in (Estado.MENU, Estado.ESPERA_OBJETO) and not self.ciclo_activo:
                self._iniciar_ciclo()
            elif self.ciclo_activo:
                # El firmware manda OBJ una sola vez (flanco): si se ignora, el residuo se queda en la bandeja
                # sin clasificar para siempre. Se recuerda y se procesa en cuanto el ciclo actual termine.
                self._objeto_esperando = True
                self.db.registrar_evento("aviso", "serial", f"OBJ durante {self.estado.value}: se procesa al terminar")
            else:
                self.db.registrar_evento("aviso", "serial", f"OBJ ignorado en {self.estado.value}")
        elif tipo == "LIBRE":
            self._bandeja_libre.set()
            self._objeto_esperando = False
        elif tipo == "KEY" and mensaje.args:
            tecla = mensaje.args[0]
            await self.difusor.emitir("tecla", {"tecla": tecla})
            try:
                await self._manejar_tecla(tecla)
            except EstadoInvalido:
                pass
        elif tipo == "WATCHDOG":
            await self._alerta("aviso", "WATCHDOG", "El Arduino activó su watchdog (HOME, trampilla cerrada)")
        else:
            self.db.registrar_evento("aviso", "serial", f"Mensaje sin manejar: {mensaje.crudo}")

    async def _manejar_tecla(self, tecla: str) -> None:
        """Significado de cada tecla según el estado (§9, tabla del teclado)."""
        if tecla == "A" and self.estado in ESTADOS_VOZ:  # push-to-talk (§15)
            self._lanzar(self._escuchar_seguro())
            return
        if self.estado == Estado.MENU:
            if tecla == "1":
                await self.seleccionar_modo("ia")
            elif tecla == "2":
                await self.seleccionar_modo("adivina")
            elif tecla == "D":
                await self.entrar_operador()
        elif self.estado == Estado.ESPERA_OBJETO:
            if tecla in ("#", "C"):
                await self.seleccionar_modo("menu")
        elif self.estado == Estado.REVISION:
            if tecla in ("1", "2", "3"):
                self.resolver_revision(int(tecla) - 1, "teclado")
            elif tecla == "C":
                self.resolver_revision(None, "teclado")
        elif self.estado == Estado.OPERADOR:
            if tecla in ("D", "#"):
                await self._entrar_menu()
            # Fase 7: 1/2/3 eligen bote y B confirma el vaciado

    # ================================================================ acciones públicas (API y teclado)
    async def seleccionar_modo(self, modo: str) -> None:
        if self.ciclo_activo or self.estado not in (Estado.MENU, Estado.ESPERA_OBJETO):
            raise EstadoInvalido(f"No se puede cambiar de modo en {self.estado.value}")
        if modo == "menu":
            await self._entrar_menu()
            return
        if modo not in ("ia", "adivina"):
            raise ValueError("modo debe ser 'ia', 'adivina' o 'menu'")
        self.modo = modo
        self.lcd = lcd_ui.pantalla_espera_objeto(modo)
        await self._transicion(Estado.ESPERA_OBJETO, f"Modo {modo}")
        await self._mostrar(self.lcd)
        await self.difusor.emitir("modo", {"modo": modo})

    async def entrar_operador(self) -> None:
        if self.ciclo_activo or self.estado != Estado.MENU:
            raise EstadoInvalido(f"No se puede entrar al menú de operador en {self.estado.value}")
        await self._transicion(Estado.OPERADOR)
        await self._mostrar(lcd_ui.pantalla_operador())

    def resolver_revision(self, final_id: int | None, origen: str) -> None:
        """Resuelve el caso en REVISION. final_id=None → dejarlo pendiente."""
        if self.estado != Estado.REVISION or self._resolucion is None or self._resolucion.done():
            raise EstadoInvalido("No hay un caso en revisión")
        if final_id is not None and final_id not in IDS_CATEGORIA:
            raise ValueError("final_id debe ser 0, 1 o 2")
        self._resolucion.set_result((final_id, origen))

    # ================================================================ voz (§15)
    def _contexto_voz(self) -> str:
        if self.estado == Estado.REVISION:
            return "revision"
        if self.estado == Estado.ESPERA_ADIVINANZA:
            return "adivinanza"
        if self.estado in (Estado.MENU, Estado.ESPERA_OBJETO):
            return "menu"
        raise EstadoInvalido(f"La voz no se usa en {self.estado.value}")

    async def escuchar_voz(self) -> dict[str, Any]:
        """Push-to-talk: graba unos segundos, reconoce con Vosk y actúa. Devuelve lo que entendió."""
        contexto = self._contexto_voz()
        if not self.voz.disponible:
            await self._alerta("aviso", "VOZ_NO_DISPONIBLE", self.voz.motivo or "Voz no disponible")
            raise ErrorVoz(self.voz.motivo or "Voz no disponible")
        if self.voz.escuchando:
            raise EstadoInvalido("Ya estoy escuchando")
        segundos = float(self.config.get("voz_segundos"))
        pantalla_previa = self.lcd
        await self.difusor.emitir("voz", {"fase": "escuchando", "segundos": segundos, "contexto": contexto})
        await self._mostrar(lcd_ui.pantalla_escuchando(segundos))
        try:
            texto = await asyncio.get_running_loop().run_in_executor(None, self.voz.escuchar, contexto, segundos)
        except ErrorVoz as error:
            await self.difusor.emitir("voz", {"fase": "error", "mensaje": str(error)})
            await self._alerta("aviso", "VOZ_NO_DISPONIBLE", str(error))
            await self._mostrar(pantalla_previa)
            raise
        if self._contexto_voz() != contexto:  # mientras hablaba, el estado cambió (ej. 30 s de revisión)
            return {"fase": "reconocido", "contexto": contexto, "texto_crudo": texto, "accion": "ignorado"}
        return await self.aplicar_voz(texto, pantalla_previa)

    async def _escuchar_seguro(self) -> None:
        """Para la tecla A: igual que escuchar_voz, pero los errores ya se avisaron con una alerta."""
        try:
            await self.escuchar_voz()
        except (ErrorVoz, EstadoInvalido):
            pass

    async def aplicar_voz(self, texto: str, pantalla_previa: list[str] | None = None) -> dict[str, Any]:
        """Interpreta el texto según el estado y actúa. También lo usa la simulación (POST /api/sim/voz)."""
        contexto = self._contexto_voz()
        intencion = self.voz.interpretar(texto, contexto)
        self.db.registrar_evento("info", "voz", f"[{contexto}] '{texto}' -> {intencion.tipo} {intencion.valor}")
        accion = await self._actuar_voz(intencion, contexto, pantalla_previa or self.lcd)
        resultado = {"fase": "reconocido", "contexto": contexto, "texto_crudo": texto,
                     "intencion": intencion.a_dict(), "accion": accion}
        await self.difusor.emitir("voz", resultado)
        return resultado

    async def _actuar_voz(self, intencion: Intencion, contexto: str, pantalla_previa: list[str]) -> str:
        if intencion.tipo not in ("modo", "categoria"):
            # §15 caso 3: "No reconocí el objeto" y el caso sigue igual (en revisión, si lo estaba)
            await self._mostrar(lcd_ui.pantalla_voz_no_reconocida(intencion.texto))
            self._lanzar(self._restaurar_lcd(pantalla_previa, self.estado))
            return "no_reconocido"
        if intencion.tipo == "modo":  # §15 caso 4: menú por voz
            if intencion.valor == "menu" and self.estado == Estado.ESPERA_OBJETO:
                await self.seleccionar_modo("menu")
                return "modo_menu"
            if intencion.valor in ("ia", "adivina") and self.estado == Estado.MENU:
                await self.seleccionar_modo(intencion.valor)
                return f"modo_{intencion.valor}"
            return "ignorado"
        categoria = int(intencion.valor)
        if contexto == "revision":  # §15 caso 1: resolver el dudoso
            await self._mostrar(lcd_ui.pantalla_voz_entendida(intencion.objeto, categoria))
            self.resolver_revision(categoria, "voz")
            return "revision_resuelta"
        # §15 caso 2 sin residuo: responder, mostrar el bote y guardar la pista para el siguiente residuo
        self._pista_voz = (categoria, intencion.objeto, time.monotonic())
        await self._mostrar(lcd_ui.pantalla_voz_entendida(intencion.objeto, categoria))
        self._lanzar(self._restaurar_lcd(pantalla_previa, self.estado, segundos=4))
        if self.estado == Estado.MENU and self.enlace.conectado and not self.ciclo_activo:
            if not (self._tarea_mostrar_bote and not self._tarea_mostrar_bote.done()):
                self._tarea_mostrar_bote = asyncio.create_task(self._mostrar_bote(categoria))
        return "respuesta_bote"

    async def _mostrar_bote(self, categoria: int) -> None:
        """Gira el disco para que la persona vea en qué bote va y regresa a HOME. Nunca abre la trampilla."""
        try:
            await self._cmd(f"POS:{categoria}", ("POS_OK",), TIEMPOS["timeout_pos_s"])
            await asyncio.sleep(3 * self.f)
            await self._cmd("HOME", ("HOME_OK",), TIEMPOS["timeout_pos_s"])
        except ErrorSerial as error:
            log.warning("No se pudo mostrar el bote: %s", error)

    async def _restaurar_lcd(self, pantalla: list[str], estado: Estado, segundos: float = 2.5) -> None:
        """Después de un mensaje de voz, regresa la pantalla anterior si el estado no cambió."""
        await asyncio.sleep(segundos * self.f)
        if self.estado == estado:
            await self._mostrar(pantalla)

    def _tomar_pista_voz(self) -> tuple[int, str | None] | None:
        """La pista se usa una sola vez y caduca a los PISTA_VOZ_S segundos."""
        pista, self._pista_voz = self._pista_voz, None
        if pista and time.monotonic() - pista[2] <= PISTA_VOZ_S * self.f:
            return pista[0], pista[1]
        return None

    def notificar_vaciado(self) -> None:
        """Lo llama la API al vaciar un bote: si un residuo esperaba (BOTE_LLENO), el ciclo sigue."""
        self._vaciado.set()

    async def calibrar_angulo(self, categoria_id: int, grados: int) -> None:
        await self._cmd(f"CAL:{categoria_id}:{grados}", ("CAL_OK",))

    async def _sincronizar_angulos(self) -> None:
        """Al conectarse el Arduino se le mandan los ángulos de la configuración (única fuente de verdad)."""
        for categoria in IDS_CATEGORIA:
            try:
                await self.calibrar_angulo(categoria, self.config.angulo(categoria))
            except ErrorSerial as error:
                await self._alerta("aviso", "CAL_NO_SINCRONIZADA", f"No se pudo enviar el ángulo {categoria}: {error}")
                return
        self.db.registrar_evento("info", "serial", f"Ángulos sincronizados: {self.config.get('angulos')}")

    async def manual(self, accion: str, datos: dict[str, Any]) -> str:
        """Control manual desde el panel (solo en MENU, OPERADOR o ERROR)."""
        if self.ciclo_activo or self.estado not in ESTADOS_CONTROL_MANUAL:
            raise EstadoInvalido(f"Control manual no permitido en {self.estado.value}")
        t_pos, t_drop = TIEMPOS["timeout_pos_s"], TIEMPOS["timeout_drop_s"]
        if accion == "pos":
            id_ = int(datos.get("id", -1))
            if id_ not in IDS_CATEGORIA:
                raise ValueError("id debe ser 0, 1 o 2")
            orden = (f"POS:{id_}", ("POS_OK",), t_pos)
        elif accion == "ang":
            grados = int(datos.get("grados", -1))
            if not 0 <= grados <= 180:
                raise ValueError("grados debe estar entre 0 y 180")
            orden = (f"ANG:{grados}", ("ANG_OK",), t_pos)
        elif accion == "home":
            orden = ("HOME", ("HOME_OK",), t_pos)
        elif accion == "drop":
            orden = ("DROP", ("DROP_OK", "DROP_TIMEOUT"), t_drop)
        elif accion == "light":
            orden = ("LIGHT:ON" if datos.get("on") else "LIGHT:OFF", ("OK",), None)
        elif accion == "led":
            color = str(datos.get("color", "")).upper()
            if color not in ("VERDE", "AMARILLO", "ROJO", "OFF"):
                raise ValueError("color debe ser VERDE, AMARILLO, ROJO u OFF")
            orden = (f"LED:{color}" + (":PARPADEO" if datos.get("parpadeo") else ""), ("OK",), None)
        else:
            raise ValueError(f"Acción manual desconocida: {accion}")
        respuesta = await self._cmd(*orden)
        self.db.registrar_evento("info", "manual", f"{orden[0]} -> {respuesta}")
        return respuesta

    # ================================================================ el ciclo
    def _iniciar_ciclo(self) -> None:
        self._objeto_esperando = False
        self._tarea_ciclo = asyncio.create_task(self._ciclo())
        self._tarea_ciclo.add_done_callback(lambda _: self._lanzar(self._revisar_objeto_esperando()))

    async def _revisar_objeto_esperando(self) -> None:
        """Al terminar un ciclo: si llegó un residuo mientras tanto y sigue en la bandeja, se procesa."""
        if (self._objeto_esperando and not self._bandeja_libre.is_set() and not self.ciclo_activo
                and self.estado in (Estado.MENU, Estado.ESPERA_OBJETO)):
            self.db.registrar_evento("info", "orquestador", "Se procesa el residuo que llegó durante el ciclo anterior")
            self._iniciar_ciclo()

    async def _ciclo(self) -> None:
        t0 = time.monotonic()
        self._espera_humana_s = 0.0
        self._marcas = []
        self.modo = self.modo or self.config.get("modo_por_defecto")
        try:
            decision = await self._capturar_y_clasificar()
            decision = self._fusionar_voz(decision)
            if self.modo == "adivina":
                # Fase 8: aquí se espera la adivinanza (resultado oculto hasta que el usuario responda)
                await self._transicion(Estado.ESPERA_ADIVINANZA, "Fase 8 pendiente: pasa de largo")
                self._oculto = False
                await self.difusor.emitir("clasificacion", self.caso_actual())
            if decision.dudoso:
                final_id, origen = await self._revision(decision)
                if final_id is None:
                    await self._pendiente()
                    return
            else:
                final_id, origen = decision.pred_id, "camara"
            await self._depositar(final_id, origen, decision, t0)
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001 — cualquier falla termina en el estado seguro
            await self._falla(error)

    async def _capturar_y_clasificar(self) -> Decision:
        # --- CAPTURA
        self._oculto = self.modo == "adivina"
        await self._transicion(Estado.CAPTURA, f"Modo {self.modo}")
        await self._mostrar(lcd_ui.pantalla_procesando())
        await self._cmd_suave("LIGHT:ON")
        await asyncio.sleep(TIEMPOS["luz_ms"] / 1000 * self.f)
        foto_mala: FotoNoValida | None = None
        try:
            # La cámara revisa la calidad (sin señal, oscura, quemada, borrosa). Si todas salen mal se repite;
            # si siguen mal, el residuo NO se clasifica: va a revisión con motivo "foto_no_valida".
            for intento in range(int(CAMARA["reintentos"]) + 1):
                try:
                    frames = await self.camara.capturar(TIEMPOS["fotogramas"])
                    foto_mala = None
                    break
                except FotoNoValida as error:
                    foto_mala = error
                    if intento < int(CAMARA["reintentos"]):
                        await self._alerta("aviso", "FOTO_REINTENTO", f"{error}: se toma otra foto")
        finally:
            await self._cmd_suave("LIGHT:OFF")
        if foto_mala is not None:
            frames = [foto_mala.frame] if foto_mala.frame is not None else []
        foto = self.camara.guardar_foto(frames[len(frames) // 2]) if frames else None
        self._caso_id = self.db.insertar_clasificacion(
            foto=foto, modo=self.modo, origen="camara", simulado=int(self.simulado),
            modelo_version=self.modelo.version if self.modelo.cargado else None, estado="en_proceso",
        )
        await self.difusor.emitir("captura", {"clasificacion_id": self._caso_id,
                                              "foto": f"/captures/{foto}" if foto else None,
                                              "oculto": self._oculto})
        # --- CLASIFICACION
        await self._transicion(Estado.CLASIFICACION)
        if foto_mala is not None:
            await self._alerta("aviso", "FOTO_NO_VALIDA", f"{foto_mala}: el residuo va a revisión")
            self.db.actualizar_clasificacion(self._caso_id, dudoso=1, motivo_dudoso="foto_no_valida")
            decision = Decision(None, None, True, "foto_no_valida")
            if not self._oculto:
                await self.difusor.emitir("clasificacion", self.caso_actual())
            return decision
        modelo = self.modelo  # referencia fija: un reentrenamiento puede cambiarlo a medio ciclo
        try:
            # La red neuronal corre en otro hilo para no congelar el servidor (~0.1–0.3 s en CPU)
            predicciones, novedad = await asyncio.get_running_loop().run_in_executor(
                None, modelo.analizar, frames, self.camara.ultima_pista)
            probs = promediar(predicciones)
            decision = aplicar_reglas(probs, self.config.get("umbral_general"), self.config.get("umbral_peligroso"),
                                      novedad, self.config.get("umbral_desconocido"))
            if decision.motivo == "desconocido":
                await self._alerta("aviso", "OBJETO_DESCONOCIDO",
                                   f"Objeto no reconocido (caso #{self._caso_id}): va a revisión")
            self.db.actualizar_clasificacion(
                self._caso_id, pred_id=decision.pred_id, confianza=decision.confianza,
                p_organica=float(probs[0]), p_inorganica=float(probs[1]), p_peligroso=float(probs[2]),
                dudoso=int(decision.dudoso), motivo_dudoso=decision.motivo,
            )
        except Exception as error:  # noqa: BLE001 — sin modelo (o si falla) el sistema NO adivina: revisión
            await self._alerta("error", "MODELO_NO_CARGADO", str(error) or type(error).__name__)
            decision = Decision(None, None, True, "sin_modelo")
            self.db.actualizar_clasificacion(self._caso_id, dudoso=1, motivo_dudoso="sin_modelo")
        if not self._oculto:
            await self.difusor.emitir("clasificacion", self.caso_actual())
        return decision

    def _fusionar_voz(self, decision: Decision) -> Decision:
        """§15 caso 2: si antes dijeron qué era y la cámara opina distinto, NO se adivina: va a revisión."""
        pista = self._tomar_pista_voz()
        if pista is None or self.modo == "adivina" or decision.dudoso or decision.pred_id is None:
            return decision
        categoria, objeto = pista
        if categoria == decision.pred_id:
            self.db.registrar_evento("info", "voz", f"La voz ('{objeto}') confirma a la cámara ({categoria})")
            return decision
        self.db.registrar_evento("aviso", "voz", f"Conflicto: voz '{objeto}' = {categoria}, cámara = {decision.pred_id}")
        self.db.actualizar_clasificacion(self._caso_id, dudoso=1, motivo_dudoso="conflicto_voz")
        return Decision(decision.pred_id, decision.confianza, True, "conflicto_voz")

    async def _revision(self, decision: Decision) -> tuple[int | None, str | None]:
        """REVISION: el residuo NO cae. Se espera la decisión del panel o del teclado (30 s)."""
        self._resolucion = asyncio.get_running_loop().create_future()
        limite = self.config.get("tiempo_revision_s") * self.f
        self._fin_cuenta = time.monotonic() + limite
        await self._transicion(Estado.REVISION, decision.motivo)
        await self._mostrar(lcd_ui.pantalla_revision(decision.motivo, decision.confianza), led="AMARILLO")
        await self.difusor.emitir("revision", {"clasificacion": self.caso_actual(), "motivo": decision.motivo,
                                               "tiempo_limite_s": self.config.get("tiempo_revision_s")})
        inicio = time.monotonic()
        try:
            final_id, origen = await asyncio.wait_for(self._resolucion, limite)
        except asyncio.TimeoutError:
            final_id, origen = None, None
        finally:
            self._resolucion = None
            self._fin_cuenta = None
            self._espera_humana_s += time.monotonic() - inicio
        if final_id is not None:
            fila = self.db.clasificacion(self._caso_id)
            # Operador (panel) → dataset/<clase>/ ; usuario (teclado/voz) → dataset/_por_verificar/<clase>/
            copiar_a_dataset(self.ajustes, fila["foto"], final_id, verificado=(origen == "panel"))
            self.db.actualizar_clasificacion(self._caso_id, corregido=1, origen=origen)
        return final_id, origen

    async def _pendiente(self) -> None:
        """PENDIENTE: nadie resolvió. El residuo se queda; un operador lo retira (§4 regla 5)."""
        self.db.actualizar_clasificacion(self._caso_id, estado="pendiente")
        await self._transicion(Estado.PENDIENTE, "Revisión pendiente: retire el residuo")
        await self._alerta("aviso", "REVISION_PENDIENTE", f"Caso #{self._caso_id} sin resolver")
        await self._mostrar(lcd_ui.pantalla_pendiente(), led="AMARILLO")
        try:
            await asyncio.wait_for(self._bandeja_libre.wait(), TIEMPOS["espera_libre_s"] * self.f)
        except asyncio.TimeoutError:
            await self._alerta("aviso", "RESIDUO_NO_RETIRADO", "No se detectó que retiraran el residuo")
        await self._entrar_menu()

    async def _depositar(self, final_id: int | None, origen: str, decision: Decision, t0: float) -> None:
        # Seguridad: jamás se suelta un residuo sin categoría válida
        if final_id not in IDS_CATEGORIA:
            raise ValueError(f"Categoría inválida ({final_id}): no se suelta el residuo")
        bote_id = self.botes.bote_para_categoria(final_id)
        # El destino ya está decidido: se guarda AHORA para que el panel lo vea mientras el disco gira
        # (antes solo se guardaba al registrar y el panel veía final_id = null en POSICIONAR y SOLTAR).
        self.db.actualizar_clasificacion(self._caso_id, final_id=final_id)

        # --- VERIFICAR_BOTE / BOTE_LLENO (el bloqueo se activa en la Fase 7)
        await self._transicion(Estado.VERIFICAR_BOTE)
        if not self.botes.tiene_espacio(bote_id):
            await self._esperar_vaciado(bote_id)

        # --- POSICIONAR
        await self._transicion(Estado.POSICIONAR, f"Bote {bote_id}")
        try:
            respuesta = await self._cmd(f"POS:{final_id}", ("POS_OK",), TIEMPOS["timeout_pos_s"])
        except TimeoutSerial as error:
            raise TimeoutSerial(f"POS_TIMEOUT: {error}") from None
        if respuesta != f"POS_OK:{final_id}":
            raise ErrorSerial(f"Posición incorrecta: se pidió {final_id} y respondió {respuesta}")

        # --- SOLTAR
        await self._transicion(Estado.SOLTAR)
        respuesta = await self._cmd("DROP", ("DROP_OK", "DROP_TIMEOUT"), TIEMPOS["timeout_drop_s"])
        confirmado = respuesta == "DROP_OK"
        if not confirmado:
            await self._alerta("aviso", "DROP_TIMEOUT", "El sensor de caída no confirmó el residuo")

        # --- REGISTRAR
        await self._transicion(Estado.REGISTRAR)
        # Tiempo de MÁQUINA: se descuenta lo que se esperó a una persona (revisión, bote lleno)
        tiempo_ms = int((time.monotonic() - t0 - self._espera_humana_s) * 1000)
        self.db.actualizar_clasificacion(
            self._caso_id, final_id=final_id, origen=origen, corregido=int(origen != "camara"),
            tiempo_ciclo_ms=tiempo_ms, drop_confirmado=int(confirmado), bote_id=bote_id, estado="registrado",
        )
        await self.difusor.emitir("registrado", self.caso_actual())
        confianza = decision.confianza if origen == "camara" else None
        await self._mostrar(lcd_ui.pantalla_resultado(final_id, confianza, origen), led="VERDE")

        # --- ACTUALIZAR_NIVEL (nivel ESTIMADO por conteo)
        await self._transicion(Estado.ACTUALIZAR_NIVEL)
        bote = self.botes.sumar_pieza(bote_id, confirmado)
        await self.difusor.emitir("bote", bote)
        if bote["estado"] != "normal":
            await self._alerta("aviso", "BOTE_CASI_LLENO" if bote["estado"] == "casi_lleno" else "BOTE_LLENO",
                               f"Bote {bote['color']} al {round(bote['nivel'] * 100)} % (ESTIMADO)")

        # --- HOME
        await self._transicion(Estado.HOME)
        await self._cmd("HOME", ("HOME_OK",), TIEMPOS["timeout_pos_s"])
        await self._entrar_menu()

    async def _esperar_vaciado(self, bote_id: int) -> None:
        """BOTE_LLENO (Fase 7): el residuo espera en la bandeja hasta que se vacíe el bote."""
        self._vaciado.clear()
        await self._transicion(Estado.BOTE_LLENO, f"Bote {bote_id} lleno")
        await self._alerta("error", "BOTE_LLENO", f"Bote {bote_id} lleno: vacíelo para continuar")
        inicio = time.monotonic()
        while not self.botes.tiene_espacio(bote_id):
            await self._vaciado.wait()
            self._vaciado.clear()
        self._espera_humana_s += time.monotonic() - inicio
        await self._transicion(Estado.VERIFICAR_BOTE, "Bote vaciado")

    def _guardar_tiempos(self) -> None:
        """Duración de cada etapa del ciclo (ms) → clasificaciones.tiempos_etapas y bitácora de eventos."""
        if self._caso_id is None or len(self._marcas) < 2:
            return
        tiempos: dict[str, int] = {}
        for (estado, inicio), (_, fin) in zip(self._marcas, self._marcas[1:]):
            tiempos[estado] = tiempos.get(estado, 0) + int((fin - inicio) * 1000)
        self.db.actualizar_clasificacion(self._caso_id, tiempos_etapas=json.dumps(tiempos))
        resumen = ", ".join(f"{e} {ms} ms" for e, ms in tiempos.items())
        self.db.registrar_evento("info", "orquestador", f"Tiempos caso #{self._caso_id}: {resumen}")

    async def _entrar_menu(self) -> None:
        if self.ciclo_activo:
            self._marcas.append(("FIN", time.monotonic()))
            self._guardar_tiempos()
        self._marcas = []
        self.modo = None
        self._caso_id = None
        self._oculto = False
        self._fin_cuenta = None
        self.lcd = lcd_ui.pantalla_menu()
        await self._transicion(Estado.MENU)
        await self._mostrar(self.lcd, led="VERDE")

    # ================================================================ fallas
    async def _falla(self, error: Exception) -> None:
        """Estado seguro: trampilla cerrada (el firmware la cierra tras DROP), disco a HOME, LED rojo, aviso."""
        mensaje = str(error) or type(error).__name__
        log.exception("Falla en el ciclo: %s", mensaje)
        if isinstance(error, ErrorCamara):
            codigo = "CAMARA_NO_DISPONIBLE"
        elif isinstance(error, TimeoutSerial) and "POS_TIMEOUT" in mensaje:
            codigo = "POS_TIMEOUT"
        elif isinstance(error, ErrorSerial):
            codigo = "SERIAL_DESCONECTADO" if not self.enlace.conectado else "ERROR_SERIAL"
        else:
            codigo = "ERROR_INTERNO"
        try:
            if self._caso_id is not None:
                self.db.actualizar_clasificacion(self._caso_id, estado="error")
            await self._alerta("error", codigo, mensaje)
            self._fin_cuenta = None
            self._t_error = time.monotonic()
            await self._transicion(Estado.ERROR, mensaje)
            await self._mostrar(lcd_ui.pantalla_error(codigo), led="ROJO")
            if self.enlace.conectado:
                await self._cmd("HOME", ("HOME_OK",), TIEMPOS["timeout_pos_s"])
        except Exception as segundo:  # noqa: BLE001 — la falla segura no debe tirar el servidor
            log.error("No se pudo completar la falla segura: %s", segundo)

    async def _supervisor(self) -> None:
        """Vigila el enlace: ERROR si se pierde en reposo; MENU cuando todo vuelve a estar bien."""
        while True:
            await asyncio.sleep(1.0 * self.f)
            try:
                if self.ciclo_activo:
                    continue
                if self.estado in ESTADOS_EN_REPOSO and not self.enlace.conectado:
                    self._t_error = time.monotonic()
                    await self._transicion(Estado.ERROR, "Serial desconectado")
                elif (self.estado == Estado.ERROR and self.enlace.conectado and self._t_error is not None
                      and time.monotonic() - self._t_error >= TIEMPOS["recuperacion_error_s"] * self.f):
                    self._t_error = None
                    await self._alerta("info", "RECUPERADO", "Sistema recuperado")
                    await self._entrar_menu()
            except asyncio.CancelledError:
                raise
            except Exception as error:  # noqa: BLE001
                log.error("Supervisor: %s", error)
