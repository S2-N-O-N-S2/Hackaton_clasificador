"""
normalizar_dataset.py — Copia fotos originales a backend/dataset/ con el formato que pide el entrenamiento.

Requisitos (docs/prompts_persona_b.md, "Prompt 3", y especificación §14.1):
  - Carpetas organica/, inorganica/ y peligroso/.
  - Nombre <objeto_id>__<nnn>.jpg: el objeto_id identifica al OBJETO FÍSICO, para separar
    entrenamiento y validación por objeto (si no, la precisión sale inflada).
  - Reducir a un máximo de 320 px por lado MANTENIENDO LA PROPORCIÓN (cv2.INTER_AREA), en JPG calidad 92.
    NO se recorta a 224×224 ni a cuadro, y NO se cambian colores ni brillo: el sistema ya aplica la zona
    de interés (roi) y el ajuste a 224×224, igual al entrenar que en vivo.
  - Cada foto se agrega a dataset/metadatos.csv (archivo,clase_id,clase,objeto_id,fecha_hora,camara).
  - Nunca modifica los originales ni sobrescribe fotos existentes.

Estructuras de origen que entiende:
  --estructura clase-objeto   (fotos del equipo)
        <origen>/organica/platano1/*.jpg   <origen>/peligroso/pila1/*.jpg ...
        Una carpeta por clase y, dentro, una carpeta por objeto físico.
  --estructura gd             ("The Garbage Dataset", Kaggle sumn2u/garbage-classification-v2)
        <origen>/battery/*.jpg  <origen>/biological/*.jpg ...  (usar la carpeta "original", no "standardized_*",
        que vienen recortadas a cuadro). Cada foto es un objeto distinto de internet, así que su objeto_id es
        gd_<categoria>_<numero>. La categoría "trash" se descarta (mezcla de todo).

Uso (desde backend/, con el entorno virtual activo):
    python tools\\normalizar_dataset.py --origen D:\\fotos_equipo --estructura clase-objeto --simular
    python tools\\normalizar_dataset.py --origen C:\\Users\\yo\\Downloads\\archive\\original --estructura gd --max-por-clase 400

Después:  python tools\\revisar_dataset.py --max-lado 320   → debe decir "LISTO PARA ENTRENAR".
Generado con Claude Code (Anthropic) para la Persona B; revisado por el equipo (ver docs/recursos_externos.md).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")   # la consola de Windows no imprime "×" ni acentos en cp1252

# ---------------------------------------------------------------------------
#  Configuración
# ---------------------------------------------------------------------------
CLASES = {"organica": 0, "inorganica": 1, "peligroso": 2}
EXTENSIONES = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
MAX_LADO = 320
CALIDAD_JPG = 92
COLUMNAS = ["archivo", "clase_id", "clase", "objeto_id", "fecha_hora", "camara"]
DIR_DATASET = Path(__file__).resolve().parent.parent / "dataset"

# The Garbage Dataset (GD) → nuestras 3 clases (especificación §4). None = se descarta.
MAPA_GD = {
    "biological": "organica",     # restos de comida y vegetales
    "battery": "peligroso",       # pilas y baterías
    "cardboard": "inorganica",
    "paper": "inorganica",
    "plastic": "inorganica",
    "metal": "inorganica",
    "glass": "inorganica",
    "clothes": "inorganica",
    "shoes": "inorganica",
    "trash": None,                # basura mezclada: confundiría a la IA
}
CAMARA_GD = "externo:garbage_dataset_gd"


@dataclass
class Foto:
    origen: Path       # archivo original (no se modifica)
    clase: str         # organica | inorganica | peligroso
    objeto_id: str     # objeto físico
    categoria: str     # carpeta de origen (para el resumen)


# ---------------------------------------------------------------------------
#  Utilidades
# ---------------------------------------------------------------------------
def limpiar_id(texto: str) -> str:
    """'Plátano 1' → 'platano1': minúsculas, sin acentos, solo letras, números, '-' y '_' (nunca '__')."""
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    limpio = re.sub(r"[^a-z0-9_-]", "", sin_acentos.lower().replace(" ", ""))
    return re.sub(r"_{2,}", "_", limpio).strip("_")


def leer_imagen(ruta: Path) -> np.ndarray | None:
    """cv2.imread falla con rutas con acentos en Windows: se lee como bytes y se decodifica."""
    try:
        datos = np.fromfile(str(ruta), dtype=np.uint8)
    except OSError:
        return None
    if datos.size == 0:
        return None
    return cv2.imdecode(datos, cv2.IMREAD_COLOR)   # siempre BGR de 3 canales (quita el canal alfa)


def reducir(imagen: np.ndarray, max_lado: int = MAX_LADO) -> np.ndarray:
    """Reduce para que el lado mayor mida max_lado, manteniendo la proporción. Nunca agranda ni recorta."""
    alto, ancho = imagen.shape[:2]
    mayor = max(alto, ancho)
    if mayor <= max_lado:
        return imagen
    escala = max_lado / mayor
    nuevo = (max(1, round(ancho * escala)), max(1, round(alto * escala)))
    return cv2.resize(imagen, nuevo, interpolation=cv2.INTER_AREA)


def guardar_jpg(imagen: np.ndarray, ruta: Path) -> None:
    ok, datos = cv2.imencode(".jpg", imagen, [cv2.IMWRITE_JPEG_QUALITY, CALIDAD_JPG])
    if not ok:
        raise ValueError("No se pudo codificar la imagen a JPG")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    datos.tofile(str(ruta))


def huella(ruta: Path) -> str:
    return hashlib.md5(ruta.read_bytes()).hexdigest()


def numero_natural(ruta: Path):
    """battery_2 antes que battery_10."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", ruta.stem)]


def imagenes_de(carpeta: Path) -> list[Path]:
    return sorted((p for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONES), key=numero_natural)


# ---------------------------------------------------------------------------
#  Lectura del origen
# ---------------------------------------------------------------------------
def listar_clase_objeto(origen: Path) -> list[Foto]:
    fotos = []
    for clase in CLASES:
        carpeta_clase = origen / clase
        if not carpeta_clase.is_dir():
            print(f"  (no hay carpeta {carpeta_clase}: se omite)")
            continue
        sueltas = imagenes_de(carpeta_clase)
        if sueltas:
            raise SystemExit(
                f"ERROR: {carpeta_clase} tiene {len(sueltas)} fotos sueltas. Pon cada foto dentro de una carpeta "
                f"con el nombre del objeto físico (por ejemplo {clase}/platano1/), para saber qué foto es de qué objeto.")
        for carpeta_objeto in sorted(p for p in carpeta_clase.iterdir() if p.is_dir()):
            objeto = limpiar_id(carpeta_objeto.name)
            if not objeto:
                raise SystemExit(f"ERROR: no se pudo sacar un ID de objeto de '{carpeta_objeto.name}'")
            fotos += [Foto(p, clase, objeto, clase) for p in imagenes_de(carpeta_objeto)]
    return fotos


def listar_gd(origen: Path, max_por_clase: int | None, semilla: int) -> list[Foto]:
    """Toma hasta max_por_clase fotos por clase, repartidas por igual entre sus categorías de origen."""
    por_clase: dict[str, dict[str, list[Path]]] = defaultdict(dict)
    for categoria, clase in MAPA_GD.items():
        carpeta = origen / categoria
        if clase is None:
            continue
        if not carpeta.is_dir():
            print(f"  (no hay carpeta {carpeta}: se omite)")
            continue
        por_clase[clase][categoria] = imagenes_de(carpeta)

    azar = random.Random(semilla)   # semilla fija: la misma selección cada vez (reproducible)
    fotos = []
    for clase, categorias in por_clase.items():
        for lista in categorias.values():
            azar.shuffle(lista)
        elegidas: dict[str, list[Path]] = {c: [] for c in categorias}
        limite = max_por_clase or sum(len(v) for v in categorias.values())
        total = 0
        # reparto por turnos: una de cada categoría hasta llenar el tope
        while total < limite and any(len(elegidas[c]) < len(categorias[c]) for c in categorias):
            for categoria, lista in categorias.items():
                if total >= limite:
                    break
                if len(elegidas[categoria]) < len(lista):
                    elegidas[categoria].append(lista[len(elegidas[categoria])])
                    total += 1
        for categoria, lista in elegidas.items():
            for ruta in sorted(lista, key=numero_natural):
                fotos.append(Foto(ruta, clase, limpiar_id(f"gd_{ruta.stem}"), categoria))
    return fotos


# ---------------------------------------------------------------------------
#  Copia al dataset
# ---------------------------------------------------------------------------
def siguiente_numero(carpeta: Path, objeto: str, usados: dict[tuple[str, str], int]) -> int:
    clave = (str(carpeta), objeto)
    if clave not in usados:
        existentes = [int(m.group(1)) for p in carpeta.glob(f"{objeto}__*.jpg")
                      if (m := re.fullmatch(rf"{re.escape(objeto)}__(\d+)", p.stem))] if carpeta.is_dir() else []
        usados[clave] = max(existentes, default=0)
    usados[clave] += 1
    return usados[clave]


def objetos_en_otra_clase(destino: Path) -> dict[str, str]:
    """objeto_id → clase, de las fotos que ya están en el dataset (para no repetir un ID en dos clases)."""
    dueños = {}
    for clase in CLASES:
        carpeta = destino / clase
        if carpeta.is_dir():
            for p in carpeta.glob("*.jpg"):
                dueños.setdefault(p.stem.split("__", 1)[0], clase)
    return dueños


def normalizar(fotos: list[Foto], destino: Path, camara: str, simular: bool) -> dict:
    ahora = datetime.now().replace(microsecond=0).isoformat()
    dueños = objetos_en_otra_clase(destino)
    conflictos = sorted({f.objeto_id for f in fotos if dueños.get(f.objeto_id, f.clase) != f.clase})
    if conflictos:
        raise SystemExit(f"ERROR: estos IDs ya existen en OTRA clase del dataset: {', '.join(conflictos[:10])}. "
                         f"Un mismo objeto no puede estar en dos categorías.")

    usados: dict[tuple[str, str], int] = {}
    vistos: dict[str, Path] = {}
    filas, resumen = [], {"copiadas": Counter(), "objetos": defaultdict(set), "categorias": Counter(),
                          "duplicadas": 0, "ilegibles": [], "reducidas": 0}
    for foto in fotos:
        h = huella(foto.origen)
        if h in vistos:                       # misma foto dos veces en el origen
            resumen["duplicadas"] += 1
            continue
        vistos[h] = foto.origen
        imagen = leer_imagen(foto.origen)
        if imagen is None:
            resumen["ilegibles"].append(str(foto.origen))
            continue
        reducida = reducir(imagen)
        if reducida.shape != imagen.shape:
            resumen["reducidas"] += 1
        carpeta = destino / foto.clase
        numero = siguiente_numero(carpeta, foto.objeto_id, usados)
        nombre = f"{foto.objeto_id}__{numero:03d}.jpg"
        if not simular:
            guardar_jpg(reducida, carpeta / nombre)
        filas.append({"archivo": f"{foto.clase}/{nombre}", "clase_id": CLASES[foto.clase], "clase": foto.clase,
                      "objeto_id": foto.objeto_id, "fecha_hora": ahora, "camara": camara})
        resumen["copiadas"][foto.clase] += 1
        resumen["objetos"][foto.clase].add(foto.objeto_id)
        resumen["categorias"][(foto.clase, foto.categoria)] += 1

    if filas and not simular:
        ruta_csv = destino / "metadatos.csv"
        nuevo = not ruta_csv.exists() or ruta_csv.stat().st_size == 0
        if not nuevo:
            with ruta_csv.open(encoding="utf-8", newline="") as f:
                encabezado = next(csv.reader(f), [])
            if encabezado != COLUMNAS:
                raise SystemExit(f"ERROR: {ruta_csv} tiene otras columnas ({encabezado}); no se agregó nada al CSV.")
        with ruta_csv.open("a", encoding="utf-8", newline="") as f:
            escritor = csv.DictWriter(f, fieldnames=COLUMNAS)
            if nuevo:
                escritor.writeheader()
            escritor.writerows(filas)
    return resumen


def imprimir_resumen(resumen: dict, simular: bool) -> None:
    print("\n=== SIMULACIÓN: no se copió nada ===" if simular else "\n=== Listo ===")
    print(f"{'Clase':<12}{'Fotos':>7}{'Objetos':>9}   Categorías de origen")
    for clase in CLASES:
        cats = ", ".join(f"{c} {n}" for (k, c), n in sorted(resumen["categorias"].items()) if k == clase)
        print(f"{clase:<12}{resumen['copiadas'][clase]:>7}{len(resumen['objetos'][clase]):>9}   {cats}")
    print(f"Reducidas a {MAX_LADO} px: {resumen['reducidas']} · duplicadas omitidas: {resumen['duplicadas']} · "
          f"ilegibles: {len(resumen['ilegibles'])}")
    for ruta in resumen["ilegibles"][:10]:
        print(f"  no se pudo abrir: {ruta}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Normaliza fotos originales y las copia a backend/dataset/.")
    parser.add_argument("--origen", required=True, type=Path, help="carpeta con las fotos originales")
    parser.add_argument("--estructura", choices=["clase-objeto", "gd"], default="clase-objeto",
                        help="clase-objeto: <clase>/<objeto>/*.jpg · gd: The Garbage Dataset (carpeta 'original')")
    parser.add_argument("--destino", type=Path, default=DIR_DATASET, help="por defecto backend/dataset")
    parser.add_argument("--max-por-clase", type=int, default=None, help="tope de fotos por clase (para no desbalancear)")
    parser.add_argument("--camara", default="droidcam", help="se anota en metadatos.csv (en gd siempre es externo)")
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--simular", action="store_true", help="solo muestra lo que haría, sin copiar nada")
    args = parser.parse_args()

    if not args.origen.is_dir():
        print(f"ERROR: no existe la carpeta {args.origen}")
        return 1
    if args.estructura == "gd" and args.origen.name.startswith("standardized"):
        print("ERROR: usa la carpeta 'original' del GD; las 'standardized_*' vienen recortadas a cuadro.")
        return 1

    print(f"Origen: {args.origen}\nDestino: {args.destino}")
    if args.estructura == "gd":
        fotos = listar_gd(args.origen, args.max_por_clase, args.semilla)
        camara = CAMARA_GD
    else:
        fotos = listar_clase_objeto(args.origen)
        if args.max_por_clase:
            azar = random.Random(args.semilla)
            por_clase = defaultdict(list)
            for f in fotos:
                por_clase[f.clase].append(f)
            fotos = [f for lista in por_clase.values() for f in azar.sample(lista, min(len(lista), args.max_por_clase))]
        camara = args.camara
    if not fotos:
        print("No se encontraron fotos con la estructura indicada.")
        return 1

    resumen = normalizar(fotos, args.destino, camara, args.simular)
    imprimir_resumen(resumen, args.simular)
    if not args.simular:
        print("\nSiguiente paso: python tools\\revisar_dataset.py --max-lado 320")
    return 0


if __name__ == "__main__":
    sys.exit(main())
