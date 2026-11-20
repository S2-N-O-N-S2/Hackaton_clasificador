// Aprendizaje: ¿el Entrenamiento con fotos enseña? Datos de GET /api/juego/aprendizaje (desde el 20-nov salen de
// las respuestas del Entrenamiento). Orden: la respuesta en una frase → detalle en pestañas (curva, mitades).
import { api } from '../api.js';
import { useEnVivo } from '../estado.jsx';
import { Cargando, MensajeError, MuestraPequena, pct, useDatos } from '../componentes/Comun.jsx';
import { GraficaLineas } from '../componentes/Graficas.jsx';
import { CabeceraVista } from '../componentes/Efectos.jsx';
import { Anillo, Explicacion, Pestanas } from '../componentes/Paneles.jsx';

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
      <Anillo valor={tasa ?? null} tam={160} detalle="corrige tras fallar" />
      <div className="resumen-textos">
        <p className="frase-grande">
          Después de fallar una foto y ver cuál era el bote correcto, <strong>{pct(tasa)}</strong> de las veces la persona acierta la siguiente
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
        </div>
      </div>
    </section>
  );
}

export default function Aprendizaje() {
  const { versiones } = useEnVivo();
  const { datos, error, cargando } = useDatos(() => api.aprendizaje(), [versiones.historial]);

  return (
    <div className="vista vista-datos">
      <CabeceraVista icono="aprendizaje" titulo="Aprendizaje" pregunta="¿El Entrenamiento con fotos enseña a separar mejor?" />
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
                    <Explicacion>Porcentaje de acierto en la 1.ª, 2.ª, 3.ª… pregunta de cada sesión de Entrenamiento. Si la gente aprende, la línea sube.</Explicacion>
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
          <p className="atenuado pie">
            Límites: son fotos del dataset (no la máquina), pocas sesiones y las fotos pueden repetirse entre sesiones. No se afirma significancia estadística.
          </p>
        </>
      )}
    </div>
  );
}
