"""Fase 5 (preparación): tiempos por etapa, sincronización de ángulos, migración y calibración."""

import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

from app.config import Configuracion
from app.db import BaseDatos
from tools.calibrar_angulos import Calibrador, ErrorApi


def _entorno(tmp_path, monkeypatch):
    monkeypatch.setenv("SIMULACION", "1")
    monkeypatch.setenv("SIM_RAPIDO", "1")
    monkeypatch.setenv("RUTA_DB", str(tmp_path / "f5.db"))
    monkeypatch.setenv("DIR_CAPTURAS", str(tmp_path / "captures"))
    monkeypatch.setenv("DIR_DATASET", str(tmp_path / "dataset"))
    monkeypatch.setenv("DIR_MODELOS", str(tmp_path / "models"))
    monkeypatch.setenv("DIR_SIM_IMAGENES", str(tmp_path / "sim"))


def esperar(condicion, limite=5.0):
    fin = time.time() + limite
    while time.time() < fin:
        if condicion():
            return
        time.sleep(0.02)
    raise AssertionError("La condición no se cumplió a tiempo")


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    _entorno(tmp_path, monkeypatch)
    from app.main import crear_app

    with TestClient(crear_app()) as c:
        esperar(lambda: c.get("/api/estado").json()["estado"] == "MENU")
        yield c


def test_tiempos_por_etapa_se_guardan(cliente):
    cliente.post("/api/sim/objeto", json={"categoria_real": 2})
    esperar(lambda: cliente.get("/api/clasificaciones").json()["total"] == 1
            and cliente.get("/api/estado").json()["estado"] == "MENU")
    caso = cliente.get("/api/clasificaciones").json()["items"][0]
    tiempos = caso["tiempos_etapas"]
    for etapa in ("CAPTURA", "CLASIFICACION", "POSICIONAR", "SOLTAR", "HOME"):
        assert etapa in tiempos and tiempos[etapa] >= 0


def test_angulos_de_la_config_se_mandan_al_arduino_al_conectar(tmp_path, monkeypatch):
    _entorno(tmp_path, monkeypatch)
    Configuracion(BaseDatos(tmp_path / "f5.db")).actualizar({"angulos": {"0": 165, "1": 92, "2": 14}})
    from app.main import crear_app

    app = crear_app()
    with TestClient(app) as c:
        esperar(lambda: c.get("/api/estado").json()["estado"] == "MENU")
        enlace = app.state.ctx.orq.enlace
        esperar(lambda: enlace.calibracion == {"0": 165, "1": 92, "2": 14})


def test_migracion_agrega_columna_a_base_vieja(tmp_path):
    ruta = tmp_path / "vieja.db"
    with sqlite3.connect(ruta) as con:  # base creada antes de la Fase 5 (sin tiempos_etapas)
        con.execute("CREATE TABLE clasificaciones (id INTEGER PRIMARY KEY, fecha_hora TEXT NOT NULL, foto TEXT, "
                    "modo TEXT NOT NULL, pred_id INTEGER, confianza REAL, p_organica REAL, p_inorganica REAL, "
                    "p_peligroso REAL, final_id INTEGER, origen TEXT NOT NULL DEFAULT 'camara', dudoso INTEGER "
                    "NOT NULL DEFAULT 0, motivo_dudoso TEXT, corregido INTEGER NOT NULL DEFAULT 0, modelo_version "
                    "TEXT, tiempo_ciclo_ms INTEGER, drop_confirmado INTEGER, bote_id INTEGER, simulado INTEGER "
                    "NOT NULL DEFAULT 0, estado TEXT NOT NULL DEFAULT 'en_proceso')")
    db = BaseDatos(ruta)
    columnas = {f["name"] for f in db.consultar("PRAGMA table_info(clasificaciones)")}
    assert "tiempos_etapas" in columnas


def _enviar_por(cliente):
    def enviar(metodo, ruta, cuerpo=None):
        respuesta = cliente.request(metodo, ruta, json=cuerpo)
        if respuesta.status_code >= 400:
            raise ErrorApi(f"{respuesta.status_code}: {respuesta.json().get('detail')}")
        return respuesta.json()
    return enviar


def test_calibrador_mueve_guarda_y_sincroniza(cliente):
    calibrador = Calibrador(_enviar_por(cliente))
    calibrador.cargar()
    assert calibrador.guardados == {0: 170, 1: 90, 2: 10} and calibrador.angulo == 90

    assert "ANG_OK:91" in calibrador.aplicar("derecha")
    assert "ANG_OK:96" in calibrador.aplicar("arriba")
    assert "GUARDADO" in calibrador.aplicar("2")             # Inorgánica = 96°
    assert cliente.get("/api/config").json()["valores"]["angulos"]["1"] == 96
    enlace = cliente.app.state.ctx.orq.enlace
    assert enlace.calibracion["1"] == 96                      # llegó a la "EEPROM" (CAL)

    assert "ANG_OK:170" in calibrador.aplicar("o")            # ir al guardado de Orgánica
    assert "HOME_OK" in calibrador.aplicar("h")
    assert "DROP_OK" in calibrador.aplicar("d")               # sin sensor de caída: abre y cierra
    assert calibrador.aplicar("q") is None


def test_calibrador_no_pasa_de_0_a_180(cliente):
    calibrador = Calibrador(_enviar_por(cliente))
    calibrador.cargar()
    calibrador.mover_a(178)
    calibrador.aplicar("arriba")
    assert calibrador.angulo == 180


def test_calibrador_se_niega_a_medio_ciclo(cliente):
    cliente.post("/api/sim/objeto", json={"categoria_real": "dudoso"})
    esperar(lambda: cliente.get("/api/estado").json()["estado"] == "REVISION")
    with pytest.raises(ErrorApi, match="REVISION"):
        Calibrador(_enviar_por(cliente)).cargar()


def test_migra_bases_viejas_para_aceptar_origen_texto(tmp_path):
    """Una base creada antes del 20-nov (CHECK sin 'texto') se migra sin perder datos y con respaldo."""
    import sqlite3

    from app.db import ESQUEMA, BaseDatos

    ruta = tmp_path / "vieja.db"
    con = sqlite3.connect(ruta)
    con.executescript(ESQUEMA.replace("'teclado', 'panel', 'texto')", "'teclado', 'panel')"))
    con.execute("INSERT INTO clasificaciones(fecha_hora, modo, origen) VALUES ('2026-11-19T10:00:00', 'ia', 'voz')")
    con.commit()
    con.close()

    db = BaseDatos(ruta)
    assert db.uno("SELECT COUNT(*) AS n FROM clasificaciones")["n"] == 1
    db.ejecutar("UPDATE clasificaciones SET origen = 'texto' WHERE id = 1")
    assert db.uno("SELECT origen FROM clasificaciones WHERE id = 1")["origen"] == "texto"
    assert (tmp_path / "vieja.db.antes_texto.bak").exists()
