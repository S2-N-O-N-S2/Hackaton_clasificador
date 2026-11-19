# App móvil (PWA) — el panel instalado en el celular

El panel React se puede **instalar en el celular como una app**: ícono propio en la pantalla de inicio, pantalla completa
y sin la barra del navegador. Es el **mismo panel**, no otra aplicación: cualquier cambio en `frontend/` aparece en el
celular al instante, sin volver a instalar nada.

> Es una **PWA** (*Progressive Web App*): un sitio web con un manifiesto (`manifest.webmanifest`), íconos y un
> *service worker* (`sw.js`). No se agregó ninguna biblioteca ni lenguaje nuevo.

## Qué se necesita
- La **laptop** con el backend y el panel corriendo (el celular solo muestra la interfaz; todo se procesa en la laptop).
- El celular en la **misma red Wi-Fi** que la laptop.
- **Otro celular**, no el de la cámara (ese está fijo transmitiendo con DroidCam).
- Chrome en Android (recomendado) o Safari en iPhone.

## 1. Arrancar el backend y el panel "hacia la red"
En dos terminales, desde la carpeta del proyecto:
```powershell
cd backend; .\.venv\Scripts\Activate.ps1; $env:SIMULACION="0"; uvicorn app.main:app --host 0.0.0.0 --port 8000
```
```powershell
cd frontend; npm run dev -- --host
```
`--host 0.0.0.0` y `--host` permiten que el celular se conecte. Si Windows pregunta por el firewall, **permitir en redes privadas**.

## 2. Saber la IP de la laptop
```powershell
ipconfig
```
Usar la **"Dirección IPv4" del adaptador Wi-Fi** (ej. `10.10.36.201` o `192.168.1.x`). Las que terminan en `.1` de
adaptadores virtuales (VirtualBox, Hyper-V/WSL, por ejemplo `192.168.56.1`) **no sirven**: no son la red del celular.
Vite también las lista al arrancar (`Network: http://…:5173/`).

Probar primero en el navegador del celular: `http://<IP>:5173`. Debe verse el panel conectado.

## 3. Instalar la app

### Android (Chrome)
Chrome solo instala una PWA "completa" en una página **segura** (HTTPS o `localhost`). En la red local la dirección es
`http://<IP>`, así que hay dos caminos:

**A) Instalación completa (recomendada para la demo, se hace una vez, ~2 min):**
1. En el celular, abrir Chrome y escribir `chrome://flags`.
2. Buscar **"Insecure origins treated as secure"**, activarlo (**Enabled**) y escribir en el cuadro:
   `http://<IP>:5173` (por ejemplo `http://10.10.36.201:5173`).
3. Tocar **Relaunch**.
4. Abrir `http://<IP>:5173` → menú **⋮** → **"Instalar app"** (o el aviso "Agregar Clasificador a la pantalla principal").
5. Aparece el ícono de los tres botes con el nombre **"Clasificador"**. Abre en pantalla completa.

**B) Acceso directo (sin tocar flags):** abrir `http://<IP>:5173` → menú **⋮** → **"Agregar a pantalla principal"**.
Crea el ícono, pero puede abrir con la barra del navegador.

### iPhone (Safari)
Abrir `http://<IP>:5173` → botón **Compartir** → **"Agregar a pantalla de inicio"**. Abre en pantalla completa.

## Si algo falla
| Síntoma | Causa | Solución |
|---|---|---|
| El celular no abre `http://<IP>:5173` | Otra red, IP equivocada o firewall | Misma Wi-Fi; IP del adaptador Wi-Fi; permitir en el firewall (redes privadas) |
| Abre pero dice "Sin conexión con el backend" | El backend no escucha en la red | Arrancar uvicorn con `--host 0.0.0.0` |
| Pantalla "Sin conexión con la laptop" (fondo oscuro) | La app instalada no encuentra la laptop | Laptop encendida, panel corriendo, misma red; botón **Reintentar** |
| No aparece "Instalar app" | Página no segura | Hacer el paso A (flag) o usar el acceso directo (B) |
| Cambió la red del evento | La IP de la laptop cambió | Repetir el flag con la IP nueva e instalar de nuevo |

## Cómo funciona (para explicarlo)
- **`frontend/public/manifest.webmanifest`**: nombre, colores y los íconos; `display: standalone` hace que abra sin barra.
- **`frontend/public/iconos/`**: íconos generados con OpenCV con la paleta del panel (normal, "adaptable" para Android
  con margen de seguridad, y el de iPhone).
- **`frontend/public/sw.js`**: el *service worker*. **No guarda nada en caché** a propósito: el panel debe mostrar
  siempre datos en vivo. Solo muestra una pantalla de "Sin conexión con la laptop" si al abrir la app no hay respuesta.
  Las llamadas al backend (puerto 8000) y el WebSocket no pasan por él.
- **`frontend/index.html`**: enlaza el manifiesto y registra el service worker (solo en páginas seguras; en
  `http://IP` sin el flag se omite sin error).

## Cómo defenderlo ante el jurado
- "No hicimos una segunda app: el mismo panel React se instala en el celular como PWA. Una sola base de código, y
  cualquier corrección se ve al instante en la laptop y en el celular."
- "El service worker no usa caché a propósito: en un sistema de control, mostrar datos viejos es peor que mostrar
  'sin conexión'. Por eso solo interviene para avisar que no encuentra la laptop."
- "Todo corre en la red local, sin nube: la laptop es el servidor y el celular solo es una pantalla más."

## Verificado
- `npm run build` incluye `manifest.webmanifest`, `sw.js` e `iconos/` en `dist/`.
- En Microsoft Edge (Chromium, mismo motor que Chrome en Android), abriendo `http://localhost:5173`: manifiesto sin
  errores, service worker **activado** y **0 errores de instalación** (`Page.getInstallabilityErrors`).
- **[COMPLETAR]** Instalación en un celular real (Android/iPhone) con la IP de la laptop en la red del evento.
