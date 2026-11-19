// =============================================================================
//  Servidor SIMULADO para trabajar sin backend (npm run dev:mock o VITE_MOCK=1).
//
//  Imita la API y el WebSocket del contrato (docs/api_contrato.md) con datos de ejemplo:
//  cada pocos segundos llega un residuo simulado y recorre la máquina de estados.
//  TODO lo que sale de aquí es SIMULADO ("simulado": true) y el panel lo rotula así.
//
//  Importante: este archivo hace de "backend falso" para probar el panel. El panel real
//  NO calcula reglas ni estadísticas: las recibe del backend de Python (contrato, sección 6).
// =============================================================================
import { ErrorApi } from '../errores.js';
import estadoEjemplo from './estado.json';
import clasificacionEjemplo from './clasificacion.json';
import botesEjemplo from './botes.json';
import modeloEjemplo from './modelo.json';
import configEjemplo from './config.json';
import juegoEstadisticasEjemplo from './juego_estadisticas.json';
import aprendizajeEjemplo from './juego_aprendizaje.json';
import porVerificarEjemplo from './por_verificar.json';
import pruebasEjemplo from './pruebas.json';

const CICLO_AUTOMATICO_MS = 7000;  // en MENU, cada 7 s llega un residuo simulado
const ESPERA_OBJETO_MS = 3000;     // tras elegir un modo, el residuo "llega" a los 3 s
const LATENCIA_MS = 120;           // demora de cada respuesta REST
const CLAVES = ['organica', 'inorganica', 'peligroso'];
const COLOR = ['verde', 'azul', 'gris'];

const copia = (x) => JSON.parse(JSON.stringify(x));
const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
const redondear = (x) => Math.round(x * 1000) / 1000;
const sinAcentos = (t) => t.normalize('NFD').replace(/[̀-ͯ]/g, '');

function fechaIso(d = new Date()) {
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

// Imagen de ejemplo dibujada en SVG (no hay cámara en el modo de ejemplo).
function fotoSimulada(categoriaReal, id) {
  const formas = [
    '<ellipse cx="160" cy="115" rx="80" ry="34" fill="#d9b43c" transform="rotate(-18 160 115)"/>',
    '<rect x="125" y="40" width="70" height="150" rx="20" fill="#a9d1f5" stroke="#3f74ad" stroke-width="5"/>',
    '<rect x="138" y="70" width="44" height="110" rx="6" fill="#3b3b3b"/><rect x="150" y="58" width="20" height="14" fill="#b5b5b5"/>',
  ];
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="320" height="240" viewBox="0 0 320 240">` +
    `<rect width="320" height="240" fill="#9aa0a8"/>${formas[categoriaReal]}` +
    `<text x="12" y="226" font-family="sans-serif" font-size="18" font-weight="bold" fill="#fff">SIMULADO #${id}</text></svg>`;
  return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
}

// ---------------------------------------------------------------------------
//  "Base de datos" en memoria (se pierde al recargar la página)
// ---------------------------------------------------------------------------
const db = {
  config: copia(configEjemplo),
  botes: copia(botesEjemplo.botes),
  vaciados: copia(botesEjemplo.vaciados),
  desviados: copia(botesEjemplo.desviados_por_categoria),
  clasificaciones: [],
  siguienteId: 43,
  modelo: copia(modeloEjemplo),
  porVerificar: copia(porVerificarEjemplo.items).map((i) => ({ ...i, foto: fotoSimulada(i.clase_id, i.clasificacion_id) })),
  residuos: copia(pruebasEjemplo.residuos),
  registros: [],
  siguientePrueba: 1,
  siguienteSesion: 1,
  sesion: { activa: false },
  ultimaRetro: null,
};

const maquina = {
  estado: 'MENU',
  estado_desde: fechaIso(),
  modo: null,
  mensaje: estadoEjemplo.mensaje,
  lcd: copia(estadoEjemplo.lcd),
  cuenta_regresiva_s: null,
  caso_actual: null,
  alertas: [],
};

let ocupado = false;          // hay un residuo en proceso
let esperaAccion = null;      // {tipo, resolver} mientras se espera al panel o al teclado
let ultimaActividad = Date.now();
const suscriptores = new Set();
let timerAutomatico = null;

// ---------------------------------------------------------------------------
//  Utilidades de la simulación
// ---------------------------------------------------------------------------
function vistaPublica(c) {
  if (!c) return null;
  const v = {};
  Object.keys(c).forEach((k) => { if (!k.startsWith('_')) v[k] = c[k]; });
  if (c._oculto) {   // modo Adivina: no se revela el resultado (contrato 2.1)
    delete v.probabilidades; delete v.pred_id; delete v.confianza; delete v.dudoso; delete v.motivo_dudoso;
    v.oculto = true;
  }
  return copia(v);
}

function emitir(tipo, datos) {
  const mensaje = { tipo, ts: fechaIso(), datos: copia(datos) };
  suscriptores.forEach((s) => s.alMensaje(mensaje));
}

function alerta(nivel, codigo, mensaje) {
  const a = { nivel, codigo, mensaje, fecha_hora: fechaIso() };
  maquina.alertas = [a, ...maquina.alertas].slice(0, 10);
  emitir('alerta', a);
}

function lineasLcd(...lineas) {
  const r = lineas.map((l) => sinAcentos(l || '').slice(0, 20));
  while (r.length < 4) r.push('');
  return r;
}

function transicion(estado, mensaje, { lcd, cuenta = null } = {}) {
  const anterior = maquina.estado;
  maquina.estado = estado;
  maquina.estado_desde = fechaIso();
  maquina.mensaje = mensaje;
  maquina.cuenta_regresiva_s = cuenta;
  maquina.lcd = lcd || lineasLcd('CLASIFICADOR', mensaje);
  emitir('estado', {
    estado, anterior, modo: maquina.modo, mensaje, lcd: maquina.lcd,
    cuenta_regresiva_s: cuenta, caso_actual: vistaPublica(maquina.caso_actual),
  });
}

function fotoDelEstado() {
  return {
    ...copia(estadoEjemplo),
    estado: maquina.estado,
    estado_desde: maquina.estado_desde,
    modo: maquina.modo,
    modo_por_defecto: db.config.valores.modo_por_defecto,
    mensaje: maquina.mensaje,
    lcd: maquina.lcd,
    cuenta_regresiva_s: maquina.cuenta_regresiva_s,
    caso_actual: vistaPublica(maquina.caso_actual),
    modelo: { cargado: true, version: db.modelo.activo, simulado: true },
    alertas: maquina.alertas,
  };
}

// Espera una acción del panel (o del teclado simulado). Devuelve null si se acaba el tiempo.
function esperarAccion(tipo, segundos) {
  return new Promise((resolver) => {
    let timer = null;
    if (segundos) {
      timer = setTimeout(() => { esperaAccion = null; resolver(null); }, segundos * 1000);
    }
    esperaAccion = {
      tipo,
      resolver: (valor) => { clearTimeout(timer); esperaAccion = null; resolver(valor); },
    };
  });
}

function generarProbabilidades(real) {
  const pred = Math.random() < 0.85 ? real : (real + 1 + Math.floor(Math.random() * 2)) % 3;
  const r = Math.random();
  let conf;
  if (r < 0.6) conf = 0.82 + Math.random() * 0.15;       // segura
  else if (r < 0.8) conf = 0.62 + Math.random() * 0.16; // certeza media
  else conf = 0.40 + Math.random() * 0.18;               // dudosa
  const p = [0, 0, 0];
  p[pred] = conf;
  const otros = [0, 1, 2].filter((i) => i !== pred);
  const a = Math.random();
  p[otros[0]] = (1 - conf) * a;
  p[otros[1]] = (1 - conf) * (1 - a);
  return { pred, p: p.map(redondear) };
}

function crearClasificacion(modo, real, fecha = new Date()) {
  const { valores } = db.config;
  const { pred, p } = generarProbabilidades(real);
  const confianza = p[pred];
  let motivo = null;
  if (confianza < valores.umbral_general) motivo = 'confianza_baja';
  else if (pred !== 2 && p[2] >= valores.umbral_peligroso) motivo = 'riesgo_peligroso';
  const id = db.siguienteId++;
  return {
    id,
    fecha_hora: fechaIso(fecha),
    foto: fotoSimulada(real, id),
    modo,
    probabilidades: { organica: p[0], inorganica: p[1], peligroso: p[2] },
    pred_id: pred,
    confianza,
    dudoso: motivo !== null,
    motivo_dudoso: motivo,
    final_id: null,
    origen: 'camara',
    corregido: false,
    modelo_version: db.modelo.activo,
    tiempo_ciclo_ms: null,
    drop_confirmado: null,
    bote_id: null,
    simulado: true,
    _real: real,
    _esperaHumanaMs: 0,
  };
}

function recalcularBote(b) {
  b.nivel = redondear(b.piezas_actuales / b.capacidad_piezas);
  b.estado = b.nivel >= 1 ? 'lleno' : b.nivel >= b.umbral_aviso ? 'casi_lleno' : 'normal';
  b.bloqueado = b.nivel >= 1;
}

function sumarPieza(id, confirmado) {
  const b = db.botes[id];
  const antes = b.estado;
  b.piezas_actuales += 1;
  if (!confirmado) b.no_confirmadas += 1;
  db.desviados[id] = (db.desviados[id] || 0) + 1;
  recalcularBote(b);
  emitir('bote', b);
  if (b.estado === 'casi_lleno' && antes === 'normal') {
    alerta('aviso', 'BOTE_CASI_LLENO', `Bote ${b.color} al ${Math.round(b.nivel * 100)} % (estimado)`);
  }
  if (b.estado === 'lleno' && antes !== 'lleno') {
    alerta('error', 'BOTE_LLENO', `Bote ${b.color} lleno (estimado ${b.piezas_actuales}/${b.capacidad_piezas})`);
  }
}

// Explicaciones de ejemplo (en el sistema real salen de backend/data/explicaciones.json).
const EXPLICACION = [
  'Proviene de un ser vivo y se descompone naturalmente; sirve para composta. (Texto de ejemplo)',
  'Plástico, metal, vidrio, papel o cartón no van a la composta; muchos se reciclan si están limpios. (Texto de ejemplo)',
  'Contiene o estuvo en contacto con sustancias tóxicas que contaminarían el suelo y el agua; requiere manejo especial. (Texto de ejemplo)',
];
const DATO = [
  'La composta reduce la basura que llega al relleno sanitario. (Dato de ejemplo)',
  'El PET y el aluminio limpios se reciclan muchas veces. (Dato de ejemplo)',
  'Las pilas van a un acopio especial, nunca a la basura común. (Dato de ejemplo)',
];

function iniciarSesionSiHaceFalta() {
  if (db.sesion.activa) return;
  db.sesion = {
    activa: true, id: db.siguienteSesion++, tipo: 'libre', alias: null, inicio: fechaIso(),
    intentos: 0, aciertos: 0, racha: 0, mejor_racha: 0,
  };
  emitir('sesion', db.sesion);
}

function anotarEnMarcador(correcto) {
  const s = db.sesion;
  s.intentos += 1;
  if (correcto) {
    s.aciertos += 1;
    s.racha += 1;
    s.mejor_racha = Math.max(s.mejor_racha, s.racha);
  } else {
    s.racha = 0;
  }
  emitir('sesion', s);
}

// ---------------------------------------------------------------------------
//  Ciclo simulado (sección 10 de la especificación)
// ---------------------------------------------------------------------------
async function faseAdivina(c) {
  const { valores } = db.config;
  iniciarSesionSiHaceFalta();
  transicion('ESPERA_ADIVINANZA', '¿A qué bote va?', {
    cuenta: valores.tiempo_adivinanza_s,
    lcd: lineasLcd('A que bote va?', '1:Organica  (verde)', '2:Inorganica (azul)', '3:Peligroso (gris)'),
  });
  const t0 = Date.now();
  const r = await esperarAccion('adivinanza', valores.tiempo_adivinanza_s);
  c._esperaHumanaMs += Date.now() - t0;
  const respuesta = r ? r.categoria : null;

  const retro = {
    adivinanza_id: db.siguienteId * 10,
    clasificacion_id: c.id,
    numero_intento: db.sesion.intentos + 1,
    respuesta_usuario: respuesta,
    categoria_referencia: c.dudoso ? null : c.pred_id,
    fuente_referencia: 'ia',
    confianza_ia: c.confianza,
    medio: r ? r.medio : 'sin_respuesta',
    puede_reportar: false,
    dato_categoria: null,
  };
  if (c.dudoso) {
    Object.assign(retro, {
      nivel_certeza: 'baja', correcto: null, tono: 'prudente', titulo: 'La IA tampoco esta segura',
      explicacion_corta: 'La IA no esta segura', explicacion_larga: 'La IA no está segura; un operador decidirá. Tu respuesta se calificará después.',
      tiempo_en_pantalla_s: 0, pendiente_operador: true,
    });
  } else {
    const firme = c.confianza >= valores.umbral_tono_firme;
    const correcto = respuesta === null ? null : respuesta === c.pred_id;
    let titulo;
    if (correcto === null) titulo = 'Sin respuesta';
    else if (firme) titulo = correcto ? '¡CORRECTO!' : 'INCORRECTO';
    else titulo = correcto ? 'PARECE CORRECTO' : 'PROBABLEMENTE NO';
    const texto = EXPLICACION[c.pred_id];
    Object.assign(retro, {
      nivel_certeza: firme ? 'alta' : 'media',
      correcto,
      tono: firme ? 'firme' : 'prudente',
      titulo,
      explicacion_corta: sinAcentos(texto).slice(0, 60),
      explicacion_larga: firme ? texto : `Probablemente va en ${['Orgánica', 'Inorgánica', 'Peligroso'][c.pred_id]}: ${texto}`,
      dato_categoria: correcto ? DATO[c.pred_id] : null,
      tiempo_en_pantalla_s: firme ? valores.tiempo_retro_firme_s : valores.tiempo_retro_media_s,
      puede_reportar: true,
    });
    if (correcto !== null) anotarEnMarcador(correcto);
  }
  retro.marcador = {
    aciertos: db.sesion.aciertos, intentos: db.sesion.intentos, racha: db.sesion.racha, mejor_racha: db.sesion.mejor_racha,
  };
  db.ultimaRetro = retro;
  c._adivinanza = respuesta;

  c._oculto = false;   // ya respondió: se revela el resultado
  emitir('clasificacion', vistaPublica(c));
  emitir('retroalimentacion', retro);
  if (c.dudoso) return null;   // pasa a REVISION

  transicion('RETROALIMENTACION', retro.titulo, {
    cuenta: retro.tiempo_en_pantalla_s,
    lcd: lineasLcd(retro.titulo, `Va en ${CLAVES[c.pred_id].toUpperCase()}`, `IA ${Math.round(c.confianza * 100)}%`, '*: si crees que no'),
  });
  const t1 = Date.now();
  const r2 = await esperarAccion('retro', retro.tiempo_en_pantalla_s);
  c._esperaHumanaMs += Date.now() - t1;
  if (r2 && r2.reportar) {
    c.dudoso = true;
    c.motivo_dudoso = 'confianza_baja';
    return null;
  }
  return c.pred_id;
}

async function faseRevision(c) {
  const { valores } = db.config;
  transicion('REVISION', 'IA dudosa: ayúdanos a clasificar', {
    cuenta: valores.tiempo_revision_s,
    lcd: lineasLcd('NO ESTOY SEGURO', 'Que es este residuo?', '1/2/3 o A: hablar', 'Panel: operador'),
  });
  emitir('revision', { clasificacion: vistaPublica(c), motivo: c.motivo_dudoso, tiempo_limite_s: valores.tiempo_revision_s });
  alerta('aviso', 'REVISION_PENDIENTE', `Caso #${c.id} en revisión`);
  const t0 = Date.now();
  const r = await esperarAccion('revision', valores.tiempo_revision_s);
  c._esperaHumanaMs += Date.now() - t0;
  if (!r || r.pendiente) return null;
  c.final_id = r.final_id;
  c.corregido = true;
  c.origen = r.origen || 'panel';
  return r.final_id;
}

function volverAlMenu() {
  maquina.caso_actual = null;
  maquina.modo = null;
  ultimaActividad = Date.now();
  transicion('MENU', estadoEjemplo.mensaje, { lcd: copia(estadoEjemplo.lcd) });
  emitir('modo', { modo: null });
}

async function procesarResiduo(modo, categoriaReal) {
  if (ocupado) return;
  ocupado = true;
  try {
    const inicio = Date.now();
    const real = categoriaReal ?? Math.floor(Math.random() * 3);
    const c = crearClasificacion(modo, real);
    c._oculto = modo === 'adivina';
    maquina.caso_actual = c;
    maquina.modo = modo;

    transicion('CAPTURA', 'Tomando la foto');
    emitir('captura', { clasificacion_id: c.id, foto: c.foto, oculto: c._oculto });
    await esperar(800);
    transicion('CLASIFICACION', 'Clasificando');
    await esperar(800);

    let destino;
    if (modo === 'adivina') {
      destino = await faseAdivina(c);
    } else {
      emitir('clasificacion', vistaPublica(c));
      destino = c.dudoso ? null : c.pred_id;
    }
    if (destino === null) {
      destino = await faseRevision(c);
      if (destino === null) {
        transicion('PENDIENTE', 'Revisión pendiente: un operador retira el residuo');
        await esperar(2500);
        db.clasificaciones.unshift(c);
        emitir('registrado', vistaPublica(c));
        volverAlMenu();
        return;
      }
    }
    c.final_id = destino;

    transicion('VERIFICAR_BOTE', 'Revisando el nivel del bote');
    await esperar(500);
    const bote = db.botes[destino];
    if (bote.bloqueado) {
      transicion('BOTE_LLENO', `Bote ${bote.color} lleno: vacíelo`, {
        lcd: lineasLcd(`BOTE ${bote.color.toUpperCase()} LLENO`, `(estimado ${bote.piezas_actuales}/${bote.capacidad_piezas})`, 'Vacie y presione', `D y luego ${destino + 1}`),
      });
      const t0 = Date.now();
      await esperarAccion('bote');
      c._esperaHumanaMs += Date.now() - t0;
    }

    transicion('POSICIONAR', `Girando al bote ${COLOR[destino]}`);
    await esperar(1500);
    transicion('SOLTAR', 'Soltando el residuo');
    await esperar(900);
    c.drop_confirmado = Math.random() > 0.05;
    if (!c.drop_confirmado) alerta('aviso', 'DROP_TIMEOUT', 'No se confirmó la caída (simulado)');
    c.bote_id = destino;

    transicion('REGISTRAR', 'Registrando');
    c.tiempo_ciclo_ms = Date.now() - inicio - c._esperaHumanaMs;  // solo tiempo de máquina
    c._oculto = false;
    db.clasificaciones.unshift(c);
    emitir('registrado', vistaPublica(c));
    await esperar(300);
    transicion('ACTUALIZAR_NIVEL', 'Actualizando el nivel estimado');
    sumarPieza(destino, c.drop_confirmado);
    await esperar(300);
    transicion('HOME', 'Regresando el disco');
    await esperar(900);
    volverAlMenu();
  } finally {
    ocupado = false;
  }
}

function revisarCicloAutomatico() {
  if (ocupado) return;
  const pasado = Date.now() - ultimaActividad;
  if (maquina.estado === 'MENU' && pasado > CICLO_AUTOMATICO_MS) {
    procesarResiduo(db.config.valores.modo_por_defecto);
  } else if (maquina.estado === 'ESPERA_OBJETO' && pasado > ESPERA_OBJETO_MS) {
    procesarResiduo(maquina.modo);
  }
}

// Datos iniciales del historial (todos SIMULADOS)
(function sembrar() {
  const ejemplo = { ...copia(clasificacionEjemplo), foto: fotoSimulada(0, 42), _real: 0 };
  ejemplo.fecha_hora = fechaIso(new Date(Date.now() - 13 * 60000));
  for (let i = 12; i >= 1; i--) {
    const real = i % 3;
    const c = crearClasificacion('ia', real, new Date(Date.now() - i * 60000));
    c.final_id = c.dudoso ? real : c.pred_id;
    if (c.dudoso) { c.corregido = true; c.origen = 'panel'; }
    c.tiempo_ciclo_ms = 2800 + Math.round(Math.random() * 800);
    c.drop_confirmado = true;
    c.bote_id = c.final_id;
    db.clasificaciones.unshift(c);
  }
  db.clasificaciones.push(ejemplo);
})();

// ---------------------------------------------------------------------------
//  "WebSocket" simulado
// ---------------------------------------------------------------------------
export function suscribir(alMensaje, alCambiarConexion) {
  const s = { alMensaje };
  suscriptores.add(s);
  setTimeout(() => {
    alCambiarConexion('en_vivo');
    alMensaje({ tipo: 'hola', ts: fechaIso(), datos: fotoDelEstado() });
  }, 300);
  if (!timerAutomatico) timerAutomatico = setInterval(revisarCicloAutomatico, 500);
  return () => {
    suscriptores.delete(s);
    if (suscriptores.size === 0) {
      clearInterval(timerAutomatico);
      timerAutomatico = null;
    }
  };
}

// ---------------------------------------------------------------------------
//  API REST simulada
// ---------------------------------------------------------------------------
function exigir(condicion, status, mensaje) {
  if (!condicion) throw new ErrorApi(status, mensaje);
}

const esCategoria = (x) => Number.isInteger(x) && x >= 0 && x <= 2;
const esFraccion = (x) => typeof x === 'number' && x >= 0 && x <= 1;
const esAngulo = (x) => Number.isInteger(x) && x >= 0 && x <= 180;

function filtrarSimulado(lista, simulado) {
  if (simulado === 'excluir') return lista.filter((c) => !c.simulado);
  if (simulado === 'solo') return lista.filter((c) => c.simulado);
  return lista;
}

function calcularEstadisticas(simulado) {
  const filtradas = filtrarSimulado(db.clasificaciones, simulado);
  const casos = filtradas.filter((c) => c.final_id !== null);
  const matriz = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
  const porCategoria = {};
  const desviados = { 0: 0, 1: 0, 2: 0 };
  casos.forEach((c) => {
    matriz[c.final_id][c.pred_id] += 1;
    if (c.bote_id !== null) desviados[c.final_id] += 1;
  });
  let aciertos = 0;
  [0, 1, 2].forEach((k) => {
    const conteo = casos.filter((c) => c.final_id === k).length;
    const ac = matriz[k][k];
    aciertos += ac;
    porCategoria[k] = { conteo, aciertos: ac, precision: conteo ? redondear(ac / conteo) : null };
  });
  const tiempos = casos.map((c) => c.tiempo_ciclo_ms).filter((t) => t !== null);
  return {
    muestra: casos.length,
    por_categoria: porCategoria,
    tasa_acierto: casos.length ? redondear(aciertos / casos.length) : null,
    matriz_confusion: { etiquetas: [0, 1, 2], filas: 'real', columnas: 'predicha', valores: matriz },
    dudosos: filtradas.filter((c) => c.dudoso).length,
    corregidos: filtradas.filter((c) => c.corregido).length,
    tiempo_promedio_ms: tiempos.length ? Math.round(tiempos.reduce((a, b) => a + b, 0) / tiempos.length) : null,
    desviados_por_categoria: desviados,
    incluye_simulados: simulado !== 'excluir',
  };
}

function calcularComparativa() {
  const resumen = (modo) => {
    const regs = db.registros.filter((r) => r.modo === modo);
    const matriz = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
    regs.forEach((r) => {
      const res = db.residuos.find((x) => x.id === r.residuo_id);
      if (res) matriz[res.categoria_real][r.categoria_asignada] += 1;
    });
    const ac = regs.filter((r) => r.correcto).length;
    return {
      resumen: {
        n: regs.length, aciertos: ac,
        precision: regs.length ? redondear(ac / regs.length) : null,
        tiempo_promedio_s: regs.length ? redondear(regs.reduce((a, r) => a + r.tiempo_s, 0) / regs.length) : null,
      },
      matriz: { etiquetas: [0, 1, 2], filas: 'real', columnas: 'asignada', valores: matriz },
    };
  };
  const manual = resumen('manual');
  const sistema = resumen('sistema');
  return { manual: manual.resumen, sistema: sistema.resumen, matriz_manual: manual.matriz, matriz_sistema: sistema.matriz };
}

function estadoDelModelo() {
  return db.modelo;
}

async function reentrenarSimulado() {
  db.modelo.entrenando = true;
  for (let p = 0.2; p <= 1.0001; p += 0.2) {
    db.modelo.progreso = redondear(p);
    emitir('modelo', db.modelo);
    await esperar(800);
  }
  const anterior = db.modelo.versiones.find((v) => v.activo);
  const n = db.modelo.versiones.length + 2;
  const precision = redondear(0.85 + Math.random() * 0.1);
  const activado = !anterior || precision >= anterior.precision_val;
  const version = `v${n}`;
  if (activado) {
    db.modelo.versiones.forEach((v) => { v.activo = false; });
    db.modelo.activo = version;
  }
  db.modelo.versiones.push({ version, fecha: fechaIso(), n_imagenes: 150 + n * 5, precision_val: precision, activo: activado });
  db.modelo.ultimo_resultado = {
    version, precision_val: precision, precision_anterior: anterior ? anterior.precision_val : null, activado,
    mensaje: activado ? `${version} activado: no empeoró` : `${version} descartado: empeoró`,
  };
  db.modelo.entrenando = false;
  db.modelo.progreso = null;
  emitir('modelo', db.modelo);
}

// Teclado simulado: imita lo que haría el orquestador con cada tecla (solo para probar el panel).
function teclaSimulada(tecla) {
  emitir('tecla', { tecla });
  ultimaActividad = Date.now();
  const tipo = esperaAccion && esperaAccion.tipo;
  if (maquina.estado === 'MENU' && (tecla === '1' || tecla === '2')) {
    elegirModo(tecla === '1' ? 'ia' : 'adivina');
  } else if (tipo === 'adivinanza' && ['1', '2', '3'].includes(tecla)) {
    esperaAccion.resolver({ categoria: Number(tecla) - 1, medio: 'teclado' });
  } else if (tipo === 'revision' && ['1', '2', '3'].includes(tecla)) {
    esperaAccion.resolver({ final_id: Number(tecla) - 1, origen: 'teclado' });
  } else if (tipo === 'retro' && tecla === 'B') {
    esperaAccion.resolver({ continuar: true });
  } else if (tipo === 'retro' && tecla === '*' && db.ultimaRetro && db.ultimaRetro.puede_reportar) {
    esperaAccion.resolver({ reportar: true });
  } else if (maquina.estado === 'ESPERA_OBJETO' && tecla === '#') {
    volverAlMenu();
  }
}

function elegirModo(modo) {
  ultimaActividad = Date.now();
  if (modo === 'menu') {
    volverAlMenu();
    return;
  }
  maquina.modo = modo;
  emitir('modo', { modo });
  if (modo === 'adivina') iniciarSesionSiHaceFalta();
  transicion('ESPERA_OBJETO', modo === 'ia' ? 'Modo IA: coloca el residuo' : 'Modo Adivina: coloca el residuo', {
    lcd: modo === 'ia'
      ? lineasLcd('MODO IA', 'Coloca el residuo', 'en la bandeja', '#: volver al menu')
      : lineasLcd('MODO ADIVINA', 'Coloca el residuo', 'en la bandeja', '#: volver al menu'),
  });
}

// Devuelve siempre una COPIA, como lo haría un backend real (JSON nuevo en cada respuesta).
export async function pedir(metodo, rutaCompleta, cuerpo) {
  return copia(await atender(metodo, rutaCompleta, cuerpo || {}));
}

async function atender(metodo, rutaCompleta, cuerpo) {
  await esperar(LATENCIA_MS);
  const url = new URL(rutaCompleta, 'http://simulado');
  const ruta = url.pathname;
  const q = url.searchParams;
  const m = (patron) => ruta.match(patron);
  let r;

  // 3.1 Estado
  if (metodo === 'GET' && ruta === '/api/estado') return fotoDelEstado();

  // 3.2 Modo
  if (ruta === '/api/modo') {
    if (metodo === 'POST') {
      exigir(['ia', 'adivina', 'menu'].includes(cuerpo.modo), 422, 'modo inválido');
      exigir(!ocupado, 409, 'Hay un residuo en proceso');
      elegirModo(cuerpo.modo);
    }
    return { modo: maquina.modo, estado: maquina.estado };
  }

  // 3.3 Clasificaciones
  if (metodo === 'GET' && ruta === '/api/clasificaciones') {
    let lista = filtrarSimulado(db.clasificaciones, q.get('simulado') || 'incluir');
    if (q.get('dudosos') === '1') lista = lista.filter((c) => c.dudoso);
    if (q.get('dudosos') === '0') lista = lista.filter((c) => !c.dudoso);
    const limit = Number(q.get('limit') || 50);
    const offset = Number(q.get('offset') || 0);
    return { total: lista.length, items: lista.slice(offset, offset + limit).map(vistaPublica) };
  }
  if (metodo === 'POST' && (r = m(/^\/api\/clasificaciones\/(\d+)\/corregir$/))) {
    const c = db.clasificaciones.find((x) => x.id === Number(r[1]));
    exigir(c, 404, 'La clasificación no existe');
    exigir(esCategoria(cuerpo.final_id), 422, 'final_id debe ser 0, 1 o 2');
    c.final_id = cuerpo.final_id;
    c.corregido = true;
    c.origen = 'panel';
    return vistaPublica(c);
  }

  // 3.4 Revisión
  if (metodo === 'POST' && ruta === '/api/revision') {
    exigir(maquina.estado === 'REVISION' && esperaAccion && esperaAccion.tipo === 'revision', 409, 'El estado no es REVISION');
    if (cuerpo.accion === 'pendiente') {
      esperaAccion.resolver({ pendiente: true });
      return { ok: true, estado: 'PENDIENTE' };
    }
    exigir(cuerpo.accion === 'resolver' && esCategoria(cuerpo.final_id), 422, 'Acción o categoría inválida');
    esperaAccion.resolver({ final_id: cuerpo.final_id, origen: 'panel' });
    return { ok: true, estado: 'VERIFICAR_BOTE' };
  }

  // 3.5 Estadísticas
  if (metodo === 'GET' && ruta === '/api/estadisticas') return calcularEstadisticas(q.get('simulado') || 'incluir');

  // 3.6 Pruebas
  if (ruta === '/api/pruebas' && metodo === 'GET') {
    return { residuos: db.residuos, registros: db.registros, comparativa: calcularComparativa() };
  }
  if (ruta === '/api/pruebas' && metodo === 'POST') {
    const res = db.residuos.find((x) => x.id === cuerpo.residuo_id);
    exigir(res, 404, 'El residuo no existe');
    exigir(['manual', 'sistema'].includes(cuerpo.modo), 422, 'modo inválido');
    exigir(esCategoria(cuerpo.categoria_asignada), 422, 'categoría inválida');
    exigir(typeof cuerpo.tiempo_s === 'number' && cuerpo.tiempo_s >= 0, 422, 'tiempo inválido');
    const prueba = {
      id: db.siguientePrueba++, corrida: cuerpo.corrida || 1, modo: cuerpo.modo, residuo_id: res.id,
      categoria_asignada: cuerpo.categoria_asignada, correcto: cuerpo.categoria_asignada === res.categoria_real,
      tiempo_s: cuerpo.tiempo_s, fecha_hora: fechaIso(),
    };
    db.registros.push(prueba);
    return prueba;
  }
  if (ruta === '/api/pruebas/residuos' && metodo === 'POST') {
    exigir(cuerpo.nombre && cuerpo.nombre.trim(), 400, 'Falta el nombre');
    exigir(esCategoria(cuerpo.categoria_real), 422, 'categoría inválida');
    const residuo = {
      id: Math.max(0, ...db.residuos.map((x) => x.id)) + 1, nombre: cuerpo.nombre.trim(),
      categoria_real: cuerpo.categoria_real, simulado: !!cuerpo.simulado, usado_en_entrenamiento: !!cuerpo.usado_en_entrenamiento,
    };
    db.residuos.push(residuo);
    return residuo;
  }

  // 3.7 Modelo
  if (metodo === 'POST' && ruta === '/api/modelo/reentrenar') {
    exigir(!db.modelo.entrenando, 409, 'Ya hay un entrenamiento en curso');
    reentrenarSimulado();
    return { estado: 'en_curso' };
  }
  if (metodo === 'GET' && ruta === '/api/modelo/estado') return estadoDelModelo();

  // 3.8 Configuración
  if (ruta === '/api/config') {
    if (metodo === 'PUT') {
      const v = db.config.valores;
      for (const [k, valor] of Object.entries(cuerpo)) {
        if (k.startsWith('umbral_')) exigir(esFraccion(valor), 422, `${k} debe estar entre 0 y 1`);
        else if (k === 'angulos') {
          Object.values(valor).forEach((a) => exigir(esAngulo(a), 422, 'Los ángulos van de 0 a 180'));
        } else if (k === 'angulo_home') exigir(esAngulo(valor), 422, 'El ángulo va de 0 a 180');
        else if (k === 'modo_por_defecto') exigir(['ia', 'adivina'].includes(valor), 422, 'modo inválido');
        else if (k.startsWith('tiempo_')) exigir(Number.isInteger(valor) && valor > 0, 422, `${k} debe ser un entero positivo`);
        else exigir(k in v, 422, `Clave desconocida: ${k}`);
      }
      Object.entries(cuerpo).forEach(([k, valor]) => {
        v[k] = k === 'angulos' ? { ...v.angulos, ...valor } : valor;
      });
    }
    return db.config;
  }

  // 3.9 Juego
  if (metodo === 'POST' && ruta === '/api/juego/adivinar') {
    exigir(maquina.estado === 'ESPERA_ADIVINANZA' && esperaAccion && esperaAccion.tipo === 'adivinanza', 409, 'El estado no es ESPERA_ADIVINANZA');
    exigir(esCategoria(cuerpo.categoria), 422, 'categoría inválida');
    esperaAccion.resolver({ categoria: cuerpo.categoria, medio: 'panel' });
    await esperar(20);   // deja que el ciclo calcule la retroalimentación
    return db.ultimaRetro;
  }
  if (metodo === 'POST' && ruta === '/api/juego/reportar-error') {
    exigir(maquina.estado === 'RETROALIMENTACION' && esperaAccion && esperaAccion.tipo === 'retro', 409, 'El estado no es RETROALIMENTACION');
    esperaAccion.resolver({ reportar: true });
    return { ok: true, estado: 'REVISION' };
  }
  if (metodo === 'POST' && ruta === '/api/juego/continuar') {
    exigir(esperaAccion && esperaAccion.tipo === 'retro', 409, 'No hay retroalimentación en pantalla');
    esperaAccion.resolver({ continuar: true });
    return { ok: true };
  }
  if (metodo === 'GET' && ruta === '/api/juego/sesion') return db.sesion;
  if (metodo === 'GET' && ruta === '/api/juego/estadisticas') {
    return { ...juegoEstadisticasEjemplo, niveles_usados: (q.get('niveles') || 'verificada,alta').split(',') };
  }
  if (metodo === 'GET' && ruta === '/api/juego/aprendizaje') {
    return { ...aprendizajeEjemplo, niveles_usados: (q.get('niveles') || 'verificada,alta').split(',') };
  }
  if (metodo === 'POST' && ruta === '/api/juego/prueba-aprendizaje') {
    exigir(cuerpo.alias && cuerpo.alias.trim(), 400, 'Falta el alias');
    exigir([1, 2].includes(cuerpo.ronda), 400, 'La ronda debe ser 1 o 2');
    exigir(Array.isArray(cuerpo.residuos) && cuerpo.residuos.length > 0, 400, 'No hay residuos de prueba seleccionados');
    const orden = [...cuerpo.residuos].sort(() => Math.random() - 0.5);
    return { sesion_id: db.siguienteSesion++, orden };
  }

  // 3.10 Botes
  if (metodo === 'GET' && ruta === '/api/botes') {
    return { botes: db.botes, vaciados: db.vaciados, desviados_por_categoria: db.desviados };
  }
  if ((r = m(/^\/api\/botes\/(\d)\/vaciar$/)) && metodo === 'POST') {
    const b = db.botes[Number(r[1])];
    exigir(b, 404, 'El bote no existe');
    db.vaciados.unshift({ id: db.vaciados.length + 1, bote_id: b.id, fecha_hora: fechaIso(), piezas_al_vaciar: b.piezas_actuales, origen: 'panel' });
    b.piezas_actuales = 0;
    b.no_confirmadas = 0;
    b.ultimo_vaciado = fechaIso();
    recalcularBote(b);
    emitir('bote', b);
    if (esperaAccion && esperaAccion.tipo === 'bote') esperaAccion.resolver({ vaciado: b.id });
    return b;
  }
  if ((r = m(/^\/api\/botes\/(\d)$/)) && metodo === 'PUT') {
    const b = db.botes[Number(r[1])];
    exigir(b, 404, 'El bote no existe');
    if ('capacidad_piezas' in cuerpo) exigir(Number.isInteger(cuerpo.capacidad_piezas) && cuerpo.capacidad_piezas >= 1, 422, 'La capacidad debe ser un entero ≥ 1');
    if ('umbral_aviso' in cuerpo) exigir(esFraccion(cuerpo.umbral_aviso), 422, 'El umbral va de 0 a 1');
    Object.assign(b, cuerpo);
    recalcularBote(b);
    emitir('bote', b);
    if (!b.bloqueado && esperaAccion && esperaAccion.tipo === 'bote') esperaAccion.resolver({ ajustado: b.id });
    return b;
  }

  // 3.11 Por verificar
  if (ruta === '/api/dataset/por-verificar') {
    if (metodo === 'POST') {
      const i = db.porVerificar.findIndex((x) => x.id === cuerpo.id);
      exigir(i >= 0, 404, 'La etiqueta no existe');
      exigir(['aprobar', 'rechazar'].includes(cuerpo.accion), 422, 'Acción inválida');
      db.porVerificar.splice(i, 1);
      return { ok: true, pendientes: db.porVerificar.length };
    }
    return { items: db.porVerificar };
  }

  // 3.12 Control manual
  if ((r = m(/^\/api\/manual\/(\w+)$/)) && metodo === 'POST') {
    exigir(['MENU', 'OPERADOR', 'ERROR'].includes(maquina.estado) && !ocupado, 409, 'Control manual solo en MENU, OPERADOR o ERROR');
    ultimaActividad = Date.now();
    await esperar(400);
    const accion = r[1];
    if (accion === 'pos') { exigir(esCategoria(cuerpo.id), 422, 'id inválido'); return { ok: true, respuesta_arduino: `POS_OK:${cuerpo.id}` }; }
    if (accion === 'ang') { exigir(esAngulo(cuerpo.grados), 422, 'Los grados van de 0 a 180'); return { ok: true, respuesta_arduino: `ANG_OK:${cuerpo.grados}` }; }
    if (accion === 'home') return { ok: true, respuesta_arduino: 'HOME_OK' };
    if (accion === 'drop') return { ok: true, respuesta_arduino: 'DROP_OK' };
    if (accion === 'light' || accion === 'led') return { ok: true, respuesta_arduino: 'OK' };
    throw new ErrorApi(404, 'Acción manual desconocida');
  }

  // 7. Simulación
  if (metodo === 'POST' && ruta === '/api/sim/objeto') {
    exigir(!ocupado, 409, 'Hay un residuo en proceso');
    ultimaActividad = Date.now();
    procesarResiduo(maquina.modo || db.config.valores.modo_por_defecto, cuerpo.categoria_real);
    return { ok: true };
  }
  if (metodo === 'POST' && ruta === '/api/sim/tecla') {
    teclaSimulada(String(cuerpo.tecla || ''));
    return { ok: true };
  }

  throw new ErrorApi(404, `Ruta no simulada: ${metodo} ${ruta}`);
}
