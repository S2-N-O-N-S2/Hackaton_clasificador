"""
capturar_dataset.py — Toma fotos para el dataset con la MISMA cámara, bandeja e iluminación de la demo (§14.1).

Uso (desde backend/, con el entorno virtual activo):
    python -m training.capturar_dataset                 # cámara de la configuración
    python -m training.capturar_dataset --camara 1
    python -m training.capturar_dataset --camara http://192.168.1.50:4747/video   # celular por Wi-Fi

Flujo:
  1. En la consola escribe el ID del objeto físico (por ejemplo: platano1, lata2, pila1).
  2. En la ventana de video, coloca el objeto y presiona 1 / 2 / 3 para guardar una foto
     (1 Orgánica, 2 Inorgánica, 3 Peligroso). Cambia posición, orientación y lado entre fotos.
  3. Presiona N para pasar a otro objeto (pide un ID nuevo en la consola) y Q o ESC para salir.

Las fotos van a dataset/<clase>/<objeto>__AAAAMMDD_HHMMSS_<n>.jpg y cada una se anota en
dataset/metadatos.csv. El objeto_id permite separar entrenamiento/validación POR OBJETO.
El rectángulo verde es la zona de interés (ROI) que usará la IA; se ajusta en la configuración ("roi").
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

import cv2

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.camera import abrir_captura  # noqa: E402
from app.config import CLAVES_CATEGORIA, fuente_camara  # noqa: E402
from training.train import ARCHIVO_METADATOS, listar_dataset, resumen_dataset  # noqa: E402

TECLAS = {ord("1"): 0, ord("2"): 1, ord("3"): 2}
NOMBRES = ["ORGANICA", "INORGANICA", "PELIGROSO"]
COLUMNAS = ["archivo", "clase_id", "clase", "objeto_id", "fecha_hora", "camara"]


def limpiar_id(texto: str) -> str:
    """'Plátano 1' → 'platano-1' (solo minúsculas, números, '-' y '_')."""
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower().strip()
    texto = re.sub(r"\s+", "-", texto)
    return re.sub(r"[^a-z0-9_-]", "", texto)[:40]


def pedir_objeto() -> str | None:
    while True:
        texto = input("\nID del objeto físico (ej. platano1; vacío para salir): ")
        if not texto.strip():
            return None
        objeto = limpiar_id(texto)
        if objeto:
            return objeto
        print("ID inválido: usen letras, números, '-' o '_'")


def anotar(dir_dataset: Path, fila: dict) -> None:
    ruta = dir_dataset / ARCHIVO_METADATOS
    nuevo = not ruta.exists()
    with ruta.open("a", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
        if nuevo:
            escritor.writeheader()
        escritor.writerow(fila)


def dibujar(frame, roi, objeto: str, conteo: dict, mensaje: str):
    vista = frame.copy()
    alto, ancho = vista.shape[:2]
    x, y, w, h = roi
    cv2.rectangle(vista, (int(x * ancho), int(y * alto)), (int((x + w) * ancho) - 1, int((y + h) * alto) - 1),
                  (0, 200, 0), 2)
    textos = [f"Objeto: {objeto}", "1:Organica 2:Inorganica 3:Peligroso  N:otro objeto  Q:salir",
              "  ".join(f"{c[:5]}: {conteo[c]['fotos']} fotos/{conteo[c]['objetos']} obj" for c in CLAVES_CATEGORIA),
              mensaje]
    for i, texto in enumerate(textos):
        cv2.putText(vista, texto, (10, 25 + 24 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3)
        cv2.putText(vista, texto, (10, 25 + 24 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    return vista


def main() -> int:
    from app.config import Configuracion, cargar_ajustes
    from app.db import BaseDatos

    parser = argparse.ArgumentParser(description="Captura fotos etiquetadas para el dataset.")
    parser.add_argument("--camara", help="índice de OpenCV o URL (por defecto, la de la configuración)")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ajustes = cargar_ajustes()
    config = Configuracion(BaseDatos(ajustes.ruta_db))
    fuente = fuente_camara(args.camara) if args.camara is not None else config.get("indice_camara")
    roi = config.get("roi")
    camara = abrir_captura(fuente)
    if not camara.isOpened():
        print(f"No se pudo abrir la cámara {fuente}. Prueben: python tools\\verificar_hardware.py")
        return 1

    print(__doc__.split("Flujo:")[1].split("Las fotos")[0])
    objeto = pedir_objeto()
    if objeto is None:
        return 0
    mensaje, n = "Listo para capturar", 0
    conteo = resumen_dataset(listar_dataset(ajustes.dir_dataset))
    ventana = "Captura de dataset (Q para salir)"
    try:
        while True:
            ok, frame = camara.read()
            if not ok or frame is None:
                mensaje = "La camara no entrega imagen"
                if cv2.waitKey(200) & 0xFF in (ord("q"), 27):
                    break
                continue
            cv2.imshow(ventana, dibujar(frame, roi, objeto, conteo, mensaje))
            tecla = cv2.waitKey(1) & 0xFF
            if tecla in (ord("q"), ord("Q"), 27):
                break
            if tecla in (ord("n"), ord("N")):
                nuevo = pedir_objeto()
                if nuevo is None:
                    break
                objeto, mensaje = nuevo, f"Nuevo objeto: {nuevo}"
            elif tecla in TECLAS:
                clase = TECLAS[tecla]
                clave = CLAVES_CATEGORIA[clase]
                n += 1
                momento = datetime.now()
                nombre = f"{objeto}__{momento:%Y%m%d_%H%M%S}_{n}.jpg"
                destino = ajustes.dir_dataset / clave / nombre
                destino.parent.mkdir(parents=True, exist_ok=True)
                if cv2.imwrite(str(destino), frame):  # se guarda la foto COMPLETA; el recorte se hace al entrenar
                    anotar(ajustes.dir_dataset, {"archivo": f"{clave}/{nombre}", "clase_id": clase, "clase": clave,
                                                 "objeto_id": objeto, "fecha_hora": momento.replace(microsecond=0)
                                                 .isoformat(), "camara": str(fuente)})
                    conteo = resumen_dataset(listar_dataset(ajustes.dir_dataset))
                    mensaje = f"Guardada en {NOMBRES[clase]}: {nombre}"
                    print(mensaje)
                else:
                    mensaje = "ERROR al guardar la foto"
    finally:
        camara.release()
        cv2.destroyAllWindows()
    print("\nResumen del dataset:")
    for clave, d in resumen_dataset(listar_dataset(ajustes.dir_dataset)).items():
        print(f"  {clave:11}: {d['fotos']:3} fotos de {d['objetos']} objetos (meta: 40–60 fotos por clase)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
