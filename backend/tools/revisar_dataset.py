"""
revisar_dataset.py — Revisa que el dataset tenga el formato que necesita el entrenamiento, ANTES de entrenar.

Comprueba:
  - carpetas organica/, inorganica/ y peligroso/ con imágenes .jpg/.jpeg/.png;
  - que cada nombre tenga el ID del objeto antes de "__" (platano1__001.jpg);
  - mínimo 2 objetos distintos por clase (ideal 5–6) y 40–60 fotos por clase;
  - tamaño máximo (320 px por lado, si así se normalizó) y fotos que parezcan RECORTADAS a 224×224;
  - imágenes que no se pueden abrir, de un solo color, o duplicadas (mismo contenido);
  - el mismo ID de objeto usado en dos clases distintas (posible error de etiqueta).

Uso (desde backend/, con el entorno virtual activo):
    python tools\\revisar_dataset.py                       # revisa backend\\dataset
    python tools\\revisar_dataset.py --carpeta D:\\dataset_nuevo
    python tools\\revisar_dataset.py --max-lado 320      # además revisa que ningún lado pase de 320 px

Termina con "LISTO PARA ENTRENAR" o con la lista de problemas a corregir.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.camera import imagen_es_plana  # noqa: E402
from app.config import CLAVES_CATEGORIA, cargar_ajustes  # noqa: E402
from training.train import EXTENSIONES, MIN_OBJETOS_POR_CLASE, objeto_desde_nombre  # noqa: E402

FOTOS_IDEALES = (40, 60)
OBJETOS_IDEALES = 5


def revisar(carpeta: Path, max_lado: int | None = None) -> tuple[list[str], list[str], dict]:
    """Devuelve (errores, avisos, resumen). Los errores impiden entrenar o falsean la validación."""
    errores: list[str] = []
    avisos: list[str] = []
    resumen: dict[str, dict] = {}
    hashes: dict[str, str] = {}
    clases_por_objeto: dict[str, set[str]] = defaultdict(set)

    if not carpeta.is_dir():
        return [f"No existe la carpeta {carpeta}"], [], {}
    extras = [p.name for p in carpeta.iterdir() if p.is_dir() and p.name not in CLAVES_CATEGORIA
              and not p.name.startswith("_")]
    if extras:
        avisos.append(f"Carpetas que el entrenamiento IGNORA: {', '.join(extras)} "
                      f"(solo se usan {', '.join(CLAVES_CATEGORIA)})")

    for clave in CLAVES_CATEGORIA:
        sub = carpeta / clave
        if not sub.is_dir():
            errores.append(f"Falta la carpeta {clave}/")
            resumen[clave] = {"fotos": 0, "objetos": 0}
            continue
        archivos = sorted(p for p in sub.iterdir() if p.is_file() and not p.name.startswith("."))
        otros = [p.name for p in archivos if p.suffix.lower() not in EXTENSIONES]
        if otros:
            avisos.append(f"{clave}/: {len(otros)} archivos que no son imagen se ignoran (ej. {otros[0]})")
        imagenes = [p for p in archivos if p.suffix.lower() in EXTENSIONES]
        sin_id = [p.name for p in imagenes if "__" not in p.stem]
        if sin_id:
            errores.append(f"{clave}/: {len(sin_id)} fotos SIN ID de objeto (ej. {sin_id[0]}). Renómbrenlas como "
                           f"<objeto>__<n>.jpg; si no, cada foto cuenta como un objeto y la validación sale inflada")
        objetos = Counter(objeto_desde_nombre(p.name) for p in imagenes)
        for objeto in objetos:
            clases_por_objeto[objeto].add(clave)
        cuadradas_224, grandes, ilegibles, planas = [], [], [], []
        for p in imagenes:
            imagen = cv2.imread(str(p))
            if imagen is None:
                ilegibles.append(p.name)
                continue
            alto, ancho = imagen.shape[:2]
            if (ancho, alto) == (224, 224):
                cuadradas_224.append(p.name)
            if max_lado and max(ancho, alto) > max_lado:
                grandes.append(f"{p.name} ({ancho}x{alto})")
            if imagen_es_plana(imagen):
                planas.append(p.name)
            huella = hashlib.md5(imagen.tobytes()).hexdigest()
            if huella in hashes:
                avisos.append(f"Foto duplicada: {clave}/{p.name} = {hashes[huella]}")
            else:
                hashes[huella] = f"{clave}/{p.name}"
        if ilegibles:
            errores.append(f"{clave}/: {len(ilegibles)} imágenes que no se pueden abrir (ej. {ilegibles[0]})")
        if planas:
            errores.append(f"{clave}/: {len(planas)} imágenes de un solo color (cámara sin señal) (ej. {planas[0]})")
        if cuadradas_224:
            avisos.append(f"{clave}/: {len(cuadradas_224)} fotos de 224×224 exactos: ¿se RECORTARON? El sistema en vivo "
                          f"usa la imagen completa reducida a 224×224; recortar al entrenar baja la precisión real")
        if grandes:
            avisos.append(f"{clave}/: {len(grandes)} fotos de más de {max_lado} px (ej. {grandes[0]}). "
                          f"No impide entrenar, pero no siguen la normalización acordada")
        n_fotos, n_objetos = len(imagenes), len(objetos)
        resumen[clave] = {"fotos": n_fotos, "objetos": n_objetos, "fotos_por_objeto": dict(objetos)}
        if n_objetos < MIN_OBJETOS_POR_CLASE:
            errores.append(f"{clave}/: solo {n_objetos} objeto(s) distinto(s); se necesitan al menos "
                           f"{MIN_OBJETOS_POR_CLASE} para separar entrenamiento y validación")
        elif n_objetos < OBJETOS_IDEALES:
            avisos.append(f"{clave}/: {n_objetos} objetos; lo ideal son {OBJETOS_IDEALES}–6 para una validación confiable")
        if n_fotos < FOTOS_IDEALES[0]:
            avisos.append(f"{clave}/: {n_fotos} fotos; la meta es {FOTOS_IDEALES[0]}–{FOTOS_IDEALES[1]} por clase")

    for objeto, clases in clases_por_objeto.items():
        if len(clases) > 1:
            avisos.append(f"El ID '{objeto}' aparece en varias clases ({', '.join(sorted(clases))}): "
                          f"¿foto mal clasificada o mismo nombre para objetos distintos?")
    return errores, avisos, resumen


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Revisa el formato del dataset antes de entrenar.")
    parser.add_argument("--carpeta", help="carpeta del dataset (por defecto backend\\dataset)")
    parser.add_argument("--max-lado", type=int, default=0,
                        help="lado máximo esperado en px, p. ej. 320 si se normalizó (0 = no revisar)")
    args = parser.parse_args()

    carpeta = Path(args.carpeta) if args.carpeta else cargar_ajustes().dir_dataset
    print(f"Revisando {carpeta}\n")
    errores, avisos, resumen = revisar(carpeta, args.max_lado or None)
    for clave, datos in resumen.items():
        detalle = ", ".join(f"{o}: {n}" for o, n in datos.get("fotos_por_objeto", {}).items())
        print(f"  {clave:11} {datos['fotos']:4} fotos, {datos['objetos']:2} objetos  {detalle}")
    if avisos:
        print("\nAVISOS (se puede entrenar, pero conviene revisarlos):")
        for a in avisos:
            print(f"  - {a}")
    if errores:
        print("\nERRORES (corríjanlos antes de entrenar):")
        for e in errores:
            print(f"  - {e}")
        return 1
    print("\nLISTO PARA ENTRENAR:  python -m training.train")
    return 0


if __name__ == "__main__":
    sys.exit(main())
