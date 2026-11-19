"""
voice.py — Voz offline con Vosk (especificación §15).

Fase 3 (actual): solo informa que la voz no está disponible.
Fase 9 (pendiente): push-to-talk con la tecla A, gramática restringida por estado y keywords.json.
"""

from __future__ import annotations


class Voz:
    disponible = False

    def estado(self) -> dict:
        return {"disponible": self.disponible}
