"""
game.py — Modo "¿Le ganas a la IA?" (especificación §12).

Fase 3 (actual): solo devuelve estructuras vacías con el formato del contrato (§3.9), para que el
panel pueda dibujar sus vistas. El orquestador ya tiene los estados ESPERA_ADIVINANZA y
RETROALIMENTACION; por ahora ESPERA_ADIVINANZA "pasa de largo".
Fase 8 (pendiente): flujo completo, niveles de certeza, explicaciones, marcador y curva de aprendizaje.
"""

from __future__ import annotations

from typing import Any

NIVELES_REPORTABLES = ("verificada", "alta")


class Juego:
    activo = False  # Fase 8: True cuando el flujo esté implementado

    def __init__(self, db) -> None:
        self.db = db

    def sesion(self) -> dict[str, Any]:
        return {"activa": False}

    def estadisticas(self, niveles: tuple[str, ...] = NIVELES_REPORTABLES) -> dict[str, Any]:
        return {
            "niveles_usados": list(niveles), "n_adivinanzas": 0, "n_sesiones": 0,
            "acierto_humano": None, "por_categoria": {"0": {"n": 0, "acierto": None},
                                                       "1": {"n": 0, "acierto": None},
                                                       "2": {"n": 0, "acierto": None}},
            "matriz_confusion_humana": {"etiquetas": [0, 1, 2], "filas": "real", "columnas": "adivinanza",
                                        "valores": [[0, 0, 0], [0, 0, 0], [0, 0, 0]]},
            "humano_vs_ia": {"n": 0, "acierto_humano": None, "acierto_ia": None},
            "parejas_confusion": [], "media_aparte": {"n_adivinanzas": 0, "acierto_humano": None},
            "muestra_pequena": True,
        }

    def aprendizaje(self, niveles: tuple[str, ...] = NIVELES_REPORTABLES) -> dict[str, Any]:
        return {
            "niveles_usados": list(niveles), "por_intento": [],
            "mitades": {"n_sesiones": 0, "primera": None, "segunda": None, "diferencia": None},
            "correccion_tras_explicacion": {"n_oportunidades": 0, "corregidas": 0, "tasa": None},
            "rondas": {"por_participante": [], "promedio": {"ronda1": None, "ronda2": None, "n_voluntarios": 0}},
            "muestra": {"n_sesiones": 0, "n_intentos": 0, "n_voluntarios": 0},
            "muestra_pequena": True,
        }
