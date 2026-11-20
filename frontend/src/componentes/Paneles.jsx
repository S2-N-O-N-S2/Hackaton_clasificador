// Piezas para las vistas de datos: pestañas, explicación desplegable, duelo, anillo y control segmentado.
// Solo muestran lo que ya calculó el backend.
import { useId, useRef, useState } from 'react';
import { Numero, pct } from './Comun.jsx';

// Pestañas accesibles (flechas izquierda/derecha para moverse).
export function Pestanas({ pestanas, inicial }) {
  const [activa, setActiva] = useState(inicial ?? pestanas[0]?.id);
  const base = useId();
  const refs = useRef({});
  const actual = pestanas.find((p) => p.id === activa) || pestanas[0];
  const mover = (e, i) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    e.preventDefault();
    const siguiente = pestanas[(i + (e.key === 'ArrowRight' ? 1 : pestanas.length - 1)) % pestanas.length];
    setActiva(siguiente.id);
    refs.current[siguiente.id]?.focus();
  };
  return (
    <div className="pestanas">
      <div className="pestanas-lista" role="tablist">
        {pestanas.map((p, i) => (
          <button key={p.id} ref={(el) => { refs.current[p.id] = el; }} type="button" role="tab" id={`${base}-${p.id}`}
            aria-selected={p.id === actual.id} aria-controls={`${base}-panel`} tabIndex={p.id === actual.id ? 0 : -1}
            onClick={() => setActiva(p.id)} onKeyDown={(e) => mover(e, i)}>
            {p.titulo}
            {p.contador !== undefined && <span className="pestana-contador">{p.contador}</span>}
          </button>
        ))}
      </div>
      <div className="pestanas-panel" role="tabpanel" id={`${base}-panel`} aria-labelledby={`${base}-${actual.id}`} key={actual.id}>
        {actual.contenido}
      </div>
    </div>
  );
}

// "¿Qué significa?": explicación corta que se abre al tocarla.
export function Explicacion({ children, titulo = '¿Qué significa?' }) {
  return (
    <details className="explicacion">
      <summary>{titulo}</summary>
      <div>{children}</div>
    </details>
  );
}

// Anillo de porcentaje (valor 0–1). Se dibuja al aparecer.
export function Anillo({ valor, color = 'var(--maquina)', tam = 150, texto, detalle }) {
  const r = 52;
  const largo = 2 * Math.PI * r;
  const v = valor === null || valor === undefined ? null : Math.max(0, Math.min(1, valor));
  return (
    <div className="anillo" style={{ width: tam }}>
      <svg viewBox="0 0 120 120" role="img" aria-label={`${texto ?? pct(v)}${detalle ? `, ${detalle}` : ''}`}>
        <circle cx="60" cy="60" r={r} className="anillo-fondo" />
        {v !== null && (
          <circle cx="60" cy="60" r={r} className="anillo-valor" stroke={color}
            style={{ '--largo': largo, '--fin': largo * (1 - v) }} strokeDasharray={largo} strokeDashoffset={largo * (1 - v)} />
        )}
      </svg>
      <div className="anillo-centro">
        <Numero valor={texto ?? (v === null ? '—' : `${Math.round(v * 100)} %`)} clase="anillo-cifra" />
        {detalle && <small>{detalle}</small>}
      </div>
    </div>
  );
}

// Duelo de dos lados (Humano vs. IA, Manual vs. Sistema). Marca al ganador solo si hay datos de ambos.
export function Duelo({ izquierda, derecha, pie }) {
  const ambos = izquierda.valor !== null && izquierda.valor !== undefined && derecha.valor !== null && derecha.valor !== undefined;
  const gana = !ambos ? null : izquierda.valor > derecha.valor ? 'izq' : derecha.valor > izquierda.valor ? 'der' : 'empate';
  const lado = (l, id) => (
    <div className={`duelo-lado ${gana === id ? 'gana' : ''}`}>
      <span className="duelo-nombre">{l.nombre}</span>
      <Anillo valor={l.valor} color={l.color} tam={140} detalle={l.detalle} />
      {gana === id && <span className="duelo-insignia">Gana</span>}
    </div>
  );
  return (
    <section className="duelo">
      {lado(izquierda, 'izq')}
      <div className="duelo-vs" aria-hidden="true">vs</div>
      {lado(derecha, 'der')}
      <p className="duelo-pie">
        {gana === 'empate' ? 'Empate.' : gana ? `${gana === 'izq' ? izquierda.nombre : derecha.nombre} acierta ${Math.abs(Math.round((izquierda.valor - derecha.valor) * 100))} puntos más.` : 'Todavía no hay datos suficientes de ambos lados.'}
        {pie && <> {pie}</>}
      </p>
    </section>
  );
}

// Control segmentado (una opción) o de casillas (varias, con `multiple`).
export function Segmentado({ etiqueta, opciones, valor, alCambiar, multiple = false }) {
  const elegido = (clave) => (multiple ? valor.includes(clave) : valor === clave);
  const tocar = (clave) => {
    if (!multiple) return alCambiar(clave);
    const nuevos = valor.includes(clave) ? valor.filter((v) => v !== clave) : [...valor, clave];
    if (nuevos.length) alCambiar(nuevos);
    return undefined;
  };
  return (
    <div className="segmentado" role="group" aria-label={etiqueta}>
      <span className="segmentado-etiqueta">{etiqueta}</span>
      <div className="segmentado-opciones">
        {opciones.map((o) => (
          <button key={o.clave} type="button" aria-pressed={elegido(o.clave)} onClick={() => tocar(o.clave)} title={o.ayuda}>
            {o.nombre}
          </button>
        ))}
      </div>
    </div>
  );
}

// Filtro de niveles de certeza (Humano vs. IA y Aprendizaje).
export function FiltroNiveles({ niveles, alCambiar }) {
  return (
    <Segmentado etiqueta="Certeza" multiple valor={niveles} alCambiar={alCambiar} opciones={[
      { clave: 'verificada', nombre: 'Verificada', ayuda: 'La respuesta correcta la confirmó una etiqueta real o un operador' },
      { clave: 'alta', nombre: 'Alta', ayuda: 'La IA estaba muy segura' },
      { clave: 'media', nombre: 'Media', ayuda: 'Se reporta aparte: la IA no estaba tan segura' },
    ]} />
  );
}
