# ESPECIFICACIÓN — Clasificador inteligente de residuos con carrusel giratorio
### Equipo Cyber Insanos · HACKATHÓN TESCo 2026 · Reto 1
**Versión 3** — incluye el **modo "¿Le ganas a la IA?"** con menú de selección, retroalimentación explicada **que muestra la confianza de la IA y ajusta su tono**, **medición de la curva de aprendizaje** y el **aviso de bote lleno (estimado)**.

> **Cambio de diseño (20-nov-2026):** la máquina **ya no lleva LCD 20×4 ni teclado 4×4**. Todo se maneja desde la página (panel) y por voz desde la página. Lo que la LCD iba a mostrar se ve en Inicio → "Pantalla de la máquina"; lo que hacía el teclado se hace con los botones del panel o con el botón «Hablar». El firmware y el backend conservan el soporte (sin la LCD conectada no se cuelga, y sin teclado no llegan teclas), así que las menciones de LCD/teclado en este documento quedan como referencia histórica.

---

## 1. Rol que debes asumir

Actúa como **ingeniero líder de un equipo multidisciplinario** (sistemas embebidos, visión por computadora, backend, frontend y diseño mecánico) que guía a estudiantes de ingeniería durante un hackatón de ~17 horas. Tu trabajo es **diseñar, programar y documentar** un prototipo funcional, explicando cada decisión técnica de forma que el equipo pueda **defenderla ante un jurado** que hará preguntas a cualquier integrante.

Prioridades, en este orden:
1. **Que el sistema completo funcione en vivo** (ciclo cerrado sin intervención).
2. **Que sea seguro** (eléctrica y mecánicamente).
3. **Que el equipo entienda y pueda modificar** todo lo que generes.
4. Que sea elegante y escalable.

---

## 2. Contexto del evento y restricciones

| Restricción | Detalle |
|---|---|
| Tiempo | Jueves 19 nov 2026, 7:00–20:00 y viernes 20 nov 2026, 7:00–13:00. |
| Impresión 3D | Hoy hasta las 16:00 (última pieza que termine antes de las 19:00) y mañana de 7:00 a 9:00. **Ninguna pieza puede exceder 3 h de impresión.** Impresoras: Ender 3 S1 Pro, Ender 3 V2, Kingroon KP3S, Bambu Lab A1 mini. Filamento: PLA 1.75 mm. |
| Originalidad | Se permiten bibliotecas, tutoriales e IA generativa **con atribución**. Todo debe ser explicable por el equipo. |
| Datos | Los datos simulados deben **identificarse como simulados**; nunca presentarlos como mediciones reales. |
| Seguridad | Prohibido usar materiales peligrosos reales. Los residuos "peligrosos" del set de prueba son **simulados** (pila descargada sin daño, envase vacío de medicamento, blíster vacío). Servos con alimentación separada. |
| Software | Debe correr **localmente** en laptops con Windows 11 (MSI Katana RTX 4060 / ASUS TUF RTX 4050). La conectividad a internet puede ser limitada: indica qué descargar por adelantado. |

---

## 3. El reto (resumen de lo que se evalúa)

Construir un clasificador en **ciclo cerrado**: **detectar → capturar imagen → clasificar con IA → separar con actuador → registrar**, con precisión medible sobre un conjunto de prueba definido por el equipo.

**Obligatorio:**
- Conjunto de **≥ 20 residuos etiquetados**, separado **dos veces**: una manual cronometrada y otra con el sistema, registradas en la misma tabla (aciertos, errores, tiempo).
- La IA entrega **categoría + confianza (0 a 1)**. Si la confianza es menor al umbral, **el sistema no adivina**: deriva a revisión y marca el caso como dudoso.
- Panel con: foto capturada en vivo, categoría predicha, confianza, conteo por categoría, historial con hora, tasa de acierto y **corrección manual** que quede registrada y sirva para reentrenar.
- **Demo en vivo con 3 momentos:** (1) orgánico → bote orgánico, (2) inorgánico → bote inorgánico, (3) objeto dudoso/no entrenado → confianza baja → revisión.
- Métricas: precisión total y por categoría (matriz de confusión), % correcto vs. separación manual, tiempo promedio por residuo, cantidad de residuos desviados de la basura mezclada.

**Rúbrica (100 pts):** Funcionamiento e integración 25 · Programación 15 · CAD 3D 15 · Electrónica y control 15 · Aplicación digital 10 · Solución del reto 10 · Innovación 5 · Equipo y defensa 5. El jurado pide **3 de 3 ciclos correctos registrados**, código modular y documentado, CAD editable con tolerancias justificadas, mediciones eléctricas con diagnóstico de una falla y que un integrante **modifique una función en vivo**.

---

## 4. Categorías y reglas de decisión

| ID | Categoría | Color del bote | Ejemplos (set de prueba) |
|---|---|---|---|
| 0 | **Orgánica** | Verde | Cáscara de plátano, restos de fruta, servilleta con comida, cáscara de huevo |
| 1 | **Inorgánica** | Azul | Botella PET, lata, cartón, papel, envoltura, unicel, vidrio simulado (material seguro) |
| 2 | **Peligroso** (simulado) | Gris | Pila descargada, envase vacío de medicamento, blíster, cubrebocas (simulado) |
| — | **Revisión / dudoso** | — (se queda en la bandeja) | Objetos no entrenados o con confianza baja |

**Reglas (todas configurables desde el panel, guardadas en `config`):**
1. `UMBRAL_GENERAL = 0.60`. Si `max(prob) ≥ 0.60` → se acepta la categoría.
2. **Regla de asimetría de riesgo:** enviar un peligroso al bote orgánico o inorgánico es el peor error. Si `p(peligroso) ≥ UMBRAL_PELIGROSO (0.35)` y no es la clase ganadora → el caso pasa a **revisión**, no se clasifica.
3. Si `max(prob) < 0.60` → **revisión**: el residuo **no cae**, se queda en la bandeja; se enciende el LED amarillo, la LCD pide ayuda y el panel muestra la alerta.
4. Un caso en revisión se resuelve por **voz**, por el **panel** o por el **teclado** (teclas 1/2/3). La resolución queda registrada con `origen` y `corregido = 1`.
   - Si la resuelve el **operador desde el panel**, la imagen va directo a `dataset/<clase>/`.
   - Si la resuelve un **usuario** (voz o teclado), la imagen va a `dataset/_por_verificar/<clase>/` y el operador la aprueba o rechaza en el panel antes de usarla para reentrenar. Así se evita que una etiqueta equivocada contamine el modelo.
5. Si nadie resuelve en 30 s → queda como "revisión pendiente" y un operador retira el residuo.
6. **Bote lleno:** si el bote destino tiene un llenado estimado del 100 %, el residuo **no se suelta**: se queda en la bandeja hasta que el operador vacíe el bote (sección 13).

> Nota para la defensa: "Inorgánica" agrupa reciclables (PET, lata, cartón, papel) y no reciclables. Justifica esa decisión por el alcance de 10 h y deja la subdivisión como ampliación.

---

## 5. Diseño mecánico (basado en el diagrama del equipo)

### 5.1 Lo que ya está definido
- **Base inferior cuadrada de MDF** 200 × 200 × 3 mm (fija).
- **Disco giratorio circular de MDF** Ø190 × 3 mm, montado sobre la base.
- **4 rodamientos de canica/balín** entre base y disco que soportan la carga vertical. El servo solo aporta par de giro, no soporta peso.
- **Servo central** fijo en la base; su **cruceta blanca** se acopla al centro del disco.
- **3 botes pequeños de plástico (1.5 L)** sobre el disco:
  - Verde → **Orgánica** → posición angular **10°**
  - Azul → **Inorgánica** → posición angular **90°**
  - Gris → **Peligroso** → posición angular **180°**
- **Contrapeso** en el disco para centrar la masa sobre el eje.

**Principio de operación:** el disco gira para colocar el bote correcto **debajo de un punto de caída fijo**; luego se abre la trampilla y el residuo cae por gravedad.

### 5.2 Lo que debes agregar al diseño (no aparece en el diagrama)
1. **Torre de captura fija** (anclada a la base, **no** al disco), en voladizo sobre la trayectoria de las bocas de los botes, con:
   - **Bandeja de captura** con fondo liso de color uniforme (fondo constante para la IA).
   - **Trampilla** accionada por un segundo servo (SG90) que deja caer el residuo.
   - **Soporte cenital de cámara** (webcam USB o celular) a altura fija.
   - **Iluminación blanca uniforme** (tira o anillo de LEDs blancos) y paredes laterales para aislar la luz ambiente.
   - **Sensor IR FC-51 #1** apuntando a la bandeja (presencia de objeto).
   - **Sensor IR FC-51 #2** en el punto de caída para confirmar que el residuo cayó.
2. **Pista o asientos para las canicas** en la base (ranura circular o 4 copas impresas) para que no se salgan.
3. **Localizadores de botes** en el disco (clips o topes) para que cada bote quede siempre en la misma posición.
4. **Soporte del contrapeso.**
5. **Adaptador cruceta–disco** (cubo atornillado) en lugar de pegar el disco directamente a la cruceta.

### 5.3 Puntos que debes verificar y advertir
- **Dimensiones:** tres botes de 1.5 L difícilmente caben en un disco de Ø190 mm. Pide al equipo medir los botes con el vernier y, si no caben, propone un disco mayor (Ø260–300 mm) o botes más pequeños. **Recalcula el radio de colocación** de los botes y la posición de la torre a partir de esa medida.
- **Servo del disco:** el diagrama usa un **SG90**. Calcula el par requerido (masa de botes + residuos + disco, fricción de rodadura, inercia) y compáralo con el par del SG90 (~1.8 kg·cm) y del **MG996R** (~9–11 kg·cm, disponible en el inventario). Recomienda el MG996R si el margen es insuficiente y diseña el soporte con **cavidad paramétrica** para usar cualquiera de los dos.
- **Movimiento suave:** el disco debe girar con una rampa (≈1° cada 15 ms) para no derramar ni golpear.
- **Calibración angular:** el ángulo del servo que alinea cada bote con el punto de caída **no es igual** a la posición del bote en el disco. Si el bote está en `φᵢ` y el punto de caída en `D`, el servo debe ir a `θᵢ = D − φᵢ` (dentro de 0–180°). Esto se **calibra empíricamente** y se guarda en la configuración; nunca se deja fijo en el código.
- **Tapas basculantes:** verificar que los objetos ligeros atraviesen la tapa; si no, retirar las tapas durante la operación.

### 5.4 Piezas CAD (SolidWorks)
Genera la lista de piezas con: nombre, proceso (corte MDF / impresión 3D / comercial), dimensiones clave, tolerancias de ajuste (0.2–0.3 mm en encajes impresos), tiempo estimado de impresión (< 3 h), y parámetros sugeridos (PLA, boquilla 0.4 mm, capa 0.2 mm, relleno 15–20 %, soportes solo donde sean necesarios).

Piezas mínimas: soporte del servo del disco · adaptador cruceta–disco · pista/copas de canicas · localizadores de botes · soporte del contrapeso · columna de la torre · bandeja + trampilla + bisagra · soporte del servo de la trampilla · soporte de cámara · soporte de iluminación · soportes de los dos FC-51.

Entrega también la **secuencia de ensamble** y qué piezas deben mandarse a imprimir **primero** (antes de las 12:00).

---

## 6. Stack tecnológico (obligatorio)

| Capa | Tecnología | Responsabilidad |
|---|---|---|
| Orquestador / backend | **Python + FastAPI** | Controla todo el ciclo en un solo proceso (máquina de estados) y expone la API REST y el WebSocket. |
| Visión | **OpenCV** | Captura de la cámara cenital, recorte de la zona de interés y guardado de fotos. |
| IA | **MobileNetV2 preentrenado (ImageNet) + clasificador propio**: Keras como extractor de características + **scikit-learn** (regresión logística); alternativa: cabeza densa entrenada en Keras | Clasificación en 3 clases con confianza; reentrenamiento local rápido con las correcciones. |
| Voz (offline) | **Vosk** con modelo pequeño en español + **diccionario de palabras clave → categoría** (`keywords.json`) | Reconocimiento local y resolución de casos dudosos. |
| Microcontrolador | **C++ en Arduino UNO** (bibliotecas `Servo`, `LiquidCrystal_I2C`, `Keypad`) | Servos, sensores IR, LCD 20×4, LEDs y teclado. |
| Comunicación | **Serial USB con pyserial** | Protocolo de texto línea por línea entre la PC y el Arduino. |
| Base de datos | **SQLite** (módulo `sqlite3` incluido en Python) | Historial, pruebas, correcciones, versiones del modelo y configuración. |
| Panel | **React (Vite)** + polling o **WebSocket** | Vista en vivo, historial, corrección, estadísticas, pruebas y configuración. |

No agregues lenguajes ni servicios en la nube fuera de esta tabla. Si alguna biblioteca adicional es imprescindible, justifícala y pide confirmación.

---

## 7. Hardware disponible (inventario declarado)

- 2 × Arduino UNO R3, 2 × Arduino Nano V3
- 5 × servomotores SG90 / MG996R
- 2 × sensores IR FC-51 / TCRT5000
- ~~LCD 2004 (20×4) con módulo I2C · Teclado matricial 4×4~~ — **no se usan** (cambio de diseño del 20-nov: todo desde la página y por voz)
- LEDs de 5 mm (rojo, verde, amarillo, azul) · transistores 2N2222 / BC547 / TIP120 · resistencias · capacitores electrolíticos (1–1000 µF) y cerámicos
- Fuente regulada DC 3–20 V con caimanes · power bank Ugreen 25 000 mAh · 2 protoboards · jumpers
- Multímetro Steren MUL-281 · vernier digital · herramientas manuales
- Filamento PLA gris 1 kg

**Pendiente de conseguir y agregar a la hoja de declaración:** webcam USB (o celular como cámara) y LEDs blancos o tira LED para la iluminación.

---

## 8. Electrónica

### 8.1 Asignación de pines propuesta (Arduino UNO)

| Pin | Elemento | Nota |
|---|---|---|
| D0/D1 | Serial USB | Reservados |
| D2 | FC-51 #1 (presencia en bandeja) | Salida activa en BAJO, con antirrebote por software |
| D3 | FC-51 #2 (confirmación de caída) | Activa en BAJO |
| D4–D7 | Teclado 4×4: filas | |
| D8, D11, D12, D13 | Teclado 4×4: columnas | |
| D9 | Servo del disco (carrusel) | Señal PWM |
| D10 | Servo de la trampilla | Señal PWM |
| A0 / A1 / A2 | LED verde / amarillo / rojo (estado) | Con resistencia de 220–330 Ω |
| A3 | Iluminación blanca vía TIP120 | Base con resistencia de 1 kΩ; diodo si la carga es inductiva |
| A4 / A5 | LCD I2C (SDA / SCL) | Dirección típica 0x27 (verificar con escáner I2C) |

Verifica que no haya conflictos y propón ajustes si los hay.

### 8.2 Alimentación y seguridad
- **Los servos NO se alimentan del pin 5 V del Arduino.** Usa la fuente regulada a **5.0–6.0 V**, con **tierra común** con el Arduino y un **capacitor de 1000 µF** en paralelo con la línea de los servos.
- Indica la corriente máxima esperada (pico del MG996R) y cómo verificar que la fuente la entrega.
- Solo se mueve un servo a la vez (disco y luego trampilla) para limitar los picos de corriente.
- Entrega un **diagrama de conexiones** (texto/tabla y, si es posible, descripción para Fritzing o Tinkercad Circuits).
- Define **3 mediciones con multímetro** que el equipo debe registrar (por ejemplo: voltaje de los servos en reposo y en movimiento, voltaje de la iluminación, continuidad de GND común) y **una falla diagnosticable** (por ejemplo: caída de voltaje que reinicia el Arduino si los servos se conectan al 5 V de la placa).

---

## 9. Protocolo serial (115 200 baudios, ASCII, líneas terminadas en `\n`)

**PC → Arduino**

| Comando | Acción |
|---|---|
| `PING` | Verificación de enlace |
| `POS:<0\|1\|2>` | Girar el disco al bote de la categoría (ángulos calibrados) |
| `HOME` | Regresar el disco a la posición de reposo |
| `DROP` | Abrir la trampilla, esperar, cerrarla |
| `LIGHT:<ON\|OFF>` | Iluminación de la zona de captura |
| `LED:<VERDE\|AMARILLO\|ROJO\|OFF>[:PARPADEO]` | LED de estado, fijo o parpadeando (correcto/incorrecto en el modo Adivina) |
| `LCD:<l1>\|<l2>\|<l3>\|<l4>` | Mensaje en la LCD 20×4 (hasta 4 líneas de 20 caracteres). El backend recorta y **quita acentos** antes de enviar (la LCD HD44780 no los muestra) |
| `LCD_SCROLL:<texto>` | Texto largo desplazándose en la línea 4 (para la explicación breve) |
| `CAL:<id>:<ángulo>` | Guardar el ángulo calibrado de un bote (EEPROM) |

**Arduino → PC**

| Mensaje | Significado |
|---|---|
| `READY` | Arranque completo |
| `PONG` | Respuesta a `PING` |
| `OBJ` | Objeto estable en la bandeja (≥ 300 ms) |
| `POS_OK:<id>` | Disco en posición |
| `DROP_OK` | FC-51 #2 confirmó la caída |
| `DROP_TIMEOUT` | No se detectó la caída en 2 s |
| `KEY:<tecla>` | Tecla presionada |
| `ERR:<código>` | Error (comando inválido, servo, etc.) |

> **Detalle y agregados (2026-11-19):** las respuestas de cada comando, los códigos de error y los agregados `ANG`, `ANG_OK`, `HOME_OK`, `OK`, `CAL_OK`, `STATUS`, `LIBRE` y `WATCHDOG` están en [`docs/api_contrato.md`](api_contrato.md), sección 5.

**Teclado (significado según el estado; el Arduino solo envía `KEY:<tecla>` y toda la lógica de menús vive en el orquestador de Python):**

| Tecla | MENÚ | ESPERA_ADIVINANZA | REVISIÓN | BOTE_LLENO / Operador |
|---|---|---|---|---|
| `1` | Modo **IA** | Adivina **Orgánica** | Forzar Orgánica | Vaciar bote verde |
| `2` | Modo **Adivina** | Adivina **Inorgánica** | Forzar Inorgánica | Vaciar bote azul |
| `3` | — | Adivina **Peligroso** | Forzar Peligroso | Vaciar bote gris |
| `A` | Hablar (push-to-talk) | Responder por voz ("orgánica", "inorgánica", "peligroso") | Hablar | — |
| `B` | — | — | Confirmar | Confirmar vaciado |
| `C` | — | Cancelar → modo IA | Dejar pendiente | Cancelar |
| `D` | Menú de operador | — | — | Salir |
| `#` | — | Volver al menú | — | Volver al menú |

En el estado **RETROALIMENTACIÓN** (después de adivinar), la tecla `*` significa **"Creo que la IA se equivocó"**: el residuo se queda en la bandeja y el caso pasa a REVISIÓN por el operador.

El firmware debe ser **no bloqueante** (`millis()`, sin `delay()` largos), validar comandos, responder siempre y tener un *watchdog* lógico: si no recibe comandos en X segundos, regresa a `HOME` con la trampilla cerrada.

---

## 10. Ciclo de operación (máquina de estados del orquestador)

```
MENÚ ──(1: IA  |  OBJ sin elegir → modo por defecto IA)──────────────────────────┐
  └──(2: Adivina)──► ESPERA_OBJETO ──(OBJ)──┐                                     │
                                            ▼                                     ▼
                                   CAPTURA ──► CLASIFICACIÓN (oculta al usuario)   CAPTURA ──► CLASIFICACIÓN
                                            │                                     │
                                            ▼                                     │
                                   ESPERA_ADIVINANZA ──(1/2/3 o voz | 20 s)──►      │
                                   RETROALIMENTACIÓN ──(* = reporte)──► REVISIÓN    │
                                            │                                     │
                                            └──────────────┬──────────────────────┘
                                                           ▼
             ┌─(confianza OK)──► VERIFICAR_BOTE ──(lleno)──► BOTE_LLENO ──(vaciado)──┐
             │                        │                                              │
             │                        └─(con espacio)──► POSICIONAR ◄────────────────┘
             │                                              │ (POS_OK)
             │                                              ▼
             │                                   SOLTAR ──(DROP_OK / TIMEOUT)──► REGISTRAR ──► ACTUALIZAR_NIVEL ──► HOME ──► MENÚ
             │
             └─(dudoso)──► REVISIÓN ──(voz / panel / tecla)──► VERIFICAR_BOTE …
                              └─(30 s sin respuesta)──► PENDIENTE ──► MENÚ
```

1. **MENÚ:** disco en reposo, trampilla cerrada, LED verde, LCD con el menú (sección 11). Si alguien coloca un residuo sin elegir, se usa el **modo por defecto (IA)**, configurable, para que el ciclo siga siendo autónomo.
2. **CAPTURA:** `LIGHT:ON`, espera 200 ms, captura **3 fotogramas**, guarda la foto en `captures/AAAAMMDD_HHMMSS.jpg`.
3. **CLASIFICACIÓN:** promedia las probabilidades de los 3 fotogramas y aplica las reglas de la sección 4. En el modo Adivina el resultado **no se muestra** (ni en la LCD ni en el panel) hasta que el usuario responda.
4. **ESPERA_ADIVINANZA / RETROALIMENTACIÓN:** solo en el modo Adivina (sección 12).
5. **VERIFICAR_BOTE:** consulta el llenado estimado del bote destino (sección 13).
6. **POSICIONAR:** `POS:<id>` y espera `POS_OK` (timeout 3 s → error).
7. **SOLTAR:** `DROP` y espera `DROP_OK` o `DROP_TIMEOUT` (este último se registra como incidencia).
8. **REGISTRAR:** inserta en SQLite, emite el evento por WebSocket y actualiza la LCD.
9. **ACTUALIZAR_NIVEL:** suma una pieza al bote y emite avisos si corresponde.
10. **HOME** y regreso al **MENÚ**. Cada residuo empieza con el menú, porque cada persona elige su modo.

Cada transición se registra en la tabla `eventos` con marca de tiempo para la bitácora y el diagnóstico. **La lógica de estados vive solo en Python**; el Arduino ejecuta comandos y reporta sensores y teclas.

---

## 11. Modos de operación y menú

El sistema ofrece al usuario dos modos al inicio de cada uso, seleccionables desde el **teclado 4×4**, el **panel** o la **voz** ("usar IA" / "quiero adivinar"):

| Modo | Qué hace |
|---|---|
| **1 · IA** | Ciclo automático normal: la IA clasifica y el carrusel deposita el residuo. |
| **2 · Adivina ("¿Le ganas a la IA?")** | El usuario intenta adivinar el bote correcto antes de que el sistema revele la clasificación; recibe retroalimentación explicada y el residuo **siempre** termina en el bote correcto. |
| **D · Operador** | Vaciar botes, ver niveles y regresar. Para el equipo, no para el público. |

**Pantallas de la LCD 20×4 (ASCII, sin acentos, máximo 20 caracteres por línea):**

```
MENÚ                     ESPERA_OBJETO            ESPERA_ADIVINANZA
+--------------------+   +--------------------+   +--------------------+
|== CLASIFICADOR ==  |   |MODO ADIVINA        |   |A que bote va?      |
|1: Usar IA          |   |Coloca el residuo   |   |1:Organica  (verde) |
|2: Adivinar (reto)  |   |en la bandeja       |   |2:Inorganica (azul) |
|Coloca o elige      |   |#: volver al menu   |   |3:Peligroso (gris)  |
+--------------------+   +--------------------+   +--------------------+
```

El panel React muestra el mismo menú con botones grandes y refleja en tiempo real lo que se elija desde el teclado, y viceversa (una sola fuente de verdad: el orquestador).

---

## 12. Innovación 1 — Modo "¿Le ganas a la IA?"

### 12.1 Objetivo
Convertir cada uso del bote en una **microlección de separación de residuos** y, al mismo tiempo, **generar datos de separación humana vs. IA** de forma continua, que complementan (no sustituyen) la prueba oficial de 20 residuos del reto.

### 12.2 Flujo
1. El usuario elige **2: Adivinar** y coloca el residuo.
2. El sistema detecta, captura y clasifica **en silencio** (resultado oculto).
3. La LCD pregunta "¿A qué bote va?". El usuario responde con `1/2/3` o por voz (tecla `A`). Tiempo límite: **20 s** → si no responde, se registra "sin respuesta" y se continúa en modo IA.
4. El sistema compara la respuesta con la **categoría de referencia**:
   - Si la IA está segura (reglas de la sección 4) → la referencia es la predicción de la IA.
   - Si la IA está **dudosa** → la LCD indica "La IA tampoco esta segura" y el caso pasa a REVISIÓN; la adivinanza se evalúa **después**, contra la categoría resuelta por el operador.
   - En la prueba oficial y en la prueba controlada de aprendizaje (12.5), la referencia es la **etiqueta real** del residuo (`residuos_prueba`).
5. **Nivel de certeza de la referencia.** Antes de dar la retroalimentación, el sistema determina qué tan confiable es la "respuesta correcta" contra la que califica al usuario, porque la IA también puede equivocarse:

   | Nivel | Condición | Tono | LED | Tiempo en pantalla |
   |---|---|---|---|---|
   | **Verificada** | Referencia = etiqueta real (prueba oficial) o decisión del operador | Firme: "¡CORRECTO!" / "INCORRECTO" | Verde o rojo parpadeando | 5 s |
   | **Alta** | Referencia = IA con confianza ≥ `UMBRAL_TONO_FIRME` (0.80, configurable) | Firme: "¡CORRECTO!" / "INCORRECTO" | Verde o rojo parpadeando | 5 s |
   | **Media** | Referencia = IA con confianza entre `UMBRAL_GENERAL` (0.60) y 0.80 | Prudente: "PARECE CORRECTO" / "PROBABLEMENTE NO" y "Probablemente va en…" | Amarillo parpadeando | 8 s (más tiempo para reportar) |
   | Baja | Confianza < 0.60 | No se califica: "La IA tampoco esta segura" → REVISIÓN | Amarillo fijo | — |

   **Siempre se muestra la confianza de la IA** (por ejemplo "IA 78% segura") en la LCD y en el panel, junto con la fuente de la referencia (IA, operador o etiqueta real). En el nivel **Media**, la línea 4 de la LCD alterna cada 3 s entre la explicación y el recordatorio **"*: si crees que no"**, y el panel muestra el botón "Creo que la IA se equivocó" destacado.

6. **Retroalimentación:**
   - **Correcto** → LCD con el resultado (según el tono), el bote y su color, la confianza de la IA y el marcador de la sesión. El panel muestra un mensaje de felicitación y un dato breve sobre esa categoría.
   - **Incorrecto** → LCD con la respuesta del usuario, la categoría de referencia y su color, y una explicación breve desplazándose en la línea 4. El panel muestra la **explicación completa**: por qué la respuesta es incorrecta, **cuál es el bote correcto** (nombre y color) y por qué. En el nivel **Media**, la explicación se redacta en condicional ("Probablemente va en Orgánica porque…").
7. Al terminar el tiempo en pantalla (o al presionar `B`), el carrusel deposita el residuo en el **bote de referencia**, nunca en el elegido por el usuario.
8. Si el usuario cree que la IA se equivocó, presiona `*` durante la retroalimentación → el residuo se queda en la bandeja y el operador decide en el panel. Si el operador le da la razón al usuario, la adivinanza se **recalifica como correcta**, el marcador y las estadísticas se actualizan y la foto se usa para reentrenar.

**Pantallas de la LCD (20×4, sin acentos):**

```
ALTA · CORRECTO          ALTA · INCORRECTO
+--------------------+   +--------------------+
|** CORRECTO! **     |   |INCORRECTO          |
|Va en ORGANICA      |   |Tu: INORGANICA      |
|(bote verde)        |   |Es: ORGANICA (verde)|
|IA 92%  Ac: 4/5     |   |<IA 91% - se descomp|  ← texto desplazándose
+--------------------+   +--------------------+

MEDIA · CORRECTO         MEDIA · INCORRECTO
+--------------------+   +--------------------+
|PARECE CORRECTO     |   |PROBABLEMENTE NO    |
|Prob: ORGANICA      |   |Tu: INORGANICA      |
|IA 72% segura       |   |Prob: ORGANICA 72%  |
|*: si crees que no  |   |*: si crees que no  |  ← alterna con la explicación
+--------------------+   +--------------------+
```

### 12.3 Base de explicaciones (`data/explicaciones.json`)
Explicaciones **por pareja de confusión** (respuesta del usuario → categoría correcta), porque la IA identifica la categoría, no el objeto exacto. Cada entrada tiene un texto corto (≤ 60 caracteres, para la LCD) y uno largo (2–3 oraciones, para el panel). Textos base que debes refinar y validar con el equipo:

| Usuario dijo → Era | Explicación base |
|---|---|
| Inorgánica → **Orgánica** | Proviene de un ser vivo y se descompone naturalmente en poco tiempo; sirve para composta. Mezclado con inorgánicos, ensucia los materiales reciclables. |
| Peligroso → **Orgánica** | No contiene sustancias tóxicas, corrosivas ni inflamables; es un resto biodegradable que va a composta. |
| Orgánica → **Inorgánica** | Plástico, metal, vidrio, papel o cartón no deben ir a la composta; muchos se reciclan si están limpios y secos. |
| Peligroso → **Inorgánica** | Es un envase o material común sin sustancias tóxicas; va con inorgánicos y, si está limpio, puede reciclarse. |
| Orgánica → **Peligroso** | Contiene o estuvo en contacto con sustancias tóxicas (metales de pilas, medicamentos, químicos) que contaminarían la composta, el suelo y el agua; requiere manejo especial. |
| Inorgánica → **Peligroso** | Aunque parezca un envase común, sus residuos tóxicos pueden contaminar los reciclables o lastimar a quien los separa; va a un acopio especial. |

Además:
- Un **dato breve por categoría** para los aciertos (por ejemplo: "La composta reduce la basura que llega al relleno sanitario").
- Si el objeto se identificó por voz y existe en `keywords.json`, se puede usar una explicación **específica del objeto** (campo opcional `explicacion`).
- Las explicaciones deben ser **correctas, breves y en lenguaje sencillo**. Indica en la documentación la fuente usada para clasificar (por ejemplo, la norma ambiental local de separación de residuos) para que el equipo pueda citarla.

### 12.4 Marcador y estadísticas
- **Sesión:** inicia al elegir el modo Adivina y termina al volver al menú o tras 2 min sin actividad. Muestra aciertos/intentos y racha. Cada adivinanza guarda su **número de intento** dentro de la sesión.
- **Global (panel):** % de acierto humano total y por categoría, **matriz de confusión humana** (real vs. adivinanza), comparación **humano vs. IA** sobre los mismos residuos y las parejas de confusión más frecuentes (evidencia del problema del reto: el error humano).
- Las estadísticas de acierto humano que se reporten al jurado usan **solo referencias de nivel Verificada o Alta**; las de nivel Media se muestran aparte. Si una adivinanza se recalifica, todas las estadísticas se recalculan.
- Todo dato del modo Adivina se registra con su origen; nunca se mezcla con los datos de la prueba oficial sin indicarlo.

### 12.5 Curva de aprendizaje (¿la retroalimentación enseña?)
El objetivo es **demostrar con datos, no afirmar**, que la retroalimentación mejora la separación que hacen las personas.

**Métricas automáticas (uso libre):**
1. **% de acierto por número de intento** (1.º, 2.º, 3.º, …, ≥ 6.º) agregado de todas las sesiones → gráfica de líneas. Si la gente aprende, la curva sube.
2. **Primera mitad vs. segunda mitad** de cada sesión con ≥ 4 intentos → % de acierto de cada mitad y la diferencia.
3. **Tasa de corrección tras explicación:** cuando un usuario falla una categoría y, **en la misma sesión**, le vuelve a tocar un residuo de esa categoría, ¿acierta esta vez? Es el indicador más directo de que la explicación funcionó.

**Prueba controlada de aprendizaje (protocolo para el viernes, ~15 min):**
1. Seleccionar 10 residuos del set de prueba (con etiqueta real conocida, mezcla de las 3 categorías).
2. 3 a 5 voluntarios, cada uno con un **alias anónimo** (sin nombres reales).
3. **Ronda 1:** el voluntario adivina los 10 residuos en orden aleatorio y recibe la retroalimentación con explicación.
4. **Ronda 2:** los mismos 10 residuos en **otro orden aleatorio**.
5. Reportar el % de acierto de la ronda 1 vs. la ronda 2 por voluntario y en promedio, y la tasa de corrección tras explicación.

**Reglas de honestidad estadística:**
- Usar solo referencias de nivel Verificada o Alta.
- Mostrar siempre el **tamaño de la muestra** (n de sesiones e intentos). Si n es pequeño (por ejemplo, menos de 10 sesiones o 5 voluntarios), el panel lo rotula como **"muestra pequeña: resultado indicativo"**.
- No afirmar significancia estadística ni generalizar más allá de lo medido; mencionar los límites (pocos voluntarios, mismos objetos en ambas rondas, posible efecto de memoria).

### 12.6 Cómo defenderlo ante el jurado
"El reto dice que el problema es que la gente decide en segundos y sin información. Nuestro modo Adivina **mide** ese error humano en cada uso y lo **corrige** con una explicación en el momento, mientras el sistema garantiza que el residuo termine en el bote correcto. La IA es honesta: muestra qué tan segura está y, si duda, no regaña al usuario. Y **medimos si la gente aprende**: comparamos la primera y la segunda ronda de la prueba controlada."

---

## 13. Innovación 2 — Aviso de bote lleno (estimado)

### 13.1 Principio
No hay sensor de nivel en el inventario, así que el llenado se **estima por conteo de piezas** depositadas en cada bote contra una **capacidad calibrada**. En el panel y en la documentación se rotula siempre como **"ESTIMADO"**.

### 13.2 Calibración de la capacidad
1. Llenar cada bote con residuos representativos de su categoría hasta que ya no cabe uno más o la tapa no cierra.
2. Contar las piezas; repetir 2 veces y promediar.
3. Guardar `capacidad_piezas` por bote en la configuración `[COMPLETAR con la medición real]` y anotar el procedimiento en la bitácora.
4. Relacionarlo con la sección 5.3: con los botes llenos, la masa sobre el disco aumenta; el cálculo de par del servo debe usar la **masa con botes llenos**.

### 13.3 Reglas
- Solo se suma una pieza cuando se confirma la caída (`DROP_OK`). Un `DROP_TIMEOUT` también suma, marcado como "no confirmado" (criterio conservador: es mejor avisar antes que desbordar).
- `nivel = piezas_actuales / capacidad_piezas`.
- **≥ 80 % (casi lleno, configurable):** aviso en el panel (barra naranja) y en la línea 4 de la LCD ("Aviso: verde 83%").
- **100 % (lleno):** el bote queda **bloqueado**. Si llega un residuo para ese bote, se queda en la bandeja; LED rojo fijo; LCD "BOTE VERDE LLENO / Vacie y presione D, luego 1"; alerta en el panel.
- **Vaciado:** desde el panel (botón "Marcar como vaciado") o con el teclado (`D` → `1/2/3` → `B` para confirmar). Reinicia el conteo, registra el evento y, si había un residuo esperando, el ciclo continúa automáticamente.
- Los demás botes siguen disponibles, pero la bandeja queda ocupada hasta que se resuelva el bloqueo.

**Pantalla de la LCD:**

```
+--------------------+
|BOTE VERDE LLENO    |
|(estimado 12/12)    |
|Vacie y presione    |
|D y luego 1         |
+--------------------+
```

### 13.4 Datos para el reporte
Cada vaciado registra cuántas piezas contenía, lo que permite reportar **residuos desviados por categoría** y la frecuencia de vaciado (insumo para el impacto ambiental del reto).

### 13.5 Cómo defenderlo ante el jurado
"No inventamos un sensor que no tenemos: estimamos el nivel con un conteo calibrado y lo declaramos como estimación. Es una ampliación que el propio reto sugiere y evita que un bote desbordado contamine los demás."

---

## 14. Inteligencia artificial

### 14.1 Dataset
- 40–60 fotos por clase, tomadas **con la misma cámara, bandeja e iluminación de la demo**, variando posición, orientación y lado visible.
- Registra a qué **objeto físico** corresponde cada foto (`objeto_id`) para poder separar entrenamiento y validación **por objeto**, no por foto, y evitar fuga de datos.
- Los 20 residuos del set de prueba oficial se documentan aparte; si alguno también se usó para entrenar, debe indicarse.
- Script `capturar_dataset.py`: muestra la vista de la cámara y guarda fotos en `dataset/<clase>/` con una tecla.

### 14.2 Entrenamiento (`training/train.py`)
- Entrada 224×224 RGB, preprocesamiento de MobileNetV2.
- **Opción principal:** MobileNetV2 (sin la capa superior, pooling promedio) como extractor congelado → embeddings en caché (`.npy`) → `LogisticRegression` de scikit-learn. Reentrenar toma segundos.
- **Alternativa:** cabeza `Dropout(0.2) + Dense(3, softmax)` sobre la base congelada, Adam 1e-3, 10–15 épocas, aumento de datos ligero (volteo, rotación pequeña, brillo ±10 %).
- Guardar el modelo versionado (`models/v<N>/`), `labels.json` y las métricas en la tabla `modelos`.
- `training/evaluate.py`: precisión total y por clase, matriz de confusión (imagen PNG y tabla), y los casos fallidos con su foto.

### 14.3 Reentrenamiento con correcciones
- Cada corrección queda marcada en SQLite. Las del **operador** (panel) copian la foto a `dataset/<clase_correcta>/`; las de **usuarios** (voz, teclado o reporte "la IA se equivocó" del modo Adivina) van a `dataset/_por_verificar/<clase>/` hasta que el operador las apruebe.
- Botón "Reentrenar" en el panel → ejecuta el entrenamiento en segundo plano, compara la precisión de validación con la versión anterior y **solo activa el nuevo modelo si no empeora**.

### 14.4 Explicabilidad para el jurado
El panel muestra las **3 probabilidades**, no solo la ganadora, y el umbral vigente. Prepara un cambio en vivo sencillo (por ejemplo, modificar `UMBRAL_GENERAL` y mostrar cómo cambia el comportamiento).

---

## 15. Voz (Vosk, offline)

- Modelo `vosk-model-small-es` descargado **por adelantado**.
- **Push-to-talk** con la tecla `A` (la biblioteca es ruidosa; no escuchar de forma continua).
- Usa el modo de **gramática restringida** de Vosk con el vocabulario de `keywords.json` para mejorar la precisión.
- Normalización del texto: minúsculas, sin acentos, singularización básica.
- `keywords.json`: ~100 objetos comunes → categoría (por ejemplo `"platano": 0`, `"botella": 1`, `"pila": 2`). Debe ser fácil de editar.

**Casos de uso:**
1. **Resolver un dudoso:** el sistema pide "¿Qué es?", el usuario responde ("una cáscara de plátano") → categoría → VERIFICAR_BOTE → POSICIONAR → SOLTAR → registro con `origen = voz`, `corregido = 1` y la foto va a `dataset/_por_verificar/`.
2. **Pregunta directa** ("¿Dónde tiro esta cáscara de plátano?"):
   - Con objeto en la bandeja → **fusión** voz + visión: si coinciden, se procede con confianza reforzada; si no coinciden, el caso pasa a **revisión** y se muestra el conflicto.
   - Sin objeto en la bandeja → solo responde en la LCD y en el panel, y gira el disco para mostrar el bote correspondiente.
3. Si la palabra no está en el diccionario → "No reconocí el objeto" y el caso sigue en revisión.
4. **Menú por voz:** "usar IA" / "inteligencia artificial" → modo IA; "adivinar" / "quiero adivinar" → modo Adivina.
5. **Adivinanza por voz:** en ESPERA_ADIVINANZA solo se aceptan "orgánica", "inorgánica", "peligroso" (y sinónimos: "composta", "reciclable", "tóxico"). Usa una **gramática restringida distinta por estado** para maximizar la precisión.

---

## 16. Base de datos (SQLite)

Diseña el esquema con al menos estas tablas (incluye las sentencias `CREATE TABLE`, índices y un script de inicialización):

- `clasificaciones(id, fecha_hora, foto, modo [ia|adivina], pred_id, confianza, p_organica, p_inorganica, p_peligroso, final_id, origen [camara|voz|manual|teclado], dudoso, corregido, modelo_version, tiempo_ciclo_ms, drop_confirmado, bote_id)`
- `sesiones_juego(id, tipo [libre|prueba_aprendizaje], participante_alias, inicio, fin, intentos, aciertos, mejor_racha)`
- `adivinanzas(id, sesion_id, clasificacion_id, residuo_prueba_id, fecha_hora, numero_intento, ronda, respuesta_usuario, categoria_referencia, fuente_referencia [ia|operador|etiqueta_real], confianza_ia, nivel_certeza [verificada|alta|media], correcto, recalificada, medio [teclado|voz|panel|sin_respuesta], tiempo_respuesta_s, reporto_error_ia, explicacion_mostrada)`
- `botes(id, nombre, color, categoria_id, capacidad_piezas, piezas_actuales, umbral_aviso, bloqueado, ultimo_vaciado)`
- `vaciados(id, bote_id, fecha_hora, piezas_al_vaciar, origen [panel|teclado])`
- `residuos_prueba(id, nombre, categoria_real, simulado, usado_en_entrenamiento)`
- `pruebas(id, corrida, modo [manual|sistema], residuo_id, categoria_asignada, correcto, tiempo_s, fecha_hora)`
- `modelos(version, fecha, n_imagenes, precision_val, activo)`
- `eventos(id, fecha_hora, nivel, origen, mensaje)`
- `config(clave, valor)` — umbrales, ángulos calibrados, puerto serial, índice de cámara

---

## 17. API del backend (FastAPI)

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/estado` | Estado de la máquina, enlace serial, cámara, modelo activo |
| GET | `/api/clasificaciones?limit=&dudosos=` | Historial |
| POST | `/api/clasificaciones/{id}/corregir` | Corrección manual |
| GET | `/api/estadisticas` | Conteos, tasa de acierto, matriz de confusión |
| GET/POST | `/api/pruebas` | Registro de corridas manual vs. sistema |
| POST | `/api/modelo/reentrenar` · GET `/api/modelo/estado` | Reentrenamiento |
| GET/PUT | `/api/config` | Umbrales, ángulos, modo por defecto, capacidades |
| GET/POST | `/api/modo` | Consultar o seleccionar el modo (`ia` / `adivina`) desde el panel |
| POST | `/api/juego/adivinar` | Enviar la adivinanza desde el panel (`{categoria}`) |
| POST | `/api/juego/reportar-error` | "Creo que la IA se equivocó" |
| GET | `/api/juego/sesion` · `/api/juego/estadisticas` | Marcador de la sesión; acierto humano, matriz de confusión humana, humano vs. IA (filtrable por nivel de certeza) |
| GET | `/api/juego/aprendizaje` | Acierto por número de intento, primera vs. segunda mitad, tasa de corrección tras explicación, ronda 1 vs. ronda 2, tamaño de muestra |
| POST | `/api/juego/prueba-aprendizaje` | Iniciar una ronda de la prueba controlada (`{alias, ronda, residuos}`), con orden aleatorio |
| GET | `/api/botes` | Nivel estimado, capacidad y estado de cada bote |
| POST | `/api/botes/{id}/vaciar` | Marcar un bote como vaciado |
| PUT | `/api/botes/{id}` | Ajustar la capacidad calibrada |
| GET/POST | `/api/dataset/por-verificar` | Listar y aprobar/rechazar etiquetas aportadas por usuarios |
| POST | `/api/manual/{accion}` | Control manual (posición, trampilla, luz); se registra como manual |
| GET | `/captures/{archivo}` | Fotos |
| WS | `/ws/eventos` | Eventos en tiempo real hacia el panel |

> **Formato JSON y agregados (2026-11-19):** los cuerpos y respuestas de cada ruta, los eventos del WebSocket y las rutas agregadas (`/api/revision`, `/api/pruebas/residuos`, `/api/juego/continuar`, `/api/manual/ang`, `/api/sim/*`) están en [`docs/api_contrato.md`](api_contrato.md).

---

## 18. Panel (React + Vite)

| Vista | Contenido |
|---|---|
| **Inicio / Menú** | Botones grandes "Usar IA" y "Adivinar"; sincronizado con el teclado y la voz |
| **En vivo** | Última foto, categoría, barra de confianza, las 3 probabilidades, estado de la máquina, alerta de dudoso con botones para resolver, **3 barras de nivel de los botes** (rotuladas "ESTIMADO") |
| **¿Le ganas a la IA?** | Durante el juego: botones de las 3 categorías y cuenta regresiva; resultado a pantalla completa (verde = correcto, rojo = incorrecto, amarillo = certeza media) con la respuesta del usuario, el bote de referencia y su color, la **confianza de la IA** y la fuente de la referencia, y la **explicación completa**; botón "Creo que la IA se equivocó" (destacado en certeza media); marcador de la sesión |
| **Humano vs. IA** | % de acierto humano total y por categoría, matriz de confusión humana, comparación con la IA, parejas de confusión más frecuentes, filtro por nivel de certeza |
| **Aprendizaje** | Gráfica de % de acierto por número de intento, barras ronda 1 vs. ronda 2 de la prueba controlada, primera vs. segunda mitad, tasa de corrección tras explicación, **n de la muestra** y rótulo "muestra pequeña" cuando aplique; control para iniciar la prueba controlada (alias y ronda) |
| **Botes** | Nivel, piezas/capacidad, estado (normal, casi lleno, lleno/bloqueado), botón "Marcar como vaciado", historial de vaciados, residuos desviados por categoría |
| **Historial** | Tabla filtrable (hora, foto miniatura, predicción, confianza, final, origen, corregido) con botón "Corregir" |
| **Estadísticas** | Conteo por categoría, tasa de acierto, matriz de confusión, tiempo promedio por residuo, residuos desviados |
| **Pruebas** | Cronómetro para la corrida manual, registro de la corrida con sistema y **tabla comparativa** lado a lado |
| **Configuración** | Umbrales, calibración de ángulos, modo por defecto, capacidades de los botes, botón reentrenar, revisión de etiquetas "por verificar", control manual |

Diseño limpio, legible a distancia (el jurado lo verá en la mesa), colores consistentes con los botes (verde, azul, gris) y amarillo para revisión. Todo dato simulado lleva una etiqueta visible **"SIMULADO"**.

---

## 19. Estructura del repositorio

```
cyber-insanos-clasificador/
├── firmware/clasificador_uno/clasificador_uno.ino
├── backend/
│   ├── app/ (main.py, config.py, serial_link.py, camera.py, model.py,
│   │         voice.py, orchestrator.py, game.py, bins.py, lcd_ui.py,
│   │         db.py, routes.py)
│   ├── training/ (capturar_dataset.py, train.py, evaluate.py)
│   ├── data/ (keywords.json, explicaciones.json)
│   ├── dataset/{organica,inorganica,peligroso,_por_verificar}/
│   ├── models/  ·  captures/
│   └── requirements.txt
├── frontend/ (Vite + React)
├── cad/ (archivos SolidWorks .SLDPRT/.SLDASM, .STL y .3mf/.gcode laminados)
└── docs/ (memoria_tecnica.md, bitacora.md, recursos_externos.md,
           diagrama_electrico, resultados_pruebas.csv)
```

---

## 20. Pruebas y validación

1. **Pruebas unitarias mínimas:** reglas de decisión, normalización de voz, parser del protocolo serial, **evaluación de adivinanzas** (correcta, incorrecta, sin respuesta, IA dudosa, reporte de error, recalificación), **selección del nivel de certeza y del tono** (límites exactos 0.60 y 0.80), **cálculo de la curva de aprendizaje** (acierto por intento, mitades, tasa de corrección tras explicación, exclusión de certeza media), **selección de explicación** por pareja de confusión, **contador de botes** (suma con `DROP_OK` y `DROP_TIMEOUT`, aviso al 80 %, bloqueo al 100 %, vaciado) y recorte de textos a 20 caracteres sin acentos para la LCD.
2. **Modo simulación:** el backend debe poder correr **sin Arduino** (puerto serial simulado) y **sin cámara** (imágenes de carpeta), para que el frontend y la IA avancen en paralelo con el hardware. Los datos generados así se marcan como simulados.
3. **Prueba de 3 ciclos** consecutivos correctos, registrados.
4. **Prueba oficial:** 20 residuos × 2 corridas (manual cronometrada y sistema) → tabla comparativa, matriz de confusión, % de acierto, tiempo promedio y residuos desviados.
5. **Prueba controlada de aprendizaje** (sección 12.5): 3–5 voluntarios, 10 residuos, ronda 1 vs. ronda 2.
6. **Ensayo de la demo** con los 3 momentos obligatorios y, si el tiempo de la defensa lo permite, 2 momentos extra:
   - **Momento 4 — Modo Adivina:** un integrante del jurado adivina; se muestra una respuesta incorrecta con su explicación y la confianza de la IA, y el residuo cae en el bote correcto. Se muestra también la gráfica de aprendizaje con los resultados de la prueba controlada.
   - **Momento 5 — Bote lleno:** con la capacidad de un bote ajustada temporalmente a un valor bajo (indicarlo al jurado), se muestra el aviso, el bloqueo y el vaciado.

---

## 21. Entregables que debes ayudar a producir

- Código fuente completo y comentado (firmware, backend, entrenamiento y frontend).
- CAD editable + archivos de fabricación con parámetros.
- Diagrama electrónico y tabla de conexiones.
- **Memoria técnica breve** (problema, objetivos medibles, arquitectura, decisiones, resultados, límites, riesgos, impacto).
- **Bitácora** de desarrollo (hora, quién, qué, problema, solución).
- **Declaración de recursos externos:** bibliotecas, modelos preentrenados, tutoriales y herramientas de IA usadas, indicando **qué generó cada una y qué modificó el equipo**.
- Guion de defensa: 7 min de exposición, 7 min de demostración y 6 min de preguntas, con preguntas probables del jurado y sus respuestas.

---

## 22. Plan de trabajo por fases (entrega en este orden)

| Fase | Entregable | Criterio de "listo" |
|---|---|---|
| 0 | Lista de descargas/instalaciones, verificación de dimensiones y decisión del servo | Todo instalado; medidas reales registradas |
| 1 | CAD de las piezas impresas prioritarias + parámetros de laminado | Enviadas a imprimir antes de las 12:00 |
| 2 | Firmware con protocolo serial + prueba desde el Monitor Serial | Disco y trampilla responden a comandos; IR envía `OBJ` |
| 3 | Backend con modo simulación + SQLite + API | Ciclo completo simulado registrando en la BD |
| 4 | Captura de dataset + entrenamiento + evaluación | Precisión de validación reportada con matriz de confusión |
| 5 | Integración real (cámara + IA + Arduino) | 3 ciclos reales correctos |
| 6 | Panel React | Vista en vivo, historial, corrección y estadísticas funcionando |
| 7 | **Aviso de bote lleno** (contador, calibración, bloqueo, vaciado por panel y teclado) | Bloqueo y vaciado demostrados con una capacidad de prueba |
| 8 | **Menú + modo "¿Le ganas a la IA?"** (teclado, LCD, panel, explicaciones, niveles de certeza, marcador, curva de aprendizaje) | Acierto y error con explicación y confianza en LCD y panel; tono prudente en certeza media; residuo siempre en el bote correcto; vista Aprendizaje con datos |
| 9 | Voz (menú, adivinanza y dudosos) + reentrenamiento | Dudoso resuelto por voz y reflejado en `_por_verificar` |
| 10 | Prueba oficial de 20 residuos + prueba controlada de aprendizaje + documentación + guion | Tabla comparativa, ronda 1 vs. ronda 2 y entregables completos |

**Reglas:**
- No avances a la fase 7 si la fase 5 no es estable. El ciclo cerrado con la cámara vale más que cualquier extra.
- El aviso de bote lleno va **antes** que el modo Adivina porque es más corto y protege el funcionamiento del ciclo.
- Desde la fase 3, el orquestador debe dejar preparados los estados MENÚ, VERIFICAR_BOTE y ESPERA_ADIVINANZA (aunque al inicio solo pasen de largo), para no reestructurar después.

---

## 23. Cómo debes trabajar y responder

1. **Antes de escribir código**, confirma en una lista breve los supuestos que hagas (puerto COM, índice de cámara, medidas de los botes, servo elegido) y marca con `[COMPLETAR]` lo que el equipo debe medir o decidir.
2. Crea o modifica **directamente los archivos completos** en el repositorio, en la ruta indicada en la sección 19 (no fragmentos sueltos).
3. Comentarios y textos de interfaz **en español**; nombres de variables claros y consistentes.
4. Manejo de errores en cada frontera (serial desconectado, cámara no disponible, modelo no cargado): el sistema debe **fallar de forma segura** (trampilla cerrada, disco en HOME, aviso en el panel).
5. Toda configuración en un solo lugar (`config.py` + tabla `config`), sin valores mágicos dispersos.
6. Después de cada fase, indica **cómo probarla** (comandos exactos) y **qué debe ver el equipo** si funciona.
7. Para cada decisión técnica importante, añade una nota de **"Cómo defenderlo ante el jurado"** (2–3 líneas).
8. **No inventes mediciones ni resultados.** Si un dato no se ha medido, déjalo como pendiente.
9. Mantén la solución simple: si algo no aporta a la rúbrica o al reto, propónlo como ampliación, no lo implementes.

**Empieza por la Fase 0.**
