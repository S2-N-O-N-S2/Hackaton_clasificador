# backend

Orquestador en **Python + FastAPI**: máquina de estados, serial, cámara, IA, voz, SQLite, API REST y WebSocket.

| Carpeta | Contenido |
|---|---|
| `app/` | Código del servidor (`main.py`, `orchestrator.py`, …) |
| `training/` | Captura de dataset, entrenamiento y evaluación |
| `tools/` | Utilidades (verificar hardware, calibrar ángulos) |
| `data/` | `keywords.json`, `explicaciones.json` |
| `dataset/` | Fotos etiquetadas por clase (no se suben a git) |
| `models/` | Modelos versionados `v<N>/` y modelo Vosk (no se suben a git) |
| `captures/` | Fotos de cada ciclo (no se suben a git) |
| `sim_images/` | Imágenes para el modo simulación (`SIMULACION=1`) |
| `tests/` | Pruebas con pytest |

```powershell
cd backend; python -m venv .venv; .\.venv\Scripts\Activate.ps1
```
