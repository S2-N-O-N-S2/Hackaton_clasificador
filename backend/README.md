# backend

Orquestador en **Python + FastAPI**: máquina de estados, serial, cámara, IA, voz, SQLite, API REST y WebSocket.
Contrato de la API: [`docs/api_contrato.md`](../docs/api_contrato.md).

| Carpeta / archivo | Contenido |
|---|---|
| `app/orchestrator.py` | **Máquina de estados** (toda la lógica del ciclo) |
| `app/model.py` | **Reglas de decisión** (`aplicar_reglas`) y modelo (simulado por ahora) |
| `app/serial_link.py` | Enlace con el Arduino (real y simulado) |
| `app/camera.py` | Cámara (real y simulada), guardado de fotos, copia al dataset |
| `app/db.py` | Esquema SQLite y consultas |
| `app/config.py` | **Toda la configuración** (umbrales, ángulos, tiempos, rutas) |
| `app/lcd_ui.py` | Pantallas de la LCD (20 caracteres, sin acentos) |
| `app/bins.py`, `app/game.py`, `app/voice.py` | Botes, juego y voz (versiones básicas; se completan en las fases 7, 8 y 9) |
| `app/routes.py`, `app/main.py` | API REST y WebSocket |
| `training/` | Captura de dataset, entrenamiento y evaluación (Fase 4) |
| `tools/` | `verificar_hardware.py`, `calcular_par.py` |
| `tests/` | Pruebas con pytest |

## Preparar el entorno (una vez)
```powershell
cd backend; py -3.12 -m venv .venv; .\.venv\Scripts\Activate.ps1; python -m pip install -r requirements.lock.txt
```

## Correr sin hardware (simulación)
```powershell
cd backend; .\.venv\Scripts\Activate.ps1; $env:SIMULACION="1"; uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
```
- API interactiva: <http://localhost:8000/docs>
- Simular un residuo: `POST /api/sim/objeto` con `{"categoria_real": 0}` (o `1`, `2`, `"dudoso"`, o sin cuerpo para uno al azar).
- Simular una tecla: `POST /api/sim/tecla` con `{"tecla": "1"}`. Retirar el residuo: `POST /api/sim/retirar`.
- Los datos van a `clasificador_sim.db` y se marcan como **SIMULADO**.

## Correr con Arduino y cámara
```powershell
cd backend; .\.venv\Scripts\Activate.ps1; $env:SIMULACION="0"; uvicorn app.main:app --port 8000 --host 0.0.0.0
```
El puerto serie es `AUTO` por defecto: detecta el Arduino o un clon CH340. Para fijarlo: `$env:PUERTO_SERIAL="COM5"`. Para otra cámara: `$env:INDICE_CAMARA="1"`.

## Pruebas
```powershell
cd backend; .\.venv\Scripts\Activate.ps1; python -m pytest
```
