"""
probar_camara.py — Toma fotos con la cámara real usando EL MISMO método del sistema y muestra las métricas
de calidad, para ajustar los umbrales de CAMARA en app/config.py (los marcados [COMPLETAR]).

Uso (PowerShell, dentro de backend/ con el venv activado; con la luz de la bandeja encendida):
    python tools/probar_camara.py              # cámara de la configuración (INDICE_CAMARA o 0)
    python tools/probar_camara.py 1            # índice 1
    python tools/probar_camara.py http://192.168.1.50:4747/video   # DroidCam por Wi-Fi

Prueba así:
  1. Bandeja vacía, 2. un residuo quieto, 3. moviendo el residuo, 4. tapando la cámara, 5. luz apagada.
Para cada caso anota brillo y nitidez. Los umbrales deben dejar pasar 1–2 y rechazar 3–5.
Las fotos quedan en captures/prueba_camara_*.jpg para revisarlas.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2  # noqa: E402

from app.camera import CamaraReal, FotoNoValida, evaluar_foto, metricas_foto  # noqa: E402
from app.config import CAMARA, cargar_ajustes, fuente_camara, valores_por_defecto  # noqa: E402


async def una_vez(camara: CamaraReal, ajustes, numero: int) -> None:
    try:
        frames = await camara.capturar(3)
        estado = "OK"
    except FotoNoValida as error:
        frames = [error.frame] if error.frame is not None else []
        estado = f"RECHAZADA: {error}"
    for i, frame in enumerate(frames):
        m = metricas_foto(frame)
        nombre = f"prueba_camara_{numero:02d}_{i}.jpg"
        cv2.imwrite(str(ajustes.dir_capturas / nombre), frame)
        print(f"  {nombre}: brillo {m['brillo']:.0f} (min {CAMARA['brillo_min']:.0f}, max {CAMARA['brillo_max']:.0f}) | "
              f"nitidez {m['nitidez']:.0f} (min {CAMARA['nitidez_min']:.0f}) | variacion {m['variacion']:.1f} "
              f"| {evaluar_foto(frame, CAMARA) or 'bien'}")
    print(f"  Resultado: {estado}")


async def principal() -> int:
    ajustes = cargar_ajustes()
    fuente = fuente_camara(sys.argv[1]) if len(sys.argv) > 1 else valores_por_defecto()["indice_camara"]
    camara = CamaraReal(ajustes, fuente)
    await camara.iniciar()
    if not camara.disponible:
        print(f"No se pudo abrir la cámara {fuente}: {camara.ultimo_error}")
        return 1
    print(f"Cámara {fuente} abierta. Enter = tomar foto, q + Enter = salir.")
    numero = 1
    try:
        while True:
            if input(f"[{numero}] > ").strip().lower() == "q":
                break
            await una_vez(camara, ajustes, numero)
            numero += 1
    finally:
        camara.cerrar()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(principal()))
