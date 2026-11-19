// =============================================================================
//  Configuración del panel: ÚNICO lugar donde se define a qué backend se conecta.
// =============================================================================

// Por defecto, el backend está en la misma máquina que sirve el panel, en el puerto 8000.
// Así funciona igual en la laptop (localhost) y en un celular de la misma red (IP de la laptop).
// Para usar otro backend: variable VITE_BACKEND_URL, por ejemplo
//   $env:VITE_BACKEND_URL="http://192.168.1.20:8000"; npm run dev
const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
export const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL || `http://${host}:8000`).replace(/\/$/, '');
export const WS_URL = BACKEND_URL.replace(/^http/, 'ws') + '/ws/eventos';

// Modo de datos de ejemplo (sin backend): `npm run dev:mock` o VITE_MOCK=1.
export const MODO_MOCK = import.meta.env.VITE_MOCK === '1' || import.meta.env.MODE === 'mock';

// WebSocket (contrato, sección 4)
export const RECONEXION_S = [1, 2, 5, 5]; // espera antes de cada reintento; después se repite el último
export const POLLING_MS = 2000;           // GET /api/estado mientras no hay WebSocket
export const PING_MS = 5000;              // latido hacia el servidor
export const PONG_TIMEOUT_MS = 12000;     // sin mensajes en este tiempo → se reconecta

// Vistas
export const HISTORIAL_POR_PAGINA = 25;
export const MAX_ALERTAS = 20;
