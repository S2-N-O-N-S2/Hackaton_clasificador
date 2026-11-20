// Aprendizaje (especificación 12.5): ¿la retroalimentación enseña? Datos de GET /api/juego/aprendizaje.
// Orden: la respuesta en una frase → detalle en pestañas (curva, rondas, mitades) → prueba controlada aparte.
import { useState } from 'react';
import { api } from '../api.js';
import { useEnVivo } from '../estado.jsx';
import { categoria } from '../categorias.js';
import { Cargando, IconoCategoria, MensajeError, MuestraPequena, Tarjeta, pct, useAccion, useDatos } from '../componentes/Comun.jsx';
import { BarrasAgrupadas, GraficaLineas } from '../componentes/Graficas.jsx';
import { CabeceraVista } from '../componentes/Efectos.jsx';
import { Anillo, Explicacion, FiltroNiveles, Pestanas } from '../componentes/Paneles.jsx';

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
    const r = await ejecutar(() => api.iniciarPruebaAprendizaje({ alias: alias.trim(), ronda, residuos: elegidos }),
      { ok: `Ronda ${ronda} iniciada para ${alias.trim()}` });
    if (r) setResultado(r);
  }

  return (
    <Tarjeta titulo="Prueba controlada de aprendizaje">
      <p className="atenuado">Un voluntario clasifica los mismos residuos en dos rondas. Si la explicación enseña, la ronda 2 sale mejor.</p>
      <form className="formulario" onSubmit={iniciar}>
        <div className="formulario-fila">
          <label>Alias anónimo (sin nombres reales)
            <input value={alias} onChange={(e) => setAlias(e.target.value)} placeholder="V1" maxLength={12} required />
          </label>
          <div className="segmentado" role="group" aria-label="Ronda">
            <span className="segmentado-etiqueta">Ronda</span>
            <div className="segmentado-opciones">
              {[1, 2].map((n) => (
                <button key={n} type="button" aria-pressed={ronda === n} onClick={() => setRonda(n)}>Ronda {n}</button>
              ))}
            </div>
          </div>
        </div>
        <fieldset>
          <legend>Residuos de prueba: <strong>{elegidos.length}</strong> elegidos (se recomiendan 10)</legend>
          {residuos.length === 0 && <p className="atenuado">No hay residuos registrados: agrégalos en la vista Pruebas.</p>}
          <div className="fichas">
            {residuos.map((r) => (
              <button key={r.id} type="button" className="ficha" aria-pressed={elegidos.includes(r.id)}
                data-cat={categoria(r.categoria_real)?.clave} onClick={() => alternar(r.id)}>
                <IconoCategoria id={r.categoria_real} tam={15} /> {r.nombre}
              </button>
            ))}
          </div>
        </fieldset>
        <button type="submit" className="boton-principal" disabled={ocupado || !alias.trim() || elegidos.length === 0}>
          Iniciar ronda {ronda}
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

// La frase principal: ¿mejoró la gente? Solo describe los números; no afirma significancia.
function Respuesta({ datos }) {
  const dif = datos.mitades?.diferencia;
  const tasa = datos.correccion_tras_explicacion?.tasa;
  const tendencia = dif === null || dif === undefined ? null : dif > 0.02 ? 'sube' : dif < -0.02 ? 'baja' : 'igual';
  const texto = {
    sube: <>En la segunda mitad de cada sesión la gente acierta <strong>{Math.round(dif * 100)} puntos más</strong> que en la primera.</>,
    baja: <>En la segunda mitad de cada sesión la gente acierta <strong>{Math.round(-dif * 100)} puntos menos</strong> que en la primera.</>,
    igual: <>La gente acierta <strong>casi igual</strong> al principio y al final de cada sesión.</>,
  }[tendencia];
  return (
    <section className="tarjeta resumen-principal revelar">
      <Anillo valor={tasa ?? null} tam={160} detalle="corrige tras la explicación" />
      <div className="resumen-textos">
        <p className="frase-grande">
          Después de ver la explicación de un error, <strong>{pct(tasa)}</strong> de las veces la persona acierta la siguiente
          vez que le toca esa categoría en la misma sesión ({datos.correccion_tras_explicacion?.corregidas ?? 0} de {datos.correccion_tras_explicacion?.n_oportunidades ?? 0}).
        </p>
        {tendencia && (
          <p className={`tendencia tendencia-${tendencia}`}>
            <span className="tendencia-flecha" aria-hidden="true">{{ sube: '↗', baja: '↘', igual: '→' }[tendencia]}</span>
            <span>{texto}</span>
          </p>
        )}
        <div className="resumen-chico">
          <div><strong>{datos.muestra?.n_sesiones ?? '—'}</strong><span>sesiones</span></div>
          <div><strong>{datos.muestra?.n_intentos ?? '—'}</strong><span>intentos</span></div>
          <div><strong>{datos.muestra?.n_voluntarios ?? '—'}</strong><span>voluntarios</span></div>
        </div>
      </div>
    </section>
  );
}

export default function Aprendizaje() {
  const [niveles, setNiveles] = useState(['verificada', 'alta']);
  const { versiones } = useEnVivo();
  const { datos, error, cargando } = useDatos(() => api.aprendizaje(niveles), [niveles.join(','), versiones.historial]);

  const gruposRondas = datos ? [
    ...(datos.rondas?.por_participante || []).map((p) => ({
      etiqueta: `${p.alias} (n=${p.n1}/${p.n2})`,
      valores: [{ nombre: 'Ronda 1', valor: p.ronda1, color: '#9CA3AF' }, { nombre: 'Ronda 2', valor: p.ronda2, color: '#0E7C86' }],
    })),
    ...(datos.rondas?.promedio ? [{
      etiqueta: `Promedio (${datos.rondas.promedio.n_voluntarios} vol.)`,
      valores: [{ nombre: 'Ronda 1', valor: datos.rondas.promedio.ronda1, color: '#9CA3AF' }, { nombre: 'Ronda 2', valor: datos.rondas.promedio.ronda2, color: '#0E7C86' }],
    }] : []),
  ] : [];

  return (
    <div className="vista vista-datos">
      <CabeceraVista icono="aprendizaje" titulo="Aprendizaje" pregunta="¿La retroalimentación del juego enseña a separar mejor?">
        <FiltroNiveles niveles={niveles} alCambiar={setNiveles} />
      </CabeceraVista>
      <MensajeError error={error} />
      {cargando && !datos && <Cargando />}
      {datos && (
        <>
          <MuestraPequena si={datos.muestra_pequena} />
          <Respuesta datos={datos} />
          <section className="tarjeta">
            <Pestanas pestanas={[
              {
                id: 'curva', titulo: 'Curva de aprendizaje',
                contenido: (
                  <>
                    <GraficaLineas puntos={(datos.por_intento || []).map((p) => ({ x: p.intento, y: p.acierto, n: p.n }))} />
                    <Explicacion>Porcentaje de acierto en el 1.er, 2.º, 3.er… intento de cada persona. Si la gente aprende, la línea sube.</Explicacion>
                  </>
                ),
              },
              {
                id: 'rondas', titulo: 'Ronda 1 vs. 2',
                contenido: (
                  <>
                    <BarrasAgrupadas grupos={gruposRondas} />
                    <Explicacion>Prueba controlada: el mismo voluntario con los mismos residuos, antes y después de la retroalimentación.</Explicacion>
                  </>
                ),
              },
              {
                id: 'mitades', titulo: 'Mitades de sesión',
                contenido: (
                  <>
                    <div className="comparacion-mitades">
                      <Anillo valor={datos.mitades?.primera ?? null} color="#9CA3AF" tam={130} detalle="primera mitad" />
                      <span className="mitades-flecha" aria-hidden="true">→</span>
                      <Anillo valor={datos.mitades?.segunda ?? null} tam={130} detalle="segunda mitad" />
                    </div>
                    <Explicacion>Se comparan la primera y la segunda mitad de cada sesión con 4 intentos o más ({datos.mitades?.n_sesiones ?? 0} sesiones).</Explicacion>
                  </>
                ),
              },
            ]} />
          </section>
          <PruebaControlada />
          <p className="atenuado pie">
            Límites: pocos voluntarios, los mismos objetos en ambas rondas y posible efecto de memoria. No se afirma significancia estadística.
          </p>
        </>
      )}
    </div>
  );
}
