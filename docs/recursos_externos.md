# Declaración de recursos externos

La convocatoria permite bibliotecas, tutoriales e IA generativa **con atribución**. Aquí se declara qué se usó, **qué generó** cada recurso y **qué modificó el equipo**. Todo debe poder explicarse ante el jurado.

## 1. Bibliotecas y frameworks

| Recurso | Versión | Licencia | Uso en el proyecto | Archivos donde se usa |
|---|---|---|---|---|
| Python | 3.12.10 | PSF | Lenguaje del backend (TensorFlow requiere ≤ 3.13) | `backend/` |
| FastAPI + uvicorn[standard] | ver `requirements.lock.txt` | MIT / BSD | API REST y WebSocket | `backend/app/` |
| OpenCV (opencv-python) | ver lock | Apache 2.0 | Cámara y procesamiento de imagen | `camera.py`, `tools/verificar_hardware.py` |
| NumPy | ver lock | BSD | Arreglos numéricos | backend |
| TensorFlow / Keras | 2.21 | Apache 2.0 | MobileNetV2 como extractor | `model.py`, `training/` |
| scikit-learn | ver lock | BSD | LogisticRegression | `training/train.py`, `model.py` |
| matplotlib | ver lock | PSF-like | PNG de la matriz de confusión | `training/evaluate.py` |
| pyserial | 3.5 | BSD | Serial con el Arduino | `serial_link.py`, `tools/verificar_hardware.py` |
| vosk | 0.3.45 | Apache 2.0 | Voz offline | `voice.py` |
| sounddevice | ver lock | MIT | Captura de micrófono para Vosk | `voice.py` |
| pytest, httpx | ver lock | MIT / BSD | Pruebas | `backend/tests/` |
| React / react-dom | 18.3.1 | MIT | Interfaz del panel | `frontend/src/` |
| Vite + @vitejs/plugin-react | 6.4.6 / 4.7.0 | MIT | Servidor de desarrollo y compilación del panel | `frontend/` |

## 2. Modelos preentrenados

| Modelo | Fuente | Licencia | Uso | Modificación del equipo |
|---|---|---|---|---|
| MobileNetV2 (ImageNet) | Keras Applications (pesos `mobilenet_v2_weights_tf_dim_ordering_tf_kernels_1.0_224_no_top.h5`) | Apache 2.0 | Extractor congelado, sin capa superior y con pooling promedio (Fase 4) | No se modifica: se usa congelada. El equipo entrena solo el clasificador de encima |
| vosk-model-small-es | alphacephei.com/vosk/models | Apache 2.0 | Reconocimiento de voz offline (Fase 9) | [COMPLETAR] |

## 3. Tutoriales y código de referencia

| Fuente (URL / autor) | Qué se tomó | Dónde se usó | Qué se adaptó |
|---|---|---|---|
| [COMPLETAR] | | | |

## 4. Herramientas de IA generativa

| Herramienta | Fase / archivo | Qué generó | Qué revisó o modificó el equipo |
|---|---|---|---|
| Claude Code (Anthropic) | Inicio: estructura de carpetas, README, plantillas de `bitacora.md`, `recursos_externos.md`, `.gitignore` | Estructura y textos iniciales | [COMPLETAR] |
| Claude Code (Anthropic) | Fase 0: `requirements.txt`, `tools/verificar_hardware.py`, `tools/calcular_par.py`, `docs/mediciones.md` | Scripts y fórmulas de geometría y par (fricción + inercia, factor de seguridad 2) | [COMPLETAR: el equipo debe revisar las fórmulas y llenar las mediciones] |
| Claude Code (Anthropic) | Fase 3: todo `backend/app/` y `backend/tests/` (orquestador, serial, cámara, modelo simulado, BD, API, WebSocket, pruebas) y `docs/api_contrato.md` | Código completo y pruebas | [COMPLETAR: el equipo debe leer `orchestrator.py` y `model.py` y poder modificar `aplicar_reglas` en vivo] |
| Claude Code (Anthropic) | Fase 4: `training/` (captura, entrenamiento por objeto, evaluación), `ModeloReal` y `GestorReentrenamiento` en `app/model.py`, `tests/test_entrenamiento.py`, sección IA de `memoria_tecnica.md` | Código, pruebas y documentación | [COMPLETAR: el equipo debe capturar el dataset real y revisar los umbrales con `evaluate.py`] |
| Claude Code (Anthropic) | Fase 6: `frontend/` (panel React + Vite) | Todo el panel: capa de API, WebSocket con reconexión, estado global, 10 vistas, gráficas SVG/CSS, estilos y el servidor de datos de ejemplo (`src/mock/`, JSON copiados de `docs/api_contrato.md`) | [COMPLETAR: el equipo debe probarlo con el backend real y poder explicar cada vista] |

## 5. Fuentes de contenido (explicaciones del modo Adivina)

| Fuente | Qué se usó | Validado por |
|---|---|---|
| [COMPLETAR: norma ambiental local de separación de residuos] | Criterios de clasificación orgánica / inorgánica / peligroso | [COMPLETAR] |
