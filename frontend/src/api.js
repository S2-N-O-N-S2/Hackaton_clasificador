// =============================================================================
//  Capa de API: una función por endpoint del contrato (docs/api_contrato.md, sección 3).
//  Las vistas NUNCA llaman fetch directamente: todo pasa por aquí.
// =============================================================================
import { BACKEND_URL, MODO_MOCK } from './config.js';
import { ErrorApi, mensajeDeError } from './errores.js';
import * as mock from './mock/servidorMock.js';

export { ErrorApi };

async function pedir(metodo, ruta, cuerpo) {
  if (MODO_MOCK) return mock.pedir(metodo, ruta, cuerpo);

  const opciones = { method: metodo };
  if (cuerpo !== undefined) {
    opciones.headers = { 'Content-Type': 'application/json' };
    opciones.body = JSON.stringify(cuerpo);
  }
  let respuesta;
  try {
    respuesta = await fetch(BACKEND_URL + ruta, opciones);
  } catch {
    throw new ErrorApi(0, 'No se pudo conectar con el backend');
  }
  let datos = null;
  try {
    datos = await respuesta.json();
  } catch {
    datos = null;
  }
  if (!respuesta.ok) throw new ErrorApi(respuesta.status, mensajeDeError(datos, respuesta.status));
  return datos;
}

function consulta(parametros) {
  const p = new URLSearchParams();
  Object.entries(parametros).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') p.set(k, String(v));
  });
  const texto = p.toString();
  return texto ? `?${texto}` : '';
}

// Las fotos llegan como ruta relativa ("/captures/x.jpg"); el mock usa imágenes "data:".
export function urlFoto(foto) {
  if (!foto) return null;
  if (foto.startsWith('data:') || foto.startsWith('http')) return foto;
  return BACKEND_URL + foto;
}

export const api = {
  // 3.1 Estado
  estado: () => pedir('GET', '/api/estado'),

  // 3.2 Modo y menú
  modo: () => pedir('GET', '/api/modo'),
  elegirModo: (modo) => pedir('POST', '/api/modo', { modo }), // 'ia' | 'adivina' | 'menu'

  // 3.3 Clasificaciones
  clasificaciones: ({ limit = 50, offset = 0, dudosos, simulado = 'incluir' } = {}) =>
    pedir('GET', `/api/clasificaciones${consulta({ limit, offset, dudosos, simulado })}`),
  corregir: (id, finalId) => pedir('POST', `/api/clasificaciones/${id}/corregir`, { final_id: finalId }),

  // 3.4 Revisión
  resolverRevision: (finalId) => pedir('POST', '/api/revision', { accion: 'resolver', final_id: finalId }),
  dejarPendiente: () => pedir('POST', '/api/revision', { accion: 'pendiente' }),

  // 3.5 Estadísticas
  estadisticas: (simulado = 'incluir') => pedir('GET', `/api/estadisticas${consulta({ simulado })}`),

  // 3.6 Pruebas oficiales
  pruebas: () => pedir('GET', '/api/pruebas'),
  registrarPrueba: (prueba) => pedir('POST', '/api/pruebas', prueba),
  registrarResiduo: (residuo) => pedir('POST', '/api/pruebas/residuos', residuo),

  // 3.7 Modelo
  reentrenar: () => pedir('POST', '/api/modelo/reentrenar', {}),
  estadoModelo: () => pedir('GET', '/api/modelo/estado'),

  // 3.8 Configuración
  config: () => pedir('GET', '/api/config'),
  guardarConfig: (parcial) => pedir('PUT', '/api/config', parcial),

  // 3.9 Juego
  adivinar: (categoria) => pedir('POST', '/api/juego/adivinar', { categoria }),
  reportarError: () => pedir('POST', '/api/juego/reportar-error', {}),
  continuar: () => pedir('POST', '/api/juego/continuar', {}),
  sesion: () => pedir('GET', '/api/juego/sesion'),
  // Práctica con fotos del dataset (no usa la máquina)
  fotosPractica: (total) => pedir('GET', `/api/juego/fotos${consulta({ total })}`), // total se reparte entre las 3 categorías
  estadisticasJuego: (niveles) => pedir('GET', `/api/juego/estadisticas${consulta({ niveles: niveles.join(',') })}`),
  aprendizaje: (niveles) => pedir('GET', `/api/juego/aprendizaje${consulta({ niveles: niveles.join(',') })}`),
  iniciarPruebaAprendizaje: ({ alias, ronda, residuos }) =>
    pedir('POST', '/api/juego/prueba-aprendizaje', { alias, ronda, residuos }),

  // 3.10 Botes
  botes: () => pedir('GET', '/api/botes'),
  vaciarBote: (id) => pedir('POST', `/api/botes/${id}/vaciar`, {}),
  ajustarBote: (id, parcial) => pedir('PUT', `/api/botes/${id}`, parcial),

  // 3.11 Etiquetas por verificar
  porVerificar: () => pedir('GET', '/api/dataset/por-verificar'),
  decidirPorVerificar: (id, accion) => pedir('POST', '/api/dataset/por-verificar', { id, accion }),

  // 3.12 Control manual: accion = pos | ang | home | drop | light | led
  manual: (accion, cuerpo = {}) => pedir('POST', `/api/manual/${accion}`, cuerpo),

  // 3.12b Voz (contrato v1.5): push-to-talk, voz que habla y diagnóstico del micrófono
  escucharVoz: () => pedir('POST', '/api/voz/escuchar', {}),          // tarda lo que dure la grabación (~4–5 s)
  decir: (texto) => pedir('POST', '/api/voz/decir', { texto }),
  voces: () => pedir('GET', '/api/voz/voces'),
  microfonos: () => pedir('GET', '/api/voz/microfonos'),
  nivelMicrofono: () => pedir('POST', '/api/voz/nivel', {}),

  // 7. Solo en simulación
  simObjeto: (categoriaReal) =>
    pedir('POST', '/api/sim/objeto', categoriaReal === undefined ? {} : { categoria_real: categoriaReal }),
  simTecla: (tecla) => pedir('POST', '/api/sim/tecla', { tecla }),
  simRetirar: () => pedir('POST', '/api/sim/retirar', {}), // como si llegara LIBRE (contrato v1.1)
  simVoz: (texto) => pedir('POST', '/api/sim/voz', { texto }),  // como si alguien lo hubiera dicho
};
