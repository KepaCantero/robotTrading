"""
Capital Phase Configuration (R25, R26, R27)

This module defines the capital phases and their associated risk parameters.
Risk levels increase as capital grows through the phases.

Rules:
- R25: Survival (EUR1k-EUR10k) -> 1% max risk, NO leverage
- R26: Growth (EUR10k-EUR50k) -> 2% max risk, NO leverage
- R27: Optimization (EUR50k+) -> 3% max risk, leverage allowed
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

logger = logging.getLogger(__name__)


class CapitalPhase(Enum):
    """Fases de capital basado en reglas de trading realistas."""

    SURVIVAL = "survival"  # EUR1k - EUR10k: Muy conservador
    GROWTH = "growth"  # EUR10k - EUR50k: Moderado
    OPTIMIZATION = "optimization"  # EUR50k+: Mas agresivo


@dataclass(frozen=True)
class PhaseRiskParameters:
    """
    Parametros de riesgo por fase de capital.

    R25: Survival phase - Max 1% risk per trade, no leverage
    R26: Growth phase - Max 2% risk per trade, no leverage
    R27: Optimization phase - Max 3% risk per trade, leverage allowed
    """

    max_risk_per_trade_pct: Decimal  # Maximo riesgo por trade
    max_portfolio_risk_pct: Decimal  # Maximo riesgo total del portfolio
    max_positions: int  # Maximo de posiciones simultaneas
    max_correlation: Decimal  # Maxima correlacion permitida entre posiciones
    position_sizing_method: str  # Metodo de calculo de tamano
    leverage_allowed: bool  # Si se permite apalancamiento


# Configuracion por fase (R25, R26, R27)
# These parameters are based on realistic retail trading rules
PHASE_CONFIGS: dict[CapitalPhase, PhaseRiskParameters] = {
    # R25: Survival phase (EUR1k-EUR10k) - Very conservative
    CapitalPhase.SURVIVAL: PhaseRiskParameters(
        max_risk_per_trade_pct=Decimal("0.01"),  # 1% - Very conservative
        max_portfolio_risk_pct=Decimal("0.05"),  # 5% total
        max_positions=3,
        max_correlation=Decimal("0.5"),
        position_sizing_method="kelly_half",  # Kelly/2 very conservative
        leverage_allowed=False,  # NO leverage
    ),
    # R26: Growth phase (EUR10k-EUR50k) - Moderate
    CapitalPhase.GROWTH: PhaseRiskParameters(
        max_risk_per_trade_pct=Decimal("0.02"),  # 2% - Moderate
        max_portfolio_risk_pct=Decimal("0.10"),  # 10% total
        max_positions=5,
        max_correlation=Decimal("0.7"),
        position_sizing_method="kelly",  # Full Kelly
        leverage_allowed=False,  # NO leverage
    ),
    # R27: Optimization phase (EUR50k+) - More aggressive
    CapitalPhase.OPTIMIZATION: PhaseRiskParameters(
        max_risk_per_trade_pct=Decimal("0.03"),  # 3% - More aggressive
        max_portfolio_risk_pct=Decimal("0.15"),  # 15% total
        max_positions=8,
        max_correlation=Decimal("0.8"),
        position_sizing_method="kelly_optimized",  # Optimized Kelly
        leverage_allowed=True,  # Leverage allowed
    ),
}


# Umbrales de capital por fase
# R25: Survival: EUR1k - EUR10k
# R26: Growth: EUR10k - EUR50k
# R27: Optimization: EUR50k+
PHASE_THRESHOLDS: dict[CapitalPhase, tuple[Decimal, Decimal]] = {
    CapitalPhase.SURVIVAL: (Decimal("1000"), Decimal("10000")),  # EUR1k-EUR10k
    CapitalPhase.GROWTH: (Decimal("10000"), Decimal("50000")),  # EUR10k-EUR50k
    CapitalPhase.OPTIMIZATION: (Decimal("50000"), Decimal("999999999")),  # EUR50k+
}


# Log module initialization
logger.info(
    "Capital phase configuration loaded",
    extra={
        "component": "phase_config",
        "operation": "module_init",
        "phases_defined": [phase.value for phase in CapitalPhase],
        "rules_implemented": ["R25", "R26", "R27"],
    },
)

logger.debug(
    "Phase configurations details",
    extra={
        "component": "phase_config",
        "operation": "log_configs",
        "survival_max_risk": str(PHASE_CONFIGS[CapitalPhase.SURVIVAL].max_risk_per_trade_pct),
        "growth_max_risk": str(PHASE_CONFIGS[CapitalPhase.GROWTH].max_risk_per_trade_pct),
        "optimization_max_risk": str(
            PHASE_CONFIGS[CapitalPhase.OPTIMIZATION].max_risk_per_trade_pct
        ),
    },
)
