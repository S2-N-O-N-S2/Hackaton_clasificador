"""
config.py — TODA la configuración del sistema en un solo lugar.

Hay dos tipos de configuración:

1. `Ajustes`: se leen de variables de entorno AL ARRANCAR y no cambian mientras corre el servidor
   (modo simulación, rutas de carpetas y de la base de datos).

2. `Configuracion`: valores que el equipo ajusta desde el panel (umbrales, ángulos, tiempos...).
   Tienen un valor por defecto aquí y se guardan en la tabla `config` de SQLite.

Además, `TIEMPOS` agrupa los tiempos internos del ciclo (timeouts, esperas) para que no haya
"números mágicos" dispersos en el código.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DIR_BACKEND = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Categorías (fijas; ver docs/api_contrato.md §1.1)
# ---------------------------------------------------------------------------
CATEGORIAS = [
    {"id": 0, "clave": "organica", "nombre": "Orgánica", "color": "verde", "hex": "#2E9E44"},
    {"id": 1, "clave": "inorganica", "nombre": "Inorgánica", "color": "azul", "hex": "#1E6FD9"},
    {"id": 2, "clave": "peligroso", "nombre": "Peligroso", "color": "gris", "hex": "#6B7280"},
]
IDS_CATEGORIA = (0, 1, 2)
CLAVES_CATEGORIA = [c["clave"] for c in CATEGORIAS]          # ["organica", "inorganica", "peligroso"]
ID_PELIGROSO = 2

# ---------------------------------------------------------------------------
# Tiempos internos del ciclo (segundos, salvo que diga ms)
# ---------------------------------------------------------------------------
TIEMPOS = {
    "luz_ms": 200,               # espera tras encender la luz antes de capturar (especificación §10.2)
    "fotogramas": 3,             # fotogramas por captura (se promedian)
    "timeout_cmd_s": 1.5,        # respuesta a comandos rápidos (LCD, LED, LIGHT, PING)
    "timeout_pos_s": 6.0,        # giro del disco: 160° a 20 ms/° ≈ 3.2 s, con margen
    "timeout_drop_s": 4.0,       # el Arduino responde DROP_OK o DROP_TIMEOUT en ≤ 2 s
    "latido_s": 3.0,             # PING periódico (el watchdog del Arduino es de 15 s)
    "reintento_serial_s": 2.0,   # cada cuánto se intenta reconectar el puerto serie
    "espera_ready_s": 4.0,       # el UNO se reinicia al abrir el puerto y tarda ~2 s en mandar READY
    "espera_libre_s": 60.0,      # PENDIENTE: tiempo máximo esperando a que retiren el residuo
    "recuperacion_error_s": 3.0, # tiempo mínimo en ERROR antes de volver al menú si el enlace está bien
}

# ---------------------------------------------------------------------------
# Calidad de la foto (camera.py). Los umbrales marcados [COMPLETAR] se ajustan midiendo con la
# cámara real en la mesa: correr `python tools/probar_camara.py` y ver las métricas de cada foto.
# ---------------------------------------------------------------------------
CAMARA = {
    "vaciar_bufer_s": 0.35,        # se leen y tiran fotogramas este tiempo: el búfer de MSMF/DroidCam guarda fotos viejas
    "estabilidad_max_s": 1.5,      # tiempo máximo esperando a que la imagen deje de moverse
    "estabilidad_diferencia": 6.0, # diferencia media (0–255) entre fotogramas seguidos para considerarla quieta [COMPLETAR]
    "candidatos": 6,               # fotogramas que se toman para elegir los mejores
    "pausa_candidatos_s": 0.04,    # separación entre candidatos
    "plana_std": 4.0,              # desviación por canal menor a esto → imagen de un solo color (sin señal)
    "brillo_min": 35.0,            # brillo medio (0–255) menor a esto → foto oscura [COMPLETAR]
    "brillo_max": 225.0,           # brillo medio mayor a esto → foto quemada [COMPLETAR]
    "nitidez_min": 30.0,           # varianza del Laplaciano menor a esto → foto borrosa / movida [COMPLETAR]
    "reintentos": 1,               # si todas las fotos salen mal, se repite la captura una vez
}


def _env_bool(nombre: str, defecto: bool = False) -> bool:
    valor = os.getenv(nombre)
    if valor is None:
        return defecto
    return valor.strip().lower() in ("1", "true", "si", "sí", "yes", "on")


def _env_ruta(nombre: str, defecto: Path) -> Path:
    return Path(os.getenv(nombre, str(defecto))).resolve()


@dataclass(frozen=True)
class Ajustes:
    """Configuración fija de arranque (variables de entorno)."""

    simulacion: bool           # SIMULACION=1 → serial, cámara y modelo simulados
    sim_rapido: bool           # SIM_RAPIDO=1 → la simulación usa tiempos muy cortos (pruebas)
    ruta_db: Path
    dir_capturas: Path
    dir_dataset: Path
    dir_modelos: Path
    dir_sim_imagenes: Path
    dir_datos: Path
    baudios: int = 115200
    # SIM_IA_REAL=1 (solo junto con SIMULACION=1): el Arduino sigue simulado, pero la cámara y el modelo
    # son los REALES. Sirve para probar la IA desde el panel sin hardware. Los casos se guardan como simulados.
    ia_real: bool = False

    @property
    def factor_tiempo(self) -> float:
        """Multiplicador de las esperas internas (en pruebas todo va 20 veces más rápido)."""
        return 0.05 if (self.simulacion and self.sim_rapido) else 1.0


def cargar_ajustes() -> Ajustes:
    """Lee las variables de entorno. Se llama una vez al crear la aplicación."""
    simulacion = _env_bool("SIMULACION")
    # En simulación se usa OTRA base de datos para que los datos simulados nunca se mezclen con los reales
    db_por_defecto = DIR_BACKEND / ("clasificador_sim.db" if simulacion else "clasificador.db")
    ajustes = Ajustes(
        simulacion=simulacion,
        sim_rapido=_env_bool("SIM_RAPIDO"),
        ia_real=simulacion and _env_bool("SIM_IA_REAL"),
        ruta_db=_env_ruta("RUTA_DB", db_por_defecto),
        dir_capturas=_env_ruta("DIR_CAPTURAS", DIR_BACKEND / "captures"),
        dir_dataset=_env_ruta("DIR_DATASET", DIR_BACKEND / "dataset"),
        dir_modelos=_env_ruta("DIR_MODELOS", DIR_BACKEND / "models"),
        dir_sim_imagenes=_env_ruta("DIR_SIM_IMAGENES", DIR_BACKEND / "sim_images"),
        dir_datos=_env_ruta("DIR_DATOS", DIR_BACKEND / "data"),
    )
    for carpeta in (ajustes.dir_capturas, ajustes.dir_modelos, ajustes.dir_sim_imagenes):
        carpeta.mkdir(parents=True, exist_ok=True)
    for sub in CLAVES_CATEGORIA:
        (ajustes.dir_dataset / sub).mkdir(parents=True, exist_ok=True)
        (ajustes.dir_dataset / "_por_verificar" / sub).mkdir(parents=True, exist_ok=True)
    ajustes.ruta_db.parent.mkdir(parents=True, exist_ok=True)
    return ajustes


# ---------------------------------------------------------------------------
# Configuración editable desde el panel (tabla `config`)
# ---------------------------------------------------------------------------
def valores_por_defecto() -> dict[str, Any]:
    """Valores iniciales. Las variables de entorno PUERTO_SERIAL e INDICE_CAMARA cambian el valor inicial."""
    return {
        "umbral_general": 0.60,        # §4 regla 1
        "umbral_peligroso": 0.35,      # §4 regla 2 (asimetría de riesgo)
        "umbral_tono_firme": 0.80,     # §12.2 nivel de certeza alta
        "modo_por_defecto": "ia",      # §10.1
        # Ángulo del servo para cada bote: θ = 180° − φ (docs/mediciones.md). [COMPLETAR con la calibración]
        "angulos": {"0": 170, "1": 90, "2": 10},
        "angulo_home": 90,
        "puerto_serial": os.getenv("PUERTO_SERIAL", "AUTO"),   # "AUTO" = detectar el Arduino (CH340/Arduino)
        # Índice de OpenCV (0, 1, ...) o URL de un celular por Wi-Fi (http://IP:4747/video)
        "indice_camara": fuente_camara(os.getenv("INDICE_CAMARA", "0")),
        # Zona de interés de la foto [x, y, ancho, alto] en fracciones (0–1). Se recorta igual al
        # entrenar y al clasificar; cada modelo guarda la ROI con la que se entrenó.
        "roi": [0.0, 0.0, 1.0, 1.0],
        "tiempo_adivinanza_s": 20,
        "tiempo_revision_s": 30,
        "tiempo_retro_firme_s": 5,
        "tiempo_retro_media_s": 8,
        "umbral_aviso_bote": 0.80,
        # Objeto desconocido: qué tan lejos (1.0 = percentil 99 × 1.1 de las fotos de entrenamiento) puede quedar
        # una foto de todo lo que la IA conoce antes de mandarla a revisión aunque la confianza sea alta.
        # Menor = más estricto. Con v1 (fotos de internet, muy variadas) 0.85 marca 2.3 % de objetos conocidos
        # de validación y sí marca ruido / cámara sin señal. [COMPLETAR: recalibrar con fotos propias de la bandeja
        # usando tools/calibrar_desconocidos.py]
        "umbral_desconocido": 0.85,
        # Voz (§15): micrófono ("" = predeterminado de Windows, o parte de su nombre, ej. "DroidCam") y
        # segundos que se graba al presionar A (push-to-talk)
        "microfono": "",
        "voz_segundos": 4,
    }


# Claves que solo se aplican al reiniciar el backend
CLAVES_REQUIEREN_REINICIO = {"puerto_serial", "indice_camara"}


def _numero(v: Any) -> float:
    """Número real finito. Rechaza true/false (en Python True == 1) y NaN/infinito."""
    if isinstance(v, bool) or v is None:
        raise ValueError("debe ser un número")
    v = float(v)
    if v != v or v in (float("inf"), float("-inf")):
        raise ValueError("debe ser un número finito")
    return v


def _entero(v: Any) -> int:
    """Entero. Rechaza true/false y decimales (antes 1.9 se convertía en 1 sin avisar)."""
    n = _numero(v)
    if n != int(n):
        raise ValueError("debe ser un número entero")
    return int(n)


def _validar_umbral(v: Any) -> float:
    v = _numero(v)
    if not 0.0 <= v <= 1.0:
        raise ValueError("debe estar entre 0 y 1")
    return round(v, 4)


def _validar_umbral_desconocido(v: Any) -> float:
    v = _numero(v)
    if not 0.5 <= v <= 3.0:
        raise ValueError("debe estar entre 0.5 y 3")
    return round(v, 3)


def _validar_angulo(v: Any) -> int:
    v = _entero(v)
    if not 0 <= v <= 180:
        raise ValueError("debe estar entre 0 y 180")
    return v


def _validar_entero_positivo(v: Any) -> int:
    """Tiempos en segundos: de 1 a 600 (10 min). Antes se aceptaba 10^12 s y una revisión no vencía nunca."""
    v = _entero(v)
    if not 1 <= v <= 600:
        raise ValueError("debe estar entre 1 y 600")
    return v


def _validar_angulos(v: Any) -> dict[str, int]:
    if not isinstance(v, dict):
        raise ValueError("debe ser un objeto {\"0\": grados, \"1\": grados, \"2\": grados}")
    salida = {}
    for clave, grados in v.items():
        if str(clave) not in ("0", "1", "2"):
            raise ValueError(f"categoría inválida: {clave}")
        salida[str(clave)] = _validar_angulo(grados)
    return salida


def _validar_modo(v: Any) -> str:
    if v not in ("ia", "adivina"):
        raise ValueError("debe ser 'ia' o 'adivina'")
    return v


def _validar_texto_opcional(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _validar_segundos_voz(v: Any) -> float:
    v = float(v)
    if not 1 <= v <= 10:
        raise ValueError("debe estar entre 1 y 10 segundos")
    return v


def _validar_texto(v: Any) -> str:
    v = str(v).strip()
    if not v:
        raise ValueError("no puede estar vacío")
    return v


def fuente_camara(v: Any) -> int | str:
    """Acepta un índice de OpenCV ('1' → 1) o una URL de video (http://, https://, rtsp://)."""
    texto = str(v).strip()
    if texto.lower().startswith(("http://", "https://", "rtsp://")):
        return texto
    indice = int(texto)
    if indice < 0:
        raise ValueError("debe ser 0 o mayor, o una URL http://...")
    return indice


def _validar_roi(v: Any) -> list[float]:
    if not isinstance(v, (list, tuple)) or len(v) != 4:
        raise ValueError("debe ser [x, y, ancho, alto] en fracciones de 0 a 1")
    x, y, ancho, alto = (_numero(n) for n in v)
    if not (0 <= x < 1 and 0 <= y < 1 and 0 < ancho <= 1 and 0 < alto <= 1 and x + ancho <= 1.0001 and y + alto <= 1.0001):
        raise ValueError("la zona debe quedar dentro de la imagen")
    return [round(x, 4), round(y, 4), round(ancho, 4), round(alto, 4)]


VALIDADORES = {
    "umbral_general": _validar_umbral,
    "umbral_peligroso": _validar_umbral,
    "umbral_tono_firme": _validar_umbral,
    "umbral_aviso_bote": _validar_umbral,
    "umbral_desconocido": _validar_umbral_desconocido,
    "modo_por_defecto": _validar_modo,
    "angulos": _validar_angulos,
    "angulo_home": _validar_angulo,
    "puerto_serial": _validar_texto,
    "indice_camara": fuente_camara,
    "roi": _validar_roi,
    "tiempo_adivinanza_s": _validar_entero_positivo,
    "tiempo_revision_s": _validar_entero_positivo,
    "tiempo_retro_firme_s": _validar_entero_positivo,
    "tiempo_retro_media_s": _validar_entero_positivo,
    "microfono": _validar_texto_opcional,
    "voz_segundos": _validar_segundos_voz,
}


class Configuracion:
    """Valores editables. Lee y escribe la tabla `config` (clave, valor en JSON)."""

    def __init__(self, db) -> None:
        self._db = db
        self._valores = valores_por_defecto()
        for fila in db.consultar("SELECT clave, valor FROM config"):
            if fila["clave"] in self._valores:
                try:
                    self._valores[fila["clave"]] = json.loads(fila["valor"])
                except json.JSONDecodeError:
                    pass  # valor corrupto: se queda el valor por defecto

    def get(self, clave: str) -> Any:
        return self._valores[clave]

    def todo(self) -> dict[str, Any]:
        return json.loads(json.dumps(self._valores))  # copia profunda

    def angulo(self, categoria_id: int) -> int:
        return int(self._valores["angulos"][str(categoria_id)])

    def actualizar(self, parcial: dict[str, Any]) -> dict[str, Any]:
        """Valida TODO antes de guardar; si un valor es inválido no se guarda nada (ValueError)."""
        nuevos: dict[str, Any] = {}
        for clave, valor in parcial.items():
            if clave not in VALIDADORES:
                raise ValueError(f"'{clave}': clave desconocida")
            try:
                nuevos[clave] = VALIDADORES[clave](valor)
            except (TypeError, ValueError) as error:
                raise ValueError(f"'{clave}': {error}") from None
        if "angulos" in nuevos:  # permitir actualizar un solo ángulo
            nuevos["angulos"] = {**self._valores["angulos"], **nuevos["angulos"]}
        for clave, valor in nuevos.items():
            self._valores[clave] = valor
            self._db.ejecutar(
                "INSERT INTO config(clave, valor) VALUES(?, ?) "
                "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
                (clave, json.dumps(valor)),
            )
        return self.todo()
