// Aprendizaje (especificación 12.5): ¿la retroalimentación enseña? Datos de GET /api/juego/aprendizaje.
import { useState } from 'react';
import { api } from '../api.js';
import { useEnVivo } from '../estado.jsx';
import { categoria } from '../categorias.js';
import { Cifra, MensajeError, MuestraPequena, Tarjeta, pct, useAccion, useDatos } from '../componentes/Comun.jsx';
import { BarrasAgrupadas, GraficaLineas } from '../componentes/Graficas.jsx';
import { FiltroNiveles } from './HumanoIA.jsx';

function PruebaControlada() {
  const pruebas = useDatos(() => api.pruebas(), []);
  const [alias, setAlias] = useState('');
  const [ronda, setRonda] = useState(1);
  const [elegidos, setElegidos] = useState([]);
  const [resultado, setResultado] = useState(null);
  const { ejecutar, ocupado, error } = useAccion();
  const residuos = pruebas.datos?.residuos || [];

  const alternar = (id) => setElegidos((l) => (l.includes(id) ? l.filter((x) => x !== id) : [...l, id]));

  async function iniciar(e) {
    e.preventDefault();
    const r = await ejecutar(() => api.iniciarPruebaAprendizaje({ alias: alias.trim(), ronda, residuos: elegidos }));
    if (r) setResultado(r);
  }

  return (
    <Tarjeta titulo="Prueba controlada de aprendizaje">
      <form className="formulario" onSubmit={iniciar}>
        <label>Alias anónimo (sin nombres reales)
          <input value={alias} onChange={(e) => setAlias(e.target.value)} placeholder="V1" maxLength={12} required />
        </label>
        <label>Ronda
          <select value={ronda} onChange={(e) => setRonda(Number(e.target.value))}>
            <option value={1}>Ronda 1</option>
            <option value={2}>Ronda 2</option>
          </select>
        </label>
        <fieldset>
          <legend>Residuos de prueba ({elegidos.length} elegidos; se recomiendan 10)</legend>
          {residuos.length === 0 && <p className="atenuado">No hay residuos registrados: agrégalos en la vista Pruebas.</p>}
          <div className="lista-casillas">
            {residuos.map((r) => (
              <label key={r.id} className="casilla">
                <input type="checkbox" checked={elegidos.includes(r.id)} onChange={() => alternar(r.id)} />
                {r.nombre} <span style={{ color: categoria(r.categoria_real)?.hex }}>({categoria(r.categoria_real)?.nombre})</span>
              </label>
            ))}
          </div>
        </fieldset>
        <button type="submit" className="boton-principal" disabled={ocupado || !alias.trim() || elegidos.length === 0}>
          Iniciar ronda
        </button>
      </form>
      <MensajeError error={error || pruebas.error} />
      {resultado && (
        <div className="orden">
          <p>Sesión #{resultado.sesion_id}. Coloca los residuos en este orden (aleatorio):</p>
          <ol>
            {resultado.orden.map((id) => <li key={id}>{residuos.find((r) => r.id === id)?.nombre || `Residuo ${id}`}</li>)}
          </ol>
        </div>
      )}
    </Tarjeta>
  );
}

export default function Aprendizaje() {
  const [niveles, setNiveles] = useState(['verificada', 'alta']);
  const { versiones } = useEnVivo();
  const { datos, error, cargando } = useDatos(() => api.aprendizaje(niveles), [niveles.join(','), versiones.historial]);

  return (
    <div className="vista">
      <h1>¿La retroalimentación enseña?</h1>
      <FiltroNiveles niveles={niveles} alCambiar={setNiveles} />
      <MensajeError error={error} />
      {cargando && !datos && <p className="atenuado">Cargando…</p>}
      {datos && (
        <>
          <MuestraPequena si={datos.muestra_pequena} />
          <div className="cifras">
            <Cifra etiqueta="Sesiones" valor={datos.muestra?.n_sesiones ?? '—'} />
            <Cifra etiqueta="Intentos" valor={datos.muestra?.n_intentos ?? '—'} />
            <Cifra etiqueta="Voluntarios" valor={datos.muestra?.n_voluntarios ?? '—'} />
            <Cifra etiqueta="Corrección tras explicación" valor={pct(datos.correccion_tras_explicacion?.tasa)}
              detalle={`${datos.correccion_tras_explicacion?.corregidas ?? 0} de ${datos.correccion_tras_explicacion?.n_oportunidades ?? 0} oportunidades`} />
          </div>
          <div className="rejilla-2">
            <Tarjeta titulo="% de acierto por número de intento">
              <GraficaLineas puntos={(datos.por_intento || []).map((p) => ({ x: p.intento, y: p.acierto, n: p.n }))} />
              <p className="atenuado pie">Si la gente aprende, la línea sube.</p>
            </Tarjeta>
            <Tarjeta titulo="Ronda 1 vs. ronda 2 (prueba controlada)">
              <BarrasAgrupadas grupos={[
                ...(datos.rondas?.por_participante || []).map((p) => ({
                  etiqueta: `${p.alias} (n=${p.n1}/${p.n2})`,
                  valores: [
                    { nombre: 'R1', valor: p.ronda1, color: '#9CA3AF' },
                    { nombre: 'R2', valor: p.ronda2, color: '#2E9E44' },
                  ],
                })),
                ...(datos.rondas?.promedio ? [{
                  etiqueta: `Promedio (${datos.rondas.promedio.n_voluntarios} vol.)`,
                  valores: [
                    { nombre: 'R1', valor: datos.rondas.promedio.ronda1, color: '#6B7280' },
                    { nombre: 'R2', valor: datos.rondas.promedio.ronda2, color: '#1F7A34' },
                  ],
                }] : []),
              ]} />
            </Tarjeta>
            <Tarjeta titulo="Primera vs. segunda mitad de cada sesión">
              <div className="cifras">
                <Cifra etiqueta="Primera mitad" valor={pct(datos.mitades?.primera)} />
                <Cifra etiqueta="Segunda mitad" valor={pct(datos.mitades?.segunda)} />
                <Cifra etiqueta="Diferencia" valor={datos.mitades?.diferencia === null || datos.mitades?.diferencia === undefined ? '—' : `${datos.mitades.diferencia > 0 ? '+' : ''}${(datos.mitades.diferencia * 100).toFixed(0)} pts`}
                  detalle={`${datos.mitades?.n_sesiones ?? 0} sesiones con ≥ 4 intentos`} />
              </div>
            </Tarjeta>
            <PruebaControlada />
          </div>
          <p className="atenuado pie">
            Límites: pocos voluntarios, los mismos objetos en ambas rondas y posible efecto de memoria. No se afirma significancia estadística.
          </p>
        </>
      )}
    </div>
  );
}
