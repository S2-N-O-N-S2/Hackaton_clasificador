"""
evaluate.py — Evalúa una versión del modelo (especificación §14.2).

Calcula la precisión total y por clase y la matriz de confusión (tabla e imagen PNG). Copia los casos
fallidos con su foto para revisarlos. También dice cuántas fotos irían a REVISIÓN con los umbrales
actuales y qué precisión tienen las que el sistema SÍ aceptaría.

Uso (desde backend/):
    python -m training.evaluate                      # versión activa, con su conjunto de validación
    python -m training.evaluate --version v2
    python -m training.evaluate --carpeta ruta\\fotos  # fotos propias en ruta\\fotos\\<organica|inorganica|peligroso>\\

Resultados en models/v<N>/evaluacion/ (o evaluacion_<carpeta>/):
    matriz_confusion.png · resultados.md · resultados.json · fallidos/
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import CLAVES_CATEGORIA, IDS_CATEGORIA  # noqa: E402
from app.model import ModeloReal, aplicar_reglas  # noqa: E402
from training.train import EXTENSIONES, metricas, tabla_matriz  # noqa: E402

NOMBRES = ["Orgánica", "Inorgánica", "Peligroso"]


def fotos_de_validacion(dir_version: Path, dir_dataset: Path) -> list[tuple[Path, int]]:
    split = json.loads((dir_version / "split.json").read_text(encoding="utf-8"))
    salida = []
    for relativa in split["validacion"]:
        clave = relativa.split("/", 1)[0]
        ruta = dir_dataset / relativa
        if ruta.exists():
            salida.append((ruta, CLAVES_CATEGORIA.index(clave)))
    return salida


def fotos_de_carpeta(carpeta: Path) -> list[tuple[Path, int]]:
    salida = []
    for clase, clave in zip(IDS_CATEGORIA, CLAVES_CATEGORIA):
        sub = carpeta / clave
        if sub.is_dir():
            salida += [(p, clase) for p in sorted(sub.iterdir()) if p.suffix.lower() in EXTENSIONES]
    return salida


def guardar_png(matriz: list[list[int]], titulo: str, ruta: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")  # sin ventana
    import matplotlib.pyplot as plt

    datos = np.array(matriz)
    fig, eje = plt.subplots(figsize=(5.5, 4.8), dpi=120)
    imagen = eje.imshow(datos, cmap="Blues")
    eje.set_xticks(range(3), NOMBRES)
    eje.set_yticks(range(3), NOMBRES)
    eje.set_xlabel("Predicción de la IA")
    eje.set_ylabel("Categoría real")
    eje.set_title(titulo)
    for i in range(3):
        for j in range(3):
            eje.text(j, i, str(datos[i, j]), ha="center", va="center",
                     color="white" if datos[i, j] > datos.max() / 2 else "black", fontsize=13)
    fig.colorbar(imagen, ax=eje, fraction=0.046)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def evaluar(dir_version: Path, fotos: list[tuple[Path, int]], extractor, destino: Path,
            umbral_general: float = 0.60, umbral_peligroso: float = 0.35) -> dict[str, Any]:
    if not fotos:
        raise ValueError("No hay fotos para evaluar")
    modelo = ModeloReal(dir_version, extractor)
    y_real, y_pred, filas = [], [], []
    for ruta, clase in fotos:
        frame = cv2.imread(str(ruta))
        if frame is None:
            continue
        probs = modelo.predecir([frame])[0]
        decision = aplicar_reglas(probs, umbral_general, umbral_peligroso)
        y_real.append(clase)
        y_pred.append(decision.pred_id)
        filas.append({"foto": ruta, "real": clase, "pred": decision.pred_id, "confianza": decision.confianza,
                      "dudoso": decision.dudoso, "probs": [round(float(p), 3) for p in probs]})

    resultado = metricas(y_real, y_pred)
    aceptadas = [f for f in filas if not f["dudoso"]]
    resultado["con_umbrales"] = {
        "umbral_general": umbral_general, "umbral_peligroso": umbral_peligroso,
        "a_revision": len(filas) - len(aceptadas),
        "fraccion_a_revision": round((len(filas) - len(aceptadas)) / len(filas), 4),
        "precision_aceptadas": (round(sum(f["real"] == f["pred"] for f in aceptadas) / len(aceptadas), 4)
                                if aceptadas else None),
        "peligrosos_enviados_a_otro_bote": sum(1 for f in aceptadas if f["real"] == 2 and f["pred"] != 2),
    }

    destino.mkdir(parents=True, exist_ok=True)
    fallidos = destino / "fallidos"
    if fallidos.exists():
        shutil.rmtree(fallidos)
    fallidos.mkdir()
    for f in filas:
        if f["real"] != f["pred"]:
            nombre = (f"real-{CLAVES_CATEGORIA[f['real']]}__pred-{CLAVES_CATEGORIA[f['pred']]}"
                      f"__{f['confianza']:.2f}__{f['foto'].name}")
            shutil.copy2(f["foto"], fallidos / nombre)
    guardar_png(resultado["matriz_confusion"], f"Modelo {dir_version.name} — precisión {resultado['precision']:.0%}",
                destino / "matriz_confusion.png")

    lineas = [f"# Evaluación del modelo {dir_version.name}", "",
              f"- Fotos evaluadas: **{resultado['n']}**",
              f"- Precisión total: **{resultado['precision']:.1%}** ({resultado['aciertos']}/{resultado['n']})", "",
              "| Clase | Aciertos | Total | Acierto |", "|---|---|---|---|"]
    for clave, d in resultado["por_clase"].items():
        acierto = "—" if d["acierto"] is None else f"{d['acierto']:.0%}"
        lineas.append(f"| {clave} | {d['aciertos']} | {d['n']} | {acierto} |")
    u = resultado["con_umbrales"]
    lineas += ["", "## Matriz de confusión (filas = real, columnas = predicción)", "", "```",
               tabla_matriz(resultado["matriz_confusion"]), "```", "",
               f"## Con los umbrales actuales ({u['umbral_general']:.2f} / {u['umbral_peligroso']:.2f})", "",
               f"- Irían a REVISIÓN: {u['a_revision']} ({u['fraccion_a_revision']:.0%})",
               f"- Precisión de las aceptadas: "
               + ("—" if u["precision_aceptadas"] is None else f"{u['precision_aceptadas']:.1%}"),
               f"- Peligrosos aceptados en un bote equivocado: {u['peligrosos_enviados_a_otro_bote']}", "",
               f"Casos fallidos copiados en `{fallidos}`."]
    (destino / "resultados.md").write_text("\n".join(lineas), encoding="utf-8")
    detalle = [{**f, "foto": str(f["foto"])} for f in filas]
    (destino / "resultados.json").write_text(json.dumps({"metricas": resultado, "detalle": detalle}, indent=2,
                                                        ensure_ascii=False), encoding="utf-8")
    resultado["destino"] = str(destino)
    return resultado


def main() -> int:
    from app.config import Configuracion, cargar_ajustes
    from app.db import BaseDatos
    from app.model import ExtractorMobileNet, version_activa

    parser = argparse.ArgumentParser(description="Evalúa una versión del modelo.")
    parser.add_argument("--version", help="v1, v2... (por defecto, la activa)")
    parser.add_argument("--carpeta", help="carpeta con subcarpetas organica/ inorganica/ peligroso/")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ajustes = cargar_ajustes()
    db = BaseDatos(ajustes.ruta_db)
    config = Configuracion(db)
    version = args.version or version_activa(db)
    if not version:
        print("No hay versión activa. Entrenen primero: python -m training.train")
        return 1
    dir_version = ajustes.dir_modelos / version
    if args.carpeta:
        carpeta = Path(args.carpeta)
        fotos = fotos_de_carpeta(carpeta)
        destino = dir_version / f"evaluacion_{carpeta.name}"
    else:
        fotos = fotos_de_validacion(dir_version, ajustes.dir_dataset)
        destino = dir_version / "evaluacion"
    r = evaluar(dir_version, fotos, ExtractorMobileNet(), destino,
                config.get("umbral_general"), config.get("umbral_peligroso"))
    print((destino / "resultados.md").read_text(encoding="utf-8"))
    print(f"\nImagen: {destino / 'matriz_confusion.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
