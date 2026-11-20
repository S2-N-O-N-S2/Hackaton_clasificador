"""
camera.py — Captura de la cámara cenital (OpenCV), guardado de fotos y copia al dataset.

  - `CamaraReal`: webcam USB con OpenCV (índice en la configuración).
  - `CamaraSimulada`: SIMULACION=1. Toma imágenes de `sim_images/` (subcarpetas organica/,
    inorganica/, peligroso/, dudoso/) y, si no hay, dibuja una imagen sintética rotulada "SIMULADO".
"""

from __future__ import annotations

import asyncio
import os
import random
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Abre más rápido las cámaras con Media Foundation (MSMF) en Windows; debe ir antes de importar cv2
os.environ.setdefault("OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS", "0")

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from .config import CAMARA, CLAVES_CATEGORIA, Ajustes

EXTENSIONES = (".jpg", ".jpeg", ".png")
ANCHO, ALTO = 640, 480


class ErrorCamara(Exception):
    pass


class CamaraBase:
    simulada = False

    def __init__(self, ajustes: Ajustes) -> None:
        self.ajustes = ajustes
        self.disponible = False
        self.indice: int | None = None
        self.ultima_pista: dict[str, Any] | None = None  # solo la usa la simulación

    async def iniciar(self) -> None: ...

    def cerrar(self) -> None: ...

    async def capturar(self, n: int) -> list[np.ndarray]:
        raise NotImplementedError

    def vista(self, calidad: int = 70) -> bytes | None:
        """Un cuadro JPEG para la vista en vivo del panel. None si no hay imagen (o la cámara está ocupada)."""
        return None

    # --- guardado
    def guardar_foto(self, frame: np.ndarray) -> str:
        """Guarda en captures/AAAAMMDD_HHMMSS.jpg (agrega _2, _3... si ya existe). Devuelve el nombre."""
        base = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre, n = f"{base}.jpg", 2
        while (self.ajustes.dir_capturas / nombre).exists():
            nombre, n = f"{base}_{n}.jpg", n + 1
        if not cv2.imwrite(str(self.ajustes.dir_capturas / nombre), frame):
            raise ErrorCamara(f"No se pudo guardar la foto {nombre}")
        return nombre


def copiar_a_dataset(ajustes: Ajustes, nombre_foto: str | None, clase_id: int, verificado: bool) -> Path | None:
    """Copia una captura al dataset para reentrenar (§4 regla 4 y §14.3).

    verificado=True  (operador desde el panel)  → dataset/<clase>/
    verificado=False (usuario: voz o teclado)   → dataset/_por_verificar/<clase>/

    En simulación las fotos son FALSAS: nunca entran al dataset. Con SIM_IA_REAL=1 la foto sí es de la cámara
    real, pero el caso es simulado, así que va siempre a _por_verificar/ (alguien la revisa antes de entrenar).
    """
    if not nombre_foto:
        return None
    if ajustes.simulacion and not ajustes.ia_real:
        return None
    if ajustes.simulacion:
        verificado = False
    origen = ajustes.dir_capturas / nombre_foto
    if not origen.exists():
        return None
    clave = CLAVES_CATEGORIA[clase_id]
    destino_dir = ajustes.dir_dataset / clave if verificado else ajustes.dir_dataset / "_por_verificar" / clave
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / nombre_foto
    shutil.copy2(origen, destino)
    return destino


# ---------------------------------------------------------------------------
# Cámara real
# ---------------------------------------------------------------------------
def abrir_captura(fuente: int | str) -> cv2.VideoCapture:
    """Abre una cámara por índice o un celular por URL (http://IP:4747/video).

    Por índice se usa Media Foundation (MSMF): ve las webcams USB y también las cámaras virtuales
    nuevas (DroidCam 7, cámara conectada de Windows 11), que DirectShow no muestra. Si MSMF no
    puede abrirla, se intenta con DirectShow (DSHOW).
    """
    if isinstance(fuente, str):
        return cv2.VideoCapture(fuente)
    captura = cv2.VideoCapture(fuente, cv2.CAP_MSMF)
    if captura.isOpened():
        return captura
    captura.release()
    return cv2.VideoCapture(fuente, cv2.CAP_DSHOW)


def imagen_es_plana(frame: np.ndarray, umbral: float = 4.0) -> bool:
    """True si la imagen es de un solo color (p. ej. la pantalla verde de DroidCam sin señal)."""
    # Variación de cada canal (B, G, R) por separado: un verde liso tiene canales muy distintos entre
    # sí, pero cada uno es constante en toda la imagen
    return float(frame.reshape(-1, frame.shape[-1]).std(axis=0).max()) < umbral


# ---------------------------------------------------------------------------
# Calidad de la foto (funciones puras, probadas en tests/test_camara.py)
# ---------------------------------------------------------------------------
class FotoNoValida(Exception):
    """Ningún fotograma pasó la revisión de calidad. NO es una falla de la cámara: el residuo va a revisión."""

    def __init__(self, problema: str, frame: np.ndarray | None = None) -> None:
        super().__init__(TEXTO_PROBLEMA.get(problema, problema))
        self.problema = problema
        self.frame = frame  # la mejor de las fotos malas, para guardarla como evidencia


TEXTO_PROBLEMA = {
    "sin_senal": "La cámara no tiene señal (imagen de un solo color)",
    "oscura": "La foto salió oscura",
    "quemada": "La foto salió quemada (demasiada luz)",
    "borrosa": "La foto salió borrosa o movida",
}


def _gris_chico(frame: np.ndarray, ancho: int = 160) -> np.ndarray:
    alto = max(1, int(frame.shape[0] * ancho / frame.shape[1]))
    gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    return cv2.resize(gris, (ancho, alto), interpolation=cv2.INTER_AREA)


def metricas_foto(frame: np.ndarray) -> dict[str, float]:
    """Brillo medio (0–255), nitidez (varianza del Laplaciano) y variación máxima por canal."""
    gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    canales = frame.reshape(-1, frame.shape[-1]) if frame.ndim == 3 else gris.reshape(-1, 1)
    return {
        "brillo": float(gris.mean()),
        "nitidez": float(cv2.Laplacian(gris, cv2.CV_64F).var()),
        "variacion": float(canales.std(axis=0).max()),
    }


def evaluar_foto(frame: np.ndarray, u: dict[str, float]) -> str | None:
    """Devuelve el problema de la foto ('sin_senal', 'oscura', 'quemada', 'borrosa') o None si está bien."""
    m = metricas_foto(frame)
    # Primero el brillo: una foto casi negra también es "plana", pero el problema real es la luz
    if m["brillo"] < u["brillo_min"]:
        return "oscura"
    if m["brillo"] > u["brillo_max"]:
        return "quemada"
    if m["variacion"] < u["plana_std"]:
        return "sin_senal"
    if m["nitidez"] < u["nitidez_min"]:
        return "borrosa"
    return None


def diferencia_fotogramas(a: np.ndarray, b: np.ndarray) -> float:
    """Diferencia media (0–255) entre dos fotogramas, en gris y a baja resolución (rápido y sin ruido)."""
    return float(cv2.absdiff(_gris_chico(a), _gris_chico(b)).mean())


def elegir_fotogramas(frames: list[np.ndarray], n: int, u: dict[str, float]) -> list[np.ndarray]:
    """Quita los fotogramas malos y devuelve los `n` más nítidos, en su orden original.

    Si ninguno sirve, lanza FotoNoValida con el problema más frecuente (y la foto más nítida como evidencia).
    """
    if not frames:
        raise FotoNoValida("sin_senal")
    evaluados = [(i, f, evaluar_foto(f, u), metricas_foto(f)["nitidez"]) for i, f in enumerate(frames)]
    buenos = [e for e in evaluados if e[2] is None]
    if not buenos:
        problemas = [e[2] for e in evaluados]
        peor = max(set(problemas), key=problemas.count)
        evidencia = max(evaluados, key=lambda e: e[3])[1]
        raise FotoNoValida(peor, evidencia)
    mejores = sorted(buenos, key=lambda e: e[3], reverse=True)[:max(1, n)]
    return [e[1] for e in sorted(mejores, key=lambda e: e[0])]


class CamaraReal(CamaraBase):
    def __init__(self, ajustes: Ajustes, indice: int | str) -> None:
        super().__init__(ajustes)
        self.indice = indice
        self._cap: cv2.VideoCapture | None = None
        self._lock = threading.Lock()
        self.ultimo_error: str | None = None

    def _abrir(self) -> None:
        cap = abrir_captura(self.indice)
        if not cap.isOpened():
            cap.release()
            raise ErrorCamara(f"No se pudo abrir la cámara {self.indice}")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO)
        for _ in range(5):  # los primeros fotogramas salen oscuros mientras ajusta la exposición
            cap.read()
        self._cap = cap

    async def iniciar(self) -> None:
        try:
            await asyncio.get_running_loop().run_in_executor(None, self._abrir_seguro)
        except ErrorCamara as error:
            self.ultimo_error = str(error)

    def _abrir_seguro(self) -> None:
        with self._lock:
            self._abrir()
            self.disponible = True

    def cerrar(self) -> None:
        with self._lock:
            if self._cap is not None:
                self._cap.release()
            self._cap = None
            self.disponible = False

    def _leer(self) -> np.ndarray:
        ok, frame = self._cap.read()
        if not ok or frame is None:
            self._cap.release()
            self._cap = None
            raise ErrorCamara("La cámara no entregó imagen")
        return frame

    def _capturar_bloqueante(self, n: int) -> list[np.ndarray]:
        """1) tira las fotos viejas del búfer, 2) espera a que la imagen esté quieta (residuo asentado y
        exposición ajustada a la luz), 3) toma varios candidatos y devuelve los `n` más nítidos que pasen la
        revisión de calidad. Si ninguno pasa, FotoNoValida (el orquestador reintenta y luego manda a revisión)."""
        c = CAMARA
        with self._lock:
            if self._cap is None:
                self._abrir()  # reintento si la cámara se desconectó
            # 1) Vaciar el búfer por TIEMPO, no por cantidad: MSMF y DroidCam guardan varios fotogramas viejos
            fin = time.monotonic() + c["vaciar_bufer_s"]
            while time.monotonic() < fin:
                if not self._cap.grab():
                    break
            # 2) Esperar estabilidad: dos fotogramas seguidos casi iguales
            anterior = self._leer()
            fin = time.monotonic() + c["estabilidad_max_s"]
            while time.monotonic() < fin:
                actual = self._leer()
                quieta = diferencia_fotogramas(anterior, actual) < c["estabilidad_diferencia"]
                anterior = actual
                if quieta:
                    break
            # 3) Candidatos
            candidatos = [anterior]
            for _ in range(int(c["candidatos"]) - 1):
                time.sleep(c["pausa_candidatos_s"])
                candidatos.append(self._leer())
        return elegir_fotogramas(candidatos, n, c)

    def vista(self, calidad: int = 70) -> bytes | None:
        """Cuadro para la vista en vivo. Si el ciclo está tomando la foto (candado ocupado) NO espera: devuelve
        None y el panel deja congelado el último cuadro. Nunca cierra la cámara por un cuadro fallido."""
        if not self._lock.acquire(blocking=False):
            return None
        try:
            if self._cap is None:
                return None
            ok, frame = self._cap.read()
            if not ok or frame is None:
                return None
            ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, calidad])
            return jpg.tobytes() if ok else None
        finally:
            self._lock.release()

    async def capturar(self, n: int) -> list[np.ndarray]:
        try:
            frames = await asyncio.get_running_loop().run_in_executor(None, self._capturar_bloqueante, n)
        except FotoNoValida:
            self.disponible = True  # la cámara funciona; la foto es la que salió mal
            raise
        except ErrorCamara as error:
            self.disponible = False
            self.ultimo_error = str(error)
            raise
        self.disponible = True
        return frames


# ---------------------------------------------------------------------------
# Cámara simulada
# ---------------------------------------------------------------------------
CARPETAS_SIM = CLAVES_CATEGORIA + ["dudoso"]
# Pistas de /api/sim/objeto además de 0/1/2: "foto_mala" (fotos oscuras, prueba la revisión de calidad)
# y "desconocido" (un objeto que el modelo nunca vio, prueba la detección de objetos desconocidos).
PISTAS_ESPECIALES = ("dudoso", "foto_mala", "desconocido")


class CamaraSimulada(CamaraBase):
    """La "verdad" de cada imagen simulada viaja en `ultima_pista` para que el modelo simulado la use."""

    simulada = True

    def __init__(self, ajustes: Ajustes) -> None:
        super().__init__(ajustes)
        self.indice = None
        self.pista_siguiente: Any = None   # 0/1/2/"dudoso"/"foto_mala"/"desconocido" desde /api/sim/objeto
        self._contador = 0
        self._fotos_malas = 0               # capturas que todavía deben salir oscuras (incluye el reintento)
        self._azar = random.Random(2026)    # reproducible

    async def iniciar(self) -> None:
        self.disponible = True

    def _imagenes(self, carpeta: str | None) -> list[Path]:
        raiz = self.ajustes.dir_sim_imagenes
        rutas = [raiz / carpeta] if carpeta else [raiz / c for c in CARPETAS_SIM]
        return sorted(p for r in rutas if r.is_dir() for p in r.iterdir() if p.suffix.lower() in EXTENSIONES)

    async def capturar(self, n: int) -> list[np.ndarray]:
        self._contador += 1
        forzada = self.pista_siguiente is not None
        pista = self.pista_siguiente
        self.pista_siguiente = None
        if pista == "foto_mala":
            self._fotos_malas = int(CAMARA["reintentos"]) + 1
            pista = self._azar.choice([0, 1, 2])
        if pista is None:
            pista = self._azar.choice([0, 1, 2])
        carpeta = pista if pista in ("dudoso", "desconocido") else CLAVES_CATEGORIA[pista]
        archivos = self._imagenes(carpeta)
        if archivos:
            imagen = cv2.imread(str(self._azar.choice(archivos)))
            imagen = cv2.resize(imagen, (ANCHO, ALTO)) if imagen is not None else self._sintetica(pista)
        else:
            imagen = self._sintetica(pista)
        if self._fotos_malas > 0:  # simula una foto con la luz apagada
            self._fotos_malas -= 1
            imagen = (imagen * 0.08).astype(np.uint8)
        self.ultima_pista = {"categoria": pista, "forzada": forzada}
        ruido = np.random.default_rng(self._contador)
        frames = [
            np.clip(imagen.astype(np.int16) + ruido.integers(-3, 4, imagen.shape), 0, 255).astype(np.uint8)
            for _ in range(max(n, 1))
        ]
        # Misma revisión de calidad que la cámara real (aquí todos los fotogramas son parecidos)
        return elegir_fotogramas(frames, n, CAMARA)

    def _sintetica(self, pista: Any) -> np.ndarray:
        """Bandeja gris uniforme con una figura según la categoría simulada."""
        img = np.full((ALTO, ANCHO, 3), 190, dtype=np.uint8)
        cv2.rectangle(img, (120, 60), (520, 420), (215, 215, 215), -1)  # fondo de la bandeja
        centro = (320 + self._azar.randint(-60, 60), 240 + self._azar.randint(-40, 40))
        if pista == 0:
            cv2.ellipse(img, centro, (70, 40), self._azar.randint(0, 180), 0, 360, (40, 160, 60), -1)
        elif pista == 1:
            cv2.rectangle(img, (centro[0] - 40, centro[1] - 80), (centro[0] + 40, centro[1] + 80), (200, 120, 30), -1)
        elif pista == 2:
            cv2.rectangle(img, (centro[0] - 25, centro[1] - 45), (centro[0] + 25, centro[1] + 45), (90, 90, 90), -1)
            cv2.putText(img, "+", (centro[0] - 15, centro[1] + 15), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 220), 3)
        elif pista == "desconocido":  # objeto que el modelo nunca vio (p. ej. un celular)
            cv2.rectangle(img, (centro[0] - 50, centro[1] - 90), (centro[0] + 50, centro[1] + 90), (30, 30, 30), -1)
            cv2.rectangle(img, (centro[0] - 42, centro[1] - 78), (centro[0] + 42, centro[1] + 70), (200, 90, 160), -1)
        else:  # dudoso / no entrenado
            puntos = np.array([[centro[0], centro[1] - 60], [centro[0] - 60, centro[1] + 50],
                               [centro[0] + 60, centro[1] + 50]])
            cv2.fillPoly(img, [puntos], (0, 200, 230))
        cv2.putText(img, f"SIMULADO #{self._contador}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        return img
