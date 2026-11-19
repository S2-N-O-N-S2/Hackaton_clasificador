// Catálogo fijo de categorías (contrato, sección 1.1). Solo sirve para mostrar nombres y colores.
export const CATEGORIAS = [
  { id: 0, clave: 'organica', nombre: 'Orgánica', color: 'verde', hex: '#2E9E44' },
  { id: 1, clave: 'inorganica', nombre: 'Inorgánica', color: 'azul', hex: '#1E6FD9' },
  { id: 2, clave: 'peligroso', nombre: 'Peligroso', color: 'gris', hex: '#6B7280' },
];

export const REVISION = { clave: 'revision', nombre: 'Revisión', color: 'amarillo', hex: '#F2B705' };

export function categoria(id) {
  if (id === null || id === undefined) return null;
  return CATEGORIAS.find((c) => c.id === Number(id)) || null;
}

export const NOMBRE_ESTADO = {
  MENU: 'Menú',
  ESPERA_OBJETO: 'Esperando residuo',
  CAPTURA: 'Captura',
  CLASIFICACION: 'Clasificación',
  ESPERA_ADIVINANZA: 'Esperando adivinanza',
  RETROALIMENTACION: 'Retroalimentación',
  REVISION: 'Revisión',
  VERIFICAR_BOTE: 'Verificando bote',
  BOTE_LLENO: 'Bote lleno',
  POSICIONAR: 'Posicionando disco',
  SOLTAR: 'Soltando',
  REGISTRAR: 'Registrando',
  ACTUALIZAR_NIVEL: 'Actualizando nivel',
  HOME: 'Regresando a HOME',
  PENDIENTE: 'Revisión pendiente',
  OPERADOR: 'Menú de operador',
  ERROR: 'Falla segura',
};

export const NOMBRE_ORIGEN = {
  camara: 'Cámara', voz: 'Voz', manual: 'Manual', teclado: 'Teclado', panel: 'Panel',
};
