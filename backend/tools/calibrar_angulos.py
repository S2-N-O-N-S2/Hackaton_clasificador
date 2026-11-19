"""
calibrar_angulos.py — Calibra el ángulo del servo que deja cada bote bajo el punto de caída (§5.3).

El ángulo correcto NO es la posición del bote en el disco: θi = D − φi, y en la práctica se ajusta a ojo.
Esta herramienta mueve el disco grado por grado y guarda el ángulo bueno de cada bote en:
  - la configuración del backend (tabla `config`), y
  - la EEPROM del Arduino (el backend le manda CAL:<id>:<ángulo>).

Requisito: el backend corriendo (en modo real o en simulación) y en MENU, OPERADOR o ERROR:
    cd backend; .\\.venv\\Scripts\\Activate.ps1; uvicorn app.main:app --port 8000

Uso (en otra terminal, desde backend/):
    python tools\\calibrar_angulos.py
    python tools\\calibrar_angulos.py --url http://localhost:8000

Teclas:
    ← / →   mover 1°          ↑ / ↓   mover 5°
    1 2 3   GUARDAR el ángulo actual para Orgánica / Inorgánica / Peligroso
    O I P   ir al ángulo guardado de Orgánica / Inorgánica / Peligroso (para verificar)
    H       HOME              D       abrir la trampilla (probar la caída)
    Q       salir

Consejo: pon un residuo en la bandeja, presiona D y observa si cae en el CENTRO de la boca del bote.
Si cae cargado a un lado, ajusta 1° y vuelve a probar.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

NOMBRES = {0: "Orgánica (verde)", 1: "Inorgánica (azul)", 2: "Peligroso (gris)"}

# Teclas especiales de msvcrt en Windows: llegan como dos bytes (b'\xe0' o b'\x00' + código)
FLECHAS = {b"K": "izquierda", b"M": "derecha", b"H": "arriba", b"P": "abajo"}


class ErrorApi(Exception):
    pass


# ---------------------------------------------------------------------------- cliente de la API
def enviar_http(base: str) -> Callable[[str, str, dict | None], dict]:
    """Devuelve una función enviar(método, ruta, cuerpo) que habla con el backend por HTTP."""
    def enviar(metodo: str, ruta: str, cuerpo: dict | None = None) -> dict:
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        peticion = urllib.request.Request(base.rstrip("/") + ruta, data=datos, method=metodo,
                                          headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(peticion, timeout=15) as respuesta:
                return json.loads(respuesta.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            try:
                detalle = json.loads(error.read().decode("utf-8")).get("detail")
            except Exception:  # noqa: BLE001
                detalle = str(error)
            raise ErrorApi(f"{error.code}: {detalle}") from None
        except urllib.error.URLError as error:
            raise ErrorApi(f"No se pudo conectar con el backend en {base} ({error.reason})") from None
    return enviar


@dataclass
class Calibrador:
    """Lógica de la calibración, separada del teclado para poder probarla."""

    enviar: Callable[[str, str, dict | None], dict]
    angulo: int = 90
    guardados: dict[int, int] = field(default_factory=dict)

    def cargar(self) -> None:
        estado = self.enviar("GET", "/api/estado", None)
        if estado["estado"] not in ("MENU", "OPERADOR", "ERROR"):
            raise ErrorApi(f"El sistema está en {estado['estado']}: esperen a que vuelva al MENU")
        if not estado["serial"]["conectado"]:
            raise ErrorApi("El backend no tiene conexión con el Arduino")
        config = self.enviar("GET", "/api/config", None)["valores"]
        self.guardados = {int(k): int(v) for k, v in config["angulos"].items()}
        self.angulo = int(config.get("angulo_home", 90))

    def mover_a(self, grados: int) -> str:
        grados = max(0, min(180, grados))
        respuesta = self.enviar("POST", "/api/manual/ang", {"grados": grados})
        self.angulo = grados
        return respuesta["respuesta_arduino"]

    def mover(self, delta: int) -> str:
        return self.mover_a(self.angulo + delta)

    def guardar(self, categoria: int) -> dict[str, int]:
        """Guarda el ángulo actual para la categoría: config del backend + CAL a la EEPROM del Arduino."""
        respuesta = self.enviar("PUT", "/api/config", {"angulos": {str(categoria): self.angulo}})
        self.guardados = {int(k): int(v) for k, v in respuesta["valores"]["angulos"].items()}
        return respuesta["valores"]["angulos"]

    def ir_a_guardado(self, categoria: int) -> str:
        return self.mover_a(self.guardados[categoria])

    def home(self) -> str:
        respuesta = self.enviar("POST", "/api/manual/home", {})
        return respuesta["respuesta_arduino"]

    def soltar(self) -> str:
        return self.enviar("POST", "/api/manual/drop", {})["respuesta_arduino"]

    def aplicar(self, tecla: str) -> str | None:
        """Ejecuta una tecla. Devuelve el mensaje a mostrar, o None para salir."""
        acciones = {
            "izquierda": lambda: self.mover(-1), "derecha": lambda: self.mover(1),
            "arriba": lambda: self.mover(5), "abajo": lambda: self.mover(-5),
            "h": self.home, "d": self.soltar,
        }
        if tecla == "q":
            return None
        if tecla in acciones:
            return f"Ángulo {self.angulo:3d}° → {acciones[tecla]()}"
        if tecla in ("1", "2", "3"):
            categoria = int(tecla) - 1
            self.guardar(categoria)
            return f"GUARDADO {NOMBRES[categoria]} = {self.angulo}° (config + EEPROM)"
        if tecla in ("o", "i", "p"):
            categoria = {"o": 0, "i": 1, "p": 2}[tecla]
            return f"Ir a {NOMBRES[categoria]} ({self.guardados[categoria]}°) → {self.ir_a_guardado(categoria)}"
        return "Tecla sin función (Q para salir)"


# ---------------------------------------------------------------------------- teclado (Windows)
def leer_tecla() -> str:
    import msvcrt

    tecla = msvcrt.getch()
    if tecla in (b"\xe0", b"\x00"):
        return FLECHAS.get(msvcrt.getch(), "")
    return tecla.decode("latin-1").lower()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Calibra el ángulo de cada bote.")
    parser.add_argument("--url", default="http://localhost:8000", help="dirección del backend")
    args = parser.parse_args()

    calibrador = Calibrador(enviar_http(args.url))
    try:
        calibrador.cargar()
    except ErrorApi as error:
        print(f"No se puede calibrar: {error}")
        return 1
    print(__doc__.split("Teclas:")[1].split("Consejo")[0])
    print("Ángulos guardados ahora:", {NOMBRES[c]: g for c, g in calibrador.guardados.items()})
    print(f"Ángulo inicial: {calibrador.angulo}° (no se mueve hasta que presiones una tecla)\n")
    while True:
        tecla = leer_tecla()
        try:
            mensaje = calibrador.aplicar(tecla)
        except ErrorApi as error:
            mensaje = f"ERROR: {error}"
        if mensaje is None:
            break
        print(mensaje)
    print("\nÁngulos finales:", {NOMBRES[c]: g for c, g in calibrador.guardados.items()})
    print("Anótenlos en docs/resultados/ciclos_reales.md (sección Calibración).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
