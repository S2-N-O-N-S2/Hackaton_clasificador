// Estructura del panel: encabezado, navegación por pestañas y la vista activa.
import { useEffect, useState } from 'react';
import { useEnVivo } from './estado.jsx';
import { NOMBRE_ESTADO } from './categorias.js';
import { MODO_MOCK } from './config.js';
import { Simulado, hora } from './componentes/Comun.jsx';
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
        <strong>Clasificador de residuos</strong>
        <span className="atenuado">Cyber Insanos · Reto 1</span>
      </div>
      <div className="encabezado-estado">
        {estado && (
          <span className={`pastilla estado-${estado.toLowerCase()}`}>
            {NOMBRE_ESTADO[estado] || estado}
            {maquina.modo && <small> · modo {maquina.modo === 'ia' ? 'IA' : 'Adivina'}</small>}
          </span>
        )}
        <span className={`conexion ${c.clase}`} title={conexion === 'polling' ? 'Consultando /api/estado cada 2 s' : ''}>
          <span className="conexion-punto" /> {c.texto}
        </span>
        {MODO_MOCK && <span className="rotulo rotulo-simulado">DATOS DE EJEMPLO</span>}
        {!MODO_MOCK && maquina?.simulacion && <Simulado />}
      </div>
    </header>
  );
}

// Avisos que importan en cualquier pestaña.
function AvisosGlobales({ ruta }) {
  const { maquina, alertas } = useEnVivo();
  const [ocultas, setOcultas] = useState(() => new Set());
  const estado = maquina?.estado;
  const visibles = alertas.filter((a) => a.nivel !== 'info' && !ocultas.has(a.fecha_hora + a.codigo)).slice(0, 3);
  return (
    <div className="avisos">
      {estado === 'REVISION' && ruta !== 'en-vivo' && ruta !== 'juego' && (
        <a className="aviso aviso-revision" href="#/en-vivo">Hay un residuo en REVISIÓN: la IA no está segura. Resolver →</a>
      )}
      {estado === 'BOTE_LLENO' && ruta !== 'botes' && (
        <a className="aviso aviso-error" href="#/botes">Un bote está LLENO (estimado): el residuo espera en la bandeja. Vaciar →</a>
      )}
      {estado === 'ERROR' && (
        <div className="aviso aviso-error">Falla segura: trampilla cerrada y disco en HOME. {maquina.mensaje}</div>
      )}
      {visibles.map((a) => (
        <div key={a.fecha_hora + a.codigo} className={`aviso aviso-${a.nivel}`}>
          <span>{hora(a.fecha_hora)} · {a.mensaje}</span>
          <button type="button" className="boton-texto" aria-label="Ocultar aviso"
            onClick={() => setOcultas((s) => new Set(s).add(a.fecha_hora + a.codigo))}>✕</button>
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const ruta = useRuta();
  const vista = VISTAS.find((v) => v.ruta === ruta) || VISTAS[0];
  const { Componente } = vista;
  return (
    <div className="app">
      <Encabezado />
      <nav className="navegacion" aria-label="Vistas">
        {VISTAS.map((v) => (
          <a key={v.ruta} href={`#/${v.ruta}`} className={v.ruta === vista.ruta ? 'activa' : ''}>{v.nombre}</a>
        ))}
      </nav>
      <AvisosGlobales ruta={vista.ruta} />
      <main className="contenido">
        <Componente />
      </main>
    </div>
  );
}
