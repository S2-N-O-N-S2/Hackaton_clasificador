"""Textos de la LCD 20×4: sin acentos, ≤ 20 caracteres, sin '|'."""

from app import lcd_ui


def test_quitar_acentos():
    assert lcd_ui.quitar_acentos("Orgánica Inorgánica ¿Qué? ¡Ñandú!") == "Organica Inorganica Que? Nandu!"


def test_linea_recorta_a_20():
    assert lcd_ui.linea("Ésta es una línea demasiado larga") == "Esta es una linea de"
    assert len(lcd_ui.linea("x" * 50)) == 20


def test_linea_quita_separador():
    assert "|" not in lcd_ui.linea("a|b")


def test_comando_lcd_siempre_4_lineas():
    cmd = lcd_ui.comando_lcd(["Hola"])
    assert cmd == "LCD:Hola|||"
    assert len(cmd) <= 80
    cmd = lcd_ui.comando_lcd(["1", "2", "3", "4", "5"])
    assert cmd.count("|") == 3


def test_comando_scroll_cabe_en_una_linea_serial():
    cmd = lcd_ui.comando_scroll("Se descompone naturalmente " * 10)
    assert len(cmd) <= 80 and cmd.startswith("LCD_SCROLL:")


def test_todas_las_pantallas_son_validas():
    pantallas = [
        lcd_ui.pantalla_menu(), lcd_ui.pantalla_espera_objeto("ia"), lcd_ui.pantalla_espera_objeto("adivina"),
        lcd_ui.pantalla_procesando(), lcd_ui.pantalla_pendiente(), lcd_ui.pantalla_operador(),
        lcd_ui.pantalla_error("SERIAL_DESCONECTADO"),
        *[lcd_ui.pantalla_resultado(c, 0.876) for c in (0, 1, 2)],
        *[lcd_ui.pantalla_revision(m, 0.45) for m in ("confianza_baja", "riesgo_peligroso", "sin_modelo")],
    ]
    for p in pantallas:
        assert len(p) == 4
        for l in p:
            assert len(l) <= 20 and l.isascii() and "|" not in l


def test_porcentaje():
    assert lcd_ui.porcentaje(0.876) == "88%"
    assert lcd_ui.porcentaje(None) == "--"
