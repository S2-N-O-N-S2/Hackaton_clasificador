// =============================================================================
//  Conexión en vivo con el backend (contrato, sección 4).
//  - WebSocket /ws/eventos con reconexión a los 1, 2, 5 y 5 s (luego cada 5 s).
//  - Latido: manda {"tipo":"ping"}; si no llega nada en PONG_TIMEOUT_MS, reconecta.
//  - Mientras no hay WebSocket: GET /api/estado cada 2 s ("Sin conexión en vivo").
// =============================================================================
import { WS_URL, MODO_MOCK, RECONEXION_S, POLLING_MS, PING_MS, PONG_TIMEOUT_MS } from './config.js';
import { api } from './api.js';
import * as mock from './mock/servidorMock.js';

// alMensaje(mensaje) recibe {tipo, ts, datos}.
// alCambiarConexion(estado) recibe 'en_vivo' | 'polling' | 'sin_backend'.
// Devuelve una función para cerrar la conexión.
export function conectarEventos({ alMensaje, alCambiarConexion }) {
  if (MODO_MOCK) return mock.suscribir(alMensaje, alCambiarConexion);

  let ws = null;
  let intento = 0;
  let detenido = false;
  let timerReconexion = null;
  let timerPing = null;
  let timerPolling = null;
  let ultimoMensaje = 0;

  async function consultarEstado() {
    try {
      const datos = await api.estado();
      if (detenido) return;
      alMensaje({ tipo: 'hola', ts: datos.estado_desde, datos });
      alCambiarConexion('polling');
    } catch {
      if (!detenido) alCambiarConexion('sin_backend');
    }
  }

  function iniciarPolling() {
    if (timerPolling) return;
    consultarEstado();
    timerPolling = setInterval(consultarEstado, POLLING_MS);
  }

  function detenerPolling() {
    clearInterval(timerPolling);
    timerPolling = null;
  }

  function programarReconexion() {
    const espera = RECONEXION_S[Math.min(intento, RECONEXION_S.length - 1)];
    intento += 1;
    clearTimeout(timerReconexion);
    timerReconexion = setTimeout(conectar, espera * 1000);
  }

  function conectar() {
    if (detenido) return;
    try {
      ws = new WebSocket(WS_URL);
    } catch {
      iniciarPolling();
      programarReconexion();
      return;
    }

    ws.onopen = () => {
      intento = 0;
      ultimoMensaje = Date.now();
      detenerPolling();
      alCambiarConexion('en_vivo');
      timerPing = setInterval(() => {
        if (Date.now() - ultimoMensaje > PONG_TIMEOUT_MS) {
          ws.close(); // el servidor no contesta: onclose reconecta
          return;
        }
        try {
          ws.send(JSON.stringify({ tipo: 'ping' }));
        } catch {
          /* onclose se encarga */
        }
      }, PING_MS);
    };

    ws.onmessage = (evento) => {
      ultimoMensaje = Date.now();
      let mensaje;
      try {
        mensaje = JSON.parse(evento.data);
      } catch {
        return; // mensaje mal formado: se ignora
      }
      if (mensaje.tipo === 'pong') return;
      alMensaje(mensaje);
    };

    ws.onclose = () => {
      clearInterval(timerPing);
      timerPing = null;
      if (detenido) return;
      iniciarPolling();
      programarReconexion();
    };

    ws.onerror = () => {
      /* el navegador llama a onclose después */
    };
  }

  conectar();

  return () => {
    detenido = true;
    clearTimeout(timerReconexion);
    clearInterval(timerPing);
    detenerPolling();
    if (ws) ws.close();
  };
}
