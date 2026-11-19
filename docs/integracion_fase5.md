# Fase 5 — Lista de verificación para la integración real

Seguir **en orden**. No pasar al siguiente bloque si el anterior no funciona: así cada falla queda aislada.
Todos los comandos se escriben en PowerShell desde `backend`, con el entorno activo:
```powershell
cd C:\Users\SrAno\Desktop\clasificador\backend; .\.venv\Scripts\Activate.ps1
```

## Bloque 0 — Antes de conectar nada
- [ ] Firmware cargado en el Arduino y **probado solo** desde el Monitor Serial a 115 200, con "Nueva línea" (`docs/prueba_firmware.md` de la Persona B). Si responde `PONG` a `PING`, pasar al siguiente punto.
- [ ] **Cierren el Monitor Serial del Arduino IDE.** El puerto COM solo lo puede usar un programa a la vez.
- [ ] Servos alimentados con la **fuente separada** (5–6 V), **tierra común** con el Arduino y capacitor de 1000 µF. **Nunca** desde el 5 V del Arduino.
- [ ] Cámara del celular transmitiendo (DroidCam → Start). Comprobar con `python tools\verificar_hardware.py`: el índice 1 debe salir sin el aviso "imagen de un solo color".
- [ ] El Arduino aparece en `verificar_hardware.py` → "Puertos serie", por ejemplo `COM5 <-- probablemente el Arduino`.

## Bloque 1 — Backend en modo real
```powershell
$env:SIMULACION="0"; uvicorn app.main:app --port 8000 --host 0.0.0.0
```
Qué debe verse (en <http://localhost:8000/api/estado> o en el panel):
- [ ] Unos 4 s después de arrancar, `serial.conectado = true` con el puerto COM. El estado pasa de `ERROR` ("Esperando al Arduino") a `MENU`.
- [ ] La LCD muestra el menú y el LED verde está encendido.
- [ ] La alerta `MODELO_NO_CARGADO` es **normal** mientras no haya modelo entrenado.
- [ ] Si no conecta: cierren el Monitor Serial, revisen el cable o fijen el puerto con `$env:PUERTO_SERIAL="COM5"`.

## Bloque 2 — Control manual (sin residuo)
Desde <http://localhost:8000/docs> (sección `manual`) o desde el panel:
- [ ] `POST /api/manual/light {"on": true}` → la luz blanca enciende.
- [ ] `POST /api/manual/led {"color": "AMARILLO"}` → el LED amarillo enciende.
- [ ] `POST /api/manual/pos {"id": 0}`, luego `1` y `2` → el disco gira **suave** (sin golpes) y responde `POS_OK:<id>`.
- [ ] `POST /api/manual/drop` → la trampilla abre y cierra. Sin residuo responde `DROP_TIMEOUT` (correcto).
- [ ] **Medición:** voltaje de los servos en reposo y **mientras giran** (multímetro). Si baja de ~4.8 V, la fuente no alcanza.

## Bloque 3 — Calibrar ángulos
```powershell
python tools\calibrar_angulos.py
```
(en otra terminal, con el backend corriendo)
- [ ] Flechas para mover el disco. Pon un residuo en la bandeja y presiona **D** para soltarlo. Debe caer en el **centro** de la boca del bote.
- [ ] Teclas **1 / 2 / 3** para guardar el ángulo de cada bote. Se guarda en la configuración y en la EEPROM del Arduino.
- [ ] Anotar los ángulos en `docs/resultados/ciclos_reales.md` §1.
- [ ] Al reiniciar el backend, los ángulos se vuelven a mandar al Arduino solos.

## Bloque 4 — Ciclo completo SIN IA
- [ ] Coloca un residuo → el sensor lo detecta (`OBJ`) → foto → **REVISIÓN** (LED amarillo, LCD "AYUDA: que es?").
- [ ] Presiona **1, 2 o 3** en el teclado 4×4, o resuélvelo en el panel → el disco gira al bote → la trampilla suelta → `DROP_OK` → el disco vuelve a HOME → MENU.
- [ ] Revisar `GET /api/clasificaciones`: `drop_confirmado: true` y `tiempos_etapas` con la duración de cada etapa.
- [ ] Repetirlo con los 3 botes y anotarlo en `ciclos_reales.md` §2.
- [ ] Probar el **pendiente**: deja un residuo en revisión y presiona **C** (o espera 30 s) → PENDIENTE → retíralo → MENU.

## Bloque 5 — Fallas seguras (diagnóstico de una falla, la pide la rúbrica)
- [ ] **Desconecta el USB del Arduino** con el sistema en MENU → estado `ERROR`, alerta `SERIAL_DESCONECTADO`. Al reconectar → vuelve solo a MENU.
- [ ] **Detén DroidCam** y pon un residuo → estado `ERROR` con `CAMARA_NO_DISPONIBLE`, y **no se suelta nada**.
- [ ] **Falla eléctrica diagnosticable:** con la fuente separada todo funciona; si los servos se alimentaran del 5 V del Arduino, el Arduino se reiniciaría al moverlos (el backend vería `READY` y la alerta `ARDUINO_REINICIADO`). Documentar con la medición de voltaje. **No dejarlo conectado así.**

## Bloque 6 — Con IA (cuando el modelo esté entrenado)
- [ ] Entrenar con fotos reales (`docs/guia_camara_y_dataset.md`) y reiniciar el backend: la alerta `MODELO_NO_CARGADO` ya no debe aparecer.
- [ ] 3 ciclos seguidos: orgánico → bote verde, inorgánico → bote azul, peligroso simulado → bote gris.
- [ ] 1 objeto dudoso o no entrenado → REVISIÓN (no cae).
- [ ] Anotarlos en `ciclos_reales.md` §3. **Criterio de listo: 3 de 3 correctos.**

## Dónde mirar si algo falla
| Dónde | Qué muestra |
|---|---|
| Terminal del backend | Cada transición de estado y cada error |
| `GET /api/estado` | Estado actual, enlace serial, cámara, modelo y últimas alertas |
| Tabla `eventos` (`backend/clasificador.db`) | Bitácora automática con hora: transiciones, comandos manuales y tiempos de cada caso |
| `tiempos_etapas` de cada clasificación | Qué etapa tarda de más (por ejemplo, POSICIONAR > 6 s = timeout) |
