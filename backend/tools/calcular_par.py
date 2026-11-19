"""
calcular_par.py — Fase 0: ¿caben los botes en el disco? y ¿qué servo necesita el carrusel?

Implementa las fórmulas de docs/mediciones.md (sección 5.3 de la especificación).
Solo usa la biblioteca estándar: se puede correr con cualquier Python 3.

Uso:
    python tools/calcular_par.py --ejemplo            # valores SUPUESTOS, solo para ver el cálculo
    python tools/calcular_par.py --d-bote 110 --r-bote 120 --r-disco 150 ^
        --m-disco 0.12 --m-bote-lleno 0.45 --m-contrapeso 0.2 --r-contrapeso 100 ^
        --r-canicas 70 --delta-phi 80

Unidades de entrada: milímetros y kilogramos (lo que dan el vernier y la báscula).
Los resultados con --ejemplo NO son mediciones: no los copien al reporte.
"""

from __future__ import annotations

import argparse
import math
import sys

# La consola de Windows usa cp1252 por defecto y falla con "≥", "²", etc.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

G = 9.81                    # m/s²
KGCM_A_NM = 0.0980665       # 1 kg·cm = 0.0981 N·m

# Par nominal del fabricante (hoja de datos típica). Verificar con el modelo real del servo.
PAR_SERVOS_KGCM = {
    "SG90 (4.8 V)": 1.8,
    "MG996R (4.8 V)": 9.4,
    "MG996R (6.0 V)": 11.0,
}

# Valores SUPUESTOS para demostrar el cálculo (NO medidos). Ver docs/mediciones.md.
EJEMPLO = dict(
    d_bote=110.0, r_bote=120.0, r_disco=150.0, delta_phi=80.0, holgura=10.0,
    m_disco=0.12, m_bote_lleno=0.45, n_botes=3, m_contrapeso=0.20, r_contrapeso=100.0,
    r_canicas=70.0, mu=0.05, omega_gps=66.7, t_acel=0.10, factor_seguridad=2.0,
)


def verificar_geometria(d_bote, r_bote, r_disco, delta_phi, holgura):
    """Comprueba que los botes no choquen entre sí y no sobresalgan del disco."""
    # Distancia entre centros de dos botes vecinos (cuerda del círculo de colocación)
    cuerda = 2 * r_bote * math.sin(math.radians(delta_phi) / 2)
    no_chocan = cuerda >= d_bote + holgura
    no_sobresalen = r_bote + d_bote / 2 <= r_disco
    # Radio mínimo de colocación para que no choquen, y disco mínimo resultante
    r_min = (d_bote + holgura) / (2 * math.sin(math.radians(delta_phi) / 2))
    diam_disco_min = 2 * (r_min + d_bote / 2)
    return cuerda, no_chocan, no_sobresalen, r_min, diam_disco_min


def calcular_par(m_disco, r_disco, m_bote_lleno, n_botes, r_bote, d_bote,
                 m_contrapeso, r_contrapeso, r_canicas, mu, omega_gps, t_acel,
                 factor_seguridad):
    """Par requerido en el eje del carrusel (N·m). Ver fórmulas en docs/mediciones.md."""
    mm = 1e-3  # mm → m
    R, rb, db, rc, rr = r_disco * mm, r_bote * mm, d_bote * mm, r_contrapeso * mm, r_canicas * mm

    m_total = m_disco + n_botes * m_bote_lleno + m_contrapeso

    # (1) Fricción de rodadura en las canicas: la fuerza resistente actúa a r_canicas del eje.
    par_friccion = mu * m_total * G * rr

    # (2) Inercia: disco macizo + botes (cilindros desplazados, teorema de Steiner) + contrapeso puntual.
    i_disco = 0.5 * m_disco * R ** 2
    i_botes = n_botes * m_bote_lleno * ((db / 2) ** 2 / 2 + rb ** 2)
    i_contrapeso = m_contrapeso * rc ** 2
    inercia = i_disco + i_botes + i_contrapeso

    omega = math.radians(omega_gps)     # rad/s (rampa 1° cada 15 ms ≈ 66.7 °/s)
    alfa = omega / t_acel               # rad/s² (se supone que alcanza esa velocidad en t_acel)
    par_inercia = inercia * alfa

    par_requerido = (par_friccion + par_inercia) * factor_seguridad
    return dict(m_total=m_total, par_friccion=par_friccion, inercia=inercia, alfa=alfa,
                par_inercia=par_inercia, par_requerido=par_requerido)


def main():
    p = argparse.ArgumentParser(description="Geometría del carrusel y par del servo (Fase 0).")
    p.add_argument("--ejemplo", action="store_true", help="usar valores SUPUESTOS (no medidos)")
    p.add_argument("--d-bote", type=float, help="diámetro mayor del bote [mm]")
    p.add_argument("--r-bote", type=float, help="radio de colocación: centro del disco → centro del bote [mm]")
    p.add_argument("--r-disco", type=float, help="radio del disco [mm]")
    p.add_argument("--delta-phi", type=float, default=EJEMPLO["delta_phi"], help="separación angular entre botes vecinos [°]")
    p.add_argument("--holgura", type=float, default=EJEMPLO["holgura"], help="espacio libre mínimo entre botes [mm]")
    p.add_argument("--m-disco", type=float, help="masa del disco [kg]")
    p.add_argument("--m-bote-lleno", type=float, help="masa del bote MÁS PESADO lleno [kg]")
    p.add_argument("--n-botes", type=int, default=3)
    p.add_argument("--m-contrapeso", type=float, default=0.0, help="[kg]")
    p.add_argument("--r-contrapeso", type=float, default=0.0, help="[mm]")
    p.add_argument("--r-canicas", type=float, help="radio del círculo de las canicas [mm]")
    p.add_argument("--mu", type=float, default=EJEMPLO["mu"], help="coef. de rodadura (0.05 conservador para canicas sobre MDF)")
    p.add_argument("--omega-gps", type=float, default=EJEMPLO["omega_gps"], help="velocidad del disco [°/s]")
    p.add_argument("--t-acel", type=float, default=EJEMPLO["t_acel"], help="tiempo para alcanzar esa velocidad [s]")
    p.add_argument("--factor-seguridad", type=float, default=EJEMPLO["factor_seguridad"])
    a = p.parse_args()

    v = dict(EJEMPLO) if a.ejemplo else {}
    for clave in ("d_bote", "r_bote", "r_disco", "m_disco", "m_bote_lleno", "r_canicas"):
        valor = getattr(a, clave)
        if valor is not None:
            v[clave] = valor
        elif clave not in v:
            p.error(f"falta --{clave.replace('_', '-')} (o usen --ejemplo)")
    for clave in ("delta_phi", "holgura", "n_botes", "mu", "omega_gps", "t_acel", "factor_seguridad"):
        v[clave] = getattr(a, clave)
    if not a.ejemplo:
        v["m_contrapeso"], v["r_contrapeso"] = a.m_contrapeso, a.r_contrapeso

    if a.ejemplo:
        print("*** EJEMPLO CON VALORES SUPUESTOS — NO SON MEDICIONES ***")

    print("\n--- Geometría ---")
    cuerda, no_chocan, no_sobresalen, r_min, d_min = verificar_geometria(
        v["d_bote"], v["r_bote"], v["r_disco"], v["delta_phi"], v["holgura"])
    print(f"Distancia entre centros de botes vecinos: {cuerda:.1f} mm (se necesitan ≥ {v['d_bote'] + v['holgura']:.1f})")
    print(f"¿Los botes no chocan?      {'SÍ' if no_chocan else 'NO'}")
    print(f"¿No sobresalen del disco?  {'SÍ' if no_sobresalen else 'NO'}")
    print(f"Radio de colocación mínimo: {r_min:.1f} mm → disco mínimo Ø{d_min:.0f} mm")

    print("\n--- Par del servo del carrusel ---")
    r = calcular_par(v["m_disco"], v["r_disco"], v["m_bote_lleno"], v["n_botes"], v["r_bote"],
                     v["d_bote"], v["m_contrapeso"], v["r_contrapeso"], v["r_canicas"], v["mu"],
                     v["omega_gps"], v["t_acel"], v["factor_seguridad"])
    print(f"Masa total sobre las canicas: {r['m_total']:.3f} kg")
    print(f"Par por fricción de rodadura: {r['par_friccion']:.4f} N·m")
    print(f"Momento de inercia:           {r['inercia']:.5f} kg·m²   (α = {r['alfa']:.1f} rad/s²)")
    print(f"Par por inercia:              {r['par_inercia']:.4f} N·m")
    req_kgcm = r["par_requerido"] / KGCM_A_NM
    print(f"Par requerido (×{v['factor_seguridad']} seguridad): {r['par_requerido']:.4f} N·m = {req_kgcm:.2f} kg·cm")
    print()
    for servo, par in PAR_SERVOS_KGCM.items():
        margen = par / req_kgcm if req_kgcm > 0 else float("inf")
        print(f"  {servo:16} {par:5.1f} kg·cm → margen ×{margen:.1f}  {'OK' if margen >= 1 else 'INSUFICIENTE'}")
    print("\nOjo: el par no es lo único. El SG90 tiene engranes de plástico y un eje que no debe cargar peso;")
    print("si las canicas no soportan todo el disco (base desnivelada), el eje recibe carga lateral.")


if __name__ == "__main__":
    main()
