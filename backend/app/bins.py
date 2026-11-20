"""
bins.py — Botes y nivel de llenado ESTIMADO por conteo de piezas (especificación §13).

Fase 3 (actual): cuenta piezas, vacía botes y calcula el nivel y el estado.
Fase 7 (pendiente): `tiene_espacio()` empezará a bloquear el bote al 100 % y el orquestador usará
el estado BOTE_LLENO. El punto de integración ya existe para no reestructurar después.
"""

from __future__ import annotations

from typing import Any

from .db import BaseDatos, ahora

BLOQUEO_ACTIVO = False  # Fase 7: True para bloquear botes llenos


class GestorBotes:
    def __init__(self, db: BaseDatos, umbral_aviso: float) -> None:
        self.db = db
        self.umbral_aviso = umbral_aviso

    @staticmethod
    def bote_para_categoria(categoria_id: int) -> int:
        """Cada categoría tiene su bote con el mismo id (0 verde, 1 azul, 2 gris)."""
        return categoria_id

    def _fila(self, bote_id: int) -> dict[str, Any]:
        fila = self.db.uno("SELECT * FROM botes WHERE id = ?", (bote_id,))
        if fila is None:
            raise KeyError(f"No existe el bote {bote_id}")
        return fila

    def a_dict(self, fila: dict[str, Any]) -> dict[str, Any]:
        """Objeto `Bote` del contrato (§2.2)."""
        capacidad = max(int(fila["capacidad_piezas"]), 1)
        nivel = fila["piezas_actuales"] / capacidad
        if nivel >= 1.0:
            estado = "lleno"
        elif nivel >= fila["umbral_aviso"]:
            estado = "casi_lleno"
        else:
            estado = "normal"
        return {
            "id": fila["id"], "nombre": fila["nombre"], "color": fila["color"],
            "categoria_id": fila["categoria_id"], "capacidad_piezas": fila["capacidad_piezas"],
            "capacidad_calibrada": bool(fila["capacidad_calibrada"]),
            "piezas_actuales": fila["piezas_actuales"], "no_confirmadas": fila["no_confirmadas"],
            "nivel": round(nivel, 3), "estado": estado, "bloqueado": bool(fila["bloqueado"]),
            "umbral_aviso": fila["umbral_aviso"], "ultimo_vaciado": fila["ultimo_vaciado"],
            "estimado": True,
        }

    def bote(self, bote_id: int) -> dict[str, Any]:
        return self.a_dict(self._fila(bote_id))

    def todos(self) -> list[dict[str, Any]]:
        return [self.a_dict(f) for f in self.db.consultar("SELECT * FROM botes ORDER BY id")]

    def tiene_espacio(self, bote_id: int) -> bool:
        """VERIFICAR_BOTE. En la Fase 3 siempre hay espacio; en la Fase 7 se bloquea al 100 %."""
        if not BLOQUEO_ACTIVO:
            return True
        return self.bote(bote_id)["estado"] != "lleno"

    def sumar_pieza(self, bote_id: int, confirmado: bool) -> dict[str, Any]:
        """ACTUALIZAR_NIVEL. Sin sensor de caída, cada DROP_OK suma una pieza (confirmado siempre es True)."""
        self.db.ejecutar(
            "UPDATE botes SET piezas_actuales = piezas_actuales + 1, "
            "no_confirmadas = no_confirmadas + ? WHERE id = ?",
            (0 if confirmado else 1, bote_id),
        )
        return self.bote(bote_id)

    def vaciar(self, bote_id: int, origen: str) -> dict[str, Any]:
        fila = self._fila(bote_id)
        momento = ahora()
        self.db.ejecutar(
            "INSERT INTO vaciados(bote_id, fecha_hora, piezas_al_vaciar, origen) VALUES (?, ?, ?, ?)",
            (bote_id, momento, fila["piezas_actuales"], origen),
        )
        self.db.ejecutar(
            "UPDATE botes SET piezas_actuales = 0, no_confirmadas = 0, bloqueado = 0, ultimo_vaciado = ? "
            "WHERE id = ?",
            (momento, bote_id),
        )
        return self.bote(bote_id)

    def ajustar(self, bote_id: int, capacidad_piezas: int | None = None,
                umbral_aviso: float | None = None) -> dict[str, Any]:
        self._fila(bote_id)
        if capacidad_piezas is not None:
            if capacidad_piezas <= 0:
                raise ValueError("capacidad_piezas debe ser mayor que 0")
            self.db.ejecutar("UPDATE botes SET capacidad_piezas = ?, capacidad_calibrada = 1 WHERE id = ?",
                             (capacidad_piezas, bote_id))
        if umbral_aviso is not None:
            if not 0 < umbral_aviso <= 1:
                raise ValueError("umbral_aviso debe estar entre 0 y 1")
            self.db.ejecutar("UPDATE botes SET umbral_aviso = ? WHERE id = ?", (umbral_aviso, bote_id))
        return self.bote(bote_id)

    def vaciados(self, limite: int = 50) -> list[dict[str, Any]]:
        return self.db.consultar("SELECT * FROM vaciados ORDER BY id DESC LIMIT ?", (limite,))

    def desviados_por_categoria(self) -> dict[str, int]:
        """Residuos depositados en cada bote (desviados de la basura mezclada)."""
        filas = self.db.consultar(
            "SELECT bote_id, COUNT(*) AS n FROM clasificaciones "
            "WHERE estado = 'registrado' AND bote_id IS NOT NULL GROUP BY bote_id"
        )
        conteo = {"0": 0, "1": 0, "2": 0}
        for f in filas:
            conteo[str(f["bote_id"])] = f["n"]
        return conteo
