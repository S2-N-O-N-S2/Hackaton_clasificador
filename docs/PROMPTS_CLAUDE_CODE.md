# Prompts para Claude Code — Cyber Insanos · Reto 1

## 0. Preparación (5 minutos, una sola vez)

1. Crea la carpeta del proyecto, por ejemplo `cyber-insanos-clasificador`, e inicia git:
   ```powershell
   mkdir cyber-insanos-clasificador; cd cyber-insanos-clasificador; git init
   mkdir docs
   ```
2. Copia los archivos así:
   - `CLAUDE.md` → en la **raíz** del proyecto (Claude Code lo lee automáticamente en cada sesión).
   - `ESPECIFICACION.md` → en `docs/ESPECIFICACION.md`.
3. Abre Claude Code en esa carpeta y pega el **Prompt inicial**.
4. Después pega los prompts de cada fase **en orden**. Usa un mensaje por fase; no los pegues todos juntos.
5. Si van a trabajar en paralelo en varias laptops, suban el repositorio a GitHub y que cada persona trabaje en su rama (`fase-2-firmware`, `fase-3-backend`, etc.). Ver la sección "Trabajo en paralelo" al final.

> Consejo: pidan siempre el plan antes del código (el prompt ya lo pide). Si el plan no les convence, corríjanlo antes de que escriba archivos.

---

## Prompt inicial (pegar primero)

```
Vas a ser el ingeniero líder de nuestro proyecto para el HACKATHÓN TESCo 2026 (Reto 1: clasificador inteligente de residuos).

1. Lee completo docs/ESPECIFICACION.md y CLAUDE.md.
2. Resúmeme en máximo 15 líneas lo que entendiste: objetivo, ciclo de operación, categorías, mecánica del carrusel, stack, innovaciones y fases.
3. Lista las dudas o contradicciones que encuentres en la especificación y los datos que el equipo debe medir o decidir ([COMPLETAR]).
4. Crea la estructura de carpetas de la sección 19 con archivos README.md breves en cada carpeta, docs/bitacora.md (con plantilla de tabla: hora | fase | responsable | qué se hizo | problema | solución), docs/recursos_externos.md (con plantilla) y un .gitignore adecuado para Python, Node y modelos/capturas grandes.
5. No escribas todavía código funcional. Termina proponiendo el primer commit.
```

---

## Fase 0 — Entorno y verificaciones

```
Fase 0 (especificación: secciones 2, 5.3, 6 y 22).

Objetivo: dejar el entorno listo en esta laptop Windows y detectar faltantes antes de programar.

Haz lo siguiente:
1. Verifica qué está instalado: Python, pip, Node, npm, git y Arduino IDE (si puedes detectarlo). Ejecuta los comandos y muéstrame los resultados.
2. Crea backend/requirements.txt con el stack de CLAUDE.md (fastapi, uvicorn, opencv-python, numpy, tensorflow, scikit-learn, pyserial, vosk, pytest, y lo mínimo adicional que justifiques). Indica el tamaño aproximado de las descargas grandes y pregúntame antes de instalarlas.
3. Crea el entorno virtual en backend/ e instala las dependencias cuando te lo autorice.
4. Crea backend/tools/verificar_hardware.py que:
   - liste los puertos COM disponibles (pyserial),
   - pruebe los índices de cámara 0–3 con OpenCV y guarde una foto de prueba de cada una que funcione,
   - confirme que el modelo de Vosk existe en backend/models/vosk-model-small-es (si no, explica cómo descargarlo).
5. Crea docs/mediciones.md con una tabla [COMPLETAR] para: medidas de los botes (diámetro/base y altura), radio de colocación en el disco, diámetro real del disco, masa de cada bote vacío y lleno, servo elegido para el disco (SG90 o MG996R) y corriente máxima de la fuente.
6. Con las fórmulas de la sección 5.3, deja preparado en docs/mediciones.md el cálculo del par del servo del disco para que solo haya que llenar los valores medidos.

Listo cuando: dependencias instaladas, verificar_hardware.py corre y docs/mediciones.md existe. Cierra con bitácora y commit.
```

---

## Fase 1 — Especificación CAD para SolidWorks

```
Fase 1 (especificación: secciones 5 y 2; restricción de impresión < 3 h por pieza).

El equipo modela en SolidWorks; tú no puedes generar archivos .SLDPRT. Tu trabajo es dejar todo listo para modelar e imprimir sin dudas.

Usa los valores de docs/mediciones.md (si faltan, usa valores de ejemplo marcados [COMPLETAR]) y crea:
1. cad/piezas.md: tabla de todas las piezas (nombre, proceso: corte MDF / impresión 3D / comercial, material, dimensiones clave, tolerancias de ajuste, cantidad, tiempo estimado de impresión y prioridad de impresión).
2. Para cada pieza impresa: croquis descrito paso a paso para SolidWorks (planos, cotas, operaciones de extrusión/corte, chaflanes), con las cotas que dependen de las mediciones como parámetros con nombre.
3. cad/ensamble.md: secuencia de ensamble, relaciones de posición, cómo verificar interferencias y la calibración del punto de caída (θi = D − φi).
4. cad/laminado.md: parámetros sugeridos por impresora (Ender 3 S1 Pro, Ender 3 V2, Kingroon KP3S, Bambu Lab A1 mini) para PLA 1.75 mm, orientación de cada pieza y soportes.
5. Señala qué piezas deben mandarse a imprimir ANTES de las 12:00 y cuáles pueden sustituirse por cartón/MDF si las impresoras se saturan.

Listo cuando: el equipo puede modelar cada pieza sin preguntar medidas. Cierra con bitácora, notas de defensa (tolerancias justificadas) y commit.
```

---

## Fase 2 — Firmware del Arduino UNO

```
Fase 2 (especificación: secciones 8, 9 y 10).

Crea firmware/clasificador_uno/clasificador_uno.ino que implemente EXACTAMENTE el protocolo serial de la sección 9:
- Servos del disco (D9) y de la trampilla (D10) con movimiento suave no bloqueante (rampa ~1° cada 15 ms) y detach opcional tras moverse.
- FC-51 #1 (D2) con antirrebote → OBJ cuando hay objeto estable ≥ 300 ms. FC-51 #2 (D3) → DROP_OK o DROP_TIMEOUT (2 s) tras DROP.
- LCD 20×4 I2C con LCD:<l1>|<l2>|<l3>|<l4> y LCD_SCROLL:<texto> en la línea 4.
- LEDs (A0/A1/A2) con LED:<color>[:PARPADEO]; iluminación (A3 vía TIP120) con LIGHT:ON/OFF.
- Teclado 4×4 → solo envía KEY:<tecla> (sin lógica de menús).
- Ángulos calibrados en EEPROM con CAL:<id>:<ángulo>; POS:<id> y HOME.
- Validación de comandos (ERR:<código>), respuesta a todo, watchdog lógico (sin comandos por X s → HOME y trampilla cerrada).
- Todo con millis(), sin delay() largos. Constantes de pines agrupadas al inicio.

Además:
1. docs/diagrama_electrico.md: tabla de conexiones completa, alimentación separada de servos (5–6 V, GND común, capacitor 1000 µF) y el escáner I2C para encontrar la dirección de la LCD.
2. docs/prueba_firmware.md: lista de comandos para probar cada función desde el Monitor Serial y la respuesta esperada.
3. Las 3 mediciones con multímetro y la falla diagnosticable (sección 8.2) como checklist.

Listo cuando: cada comando responde según el protocolo en el Monitor Serial. Cierra con bitácora, notas de defensa y commit.
```

---

## Fase 3 — Backend con modo simulación, SQLite y API

```
Fase 3 (especificación: secciones 4, 9, 10, 16, 17 y 20).

Construye el backend en backend/app/:
1. config.py: toda la configuración (puerto COM, índice de cámara, umbrales 0.60 / 0.35 / 0.80, modo por defecto, tiempos, rutas). Lee de variables de entorno y de la tabla config.
2. db.py: esquema COMPLETO de la sección 16 (incluye tablas de juego, botes, vaciados y modelos), índices y datos iniciales (3 botes con capacidad [COMPLETAR]).
3. serial_link.py: hilo lector + cola de mensajes, envío con espera de respuesta y timeout; implementación simulada cuando SIMULACION=1.
4. camera.py: captura de 3 fotogramas y guardado; implementación simulada que lee imágenes de backend/sim_images/.
5. model.py: interfaz predict(imagenes) -> probabilidades; por ahora un modelo simulado (aleatorio reproducible) marcado como simulado.
6. orchestrator.py: máquina de estados de la sección 10 con TODOS los estados (MENÚ, ESPERA_OBJETO, CAPTURA, CLASIFICACIÓN, ESPERA_ADIVINANZA, RETROALIMENTACIÓN, VERIFICAR_BOTE, BOTE_LLENO, REVISIÓN, POSICIONAR, SOLTAR, REGISTRAR, ACTUALIZAR_NIVEL, HOME, PENDIENTE). En esta fase, los estados del juego y de botes pueden pasar de largo, pero deben existir. Registra cada transición en eventos.
7. lcd_ui.py: generación de pantallas de la LCD (20 caracteres, sin acentos).
8. routes.py + main.py: endpoints de la sección 17 (los del juego y botes pueden devolver datos vacíos por ahora) y WebSocket /ws/eventos.
9. Fallas seguras (CLAUDE.md, regla 4).
10. tests/: pruebas de reglas de decisión (límites exactos 0.60, 0.35), parser del protocolo y recorte de textos LCD.

Listo cuando: con SIMULACION=1 se ejecuta un ciclo completo (OBJ simulado → clasificación → POS → DROP → registro en SQLite → evento por WebSocket) y pytest pasa. Muéstrame cómo verlo con curl o el navegador. Cierra con bitácora, notas de defensa y commit.
```

---

## Fase 4 — Dataset, entrenamiento y evaluación

```
Fase 4 (especificación: sección 14).

1. training/capturar_dataset.py: vista en vivo de la cámara; teclas para guardar en organica/inorganica/peligroso; pide y guarda el objeto_id de cada foto (CSV de metadatos); muestra el conteo por clase.
2. training/train.py: MobileNetV2 (ImageNet, sin capa superior, pooling promedio) como extractor congelado → embeddings en caché (.npy) → LogisticRegression. Separación entrenamiento/validación POR OBJETO (no por foto). Guarda models/v<N>/ con modelo, labels.json y métricas, y registra la versión en la tabla modelos. Deja la alternativa de cabeza densa en Keras como opción con un parámetro.
3. training/evaluate.py: precisión total y por clase, matriz de confusión (PNG y tabla) y carpeta con los casos fallidos.
4. Reemplaza el modelo simulado de model.py por el real (promedio de 3 fotogramas), conservando el simulado para SIMULACION=1.
5. Reentrenamiento en segundo plano llamado desde /api/modelo/reentrenar: solo activa la nueva versión si la precisión de validación no empeora.
6. Explica en docs/memoria_tecnica.md (sección IA) por qué transfer learning, por qué separar por objeto y cómo se interpreta la confianza.

Listo cuando: el equipo puede capturar fotos, entrenar en minutos y ver la matriz de confusión. Cierra con bitácora, notas de defensa y commit.
```

---

## Fase 5 — Integración real

```
Fase 5 (especificación: secciones 10 y 20).

Conecta todo con hardware real (SIMULACION=0): Arduino por COM, cámara real y modelo entrenado.
1. Crea backend/tools/calibrar_angulos.py: mueve el disco con las flechas/teclas, guarda el ángulo de cada bote con CAL y en la tabla config.
2. Ajusta tiempos y timeouts reales; mide y registra el tiempo de cada etapa del ciclo (tiempo de máquina) en clasificaciones.tiempo_ciclo_ms.
3. Prueba 3 ciclos reales seguidos (orgánico, inorgánico, peligroso simulado) y un caso dudoso; ayúdame a diagnosticar cualquier falla leyendo logs y eventos.
4. Crea docs/resultados/ciclos_reales.md para registrar los 3 ciclos (hora, residuo, predicción, confianza, resultado).

Listo cuando: 3 de 3 ciclos reales correctos registrados. Cierra con bitácora, notas de defensa y commit.
```

---

## Fase 6 — Panel React

```
Fase 6 (especificación: sección 18; API de la sección 17).

Crea el frontend con Vite + React en frontend/:
- Vistas: Inicio/Menú, En vivo, Historial (con Corregir), Estadísticas, Pruebas (cronómetro manual + corrida del sistema + tabla comparativa), Configuración. Deja creadas, aunque vacías, las vistas ¿Le ganas a la IA?, Humano vs. IA, Aprendizaje y Botes.
- Conexión por WebSocket con reconexión automática y polling de respaldo.
- Diseño legible a distancia, colores de los botes (verde, azul, gris) y amarillo para revisión; etiqueta SIMULADO visible cuando corresponda.
- Configuración de la URL del backend en un solo archivo.
- Sin bibliotecas de UI pesadas; si propones alguna (por ejemplo, para gráficas), justifícala y pídeme confirmación.

Listo cuando: el panel muestra en vivo un ciclo real o simulado y permite corregir una clasificación. Cierra con bitácora, notas de defensa y commit.
```

---

## Fase 7 — Aviso de bote lleno (estimado)

```
Fase 7 (especificación: sección 13). Solo si la fase 5 está estable.

1. bins.py: contador por bote (suma con DROP_OK y con DROP_TIMEOUT marcado "no confirmado"), nivel = piezas/capacidad, aviso ≥ 80 %, bloqueo al 100 %, vaciado (panel y teclado D → 1/2/3 → B), recarga desde SQLite al iniciar.
2. Integra VERIFICAR_BOTE y BOTE_LLENO en el orquestador: el residuo se queda en la bandeja, LED rojo fijo, pantalla de la LCD de la sección 13.3; al vaciar, el ciclo continúa automáticamente.
3. Vista Botes en el panel y barras de nivel en En vivo, siempre rotuladas ESTIMADO.
4. Procedimiento de calibración de capacidad en docs/mediciones.md.
5. Pruebas pytest del contador, aviso, bloqueo y vaciado.

Listo cuando: con una capacidad de prueba baja se demuestran aviso, bloqueo y vaciado. Cierra con bitácora, notas de defensa y commit.
```

---

## Fase 8 — Menú + modo "¿Le ganas a la IA?" + certeza + curva de aprendizaje

```
Fase 8 (especificación: secciones 11 y 12 completas). Solo si las fases 5 y 7 están estables.

1. Menú (sección 11): selección por teclado, panel y voz (la voz se conecta en la fase 9; deja el punto de integración); modo por defecto IA si se coloca un residuo sin elegir; teclado contextual de la sección 9.
2. game.py: flujo de la sección 12.2 completo:
   - resultado oculto hasta que el usuario responda; límite de 20 s;
   - niveles de certeza Verificada / Alta / Media / Baja con UMBRAL_TONO_FIRME = 0.80, tono, LED y tiempo en pantalla de la tabla;
   - confianza de la IA siempre visible; en Media, línea 4 alternando explicación y "*: si crees que no";
   - el residuo SIEMPRE va al bote de referencia;
   - reporte con * → REVISIÓN por operador → recalificación y recálculo de estadísticas.
3. data/explicaciones.json con las 6 parejas de confusión (texto corto ≤ 60 caracteres y largo), redacción firme y condicional, y un dato por categoría. Indica en docs/recursos_externos.md que el equipo debe validar los textos con la norma local de separación de residuos.
4. Marcador de sesión y estadísticas de la sección 12.4 (solo Verificada/Alta para lo que se reporta).
5. Curva de aprendizaje (sección 12.5): acierto por número de intento, primera vs. segunda mitad, tasa de corrección tras explicación, prueba controlada (alias, ronda 1 y 2 con orden aleatorio), tamaño de muestra y rótulo "muestra pequeña".
6. Vistas del panel: ¿Le ganas a la IA?, Humano vs. IA y Aprendizaje.
7. Pruebas pytest: niveles de certeza en los límites exactos, evaluación de adivinanzas (correcta, incorrecta, sin respuesta, IA dudosa, reporte, recalificación), selección de explicación y cálculos de aprendizaje.

Listo cuando: se demuestra un acierto y un error con explicación y confianza en LCD y panel, un caso de certeza media con tono prudente, y la vista Aprendizaje muestra datos. Cierra con bitácora, notas de defensa y commit.
```

---

## Fase 9 — Voz y reentrenamiento con correcciones

```
Fase 9 (especificación: secciones 14.3 y 15). Solo si la fase 8 está estable.

1. voice.py con Vosk: push-to-talk (tecla A), gramática restringida distinta por estado (menú, adivinanza, revisión, objeto libre), normalización (minúsculas, sin acentos, singular básico).
2. data/keywords.json con ~100 objetos comunes → categoría (y campo opcional "explicacion").
3. Casos de uso de la sección 15: resolver dudoso, pregunta directa con fusión voz + visión, menú por voz y adivinanza por voz.
4. Etiquetas de usuarios a dataset/_por_verificar/; aprobación/rechazo del operador en Configuración; reentrenamiento desde el panel.
5. Pruebas pytest de la normalización y del mapeo de palabras clave.

Listo cuando: un caso dudoso se resuelve por voz, aparece en _por_verificar y, tras aprobarlo, se reentrena el modelo. Cierra con bitácora, notas de defensa y commit.
```

---

## Fase 10 — Prueba oficial, documentación y defensa

```
Fase 10 (especificación: secciones 3, 20 y 21).

1. Guíame en la prueba oficial: 20 residuos × 2 corridas (manual cronometrada y sistema en modo IA). Verifica que el tiempo promedio use solo tiempo de máquina.
2. Genera docs/resultados/: tabla comparativa, matriz de confusión, % de acierto total y por categoría, tiempo promedio por residuo, residuos desviados por categoría, resultados de la prueba controlada de aprendizaje (con n y límites).
3. Completa docs/memoria_tecnica.md: problema, objetivos medibles, arquitectura, decisiones, resultados reales, límites, riesgos e impacto.
4. Revisa y completa docs/bitacora.md y docs/recursos_externos.md.
5. Crea docs/guion_defensa.md: 7 min de exposición (quién dice qué), 7 min de demostración (los 3 momentos obligatorios + momentos 4 y 5 si hay tiempo), 6 min de preguntas probables del jurado con respuestas técnicas, y un cambio de código en vivo preparado (por ejemplo, el umbral).
6. Lista de verificación final de entregables contra la rúbrica (sección 3).

No inventes ningún resultado: si falta un dato, márcalo como pendiente.
```

---

## Prompts de apoyo (usar cuando haga falta)

**Depurar un error**
```
Tengo este error/comportamiento: <pega el error o describe qué pasa>.
Antes de cambiar código: explica la causa más probable, cómo confirmarla (comandos o mediciones) y la corrección mínima. Después aplícala, corre las pruebas y registra el problema y la solución en docs/bitacora.md.
```

**Preparar a un integrante para la defensa**
```
Explícame el módulo <archivo o tema> como si yo tuviera que defenderlo ante el jurado: qué hace, por qué se diseñó así, qué alternativas descartamos, qué preguntas difíciles podrían hacerme y cómo responderlas. Termina con un cambio pequeño que yo pueda hacer en vivo para demostrar que entiendo el código.
```

**Revisión de seguridad antes de la demo**
```
Revisa todo el proyecto buscando riesgos para la demo: fallas sin manejar, estados de los que el sistema no sale, casos en los que podría soltar un residuo sin categoría válida o a un bote lleno, y datos simulados que no estén rotulados. Dame la lista ordenada por gravedad y corrige solo lo crítico.
```

**Actualizar la documentación**
```
Revisa los commits y cambios desde la última entrada de docs/bitacora.md y actualiza la bitácora y docs/recursos_externos.md. No inventes horas ni responsables: deja [COMPLETAR] donde no lo sepas.
```

---

## Trabajo en paralelo (equipo de 6, varias laptops)

La especificación ya define los "contratos" (protocolo serial en la sección 9 y API en la sección 17), así que después de la fase 0 pueden avanzar en paralelo, cada quien con su propia sesión de Claude Code y su rama:

| Persona | Rama | Fases | Depende de |
|---|---|---|---|
| Mecánica / CAD | `fase-1-cad` | 1 | Fase 0 (mediciones) |
| Electrónica / firmware | `fase-2-firmware` | 2 | — |
| Backend | `fase-3-backend` | 3 → 5 | — (usa modo simulación) |
| IA / dataset | `fase-4-ia` | 4 | Cámara y caja de captura armadas |
| Frontend | `fase-6-panel` | 6 | Fase 3 (puede empezar con la API en modo simulación) |
| Pruebas / documentación | `main` | bitácora, recursos, pruebas, guion | Todas |

Reglas para el paralelo:
- Nadie cambia el protocolo serial ni la API sin avisar al equipo y actualizar `docs/ESPECIFICACION.md`.
- Integren en `main` al menos cada 2 horas.
- Las fases 7, 8 y 9 se hacen sobre `main` cuando la fase 5 ya funciona.
