// "¿Le ganas a la IA?" (especificación 12.2). El panel solo muestra lo que calcula el backend:
// nivel de certeza, tono, título y explicación vienen en la Retroalimentacion (contrato 2.3).
import { api } from '../api.js';
import { useCuentaRegresiva, useEnVivo } from '../estado.jsx';
import { categoria } from '../categorias.js';
import { BotonesCategoria, Categoria, MensajeError, pct, Tarjeta, useAccion } from '../componentes/Comun.jsx';

const FUENTE = { ia: 'la IA', operador: 'el operador', etiqueta_real: 'la etiqueta real del residuo' };
const NIVEL = { verificada: 'Verificada', alta: 'Alta', media: 'Media', baja: 'Baja' };
const ESTADOS_DESPUES = ['RETROALIMENTACION', 'REVISION', 'VERIFICAR_BOTE', 'BOTE_LLENO', 'POSICIONAR', 'SOLTAR',
  'REGISTRAR', 'ACTUALIZAR_NIVEL', 'HOME', 'PENDIENTE'];

function colorRetro(retro) {
  if (retro.correcto === null || retro.correcto === undefined) return 'amarillo';
  if (retro.tono === 'prudente') return 'amarillo';
  return retro.correcto ? 'verde' : 'rojo';
}

function Marcador({ sesion, retro }) {
  const m = sesion?.activa ? sesion : retro?.marcador;
  if (!m) return null;
  return (
    <div className="marcador">
      <span>Aciertos <strong>{m.aciertos}/{m.intentos}</strong></span>
      <span>Racha <strong>{m.racha}</strong></span>
      <span>Mejor racha <strong>{m.mejor_racha}</strong></span>
    </div>
  );
}

function PantallaRetro({ retro, estado }) {
  const segundos = useCuentaRegresiva();
  const { ejecutar, ocupado, error } = useAccion();
  const ref = categoria(retro.categoria_referencia);
  const enPantalla = estado === 'RETROALIMENTACION';
  return (
    <div className={`retro retro-${colorRetro(retro)}`}>
      <div className="retro-titulo">{retro.titulo}</div>
      <div className="retro-datos">
        <div>
          <span className="atenuado">Tu respuesta</span>
          <Categoria id={retro.respuesta_usuario} grande vacio="Sin respuesta" />
        </div>
        <div>
          <span className="atenuado">{retro.tono === 'prudente' && ref ? 'Probablemente va en' : 'Va en'}</span>
          {ref ? <Categoria id={retro.categoria_referencia} grande /> : <span className="chip chip-grande chip-vacio">Lo decide el operador</span>}
        </div>
        <div>
          <span className="atenuado">Confianza de la IA</span>
          <strong className="retro-confianza">IA {pct(retro.confianza_ia)} segura</strong>
          <span className="atenuado">Referencia: {FUENTE[retro.fuente_referencia] || retro.fuente_referencia} · certeza {NIVEL[retro.nivel_certeza] || retro.nivel_certeza}</span>
        </div>
      </div>
      {retro.explicacion_larga && <p className="retro-explicacion">{retro.explicacion_larga}</p>}
      {retro.dato_categoria && <p className="retro-dato">💡 {retro.dato_categoria}</p>}
      {retro.recalificada && <p className="retro-dato">El operador te dio la razón: la adivinanza se recalificó como correcta.</p>}
      {enPantalla && (
        <div className="retro-acciones">
          {retro.puede_reportar && (
            <button type="button" className={`boton-reportar ${retro.tono === 'prudente' ? 'destacado' : ''}`}
              disabled={ocupado} onClick={() => ejecutar(() => api.reportarError())}>
              Creo que la IA se equivocó (tecla *)
            </button>
          )}
          <button type="button" className="boton-secundario" disabled={ocupado} onClick={() => ejecutar(() => api.continuar())}>
            Continuar (tecla B){segundos !== null ? ` · ${segundos} s` : ''}
          </button>
        </div>
      )}
      {!enPantalla && <p className="atenuado">El residuo va al bote de referencia, nunca al elegido por el usuario.</p>}
      <MensajeError error={error} />
    </div>
  );
}

export default function Juego() {
  const { maquina, retro, sesion } = useEnVivo();
  const segundos = useCuentaRegresiva();
  const { ejecutar, ocupado, error } = useAccion();
  const estado = maquina?.estado;
  const modo = maquina?.modo;

  let contenido;
  if (estado === 'ESPERA_ADIVINANZA') {
    contenido = (
      <div className="juego-pregunta">
        <h1 className="titulo-grande">¿A qué bote va?</h1>
        {segundos !== null && <div className="cuenta-grande">{segundos}</div>}
        <BotonesCategoria deshabilitado={ocupado} alElegir={(id) => ejecutar(() => api.adivinar(id))} />
      </div>
    );
  } else if (retro && ESTADOS_DESPUES.includes(estado)) {
    contenido = <PantallaRetro retro={retro} estado={estado} />;
  } else if (modo === 'adivina' && estado === 'ESPERA_OBJETO') {
    contenido = (
      <div className="juego-pregunta">
        <h1 className="titulo-grande">Coloca el residuo en la bandeja</h1>
        <p className="atenuado">La IA lo clasificará en secreto y tú intentarás adivinar.</p>
        <button type="button" className="boton-secundario" disabled={ocupado} onClick={() => ejecutar(() => api.elegirModo('menu'))}>
          Volver al menú (tecla #)
        </button>
      </div>
    );
  } else if (modo === 'adivina' && (estado === 'CAPTURA' || estado === 'CLASIFICACION')) {
    contenido = <h1 className="titulo-grande centrado">La IA está pensando… (resultado oculto)</h1>;
  } else {
    const libre = estado === 'MENU' || estado === 'ESPERA_OBJETO';
    contenido = (
      <div className="juego-pregunta">
        <h1 className="titulo-grande">¿Le ganas a la IA?</h1>
        <p>Adivina en qué bote va cada residuo. Si fallas, te explicamos por qué.</p>
        <button type="button" className="boton-menu boton-adivina" disabled={ocupado || !libre}
          onClick={() => ejecutar(() => api.elegirModo('adivina'))}>
          <span className="tecla">2</span> Jugar
        </button>
        {!libre && <p className="atenuado">Espera a que termine el residuo actual.</p>}
      </div>
    );
  }

  return (
    <div className="vista-juego">
      <Marcador sesion={sesion} retro={retro} />
      {contenido}
      <MensajeError error={error} />
      <Tarjeta titulo="Cómo se califica">
        <p className="atenuado">
          Si la IA está muy segura (≥ umbral de tono firme) el resultado es firme: verde o rojo. Si su certeza es media,
          el tono es prudente (amarillo) y puedes reportar que crees que se equivocó. Si la IA tampoco está segura,
          decide un operador. Los umbrales y la calificación los calcula el backend.
        </p>
      </Tarjeta>
    </div>
  );
}
