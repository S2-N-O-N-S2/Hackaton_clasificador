"""
tts.py — El sistema HABLA (texto a voz, offline).

Usa el sintetizador que ya trae Windows (System.Speech, voz en español "Microsoft Helena"), así que NO hay
dependencias nuevas ni internet. Se abre UN proceso de PowerShell que se queda escuchando: Python le manda
una frase por línea y Windows la dice por las bocinas de la laptop, sin bloquear el ciclo.

Si algo falla (otro sistema operativo, sin voz en español, sin PowerShell), el sistema sigue funcionando
en silencio: la LCD y el panel muestran lo mismo.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading

log = logging.getLogger("tts")

# Script de PowerShell: elige la primera voz en español y lee frases de la entrada estándar (UTF-8).
SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [Text.Encoding]::UTF8
[Console]::OutputEncoding = [Text.Encoding]::UTF8
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$v = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'es*' } | Select-Object -First 1
if ($v) { $s.SelectVoice($v.VoiceInfo.Name); [Console]::Out.WriteLine('LISTO:' + $v.VoiceInfo.Name) }
else { [Console]::Out.WriteLine('SIN_VOZ') }
[Console]::Out.Flush()
while ($null -ne ($l = [Console]::In.ReadLine())) {
  if ($l -eq '__CALLA__') { $s.SpeakAsyncCancelAll() }
  elseif ($l.StartsWith('__VEL__')) { $s.Rate = [int]$l.Substring(7) }
  elseif ($l.Trim()) { $s.SpeakAsync($l) | Out-Null }
}
"""


class Locutor:
    def __init__(self, activo: bool = True, velocidad: int = 0) -> None:
        self.activo = activo and os.name == "nt" and shutil.which("powershell") is not None
        self.velocidad = velocidad  # -10 (lento) a 10 (rápido)
        self.nombre_voz: str | None = None
        self.motivo: str | None = None if self.activo else "Solo disponible en Windows con PowerShell"
        self._proceso: subprocess.Popen | None = None
        self._candado = threading.Lock()

    @property
    def disponible(self) -> bool:
        return self.activo and self.motivo is None

    def _arrancar(self) -> bool:
        if self._proceso and self._proceso.poll() is None:
            return True
        try:
            self._proceso = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", SCRIPT],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            primera = self._proceso.stdout.readline().decode("utf-8", "replace").strip()
            if not primera.startswith("LISTO:"):
                self.motivo = "Windows no tiene una voz en español instalada"
                self.cerrar()
                return False
            self.nombre_voz = primera[len("LISTO:"):]
            self._enviar(f"__VEL__{self.velocidad}")
            log.info("Locutor listo con la voz %s", self.nombre_voz)
            return True
        except Exception as error:  # noqa: BLE001 — sin voz, el sistema sigue en silencio
            self.motivo = f"No se pudo iniciar la voz de Windows: {error}"
            self._proceso = None
            return False

    def _enviar(self, linea: str) -> None:
        self._proceso.stdin.write((linea.replace("\n", " ") + "\n").encode("utf-8"))
        self._proceso.stdin.flush()

    def calentar(self) -> None:
        if self.activo:
            with self._candado:
                self._arrancar()

    def decir(self, texto: str, interrumpir: bool = False) -> bool:
        """Dice `texto` sin esperar a que termine. interrumpir=True calla lo que estuviera diciendo antes."""
        if not self.activo or not texto:
            return False
        with self._candado:
            if not self._arrancar():
                return False
            try:
                if interrumpir:
                    self._enviar("__CALLA__")
                self._enviar(texto)
                return True
            except OSError as error:
                log.warning("La voz de Windows se cerró: %s", error)
                self._proceso = None
                return False

    def cerrar(self) -> None:
        if self._proceso:
            try:
                self._proceso.stdin.close()
                self._proceso.terminate()
            except Exception:  # noqa: BLE001
                pass
            self._proceso = None


# ---------------------------------------------------------------------------
# Frases (con acentos: aquí no hay límite de la LCD)
# ---------------------------------------------------------------------------
NOMBRES = {0: "orgánica", 1: "inorgánica", 2: "peligroso"}
BOTES = {0: "verde", 1: "azul", 2: "gris"}


def frase_resultado(categoria_id: int, confianza: float | None, origen: str) -> str:
    """Lo que dice al soltar el residuo: la clasificación y el bote."""
    bote = f"Va en el bote {BOTES[categoria_id]}."
    if origen == "camara" and confianza is not None:
        return f"Es {NOMBRES[categoria_id]}, con {round(confianza * 100)} por ciento de certeza. {bote}"
    return f"Listo: {NOMBRES[categoria_id]}. {bote}"


def frase_revision(motivo: str | None) -> str:
    if motivo == "conflicto_voz":
        inicio = "Lo que me dijiste no coincide con lo que veo."
    elif motivo == "riesgo_peligroso":
        inicio = "Podría ser peligroso y no quiero equivocarme."
    elif motivo == "sin_modelo":
        inicio = "La inteligencia artificial no está disponible."
    else:
        inicio = "No estoy seguro."
    return f"{inicio} ¿Qué es? Presiona uno, dos o tres, o presiona A y dímelo."


def frase_objeto(objeto: str | None, categoria_id: int) -> str:
    sujeto = f"{objeto.capitalize()}: " if objeto else ""
    return f"{sujeto}es {NOMBRES[categoria_id]}. Va en el bote {BOTES[categoria_id]}."


FRASE_NO_RECONOCIDO = "No reconocí el objeto. Presiona A e intenta de nuevo."
FRASE_PENDIENTE = "Nadie respondió. Un operador retirará el residuo."
FRASE_FALLA = "Falla del sistema. Me detuve en modo seguro. Avise al operador."
FRASES_MODO = {"ia": "Modo inteligencia artificial. Coloca el residuo.",
               "adivina": "Modo adivina. Coloca el residuo y adivina en qué bote va.",
               "menu": "Menú principal."}
