"""
db.py — Base de datos SQLite: esquema completo (especificación §16), datos iniciales y consultas comunes.

Se usa `sqlite3` de la biblioteca estándar. Una sola conexión protegida con un candado (lock),
suficiente para un prototipo con un solo proceso.

Inicializar a mano (crea las tablas si no existen):
    python -m app.db
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

ESQUEMA = """
-- Cada residuo que entra al sistema (un ciclo)
CREATE TABLE IF NOT EXISTS clasificaciones (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora       TEXT    NOT NULL,
    foto             TEXT,                       -- nombre del archivo en captures/
    modo             TEXT    NOT NULL CHECK (modo IN ('ia', 'adivina')),
    pred_id          INTEGER,                    -- clase ganadora de la IA (NULL si no hubo modelo)
    confianza        REAL,
    p_organica       REAL,
    p_inorganica     REAL,
    p_peligroso      REAL,
    final_id         INTEGER,                    -- categoría con la que se depositó (NULL = sin resolver)
    origen           TEXT    NOT NULL DEFAULT 'camara'
                     CHECK (origen IN ('camara', 'voz', 'manual', 'teclado', 'panel')),
    dudoso           INTEGER NOT NULL DEFAULT 0,
    motivo_dudoso    TEXT,                       -- confianza_baja | riesgo_peligroso | conflicto_voz | sin_modelo
    corregido        INTEGER NOT NULL DEFAULT 0,
    modelo_version   TEXT,
    tiempo_ciclo_ms  INTEGER,                    -- tiempo de MÁQUINA (sin la espera humana)
    drop_confirmado  INTEGER,                    -- 1 la trampilla abrió y cerró (DROP_OK; no hay sensor de caída), NULL no se soltó
    bote_id          INTEGER,
    tiempos_etapas   TEXT,                       -- JSON {estado: ms} para diagnosticar dónde se atora el ciclo
    simulado         INTEGER NOT NULL DEFAULT 0,
    estado           TEXT    NOT NULL DEFAULT 'en_proceso'
                     CHECK (estado IN ('en_proceso', 'registrado', 'pendiente', 'error'))
);
CREATE INDEX IF NOT EXISTS idx_clasif_fecha  ON clasificaciones(fecha_hora);
CREATE INDEX IF NOT EXISTS idx_clasif_dudoso ON clasificaciones(dudoso);

CREATE TABLE IF NOT EXISTS sesiones_juego (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo               TEXT    NOT NULL DEFAULT 'libre' CHECK (tipo IN ('libre', 'prueba_aprendizaje')),
    participante_alias TEXT,
    inicio             TEXT    NOT NULL,
    fin                TEXT,
    intentos           INTEGER NOT NULL DEFAULT 0,
    aciertos           INTEGER NOT NULL DEFAULT 0,
    mejor_racha        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS adivinanzas (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id            INTEGER REFERENCES sesiones_juego(id),
    clasificacion_id     INTEGER REFERENCES clasificaciones(id),
    residuo_prueba_id    INTEGER REFERENCES residuos_prueba(id),
    fecha_hora           TEXT    NOT NULL,
    numero_intento       INTEGER NOT NULL,
    ronda                INTEGER,
    respuesta_usuario    INTEGER,
    categoria_referencia INTEGER,
    fuente_referencia    TEXT CHECK (fuente_referencia IN ('ia', 'operador', 'etiqueta_real')),
    confianza_ia         REAL,
    nivel_certeza        TEXT CHECK (nivel_certeza IN ('verificada', 'alta', 'media', 'baja')),
    correcto             INTEGER,
    recalificada         INTEGER NOT NULL DEFAULT 0,
    medio                TEXT CHECK (medio IN ('teclado', 'voz', 'panel', 'sin_respuesta')),
    tiempo_respuesta_s   REAL,
    reporto_error_ia     INTEGER NOT NULL DEFAULT 0,
    explicacion_mostrada TEXT
);
CREATE INDEX IF NOT EXISTS idx_adiv_sesion ON adivinanzas(sesion_id);

CREATE TABLE IF NOT EXISTS botes (
    id                 INTEGER PRIMARY KEY,
    nombre             TEXT    NOT NULL,
    color              TEXT    NOT NULL,
    categoria_id       INTEGER NOT NULL,
    capacidad_piezas   INTEGER NOT NULL,
    capacidad_calibrada INTEGER NOT NULL DEFAULT 0,  -- 0 = valor provisional, falta medir (§13.2)
    piezas_actuales    INTEGER NOT NULL DEFAULT 0,
    no_confirmadas     INTEGER NOT NULL DEFAULT 0,   -- piezas sumadas con DROP_TIMEOUT
    umbral_aviso       REAL    NOT NULL DEFAULT 0.8,
    bloqueado          INTEGER NOT NULL DEFAULT 0,
    ultimo_vaciado     TEXT
);

CREATE TABLE IF NOT EXISTS vaciados (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    bote_id          INTEGER NOT NULL REFERENCES botes(id),
    fecha_hora       TEXT    NOT NULL,
    piezas_al_vaciar INTEGER NOT NULL,
    origen           TEXT    NOT NULL CHECK (origen IN ('panel', 'teclado'))
);

CREATE TABLE IF NOT EXISTS residuos_prueba (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre                 TEXT    NOT NULL,
    categoria_real         INTEGER NOT NULL CHECK (categoria_real IN (0, 1, 2)),
    simulado               INTEGER NOT NULL DEFAULT 1,  -- residuo peligroso simulado (§2)
    usado_en_entrenamiento INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pruebas (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    corrida            INTEGER NOT NULL,
    modo               TEXT    NOT NULL CHECK (modo IN ('manual', 'sistema')),
    residuo_id         INTEGER NOT NULL REFERENCES residuos_prueba(id),
    categoria_asignada INTEGER,
    correcto           INTEGER,
    tiempo_s           REAL,
    fecha_hora         TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pruebas ON pruebas(corrida, modo);

CREATE TABLE IF NOT EXISTS modelos (
    version       TEXT PRIMARY KEY,
    fecha         TEXT    NOT NULL,
    n_imagenes    INTEGER,
    precision_val REAL,
    activo        INTEGER NOT NULL DEFAULT 0
);

-- Bitácora automática: cada transición de estado, falla y acción manual
CREATE TABLE IF NOT EXISTS eventos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora TEXT NOT NULL,
    nivel      TEXT NOT NULL,     -- info | aviso | error
    origen     TEXT NOT NULL,     -- orquestador | serial | camara | modelo | manual | api
    mensaje    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_eventos_fecha ON eventos(fecha_hora);

CREATE TABLE IF NOT EXISTS config (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL           -- JSON
);
"""

# (tabla, columna, tipo) que se agregaron después de la primera versión del esquema
COLUMNAS_AGREGADAS = [
    ("clasificaciones", "tiempos_etapas", "TEXT"),  # Fase 5
]

# Botes iniciales. CAPACIDAD PROVISIONAL: [COMPLETAR con la calibración de §13.2]
BOTES_INICIALES = [
    (0, "Orgánica", "verde", 0),
    (1, "Inorgánica", "azul", 1),
    (2, "Peligroso", "gris", 2),
]
CAPACIDAD_PROVISIONAL = 10


def ahora() -> str:
    """Fecha y hora local en ISO 8601 sin zona (formato del contrato)."""
    return datetime.now().replace(microsecond=0).isoformat()


class BaseDatos:
    def __init__(self, ruta: Path | str) -> None:
        self.ruta = str(ruta)
        self._conexion = sqlite3.connect(self.ruta, check_same_thread=False)
        self._conexion.row_factory = sqlite3.Row
        self._conexion.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.Lock()
        self.inicializar()

    # ------------------------------------------------------------------ básico
    def inicializar(self) -> None:
        with self._lock:
            self._conexion.executescript(ESQUEMA)
            # Migraciones: columnas agregadas después de crear bases de datos existentes
            for tabla, columna, tipo in COLUMNAS_AGREGADAS:
                existentes_col = {f[1] for f in self._conexion.execute(f"PRAGMA table_info({tabla})")}
                if columna not in existentes_col:
                    self._conexion.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")
            existentes = self._conexion.execute("SELECT COUNT(*) FROM botes").fetchone()[0]
            if existentes == 0:
                self._conexion.executemany(
                    "INSERT INTO botes(id, nombre, color, categoria_id, capacidad_piezas) VALUES (?, ?, ?, ?, ?)",
                    [(i, n, c, cat, CAPACIDAD_PROVISIONAL) for i, n, c, cat in BOTES_INICIALES],
                )
            self._conexion.commit()

    def ejecutar(self, sql: str, parametros: Iterable[Any] = ()) -> int:
        """INSERT/UPDATE/DELETE. Devuelve el id de la última fila insertada."""
        with self._lock:
            cursor = self._conexion.execute(sql, tuple(parametros))
            self._conexion.commit()
            return cursor.lastrowid

    def consultar(self, sql: str, parametros: Iterable[Any] = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(f) for f in self._conexion.execute(sql, tuple(parametros)).fetchall()]

    def uno(self, sql: str, parametros: Iterable[Any] = ()) -> dict[str, Any] | None:
        filas = self.consultar(sql, parametros)
        return filas[0] if filas else None

    def cerrar(self) -> None:
        with self._lock:
            self._conexion.close()

    # ------------------------------------------------------------------ eventos
    def registrar_evento(self, nivel: str, origen: str, mensaje: str) -> None:
        self.ejecutar(
            "INSERT INTO eventos(fecha_hora, nivel, origen, mensaje) VALUES (?, ?, ?, ?)",
            (ahora(), nivel, origen, mensaje[:500]),
        )

    # ------------------------------------------------------------------ clasificaciones
    def insertar_clasificacion(self, **campos: Any) -> int:
        campos.setdefault("fecha_hora", ahora())
        columnas = ", ".join(campos)
        marcas = ", ".join("?" for _ in campos)
        return self.ejecutar(f"INSERT INTO clasificaciones({columnas}) VALUES ({marcas})", campos.values())

    def actualizar_clasificacion(self, id_: int, **campos: Any) -> None:
        if not campos:
            return
        asignaciones = ", ".join(f"{c} = ?" for c in campos)
        self.ejecutar(f"UPDATE clasificaciones SET {asignaciones} WHERE id = ?", [*campos.values(), id_])

    def clasificacion(self, id_: int) -> dict[str, Any] | None:
        return self.uno("SELECT * FROM clasificaciones WHERE id = ?", (id_,))


def _bool_o_none(valor: Any) -> bool | None:
    return None if valor is None else bool(valor)


def clasificacion_a_dict(fila: dict[str, Any], oculto: bool = False) -> dict[str, Any]:
    """Convierte una fila de `clasificaciones` al objeto `Clasificacion` del contrato (§2.1)."""
    datos = {
        "id": fila["id"],
        "fecha_hora": fila["fecha_hora"],
        "foto": f"/captures/{fila['foto']}" if fila.get("foto") else None,
        "modo": fila["modo"],
        "final_id": fila["final_id"],
        "origen": fila["origen"],
        "corregido": bool(fila["corregido"]),
        "modelo_version": fila["modelo_version"],
        "tiempo_ciclo_ms": fila["tiempo_ciclo_ms"],
        "drop_confirmado": _bool_o_none(fila["drop_confirmado"]),
        "bote_id": fila["bote_id"],
        "tiempos_etapas": json.loads(fila["tiempos_etapas"]) if fila.get("tiempos_etapas") else None,
        "simulado": bool(fila["simulado"]),
        "estado": fila["estado"],
    }
    if oculto:
        # Modo Adivina antes de que el usuario responda: no se revela nada de la IA
        datos["oculto"] = True
        datos["final_id"] = None
        return datos
    if fila["p_organica"] is None:
        datos["probabilidades"] = None
    else:
        datos["probabilidades"] = {
            "organica": round(fila["p_organica"], 3),
            "inorganica": round(fila["p_inorganica"], 3),
            "peligroso": round(fila["p_peligroso"], 3),
        }
    datos["pred_id"] = fila["pred_id"]
    datos["confianza"] = None if fila["confianza"] is None else round(fila["confianza"], 3)
    datos["dudoso"] = bool(fila["dudoso"])
    datos["motivo_dudoso"] = fila["motivo_dudoso"]
    return datos


if __name__ == "__main__":
    from .config import cargar_ajustes

    ajustes = cargar_ajustes()
    BaseDatos(ajustes.ruta_db)
    print(f"Base de datos lista en {ajustes.ruta_db}")
