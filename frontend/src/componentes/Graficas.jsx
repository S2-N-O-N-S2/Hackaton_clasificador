// Gráficas hechas con CSS y SVG propios (sin bibliotecas).
import { useEffect, useRef, useState } from 'react';
import { CATEGORIAS, categoria } from '../categorias.js';
import { Barra, IconoCategoria, pct } from './Comun.jsx';

// ---- Carrusel (dibujo) ----
// Disco con los 3 botes; la trampilla está arriba. Solo es una ilustración: gira para dejar bajo la trampilla
// el bote de la categoría que mandó el backend (cada bote ocupa 120°). Sin categoría queda entre dos botes (HOME).
const punto = (r, grados) => {
  const a = (grados * Math.PI) / 180;
  return [r * Math.sin(a), -r * Math.cos(a)];
};
function rutaSector(centro, R = 92, r = 34, medio = 58) {
  const [x1, y1] = punto(R, centro - medio);
  const [x2, y2] = punto(R, centro + medio);
  const [x3, y3] = punto(r, centro + medio);
  const [x4, y4] = punto(r, centro - medio);
  return `M${x1} ${y1} A${R} ${R} 0 0 1 ${x2} ${y2} L${x3} ${y3} A${r} ${r} 0 0 0 ${x4} ${y4} Z`;
}

// `residuo`: 'ninguno' | 'en_bandeja' | 'cayendo'. Lo decide la vista a partir del estado que manda el backend.
export function Carrusel({ categoriaId, residuo = 'ninguno', pie }) {
  const id = categoriaId === null || categoriaId === undefined ? null : Number(categoriaId);
  const destino = id === null ? -60 : -id * 120;
  // Gira por el camino más corto desde donde quedó la vez anterior.
  const giro = useRef(destino);
  const delta = ((((destino - giro.current) % 360) + 540) % 360) - 180;
  giro.current += delta;
  const rot = giro.current;
  // SOLTAR puede durar menos que la animación: la caída se mantiene visible al menos 0.9 s (solo dibujo).
  const [caidaVisible, setCaidaVisible] = useState(false);
  const temporizador = useRef(null);
  useEffect(() => {
    if (residuo !== 'cayendo') return;
    setCaidaVisible(true);
    clearTimeout(temporizador.current);
    temporizador.current = setTimeout(() => setCaidaVisible(false), 900);
  }, [residuo]);
  useEffect(() => () => clearTimeout(temporizador.current), []);
  const cayendo = residuo === 'cayendo' || caidaVisible;
  return (
    <figure className="carrusel">
      <svg viewBox="-110 -130 220 240" role="img"
        aria-label={id === null ? 'Carrusel en HOME' : `Carrusel: bote ${categoria(id)?.nombre} bajo la trampilla`}>
        {/* Disco: arranca y frena suave, como la rampa del servo en el firmware. */}
        <g className="carrusel-disco" style={{ transform: `rotate(${rot}deg)` }}>
          {CATEGORIAS.map((c) => {
            const [tx, ty] = punto(80, c.id * 120);
            const apagado = id !== null && id !== c.id;
            return (
              <g key={c.id}>
                <path d={rutaSector(c.id * 120)} fill={c.hex}
                  className={`carrusel-sector ${apagado ? 'apagado' : ''} ${cayendo && id === c.id ? 'impacto' : ''}`} />
                <text x={tx} y={ty + 4} textAnchor="middle" className={`carrusel-texto carrusel-etiqueta ${apagado ? 'apagado' : ''}`}
                  style={{ transform: `rotate(${-rot}deg)` }}>{c.nombre}</text>
              </g>
            );
          })}
        </g>
        <circle r="30" className="carrusel-centro" />
        <text y="4" textAnchor="middle" className="carrusel-centro-texto">{id === null ? 'HOME' : 'bote'}</text>

        {/* Bandeja con trampilla de dos hojas (vista desde arriba), fija sobre el disco. */}
        <g className={`carrusel-bandeja ${cayendo ? 'abierta' : ''}`}>
          <rect x="-15" y="-70" width="30" height="30" rx="3" className="bandeja-hueco" />
          <rect x="-15" y="-70" width="15" height="30" className="bandeja-hoja hoja-izq" />
          <rect x="0" y="-70" width="15" height="30" className="bandeja-hoja hoja-der" />
          {(residuo !== 'ninguno' || cayendo) && (
            <rect x="-7" y="-62" width="14" height="14" rx="4" className={`bandeja-residuo ${cayendo ? 'cayendo' : ''}`} />
          )}
        </g>
        <polygon points="0,-94 -11,-112 11,-112" className="carrusel-trampilla" />
        <text y="-118" textAnchor="middle" className="carrusel-trampilla-texto">trampilla</text>
      </svg>
      {pie && <figcaption>{pie}</figcaption>}
    </figure>
  );
}

// Logotipo: el mismo disco, pequeño y quieto.
export function Logotipo() {
  return (
    <svg className="marca-logo" viewBox="-100 -100 200 200" aria-hidden="true">
      {CATEGORIAS.map((c) => <path key={c.id} d={rutaSector(c.id * 120, 96, 30, 56)} fill={c.hex} />)}
      <circle r="18" fill="#FFFFFF" />
    </svg>
  );
}

// Matriz de confusión: filas = categoría real, columnas = predicha (o adivinanza).
// Cada celda muestra el conteo y el % de su fila; los aciertos llevan ✓ (no depende solo del color).
function EncabezadoMatriz({ e }) {
  const c = categoria(e);
  return <span className="matriz-cat" data-cat={c?.clave}><IconoCategoria id={c?.id} tam={15} /> {c?.nombre}</span>;
}

export function MatrizConfusion({ matriz, titulo = 'Matriz de confusión', columnas = 'Predicha' }) {
  if (!matriz || !matriz.valores) return <p className="atenuado">Sin datos.</p>;
  const { etiquetas, valores } = matriz;
  const maximo = Math.max(1, ...valores.flat());
  return (
    <div className="matriz-contenedor">
      <table className="matriz" aria-label={titulo}>
        <thead>
          <tr>
            <th className="matriz-esquina">Real ↓<br />{columnas} →</th>
            {etiquetas.map((e) => <th key={e} scope="col"><EncabezadoMatriz e={e} /></th>)}
          </tr>
        </thead>
        <tbody>
          {valores.map((fila, i) => {
            const total = fila.reduce((a, b) => a + b, 0);
            return (
              <tr key={etiquetas[i]}>
                <th scope="row"><EncabezadoMatriz e={etiquetas[i]} /></th>
                {fila.map((v, j) => {
                  const diagonal = i === j;
                  const alfa = v ? 0.14 + (v / maximo) * 0.76 : 0;
                  const fondo = diagonal ? `rgba(30, 107, 46, ${alfa})` : `rgba(176, 32, 32, ${alfa})`;
                  const porcentaje = total ? Math.round((v / total) * 100) : null;
                  return (
                    <td key={j} style={{ background: fondo }}
                      className={`${diagonal ? 'diagonal' : ''} ${alfa > 0.7 ? 'texto-claro' : ''}`}
                      title={`${v} de ${total}${porcentaje !== null ? ` (${porcentaje} %)` : ''}`}>
                      <span className="matriz-n">{diagonal && v > 0 ? '✓ ' : ''}{v}</span>
                      <span className="matriz-pct">{porcentaje !== null ? `${porcentaje} %` : '—'}</span>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="leyenda">
        <span><i className="leyenda-muestra" style={{ background: 'rgba(30, 107, 46, 0.75)' }} /> ✓ Aciertos (diagonal)</span>
        <span><i className="leyenda-muestra" style={{ background: 'rgba(176, 32, 32, 0.6)' }} /> Confusiones</span>
        <span className="atenuado">% respecto a su fila (categoría real)</span>
      </div>
    </div>
  );
}

// Barras horizontales: items = [{etiqueta, valor (0–1 o null), color, detalle, id (categoría, opcional)}]
export function BarrasHorizontales({ items }) {
  return (
    <div className="barras-h">
      {items.map((it) => (
        <div key={it.etiqueta} className="barras-h-fila">
          <span className="barras-h-etiqueta">
            {it.id !== undefined && <IconoCategoria id={it.id} tam={16} />} {it.etiqueta}
          </span>
          <Barra valor={it.valor} color={it.color || '#1E6FD9'} alto={18}
            texto={`${pct(it.valor)}${it.detalle ? ` · ${it.detalle}` : ''}`} />
        </div>
      ))}
    </div>
  );
}

// Gráfica de línea en SVG: puntos = [{x: '1', y: 0.44, n: 9}], y de 0 a 1.
// Área sombreada bajo la línea; la línea se dibuja una vez al aparecer.
export function GraficaLineas({ puntos, etiquetaX = 'Intento', etiquetaY = '% de acierto' }) {
  if (!puntos || puntos.length === 0) return <p className="atenuado">Sin datos.</p>;
  const ancho = 560;
  const alto = 290;
  const m = { izq: 54, der: 24, arr: 36, aba: 64 };
  const w = ancho - m.izq - m.der;
  const h = alto - m.arr - m.aba;
  const paso = puntos.length > 1 ? w / (puntos.length - 1) : 0;
  const px = (i) => m.izq + (puntos.length > 1 ? i * paso : w / 2);
  const py = (y) => m.arr + h - (y ?? 0) * h;
  const conDatos = puntos.map((p, i) => ({ ...p, i })).filter((p) => p.y !== null && p.y !== undefined);
  const ruta = conDatos.map((p, k) => `${k === 0 ? 'M' : 'L'} ${px(p.i)} ${py(p.y)}`).join(' ');
  const area = conDatos.length > 1
    ? `${ruta} L ${px(conDatos[conDatos.length - 1].i)} ${py(0)} L ${px(conDatos[0].i)} ${py(0)} Z` : null;
  return (
    <svg className="grafica" viewBox={`0 0 ${ancho} ${alto}`} role="img" aria-label={`${etiquetaY} por ${etiquetaX}`}>
      <defs>
        <linearGradient id="relleno-linea" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#0E7C86" stopOpacity="0.30" />
          <stop offset="1" stopColor="#0E7C86" stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {[0, 0.25, 0.5, 0.75, 1].map((y) => (
        <g key={y}>
          <line x1={m.izq} x2={ancho - m.der} y1={py(y)} y2={py(y)} className={y === 0 ? 'grafica-eje' : 'grafica-rejilla'} />
          <text x={m.izq - 10} y={py(y) + 5} textAnchor="end" className="grafica-texto">{y * 100} %</text>
        </g>
      ))}
      {area && <path d={area} fill="url(#relleno-linea)" className="grafica-area" />}
      <path d={ruta} className="grafica-linea" pathLength="1" />
      {conDatos.map((p) => (
        <g key={p.i}>
          <circle cx={px(p.i)} cy={py(p.y)} r="7" className="grafica-punto" />
          <rect x={px(p.i) - 26} y={py(p.y) - 35} width="52" height="23" rx="5" className="grafica-globo" />
          <text x={px(p.i)} y={py(p.y) - 18} textAnchor="middle" className="grafica-valor">{pct(p.y)}</text>
        </g>
      ))}
      {puntos.map((p, i) => (
        <text key={p.x} x={px(i)} y={alto - m.aba + 24} textAnchor="middle" className="grafica-texto grafica-x">
          {p.x}
          <tspan x={px(i)} dy="17" className="grafica-n">n = {p.n ?? '—'}</tspan>
        </text>
      ))}
      <text x={m.izq + w / 2} y={alto - 4} textAnchor="middle" className="grafica-titulo-eje">{etiquetaX}</text>
    </svg>
  );
}

const NOMBRE_SERIE = { R1: 'Ronda 1', R2: 'Ronda 2' };

// Barras verticales agrupadas: grupos = [{etiqueta, valores: [{nombre, valor, color}]}]
export function BarrasAgrupadas({ grupos }) {
  if (!grupos || grupos.length === 0) return <p className="atenuado">Sin datos.</p>;
  const leyenda = grupos[0].valores.map((v) => ({ nombre: v.nombre, color: v.color }));
  return (
    <div className="barras-v-contenedor">
      <div className="leyenda">
        {leyenda.map((l) => (
          <span key={l.nombre}><i className="leyenda-muestra" style={{ background: l.color }} /> {NOMBRE_SERIE[l.nombre] || l.nombre}</span>
        ))}
      </div>
      <div className="barras-v">
        {grupos.map((g) => (
          <div key={g.etiqueta} className="barras-v-grupo">
            <div className="barras-v-columnas">
              {g.valores.map((v) => (
                <div key={v.nombre} className="barras-v-col" title={`${NOMBRE_SERIE[v.nombre] || v.nombre}: ${pct(v.valor)}`}>
                  <span className="barras-v-valor">{pct(v.valor)}</span>
                  <div className="barras-v-barra" style={{ height: `${(v.valor || 0) * 100}%`, background: v.color }} />
                  <span className="barras-v-nombre">{v.nombre}</span>
                </div>
              ))}
            </div>
            <div className="barras-v-etiqueta">{g.etiqueta}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
