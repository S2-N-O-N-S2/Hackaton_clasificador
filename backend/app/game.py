"""
game.py — Entrenamiento (antes "¿Le ganas a la IA?") con fotos del dataset.

Desde el 20-nov el juego ya NO usa la máquina: la persona clasifica fotos del dataset en el panel
(app/practica.py elige las fotos). Cada respuesta se guarda en la tabla `practica_respuestas` junto con lo que
la IA predice para ESA MISMA foto, y de ahí salen:
  - Humano vs. IA (`estadisticas`): acierto de las personas y de la IA con las mismas fotos, por categoría,
    matriz de confusión humana y errores más repetidos.
  - Aprendizaje (`aprendizaje`): acierto por número de pregunta, primera mitad vs. segunda mitad de cada
    sesión y si la persona corrige una categoría después de fallarla.

Honestidad: la IA se entrenó con la mayoría de estas fotos. Por eso cada respuesta guarda si la foto fue de
VALIDACIÓN (la IA nunca la vio, según models/<versión>/split.json) y la comparación justa se reporta aparte.
El formato de respuesta es el del contrato §3.9 (las vistas del panel no cambian de forma).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .db import ahora

NIVELES_REPORTABLES = ("verificada", "alta")  # se conserva por compatibilidad de la API (no aplica a fotos)
MIN_SESIONES = 10  # menos sesiones que esto → "muestra pequeña: resultado indicativo"


def _tasa(aciertos: int, n: int) -> float | None:
    return round(aciertos / n, 3) if n else None


def fotos_de_validacion(dir_modelo: Path | None) -> set[str]:
    """Fotos ("clave/archivo") que la IA NO vio al entrenar, según split.json de la versión activa."""
    if dir_modelo is None:
        return set()
    ruta = Path(dir_modelo) / "split.json"
    if not ruta.exists():
        return set()
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return {str(f).replace("\\", "/") for f in datos.get("validacion", [])}


class Juego:
    activo = False  # el flujo con la máquina (ESPERA_ADIVINANZA) ya no se usa

    def __init__(self, db) -> None:
        self.db = db

    def sesion(self) -> dict[str, Any]:
        return {"activa": False}

    # ------------------------------------------------------------------ registro
    def registrar_respuesta(self, sesion: str, foto: str, categoria_real: int, respuesta: int, intento: int,
                            pred_ia: int | None, confianza_ia: float | None, foto_validacion: bool) -> dict[str, Any]:
        correcto = int(respuesta == categoria_real)
        self.db.ejecutar(
            "INSERT INTO practica_respuestas(fecha_hora, sesion, foto, categoria_real, respuesta, correcto, intento, "
            "pred_ia, confianza_ia, foto_validacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ahora(), sesion, foto, categoria_real, respuesta, correcto, intento, pred_ia, confianza_ia,
             int(foto_validacion)),
        )
        return {
            "correcto": bool(correcto), "categoria_real": categoria_real,
            "ia": None if pred_ia is None else {"pred_id": pred_ia, "confianza": confianza_ia,
                                                "correcto": pred_ia == categoria_real},
            "foto_validacion": foto_validacion,
        }

    def _filas(self) -> list[Any]:
        return self.db.consultar("SELECT * FROM practica_respuestas ORDER BY sesion, intento, id")

    # ------------------------------------------------------------------ Humano vs. IA
    def estadisticas(self, niveles: tuple[str, ...] = NIVELES_REPORTABLES) -> dict[str, Any]:
        filas = self._filas()
        n = len(filas)
        sesiones = {f["sesion"] for f in filas}
        matriz = [[0, 0, 0] for _ in range(3)]
        por_cat = {str(c): {"n": 0, "aciertos": 0} for c in range(3)}
        parejas: dict[tuple[int, int], int] = {}
        for f in filas:
            matriz[f["categoria_real"]][f["respuesta"]] += 1
            pc = por_cat[str(f["categoria_real"])]
            pc["n"] += 1
            pc["aciertos"] += f["correcto"]
            if not f["correcto"]:
                clave = (f["respuesta"], f["categoria_real"])
                parejas[clave] = parejas.get(clave, 0) + 1
        con_ia = [f for f in filas if f["pred_ia"] is not None]
        no_vistas = [f for f in con_ia if f["foto_validacion"]]
        return {
            "niveles_usados": list(niveles),
            "n_adivinanzas": n, "n_sesiones": len(sesiones),
            "acierto_humano": _tasa(sum(f["correcto"] for f in filas), n),
            "por_categoria": {c: {"n": v["n"], "acierto": _tasa(v["aciertos"], v["n"])} for c, v in por_cat.items()},
            "matriz_confusion_humana": {"etiquetas": [0, 1, 2], "filas": "real", "columnas": "adivinanza",
                                        "valores": matriz},
            "humano_vs_ia": {
                "n": len(con_ia),
                "acierto_humano": _tasa(sum(f["correcto"] for f in con_ia), len(con_ia)),
                "acierto_ia": _tasa(sum(f["pred_ia"] == f["categoria_real"] for f in con_ia), len(con_ia)),
                # Comparación justa: solo fotos de validación (la IA no las vio al entrenar)
                "n_no_vistas": len(no_vistas),
                "acierto_humano_no_vistas": _tasa(sum(f["correcto"] for f in no_vistas), len(no_vistas)),
                "acierto_ia_no_vistas": _tasa(sum(f["pred_ia"] == f["categoria_real"] for f in no_vistas),
                                              len(no_vistas)),
            },
            "parejas_confusion": [{"dijo": d, "era": e, "veces": v}
                                  for (d, e), v in sorted(parejas.items(), key=lambda x: -x[1])[:5]],
            "media_aparte": {"n_adivinanzas": 0, "acierto_humano": None},  # no aplica a fotos
            "fuente": "fotos",
            "muestra_pequena": len(sesiones) < MIN_SESIONES,
        }

    # ------------------------------------------------------------------ Aprendizaje
    def aprendizaje(self, niveles: tuple[str, ...] = NIVELES_REPORTABLES) -> dict[str, Any]:
        filas = self._filas()
        por_sesion: dict[str, list[Any]] = {}
        for f in filas:
            por_sesion.setdefault(f["sesion"], []).append(f)

        # Acierto por número de pregunta (1, 2, … 9, 10+)
        grupos: dict[str, list[int]] = {}
        for respuestas in por_sesion.values():
            for i, f in enumerate(respuestas, start=1):
                grupos.setdefault(str(i) if i < 10 else "10+", []).append(f["correcto"])
        orden = [str(i) for i in range(1, 10)] + ["10+"]
        por_intento = [{"intento": k, "n": len(grupos[k]), "acierto": _tasa(sum(grupos[k]), len(grupos[k]))}
                       for k in orden if k in grupos]

        # Primera mitad vs. segunda mitad (solo sesiones con 4 o más respuestas)
        primeras, segundas = [], []
        for respuestas in por_sesion.values():
            if len(respuestas) >= 4:
                mitad = len(respuestas) // 2
                primeras.append(sum(f["correcto"] for f in respuestas[:mitad]) / mitad)
                segundas.append(sum(f["correcto"] for f in respuestas[mitad:]) / (len(respuestas) - mitad))
        primera = round(sum(primeras) / len(primeras), 3) if primeras else None
        segunda = round(sum(segundas) / len(segundas), 3) if segundas else None

        # Corrección tras ver la respuesta: después de fallar una categoría, ¿acierta la siguiente foto de esa categoría?
        oportunidades = corregidas = 0
        for respuestas in por_sesion.values():
            pendientes: set[int] = set()
            for f in respuestas:
                if f["categoria_real"] in pendientes:
                    oportunidades += 1
                    corregidas += f["correcto"]
                    pendientes.discard(f["categoria_real"])
                if not f["correcto"]:
                    pendientes.add(f["categoria_real"])

        return {
            "niveles_usados": list(niveles),
            "por_intento": por_intento,
            "mitades": {"n_sesiones": len(primeras), "primera": primera, "segunda": segunda,
                        "diferencia": round(segunda - primera, 3) if primeras else None},
            "correccion_tras_explicacion": {"n_oportunidades": oportunidades, "corregidas": corregidas,
                                            "tasa": _tasa(corregidas, oportunidades)},
            "rondas": {"por_participante": [], "promedio": {"ronda1": None, "ronda2": None, "n_voluntarios": 0}},
            "muestra": {"n_sesiones": len(por_sesion), "n_intentos": len(filas), "n_voluntarios": 0},
            "fuente": "fotos",
            "muestra_pequena": len(por_sesion) < MIN_SESIONES,
        }
