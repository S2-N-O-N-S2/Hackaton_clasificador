"""Ciclo completo con SIMULACION=1: OBJ → clasificación → POS → DROP → SQLite → WebSocket."""

import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("SIMULACION", "1")
    monkeypatch.setenv("SIM_RAPIDO", "1")
    monkeypatch.setenv("RUTA_DB", str(tmp_path / "prueba.db"))
    monkeypatch.setenv("DIR_CAPTURAS", str(tmp_path / "captures"))
    monkeypatch.setenv("DIR_DATASET", str(tmp_path / "dataset"))
    monkeypatch.setenv("DIR_MODELOS", str(tmp_path / "models"))
    monkeypatch.setenv("DIR_SIM_IMAGENES", str(tmp_path / "sim_images"))
    from app.main import crear_app

    with TestClient(crear_app()) as c:
        esperar(lambda: c.get("/api/estado").json()["estado"] == "MENU")
        yield c, tmp_path


def copiar_como_en_modo_real(monkeypatch):
    """La simulación nunca copia fotos al dataset (son falsas). Para probar la RUTA de copia (panel → dataset,
    teclado → _por_verificar) se hace la copia como en modo real."""
    import dataclasses

    import app.orchestrator as orq
    from app.camera import copiar_a_dataset

    monkeypatch.setattr(orq, "copiar_a_dataset", lambda ajustes, *a, **k: copiar_a_dataset(
        dataclasses.replace(ajustes, simulacion=False), *a, **k))


def esperar(condicion, limite=5.0):
    fin = time.time() + limite
    while time.time() < fin:
        if condicion():
            return
        time.sleep(0.02)
    raise AssertionError("La condición no se cumplió a tiempo")


def test_ciclo_ia_completo_registra_y_emite(cliente):
    c, tmp = cliente
    with c.websocket_connect("/ws/eventos") as ws:
        assert ws.receive_json()["tipo"] == "hola"
        assert c.post("/api/sim/objeto", json={"categoria_real": 1}).status_code == 200
        tipos, estados = [], []
        while "registrado" not in tipos:
            m = ws.receive_json()
            tipos.append(m["tipo"])
            if m["tipo"] == "estado":
                estados.append(m["datos"]["estado"])
    for e in ("CAPTURA", "CLASIFICACION", "VERIFICAR_BOTE", "POSICIONAR", "SOLTAR", "REGISTRAR"):
        assert e in estados
    esperar(lambda: c.get("/api/estado").json()["estado"] == "MENU")

    datos = c.get("/api/clasificaciones").json()
    assert datos["total"] == 1
    caso = datos["items"][0]
    assert caso["final_id"] == 1 and caso["pred_id"] == 1 and not caso["dudoso"]
    assert caso["simulado"] is True and caso["drop_confirmado"] is True and caso["estado"] == "registrado"
    assert caso["tiempo_ciclo_ms"] > 0
    assert (tmp / "captures" / caso["foto"].split("/")[-1]).exists()
    assert c.get(caso["foto"]).status_code == 200

    bote = c.get("/api/botes").json()["botes"][1]
    assert bote["piezas_actuales"] == 1 and bote["estimado"] is True
    stats = c.get("/api/estadisticas").json()
    assert stats["muestra"] == 1 and stats["matriz_confusion"]["valores"][1][1] == 1


def test_dudoso_va_a_revision_y_el_panel_lo_resuelve(cliente, monkeypatch):
    c, tmp = cliente
    copiar_como_en_modo_real(monkeypatch)
    c.post("/api/sim/objeto", json={"categoria_real": "dudoso"})
    esperar(lambda: c.get("/api/estado").json()["estado"] == "REVISION")
    estado = c.get("/api/estado").json()
    assert estado["caso_actual"]["dudoso"] is True and estado["caso_actual"]["final_id"] is None
    assert c.post("/api/modo", json={"modo": "ia"}).status_code == 409  # no se cambia de modo a medio ciclo

    r = c.post("/api/revision", json={"accion": "resolver", "final_id": 0})
    assert r.status_code == 200
    esperar(lambda: c.get("/api/estado").json()["estado"] == "MENU")
    caso = c.get("/api/clasificaciones").json()["items"][0]
    assert caso["final_id"] == 0 and caso["corregido"] is True and caso["origen"] == "panel"
    # Decisión del operador → directo al dataset (no a _por_verificar)
    assert (tmp / "dataset" / "organica" / caso["foto"].split("/")[-1]).exists()


def test_dudoso_resuelto_por_teclado_va_a_por_verificar(cliente, monkeypatch):
    c, tmp = cliente
    copiar_como_en_modo_real(monkeypatch)
    c.post("/api/sim/objeto", json={"categoria_real": "dudoso"})
    esperar(lambda: c.get("/api/estado").json()["estado"] == "REVISION")
    c.post("/api/sim/tecla", json={"tecla": "3"})
    esperar(lambda: c.get("/api/estado").json()["estado"] == "MENU")
    caso = c.get("/api/clasificaciones").json()["items"][0]
    assert caso["final_id"] == 2 and caso["origen"] == "teclado"
    pendientes = c.get("/api/dataset/por-verificar").json()["items"]
    assert len(pendientes) == 1 and pendientes[0]["clase_id"] == 2
    r = c.post("/api/dataset/por-verificar", json={"id": pendientes[0]["id"], "accion": "aprobar"})
    assert r.json() == {"ok": True, "pendientes": 0}


def test_revision_sin_respuesta_queda_pendiente(cliente):
    c, _ = cliente
    c.post("/api/sim/objeto", json={"categoria_real": "dudoso"})
    esperar(lambda: c.get("/api/estado").json()["estado"] == "REVISION")
    c.post("/api/revision", json={"accion": "pendiente"})
    esperar(lambda: c.get("/api/estado").json()["estado"] == "PENDIENTE")
    c.post("/api/sim/retirar")
    esperar(lambda: c.get("/api/estado").json()["estado"] == "MENU")
    caso = c.get("/api/clasificaciones").json()["items"][0]
    assert caso["estado"] == "pendiente" and caso["final_id"] is None and caso["drop_confirmado"] is None


def test_menu_por_teclado_y_modo_adivina_pasa_de_largo(cliente):
    c, _ = cliente
    c.post("/api/sim/tecla", json={"tecla": "2"})
    esperar(lambda: c.get("/api/estado").json()["estado"] == "ESPERA_OBJETO")
    assert c.get("/api/modo").json()["modo"] == "adivina"
    c.post("/api/sim/objeto", json={"categoria_real": 0})
    esperar(lambda: c.get("/api/clasificaciones").json()["total"] == 1
            and c.get("/api/estado").json()["estado"] == "MENU")
    caso = c.get("/api/clasificaciones").json()["items"][0]
    assert caso["modo"] == "adivina" and caso["final_id"] == 0


def test_config_valida_y_corregir(cliente):
    c, _ = cliente
    assert c.put("/api/config", json={"umbral_general": 1.5}).status_code == 422
    assert c.put("/api/config", json={"clave_rara": 1}).status_code == 422
    r = c.put("/api/config", json={"umbral_general": 0.7, "angulos": {"1": 95}})
    assert r.status_code == 200
    valores = r.json()["valores"]
    assert valores["umbral_general"] == 0.7 and valores["angulos"] == {"0": 170, "1": 95, "2": 10}

    c.post("/api/sim/objeto", json={"categoria_real": 0})
    esperar(lambda: c.get("/api/clasificaciones").json()["total"] == 1
            and c.get("/api/estado").json()["estado"] == "MENU")
    id_ = c.get("/api/clasificaciones").json()["items"][0]["id"]
    r = c.post(f"/api/clasificaciones/{id_}/corregir", json={"final_id": 2})
    assert r.status_code == 200 and r.json()["final_id"] == 2 and r.json()["corregido"] is True
    assert c.post("/api/clasificaciones/999/corregir", json={"final_id": 1}).status_code == 404


def test_control_manual_y_pruebas(cliente):
    c, _ = cliente
    r = c.post("/api/manual/pos", json={"id": 2})
    assert r.json() == {"ok": True, "respuesta_arduino": "POS_OK:2"}
    assert c.post("/api/manual/ang", json={"grados": 200}).status_code == 400
    assert c.post("/api/manual/home").json()["respuesta_arduino"] == "HOME_OK"

    residuo = c.post("/api/pruebas/residuos", json={"nombre": "Lata", "categoria_real": 1}).json()
    c.post("/api/pruebas", json={"corrida": 1, "modo": "manual", "residuo_id": residuo["id"],
                                 "categoria_asignada": 1, "tiempo_s": 3.5})
    comp = c.get("/api/pruebas").json()["comparativa"]
    assert comp["manual"]["precision"] == 1.0 and comp["sistema"]["n"] == 0


def test_foto_mala_no_se_clasifica_y_va_a_revision(cliente):
    c, _ = cliente
    c.post("/api/sim/objeto", json={"categoria_real": "foto_mala"})
    esperar(lambda: c.get("/api/estado").json()["estado"] == "REVISION")
    caso = c.get("/api/estado").json()["caso_actual"]
    assert caso["dudoso"] and caso["motivo_dudoso"] == "foto_no_valida" and caso["pred_id"] is None
    codigos = [a["codigo"] for a in c.get("/api/estado").json()["alertas"]]
    assert "FOTO_REINTENTO" in codigos and "FOTO_NO_VALIDA" in codigos
    assert c.post("/api/revision", json={"accion": "resolver", "final_id": 0}).status_code == 200
    esperar(lambda: c.get("/api/estado").json()["estado"] == "MENU")


def test_objeto_desconocido_va_a_revision_aunque_la_ia_este_segura(cliente):
    c, _ = cliente
    c.post("/api/sim/objeto", json={"categoria_real": "desconocido"})
    esperar(lambda: c.get("/api/estado").json()["estado"] == "REVISION")
    caso = c.get("/api/estado").json()["caso_actual"]
    assert caso["dudoso"] and caso["motivo_dudoso"] == "desconocido"
    assert caso["confianza"] >= 0.70  # la IA "cree" que sabe: por eso hace falta esta regla
    assert c.post("/api/revision", json={"accion": "pendiente"}).status_code == 200


def test_sim_objeto_rechaza_booleanos(cliente):
    c, _ = cliente
    assert c.post("/api/sim/objeto", json={"categoria_real": True}).status_code in (400, 422)


# --- Regresiones encontradas por la auditoría de 3000 usuarios (tools/auditoria_usuarios.py)
def test_el_panel_ve_el_destino_mientras_el_disco_gira(cliente):
    c, _ = cliente
    with c.websocket_connect("/ws/eventos") as ws:
        ws.receive_json()
        c.post("/api/sim/objeto", json={"categoria_real": 2})
        vistos = {}
        while "SOLTAR" not in vistos:
            m = ws.receive_json()
            if m["tipo"] == "estado" and m["datos"]["estado"] in ("POSICIONAR", "SOLTAR"):
                vistos[m["datos"]["estado"]] = (m["datos"].get("caso_actual") or {}).get("final_id")
    assert vistos == {"POSICIONAR": 2, "SOLTAR": 2}


def test_residuo_colocado_mientras_termina_el_ciclo_no_se_pierde(cliente):
    c, _ = cliente
    with c.websocket_connect("/ws/eventos") as ws:
        ws.receive_json()
        c.post("/api/sim/objeto", json={"categoria_real": 0})
        while True:  # el primer residuo ya cayó: el siguiente llega mientras se registra / regresa a HOME
            m = ws.receive_json()
            if m["tipo"] == "registrado":
                break
        assert c.post("/api/sim/objeto", json={"categoria_real": 1}).status_code == 200
    esperar(lambda: c.get("/api/clasificaciones").json()["total"] == 2
            and c.get("/api/estado").json()["estado"] == "MENU", limite=8)
    finales = sorted(x["final_id"] for x in c.get("/api/clasificaciones").json()["items"])
    assert finales == [0, 1]


@pytest.mark.parametrize("ruta, cuerpo", [
    ("/api/clasificaciones/1/corregir", {"final_id": True}),
    ("/api/pruebas/residuos", {"nombre": "x" * 500, "categoria_real": 1}),
    ("/api/pruebas/residuos", {"nombre": "", "categoria_real": 1}),
    ("/api/pruebas", {"corrida": 1, "modo": "manual", "residuo_id": 1, "categoria_asignada": 1, "tiempo_s": -3}),
    ("/api/juego/adivinar", {"categoria": True}),
])
def test_datos_invalidos_se_rechazan(cliente, ruta, cuerpo):
    c, _ = cliente
    assert c.post(ruta, json=cuerpo).status_code == 422


@pytest.mark.parametrize("cambio", [
    {"tiempo_revision_s": 10 ** 12}, {"umbral_general": True}, {"angulo_home": 90.5}, {"angulo_home": True},
    {"umbral_desconocido": 0}, {"roi": [0, 0, True, 1]},
])
def test_config_invalida_se_rechaza(cliente, cambio):
    c, _ = cliente
    assert c.put("/api/config", json=cambio).status_code in (400, 422)
    assert c.put("/api/config", content='{"umbral_general": NaN}', headers={"Content-Type": "application/json"}).status_code in (400, 422)
