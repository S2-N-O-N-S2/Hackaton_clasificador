// Pruebas oficiales (especificación 3 y 20.4): 20 residuos × 2 corridas, manual cronometrada vs. sistema.
import { useEffect, useRef, useState } from 'react';
import { api } from '../api.js';
import { categoria } from '../categorias.js';
import {
  BotonesCategoria, Categoria, Cifra, MensajeError, Simulado, Tarjeta, pct, useAccion, useDatos,
} from '../componentes/Comun.jsx';
import { MatrizConfusion } from '../componentes/Graficas.jsx';

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
    }));
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
    }));
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
    }));
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

export default function Pruebas() {
  const [corrida, setCorrida] = useState(1);
  const { datos, error, recargar } = useDatos(() => api.pruebas(), []);
  const residuos = datos?.residuos || [];
  const registros = (datos?.registros || []).filter((r) => r.corrida === corrida);
  const ultimoDe = (residuoId, modo) => registros.filter((r) => r.residuo_id === residuoId && r.modo === modo).at(-1);
  const comp = datos?.comparativa;

  return (
    <div className="vista">
      <h1>Pruebas: manual vs. sistema</h1>
      <MensajeError error={error} />
      <Tarjeta titulo={`Residuos de prueba (${residuos.length}; el reto pide ≥ 20)`}>
        <div className="tabla-desplazable">
          <table className="tabla">
            <thead><tr><th>#</th><th>Nombre</th><th>Categoría real</th><th>Simulado</th><th>Usado en entrenamiento</th></tr></thead>
            <tbody>
              {residuos.map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td><td>{r.nombre}</td><td><Categoria id={r.categoria_real} /></td>
                  <td><Simulado si={r.simulado} />{!r.simulado && 'No'}</td>
                  <td>{r.usado_en_entrenamiento ? 'Sí (indicarlo)' : 'No'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <NuevoResiduo alGuardar={recargar} />
      </Tarjeta>

      <div className="filtros">
        <label>Corrida
          <select value={corrida} onChange={(e) => setCorrida(Number(e.target.value))}>
            <option value={1}>Corrida 1</option>
            <option value={2}>Corrida 2</option>
          </select>
        </label>
      </div>

      <div className="rejilla-2">
        <CorridaManual residuos={residuos} corrida={corrida} alRegistrar={recargar} />
        <CorridaSistema residuos={residuos} corrida={corrida} alRegistrar={recargar} />
      </div>

      <Tarjeta titulo="Tabla comparativa">
        {comp && (
          <div className="cifras">
            <Cifra etiqueta="Manual: acierto" valor={pct(comp.manual?.precision)} detalle={`${comp.manual?.aciertos ?? 0}/${comp.manual?.n ?? 0} · ${comp.manual?.tiempo_promedio_s ?? '—'} s prom.`} />
            <Cifra etiqueta="Sistema: acierto" valor={pct(comp.sistema?.precision)} detalle={`${comp.sistema?.aciertos ?? 0}/${comp.sistema?.n ?? 0} · ${comp.sistema?.tiempo_promedio_s ?? '—'} s prom.`} />
          </div>
        )}
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
        {comp && (
          <div className="rejilla-2">
            <div><h3>Matriz manual</h3><MatrizConfusion matriz={comp.matriz_manual} columnas="Asignada" /></div>
            <div><h3>Matriz del sistema</h3><MatrizConfusion matriz={comp.matriz_sistema} columnas="Asignada" /></div>
          </div>
        )}
      </Tarjeta>
    </div>
  );
}
