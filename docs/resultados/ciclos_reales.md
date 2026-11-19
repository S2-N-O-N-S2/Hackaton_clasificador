# Fase 5 — Ciclos reales registrados

> Solo se anotan ciclos **reales** (`SIMULACION=0`, `simulado = false` en el panel). No se inventan datos: si algo no se midió, queda `[COMPLETAR]`.
> Los datos completos de cada ciclo están en la base de datos (`backend/clasificador.db`, tabla `clasificaciones`) y en `GET /api/clasificaciones`.

## 1. Calibración de ángulos
Herramienta: `python tools\calibrar_angulos.py` (con el backend corriendo).

| Bote | Posición en el disco φ | Ángulo calibrado θ | Prueba de caída (centro de la boca: sí/no) | Fecha y hora | Quién |
|---|---|---|---|---|---|
| Orgánica (verde) | [COMPLETAR] | [COMPLETAR] | [COMPLETAR] | | |
| Inorgánica (azul) | [COMPLETAR] | [COMPLETAR] | [COMPLETAR] | | |
| Peligroso (gris) | [COMPLETAR] | [COMPLETAR] | [COMPLETAR] | | |
| HOME | — | [COMPLETAR] | — | | |

## 2. Ciclo mecánico SIN IA (resolución manual)
Mientras no haya modelo entrenado, cada residuo va a REVISIÓN (`sin_modelo`) y se resuelve con el teclado (1/2/3) o el panel. Sirve para validar el firmware, el carrusel, la trampilla y el sensor de caída.

| # | Hora | Residuo | Categoría dada | ¿Giró al bote correcto? | `drop_confirmado` | `tiempos_etapas` (POSICIONAR / SOLTAR ms) | Observaciones |
|---|---|---|---|---|---|---|---|
| 1 | | | | | | | |
| 2 | | | | | | | |
| 3 | | | | | | | |

## 3. Ciclos con IA — criterio de "listo" de la Fase 5 (3 de 3 correctos)
Requiere el modelo entrenado con fotos reales (`python -m training.train`). Versión del modelo: [COMPLETAR].

| # | Hora | Residuo (real) | Categoría real | Predicción | Confianza | ¿Dudoso? | Bote final | `drop_confirmado` | Tiempo de ciclo (ms) | ¿Correcto? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | | (orgánico) | Orgánica | | | | | | | |
| 2 | | (inorgánico) | Inorgánica | | | | | | | |
| 3 | | (peligroso simulado) | Peligroso | | | | | | | |
| D | | (objeto dudoso o no entrenado) | — | | | debe ser **sí** | queda en la bandeja | — | — | |

**Resultado:** [COMPLETAR] de 3 ciclos correctos.

## 4. Fallas encontradas y diagnóstico
| Hora | Síntoma | Causa (cómo se confirmó: evento, medición, log) | Solución |
|---|---|---|---|
| | | | |
