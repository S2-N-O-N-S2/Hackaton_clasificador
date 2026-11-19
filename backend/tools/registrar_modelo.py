"""
registrar_modelo.py — Activa en ESTA laptop un modelo que ya viene entrenado (por ejemplo, bajado con git pull).

Por qué hace falta: el backend usa la versión marcada como activa en la tabla `modelos` de la base de datos
(app/model.py, cargar_modelo). La carpeta backend/models/v<N>/ viaja por Git, pero la base de datos es local
(*.db no se sube). Este script registra esa carpeta en la base de datos de esta laptop y la marca como activa,
sin reentrenar y sin necesitar las fotos.

Uso (desde backend/, con el entorno virtual activo):
    python tools\\registrar_modelo.py --listar          # versiones en models/ y en la base de datos
    python tools\\registrar_modelo.py v1                # registra v1 y la activa
    python tools\\registrar_modelo.py v1 --no-activar   # solo la registra

Después hay que reiniciar el backend (carga el modelo al arrancar).
Con SIMULACION=1 el backend usa un modelo simulado, así que el registro solo sirve en modo real.

Generado con Claude Code (Anthropic) para la Persona B; ver docs/recursos_externos.md.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import cargar_ajustes  # noqa: E402
from app.db import BaseDatos  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def leer_json(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def revisar_carpeta(carpeta: Path) -> dict:
    """Comprueba que la versión esté completa y que el clasificador se pueda abrir. Devuelve sus métricas."""
    if not carpeta.is_dir():
        raise SystemExit(f"ERROR: no existe {carpeta}. ¿Hiciste git pull? (python tools\\registrar_modelo.py --listar)")
    for archivo in ("labels.json", "metricas.json"):
        if not (carpeta / archivo).exists():
            raise SystemExit(f"ERROR: falta {carpeta / archivo}: la versión está incompleta")
    etiquetas = leer_json(carpeta / "labels.json")
    cabeza = etiquetas.get("cabeza")
    if cabeza == "logistica":
        import joblib

        with warnings.catch_warnings(record=True) as avisos:
            warnings.simplefilter("always")
            try:
                joblib.load(carpeta / "modelo.joblib")
            except Exception as error:  # noqa: BLE001 — se explica al usuario y no se registra
                raise SystemExit(f"ERROR: no se pudo abrir modelo.joblib ({error}). "
                                 f"Revisa que scikit-learn sea la versión de requirements.lock.txt.") from error
        for aviso in avisos:
            if "version" in str(aviso.message).lower():
                print(f"AVISO: {aviso.message}\n  Instala la versión de scikit-learn de requirements.lock.txt "
                      f"o reentrena en esta laptop (python -m training.train).")
    elif cabeza == "densa":
        if not (carpeta / "cabeza.keras").exists():
            raise SystemExit(f"ERROR: falta {carpeta / 'cabeza.keras'}")
    else:
        raise SystemExit(f"ERROR: cabeza desconocida en labels.json: {cabeza!r}")
    return leer_json(carpeta / "metricas.json")


def listar(dir_modelos: Path, db: BaseDatos) -> None:
    en_db = {f["version"]: f for f in db.consultar(
        "SELECT version, fecha, n_imagenes, precision_val, activo FROM modelos ORDER BY fecha")}
    carpetas = sorted(p.name for p in dir_modelos.glob("v*") if p.is_dir() and p.name[1:].isdigit())
    print(f"{'Versión':<9}{'Carpeta':<9}{'En la BD':<10}{'Activa':<8}Precisión val.")
    for version in sorted(set(carpetas) | set(en_db), key=lambda v: int(v[1:]) if v[1:].isdigit() else 0):
        fila = en_db.get(version)
        precision = fila["precision_val"] if fila else None
        if precision is None and version in carpetas:
            precision = leer_json(dir_modelos / version / "metricas.json").get("validacion", {}).get("precision")
        print(f"{version:<9}{'sí' if version in carpetas else 'NO':<9}{'sí' if fila else 'no':<10}"
              f"{'✔' if fila and fila['activo'] else '':<8}{'—' if precision is None else f'{precision:.1%}'}")


def registrar(version: str, dir_modelos: Path, db: BaseDatos, activar: bool) -> None:
    metricas = revisar_carpeta(dir_modelos / version)
    fecha = metricas.get("fecha")
    n_imagenes = metricas.get("n_imagenes")
    precision = metricas.get("validacion", {}).get("precision")
    if db.uno("SELECT version FROM modelos WHERE version = ?", (version,)):
        db.ejecutar("UPDATE modelos SET fecha = ?, n_imagenes = ?, precision_val = ? WHERE version = ?",
                    (fecha, n_imagenes, precision, version))
        print(f"{version} ya estaba registrada: datos actualizados desde metricas.json")
    else:
        db.ejecutar("INSERT INTO modelos(version, fecha, n_imagenes, precision_val, activo) VALUES (?, ?, ?, ?, 0)",
                    (version, fecha, n_imagenes, precision))
        print(f"{version} registrada")
    if activar:
        db.ejecutar("UPDATE modelos SET activo = CASE WHEN version = ? THEN 1 ELSE 0 END", (version,))
        print(f"{version} es ahora el modelo ACTIVO")
    db.registrar_evento("info", "modelo",
                        f"Registrado {version} desde la carpeta (sin reentrenar), precisión val {precision}"
                        + (" — activado" if activar else ""))
    print(f"  Entrenado: {fecha} · {n_imagenes} fotos · validación "
          f"{'—' if precision is None else f'{precision:.1%}'}")
    nota = metricas.get("nota")
    if nota:
        print(f"  Nota: {nota}")
    print("Reinicia el backend para que lo cargue.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Registra en la base de datos local un modelo ya entrenado.")
    parser.add_argument("version", nargs="?", help="carpeta de backend/models, por ejemplo v1")
    parser.add_argument("--no-activar", action="store_true", help="solo registrar, sin activarlo")
    parser.add_argument("--listar", action="store_true", help="mostrar versiones en models/ y en la base de datos")
    args = parser.parse_args()

    ajustes = cargar_ajustes()
    db = BaseDatos(ajustes.ruta_db)
    print(f"Base de datos: {ajustes.ruta_db}")
    if ajustes.simulacion:
        print("AVISO: SIMULACION=1 → esta es la base de simulación y el backend usará un modelo simulado.")
    if args.listar or not args.version:
        listar(ajustes.dir_modelos, db)
        return 0
    registrar(args.version, ajustes.dir_modelos, db, activar=not args.no_activar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
