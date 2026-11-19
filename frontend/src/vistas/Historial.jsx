// Historial filtrable con corrección manual (POST /api/clasificaciones/{id}/corregir).
import { useState } from 'react';
import { api, urlFoto } from '../api.js';
import { useEnVivo } from '../estado.jsx';
import { NOMBRE_ORIGEN, categoria } from '../categorias.js';
import { HISTORIAL_POR_PAGINA } from '../config.js';
import {
  Categoria, ChipRevision, MensajeError, Simulado, TEXTO_ESTADO_CLASIFICACION, fechaHora, pct, useAccion, useDatos,
} from '../componentes/Comun.jsx';

function Fila({ c, alCorregir }) {
  const [abierto, setAbierto] = useState(false);
  const { ejecutar, ocupado, error } = useAccion();
  async function corregir(id) {
    const r = await ejecutar(() => api.corregir(c.id, id));
    if (r) { setAbierto(false); alCorregir(); }
  }
  return (
    <tr className={c.dudoso ? 'fila-dudosa' : ''}>
      <td>{c.id}</td>
      <td>{fechaHora(c.fecha_hora)}</td>
      <td>{c.foto && <img className="miniatura" src={urlFoto(c.foto)} alt={`Foto #${c.id}`} loading="lazy" />}</td>
      <td>{c.oculto ? '(oculto)' : <Categoria id={c.pred_id} />} {c.dudoso && <ChipRevision />}</td>
      <td>{pct(c.confianza)}</td>
      <td>
        <Categoria id={c.final_id} vacio="Pendiente" />
        {TEXTO_ESTADO_CLASIFICACION[c.estado] && (
          <span className={`rotulo ${c.estado === 'error' ? 'rotulo-error' : 'rotulo-aviso'}`}>{TEXTO_ESTADO_CLASIFICACION[c.estado]}</span>
        )}
      </td>
      <td>{NOMBRE_ORIGEN[c.origen] || c.origen}</td>
      <td>{c.corregido ? 'Sí' : 'No'}</td>
      <td><Simulado si={!!c.simulado} /></td>
      <td>
        {!abierto && <button type="button" className="boton-secundario" onClick={() => setAbierto(true)}>Corregir</button>}
        {abierto && (
          <div className="corregir">
            {[0, 1, 2].map((id) => (
              <button key={id} type="button" disabled={ocupado} style={{ background: categoria(id).hex }}
                className="boton-mini" onClick={() => corregir(id)}>{categoria(id).nombre}</button>
            ))}
            <button type="button" className="boton-texto" onClick={() => setAbierto(false)}>Cancelar</button>
          </div>
        )}
        <MensajeError error={error} />
      </td>
    </tr>
  );
}

export default function Historial() {
  const { versiones } = useEnVivo();
  const [dudosos, setDudosos] = useState('');
  const [simulado, setSimulado] = useState('incluir');
  const [pagina, setPagina] = useState(0);
  const { datos, error, cargando, recargar } = useDatos(
    () => api.clasificaciones({ limit: HISTORIAL_POR_PAGINA, offset: pagina * HISTORIAL_POR_PAGINA, dudosos, simulado }),
    [dudosos, simulado, pagina, versiones.historial],
  );
  const total = datos?.total ?? 0;
  const paginas = Math.max(1, Math.ceil(total / HISTORIAL_POR_PAGINA));

  return (
    <div className="vista">
      <h1>Historial</h1>
      <div className="filtros">
        <label>Casos
          <select value={dudosos} onChange={(e) => { setDudosos(e.target.value); setPagina(0); }}>
            <option value="">Todos</option>
            <option value="1">Solo dudosos</option>
            <option value="0">Sin dudosos</option>
          </select>
        </label>
        <label>Datos simulados
          <select value={simulado} onChange={(e) => { setSimulado(e.target.value); setPagina(0); }}>
            <option value="incluir">Incluir</option>
            <option value="excluir">Excluir</option>
            <option value="solo">Solo simulados</option>
          </select>
        </label>
        <span className="atenuado">{total} registros</span>
      </div>
      <MensajeError error={error} />
      {cargando && !datos && <p className="atenuado">Cargando…</p>}
      {datos && (
        <div className="tabla-desplazable">
          <table className="tabla">
            <thead>
              <tr><th>#</th><th>Hora</th><th>Foto</th><th>Predicción</th><th>Confianza</th><th>Final</th><th>Origen</th><th>Corregido</th><th></th><th>Acción</th></tr>
            </thead>
            <tbody>
              {datos.items.map((c) => <Fila key={c.id} c={c} alCorregir={recargar} />)}
              {datos.items.length === 0 && <tr><td colSpan={10} className="atenuado">Sin registros.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      <div className="paginacion">
        <button type="button" className="boton-secundario" disabled={pagina === 0} onClick={() => setPagina((p) => p - 1)}>← Anterior</button>
        <span>Página {pagina + 1} de {paginas}</span>
        <button type="button" className="boton-secundario" disabled={pagina + 1 >= paginas} onClick={() => setPagina((p) => p + 1)}>Siguiente →</button>
      </div>
      <p className="atenuado pie">Una corrección desde el panel es decisión del operador: la foto se copia a dataset/&lt;clase&gt;/ para reentrenar.</p>
    </div>
  );
}
