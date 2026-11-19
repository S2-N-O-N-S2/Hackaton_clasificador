# Fase 1 dividida entre dos personas

La Fase 1 se divide en las **dos mitades físicas** del prototipo. Lo único que tocan en común son unas pocas cotas, y esas están fijadas en [`cad/parametros.md`](../cad/parametros.md). Así cada quien modela e imprime sin esperar a la otra persona.

| | **Persona A — Carrusel** | **Persona B — Torre de captura** |
|---|---|---|
| Piezas | Base y disco de MDF, soporte del servo del disco (cavidad paramétrica SG90/MG996R), adaptador cruceta–disco, copas de canicas ×4, localizadores de botes ×3, soporte del contrapeso | Columna (MDF + soportes impresos), bandeja, trampilla + bisagra, soporte del servo de la trampilla, embudo, soporte de cámara, soporte de iluminación y paredes, soportes FC-51 #1 y #2 |
| Archivos que crea | `cad/carrusel.md`, `cad/piezas.md` (tabla maestra), `cad/ensamble.md` | `cad/torre.md`, `cad/laminado.md` |
| Publica para la otra persona | `Z_DISCO_INF` (altura del disco), **lo antes posible** | Si necesita mover el pie de la torre o el embudo, lo propone en `parametros.md` §8 |
| Impresoras sugeridas | Bambu A1 mini, Kingroon KP3S | Ender 3 S1 Pro, Ender 3 V2 |

**Reglas para no pisarse:**
1. Cada quien **solo edita sus propios archivos**. `cad/parametros.md` se cambia solo de común acuerdo (sección 8 del archivo).
2. En `docs/bitacora.md` cada quien **agrega filas al final**, sin editar las de la otra persona.
3. Al terminar, A integra en `cad/piezas.md` las filas de la tabla de piezas de B (que vienen en `cad/torre.md`) y escribe `cad/ensamble.md`, que cubre el ensamble completo.
4. Si usan git, cada quien trabaja en su rama: `fase-1-carrusel` y `fase-1-torre`. Luego se unen en `main`.

---

## Qué archivos pasarle a la otra persona (Persona B)

**Opción recomendada:** pásale el repositorio completo (súbelo a GitHub y que lo clone, o cópialo por USB **sin** la carpeta `backend/.venv`, que pesa ~1.5 GB). Así Claude Code lee `CLAUDE.md` automáticamente.

**Mínimo indispensable**, si solo se pasan archivos. Deben conservar la estructura de carpetas:

```
CLAUDE.md                     ← en la raíz; Claude Code lo lee solo
docs/ESPECIFICACION.md
docs/mediciones.md
docs/fase1_division.md        ← este archivo
docs/bitacora.md
docs/recursos_externos.md
cad/parametros.md             ← el contrato de cotas
cad/README.md
```

Persona B **no necesita** el backend, el entorno de Python ni los modelos.

---

## Prompt para Persona A — Carrusel

```
Fase 1 — MITAD A: CARRUSEL (especificación: secciones 2, 5.1–5.4; restricción < 3 h por pieza).
Trabajamos la Fase 1 entre dos personas; lee docs/fase1_division.md. Yo soy la Persona A.
El equipo modela en SolidWorks; tú no generas .SLDPRT. Deja todo listo para modelar e imprimir sin dudas.

Lee CLAUDE.md, docs/ESPECIFICACION.md (secciones 2 y 5), docs/mediciones.md y cad/parametros.md.
cad/parametros.md es el CONTRATO con la Persona B (torre): usa exactamente sus variables y su sistema de
coordenadas. No lo modifiques; si algo debe cambiar, agrégalo en su sección 8 "Cambios propuestos" y avísame.

Mis piezas: base de MDF, disco de MDF, soporte del servo del disco (cavidad paramétrica para MG996R y SG90),
adaptador cruceta–disco (el disco NO debe colgar del servo: las canicas soportan el peso), copas de canicas ×4,
localizadores de botes ×3 (lado largo tangencial, R_BOTE), soporte o cajón del contrapeso en φ = 270°.

Crea:
1. cad/carrusel.md: para cada pieza, una ficha con proceso (corte MDF / impresión 3D / comercial), material,
   cantidad, cotas clave como parámetros con nombre (variables globales de SolidWorks), tolerancias justificadas,
   croquis paso a paso para SolidWorks (plano, cotas, extruir/cortar, chaflanes/redondeos), orientación de impresión,
   soportes sí/no, tiempo estimado (< 3 h) y prioridad. Si una pieza no cabe o supera 3 h, divídela o pásala a MDF.
2. Calcula y publica Z_DISCO_INF en cad/parametros.md (este dato SÍ lo escribo yo, es mío), justificando la cadena
   de cotas: canica, copa, orejas del servo, cruceta, adaptador.
3. cad/piezas.md: tabla maestra con TODAS las piezas del proyecto. Llena las mías y deja las filas de la torre
   marcadas "pendiente de cad/torre.md (Persona B)".
4. cad/ensamble.md: secuencia de ensamble del carrusel, relaciones de posición en SolidWorks, verificación de
   interferencias (incluida la zona prohibida de la torre, §4 de parametros.md), cómo nivelar las canicas y la
   calibración del punto de caída (θi = 180° − φi) con el disco montado. Deja una sección "Ensamble de la torre"
   para integrar lo de la Persona B.
5. Señala qué pieza mando a imprimir PRIMERO (antes de las 12:00) y cuáles se sustituyen por MDF o cartón.

Usa los valores medidos; lo que falte, márcalo [COMPLETAR] y dime qué medir con el vernier.
Listo cuando: puedo modelar cada pieza del carrusel sin preguntar medidas. Cierra con una fila en docs/bitacora.md
(al final, sin tocar las de otros), notas "Cómo defenderlo ante el jurado" (tolerancias, servo, canicas) y un mensaje
de commit propuesto "fase 1: carrusel ...". No hagas git add, commit ni push.
```

---

## Prompt para Persona B — Torre de captura

```
Fase 1 — MITAD B: TORRE DE CAPTURA (especificación: secciones 2, 5.2–5.4, 8.1 y 14.1; restricción < 3 h por pieza).
Trabajamos la Fase 1 entre dos personas; lee docs/fase1_division.md. Yo soy la Persona B.
El equipo modela en SolidWorks; tú no generas .SLDPRT. Deja todo listo para modelar e imprimir sin dudas.

Lee CLAUDE.md, docs/ESPECIFICACION.md (secciones 2, 5 y 14.1), docs/mediciones.md y cad/parametros.md.
cad/parametros.md es el CONTRATO con la Persona A (carrusel): usa exactamente sus variables y su sistema de
coordenadas, respeta la zona prohibida (§4) y el pie de la torre. No lo modifiques; si necesito cambiar algo, agrégalo
en su sección 8 "Cambios propuestos" y dime qué avisarle a la Persona A. Z_DISCO_INF lo publica la Persona A: mientras
no esté, usa el valor supuesto, déjalo como parámetro y márcalo [COMPLETAR].

Mis piezas: columna (MDF o madera con soportes impresos; no cabe impresa en < 3 h), brazo en voladizo, bandeja con
fondo liso de color uniforme, trampilla + bisagra, soporte del servo SG90 de la trampilla, embudo hacia la boca del bote
(salida por encima de Z_BOCA + 8), soporte cenital de la cámara a H_CAM ajustable, soporte de la iluminación blanca y
paredes contra la luz ambiente, soporte del FC-51 #1 (presencia en la bandeja) y del FC-51 #2 (caída, en la garganta del
embudo).

Crea:
1. cad/torre.md: para cada pieza, una ficha con proceso (corte MDF / impresión 3D / comercial), material, cantidad,
   cotas clave como parámetros con nombre (variables globales de SolidWorks), tolerancias justificadas, croquis paso a
   paso para SolidWorks (plano, cotas, extruir/cortar, chaflanes/redondeos), orientación de impresión, soportes sí/no,
   tiempo estimado (< 3 h) y prioridad. Si una pieza no cabe o supera 3 h, divídela o pásala a MDF o cartón.
   Incluye la cadena de alturas: Z_BOCA → embudo → trampilla → bandeja → cámara.
   Al final, una "Tabla de piezas de la torre" con las mismas columnas que cad/piezas.md, para que la Persona A la integre.
2. Justifica el ángulo de apertura de la trampilla, la palanca del SG90 (par de la trampilla con el residuo más pesado
   del set) y cómo se evita que el residuo se atore en el embudo.
3. Sección "Ensamble de la torre" (secuencia, cómo fijarla a la base, cómo alinear el embudo con el punto de caída
   (−120, 0) y cómo verificar que el disco gira sin rozar).
4. cad/laminado.md: parámetros por impresora (Ender 3 S1 Pro, Ender 3 V2, Kingroon KP3S, Bambu Lab A1 mini) para
   PLA 1.75 mm, y orientación y soportes de CADA pieza del proyecto. Las del carrusel tómalas de cad/carrusel.md si ya
   existe; si no, deja la fila pendiente.
5. Señala qué pieza mando a imprimir PRIMERO (antes de las 12:00; prioridad: trampilla + soporte de su servo y un
   soporte de cámara provisional para empezar el dataset) y cuáles se sustituyen por MDF o cartón.

Usa los valores medidos; lo que falte (altura y boca del bote, modelo de cámara, iluminación), márcalo [COMPLETAR] y
dime qué medir.
Listo cuando: puedo modelar cada pieza de la torre sin preguntar medidas. Cierra con una fila en docs/bitacora.md (al
final, sin tocar las de otros), notas "Cómo defenderlo ante el jurado" (tolerancias, fondo e iluminación constantes
para la IA) y un mensaje de commit propuesto "fase 1: torre ...". No hagas git add, commit ni push.
```

---

## Integración (cuando las dos mitades terminen)

1. A copia la "Tabla de piezas de la torre" de `cad/torre.md` a `cad/piezas.md`.
2. A completa la sección "Ensamble de la torre" de `cad/ensamble.md` con lo de `cad/torre.md`.
3. Los dos revisan juntos `cad/parametros.md` §8 y cierran los cambios pendientes.
4. Ensamble virtual en SolidWorks: el carrusel y la torre en un solo `.SLDASM`, con la **detección de interferencias** girando el disco a 10°, 90° y 170°.
