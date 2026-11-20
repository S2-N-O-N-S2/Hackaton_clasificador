"""Calidad de la foto: sin señal, oscura, quemada, borrosa, estabilidad y elección de los mejores fotogramas."""

import numpy as np
import pytest

from app.camera import (
    FotoNoValida, diferencia_fotogramas, elegir_fotogramas, evaluar_foto, imagen_es_plana, metricas_foto,
)
from app.config import CAMARA


def foto_buena(semilla=0, brillo=130):
    """Bandeja gris con un objeto de bordes nítidos (como una foto bien tomada)."""
    azar = np.random.default_rng(semilla)
    img = np.full((240, 320, 3), brillo, dtype=np.uint8)
    img[60:180, 100:220] = (40, 160, 60)
    img[90:150, 130:190] = (230, 230, 230)
    ruido = azar.integers(-4, 5, img.shape)
    return np.clip(img.astype(np.int16) + ruido, 0, 255).astype(np.uint8)


def borrosa(img):
    import cv2
    return cv2.GaussianBlur(img, (0, 0), 9)


def test_foto_buena_pasa():
    assert evaluar_foto(foto_buena(), CAMARA) is None


def test_pantalla_verde_sin_senal():
    verde = np.zeros((240, 320, 3), dtype=np.uint8)
    verde[:] = (0, 200, 0)
    assert imagen_es_plana(verde)
    assert evaluar_foto(verde, CAMARA) == "sin_senal"


def test_oscura_y_quemada():
    assert evaluar_foto((foto_buena() * 0.1).astype(np.uint8), CAMARA) == "oscura"
    quemada = np.clip(foto_buena(brillo=250).astype(np.int16) + 120, 0, 255).astype(np.uint8)
    assert evaluar_foto(quemada, CAMARA) == "quemada"


def test_borrosa():
    assert metricas_foto(borrosa(foto_buena()))["nitidez"] < CAMARA["nitidez_min"]
    assert evaluar_foto(borrosa(foto_buena()), CAMARA) == "borrosa"


def test_elige_los_mas_nitidos_en_orden():
    frames = [borrosa(foto_buena(1)), foto_buena(2), (foto_buena(3) * 0.1).astype(np.uint8), foto_buena(4)]
    elegidos = elegir_fotogramas(frames, 3, CAMARA)
    # solo 2 sirven: se devuelven esos 2, en su orden original
    assert len(elegidos) == 2
    assert elegidos[0] is frames[1] and elegidos[1] is frames[3]


def test_si_ninguna_sirve_lanza_foto_no_valida_con_evidencia():
    oscuras = [(foto_buena(i) * 0.1).astype(np.uint8) for i in range(4)]
    with pytest.raises(FotoNoValida) as error:
        elegir_fotogramas(oscuras, 3, CAMARA)
    assert error.value.problema == "oscura"
    assert error.value.frame is not None
    assert "oscura" in str(error.value)


def test_lista_vacia():
    with pytest.raises(FotoNoValida):
        elegir_fotogramas([], 3, CAMARA)


def test_diferencia_detecta_movimiento():
    a = foto_buena(1)
    assert diferencia_fotogramas(a, a.copy()) < CAMARA["estabilidad_diferencia"]
    movida = np.roll(a, 40, axis=1)
    assert diferencia_fotogramas(a, movida) > CAMARA["estabilidad_diferencia"]


def test_vista_en_vivo_responde_204_en_simulacion(tmp_path, monkeypatch):
    """La cámara simulada no tiene vista en vivo: el panel recibe 204 y muestra la última foto."""
    monkeypatch.setenv("SIMULACION", "1")
    monkeypatch.delenv("SIM_IA_REAL", raising=False)
    monkeypatch.setenv("RUTA_DB", str(tmp_path / "prueba.db"))
    monkeypatch.setenv("DIR_CAPTURAS", str(tmp_path / "captures"))
    monkeypatch.setenv("DIR_DATASET", str(tmp_path / "dataset"))
    monkeypatch.setenv("DIR_MODELOS", str(tmp_path / "models"))
    from fastapi.testclient import TestClient

    from app.main import crear_app

    with TestClient(crear_app()) as c:
        r = c.get("/api/camara/cuadro")
    assert r.status_code == 204 and r.headers["cache-control"] == "no-store"


def test_vista_no_espera_si_el_ciclo_esta_tomando_la_foto():
    """Con el candado ocupado (CAPTURA), vista() regresa None al instante: la imagen se congela."""
    from app.camera import CamaraReal

    cam = CamaraReal.__new__(CamaraReal)
    import threading
    cam._lock = threading.Lock()
    cam._cap = object()
    with cam._lock:
        assert cam.vista() is None


def test_foto_movida_con_franjas_y_marca_de_agua_es_borrosa():
    """20-nov: una foto movida de DroidCam salía "nítida" por los bordes de las franjas negras y las letras de
    la marca "using droidcam.app". La nitidez se mide sin franjas y tras un filtro de mediana."""
    import cv2
    import numpy as np

    from app.camera import evaluar_foto
    from app.config import CAMARA

    azar = np.random.default_rng(7)
    escena = np.full((360, 640, 3), 120, np.uint8)
    for _ in range(60):  # objetos con bordes (como una foto real enfocada)
        x, y = int(azar.integers(0, 600)), int(azar.integers(0, 330))
        color = tuple(int(c) for c in azar.integers(40, 230, 3))
        cv2.rectangle(escena, (x, y), (x + int(azar.integers(10, 60)), y + int(azar.integers(10, 40))), color, -1)

    def como_droidcam(img):
        foto = np.zeros((480, 640, 3), np.uint8)  # franjas negras arriba y abajo (16:9 dentro de 4:3)
        foto[60:420] = img
        cv2.putText(foto, "using droidcam.app", (80, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        return foto

    nitida = como_droidcam(escena)
    movida = como_droidcam(cv2.GaussianBlur(escena, (0, 0), 6))
    assert evaluar_foto(nitida, CAMARA) is None
    assert evaluar_foto(movida, CAMARA) == "borrosa"
