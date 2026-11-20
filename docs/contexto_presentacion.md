# Contexto del sistema para la presentación — Cyber Insanos · Reto 1

> Resumen de todo el sistema y lista de puntos que se pueden **verificar en vivo**.
> Estado al 20-nov-2026. ✅ = probado · 🟡 = hecho en código, falta probarlo en la máquina real · ⏳ = pendiente.
> Regla del equipo: **no se presenta ningún dato que no se haya medido.** Lo simulado se dice que es simulado.

---

## 1. El problema y la idea en una frase
La basura mezclada no se recicla. Nuestro prototipo **ve el residuo con una cámara, lo clasifica con IA y lo manda solo al bote correcto**: Orgánica (verde), Inorgánica (azul) o Peligroso (gris). Si no está seguro, **no adivina**: le pide ayuda a una persona.

## 2. El ciclo cerrado (lo que pide el reto)
```
Detectar (sensor IR) → Fotografiar (cámara) → Clasificar (IA) → Girar el carrusel al bote → Soltar → Registrar (SQLite + panel)
```
- Si la confianza es baja, si puede ser peligroso o si el objeto es desconocido → **REVISIÓN**: el residuo no cae.
- La revisión se resuelve por **voz** o con los **botones del panel**, y queda registrada.

## 3. Arquitectura (quién hace qué)
| Pieza | Tecnología | Qué hace |
|---|---|---|
| **Arduino UNO** | C++ (`Servo`) | Solo obedece comandos y reporta sensores. Mueve el servo y enciende LEDs. **Sin LCD, teclado ni sensor de caída:** todo se maneja desde la página y por voz. |
| **Comunicación** | Serial USB, 115 200 baudios, texto (`POS:1` → `POS_OK:1`, `DROP` → `DROP_OK`) | Protocolo simple que se puede probar a mano desde el Monitor Serial. |
| **Backend / cerebro** | Python 3.12 + FastAPI | `orchestrator.py` tiene **toda** la lógica de estados. Si algo falla → estado ERROR seguro. |
| **IA** | MobileNetV2 (preentrenada, congelada) + regresión logística | Da 3 probabilidades. Promedia 3 fotos. Detecta objetos "desconocidos". |
| **Voz** | Vosk (offline) + voz de Windows (Laura, es-ES) | Escucha solo al presionar «Hablar» en la página y dice el resultado en voz alta. |
| **Base de datos** | SQLite | `clasificador.db` (real) y `clasificador_sim.db` (simulación, separada). |
| **Panel** | React + Vite, REST + WebSocket | **Única interfaz de la máquina** (sustituye LCD y teclado): menú, pantalla de la máquina, en vivo, historial, corrección, estadísticas, juego, botes y configuración. Se instala en el celular como app (PWA). |

**Todo funciona sin internet.** Solo hace falta una red local para que el celular abra el panel.

## 4. Decisiones clave (para defender)
1. **El sistema no adivina.** Si la confianza es menor a 0.60, o si p(peligroso) es ≥ 0.35 sin ser la ganadora → revisión. `_depositar()` se niega a soltar sin una categoría válida y sin la confirmación `POS_OK` del bote correcto.
2. **Asimetría de riesgo:** mandar un peligroso al bote orgánico es el peor error, por eso el peligroso tiene un umbral propio más bajo.
3. **Falla segura:** si se pierde el serial, la cámara o el modelo → el disco va a HOME, la trampilla se queda cerrada, se prende el LED rojo y sale un aviso en el panel.
4. **Una sola fuente de verdad:** las reglas viven en Python. El Arduino y el panel solo ejecutan y muestran.
5. **Transfer learning:** con pocas fotos no se puede entrenar una red desde cero. MobileNetV2 convierte cada foto en 1 280 números y encima entrenamos un clasificador que aprende en segundos en CPU.
6. **Validación honesta:** separamos entrenamiento y validación **por objeto**, no por foto, para que el modelo no "haga trampa".
7. **Objetos desconocidos:** la IA siempre elige una de 3 clases. Por eso medimos qué tan lejos queda la foto de lo que conoce, y lo raro se manda a revisión.
8. **Reentrenamiento seguro:** las correcciones de usuarios esperan en `_por_verificar/` hasta que el operador las aprueba. Un modelo nuevo solo se activa si no empeora.
9. **Simulación marcada:** con `SIMULACION=1` todo corre sin hardware, pero queda marcado como **SIMULADO** y va a otra base de datos.
10. **Voz que no manda sobre la seguridad:** si la voz dice "botella" y la cámara ve algo orgánico → revisión (`conflicto_voz`).

## 5. Innovaciones
- **"¿Le ganas a la IA?"** Hay dos versiones:
  - **Con fotos:** ✅ funciona. Tiene 1 200 fotos y elige 5–30 preguntas repartidas entre las 3 clases. Lleva puntos, racha y resultado por categoría.
  - **Con la máquina:** ⏳ el estado `ESPERA_ADIVINANZA` todavía "pasa de largo" (Fase 8).
- **Aviso de bote lleno (ESTIMADO):** 🟡 el nivel se calcula contando piezas contra una capacidad. Hay aviso al 80 % y bloqueo al 100 %, y se vacía desde el panel. Falta calibrar la capacidad real y demostrarlo.
- **Voz offline:** ✅ menú por voz, resolver dudosos y "¿dónde tiro…?". El sistema dice la categoría, la certeza y el bote.
- **App móvil (PWA):** 🟡 instalable (verificado en Edge). Falta probarla en un celular real.

## 6. Resultados medidos (solo lo real)
| Qué | Resultado | Ojo |
|---|---|---|
| Modelo v1: validación | **98 %** (294/300). Orgánica 100 %, Inorgánica 96 %, Peligroso 98 % | Medido con fotos de **The Garbage Dataset** (internet), no con fotos de nuestra bandeja. Falta validarlo en la posición final de la cámara. |
| Pruebas automáticas | **155 pruebas pytest pasan** | Reglas, protocolo, botes, voz, LCD, cámara, práctica, ciclo simulado. |
| Auditoría de carga | 3 000 usuarios virtuales, 33 056 peticiones, p95 162 ms, 0 hallazgos en la corrida final (antes encontró 5 fallas, ya corregidas) | **Simulación:** no reemplaza la prueba con personas. |
| Firmware | Compila (36 % del flash, 60 % de la RAM), cargado en el UNO (COM6), todos los comandos responden | Sin servos ni LCD con la fuente externa todavía. |
| 3 ciclos reales | ⏳ [COMPLETAR] | Ver `docs/resultados/ciclos_reales.md`. |
| Prueba oficial 20 residuos (manual contra sistema) | ⏳ [COMPLETAR] | |

---

## 7. Lista de verificación en vivo
Cada punto dice **cómo probarlo** y **qué se debe ver**. Antes de presentar, levantar el sistema:

```powershell
cd backend; .\.venv\Scripts\Activate.ps1; $env:SIMULACION="0"; uvicorn app.main:app --port 8000
```
```powershell
cd frontend; npm run dev -- --host
```
(Sin Arduino: `$env:SIMULACION="1"`. Con cámara e IA reales pero Arduino simulado: además `$env:SIM_IA_REAL="1"`.)

### A. Software (se puede probar ya)
| # | Punto | Cómo | Qué debe verse | Estado |
|---|---|---|---|---|
| A1 | Pruebas automáticas | `cd backend; python -m pytest -q` | `155 passed` | ✅ |
| A2 | Backend vivo | Abrir `http://localhost:8000/docs` | Lista de rutas de la API | ✅ |
| A3 | Panel en vivo | `http://localhost:5173` | Estado de la máquina, conexión y carrusel | ✅ |
| A4 | Clasificación con IA | Poner un objeto frente a la cámara (`SIM_IA_REAL=1`) | Foto, categoría, **3 probabilidades** y umbral | ✅ |
| A5 | "No adivina" | Mostrar un objeto raro o ambiguo | Va a **REVISIÓN**, LED amarillo, aviso y "Pantalla de la máquina" pidiendo ayuda en el panel | ✅ en simulación |
| A6 | Cambio de función en vivo | Configuración → subir `UMBRAL_GENERAL` de 0.60 a 0.80 | Un objeto que antes se aceptaba ahora va a revisión | ✅ |
| A7 | Corrección manual | Historial → "Corregir" | Queda registrada (`corregido = 1`) y la foto va al dataset | ✅ |
| A8 | Estadísticas | Pestaña Estadísticas | Precisión total y por clase, matriz de confusión y tiempo promedio | ✅ |
| A9 | Voz que escucha | Botón «Hablar» → decir "plátano" | Burbuja "Oí… → Orgánica (bote verde)" | ✅ |
| A10 | Voz que habla | Configuración → "Probar la voz" | Laura dice "Es inorgánica… va en el bote azul" | ✅ |
| A11 | Conflicto voz-cámara | Decir "botella" con algo orgánico frente a la cámara | Revisión con `conflicto_voz` | ✅ en simulación |
| A12 | Juego con fotos | Juego → "Con fotos" → Empezar | Fotos reales, acierto/error, resultado por categoría | ✅ |
| A13 | Simulación separada | Correr con `SIMULACION=1` | Chip **SIMULADO**; datos en `clasificador_sim.db` | ✅ |
| A14 | Sin internet | Desconectar el wifi y repetir A4 y A9 | Todo sigue funcionando | ✅ (todo es local) |
| A15 | Falla segura | Desconectar el USB del Arduino con el backend corriendo | Estado ERROR, aviso en el panel; se recupera al reconectar | 🟡 probado al arrancar sin Arduino |

### B. Hardware (requiere la máquina armada)
| # | Punto | Cómo | Qué debe verse | Estado |
|---|---|---|---|---|
| B1 | Comandos del firmware | Monitor Serial 115 200, fin de línea `\n`: `PING`, `POS:0`, `DROP` | `PONG`, `POS_OK:0`, `DROP_OK` | ✅ 20-nov: READY, PONG, HOME y POS:0/1/2; servo visto moviéndose (sin carga, con USB) |
| B2 | Control desde la página | Configuración → Control manual: POS a cada bote y HOME | El Arduino contesta `POS_OK:n` / `HOME_OK` bajo los botones | ✅ 20-nov (POS:1 y HOME) |
| B3 | ~~LCD y teclado~~ | — | **Ya no se usan** (cambio de diseño del 20-nov): su función está en la página y la voz | — |
| B4 | Sensor IR | Poner un objeto | Llega `OBJ` y arranca el ciclo | ⏳ |
| B5 | Servo con fuente externa | `POS:0/1/2` | El disco gira al bote correcto sin temblar | ⏳ |
| B6 | Calibración de ángulos | `python tools\calibrar_angulos.py` | Cae al centro de la boca del bote | ⏳ |
| B7 | **3 de 3 ciclos reales** | Orgánico, inorgánico, peligroso + 1 dudoso | Cada uno en su bote; el dudoso se queda | ⏳ **criterio del jurado** |
| B8 | Mediciones eléctricas | Multímetro: 5 V de la lógica, voltaje del servo, consumo | Valores anotados en `docs/mediciones.md` | ⏳ |
| B9 | Falla diagnosticable | Provocar una (por ejemplo, desconectar el servo) | Se ve en `eventos` / `tiempos_etapas` en qué etapa falló | ⏳ |
| B10 | Bote lleno | Capacidad de prueba = 2 piezas | Aviso, bloqueo y vaciado con "Marcar como vaciado" en Botes | 🟡 |

### C. Entregables
| Entregable | Dónde | Estado |
|---|---|---|
| Código comentado (firmware, backend, IA, panel) | repo | ✅ |
| Contrato de la API | `docs/api_contrato.md` (v1.5) | ✅ |
| Bitácora | `docs/bitacora.md` | ✅ (al día) |
| Recursos externos (qué hizo la IA y qué el equipo) | `docs/recursos_externos.md` | ✅ |
| Diagrama eléctrico | `docs/diagrama_electrico.md` | revisar |
| CAD editable con tolerancias | `cad/` | equipo de CAD |
| Memoria técnica | `docs/memoria_tecnica.md` | ⏳ secciones de Fase 10 |
| Guion de defensa (7 + 7 + 6 min) | `docs/notas_defensa.md` | ⏳ falta el guion completo |

---

## 8. Riesgos y límites (dilo antes de que te lo pregunten)
- La IA se entrenó con fotos de internet. **Con la cámara real puede bajar la precisión**: por eso hay umbrales, detector de desconocidos y reentrenamiento con fotos propias.
- "Inorgánica" junta reciclables y no reciclables, por el tiempo del hackatón. Subdividirla queda como ampliación.
- El nivel de los botes es **ESTIMADO** por conteo: no hay sensor de nivel.
- Falta decidir la trampilla: A (compuerta) o B (depósito manual).
- El peligroso es **simulado** (pilas descargadas, envases vacíos).
- **No hay sensor de caída:** el sistema sabe que la trampilla se abrió y se cerró, no que el residuo cayó. Por eso el conteo de los botes es una estimación.

## 9. Preguntas probables del jurado
| Pregunta | Respuesta corta |
|---|---|
| ¿Qué pasa si la IA se equivoca? | Si duda, no suelta. Si se equivoca segura, el operador corrige en el panel, eso queda registrado y sirve para reentrenar. |
| ¿Por qué no entrenaron su propia red? | Con cientos de fotos se sobreajusta. El transfer learning da 98 % en validación y entrena en segundos. |
| ¿Cómo saben que el 98 % es real? | La validación separa por objeto y el modelo nunca vio esas fotos. Pero es con el dataset, no con la bandeja: lo decimos. |
| ¿Funciona sin internet? | Sí: la IA, la voz y la base de datos corren en la laptop. |
| ¿Quién decide, el Arduino o la laptop? | La laptop (Python). El Arduino solo ejecuta y reporta. |
| ¿Por qué no tiene pantalla ni teclado? | Los quitamos: la página ya hace todo (menú, ayuda, resultado, bote lleno) y también se maneja por voz. Menos cables y menos fallas, y se ve desde el celular. |
| ¿Qué hace si se desconecta algo? | Falla segura: HOME, trampilla cerrada, LED rojo y aviso. |
| Modifiquen una función en vivo | Cambiar `UMBRAL_GENERAL` desde el panel o editar `aplicar_reglas()` en `backend/app/model.py`. |
