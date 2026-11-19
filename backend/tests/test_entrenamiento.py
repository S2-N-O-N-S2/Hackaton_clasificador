"""Fase 4: separación por objeto, versiones, activación, caché, modelo real y evaluación.

Se usa un extractor FALSO (rápido, sin TensorFlow) que convierte la imagen en un vector de colores.
Las imágenes son sintéticas: esto prueba la LÓGICA, no la precisión real del sistema.
"""

import json
import time

import cv2
import numpy as np
import pytest

from app.config import Configuracion, fuente_camara
from app.db import BaseDatos
from app.model import ModeloReal, preparar_imagen, recortar_roi, version_activa
from training import train
from training.evaluate import evaluar, fotos_de_validacion

COLORES = {"organica": (40, 160, 60), "inorganica": (200, 120, 30), "peligroso": (90, 90, 90)}


class ExtractorFalso:
    nombre = "falso"

    def __init__(self):
        self.llamadas = 0

    def embeddings(self, imagenes):
        self.llamadas += len(imagenes)
        pequenas = [cv2.resize(i, (16, 16)).astype(np.float32).ravel() / 255 for i in imagenes]
        x = np.zeros((len(imagenes), 1280), dtype=np.float32)
        x[:, :768] = np.stack(pequenas)
        return x


def crear_dataset(raiz, objetos_por_clase=3, fotos_por_objeto=4, con_metadatos=True):
    azar = np.random.default_rng(0)
    filas = ["archivo,clase_id,clase,objeto_id,fecha_hora,camara"]
    for clase_id, (clave, color) in enumerate(COLORES.items()):
        (raiz / clave).mkdir(parents=True, exist_ok=True)
        for o in range(objetos_por_clase):
            for f in range(fotos_por_objeto):
                img = np.full((120, 160, 3), 200, np.uint8)
                c = tuple(int(v + azar.integers(-20, 20)) for v in color)
                cv2.circle(img, (int(azar.integers(50, 110)), int(azar.integers(40, 80))), 30, c, -1)
                nombre = f"{clave[:3]}{o}__20261119_1000{f:02d}_{f}.jpg"
                cv2.imwrite(str(raiz / clave / nombre), img)
                filas.append(f"{clave}/{nombre},{clase_id},{clave},{clave[:3]}{o},2026-11-19T10:00:00,0")
    if con_metadatos:
        (raiz / "metadatos.csv").write_text("\n".join(filas) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------- dataset y separación
def test_objeto_desde_nombre():
    assert train.objeto_desde_nombre("platano1__20261119_101500_3.jpg") == "platano1"
    assert train.objeto_desde_nombre("20261119_103205.jpg") == "20261119_103205"  # captura del backend


def test_listar_y_separar_por_objeto_sin_fuga(tmp_path):
    crear_dataset(tmp_path, objetos_por_clase=4)
    muestras = train.listar_dataset(tmp_path)
    assert len(muestras) == 3 * 4 * 4
    ent, val = train.separar_por_objeto(muestras, 0.25, semilla=1)
    objetos_ent = {muestras[i].objeto for i in ent}
    objetos_val = {muestras[i].objeto for i in val}
    assert objetos_ent and objetos_val and not (objetos_ent & objetos_val)  # ningún objeto en ambos lados
    for c in (0, 1, 2):
        assert any(muestras[i].clase == c for i in ent) and any(muestras[i].clase == c for i in val)


def test_separar_exige_dos_objetos_por_clase(tmp_path):
    crear_dataset(tmp_path, objetos_por_clase=1)
    with pytest.raises(train.ErrorDatos, match="al menos 2 objetos"):
        train.separar_por_objeto(train.listar_dataset(tmp_path))


def test_mismo_id_en_clases_distintas_no_se_mezcla(tmp_path):
    crear_dataset(tmp_path, objetos_por_clase=2, con_metadatos=False)
    grupos = {m.objeto for m in train.listar_dataset(tmp_path)}
    assert all(":" in g for g in grupos) and len(grupos) == 6


# ----------------------------------------------------------------------------- reglas de versiones
@pytest.mark.parametrize("nueva, activa, politica, esperado", [
    (0.80, None, "si_no_empeora", True),
    (0.80, 0.80, "si_no_empeora", True),    # igual: no empeora
    (0.79, 0.80, "si_no_empeora", False),
    (0.50, 0.90, "siempre", True),
    (0.99, 0.10, "nunca", False),
    (None, 0.50, "si_no_empeora", False),
])
def test_decidir_activacion(nueva, activa, politica, esperado):
    assert train.decidir_activacion(nueva, activa, politica)[0] is esperado


def test_siguiente_version(tmp_path):
    assert train.siguiente_version(tmp_path) == "v1"
    (tmp_path / "v1").mkdir()
    (tmp_path / "v7").mkdir()
    (tmp_path / "cache").mkdir()
    assert train.siguiente_version(tmp_path) == "v8"


def test_metricas():
    m = train.metricas([0, 0, 1, 2, 2], [0, 1, 1, 2, 0])
    assert m["precision"] == 0.6 and m["matriz_confusion"] == [[1, 1, 0], [0, 1, 0], [1, 0, 1]]
    assert m["por_clase"]["organica"]["acierto"] == 0.5


# ----------------------------------------------------------------------------- preprocesamiento y config
def test_roi_y_preparar_imagen():
    img = np.zeros((480, 640, 3), np.uint8)
    assert recortar_roi(img, [0.25, 0.5, 0.5, 0.5]).shape == (240, 320, 3)
    salida = preparar_imagen(img, [0, 0, 1, 1])
    assert salida.shape == (224, 224, 3) and salida.dtype == np.uint8


def test_config_roi_y_camara_url(tmp_path):
    config = Configuracion(BaseDatos(tmp_path / "c.db"))
    assert config.actualizar({"roi": [0.1, 0.1, 0.8, 0.8]})["roi"] == [0.1, 0.1, 0.8, 0.8]
    with pytest.raises(ValueError):
        config.actualizar({"roi": [0.5, 0.5, 0.8, 0.8]})  # se sale de la imagen
    assert fuente_camara("1") == 1
    assert fuente_camara("http://192.168.1.50:4747/video").startswith("http")
    with pytest.raises(ValueError):
        fuente_camara("-1")


# ----------------------------------------------------------------------------- entrenamiento completo
def test_entrenar_versiona_activa_y_usa_cache(tmp_path):
    datos, modelos = tmp_path / "dataset", tmp_path / "models"
    crear_dataset(datos)
    db = BaseDatos(tmp_path / "m.db")
    extractor = ExtractorFalso()

    r1 = train.entrenar(datos, modelos, db, extractor=extractor, semilla=3)
    assert r1["version"] == "v1" and r1["activado"] and version_activa(db) == "v1"
    for archivo in ("modelo.joblib", "labels.json", "split.json", "metricas.json"):
        assert (modelos / "v1" / archivo).exists()
    assert r1["precision_val"] > 0.5  # mejor que el azar (0.33). Dato SINTÉTICO: no es una medición real
    llamadas = extractor.llamadas

    r2 = train.entrenar(datos, modelos, db, extractor=extractor, semilla=3)
    assert extractor.llamadas == llamadas  # todo salió de la caché
    assert r2["version"] == "v2" and r2["activado"]  # misma precisión → no empeora → se activa

    db.ejecutar("UPDATE modelos SET precision_val = 1.01 WHERE version = 'v2'")  # simular uno "mejor"
    r3 = train.entrenar(datos, modelos, db, extractor=extractor, semilla=3)
    assert r3["activado"] is False and version_activa(db) == "v2"


def test_modelo_real_predice_en_orden_de_clases(tmp_path):
    datos, modelos = tmp_path / "dataset", tmp_path / "models"
    crear_dataset(datos)
    train.entrenar(datos, modelos, None, extractor=ExtractorFalso())
    modelo = ModeloReal(modelos / "v1", ExtractorFalso())
    foto = cv2.imread(str(next((datos / "peligroso").glob("*.jpg"))))
    probs = modelo.predecir([foto, foto])
    assert len(probs) == 2 and probs[0].shape == (3,) and abs(probs[0].sum() - 1) < 1e-6
    assert int(np.argmax(probs[0])) == 2


def test_aumento_de_datos_agrega_variantes(tmp_path):
    datos, modelos = tmp_path / "dataset", tmp_path / "models"
    crear_dataset(datos)
    r = train.entrenar(datos, modelos, None, extractor=ExtractorFalso(), aumentar=True)
    m = r["metricas"]
    n_val = m["validacion"]["n"]
    assert m["entrenamiento"]["n"] == 3 * (m["n_imagenes"] - n_val)  # original + 2 variantes, solo entrenamiento


def test_evaluar_genera_reportes(tmp_path):
    datos, modelos = tmp_path / "dataset", tmp_path / "models"
    crear_dataset(datos)
    train.entrenar(datos, modelos, None, extractor=ExtractorFalso())
    fotos = fotos_de_validacion(modelos / "v1", datos)
    r = evaluar(modelos / "v1", fotos, ExtractorFalso(), modelos / "v1" / "evaluacion")
    destino = modelos / "v1" / "evaluacion"
    assert (destino / "matriz_confusion.png").exists() and (destino / "resultados.md").exists()
    assert (destino / "fallidos").is_dir()
    assert r["n"] == len(fotos) and "a_revision" in r["con_umbrales"]
    assert json.loads((destino / "resultados.json").read_text(encoding="utf-8"))["metricas"]["n"] == len(fotos)


# ----------------------------------------------------------------------------- reentrenar desde la API
def test_reentrenar_desde_la_api(tmp_path, monkeypatch):
    monkeypatch.setenv("SIMULACION", "1")
    monkeypatch.setenv("SIM_RAPIDO", "1")
    monkeypatch.setenv("RUTA_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("DIR_CAPTURAS", str(tmp_path / "captures"))
    monkeypatch.setenv("DIR_DATASET", str(tmp_path / "dataset"))
    monkeypatch.setenv("DIR_MODELOS", str(tmp_path / "models"))
    monkeypatch.setenv("DIR_SIM_IMAGENES", str(tmp_path / "sim"))
    crear_dataset(tmp_path / "dataset")
    import app.main as principal
    from fastapi.testclient import TestClient

    monkeypatch.setattr(principal, "ExtractorMobileNet", ExtractorFalso)
    with TestClient(principal.crear_app()) as c:
        assert c.post("/api/modelo/reentrenar").status_code == 202
        fin = time.time() + 20
        while time.time() < fin and c.get("/api/modelo/estado").json()["entrenando"]:
            time.sleep(0.05)
        estado = c.get("/api/modelo/estado").json()
        assert estado["entrenando"] is False
        assert estado["ultimo_resultado"]["version"] == "v1" and estado["ultimo_resultado"]["activado"]
        assert estado["versiones"][0]["version"] == "v1"


# ----------------------------------------------------------------------------- revisar_dataset
def test_revisar_dataset_detecta_problemas(tmp_path):
    from tools.revisar_dataset import revisar

    crear_dataset(tmp_path, objetos_por_clase=2)
    errores, avisos, resumen = revisar(tmp_path, max_lado=320)
    assert errores == [] and resumen["organica"]["objetos"] == 2

    cv2.imwrite(str(tmp_path / "organica" / "sinid.jpg"), np.full((224, 224, 3), 120, np.uint8))
    cv2.imwrite(str(tmp_path / "inorganica" / "grande__1.jpg"),
                np.random.default_rng(1).integers(0, 255, (480, 640, 3), dtype=np.uint8))
    errores, avisos, _ = revisar(tmp_path, max_lado=320)
    texto = " ".join(errores + avisos)
    assert "SIN ID" in texto and "un solo color" in texto and "224×224" in texto and "más de 320" in texto


def test_revisar_dataset_exige_dos_objetos(tmp_path):
    from tools.revisar_dataset import revisar

    crear_dataset(tmp_path, objetos_por_clase=1)
    errores, _, _ = revisar(tmp_path)
    assert sum("al menos 2" in e for e in errores) == 3
