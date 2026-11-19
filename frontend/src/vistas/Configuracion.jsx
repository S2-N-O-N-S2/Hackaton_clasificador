// Configuración: umbrales, calibración de ángulos, capacidades, modelo, etiquetas por verificar,
// control manual y (en simulación) residuos y teclas simuladas.
import { useEffect, useState } from 'react';
import { api, urlFoto } from '../api.js';
import { useEnVivo } from '../estado.jsx';
import { categoria } from '../categorias.js';
import { BotonCategoria, Categoria, MensajeError, Tarjeta, fechaHora, pct, useAccion, useDatos } from '../componentes/Comun.jsx';

const CAMPOS = [
  { clave: 'umbral_general', nombre: 'Umbral general (0–1)', tipo: 'fraccion' },
  { clave: 'umbral_peligroso', nombre: 'Umbral de peligroso (0–1)', tipo: 'fraccion' },
  { clave: 'umbral_tono_firme', nombre: 'Umbral de tono firme (0–1)', tipo: 'fraccion' },
  { clave: 'umbral_aviso_bote', nombre: 'Aviso de bote casi lleno (0–1)', tipo: 'fraccion' },
  { clave: 'umbral_desconocido', nombre: 'Objeto desconocido (0.5–3; menor = más estricto)', tipo: 'decimal' },
  { clave: 'tiempo_adivinanza_s', nombre: 'Tiempo para adivinar (s)', tipo: 'entero' },
  { clave: 'tiempo_revision_s', nombre: 'Tiempo de revisión (s)', tipo: 'entero' },
  { clave: 'tiempo_retro_firme_s', nombre: 'Retroalimentación firme (s)', tipo: 'entero' },
  { clave: 'tiempo_retro_media_s', nombre: 'Retroalimentación media (s)', tipo: 'entero' },
];

function Umbrales({ config, alGuardar }) {
  const [valores, setValores] = useState({});
  const { ejecutar, ocupado, error } = useAccion();
  const [guardado, setGuardado] = useState(false);
  useEffect(() => { setValores(config.valores); }, [config]);

  async function guardar(e) {
    e.preventDefault();
    const parcial = {};   // solo se envía lo que cambió (PUT parcial)
    CAMPOS.forEach(({ clave, tipo }) => {
      const v = tipo === 'entero' ? parseInt(valores[clave], 10) : parseFloat(valores[clave]);
      if (v !== config.valores[clave]) parcial[clave] = v;
    });
    if (valores.modo_por_defecto !== config.valores.modo_por_defecto) parcial.modo_por_defecto = valores.modo_por_defecto;
    if (Object.keys(parcial).length === 0) return;
    const r = await ejecutar(() => api.guardarConfig(parcial), { ok: 'Cambios guardados' });
    if (r) { setGuardado(true); alGuardar(r); setTimeout(() => setGuardado(false), 2000); }
  }

  return (
    <Tarjeta titulo="Reglas y tiempos">
      <form className="formulario rejilla-campos" onSubmit={guardar}>
        {CAMPOS.map(({ clave, nombre, tipo }) => (
          <label key={clave}>{nombre}
            <input type="number" step={tipo === 'entero' ? 1 : 0.01} min={0} max={tipo === 'fraccion' ? 1 : undefined}
              value={valores[clave] ?? ''} onChange={(e) => setValores({ ...valores, [clave]: e.target.value })} />
          </label>
        ))}
        <label>Modo por defecto
          <select value={valores.modo_por_defecto || 'ia'} onChange={(e) => setValores({ ...valores, modo_por_defecto: e.target.value })}>
            <option value="ia">IA</option>
            <option value="adivina">Adivina</option>
          </select>
        </label>
        <div>
          <button type="submit" className="boton-principal" disabled={ocupado}>Guardar cambios</button>
          {guardado && <span className="texto-ok"> Guardado ✔</span>}
        </div>
      </form>
      <MensajeError error={error} />
      <p className="atenuado pie">Cambio en vivo sugerido para la defensa: subir el umbral general y ver cómo más casos pasan a revisión.</p>
    </Tarjeta>
  );
}

// Calibración (Fase 5): mover el disco con ANG y guardar el ángulo de cada bote (el backend manda CAL).
function Calibracion({ config, alGuardar }) {
  const [grados, setGrados] = useState(90);
  const [angulos, setAngulos] = useState(config.valores.angulos);
  const [respuesta, setRespuesta] = useState(null);
  const { ejecutar, ocupado, error } = useAccion();
  useEffect(() => { setAngulos(config.valores.angulos); }, [config]);

  async function mover() {
    const r = await ejecutar(() => api.manual('ang', { grados: Number(grados) }), { ok: `Disco movido a ${grados}°` });
    if (r) setRespuesta(r.respuesta_arduino);
  }
  async function guardarComo(id) {
    const r = await ejecutar(() => api.guardarConfig({ angulos: { ...angulos, [id]: Number(grados) } }),
      { ok: `Ángulo de ${categoria(id).nombre}: ${grados}°` });
    if (r) alGuardar(r);
  }

  return (
    <Tarjeta titulo="Calibración de ángulos del disco">
      <label>Ángulo de prueba: <strong>{grados}°</strong>
        <input type="range" min="0" max="180" value={grados} onChange={(e) => setGrados(Number(e.target.value))} />
      </label>
      <div className="fila-botones">
        <button type="button" className="boton-principal" disabled={ocupado} onClick={mover}>Mover el disco (ANG)</button>
        {[0, 1, 2].map((id) => (
          <BotonCategoria key={id} id={id} disabled={ocupado} onClick={() => guardarComo(id)}>Guardar como {categoria(id).nombre}</BotonCategoria>
        ))}
      </div>
      <p>Ángulos guardados: {[0, 1, 2].map((id) => `${categoria(id).nombre} ${angulos?.[id] ?? '—'}°`).join(' · ')} · HOME {config.valores.angulo_home}°</p>
      {respuesta && <p className="atenuado">Arduino: {respuesta}</p>}
      <MensajeError error={error} />
    </Tarjeta>
  );
}

// Zona de interés de la cámara (contrato v1.2): [x, y, ancho, alto] en fracciones de la imagen.
function ZonaDeInteres({ config, alGuardar }) {
  const [roi, setRoi] = useState(config.valores.roi || [0, 0, 1, 1]);
  const { ejecutar, ocupado, error } = useAccion();
  useEffect(() => { setRoi(config.valores.roi || [0, 0, 1, 1]); }, [config]);
  if (!config.valores.roi) return null;   // backend sin ROI (contrato < 1.2)
  const nombres = ['x (izquierda)', 'y (arriba)', 'ancho', 'alto'];

  async function guardar(e) {
    e.preventDefault();
    const r = await ejecutar(() => api.guardarConfig({ roi: roi.map(Number) }), { ok: 'Zona de interés guardada' });
    if (r) alGuardar(r);
  }
  return (
    <Tarjeta titulo="Zona de interés de la cámara (ROI)">
      <form className="formulario rejilla-campos" onSubmit={guardar}>
        {nombres.map((n, i) => (
          <label key={n}>{n} (0–1)
            <input type="number" step="0.01" min="0" max="1" value={roi[i]}
              onChange={(e) => setRoi(roi.map((v, j) => (j === i ? e.target.value : v)))} />
          </label>
        ))}
        <div className="roi-vista" aria-label="Vista previa de la zona">
          <div className="roi-zona" style={{
            left: `${roi[0] * 100}%`, top: `${roi[1] * 100}%`, width: `${roi[2] * 100}%`, height: `${roi[3] * 100}%`,
          }} />
        </div>
        <div><button type="submit" className="boton-principal" disabled={ocupado}>Guardar zona</button></div>
      </form>
      <MensajeError error={error} />
      <p className="atenuado pie">La IA solo mira el rectángulo verde: recorta el fondo fuera de la bandeja.</p>
    </Tarjeta>
  );
}

function Capacidades() {
  const { botes } = useEnVivo();
  const [valores, setValores] = useState({});
  const { ejecutar, ocupado, error } = useAccion();
  if (!botes) return null;
  return (
    <Tarjeta titulo="Capacidad calibrada de los botes (ESTIMADO)">
      {botes.map((b) => (
        <form key={b.id} className="formulario en-linea" onSubmit={(e) => {
          e.preventDefault();
          ejecutar(() => api.ajustarBote(b.id, { capacidad_piezas: parseInt(valores[b.id] ?? b.capacidad_piezas, 10) }),
            { ok: `Capacidad del bote ${b.color} guardada` });
        }}>
          <label>{b.nombre} (piezas)
            <input type="number" min="1" step="1" value={valores[b.id] ?? b.capacidad_piezas}
              onChange={(e) => setValores({ ...valores, [b.id]: e.target.value })} />
          </label>
          <button type="submit" className="boton-secundario" disabled={ocupado}>Guardar</button>
          <span className="atenuado">{b.piezas_actuales}/{b.capacidad_piezas} · {pct(b.nivel)}</span>
        </form>
      ))}
      <MensajeError error={error} />
      <p className="atenuado pie">Para el momento 5 de la demo: baja temporalmente la capacidad (y díselo al jurado).</p>
    </Tarjeta>
  );
}

function Modelo() {
  const { modelo } = useEnVivo();
  const { ejecutar, ocupado, error } = useAccion();
  if (!modelo) return null;
  const r = modelo.ultimo_resultado;
  return (
    <Tarjeta titulo="Modelo de IA">
      <p>Activo: <strong>{modelo.activo ?? 'ninguno'}</strong></p>
      {modelo.mensaje && <p className="atenuado">{modelo.mensaje}</p>}
      {modelo.entrenando ? (
        <p>Reentrenando… {modelo.progreso !== null ? pct(modelo.progreso) : ''}</p>
      ) : (
        <button type="button" className="boton-principal" disabled={ocupado} onClick={() => ejecutar(() => api.reentrenar(), { ok: 'Reentrenamiento iniciado' })}>
          Reentrenar con las correcciones
        </button>
      )}
      {r && <p className={r.activado ? 'texto-ok' : 'texto-error'}>{r.mensaje} (validación {pct(r.precision_val, 1)} vs. {pct(r.precision_anterior, 1)})</p>}
      <div className="tabla-desplazable">
      <table className="tabla">
        <thead><tr><th>Versión</th><th>Fecha</th><th>Imágenes</th><th>Precisión val.</th><th>Activa</th></tr></thead>
        <tbody>
          {modelo.versiones.map((v) => (
            <tr key={v.version}><td>{v.version}</td><td>{fechaHora(v.fecha)}</td><td>{v.n_imagenes}</td><td>{pct(v.precision_val, 1)}</td><td>{v.activo ? '✔' : ''}</td></tr>
          ))}
        </tbody>
      </table>
      </div>
      <MensajeError error={error} />
      <p className="atenuado pie">El nuevo modelo solo se activa si su precisión de validación no empeora.</p>
    </Tarjeta>
  );
}

function PorVerificar() {
  const { datos, error, recargar } = useDatos(() => api.porVerificar(), []);
  const accion = useAccion();
  async function decidir(id, a) {
    const r = await accion.ejecutar(() => api.decidirPorVerificar(id, a), { ok: a === 'aprobar' ? 'Etiqueta aprobada' : 'Etiqueta rechazada' });
    if (r) recargar();
  }
  return (
    <Tarjeta titulo="Etiquetas por verificar (aportadas por usuarios)">
      {datos?.items?.length ? (
        <div className="lista-verificar">
          {datos.items.map((it) => (
            <div key={it.id} className="item-verificar">
              <img className="miniatura" src={urlFoto(it.foto)} alt={it.id} />
              <div>
                <Categoria id={it.clase_id} /> <span className="atenuado">por {it.origen} · {fechaHora(it.fecha_hora)}</span>
              </div>
              <button type="button" className="boton-mini aprobar" disabled={accion.ocupado} onClick={() => decidir(it.id, 'aprobar')}>Aprobar</button>
              <button type="button" className="boton-mini rechazar" disabled={accion.ocupado} onClick={() => decidir(it.id, 'rechazar')}>Rechazar</button>
            </div>
          ))}
        </div>
      ) : <p className="atenuado">No hay etiquetas pendientes.</p>}
      <MensajeError error={error || accion.error} />
    </Tarjeta>
  );
}

function ControlManual() {
  const { maquina } = useEnVivo();
  const [respuesta, setRespuesta] = useState(null);
  const { ejecutar, ocupado, error } = useAccion();
  const permitido = ['MENU', 'OPERADOR', 'ERROR'].includes(maquina?.estado);
  async function hacer(accion, cuerpo) {
    const r = await ejecutar(() => api.manual(accion, cuerpo), { ok: `${accion.toUpperCase()} enviado al Arduino` });
    if (r) setRespuesta(`${accion.toUpperCase()} → ${r.respuesta_arduino}`);
  }
  return (
    <Tarjeta titulo="Control manual (se registra como manual)">
      {!permitido && <p className="texto-error">Solo en MENÚ, OPERADOR o ERROR.</p>}
      <div className="fila-botones">
        {[0, 1, 2].map((id) => (
          <BotonCategoria key={id} id={id} disabled={ocupado || !permitido} onClick={() => hacer('pos', { id })}>POS {categoria(id).nombre}</BotonCategoria>
        ))}
        <button type="button" className="boton-secundario" disabled={ocupado || !permitido} onClick={() => hacer('home')}>HOME</button>
        <button type="button" className="boton-secundario" disabled={ocupado || !permitido} onClick={() => hacer('drop')}>Abrir trampilla</button>
        <button type="button" className="boton-secundario" disabled={ocupado || !permitido} onClick={() => hacer('light', { on: true })}>Luz ON</button>
        <button type="button" className="boton-secundario" disabled={ocupado || !permitido} onClick={() => hacer('light', { on: false })}>Luz OFF</button>
        {['VERDE', 'AMARILLO', 'ROJO', 'OFF'].map((c) => (
          <button key={c} type="button" className="boton-secundario" disabled={ocupado || !permitido}
            onClick={() => hacer('led', { color: c, parpadeo: false })}>LED {c}</button>
        ))}
      </div>
      {respuesta && <p className="atenuado">Arduino: {respuesta}</p>}
      <MensajeError error={error} />
    </Tarjeta>
  );
}

// Solo con el backend en SIMULACION=1 (o datos de ejemplo): simula un residuo o una tecla.
function Simulacion() {
  const { ejecutar, ocupado, error } = useAccion();
  const teclas = ['1', '2', '3', 'A', '4', '5', '6', 'B', '7', '8', '9', 'C', '*', '0', '#', 'D'];
  return (
    <Tarjeta titulo="Simulación (sin hardware)" className="tarjeta-simulacion">
      <p>Colocar un residuo simulado:</p>
      <div className="fila-botones">
        <button type="button" className="boton-secundario" disabled={ocupado} onClick={() => ejecutar(() => api.simObjeto(), { ok: 'Residuo simulado colocado' })}>Al azar</button>
        {[0, 1, 2].map((id) => (
          <BotonCategoria key={id} id={id} disabled={ocupado}
            onClick={() => ejecutar(() => api.simObjeto(id), { ok: `Residuo simulado: ${categoria(id).nombre}` })} />
        ))}
        <button type="button" className="boton-secundario" disabled={ocupado}
          onClick={() => ejecutar(() => api.simObjeto('desconocido'), { ok: 'Objeto desconocido simulado' })}>Objeto desconocido</button>
        <button type="button" className="boton-secundario" disabled={ocupado}
          onClick={() => ejecutar(() => api.simObjeto('foto_mala'), { ok: 'Foto mala simulada' })}>Foto mala</button>
      </div>
      <button type="button" className="boton-secundario" disabled={ocupado} onClick={() => ejecutar(() => api.simRetirar(), { ok: 'Bandeja libre' })}>
        Retirar el residuo de la bandeja (LIBRE)
      </button>
      <p>Teclado 4×4 simulado:</p>
      <div className="teclado">
        {teclas.map((t) => (
          <button key={t} type="button" className="tecla-boton" disabled={ocupado} onClick={() => ejecutar(() => api.simTecla(t))}>{t}</button>
        ))}
      </div>
      <MensajeError error={error} />
    </Tarjeta>
  );
}

export default function Configuracion() {
  const { maquina } = useEnVivo();
  const config = useDatos(() => api.config(), []);
  const [actual, setActual] = useState(null);
  const valores = actual || config.datos;

  return (
    <div className="vista">
      <h1>Configuración</h1>
      <MensajeError error={config.error} />
      {maquina?.simulacion && <Simulacion />}
      {valores && (
        <div className="rejilla-2">
          <Umbrales config={valores} alGuardar={setActual} />
          <Calibracion config={valores} alGuardar={setActual} />
          <ZonaDeInteres config={valores} alGuardar={setActual} />
          <Capacidades />
          <Modelo />
          <PorVerificar />
          <ControlManual />
        </div>
      )}
      {valores && (
        <p className="atenuado pie">
          Puerto serial: {valores.valores.puerto_serial} · cámara: {String(valores.valores.indice_camara)} (índice o URL del celular).
          {valores.requieren_reinicio?.length > 0 && ` Cambiar ${valores.requieren_reinicio.join(' o ')} requiere reiniciar el backend.`}
        </p>
      )}
    </div>
  );
}
