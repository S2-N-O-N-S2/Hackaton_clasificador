"""Fase 9 (voz): interpretación del texto (sin micrófono) y la voz dentro del ciclo simulado.

La parte de audio (micrófono + Vosk) no se prueba aquí: se prueba a mano con el micrófono real.
Todo lo demás se prueba pasando TEXTO, como si Vosk ya lo hubiera reconocido (POST /api/sim/voz).
"""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Configuracion
from app.db import BaseDatos
from app.voice import Vocabulario, Voz, normalizar_texto, singular

KEYWORDS = Path(__file__).resolve().parent.parent / "data" / "keywords.json"


@pytest.fixture(scope="module")
def vocab():
    return Vocabulario.desde_archivo(KEYWORDS)


# ----------------------------------------------------------------------------- normalización
@pytest.mark.parametrize("palabra, esperado", [
    ("latas", "lata"), ("papeles", "papel"), ("cartones", "carton"), ("lapices", "lapiz"),
    ("envases", "envase"), ("pilas", "pila"), ("es", "es"), ("son", "son"), ("pan", "pan"),
])
def test_singular(palabra, esperado):
    assert singular(palabra) == esperado


def test_normalizar_texto():
    assert normalizar_texto("¿Dónde tiro ESTAS Cáscaras de plátano?") == \
        ["donde", "tiro", "esta", "cascara", "de", "platano"]
    assert normalizar_texto("La piña") == ["la", "piña"]
    assert normalizar_texto("") == []


# ----------------------------------------------------------------------------- interpretación
@pytest.mark.parametrize("texto, contexto, tipo, valor", [
    ("Es una cáscara de plátano", "revision", "categoria", 0),
    ("unas latas de refresco", "revision", "categoria", 1),
    ("una pila", "revision", "categoria", 2),
    ("es inorgánico", "revision", "categoria", 1),          # categoría dicha directo
    ("composta", "revision", "categoria", 0),               # sinónimo
    ("es una cosa rara", "revision", "desconocido", None),  # §15 caso 3
    ("", "revision", "vacio", None),
    ("usar IA", "menu", "modo", "ia"),
    ("quiero adivinar", "menu", "modo", "adivina"),
    ("¿dónde tiro esta botella?", "menu", "categoria", 1),  # §15 caso 2: pregunta directa
    ("orgánica", "adivinanza", "categoria", 0),
    ("tóxico", "adivinanza", "categoria", 2),
    ("botella", "adivinanza", "desconocido", None),         # en el juego solo cuentan las categorías
])
def test_interpretar(vocab, texto, contexto, tipo, valor):
    intencion = vocab.interpretar(texto, contexto)
    assert (intencion.tipo, intencion.valor) == (tipo, valor)


def test_gana_la_frase_mas_larga(vocab):
    assert vocab.interpretar("servilleta con comida", "revision").objeto == "servilleta con comida"
    assert vocab.interpretar("envases de medicina", "revision").valor == 2  # no "envase" (inorgánico)


def test_gramatica_por_estado(vocab):
    adivinanza = vocab.gramatica("adivinanza")
    assert "orgánica" in adivinanza and "botella" not in adivinanza and adivinanza[-1] == "[unk]"
    assert "usar ia" in vocab.gramatica("menu") and "usar ia" not in vocab.gramatica("revision")
    assert "cáscara de plátano" in vocab.gramatica("revision")  # con acentos: así las conoce Vosk


def test_vocabulario_valida_categorias():
    with pytest.raises(ValueError):
        Vocabulario({"objetos": {"cosa": 5}})
    with pytest.raises(ValueError):
        Vocabulario({"menu": {"hola": "bailar"}})
    with pytest.raises(ValueError):
        Vocabulario({}).interpretar("hola", "otro_contexto")


def test_keywords_tiene_unos_100_objetos(vocab):
    assert len(vocab.objetos) >= 100
    assert {0, 1, 2} == set(vocab.objetos.values())


def test_voz_sin_modelo_no_disponible_pero_interpreta(tmp_path):
    class A:
        dir_datos = KEYWORDS.parent
        dir_modelos = tmp_path  # sin vosk-model-small-es
    voz = Voz(A())
    assert voz.disponible is False and "Vosk" in voz.motivo
    assert voz.interpretar("una lata", "revision").valor == 1


def test_config_de_voz(tmp_path):
    config = Configuracion(BaseDatos(tmp_path / "c.db"))
    assert config.get("microfono") == "" and config.get("voz_segundos") == 4
    assert config.actualizar({"microfono": "DroidCam", "voz_segundos": 3})["microfono"] == "DroidCam"
    with pytest.raises(ValueError):
        config.actualizar({"voz_segundos": 30})


# ----------------------------------------------------------------------------- en el ciclo simulado
@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("SIMULACION", "1")
    monkeypatch.setenv("SIM_RAPIDO", "1")
    monkeypatch.delenv("SIM_IA_REAL", raising=False)
    monkeypatch.setenv("RUTA_DB", str(tmp_path / "prueba.db"))
    monkeypatch.setenv("DIR_CAPTURAS", str(tmp_path / "captures"))
    monkeypatch.setenv("DIR_DATASET", str(tmp_path / "dataset"))
    monkeypatch.setenv("DIR_MODELOS", str(tmp_path / "models"))  # sin Vosk: la voz real NO está disponible
    monkeypatch.setenv("DIR_SIM_IMAGENES", str(tmp_path / "sim_images"))
    from app.main import crear_app

    with TestClient(crear_app()) as c:
        esperar(lambda: c.get("/api/estado").json()["estado"] == "MENU")
        yield c


def esperar(condicion, limite=5.0):
    fin = time.time() + limite
    while time.time() < fin:
        if condicion():
            return
        time.sleep(0.02)
    raise AssertionError("La condición no se cumplió a tiempo")


def estado(c):
    return c.get("/api/estado").json()


def test_menu_por_voz(cliente):
    r = cliente.post("/api/sim/voz", json={"texto": "quiero adivinar"}).json()
    assert r["accion"] == "modo_adivina" and r["simulado"] is True
    assert estado(cliente)["estado"] == "ESPERA_OBJETO" and estado(cliente)["modo"] == "adivina"
    assert cliente.post("/api/sim/voz", json={"texto": "volver"}).json()["accion"] == "modo_menu"
    assert estado(cliente)["estado"] == "MENU"


def test_revision_resuelta_por_voz(cliente):
    cliente.post("/api/sim/objeto", json={"categoria_real": "dudoso"})
    esperar(lambda: estado(cliente)["estado"] == "REVISION")
    r = cliente.post("/api/sim/voz", json={"texto": "es una pila descargada"}).json()
    assert r["accion"] == "revision_resuelta" and r["intencion"]["valor"] == 2
    esperar(lambda: estado(cliente)["estado"] == "MENU")
    caso = cliente.get("/api/clasificaciones").json()["items"][0]
    assert caso["final_id"] == 2 and caso["origen"] == "voz" and caso["corregido"] is True
    assert caso["drop_confirmado"] is True


def test_palabra_desconocida_sigue_en_revision(cliente):
    cliente.post("/api/sim/objeto", json={"categoria_real": "dudoso"})
    esperar(lambda: estado(cliente)["estado"] == "REVISION")
    r = cliente.post("/api/sim/voz", json={"texto": "es un dinosaurio"}).json()
    assert r["accion"] == "no_reconocido"
    assert estado(cliente)["estado"] == "REVISION"
    assert estado(cliente)["lcd"][0] == "No reconoci el"


def test_conflicto_voz_y_camara_va_a_revision(cliente):
    r = cliente.post("/api/sim/voz", json={"texto": "¿dónde tiro esta botella?"}).json()
    assert r["accion"] == "respuesta_bote" and r["intencion"]["valor"] == 1
    cliente.post("/api/sim/objeto", json={"categoria_real": 0})  # la cámara ve algo orgánico
    esperar(lambda: estado(cliente)["estado"] == "REVISION")
    caso = estado(cliente)["caso_actual"]
    assert caso["dudoso"] is True and caso["motivo_dudoso"] == "conflicto_voz"


def test_voz_que_coincide_no_frena_el_ciclo(cliente):
    cliente.post("/api/sim/voz", json={"texto": "una lata"})
    cliente.post("/api/sim/objeto", json={"categoria_real": 1})
    esperar(lambda: cliente.get("/api/clasificaciones").json()["total"] == 1
            and estado(cliente)["estado"] == "MENU")
    caso = cliente.get("/api/clasificaciones").json()["items"][0]
    assert caso["final_id"] == 1 and not caso["dudoso"] and caso["origen"] == "camara"


def test_escuchar_sin_vosk_responde_503(cliente):
    assert estado(cliente)["voz"]["disponible"] is False
    r = cliente.post("/api/voz/escuchar")
    assert r.status_code == 503
    assert any(a["codigo"] == "VOZ_NO_DISPONIBLE" for a in estado(cliente)["alertas"])


def test_voz_no_se_usa_a_media_captura(cliente):
    cliente.post("/api/sim/objeto", json={"categoria_real": 1})
    esperar(lambda: estado(cliente)["estado"] in ("POSICIONAR", "SOLTAR", "REGISTRAR", "HOME"), 3)
    r = cliente.post("/api/sim/voz", json={"texto": "una lata"})
    assert r.status_code in (409, 200)  # 409 si sigue en el ciclo; 200 si ya regresó al menú


def test_arranque_con_voz_disponible_precarga_vosk(tmp_path, monkeypatch):
    """Con Vosk disponible el backend debe arrancar y precargar el modelo en segundo plano (error real del 19 nov)."""
    for var, valor in {"SIMULACION": "1", "SIM_RAPIDO": "1", "RUTA_DB": str(tmp_path / "v.db"),
                       "DIR_CAPTURAS": str(tmp_path / "c"), "DIR_DATASET": str(tmp_path / "d"),
                       "DIR_MODELOS": str(tmp_path / "m"), "DIR_SIM_IMAGENES": str(tmp_path / "s")}.items():
        monkeypatch.setenv(var, valor)
    monkeypatch.delenv("SIM_IA_REAL", raising=False)
    import app.main as principal

    llamadas = []

    class VozFalsa(Voz):
        def _revisar(self):
            return True

        def calentar(self):
            llamadas.append("calentar")

        def escuchar(self, contexto, segundos):
            return "es una lata" if contexto == "revision" else "usar ia"

    monkeypatch.setattr(principal, "Voz", VozFalsa)
    with TestClient(principal.crear_app()) as c:
        esperar(lambda: c.get("/api/estado").json()["estado"] == "MENU")
        esperar(lambda: llamadas == ["calentar"])
        assert c.get("/api/estado").json()["voz"]["disponible"] is True
        r = c.post("/api/voz/escuchar").json()  # "usar ia" en el menú
        assert r["accion"] == "modo_ia" and c.get("/api/estado").json()["estado"] == "ESPERA_OBJETO"


def test_pagina_de_prueba_y_microfonos(cliente):
    r = cliente.get("/prueba/voz")
    assert r.status_code == 200 and "PRUEBA DE VOZ" in r.text and "/api/voz/escuchar" in r.text
    d = cliente.get("/api/voz/microfonos").json()
    assert isinstance(d["microfonos"], list) and d["configurado"] == "" and "disponible" in d["voz"]


# ----------------------------------------------------------------------------- la voz que HABLA (tts.py)
def test_frases_del_locutor():
    from app import tts

    assert tts.frase_resultado(1, 0.948, "camara") == \
        "Es inorgánica, con 95 por ciento de certeza. Va en el bote azul."
    assert tts.frase_resultado(0, None, "voz") == "Listo: orgánica. Va en el bote verde."
    assert tts.frase_objeto("botella", 1) == "Botella: es inorgánica. Va en el bote azul."
    assert "no coincide" in tts.frase_revision("conflicto_voz")
    assert tts.frase_revision("confianza_baja").startswith("No estoy seguro.")


def test_locutor_callado_en_pruebas_y_fuera_de_windows():
    from app.tts import Locutor

    assert Locutor(activo=False).decir("hola") is False


class LocutorFalso:
    """Anota lo que el sistema habría dicho, sin sonido."""

    activo = True
    disponible = True
    nombre_voz = "falsa"
    motivo = None

    def __init__(self):
        self.dicho = []

    def calentar(self):
        pass

    def decir(self, texto, interrumpir=False):
        self.dicho.append(texto)
        return True

    def cerrar(self):
        pass


def test_dice_la_clasificacion_y_el_bote(cliente):
    locutor = LocutorFalso()
    cliente.app.state.ctx.orq.voz.locutor = locutor
    assert estado(cliente)["voz"]["habla"] is True
    cliente.post("/api/sim/objeto", json={"categoria_real": 1})
    esperar(lambda: any("bote azul" in d for d in locutor.dicho))
    assert any(d.startswith("Es inorgánica, con ") for d in locutor.dicho)

    cliente.post("/api/sim/objeto", json={"categoria_real": "dudoso"})
    esperar(lambda: any("¿Qué es?" in d for d in locutor.dicho))
    cliente.post("/api/sim/voz", json={"texto": "es una pila"})
    esperar(lambda: any(d == "Listo: peligroso. Va en el bote gris." for d in locutor.dicho))


def test_se_puede_callar_desde_la_configuracion(cliente):
    locutor = LocutorFalso()
    cliente.app.state.ctx.orq.voz.locutor = locutor
    assert cliente.put("/api/config", json={"voz_habla": False}).status_code == 200
    assert estado(cliente)["voz"]["habla"] is False
    cliente.post("/api/sim/voz", json={"texto": "dónde tiro esta lata"})
    time.sleep(0.3)
    assert locutor.dicho == []


def test_decir_y_nivel_responden_sin_hardware(cliente):
    assert cliente.post("/api/voz/decir", json={"texto": "hola"}).status_code == 503  # en pruebas está callada
    assert cliente.post("/api/voz/nivel").status_code in (200, 503)  # depende de si hay micrófono


def test_volumen_normaliza_y_no_satura():
    import numpy as np

    from app.tts import preparar_audio

    bajito = (np.sin(np.linspace(0, 60, 4000)) * 800).astype(np.int16)  # voz "bajita"
    normal = preparar_audio(bajito, 1.0)
    assert abs(np.abs(normal).max() - 0.98) < 1e-3          # 100 % = al máximo sin distorsión
    assert abs(np.abs(preparar_audio(bajito, 0.5)).max() - 0.49) < 1e-3
    fuerte = preparar_audio(bajito, 3.0)
    assert np.abs(fuerte).max() <= 0.981                     # 300 %: más fuerte, pero sin pasarse de 1.0
    assert np.sqrt((fuerte ** 2).mean()) > np.sqrt((normal ** 2).mean())  # se oye más fuerte (más energía)
    assert preparar_audio(np.zeros(10, np.int16), 2.0).max() == 0


def test_config_de_la_voz_que_habla(tmp_path):
    config = Configuracion(BaseDatos(tmp_path / "c.db"))
    assert config.get("voz_nombre") == "Laura" and config.get("voz_volumen") == 150
    assert config.actualizar({"voz_nombre": "Pablo", "voz_volumen": 250, "voz_velocidad": 1.2})["voz_volumen"] == 250
    for malo in ({"voz_volumen": 500}, {"voz_velocidad": 3}, {"voz_habla": "tal vez"}):
        with pytest.raises(ValueError):
            config.actualizar(malo)


def test_endpoint_de_voces(cliente):
    d = cliente.get("/api/voz/voces").json()
    assert d["voces"] == [] and d["configurada"] == "Laura" and d["volumen"] == 150  # en pruebas está callada


def test_listo_por_voz_toma_la_foto(cliente):
    r = cliente.post("/api/sim/voz", json={"texto": "listo"}).json()
    assert r["intencion"]["valor"] == "foto" and r["accion"] == "foto"


def _llevar_a_revision(cliente):
    cliente.post("/api/sim/objeto", json={"categoria_real": "desconocido"})
    esperar(lambda: cliente.get("/api/estado").json()["estado"] == "REVISION")


def test_revision_escrita_resuelve_con_el_objeto(cliente):
    """La persona escribe qué objeto es (no la categoría): el backend decide el bote."""
    _llevar_a_revision(cliente)
    r = cliente.post("/api/revision/objeto", json={"texto": "Es una cáscara de plátano"}).json()
    assert r["accion"] == "revision_resuelta" and r["intencion"]["valor"] == 0
    esperar(lambda: cliente.get("/api/clasificaciones").json()["items"][0]["estado"] == "registrado")
    caso = cliente.get("/api/clasificaciones").json()["items"][0]
    assert caso["origen"] == "texto" and caso["final_id"] == 0 and caso["corregido"] is True


def test_revision_escrita_desconocida_sigue_en_revision(cliente):
    _llevar_a_revision(cliente)
    r = cliente.post("/api/revision/objeto", json={"texto": "un cachivache raro"}).json()
    assert r["accion"] == "no_reconocido"
    assert cliente.get("/api/estado").json()["estado"] == "REVISION"


def test_revision_escrita_fuera_de_revision_da_409(cliente):
    assert cliente.post("/api/revision/objeto", json={"texto": "lata"}).status_code == 409
