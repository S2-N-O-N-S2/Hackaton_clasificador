// Componentes pequeños que usan varias vistas.
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
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

const sinMovimiento = () => typeof window !== 'undefined'
  && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

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

// ---- Íconos propios (SVG): cada categoría se reconoce sin depender del color ----
// Orgánica = hoja, Inorgánica = botella, Peligroso = triángulo de advertencia, Revisión = signo de pregunta.
const TRAZOS = {
  0: <><path d="M5 19c0-8.5 5.5-14 14-14 0 8.5-5.5 14-14 14Z" /><path d="M5 19 13 11" /></>,
  1: <><path d="M10 2.5h4v3.2l2 2.8V20a1.5 1.5 0 0 1-1.5 1.5h-5A1.5 1.5 0 0 1 8 20V8.5l2-2.8Z" /><path d="M8 12.5h8" /></>,
  2: <><path d="M12 3 22 20.5H2Z" /><path d="M12 9.5v5" /><path d="M12 17.6v.2" /></>,
  revision: <><circle cx="12" cy="12" r="9.5" /><path d="M9.3 9.3a2.8 2.8 0 1 1 3.9 2.6c-.8.4-1.2 1-1.2 1.9v.6" /><path d="M12 17.4v.2" /></>,
};

export function IconoCategoria({ id, tam = 18 }) {
  const trazo = TRAZOS[id];
  if (!trazo) return null;
  return (
    <svg className="icono" width={tam} height={tam} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {trazo}
    </svg>
  );
}

// ---- Categorías ----
// Placa: bloque con el color del contrato y el ícono, y el nombre en texto oscuro sobre un tinte claro
// (se lee bien aunque la persona no distinga los colores).
export function Categoria({ id, grande = false, vacio = 'Sin categoría' }) {
  const c = categoria(id);
  if (!c) return <span className={`chip ${grande ? 'chip-grande' : ''} chip-vacio`}>{vacio}</span>;
  return (
    <span className={`chip chip-cat ${grande ? 'chip-grande' : ''}`} data-cat={c.clave} style={{ '--cat': c.hex }}>
      <span className="chip-icono"><IconoCategoria id={c.id} tam={grande ? 30 : 16} /></span>
      <span className="chip-texto">{c.nombre} <small>({c.color})</small></span>
    </span>
  );
}

export function ChipRevision() {
  return (
    <span className="chip chip-cat" data-cat="revision" style={{ '--cat': REVISION.hex }}>
      <span className="chip-icono"><IconoCategoria id="revision" tam={16} /></span>
      <span className="chip-texto">Revisión</span>
    </span>
  );
}

// Botón chico de una categoría (corregir, simular, calibrar): mismo estilo que la placa.
export function BotonCategoria({ id, children, className = '', ...resto }) {
  const c = categoria(id);
  return (
    <button type="button" className={`boton-cat ${className}`} data-cat={c.clave} style={{ '--cat': c.hex }} {...resto}>
      <span className="chip-icono"><IconoCategoria id={c.id} tam={16} /></span>
      <span>{children ?? c.nombre}</span>
    </button>
  );
}

// ---- Barras ----
// El número va FUERA del relleno, para que nunca quede texto encima del color.
export function Barra({ valor, color = '#1E6FD9', marca = null, alto = 14, texto }) {
  const proporcion = Math.max(0, Math.min(1, valor || 0));
  return (
    <div className="barra-fila">
      <div className="barra" style={{ height: alto }} role="meter" aria-valuemin={0} aria-valuemax={1}
        aria-valuenow={valor ?? undefined} aria-label={texto ?? pct(valor)}>
        <div className="barra-relleno" style={{ width: `${proporcion * 100}%`, background: color }} />
        {marca !== null && <div className="barra-marca" style={{ left: `${marca * 100}%` }} title={`Umbral ${pct(marca)}`} />}
      </div>
      <span className="barra-valor">{texto ?? pct(valor)}</span>
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
            <span className="fila-prob-nombre" data-cat={c.clave}><IconoCategoria id={c.id} tam={16} /> {c.nombre}</span>
            <Barra valor={f.valor} color={c.hex} marca={umbral ?? null} />
          </div>
        );
      })}
    </div>
  );
}

const COLOR_ESTADO_BOTE = { normal: '#2E9E44', casi_lleno: '#F28C05', lleno: '#C62828' };
const TEXTO_ESTADO_BOTE = { normal: '#1E6B2E', casi_lleno: '#8A4A00', lleno: '#9B1C1C' };
const NOMBRE_ESTADO_BOTE = { normal: 'Normal', casi_lleno: 'Casi lleno', lleno: 'LLENO · bloqueado' };

export function NivelBote({ bote, compacto = false }) {
  const c = categoria(bote.categoria_id);
  return (
    <div className={`nivel-bote ${compacto ? 'compacto' : ''}`}>
      <div className="nivel-bote-titulo">
        {c && <span className="chip-icono chip-icono-suelto" style={{ '--cat': c.hex }}><IconoCategoria id={c.id} tam={15} /></span>}
        <strong>{bote.nombre}</strong>
        <span className="atenuado">({bote.color})</span>
        <Estimado />
        {bote.capacidad_calibrada === false && (
          <span className="rotulo rotulo-aviso" title="La capacidad todavía no se ha medido (especificación 13.2)">capacidad sin calibrar</span>
        )}
      </div>
      {compacto ? (
        <Barra
          valor={bote.nivel}
          color={COLOR_ESTADO_BOTE[bote.estado] || '#999'}
          marca={bote.umbral_aviso}
          alto={16}
          texto={`${pct(bote.nivel)} · ${bote.piezas_actuales}/${bote.capacidad_piezas}`}
        />
      ) : (
        // Bote dibujado: se llena con el nivel que manda el backend; la línea punteada es el umbral de aviso.
        <div className="bote-cuerpo">
          <div className="bote-figura" aria-hidden="true">
            <div className="bote-tapa" style={{ background: c ? c.hex : '#999' }} />
            <div className="bote-vaso">
              <div className="bote-relleno" style={{
                height: `${Math.max(0, Math.min(1, bote.nivel || 0)) * 100}%`,
                // Normal: color de su categoría; casi lleno / lleno: naranja / rojo.
                background: bote.estado === 'normal' && c ? c.hex : (COLOR_ESTADO_BOTE[bote.estado] || '#999'),
              }} />
              {bote.umbral_aviso !== null && bote.umbral_aviso !== undefined && (
                <div className="bote-umbral" style={{ bottom: `${bote.umbral_aviso * 100}%` }} />
              )}
            </div>
          </div>
          <div>
            <Numero valor={pct(bote.nivel)} clase="bote-cifra" />
            <div>{bote.piezas_actuales}/{bote.capacidad_piezas} piezas</div>
          </div>
        </div>
      )}
      <div className={`nivel-bote-estado estado-${bote.estado}`} style={{ color: TEXTO_ESTADO_BOTE[bote.estado] }}>
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

// `tapa`: color de la franja superior (tarjetas principales), como la tapa de un bote.
export function Tarjeta({ titulo, extra, children, className = '', tapa }) {
  return (
    <section className={`tarjeta ${tapa ? 'tarjeta-tapa' : ''} ${className}`} style={tapa ? { '--tapa': tapa } : undefined}>
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

// ---- Números ----
// Cuenta desde el valor anterior hasta el nuevo (solo dibujo: el número final es el que manda el backend).
function useContador(objetivo, duracionMs = 650) {
  const [actual, setActual] = useState(objetivo);
  const desde = useRef(objetivo);
  useEffect(() => {
    if (objetivo === null || Number.isNaN(objetivo)) { setActual(objetivo); return undefined; }
    const inicio = desde.current;
    if (inicio === null || inicio === undefined || Number.isNaN(inicio) || sinMovimiento()) {
      desde.current = objetivo; setActual(objetivo); return undefined;
    }
    let cuadro;
    const t0 = performance.now();
    const paso = (t) => {
      const k = Math.min(1, (t - t0) / duracionMs);
      const suave = 1 - (1 - k) ** 3;
      setActual(inicio + (objetivo - inicio) * suave);
      if (k < 1) cuadro = requestAnimationFrame(paso);
      else desde.current = objetivo;
    };
    cuadro = requestAnimationFrame(paso);
    return () => { cancelAnimationFrame(cuadro); desde.current = objetivo; };
  }, [objetivo, duracionMs]);
  return actual;
}

// Separa "94.1 %" en número (que cuenta) y unidad (más chica). Si no es un número, lo muestra tal cual.
export function Numero({ valor, clase = '' }) {
  const texto = valor === null || valor === undefined ? '—' : String(valor);
  const m = /^([+-]?)(\d+(?:\.\d+)?)\s*(.*)$/.exec(texto);
  const objetivo = m ? parseFloat(m[2]) : null;
  const animado = useContador(objetivo);
  if (!m) return <span className={clase}>{texto}</span>;
  const decimales = m[2].includes('.') ? m[2].split('.')[1].length : 0;
  const mostrado = (animado ?? objetivo).toFixed(decimales);
  return (
    <span className={clase}>
      {m[1]}{mostrado}{m[3] && <span className="unidad">{m[3]}</span>}
    </span>
  );
}

// `progreso` (0–1): para porcentajes, dibuja una barra delgada bajo el número.
export function Cifra({ etiqueta, valor, detalle, progreso }) {
  const p = progreso === null || progreso === undefined ? null : Math.max(0, Math.min(1, progreso));
  return (
    <div className="cifra">
      <Numero valor={valor} clase="cifra-valor" />
      {p !== null && <div className="cifra-progreso" aria-hidden="true"><div style={{ width: `${p * 100}%` }} /></div>}
      <div className="cifra-etiqueta">{etiqueta}</div>
      {detalle && <div className="cifra-detalle">{detalle}</div>}
    </div>
  );
}

export function MensajeError({ error }) {
  if (!error) return null;
  return <div className="mensaje-error" role="alert">{error}</div>;
}

// ---- Notificaciones flotantes y "procesando" ----
// Un almacén pequeño fuera de React: cualquier componente puede llamar a notificar().
let notas = [];
let pendientes = 0;
let siguienteNota = 1;
const oyentes = new Set();
const avisar = () => oyentes.forEach((f) => f());
const suscribir = (f) => { oyentes.add(f); return () => oyentes.delete(f); };

export function quitarNota(id) {
  notas = notas.filter((n) => n.id !== id);
  avisar();
}

// tipo: 'ok' | 'error' | 'aviso' | 'info'
export function notificar(texto, tipo = 'ok', ms = 3800) {
  const id = siguienteNota++;
  notas = [...notas, { id, texto, tipo }].slice(-4);
  avisar();
  setTimeout(() => quitarNota(id), ms);
}

function cambiarPendientes(delta) {
  pendientes = Math.max(0, pendientes + delta);
  avisar();
}

const ICONO_NOTA = { ok: '✓', error: '!', aviso: '!', info: 'i' };

export function Notificaciones() {
  const lista = useSyncExternalStore(suscribir, () => notas);
  return (
    <div className="notificaciones" role="status" aria-live="polite">
      {lista.map((n) => (
        <div key={n.id} className={`nota nota-${n.tipo}`}>
          <span className="nota-icono" aria-hidden="true">{ICONO_NOTA[n.tipo] || 'i'}</span>
          <span className="nota-texto">{n.texto}</span>
          <button type="button" className="nota-cerrar" aria-label="Cerrar notificación" onClick={() => quitarNota(n.id)}>✕</button>
        </div>
      ))}
    </div>
  );
}

// Línea animada bajo el encabezado mientras alguna acción espera al backend.
export function BarraProceso() {
  const n = useSyncExternalStore(suscribir, () => pendientes);
  return <div className={`barra-proceso ${n > 0 ? 'activa' : ''}`} aria-hidden="true" />;
}

// Ejecuta una acción de la API mostrando "ocupado" y el error en español.
// opciones.ok: texto (o función del resultado) para la notificación de éxito.
export function useAccion() {
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState(null);
  const ejecutar = useCallback(async (fn, opciones = {}) => {
    setOcupado(true);
    setError(null);
    cambiarPendientes(1);
    try {
      const r = await fn();
      const ok = typeof opciones.ok === 'function' ? opciones.ok(r) : opciones.ok;
      if (ok) notificar(ok, 'ok');
      return r;
    } catch (e) {
      const texto = e.message || 'Error inesperado';
      setError(texto);
      if (opciones.ok) notificar(texto, 'error', 5000);
      return undefined;
    } finally {
      cambiarPendientes(-1);
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

// Espera mientras llegan los datos: bloques grises que "respiran" en lugar de un texto suelto.
export function Cargando({ filas = 3 }) {
  return (
    <div className="cargando" role="status" aria-label="Cargando">
      {Array.from({ length: filas }, (_, i) => <div key={i} className="cargando-linea" style={{ width: `${90 - i * 18}%` }} />)}
    </div>
  );
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
  sin_modelo: 'No hay modelo cargado: el sistema no adivina',
};

// Estado de una clasificación (contrato v1.1). "registrado" no se rotula.
export const TEXTO_ESTADO_CLASIFICACION = {
  en_proceso: 'en proceso',
  pendiente: 'pendiente',
  error: 'error',
};

// Las tres categorías como botones grandes, con ícono y número de tecla.
export function BotonesCategoria({ alElegir, deshabilitado, prefijo = '' }) {
  return (
    <div className="botones-categoria">
      {[0, 1, 2].map((id) => {
        const c = categoria(id);
        return (
          <button key={id} type="button" className="boton-categoria" style={{ background: c.hex }} data-cat={c.clave}
            disabled={deshabilitado} onClick={() => alElegir(id)}>
            <IconoCategoria id={id} tam={40} />
            <span className="boton-categoria-nombre">{prefijo}{id + 1} · {c.nombre}</span>
            <small>bote {c.color}</small>
          </button>
        );
      })}
    </div>
  );
}
