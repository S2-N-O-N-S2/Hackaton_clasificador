// "¿Le ganas a la IA?": práctica con fotos del dataset.
// El juego "con la máquina" (residuo real + ESPERA_ADIVINANZA) se quitó el 20-nov por decisión del equipo:
// la máquina solo clasifica; para jugar se usan las fotos (componentes/Practica.jsx, rutas /api/juego/fotos).
import Practica from '../componentes/Practica.jsx';
import { BotonSonido, CabeceraVista } from '../componentes/Efectos.jsx';

export default function Juego() {
  return (
    <div className="vista-juego">
      <CabeceraVista icono="juego" titulo="¿Le ganas a la IA?" pregunta="Adivina en qué bote va cada residuo y descubre si separas mejor que la IA.">
        <BotonSonido />
      </CabeceraVista>
      <Practica />
    </div>
  );
}
