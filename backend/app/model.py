"""
model.py — Clasificación: probabilidades por fotograma, promedio y REGLAS DE DECISIÓN (§4).

  - `aplicar_reglas()`: función pura con las reglas del reto (umbral general y asimetría de riesgo).
    Es la función ideal para "modificar en vivo" ante el jurado.
  - `ModeloReal`: MobileNetV2 preentrenado (ImageNet) como EXTRACTOR congelado → vector de 1280
    números por foto → clasificador propio (regresión logística de scikit-learn o cabeza densa de Keras).
  - `ModeloSimulado`: SIMULACION=1, probabilidades reproducibles (mismo fotograma → mismo resultado).
  - `ModeloNoDisponible`: cuando no hay modelo entrenado. El sistema NO adivina: el caso va a revisión.
  - `GestorReentrenamiento`: reentrena en segundo plano desde el panel (§14.3).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import cv2
import numpy as np

from .config import ID_PELIGROSO, IDS_CATEGORIA, Ajustes

log = logging.getLogger("modelo")

TAMANO_ENTRADA = 224        # MobileNetV2 espera 224×224 RGB
DIMENSION_EMBEDDING = 1280  # salida de MobileNetV2 con pooling promedio


@dataclass
class Decision:
    pred_id: int | None          # clase ganadora (argmax)
    confianza: float | None      # probabilidad de la ganadora
    dudoso: bool                 # True → REVISION (el sistema no adivina)
    motivo: str | None           # confianza_baja | riesgo_peligroso | sin_modelo | None


# =============================================================================
# Reglas de decisión (funciones puras, probadas en tests/test_reglas.py)
# =============================================================================
def promediar(probabilidades: Sequence[Sequence[float]]) -> np.ndarray:
    """Promedia las probabilidades de los 3 fotogramas (§10.3) y renormaliza a suma 1."""
    arreglo = np.asarray(probabilidades, dtype=float)
    if arreglo.ndim != 2 or arreglo.shape[1] != 3:
        raise ValueError("Se esperan probabilidades de forma (n_fotogramas, 3)")
    promedio = arreglo.mean(axis=0)
    return promedio / promedio.sum()


def aplicar_reglas(probs: Sequence[float], umbral_general: float, umbral_peligroso: float) -> Decision:
    """Reglas de decisión de la especificación §4.

    1. Si p(peligroso) ≥ UMBRAL_PELIGROSO y peligroso NO es la ganadora → revisión
       (asimetría de riesgo: mandar un peligroso a otro bote es el peor error).
    2. Si max(prob) < UMBRAL_GENERAL → revisión (el sistema no adivina).
    3. En otro caso se acepta la clase ganadora.
    Los límites son inclusivos: confianza = 0.60 se acepta; p(peligroso) = 0.35 manda a revisión.
    """
    p = [float(x) for x in probs]
    pred = int(np.argmax(p))
    confianza = p[pred]
    # Redondeo a 6 decimales para que 0.6000000001 o 0.5999999999 (promedios) no cambien la decisión
    if pred != ID_PELIGROSO and round(p[ID_PELIGROSO], 6) >= umbral_peligroso:
        return Decision(pred, confianza, True, "riesgo_peligroso")
    if round(confianza, 6) < umbral_general:
        return Decision(pred, confianza, True, "confianza_baja")
    return Decision(pred, confianza, False, None)


# =============================================================================
# Preprocesamiento (IGUAL al entrenar y al clasificar)
# =============================================================================
def recortar_roi(frame: np.ndarray, roi: Sequence[float]) -> np.ndarray:
    """Recorta la zona de interés [x, y, ancho, alto] (fracciones 0–1) de una imagen BGR."""
    alto_img, ancho_img = frame.shape[:2]
    x, y, ancho, alto = roi
    x0, y0 = int(round(x * ancho_img)), int(round(y * alto_img))
    x1 = max(x0 + 1, min(ancho_img, int(round((x + ancho) * ancho_img))))
    y1 = max(y0 + 1, min(alto_img, int(round((y + alto) * alto_img))))
    return frame[y0:y1, x0:x1]


def preparar_imagen(frame_bgr: np.ndarray, roi: Sequence[float]) -> np.ndarray:
    """BGR de OpenCV → recorte ROI → 224×224 → RGB (uint8). La normalización la hace el extractor."""
    recorte = recortar_roi(frame_bgr, roi)
    redimensionada = cv2.resize(recorte, (TAMANO_ENTRADA, TAMANO_ENTRADA), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(redimensionada, cv2.COLOR_BGR2RGB)


# =============================================================================
# Extractor de características (MobileNetV2 congelado)
# =============================================================================
class ExtractorMobileNet:
    """MobileNetV2 sin la capa superior + pooling promedio → vector de 1280 números por imagen.

    Se carga la primera vez que se usa (importar TensorFlow tarda unos segundos). Los pesos de
    ImageNet se leen de %USERPROFILE%\\.keras\\models (descargados en la Fase 0).
    Un candado evita que el reentrenamiento y la clasificación usen la red al mismo tiempo.
    """

    nombre = "MobileNetV2-imagenet-avg"

    def __init__(self) -> None:
        self._red = None
        self._preprocesar = None
        self._lock = threading.Lock()

    def _cargar(self) -> None:
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")  # menos mensajes de TensorFlow
        from keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input

        self._red = MobileNetV2(input_shape=(TAMANO_ENTRADA, TAMANO_ENTRADA, 3), include_top=False,
                                pooling="avg", weights="imagenet")
        self._preprocesar = preprocess_input

    def embeddings(self, imagenes_rgb: np.ndarray) -> np.ndarray:
        """(n, 224, 224, 3) uint8 RGB → (n, 1280) float32."""
        with self._lock:
            if self._red is None:
                self._cargar()
            x = self._preprocesar(np.asarray(imagenes_rgb, dtype=np.float32))
            return np.asarray(self._red.predict(x, verbose=0, batch_size=16), dtype=np.float32)


# =============================================================================
# Modelos
# =============================================================================
class ErrorModelo(Exception):
    pass


class ModeloBase:
    version: str | None = None
    simulado = False
    cargado = False
    motivo_no_cargado: str | None = None

    def predecir(self, frames: list[np.ndarray], pista: dict[str, Any] | None = None) -> list[np.ndarray]:
        """Devuelve una lista de vectores [p_organica, p_inorganica, p_peligroso], uno por fotograma."""
        raise NotImplementedError

    def calentar(self) -> None:
        """Prepara el modelo (carga pesada) antes del primer residuo. Por defecto no hace nada."""


class ModeloNoDisponible(ModeloBase):
    def __init__(self, motivo: str) -> None:
        self.motivo_no_cargado = motivo

    def predecir(self, frames, pista=None):
        raise ErrorModelo(self.motivo_no_cargado)


class ModeloReal(ModeloBase):
    """Carga una versión entrenada de models/v<N>/ (la crea training/train.py)."""

    simulado = False
    cargado = True

    def __init__(self, dir_version: Path, extractor: ExtractorMobileNet) -> None:
        self.dir = Path(dir_version)
        self.version = self.dir.name
        self.extractor = extractor
        meta = json.loads((self.dir / "labels.json").read_text(encoding="utf-8"))
        self.roi = meta["roi"]
        self.cabeza = meta["cabeza"]
        self.clases = [int(c) for c in meta["clases"]]
        if self.cabeza == "logistica":
            import joblib

            self._clasificador = joblib.load(self.dir / "modelo.joblib")
        elif self.cabeza == "densa":
            import keras

            self._clasificador = keras.models.load_model(self.dir / "cabeza.keras")
        else:
            raise ErrorModelo(f"Cabeza desconocida: {self.cabeza}")

    def probabilidades(self, embeddings: np.ndarray) -> np.ndarray:
        """(n, 1280) → (n, 3) con columnas en el orden 0 orgánica, 1 inorgánica, 2 peligroso."""
        if self.cabeza == "logistica":
            crudas = self._clasificador.predict_proba(embeddings)
        else:
            crudas = np.asarray(self._clasificador.predict(embeddings, verbose=0))
        salida = np.zeros((len(embeddings), 3))
        for columna, clase in enumerate(self.clases):
            salida[:, clase] = crudas[:, columna]
        return salida

    def predecir(self, frames, pista=None):
        imagenes = np.stack([preparar_imagen(f, self.roi) for f in frames])
        return list(self.probabilidades(self.extractor.embeddings(imagenes)))

    def calentar(self) -> None:
        self.extractor.embeddings(np.zeros((1, TAMANO_ENTRADA, TAMANO_ENTRADA, 3), dtype=np.uint8))


class ModeloSimulado(ModeloBase):
    """Probabilidades simuladas y reproducibles (la semilla sale del contenido del fotograma).

    Con la "pista" de la cámara simulada:
      - categoría forzada (desde /api/sim/objeto) → acierta con confianza 0.70–0.97;
      - "dudoso" → confianza baja (0.38–0.52);
      - categoría al azar → 85 % acierta, 10 % dudoso, 5 % se equivoca con confianza (realista).
    """

    version = "sim"
    simulado = True
    cargado = True

    def predecir(self, frames, pista=None):
        semilla = int.from_bytes(hashlib.sha1(frames[0].tobytes()).digest()[:8], "big")
        azar = np.random.default_rng(semilla)
        base = self._base(azar, pista or {})
        salida = []
        for _ in frames:
            p = np.clip(base + azar.normal(0, 0.01, 3), 1e-4, None)
            salida.append(p / p.sum())
        return salida

    @staticmethod
    def _base(azar: np.random.Generator, pista: dict[str, Any]) -> np.ndarray:
        categoria = pista.get("categoria")
        forzada = bool(pista.get("forzada"))
        if categoria not in (0, 1, 2, "dudoso"):
            categoria = int(azar.integers(3))
        if categoria != "dudoso" and not forzada:
            r = azar.random()
            if r < 0.10:
                categoria = "dudoso"
            elif r < 0.15:
                categoria = int((categoria + 1 + azar.integers(2)) % 3)  # error con confianza
        if categoria == "dudoso":
            ganadora = int(azar.integers(2))  # orgánica o inorgánica, sin riesgo peligroso
            p = np.zeros(3)
            p[ganadora] = azar.uniform(0.38, 0.52)
            p[1 - ganadora] = (1 - p[ganadora]) * azar.uniform(0.55, 0.75)
            p[2] = 1 - p[0] - p[1]
            return p
        p = np.zeros(3)
        p[categoria] = azar.uniform(0.70, 0.97)
        resto = 1 - p[categoria]
        otras = [c for c in range(3) if c != categoria]
        reparto = azar.uniform(0.2, 0.8)
        p[otras[0]], p[otras[1]] = resto * reparto, resto * (1 - reparto)
        return p


def version_activa(db) -> str | None:
    fila = db.uno("SELECT version FROM modelos WHERE activo = 1 ORDER BY fecha DESC LIMIT 1")
    return fila["version"] if fila else None


def cargar_modelo(ajustes: Ajustes, db, extractor: ExtractorMobileNet | None = None) -> ModeloBase:
    """SIMULACION=1 → simulado. Si no, la versión marcada como activa en la tabla `modelos`."""
    if ajustes.simulacion:
        return ModeloSimulado()
    version = version_activa(db)
    if version is None:
        return ModeloNoDisponible("No hay modelo entrenado todavía (python -m training.train)")
    try:
        return ModeloReal(ajustes.dir_modelos / version, extractor or ExtractorMobileNet())
    except Exception as error:  # noqa: BLE001 — archivo dañado o incompleto: no se adivina
        return ModeloNoDisponible(f"No se pudo cargar el modelo {version}: {error}")


# =============================================================================
# Reentrenamiento en segundo plano (POST /api/modelo/reentrenar)
# =============================================================================
class GestorReentrenamiento:
    """Ejecuta training.train.entrenar() en un hilo y avisa el progreso por WebSocket.

    Solo se activa la nueva versión si su precisión de validación no empeora (§14.3).
    """

    def __init__(self, ajustes: Ajustes, db, obtener_roi: Callable[[], list[float]],
                 extractor: ExtractorMobileNet, al_cambiar: Callable[[dict[str, Any]], Any],
                 al_activar: Callable[[ModeloBase], None]) -> None:
        self.ajustes = ajustes
        self.db = db
        self.obtener_roi = obtener_roi
        self.extractor = extractor
        self.al_cambiar = al_cambiar      # corrutina que emite el evento "modelo"
        self.al_activar = al_activar      # cambia el modelo del orquestador
        self.entrenando = False
        self.progreso: float | None = None
        self.mensaje: str | None = None
        self.ultimo_resultado: dict[str, Any] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def estado(self, version_en_uso: str | None) -> dict[str, Any]:
        versiones = self.db.consultar(
            "SELECT version, fecha, n_imagenes, precision_val, activo FROM modelos ORDER BY fecha DESC")
        for v in versiones:
            v["activo"] = bool(v["activo"])
        return {"activo": version_en_uso, "entrenando": self.entrenando, "progreso": self.progreso,
                "mensaje": self.mensaje, "ultimo_resultado": self.ultimo_resultado, "versiones": versiones}

    def _avisar(self) -> None:
        if self._loop is not None:
            asyncio.run_coroutine_threadsafe(self.al_cambiar(), self._loop)

    async def iniciar(self) -> None:
        if self.entrenando:
            raise RuntimeError("Ya hay un entrenamiento en curso")
        self._loop = asyncio.get_running_loop()
        self.entrenando, self.progreso, self.mensaje = True, 0.0, "Iniciando"
        await self.al_cambiar()
        self._loop.run_in_executor(None, self._trabajo)

    def _trabajo(self) -> None:
        from training.train import entrenar  # importación tardía: evita cargar el entrenamiento al arrancar

        def progreso(fraccion: float, mensaje: str) -> None:
            self.progreso, self.mensaje = round(fraccion, 2), mensaje
            self._avisar()

        try:
            resultado = entrenar(dir_dataset=self.ajustes.dir_dataset, dir_modelos=self.ajustes.dir_modelos,
                                 db=self.db, roi=self.obtener_roi(), extractor=self.extractor, progreso=progreso)
            self.ultimo_resultado = {k: resultado[k] for k in
                                     ("version", "precision_val", "precision_anterior", "activado", "mensaje")}
            if resultado["activado"] and not self.ajustes.simulacion:
                nuevo = ModeloReal(self.ajustes.dir_modelos / resultado["version"], self.extractor)
                self._loop.call_soon_threadsafe(self.al_activar, nuevo)
        except Exception as error:  # noqa: BLE001 — se informa en el panel
            log.exception("Reentrenamiento fallido")
            self.ultimo_resultado = {"version": None, "precision_val": None, "precision_anterior": None,
                                     "activado": False, "mensaje": f"Falló el entrenamiento: {error}"}
        finally:
            self.entrenando, self.progreso = False, None
            self.mensaje = self.ultimo_resultado["mensaje"] if self.ultimo_resultado else None
            self._avisar()
