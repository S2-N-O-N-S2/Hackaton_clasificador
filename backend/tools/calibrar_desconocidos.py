"""
calibrar_desconocidos.py — Crea models/<versión>/novedad.json para un modelo YA entrenado, sin reentrenarlo.

Con ese archivo el sistema detecta objetos que la IA nunca vio (la foto queda lejos del "centro" de las
3 clases) y los manda a revisión aunque la confianza sea alta. Los modelos nuevos lo crean solos (train.py).

Usa los vectores de MobileNetV2 que train.py dejó en models/cache/ (no hace falta TensorFlow ni las fotos).
Si no hay caché, calcula los vectores con las fotos de entrenamiento listadas en split.json.

Uso (PowerShell, dentro de backend/ con el venv activado):
    python tools/calibrar_desconocidos.py v1
    python tools/calibrar_desconocidos.py v1 --cache ..\\ruta\\embeddings_MobileNetV2-imagenet-avg.npz
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import CLAVES_CATEGORIA, cargar_ajustes, valores_por_defecto  # noqa: E402
from app.model import calcular_novedad, puntaje_novedad  # noqa: E402


def relativa_de_clave(clave: str) -> str:
    """'C:/.../dataset/organica/foto.jpg|tam|mtime|roi|variante' → 'organica/foto.jpg'."""
    ruta = clave.split("|", 1)[0].replace("\\", "/")
    partes = ruta.split("/")
    return "/".join(partes[-2:])


def vectores_de_cache(ruta_cache: Path, relativas: set[str]) -> dict[str, np.ndarray]:
    datos = np.load(ruta_cache, allow_pickle=True)
    salida = {}
    for clave, vector in zip(datos["claves"], datos["vectores"]):
        clave = str(clave)
        if not clave.endswith("|0"):  # solo la foto original, no las aumentadas
            continue
        relativa = relativa_de_clave(clave)
        if relativa in relativas:
            salida[relativa] = vector
    return salida


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("version", help="versión del modelo, p. ej. v1")
    parser.add_argument("--cache", type=Path, help="archivo embeddings_*.npz (por defecto models/cache/)")
    args = parser.parse_args()

    ajustes = cargar_ajustes()
    dir_version = ajustes.dir_modelos / args.version
    split = json.loads((dir_version / "split.json").read_text(encoding="utf-8"))
    entrenamiento, validacion = split["entrenamiento"], split["validacion"]
    ruta_cache = args.cache or next((ajustes.dir_modelos / "cache").glob("embeddings_*.npz"), None)

    vectores: dict[str, np.ndarray] = {}
    if ruta_cache and Path(ruta_cache).exists():
        vectores = vectores_de_cache(Path(ruta_cache), set(entrenamiento) | set(validacion))
        print(f"Caché: {ruta_cache}: {len(vectores)} vectores")
    faltan = [r for r in entrenamiento if r not in vectores]
    if faltan:
        print(f"Faltan {len(faltan)} vectores en la caché: se calculan con las fotos de {ajustes.dir_dataset}")
        import cv2

        from app.model import ExtractorMobileNet, preparar_imagen
        meta = json.loads((dir_version / "labels.json").read_text(encoding="utf-8"))
        extractor = ExtractorMobileNet()
        for relativa in faltan:
            imagen = cv2.imread(str(ajustes.dir_dataset / relativa))
            if imagen is None:
                print(f"  No se pudo leer {relativa}: se omite")
                continue
            vectores[relativa] = extractor.embeddings(preparar_imagen(imagen, meta["roi"])[None])[0]

    usadas = [r for r in entrenamiento if r in vectores]
    x = np.stack([vectores[r] for r in usadas])
    y = [CLAVES_CATEGORIA.index(r.split("/")[0]) for r in usadas]
    novedad = calcular_novedad(x, y)
    (dir_version / "novedad.json").write_text(json.dumps(novedad), encoding="utf-8")

    val = [r for r in validacion if r in vectores]
    limite = valores_por_defecto()["umbral_desconocido"]
    puntajes = np.array([puntaje_novedad(vectores[r][None], novedad) for r in val])
    fuera = int((puntajes > limite).sum())
    print(f"Guardado {dir_version / 'novedad.json'} (fotos de entrenamiento por clase: {novedad['n']})")
    print(f"Límites por clase (distancia coseno): {novedad['limites']}")
    if val:
        p50, p90, p99 = np.percentile(puntajes, [50, 90, 99])
        print(f"Puntaje de objetos CONOCIDOS (validación): mediana {p50:.2f}, p90 {p90:.2f}, p99 {p99:.2f}")
        print(f"Con umbral_desconocido = {limite}: {fuera} de {len(val)} se marcarían como desconocidos "
              f"({fuera / len(val):.1%}). Elige un umbral un poco arriba del p99 de tus fotos propias.")
    print("Reinicia el backend para que lo use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
