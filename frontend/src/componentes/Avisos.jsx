// Avisos del panel sin amontonar barras:
//  - BarraUrgente: UNA sola barra, solo cuando la máquina espera que alguien actúe (falla, bote lleno, revisión).
//  - Campana: el resto de las alertas que manda el backend, en una lista que se abre al tocarla.
//  - Cada alerta nueva aparece unos segundos como notificación flotante.
// Las alertas vienen tal cual del backend; aquí solo se decide cómo mostrarlas.
import { useEffect, useRef, useState } from 'react';
import { useEnVivo } from '../estado.jsx';
import { hora, notificar } from './Comun.jsx';

const clave = (a) => `${a.fecha_hora}|${a.codigo}`;

export function BarraUrgente({ ruta }) {
  const { maquina } = useEnVivo();
  const estado = maquina?.estado;
  let aviso = null;
  if (estado === 'ERROR') {
    aviso = { tipo: 'error', texto: `Falla segura: trampilla cerrada y disco en HOME. ${maquina.mensaje || ''}`, accion: null };
  } else if (estado === 'BOTE_LLENO' && ruta !== 'botes') {
    aviso = { tipo: 'error', texto: 'Un bote está lleno (ESTIMADO): el residuo espera en la bandeja.', accion: { texto: 'Ir a Botes', href: '#/botes' } };
  } else if (estado === 'REVISION' && ruta !== 'en-vivo' && ruta !== 'juego') {
    aviso = { tipo: 'revision', texto: 'La IA no está segura: hay un residuo en revisión.', accion: { texto: 'Resolver', href: '#/en-vivo' } };
  }
  if (!aviso) return null;
  return (
    <div className={`barra-urgente urgente-${aviso.tipo}`} role="alert">
      <span className="barra-urgente-texto">{aviso.texto}</span>
      {aviso.accion && <a className="barra-urgente-accion" href={aviso.accion.href}>{aviso.accion.texto}</a>}
    </div>
  );
}

const NIVEL = { error: 'Error', aviso: 'Aviso', info: 'Info' };

export function Campana() {
  const { alertas } = useEnVivo();
  const [abierta, setAbierta] = useState(false);
  const [descartadas, setDescartadas] = useState(() => new Set());
  const [vistas, setVistas] = useState(() => new Set());
  const conocidas = useRef(null);
  const caja = useRef(null);

  const lista = alertas.filter((a) => !descartadas.has(clave(a)));
  const sinLeer = lista.filter((a) => !vistas.has(clave(a))).length;

  // Las alertas que llegan después de abrir el panel se anuncian como notificación flotante.
  // Las que ya existían al conectar (llegan en "hola", en los primeros segundos) no se anuncian.
  const montado = useRef(Date.now());
  useEffect(() => {
    if (conocidas.current === null) conocidas.current = new Set();
    const alConectar = Date.now() - montado.current < 3000;
    alertas.forEach((a) => {
      const k = clave(a);
      if (conocidas.current.has(k)) return;
      conocidas.current.add(k);
      if (alConectar) return;
      notificar(a.mensaje, a.nivel === 'error' ? 'error' : a.nivel === 'aviso' ? 'aviso' : 'info', 5000);
    });
  }, [alertas]);

  // Cerrar con Escape o al tocar fuera.
  useEffect(() => {
    if (!abierta) return undefined;
    const fuera = (e) => { if (caja.current && !caja.current.contains(e.target)) setAbierta(false); };
    const tecla = (e) => { if (e.key === 'Escape') setAbierta(false); };
    document.addEventListener('pointerdown', fuera);
    document.addEventListener('keydown', tecla);
    return () => { document.removeEventListener('pointerdown', fuera); document.removeEventListener('keydown', tecla); };
  }, [abierta]);

  function alternar() {
    if (!abierta) setVistas(new Set(lista.map(clave)));
    setAbierta((x) => !x);
  }

  return (
    <div className="campana" ref={caja}>
      <button type="button" className={`campana-boton ${sinLeer ? 'con-nuevas' : ''}`} onClick={alternar}
        aria-expanded={abierta} aria-label={`Avisos: ${lista.length}${sinLeer ? `, ${sinLeer} sin leer` : ''}`}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M6 9a6 6 0 0 1 12 0c0 6 2.5 7.5 2.5 7.5h-17S6 15 6 9Z" /><path d="M10 20a2 2 0 0 0 4 0" />
        </svg>
        {sinLeer > 0 && <span className="campana-contador">{sinLeer > 9 ? '9+' : sinLeer}</span>}
      </button>
      {abierta && (
        <div className="campana-panel" role="dialog" aria-label="Avisos">
          <div className="campana-encabezado">
            <strong>Avisos</strong>
            {lista.length > 0 && (
              <button type="button" className="boton-texto" onClick={() => setDescartadas(new Set([...descartadas, ...lista.map(clave)]))}>
                Descartar todos
              </button>
            )}
          </div>
          {lista.length === 0 ? (
            <p className="campana-vacia">No hay avisos.</p>
          ) : (
            <ul className="campana-lista">
              {lista.map((a) => (
                <li key={clave(a)} className={`campana-item item-${a.nivel}`}>
                  <span className="campana-nivel">{NIVEL[a.nivel] || a.nivel}</span>
                  <span className="campana-mensaje">{a.mensaje}</span>
                  <span className="campana-hora">{hora(a.fecha_hora)}</span>
                  <button type="button" className="campana-quitar" aria-label="Descartar aviso"
                    onClick={() => setDescartadas(new Set(descartadas).add(clave(a)))}>✕</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
