// Estructura del panel: encabezado, navegación por pestañas y la vista activa.
import { useEffect, useRef, useState } from 'react';
import { useEnVivo } from './estado.jsx';
import { NOMBRE_ESTADO } from './categorias.js';
import { MODO_MOCK } from './config.js';
import { BarraProceso, Notificaciones, Simulado } from './componentes/Comun.jsx';
import { BarraUrgente, Campana } from './componentes/Avisos.jsx';
import { Logotipo } from './componentes/Graficas.jsx';
import { BotonVoz } from './componentes/Voz.jsx';
import { BarraScroll, useRevelarAlScroll } from './componentes/Efectos.jsx';
import Inicio from './vistas/Inicio.jsx';
import EnVivo from './vistas/EnVivo.jsx';
import Juego from './vistas/Juego.jsx';
import HumanoIA from './vistas/HumanoIA.jsx';
import Aprendizaje from './vistas/Aprendizaje.jsx';
import Botes from './vistas/Botes.jsx';
import Historial from './vistas/Historial.jsx';
import Estadisticas from './vistas/Estadisticas.jsx';
import Pruebas from './vistas/Pruebas.jsx';
import Configuracion from './vistas/Configuracion.jsx';

const VISTAS = [
  { ruta: 'inicio', nombre: 'Inicio', Componente: Inicio },
  { ruta: 'en-vivo', nombre: 'En vivo', Componente: EnVivo },
  { ruta: 'juego', nombre: '¿Le ganas a la IA?', Componente: Juego },
  { ruta: 'humano-ia', nombre: 'Humano vs. IA', Componente: HumanoIA },
  { ruta: 'aprendizaje', nombre: 'Aprendizaje', Componente: Aprendizaje },
  { ruta: 'botes', nombre: 'Botes', Componente: Botes },
  { ruta: 'historial', nombre: 'Historial', Componente: Historial },
  { ruta: 'estadisticas', nombre: 'Estadísticas', Componente: Estadisticas },
  { ruta: 'pruebas', nombre: 'Pruebas', Componente: Pruebas },
  { ruta: 'configuracion', nombre: 'Configuración', Componente: Configuracion },
];

// Navegación con el "#" de la URL (#/en-vivo), sin bibliotecas de rutas.
function useRuta() {
  const leer = () => window.location.hash.replace(/^#\/?/, '') || 'inicio';
  const [ruta, setRuta] = useState(leer);
  useEffect(() => {
    const alCambiar = () => setRuta(leer());
    window.addEventListener('hashchange', alCambiar);
    return () => window.removeEventListener('hashchange', alCambiar);
  }, []);
  return ruta;
}

const TEXTO_CONEXION = {
  conectando: { texto: 'Conectando…', clase: 'conexion-espera' },
  en_vivo: { texto: 'En vivo', clase: 'conexion-ok' },
  polling: { texto: 'Sin conexión en vivo', clase: 'conexion-aviso' },
  sin_backend: { texto: 'Sin conexión con el backend', clase: 'conexion-error' },
};

function Encabezado() {
  const { conexion, maquina } = useEnVivo();
  const c = TEXTO_CONEXION[conexion] || TEXTO_CONEXION.conectando;
  const estado = maquina?.estado;
  return (
    <header className="encabezado">
      <div className="marca">
        <Logotipo />
        <div className="marca-textos">
          <strong>Clasificador de residuos</strong>
          <span className="atenuado">Cyber Insanos, Reto 1</span>
        </div>
      </div>
      <div className="encabezado-estado">
        {estado && (
          <span className={`pastilla estado-${estado.toLowerCase()}`}>
            {NOMBRE_ESTADO[estado] || estado}
            {maquina.modo && <small> · modo {maquina.modo === 'ia' ? 'IA' : 'Adivina'}</small>}
          </span>
        )}
        <span className={`conexion ${c.clase}`} title={conexion === 'polling' ? 'Consultando /api/estado cada 2 s' : c.texto}>
          <span className="conexion-punto" /> <span className="conexion-texto">{c.texto}</span>
        </span>
        {MODO_MOCK && <span className="rotulo rotulo-simulado" title="Datos de ejemplo, sin backend">DATOS DE EJEMPLO</span>}
        {!MODO_MOCK && maquina?.simulacion && <Simulado />}
        <Campana />
      </div>
    </header>
  );
}

export default function App() {
  const ruta = useRuta();
  const vista = VISTAS.find((v) => v.ruta === ruta) || VISTAS[0];
  const { Componente } = vista;
  const principal = useRef(null);
  useRevelarAlScroll(principal, vista.ruta);
  // En el celular la regleta de pestañas se desplaza: deja visible la pestaña activa.
  // Y cada pestaña nueva empieza desde arriba.
  useEffect(() => {
    document.querySelector('.navegacion a.activa')?.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' });
    window.scrollTo({ top: 0 });
  }, [vista.ruta]);
  return (
    <div className="app">
      <Encabezado />
      <nav className="navegacion" aria-label="Vistas">
        {VISTAS.map((v) => (
          <a key={v.ruta} href={`#/${v.ruta}`} className={v.ruta === vista.ruta ? 'activa' : ''}
            aria-current={v.ruta === vista.ruta ? 'page' : undefined}>{v.nombre}</a>
        ))}
      </nav>
      <BarraProceso />
      <BarraScroll />
      <BarraUrgente ruta={vista.ruta} />
      {/* key: al cambiar de pestaña el contenido entra con un fundido corto. */}
      <main className="contenido entra-vista" key={vista.ruta} ref={principal}>
        <Componente />
      </main>
      <BotonVoz />
      <Notificaciones />
    </div>
  );
}
