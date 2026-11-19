// Inicio / Menú: los mismos dos modos que el teclado (1 y 2) y la voz.
import { api } from '../api.js';
import { useEnVivo } from '../estado.jsx';
import { Lcd, MensajeError, Tarjeta, useAccion } from '../componentes/Comun.jsx';

export default function Inicio() {
  const { maquina, ultimaTecla } = useEnVivo();
  const { ejecutar, ocupado, error } = useAccion();
  const estado = maquina?.estado;
  const puedeElegir = estado === 'MENU' || estado === 'ESPERA_OBJETO';

  async function elegir(modo) {
    const r = await ejecutar(() => api.elegirModo(modo), {
      ok: modo === 'menu' ? 'De vuelta al menú' : `Modo ${modo === 'ia' ? 'IA' : 'Adivina'}: coloca el residuo en la bandeja`,
    });
    if (r && modo === 'adivina') window.location.hash = '#/juego';
  }

  return (
    <div className="vista-inicio">
      <h1 className="titulo-grande">¿Cómo quieres separar tu residuo?</h1>
      <div className="botones-menu">
        <button type="button" className={`boton-menu boton-ia ${maquina?.modo === 'ia' ? 'elegido' : ''}`}
          disabled={ocupado || !puedeElegir} onClick={() => elegir('ia')}>
          {maquina?.modo === 'ia' && <span className="elegido-marca">Modo actual</span>}
          <span className="tecla">1</span>
          <span>Usar IA</span>
          <small>La IA clasifica y el carrusel lo deposita</small>
        </button>
        <button type="button" className={`boton-menu boton-adivina ${maquina?.modo === 'adivina' ? 'elegido' : ''}`}
          disabled={ocupado || !puedeElegir} onClick={() => elegir('adivina')}>
          {maquina?.modo === 'adivina' && <span className="elegido-marca">Modo actual</span>}
          <span className="tecla">2</span>
          <span>Adivinar</span>
          <small>¿Le ganas a la IA?</small>
        </button>
      </div>
      {!puedeElegir && estado && (
        <p className="atenuado centrado">Hay un residuo en proceso: espera a que termine el ciclo.</p>
      )}
      {maquina?.modo && estado === 'ESPERA_OBJETO' && (
        <p className="centrado">
          Coloca el residuo en la bandeja.{' '}
          <button type="button" className="boton-secundario" disabled={ocupado} onClick={() => elegir('menu')}>
            Volver al menú
          </button>
        </p>
      )}
      {maquina && !maquina.modo && estado === 'MENU' && (
        <p className="atenuado centrado">
          Si colocas un residuo sin elegir, se usa el modo por defecto: <strong>{maquina.modo_por_defecto === 'adivina' ? 'Adivina' : 'IA'}</strong>.
        </p>
      )}
      <MensajeError error={error} />

      <div className="rejilla-2">
        <Tarjeta titulo="Pantalla del Arduino (espejo de la LCD)">
          <Lcd lineas={maquina?.lcd} />
          <p className="mensaje-maquina">{maquina?.mensaje}</p>
        </Tarjeta>
        <Tarjeta titulo="Teclado 4×4">
          <p>Última tecla: <span className="tecla tecla-grande llegada" key={ultimaTecla?.recibido}>{ultimaTecla ? ultimaTecla.tecla : '—'}</span></p>
          <p className="atenuado">El panel y el teclado comparten el mismo estado: lo que elijas aquí se ve en la LCD y viceversa.</p>
        </Tarjeta>
      </div>
    </div>
  );
}
