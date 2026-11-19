# Prueba del firmware desde el Monitor Serial (Fase 2)

> Firmware: `firmware/clasificador_uno/clasificador_uno.ino`. Protocolo: especificación, sección 9, y `docs/api_contrato.md`, sección 5.

## 1. Preparación

1. Arduino IDE 2.x → **Herramientas → Placa → Arduino UNO** y elegir el puerto `COMx`.
2. Bibliotecas (Gestor de bibliotecas): **LiquidCrystal I2C** (Frank de Brabander) y **Keypad** (Mark Stanley, Alexander Brevig).
3. Si la LCD no muestra nada, cargar primero `firmware/escaner_i2c/escaner_i2c.ino`, anotar la dirección y cambiar `LCD_DIRECCION`.
4. Cargar `clasificador_uno.ino`.
5. **Monitor Serial:** 115 200 baudios y fin de línea **"Nueva línea"**.

> **Watchdog durante la prueba manual:** si pasan **15 s sin escribir nada**, aparece `WATCHDOG`, el disco regresa a HOME y la LCD dice "SIN ENLACE CON PC". Es el comportamiento correcto. El siguiente comando funciona normalmente.

Para probar sin la estructura física basta un servo en D9 (o en D10 para la trampilla), la LCD, el teclado, un FC-51 y los LEDs. Para el FC-51 #2 se puede pasar la mano frente al sensor.

## 2. Comandos y respuestas esperadas

Los ángulos de ejemplo suponen la EEPROM vacía (valores por defecto 170 / 90 / 10 y HOME 90).

| # | Escribir | Respuesta esperada | Qué debe verse |
|---|---|---|---|
| 1 | *(presionar reset)* | `READY` | Trampilla cerrada, disco en 90°, LCD "== CLASIFICADOR ==" |
| 2 | `PING` | `PONG` | — |
| 3 | `ping` | `PONG` | El nombre del comando no distingue mayúsculas |
| 4 | `STATUS` | `STATUS:ang=90,tramp=CERRADA,obj=0,cal=170/90/10` | — |
| 5 | `POS:0` | `POS_OK:0` después de ~1.6 s | El disco sube suavemente de 90° a 170° |
| 6 | `POS:2` | `POS_OK:2` después de ~3.4 s | Baja hasta 5° y **sube** a 10° (llega siempre desde abajo) |
| 7 | `POS:0` y, enseguida, `POS:1` | `ERR:OCUPADO`, luego `POS_OK:0` | El segundo movimiento se rechaza |
| 8 | `POS:3` · `POS` · `POS:x` | `ERR:ARG` (las tres) | Nada se mueve |
| 9 | `ANG:45` | `ANG_OK:45` | El disco va a 45° |
| 10 | `ANG:181` | `ERR:ANG_RANGO` | — |
| 11 | `ANG:abc` · `ANG:-5` | `ERR:ARG` | — |
| 12 | `HOME` | `HOME_OK` | El disco vuelve a 90° |
| 13 | `DROP` (pasando la mano frente al FC-51 #2) | `DROP_OK` a los ~0.9 s | La trampilla abre 600 ms y cierra; la respuesta llega **con la trampilla ya cerrada** |
| 14 | `DROP` (sin pasar nada) | `DROP_TIMEOUT` a los 2 s | Igual que el anterior |
| 15 | `DROP` y, enseguida, `HOME` | `ERR:OCUPADO`, luego `DROP_OK` o `DROP_TIMEOUT` | — |
| 16 | `LIGHT:ON` · `LIGHT:OFF` | `OK` · `OK` | La iluminación se enciende y se apaga |
| 17 | `LIGHT:X` | `ERR:ARG` | — |
| 18 | `LED:VERDE` | `OK` | Verde fijo; los demás apagados |
| 19 | `LED:ROJO:PARPADEO` | `OK` | Rojo parpadeando |
| 20 | `LED:OFF` | `OK` | Todos apagados |
| 21 | `LED:AZUL` · `LED:VERDE:RAPIDO` | `ERR:ARG` | — |
| 22 | `LCD:Hola\|Linea dos\|Linea tres\|IA 92%  Ac: 4/5` | `OK` | Las 4 líneas, respetando mayúsculas y minúsculas |
| 23 | `LCD:Solo una linea` | `OK` | Líneas 2–4 en blanco |
| 24 | `LCD:Esta linea mide mas de veinte caracteres` | `OK` | Se recorta a 20 |
| 25 | `LCD_SCROLL:Proviene de un ser vivo y se descompone naturalmente` | `OK` | El texto se desplaza en la línea 4 |
| 26 | `LCD:Árbol` | `OK` | Se ve `??rbol`: el backend debe quitar los acentos antes de enviar (lo hace `lcd_ui.py`) |
| 27 | `CAL:0:165` | `CAL_OK:0:165` | `STATUS` muestra `cal=165/90/10` |
| 28 | *(reset)* y luego `STATUS` | `READY`, luego `...cal=165/90/10` | La calibración sobrevive al reinicio (EEPROM) |
| 29 | `CAL:3:10` · `CAL:0` · `CAL:x:10` | `ERR:ARG` | — |
| 30 | `CAL:0:200` | `ERR:ANG_RANGO` | — |
| 31 | `CAL:0:170` | `CAL_OK:0:170` | Deja el valor por defecto otra vez |
| 32 | `FOO` · `PING:1` | `ERR:CMD_DESCONOCIDO` · `ERR:ARG` | — |
| 33 | `LCD:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX` (más de 80 caracteres) | `ERR:LINEA_LARGA` | La LCD no cambia |
| 34 | *(poner la mano frente al FC-51 #1 ≥ 0.3 s)* | `OBJ` (una sola vez) | — |
| 35 | *(retirar la mano ≥ 0.3 s)* | `LIBRE` (una sola vez) | — |
| 36 | *(presionar cada tecla)* | `KEY:1` … `KEY:D`, `KEY:*`, `KEY:#` | Una línea por tecla |
| 37 | `POS:0`, y luego **no escribir nada 15 s** | `POS_OK:0` … y a los 15 s `WATCHDOG` | El disco regresa a 90°; la LCD dice "SIN ENLACE CON PC" |
| 38 | `PING` (después del watchdog) | `PONG` | Todo funciona otra vez |

Si alguna respuesta no coincide, anotar el número de prueba y lo que salió en `docs/bitacora.md`.

## 3. Ajustes que se hacen con el hardware armado

Todos están en la sección 2 de `clasificador_uno.ino`:

| Constante | Valor actual | Qué medir |
|---|---|---|
| `LCD_DIRECCION` | 0x27 | Resultado del escáner I2C [COMPLETAR] |
| `ANG_TRAMPILLA_CERRADA` / `ANG_TRAMPILLA_ABIERTA` | 0 / 90 | Ángulos reales del mecanismo [COMPLETAR] |
| `PASO_DISCO_MS` | 20 | Subirlo si los botes se mueven o derraman |
| Ángulos de los botes | 170 / 90 / 10 | Se calibran con `ANG` + `CAL` (Fase 5), no editando el código |

Los FC-51 tienen un potenciómetro: ajustarlo para que el LED del módulo se encienda con el objeto y se apague sin él.

## 4. Notas para la Persona A (backend)

Nada de esto cambia el contrato; son detalles que el backend debe tomar en cuenta:

1. **Timeout de `POS`.** La especificación (sección 10.6) dice 3 s, pero con la rampa de 1° cada 20 ms el peor caso (de 170° a 10°, con sobrepaso) tarda **~3.4 s**. Sugerencia: un timeout de **5 s** para `POS`, `ANG` y `HOME`, o calcularlo como `(|Δ| + 10) × 20 ms + 1 s`.
2. **`DROP_OK` llega con la trampilla ya cerrada**, entre 0.9 y 2 s después de `DROP`. Usar un timeout de ~3 s. Así, después de `DROP_OK` se puede mandar `HOME` sin recibir `ERR:OCUPADO`.
3. **Esperar la respuesta de cada comando antes de mandar el siguiente.** El búfer serial del UNO es de 64 bytes.
4. **Al abrir el puerto, el UNO se reinicia solo** (DTR). Esperar `READY` (~2–3 s) antes de mandar comandos.
5. **El ángulo de HOME no se puede cambiar por serial:** `GET /api/config` tiene `angulo_home`, pero el contrato no define un comando para mandarlo. Si se necesita, hay que acordar un agregado (versión 1.1 del contrato).
6. Cuando el residuo cae, también llega **`LIBRE`** (antes de `DROP_OK`).
7. Después de `WATCHDOG`, el Arduino acepta comandos normalmente; el backend debe volver a mandar `LCD` y `LED`.
