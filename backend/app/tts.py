"""
tts.py — El sistema HABLA (texto a voz, offline).

Cómo funciona (sin dependencias nuevas ni internet):
  1. Un proceso de PowerShell que se queda abierto GENERA el audio con las voces de Windows:
     primero intenta las voces modernas (OneCore: "Microsoft Laura", "Microsoft Pablo", "Microsoft Helena",
     español de España) y, si no puede, la voz clásica (System.Speech). Escribe un .wav temporal.
  2. Python lee el .wav, lo NORMALIZA (lo lleva al volumen máximo sin distorsión), le aplica el volumen
     configurado (`voz_volumen`, 10–300 %) y lo reproduce con sounddevice por las bocinas de la laptop.

Si algo falla (otro sistema operativo, sin voces en español), el sistema sigue funcionando en silencio:
la LCD y el panel muestran lo mismo.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import threading
import wave
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("tts")

# Script de PowerShell. Protocolo por líneas (UTF-8):
#   al arrancar imprime  VOCES:<voz1>|<voz2>|...    (voces en español)
#   recibe               <voz>\t<velocidad>\t<ruta.wav>\t<texto>
#   responde             OK   o   ERR:<mensaje>
SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [Text.Encoding]::UTF8
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$moderno = $false
try {
  Add-Type -AssemblyName System.Runtime.WindowsRuntime
  $null = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]
  $asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
      $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
      $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0].MakeGenericMethod(
      [Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
  $wr = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
  $vocesWr = @([Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | Where-Object { $_.Language -like 'es*' })
  if ($vocesWr.Count -gt 0) { $moderno = $true }
} catch { $moderno = $false }
Add-Type -AssemblyName System.Speech
$sapi = New-Object System.Speech.Synthesis.SpeechSynthesizer
$vocesSapi = @($sapi.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'es*' } | ForEach-Object { $_.VoiceInfo.Name })
if ($moderno) { [Console]::Out.WriteLine('VOCES:' + (($vocesWr | ForEach-Object { $_.DisplayName }) -join '|')) }
else { [Console]::Out.WriteLine('VOCES:' + ($vocesSapi -join '|')) }
[Console]::Out.Flush()
while ($null -ne ($l = [Console]::In.ReadLine())) {
  try {
    $p = $l.Split("`t", 4); $nombre = $p[0]; $vel = [double]::Parse($p[1], [Globalization.CultureInfo]::InvariantCulture)
    $ruta = $p[2]; $texto = $p[3]
    if ($moderno) {
      $v = $vocesWr | Where-Object { $_.DisplayName -like "*$nombre*" } | Select-Object -First 1
      if (-not $v) { $v = $vocesWr[0] }
      $wr.Voice = $v
      try { $wr.Options.SpeakingRate = $vel } catch { }
      $t = $asTask.Invoke($null, @($wr.SynthesizeTextToStreamAsync($texto))); $t.Wait(-1) | Out-Null
      $origen = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($t.Result)
      $destino = [System.IO.File]::Create($ruta); $origen.CopyTo($destino); $destino.Close(); $origen.Close()
    } else {
      $n = $vocesSapi | Where-Object { $_ -like "*$nombre*" } | Select-Object -First 1
      if ($n) { $sapi.SelectVoice($n) } elseif ($vocesSapi.Count -gt 0) { $sapi.SelectVoice($vocesSapi[0]) }
      $sapi.Rate = [int][Math]::Max(-10, [Math]::Min(10, ($vel - 1) * 10))
      $sapi.SetOutputToWaveFile($ruta); $sapi.Speak($texto); $sapi.SetOutputToNull()
    }
    [Console]::Out.WriteLine('OK')
  } catch { [Console]::Out.WriteLine('ERR:' + $_.Exception.Message) }
  [Console]::Out.Flush()
}
"""


def preparar_audio(datos, volumen: float):
    """Normaliza el audio al máximo sin distorsión y aplica el volumen (1.0 = 100 %).
    Por encima de 100 % se comprime suavemente (tanh) para que suene más fuerte sin "tronar"."""
    import numpy as np

    x = datos.astype(np.float32)
    pico = float(np.abs(x).max()) if x.size else 0.0
    if pico == 0:
        return x
    x = x / pico * 0.98
    if volumen <= 1.0:
        return x * volumen
    return np.tanh(x * volumen) / np.tanh(volumen) * 0.98


class Locutor:
    def __init__(self, activo: bool = True, config: Callable[[str], Any] | None = None) -> None:
        self.activo = activo and os.name == "nt" and shutil.which("powershell") is not None
        self._config = config or (lambda clave: {"voz_nombre": "Laura", "voz_volumen": 150,
                                                 "voz_velocidad": 1.0}[clave])
        self.voces: list[str] = []
        self.nombre_voz: str | None = None
        self.motivo: str | None = None if self.activo else "Solo disponible en Windows con PowerShell"
        self._proceso: subprocess.Popen | None = None
        self._candado = threading.Lock()
        self._carpeta = Path(tempfile.gettempdir()) / "clasificador_voz"

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
            primera = self._leer()
            self.voces = [v for v in primera.removeprefix("VOCES:").split("|") if v] if primera.startswith("VOCES:") else []
            if not self.voces:
                self.motivo = "Windows no tiene una voz en español instalada"
                self.cerrar()
                return False
            self._carpeta.mkdir(parents=True, exist_ok=True)
            log.info("Locutor listo. Voces: %s", ", ".join(self.voces))
            return True
        except Exception as error:  # noqa: BLE001 — sin voz, el sistema sigue en silencio
            self.motivo = f"No se pudo iniciar la voz de Windows: {error}"
            self._proceso = None
            return False

    def _leer(self) -> str:
        return self._proceso.stdout.readline().decode("utf-8", "replace").strip()

    def _elegir_voz(self) -> str:
        preferida = str(self._config("voz_nombre") or "").lower()
        for voz in self.voces:
            if preferida and preferida in voz.lower():
                return voz
        return self.voces[0]

    def calentar(self) -> None:
        if self.activo:
            with self._candado:
                self._arrancar()

    def sintetizar(self, texto: str) -> Path:
        """Genera el .wav con la voz configurada (BLOQUEANTE, ~0.3–1 s)."""
        voz = self._elegir_voz()
        velocidad = float(self._config("voz_velocidad"))
        ruta = self._carpeta / f"frase_{threading.get_ident()}.wav"
        texto = " ".join(texto.split())
        self._proceso.stdin.write(f"{voz}\t{velocidad:.2f}\t{ruta}\t{texto}\n".encode("utf-8"))
        self._proceso.stdin.flush()
        respuesta = self._leer()
        if respuesta != "OK":
            raise RuntimeError(respuesta.removeprefix("ERR:") or "sin respuesta de la voz de Windows")
        self.nombre_voz = voz
        return ruta

    def decir(self, texto: str, interrumpir: bool = True) -> bool:
        """Dice `texto` por las bocinas. BLOQUEANTE mientras genera el audio (no mientras suena):
        llamarlo en otro hilo. Una frase nueva corta la anterior (interrumpir=True)."""
        if not self.activo or not texto:
            return False
        import numpy as np
        import sounddevice as sd

        with self._candado:
            if not self._arrancar():
                return False
            try:
                ruta = self.sintetizar(texto)
                with wave.open(str(ruta), "rb") as w:
                    tasa, canales = w.getframerate(), w.getnchannels()
                    datos = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
                if canales > 1:
                    datos = datos.reshape(-1, canales)
                audio = preparar_audio(datos, float(self._config("voz_volumen")) / 100)
                if interrumpir:
                    sd.stop()
                sd.play(audio, tasa)
                return True
            except Exception as error:  # noqa: BLE001 — frontera con el audio de Windows
                log.warning("No se pudo hablar: %s", error)
                if self._proceso and self._proceso.poll() is not None:
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
