# Bitácora de desarrollo — Cyber Insanos · Reto 1

Registrar **cada avance o problema** con hora real. No inventar horas ni responsables: usar `[COMPLETAR]` si no se sabe.

| Fecha | Hora | Fase | Responsable | Qué se hizo | Problema | Solución |
|---|---|---|---|---|---|---|
| 2026-11-19 | [COMPLETAR] | Inicio | [COMPLETAR] | Estructura de carpetas (sección 19), README por carpeta, bitácora, recursos externos y `.gitignore`. Copia de `CLAUDE.md` y `docs/ESPECIFICACION.md` al repositorio. Generado con Claude Code. | — | — |
| 2026-11-19 | [COMPLETAR] | 0 | [COMPLETAR] | Verificación del entorno: Python 3.14.6, pip 26.2, Node 24.18.0, npm 12.0.1, git 2.55.0, Arduino IDE instalado, GPU RTX 4050 (laptop ASUS TUF). Creados `backend/requirements.txt`, `tools/verificar_hardware.py`, `tools/calcular_par.py`, `docs/mediciones.md`. | TensorFlow 2.21 no tiene ruedas para Python 3.14. | Se instaló Python 3.12.10 (winget, junto al 3.14) y el venv `backend/.venv` se creó con `py -3.12`. |
| 2026-11-19 | [COMPLETAR] | 0 | [COMPLETAR] | Descargado `vosk-model-small-es-0.42` en `backend/models/vosk-model-small-es`. Cámara índice 0 detectada (640×480, probablemente la integrada). | Los scripts fallaban al imprimir "≥" en la consola de Windows (cp1252). | `sys.stdout.reconfigure(encoding="utf-8")` en los scripts. |
| 2026-11-19 | [COMPLETAR] | 0 | [COMPLETAR] | Cálculo geométrico preliminar: con botes de 1.5 L (Ø110–130 mm) y los 3 botes en ≤ 180°, el disco debe medir ~Ø300–330 mm; Ø190 no alcanza. Propuesta de botes a 10°/90°/170° con D = 180°. | Falta medir botes, disco y masas. | Pendiente [COMPLETAR] en `docs/mediciones.md`. |
