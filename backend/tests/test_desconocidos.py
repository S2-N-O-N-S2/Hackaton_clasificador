"""Objetos desconocidos: centros por clase, puntaje de novedad y la regla que manda a revisión."""

import numpy as np
import pytest

from app.model import DIMENSION_EMBEDDING, aplicar_reglas, calcular_novedad, puntaje_novedad


def nube(centro, n, dispersion, semilla):
    azar = np.random.default_rng(semilla)
    return centro + azar.normal(0, dispersion, (n, DIMENSION_EMBEDDING))


@pytest.fixture
def datos():
    azar = np.random.default_rng(7)
    centros = [np.abs(azar.normal(0, 1, DIMENSION_EMBEDDING)) for _ in range(3)]
    x = np.vstack([nube(c, 60, 0.15, i) for i, c in enumerate(centros)])
    y = [0] * 60 + [1] * 60 + [2] * 60
    return centros, calcular_novedad(x, y)


def test_formato(datos):
    _, d = datos
    assert len(d["centros"]) == 3 and len(d["centros"][0]) == DIMENSION_EMBEDDING
    assert len(d["limites"]) == 3 and all(lim > 0 for lim in d["limites"])
    assert d["n"] == [60, 60, 60]


def test_objeto_conocido_queda_dentro(datos):
    centros, d = datos
    for i, c in enumerate(centros):
        assert puntaje_novedad(nube(c, 3, 0.15, 100 + i), d) <= 1.0


def test_objeto_desconocido_queda_fuera(datos):
    _, d = datos
    raro = np.random.default_rng(99).normal(0, 1, (3, DIMENSION_EMBEDDING))  # nada que ver con las clases
    assert puntaje_novedad(raro, d) > 1.0


def test_clase_sin_ejemplos():
    with pytest.raises(ValueError):
        calcular_novedad(np.ones((4, DIMENSION_EMBEDDING)), [0, 0, 1, 1])


def test_regla_desconocido_aunque_la_confianza_sea_alta():
    d = aplicar_reglas([0.05, 0.90, 0.05], 0.60, 0.35, novedad=1.5, umbral_desconocido=1.0)
    assert d.dudoso and d.motivo == "desconocido" and d.pred_id == 1


def test_regla_limite_inclusivo_y_sin_datos():
    assert not aplicar_reglas([0.05, 0.90, 0.05], 0.60, 0.35, novedad=1.0, umbral_desconocido=1.0).dudoso
    assert not aplicar_reglas([0.05, 0.90, 0.05], 0.60, 0.35, novedad=None).dudoso


def test_riesgo_peligroso_tiene_prioridad():
    d = aplicar_reglas([0.55, 0.05, 0.40], 0.60, 0.35, novedad=2.0)
    assert d.motivo == "riesgo_peligroso"


def test_probabilidades_invalidas():
    with pytest.raises(ValueError):
        aplicar_reglas([float("nan"), 0.5, 0.5], 0.60, 0.35)
