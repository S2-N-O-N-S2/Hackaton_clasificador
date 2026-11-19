"""
probar_modelo_vivo.py — Prueba el modelo ACTIVO con la cámara en vivo, sin Arduino.

Muestra la vista de la cámara con la zona de interés (ROI) y, al presionar ESPACIO, clasifica
3 fotogramas como lo hará el sistema real: promedio de probabilidades + reglas de decisión.

Uso (desde backend/, con el entorno virtual activo):
    python tools/probar_modelo_vivo.py
    python tools/probar_modelo_vivo.py --camara 1
    python tools/probar_modelo_vivo.py --version v2

Teclas: ESPACIO clasificar · C clasificación continua (cada ~1 s) · Q o ESC salir.
Sirve para ver qué objetos confunde el modelo ANTES de integrar el hardware (Fase 5).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.camera import abrir_captura  # noqa: E402
from app.config import Configuracion, cargar_ajustes, fuente_camara  # noqa: E402
from app.db import BaseDatos  # noqa: E402
from app.model import ExtractorMobileNet, ModeloReal, aplicar_reglas, promediar, version_activa  # noqa: E402

NOMBRES = ["ORGANICA", "INORGANICA", "PELIGROSO"]
COLORES = [(60, 160, 40), (215, 110, 30), (128, 114, 107)]  # BGR: verde, azul, gris
AMARILLO = (5, 183, 242)


def dibujar(frame, roi, resultado):
    vista = frame.copy()
    alto, ancho = vista.shape[:2]
    x, y, w, h = roi
    cv2.rectangle(vista, (int(x * ancho), int(y * alto)), (int((x + w) * ancho) - 1, int((y + h) * alto) - 1),
                  (0, 200, 0), 2)
    lineas = ["ESPACIO: clasificar   C: continuo   Q: salir"]
    color = (255, 255, 255)
    if resultado:
        probs, decision, ms = resultado
        if decision.dudoso:
            lineas.append(f"REVISION ({decision.motivo})")
            color = AMARILLO
        else:
            lineas.append(f"{NOMBRES[decision.pred_id]}  {decision.confianza:.0%}")
            color = COLORES[decision.pred_id]
        lineas += [f"Org {probs[0]:.0%}  Inorg {probs[1]:.0%}  Pel {probs[2]:.0%}", f"{ms:.0f} ms"]
    for i, texto in enumerate(lineas):
        escala = 1.0 if i == 1 else 0.6
        cv2.putText(vista, texto, (10, 30 + 32 * i), cv2.FONT_HERSHEY_SIMPLEX, escala, (0, 0, 0), 4)
        cv2.putText(vista, texto, (10, 30 + 32 * i), cv2.FONT_HERSHEY_SIMPLEX, escala,
                    color if i == 1 else (255, 255, 255), 2)
    return vista


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba el modelo con la cámara en vivo.")
    parser.add_argument("--camara", help="índice de OpenCV o URL (por defecto, la de la configuración)")
    parser.add_argument("--version", help="versión del modelo (por defecto, la activa)")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ajustes = cargar_ajustes()
    db = BaseDatos(ajustes.ruta_db)
    config = Configuracion(db)
    version = args.version or version_activa(db)
    if not version:
        print("No hay modelo activo. Entrenen primero: python -m training.train")
        return 1
    print(f"Cargando modelo {version} (TensorFlow tarda unos segundos)...")
    modelo = ModeloReal(ajustes.dir_modelos / version, ExtractorMobileNet())
    modelo.calentar()
    fuente = fuente_camara(args.camara) if args.camara is not None else config.get("indice_camara")
    camara = abrir_captura(fuente)
    if not camara.isOpened():
        print(f"No se pudo abrir la cámara {fuente}")
        return 1
    umbral_g, umbral_p = config.get("umbral_general"), config.get("umbral_peligroso")
    print(f"Listo. Umbrales: general {umbral_g}, peligroso {umbral_p}. ROI del modelo: {modelo.roi}")

    resultado, continuo, ultimo = None, False, 0.0
    ventana = f"Modelo {version} en vivo (Q para salir)"
    try:
        while True:
            ok, frame = camara.read()
            if not ok or frame is None:
                if cv2.waitKey(200) & 0xFF in (ord("q"), 27):
                    break
                continue
            tecla = cv2.waitKey(1) & 0xFF
            if tecla in (ord("q"), ord("Q"), 27):
                break
            if tecla in (ord("c"), ord("C")):
                continuo = not continuo
            if tecla == ord(" ") or (continuo and time.time() - ultimo > 1.0):
                inicio = time.time()
                frames = [frame] + [camara.read()[1] for _ in range(2)]
                frames = [f for f in frames if f is not None]
                probs = promediar(modelo.predecir(frames))
                decision = aplicar_reglas(probs, umbral_g, umbral_p)
                resultado = (probs, decision, (time.time() - inicio) * 1000)
                ultimo = time.time()
                if tecla == ord(" "):
                    texto = "REVISION" if decision.dudoso else NOMBRES[decision.pred_id]
                    print(f"{texto:10} conf {decision.confianza:.2f}  probs {[round(float(p), 2) for p in probs]}")
            cv2.imshow(ventana, dibujar(frame, modelo.roi, resultado))
    finally:
        camara.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
