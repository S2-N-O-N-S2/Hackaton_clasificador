// En vivo: última foto, resultado de la IA, estado de la máquina, revisión y botes.
import { useEffect, useRef, useState } from 'react';
import { api } from '../api.js';
import { MODO_MOCK } from '../config.js';
import { useCuentaRegresiva, useEnVivo } from '../estado.jsx';
import { NOMBRE_ESTADO, NOMBRE_ORIGEN, REVISION, categoria } from '../categorias.js';
import { Carrusel } from '../componentes/Graficas.jsx';
import {
  Barra, BotonesCategoria, Categoria, ChipRevision, Foto, MensajeError, NivelBote, Probabilidades,
  AvisoMotivo, Cargando, Simulado, Tarjeta, TEXTO_MOTIVO, hora, pct, useAccion, useDatos,
} from '../componentes/Comun.jsx';

const EN_BOTE = ['POSICIONAR', 'SOLTAR', 'REGISTRAR', 'ACTUALIZAR_NIVEL'];
const EN_BANDEJA = ['CAPTURA', 'CLASIFICACION', 'ESPERA_ADIVINANZA', 'RETROALIMENTACION', 'REVISION', 'VERIFICAR_BOTE',
  'BOTE_LLENO', 'POSICIONAR', 'PENDIENTE'];

function Resultado({ caso, umbrales }) {
  if (!caso) return <p className="atenuado">Esperando el primer residuo…</p>;
  if (caso.oculto) {
    return <p className="resultado-oculto">Resultado oculto: modo Adivina.</p>;
  }
  return (
    <div className="resultado">
      {/* Objeto no reconocido / foto mala: se ve primero y en grande, antes que la categoría. */}
      {caso.dudoso && <AvisoMotivo motivo={caso.motivo_dudoso} grande />}
      {/* key = id del caso: al llegar una clasificación nueva la placa "cae" por la trampilla (una sola vez). */}
      <div className="resultado-principal llegada" key={caso.id}>
        <span className="atenuado">{caso.motivo_dudoso === 'desconocido' ? 'La IA diría' : 'La IA dice'}</span>
        <Categoria id={caso.pred_id} grande vacio="Sin clasificar" />
        {caso.dudoso && <ChipRevision />}
      </div>
      <div>
        <span className="atenuado">Confianza</span>
        <Barra valor={caso.confianza} marca={umbrales?.umbral_general ?? null} alto={24}
          color={caso.dudoso ? '#F2B705' : '#0E7C86'} />
      </div>
      <Probabilidades probabilidades={caso.probabilidades}
        umbralGeneral={umbrales?.umbral_general} umbralPeligroso={umbrales?.umbral_peligroso} />
      {umbrales && (
        <p className="atenuado pie">
          Umbral vigente: {pct(umbrales.umbral_general)} · umbral de peligroso: {pct(umbrales.umbral_peligroso)} (marcas oscuras)
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

// Estados en los que la cámara se ve EN VIVO. En cualquier otro (desde CAPTURA) la imagen se congela:
// primero en el último cuadro y, en cuanto existe, en la foto que tomó el ciclo.
const EN_REPOSO = ['MENU', 'ESPERA_OBJETO', 'OPERADOR', 'ERROR'];
const PAUSA_CUADROS_MS = 120;   // ~6–8 cuadros por segundo: suficiente para acomodar el residuo

// Pide cuadros uno tras otro mientras `activa`; al desactivarse se queda con el último (congelado).
function useCuadrosCamara(activa) {
  const [url, setUrl] = useState(null);
  const [hayCuadros, setHayCuadros] = useState(true);
  const actual = useRef(null);
  useEffect(() => {
    if (!activa || MODO_MOCK) return undefined;
    const control = new AbortController();
    let vivo = true;
    let vacios = 0;
    (async () => {
      while (vivo) {
        try {
          const blob = await api.cuadroCamara(control.signal);
          if (!vivo) break;
          if (blob) {
            const nueva = URL.createObjectURL(blob);
            if (actual.current) URL.revokeObjectURL(actual.current);
            actual.current = nueva;
            setUrl(nueva);
            vacios = 0;
            setHayCuadros(true);
          } else if (++vacios > 15) {
            setHayCuadros(false);   // simulación o cámara sin imagen
          }
        } catch {
          if (!vivo) break;
          setHayCuadros(false);
        }
        await new Promise((r) => setTimeout(r, PAUSA_CUADROS_MS));
      }
    })();
    return () => { vivo = false; control.abort(); };
  }, [activa]);
  useEffect(() => () => { if (actual.current) URL.revokeObjectURL(actual.current); }, []);
  return { url, hayCuadros };
}

// `casoActual` = el residuo de ESTE ciclo (no el anterior), para no congelar con una foto vieja.
function VistaCamara({ estado, foto, casoActual }) {
  const enVivo = !MODO_MOCK && EN_REPOSO.includes(estado);
  const { url, hayCuadros } = useCuadrosCamara(enVivo);
  // Congelada: la foto del ciclo en cuanto existe; mientras tanto, el último cuadro en vivo.
  const fotoCiclo = !enVivo && casoActual && !casoActual.oculto ? casoActual.foto : null;
  if (MODO_MOCK || !url || (enVivo && !hayCuadros) || fotoCiclo) {
    // Sin vista en vivo (simulación o cámara sin imagen) o con la foto del ciclo ya guardada.
    return <Foto foto={fotoCiclo || foto} simulado={casoActual?.simulado} />;
  }
  return (
    <div className="foto">
      <img src={url} alt={enVivo ? 'Cámara en vivo' : 'Foto congelada'} />
      <div className={`camara-rotulo ${enVivo ? 'en-vivo' : 'congelada'}`}>{enVivo ? 'EN VIVO' : 'FOTO TOMADA'}</div>
    </div>
  );
}

// «Tomar foto»: arranca el ciclo como lo haría el sensor IR (la máquina no lo tiene). También por voz: «listo».
function TomarFoto({ estado }) {
  const { ejecutar, ocupado, error } = useAccion();
  const puede = estado === 'MENU' || estado === 'ESPERA_OBJETO';
  const aviso = puede ? 'Pon el residuo frente a la cámara y presiona aquí (o di «listo» con el botón Hablar).'
    : estado === 'ERROR' ? 'La máquina está en falla segura (revisa el Arduino): no se puede tomar la foto.'
      : 'Hay un residuo en proceso: espera a que termine el ciclo.';
  return (
    <div className="tomar-foto centrado">
      <button type="button" className="boton-tomar-foto" disabled={ocupado || !puede}
        onClick={() => ejecutar(() => api.tomarFoto(), { ok: 'Tomando la foto…' })}>
        📷 Tomar foto
      </button>
      <p className={estado === 'ERROR' ? 'texto-error' : 'atenuado'}>{aviso}</p>
      <MensajeError error={error} />
    </div>
  );
}

// Qué responder según lo que el backend entendió (texto escrito o voz). El panel no interpreta nada.
function respuestaObjeto(r) {
  if (r?.accion === 'revision_resuelta') {
    const c = categoria(r.intencion?.valor);
    return { ok: true, texto: `Entendí: ${r.intencion?.objeto || r.texto_crudo} → ${c?.nombre} (bote ${c?.color})` };
  }
  return {
    ok: false,
    texto: r?.texto_crudo ? `No conozco «${r.texto_crudo}». Prueba con otra palabra (ej.: botella, cáscara de plátano, pila).`
      : 'No oí nada. Vuelve a intentarlo.',
  };
}

// Revisión: quien usa la máquina NO sabe la categoría; solo dice QUÉ OBJETO es (escrito o por voz) y el
// backend decide el bote con keywords.json. Los botones de bote quedan plegados para el operador.
function PanelRevision({ revision }) {
  const segundos = useCuentaRegresiva();
  const { ejecutar, ocupado, error } = useAccion();
  const [texto, setTexto] = useState('');
  const [respuesta, setRespuesta] = useState(null);
  const [escuchando, setEscuchando] = useState(false);

  async function enviar(e) {
    e.preventDefault();
    if (!texto.trim()) return;
    const r = await ejecutar(() => api.describirObjeto(texto.trim()));
    if (r) { setRespuesta(respuestaObjeto(r)); if (r.accion === 'revision_resuelta') setTexto(''); }
  }
  async function hablar() {
    setRespuesta(null);
    setEscuchando(true);
    const r = await ejecutar(() => api.escucharVoz());
    setEscuchando(false);
    if (r) setRespuesta(respuestaObjeto(r));
  }

  return (
    <Tarjeta titulo={revision?.motivo === 'desconocido' ? 'Objeto no reconocido: ¿qué es?'
      : revision?.motivo === 'foto_no_valida' ? 'Foto no válida: ¿qué es?' : 'La IA no está segura: ¿qué es?'}
      className="tarjeta-revision" extra={segundos !== null && <span className="cuenta-chica">{segundos} s</span>}>
      <p>
        {TEXTO_MOTIVO[revision?.motivo] || 'Caso dudoso'}. El residuo se queda frente a la cámara.
        Dinos <strong>qué objeto es</strong> y el sistema elige el bote.
      </p>
      <form className="revision-objeto" onSubmit={enviar}>
        <label htmlFor="revision-texto" className="sr-only">¿Qué objeto es?</label>
        <input id="revision-texto" type="text" value={texto} maxLength={120} autoComplete="off" autoFocus
          placeholder="Ej.: botella de agua, cáscara de plátano, pila…" disabled={ocupado}
          onChange={(e) => { setTexto(e.target.value); setRespuesta(null); }} />
        <button type="submit" className="boton-principal" disabled={ocupado || !texto.trim()}>Listo</button>
        <button type="button" className={`boton-secundario revision-voz ${escuchando ? 'escuchando' : ''}`} disabled={ocupado}
          onClick={hablar}>
          🎤 {escuchando ? 'Habla ahora…' : 'Decirlo por voz'}
        </button>
      </form>
      {respuesta && <p className={respuesta.ok ? 'revision-ok' : 'texto-error'} role="status">{respuesta.texto}</p>}
      <details className="revision-operador">
        <summary>Soy operador: elegir el bote directamente</summary>
        <p className="atenuado">Decisión del operador: la foto va directo al dataset.</p>
        <BotonesCategoria deshabilitado={ocupado} alElegir={(id) => ejecutar(() => api.resolverRevision(id), { ok: `Revisión resuelta: va al bote ${categoria(id)?.color}` })} />
      </details>
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
  const estado = maquina?.estado;
  // Solo para dibujar, siguiendo el estado que manda el backend (como se mueve la máquina real):
  // el disco sale de HOME al POSICIONAR y vuelve en HOME; el residuo está en la bandeja hasta SOLTAR.
  const idCarrusel = EN_BOTE.includes(estado) && caso && !caso.oculto ? (caso.final_id ?? null) : null;
  const residuo = estado === 'SOLTAR' ? 'cayendo' : EN_BANDEJA.includes(estado) ? 'en_bandeja' : 'ninguno';
  const efectoFoto = estado === 'CAPTURA' ? 'disparo' : estado === 'CLASIFICACION' ? 'analizando' : '';
  const tapaResultado = caso?.oculto ? undefined : caso?.dudoso ? REVISION.hex : categoria(caso?.pred_id)?.hex;

  return (
    <div className="vista-en-vivo">
      <TomarFoto estado={estado} />
      <div className="rejilla-en-vivo">
        <Tarjeta titulo="Cámara" extra={!EN_REPOSO.includes(estado) && caso && <span className="atenuado">#{caso.id} · {hora(caso.fecha_hora)}</span>}>
          {/* En vivo mientras espera; se congela al tomar la foto (flash) y muestra la línea de escaneo al clasificar. */}
          <div className={`foto-marco ${efectoFoto}`}>
            <VistaCamara estado={estado} foto={foto} casoActual={maquina?.caso_actual} />
          </div>
        </Tarjeta>

        <Tarjeta titulo="Resultado" tapa={tapaResultado} extra={<Simulado si={!!caso?.simulado} />}>
          <Resultado caso={caso} umbrales={umbrales} />
        </Tarjeta>

        <Tarjeta titulo="Estado de la máquina" tapa="#23332E">
          <div className="estado-grande">{NOMBRE_ESTADO[maquina?.estado] || '—'}</div>
          <p className="mensaje-maquina">{maquina?.mensaje}</p>
          {segundos !== null && <p className="cuenta-chica">Quedan {segundos} s</p>}
          <Carrusel categoriaId={idCarrusel} residuo={residuo}
            pie={idCarrusel === null ? 'Disco en HOME' : `Bote ${categoria(idCarrusel)?.color} bajo la trampilla`} />
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
          {botes ? botes.map((b) => <NivelBote key={b.id} bote={b} compacto />) : <Cargando />}
        </Tarjeta>
      </div>
    </div>
  );
}
