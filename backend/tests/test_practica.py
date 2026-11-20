"""Práctica con fotos del dataset: elección al azar por clase y rutas seguras."""

import random

from app.practica import elegir_fotos, ruta_foto
from tests.test_ciclo_simulado import cliente  # noqa: F401  (fixture con SIMULACION=1)


def crear_dataset(raiz, cuantas):
    for clave, n in cuantas.items():
        (raiz / clave).mkdir(parents=True, exist_ok=True)
        for i in range(n):
            (raiz / clave / f"{clave}_{i}.jpg").write_bytes(b"\xff\xd8\xff")
        (raiz / clave / "notas.txt").write_text("no es foto")
    (raiz / "_por_verificar" / "organica").mkdir(parents=True, exist_ok=True)
    (raiz / "_por_verificar" / "organica" / "sin_aprobar.jpg").write_bytes(b"\xff\xd8\xff")


def test_elige_20_por_clase_revueltas_y_sin_por_verificar(tmp_path):
    crear_dataset(tmp_path, {"organica": 30, "inorganica": 25, "peligroso": 40})
    r = elegir_fotos(tmp_path, 20, random.Random(1))
    assert r["total"] == 60
    cuenta = {0: 0, 1: 0, 2: 0}
    for it in r["items"]:
        cuenta[it["categoria_id"]] += 1
        assert it["id"].split("/")[0] == ["organica", "inorganica", "peligroso"][it["categoria_id"]]
        assert "_por_verificar" not in it["foto"] and it["foto"].endswith(".jpg")
    assert cuenta == {0: 20, 1: 20, 2: 20}
    assert len({it["id"] for it in r["items"]}) == 60
    assert [it["categoria_id"] for it in r["items"]] != sorted(it["categoria_id"] for it in r["items"])
    assert r["disponibles"] == {"organica": 30, "inorganica": 25, "peligroso": 40}


def test_si_una_clase_tiene_pocas_fotos_usa_todas(tmp_path):
    crear_dataset(tmp_path, {"organica": 5, "inorganica": 25})
    r = elegir_fotos(tmp_path, 20, random.Random(2))
    assert r["total"] == 25
    assert r["disponibles"]["peligroso"] == 0


def test_ruta_foto_no_sale_del_dataset(tmp_path):
    crear_dataset(tmp_path, {"organica": 1})
    (tmp_path / "secreto.jpg").write_bytes(b"x")
    assert ruta_foto(tmp_path, "organica", "organica_0.jpg") is not None
    assert ruta_foto(tmp_path, "organica", "../secreto.jpg") is None
    assert ruta_foto(tmp_path, "organica", "..\\secreto.jpg") is None
    assert ruta_foto(tmp_path, "_por_verificar", "sin_aprobar.jpg") is None
    assert ruta_foto(tmp_path, "organica", "notas.txt") is None
    assert ruta_foto(tmp_path, "organica", "no_existe.jpg") is None


def test_endpoints_de_practica(cliente):  # noqa: F811
    c, tmp = cliente
    crear_dataset(tmp / "dataset", {"organica": 22, "inorganica": 22, "peligroso": 22})
    r = c.get("/api/juego/fotos")
    assert r.status_code == 200 and r.json()["total"] == 60
    foto = r.json()["items"][0]["foto"]
    assert c.get(foto).status_code == 200
    assert c.get("/api/juego/fotos?por_categoria=0").status_code == 422
    assert c.get("/api/juego/fotos?por_categoria=500").status_code == 422
    assert c.get("/api/juego/fotos/organica/..%2Fsecreto.jpg").status_code == 404
    assert c.get("/api/juego/fotos/otra/x.jpg").status_code == 404
