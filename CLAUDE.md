# CLAUDE.md — Clasificador inteligente de residuos (Cyber Insanos · HACKATHÓN TESCo 2026 · Reto 1)

## Qué es este proyecto
Prototipo de clasificador de residuos en **ciclo cerrado** para un hackatón de ~17 h (jue 19 nov 7:00–20:00 y vie 20 nov 7:00–13:00).
Un residuo se coloca en una bandeja → sensor IR lo detecta → cámara cenital lo fotografía → IA (MobileNetV2) lo clasifica en
**Orgánica (0, verde) · Inorgánica (1, azul) · Peligroso (2, gris)** → un **disco giratorio (carrusel)** coloca el bote correcto bajo
una trampilla → la trampilla se abre → todo se registra en SQLite y se muestra en un panel React.
Incluye: modo **"¿Le ganas a la IA?"** con menú, retroalimentación explicada con nivel de certeza y curva de aprendizaje,
**aviso de bote lleno (estimado)**, voz offline y reentrenamiento con correcciones.

**La especificación completa y obligatoria está en `docs/ESPECIFICACION.md`.** Léela (al menos las secciones que aplican) antes de cada fase.
Si este archivo y la especificación se contradicen, manda la especificación; avísalo.

## Stack (no agregar otros lenguajes ni servicios en la nube)
| Capa | Tecnología |
|---|---|
| Orquestador / backend | Python 3 + FastAPI (uvicorn) |
| Visión | OpenCV |
| IA | MobileNetV2 (Keras) como extractor + scikit-learn (LogisticRegression); alternativa: cabeza densa en Keras |
| Voz offline | Vosk (`vosk-model-small-es`) + `data/keywords.json` |
| Microcontrolador | C++ Arduino UNO (`Servo`, `LiquidCrystal_I2C`, `Keypad`) |
| Comunicación | Serial USB, pyserial, 115200 baudios, protocolo de texto (sección 9 de la especificación) |
| Base de datos | SQLite (`sqlite3` de la biblioteca estándar) |
| Panel | React + Vite, REST + WebSocket |

Cualquier dependencia nueva: justifícala y **pide confirmación antes de instalarla**.

## Entorno
- Laptops con **Windows 11** (PowerShell). Usa comandos de PowerShell en las instrucciones que des.
- Entorno virtual: `python -m venv .venv` y `.\.venv\Scripts\Activate.ps1` dentro de `backend/`.
- El Arduino aparece como `COMx`; la cámara por índice de OpenCV. Ambos van en configuración, nunca fijos en el código.
- La red del evento puede ser lenta o inexistente: avisa de cualquier descarga grande antes de hacerla.

## Estructura del repositorio
```
firmware/clasificador_uno/clasificador_uno.ino
backend/app/        main.py config.py serial_link.py camera.py model.py voice.py orchestrator.py
                    game.py bins.py lcd_ui.py db.py routes.py
backend/training/   capturar_dataset.py train.py evaluate.py
backend/data/       keywords.json explicaciones.json
backend/dataset/    organica/ inorganica/ peligroso/ _por_verificar/
backend/models/  backend/captures/  backend/tests/
frontend/           (Vite + React)
cad/                (SolidWorks lo modela el equipo; aquí van especificaciones y archivos exportados)
docs/               ESPECIFICACION.md bitacora.md recursos_externos.md memoria_tecnica.md
                    diagrama_electrico.md resultados/
```

## Comandos
- Backend: `cd backend; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000`
- Backend sin hardware: variable `SIMULACION=1` (serial simulado + imágenes de carpeta)
- Pruebas: `cd backend; python -m pytest -q`
- Frontend: `cd frontend; npm run dev -- --host`
- Firmware: Arduino IDE (placa Arduino UNO); prueba manual desde el Monitor Serial a 115200, fin de línea `\n`.

## Reglas de trabajo (obligatorias)
1. **Trabaja por fases** (sección 22 de la especificación). No empieces una fase sin que la anterior cumpla su criterio de "listo", salvo que se indique trabajo en paralelo.
2. **Antes de programar**, presenta un plan corto: archivos que vas a crear o modificar, supuestos y lo que el equipo debe medir. Marca lo desconocido como `[COMPLETAR]`. Espera aprobación si el cambio es grande.
3. **El ciclo cerrado con cámara es la prioridad.** Las innovaciones (fases 7–9) solo van cuando la fase 5 es estable.
4. **Seguridad ante fallas:** si se pierde el serial, la cámara o el modelo → trampilla cerrada, disco en HOME, aviso en el panel. Nunca soltar un residuo sin categoría válida ni a un bote lleno.
5. **La lógica de estados vive solo en Python** (`orchestrator.py`). El Arduino ejecuta comandos y reporta sensores y teclas.
6. **Toda configuración en un solo lugar** (`config.py` + tabla `config`). Nada de valores mágicos dispersos.
7. **Nunca inventes mediciones ni resultados.** Todo dato simulado se marca como `simulado` en la BD y como **SIMULADO** en el panel; todo nivel de bote se rotula **ESTIMADO**.
8. Comentarios, mensajes de interfaz y documentación **en español**. Código legible, modular, con manejo de errores en cada frontera (serial, cámara, modelo, BD, voz).
9. Textos para la LCD 20×4: máximo 20 caracteres por línea y **sin acentos** (usa la función de `lcd_ui.py`).
10. Escribe **pruebas con pytest** para la lógica pura (reglas de decisión, protocolo, juego, botes, aprendizaje) y ejecútalas antes de dar una fase por terminada.
11. **Al terminar cada fase:**
    - Di exactamente cómo probarla (comandos) y qué debe verse si funciona.
    - Agrega una entrada en `docs/bitacora.md` (hora, fase, qué se hizo, problemas, solución).
    - Actualiza `docs/recursos_externos.md` (bibliotecas, modelos, código de referencia y qué partes generó la IA vs. qué modificó el equipo).
    - Agrega 2–3 líneas de **"Cómo defenderlo ante el jurado"** para las decisiones importantes.
    - Propón un commit con mensaje `fase N: <resumen>`.
12. Mantén la solución simple: lo que no aporte al reto o a la rúbrica se propone como ampliación, no se implementa.
13. El equipo debe poder explicar y modificar todo. Si algo es complejo, explícalo en términos sencillos.
