// Humano vs. IA (especificación 12.4). Todo viene calculado de GET /api/juego/estadisticas.
// Orden: primero la respuesta (duelo), después el detalle en pestañas.
import { useState } from 'react';
import { api } from '../api.js';
import { useEnVivo } from '../estado.jsx';
import { categoria } from '../categorias.js';
import { Cargando, IconoCategoria, MensajeError, MuestraPequena, pct, useDatos } from '../componentes/Comun.jsx';
import { BarrasHorizontales, MatrizConfusion } from '../componentes/Graficas.jsx';
import { CabeceraVista } from '../componentes/Efectos.jsx';
import { Duelo, Explicacion, FiltroNiveles, Pestanas } from '../componentes/Paneles.jsx';

function PorCategoria({ datos }) {
  const filas = [0, 1, 2].map((id) => ({ id, ...datos.por_categoria?.[id] }));
  const conDatos = filas.filter((f) => f.acierto !== null && f.acierto !== undefined && f.n);
  const dificil = conDatos.length ? conDatos.reduce((a, b) => (b.acierto < a.acierto ? b : a)) : null;
  return (
    <>
      {dificil && (
        <p className="frase-clave">
          La categoría más difícil para las personas es <strong className="nombre-cat" data-cat={categoria(dificil.id).clave}>
            <IconoCategoria id={dificil.id} tam={16} /> {categoria(dificil.id).nombre}</strong>: aciertan {pct(dificil.acierto)}.
        </p>
      )}
      <BarrasHorizontales items={filas.map((f) => ({
        id: f.id, etiqueta: categoria(f.id).nombre, valor: f.acierto ?? null, color: categoria(f.id).hex, detalle: `n=${f.n ?? 0}`,
      }))} />
      <Explicacion>Porcentaje de adivinanzas correctas cuando el residuo era de esa categoría. «n» es cuántas adivinanzas hubo.</Explicacion>
    </>
  );
}

function Confusiones({ parejas }) {
  if (!parejas?.length) return <p className="atenuado">Sin confusiones registradas.</p>;
  const maximo = Math.max(...parejas.map((p) => p.veces));
  return (
    <>
      <ul className="parejas-confusion">
        {parejas.map((p, i) => (
          <li key={`${p.dijo}-${p.era}`} className="pareja-confusion">
            <span className="pareja-orden">{i + 1}</span>
            <span className="pareja-cat" data-cat={categoria(p.dijo)?.clave}><IconoCategoria id={p.dijo} tam={22} /><small>Dijeron</small>{categoria(p.dijo)?.nombre}</span>
            <span className="pareja-flecha" aria-hidden="true">→</span>
            <span className="pareja-cat" data-cat={categoria(p.era)?.clave}><IconoCategoria id={p.era} tam={22} /><small>Era</small>{categoria(p.era)?.nombre}</span>
            <span className="pareja-veces">
              <strong>{p.veces}</strong> veces
              <span className="pareja-barra"><span style={{ width: `${(p.veces / maximo) * 100}%` }} /></span>
            </span>
          </li>
        ))}
      </ul>
      <Explicacion>Los errores más repetidos. Sirven para saber qué explicar mejor en la retroalimentación.</Explicacion>
    </>
  );
}

export default function HumanoIA() {
  const [niveles, setNiveles] = useState(['verificada', 'alta']);
  const { versiones } = useEnVivo();
  const { datos, error, cargando } = useDatos(() => api.estadisticasJuego(niveles), [niveles.join(','), versiones.historial]);

  return (
    <div className="vista vista-datos">
      <CabeceraVista icono="duelo" titulo="Humano vs. IA" pregunta="¿Quién clasifica mejor los mismos residuos: las personas o la IA?">
        <FiltroNiveles niveles={niveles} alCambiar={setNiveles} />
      </CabeceraVista>
      <MensajeError error={error} />
      {cargando && !datos && <Cargando />}
      {datos && (
        <>
          <MuestraPequena si={datos.muestra_pequena} />
          <Duelo
            izquierda={{ nombre: 'Personas', valor: datos.humano_vs_ia?.acierto_humano ?? null, color: '#F28C05', detalle: 'acierto' }}
            derecha={{ nombre: 'IA', valor: datos.humano_vs_ia?.acierto_ia ?? null, color: '#0E7C86', detalle: 'acierto' }}
            pie={`Comparación con los mismos ${datos.humano_vs_ia?.n ?? 0} residuos.`}
          />
          <div className="resumen-chico">
            <div><strong>{datos.n_adivinanzas ?? 0}</strong><span>adivinanzas</span></div>
            <div><strong>{datos.n_sesiones ?? 0}</strong><span>sesiones de juego</span></div>
            <div><strong>{pct(datos.acierto_humano)}</strong><span>acierto humano total</span></div>
            <div title="No entra en lo que se reporta al jurado">
              <strong>{pct(datos.media_aparte?.acierto_humano)}</strong><span>con certeza media (aparte, n={datos.media_aparte?.n_adivinanzas ?? 0})</span>
            </div>
          </div>
          <section className="tarjeta">
            <Pestanas pestanas={[
              { id: 'categoria', titulo: 'Por categoría', contenido: <PorCategoria datos={datos} /> },
              { id: 'confusiones', titulo: 'Confusiones', contador: datos.parejas_confusion?.length || undefined, contenido: <Confusiones parejas={datos.parejas_confusion} /> },
              {
                id: 'matriz', titulo: 'Matriz',
                contenido: (
                  <>
                    <MatrizConfusion matriz={datos.matriz_confusion_humana} columnas="Adivinanza" />
                    <Explicacion>Cada fila es la categoría real y cada columna lo que adivinó la persona. La diagonal (✓) son los aciertos.</Explicacion>
                  </>
                ),
              },
            ]} />
          </section>
          <p className="atenuado pie">Niveles usados: {datos.niveles_usados?.join(', ')}. Lo que se reporta al jurado usa solo Verificada y Alta.</p>
        </>
      )}
    </div>
  );
}
