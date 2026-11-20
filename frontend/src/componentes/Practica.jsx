// "Practica con fotos": el usuario clasifica fotos del dataset de entrenamiento sin usar la máquina.
// Elige cuántas preguntas (5–30); el backend reparte ese total entre las 3 categorías (GET /api/juego/fotos?total=N).
// La categoría correcta es la carpeta del dataset donde está la foto, así que la calificación se hace aquí.
// Puntos: 100 por acierto + 20 por cada acierto seguido (hasta +100). Los puntos no se guardan, pero CADA RESPUESTA
// sí (POST /api/juego/fotos/respuesta): alimenta «Humano vs. IA» y «Aprendizaje», y el backend devuelve qué dijo la IA.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api, urlFoto } from '../api.js';
import { CATEGORIAS, categoria } from '../categorias.js';
import { confeti, lluviaConfeti, sonar } from '../efectos.js';
import { Barra, Categoria, IconoCategoria, MensajeError, Numero, pct, useAccion } from './Comun.jsx';
import { BotonSonido } from './Efectos.jsx';

const OPCIONES = [5, 10, 15, 20, 25, 30];
const AVANCE_AUTOMATICO_MS = 1700;

const puntosPor = (racha) => 100 + Math.min(100, 20 * (racha - 1));

function reparto(n) {
  const base = Math.floor(n / 3);
  return n % 3 === 0 ? `${base} de cada bote` : `${base} o ${base + 1} de cada bote`;
}

function Elegir({ alElegir, ocupado, sinFotos, elegido }) {
  return (
    <div className="practica-inicio">
      <h2 className="titulo-grande">¿Cuántas preguntas quieres?</h2>
      <p>Usamos fotos reales del dataset con el que aprendió la IA, repartidas entre los 3 botes.</p>
      <div className="opciones-preguntas" role="group" aria-label="Número de preguntas">
        {OPCIONES.map((n, i) => (
          <button key={n} type="button" className={`opcion-pregunta ${elegido === n && ocupado ? 'cargando' : ''}`}
            style={{ '--i': i }} disabled={ocupado} onClick={() => alElegir(n)}>
            <strong>{n}</strong>
            <span>preguntas</span>
            <small>{reparto(n)}</small>
          </button>
        ))}
      </div>
      <p className="atenuado">Responde con los botones o con las teclas 1, 2 y 3. Enter pasa a la siguiente.</p>
      {sinFotos && (
        <p className="mensaje-error" role="alert">
          El dataset no tiene fotos todavía. Captúralas con <code>training/capturar_dataset.py</code> o cópialas
          a <code>backend/dataset/&lt;clase&gt;/</code>.
        </p>
      )}
    </div>
  );
}

// Medalla dibujada (sin imágenes externas). nivel: oro | plata | bronce | practica
function Medalla({ nivel }) {
  const colores = {
    oro: ['#F2B705', '#C98F00'], plata: ['#C9D1D9', '#8B98A5'], bronce: ['#D08A4E', '#9C5B26'], practica: ['#9FD4CF', '#0E7C86'],
  }[nivel];
  return (
    <svg className={`medalla medalla-${nivel}`} viewBox="0 0 120 150" aria-hidden="true">
      <path d="M38 0h18l14 52H52z" fill="#1E6FD9" />
      <path d="M82 0H64L50 52h18z" fill="#2E9E44" />
      <circle cx="60" cy="96" r="44" fill={colores[1]} />
      <circle cx="60" cy="96" r="36" fill={colores[0]} />
      <path d="M60 72l7 15 16 2-12 11 3 16-14-8-14 8 3-16-12-11 16-2z" fill="#fff" opacity="0.9" />
    </svg>
  );
}

function Resultado({ fotos, respuestas, puntos, mejorRacha, alRepetir, alCambiar, ocupado }) {
  const aciertos = respuestas.filter((r, i) => r === fotos[i].categoria_id).length;
  const proporcion = aciertos / fotos.length;
  const nivel = proporcion >= 0.9 ? 'oro' : proporcion >= 0.7 ? 'plata' : proporcion >= 0.5 ? 'bronce' : 'practica';
  const titulo = { oro: '¡Excelente! Medalla de oro', plata: '¡Muy bien! Medalla de plata', bronce: 'Vas bien: medalla de bronce', practica: 'Sigue practicando' }[nivel];
  const errores = fotos.map((f, i) => ({ ...f, respuesta: respuestas[i] })).filter((f) => f.respuesta !== f.categoria_id);
  const porCategoria = CATEGORIAS.map((c) => {
    const indices = fotos.map((f, i) => (f.categoria_id === c.id ? i : -1)).filter((i) => i >= 0);
    return { ...c, total: indices.length, bien: indices.filter((i) => respuestas[i] === c.id).length };
  });

  useEffect(() => {
    sonar('fin');
    if (proporcion >= 0.8) lluviaConfeti();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="practica-fin">
      <div className="fin-cabecera">
        <Medalla nivel={nivel} />
        <div>
          <h1 className="titulo-grande">{titulo}</h1>
          <div className="fin-resumen">
            <div><Numero valor={`${aciertos}`} clase="fin-cifra" /><span>de {fotos.length} correctas</span></div>
            <div><Numero valor={`${Math.round(proporcion * 100)} %`} clase="fin-cifra" /><span>de acierto</span></div>
            <div><Numero valor={`${puntos}`} clase="fin-cifra" /><span>puntos</span></div>
            <div><Numero valor={`${mejorRacha}`} clase="fin-cifra" /><span>mejor racha</span></div>
          </div>
        </div>
      </div>
      <div className="practica-por-categoria">
        {porCategoria.filter((c) => c.total > 0).map((c) => (
          <div key={c.id} className="practica-fila">
            <Categoria id={c.id} />
            <Barra valor={c.bien / c.total} color={c.hex} texto={`${c.bien} de ${c.total} · ${pct(c.bien / c.total)}`} />
          </div>
        ))}
      </div>
      {errores.length > 0 && (
        <>
          <h2 className="practica-subtitulo">Repasa las que fallaste</h2>
          <ul className="practica-errores">
            {errores.map((f) => (
              <li key={f.id}>
                <img src={urlFoto(f.foto)} alt="Foto que fallaste" loading="lazy" />
                <div>
                  <span className="atenuado">Va en</span> <Categoria id={f.categoria_id} />
                  <span className="atenuado">Elegiste</span> <Categoria id={f.respuesta} />
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
      <div className="fin-acciones">
        <button type="button" className="boton-principal" disabled={ocupado} onClick={alRepetir}>
          {ocupado ? 'Cargando fotos…' : `Jugar otra vez (${fotos.length} fotos nuevas)`}
        </button>
        <button type="button" className="boton-secundario" onClick={alCambiar}>Cambiar número de preguntas</button>
      </div>
    </div>
  );
}

// Botones de respuesta: después de responder, el correcto brilla y el elegido por error se marca.
function BotonesRespuesta({ alElegir, respuesta, correcta }) {
  const respondida = respuesta !== undefined;
  return (
    <div className="botones-categoria botones-juego">
      {CATEGORIAS.map((c) => {
        let estado = '';
        if (respondida) {
          if (c.id === correcta) estado = 'es-correcta';
          else if (c.id === respuesta) estado = 'es-incorrecta';
          else estado = 'apagada';
        }
        return (
          <button key={c.id} type="button" className={`boton-categoria ${estado}`} style={{ background: c.hex }} data-cat={c.clave}
            disabled={respondida} aria-pressed={respuesta === c.id} onClick={() => alElegir(c.id)}>
            <IconoCategoria id={c.id} tam={40} />
            <span className="boton-categoria-nombre">{c.id + 1} · {c.nombre}</span>
            <small>bote {c.color}</small>
          </button>
        );
      })}
    </div>
  );
}

export default function Practica() {
  const [total, setTotal] = useState(null);
  const [fotos, setFotos] = useState(null); // null = todavía no empieza
  const [respuestas, setRespuestas] = useState([]);
  const [indice, setIndice] = useState(0);
  const [puntos, setPuntos] = useState(0);
  const [racha, setRacha] = useState(0);
  const [mejorRacha, setMejorRacha] = useState(0);
  const [ganados, setGanados] = useState(null); // {valor, clave} para el "+120" flotante
  const [sinFotos, setSinFotos] = useState(false);
  const [aviso, setAviso] = useState(null);
  const [ia, setIa] = useState({});          // índice → {pred_id, confianza, correcto} de la IA
  const sesion = useRef(null);
  const { ejecutar, ocupado, error } = useAccion();
  const marcoFoto = useRef(null);
  const temporizador = useRef(null);

  const respondida = respuestas.length > indice;
  const terminado = fotos && indice >= fotos.length;
  const foto = fotos && !terminado ? fotos[indice] : null;

  const empezar = useCallback(async (n) => {
    clearTimeout(temporizador.current);
    setTotal(n);
    const r = await ejecutar(() => api.fotosPractica(n));
    if (!r) return;
    setSinFotos(r.total === 0);
    if (r.total === 0) return;
    setAviso(r.total < n ? `El dataset solo alcanzó para ${r.total} preguntas.` : null);
    sesion.current = window.crypto?.randomUUID?.() || `s${Date.now()}`;
    setIa({});
    setFotos(r.items);
    setRespuestas([]);
    setIndice(0);
    setPuntos(0);
    setRacha(0);
    setMejorRacha(0);
    setGanados(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [ejecutar]);

  const siguiente = useCallback(() => {
    clearTimeout(temporizador.current);
    if (respondida) setIndice((i) => i + 1);
  }, [respondida]);

  const responder = useCallback((id) => {
    if (!foto || respondida) return;
    setRespuestas((rs) => [...rs, id]);
    const n = indice;
    api.respuestaPractica({ sesion: sesion.current, foto: foto.id, respuesta: id, intento: n + 1 })
      .then((r) => { if (r?.ia) setIa((m) => ({ ...m, [n]: r.ia })); })
      .catch(() => {});  // si no se guarda, el entrenamiento sigue igual
    if (id === foto.categoria_id) {
      const nuevaRacha = racha + 1;
      const valor = puntosPor(nuevaRacha);
      setRacha(nuevaRacha);
      setMejorRacha((m) => Math.max(m, nuevaRacha));
      setPuntos((p) => p + valor);
      setGanados({ valor, clave: indice });
      sonar(nuevaRacha >= 3 ? 'racha' : 'acierto');
      const caja = marcoFoto.current?.getBoundingClientRect();
      confeti(caja ? { x: caja.left + caja.width / 2, y: caja.top + caja.height / 2, cantidad: nuevaRacha >= 3 ? 110 : 70 } : {});
      // Si acertó, pasa sola a la siguiente; si falló, espera a que lea cuál era.
      temporizador.current = setTimeout(() => setIndice((i) => i + 1), AVANCE_AUTOMATICO_MS);
    } else {
      setRacha(0);
      setGanados(null);
      sonar('error');
      navigator.vibrate?.(120);
    }
  }, [foto, respondida, racha, indice]);

  useEffect(() => () => clearTimeout(temporizador.current), []);

  // Teclado: 1/2/3 responden, Enter o espacio pasan a la siguiente.
  useEffect(() => {
    if (!foto) return undefined;
    const alTeclear = (e) => {
      if (e.target.closest?.('input, textarea, select')) return;
      if (!respondida && ['1', '2', '3'].includes(e.key)) { e.preventDefault(); responder(Number(e.key) - 1); }
      else if (respondida && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); siguiente(); }
    };
    window.addEventListener('keydown', alTeclear);
    return () => window.removeEventListener('keydown', alTeclear);
  }, [foto, respondida, responder, siguiente]);

  // Precarga la siguiente foto para que no haya espera al pasar.
  useEffect(() => {
    const prox = fotos?.[indice + 1];
    if (prox) { const img = new Image(); img.src = urlFoto(prox.foto); }
  }, [fotos, indice]);

  const aciertos = useMemo(() => respuestas.filter((r, i) => fotos && r === fotos[i].categoria_id).length, [respuestas, fotos]);

  if (!fotos) {
    return (
      <>
        <Elegir alElegir={empezar} ocupado={ocupado} sinFotos={sinFotos} elegido={total} />
        <MensajeError error={error} />
      </>
    );
  }
  if (terminado) {
    return (
      <>
        <Resultado fotos={fotos} respuestas={respuestas} puntos={puntos} mejorRacha={mejorRacha}
          alRepetir={() => empezar(total)} alCambiar={() => setFotos(null)} ocupado={ocupado} />
        <MensajeError error={error} />
      </>
    );
  }

  const respuesta = respuestas[indice];
  const correcta = respondida && respuesta === foto.categoria_id;
  const cat = categoria(foto.categoria_id);
  return (
    <div className="practica">
      <div className="practica-marcador">
        <div className="marcador-dato"><span>Pregunta</span><strong>{indice + 1}<small>/{fotos.length}</small></strong></div>
        <div className="marcador-dato"><span>Puntos</span><Numero valor={`${puntos}`} clase="marcador-puntos" /></div>
        <div className={`marcador-dato racha ${racha >= 2 ? 'encendida' : ''}`} key={`r${racha}`}>
          <span>Racha</span><strong>×{racha}</strong>
        </div>
        <BotonSonido />
      </div>
      <ol className="puntos-avance" aria-label={`Llevas ${aciertos} aciertos de ${respuestas.length}`}>
        {fotos.map((f, i) => {
          const r = respuestas[i];
          const clase = r === undefined ? (i === indice ? 'actual' : '') : r === f.categoria_id ? 'bien' : 'mal';
          return <li key={f.id} className={clase} />;
        })}
      </ol>
      {aviso && <p className="atenuado">{aviso}</p>}
      <div ref={marcoFoto} className={`practica-foto ${respondida ? (correcta ? 'bien' : 'mal') : ''}`} key={foto.id}>
        <img src={urlFoto(foto.foto)} alt="Foto del dataset: ¿a qué bote va?" />
        {respondida && (
          <div className={`sello ${correcta ? 'sello-bien' : 'sello-mal'}`} aria-hidden="true">
            {correcta
              ? <svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
              : <svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg>}
          </div>
        )}
        {correcta && ganados?.clave === indice && <div className="puntos-flotantes" aria-hidden="true">+{ganados.valor}</div>}
      </div>
      <h2 className={`practica-pregunta ${respondida ? (correcta ? 'txt-bien' : 'txt-mal') : ''}`} key={`p${indice}${respondida}`}>
        {respondida ? (correcta ? (racha >= 3 ? `¡${racha} seguidas!` : '¡Correcto!') : `Casi: era ${cat.nombre}`) : '¿A qué bote va?'}
      </h2>
      <BotonesRespuesta alElegir={responder} respuesta={respuesta} correcta={foto.categoria_id} />
      {respondida && ia[indice] && (
        <p className={`practica-ia ${ia[indice].correcto ? 'ia-bien' : 'ia-mal'}`}>
          La IA dijo <strong>{categoria(ia[indice].pred_id)?.nombre}</strong> ({pct(ia[indice].confianza)}) {ia[indice].correcto ? '✓' : '✗'}
        </p>
      )}
      {respondida && (
        <div className="practica-siguiente">
          <button type="button" className={`boton-principal ${correcta ? 'con-avance' : ''}`} onClick={siguiente} autoFocus
            style={{ '--avance-ms': `${AVANCE_AUTOMATICO_MS}ms` }}>
            {indice + 1 < fotos.length ? 'Siguiente (Enter)' : 'Ver resultado (Enter)'}
          </button>
        </div>
      )}
      <button type="button" className="boton-texto practica-salir" onClick={() => { clearTimeout(temporizador.current); setFotos(null); }}>
        Salir del entrenamiento
      </button>
    </div>
  );
}
