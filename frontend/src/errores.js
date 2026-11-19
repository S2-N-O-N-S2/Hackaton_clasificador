// Error de la API con el código HTTP (0 = no hubo conexión).
export class ErrorApi extends Error {
  constructor(status, mensaje) {
    super(mensaje);
    this.status = status;
  }
}

// FastAPI responde {"detail": "texto"} o, en 422, {"detail": [{msg, loc}, …]}.
export function mensajeDeError(datos, status) {
  const detalle = datos && datos.detail;
  if (typeof detalle === 'string') return detalle;
  if (Array.isArray(detalle) && detalle.length) {
    return detalle.map((d) => d.msg || JSON.stringify(d)).join('; ');
  }
  const porCodigo = {
    400: 'Dato inválido',
    404: 'No existe',
    409: 'Acción no permitida en el estado actual',
    422: 'Valor fuera de rango',
    501: 'Todavía no está implementado en el backend',
    503: 'Hardware no disponible',
  };
  return porCodigo[status] || `Error ${status}`;
}
