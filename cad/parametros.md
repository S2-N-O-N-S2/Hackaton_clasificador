# Parámetros compartidos del CAD — contrato entre Persona A (carrusel) y Persona B (torre)

> **Este archivo es la única fuente de verdad de las cotas que comparten las dos mitades del diseño.**
> - Nadie lo cambia solo. Si alguien necesita cambiar un valor, lo anota en "Cambios propuestos" al final, avisa a la otra persona y los dos lo actualizan juntos.
> - En SolidWorks, carguen estos nombres como **Variables globales** (Herramientas → Ecuaciones) para cambiarlos en un solo lugar.
> - `[COMPLETAR]` = falta medirlo. `[DECISIÓN]` = propuesta que el equipo debe aceptar o cambiar.
> - Todas las medidas van en mm, salvo que se indique otra unidad.

## 1. Sistema de coordenadas (ambos lo usan igual)

- **Origen:** el eje del servo del carrusel, sobre la **cara superior de la base** (z = 0).
- **+X:** hacia donde apunta la marca 0° del disco cuando el servo está en 0°.
- **+Z:** hacia arriba.
- **Torre y punto de caída:** en la dirección **−X** (ángulo mundial `D = 180°`).
- Un bote en la posición `φ` del disco queda bajo el punto de caída cuando el servo está en `θ = D − φ = 180° − φ`.

## 2. Botes (medidos)

| Variable | Valor | Estado |
|---|---|---|
| `BOTE_LARGO` | 120 | Medido 2026-11-19 (interpretado como planta rectangular; ver `docs/mediciones.md`) |
| `BOTE_ANCHO` | 80 | Medido 2026-11-19 |
| `BOTE_ALTO` | [COMPLETAR] | **Urgente:** de él depende la altura de la torre |
| `BOCA_LARGO` × `BOCA_ANCHO` | [COMPLETAR] (supuesto inicial 110 × 70) | Abertura libre de la boca, sin tapa |
| Tapas | [DECISIÓN] retirarlas durante la operación | Especificación 5.3 |

## 3. Carrusel (dueña: Persona A)

| Variable | Valor | Nota |
|---|---|---|
| `PHI_ORG`, `PHI_INO`, `PHI_PEL` | 10°, 90°, 170° | [DECISIÓN] Sustituye 10/90/180 de la especificación; deja 10° de margen en los dos extremos del servo |
| `R_BOTE` | 120 | Radio al centro de cada bote, con el **lado largo tangencial** (geometría en `docs/mediciones.md`) |
| `DISCO_D` | 350 | [DECISIÓN] El disco Ø190 de la especificación no alcanza (mínimo Ø340) |
| `DISCO_ESP` | 3 | MDF |
| `BASE_X` × `BASE_Y` | 450 × 400 | [DECISIÓN] El eje queda a 200 del borde +X y a 250 del borde −X, que deja espacio para el pie de la torre. Confirmar que hay MDF de ese tamaño [COMPLETAR] |
| `Z_DISCO_INF` | [COMPLETAR por A] (~18) | Altura de la cara inferior del disco. Depende de las canicas y de cómo se monte el servo. **A la publica lo antes posible** |
| `Z_DISCO_SUP` | `Z_DISCO_INF + DISCO_ESP` | |
| `Z_BOCA` | `Z_DISCO_SUP + BOTE_ALTO` | Altura del borde superior de los botes |
| `R_BARRIDO` | 175 | Radio máximo que barre cualquier cosa sobre el disco (borde del disco) |
| `CANICA_D` | [COMPLETAR] (típica 16) | Medir con el vernier |
| `R_CANICAS` | 90 | [DECISIÓN] 4 copas a 45°, 135°, 225° y 315° |
| Servo del disco | MG996R a 6 V | Ver `docs/mediciones.md`, sección 4. La cavidad debe aceptar también el SG90 |

**Recomendación de montaje (A decide):** empotrar el servo en un hueco rectangular de la base, con las orejas apoyadas en la cara superior y el cuerpo colgando debajo. Así el eje sobresale poco y el disco queda bajo (~18 mm), a la altura de las copas. La base necesita **patas ≥ 45 mm** para que el cuerpo del servo no toque la mesa.

**Contrapeso:** con los botes en 10°, 90° y 170°, el centro de masa de los botes queda hacia +90°, a `0.449 · R_BOTE ≈ 54 mm` del eje. El contrapeso va en **φ = 270°**, con:
`m_contrapeso · r_contrapeso = 3 · m_bote · 0.449 · R_BOTE`.
Conviene que sea un **cajón rellenable** (rondanas o arena) para ajustarlo con los botes medio llenos.

## 4. Interfaz carrusel ↔ torre (lo que B necesita de A)

| Variable | Valor | Regla |
|---|---|---|
| Punto de caída (centro del embudo) | (x, y) = (−`R_BOTE`, 0) = (−120, 0) | Fijo |
| Zona prohibida para la torre | Cilindro de radio `R_BARRIDO + 10 = 185` alrededor del eje, desde z = 0 hasta `Z_BOCA + 5` | Nada de la torre puede entrar ahí, salvo el embudo, que queda **por encima** de `Z_BOCA + 5` |
| Pie de la torre | Rectángulo x ∈ [−250, −190], y ∈ [−60, 60] sobre la base | Se fija con tornillos M3 o para madera [COMPLETAR qué tornillería hay] |
| `Z_SALIDA_EMBUDO` | `Z_BOCA + 8` | La boca inferior del embudo pasa 8 mm por encima del borde de los botes al girar |
| Salida del embudo | ≤ `BOCA_LARGO − 20` (tangencial, eje Y) × `BOCA_ANCHO − 20` (radial, eje X) | Supuesto inicial 90 × 50 |
| FC-51 #2 (caída) | En la garganta del embudo, mirando en horizontal | Debe ver pasar el residuo |

## 5. Torre de captura (dueña: Persona B)

| Variable | Valor | Nota |
|---|---|---|
| `BANDEJA_INT` | 100 × 100 | [DECISIÓN] Interior de la bandeja: el residuo debe caber en el bote |
| `BANDEJA_PARED` | 40 de alto | Fondo liso de color uniforme (sugerencia: PLA gris mate o una lámina blanca encima) [DECISIÓN] |
| Trampilla | Una hoja de 100 × 100 con bisagra a lo largo de un lado. La mueve el SG90 (D10) | Abre hacia abajo ≥ 70° |
| `H_CAM` | 180 (ajustable ±40 con una ranura) | Del fondo de la bandeja al lente. A ~60° de campo, ve ~200 mm de ancho |
| Cámara | [COMPLETAR modelo de webcam / celular] | El soporte depende de ella |
| Iluminación | [COMPLETAR tira LED o anillo, y su voltaje] | Uniforme, sin sombras duras; paredes o cubierta contra la luz ambiente |
| FC-51 #1 (presencia) | Mirando la bandeja desde arriba o en diagonal | Alcance de 2–30 cm ajustable con su potenciómetro |
| Columna | [DECISIÓN] MDF o madera, con soportes impresos | Mide ~400 mm o más: **no cabe en ninguna impresora en < 3 h** |

## 6. Reglas de fabricación comunes

| Concepto | Valor |
|---|---|
| Material | PLA 1.75 mm (gris) |
| Boquilla / capa / relleno | 0.4 / 0.2 / 15–20 % (piezas que cargan peso: 30 %, 4 perímetros) |
| Holgura en encajes deslizantes | **0.25 por lado** (rango 0.2–0.3 de la especificación) |
| Agujero para M3 pasante | Ø3.4 |
| Agujero para M3 roscado en plástico / autorroscante | Ø2.8 |
| Cavidad SG90 (cuerpo) | 22.8 × 12.4 + holgura → **23.3 × 12.9** (verificar con el vernier) |
| Cavidad MG996R (cuerpo) | 40.7 × 19.7 + holgura → **41.2 × 20.2** (verificar con el vernier) |
| Espesor mínimo de pared | 2.0 (5 perímetros de 0.4) |
| Tiempo máximo por pieza | **< 3 h** (si se pasa, dividir la pieza o pasarla a MDF o cartón) |
| Volúmenes de impresión | Ender 3 S1 Pro 220×220×270 · Ender 3 V2 220×220×250 · KP3S 180×180×180 · A1 mini 180×180×180 |

## 7. Prioridad de impresión (hoy antes de las 12:00)

| Prioridad | Pieza | Dueña | Por qué primero |
|---|---|---|---|
| 1 | Soporte del servo de la trampilla + trampilla + bisagra | B | Mecanismo crítico del ciclo; hay que probarlo con el firmware |
| 1 | Soporte de cámara (provisional) | B | Sin cámara fija **no se puede capturar el dataset (Fase 4)** |
| 1 | Adaptador cruceta–disco | A | Necesario para probar el giro del disco |
| 2 | Bandeja | B | |
| 2 | Copas de canicas (×4) | A | Piezas pequeñas y rápidas |
| 2 | Soporte del servo del disco | A | Puede ser un hueco en el MDF con 2 calzas impresas |
| 3 | Embudo, soportes FC-51, soporte de iluminación | B | Sustituibles con cartón o cinta |
| 3 | Localizadores de botes, soporte del contrapeso | A | Sustituibles con tiras de MDF y silicón |

Reparto sugerido de impresoras: **A** usa la A1 mini y la KP3S (piezas pequeñas); **B** usa la Ender 3 S1 Pro y la V2 (bandeja y embudo, que son más grandes). [DECISIÓN]

## 8. Cambios propuestos (pendientes de acuerdo)

| Fecha / hora | Quién | Variable | Valor actual → propuesto | Motivo | ¿Aceptado? |
|---|---|---|---|---|---|
| | | | | | |
