// =============================================================================
//  Modal «Deposita tu residuo» (en todas las pestañas).
//  Aparece mientras la máquina está en SOLTAR: el bote elegido está al frente y la persona tiene
//  `tiempo_deposito_s` (10 s) para echar el residuo. La cuenta regresiva la manda el backend; cuando
//  termina, la base vuelve a reposo y el modal desaparece solo (el estado deja de ser SOLTAR).
// =============================================================================
import { useEnVivo, useCuentaRegresiva } from '../estado.jsx';
import { categoria } from '../categorias.js';
import { IconoCategoria } from './Comun.jsx';

export function ModalDeposito() {
  const { maquina, cuenta } = useEnVivo();
  const segundos = useCuentaRegresiva();
  const caso = maquina?.caso_actual;
  if (maquina?.estado !== 'SOLTAR' || !caso || caso.oculto || caso.final_id === null || caso.final_id === undefined) {
    return null;
  }
  const c = categoria(caso.final_id);
  const total = cuenta?.valor || 10;   // segundos con los que empezó la cuenta (tiempo_deposito_s)
  return (
    <div className="modal-fondo" role="presentation">
      <div className="modal-deposito" role="alertdialog" aria-modal="true" aria-labelledby="deposito-titulo"
        style={{ '--cat': c.hex }}>
        <div className="modal-deposito-icono"><IconoCategoria id={caso.final_id} tam={36} /></div>
        <h2 id="deposito-titulo">Deposita tu residuo</h2>
        <p className="modal-deposito-bote">en el bote <strong>{c.color}</strong> · {c.nombre}</p>
        {segundos !== null && (
          <>
            <div className="modal-deposito-cuenta" aria-live="polite">{segundos} s</div>
            <div className="modal-deposito-barra"><span style={{ width: `${Math.min(100, (segundos / total) * 100)}%` }} /></div>
          </>
        )}
        <p className="atenuado">Después la base regresa sola a reposo.</p>
      </div>
    </div>
  );
}
