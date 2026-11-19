# Notas "Cómo defenderlo ante el jurado"

## Fase 0 — Entorno y cálculos
- **Python 3.12 y versiones congeladas:** TensorFlow no soporta 3.14. Congelamos las versiones en `requirements.lock.txt` para que todas las laptops instalen exactamente lo mismo.
- **Geometría y servo:** antes de diseñar comprobamos que los botes de 120 × 80 mm caben en medio disco, porque el servo gira 180°. Eso llevó a un disco de Ø350 y al MG996R. El par se calculó con botes llenos y factor de seguridad 2.

## Fase 3 — Backend
- **Una sola fuente de verdad:** toda la lógica de estados vive en `orchestrator.py`. El Arduino solo ejecuta comandos y el panel solo muestra lo que manda el backend. Si se cambia una regla, cambia en un solo lugar y se refleja igual en la LCD y en el panel.
- **El sistema no adivina:** si la confianza es < 0.60, si p(peligroso) ≥ 0.35 sin ser la ganadora o si no hay modelo, el residuo NO cae y pasa a REVISION. Además, `_depositar()` se niega a mandar `DROP` sin una categoría válida y sin `POS_OK` del bote correcto.
- **Falla segura:** cualquier error de serial, cámara o código lleva al estado ERROR. Ahí el disco va a HOME, la trampilla queda cerrada, se enciende el LED rojo y aparece una alerta en el panel. El supervisor regresa al MENU cuando el enlace vuelve. Lo probamos arrancando sin Arduino.
- **Modo simulación:** con `SIMULACION=1` el ciclo completo corre sin hardware. Todo dato generado así queda marcado `simulado = 1` y va a una base de datos separada (`clasificador_sim.db`). Nunca se mezcla con las mediciones reales.
- **Tiempo de máquina:** `tiempo_ciclo_ms` descuenta el tiempo que se esperó a una persona en revisión, así que el promedio del reto mide solo al sistema.
- **Cambio en vivo propuesto:** subir `UMBRAL_GENERAL` de 0.60 a 0.80 desde el panel (`PUT /api/config`), o editar `aplicar_reglas()` en `backend/app/model.py`. Un residuo que antes se aceptaba ahora va a revisión.
