// Pruebas oficiales (especificación 3 y 20.4): 20 residuos × 2 corridas, manual cronometrada vs. sistema.
// Organizada en 4 pasos para no mostrar todo a la vez: residuos → corrida manual → corrida del sistema → resultados.
import { useEffect, useRef, useState } from 'react';
import { api } from '../api.js';
import { categoria } from '../categorias.js';
import {
  BotonesCategoria, Categoria, IconoCategoria, MensajeError, Simulado, Tarjeta, pct, useAccion, useDatos,
} from '../componentes/Comun.jsx';
import { MatrizConfusion } from '../componentes/Graficas.jsx';
import { CabeceraVista } from '../componentes/Efectos.jsx';
import { Duelo, Explicacion, Pestanas, Segmentado } from '../componentes/Paneles.jsx';

function NuevoResiduo({ alGuardar }) {
  const [nombre, setNombre] = useState('');
  const [cat, setCat] = useState(0);
  const [simulado, setSimulado] = useState(false);
  const [usado, setUsado] = useState(false);
  const { ejecutar, ocupado, error } = useAccion();
  async function guardar(e) {
    e.preventDefault();
    const r = await ejecutar(() => api.registrarResiduo({
      nombre: nombre.trim(), categoria_real: cat, simulado, usado_en_entrenamiento: usado,
    }), { ok: `Residuo agregado: ${nombre.trim()}` });
    if (r) { setNombre(''); alGuardar(); }
  }
  return (
    <form className="formulario en-linea" onSubmit={guardar}>
      <label>Nombre<input value={nombre} onChange={(e) => setNombre(e.target.value)} required placeholder="Cáscara de plátano" /></label>
      <label>Categoría real
        <select value={cat} onChange={(e) => setCat(Number(e.target.value))}>
          {[0, 1, 2].map((id) => <option key={id} value={id}>{categoria(id).nombre}</option>)}
        </select>
      </label>
      <label className="casilla"><input type="checkbox" checked={simulado} onChange={(e) => setSimulado(e.target.checked)} /> Peligroso simulado</label>
      <label className="casilla"><input type="checkbox" checked={usado} onChange={(e) => setUsado(e.target.checked)} /> Usado en entrenamiento</label>
      <button type="submit" className="boton-principal" disabled={ocupado || !nombre.trim()}>Agregar</button>
      <MensajeError error={error} />
    </form>
  );
}

// Cronómetro para la separación manual: inicia, la persona elige el bote y se registra el tiempo.
function CorridaManual({ residuos, corrida, alRegistrar }) {
  const [residuoId, setResiduoId] = useState('');
  const [inicio, setInicio] = useState(null);
  const [ahora, setAhora] = useState(Date.now());
  const [ultimo, setUltimo] = useState(null);
  const { ejecutar, ocupado, error } = useAccion();
  const timer = useRef(null);

  useEffect(() => {
    if (inicio === null) return undefined;
    timer.current = setInterval(() => setAhora(Date.now()), 100);
    return () => clearInterval(timer.current);
  }, [inicio]);

  async function elegir(cat) {
    const tiempo = Math.round((Date.now() - inicio) / 100) / 10;
    setInicio(null);
    const r = await ejecutar(() => api.registrarPrueba({
      corrida, modo: 'manual', residuo_id: Number(residuoId), categoria_asignada: cat, tiempo_s: tiempo,
    }), { ok: `Registrado en ${tiempo} s` });
    if (r) { setUltimo(r); alRegistrar(); }
  }

  const segundos = inicio === null ? 0 : (ahora - inicio) / 1000;
  return (
    <Tarjeta titulo="Corrida manual (cronometrada)">
      <label>Residuo
        <select value={residuoId} onChange={(e) => setResiduoId(e.target.value)} disabled={inicio !== null}>
          <option value="">— elige —</option>
          {residuos.map((r) => <option key={r.id} value={r.id}>{r.nombre}</option>)}
        </select>
      </label>
      <div className="cronometro">{segundos.toFixed(1)} s</div>
      {inicio === null ? (
        <button type="button" className="boton-principal" disabled={!residuoId || ocupado} onClick={() => { setInicio(Date.now()); setAhora(Date.now()); }}>
          Iniciar cronómetro
        </button>
      ) : (
        <>
          <p>La persona elige el bote:</p>
          <BotonesCategoria alElegir={elegir} deshabilitado={ocupado} />
          <button type="button" className="boton-texto" onClick={() => setInicio(null)}>Cancelar</button>
        </>
      )}
      {ultimo && (
        <p>Registrado: {ultimo.tiempo_s} s · {ultimo.correcto ? '✔ correcto' : '✘ incorrecto'}</p>
      )}
      <MensajeError error={error} />
    </Tarjeta>
  );
}

function CorridaSistema({ residuos, corrida, alRegistrar }) {
  const [residuoId, setResiduoId] = useState('');
  const [cat, setCat] = useState(0);
  const [tiempo, setTiempo] = useState('');
  const { ejecutar, ocupado, error } = useAccion();
  async function guardar(e) {
    e.preventDefault();
    const r = await ejecutar(() => api.registrarPrueba({
      corrida, modo: 'sistema', residuo_id: Number(residuoId), categoria_asignada: cat, tiempo_s: Number(tiempo),
    }), { ok: 'Corrida del sistema registrada' });
    if (r) { setResiduoId(''); setTiempo(''); alRegistrar(); }
  }
  return (
    <Tarjeta titulo="Corrida con el sistema">
      <form className="formulario" onSubmit={guardar}>
        <label>Residuo
          <select value={residuoId} onChange={(e) => setResiduoId(e.target.value)} required>
            <option value="">— elige —</option>
            {residuos.map((r) => <option key={r.id} value={r.id}>{r.nombre}</option>)}
          </select>
        </label>
        <label>Bote al que lo envió el sistema
          <select value={cat} onChange={(e) => setCat(Number(e.target.value))}>
            {[0, 1, 2].map((id) => <option key={id} value={id}>{categoria(id).nombre}</option>)}
          </select>
        </label>
        <label>Tiempo de máquina (s) — "tiempo de ciclo" en el Historial
          <input type="number" min="0" step="0.1" value={tiempo} onChange={(e) => setTiempo(e.target.value)} required />
        </label>
        <button type="submit" className="boton-principal" disabled={ocupado || !residuoId || tiempo === ''}>Registrar</button>
      </form>
      <MensajeError error={error} />
    </Tarjeta>
  );
}

function celda(registro) {
  if (!registro) return <td className="atenuado">—</td>;
  return (
    <td className={registro.correcto ? 'celda-ok' : 'celda-mal'}>
      <Categoria id={registro.categoria_asignada} /> {registro.correcto ? '✔' : '✘'} · {registro.tiempo_s} s
    </td>
  );
}

function ListaResiduos({ residuos, recargar }) {
  const meta = 20;
  return (
    <>
      <div className="meta-residuos">
        <span><strong>{residuos.length}</strong> de {meta} residuos registrados (el reto pide 20 o más)</span>
        <div className="meta-barra" aria-hidden="true"><div style={{ width: `${Math.min(1, residuos.length / meta) * 100}%` }} /></div>
      </div>
      {residuos.length > 0 && (
        <ul className="fichas fichas-residuos">
          {residuos.map((r) => (
            <li key={r.id} className="ficha" data-cat={categoria(r.categoria_real)?.clave}>
              <span className="ficha-n">{r.id}</span>
              <IconoCategoria id={r.categoria_real} tam={15} /> {r.nombre}
              {r.simulado && <Simulado />}
              {r.usado_en_entrenamiento && <span className="rotulo rotulo-aviso" title="Indicarlo al jurado">en entrenamiento</span>}
            </li>
          ))}
        </ul>
      )}
      <h3>Agregar residuo</h3>
      <NuevoResiduo alGuardar={recargar} />
    </>
  );
}

function Resultados({ residuos, comp, ultimoDe }) {
  return (
    <>
      {comp && (
        <Duelo
          izquierda={{ nombre: 'Manual', valor: comp.manual?.precision ?? null, color: '#F28C05', detalle: `${comp.manual?.aciertos ?? 0}/${comp.manual?.n ?? 0} · ${comp.manual?.tiempo_promedio_s ?? '—'} s` }}
          derecha={{ nombre: 'Sistema', valor: comp.sistema?.precision ?? null, color: '#0E7C86', detalle: `${comp.sistema?.aciertos ?? 0}/${comp.sistema?.n ?? 0} · ${comp.sistema?.tiempo_promedio_s ?? '—'} s` }}
          pie="Debajo de cada anillo: aciertos y tiempo promedio por residuo."
        />
      )}
      <Pestanas pestanas={[
        {
          id: 'tabla', titulo: 'Residuo por residuo',
          contenido: (
            <div className="tabla-desplazable">
              <table className="tabla">
                <thead><tr><th>Residuo</th><th>Real</th><th>Manual</th><th>Sistema</th></tr></thead>
                <tbody>
                  {residuos.map((r) => (
                    <tr key={r.id}>
                      <td>{r.nombre}</td><td><Categoria id={r.categoria_real} /></td>
                      {celda(ultimoDe(r.id, 'manual'))}
                      {celda(ultimoDe(r.id, 'sistema'))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ),
        },
        ...(comp ? [{
          id: 'matrices', titulo: 'Matrices',
          contenido: (
            <>
              <div className="rejilla-2">
                <div><h3>Manual</h3><MatrizConfusion matriz={comp.matriz_manual} columnas="Asignada" /></div>
                <div><h3>Sistema</h3><MatrizConfusion matriz={comp.matriz_sistema} columnas="Asignada" /></div>
              </div>
              <Explicacion>Cada fila es la categoría real y cada columna el bote asignado. La diagonal (✓) son los aciertos.</Explicacion>
            </>
          ),
        }] : []),
      ]} />
    </>
  );
}

export default function Pruebas() {
  const [corrida, setCorrida] = useState(1);
  const [paso, setPaso] = useState('residuos');
  const { datos, error, recargar } = useDatos(() => api.pruebas(), []);
  const residuos = datos?.residuos || [];
  const registros = (datos?.registros || []).filter((r) => r.corrida === corrida);
  const ultimoDe = (residuoId, modo) => registros.filter((r) => r.residuo_id === residuoId && r.modo === modo).at(-1);
  const hechos = (modo) => new Set(registros.filter((r) => r.modo === modo).map((r) => r.residuo_id)).size;
  const comp = datos?.comparativa;

  const pasos = [
    { id: 'residuos', titulo: 'Residuos', estado: `${residuos.length}/20`, listo: residuos.length >= 20 },
    { id: 'manual', titulo: 'Corrida manual', estado: `${hechos('manual')}/${residuos.length}`, listo: residuos.length > 0 && hechos('manual') >= residuos.length },
    { id: 'sistema', titulo: 'Corrida con el sistema', estado: `${hechos('sistema')}/${residuos.length}`, listo: residuos.length > 0 && hechos('sistema') >= residuos.length },
    { id: 'resultados', titulo: 'Resultados', estado: comp ? pct(comp.sistema?.precision) : '—', listo: false },
  ];

  return (
    <div className="vista vista-datos">
      <CabeceraVista icono="pruebas" titulo="Pruebas" pregunta="¿Separa mejor y más rápido una persona o el sistema, con los mismos 20 residuos?">
        <Segmentado etiqueta="Corrida" valor={corrida} alCambiar={setCorrida}
          opciones={[{ clave: 1, nombre: 'Corrida 1' }, { clave: 2, nombre: 'Corrida 2' }]} />
      </CabeceraVista>
      <MensajeError error={error} />
      <ol className="pasos" aria-label="Pasos de la prueba">
        {pasos.map((p, i) => (
          <li key={p.id} className="paso">
            <button type="button" aria-current={paso === p.id ? 'step' : undefined} className={p.listo ? 'listo' : ''} onClick={() => setPaso(p.id)}>
              <span className="paso-numero">{p.listo ? '✓' : i + 1}</span>
              <span className="paso-texto"><strong>{p.titulo}</strong><small>{p.estado}</small></span>
            </button>
          </li>
        ))}
      </ol>
      <section className="tarjeta paso-contenido" key={paso}>
        {paso === 'residuos' && <ListaResiduos residuos={residuos} recargar={recargar} />}
        {paso === 'manual' && <CorridaManual residuos={residuos} corrida={corrida} alRegistrar={recargar} />}
        {paso === 'sistema' && <CorridaSistema residuos={residuos} corrida={corrida} alRegistrar={recargar} />}
        {paso === 'resultados' && <Resultados residuos={residuos} comp={comp} ultimoDe={ultimoDe} />}
      </section>
    </div>
  );
}
