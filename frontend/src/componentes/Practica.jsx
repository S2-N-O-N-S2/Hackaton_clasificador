// "Practica con fotos": el usuario clasifica fotos del dataset de entrenamiento sin usar la máquina.
// El backend elige 20 fotos al azar de cada clase (GET /api/juego/fotos); la categoría correcta es la carpeta
// del dataset donde está la foto, así que la calificación se hace aquí, en el panel.
import { useCallback, useEffect, useMemo, useState } from 'react';
import { api, urlFoto } from '../api.js';
import { CATEGORIAS, categoria } from '../categorias.js';
import { Barra, BotonesCategoria, Categoria, Cifra, MensajeError, pct, useAccion } from './Comun.jsx';

const POR_CATEGORIA = 20;

function Inicio({ alEmpezar, ocupado, sinFotos }) {
  return (
    <div className="practica-inicio">
      <h1 className="titulo-grande">Practica con fotos</h1>
      <p>
        Te mostramos {POR_CATEGORIA * 3} fotos del dataset con el que aprendió la IA ({POR_CATEGORIA} orgánicas,
        {' '}{POR_CATEGORIA} inorgánicas y {POR_CATEGORIA} peligrosas) en orden al azar. Elige el bote de cada una.
      </p>
      <p className="atenuado">No usa la máquina: puedes jugar aunque haya un residuo en proceso. Teclas 1, 2 y 3 para responder; Enter para seguir.</p>
      {sinFotos && (
        <p className="mensaje-error" role="alert">
          El dataset no tiene fotos todavía. Captúralas con <code>training/capturar_dataset.py</code> o cópialas
          a <code>backend/dataset/&lt;clase&gt;/</code>.
        </p>
      )}
      <button type="button" className="boton-principal" disabled={ocupado} onClick={alEmpezar}>
        {ocupado ? 'Cargando fotos…' : 'Empezar'}
      </button>
    </div>
  );
}

function Resultado({ fotos, respuestas, alRepetir, ocupado }) {
  const aciertos = respuestas.filter((r, i) => r === fotos[i].categoria_id).length;
  const errores = fotos.map((f, i) => ({ ...f, respuesta: respuestas[i] })).filter((f) => f.respuesta !== f.categoria_id);
  const porCategoria = CATEGORIAS.map((c) => {
    const indices = fotos.map((f, i) => (f.categoria_id === c.id ? i : -1)).filter((i) => i >= 0);
    const bien = indices.filter((i) => respuestas[i] === c.id).length;
    return { ...c, total: indices.length, bien };
  });
  const mensaje = aciertos === fotos.length ? '¡Perfecto! No fallaste ninguna.'
    : aciertos / fotos.length >= 0.8 ? '¡Muy bien! Repasa las que fallaste.'
      : 'Repasa las que fallaste y vuelve a intentarlo.';
  return (
    <div className="practica-fin llegada-suave">
      <h1 className="titulo-grande">{mensaje}</h1>
      <div className="cifras practica-cifras">
        <Cifra etiqueta="Aciertos" valor={String(aciertos)} detalle={`de ${fotos.length} fotos`} progreso={aciertos / fotos.length} />
        <Cifra etiqueta="Porcentaje" valor={`${Math.round((aciertos / fotos.length) * 100)} %`} />
        <Cifra etiqueta="Errores" valor={String(errores.length)} />
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
          <h2 className="practica-subtitulo">Las que fallaste</h2>
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
      <button type="button" className="boton-principal" disabled={ocupado} onClick={alRepetir}>
        {ocupado ? 'Cargando fotos…' : 'Jugar otra vez con fotos nuevas'}
      </button>
    </div>
  );
}

export default function Practica() {
  const [fotos, setFotos] = useState(null); // null = todavía no empieza
  const [respuestas, setRespuestas] = useState([]);
  const [sinFotos, setSinFotos] = useState(false);
  const [aviso, setAviso] = useState(null);
  const { ejecutar, ocupado, error } = useAccion();

  // Índice de la foto en pantalla y si ya se respondió (se queda en pantalla hasta pulsar "Siguiente").
  const [indice, setIndice] = useState(0);
  const respondida = respuestas.length > indice;
  const terminado = fotos && indice >= fotos.length;
  const foto = fotos && !terminado ? fotos[indice] : null;

  const empezar = useCallback(async () => {
    const r = await ejecutar(() => api.fotosPractica(POR_CATEGORIA));
    if (!r) return;
    setSinFotos(r.total === 0);
    if (r.total === 0) return;
    const pocas = Object.entries(r.disponibles || {}).filter(([, n]) => n < POR_CATEGORIA);
    setAviso(pocas.length ? `Hay pocas fotos de ${pocas.map(([k, n]) => `${CATEGORIAS.find((c) => c.clave === k)?.nombre.toLowerCase() ?? k} (${n})`).join(' y ')}: se usan todas.` : null);
    setFotos(r.items);
    setRespuestas([]);
    setIndice(0);
  }, [ejecutar]);

  const responder = useCallback((id) => {
    if (!foto || respondida) return;
    setRespuestas((rs) => [...rs, id]);
  }, [foto, respondida]);

  const siguiente = useCallback(() => {
    if (respondida) setIndice((i) => i + 1);
  }, [respondida]);

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
    return (<><Inicio alEmpezar={empezar} ocupado={ocupado} sinFotos={sinFotos} /><MensajeError error={error} /></>);
  }
  if (terminado) {
    return (<><Resultado fotos={fotos} respuestas={respuestas} alRepetir={empezar} ocupado={ocupado} /><MensajeError error={error} /></>);
  }

  const respuesta = respuestas[indice];
  const correcta = respondida && respuesta === foto.categoria_id;
  const cat = categoria(foto.categoria_id);
  return (
    <div className="practica">
      <div className="practica-progreso">
        <span>Foto <strong>{indice + 1}</strong> de {fotos.length}</span>
        <div className="practica-pista" aria-hidden="true"><div style={{ width: `${(respuestas.length / fotos.length) * 100}%` }} /></div>
        <span>Aciertos <strong>{aciertos}</strong></span>
      </div>
      {aviso && <p className="atenuado">{aviso}</p>}
      <div className={`practica-foto ${respondida ? (correcta ? 'bien' : 'mal') : ''}`} key={foto.id}>
        <img src={urlFoto(foto.foto)} alt="Foto del dataset: ¿a qué bote va?" />
      </div>
      {!respondida ? (
        <>
          <h2 className="practica-pregunta">¿A qué bote va?</h2>
          <BotonesCategoria alElegir={responder} />
        </>
      ) : (
        <div className={`practica-veredicto ${correcta ? 'bien' : 'mal'} llegada-suave`} role="status" style={{ '--cat': cat.hex }}>
          <strong>{correcta ? '¡Correcto!' : 'No era ese bote'}</strong>
          <span>Va en <Categoria id={foto.categoria_id} grande /></span>
          {!correcta && <span className="atenuado">Elegiste <Categoria id={respuesta} /></span>}
          <button type="button" className="boton-principal" onClick={siguiente} autoFocus>
            {indice + 1 < fotos.length ? 'Siguiente (Enter)' : 'Ver resultado (Enter)'}
          </button>
        </div>
      )}
      <button type="button" className="boton-texto practica-salir" onClick={() => setFotos(null)}>Salir de la práctica</button>
    </div>
  );
}
