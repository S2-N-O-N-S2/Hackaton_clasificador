# Auditoría con 3000 usuarios virtuales — SIMULADO

- Fecha: 2026-11-19 17:16  ·  Backend: `http://127.0.0.1:8010` con `SIMULACION=1` y `SIM_RAPIDO=1`
- Usuarios: {'espectador': 1793, 'corrector': 304, 'jugador': 620, 'operador': 283}  ·  hasta 200 a la vez  ·  semilla 2026
- Duración: 70 s  ·  peticiones HTTP: 32290  ·  WebSockets abiertos: 1793 (fallidos: 0, mensajes: 175493)
- Ciclos de la máquina: 80  ·  residuos soltados: 76  ·  estado final: **MENU**
- Tiempo de respuesta (todas): mediana 10 ms, p95 244 ms, p99 355 ms, máximo 553 ms
- Códigos HTTP: {200: 28896, 400: 280, 404: 226, 409: 1366, 422: 1522}  ·  501 = función de la Fase 8 todavía pendiente (acordado en el contrato, no es falla): 0

## Resultado: SIN HALLAZGOS GRAVES (0 hallazgos en total)

Graves = error del servidor (5xx), conexión caída, regla de seguridad rota o historial incoherente.

## Hallazgos agrupados

| Tipo | Detalle | Veces |
|---|---|---|
| — | Ninguno | 0 |

## Tiempos por ruta (ms)

| Ruta | n | mediana | p95 | máx | lentas (>1 s) |
|---|---|---|---|---|---|
| `GET /captures/{foto}` | 3607 | 8 | 301 | 553 | 0 |
| `GET /api/pruebas` | 617 | 19 | 281 | 455 | 0 |
| `GET /api/estadisticas` | 1360 | 20 | 275 | 479 | 0 |
| `GET /api/botes` | 644 | 18 | 273 | 467 | 0 |
| `POST /api/clasificaciones/{id}/corregir` | 970 | 13 | 268 | 471 | 0 |
| `GET /api/juego/estadisticas` | 645 | 17 | 262 | 442 | 0 |
| `GET /api/clasificaciones` | 4165 | 15 | 261 | 472 | 0 |
| `GET /api/juego/aprendizaje` | 637 | 11 | 253 | 469 | 0 |
| `GET /api/config` | 936 | 14 | 251 | 470 | 0 |
| `GET /api/estado` | 12443 | 10 | 237 | 509 | 0 |
| `GET /api/modelo/estado` | 634 | 15 | 237 | 441 | 0 |
| `GET /api/juego/sesion` | 1284 | 15 | 234 | 470 | 0 |
| `GET /api/modo` | 703 | 11 | 223 | 492 | 0 |
| `GET /api/dataset/por-verificar` | 647 | 13 | 208 | 472 | 0 |
| `POST /api/botes/{id}/vaciar` | 65 | 15 | 121 | 264 | 0 |
| `POST /api/dataset/por-verificar` | 28 | 4 | 116 | 136 | 0 |
| `POST /api/modo` | 908 | 10 | 106 | 224 | 0 |
| `PUT /api/botes/{id}` | 85 | 3 | 96 | 334 | 0 |
| `POST /api/sim/tecla` | 42 | 3 | 95 | 100 | 0 |
| `POST /api/juego/adivinar` | 54 | 6 | 93 | 420 | 0 |
| `PUT /api/config` | 539 | 4 | 89 | 233 | 0 |
| `POST /api/manual/pos` | 27 | 5 | 88 | 115 | 0 |
| `POST /api/juego/prueba-aprendizaje` | 64 | 5 | 84 | 98 | 0 |
| `POST /api/sim/objeto` | 777 | 6 | 83 | 265 | 0 |
| `POST /api/pruebas` | 58 | 4 | 78 | 216 | 0 |
| `POST /api/pruebas/residuos` | 100 | 4 | 75 | 138 | 0 |
| `POST /api/revision` | 134 | 4 | 74 | 204 | 0 |
| `POST /api/manual/explotar` | 32 | 4 | 60 | 128 | 0 |
| `POST /api/manual/home` | 8 | 2 | 58 | 58 | 0 |
| `POST /api/sim/retirar` | 12 | 4 | 47 | 55 | 0 |
| `POST /api/manual/light` | 7 | 4 | 38 | 38 | 0 |
| `GET /api/no-existe` | 28 | 4 | 28 | 106 | 0 |
| `POST /api/manual/led` | 12 | 8 | 23 | 38 | 0 |
| `POST /api/manual/ang` | 18 | 7 | 17 | 34 | 0 |

## Historial al terminar

- Casos: 80  ·  por estado: {'registrado': 76, 'pendiente': 4}
- Motivos de revisión: {'foto_no_valida': 5, 'confianza_baja': 3, 'desconocido': 2}
- Corregidos desde el panel DESPUÉS de caer (el residuo sigue en el otro bote; el panel pide moverlo a mano): 39
- Estados vistos por el monitor: {'ESPERA_OBJETO': 87, 'CAPTURA': 80, 'CLASIFICACION': 80, 'ESPERA_ADIVINANZA': 20, 'VERIFICAR_BOTE': 76, 'POSICIONAR': 76, 'SOLTAR': 76, 'REGISTRAR': 76, 'ACTUALIZAR_NIVEL': 76, 'HOME': 76, 'MENU': 80, 'REVISION': 10, 'PENDIENTE': 4}

## Ejemplos de hallazgos (máx. 25)

```json
```

_Datos SIMULADOS: usuarios virtuales contra el backend en simulación; no son mediciones con personas ni con el Arduino._
## Qué encontraron las corridas anteriores y cómo se arregló

Esta es la corrida final (0 hallazgos). Las corridas anteriores, con la misma herramienta, encontraron lo siguiente.
Todo se corrigió y quedó cubierto por pruebas de pytest (`tests/test_ciclo_simulado.py`, sección "Regresiones").

| # | Hallazgo | Gravedad | Arreglo |
|---|---|---|---|
| 1 | Un residuo colocado mientras el ciclo anterior terminaba (registrar / HOME) **se perdía**: el `OBJ` del sensor se ignoraba, y como el firmware lo manda una sola vez, el residuo quedaba en la bandeja sin clasificar | Alta | El orquestador recuerda ese `OBJ` y procesa el residuo al volver al menú |
| 2 | Mientras el disco giraba (POSICIONAR, SOLTAR), el panel recibía `final_id = null`: el carrusel no mostraba el bote destino | Media | El destino se guarda en cuanto se decide |
| 3 | `true` se aceptaba como categoría 1 (corregir, adivinar, simular) | Media | `StrictInt` en las entradas |
| 4 | Tiempos de 10¹² s (una revisión que nunca vence), tiempos de prueba negativos, nombres de 5000 caracteres, ángulos con decimales y NaN/infinito se aceptaban | Media | Validación con límites: tiempos 1–600 s, nombres 1–80 caracteres, números finitos y enteros sin decimales |
| 5 | Dos operadores aprobando la misma etiqueta a la vez podían provocar un error 500 | Baja | Responde 404 «ya fue revisada» |
| 6 | Corregir un caso **después** de que cayó cambia el dato, pero el residuo sigue físicamente en el otro bote (24–39 casos por corrida) | Operación | No es una falla del software: ahora el panel avisa «muévelo a mano al bote X» |

Datos SIMULADOS. Lo que esta auditoría **no** prueba: personas reales, el Arduino, la cámara real ni la red Wi-Fi del evento.
