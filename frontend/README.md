# frontend — Panel React + Vite (Fase 6)

Panel del clasificador. Se comunica con el backend por REST y WebSocket (`/ws/eventos`) según `docs/api_contrato.md`.
**Una sola fuente de verdad:** el panel solo muestra lo que manda el backend; no calcula reglas, certezas ni estadísticas.

## Comandos (PowerShell)

```powershell
cd frontend
npm install              # solo la primera vez (necesita internet)
npm run dev:mock         # datos de ejemplo, sin backend (VITE_MOCK=1)
npm run dev              # con el backend real en el puerto 8000
npm run build            # versión optimizada en frontend/dist/
```

Abrir `http://localhost:5173`. Desde un celular **en la misma red**: `http://<IP-de-la-laptop>:5173`
(la IP se ve con `ipconfig`, en "Dirección IPv4"). Si Windows pregunta por el firewall, permitir el acceso en **redes privadas**.
Para **instalarlo como app** en el celular (PWA, con ícono y pantalla completa), ver [`docs/app_movil.md`](../docs/app_movil.md).

Para el celular, el **backend** también debe escuchar en la red (por defecto uvicorn solo atiende a `127.0.0.1`):

```powershell
cd backend; .\.venv\Scripts\Activate.ps1; $env:SIMULACION="1"; uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Configuración

Todo está en `src/config.js`:
- **Backend:** por defecto, la misma máquina que sirve el panel, puerto 8000 (funciona igual desde el celular).
  Para otro backend: `$env:VITE_BACKEND_URL="http://192.168.1.20:8000"; npm run dev`.
- **Datos de ejemplo:** `npm run dev:mock` o `$env:VITE_MOCK="1"; npm run dev`.
- Reconexión del WebSocket (1, 2, 5, 5 s), latido y polling cada 2 s.

## Estructura

| Archivo | Qué hace |
|---|---|
| `src/config.js` | URL del backend y tiempos de conexión |
| `src/api.js` | Una función por endpoint del contrato |
| `src/ws.js` | WebSocket con reconexión, latido y polling de respaldo |
| `src/estado.jsx` | Estado global alimentado por los eventos del WebSocket |
| `src/mock/` | JSON de ejemplo del contrato + servidor simulado (`servidorMock.js`) |
| `src/componentes/` | Piezas comunes (barras, rótulos SIMULADO/ESTIMADO, LCD) y gráficas SVG/CSS |
| `src/vistas/` | Una vista por pestaña: Inicio, En vivo, ¿Le ganas a la IA?, Humano vs. IA, Aprendizaje, Botes, Historial, Estadísticas, Pruebas, Configuración |

Dependencias: solo `react`, `react-dom`, `vite` y `@vitejs/plugin-react`. Las gráficas son SVG/CSS propios.
