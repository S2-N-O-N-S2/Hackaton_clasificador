# Prompts para la Persona B — Firmware (Fase 2) y Panel (Fase 6)

## Reparto del software

| | Persona A | Persona B |
|---|---|---|
| Carpetas | `backend/` | `firmware/` y `frontend/` |
| Orden | Fase 3 (backend con simulación) → Fase 4 (scripts de IA) | **Fase 2 (firmware) → Fase 6 (panel)** |
| Se juntan en | Fase 5: integración real | Fase 5: integración real |

**Contrato entre los dos:** [`docs/api_contrato.md`](api_contrato.md). Define el JSON de la API, los eventos del WebSocket y el detalle del protocolo serial. **No se cambia sin avisar a la otra persona.**

**Reglas para no pisarse:**
- B solo edita `firmware/`, `frontend/` y sus propios documentos de `docs/` (`diagrama_electrico.md`, `prueba_firmware.md`).
- En `docs/bitacora.md` y `docs/recursos_externos.md`, solo se **agregan filas al final**.
- Si usan git: ramas `fase-2-firmware` y `fase-6-panel`.

## Qué necesita tener la Persona B

**Lo mejor:** el repositorio completo (clonado de GitHub o copiado por USB **sin** `backend/.venv`).

**Mínimo indispensable** (conservando las carpetas):
```
CLAUDE.md
docs/ESPECIFICACION.md
docs/api_contrato.md
docs/prompts_persona_b.md
docs/bitacora.md
docs/recursos_externos.md
firmware/README.md
frontend/README.md
```

**Software en su laptop:**
- **Arduino IDE 2.x**, con estas bibliotecas del Gestor de bibliotecas:
  - **LiquidCrystal I2C** (Frank de Brabander)
  - **Keypad** (Mark Stanley, Alexander Brevig)
  - `Servo` y `EEPROM` ya vienen incluidas.
- **Node.js ≥ 20 y npm**, para Vite + React. Hay que correr `npm install` **con buena red** (~100 MB en `node_modules`).
- Para probar el firmware: un Arduino UNO, un servo, la LCD I2C, el teclado 4×4, un FC-51 y LEDs. **No hace falta la estructura física.**

---

## Prompt 1 — Fase 2: Firmware del Arduino UNO

```
Fase 2 (especificación: secciones 8, 9 y 10; contrato: docs/api_contrato.md sección 5).
Trabajamos el software entre dos personas; lee docs/prompts_persona_b.md. Yo soy la Persona B: me tocan firmware/ y
frontend/. La Persona A hace el backend. Lee CLAUDE.md, docs/ESPECIFICACION.md (secciones 8, 9 y 10) y
docs/api_contrato.md (sección 5, que es OBLIGATORIA: respuestas, errores y comandos agregados).

Crea firmware/clasificador_uno/clasificador_uno.ino que implemente EXACTAMENTE el protocolo de la sección 9 de la
especificación más las aclaraciones de la sección 5 del contrato:
- Pines de la sección 8.1 agrupados como constantes al inicio (no quedan pines libres; D13 tiene el LED de la placa).
- Servo del disco (D9) con rampa no bloqueante (1° cada 20 ms, constante editable), acercándose siempre desde abajo
  para eliminar el juego mecánico; servo de la trampilla (D10): cerrada 0° / abierta 90° (constantes [COMPLETAR]),
  abierta 600 ms. Nunca se mueven los dos servos a la vez (si llega una orden de movimiento → ERR:OCUPADO).
- FC-51 #1 (D2, activo en BAJO) con antirrebote: OBJ al quedar estable ≥ 300 ms y LIBRE al quedar vacío ≥ 300 ms,
  una sola vez por flanco. FC-51 #2 (D3) por interrupción (INT1) para no perder objetos rápidos: DROP_OK o
  DROP_TIMEOUT (2 s desde que se abre la trampilla).
- LCD 20×4 I2C (dirección 0x27 en una constante): LCD:<l1>|<l2>|<l3>|<l4> y LCD_SCROLL:<texto> en la línea 4,
  recortando si llega algo largo.
- LEDs A0/A1/A2 con LED:<VERDE|AMARILLO|ROJO|OFF>[:PARPADEO]; iluminación en A3 (TIP120) con LIGHT:ON/OFF.
- Teclado 4×4 → solo envía KEY:<tecla> (ninguna lógica de menús en el Arduino).
- Ángulos en EEPROM con CAL:<id>:<ángulo> (con una marca de "EEPROM válida"); valores por defecto 170/90/10 y
  HOME 90 SOLO si la EEPROM está vacía. POS, ANG, HOME y STATUS según el contrato.
- Validación de cada comando y respuesta SIEMPRE (OK, *_OK o ERR:<código> del contrato); líneas de hasta 80
  caracteres; ignora \r.
- Watchdog lógico: 15 s sin comandos → HOME, trampilla cerrada y mensaje WATCHDOG.
- Todo con millis(), sin delay() largos (solo se permite en setup()). Al arrancar: trampilla cerrada, HOME, READY.
- Código comentado en español, dividido en secciones claras (pines, configuración, servos, sensores, LCD, LEDs,
  teclado, parser, watchdog) para que cualquiera del equipo pueda modificar una función en vivo.

Además:
1. firmware/escaner_i2c/escaner_i2c.ino: escáner para encontrar la dirección de la LCD.
2. docs/diagrama_electrico.md: tabla completa de conexiones (pin, componente, cable, nota); alimentación de servos
   SEPARADA a 5–6 V con tierra común y capacitor de 1000 µF; corriente pico esperada (MG996R ~2.5 A bloqueado,
   SG90 ~0.65 A) y cómo verificar la fuente; TIP120 con resistencia de base de 1 kΩ (y diodo si la carga es
   inductiva); descripción para armarlo en Tinkercad Circuits o Fritzing.
3. Checklist con las 3 mediciones con multímetro (voltaje de los servos en reposo y en movimiento, voltaje de la
   iluminación, continuidad de GND común) y la falla diagnosticable (servos en el 5 V del Arduino → caída de voltaje
   → el Arduino se reinicia y vuelve a mandar READY), con cómo provocarla de forma segura y cómo diagnosticarla.
4. docs/prueba_firmware.md: cada comando para escribir en el Monitor Serial (115 200, "Nueva línea") con la respuesta
   esperada, incluidos los casos de error y el watchdog.
5. Si el Arduino IDE (arduino-cli) está disponible en esta laptop, compila el sketch y muéstrame el resultado;
   si no, dime cómo compilarlo yo y qué memoria debe ocupar (RAM < 75 % del UNO).

Listo cuando: cada comando responde según el protocolo en el Monitor Serial. Si encuentras algo del contrato que
no se pueda cumplir, NO lo cambies: dime qué avisarle a la Persona A. Cierra con filas al final de docs/bitacora.md
y docs/recursos_externos.md (bibliotecas usadas y qué generó la IA), notas "Cómo defenderlo ante el jurado"
(no bloqueante, watchdog, alimentación separada) y un mensaje de commit propuesto "fase 2: ...".
No hagas git add, commit ni push.
```

---

## Prompt 2 — Fase 6: Panel React (después de la Fase 2)

```
Fase 6 (especificación: sección 18; contrato: docs/api_contrato.md secciones 1–4, 6 y 7).
Soy la Persona B (frontend/). La Persona A hace el backend en paralelo; quizá todavía no esté listo. Lee CLAUDE.md,
docs/ESPECIFICACION.md (secciones 11, 12.2, 13 y 18) y docs/api_contrato.md completo.

Crea el panel con Vite + React en frontend/:
- La URL del backend va en UN solo archivo: frontend/src/config.js.
- Modo de datos de ejemplo (variable VITE_MOCK=1): usa JSON en frontend/src/mock/ copiados de los ejemplos del
  contrato y simula eventos del WebSocket (un ciclo completo cada pocos segundos), para avanzar sin backend.
  Con VITE_MOCK=0 usa el backend real.
- Capa de API en un solo módulo (frontend/src/api.js) con una función por endpoint del contrato; y un hook o módulo
  del WebSocket con reconexión (1, 2, 5, 5 s), latido ping/pong y polling de GET /api/estado cada 2 s mientras no
  haya conexión, mostrando "Sin conexión en vivo".
- Una sola fuente de verdad: el panel SOLO muestra lo que manda el backend (contrato, sección 6). No calcula reglas,
  niveles de certeza ni estadísticas.
- Vistas: Inicio/Menú (botones grandes "Usar IA" y "Adivinar"), En vivo (última foto, categoría, barra de confianza,
  las 3 probabilidades, umbral vigente, estado de la máquina, alerta de dudoso con botones para resolver vía
  POST /api/revision, 3 barras de nivel de los botes rotuladas ESTIMADO), Historial (tabla filtrable con miniatura y
  botón Corregir), Estadísticas (conteos, tasa de acierto, matriz de confusión, tiempo promedio, desviados), Pruebas
  (registro de los residuos de prueba, cronómetro para la corrida manual, registro de la corrida con sistema y tabla
  comparativa lado a lado) y Configuración (umbrales, ángulos, modo por defecto, capacidades de los botes, botón
  Reentrenar con su estado, revisión de etiquetas "por verificar", control manual incluido ANG para calibrar).
- Deja creadas, aunque sean sencillas, las vistas ¿Le ganas a la IA?, Humano vs. IA, Aprendizaje y Botes. Su
  contenido completo llega en las fases 7 y 8, pero ya tienes el JSON en el contrato: si te sobra tiempo, avanza
  con los datos de ejemplo.
- Diseño legible a distancia (el jurado lo ve en la mesa): letra grande, colores del contrato (verde, azul, gris) y
  amarillo para revisión; etiqueta SIMULADO visible cuando "simulado" sea true; ESTIMADO en todo nivel de bote.
  Debe verse bien también en el navegador de un celular (diseño responsivo); NO es una app nativa.
- Sin bibliotecas de UI pesadas. Las gráficas (matriz de confusión, barras, curva de aprendizaje) hazlas con SVG o
  CSS propio; si crees que una biblioteca es imprescindible, justifícala y pídeme confirmación antes de instalarla.
- Antes de npm install, dime el tamaño aproximado de la descarga.

Listo cuando: con VITE_MOCK=1 el panel muestra un ciclo simulado en vivo y permite corregir una clasificación; y
cuando el backend de la Persona A esté corriendo (SIMULACION=1), lo mismo funciona con VITE_MOCK=0. Si el backend
no cumple el contrato, NO cambies el contrato: dime qué avisarle a la Persona A.
Dime los comandos exactos para correrlo (npm run dev -- --host) y cómo abrirlo desde un celular en la misma red.
Cierra con filas al final de docs/bitacora.md y docs/recursos_externos.md, notas "Cómo defenderlo ante el jurado"
(una sola fuente de verdad, reconexión, rótulos SIMULADO/ESTIMADO) y un mensaje de commit propuesto "fase 6: ...".
No hagas git add, commit ni push.
```

---

## Prompt 3 — Preparar el dataset para entrenar la IA

### Requisitos del dataset (acordados con la Persona A)

**1. Estructura de carpetas y nombres (obligatorio)**
```
backend\dataset\
  organica\    platano1__001.jpg  platano1__002.jpg  manzana1__001.jpg ...
  inorganica\  lata1__001.jpg  botella1__001.jpg ...
  peligroso\   pila1__001.jpg  blister1__001.jpg ...
```
- Las carpetas se llaman exactamente `organica`, `inorganica` y `peligroso` (minúsculas, sin acentos).
- **Cada nombre lleva el ID del objeto físico antes de `__`.** Todas las fotos del mismo objeto llevan el mismo ID, y objetos distintos llevan IDs distintos (aunque sean del mismo tipo: `platano1`, `platano2`).
  - **Por qué:** el entrenamiento separa entrenamiento y validación **por objeto**. Sin el ID, cada foto cuenta como un objeto distinto, el mismo plátano termina en los dos lados y la precisión reportada sale inflada (falsa).
- Un mismo ID **no** debe aparecer en dos categorías.

**2. Cantidad**
- **Mínimo:** 2 objetos distintos por categoría. Sin eso el entrenamiento no arranca.
- **Meta:** 5–6 objetos por categoría y 40–60 fotos por categoría (unas 8–10 fotos por objeto, con distintas posiciones, orientaciones y lados).

**3. Normalización de las imágenes**
- ✅ **Reducir** a un máximo de 320 px por lado, **manteniendo la proporción** (por ejemplo 640×480 → 320×240), en **JPG**.
- ❌ **NO recortar a 224×224** ni a ningún cuadro. El sistema ya hace ese paso, igual al entrenar y al clasificar en vivo: toma la imagen **completa**, aplica la zona de interés (`roi` de la configuración) y la ajusta a 224×224. Si el dataset viene recortado y en vivo la cámara da la imagen completa, la IA ve los objetos de otro tamaño y falla en la demo aunque la validación salga alta.
- ❌ No cambiar colores, brillo ni contraste, no aplicar filtros y no rotar (salvo para corregir fotos que estén de lado).
- Si quieren quitar bordes que no son la bandeja, avisen a la Persona A para ajustar la `roi`. No lo hagan recortando las fotos.

**4. Origen de las fotos**
- Lo ideal es la **misma cámara (el celular con DroidCam), la misma bandeja y la misma luz de la demo** (especificación §14.1).
- Si alguna foto viene de internet o de otra cámara, avisen y anótenlo en `docs/recursos_externos.md` (fuente y licencia). Esas fotos funcionan peor en la demo.
- No incluyan el objeto "dudoso" de la demo (momento 3) ni, de preferencia, los 20 residuos de la prueba oficial.

**5. Verificación antes de entregar**
```powershell
cd backend; .\.venv\Scripts\Activate.ps1; python tools\revisar_dataset.py --max-lado 320
```
Debe terminar con **"LISTO PARA ENTRENAR"**. Si muestra ERRORES, corríjanlos. Los AVISOS conviene revisarlos.

### Prompt para Claude Code (Persona B)

```
Necesito preparar el dataset de fotos para entrenar la IA (lee docs/prompts_persona_b.md, "Prompt 3",
y docs/ESPECIFICACION.md §14.1). Soy la Persona B. Excepción acordada: puedo crear UN archivo en el backend,
backend/tools/normalizar_dataset.py; no modifiques nada más de backend/.

Tengo las fotos originales en <RUTA_DE_LAS_FOTOS_ORIGINALES> [COMPLETAR], organizadas así: [COMPLETAR: cómo están
organizadas, por ejemplo una carpeta por objeto o por categoría].

Crea backend/tools/normalizar_dataset.py que:
1. Lea las fotos originales y las copie (sin modificar los originales) a backend/dataset/<organica|inorganica|peligroso>/.
2. Reduzca cada foto a un máximo de 320 px por lado, MANTENIENDO LA PROPORCIÓN (cv2.INTER_AREA), y la guarde en JPG
   (calidad 92). NO recortes a 224×224 ni a cuadro; NO cambies colores ni brillo.
3. Renombre cada foto como <objeto_id>__<nnn>.jpg, donde objeto_id identifica al OBJETO FÍSICO (minúsculas, sin acentos,
   sin espacios; por ejemplo platano1). Pregúntame cómo saber el objeto de cada foto si no es evidente por la carpeta.
4. Agregue cada foto a backend/dataset/metadatos.csv con las columnas
   archivo,clase_id,clase,objeto_id,fecha_hora,camara (clase_id: 0 organica, 1 inorganica, 2 peligroso).
5. No sobrescriba fotos existentes (si el nombre existe, use el siguiente número) y muestre un resumen de fotos y
   objetos por categoría.
6. Tenga una opción --simular que solo muestre lo que haría, sin copiar nada.

Usa solo lo que ya está en backend/requirements.txt (OpenCV, numpy). Comentarios en español.
Al terminar, corre: python tools\revisar_dataset.py --max-lado 320 y muéstrame el resultado.
No hagas git add, commit ni push. Agrega una fila al final de docs/bitacora.md.
```

### Al terminar, la Persona A entrena y prueba
```powershell
python -m training.train
```
```powershell
python -m training.evaluate
```
```powershell
python tools\probar_modelo_vivo.py
```

---

## Prompt 4 — Probar el firmware con el hardware real (antes de la Fase 5)

**Contexto:** el firmware (`firmware/clasificador_uno/clasificador_uno.ino`) ya está en `main`, pero **solo se revisó leyendo el código: nunca se ha compilado ni cargado en un Arduino.** El backend y la IA (modelo v1) ya funcionan. Este paso deja el Arduino listo para conectarlo al backend (Fase 5, `docs/integracion_fase5.md`).

**Material:** Arduino UNO, MG996R (disco), SG90 (trampilla), fuente regulada de 5.5–6.0 V y ≥ 3 A, capacitor de 1000 µF, LCD 20×4 I2C, teclado 4×4, 2 FC-51, LEDs (verde, amarillo y rojo) con 220–330 Ω, TIP120 con 1 kΩ, tira LED y multímetro.

**Cableado:** `docs/diagrama_electrico.md` §1 y §2. **Los servos NUNCA van al 5 V del Arduino**: fuente externa + tierra común + capacitor (franja − a GND).

**Orden recomendado (por partes, para aislar fallas):**
1. Sin servos: LCD (con el escáner I2C), LEDs, teclado y sensores.
2. Servo del disco con la fuente externa.
3. Servo de la trampilla.
4. Todo junto, con el disco y los botes montados (si ya existen).

### Prompt para Claude Code (Persona B)

```
Soy la Persona B (firmware y panel; lee docs/prompts_persona_b.md, "Prompt 4"). Ya tengo el hardware para probar el
firmware de verdad. Lee CLAUDE.md, docs/diagrama_electrico.md, docs/prueba_firmware.md, docs/api_contrato.md §5 y
firmware/clasificador_uno/clasificador_uno.ino. Solo puedes editar firmware/, docs/diagrama_electrico.md,
docs/prueba_firmware.md y agregar filas al final de docs/bitacora.md. No toques backend/ ni frontend/.
No hagas git add, commit ni push.

Guíame paso a paso, UNO a la vez, esperando a que te diga qué pasó:
1. Revisar el cableado contra docs/diagrama_electrico.md §1 (te describo o te mando foto de lo que tengo).
   Antes de energizar: continuidad de la GND común (medición 3) y polaridad del capacitor y de los LEDs.
2. Cargar firmware/escaner_i2c/escaner_i2c.ino y, según la dirección que salga, ajustar LCD_DIRECCION.
3. Compilar y cargar firmware/clasificador_uno/clasificador_uno.ino (placa Arduino UNO). Si hay errores de
   compilación, corrígelos sin cambiar el protocolo del contrato.
4. Probar desde el Monitor Serial (115200, "Nueva línea") la lista de docs/prueba_firmware.md §2, por partes:
   primero READY, PING, STATUS, LCD, LCD_SCROLL, LED, LIGHT, KEY (cada tecla del teclado: si salen cambiadas, ajustar el
   mapa de teclas o el orden de los cables) y OBJ/LIBRE con los FC-51 (ajustar su potenciómetro);
   después POS:0/1/2, ANG, HOME, CAL y DROP (DROP_OK con un objeto que caiga, DROP_TIMEOUT sin objeto);
   ERR:OCUPADO mandando POS mientras gira; WATCHDOG (15 s sin comandos).
5. Ajustar con el mecanismo armado: ANG_TRAMPILLA_CERRADA / ANG_TRAMPILLA_ABIERTA y PASO_DISCO_MS (más grande =
   más suave). Si PASO_DISCO_MS pasa de 30, avisar a la Persona A: el backend espera máximo 6 s por cada giro
   (timeout_pos_s en backend/app/config.py).
   Los ángulos de los botes NO se editan en el código: se calibran en la Fase 5 con tools/calibrar_angulos.py.
6. Mediciones con el multímetro de docs/diagrama_electrico.md §4 (1a, 1b, 2 y 3). Anota SOLO valores medidos de
   verdad; si algo no se midió, déjalo como [COMPLETAR]. Si 1b < 4.8 V, ayúdame a diagnosticarlo.
7. Falla diagnosticable (docs/diagrama_electrico.md §5), solo con el SG90 y menos de un minuto. Anotar lo observado
   (READY inesperado, voltaje mínimo medido) y la solución.
8. Actualizar los [COMPLETAR] de docs/diagrama_electrico.md y docs/prueba_firmware.md con lo medido, y agregar una fila
   en docs/bitacora.md (hora, qué se probó, problemas, solución).
Al final dame un resumen: qué comandos pasaron, qué se cambió en el firmware y qué falta, y proponme el mensaje de commit
"fase 2: firmware probado con hardware". Recuérdame CERRAR el Monitor Serial antes de conectar el backend.
```

### Al terminar, se juntan A y B (Fase 5)
La Persona A conecta el Arduino a la laptop de la demo y sigue `docs/integracion_fase5.md` desde el **Bloque 1**. La calibración de ángulos (Bloque 3) conviene hacerla juntos: uno mueve el disco con `tools\calibrar_angulos.py` y el otro revisa dónde cae el residuo.
