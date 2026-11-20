// Piezas visuales compartidas: botón de sonido, barra de avance del scroll, "volver arriba",
// aparición de tarjetas al hacer scroll y la cabecera de cada vista.
import { useEffect, useState } from 'react';
import { alternarSonido, useSonido } from '../efectos.js';

export function BotonSonido() {
  const activo = useSonido();
  return (
    <button type="button" className="boton-sonido" onClick={alternarSonido} aria-pressed={activo}
      title={activo ? 'Silenciar sonidos' : 'Activar sonidos'}>
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z" className="relleno" />
        {activo
          ? <><path d="M15.5 9a4 4 0 0 1 0 6" /><path d="M18 6.5a7.5 7.5 0 0 1 0 11" /></>
          : <path d="M16 9.5l5 5M21 9.5l-5 5" />}
      </svg>
      <span>{activo ? 'Sonido' : 'Silencio'}</span>
    </button>
  );
}

// Barra fina bajo el encabezado que se llena al bajar por la página.
export function BarraScroll() {
  const [avance, setAvance] = useState(0);
  const [mostrarArriba, setMostrarArriba] = useState(false);
  useEffect(() => {
    let pendiente = false;
    const medir = () => {
      pendiente = false;
      const alto = document.documentElement.scrollHeight - window.innerHeight;
      setAvance(alto > 0 ? Math.min(1, window.scrollY / alto) : 0);
      setMostrarArriba(window.scrollY > 600);
    };
    const alMover = () => { if (!pendiente) { pendiente = true; requestAnimationFrame(medir); } };
    medir();
    window.addEventListener('scroll', alMover, { passive: true });
    window.addEventListener('resize', alMover);
    return () => { window.removeEventListener('scroll', alMover); window.removeEventListener('resize', alMover); };
  }, []);
  return (
    <>
      <div className="barra-scroll" aria-hidden="true"><div style={{ transform: `scaleX(${avance})` }} /></div>
      <button type="button" className={`volver-arriba ${mostrarArriba ? 'visible' : ''}`} aria-label="Volver arriba"
        tabIndex={mostrarArriba ? 0 : -1} onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 14l6-6 6 6" /></svg>
      </button>
    </>
  );
}

// Aparición suave al entrar en pantalla: tarjetas, cifras y bloques marcados con .revelar.
// Observa también lo que se agrega después (datos que llegan, pestañas que cambian).
const SELECTOR_REVELAR = '.tarjeta, .cifra, .revelar, .duelo, .tarjeta-cat, .paso, .pareja-confusion';

export function useRevelarAlScroll(contenedorRef, clave) {
  useEffect(() => {
    const raiz = contenedorRef.current;
    if (!raiz || !('IntersectionObserver' in window)) return undefined;
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined;

    let lote = 0;
    let reinicio = null;
    const io = new IntersectionObserver((entradas) => {
      entradas.forEach((e) => {
        if (!e.isIntersecting) return;
        // Escalonado: los que aparecen juntos entran uno tras otro.
        e.target.style.setProperty('--retraso', `${Math.min(lote, 8) * 70}ms`);
        lote += 1;
        e.target.classList.add('revelado');
        io.unobserve(e.target);
      });
      clearTimeout(reinicio);
      reinicio = setTimeout(() => { lote = 0; }, 120);
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

    const preparar = (el) => {
      if (el.classList.contains('por-revelar')) return;
      el.classList.add('por-revelar');
      io.observe(el);
    };
    raiz.querySelectorAll(SELECTOR_REVELAR).forEach(preparar);
    const mo = new MutationObserver((cambios) => {
      cambios.forEach((c) => c.addedNodes.forEach((n) => {
        if (n.nodeType !== 1) return;
        if (n.matches(SELECTOR_REVELAR)) preparar(n);
        n.querySelectorAll?.(SELECTOR_REVELAR).forEach(preparar);
      }));
    });
    mo.observe(raiz, { childList: true, subtree: true });
    return () => { io.disconnect(); mo.disconnect(); clearTimeout(reinicio); };
  }, [contenedorRef, clave]);
}

export const ICONOS = {
  inicio: <><path d="M3.5 11L12 4l8.5 7" /><path d="M6 9.5V20h12V9.5" /><path d="M10 20v-5h4v5" /></>,
  envivo: <><circle cx="12" cy="12" r="2.2" /><path d="M8 8a5.6 5.6 0 0 0 0 8M16 8a5.6 5.6 0 0 1 0 8" /><path d="M5 5a9.9 9.9 0 0 0 0 14M19 5a9.9 9.9 0 0 1 0 14" /></>,
  duelo: <><circle cx="8" cy="8" r="3" /><path d="M3 20c0-3 2.2-5 5-5s5 2 5 5" /><rect x="14" y="5" width="7" height="7" rx="1.5" /><path d="M16 15h3M17.5 12v3M15 20h5" /></>,
  aprendizaje: <><path d="M3 18l5-5 4 3 8-9" /><path d="M15 7h5v5" /></>,
  estadisticas: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>,
  pruebas: <><path d="M9 4h6M10 4v5l-5 9a1.5 1.5 0 0 0 1.3 2h11.4a1.5 1.5 0 0 0 1.3-2l-5-9V4" /><path d="M7.5 15h9" /></>,
  botes: <><path d="M5 7h14l-1.3 13H6.3z" /><path d="M3.5 7h17M9.5 4h5" /><path d="M10 11v6M14 11v6" /></>,
  historial: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" /></>,
  configuracion: <><circle cx="12" cy="12" r="3" /><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1" /></>,
  juego: <><rect x="3" y="7" width="18" height="11" rx="4" /><path d="M8 11v3M6.5 12.5h3" /><circle cx="15.5" cy="11.5" r="1" /><circle cx="17.5" cy="13.5" r="1" /></>,
};

// Cabecera de cada vista: ícono, título y la pregunta que responde la página.
export function CabeceraVista({ icono, titulo, pregunta, children }) {
  return (
    <header className="cabecera-vista">
      {icono && <span className="cabecera-icono" aria-hidden="true"><svg viewBox="0 0 24 24">{ICONOS[icono]}</svg></span>}
      <div className="cabecera-textos">
        <h1>{titulo}</h1>
        {pregunta && <p>{pregunta}</p>}
      </div>
      {children && <div className="cabecera-extra">{children}</div>}
    </header>
  );
}
