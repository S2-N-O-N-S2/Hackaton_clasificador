# Auditoría con 3000 usuarios virtuales — SIMULADO

- Fecha: 2026-11-19 17:20  ·  Backend: `http://127.0.0.1:8010` con `SIMULACION=1` y `SIM_RAPIDO=1`
- Usuarios: {'espectador': 1793, 'corrector': 304, 'jugador': 620, 'operador': 283}  ·  hasta 200 a la vez  ·  semilla 2026
- Duración: 69 s  ·  peticiones HTTP: 33056  ·  WebSockets abiertos: 1793 (fallidos: 0, mensajes: 187819)
- Ciclos de la máquina: 77  ·  residuos soltados: 73  ·  estado final: **MENU**
- Tiempo de respuesta (todas): mediana 5 ms, p95 162 ms, p99 316 ms, máximo 754 ms
- Códigos HTTP: {200: 29718, 400: 278, 404: 229, 409: 1309, 422: 1522}  ·  501 = función de la Fase 8 todavía pendiente (acordado en el contrato, no es falla): 0

## Resultado: SIN HALLAZGOS GRAVES (0 hallazgos en total)

Graves = error del servidor (5xx), conexión caída, regla de seguridad rota o historial incoherente.

## Hallazgos agrupados

| Tipo | Detalle | Veces |
|---|---|---|
| — | Ninguno | 0 |

## Tiempos por ruta (ms)

| Ruta | n | mediana | p95 | máx | lentas (>1 s) |
|---|---|---|---|---|---|
| `GET /api/estadisticas` | 1360 | 8 | 191 | 547 | 0 |
| `POST /api/clasificaciones/{id}/corregir` | 963 | 9 | 190 | 552 | 0 |
| `GET /api/botes` | 644 | 7 | 189 | 507 | 0 |
| `GET /captures/{foto}` | 3607 | 5 | 185 | 754 | 0 |
| `GET /api/modelo/estado` | 634 | 8 | 184 | 547 | 0 |
| `GET /api/clasificaciones` | 4165 | 7 | 181 | 562 | 0 |
| `GET /api/juego/sesion` | 1284 | 6 | 177 | 514 | 0 |
| `GET /api/pruebas` | 617 | 6 | 177 | 541 | 0 |
| `GET /api/dataset/por-verificar` | 647 | 6 | 167 | 553 | 0 |
| `GET /api/config` | 936 | 5 | 167 | 507 | 0 |
| `GET /api/juego/aprendizaje` | 637 | 6 | 162 | 494 | 0 |
| `GET /api/juego/estadisticas` | 645 | 7 | 162 | 512 | 0 |
| `GET /api/modo` | 703 | 6 | 159 | 526 | 0 |
| `GET /api/estado` | 13221 | 5 | 154 | 564 | 0 |
| `POST /api/juego/adivinar` | 54 | 3 | 143 | 223 | 0 |
| `POST /api/botes/{id}/vaciar` | 65 | 14 | 97 | 166 | 0 |
| `POST /api/pruebas` | 58 | 3 | 92 | 126 | 0 |
| `POST /api/modo` | 903 | 7 | 85 | 299 | 0 |
| `PUT /api/botes/{id}` | 85 | 2 | 82 | 136 | 0 |
| `POST /api/sim/tecla` | 42 | 3 | 67 | 84 | 0 |
| `PUT /api/config` | 539 | 3 | 61 | 137 | 0 |
| `POST /api/manual/home` | 8 | 2 | 60 | 60 | 0 |
| `POST /api/revision` | 134 | 2 | 57 | 135 | 0 |
| `POST /api/dataset/por-verificar` | 28 | 2 | 56 | 114 | 0 |
| `POST /api/sim/objeto` | 777 | 4 | 53 | 212 | 0 |
| `GET /api/no-existe` | 28 | 2 | 37 | 53 | 0 |
| `POST /api/sim/retirar` | 12 | 3 | 31 | 169 | 0 |
| `POST /api/manual/ang` | 18 | 3 | 28 | 53 | 0 |
| `POST /api/manual/light` | 7 | 3 | 26 | 26 | 0 |
| `POST /api/manual/pos` | 27 | 2 | 24 | 109 | 0 |
| `POST /api/manual/explotar` | 32 | 2 | 24 | 73 | 0 |
| `POST /api/juego/prueba-aprendizaje` | 64 | 3 | 23 | 59 | 0 |
| `POST /api/pruebas/residuos` | 100 | 2 | 18 | 94 | 0 |
| `POST /api/manual/led` | 12 | 2 | 13 | 16 | 0 |

## Historial al terminar

- Casos: 77  ·  por estado: {'registrado': 73, 'pendiente': 4}
- Motivos de revisión: {'desconocido': 1, 'confianza_baja': 5, 'foto_no_valida': 2}
- Corregidos desde el panel DESPUÉS de caer (el residuo sigue en el otro bote; el panel pide moverlo a mano): 41
- Estados vistos por el monitor: {'ESPERA_OBJETO': 144, 'CAPTURA': 77, 'CLASIFICACION': 77, 'ESPERA_ADIVINANZA': 25, 'VERIFICAR_BOTE': 73, 'POSICIONAR': 73, 'SOLTAR': 73, 'REGISTRAR': 73, 'ACTUALIZAR_NIVEL': 73, 'HOME': 73, 'MENU': 77, 'REVISION': 8, 'PENDIENTE': 4}

## Ejemplos de hallazgos (máx. 25)

```json
```

_Datos SIMULADOS: usuarios virtuales contra el backend en simulación; no son mediciones con personas ni con el Arduino._
## Qué encontraron las corridas anteriores y cómo se arregló

Esta es la corrida final (0 hallazgos), hecha después de juntar la voz (Fase 9) de main. Las corridas anteriores, con la misma herramienta, encontraron lo siguiente.
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
