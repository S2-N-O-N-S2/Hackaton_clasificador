// Componentes pequeños que usan varias vistas.
import { useCallback, useEffect, useState } from 'react';
import { categoria, REVISION } from '../categorias.js';
import { urlFoto } from '../api.js';

// ---- Formatos ----
export function pct(x, decimales = 0) {
  if (x === null || x === undefined) return '—';
  return `${(x * 100).toFixed(decimales)} %`;
}

export function hora(iso) {
  if (!iso) return '—';
  const t = iso.split('T')[1];
  return t ? t.slice(0, 8) : iso;
}

export function fechaHora(iso) {
  if (!iso) return '—';
  return iso.replace('T', ' ').slice(0, 19);
}

// ---- Etiquetas de honestidad ----
export function Simulado({ si = true }) {
  if (!si) return null;
  return <span className="rotulo rotulo-simulado" title="Dato generado en simulación, no es una medición real">SIMULADO</span>;
}

export function Estimado() {
  return <span className="rotulo rotulo-estimado" title="Se estima contando piezas; no hay sensor de nivel">ESTIMADO</span>;
}

export function MuestraPequena({ si }) {
  if (!si) return null;
  return <span className="rotulo rotulo-aviso">muestra pequeña: resultado indicativo</span>;
}

// ---- Categorías ----
export function Categoria({ id, grande = false, vacio = 'Sin categoría' }) {
  const c = categoria(id);
  if (!c) return <span className={`chip ${grande ? 'chip-grande' : ''} chip-vacio`}>{vacio}</span>;
  return (
    <span className={`chip ${grande ? 'chip-grande' : ''}`} style={{ background: c.hex }}>
      {c.nombre} <small>({c.color})</small>
    </span>
  );
}

export function ChipRevision() {
  return <span className="chip" style={{ background: REVISION.hex, color: '#1f2937' }}>Revisión</span>;
}

// ---- Barras ----
export function Barra({ valor, color = '#1E6FD9', marca = null, alto = 22, texto }) {
  const ancho = Math.max(0, Math.min(1, valor || 0)) * 100;
  return (
    <div className="barra" style={{ height: alto }}>
      <div className="barra-relleno" style={{ width: `${ancho}%`, background: color }} />
      {marca !== null && <div className="barra-marca" style={{ left: `${marca * 100}%` }} title={`Umbral ${pct(marca)}`} />}
      <span className="barra-texto">{texto ?? pct(valor)}</span>
    </div>
  );
}

// Las 3 probabilidades que manda el backend, con el umbral vigente marcado.
export function Probabilidades({ probabilidades, umbralGeneral, umbralPeligroso }) {
  if (!probabilidades) return null;
  const filas = [
    { id: 0, valor: probabilidades.organica },
    { id: 1, valor: probabilidades.inorganica },
    { id: 2, valor: probabilidades.peligroso },
  ];
  return (
    <div className="probabilidades">
      {filas.map((f) => {
        const c = categoria(f.id);
        const umbral = f.id === 2 ? umbralPeligroso : umbralGeneral;
        return (
          <div key={f.id} className="fila-prob">
            <span className="fila-prob-nombre">{c.nombre}</span>
            <Barra valor={f.valor} color={c.hex} marca={umbral ?? null} />
          </div>
        );
      })}
    </div>
  );
}

const COLOR_ESTADO_BOTE = { normal: '#2E9E44', casi_lleno: '#F28C05', lleno: '#C62828' };
const NOMBRE_ESTADO_BOTE = { normal: 'Normal', casi_lleno: 'Casi lleno', lleno: 'LLENO · bloqueado' };

export function NivelBote({ bote, compacto = false }) {
  const c = categoria(bote.categoria_id);
  return (
    <div className={`nivel-bote ${compacto ? 'compacto' : ''}`}>
      <div className="nivel-bote-titulo">
        <span className="punto" style={{ background: c ? c.hex : '#999' }} />
        <strong>{bote.nombre}</strong>
        <span className="atenuado">({bote.color})</span>
        <Estimado />
      </div>
      <Barra
        valor={bote.nivel}
        color={COLOR_ESTADO_BOTE[bote.estado] || '#999'}
        marca={bote.umbral_aviso}
        alto={compacto ? 22 : 30}
        texto={`${pct(bote.nivel)} · ${bote.piezas_actuales}/${bote.capacidad_piezas} piezas`}
      />
      <div className="nivel-bote-estado" style={{ color: COLOR_ESTADO_BOTE[bote.estado] }}>
        {NOMBRE_ESTADO_BOTE[bote.estado] || bote.estado}
        {bote.no_confirmadas > 0 && <span className="atenuado"> · {bote.no_confirmadas} sin confirmar</span>}
      </div>
    </div>
  );
}

export function Foto({ foto, simulado, alt = 'Foto capturada' }) {
  const url = urlFoto(foto);
  return (
    <div className="foto">
      {url ? <img src={url} alt={alt} /> : <div className="foto-vacia">Sin foto todavía</div>}
      {simulado && <div className="foto-rotulo"><Simulado /></div>}
    </div>
  );
}

export function Tarjeta({ titulo, extra, children, className = '' }) {
  return (
    <section className={`tarjeta ${className}`}>
      {(titulo || extra) && (
        <header className="tarjeta-titulo">
          <h2>{titulo}</h2>
          {extra && <div className="tarjeta-extra">{extra}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function Cifra({ etiqueta, valor, detalle }) {
  return (
    <div className="cifra">
      <div className="cifra-valor">{valor}</div>
      <div className="cifra-etiqueta">{etiqueta}</div>
      {detalle && <div className="cifra-detalle">{detalle}</div>}
    </div>
  );
}

export function MensajeError({ error }) {
  if (!error) return null;
  return <div className="mensaje-error" role="alert">{error}</div>;
}

// Ejecuta una acción de la API mostrando "ocupado" y el error en español.
export function useAccion() {
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState(null);
  const ejecutar = useCallback(async (fn) => {
    setOcupado(true);
    setError(null);
    try {
      return await fn();
    } catch (e) {
      setError(e.message || 'Error inesperado');
      return undefined;
    } finally {
      setOcupado(false);
    }
  }, []);
  return { ejecutar, ocupado, error, setError };
}

// Carga datos con la API y los vuelve a pedir cuando cambian las dependencias.
export function useDatos(cargar, dependencias) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [recarga, setRecarga] = useState(0);
  useEffect(() => {
    let vigente = true;
    setCargando(true);
    cargar()
      .then((d) => { if (vigente) { setDatos(d); setError(null); } })
      .catch((e) => { if (vigente) setError(e.message); })
      .finally(() => { if (vigente) setCargando(false); });
    return () => { vigente = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dependencias, recarga]);
  return { datos, error, cargando, recargar: () => setRecarga((x) => x + 1) };
}

// Espejo de la LCD 20×4 del Arduino (las líneas las genera el backend).
export function Lcd({ lineas }) {
  const filas = [0, 1, 2, 3].map((i) => ((lineas && lineas[i]) || '').padEnd(20, ' ').slice(0, 20));
  return (
    <pre className="lcd" aria-label="Pantalla LCD">
      {filas.join('\n')}
    </pre>
  );
}

export const TEXTO_MOTIVO = {
  confianza_baja: 'La confianza es menor que el umbral',
  riesgo_peligroso: 'Podría ser peligroso: no se arriesga',
  conflicto_voz: 'La voz y la cámara no coinciden',
};

// Las tres categorías como botones grandes.
export function BotonesCategoria({ alElegir, deshabilitado, prefijo = '' }) {
  return (
    <div className="botones-categoria">
      {[0, 1, 2].map((id) => {
        const c = categoria(id);
        return (
          <button key={id} type="button" className="boton-categoria" style={{ background: c.hex }}
            disabled={deshabilitado} onClick={() => alElegir(id)}>
            {prefijo}{id + 1} · {c.nombre}
            <small>bote {c.color}</small>
          </button>
        );
      })}
    </div>
  );
}
