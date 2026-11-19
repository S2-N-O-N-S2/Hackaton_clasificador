# Memoria técnica — Clasificador inteligente de residuos (Cyber Insanos)

> Documento en construcción. Las secciones de problema, objetivos, arquitectura, resultados, límites, riesgos e impacto se completan en la Fase 10. **No se reporta ningún resultado que no se haya medido.**

## [COMPLETAR en Fase 10] 1. Problema y objetivos medibles
## [COMPLETAR en Fase 10] 2. Arquitectura

## 3. Inteligencia artificial

### 3.1 Por qué transfer learning (MobileNetV2 + clasificador propio)
- **Problema:** con 40–60 fotos por clase no se puede entrenar una red neuronal desde cero, porque aprendería de memoria las pocas fotos que tiene (sobreajuste).
- **Solución:** usamos **MobileNetV2**, una red ya entrenada por terceros con ~1.2 millones de imágenes de ImageNet. Le quitamos la última capa y la usamos **congelada** como "extractor": convierte cada foto en un vector de **1280 números** que describe formas, texturas y colores. Sobre esos vectores entrenamos un clasificador pequeño, una **regresión logística** de scikit-learn.
- **Ventajas para el reto:**
  - Entrena en **segundos** en una laptop sin GPU. La prueba de humo con 45 fotos tardó ~11 s en total; reentrenar con las correcciones solo procesa las fotos nuevas, gracias a la caché de vectores.
  - MobileNetV2 es ligera (~3.5 M parámetros) y clasifica cada foto en décimas de segundo en CPU.
  - Es explicable: el único parámetro aprendido por nosotros es un clasificador lineal.
- **Alternativa disponible:** una cabeza densa de Keras (`Dropout(0.2) + Dense(3, softmax)`, Adam 1e-3, 15 épocas), con `--cabeza densa`. Opcionalmente se agrega **aumento de datos** ligero (volteo, rotación de ±8°, brillo de ±10 %), con `--aumentar`, solo en la parte de entrenamiento.

### 3.2 Por qué separar entrenamiento y validación **por objeto**
- De cada objeto físico tomamos varias fotos (distintas posiciones y lados). Si fotos del **mismo** plátano quedan en entrenamiento y en validación, el modelo "ya lo vio": la validación saldría inflada y no diría cómo le irá con un plátano **nuevo** (fuga de datos).
- Por eso cada foto lleva un `objeto_id` (lo pide `capturar_dataset.py`, se guarda en `dataset/metadatos.csv`). `train.py` usa `StratifiedGroupKFold` de scikit-learn:
  - todas las fotos de un objeto quedan **del mismo lado**;
  - cada clase aparece en entrenamiento **y** en validación;
  - si una clase tiene menos de 2 objetos distintos, el entrenamiento se niega y explica qué falta.
- El modelo que se guarda es el entrenado **solo** con la parte de entrenamiento, así que la precisión de validación que reportamos es honesta.
- Las fotos que llegan por correcciones del backend (sin `objeto_id`) cuentan como un objeto cada una.

### 3.3 Cómo se interpreta la confianza
- El clasificador entrega 3 probabilidades que suman 1 (orgánica, inorgánica, peligroso). El backend toma **3 fotogramas**, **promedia** sus probabilidades y llama **confianza** a la probabilidad de la clase ganadora.
- **No es una garantía.** Una confianza de 0.85 significa que el modelo está más seguro, no que acierte el 85 % de las veces. Con pocos datos, el modelo puede estar "muy seguro" de algo incorrecto, sobre todo con objetos que nunca vio.
- Por eso el sistema aplica las **reglas del reto** (`aplicar_reglas()` en `backend/app/model.py`):
  - confianza < `UMBRAL_GENERAL` (0.60) → **revisión**: el residuo no cae;
  - p(peligroso) ≥ `UMBRAL_PELIGROSO` (0.35) sin ser la ganadora → **revisión** (asimetría de riesgo: mandar un peligroso a otro bote es el peor error).
- `evaluate.py` reporta, con los umbrales actuales, cuántas fotos irían a revisión y qué precisión tienen las aceptadas. Así se puede justificar el umbral con datos: subirlo manda más casos a revisión, pero los aceptados se equivocan menos.
- La **zona de interés (ROI)** con la que se entrenó cada versión queda guardada en su `labels.json` y se usa igual al clasificar, para que la IA siempre vea el mismo recorte.

### 3.4 Versiones y reentrenamiento
- Cada entrenamiento crea `backend/models/v<N>/` con estos archivos:
  - `modelo.joblib` o `cabeza.keras`;
  - `labels.json` (clases, ROI, extractor);
  - `split.json` (qué fotos fueron a validación);
  - `metricas.json`.
- También se registra en la tabla `modelos`.
- La versión nueva **solo se activa si su precisión de validación no empeora** respecto a la activa (§14.3).
  - **Límite:** si el dataset creció, las dos versiones se validaron con conjuntos distintos, así que la comparación es orientativa.
- Reentrenar desde el panel (`POST /api/modelo/reentrenar`) corre en segundo plano y avisa su progreso por WebSocket. Usa solo `dataset/<clase>/`: las etiquetas de usuarios esperan en `_por_verificar/` hasta que el operador las aprueba.

### 3.5 Resultados del modelo
| Versión | Fecha | Fotos (org / inorg / pel) | Objetos (entr. / val.) | Precisión de validación | Matriz de confusión |
|---|---|---|---|---|---|
| [COMPLETAR con la primera versión entrenada con fotos reales] | | | | | `models/v<N>/evaluacion/matriz_confusion.png` |

> Las pruebas de la Fase 4 se hicieron con **imágenes sintéticas** (figuras de colores) solo para comprobar que el código funciona. **Esos resultados no se reportan** como precisión del sistema.

## [COMPLETAR en Fase 10] 4. Resultados de la prueba oficial
## [COMPLETAR en Fase 10] 5. Límites, riesgos e impacto
