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


def fotos_de_clase(dir_dataset: Path, clave: str) -> list[Path]:
    carpeta = dir_dataset / clave
    if not carpeta.is_dir():
        return []
    return sorted(p for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONES)


def elegir_fotos(dir_dataset: Path, por_categoria: int, rng: random.Random | None = None) -> dict:
    """Hasta `por_categoria` fotos al azar de cada clase, revueltas. Si una clase tiene menos, se usan todas."""
    rng = rng or random.Random()
    items: list[dict] = []
    disponibles: dict[str, int] = {}
    for categoria_id, clave in enumerate(CLAVES_CATEGORIA):
        fotos = fotos_de_clase(dir_dataset, clave)
        disponibles[clave] = len(fotos)
        for p in rng.sample(fotos, min(por_categoria, len(fotos))):
            items.append({
                "id": f"{clave}/{p.name}",
                "foto": f"/api/juego/fotos/{clave}/{quote(p.name)}",
                "categoria_id": categoria_id,
            })
    rng.shuffle(items)
    return {"total": len(items), "por_categoria": por_categoria, "disponibles": disponibles, "items": items}


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
