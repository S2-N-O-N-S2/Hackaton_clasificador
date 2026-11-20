// Botes (especificación 13): nivel ESTIMADO por conteo de piezas, vaciado e historial.
import { CabeceraVista } from '../componentes/Efectos.jsx';
import { api } from '../api.js';
import { useEnVivo } from '../estado.jsx';
import { categoria } from '../categorias.js';
import {
  Cargando, Estimado, IconoCategoria, MensajeError, NivelBote, Numero, Tarjeta, fechaHora, useAccion, useDatos,
} from '../componentes/Comun.jsx';

export default function Botes() {
  const { botes, versiones } = useEnVivo();
  const datos = useDatos(() => api.botes(), [versiones.historial]);
  const { ejecutar, ocupado, error } = useAccion();
  const lista = botes || datos.datos?.botes || [];

  async function vaciar(b) {
    if (!window.confirm(`¿Confirmas que el bote ${b.color} (${b.nombre}) ya se vació?`)) return;
    const r = await ejecutar(() => api.vaciarBote(b.id), { ok: `Bote ${b.color} marcado como vaciado` });
    if (r) datos.recargar();
  }

  return (
    <div className="vista">
      <CabeceraVista icono="botes" titulo="Botes" pregunta="¿Cuánto le cabe todavía a cada bote? (sin sensor: se estima contando piezas)">
        <Estimado />
      </CabeceraVista>
      <MensajeError error={error || datos.error} />
      <div className="rejilla-3">
        {lista.map((b) => (
          <Tarjeta key={b.id} titulo={`Bote ${b.color}`} className={`tarjeta-bote ${b.bloqueado ? 'bloqueado' : ''}`}>
            <NivelBote bote={b} />
            <ul className="lista-datos">
              <li>Capacidad calibrada: <strong>{b.capacidad_piezas}</strong> piezas</li>
              <li>Aviso al <strong>{Math.round(b.umbral_aviso * 100)} %</strong></li>
              <li>Último vaciado: {fechaHora(b.ultimo_vaciado)}</li>
              {b.bloqueado && <li className="texto-error">Bloqueado: no se suelta nada aquí hasta vaciarlo.</li>}
            </ul>
            <button type="button" className="boton-principal" disabled={ocupado} onClick={() => vaciar(b)}>
              Marcar como vaciado
            </button>
          </Tarjeta>
        ))}
      </div>

      <div className="rejilla-2">
        <Tarjeta titulo="Residuos desviados de la basura mezclada">
          {datos.datos ? (
            <ul className="lista-desviados">
              {[0, 1, 2].map((id) => (
                <li key={id} data-cat={categoria(id).clave}>
                  <IconoCategoria id={id} tam={18} /> <span>{categoria(id).nombre}</span>
                  <Numero valor={datos.datos.desviados_por_categoria?.[id] ?? 0} clase="desviados-n" />
                </li>
              ))}
            </ul>
          ) : <Cargando />}
        </Tarjeta>
        <Tarjeta titulo="Historial de vaciados">
          {datos.datos?.vaciados?.length ? (
            <div className="tabla-desplazable">
            <table className="tabla">
              <thead><tr><th>Fecha</th><th>Bote</th><th>Piezas</th><th>Origen</th></tr></thead>
              <tbody>
                {datos.datos.vaciados.map((v) => (
                  <tr key={v.id}>
                    <td>{fechaHora(v.fecha_hora)}</td>
                    <td>{categoria(v.bote_id)?.nombre}</td>
                    <td>{v.piezas_al_vaciar}</td>
                    <td>{v.origen}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          ) : <p className="atenuado">Sin vaciados registrados.</p>}
        </Tarjeta>
      </div>
      <p className="atenuado pie">La capacidad de cada bote se ajusta en Configuración.</p>
    </div>
  );
}
