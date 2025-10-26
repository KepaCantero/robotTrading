"""
Position Sizing Engine - TASK-15: Refactorización de Servicios

Este módulo implementa el motor de cálculo de tamaño de posición, separando
la lógica de sizing de la gestión de portafolio y ejecución de señales.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from app.core.centralized_config import get_config
from app.models.portfolio import Portfolio, Position
from app.models.signal import Signal

logger = logging.getLogger(__name__)


class PositionSizingEngine:
    """
    Motor de cálculo de tamaño de posición.

    Responsabilidades:
    - Calcular tamaño óptimo de posición
    - Aplicar límites de riesgo
    - Considerar volatilidad del activo
    - Gestionar diversificación
    """

    def __init__(self):
        """Inicializar motor de sizing."""
        self.config = get_config().trading

        # Límites de posición
        self.max_position_size = self.config.max_position_size
        self.min_position_size = self.config.min_position_size
        self.max_total_exposure = self.config.max_total_exposure
        self.max_sector_exposure = self.config.max_sector_exposure

        # Métricas de rendimiento
        self.sizing_calculations = 0
        self.position_size_adjustments = 0

    def calculate_position_size(
        self,
        signal: Signal,
        portfolio: Portfolio,
        available_capital: Decimal,
        metadata: Dict[str, Any],
    ) -> Tuple[Decimal, Dict[str, Any]]:
        """
        Calcular tamaño óptimo de posición.

        Args:
            signal: Señal de trading
            portfolio: Portafolio actual
            available_capital: Capital disponible
            metadata: Metadatos adicionales

        Returns:
            Tupla con (tamaño_posición, detalles_cálculo)
        """
        self.sizing_calculations += 1

        # Obtener información del activo
        asset_info = self._get_asset_info(signal.symbol, metadata)

        # Calcular tamaño base usando Kelly Criterion simplificado
        base_size = self._calculate_base_position_size(
            signal, asset_info, available_capital
        )

        # Aplicar límites de riesgo
        risk_adjusted_size = self._apply_risk_limits(
            base_size, signal, portfolio, available_capital
        )

        # Aplicar límites de diversificación
        diversified_size = self._apply_diversification_limits(
            risk_adjusted_size, signal, portfolio, available_capital
        )

        # Aplicar límites de volatilidad
        final_size = self._apply_volatility_limits(
            diversified_size, signal, asset_info, available_capital
        )

        # Detalles del cálculo
        calculation_details = {
            "symbol": signal.symbol,
            "signal_type": signal.signal_type,
            "base_size": base_size,
            "risk_adjusted_size": risk_adjusted_size,
            "diversified_size": diversified_size,
            "final_size": final_size,
            "available_capital": available_capital,
            "asset_info": asset_info,
            "calculation_time": datetime.utcnow(),
            "adjustments_applied": self.position_size_adjustments,
        }

        logger.debug(f"Position sizing for {signal.symbol}: {calculation_details}")
        return final_size, calculation_details

    def _get_asset_info(self, symbol: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Obtener información del activo."""
        return {
            "symbol": symbol,
            "volatility": metadata.get("volatility", 0.2),
            "sector": metadata.get("sector", "unknown"),
            "market_cap": metadata.get("market_cap", 1000000000),
            "liquidity_score": metadata.get("liquidity_score", 50.0),
            "correlation": metadata.get("correlation", 0.0),
        }

    def _calculate_base_position_size(
        self, signal: Signal, asset_info: Dict[str, Any], available_capital: Decimal
    ) -> Decimal:
        """Calcular tamaño base de posición usando Kelly Criterion simplificado."""
        # Parámetros del Kelly Criterion
        win_probability = Decimal("0.6")  # Probabilidad de ganancia estimada
        avg_win = Decimal("0.15")  # Ganancia promedio (15%)
        avg_loss = Decimal("0.05")  # Pérdida promedio (5%)

        # Kelly Criterion: f = (bp - q) / b
        # donde b = odds, p = win probability, q = loss probability
        b = avg_win / avg_loss  # odds ratio
        p = win_probability
        q = Decimal("1") - p

        kelly_fraction = (b * p - q) / b

        # Aplicar factor de seguridad (usar solo 25% del Kelly)
        safe_kelly = kelly_fraction * Decimal("0.25")

        # Calcular tamaño en términos de capital
        base_size = available_capital * safe_kelly

        # Ajustar por volatilidad del activo
        volatility = asset_info["volatility"]
        volatility_adjustment = Decimal("1.0") / (
            Decimal(str(volatility)) + Decimal("0.1")
        )
        base_size = base_size * volatility_adjustment

        return max(base_size, Decimal("0"))

    def _apply_risk_limits(
        self,
        base_size: Decimal,
        signal: Signal,
        portfolio: Portfolio,
        available_capital: Decimal,
    ) -> Decimal:
        """Aplicar límites de riesgo."""
        # Límite máximo por posición
        max_position_value = available_capital * Decimal(str(self.max_position_size))
        risk_limited_size = min(base_size, max_position_value)

        # Límite mínimo por posición
        min_position_value = available_capital * Decimal(str(self.min_position_size))
        risk_limited_size = max(risk_limited_size, min_position_value)

        if risk_limited_size != base_size:
            self.position_size_adjustments += 1
            logger.debug(f"Applied risk limits: {base_size} -> {risk_limited_size}")

        return risk_limited_size

    def _apply_diversification_limits(
        self,
        risk_limited_size: Decimal,
        signal: Signal,
        portfolio: Portfolio,
        available_capital: Decimal,
    ) -> Decimal:
        """Aplicar límites de diversificación."""
        # Calcular exposición actual por sector
        current_sector_exposure = self._calculate_sector_exposure(
            signal.symbol, portfolio
        )

        # Límite de exposición por sector
        max_sector_value = available_capital * Decimal(str(self.max_sector_exposure))
        remaining_sector_capacity = max_sector_value - current_sector_exposure

        # Ajustar tamaño si excede límite de sector
        diversified_size = min(risk_limited_size, remaining_sector_capacity)

        # Calcular exposición total actual
        current_total_exposure = self._calculate_total_exposure(portfolio)

        # Límite de exposición total
        max_total_value = available_capital * Decimal(str(self.max_total_exposure))
        remaining_total_capacity = max_total_value - current_total_exposure

        # Ajustar tamaño si excede límite total
        diversified_size = min(diversified_size, remaining_total_capacity)

        if diversified_size != risk_limited_size:
            self.position_size_adjustments += 1
            logger.debug(
                f"Applied diversification limits: {risk_limited_size} -> {diversified_size}"
            )

        return max(diversified_size, Decimal("0"))

    def _apply_volatility_limits(
        self,
        diversified_size: Decimal,
        signal: Signal,
        asset_info: Dict[str, Any],
        available_capital: Decimal,
    ) -> Decimal:
        """Aplicar límites basados en volatilidad."""
        volatility = asset_info["volatility"]

        # Reducir tamaño para activos muy volátiles
        if volatility > 0.5:  # Más del 50% de volatilidad
            volatility_adjustment = Decimal("0.5")
        elif volatility > 0.3:  # Más del 30% de volatilidad
            volatility_adjustment = Decimal("0.75")
        else:
            volatility_adjustment = Decimal("1.0")

        volatility_adjusted_size = diversified_size * volatility_adjustment

        if volatility_adjusted_size != diversified_size:
            self.position_size_adjustments += 1
            logger.debug(
                f"Applied volatility limits: {diversified_size} -> {volatility_adjusted_size}"
            )

        return volatility_adjusted_size

    def _calculate_sector_exposure(self, symbol: str, portfolio: Portfolio) -> Decimal:
        """Calcular exposición actual por sector."""
        # Implementación simplificada - en producción vendría de metadata
        sector_exposure = Decimal("0")

        for position in portfolio.positions:
            # Asumir que todas las posiciones están en el mismo sector por
            # simplicidad
            if position.symbol != symbol:
                sector_exposure += position.market_value

        return sector_exposure

    def _calculate_total_exposure(self, portfolio: Portfolio) -> Decimal:
        """Calcular exposición total del portafolio."""
        total_exposure = Decimal("0")

        for position in portfolio.positions:
            total_exposure += position.market_value

        return total_exposure

    def get_sizing_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de sizing."""
        return {
            "sizing_calculations": self.sizing_calculations,
            "position_size_adjustments": self.position_size_adjustments,
            "max_position_size": self.max_position_size,
            "min_position_size": self.min_position_size,
            "max_total_exposure": self.max_total_exposure,
            "max_sector_exposure": self.max_sector_exposure,
        }

    def update_limits(
        self,
        max_position_size: Optional[float] = None,
        min_position_size: Optional[float] = None,
        max_total_exposure: Optional[float] = None,
        max_sector_exposure: Optional[float] = None,
    ) -> None:
        """Actualizar límites de sizing."""
        if max_position_size is not None:
            self.max_position_size = max_position_size
            logger.info(f"Updated max_position_size to {max_position_size}")

        if min_position_size is not None:
            self.min_position_size = min_position_size
            logger.info(f"Updated min_position_size to {min_position_size}")

        if max_total_exposure is not None:
            self.max_total_exposure = max_total_exposure
            logger.info(f"Updated max_total_exposure to {max_total_exposure}")

        if max_sector_exposure is not None:
            self.max_sector_exposure = max_sector_exposure
            logger.info(f"Updated max_sector_exposure to {max_sector_exposure}")

    def reset_statistics(self) -> None:
        """Resetear estadísticas de sizing."""
        self.sizing_calculations = 0
        self.position_size_adjustments = 0
        logger.info("Reset position sizing statistics")
