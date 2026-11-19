"""
model.py — Clasificación: probabilidades por fotograma, promedio y REGLAS DE DECISIÓN (§4).

  - `aplicar_reglas()`: función pura con las reglas del reto (umbral general y asimetría de riesgo).
    Es la función ideal para "modificar en vivo" ante el jurado.
  - `ModeloSimulado`: SIMULACION=1, probabilidades reproducibles (mismo fotograma → mismo resultado).
  - `ModeloNoDisponible`: cuando no hay modelo entrenado. El sistema NO adivina: el caso va a revisión.
  - El modelo real (MobileNetV2 + LogisticRegression) se agrega en la Fase 4.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from .config import ID_PELIGROSO, Ajustes


@dataclass
class Decision:
    pred_id: int | None          # clase ganadora (argmax)
    confianza: float | None      # probabilidad de la ganadora
    dudoso: bool                 # True → REVISION (el sistema no adivina)
    motivo: str | None           # confianza_baja | riesgo_peligroso | sin_modelo | None


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


class ModeloNoDisponible(ModeloBase):
    def __init__(self, motivo: str) -> None:
        self.motivo_no_cargado = motivo

    def predecir(self, frames, pista=None):
        raise ErrorModelo(self.motivo_no_cargado)


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


def cargar_modelo(ajustes: Ajustes) -> ModeloBase:
    if ajustes.simulacion:
        return ModeloSimulado()
    # Fase 4: aquí se cargará models/v<N>/ (MobileNetV2 + LogisticRegression)
    return ModeloNoDisponible("No hay modelo entrenado todavía (Fase 4: training/train.py)")
