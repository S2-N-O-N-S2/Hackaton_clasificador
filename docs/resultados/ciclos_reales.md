# Fase 5 — Ciclos reales registrados

> Solo se anotan ciclos **reales** (`SIMULACION=0`, `simulado = false` en el panel). No se inventan datos: si algo no se midió, queda `[COMPLETAR]`.
> Los datos completos de cada ciclo están en la base de datos (`backend/clasificador.db`, tabla `clasificaciones`) y en `GET /api/clasificaciones`.

## 1. Calibración de ángulos
Herramienta: `python tools\calibrar_angulos.py` (con el backend corriendo).

| Bote | Posición en el disco φ | Ángulo calibrado θ | Prueba de caída (centro de la boca: sí/no) | Fecha y hora | Quién |
|---|---|---|---|---|---|
| Orgánica (verde) | derecha (vista desde el frente) | **180°** | sí (visual, al frente y centrado) | 2026-11-20 ~09:50 | Persona A + equipo |
| Inorgánica (azul) | izquierda | **0°** | sí (visual, al frente y centrado) | 2026-11-20 ~09:50 | Persona A + equipo |
| Peligroso (gris) | frente (en reposo) | **90°** | sí (visual, al frente y centrado) | 2026-11-20 ~09:50 | Persona A + equipo |
| HOME | — | **90°** (Peligroso queda al frente) | — | 2026-11-20 ~09:50 | Persona A + equipo |

## 2. Ciclo mecánico SIN IA (resolución manual)
Mientras no haya modelo entrenado, cada residuo va a REVISIÓN (`sin_modelo`) y se resuelve con el teclado (1/2/3) o el panel. Sirve para validar el firmware, el carrusel y la trampilla (no hay sensor de caída).

| # | Hora | Residuo | Categoría dada | ¿Giró al bote correcto? | `drop_confirmado` | `tiempos_etapas` (POSICIONAR / SOLTAR ms) | Observaciones |
|---|---|---|---|---|---|---|---|
| 1 | | | | | | | |
| 2 | | | | | | | |
| 3 | | | | | | | |

## 3. Ciclos con IA — criterio de "listo" de la Fase 5 (3 de 3 correctos)
Requiere el modelo entrenado con fotos reales (`python -m training.train`). Versión del modelo: **v1** (The Garbage Dataset). Cámara: celular con DroidCam (índice 1). Arduino en COM7. Sin sensor IR: cada ciclo se inicia con «Tomar foto».

| # | Hora | Residuo (real) | Categoría real | Predicción | Confianza | ¿Dudoso? | Bote final | `drop_confirmado` | Tiempo de ciclo (ms) | ¿Correcto? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 09:56:21 | lechuga sobre papel (caso #8) | Orgánica | Orgánica | 0.927 | no | Orgánico (180°) | sí* | 4000 | **sí** |
| 2 | 09:55:58 | lata de refresco (caso #7) | Inorgánica | Inorgánica | 0.799 | no | Inorgánico (0°) | sí* | 9733 | **sí** |
| 3 | 09:56:37 | power bank / batería (caso #9) | Peligroso | Peligroso | 0.937 | **sí** (`desconocido`) | Peligroso (90°), resuelto escribiendo «pila» | sí* | 2282 | **sí**, vía revisión |
| D | 09:56:37 | el mismo caso #9 (objeto no entrenado) | — | — | — | **sí** | esperó en revisión hasta que la persona dijo qué era | — | — | **sí** |

**Resultado:** **3 de 3** residuos terminaron en el bote correcto (2 directo por la IA y 1 por revisión) y el objeto no entrenado **no se soltó** sin ayuda. Bote correcto confirmado visualmente por el equipo.

* Sin sensor de caída: `drop_confirmado` solo indica que el ciclo terminó el depósito, no que se midiera la caída. El ciclo 2 tardó 9.7 s (la captura repitió la foto por calidad).

> Pendiente para el criterio estricto: un peligroso clasificado directo por la IA (sin revisión) y repetir con las tapas conectadas.

## 4. Fallas encontradas y diagnóstico
| Hora | Síntoma | Causa (cómo se confirmó: evento, medición, log) | Solución |
|---|---|---|---|
| | | | |
