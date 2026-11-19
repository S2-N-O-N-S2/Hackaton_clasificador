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

## 2. Modelos preentrenados

| Modelo | Fuente | Licencia | Uso | Modificación del equipo |
|---|---|---|---|---|
| MobileNetV2 (ImageNet) | Keras Applications | Apache 2.0 | Extractor de características (Fase 4) | [COMPLETAR] |
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

## 5. Fuentes de contenido (explicaciones del modo Adivina)

| Fuente | Qué se usó | Validado por |
|---|---|---|
| [COMPLETAR: norma ambiental local de separación de residuos] | Criterios de clasificación orgánica / inorgánica / peligroso | [COMPLETAR] |
