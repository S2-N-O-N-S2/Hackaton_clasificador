// Historial filtrable con corrección manual (POST /api/clasificaciones/{id}/corregir).
import { useState } from 'react';
import { CabeceraVista } from '../componentes/Efectos.jsx';
import { api, urlFoto } from '../api.js';
import { useEnVivo } from '../estado.jsx';
import { NOMBRE_ORIGEN, categoria } from '../categorias.js';
import { HISTORIAL_POR_PAGINA } from '../config.js';
import {
  BotonCategoria, Cargando, Categoria, ChipRevision, MensajeError, RotuloMotivo, Simulado, TEXTO_ESTADO_CLASIFICACION,
  fechaHora, pct,
  useAccion, useDatos,
} from '../componentes/Comun.jsx';

function Fila({ c, alCorregir }) {
  const [abierto, setAbierto] = useState(false);
  const { ejecutar, ocupado, error } = useAccion();
  async function corregir(id) {
    // Si el residuo YA cayó en otro bote, corregir el dato no lo mueve: se avisa que hay que pasarlo a mano.
    const yaCayo = c.bote_id !== null && c.bote_id !== undefined && c.bote_id !== id;
    const r = await ejecutar(() => api.corregir(c.id, id), {
      ok: yaCayo
        ? `Caso #${c.id} corregido a ${categoria(id).nombre}. El residuo ya cayó en el bote ${categoria(c.bote_id)?.color}: muévelo a mano al bote ${categoria(id).color}.`
        : `Caso #${c.id} corregido a ${categoria(id).nombre}`,
    });
    if (r) { setAbierto(false); alCorregir(); }
  }
  // Escribir qué objeto es: el backend elige la categoría (keywords.json), como en la revisión.
  const [texto, setTexto] = useState('');
  const [aviso, setAviso] = useState(null);
  async function corregirPorObjeto(e) {
    e.preventDefault();
    if (!texto.trim()) return;
    const r = await ejecutar(() => api.corregirObjeto(c.id, texto.trim()), {
      ok: (r) => {
        if (r.accion !== 'corregido') return null;
        const id = r.clasificacion.final_id;
        const yaCayo = c.bote_id !== null && c.bote_id !== undefined && c.bote_id !== id;
        return yaCayo
          ? `Caso #${c.id}: ${r.intencion.objeto} → ${categoria(id).nombre}. Ya cayó en el bote ${categoria(c.bote_id)?.color}: muévelo a mano al ${categoria(id).color}.`
          : `Caso #${c.id}: ${r.intencion.objeto} → ${categoria(id).nombre} (bote ${categoria(id).color})`;
      },
    });
    if (!r) return;
    if (r.accion !== 'corregido') {
      setAviso(`No conozco «${texto.trim()}». Prueba con otra palabra (ej.: botella, cáscara de plátano, pila).`);
      return;
    }
    setAviso(null);
    setTexto('');
    setAbierto(false);
    alCorregir();
  }
  return (
    <tr className={`${c.dudoso ? 'fila-dudosa' : ''} ${c.motivo_dudoso === 'desconocido' || c.motivo_dudoso === 'foto_no_valida' ? 'fila-no-reconocida' : ''}`}>
      <td data-etiqueta="Caso">#{c.id}</td>
      <td data-etiqueta="Hora">{fechaHora(c.fecha_hora)}</td>
      <td className="celda-foto">{c.foto && <img className="miniatura" src={urlFoto(c.foto)} alt={`Foto #${c.id}`} loading="lazy" />}</td>
      <td data-etiqueta="Predicción">{c.oculto ? '(oculto)' : <Categoria id={c.pred_id} vacio="Sin clasificar" />} {c.dudoso && <ChipRevision />}
        <RotuloMotivo motivo={c.motivo_dudoso} /></td>
      <td data-etiqueta="Confianza">{pct(c.confianza)}</td>
      <td data-etiqueta="Final">
        <Categoria id={c.final_id} vacio="Pendiente" />
        {TEXTO_ESTADO_CLASIFICACION[c.estado] && (
          <span className={`rotulo ${c.estado === 'error' ? 'rotulo-error' : 'rotulo-aviso'}`}>{TEXTO_ESTADO_CLASIFICACION[c.estado]}</span>
        )}
      </td>
      <td data-etiqueta="Origen">{NOMBRE_ORIGEN[c.origen] || c.origen}</td>
      <td data-etiqueta="Corregido">{c.corregido ? 'Sí' : 'No'}</td>
      <td>{c.simulado ? <Simulado /> : null}</td>
      <td className="celda-acciones">
        {!abierto && <button type="button" className="boton-secundario" onClick={() => setAbierto(true)}>Corregir</button>}
        {abierto && (
          <div className="corregir">
            <form className="revision-objeto" onSubmit={corregirPorObjeto}>
              <label htmlFor={`objeto-${c.id}`} className="sr-only">¿Qué objeto es?</label>
              <input id={`objeto-${c.id}`} type="text" value={texto} maxLength={120} autoComplete="off" autoFocus
                placeholder="¿Qué objeto es? Ej.: botella" disabled={ocupado}
                onChange={(e) => { setTexto(e.target.value); setAviso(null); }} />
              <button type="submit" className="boton-principal" disabled={ocupado || !texto.trim()}>Listo</button>
            </form>
            {aviso && <p className="texto-error">{aviso}</p>}
            <details className="revision-operador">
              <summary>Soy operador: elegir el bote</summary>
              {[0, 1, 2].map((id) => (
                <BotonCategoria key={id} id={id} disabled={ocupado} onClick={() => corregir(id)} />
              ))}
            </details>
            <button type="button" className="boton-texto" onClick={() => { setAbierto(false); setAviso(null); }}>Cancelar</button>
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
      <CabeceraVista icono="historial" titulo="Historial" pregunta="Cada residuo que pasó por la máquina, con su foto y cómo se decidió." />
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
      {cargando && !datos && <Cargando />}
      {datos && (
        <div className="tabla-desplazable">
          <table className="tabla tabla-tarjetas">
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
