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
| Arduino AVR core | 1.8.8 | LGPL | Compilación para el Arduino UNO | `firmware/` |
| Servo (Arduino) | 1.3.0 | LGPL | Servos del disco y de la trampilla | `clasificador_uno.ino` |
| EEPROM, Wire (Arduino) | 2.0 / 1.0 | LGPL | Calibración persistente; bus I2C de la LCD | `clasificador_uno.ino`, `escaner_i2c.ino` |
| LiquidCrystal I2C (Frank de Brabander) | 1.1.2 | ver repositorio de la biblioteca | LCD 20×4 por I2C | `clasificador_uno.ino` |
| Keypad (Mark Stanley, Alexander Brevig) | 3.1.1 | LGPL | Teclado matricial 4×4 | `clasificador_uno.ino` |

## 2. Modelos preentrenados

| Modelo | Fuente | Licencia | Uso | Modificación del equipo |
|---|---|---|---|---|
| MobileNetV2 (ImageNet) | Keras Applications (pesos `mobilenet_v2_weights_tf_dim_ordering_tf_kernels_1.0_224_no_top.h5`) | Apache 2.0 | Extractor congelado, sin capa superior y con pooling promedio (Fase 4) | No se modifica: se usa congelada. El equipo entrena solo el clasificador de encima |
| vosk-model-small-es | alphacephei.com/vosk/models | Apache 2.0 | Reconocimiento de voz offline (Fase 9) | [COMPLETAR] |
| DroidCam (Dev47Apps): app del celular + DroidCam Client para Windows | [COMPLETAR versión] | Propietaria, gratuita | Usar el celular como cámara cenital (si el equipo la elige) | Solo se usa como fuente de video; no forma parte del código |

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
| Claude Code (Anthropic) | Fase 5 (preparación): `tools/calibrar_angulos.py`, tiempos por etapa y sincronización de ángulos en `orchestrator.py`, migración en `db.py`, `tests/test_fase5.py`, `docs/integracion_fase5.md`, `docs/resultados/ciclos_reales.md` | Código, pruebas y documentación | [COMPLETAR] |
| Claude Code (Anthropic) | Fase 2: `firmware/clasificador_uno/clasificador_uno.ino`, `firmware/escaner_i2c/escaner_i2c.ino`, `docs/diagrama_electrico.md`, `docs/prueba_firmware.md` | Firmware completo (parser, rampa del disco, DROP con interrupción, LCD no bloqueante, EEPROM, watchdog), escáner I2C (basado en el escáner clásico de Arduino Playground), tabla de conexiones, checklist de mediciones y la lista de pruebas | [COMPLETAR: el equipo debe probarlo en el hardware, ajustar los ángulos de la trampilla y la dirección de la LCD, y poder explicar cada sección] |
| Claude Code (Anthropic) | Prompt 3 (dataset): `backend/tools/normalizar_dataset.py` | Script que copia fotos originales a `backend/dataset/` (reduce a 320 px sin recortar, renombra <objeto>__<nnn>.jpg, agrega a metadatos.csv) y agrupa The Garbage Dataset en 3 clases | [COMPLETAR: revisar el mapeo de categorías y validar con la norma local] |
| Claude Code (Anthropic) | Despliegue del modelo: `backend/tools/registrar_modelo.py` y excepción en `.gitignore` para `backend/models/v*/` | Script que registra y activa en la base de datos local un modelo que llegó por Git | [COMPLETAR: la Persona A revisa que encaje con `app/model.py`] |

## 5. Fuentes de contenido (explicaciones del modo Adivina)

| Fuente | Qué se usó | Validado por |
|---|---|---|
| [COMPLETAR: norma ambiental local de separación de residuos] | Criterios de clasificación orgánica / inorgánica / peligroso | [COMPLETAR] |

## 6. Datasets externos

| Dataset | Fuente | Licencia | Qué se usó | Cómo se rotula |
|---|---|---|---|---|
| The Garbage Dataset (GD), Suman Kunwar | Kaggle `sumn2u/garbage-classification-v2` · artículo arXiv 2602.10500 | Artículo CC BY 4.0; [COMPLETAR: confirmar la licencia en la página de Kaggle] | Carpeta `original`, 400 fotos por clase con semilla 42: biological → orgánica; cardboard, paper, plastic, metal, glass, clothes, shoes → inorgánica (57–58 de cada una); battery → peligroso. "trash" se descartó | En `metadatos.csv`: `camara = externo:garbage_dataset_gd` y `objeto_id = gd_<categoria>_<n>` (cada foto es un objeto distinto) |

**Advertencia para la defensa:** son fotos de internet con otros fondos y otra luz (especificación §14.1). Sirven para que la IA conozca muchos productos, pero la precisión que se reporta al jurado debe medirse con nuestros residuos en la bandeja.

| Herramienta | Fase / archivo | Qué generó | Qué revisó o modificó el equipo |
|---|---|---|---|
| Claude Code (Anthropic), skill `frontend-design` | Fase 6 (rediseño visual): `frontend/src/estilos.css`, `App.jsx`, `componentes/Comun.jsx`, `componentes/Graficas.jsx` (`Carrusel`, `Logotipo`) y marcado de `vistas/*.jsx` | Nueva identidad visual ("señalética de estación de reciclaje"): fichas de diseño, placas de categoría, franjas de advertencia, botes dibujados y carrusel SVG animado con CSS. Sin bibliotecas nuevas; la fuente Bahnschrift es del sistema (Windows) y en otros equipos se usan fuentes de respaldo del sistema | [COMPLETAR: la Persona B revisa el diseño en la laptop de la demo y en un celular real, y debe poder explicar el carrusel y las franjas] |
| Claude Code (Anthropic) | Fase 6 (animaciones): `Carrusel` en `componentes/Graficas.jsx`, `vistas/EnVivo.jsx`, `vistas/Juego.jsx`, `estilos.css` | Animaciones CSS/SVG ligadas a los estados del backend: giro con rampa, trampilla y caída del residuo, flash de cámara, escaneo de la IA y cuenta regresiva | [COMPLETAR: revisar que los tiempos se vean bien con el backend real y el Arduino] |
| Claude Code (Anthropic) | App móvil (PWA): `frontend/public/manifest.webmanifest`, `frontend/public/sw.js`, `frontend/public/iconos/*`, `<head>` de `frontend/index.html`, `docs/app_movil.md` | Manifiesto, service worker sin caché (solo una pantalla de "sin conexión" al abrir la app), íconos de los tres botes generados con un script de OpenCV (paleta del rediseño) y la guía de instalación. Sin bibliotecas nuevas | [COMPLETAR: probar la instalación en un celular real y que el equipo pueda explicar qué hace cada archivo] |
| Claude Code (Anthropic), skill `frontend-design` | Fase 6 (contraste y avisos): `componentes/Avisos.jsx` (barra urgente, campana), `componentes/Comun.jsx` (íconos SVG por categoría, notificaciones, cifras animadas), `componentes/Graficas.jsx`, `estilos.css` y vistas | Avisos consolidados, íconos propios para daltonismo, contraste AA, interacciones de botones, confirmaciones y gráficas mejoradas, sin bibliotecas nuevas | [COMPLETAR: revisar en un celular real y con el backend real] |
| Claude Code (Anthropic) | Fotos y desconocidos: `backend/app/camera.py` (calidad, búfer, estabilidad), `app/model.py` (`calcular_novedad`, `puntaje_novedad`, regla `desconocido`), `app/orchestrator.py`, `training/train.py`, `tools/calibrar_desconocidos.py`, `tools/probar_camara.py`, `tests/test_camara.py`, `tests/test_desconocidos.py` | Revisión de calidad de la foto (varianza del Laplaciano para nitidez, técnica clásica de OpenCV) y detección de objetos fuera de distribución por distancia coseno al centro de cada clase | [COMPLETAR: la Persona A revisa los cambios en su código; el equipo mide los umbrales con la cámara real y recalibra con fotos propias] |
| Claude Code (Anthropic) | Auditoría: `backend/tools/auditoria_usuarios.py`, `docs/resultados/auditoria_3000.md` y arreglos en `orchestrator.py` y `routes.py` (con pruebas de regresión) | Prueba de carga con usuarios virtuales (requests y websockets, ya instalados) y validación estricta de entradas | [COMPLETAR: repetir la auditoría antes de la demo con `SIMULACION=1`] |
