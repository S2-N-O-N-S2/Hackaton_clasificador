# Contrato de interfaces — Backend ↔ Panel ↔ Arduino

> **Versión 1.3 — 2026-11-19.** Es el acuerdo entre la Persona A (backend, `backend/`) y la Persona B (firmware `firmware/` y panel `frontend/`).
> Detalla las secciones 9 y 17 de `docs/ESPECIFICACION.md`. Si este contrato y la especificación se contradicen, manda la especificación: avisen y corrijan este archivo.
> **Nadie cambia este archivo sin avisar a la otra persona.** Cada cambio sube la versión y se anota en la sección 9 ("Historial").

---

## 1. Convenciones generales

| Tema | Regla |
|---|---|
| URL base | `http://<ip-de-la-laptop>:8000`. El panel la lee de un solo archivo de configuración (`frontend/src/config.js`) |
| Formato | JSON UTF-8. Nombres de campos en **español, `snake_case`, sin acentos** |
| Fechas | ISO 8601, hora local, sin zona: `"2026-11-19T10:32:05"` |
| Categorías | Siempre por **id numérico**: `0` Orgánica, `1` Inorgánica, `2` Peligroso. `null` = sin categoría |
| Probabilidades | Números de 0 a 1 con 3 decimales; en el panel se muestran como % |
| Fotos | Ruta relativa servida por el backend: `"/captures/20261119_103205.jpg"` |
| Datos simulados | Todo objeto que pueda venir de simulación trae `"simulado": true/false`. Si es `true`, el panel muestra la etiqueta **SIMULADO** |
| Niveles de bote | Siempre traen `"estimado": true`. El panel los rotula **ESTIMADO** |
| Errores | Formato de FastAPI: `{"detail": "mensaje en español"}`. Códigos: `400` dato inválido, `404` no existe, `409` acción no permitida en el estado actual, `422` validación, `501` todavía no implementado (indica la fase), `503` hardware no disponible |
| CORS | El backend permite cualquier origen (red local del evento) |

### 1.1 Catálogo de categorías (fijo)

| id | `clave` | `nombre` | `color` | `hex` (panel) |
|---|---|---|---|---|
| 0 | `organica` | Orgánica | verde | `#2E9E44` |
| 1 | `inorganica` | Inorgánica | azul | `#1E6FD9` |
| 2 | `peligroso` | Peligroso | gris | `#6B7280` |
| — | `revision` | Revisión | amarillo | `#F2B705` |

### 1.2 Enumeraciones

| Campo | Valores |
|---|---|
| `estado` (máquina) | `MENU`, `ESPERA_OBJETO`, `CAPTURA`, `CLASIFICACION`, `ESPERA_ADIVINANZA`, `RETROALIMENTACION`, `REVISION`, `VERIFICAR_BOTE`, `BOTE_LLENO`, `POSICIONAR`, `SOLTAR`, `REGISTRAR`, `ACTUALIZAR_NIVEL`, `HOME`, `PENDIENTE`, `OPERADOR`, `ERROR` |
| `modo` | `ia`, `adivina`, `null` (todavía no se elige) |
| `origen` (clasificación) | `camara`, `voz`, `manual`, `teclado`, `panel` |
| `motivo_dudoso` | `confianza_baja`, `riesgo_peligroso`, `conflicto_voz`, `sin_modelo` (no hay modelo cargado: el sistema no adivina), `null` |
| `estado` (clasificación) | `en_proceso`, `registrado`, `pendiente`, `error` |
| `nivel_certeza` | `verificada`, `alta`, `media`, `baja` |
| `fuente_referencia` | `ia`, `operador`, `etiqueta_real` |
| `medio` (adivinanza) | `teclado`, `voz`, `panel`, `sin_respuesta` |
| `estado` (bote) | `normal`, `casi_lleno`, `lleno` |
| `nivel` (alerta) | `info`, `aviso`, `error` |

`OPERADOR` (menú de operador con la tecla `D`) y `ERROR` (falla segura: trampilla cerrada y disco en HOME) **se agregan** a los estados de la sección 10.

---

## 2. Objetos comunes

### 2.1 `Clasificacion`
```json
{
  "id": 42,
  "fecha_hora": "2026-11-19T10:32:05",
  "foto": "/captures/20261119_103205.jpg",
  "modo": "ia",
  "probabilidades": {"organica": 0.821, "inorganica": 0.120, "peligroso": 0.059},
  "pred_id": 0,
  "confianza": 0.821,
  "dudoso": false,
  "motivo_dudoso": null,
  "final_id": 0,
  "origen": "camara",
  "corregido": false,
  "modelo_version": "v1",
  "tiempo_ciclo_ms": 3120,
  "drop_confirmado": true,
  "bote_id": 0,
  "tiempos_etapas": {"CAPTURA": 412, "CLASIFICACION": 180, "VERIFICAR_BOTE": 2, "POSICIONAR": 1650, "SOLTAR": 820, "REGISTRAR": 15, "ACTUALIZAR_NIVEL": 5, "HOME": 1600},
  "simulado": true,
  "estado": "registrado"
}
```
- `final_id` es `null` mientras el caso está en revisión o pendiente.
- `tiempos_etapas`: milisegundos que duró cada estado del ciclo (diagnóstico). Vale `null` mientras el ciclo no termina.
- `drop_confirmado` vale `true` con `DROP_OK`, `false` con `DROP_TIMEOUT` y `null` si el residuo no se soltó.
- En modo Adivina, **antes de que el usuario responda**, el backend **no envía** `probabilidades`, `pred_id`, `confianza` ni `dudoso`. En su lugar manda `"oculto": true`.

### 2.2 `Bote`
```json
{
  "id": 0, "nombre": "Orgánica", "color": "verde", "categoria_id": 0,
  "capacidad_piezas": 12, "piezas_actuales": 10, "no_confirmadas": 1,
  "nivel": 0.833, "estado": "casi_lleno", "bloqueado": false,
  "umbral_aviso": 0.8, "ultimo_vaciado": "2026-11-19T09:10:00",
  "capacidad_calibrada": false,
  "estimado": true
}
```

### 2.3 `Retroalimentacion` (modo Adivina)
```json
{
  "adivinanza_id": 7,
  "clasificacion_id": 42,
  "numero_intento": 3,
  "respuesta_usuario": 1,
  "categoria_referencia": 0,
  "fuente_referencia": "ia",
  "confianza_ia": 0.72,
  "nivel_certeza": "media",
  "correcto": false,
  "tono": "prudente",
  "titulo": "PROBABLEMENTE NO",
  "explicacion_corta": "Prob. organica: se descompone sola",
  "explicacion_larga": "Probablemente va en Orgánica porque proviene de un ser vivo…",
  "dato_categoria": null,
  "tiempo_en_pantalla_s": 8,
  "puede_reportar": true,
  "medio": "panel",
  "marcador": {"aciertos": 2, "intentos": 3, "racha": 0, "mejor_racha": 2}
}
```
- `tono` vale `firme` (niveles verificada y alta) o `prudente` (nivel media).
- Si la IA está **dudosa** (nivel `baja`), se envía `"correcto": null`, `"titulo": "La IA tampoco esta segura"` y `"pendiente_operador": true`. La adivinanza se califica después, con la decisión del operador.
- Si el usuario no responde en 20 s: `"medio": "sin_respuesta"`, `"respuesta_usuario": null` y `"correcto": null`.
- `dato_categoria` lleva texto solo cuando la respuesta es correcta.

### 2.4 `Alerta`
```json
{"nivel": "error", "codigo": "SERIAL_DESCONECTADO", "mensaje": "Se perdió el enlace con el Arduino", "fecha_hora": "2026-11-19T10:40:00"}
```
Códigos: `SERIAL_CONECTADO`, `SERIAL_DESCONECTADO`, `ERROR_SERIAL`, `ARDUINO_REINICIADO`, `WATCHDOG`, `CAMARA_NO_DISPONIBLE`, `MODELO_NO_CARGADO`, `POS_TIMEOUT`, `DROP_TIMEOUT`, `BOTE_CASI_LLENO`, `BOTE_LLENO`, `REVISION_PENDIENTE`, `RESIDUO_NO_RETIRADO`, `ERROR_INTERNO`, `RECUPERADO`, `MODELO_ACTIVADO`, `CAL_NO_SINCRONIZADA`, `VOZ_NO_DISPONIBLE`.

---

## 3. Endpoints REST

### 3.1 Estado
**`GET /api/estado`**
```json
{
  "estado": "MENU",
  "estado_desde": "2026-11-19T10:31:00",
  "modo": null,
  "modo_por_defecto": "ia",
  "simulacion": true,
  "serial": {"conectado": true, "puerto": "SIMULADO", "simulado": true},
  "camara": {"disponible": true, "indice": 0, "simulada": true},
  "modelo": {"cargado": true, "version": "sim", "simulado": true},
  "voz": {"disponible": false},
  "caso_actual": null,
  "cuenta_regresiva_s": null,
  "mensaje": "Coloca un residuo o elige un modo",
  "lcd": ["== CLASIFICADOR ==", "1: Usar IA", "2: Adivinar (reto)", "Coloca o elige"],
  "prueba_actual": null,
  "alertas": []
}
```
- `caso_actual` es una `Clasificacion` (ver 2.1) mientras haya un residuo en proceso.
- `cuenta_regresiva_s` se llena en `ESPERA_ADIVINANZA` (20 s), `RETROALIMENTACION` (5 u 8 s) y `REVISION` (30 s).
- `prueba_actual` se llena durante la prueba controlada:
  ```json
  {"sesion_id": 3, "alias": "V1", "ronda": 1, "indice": 4, "total": 10, "residuo_esperado": {"id": 7, "nombre": "Lata"}}
  ```

### 3.2 Modo y menú
| Ruta | Cuerpo | Respuesta |
|---|---|---|
| `GET /api/modo` | — | `{"modo": "ia", "estado": "MENU"}` |
| `POST /api/modo` | `{"modo": "ia" \| "adivina" \| "menu"}` (`menu` = volver al menú) | Igual que el GET. `409` si hay un residuo en proceso |

### 3.3 Clasificaciones
| Ruta | Cuerpo / parámetros | Respuesta |
|---|---|---|
| `GET /api/clasificaciones` | `?limit=50&offset=0&dudosos=0\|1&simulado=incluir\|excluir\|solo` | `{"total": 120, "items": [Clasificacion, …]}`, de la más reciente a la más antigua |
| `POST /api/clasificaciones/{id}/corregir` | `{"final_id": 1}` | La `Clasificacion` actualizada (`corregido: true`, `origen: "panel"`). La foto se copia a `dataset/<clase>/` |

### 3.4 Revisión (casos dudosos) — **agregado**
La especificación pide que el panel resuelva dudosos (sección 4, regla 4), pero no define la ruta.

| Ruta | Cuerpo | Respuesta |
|---|---|---|
| `POST /api/revision` | `{"accion": "resolver", "final_id": 1}` o `{"accion": "pendiente"}` | `{"ok": true, "estado": "VERIFICAR_BOTE"}`. `409` si el estado no es `REVISION` |

Si la resuelve el panel, es una decisión del operador: la foto va directo a `dataset/<clase>/` y, en modo Adivina, la referencia queda como `verificada`.

### 3.5 Estadísticas del sistema
**`GET /api/estadisticas?simulado=incluir|excluir|solo`**
```json
{
  "muestra": 58,
  "por_categoria": {
    "0": {"conteo": 20, "aciertos": 18, "precision": 0.90},
    "1": {"conteo": 25, "aciertos": 22, "precision": 0.88},
    "2": {"conteo": 13, "aciertos": 12, "precision": 0.92}
  },
  "tasa_acierto": 0.897,
  "matriz_confusion": {"etiquetas": [0, 1, 2], "filas": "real", "columnas": "predicha", "valores": [[18, 1, 1], [2, 22, 1], [0, 1, 12]]},
  "dudosos": 6,
  "corregidos": 6,
  "tiempo_promedio_ms": 3240,
  "desviados_por_categoria": {"0": 20, "1": 25, "2": 13},
  "incluye_simulados": true
}
```
La "categoría real" es `final_id`, que es la corrección si la hubo. Los casos sin `final_id` no cuentan.

### 3.6 Pruebas oficiales (manual vs. sistema)
| Ruta | Cuerpo | Respuesta |
|---|---|---|
| `GET /api/pruebas` | — | `{"residuos": [ResiduoPrueba], "registros": [Prueba], "comparativa": {...}}` |
| `POST /api/pruebas` | `{"corrida": 1, "modo": "manual" \| "sistema", "residuo_id": 3, "categoria_asignada": 1, "tiempo_s": 4.2}` | La `Prueba` creada. `correcto` lo calcula el backend |
| `POST /api/pruebas/residuos` (**agregado**) | `{"nombre": "Lata", "categoria_real": 1, "simulado": false, "usado_en_entrenamiento": false}` | El `ResiduoPrueba` creado |

- `ResiduoPrueba`: `{"id", "nombre", "categoria_real", "simulado", "usado_en_entrenamiento"}`
- `Prueba`: `{"id", "corrida", "modo", "residuo_id", "categoria_asignada", "correcto", "tiempo_s", "fecha_hora"}`
- `comparativa`:
  ```json
  {"manual": {"n": 20, "aciertos": 17, "precision": 0.85, "tiempo_promedio_s": 3.9}, "sistema": {"n": 20, "aciertos": 19, "precision": 0.95, "tiempo_promedio_s": 3.2}, "matriz_sistema": {...}, "matriz_manual": {...}}
  ```

### 3.7 Modelo
| Ruta | Respuesta |
|---|---|
| `POST /api/modelo/reentrenar` | `202 {"estado": "en_curso"}`. `409` si ya hay un entrenamiento en curso |
| `GET /api/modelo/estado` | Ver abajo |

Respuesta de `GET /api/modelo/estado`:
```json
{
  "activo": "v2", "entrenando": false, "progreso": null, "mensaje": null,
  "ultimo_resultado": {"version": "v3", "precision_val": 0.91, "precision_anterior": 0.89, "activado": true, "mensaje": "v3 activado: no empeoró"},
  "versiones": [{"version": "v2", "fecha": "2026-11-19T15:00:00", "n_imagenes": 150, "precision_val": 0.89, "activo": true}]
}
```

### 3.8 Configuración
**`GET /api/config`**
```json
{
  "valores": {
    "umbral_general": 0.60, "umbral_peligroso": 0.35, "umbral_tono_firme": 0.80,
    "modo_por_defecto": "ia",
    "angulos": {"0": 170, "1": 90, "2": 10}, "angulo_home": 90,
    "puerto_serial": "COM5", "indice_camara": 0,
    "roi": [0.0, 0.0, 1.0, 1.0],
    "tiempo_adivinanza_s": 20, "tiempo_revision_s": 30,
    "tiempo_retro_firme_s": 5, "tiempo_retro_media_s": 8,
    "umbral_aviso_bote": 0.80
  },
  "categorias": [{"id": 0, "clave": "organica", "nombre": "Orgánica", "color": "verde", "hex": "#2E9E44"}],
  "requieren_reinicio": ["indice_camara", "puerto_serial"]
}
```
**`PUT /api/config`**: el cuerpo es un objeto **parcial**, por ejemplo `{"umbral_general": 0.7}`. Responde la configuración completa. Si un valor está fuera de rango (umbrales fuera de 0–1, ángulos fuera de 0–180), responde `422`. Al cambiar un ángulo, el backend manda `CAL:<id>:<ángulo>` al Arduino.

### 3.9 Juego "¿Le ganas a la IA?"
| Ruta | Cuerpo | Respuesta |
|---|---|---|
| `POST /api/juego/adivinar` | `{"categoria": 1}` | `Retroalimentacion`. `409` si el estado no es `ESPERA_ADIVINANZA` |
| `POST /api/juego/reportar-error` | `{}` | `{"ok": true, "estado": "REVISION"}`. `409` si el estado no es `RETROALIMENTACION` |
| `POST /api/juego/continuar` (**agregado**: equivale a la tecla `B`) | `{}` | `{"ok": true}`. Corta el tiempo de retroalimentación |
| `GET /api/juego/sesion` | — | `{"activa": true, "id": 5, "tipo": "libre", "alias": null, "inicio": "…", "intentos": 3, "aciertos": 2, "racha": 0, "mejor_racha": 2}`, o `{"activa": false}` |
| `GET /api/juego/estadisticas` | `?niveles=verificada,alta` (valor por defecto) | Ver abajo |
| `GET /api/juego/aprendizaje` | `?niveles=verificada,alta` | Ver abajo |
| `POST /api/juego/prueba-aprendizaje` | `{"alias": "V1", "ronda": 1, "residuos": [3, 5, 7, …]}` | `{"sesion_id": 9, "orden": [7, 3, 5, …]}` (orden aleatorio). Si no hay residuos de prueba registrados, responde `400` |

Respuesta de `GET /api/juego/estadisticas`:
```json
{
  "niveles_usados": ["verificada", "alta"],
  "n_adivinanzas": 40, "n_sesiones": 9,
  "acierto_humano": 0.62,
  "por_categoria": {"0": {"n": 12, "acierto": 0.75}, "1": {"n": 18, "acierto": 0.61}, "2": {"n": 10, "acierto": 0.50}},
  "matriz_confusion_humana": {"etiquetas": [0, 1, 2], "filas": "real", "columnas": "adivinanza", "valores": [[9, 2, 1], [5, 11, 2], [1, 4, 5]]},
  "humano_vs_ia": {"n": 40, "acierto_humano": 0.62, "acierto_ia": 0.90},
  "parejas_confusion": [{"dijo": 1, "era": 0, "veces": 5}, {"dijo": 1, "era": 2, "veces": 4}],
  "media_aparte": {"n_adivinanzas": 6, "acierto_humano": 0.5},
  "muestra_pequena": true
}
```

Respuesta de `GET /api/juego/aprendizaje`:
```json
{
  "niveles_usados": ["verificada", "alta"],
  "por_intento": [{"intento": "1", "n": 9, "acierto": 0.44}, {"intento": "2", "n": 9, "acierto": 0.56}, {"intento": "6+", "n": 4, "acierto": 0.75}],
  "mitades": {"n_sesiones": 5, "primera": 0.52, "segunda": 0.70, "diferencia": 0.18},
  "correccion_tras_explicacion": {"n_oportunidades": 7, "corregidas": 5, "tasa": 0.71},
  "rondas": {
    "por_participante": [{"alias": "V1", "ronda1": 0.6, "ronda2": 0.8, "n1": 10, "n2": 10}],
    "promedio": {"ronda1": 0.6, "ronda2": 0.8, "n_voluntarios": 1}
  },
  "muestra": {"n_sesiones": 9, "n_intentos": 40, "n_voluntarios": 1},
  "muestra_pequena": true
}
```
- `muestra_pequena` vale `true` si hay menos de 10 sesiones o menos de 5 voluntarios. El panel muestra entonces el rótulo **"muestra pequeña: resultado indicativo"**.
- Las tasas sin datos se envían como `null`, no como 0.

### 3.10 Botes
| Ruta | Cuerpo | Respuesta |
|---|---|---|
| `GET /api/botes` | — | `{"botes": [Bote ×3], "vaciados": [{"id", "bote_id", "fecha_hora", "piezas_al_vaciar", "origen"}], "desviados_por_categoria": {"0": 34, "1": 51, "2": 12}}` |
| `POST /api/botes/{id}/vaciar` | `{}` | El `Bote` actualizado. Si había un residuo esperando, el ciclo continúa |
| `PUT /api/botes/{id}` | `{"capacidad_piezas": 3, "umbral_aviso": 0.8}` (parcial) | El `Bote` actualizado |

### 3.11 Etiquetas por verificar
| Ruta | Cuerpo | Respuesta |
|---|---|---|
| `GET /api/dataset/por-verificar` | — | `{"items": [{"id": "inorganica/20261119_103205.jpg", "clase_id": 1, "foto": "/captures/20261119_103205.jpg", "origen": "voz", "clasificacion_id": 42, "fecha_hora": "…"}]}` |
| `POST /api/dataset/por-verificar` | `{"id": "inorganica/20261119_103205.jpg", "accion": "aprobar" \| "rechazar"}` | `{"ok": true, "pendientes": 3}` |

### 3.12 Control manual (solo en `MENU`, `OPERADOR` o `ERROR`; si no, `409`)
| Ruta | Cuerpo |
|---|---|
| `POST /api/manual/pos` | `{"id": 0}` |
| `POST /api/manual/ang` (**agregado**, para calibrar) | `{"grados": 95}` |
| `POST /api/manual/home` | `{}` |
| `POST /api/manual/drop` | `{}` |
| `POST /api/manual/light` | `{"on": true}` |
| `POST /api/manual/led` | `{"color": "VERDE" \| "AMARILLO" \| "ROJO" \| "OFF", "parpadeo": false}` |

Respuesta: `{"ok": true, "respuesta_arduino": "POS_OK:0"}`. Si el Arduino no responde a tiempo, `503`. Cada acción manual se registra en `eventos` con origen `manual`.

### 3.13 Archivos
`GET /captures/{archivo}` → `image/jpeg`.

---

## 4. WebSocket `/ws/eventos`

Cada mensaje del servidor tiene esta forma:
```json
{"tipo": "<tipo>", "ts": "2026-11-19T10:32:05", "datos": {...}}
```

| `tipo` | Cuándo | `datos` |
|---|---|---|
| `hola` | Al conectarse | Igual que `GET /api/estado` (foto completa del estado) |
| `estado` | Cada transición de la máquina | `{"estado", "anterior", "modo", "mensaje", "lcd", "cuenta_regresiva_s", "caso_actual"}` |
| `captura` | Al tomar la foto | `{"clasificacion_id", "foto", "oculto"}` |
| `clasificacion` | Al terminar de clasificar. En modo Adivina, **después** de la respuesta del usuario | `Clasificacion` |
| `revision` | Al entrar a `REVISION` | `{"clasificacion": Clasificacion, "motivo", "tiempo_limite_s": 30}` |
| `retroalimentacion` | Después de una adivinanza | `Retroalimentacion` |
| `registrado` | Después de `REGISTRAR` | `Clasificacion` (final) |
| `bote` | Cuando cambia el nivel, se bloquea o se vacía un bote | `Bote` |
| `modo` | Cuando cambia el modo | `{"modo"}` |
| `sesion` | Cuando cambia el marcador del juego | Igual que `GET /api/juego/sesion` |
| `modelo` | Progreso y fin de un reentrenamiento | Igual que `GET /api/modelo/estado` |
| `alerta` | Fallas y avisos | `Alerta` |
| `tecla` | Cada tecla del teclado 4×4 (para mostrarla en el panel) | `{"tecla": "1"}` |

- **Mensajes del panel al servidor:** solo `{"tipo": "ping"}`, al que el servidor responde `{"tipo": "pong", …}`.
- **Reconexión del panel:** reintenta a los 1, 2, 5 y 5 s. Mientras está desconectado, consulta `GET /api/estado` cada 2 s y muestra el aviso "Sin conexión en vivo".

---

## 5. Protocolo serial — aclaraciones a la sección 9

Se usa a 115 200 baudios, en ASCII, con líneas terminadas en `\n` (el Arduino ignora `\r`). Cada línea mide como máximo **80 caracteres**.

### 5.1 Respuestas de cada comando (PC → Arduino)
| Comando | Respuesta inmediata | Respuesta al terminar |
|---|---|---|
| `PING` | `PONG` | — |
| `POS:<0\|1\|2>` | — | `POS_OK:<id>` cuando termina la rampa |
| `ANG:<0-180>` (**agregado**) | — | `ANG_OK:<grados>` |
| `HOME` | — | `HOME_OK` (**agregado**: la especificación no define respuesta) |
| `DROP` | — | `DROP_OK` o `DROP_TIMEOUT` (2 s desde que se abre la trampilla) |
| `LIGHT:<ON\|OFF>` | `OK` (**agregado**) | — |
| `LED:<VERDE\|AMARILLO\|ROJO\|OFF>[:PARPADEO]` | `OK` | — |
| `LCD:<l1>\|<l2>\|<l3>\|<l4>` | `OK` | — |
| `LCD_SCROLL:<texto>` | `OK` | — |
| `CAL:<id>:<ángulo>` | `CAL_OK:<id>:<ángulo>` (**agregado**) | — |
| `STATUS` (**agregado**, diagnóstico) | `STATUS:ang=<a>,tramp=<CERRADA\|ABIERTA>,obj=<0\|1>,cal=<a0>/<a1>/<a2>` | — |

### 5.2 Mensajes espontáneos (Arduino → PC)
| Mensaje | Significado |
|---|---|
| `READY` | Arranque completo; trampilla cerrada y disco en HOME |
| `OBJ` | Objeto estable en la bandeja (≥ 300 ms). Se envía **una vez** por objeto, en el flanco |
| `LIBRE` (**agregado**) | La bandeja quedó vacía (≥ 300 ms sin objeto). Sirve para `PENDIENTE` y `BOTE_LLENO` |
| `KEY:<tecla>` | Tecla presionada: `0–9`, `A–D`, `*`, `#` |
| `WATCHDOG` (**agregado**) | Pasaron 15 s sin comandos: el disco volvió a HOME y la trampilla se cerró |

### 5.3 Errores
`ERR:CMD_DESCONOCIDO`, `ERR:ARG` (argumento inválido), `ERR:ANG_RANGO` (ángulo fuera de 0–180), `ERR:OCUPADO` (llega `POS`, `ANG`, `HOME` o `DROP` mientras un servo se mueve), `ERR:LINEA_LARGA`.

### 5.4 Reglas
- Solo se mueve un servo a la vez. Mientras el disco gira, `DROP` responde `ERR:OCUPADO`.
- El backend envía `PING` cada **3 s** como latido. Si el Arduino no recibe ningún comando en **15 s**, aplica el watchdog.
- Para eliminar el juego mecánico, el disco **siempre se acerca al ángulo destino desde abajo** (desde un ángulo menor). Si el destino es menor que el actual, primero baja 5° de más y luego sube.
- El backend **quita acentos y el carácter `|`** de los textos antes de mandarlos y recorta cada línea a 20 caracteres. El Arduino confía en esos textos, pero no se cae si llega algo más largo: recorta.
- Los valores por defecto de los ángulos (170 / 90 / 10, con HOME en 90) se usan **solo si la EEPROM está vacía**. El valor bueno viene de la calibración.
- **Cada vez que se conecta**, el backend manda `CAL:0`, `CAL:1` y `CAL:2` con los ángulos de su configuración. La configuración del backend es la fuente de verdad, y la EEPROM es la copia para cuando el Arduino trabaja solo.

---

## 6. Datos que el panel no debe calcular

El panel **solo muestra** lo que manda el backend. Las reglas de decisión, los niveles de certeza, los tonos, las estadísticas y la curva de aprendizaje se calculan en Python, porque esa es la única fuente de verdad. Así el resultado es igual en la LCD y en el panel.

## 7. Modo simulación

Con `SIMULACION=1`, el backend se comporta igual en esta API, con estas diferencias:
- `serial.simulado`, `camara.simulada`, `modelo.simulado` y el campo `simulado` de cada clasificación valen `true`.
- **`POST /api/sim/objeto`** (**agregado**, solo en simulación) simula que se colocó un residuo, como si llegara `OBJ`. El cuerpo es opcional: `{"categoria_real": 1}`, para forzar la imagen de una carpeta de `sim_images/`.
- **`POST /api/sim/tecla`** (**agregado**, solo en simulación): `{"tecla": "1"}` simula una tecla del teclado 4×4.
- **`POST /api/sim/retirar`** (**agregado**, solo en simulación) simula que el operador retiró el residuo de la bandeja (`LIBRE`).
- En simulación, el backend usa otra base de datos (`clasificador_sim.db`) para no mezclar datos simulados con reales.

Mientras el backend no exista, el panel puede trabajar con **datos de ejemplo**: los JSON de este documento, guardados en `frontend/src/mock/`.

## 8. Agregados respecto a la especificación (resumen)

| Agregado | Motivo |
|---|---|
| Estados `OPERADOR` y `ERROR` | Menú de operador (tecla D) y falla segura explícita |
| `POST /api/revision` | Resolver dudosos desde el panel (regla 4 de la sección 4) |
| `POST /api/pruebas/residuos` | Registrar los 20 residuos del set de prueba |
| `POST /api/juego/continuar` | Equivale a la tecla B en la retroalimentación |
| `POST /api/manual/ang` y serial `ANG` / `ANG_OK` | Calibrar ángulos (Fase 5) |
| Serial `HOME_OK`, `OK`, `CAL_OK`, `STATUS`, `LIBRE`, `WATCHDOG` | La especificación pide "responder siempre"; `LIBRE` sirve para saber cuándo se retiró el residuo |
| `POST /api/sim/objeto`, `/api/sim/tecla` y `/api/sim/retirar` | Probar el ciclo completo sin hardware (sección 20.2) |
| `motivo_dudoso: sin_modelo` y `estado` de la clasificación | Falla segura sin modelo; distinguir casos pendientes o con error |

## 9. Historial

| Versión | Fecha | Quién | Cambio |
|---|---|---|---|
| 1.0 | 2026-11-19 | Persona A (generado con Claude Code) | Versión inicial |
| 1.3 | 2026-11-19 | Persona A (generado con Claude Code) | Fase 5: campo `tiempos_etapas` en Clasificacion; el backend manda los 3 `CAL` al conectarse; alerta `CAL_NO_SINCRONIZADA`. **Avisar a la Persona B** (el firmware debe responder `CAL_OK` rápido justo después de `READY`). |
| 1.2 | 2026-11-19 | Persona A (generado con Claude Code) | Fase 4: `roi` en la configuración (`[x, y, ancho, alto]` en fracciones), `indice_camara` acepta también una URL (celular), `mensaje` en `GET /api/modelo/estado`, alerta `MODELO_ACTIVADO`. `POST /api/modelo/reentrenar` ya funciona (antes `501`). **Avisar a la Persona B.** |
| 1.1 | 2026-11-19 | Persona A (generado con Claude Code) | Al implementar la Fase 3: `sin_modelo`, campo `estado` en Clasificacion, `capacidad_calibrada` en Bote, `requieren_reinicio` en la configuración, código `501`, `/api/sim/retirar` y lista completa de códigos de alerta. **Avisar a la Persona B.** |
