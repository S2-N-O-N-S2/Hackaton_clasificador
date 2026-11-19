"""
voice.py — Voz offline con Vosk (especificación §15).

Dos partes separadas a propósito:

1. **Interpretar texto** (lógica pura, se prueba sin micrófono): `normalizar_texto()` + `Vocabulario.interpretar()`.
   Convierte "Es una cáscara de plátano" → Intencion(tipo="categoria", valor=0, objeto="cascara de platano").
2. **Escuchar** (`Voz.escuchar()`): push-to-talk. Graba unos segundos del micrófono y Vosk los convierte en texto
   usando una GRAMÁTICA RESTRINGIDA según el estado: solo puede "oír" las palabras útiles en ese momento.
   Así el modelo pequeño (`vosk-model-small-es`) se equivoca mucho menos que con vocabulario libre.

El vocabulario vive en `data/keywords.json` (editable sin tocar código).
Palabras que el modelo de Vosk NO conoce (se ignoran al escuchar, pero sí sirven al simular con texto):
unicel, blíster, tetrapak, popote.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger("voz")

TASA_VOSK = 16000
CONTEXTOS = ("menu", "revision", "adivinanza")
NOMBRE_MODELO = "vosk-model-small-es"


# =============================================================================
# 1. Texto → intención (lógica pura)
# =============================================================================
def quitar_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def singular(palabra: str) -> str:
    """Singularización básica del español: latas → lata, papeles → papel, lápices → lápiz, envases → envase."""
    if len(palabra) <= 3:
        return palabra
    if palabra.endswith("ces"):
        return palabra[:-3] + "z"
    if palabra.endswith("es") and palabra[-3] in "lrndj":
        return palabra[:-2]
    if palabra.endswith("s"):
        return palabra[:-1]
    return palabra


def normalizar_texto(texto: str) -> list[str]:
    """Minúsculas, sin acentos, sin signos y en singular. Devuelve la lista de palabras."""
    limpio = re.sub(r"[^a-z0-9ñ ]+", " ", quitar_acentos(texto.lower().replace("ñ", "\0")).replace("\0", "ñ"))
    return [singular(p) for p in limpio.split()]


@dataclass(frozen=True)
class Intencion:
    tipo: str               # "modo" | "categoria" | "desconocido" | "vacio"
    valor: Any = None       # modo ("ia" | "adivina" | "menu") o categoría (0, 1, 2)
    objeto: str | None = None  # frase reconocida, normalizada (ej. "cascara de platano")
    texto: str = ""         # todo lo que se entendió, normalizado

    def a_dict(self) -> dict[str, Any]:
        return {"tipo": self.tipo, "valor": self.valor, "objeto": self.objeto, "texto": self.texto}


class Vocabulario:
    """Lee `keywords.json` y busca la frase MÁS LARGA que aparezca en lo que se dijo."""

    def __init__(self, datos: dict[str, Any]) -> None:
        self.objetos = {k: int(v) for k, v in datos.get("objetos", {}).items()}
        self.categorias = {k: int(v) for k, v in datos.get("categorias", {}).items()}
        self.menu = dict(datos.get("menu", {}))
        self.relleno = list(datos.get("relleno", []))
        # Palabras que el modelo de Vosk no conoce: sirven al simular con texto, pero no van en la gramática
        self.fuera_de_vosk = {normalizar_texto(p)[0] for p in datos.get("fuera_de_vosk", []) if normalizar_texto(p)}
        for valor in [*self.objetos.values(), *self.categorias.values()]:
            if valor not in (0, 1, 2):
                raise ValueError(f"keywords.json: categoría inválida {valor} (debe ser 0, 1 o 2)")
        for valor in self.menu.values():
            if valor not in ("ia", "adivina", "menu"):
                raise ValueError(f"keywords.json: modo inválido {valor!r}")

    @classmethod
    def desde_archivo(cls, ruta: Path) -> "Vocabulario":
        return cls(json.loads(Path(ruta).read_text(encoding="utf-8")))

    @staticmethod
    def _buscar(palabras: list[str], frases: dict[str, Any]) -> tuple[str, Any] | None:
        """La frase más larga (en palabras) que aparece completa y seguida dentro de `palabras`."""
        mejor: tuple[int, str, Any] | None = None
        for frase, valor in frases.items():
            clave = normalizar_texto(frase)
            n = len(clave)
            if n == 0 or (mejor and n <= mejor[0]):
                continue
            if any(palabras[i:i + n] == clave for i in range(len(palabras) - n + 1)):
                mejor = (n, " ".join(clave), valor)
        return (mejor[1], mejor[2]) if mejor else None

    def interpretar(self, texto: str, contexto: str) -> Intencion:
        """Qué quiso decir la persona, según el estado en que está el sistema."""
        if contexto not in CONTEXTOS:
            raise ValueError(f"contexto desconocido: {contexto}")
        palabras = normalizar_texto(texto)
        dicho = " ".join(palabras)
        if not palabras:
            return Intencion("vacio", texto=dicho)
        if contexto == "menu":
            hallado = self._buscar(palabras, self.menu)
            if hallado:
                return Intencion("modo", hallado[1], hallado[0], dicho)
        if contexto == "adivinanza":  # en el juego solo cuentan las categorías, nunca los objetos
            hallado = self._buscar(palabras, self.categorias)
            return Intencion("categoria", hallado[1], hallado[0], dicho) if hallado else Intencion("desconocido", texto=dicho)
        # "menu" (pregunta directa: ¿dónde tiro…?) y "revision" (¿qué es?): objetos o categoría dicha directo
        objeto = self._buscar(palabras, self.objetos)
        categoria = self._buscar(palabras, self.categorias)
        if categoria and (not objeto or len(categoria[0].split()) >= len(objeto[0].split())):
            return Intencion("categoria", categoria[1], categoria[0], dicho)
        if objeto:
            return Intencion("categoria", objeto[1], objeto[0], dicho)
        return Intencion("desconocido", texto=dicho)

    def gramatica(self, contexto: str) -> list[str]:
        """Frases que Vosk puede reconocer en cada estado (gramática restringida, §15)."""
        if contexto == "adivinanza":
            frases = list(self.categorias)
        elif contexto == "menu":
            frases = [*self.menu, *self.objetos, *self.categorias, *self.relleno]
        else:
            frases = [*self.objetos, *self.categorias, *self.relleno]
        utiles = {f for f in frases if not set(normalizar_texto(f)) & self.fuera_de_vosk}
        return sorted(utiles) + ["[unk]"]


# =============================================================================
# 2. Micrófono + Vosk (push-to-talk)
# =============================================================================
class ErrorVoz(Exception):
    """No se pudo escuchar: sin micrófono, sin modelo o error de audio."""


class Voz:
    def __init__(self, ajustes=None, config=None, vocabulario: Vocabulario | None = None) -> None:
        self._config = config
        self._modelo = None
        self._candado = threading.Lock()
        self.escuchando = False
        self.motivo: str | None = None
        self.vocabulario = vocabulario
        if self.vocabulario is None and ajustes is not None:
            try:
                self.vocabulario = Vocabulario.desde_archivo(ajustes.dir_datos / "keywords.json")
            except (OSError, ValueError) as error:
                self.motivo = f"No se pudo leer keywords.json: {error}"
        self._ruta_modelo = (ajustes.dir_modelos / NOMBRE_MODELO) if ajustes is not None else None
        self.disponible = self._revisar()

    def _revisar(self) -> bool:
        if self.vocabulario is None:
            self.motivo = self.motivo or "Sin vocabulario"
            return False
        if self._ruta_modelo is None or not (self._ruta_modelo / "am").is_dir():
            self.motivo = f"Falta el modelo de Vosk en {self._ruta_modelo}"
            return False
        try:
            import sounddevice  # noqa: F401
            import vosk  # noqa: F401
        except Exception as error:  # noqa: BLE001
            self.motivo = f"Falta una biblioteca de voz: {error}"
            return False
        self.motivo = None
        return True

    def estado(self) -> dict[str, Any]:
        return {"disponible": self.disponible, "escuchando": self.escuchando, "motivo": self.motivo,
                "microfono": (self._config.get("microfono") if self._config else "") or "predeterminado"}

    def interpretar(self, texto: str, contexto: str) -> Intencion:
        if self.vocabulario is None:
            raise ErrorVoz(self.motivo or "Sin vocabulario")
        return self.vocabulario.interpretar(texto, contexto)

    def calentar(self) -> None:
        """Carga el modelo de Vosk (~1–2 s) antes de la primera vez que se habla."""
        if self.disponible and self._modelo is None:
            import vosk

            vosk.SetLogLevel(-1)
            self._modelo = vosk.Model(str(self._ruta_modelo))

    @staticmethod
    def _dispositivo(preferido: Any) -> Any:
        """'' → micrófono predeterminado; número → índice; texto → primer micrófono cuyo nombre lo contenga."""
        import sounddevice as sd

        if preferido in (None, ""):
            return None
        if isinstance(preferido, int) or str(preferido).isdigit():
            return int(preferido)
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0 and str(preferido).lower() in d["name"].lower():
                return i
        raise ErrorVoz(f"No hay un micrófono que se llame '{preferido}'")

    def escuchar(self, contexto: str, segundos: float) -> str:
        """BLOQUEANTE (se llama en otro hilo): graba `segundos` y devuelve el texto reconocido."""
        if not self.disponible:
            raise ErrorVoz(self.motivo or "Voz no disponible")
        if not self._candado.acquire(blocking=False):
            raise ErrorVoz("Ya estoy escuchando")
        self.escuchando = True
        try:
            import sounddevice as sd
            import vosk

            self.calentar()
            dispositivo = self._dispositivo(self._config.get("microfono") if self._config else "")
            tasa = int(sd.query_devices(dispositivo, "input")["default_samplerate"])
            audio = sd.rec(int(segundos * tasa), samplerate=tasa, channels=1, dtype="int16", device=dispositivo)
            sd.wait()
            gramatica = json.dumps(self.vocabulario.gramatica(contexto), ensure_ascii=False)
            reconocedor = vosk.KaldiRecognizer(self._modelo, tasa, gramatica)
            reconocedor.AcceptWaveform(audio.tobytes())
            texto = json.loads(reconocedor.FinalResult()).get("text", "")
            texto = " ".join(p for p in texto.split() if p != "[unk]")
            log.info("Voz (%s): %r", contexto, texto)
            return texto
        except ErrorVoz:
            raise
        except Exception as error:  # noqa: BLE001 — frontera con el hardware de audio
            raise ErrorVoz(f"Error de audio: {error}") from error
        finally:
            self.escuchando = False
            self._candado.release()
