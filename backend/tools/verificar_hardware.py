"""
verificar_hardware.py — Fase 0: diagnóstico del entorno y del hardware.

Qué revisa:
  1. Versión de Python y bibliotecas instaladas (sin importarlas, para que sea rápido).
  2. Puertos COM disponibles (pyserial) → para saber en qué COMx está el Arduino.
  3. Cámaras en los índices 0–3 (OpenCV) → guarda una foto de prueba de cada una que funcione
     en backend/captures/prueba_camara_<i>.jpg.
  4. Que exista el modelo de voz Vosk en backend/models/vosk-model-small-es.
  5. Micrófonos disponibles (sounddevice), para el push-to-talk de la Fase 9.

Uso (desde backend/, con el entorno virtual activo):
    python tools/verificar_hardware.py
    python tools/verificar_hardware.py --max-camaras 6

No modifica nada fuera de backend/captures/. Si falta una biblioteca, lo dice y sigue con lo demás.
"""

from __future__ import annotations

import argparse
import sys
from importlib import metadata
from pathlib import Path

# La consola de Windows usa cp1252 por defecto y falla con algunos caracteres.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Rutas relativas a backend/ (este archivo está en backend/tools/)
DIR_BACKEND = Path(__file__).resolve().parent.parent
DIR_CAPTURAS = DIR_BACKEND / "captures"
DIR_VOSK = DIR_BACKEND / "models" / "vosk-model-small-es"

# Bibliotecas de requirements.txt (nombre del paquete en pip)
PAQUETES = [
    "fastapi", "uvicorn", "opencv-python", "numpy", "tensorflow", "scikit-learn",
    "matplotlib", "pyserial", "vosk", "sounddevice", "pytest", "httpx",
]

OK, FALLA, AVISO = "[ OK ]", "[FALLA]", "[AVISO]"


def titulo(texto: str) -> None:
    print(f"\n=== {texto} ===")


def revisar_python() -> bool:
    titulo("Python y bibliotecas")
    v = sys.version_info
    version = f"{v.major}.{v.minor}.{v.micro}"
    # TensorFlow 2.21 publica ruedas para 3.10–3.13
    if (3, 10) <= (v.major, v.minor) <= (3, 13):
        print(f"{OK} Python {version} ({sys.executable})")
        python_ok = True
    else:
        print(f"{FALLA} Python {version}: TensorFlow requiere 3.10–3.13. Usen Python 3.12.")
        python_ok = False

    faltantes = []
    for paquete in PAQUETES:
        try:
            print(f"{OK} {paquete} {metadata.version(paquete)}")
        except metadata.PackageNotFoundError:
            print(f"{FALLA} {paquete} no instalado")
            faltantes.append(paquete)
    if faltantes:
        print(f"{AVISO} Instalen con: python -m pip install -r requirements.txt")
    return python_ok and not faltantes


def revisar_puertos() -> bool:
    titulo("Puertos serie (Arduino)")
    try:
        from serial.tools import list_ports
    except ImportError:
        print(f"{FALLA} pyserial no instalado; no se pueden listar puertos.")
        return False

    puertos = list(list_ports.comports())
    if not puertos:
        print(f"{AVISO} No hay puertos COM. ¿Está conectado el Arduino? ¿Falta el driver CH340?")
        return False
    for p in puertos:
        # Los UNO originales dicen "Arduino"; los clones suelen usar el chip CH340.
        pista = ""
        texto = f"{p.description} {p.manufacturer or ''}".lower()
        if "arduino" in texto or "ch340" in texto or "usb-serial" in texto:
            pista = "  <-- probablemente el Arduino"
        print(f"{OK} {p.device}: {p.description}{pista}")
    print("Anoten el COMx del Arduino en docs/mediciones.md (se configurará en la Fase 3).")
    return True


def revisar_camaras(max_indices: int) -> bool:
    titulo(f"Cámaras (índices 0–{max_indices - 1})")
    # Silencia los avisos internos de OpenCV al probar índices que no existen.
    import os
    os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
    try:
        import cv2
    except ImportError:
        print(f"{FALLA} opencv-python no instalado; no se pueden probar cámaras.")
        return False

    DIR_CAPTURAS.mkdir(parents=True, exist_ok=True)
    encontradas = 0
    for indice in range(max_indices):
        # CAP_DSHOW abre más rápido en Windows que el backend por defecto (MSMF).
        cam = cv2.VideoCapture(indice, cv2.CAP_DSHOW)
        try:
            if not cam.isOpened():
                print(f"  - índice {indice}: no disponible")
                continue
            # Los primeros fotogramas suelen salir oscuros mientras se ajusta la exposición.
            frame = None
            for _ in range(10):
                leido, frame = cam.read()
            if not leido or frame is None:
                print(f"{AVISO} índice {indice}: se abre pero no entrega imagen")
                continue
            alto, ancho = frame.shape[:2]
            destino = DIR_CAPTURAS / f"prueba_camara_{indice}.jpg"
            cv2.imwrite(str(destino), frame)
            print(f"{OK} índice {indice}: {ancho}x{alto} → foto en {destino.relative_to(DIR_BACKEND)}")
            encontradas += 1
        finally:
            cam.release()

    if encontradas == 0:
        print(f"{AVISO} No se encontró ninguna cámara. Revisen el cable USB o los permisos de cámara de Windows.")
        return False
    print("Abran las fotos para identificar cuál es la cámara cenital (la integrada de la laptop suele ser el índice 0).")
    return True


def revisar_vosk() -> bool:
    titulo("Modelo de voz Vosk")
    if DIR_VOSK.is_dir() and (DIR_VOSK / "am").is_dir():
        print(f"{OK} Modelo encontrado en {DIR_VOSK.relative_to(DIR_BACKEND)}")
        return True
    print(f"{FALLA} No existe {DIR_VOSK.relative_to(DIR_BACKEND)} (o está incompleto).")
    print("  Cómo descargarlo (~40 MB, hacerlo con buena red):")
    print("   1. Ir a https://alphacephei.com/vosk/models y bajar 'vosk-model-small-es-0.42' (.zip).")
    print("   2. Descomprimirlo en backend/models/.")
    print("   3. Renombrar la carpeta a 'vosk-model-small-es' (debe contener 'am/', 'conf/', 'graph/'...).")
    return False


def revisar_microfono() -> bool:
    titulo("Micrófonos (para la voz)")
    try:
        import sounddevice as sd
    except ImportError:
        print(f"{FALLA} sounddevice no instalado.")
        return False
    except OSError as error:  # PortAudio no se pudo cargar
        print(f"{FALLA} No se pudo cargar PortAudio: {error}")
        return False

    entradas = [(i, d) for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]
    if not entradas:
        print(f"{AVISO} No hay dispositivos de entrada de audio.")
        return False
    try:
        predeterminado = sd.default.device[0]
    except Exception:
        predeterminado = None
    for i, d in entradas:
        marca = "  <-- predeterminado" if i == predeterminado else ""
        print(f"{OK} [{i}] {d['name']}{marca}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico de entorno y hardware (Fase 0).")
    parser.add_argument("--max-camaras", type=int, default=4, help="cuántos índices de cámara probar (por defecto 4: 0–3)")
    args = parser.parse_args()

    resultados = {
        "Python y bibliotecas": revisar_python(),
        "Puertos COM": revisar_puertos(),
        "Cámaras": revisar_camaras(args.max_camaras),
        "Modelo Vosk": revisar_vosk(),
        "Micrófono": revisar_microfono(),
    }

    titulo("Resumen")
    for nombre, ok in resultados.items():
        print(f"{OK if ok else FALLA} {nombre}")
    # Código de salida 0 solo si todo está bien (útil para scripts).
    return 0 if all(resultados.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
