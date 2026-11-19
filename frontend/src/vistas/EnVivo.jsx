// En vivo: última foto, resultado de la IA, estado de la máquina, revisión y botes.
import { api } from '../api.js';
import { useCuentaRegresiva, useEnVivo } from '../estado.jsx';
import { NOMBRE_ESTADO, NOMBRE_ORIGEN } from '../categorias.js';
import {
  Barra, BotonesCategoria, Categoria, ChipRevision, Foto, MensajeError, NivelBote, Probabilidades,
  Simulado, Tarjeta, TEXTO_MOTIVO, hora, pct, useAccion, useDatos,
} from '../componentes/Comun.jsx';

function Resultado({ caso, umbrales }) {
  if (!caso) return <p className="atenuado">Esperando el primer residuo…</p>;
  if (caso.oculto) {
    return <p className="resultado-oculto">Resultado oculto: alguien está jugando "¿Le ganas a la IA?".</p>;
  }
  return (
    <div className="resultado">
      <div className="resultado-principal">
        <span className="atenuado">La IA dice</span>
        <Categoria id={caso.pred_id} grande />
        {caso.dudoso && <ChipRevision />}
      </div>
      <div>
        <span className="atenuado">Confianza</span>
        <Barra valor={caso.confianza} marca={umbrales?.umbral_general ?? null} alto={34}
          color={caso.dudoso ? '#F2B705' : '#1f2937'} />
      </div>
      {caso.dudoso && <p className="texto-revision">{TEXTO_MOTIVO[caso.motivo_dudoso] || 'Caso dudoso'}</p>}
      <Probabilidades probabilidades={caso.probabilidades}
        umbralGeneral={umbrales?.umbral_general} umbralPeligroso={umbrales?.umbral_peligroso} />
      {umbrales && (
        <p className="atenuado pie">
          Umbral vigente: {pct(umbrales.umbral_general)} · umbral de peligroso: {pct(umbrales.umbral_peligroso)} (líneas negras)
        </p>
      )}
      <div className="resultado-final">
        <span>Destino final:</span>
        <Categoria id={caso.final_id} vacio="Pendiente" />
        {caso.corregido && <span className="rotulo rotulo-aviso">corregido</span>}
        <span className="atenuado">origen: {NOMBRE_ORIGEN[caso.origen] || caso.origen}</span>
      </div>
    </div>
  );
}

function PanelRevision({ revision }) {
  const segundos = useCuentaRegresiva();
  const { ejecutar, ocupado, error } = useAccion();
  return (
    <Tarjeta titulo="Revisión: la IA no está segura" className="tarjeta-revision"
      extra={segundos !== null && <span className="cuenta-chica">{segundos} s</span>}>
      <p>
        {TEXTO_MOTIVO[revision?.motivo] || 'Caso dudoso'}. El residuo se queda en la bandeja.
        ¿En qué bote va? (decisión del operador: la foto va directo al dataset)
      </p>
      <BotonesCategoria deshabilitado={ocupado} alElegir={(id) => ejecutar(() => api.resolverRevision(id))} />
      <button type="button" className="boton-secundario" disabled={ocupado} onClick={() => ejecutar(() => api.dejarPendiente())}>
        Dejar pendiente (un operador lo retira)
      </button>
      <MensajeError error={error} />
    </Tarjeta>
  );
}

export default function EnVivo() {
  const { maquina, captura, ultimaClasificacion, revision, botes } = useEnVivo();
  const segundos = useCuentaRegresiva();
  const config = useDatos(() => api.config(), []);
  const umbrales = config.datos?.valores;
  const caso = maquina?.caso_actual || ultimaClasificacion;
  const foto = caso?.foto || captura?.foto;
  const enRevision = maquina?.estado === 'REVISION';

  return (
    <div className="vista-en-vivo">
      <div className="rejilla-en-vivo">
        <Tarjeta titulo="Última foto" extra={caso && <span className="atenuado">#{caso.id} · {hora(caso.fecha_hora)}</span>}>
          <Foto foto={foto} simulado={caso?.simulado} />
        </Tarjeta>

        <Tarjeta titulo="Resultado" extra={<Simulado si={!!caso?.simulado} />}>
          <Resultado caso={caso} umbrales={umbrales} />
        </Tarjeta>

        <Tarjeta titulo="Estado de la máquina">
          <div className="estado-grande">{NOMBRE_ESTADO[maquina?.estado] || '—'}</div>
          <p className="mensaje-maquina">{maquina?.mensaje}</p>
          {segundos !== null && <p className="cuenta-chica">Quedan {segundos} s</p>}
          {maquina && (
            <ul className="lista-hardware">
              <li>Arduino: {maquina.serial?.conectado ? `conectado (${maquina.serial.puerto})` : 'DESCONECTADO'} <Simulado si={!!maquina.serial?.simulado} /></li>
              <li>Cámara: {maquina.camara?.disponible ? `índice ${maquina.camara.indice}` : 'NO DISPONIBLE'} <Simulado si={!!maquina.camara?.simulada} /></li>
              <li>Modelo: {maquina.modelo?.cargado ? maquina.modelo.version : 'NO CARGADO'} <Simulado si={!!maquina.modelo?.simulado} /></li>
            </ul>
          )}
        </Tarjeta>

        {enRevision && <PanelRevision revision={revision} />}

        <Tarjeta titulo="Nivel de los botes" className="tarjeta-botes">
          {botes ? botes.map((b) => <NivelBote key={b.id} bote={b} compacto />) : <p className="atenuado">Cargando…</p>}
        </Tarjeta>
      </div>
    </div>
  );
}
