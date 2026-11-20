// Estadísticas del sistema (GET /api/estadisticas): el panel solo las muestra.
// Orden: la respuesta (anillo de acierto) → casos que necesitaron ayuda → detalle en pestañas.
import { useState } from 'react';
import { api } from '../api.js';
import { useEnVivo } from '../estado.jsx';
import { categoria } from '../categorias.js';
import { Cargando, IconoCategoria, MensajeError, Numero, pct, useDatos } from '../componentes/Comun.jsx';
import { MatrizConfusion } from '../componentes/Graficas.jsx';
import { CabeceraVista } from '../componentes/Efectos.jsx';
import { Anillo, Explicacion, Pestanas, Segmentado } from '../componentes/Paneles.jsx';

function TarjetasCategoria({ datos }) {
  return (
    <>
      <div className="tarjetas-cat">
        {[0, 1, 2].map((id) => {
          const c = categoria(id);
          const f = datos.por_categoria?.[id];
          return (
            <article key={id} className="tarjeta-cat" data-cat={c.clave} style={{ '--cat': c.hex }}>
              <header><IconoCategoria id={id} tam={22} /> {c.nombre}</header>
              <Anillo valor={f?.precision ?? null} color={c.hex} tam={112} detalle="precisión" />
              <p><strong>{f?.aciertos ?? 0}</strong> bien de <strong>{f?.conteo ?? 0}</strong></p>
            </article>
          );
        })}
      </div>
      <Explicacion>Precisión = de los residuos que eran de esa categoría, cuántos fueron al bote correcto.</Explicacion>
    </>
  );
}

export default function Estadisticas() {
  const { versiones } = useEnVivo();
  const [simulado, setSimulado] = useState('incluir');
  const { datos, error, cargando } = useDatos(() => api.estadisticas(simulado), [simulado, versiones.historial]);

  const ayuda = datos ? [
    { valor: datos.dudosos, nombre: 'Dudosos', texto: 'la IA no estaba segura y decidió una persona' },
    { valor: datos.corregidos, nombre: 'Corregidos', texto: 'alguien cambió la categoría después' },
    { valor: datos.no_reconocidos ?? 0, nombre: 'No reconocidos', texto: 'objetos que la IA nunca había visto' },
    { valor: datos.fotos_no_validas ?? 0, nombre: 'Fotos no válidas', texto: 'oscuras o borrosas: no se clasificaron' },
  ] : [];

  return (
    <div className="vista vista-datos">
      <CabeceraVista icono="estadisticas" titulo="Estadísticas" pregunta="¿Qué tan bien está separando la máquina?">
        <Segmentado etiqueta="Datos" valor={simulado} alCambiar={setSimulado} opciones={[
          { clave: 'incluir', nombre: 'Todos' },
          { clave: 'excluir', nombre: 'Solo reales' },
          { clave: 'solo', nombre: 'Solo simulados' },
        ]} />
      </CabeceraVista>
      <MensajeError error={error} />
      {cargando && !datos && <Cargando />}
      {datos && (
        <>
          {datos.incluye_simulados && <span className="rotulo rotulo-simulado">INCLUYE DATOS SIMULADOS</span>}
          <section className="tarjeta resumen-principal revelar">
            <Anillo valor={datos.tasa_acierto} tam={170} texto={pct(datos.tasa_acierto, 1)} detalle="de acierto" />
            <div className="resumen-textos">
              <p className="frase-grande">
                De <strong>{datos.muestra}</strong> residuos, la máquina mandó <strong>{pct(datos.tasa_acierto, 0)}</strong> al bote correcto.
              </p>
              <div className="resumen-chico">
                <div><strong>{datos.tiempo_promedio_ms ? `${(datos.tiempo_promedio_ms / 1000).toFixed(1)} s` : '—'}</strong><span>por residuo (tiempo de máquina)</span></div>
                <div><strong>{datos.muestra}</strong><span>residuos con categoría final</span></div>
              </div>
            </div>
          </section>

          <h2 className="titulo-seccion">Casos que necesitaron ayuda</h2>
          <div className="ayuda-lista">
            {ayuda.map((a) => (
              <div key={a.nombre} className="cifra cifra-ayuda">
                <Numero valor={a.valor ?? 0} clase="cifra-valor" />
                <div className="cifra-etiqueta">{a.nombre}</div>
                <div className="cifra-detalle">{a.texto}</div>
              </div>
            ))}
          </div>

          <section className="tarjeta">
            <Pestanas pestanas={[
              { id: 'categoria', titulo: 'Por categoría', contenido: <TarjetasCategoria datos={datos} /> },
              {
                id: 'matriz', titulo: 'Matriz',
                contenido: (
                  <>
                    <MatrizConfusion matriz={datos.matriz_confusion} />
                    <Explicacion>Cada fila es la categoría real y cada columna el bote al que la mandó la IA. La diagonal (✓) son los aciertos; lo demás, errores.</Explicacion>
                  </>
                ),
              },
              {
                id: 'desviados', titulo: 'Desviados',
                contenido: (
                  <>
                    <p className="frase-clave">Residuos que no terminaron en la basura mezclada gracias a la separación:</p>
                    <ul className="lista-desviados">
                      {[0, 1, 2].map((id) => (
                        <li key={id} data-cat={categoria(id).clave}>
                          <IconoCategoria id={id} tam={18} /> <span>{categoria(id).nombre}</span>
                          <Numero valor={datos.desviados_por_categoria?.[id] ?? 0} clase="desviados-n" />
                        </li>
                      ))}
                    </ul>
                  </>
                ),
              },
            ]} />
          </section>
          <p className="atenuado pie">La categoría real es la final (con corrección, si la hubo). Los casos sin categoría final no cuentan.</p>
        </>
      )}
    </div>
  );
}
