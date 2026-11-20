// =============================================================================
//  Voz (Fase 9, contrato v1.5).
//  - BotonVoz: micrófono flotante (push-to-talk, igual que la tecla A). Muestra la cuenta regresiva
//    mientras graba y una burbuja con lo que entendió. También reacciona si alguien presiona A en el
//    teclado físico (evento "voz" del WebSocket).
//  - AjustesVoz: tarjeta de Configuración (voz que habla, volumen, velocidad, micrófono, prueba).
//  El panel NO interpreta nada: solo muestra lo que el backend reconoció y decidió.
// =============================================================================
import { useEffect, useRef, useState } from 'react';
import { api } from '../api.js';
import { useEnVivo } from '../estado.jsx';
import { categoria } from '../categorias.js';
import { MODO_MOCK } from '../config.js';
import { MensajeError, Tarjeta, useAccion, useDatos } from './Comun.jsx';

const ESTADOS_VOZ = ['MENU', 'ESPERA_OBJETO', 'REVISION'];
const MS_BURBUJA = 7000;

const ACCIONES = {
  revision_resuelta: 'Caso resuelto: el residuo va al bote',
  modo_ia: 'Modo IA elegido', modo_adivina: 'Modo Adivina elegido', modo_menu: 'De vuelta al menú',
  respuesta_bote: 'Te mostré el bote',
  no_reconocido: 'Presiona de nuevo y repítelo',
  ignorado: 'No hay nada que hacer ahora',
};

function IconoMicrofono() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10v1a7 7 0 0 0 14 0v-1" />
      <line x1="12" y1="18" x2="12" y2="22" />
      <line x1="8" y1="22" x2="16" y2="22" />
    </svg>
  );
}

// Texto de lo que entendió el backend (sin interpretar nada aquí).
function textoEntendido(intencion) {
  if (!intencion) return '—';
  if (intencion.tipo === 'categoria') {
    const c = categoria(intencion.valor);
    return `${intencion.objeto ? `${intencion.objeto} → ` : ''}${c.nombre} (bote ${c.color})`;
  }
  if (intencion.tipo === 'modo') return { ia: 'Modo IA', adivina: 'Modo Adivina', menu: 'Menú' }[intencion.valor] || intencion.valor;
  if (intencion.tipo === 'desconocido') return 'No reconocí el objeto';
  return 'No oí nada';
}

export function BotonVoz() {
  const { maquina, voz } = useEnVivo();
  const [grabando, setGrabando] = useState(null);   // {inicio, segundos} mientras se graba desde el panel
  const [burbuja, setBurbuja] = useState(null);     // {texto, entendido, accion, error}
  const [, setTic] = useState(0);
  const temporizador = useRef(null);

  // Muestra lo que llegue por el WebSocket (también si se presionó A en el teclado físico).
  useEffect(() => {
    if (!voz) return;
    if (voz.fase === 'escuchando') setGrabando((g) => g || { inicio: voz.recibido, segundos: voz.segundos || 4 });
    if (voz.fase === 'reconocido' || voz.fase === 'error') {
      setGrabando(null);
      mostrar(voz.fase === 'error'
        ? { error: voz.mensaje || 'No se pudo escuchar' }
        : { texto: voz.texto_crudo, entendido: textoEntendido(voz.intencion), accion: ACCIONES[voz.accion],
            cat: voz.intencion?.tipo === 'categoria' ? voz.intencion.valor : null,
            fallo: voz.intencion?.tipo !== 'categoria' && voz.intencion?.tipo !== 'modo' });
    }
  }, [voz?.recibido]); // eslint-disable-line react-hooks/exhaustive-deps

  // Cuenta regresiva visible mientras graba.
  useEffect(() => {
    if (!grabando) return undefined;
    const t = setInterval(() => setTic((x) => x + 1), 250);
    return () => clearInterval(t);
  }, [grabando]);

  useEffect(() => () => clearTimeout(temporizador.current), []);

  function mostrar(datos) {
    setBurbuja({ ...datos, id: Date.now() }); // id nuevo: la barra de tiempo vuelve a empezar
    clearTimeout(temporizador.current);
    temporizador.current = setTimeout(() => setBurbuja(null), MS_BURBUJA);
  }

  if (MODO_MOCK || !maquina?.voz?.disponible) return null;

  const puede = ESTADOS_VOZ.includes(maquina.estado);
  const ocupado = !!grabando || maquina.voz.escuchando;

  async function hablar() {
    setBurbuja(null);
    setGrabando({ inicio: Date.now(), segundos: 4 });
    try {
      const r = await api.escucharVoz();
      mostrar({ texto: r.texto_crudo, entendido: textoEntendido(r.intencion), accion: ACCIONES[r.accion],
                cat: r.intencion?.tipo === 'categoria' ? r.intencion.valor : null,
                fallo: r.intencion?.tipo !== 'categoria' && r.intencion?.tipo !== 'modo' });
    } catch (e) {
      mostrar({ error: e.message || 'No se pudo escuchar' });
    } finally {
      setGrabando(null);
    }
  }

  let etiqueta = maquina.estado === 'REVISION' ? 'Dime qué es' : 'Hablar';
  let clase = '';
  let avance = 0; // 0–1: cuánto del tiempo de grabación ya pasó (anillo alrededor del micrófono)
  if (grabando) {
    const pasado = (Date.now() - grabando.inicio) / 1000;
    const restante = Math.ceil(grabando.segundos - pasado);
    avance = Math.min(1, pasado / grabando.segundos);
    etiqueta = restante > 0 ? `Habla ahora… ${restante}` : 'Reconociendo…';
    clase = restante > 0 ? 'escuchando' : 'procesando';
  }
  const colorCat = burbuja?.cat !== null && burbuja?.cat !== undefined ? categoria(burbuja.cat) : null;

  return (
    <div className="voz-flotante">
      {burbuja && (
        <div key={burbuja.id} className={`voz-burbuja ${burbuja.error || burbuja.fallo ? 'voz-error' : 'voz-ok'}`} role="status" aria-live="polite"
          style={colorCat ? { '--cat': colorCat.hex } : undefined}>
          {burbuja.error ? (
            <>
              <span className="voz-etiqueta">No se pudo escuchar</span>
              <span className="voz-entendido">{burbuja.error}</span>
            </>
          ) : (
            <>
              <span className="voz-etiqueta">Lo que oí</span>
              <span className="voz-oido">{burbuja.texto ? `“${burbuja.texto}”` : 'No oí nada'}</span>
              <span className="voz-etiqueta">Entendí</span>
              <span className="voz-entendido">
                {colorCat && <span className="voz-cat-punto" aria-hidden="true" />}
                {burbuja.entendido}
              </span>
              {burbuja.accion && <span className="voz-accion">{burbuja.accion}</span>}
            </>
          )}
          <span className="voz-tiempo" aria-hidden="true" style={{ '--ms': `${MS_BURBUJA}ms` }} />
        </div>
      )}
      <button type="button" className={`voz-boton ${clase}`} onClick={hablar} disabled={!puede || ocupado}
        title={puede ? 'Presiona y habla (igual que la tecla A)' : 'La voz se usa en el menú o cuando el sistema pide ayuda'}
        aria-label={etiqueta}>
        <span className="voz-mic" style={{ '--avance': avance }}>
          <IconoMicrofono />
        </span>
        <span className="voz-boton-texto">{etiqueta}</span>
        <span className="voz-ondas" aria-hidden="true">{[0, 1, 2, 3, 4].map((i) => <i key={i} style={{ '--i': i }} />)}</span>
      </button>
    </div>
  );
}

// ----------------------------------------------------------------------------- Configuración
export function AjustesVoz() {
  const config = useDatos(() => api.config(), []);
  const voces = useDatos(() => api.voces(), []);
  const microfonos = useDatos(() => api.microfonos(), []);
  const { ejecutar, ocupado, error } = useAccion();
  const [v, setV] = useState(null);
  const [nivel, setNivel] = useState(null);

  useEffect(() => {
    if (config.datos) setV(config.datos.valores);
  }, [config.datos]);

  if (!v) return <Tarjeta titulo="Voz"><MensajeError error={config.error} /></Tarjeta>;

  async function guardar(parcial, ok) {
    setV({ ...v, ...parcial });
    return ejecutar(() => api.guardarConfig(parcial), { ok });
  }
  async function guardarYProbar(parcial, ok) {
    if (await guardar(parcial, ok)) api.decir('Es inorgánica. Va en el bote azul.').catch(() => {});
  }

  const listaVoces = voces.datos?.voces || [];
  const listaMics = microfonos.datos?.microfonos || [];

  return (
    <Tarjeta titulo="Voz" className="voz-ajustes">
      <label className="casilla">
        <input type="checkbox" checked={!!v.voz_habla} disabled={ocupado}
          onChange={(e) => guardar({ voz_habla: e.target.checked }, e.target.checked ? 'El sistema dirá los resultados' : 'El sistema se quedará callado')} />
        {' '}El sistema dice en voz alta la clasificación y el bote
      </label>

      <div className="fila-control">
        <label htmlFor="voz-nombre">Voz</label>
        <select id="voz-nombre" value={v.voz_nombre} disabled={ocupado || !listaVoces.length}
          onChange={(e) => guardarYProbar({ voz_nombre: e.target.value }, `Voz: ${e.target.value}`)}>
          {!listaVoces.length && <option value={v.voz_nombre}>{voces.datos?.motivo || 'Sin voces en español'}</option>}
          {listaVoces.map((nombre) => {
            const corto = nombre.replace('Microsoft ', '');
            return <option key={nombre} value={corto}>{corto} (España)</option>;
          })}
        </select>
        <span />
      </div>
      <div className="fila-control">
        <label htmlFor="voz-volumen">Volumen</label>
        <input id="voz-volumen" type="range" min="10" max="300" step="10" value={v.voz_volumen} disabled={ocupado}
          onChange={(e) => setV({ ...v, voz_volumen: Number(e.target.value) })}
          onPointerUp={(e) => guardarYProbar({ voz_volumen: Number(e.target.value) }, `Volumen: ${e.target.value} %`)}
          onKeyUp={(e) => guardarYProbar({ voz_volumen: Number(e.target.value) }, `Volumen: ${e.target.value} %`)} />
        <output>{v.voz_volumen} %</output>
      </div>
      <div className="fila-control">
        <label htmlFor="voz-velocidad">Velocidad</label>
        <input id="voz-velocidad" type="range" min="0.5" max="2" step="0.1" value={v.voz_velocidad} disabled={ocupado}
          onChange={(e) => setV({ ...v, voz_velocidad: Number(e.target.value) })}
          onPointerUp={(e) => guardarYProbar({ voz_velocidad: Number(e.target.value) }, `Velocidad: ${e.target.value}×`)}
          onKeyUp={(e) => guardarYProbar({ voz_velocidad: Number(e.target.value) }, `Velocidad: ${e.target.value}×`)} />
        <output>{Number(v.voz_velocidad).toFixed(1)}×</output>
      </div>
      <p className="atenuado">100 % = lo más fuerte sin distorsión; más arriba suena más fuerte. Si aun así se oye bajo, sube el volumen de Windows.</p>

      <div className="fila-control">
        <label htmlFor="voz-mic">Micrófono</label>
        <select id="voz-mic" value={v.microfono} disabled={ocupado}
          onChange={(e) => guardar({ microfono: e.target.value }, `Micrófono: ${e.target.value || 'predeterminado'}`)}>
          <option value="">Predeterminado de Windows</option>
          {listaMics.map((m) => <option key={m.indice} value={m.nombre}>{m.nombre}</option>)}
        </select>
        <span />
      </div>
      <div className="fila-control">
        <label htmlFor="voz-seg">Grabar</label>
        <input id="voz-seg" type="range" min="2" max="8" step="0.5" value={v.voz_segundos} disabled={ocupado}
          onChange={(e) => setV({ ...v, voz_segundos: Number(e.target.value) })}
          onPointerUp={(e) => guardar({ voz_segundos: Number(e.target.value) }, `Grabará ${e.target.value} s`)}
          onKeyUp={(e) => guardar({ voz_segundos: Number(e.target.value) }, `Grabará ${e.target.value} s`)} />
        <output>{v.voz_segundos} s</output>
      </div>

      <div className="fila-botones">
        <button type="button" className="boton-secundario" disabled={ocupado}
          onClick={() => ejecutar(() => api.decir('Es inorgánica, con 92 por ciento de certeza. Va en el bote azul.'))}>
          Probar la voz
        </button>
        <button type="button" className="boton-secundario" disabled={ocupado}
          onClick={async () => { setNivel('Habla ahora (1 s)…'); const r = await ejecutar(() => api.nivelMicrofono()); setNivel(r ? `${r.veredicto} · nivel ${r.rms}` : null); }}>
          Medir micrófono
        </button>
      </div>
      {nivel && <p className="voz-nivel">{nivel}</p>}
      <MensajeError error={error || voces.error || microfonos.error} />
    </Tarjeta>
  );
}
