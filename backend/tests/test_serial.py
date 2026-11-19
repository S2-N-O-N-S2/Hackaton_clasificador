"""Parser del protocolo serial y comportamiento del enlace (con el simulador)."""

import asyncio

import pytest

from app.serial_link import (ErrorArduino, ErrorSerial, EnlaceSimulado, TimeoutSerial, formatear_comando,
                             parsear_linea)


@pytest.mark.parametrize("linea, tipo, args", [
    ("POS_OK:1\r\n", "POS_OK", ["1"]),
    ("KEY:#\n", "KEY", ["#"]),
    ("KEY:*", "KEY", ["*"]),
    ("ERR:OCUPADO", "ERR", ["OCUPADO"]),
    ("CAL_OK:2:15", "CAL_OK", ["2", "15"]),
    ("READY", "READY", []),
    ("  OBJ  ", "OBJ", []),
    ("STATUS:ang=90,tramp=CERRADA,obj=0,cal=170/90/10", "STATUS", ["ang=90,tramp=CERRADA,obj=0,cal=170/90/10"]),
])
def test_parsear_linea(linea, tipo, args):
    m = parsear_linea(linea)
    assert m.tipo == tipo and m.args == args


@pytest.mark.parametrize("vacia", ["", "\r\n", "   "])
def test_lineas_vacias(vacia):
    assert parsear_linea(vacia) is None


def test_formatear_comando_valida():
    assert formatear_comando("POS:1") == "POS:1"
    with pytest.raises(ValueError):
        formatear_comando("LCD:a\nb")
    with pytest.raises(ValueError):
        formatear_comando("X" * 81)
    with pytest.raises(ValueError):
        formatear_comando("LCD:Orgánica")  # acentos: deben quitarse antes con lcd_ui


def _correr(corrutina):
    return asyncio.run(corrutina)


def test_simulador_responde_y_espontaneos():
    recibidos = []

    async def prueba():
        enlace = EnlaceSimulado(recibidos.append, factor_tiempo=0.01)
        await enlace.iniciar()
        assert await enlace.comando("PING", ("PONG",)) == "PONG"
        assert await enlace.comando("POS:0", ("POS_OK",), 2) == "POS_OK:0"
        assert enlace.angulo == 170
        assert await enlace.comando("CAL:1:95", ("CAL_OK",)) == "CAL_OK:1:95"
        assert await enlace.comando("LCD:hola|mundo||", ("OK",)) == "OK"
        enlace.simular_objeto()
        await asyncio.sleep(0.05)
        assert await enlace.comando("DROP", ("DROP_OK", "DROP_TIMEOUT"), 2) == "DROP_OK"
        await asyncio.sleep(0.05)
        await enlace.cerrar()

    _correr(prueba())
    tipos = [m.tipo for m in recibidos]
    assert "READY" in tipos and "OBJ" in tipos and "LIBRE" in tipos


def test_err_se_entrega_al_comando_que_espera():
    async def prueba():
        enlace = EnlaceSimulado(lambda m: None, factor_tiempo=0.01)
        await enlace.iniciar()
        with pytest.raises(ErrorArduino) as info:
            await enlace.comando("POS:7", ("POS_OK",))
        assert info.value.codigo == "ARG"
        with pytest.raises(ErrorArduino):
            await enlace.comando("ANG:200", ("ANG_OK",))
        with pytest.raises(ErrorArduino):
            await enlace.comando("FOO", ("OK",))
        await enlace.cerrar()

    _correr(prueba())


def test_drop_sin_objeto_da_timeout_del_sensor():
    async def prueba():
        enlace = EnlaceSimulado(lambda m: None, factor_tiempo=0.01)
        await enlace.iniciar()
        r = await enlace.comando("DROP", ("DROP_OK", "DROP_TIMEOUT"), 2)
        await enlace.cerrar()
        return r

    assert _correr(prueba()) == "DROP_TIMEOUT"


def test_sin_respuesta_lanza_timeout():
    class Mudo(EnlaceSimulado):
        def _escribir(self, linea):  # el "Arduino" no contesta
            pass

    async def prueba():
        enlace = Mudo(lambda m: None)
        await enlace.iniciar()
        with pytest.raises(TimeoutSerial):
            await enlace.comando("PING", ("PONG",), 0.05)
        await enlace.cerrar()

    _correr(prueba())


def test_desconectado_no_envia():
    async def prueba():
        enlace = EnlaceSimulado(lambda m: None)
        with pytest.raises(ErrorSerial):
            await enlace.comando("PING", ("PONG",))

    _correr(prueba())
