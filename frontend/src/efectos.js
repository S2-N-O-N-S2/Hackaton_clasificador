// =============================================================================
//  Efectos del juego: confeti (canvas) y sonidos (Web Audio). Sin bibliotecas ni archivos de audio:
//  los sonidos se generan con osciladores, así funcionan sin internet.
//  - Si la persona pidió "reducir movimiento" en su sistema, no hay confeti.
//  - El sonido se puede silenciar; la elección se guarda en el navegador.
// =============================================================================
import { useSyncExternalStore } from 'react';

const COLORES = ['#2E9E44', '#1E6FD9', '#6B7280', '#F2B705', '#0E7C86', '#FFFFFF'];
const reducido = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

// ---------------------------------------------------------------- confeti
let lienzo = null;
let piezas = [];
let animando = false;

function asegurarLienzo() {
  if (lienzo) return lienzo;
  lienzo = document.createElement('canvas');
  lienzo.className = 'lienzo-confeti';
  lienzo.setAttribute('aria-hidden', 'true');
  document.body.appendChild(lienzo);
  return lienzo;
}

function cuadro() {
  const ctx = lienzo.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  if (lienzo.width !== window.innerWidth * dpr || lienzo.height !== window.innerHeight * dpr) {
    lienzo.width = window.innerWidth * dpr;
    lienzo.height = window.innerHeight * dpr;
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
  piezas = piezas.filter((p) => p.vida > 0 && p.y < window.innerHeight + 40);
  for (const p of piezas) {
    p.vx *= 0.985;
    p.vy = p.vy * 0.985 + 0.32;          // gravedad
    p.x += p.vx;
    p.y += p.vy;
    p.giro += p.vgiro;
    p.vida -= 1;
    ctx.save();
    ctx.globalAlpha = Math.min(1, p.vida / 40);
    ctx.translate(p.x, p.y);
    ctx.rotate(p.giro);
    ctx.fillStyle = p.color;
    if (p.forma === 0) ctx.fillRect(-p.t / 2, -p.t / 4, p.t, p.t / 2);
    else { ctx.beginPath(); ctx.arc(0, 0, p.t / 3, 0, Math.PI * 2); ctx.fill(); }
    ctx.restore();
  }
  if (piezas.length) requestAnimationFrame(cuadro);
  else { animando = false; ctx.clearRect(0, 0, window.innerWidth, window.innerHeight); }
}

// Lanza confeti desde un punto (por defecto, el centro de la pantalla). `cantidad` ≈ 60 para un acierto.
export function confeti({ x, y, cantidad = 70, colores = COLORES } = {}) {
  if (reducido()) return;
  asegurarLienzo();
  const ox = x ?? window.innerWidth / 2;
  const oy = y ?? window.innerHeight / 2.5;
  for (let i = 0; i < cantidad; i += 1) {
    const angulo = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI * 1.1;
    const fuerza = 7 + Math.random() * 9;
    piezas.push({
      x: ox, y: oy, vx: Math.cos(angulo) * fuerza, vy: Math.sin(angulo) * fuerza,
      giro: Math.random() * Math.PI, vgiro: (Math.random() - 0.5) * 0.35,
      t: 8 + Math.random() * 7, forma: Math.random() < 0.7 ? 0 : 1,
      color: colores[Math.floor(Math.random() * colores.length)], vida: 110 + Math.random() * 60,
    });
  }
  if (!animando) { animando = true; requestAnimationFrame(cuadro); }
}

// Lluvia desde arriba (para el final del juego con buen resultado).
export function lluviaConfeti() {
  if (reducido()) return;
  const ancho = window.innerWidth;
  [0.2, 0.5, 0.8].forEach((f, i) => setTimeout(() => confeti({ x: ancho * f, y: window.innerHeight * 0.35, cantidad: 60 }), i * 180));
}

// ---------------------------------------------------------------- sonido
const CLAVE = 'panel-sonido';
let activo = (() => { try { return localStorage.getItem(CLAVE) !== 'no'; } catch { return true; } })();
const oyentes = new Set();
let audio = null;

export function sonidoActivo() { return activo; }
export function alternarSonido() {
  activo = !activo;
  try { localStorage.setItem(CLAVE, activo ? 'si' : 'no'); } catch { /* sin almacenamiento */ }
  oyentes.forEach((f) => f());
  if (activo) sonar('clic');
}
export function useSonido() {
  return useSyncExternalStore((f) => { oyentes.add(f); return () => oyentes.delete(f); }, () => activo);
}

function contexto() {
  if (!audio) {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    audio = new Ctx();
  }
  if (audio.state === 'suspended') audio.resume();
  return audio;
}

// Una nota con envolvente corta (sin clics al empezar ni al terminar).
function nota(ctx, frecuencia, inicio, duracion, { tipo = 'triangle', volumen = 0.18, hasta = null } = {}) {
  const osc = ctx.createOscillator();
  const g = ctx.createGain();
  osc.type = tipo;
  osc.frequency.setValueAtTime(frecuencia, inicio);
  if (hasta) osc.frequency.exponentialRampToValueAtTime(hasta, inicio + duracion);
  g.gain.setValueAtTime(0.0001, inicio);
  g.gain.exponentialRampToValueAtTime(volumen, inicio + 0.015);
  g.gain.exponentialRampToValueAtTime(0.0001, inicio + duracion);
  osc.connect(g).connect(ctx.destination);
  osc.start(inicio);
  osc.stop(inicio + duracion + 0.02);
}

const SONIDOS = {
  clic: (ctx, t) => nota(ctx, 660, t, 0.06, { tipo: 'square', volumen: 0.05 }),
  // Acierto: tres notas que suben (do-mi-sol) y un brillo.
  acierto: (ctx, t) => {
    [523.25, 659.25, 783.99].forEach((f, i) => nota(ctx, f, t + i * 0.075, 0.22));
    nota(ctx, 1567.98, t + 0.24, 0.3, { tipo: 'sine', volumen: 0.07 });
  },
  // Racha (3 o más seguidos): el acierto una octava arriba.
  racha: (ctx, t) => {
    [659.25, 783.99, 1046.5, 1318.5].forEach((f, i) => nota(ctx, f, t + i * 0.065, 0.2));
  },
  // Error: dos notas graves que bajan.
  error: (ctx, t) => {
    nota(ctx, 220, t, 0.16, { tipo: 'sawtooth', volumen: 0.07, hasta: 180 });
    nota(ctx, 174.6, t + 0.15, 0.3, { tipo: 'sawtooth', volumen: 0.07, hasta: 130 });
  },
  // Fin del juego: pequeña fanfarria.
  fin: (ctx, t) => {
    [523.25, 659.25, 783.99, 1046.5].forEach((f, i) => nota(ctx, f, t + i * 0.12, 0.28));
    [523.25, 659.25, 783.99].forEach((f) => nota(ctx, f, t + 0.5, 0.7, { volumen: 0.08 }));
  },
};

export function sonar(nombre) {
  if (!activo) return;
  try {
    const ctx = contexto();
    if (ctx && SONIDOS[nombre]) SONIDOS[nombre](ctx, ctx.currentTime + 0.01);
  } catch { /* el navegador no permite audio: el juego sigue sin sonido */ }
}
