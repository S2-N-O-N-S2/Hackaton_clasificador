// Estadísticas del sistema (GET /api/estadisticas): el panel solo las muestra.
import { useState } from 'react';
import { api } from '../api.js';
import { useEnVivo } from '../estado.jsx';
import { categoria } from '../categorias.js';
import { Cargando, Cifra, IconoCategoria, MensajeError, Numero, Tarjeta, pct, useDatos } from '../componentes/Comun.jsx';
import { BarrasHorizontales, MatrizConfusion } from '../componentes/Graficas.jsx';

export default function Estadisticas() {
  const { versiones } = useEnVivo();
  const [simulado, setSimulado] = useState('incluir');
  const { datos, error, cargando } = useDatos(() => api.estadisticas(simulado), [simulado, versiones.historial]);

  return (
    <div className="vista">
      <h1>Estadísticas</h1>
      <div className="filtros">
        <label>Datos simulados
          <select value={simulado} onChange={(e) => setSimulado(e.target.value)}>
            <option value="incluir">Incluir</option>
            <option value="excluir">Excluir (solo datos reales)</option>
            <option value="solo">Solo simulados</option>
          </select>
        </label>
        {datos?.incluye_simulados && <span className="rotulo rotulo-simulado">INCLUYE DATOS SIMULADOS</span>}
      </div>
      <MensajeError error={error} />
      {cargando && !datos && <Cargando />}
      {datos && (
        <>
          <div className="cifras">
            <Cifra etiqueta="Tasa de acierto" valor={pct(datos.tasa_acierto, 1)} progreso={datos.tasa_acierto} detalle={`n = ${datos.muestra}`} />
            <Cifra etiqueta="Tiempo promedio por residuo" valor={datos.tiempo_promedio_ms ? `${(datos.tiempo_promedio_ms / 1000).toFixed(1)} s` : '—'} detalle="tiempo de máquina" />
            <Cifra etiqueta="Dudosos" valor={datos.dudosos} />
            <Cifra etiqueta="Corregidos" valor={datos.corregidos} />
            <Cifra etiqueta="Objetos no reconocidos" valor={datos.no_reconocidos ?? 0} detalle="fueron a revisión" />
            <Cifra etiqueta="Fotos no válidas" valor={datos.fotos_no_validas ?? 0} detalle="no se clasificaron" />
          </div>
          <div className="rejilla-2">
            <Tarjeta titulo="Conteo y precisión por categoría">
              <table className="tabla">
                <thead><tr><th>Categoría</th><th>Conteo</th><th>Aciertos</th><th>Precisión</th></tr></thead>
                <tbody>
                  {[0, 1, 2].map((id) => {
                    const f = datos.por_categoria?.[id];
                    return (
                      <tr key={id}>
                        <td className="celda-cat" data-cat={categoria(id).clave}><IconoCategoria id={id} tam={16} /> {categoria(id).nombre}</td>
                        <td>{f?.conteo ?? 0}</td><td>{f?.aciertos ?? 0}</td><td>{pct(f?.precision)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <BarrasHorizontales items={[0, 1, 2].map((id) => ({
                id, etiqueta: categoria(id).nombre, valor: datos.por_categoria?.[id]?.precision ?? null, color: categoria(id).hex,
              }))} />
            </Tarjeta>
            <Tarjeta titulo="Matriz de confusión">
              <MatrizConfusion matriz={datos.matriz_confusion} />
            </Tarjeta>
            <Tarjeta titulo="Residuos desviados de la basura mezclada">
              <ul className="lista-desviados">
                {[0, 1, 2].map((id) => (
                  <li key={id} data-cat={categoria(id).clave}>
                    <IconoCategoria id={id} tam={18} /> <span>{categoria(id).nombre}</span>
                    <Numero valor={datos.desviados_por_categoria?.[id] ?? 0} clase="desviados-n" />
                  </li>
                ))}
              </ul>
            </Tarjeta>
          </div>
          <p className="atenuado pie">La categoría real es la final (con corrección, si la hubo). Los casos sin categoría final no cuentan.</p>
        </>
      )}
    </div>
  );
}
