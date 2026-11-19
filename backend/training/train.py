"""
train.py — Entrena el clasificador de residuos (especificación §14.2).

Cómo funciona (en palabras sencillas):
  1. Cada foto del dataset se recorta (ROI), se reduce a 224×224 y pasa por MobileNetV2, una red ya
     entrenada con millones de imágenes (ImageNet). No la reentrenamos: solo la usamos para convertir
     cada foto en un vector de 1280 números que describe lo que se ve (transfer learning).
  2. Esos vectores se guardan en caché (.npz): reentrenar solo calcula los de fotos nuevas → segundos.
  3. Con los vectores se entrena un clasificador pequeño: regresión logística (por defecto) o una
     cabeza densa de Keras (--cabeza densa).
  4. Entrenamiento y validación se separan POR OBJETO FÍSICO, no por foto: si el mismo plátano
     aparece en las dos partes, la validación sería "trampa" (fuga de datos).
  5. Se guarda models/v<N>/ y se registra en la tabla `modelos`. La versión nueva se ACTIVA solo si su
     precisión de validación no es peor que la de la versión activa.

Uso (desde backend/, con el entorno virtual activo):
    python -m training.train                          # regresión logística
    python -m training.train --cabeza densa           # alternativa con Keras
    python -m training.train --aumentar               # + aumento de datos ligero
    python -m training.train --activar siempre        # forzar activación

El modelo que se guarda es el entrenado SOLO con la parte de entrenamiento, para que la precisión de
validación reportada sea honesta (no se reentrena con todo al final).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Sequence

import cv2
import numpy as np

if __package__ in (None, ""):  # permite también: python training/train.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import CLAVES_CATEGORIA, IDS_CATEGORIA  # noqa: E402
from app.model import DIMENSION_EMBEDDING, preparar_imagen  # noqa: E402

EXTENSIONES = (".jpg", ".jpeg", ".png")
ARCHIVO_METADATOS = "metadatos.csv"
MIN_OBJETOS_POR_CLASE = 2

Progreso = Callable[[float, str], None]


class ErrorDatos(Exception):
    """El dataset no alcanza para entrenar (faltan clases u objetos)."""


# =============================================================================
# Dataset
# =============================================================================
@dataclass
class Muestra:
    ruta: Path
    relativa: str        # "organica/platano1__20261119_101500_1.jpg"
    clase: int
    objeto: str          # grupo para separar por objeto: "organica:platano1"


def objeto_desde_nombre(nombre: str) -> str:
    """'platano1__20261119_101500_1.jpg' → 'platano1'. Sin '__' (fotos del backend) → cada foto es su objeto."""
    base = Path(nombre).stem
    return base.split("__", 1)[0] if "__" in base else base


def leer_metadatos(dir_dataset: Path) -> dict[str, str]:
    """archivo relativo → objeto_id, desde dataset/metadatos.csv (lo escribe capturar_dataset.py)."""
    ruta = Path(dir_dataset) / ARCHIVO_METADATOS
    if not ruta.exists():
        return {}
    with ruta.open(encoding="utf-8", newline="") as archivo:
        return {fila["archivo"]: fila["objeto_id"] for fila in csv.DictReader(archivo) if fila.get("archivo")}


def listar_dataset(dir_dataset: Path) -> list[Muestra]:
    """Fotos de dataset/<clase>/ (NO incluye _por_verificar/: esas esperan la aprobación del operador)."""
    dir_dataset = Path(dir_dataset)
    metadatos = leer_metadatos(dir_dataset)
    muestras = []
    for clase, clave in zip(IDS_CATEGORIA, CLAVES_CATEGORIA):
        carpeta = dir_dataset / clave
        if not carpeta.is_dir():
            continue
        for ruta in sorted(carpeta.iterdir()):
            if ruta.suffix.lower() not in EXTENSIONES:
                continue
            relativa = f"{clave}/{ruta.name}"
            objeto = metadatos.get(relativa) or objeto_desde_nombre(ruta.name)
            muestras.append(Muestra(ruta, relativa, clase, f"{clave}:{objeto}"))
    return muestras


def resumen_dataset(muestras: Sequence[Muestra]) -> dict[str, dict[str, int]]:
    resumen = {}
    for clase, clave in zip(IDS_CATEGORIA, CLAVES_CATEGORIA):
        de_clase = [m for m in muestras if m.clase == clase]
        resumen[clave] = {"fotos": len(de_clase), "objetos": len({m.objeto for m in de_clase})}
    return resumen


# =============================================================================
# Separación entrenamiento / validación POR OBJETO
# =============================================================================
def separar_por_objeto(muestras: Sequence[Muestra], fraccion_val: float = 0.25,
                       semilla: int = 42) -> tuple[list[int], list[int]]:
    """Índices (entrenamiento, validación). Todas las fotos de un objeto quedan del mismo lado y
    cada clase aparece en ambos lados (estratificado)."""
    from sklearn.model_selection import StratifiedGroupKFold

    clases = np.array([m.clase for m in muestras])
    grupos = np.array([m.objeto for m in muestras])
    objetos_por_clase = {c: len(set(grupos[clases == c])) for c in IDS_CATEGORIA}
    faltan = [CLAVES_CATEGORIA[c] for c, n in objetos_por_clase.items() if n < MIN_OBJETOS_POR_CLASE]
    if faltan:
        raise ErrorDatos(
            f"Cada clase necesita fotos de al menos {MIN_OBJETOS_POR_CLASE} objetos distintos "
            f"(uno para entrenar y otro para validar). Faltan en: {', '.join(faltan)}. "
            f"Objetos por clase: { {CLAVES_CATEGORIA[c]: n for c, n in objetos_por_clase.items()} }"
        )
    n_particiones = max(2, min(round(1 / fraccion_val), min(objetos_por_clase.values())))
    divisor = StratifiedGroupKFold(n_splits=n_particiones, shuffle=True, random_state=semilla)
    entrenamiento, validacion = next(divisor.split(np.zeros(len(muestras)), clases, grupos))
    for c in IDS_CATEGORIA:  # garantía extra: cada clase en ambos lados
        if c not in clases[entrenamiento] or c not in clases[validacion]:
            raise ErrorDatos(f"No se pudo poner la clase {CLAVES_CATEGORIA[c]} en entrenamiento y validación")
    return sorted(entrenamiento.tolist()), sorted(validacion.tolist())


# =============================================================================
# Embeddings con caché
# =============================================================================
def variante_aumentada(imagen_rgb: np.ndarray, numero: int, semilla: int) -> np.ndarray:
    """Aumento ligero (§14.2): volteo horizontal, rotación pequeña (±8°) y brillo ±10 %."""
    azar = np.random.default_rng(semilla + numero)
    salida = imagen_rgb[:, ::-1] if numero % 2 == 1 else imagen_rgb
    angulo = float(azar.uniform(-8, 8))
    centro = (salida.shape[1] / 2, salida.shape[0] / 2)
    matriz = cv2.getRotationMatrix2D(centro, angulo, 1.0)
    salida = cv2.warpAffine(np.ascontiguousarray(salida), matriz, (salida.shape[1], salida.shape[0]),
                            borderMode=cv2.BORDER_REFLECT)
    factor = float(azar.uniform(0.9, 1.1))
    return np.clip(salida.astype(np.float32) * factor, 0, 255).astype(np.uint8)


class CacheEmbeddings:
    """Guarda los vectores ya calculados en models/cache/embeddings_<extractor>.npz.

    La clave incluye tamaño y fecha del archivo, la ROI y la variante: si algo cambia, se recalcula.
    """

    def __init__(self, ruta: Path) -> None:
        self.ruta = Path(ruta)
        self.datos: dict[str, np.ndarray] = {}
        self.cambios = False
        if self.ruta.exists():
            try:
                with np.load(self.ruta, allow_pickle=False) as archivo:
                    self.datos = dict(zip(archivo["claves"].tolist(), archivo["vectores"]))
            except Exception:  # noqa: BLE001 — caché dañada: se reconstruye
                self.datos = {}

    @staticmethod
    def clave(ruta: Path, roi: Sequence[float], variante: int) -> str:
        info = ruta.stat()
        return f"{ruta.as_posix()}|{info.st_size}|{info.st_mtime_ns}|{','.join(map(str, roi))}|{variante}"

    def guardar(self) -> None:
        if not self.cambios:
            return
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        claves = np.array(list(self.datos.keys()))
        vectores = np.stack(list(self.datos.values())) if self.datos else np.zeros((0, DIMENSION_EMBEDDING))
        np.savez_compressed(self.ruta, claves=claves, vectores=vectores)
        self.cambios = False


def calcular_embeddings(trabajos: list[tuple[Muestra, int]], roi: Sequence[float], extractor, cache: CacheEmbeddings,
                        semilla: int, progreso: Progreso | None = None, lote: int = 32) -> np.ndarray:
    """trabajos = [(muestra, variante)], variante 0 = original, 1..k = aumentadas."""
    claves = [cache.clave(m.ruta, roi, v) for m, v in trabajos]
    pendientes = [i for i, c in enumerate(claves) if c not in cache.datos]
    for inicio in range(0, len(pendientes), lote):
        indices = pendientes[inicio:inicio + lote]
        imagenes = []
        for i in indices:
            muestra, variante = trabajos[i]
            frame = cv2.imread(str(muestra.ruta))
            if frame is None:
                raise ErrorDatos(f"No se pudo leer la imagen {muestra.relativa}")
            imagen = preparar_imagen(frame, roi)
            imagenes.append(imagen if variante == 0 else variante_aumentada(imagen, variante, semilla))
        vectores = extractor.embeddings(np.stack(imagenes))
        for i, vector in zip(indices, vectores):
            cache.datos[claves[i]] = vector
        cache.cambios = True
        if progreso:
            progreso(0.1 + 0.7 * min(1.0, (inicio + len(indices)) / len(pendientes)),
                     f"Extrayendo características {inicio + len(indices)}/{len(pendientes)}")
    cache.guardar()
    return np.stack([cache.datos[c] for c in claves]) if claves else np.zeros((0, DIMENSION_EMBEDDING))


# =============================================================================
# Clasificadores
# =============================================================================
def entrenar_logistica(x: np.ndarray, y: np.ndarray, semilla: int):
    """Estandarizar + regresión logística (clases balanceadas). Entrena en segundos."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    modelo = make_pipeline(StandardScaler(),
                           LogisticRegression(max_iter=3000, C=1.0, class_weight="balanced", random_state=semilla))
    modelo.fit(x, y)
    return modelo


def entrenar_densa(x: np.ndarray, y: np.ndarray, semilla: int, epocas: int = 15):
    """Alternativa §14.2: Dropout(0.2) + Dense(3, softmax), Adam 1e-3, sobre los vectores congelados."""
    import keras

    keras.utils.set_random_seed(semilla)
    modelo = keras.Sequential([
        keras.Input(shape=(x.shape[1],)),
        keras.layers.Dropout(0.2),
        keras.layers.Dense(3, activation="softmax"),
    ])
    modelo.compile(optimizer=keras.optimizers.Adam(1e-3), loss="sparse_categorical_crossentropy",
                   metrics=["accuracy"])
    modelo.fit(x, y, epochs=epocas, batch_size=16, verbose=0)
    return modelo


def probabilidades(modelo, cabeza: str, x: np.ndarray) -> np.ndarray:
    """(n, 3) con columnas 0, 1, 2 (todas las clases están en el entrenamiento)."""
    if cabeza == "logistica":
        return modelo.predict_proba(x)
    return np.asarray(modelo.predict(x, verbose=0))


# =============================================================================
# Métricas y versiones
# =============================================================================
def metricas(y_real: Sequence[int], y_pred: Sequence[int]) -> dict[str, Any]:
    """Precisión total (aciertos / total), acierto por clase y matriz de confusión (filas real, columnas predicha)."""
    matriz = [[0, 0, 0] for _ in IDS_CATEGORIA]
    for r, p in zip(y_real, y_pred):
        matriz[int(r)][int(p)] += 1
    n = len(y_real)
    por_clase = {}
    for c, clave in zip(IDS_CATEGORIA, CLAVES_CATEGORIA):
        total = sum(matriz[c])
        por_clase[clave] = {"n": total, "aciertos": matriz[c][c],
                            "acierto": round(matriz[c][c] / total, 4) if total else None}
    aciertos = sum(matriz[c][c] for c in IDS_CATEGORIA)
    return {"n": n, "aciertos": aciertos, "precision": round(aciertos / n, 4) if n else None,
            "por_clase": por_clase, "matriz_confusion": matriz}


def siguiente_version(dir_modelos: Path) -> str:
    numeros = [int(m.group(1)) for p in Path(dir_modelos).glob("v*")
               if p.is_dir() and (m := re.fullmatch(r"v(\d+)", p.name))]
    return f"v{max(numeros, default=0) + 1}"


def decidir_activacion(precision_nueva: float | None, precision_activa: float | None,
                       politica: str = "si_no_empeora") -> tuple[bool, str]:
    """Regla §14.3: solo se activa la versión nueva si NO empeora la precisión de validación."""
    if politica == "siempre":
        return True, "Activado (forzado)"
    if politica == "nunca":
        return False, "No activado (se pidió no activar)"
    if precision_nueva is None:
        return False, "No activado: sin precisión de validación"
    if precision_activa is None:
        return True, "Activado: es el primer modelo"
    if precision_nueva >= precision_activa:
        return True, f"Activado: {precision_nueva:.1%} ≥ {precision_activa:.1%} de la versión activa"
    return False, f"No activado: empeoró ({precision_nueva:.1%} < {precision_activa:.1%})"


def tabla_matriz(matriz: list[list[int]]) -> str:
    """Matriz de confusión como tabla de texto (consola y docs)."""
    cortos = ["Org", "Inorg", "Pel"]
    lineas = ["real \\ pred " + " ".join(f"{c:>6}" for c in cortos)]
    for c, fila in zip(cortos, matriz):
        lineas.append(f"{c:>11} " + " ".join(f"{v:>6}" for v in fila))
    return "\n".join(lineas)


# =============================================================================
# Entrenamiento completo
# =============================================================================
def entrenar(dir_dataset: Path, dir_modelos: Path, db=None, cabeza: str = "logistica",
             fraccion_val: float = 0.25, semilla: int = 42, aumentar: bool = False,
             roi: Sequence[float] = (0.0, 0.0, 1.0, 1.0), extractor=None, activar: str = "si_no_empeora",
             progreso: Progreso | None = None) -> dict[str, Any]:
    """Entrena, guarda models/v<N>/, registra en la BD y decide si activar. Devuelve un resumen."""
    if cabeza not in ("logistica", "densa"):
        raise ValueError("cabeza debe ser 'logistica' o 'densa'")
    avisar = progreso or (lambda f, m: None)
    dir_modelos = Path(dir_modelos)
    roi = [float(v) for v in roi]

    avisar(0.02, "Leyendo dataset")
    muestras = listar_dataset(dir_dataset)
    if not muestras:
        raise ErrorDatos(f"No hay fotos en {dir_dataset}/<organica|inorganica|peligroso>/")
    idx_ent, idx_val = separar_por_objeto(muestras, fraccion_val, semilla)

    if extractor is None:
        from app.model import ExtractorMobileNet
        extractor = ExtractorMobileNet()
    cache = CacheEmbeddings(dir_modelos / "cache" / f"embeddings_{getattr(extractor, 'nombre', 'extractor')}.npz")

    n_aumentos = 2 if aumentar else 0
    trabajos_ent = [(muestras[i], v) for i in idx_ent for v in range(n_aumentos + 1)]
    trabajos_val = [(muestras[i], 0) for i in idx_val]  # la validación NUNCA se aumenta
    avisar(0.1, "Extrayendo características")
    x_todo = calcular_embeddings(trabajos_ent + trabajos_val, roi, extractor, cache, semilla, avisar)
    x_ent, x_val = x_todo[:len(trabajos_ent)], x_todo[len(trabajos_ent):]
    y_ent = np.array([m.clase for m, _ in trabajos_ent])
    y_val = np.array([m.clase for m, _ in trabajos_val])

    avisar(0.85, f"Entrenando clasificador ({cabeza})")
    modelo = entrenar_logistica(x_ent, y_ent, semilla) if cabeza == "logistica" else entrenar_densa(x_ent, y_ent, semilla)
    p_val = probabilidades(modelo, cabeza, x_val)
    m_val = metricas(y_val.tolist(), p_val.argmax(axis=1).tolist())
    m_ent = metricas(y_ent.tolist(), probabilidades(modelo, cabeza, x_ent).argmax(axis=1).tolist())

    # --- guardar versión
    avisar(0.93, "Guardando versión")
    version = siguiente_version(dir_modelos)
    destino = dir_modelos / version
    destino.mkdir(parents=True)
    if cabeza == "logistica":
        import joblib
        joblib.dump(modelo, destino / "modelo.joblib")
    else:
        modelo.save(destino / "cabeza.keras")
    fecha = datetime.now().replace(microsecond=0).isoformat()
    etiquetas = {"clases": list(IDS_CATEGORIA), "nombres": CLAVES_CATEGORIA, "cabeza": cabeza, "roi": roi,
                 "extractor": getattr(extractor, "nombre", "desconocido"), "entrada": [224, 224, 3]}
    (destino / "labels.json").write_text(json.dumps(etiquetas, indent=2, ensure_ascii=False), encoding="utf-8")
    # Objetos desconocidos: centro y límite de cada clase con las fotos ORIGINALES de entrenamiento
    from app.model import calcular_novedad, puntaje_novedad
    originales = [k for k, (_, variante) in enumerate(trabajos_ent) if variante == 0]
    novedad = calcular_novedad(x_ent[originales], y_ent[originales])
    (destino / "novedad.json").write_text(json.dumps(novedad), encoding="utf-8")
    from app.config import valores_por_defecto
    limite_desconocido = valores_por_defecto()["umbral_desconocido"]
    fuera_val = sum(puntaje_novedad(x_val[k:k + 1], novedad) > limite_desconocido for k in range(len(x_val)))
    (destino / "split.json").write_text(json.dumps({
        "entrenamiento": [muestras[i].relativa for i in idx_ent],
        "validacion": [muestras[i].relativa for i in idx_val],
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    info = {
        "version": version, "fecha": fecha, "cabeza": cabeza, "aumento": aumentar, "semilla": semilla,
        "fraccion_val": fraccion_val, "roi": roi, "dataset": resumen_dataset(muestras),
        "n_imagenes": len(muestras),
        "objetos_entrenamiento": len({muestras[i].objeto for i in idx_ent}),
        "objetos_validacion": len({muestras[i].objeto for i in idx_val}),
        "entrenamiento": m_ent, "validacion": m_val,
        # Fotos de validación (objetos conocidos) que la regla de "desconocido" mandaría a revisión
        "validacion_marcadas_desconocido": {"n": int(fuera_val), "de": len(x_val)},
        "nota": "Separación por objeto físico; el modelo guardado se entrenó solo con la parte de entrenamiento.",
    }
    (destino / "metricas.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- registrar y decidir activación
    precision_anterior = None
    if db is not None:
        fila = db.uno("SELECT precision_val FROM modelos WHERE activo = 1 ORDER BY fecha DESC LIMIT 1")
        precision_anterior = fila["precision_val"] if fila else None
    activado, mensaje = decidir_activacion(m_val["precision"], precision_anterior, activar)
    if db is not None:
        db.ejecutar("INSERT INTO modelos(version, fecha, n_imagenes, precision_val, activo) VALUES (?, ?, ?, ?, 0)",
                    (version, fecha, len(muestras), m_val["precision"]))
        if activado:
            db.ejecutar("UPDATE modelos SET activo = CASE WHEN version = ? THEN 1 ELSE 0 END", (version,))
        db.registrar_evento("info", "modelo", f"Entrenado {version}: precisión val {m_val['precision']} — {mensaje}")
    avisar(1.0, mensaje)
    return {"version": version, "dir": str(destino), "precision_val": m_val["precision"],
            "precision_anterior": precision_anterior, "activado": activado, "mensaje": mensaje,
            "n_imagenes": len(muestras), "metricas": info}


# =============================================================================
# Línea de comandos
# =============================================================================
def main() -> int:
    from app.config import Configuracion, cargar_ajustes
    from app.db import BaseDatos

    parser = argparse.ArgumentParser(description="Entrena el clasificador (MobileNetV2 + clasificador propio).")
    parser.add_argument("--cabeza", choices=["logistica", "densa"], default="logistica")
    parser.add_argument("--val", type=float, default=0.25, help="fracción de OBJETOS para validación (0.25)")
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--aumentar", action="store_true", help="aumento de datos ligero en entrenamiento")
    parser.add_argument("--activar", choices=["si_no_empeora", "siempre", "nunca"], default="si_no_empeora")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ajustes = cargar_ajustes()
    db = BaseDatos(ajustes.ruta_db)
    roi = Configuracion(db).get("roi")
    print(f"Dataset: {ajustes.dir_dataset}")
    print(f"Base de datos: {ajustes.ruta_db}")
    try:
        r = entrenar(ajustes.dir_dataset, ajustes.dir_modelos, db, args.cabeza, args.val, args.semilla,
                     args.aumentar, roi, activar=args.activar,
                     progreso=lambda f, m: print(f"  [{f:4.0%}] {m}"))
    except ErrorDatos as error:
        print(f"\nNO SE PUDO ENTRENAR: {error}")
        return 1
    m = r["metricas"]
    print(f"\nVersión {r['version']} ({m['cabeza']}) guardada en {r['dir']}")
    for clave, d in m["dataset"].items():
        print(f"  {clave:11}: {d['fotos']:3} fotos de {d['objetos']} objetos")
    print(f"Objetos: {m['objetos_entrenamiento']} entrenamiento / {m['objetos_validacion']} validación")
    print(f"Precisión entrenamiento: {m['entrenamiento']['precision']:.1%}")
    print(f"Precisión VALIDACIÓN:    {m['validacion']['precision']:.1%}  (n = {m['validacion']['n']} fotos)")
    for clave, d in m["validacion"]["por_clase"].items():
        acierto = "--" if d["acierto"] is None else f"{d['acierto']:.0%}"
        print(f"  {clave:11}: {acierto} ({d['aciertos']}/{d['n']})")
    print("\nMatriz de confusión (validación):")
    print(tabla_matriz(m["validacion"]["matriz_confusion"]))
    print(f"\n{r['mensaje']}")
    print("Siguiente paso: python -m training.evaluate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
