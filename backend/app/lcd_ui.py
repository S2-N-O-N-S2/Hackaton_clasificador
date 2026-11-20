"""
lcd_ui.py — "Pantalla de la máquina" (4 líneas × 20 caracteres).

Cambio de diseño (20-nov): la máquina ya NO lleva LCD ni teclado 4×4. Todo se hace desde la página y por
voz. Estas pantallas se siguen generando porque el panel las muestra en Inicio ("Pantalla de la máquina").
Por eso los textos ya no mencionan teclas. Se conserva el formato de 20×4 sin acentos: si algún día se
conecta una LCD, el firmware la sigue soportando sin cambios.

Reglas (CLAUDE.md, regla 9):
  - máximo 20 caracteres por línea;
  - SIN acentos (la LCD HD44780 no los muestra);
  - sin el carácter '|' (es el separador de líneas del comando LCD).

Cada función `pantalla_*` devuelve una lista de 4 líneas ya limpias. `comando_lcd()` arma el
comando serial `LCD:<l1>|<l2>|<l3>|<l4>`.
"""

from __future__ import annotations

import unicodedata

ANCHO = 20
LINEAS = 4
MAX_SCROLL = 69  # línea serial ≤ 80 caracteres: 80 − len("LCD_SCROLL:") = 69

NOMBRES_LCD = {0: "ORGANICA", 1: "INORGANICA", 2: "PELIGROSO"}
COLORES_LCD = {0: "verde", 1: "azul", 2: "gris"}


def quitar_acentos(texto: str) -> str:
    """'Orgánica ¿ñandú?' → 'Organica nandu?'. Cualquier carácter no ASCII que quede se cambia por '?'."""
    texto = texto.replace("¿", "").replace("¡", "")
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_marcas = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return sin_marcas.encode("ascii", "replace").decode("ascii")


def limpiar(texto: str) -> str:
    """Texto seguro para el protocolo serial: ASCII, sin '|' ni saltos de línea."""
    texto = quitar_acentos(str(texto))
    return texto.replace("|", "/").replace("\r", " ").replace("\n", " ")


def linea(texto: str) -> str:
    """Una línea de la LCD: limpia y recortada a 20 caracteres."""
    return limpiar(texto)[:ANCHO]


def normalizar(lineas: list[str]) -> list[str]:
    """Exactamente 4 líneas válidas."""
    lineas = [linea(t) for t in lineas[:LINEAS]]
    return lineas + [""] * (LINEAS - len(lineas))


def comando_lcd(lineas: list[str]) -> str:
    return "LCD:" + "|".join(normalizar(lineas))


def comando_scroll(texto: str) -> str:
    return "LCD_SCROLL:" + limpiar(texto)[:MAX_SCROLL]


def porcentaje(confianza: float | None) -> str:
    return "--" if confianza is None else f"{round(confianza * 100)}%"


# ---------------------------------------------------------------------------
# Pantallas (§11 y §13 de la especificación)
# ---------------------------------------------------------------------------
def pantalla_menu() -> list[str]:
    return normalizar(["== CLASIFICADOR ==", "Elige en la pagina:", "Usar IA o Adivinar", "o dilo por voz"])


def pantalla_espera_objeto(modo: str) -> list[str]:
    titulo = "MODO ADIVINA" if modo == "adivina" else "MODO IA"
    return normalizar([titulo, "Coloca el residuo", "frente a la camara", "Menu: en la pagina"])


def pantalla_procesando() -> list[str]:
    return normalizar(["Analizando...", "No retires el", "residuo", ""])


def pantalla_resultado(categoria_id: int, confianza: float | None, origen: str = "camara") -> list[str]:
    fuente = "IA " + porcentaje(confianza) if origen == "camara" else f"Decidido: {origen}"
    return normalizar([
        f"Va en {NOMBRES_LCD[categoria_id]}",
        f"(bote {COLORES_LCD[categoria_id]})",
        fuente,
        "Gracias!",
    ])


def pantalla_revision(motivo: str | None, confianza: float | None) -> list[str]:
    if motivo == "riesgo_peligroso":
        segunda = "Posible peligroso"
    elif motivo == "conflicto_voz":
        segunda = "Voz y camara difieren"
    elif motivo == "sin_modelo":
        segunda = "IA no disponible"
    elif motivo == "desconocido":
        segunda = "Objeto no reconocido"
    elif motivo == "foto_no_valida":
        segunda = "Foto no valida"
    else:
        segunda = f"IA {porcentaje(confianza)} no segura"
    return normalizar(["AYUDA: que es?", segunda, "Elige en la pagina", "o dilo por voz"])


def pantalla_pendiente() -> list[str]:
    return normalizar(["REVISION PENDIENTE", "Un operador", "retirara el residuo", ""])


def pantalla_operador() -> list[str]:
    return normalizar(["MENU OPERADOR", "1/2/3: vaciar bote", "B: confirmar", "D o #: salir"])


def pantalla_error(mensaje: str) -> list[str]:
    return normalizar(["FALLA - SISTEMA", "DETENIDO (seguro)", mensaje, "Avise al operador"])


# ---------------------------------------------------------------------------
# Voz (§15)
# ---------------------------------------------------------------------------
def pantalla_escuchando(segundos: float) -> list[str]:
    return normalizar(["ESCUCHANDO...", f"Habla ahora ({segundos:g} s)", "Ej: cascara de", "platano"])


def pantalla_voz_entendida(objeto: str | None, categoria_id: int) -> list[str]:
    return normalizar([f"Entendi: {(objeto or '').upper()}", f"Va en {NOMBRES_LCD[categoria_id]}",
                       f"(bote {COLORES_LCD[categoria_id]})", ""])


def pantalla_voz_no_reconocida(texto: str) -> list[str]:
    return normalizar(["No reconoci el", "objeto", f"Oi: {texto}" if texto else "No oi nada", "Habla de nuevo"])
