// Estructura del panel: encabezado, navegación por pestañas y la vista activa.
import { useEffect, useRef, useState } from 'react';
import { useEnVivo } from './estado.jsx';
import { NOMBRE_ESTADO } from './categorias.js';
import { MODO_MOCK } from './config.js';
import { BarraProceso, Notificaciones, Simulado } from './componentes/Comun.jsx';
import { BarraUrgente, Campana } from './componentes/Avisos.jsx';
import { Logotipo } from './componentes/Graficas.jsx';
import { BotonVoz } from './componentes/Voz.jsx';
import { ModalDeposito } from './componentes/Deposito.jsx';
import { BarraScroll, ICONOS, useRevelarAlScroll } from './componentes/Efectos.jsx';
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
  { ruta: 'inicio', nombre: 'Inicio', icono: 'inicio', Componente: Inicio },
  { ruta: 'en-vivo', nombre: 'En vivo', icono: 'envivo', Componente: EnVivo },
  { ruta: 'juego', nombre: 'Entrenamiento', icono: 'juego', Componente: Juego },
  { ruta: 'humano-ia', nombre: 'Humano vs. IA', icono: 'duelo', Componente: HumanoIA },
  { ruta: 'aprendizaje', nombre: 'Aprendizaje', icono: 'aprendizaje', Componente: Aprendizaje },
  { ruta: 'botes', nombre: 'Botes', icono: 'botes', Componente: Botes },
  { ruta: 'historial', nombre: 'Historial', icono: 'historial', Componente: Historial },
  { ruta: 'estadisticas', nombre: 'Estadísticas', icono: 'estadisticas', Componente: Estadisticas },
  { ruta: 'pruebas', nombre: 'Pruebas', icono: 'pruebas', Componente: Pruebas },
  { ruta: 'configuracion', nombre: 'Configuración', icono: 'configuracion', Componente: Configuracion },
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
  conectando: { texto: 'Conectando…', clase: 'conexion-espera', barras: 1 },
  en_vivo: { texto: 'En vivo', clase: 'conexion-ok', barras: 4 },
  polling: { texto: 'Sin conexión en vivo', clase: 'conexion-aviso', barras: 2 },
  sin_backend: { texto: 'Sin conexión con el backend', clase: 'conexion-error', barras: 0 },
};

// Tipo de estado de la máquina para el color y la animación de la insignia.
const ESTADOS_TRABAJANDO = ['CAPTURA', 'CLASIFICACION', 'VERIFICAR_BOTE', 'POSICIONAR', 'SOLTAR', 'REGISTRAR', 'ACTUALIZAR_NIVEL', 'HOME'];
const ESTADOS_ESPERA_PERSONA = ['ESPERA_ADIVINANZA', 'RETROALIMENTACION', 'REVISION', 'PENDIENTE'];
const ESTADOS_FALLA = ['ERROR', 'BOTE_LLENO'];
function tipoEstado(estado) {
  if (ESTADOS_FALLA.includes(estado)) return 'falla';
  if (ESTADOS_ESPERA_PERSONA.includes(estado)) return 'persona';
  if (ESTADOS_TRABAJANDO.includes(estado)) return 'trabajando';
  return 'listo';
}

// Barras de señal: cuántas se encienden según la conexión.
function Senal({ barras }) {
  return (
    <span className="senal" aria-hidden="true">
      {[1, 2, 3, 4].map((n) => <i key={n} className={n <= barras ? 'encendida' : ''} style={{ '--n': n }} />)}
    </span>
  );
}

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
          <span className="marca-linea" aria-hidden="true"><i /><i /><i /></span>
        </div>
      </div>
      <div className="encabezado-estado">
        {estado && (
          <span className={`pastilla estado-${estado.toLowerCase()} tipo-${tipoEstado(estado)}`} key={estado} title="Estado de la máquina">
            <span className="pastilla-luz" aria-hidden="true" />
            <span className="pastilla-texto">{NOMBRE_ESTADO[estado] || estado}</span>
            {maquina.modo && <span className={`pastilla-modo modo-${maquina.modo}`}>{maquina.modo === 'ia' ? 'Modo IA' : 'Modo Adivina'}</span>}
          </span>
        )}
        <span className={`conexion ${c.clase}`} title={conexion === 'polling' ? 'Consultando /api/estado cada 2 s' : c.texto}>
          <Senal barras={c.barras} /> <span className="conexion-texto">{c.texto}</span>
        </span>
        {MODO_MOCK && <span className="rotulo rotulo-simulado insignia-sim" title="Datos de ejemplo, sin backend">DATOS DE EJEMPLO</span>}
        {!MODO_MOCK && maquina?.simulacion && <span className="insignia-sim-caja"><Simulado /></span>}
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
        {VISTAS.map((v, i) => (
          <a key={v.ruta} href={`#/${v.ruta}`} className={v.ruta === vista.ruta ? 'activa' : ''} style={{ '--i': i }}
            aria-current={v.ruta === vista.ruta ? 'page' : undefined}>
            <svg className="nav-icono" viewBox="0 0 24 24" aria-hidden="true">{ICONOS[v.icono]}</svg>
            <span className="nav-texto">{v.nombre}</span>
          </a>
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
      <ModalDeposito />
      <Notificaciones />
    </div>
  );
}
