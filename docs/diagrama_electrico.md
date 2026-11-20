# Diagrama eléctrico — Arduino UNO (Fase 2)

> **Cambio de diseño (20-nov-2026):** la máquina **ya no lleva LCD 20×4 ni teclado 4×4**. Todo se maneja desde la página (panel) y por voz desde la página. Lo que la LCD iba a mostrar se ve en Inicio → "Pantalla de la máquina"; lo que hacía el teclado se hace con los botones del panel o con el botón «Hablar». El firmware y el backend conservan el soporte (sin la LCD conectada no se cuelga, y sin teclado no llegan teclas), así que las menciones de LCD/teclado en este diagrama quedan como referencia histórica.
> **Pines libres:** D4–D8 y D11–D13 (eran del teclado) y A4/A5 (eran de la LCD).


> Basado en la especificación, secciones 8.1 y 8.2, y en `firmware/clasificador_uno/clasificador_uno.ino` (sección 1, "Pines").
> `[COMPLETAR]` = falta medirlo o decidirlo. **No se anotan mediciones que no se hayan hecho.**

## 1. Tabla de conexiones

| Pin UNO | Componente | Cable del componente | Nota |
|---|---|---|---|
| D0 / D1 | USB serial | — | Reservados: no conectar nada |
| D2 | FC-51 #1 (presencia en la bandeja) | OUT | Activo en BAJO. VCC → 5 V del Arduino, GND → GND |
| D3 | FC-51 #2 (confirmación de caída) | OUT | Activo en BAJO, con interrupción INT1. VCC → 5 V del Arduino, GND → GND |
| D4, D5, D6, D7 | Teclado 4×4: filas F1–F4 | Pines 1–4 del conector | Verificar el orden con el multímetro (continuidad al presionar una tecla) |
| D8, D11, D12, D13 | Teclado 4×4: columnas C1–C4 | Pines 5–8 del conector | D13 también tiene el LED "L" de la placa: parpadea al leer el teclado, es normal |
| D9 | Servo del disco (MG996R) | Naranja/amarillo (señal) | Rojo → **+V de servos (fuente externa)**, marrón/negro → GND común |
| D10 | Servo de la trampilla (SG90) | Naranja (señal) | Rojo → **+V de servos (fuente externa)**, marrón → GND común |
| A0 | LED verde | Ánodo (pata larga) a través de **220–330 Ω** | Cátodo → GND |
| A1 | LED amarillo | Ánodo a través de 220–330 Ω | Cátodo → GND |
| A2 | LED rojo | Ánodo a través de 220–330 Ω | Cátodo → GND |
| A3 | TIP120 (iluminación) | Base a través de **1 kΩ** | Emisor → GND común; colector → (−) de la tira LED; (+) de la tira → +V de la iluminación |
| A4 | LCD 20×4 I2C | SDA | VCC → 5 V del Arduino, GND → GND |
| A5 | LCD 20×4 I2C | SCL | Dirección 0x27 o 0x3F: confirmar con `firmware/escaner_i2c` |
| 5 V | FC-51 ×2, LCD | VCC | **Nunca alimentar los servos desde aquí** |
| GND | Todo | GND | Unido a la GND de la fuente de servos (tierra común) |

## 2. Alimentación

```
 Laptop (USB) ──────────► Arduino UNO ──► 5 V: LCD, FC-51 ×2, LEDs (señales)
                               │
                               GND ─────────────┐   ← tierra común (obligatoria)
                                                │
 Fuente regulada 5.5–6.0 V ──► +V servos ──┬────┼──► rojo MG996R (disco)
                    │                       │    │──► rojo SG90 (trampilla)
                    │                  [1000 µF]  │
                    │                  (+)  (−)   │
                    └──────── GND ──────────┴────┴──► marrón de ambos servos
```

| Concepto | Valor | Nota |
|---|---|---|
| Voltaje de la fuente de servos | 5.5–6.0 V [COMPLETAR valor usado] | El SG90 admite hasta ~6 V; el MG996R de 4.8 a 7.2 V. No pasar de 6.0 V |
| Capacitor | 1000 µF, ≥ 10 V (de preferencia 16 V) | **Polaridad:** la franja (−) va a GND. Lo más cerca posible de los conectores de los servos |
| Corriente pico esperada | MG996R ≈ 2.5 A (eje bloqueado, hoja de datos típica); SG90 ≈ 0.65 A | El firmware **nunca mueve los dos a la vez**, así que el pico es el del MG996R |
| Corriente que debe dar la fuente | **≥ 3 A** | Límite real de la fuente: [COMPLETAR] |
| Iluminación | [COMPLETAR: tira de 5 V o 12 V, corriente] | Con su propia alimentación, no del USB |

**Cómo verificar que la fuente alcanza:** medir el voltaje en los bornes de los servos **mientras el disco gira con los botes cargados** (`POS:0` ↔ `POS:2`). Si baja de ~4.8 V, la fuente no alcanza: subir el límite de corriente de la fuente, acortar o engrosar los cables, o revisar el capacitor.

### TIP120 (iluminación)
- Resistencia de base de **1 kΩ**: corriente de base ≈ (5 − 1.4) V / 1 kΩ ≈ 3.6 mA. Con la ganancia del Darlington (≥ 1000), alcanza para varios amperios.
- **Diodo** (por ejemplo, un 1N4007) en paralelo con la carga, con el cátodo hacia +V, **solo si la carga es inductiva** (motor, relé). Una tira LED no es inductiva, así que no hace falta.
- El TIP120 es un Darlington: entre colector y emisor se pierde ~0.8–2 V. Con una tira de **5 V** la luz puede quedar tenue; con una de **12 V** casi no se nota. Si la tira es de 5 V y consume poco (< 500 mA), un 2N2222 pierde menos (~0.3 V). Hay que medirlo (medición 2).

## 3. Cómo armarlo en un simulador

**Tinkercad Circuits** (gratis, en el navegador):
- Arduino Uno R3, "Micro servo" ×2 (para el disco y la trampilla), "Keypad 4x4", LEDs con resistencias y un "NPN transistor" en lugar del TIP120.
- Tinkercad no tiene una LCD 20×4 I2C: usar la "LCD 16x2 (I2C)" y cambiar `LCD_COLUMNAS`/`LCD_FILAS` solo para la simulación.
- Tampoco tiene el FC-51: simularlo con un **botón** entre D2 (o D3) y GND, porque el sensor es activo en BAJO y el pin usa `INPUT_PULLUP`.
- Agregar una "Power supply" de 6 V para los servos, con su GND unida a la del Arduino.

**Fritzing:** sí tiene LCD I2C, TIP120, teclado 4×4 y servos. Seguir la tabla de la sección 1 y exportar la vista de protoboard como imagen para la memoria técnica.

---

## 4. Checklist de mediciones con el multímetro (Steren MUL-281)

Registrar cada medición con la hora y quién la hizo, aquí y en `docs/bitacora.md`.

| # | Medición | Cómo | Esperado | Medido | Quién / hora |
|---|---|---|---|---|---|
| 1a | Voltaje de los servos **en reposo** | DCV, puntas en +V y GND del conector de los servos. Todo encendido, sin movimiento | 5.5–6.0 V (lo que marca la fuente) | [COMPLETAR] | |
| 1b | Voltaje de los servos **en movimiento** | Igual que 1a, mientras se manda `POS:0` y `POS:2` con los botes puestos. Leer el valor más bajo | ≥ 4.8 V | [COMPLETAR] | |
| 2 | Voltaje en la iluminación | DCV en los bornes (+) y (−) de la tira con `LIGHT:ON`. Medir también colector–emisor del TIP120 | Tira: cerca de su voltaje nominal. C–E: ~0.8–2 V | [COMPLETAR] | |
| 3 | Continuidad de la GND común | **Todo apagado.** Modo continuidad (pitido) entre la GND de la fuente de servos y un pin GND del Arduino | Pitido, < 1 Ω | [COMPLETAR] | |

## 5. Falla diagnosticable: servos alimentados desde el 5 V del Arduino

**Qué pasa:** el pin de 5 V del UNO viene del USB (~500 mA, con un fusible reajustable). Cuando un servo arranca o se frena, pide un pico de corriente; el voltaje cae por debajo de ~4.3 V y el microcontrolador **se reinicia** por bajo voltaje (*brown-out*).

**Síntomas:**
- En el Monitor Serial aparece **`READY`** otra vez sin que nadie haya presionado reset.
- La LCD vuelve a mostrar "Esperando PC..." y el disco salta a HOME.
- `STATUS` muestra `ang=90` aunque se había mandado otro ángulo.
- A veces Windows desconecta y vuelve a conectar el puerto COM.

**Cómo provocarla de forma segura (solo para la demostración):**
1. Usar **solo el SG90**, nunca el MG996R: su pico de ~2.5 A puede dañar el puerto USB o el regulador.
2. Desconectar el servo del disco. Conectar el SG90 a D9 con su rojo al **5 V del Arduino** (en vez de a la fuente externa).
3. En el Monitor Serial, mandar `ANG:0`, luego `ANG:180` y luego `ANG:0` varias veces. Si no se reinicia, frenar **suavemente** la cruceta con los dedos durante el movimiento (es lo que pasa con un disco pesado).
4. Medir en DCV entre 5 V y GND del Arduino durante el movimiento: se ve la caída de voltaje.
5. Terminar en menos de un minuto y regresar el rojo del servo a la fuente externa.

**Cómo diagnosticarla:** el `READY` inesperado indica que el Arduino se reinició, y el multímetro en el pin de 5 V muestra la caída. Al pasar el servo a la fuente externa con tierra común y el capacitor de 1000 µF, la falla desaparece: hay que repetir la prueba y anotarla.

---

## 6. Cómo defenderlo ante el jurado

- **Alimentación separada:** "Los servos piden picos de hasta 2.5 A y el USB del Arduino da 0.5 A. Los alimentamos con una fuente aparte, con tierra común para que la señal PWM tenga la misma referencia, y un capacitor de 1000 µF que absorbe los picos. Si se conectan al 5 V del Arduino, la placa se reinicia: lo demostramos y lo medimos."
- **Un servo a la vez:** "El firmware rechaza (`ERR:OCUPADO`) cualquier movimiento mientras el otro servo trabaja. Así el pico de corriente nunca es la suma de los dos."
- **TIP120:** "Un pin del Arduino da como máximo ~20 mA y la tira LED pide más. El transistor funciona como interruptor: el pin solo maneja ~4 mA de base."
