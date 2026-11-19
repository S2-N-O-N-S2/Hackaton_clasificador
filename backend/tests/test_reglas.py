"""Reglas de decisión (§4): límites EXACTOS de 0.60 y 0.35."""

import pytest

from app.model import aplicar_reglas, promediar

G, P = 0.60, 0.35  # UMBRAL_GENERAL, UMBRAL_PELIGROSO


def test_confianza_exactamente_060_se_acepta():
    d = aplicar_reglas([0.60, 0.30, 0.10], G, P)
    assert (d.pred_id, d.dudoso, d.motivo) == (0, False, None)


def test_confianza_debajo_de_060_va_a_revision():
    d = aplicar_reglas([0.599, 0.301, 0.10], G, P)
    assert d.dudoso and d.motivo == "confianza_baja" and d.pred_id == 0


def test_peligroso_exactamente_035_sin_ganar_va_a_revision():
    # Orgánica gana con 0.65 (≥ 0.60), pero p(peligroso) = 0.35 → asimetría de riesgo
    d = aplicar_reglas([0.65, 0.00, 0.35], G, P)
    assert d.dudoso and d.motivo == "riesgo_peligroso" and d.pred_id == 0


def test_peligroso_debajo_de_035_se_acepta():
    d = aplicar_reglas([0.651, 0.00, 0.349], G, P)
    assert not d.dudoso and d.pred_id == 0


def test_peligroso_ganador_seguro_se_acepta():
    d = aplicar_reglas([0.10, 0.20, 0.70], G, P)
    assert (d.pred_id, d.dudoso) == (2, False)


def test_peligroso_ganador_con_baja_confianza_va_a_revision():
    d = aplicar_reglas([0.25, 0.20, 0.55], G, P)
    assert d.dudoso and d.motivo == "confianza_baja" and d.pred_id == 2


def test_riesgo_peligroso_tiene_prioridad_sobre_confianza_baja():
    d = aplicar_reglas([0.40, 0.20, 0.40 - 1e-9], G, P)
    assert d.motivo == "riesgo_peligroso"


def test_promedio_con_error_de_redondeo_en_el_limite():
    # Tres fotogramas cuyo promedio es 0.6 con error de punto flotante
    probs = promediar([[0.6, 0.3, 0.1], [0.7, 0.2, 0.1], [0.5, 0.4, 0.1]])
    d = aplicar_reglas(probs, G, P)
    assert probs[0] == pytest.approx(0.6) and not d.dudoso


def test_umbral_configurable():
    probs = [0.70, 0.20, 0.10]
    assert not aplicar_reglas(probs, 0.60, P).dudoso
    assert aplicar_reglas(probs, 0.75, P).dudoso  # cambio "en vivo" del umbral


def test_promediar_valida_forma():
    with pytest.raises(ValueError):
        promediar([[0.5, 0.5]])
