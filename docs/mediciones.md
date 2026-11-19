# Mediciones reales — Fase 0

> **Regla:** aquí solo van valores **medidos** por el equipo (vernier, báscula, multímetro).
> Lo que falte se queda como `[COMPLETAR]`. Los números de ejemplo del final están rotulados como **SUPUESTOS** y no deben copiarse al reporte.

## 1. Equipo y conexiones

| Dato | Valor | Cómo obtenerlo | Quién / hora |
|---|---|---|---|
| Laptop usada para la demo | [COMPLETAR] (MSI Katana RTX 4060 / ASUS TUF RTX 4050) | — | |
| Puerto COM del Arduino UNO | [COMPLETAR] | `python tools/verificar_hardware.py` | |
| Índice de la cámara cenital | [COMPLETAR] | Igual; revisar `captures/prueba_camara_<i>.jpg` | |
| Modelo de la cámara (webcam / celular) | [COMPLETAR] | — | |
| Dirección I2C de la LCD | [COMPLETAR] (típica 0x27 o 0x3F) | Escáner I2C (Fase 2) | |
| Servo elegido para el disco | [COMPLETAR] SG90 / MG996R | Sección 4 de este documento | |
| Servo de la trampilla | SG90 (especificación) | — | |
| Iluminación: tipo y voltaje | [COMPLETAR] (tira 5 V / 12 V, anillo USB…) | Etiqueta o multímetro | |
| Corriente máxima de la fuente regulada | [COMPLETAR] A | Placa de la fuente / manual | |

## 2. Botes y disco

Medir con el vernier en **mm** y la báscula en **kg**. Medir el **diámetro mayor** del bote (normalmente la boca o la tapa).

| Dato | Verde (Orgánica) | Azul (Inorgánica) | Gris (Peligroso) |
|---|---|---|---|
| Planta: largo × ancho [mm] | **120 × 80** | **120 × 80** | **120 × 80** |
| Altura (con tapa) `H_bote` [mm] | [COMPLETAR] | [COMPLETAR] | [COMPLETAR] |
| Forma de la boca y medida libre [mm] | [COMPLETAR] | [COMPLETAR] | [COMPLETAR] |

> Medida reportada por el equipo el 2026-11-19: "12 cm de largo y 8 de ancho" (los tres botes iguales). Se interpreta como la **planta rectangular** 120 × 80 mm. Un bote redondo de Ø80 × 120 mm tendría solo ~0.6 L, no 1.5 L. Si la interpretación es incorrecta, corríjanla aquí y en `cad/parametros.md`.
> Falta medir: la **altura** (de ella depende la altura de la torre) y la **boca** (de ella depende el tamaño máximo del residuo).
| Diámetro de la boca / abertura de la tapa [mm] | [COMPLETAR] | [COMPLETAR] | [COMPLETAR] |
| Masa vacío [kg] | [COMPLETAR] | [COMPLETAR] | [COMPLETAR] |
| Masa lleno con residuos representativos [kg] | [COMPLETAR] | [COMPLETAR] | [COMPLETAR] |
| Capacidad estimada [piezas] (sección 13.2) | [COMPLETAR] | [COMPLETAR] | [COMPLETAR] |

| Dato del carrusel | Valor |
|---|---|
| Diámetro real del disco [mm] | [COMPLETAR] (especificación: Ø190; probablemente insuficiente, ver sección 3) |
| Espesor del disco [mm] | [COMPLETAR] (3 mm MDF) |
| Masa del disco [kg] | [COMPLETAR] |
| Lado de la base [mm] | [COMPLETAR] (200 × 200; debe ser ≥ diámetro del disco) |
| Radio de colocación de los botes `r_bote` [mm] | [COMPLETAR] (calcular con la sección 3) |
| Radio del círculo de las canicas `r_canicas` [mm] | [COMPLETAR] |
| Diámetro de las canicas [mm] | [COMPLETAR] |
| Masa y radio del contrapeso [kg, mm] | [COMPLETAR] |
| Rango real de giro del servo del disco [°] | [COMPLETAR] (medir: muchos llegan solo a ~160–170°) |

## 3. ¿Caben los botes? (geometría)

El servo gira como máximo ~180°, así que **los 3 botes tienen que caber en medio disco**. La separación angular entre botes vecinos `Δφ` queda en ~80–85° como máximo (por ejemplo, botes a 10°, 90° y 170°).

Dos botes vecinos, con sus centros a radio `r_bote` y separados `Δφ`, están a esta distancia:

```
cuerda = 2 · r_bote · sen(Δφ / 2)        debe ser ≥ d_bote + holgura (≈ 10 mm)
```

y el bote no debe salirse del disco:

```
r_bote + d_bote / 2 ≤ R_disco
```

Despejando, se obtienen el radio mínimo de colocación y el disco mínimo:

```
r_bote_min = (d_bote + holgura) / (2 · sen(Δφ / 2))
Ø_disco_min = 2 · (r_bote_min + d_bote / 2)
```

Referencia rápida (Δφ = 80°, holgura = 10 mm; es geometría, no una medición):

| `d_bote` [mm] | `r_bote_min` [mm] | Ø disco mínimo [mm] |
|---|---|---|
| 80 | 70 | 220 |
| 100 | 86 | 271 |
| 110 | 93 | 297 |
| 120 | 101 | 322 |

### Botes rectangulares (caso real: 120 × 80 mm)

Con el bote centrado a `r_bote`, alineado con el radio, y semilados `a` (radial) y `b` (tangencial), las esquinas interiores de botes vecinos son lo primero que choca:

```
r_bote_min = a + (b · cos(Δφ/2) + holgura/2) / sen(Δφ/2)
R_disco ≥ √((r_bote + a)² + b²)          (esquina exterior)
```

Resultado con 120 × 80 mm, Δφ = 80° y holgura de 10 mm (es geometría, no una medición):

| Orientación | `r_bote` mínimo | Ø disco mínimo |
|---|---|---|
| **Lado largo (120) tangencial** — recomendada | 119.3 mm | **Ø340 mm** |
| Lado largo hacia el centro | 115.4 mm | Ø360 mm |

**Decisión propuesta:** `r_bote = 120 mm`, lado largo tangencial y disco de **Ø350 mm**. La esquina exterior queda a 170.9 mm y deja ~4 mm de borde. El cálculo se reproduce con:

```powershell
python tools/calcular_par.py --largo-bote 120 --ancho-bote 80 --r-bote 120 --r-disco 175 --m-disco <kg> --m-bote-lleno <kg> --r-canicas <mm>
```

**Conclusión preliminar (botes redondos de referencia):** con botes de 1.5 L (normalmente Ø110–130 mm), el disco de **Ø190 mm no alcanza**. Las opciones son:
- un disco de Ø300–330 mm, con una base de MDF del mismo tamaño o mayor;
- botes más pequeños (Ø ≤ 80 mm caben en Ø220).

Hay que decidirlo con las medidas reales.

**Punto de caída:** la torre debe dejar la trampilla justo sobre el círculo de radio `r_bote`. La posición angular de la torre es `D`, y el servo va a `θᵢ = D − φᵢ`. Con botes a 10°, 90° y 170° y `D = 180°`, resultan θ = 170°, 90° y 10°. Todos quedan dentro del rango, con 10° de margen en cada extremo. Así se evita el problema del bote a 180° de la especificación, que exigiría `D` entre 180° y 190°.

## 4. Par requerido del servo del carrusel

El disco gira en un plano horizontal. La gravedad no produce par sobre el eje; solo hay que vencer la **fricción de rodadura** y la **inercia**.

**Masa total** (usar los botes **llenos**, sección 13.2.4):
```
m_total = m_disco + Σ m_bote_lleno + m_contrapeso
```

**(1) Fricción de rodadura** de las canicas, que actúan a `r_canicas` del eje (μ ≈ 0.05 es conservador para canicas sobre MDF impreso o lijado):
```
T_fricción = μ · m_total · g · r_canicas
```

**(2) Inercia.** Se suman el disco macizo, cada bote (cilindro desplazado, teorema de Steiner) y el contrapeso puntual:
```
I = ½·m_disco·R² + Σ m_bote·( (d_bote/2)²/2 + r_bote² ) + m_contrapeso·r_contrapeso²
ω = 1° / 15 ms ≈ 66.7 °/s ≈ 1.16 rad/s
α = ω / t_acel          (t_acel ≈ 0.1 s, supuesto conservador)
T_inercia = I · α
```

**(3) Par requerido** con factor de seguridad 2:
```
T_req = 2 · (T_fricción + T_inercia)          [N·m]
T_req [kg·cm] = T_req [N·m] / 0.0981
```

**(4) Comparación** (par nominal de la hoja de datos):

| Servo | Par nominal | Margen = par / T_req | ¿Sirve? (margen ≥ 1) |
|---|---|---|---|
| SG90 @ 4.8 V | 1.8 kg·cm | [COMPLETAR] | [COMPLETAR] |
| MG996R @ 4.8 V | 9.4 kg·cm | [COMPLETAR] | [COMPLETAR] |
| MG996R @ 6.0 V | 11.0 kg·cm | [COMPLETAR] | [COMPLETAR] |

### Cómo calcularlo con los valores medidos

```powershell
cd backend; python tools/calcular_par.py --d-bote <mm> --r-bote <mm> --r-disco <mm> --m-disco <kg> --m-bote-lleno <kg> --m-contrapeso <kg> --r-contrapeso <mm> --r-canicas <mm> --delta-phi 80
```

Usen la masa del bote **más pesado** lleno; el script la multiplica por 3.

### Ejemplo con valores SUPUESTOS (NO medidos, solo para entender el cálculo)

Valores supuestos: `python tools/calcular_par.py --ejemplo`, con bote Ø110 mm a r = 120 mm, disco R = 150 mm de 0.12 kg, botes llenos de 0.45 kg, contrapeso de 0.20 kg a 100 mm, canicas a 70 mm y μ = 0.05.

| Concepto | Resultado (SUPUESTO) |
|---|---|
| Masa total | 1.67 kg |
| T_fricción | 0.057 N·m |
| I | 0.0248 kg·m² (α = 11.6 rad/s²) |
| T_inercia | 0.289 N·m |
| T_req (×2) | 0.69 N·m ≈ **7.1 kg·cm** |
| SG90 | margen ×0.3 → **insuficiente** |
| MG996R (6 V) | margen ×1.6 → suficiente |

**Segundo ejemplo SUPUESTO con la geometría real (120 × 80 mm, r = 120 mm, disco Ø350 de 0.25 kg, canicas a 90 mm en copas con μ = 0.10):** el par requerido sube a **≈ 9.8 kg·cm**. El MG996R a 4.8 V queda justo (×1.0) y a 6 V tiene ×1.1. **Recomendación:** alimentar el MG996R a 6 V y hacer más lenta la rampa del disco (por ejemplo 1° cada 25 ms). Con un `t_acel` de 0.2 s, el par de inercia se reduce a la mitad. Hay que confirmarlo con las masas reales.

En el primer ejemplo, el disco de R = 150 mm tampoco basta: el bote sobresale, porque se necesita Ø297.
Lo que domina es la **inercia de los botes lejos del eje**, no la fricción. Por eso conviene un giro suave (rampa) y, si se puede, acercar los botes al centro.

> **Cómo defenderlo ante el jurado:** "Calculamos el par con los botes llenos, separando la fricción de rodadura de las canicas y la inercia del carrusel, con factor de seguridad 2. El SG90 del diagrama original no alcanza y por eso usamos el MG996R. El soporte tiene una cavidad paramétrica que acepta cualquiera de los dos."

## 5. Alimentación de los servos

| Dato | Valor | Nota |
|---|---|---|
| Voltaje de servos elegido | [COMPLETAR] (5.0–6.0 V) | Fuente regulada, **no** el 5 V del Arduino |
| Corriente pico esperada | MG996R ≈ 2.5 A con el eje bloqueado (hoja de datos típica); SG90 ≈ 0.65 A | Solo un servo se mueve a la vez |
| Corriente máxima de la fuente | [COMPLETAR] A | Debe ser ≥ 3 A para tener margen |
| Verificación | [COMPLETAR] | Medir el voltaje en los bornes del servo **mientras se mueve con carga**: si baja de ~4.8 V, la fuente no alcanza |
