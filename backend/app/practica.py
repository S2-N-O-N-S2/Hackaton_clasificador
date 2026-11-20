"""
practica.py — "Practica con fotos" del modo ¿Le ganas a la IA?

El usuario clasifica fotos del dataset de entrenamiento (sin usar la máquina). Aquí solo se elige qué fotos
mostrar y se valida la ruta de cada una; la calificación la hace el panel comparando con la carpeta de la foto.

Solo se usan las carpetas de clase (organica/, inorganica/, peligroso/). `_por_verificar/` se excluye porque
sus etiquetas todavía no las aprobó el operador.
"""

from __future__ import annotations

import random
from pathlib import Path
from urllib.parse import quote

from .config import CLAVES_CATEGORIA

EXTENSIONES = {".jpg", ".jpeg", ".png"}
POR_CATEGORIA_MAX = 50
TOTAL_MIN, TOTAL_MAX = 3, 60  # el panel ofrece 5, 10, 15, 20, 25 y 30 preguntas


def fotos_de_clase(dir_dataset: Path, clave: str) -> list[Path]:
    carpeta = dir_dataset / clave
    if not carpeta.is_dir():
        return []
    return sorted(p for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONES)


def repartir(total: int, rng: random.Random) -> list[int]:
    """Reparte `total` preguntas entre las 3 categorías lo más parejo posible.
    Ej.: 15 → [5, 5, 5]; 10 → [4, 3, 3] con la pregunta extra en una categoría al azar."""
    cuotas = [total // 3] * 3
    for i in rng.sample(range(3), total % 3):
        cuotas[i] += 1
    return cuotas


def elegir_fotos(dir_dataset: Path, por_categoria: int | None = None, rng: random.Random | None = None,
                 total: int | None = None) -> dict:
    """Fotos al azar de cada clase, revueltas: `por_categoria` de cada una, o `total` repartido entre las 3.
    Si una clase tiene menos fotos que su cuota, se usan todas."""
    rng = rng or random.Random()
    cuotas = repartir(total, rng) if total is not None else [por_categoria or 0] * 3
    items: list[dict] = []
    disponibles: dict[str, int] = {}
    for categoria_id, clave in enumerate(CLAVES_CATEGORIA):
        fotos = fotos_de_clase(dir_dataset, clave)
        disponibles[clave] = len(fotos)
        for p in rng.sample(fotos, min(cuotas[categoria_id], len(fotos))):
            items.append({
                "id": f"{clave}/{p.name}",
                "foto": f"/api/juego/fotos/{clave}/{quote(p.name)}",
                "categoria_id": categoria_id,
            })
    rng.shuffle(items)
    return {"total": len(items), "por_categoria": por_categoria, "cuotas": cuotas, "disponibles": disponibles,
            "items": items}


def ruta_foto(dir_dataset: Path, clave: str, archivo: str) -> Path | None:
    """Ruta segura de una foto del dataset, o None si no es válida (evita salir de la carpeta con '..')."""
    if clave not in CLAVES_CATEGORIA:
        return None
    if Path(archivo).name != archivo or Path(archivo).suffix.lower() not in EXTENSIONES:
        return None
    carpeta = (dir_dataset / clave).resolve()
    ruta = (carpeta / archivo).resolve()
    if ruta.parent != carpeta or not ruta.is_file():
        return None
    return ruta
