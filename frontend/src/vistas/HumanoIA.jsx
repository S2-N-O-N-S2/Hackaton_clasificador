// Humano vs. IA (especificación 12.4). Todo viene calculado de GET /api/juego/estadisticas.
import { useState } from 'react';
import { api } from '../api.js';
import { useEnVivo } from '../estado.jsx';
import { categoria } from '../categorias.js';
import { Cifra, MensajeError, MuestraPequena, Tarjeta, pct, useDatos } from '../componentes/Comun.jsx';
import { BarrasHorizontales, MatrizConfusion } from '../componentes/Graficas.jsx';

export function FiltroNiveles({ niveles, alCambiar }) {
  const opciones = [
    { clave: 'verificada', nombre: 'Verificada' },
    { clave: 'alta', nombre: 'Alta' },
    { clave: 'media', nombre: 'Media (se reporta aparte)' },
  ];
  const cambiar = (clave) => {
    const nuevos = niveles.includes(clave) ? niveles.filter((n) => n !== clave) : [...niveles, clave];
    if (nuevos.length) alCambiar(nuevos);
  };
  return (
    <div className="filtros">
      <span>Niveles de certeza:</span>
      {opciones.map((o) => (
        <label key={o.clave} className="casilla">
          <input type="checkbox" checked={niveles.includes(o.clave)} onChange={() => cambiar(o.clave)} /> {o.nombre}
        </label>
      ))}
    </div>
  );
}

export default function HumanoIA() {
  const [niveles, setNiveles] = useState(['verificada', 'alta']);
  const { versiones } = useEnVivo();
  const { datos, error, cargando } = useDatos(() => api.estadisticasJuego(niveles), [niveles.join(','), versiones.historial]);

  return (
    <div className="vista">
      <h1>Humano vs. IA</h1>
      <FiltroNiveles niveles={niveles} alCambiar={setNiveles} />
      <MensajeError error={error} />
      {cargando && !datos && <p className="atenuado">Cargando…</p>}
      {datos && (
        <>
          <MuestraPequena si={datos.muestra_pequena} />
          <div className="cifras">
            <Cifra etiqueta="Acierto humano" valor={pct(datos.acierto_humano)} detalle={`n = ${datos.n_adivinanzas} adivinanzas`} />
            <Cifra etiqueta="Acierto de la IA (mismos residuos)" valor={pct(datos.humano_vs_ia?.acierto_ia)} detalle={`n = ${datos.humano_vs_ia?.n ?? '—'}`} />
            <Cifra etiqueta="Sesiones" valor={datos.n_sesiones} />
            <Cifra etiqueta="Certeza media (aparte)" valor={pct(datos.media_aparte?.acierto_humano)} detalle={`n = ${datos.media_aparte?.n_adivinanzas ?? 0}`} />
          </div>
          <div className="rejilla-2">
            <Tarjeta titulo="Humano vs. IA">
              <BarrasHorizontales items={[
                { etiqueta: 'Humano', valor: datos.humano_vs_ia?.acierto_humano, color: '#F28C05' },
                { etiqueta: 'IA', valor: datos.humano_vs_ia?.acierto_ia, color: '#1f2937' },
              ]} />
            </Tarjeta>
            <Tarjeta titulo="Acierto humano por categoría">
              <BarrasHorizontales items={[0, 1, 2].map((id) => ({
                etiqueta: categoria(id).nombre,
                valor: datos.por_categoria?.[id]?.acierto ?? null,
                color: categoria(id).hex,
                detalle: `n=${datos.por_categoria?.[id]?.n ?? 0}`,
              }))} />
            </Tarjeta>
            <Tarjeta titulo="Matriz de confusión humana">
              <MatrizConfusion matriz={datos.matriz_confusion_humana} columnas="Adivinanza" />
            </Tarjeta>
            <Tarjeta titulo="Confusiones más frecuentes">
              {datos.parejas_confusion?.length ? (
                <ol className="lista-parejas">
                  {datos.parejas_confusion.map((p) => (
                    <li key={`${p.dijo}-${p.era}`}>
                      Dijeron <strong style={{ color: categoria(p.dijo)?.hex }}>{categoria(p.dijo)?.nombre}</strong> y era{' '}
                      <strong style={{ color: categoria(p.era)?.hex }}>{categoria(p.era)?.nombre}</strong>: {p.veces} veces
                    </li>
                  ))}
                </ol>
              ) : <p className="atenuado">Sin confusiones registradas.</p>}
            </Tarjeta>
          </div>
          <p className="atenuado pie">Niveles usados: {datos.niveles_usados?.join(', ')}. Lo que se reporta al jurado usa solo Verificada y Alta.</p>
        </>
      )}
    </div>
  );
}
