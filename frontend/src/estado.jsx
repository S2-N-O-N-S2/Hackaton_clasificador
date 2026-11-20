// =============================================================================
//  Estado global del panel. UNA sola fuente de verdad: lo que manda el backend.
//  Cada mensaje del WebSocket (contrato, sección 4) actualiza este estado; el panel
//  no calcula reglas, niveles de certeza ni estadísticas (contrato, sección 6).
// =============================================================================
import { createContext, useContext, useEffect, useReducer, useState } from 'react';
import { conectarEventos } from './ws.js';
import { api } from './api.js';
import { MAX_ALERTAS } from './config.js';

const Contexto = createContext(null);

const inicial = {
  conexion: 'conectando',   // 'conectando' | 'en_vivo' | 'polling' | 'sin_backend'
  maquina: null,            // la última foto de GET /api/estado, actualizada con cada evento
  cuenta: null,             // {valor, recibido}: para mostrar la cuenta regresiva
  captura: null,            // último evento "captura"
  ultimaClasificacion: null,
  revision: null,           // evento "revision" mientras el estado es REVISION
  retro: null,              // última Retroalimentacion
  botes: null,              // lista de Bote
  sesion: null,
  modelo: null,
  alertas: [],
  ultimaTecla: null,
  voz: null,                // último evento "voz": {fase: escuchando | reconocido | error, …, recibido}
  versiones: { historial: 0 }, // cambia cuando hay que recargar el historial y las estadísticas
};

function conCuenta(estado, valor) {
  return { ...estado, cuenta: valor === null || valor === undefined ? null : { valor, recibido: Date.now() } };
}

function reductor(estado, accion) {
  if (accion.tipo === 'conexion') return { ...estado, conexion: accion.valor };
  if (accion.tipo === 'botes') return { ...estado, botes: accion.valor };
  if (accion.tipo === 'sesion') return { ...estado, sesion: accion.valor };
  if (accion.tipo === 'modelo') return { ...estado, modelo: accion.valor };
  if (accion.tipo !== 'mensaje') return estado;

  const { tipo, datos, ts } = accion.mensaje;
  switch (tipo) {
    case 'hola': {
      const nuevo = { ...estado, maquina: datos, alertas: datos.alertas || estado.alertas };
      const cambio = !estado.maquina || estado.maquina.estado !== datos.estado;
      return cambio ? conCuenta(nuevo, datos.cuenta_regresiva_s) : nuevo;
    }
    case 'estado': {
      const maquina = { ...(estado.maquina || {}), ...datos, estado_desde: ts };
      delete maquina.anterior;
      let nuevo = { ...estado, maquina };
      if (datos.estado !== 'REVISION') nuevo.revision = null;
      return conCuenta(nuevo, datos.cuenta_regresiva_s);
    }
    case 'captura':
      return { ...estado, captura: datos, retro: null };
    case 'clasificacion':
      return { ...estado, ultimaClasificacion: datos };
    case 'revision':
      return { ...estado, revision: datos };
    case 'registrado':
      return {
        ...estado,
        ultimaClasificacion: datos,
        versiones: { ...estado.versiones, historial: estado.versiones.historial + 1 },
      };
    case 'retroalimentacion':
      return { ...estado, retro: datos };
    case 'bote': {
      const botes = (estado.botes || []).map((b) => (b.id === datos.id ? datos : b));
      if (!botes.some((b) => b.id === datos.id)) botes.push(datos);
      return { ...estado, botes };
    }
    case 'modo':
      return { ...estado, maquina: { ...(estado.maquina || {}), modo: datos.modo } };
    case 'sesion':
      return { ...estado, sesion: datos };
    case 'modelo':
      return { ...estado, modelo: datos };
    case 'alerta':
      return { ...estado, alertas: [datos, ...estado.alertas].slice(0, MAX_ALERTAS) };
    case 'voz':
      return { ...estado, voz: { ...datos, recibido: Date.now() } };
    case 'tecla':
      return { ...estado, ultimaTecla: { tecla: datos.tecla, recibido: Date.now() } };
    default:
      return estado; // tipo desconocido: se ignora
  }
}

export function ProveedorEstado({ children }) {
  const [estado, despachar] = useReducer(reductor, inicial);

  useEffect(() => {
    const cerrar = conectarEventos({
      alMensaje: (mensaje) => despachar({ tipo: 'mensaje', mensaje }),
      alCambiarConexion: (valor) => despachar({ tipo: 'conexion', valor }),
    });
    return cerrar;
  }, []);

  // Datos que el WebSocket solo manda cuando cambian: se piden una vez al conectar.
  useEffect(() => {
    if (estado.conexion !== 'en_vivo' && estado.conexion !== 'polling') return;
    api.botes().then((r) => despachar({ tipo: 'botes', valor: r.botes })).catch(() => {});
    api.sesion().then((r) => despachar({ tipo: 'sesion', valor: r })).catch(() => {});
    api.estadoModelo().then((r) => despachar({ tipo: 'modelo', valor: r })).catch(() => {});
  }, [estado.conexion]);

  return <Contexto.Provider value={estado}>{children}</Contexto.Provider>;
}

export function useEnVivo() {
  return useContext(Contexto);
}

// Segundos que faltan de la cuenta regresiva que mandó el backend (solo para mostrar).
export function useCuentaRegresiva() {
  const { cuenta } = useEnVivo();
  const [, setTic] = useState(0);
  useEffect(() => {
    if (!cuenta) return undefined;
    const t = setInterval(() => setTic((x) => x + 1), 250);
    return () => clearInterval(t);
  }, [cuenta]);
  if (!cuenta) return null;
  return Math.max(0, Math.ceil(cuenta.valor - (Date.now() - cuenta.recibido) / 1000));
}
