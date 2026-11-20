// Inicio / Menú: los dos modos (botones o voz). La máquina no tiene LCD ni teclado: su pantalla se ve aquí.
import { api } from '../api.js';
import { useEnVivo } from '../estado.jsx';
import { Lcd, MensajeError, Tarjeta, useAccion } from '../componentes/Comun.jsx';

export default function Inicio() {
  const { maquina } = useEnVivo();
  const { ejecutar, ocupado, error } = useAccion();
  const estado = maquina?.estado;
  const puedeElegir = estado === 'MENU' || estado === 'ESPERA_OBJETO';

  async function elegir(modo) {
    const r = await ejecutar(() => api.elegirModo(modo), {
      ok: modo === 'menu' ? 'De vuelta al menú' : `Modo ${modo === 'ia' ? 'IA' : 'Adivina'}: pon el residuo frente a la cámara`,
    });
    if (r && modo === 'ia') window.location.hash = '#/en-vivo';   // ahí está «Tomar foto» y se ve el resultado
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
        {/* El juego ya no usa la máquina (20-nov): solo lleva a la práctica con fotos, sin cambiar el modo. */}
        <a href="#/juego" className="boton-menu boton-adivina">
          <span className="tecla">2</span>
          <span>Entrenamiento</span>
          <small>Practica con fotos y compárate con la IA</small>
        </a>
      </div>
      {!puedeElegir && estado && (
        <p className="atenuado centrado">Hay un residuo en proceso: espera a que termine el ciclo.</p>
      )}
      {maquina?.modo && estado === 'ESPERA_OBJETO' && (
        <p className="centrado">
          Pon el residuo frente a la cámara y presiona «Tomar foto» en <a href="#/en-vivo">En vivo</a>.{' '}
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

      <Tarjeta titulo="Pantalla de la máquina">
        <Lcd lineas={maquina?.lcd} />
        <p className="mensaje-maquina">{maquina?.mensaje}</p>
        <p className="atenuado">Lo que la máquina le dice a quien la usa. Todo se maneja desde esta página o por voz (botón «Hablar»).</p>
      </Tarjeta>
    </div>
  );
}
