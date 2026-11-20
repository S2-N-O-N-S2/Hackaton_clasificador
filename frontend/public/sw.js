// Service worker mínimo para que el panel se pueda instalar como app (PWA).
//
// NO guarda nada en caché a propósito: el panel debe mostrar SIEMPRE los datos en vivo del backend,
// nunca una versión vieja. Solo intercepta la navegación (abrir la app) para mostrar un aviso claro
// si la laptop no responde. Las llamadas al backend (puerto 8000) y el WebSocket no se tocan.

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (evento) => evento.waitUntil(self.clients.claim()));

const PAGINA_SIN_CONEXION = `<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Clasificador</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#E9F2EE;color:#1A2A28;
font-family:system-ui,sans-serif;text-align:center;padding:24px;box-sizing:border-box}
button{margin-top:16px;padding:12px 20px;border:0;border-radius:6px;background:#0E7C86;color:#FFFFFF;
font-weight:700;font-size:1rem}</style></head><body><div><h1>Sin conexión con la laptop</h1>
<p>Revisa que la laptop esté encendida, con el panel corriendo, y que el celular esté en la misma red Wi-Fi.</p>
<button onclick="location.reload()">Reintentar</button></div></body></html>`;

// Si el servidor del panel se reinició, el primer intento puede fallar con una conexión vieja aunque
// la laptop ya responda: se reintenta una vez (con una petición nueva) antes de mostrar el aviso.
async function navegar(peticion) {
  try {
    return await fetch(peticion);
  } catch {
    await new Promise((listo) => setTimeout(listo, 400));
    try {
      return await fetch(peticion.url, { cache: 'no-store', credentials: 'same-origin' });
    } catch {
      return new Response(PAGINA_SIN_CONEXION, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
    }
  }
}

self.addEventListener('fetch', (evento) => {
  if (evento.request.mode !== 'navigate') return; // todo lo demás va directo a la red, sin caché
  evento.respondWith(navegar(evento.request));
});
