"""Cartera pasiva de PESOS FIJOS equity/bono — el reparto que se BUSCA.

El owner (31-10) rechazó los pesos fijos a mano y pidió que el motor
``busque el mejor peso para mi edad``: esta estrategia expone UN grado
de libertad honesto (``equity_weight``) que el optimizador in-backtest
barre en cada run. El default y el techo de la búsqueda vienen del
perfil de riesgo del run (BAJO 0.60 / MEDIO 0.75 / ALTO 0.90, los
mismos equity_max_pct del robo-advisor) — la edad entra por ahí.

Solo aplica a un universo DOS FONDOS con una pata identificada como
bono (tabla abajo); cualquier otro universo degenera honestamente en
static_ew (equal weight) en vez de inventar clasificaciones.

Los pesos se derivan PEREZOSAMENTE de ``self.equity_weight`` en cada
uso: el orquestador aplica los overrides con ``setattr`` DESPUÉS de
``__init__`` — una tabla congelada en el constructor hacía invisible
cualquier peso del optimizador (todos los trials corrían el default
mientras el gemelo leía el override: 12,8 pp de gap fabricado, 31-10).
"""

from __future__ import annotations

import math
from typing import Any

from app.domain.strategies.static_ew import StaticEqualWeightStrategy

#: pata "bono" del universo dos-fondos. Fuente: ASSET_CLASS del
#: portfolio-management (BND/BIV/SCHZ/VBT/IBTS/IBGS.AS/AGGH.AS) — todo lo
#: demás cuenta como equity (fail-safe: el cap de equity binda).
BOND_ETFS: frozenset[str] = frozenset({"BND", "BIV", "SCHZ", "VBT", "IBTS", "IBGS.AS", "AGGH.AS"})

#: default del grado de libertad cuando ni el perfil ni lo adoptado lo
#: traen (MEDIO — el dueño tiene 45 y riesgo MEDIO; el optimizador barre
#: alrededor en el mismo run)
DEFAULT_EQUITY_WEIGHT = 0.75


class StaticWeightedStrategy(StaticEqualWeightStrategy):
    """Pasiva dos-fondos: ``equity_weight`` al fondo equity, el resto al bono."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.equity_weight = min(
            max(float(config.get("equity_weight", DEFAULT_EQUITY_WEIGHT)), 0.05), 0.95
        )

    def _split(self) -> dict[str, float] | None:
        """Pesos por símbolo derivados del equity_weight VIGENTE; None si el
        universo no es un par equity+bono clasificable → equal weight."""
        equity = [s for s in self.universe if s not in BOND_ETFS]
        bonds = [s for s in self.universe if s in BOND_ETFS]
        if len(equity) == 1 and len(bonds) == 1:
            ew = min(max(self.equity_weight, 0.05), 0.95)
            return {equity[0]: ew, bonds[0]: 1.0 - ew}
        return None

    @property
    def suggested_max_position_size(self) -> float:
        """El techo del validador debe cubrir la manga MÁS grande."""
        weights = self._split()
        if weights is None:
            return super().suggested_max_position_size
        heaviest = max(weights.values()) * self.target_exposure
        return math.ceil(min(0.95, heaviest) * 100) / 100

    def get_required_parameters(self) -> list[str]:
        return ["rebalance_days", "equity_weight"]

    def _position_weight(self, symbol: str) -> float:
        # peso declarado por manga (× exposure); sin clasificación → 1/N
        weights = self._split()
        if weights is not None and symbol in weights:
            return round(min(0.95, weights[symbol] * self.target_exposure), 4)
        return super()._position_weight(symbol)
