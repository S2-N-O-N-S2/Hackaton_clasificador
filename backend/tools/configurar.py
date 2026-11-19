"""
configurar.py — Ver o cambiar la configuración guardada (tabla `config`) SIN levantar el servidor.

Uso (desde backend/, con el entorno virtual activo):
    python tools/configurar.py --ver
    python tools/configurar.py indice_camara 1
    python tools/configurar.py indice_camara http://192.168.1.50:4747/video
    python tools/configurar.py roi "[0.2, 0.1, 0.6, 0.8]"
    python tools/configurar.py umbral_general 0.7

Valida igual que el panel (PUT /api/config). Si el backend está corriendo, reinícienlo para que tome
`indice_camara` o `puerto_serial`. Usa la base de datos real; con SIMULACION=1 usa la de simulación.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Configuracion, cargar_ajustes  # noqa: E402
from app.db import BaseDatos  # noqa: E402


def interpretar(texto: str):
    """'1' → 1, '0.7' → 0.7, '[0.2, 0.1, 0.6, 0.8]' → lista; cualquier otra cosa se deja como texto."""
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return texto


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    ajustes = cargar_ajustes()
    config = Configuracion(BaseDatos(ajustes.ruta_db))
    if not args or args[0] in ("--ver", "-v"):
        print(f"Base de datos: {ajustes.ruta_db}")
        for clave, valor in config.todo().items():
            print(f"  {clave:22} = {json.dumps(valor, ensure_ascii=False)}")
        return 0
    if len(args) != 2:
        print(__doc__)
        return 1
    clave, valor = args
    try:
        nuevos = config.actualizar({clave: interpretar(valor)})
    except ValueError as error:
        print(f"No se guardó: {error}")
        return 1
    print(f"Guardado: {clave} = {json.dumps(nuevos[clave], ensure_ascii=False)}  (en {ajustes.ruta_db})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
