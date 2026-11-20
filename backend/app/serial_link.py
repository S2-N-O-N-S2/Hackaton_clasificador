"""
serial_link.py — Enlace serie con el Arduino UNO (protocolo: especificación §9 + docs/api_contrato.md §5).

Idea general:
  - El Arduino manda líneas de texto. Un hilo (real) o temporizadores (simulado) las entregan a
    `_procesar_linea()`, que corre en el bucle de asyncio del servidor.
  - Si alguien está esperando una respuesta (por ejemplo POS_OK), se le entrega a él.
  - Si es un mensaje espontáneo (OBJ, LIBRE, KEY, READY, WATCHDOG) se pasa al orquestador.

Dos implementaciones con la MISMA interfaz:
  - `EnlaceReal`: pyserial, reconexión automática y latido (PING) cada 3 s.
  - `EnlaceSimulado`: imita al firmware (SIMULACION=1), para trabajar sin Arduino.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from typing import Callable

from .config import TIEMPOS

log = logging.getLogger("serial")

MAX_LINEA = 80
ESPONTANEOS = {"READY", "OBJ", "LIBRE", "KEY", "WATCHDOG"}
# Mensajes internos (no vienen del Arduino) para avisar cambios de conexión al orquestador
CONECTADO = "_CONECTADO"
DESCONECTADO = "_DESCONECTADO"
TECLAS_VALIDAS = set("0123456789ABCD*#")


# ---------------------------------------------------------------------------
# Errores
# ---------------------------------------------------------------------------
class ErrorSerial(Exception):
    """Cualquier falla del enlace: desconectado, sin respuesta o error del Arduino."""


class TimeoutSerial(ErrorSerial):
    pass


class ErrorArduino(ErrorSerial):
    def __init__(self, codigo: str, comando: str) -> None:
        super().__init__(f"El Arduino respondió ERR:{codigo} a '{comando}'")
        self.codigo = codigo


# ---------------------------------------------------------------------------
# Parser (funciones puras, probadas en tests/test_serial.py)
# ---------------------------------------------------------------------------
@dataclass
class Mensaje:
    tipo: str                    # "POS_OK", "KEY", "ERR", ...
    args: list[str] = field(default_factory=list)
    crudo: str = ""


def parsear_linea(linea: str) -> Mensaje | None:
    """'POS_OK:1\\r\\n' → Mensaje('POS_OK', ['1']). Las líneas vacías devuelven None."""
    linea = linea.strip()
    if not linea:
        return None
    tipo, separador, resto = linea.partition(":")
    args = resto.split(":") if separador else []
    return Mensaje(tipo=tipo.strip().upper(), args=args, crudo=linea)


def formatear_comando(texto: str) -> str:
    """Valida un comando antes de mandarlo (sin saltos de línea, ASCII, ≤ 80 caracteres)."""
    if "\n" in texto or "\r" in texto:
        raise ValueError("El comando no puede contener saltos de línea")
    if len(texto) > MAX_LINEA:
        raise ValueError(f"Comando de {len(texto)} caracteres (máximo {MAX_LINEA})")
    try:
        texto.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError("El comando debe ser ASCII (usen lcd_ui.limpiar)") from None
    return texto


@dataclass
class _Espera:
    prefijos: tuple[str, ...]
    futuro: asyncio.Future
    comando: str


# ---------------------------------------------------------------------------
# Base común
# ---------------------------------------------------------------------------
class EnlaceBase:
    simulado = False

    def __init__(self, al_mensaje: Callable[[Mensaje], None]) -> None:
        self._al_mensaje = al_mensaje
        self._esperas: list[_Espera] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._abierto = False        # el puerto está abierto (se puede escribir)
        self.conectado = False       # abierto y verificado con PING
        self.puerto: str | None = None
        self._tarea_latido: asyncio.Task | None = None
        self._fallas_latido = 0

    # --- ciclo de vida
    async def iniciar(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._tarea_latido = asyncio.create_task(self._latido())

    async def cerrar(self) -> None:
        if self._tarea_latido:
            self._tarea_latido.cancel()

    # --- envío
    @property
    def ocupado(self) -> bool:
        return bool(self._esperas)

    async def comando(self, texto: str, esperar: tuple[str, ...] = ("OK",),
                      timeout: float = TIEMPOS["timeout_cmd_s"]) -> str:
        """Manda un comando y espera la primera línea que empiece con alguno de `esperar`."""
        if not self._abierto:
            raise ErrorSerial("Enlace serial desconectado")
        texto = formatear_comando(texto)
        futuro = self._loop.create_future()
        espera = _Espera(tuple(esperar), futuro, texto)
        self._esperas.append(espera)
        try:
            self._escribir(texto)
            return await asyncio.wait_for(futuro, timeout)
        except asyncio.TimeoutError:
            raise TimeoutSerial(f"Sin respuesta del Arduino a '{texto}' en {timeout:.1f} s") from None
        finally:
            if espera in self._esperas:
                self._esperas.remove(espera)

    def _escribir(self, linea: str) -> None:  # implementado por cada subclase
        raise NotImplementedError

    # --- recepción (siempre en el hilo del bucle de asyncio)
    def _procesar_linea(self, linea: str) -> None:
        mensaje = parsear_linea(linea)
        if mensaje is None:
            return
        if mensaje.tipo == "ERR":
            codigo = mensaje.args[0] if mensaje.args else "DESCONOCIDO"
            # Un ERR responde al comando más antiguo que sigue esperando
            for espera in self._esperas:
                if not espera.futuro.done():
                    espera.futuro.set_exception(ErrorArduino(codigo, espera.comando))
                    self._esperas.remove(espera)
                    return
            self._al_mensaje(mensaje)
            return
        for espera in self._esperas:
            if not espera.futuro.done() and mensaje.crudo.startswith(espera.prefijos):
                espera.futuro.set_result(mensaje.crudo)
                self._esperas.remove(espera)
                return
        if mensaje.tipo in ESPONTANEOS:
            self._al_mensaje(mensaje)
        else:
            log.warning("Mensaje serial inesperado: %s", mensaje.crudo)

    def _avisar(self, tipo: str) -> None:
        self._al_mensaje(Mensaje(tipo=tipo, crudo=tipo))

    # --- latido: mantiene vivo el watchdog del Arduino y detecta desconexiones
    async def _latido(self) -> None:
        while True:
            await asyncio.sleep(TIEMPOS["latido_s"])
            if not self.conectado or self.ocupado:
                continue
            try:
                await self.comando("PING", ("PONG",))
                self._fallas_latido = 0
            except ErrorSerial:
                self._fallas_latido += 1
                if self._fallas_latido >= 2:
                    self._marcar_desconectado("el Arduino no responde a PING")


    def _marcar_desconectado(self, motivo: str) -> None:
        if not self._abierto and not self.conectado:
            return
        log.error("Serial desconectado: %s", motivo)
        self._abierto = False
        self.conectado = False
        for espera in list(self._esperas):
            if not espera.futuro.done():
                espera.futuro.set_exception(ErrorSerial(f"Serial desconectado ({motivo})"))
        self._esperas.clear()
        self._avisar(DESCONECTADO)


# ---------------------------------------------------------------------------
# Enlace real (pyserial)
# ---------------------------------------------------------------------------
def detectar_puerto() -> str | None:
    """Busca un Arduino UNO original o clon (CH340). Si solo hay un puerto, usa ese."""
    from serial.tools import list_ports

    puertos = list(list_ports.comports())
    for p in puertos:
        texto = f"{p.description} {p.manufacturer or ''}".lower()
        if any(pista in texto for pista in ("arduino", "ch340", "usb-serial", "usb serial")):
            return p.device
    return puertos[0].device if len(puertos) == 1 else None


class EnlaceReal(EnlaceBase):
    def __init__(self, al_mensaje: Callable[[Mensaje], None], puerto_cfg: str, baudios: int) -> None:
        super().__init__(al_mensaje)
        self._puerto_cfg = puerto_cfg
        self._baudios = baudios
        self._serial = None
        self._hilo: threading.Thread | None = None
        self._tarea_conexion: asyncio.Task | None = None
        self.ultimo_error: str | None = None

    async def iniciar(self) -> None:
        await super().iniciar()
        self._tarea_conexion = asyncio.create_task(self._mantener_conexion())

    async def cerrar(self) -> None:
        await super().cerrar()
        if self._tarea_conexion:
            self._tarea_conexion.cancel()
        self._cerrar_puerto()

    async def _mantener_conexion(self) -> None:
        """Intenta conectar al arrancar y cada 2 s mientras no haya enlace."""
        while True:
            if not self._abierto:
                try:
                    await self._conectar()
                except Exception as error:  # noqa: BLE001 — cualquier falla: se reintenta
                    mensaje = str(error)
                    if mensaje != self.ultimo_error:
                        log.warning("No se pudo abrir el puerto serie: %s", mensaje)
                    self.ultimo_error = mensaje
                    self._cerrar_puerto()
            await asyncio.sleep(TIEMPOS["reintento_serial_s"])

    async def _conectar(self) -> None:
        import serial

        puerto = detectar_puerto() if self._puerto_cfg.upper() == "AUTO" else self._puerto_cfg
        if not puerto:
            raise ErrorSerial("No se encontró el Arduino (puerto AUTO)")
        self._serial = await self._loop.run_in_executor(
            None, lambda: serial.Serial(puerto, self._baudios, timeout=0.2, write_timeout=1)
        )
        self.puerto = puerto
        self._abierto = True
        self._hilo = threading.Thread(target=self._hilo_lector, name="lector-serial", daemon=True)
        self._hilo.start()
        # Abrir el puerto reinicia el UNO: esperar a que arranque y verificar con PING
        await asyncio.sleep(TIEMPOS["espera_ready_s"])
        await self.comando("PING", ("PONG",))
        self.conectado = True
        self.ultimo_error = None
        log.info("Arduino conectado en %s", puerto)
        self._avisar(CONECTADO)

    def _hilo_lector(self) -> None:
        """Hilo aparte: lee líneas y las pasa al bucle de asyncio."""
        import serial

        buffer = b""
        while self._abierto and self._serial is not None:
            try:
                datos = self._serial.readline()
            except (serial.SerialException, OSError, TypeError) as error:
                self._loop.call_soon_threadsafe(self._perdida, str(error))
                return
            if not datos:
                continue
            buffer += datos
            if buffer.endswith(b"\n"):  # readline puede devolver líneas incompletas al vencer el timeout
                texto = buffer.decode("ascii", errors="replace")
                buffer = b""
                self._loop.call_soon_threadsafe(self._procesar_linea, texto)

    def _escribir(self, linea: str) -> None:
        try:
            self._serial.write((linea + "\n").encode("ascii"))
        except Exception as error:  # noqa: BLE001
            self._perdida(str(error))
            raise ErrorSerial(f"No se pudo escribir en el puerto: {error}") from None

    def _perdida(self, motivo: str) -> None:
        self._marcar_desconectado(motivo)
        self._cerrar_puerto()

    def _cerrar_puerto(self) -> None:
        self._abierto = False
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:  # noqa: BLE001
                pass
        self._serial = None


# ---------------------------------------------------------------------------
# Enlace simulado (imita al firmware; SIMULACION=1)
# ---------------------------------------------------------------------------
class EnlaceSimulado(EnlaceBase):
    """Responde como el firmware descrito en el contrato §5, con tiempos aproximados."""

    simulado = True

    def __init__(self, al_mensaje: Callable[[Mensaje], None], factor_tiempo: float = 1.0) -> None:
        super().__init__(al_mensaje)
        self._f = factor_tiempo
        self.angulo = 90
        self.home = 90
        self.calibracion = {"0": 170, "1": 90, "2": 10}
        self.objeto = False
        self.luz = False
        self.led = "OFF"
        self.lcd = [""] * 4
        self.scroll = ""
        self._moviendo = False
        self.ms_por_grado = 20

    async def iniciar(self) -> None:
        await super().iniciar()
        self.puerto = "SIMULADO"
        self._abierto = True
        self.conectado = True
        self._responder("READY", 0.05)
        self._avisar(CONECTADO)  # igual que el enlace real: el orquestador sincroniza los ángulos

    # --- utilidades
    def _responder(self, texto: str, segundos: float = 0.005) -> None:
        self._loop.call_later(max(segundos, 0.0) * self._f if segundos > 0.005 else 0.001,
                              self._procesar_linea, texto)

    def _mover(self, destino: int, respuesta: str) -> None:
        if self._moviendo:
            self._responder("ERR:OCUPADO")
            return
        self._moviendo = True
        duracion = abs(destino - self.angulo) * self.ms_por_grado / 1000 + 0.05

        def terminar() -> None:
            self.angulo = destino
            self._moviendo = False
            self._procesar_linea(respuesta)

        self._loop.call_later(duracion * self._f, terminar)

    # --- "firmware"
    def _escribir(self, linea: str) -> None:
        nombre, _, resto = linea.partition(":")
        args = resto.split(":") if resto else []
        if nombre == "PING":
            self._responder("PONG")
        elif nombre == "POS":
            if len(args) != 1 or args[0] not in self.calibracion:
                self._responder("ERR:ARG")
                return
            self._mover(self.calibracion[args[0]], f"POS_OK:{args[0]}")
        elif nombre == "ANG":
            try:
                grados = int(args[0])
            except (IndexError, ValueError):
                self._responder("ERR:ARG")
                return
            if not 0 <= grados <= 180:
                self._responder("ERR:ANG_RANGO")
                return
            self._mover(grados, f"ANG_OK:{grados}")
        elif nombre == "HOME":
            self._mover(self.home, "HOME_OK")
        elif nombre == "DROP":
            self._drop()
        elif nombre == "LIGHT" and args in (["ON"], ["OFF"]):
            self.luz = args[0] == "ON"
            self._responder("OK")
        elif nombre == "LED" and args and args[0] in ("VERDE", "AMARILLO", "ROJO", "OFF"):
            self.led = ":".join(args)
            self._responder("OK")
        elif nombre == "LCD":
            self.lcd = (resto.split("|") + [""] * 4)[:4]
            self._responder("OK")
        elif nombre == "LCD_SCROLL":
            self.scroll = resto
            self._responder("OK")
        elif nombre == "CAL":
            try:
                id_, grados = args[0], int(args[1])
            except (IndexError, ValueError):
                self._responder("ERR:ARG")
                return
            if id_ not in self.calibracion:
                self._responder("ERR:ARG")
            elif not 0 <= grados <= 180:
                self._responder("ERR:ANG_RANGO")
            else:
                self.calibracion[id_] = grados
                self._responder(f"CAL_OK:{id_}:{grados}")
        elif nombre == "STATUS":
            c = self.calibracion
            self._responder(f"STATUS:ang={self.angulo},tramp=CERRADA,obj={int(self.objeto)},"
                            f"cal={c['0']}/{c['1']}/{c['2']}")
        elif nombre in ("LIGHT", "LED"):
            self._responder("ERR:ARG")
        else:
            self._responder("ERR:CMD_DESCONOCIDO")

    def _drop(self) -> None:
        if self._moviendo:
            self._responder("ERR:OCUPADO")
            return
        # Como el firmware: abre, cierra y responde DROP_OK (no hay sensor de caída). Si había residuo, cae.
        def cerrar() -> None:
            habia = self.objeto
            self.objeto = False
            self._procesar_linea("DROP_OK")
            if habia:
                self._responder("LIBRE", 0.3)
        self._loop.call_later(0.9 * self._f, cerrar)

    # --- acciones de prueba (rutas /api/sim/*)
    def simular_objeto(self) -> bool:
        """Coloca un residuo en la bandeja. Devuelve False si ya había uno."""
        if self.objeto:
            return False
        self.objeto = True
        self._responder("OBJ", 0.3)  # antirrebote de 300 ms del firmware
        return True

    def simular_retiro(self) -> None:
        if self.objeto:
            self.objeto = False
            self._responder("LIBRE", 0.3)

    def simular_tecla(self, tecla: str) -> None:
        if tecla not in TECLAS_VALIDAS:
            raise ValueError(f"Tecla inválida: {tecla}")
        self._responder(f"KEY:{tecla}")
