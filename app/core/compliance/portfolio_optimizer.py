"""
Portfolio Compliance Optimizer
===============================

Coordinates portfolio optimization across multiple services.

Responsibilities:
- Collect optimization results from available services
- Combine regime-aware optimization
- Apply risk constraints
- Generate optimal portfolio weights

Author: Compliance Integration System
Date: 2026-02-03
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd

from app.core.compliance.service_registry import get_service_registry
from app.core.compliance.results import OptimizeResult

logger = logging.getLogger(__name__)


# =============================================================================
# PORTFOLIO COMPLIANCE OPTIMIZER
# =============================================================================


class PortfolioComplianceOptimizer:
    """
    Coordinates portfolio optimization from multiple services.

    This class has a Single Responsibility:
        - Aggregate portfolio optimization from multiple services
        - Provide unified optimal weights

    It delegates to:
        - Chan optimizer: Mean-variance optimization
        - Narang portfolio constructor: Risk-aware construction
        - Chan regime detector: Regime-aware adjustments
    """

    def __init__(self) -> None:
        """Initialize the portfolio optimizer with service registry."""
        self._registry = get_service_registry()
        self._cache: Dict[str, Any] = {}

    # =========================================================================
    # MAIN OPTIMIZE METHOD
    # =========================================================================

    def optimize_portfolio(
        self,
        symbols: List[str],
        returns: pd.DataFrame,
        current_prices: Dict[str, Decimal],
        price_histories: Optional[Dict[str, pd.DataFrame]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,  # Extension point for additional params
    ) -> OptimizeResult:
        """
        Perform comprehensive portfolio optimization using all available services.

        Args:
            symbols: List of symbols in portfolio
            returns: Returns DataFrame (symbols x dates)
            current_prices: Current market prices
            price_histories: Historical price data for each symbol
            constraints: Optimization constraints
            **kwargs: Additional parameters

        Returns:
            OptimizeResult with optimal weights and metrics
        """
        result = OptimizeResult(
            passed=True,
            confidence=1.0,
        )

        # Default constraints
        if constraints is None:
            constraints = {}

        # -------------------------------------------------------------------------
        # 1. Chan: Mean-Variance Optimization
        # -------------------------------------------------------------------------
        chan_success = self._optimize_chan(
            symbols=symbols,
            returns=returns,
            result=result,
        )

        # -------------------------------------------------------------------------
        # 2. Fallback to equal weights if optimization fails
        # -------------------------------------------------------------------------
        if not chan_success or not result.weights:
            self._apply_equal_weights(symbols, result)

        # -------------------------------------------------------------------------
        # 3. Regime-Aware Adjustment
        # -------------------------------------------------------------------------
        if price_histories:
            self._adjust_for_regime(
                price_histories=price_histories,
                result=result,
            )

        # -------------------------------------------------------------------------
        # 4. Apply Constraints
        # -------------------------------------------------------------------------
        self._apply_constraints(
            constraints=constraints,
            result=result,
        )

        # -------------------------------------------------------------------------
        # FINAL RESULT
        # -------------------------------------------------------------------------
        result.passed = bool(result.weights)
        result.confidence = 1.0 if result.sharpe_ratio > 0 else 0.5

        return result

    # =========================================================================
    # INDIVIDUAL OPTIMIZATION METHODS
    # =========================================================================

    def _optimize_chan(
        self,
        symbols: List[str],
        returns: pd.DataFrame,
        result: OptimizeResult,
    ) -> bool:
        """
        Optimize using Chan's mean-variance optimizer.

        Returns:
            True if optimization succeeded
        """
        portfolio_optimizer = self._registry.get_service("portfolio_optimizer")
        if portfolio_optimizer is None:
            logger.warning("Chan portfolio optimizer not available")
            return False

        try:
            optimization_result = portfolio_optimizer.optimize(returns)

            # Convert to dict
            weights_dict = {
                symbol: float(weight)
                for symbol, weight in zip(symbols, optimization_result.weights)
            }

            result.weights = weights_dict
            result.expected_return = float(optimization_result.expected_return)
            result.expected_risk = float(optimization_result.risk)
            result.sharpe_ratio = float(optimization_result.sharpe_ratio)

            return True

        except Exception as e:
            logger.warning("Chan portfolio optimization error:", error=e)
            return False

    def _apply_equal_weights(
        self,
        symbols: List[str],
        result: OptimizeResult,
    ) -> None:
        """Apply equal weights as fallback."""
        equal_weight = 1.0 / len(symbols)
        result.weights = {symbol: equal_weight for symbol in symbols}
        result.expected_return = 0.0
        result.expected_risk = 0.0
        result.sharpe_ratio = 0.0
        result.reasons.append("Equal weights applied (optimization unavailable)")

    def _adjust_for_regime(
        self,
        price_histories: Dict[str, pd.DataFrame],
        result: OptimizeResult,
    ) -> None:
        """Adjust portfolio based on market regime."""
        if not price_histories:
            return

        regime_detector = self._registry.get_service("regime_detector")
        if regime_detector is None:
            return

        try:
            # Get regime from first available history
            sample_history = next(iter(price_histories.values()))
            regime_result = regime_detector.detect_regimes(sample_history)

            if regime_result and len(regime_result) > 0:
                current_regime = regime_result[-1]
                result.regime = current_regime
                result.regime_adjusted = True

                # Adjust weights based on regime
                if current_regime == "BEAR":
                    # Reduce exposure in bear market
                    adjustment_factor = 0.8
                    result.weights = {
                        k: v * adjustment_factor for k, v in result.weights.items()
                    }
                    result.reasons.append("Weights reduced for bear regime")

                elif current_regime == "BULL":
                    # Increase exposure in bull market
                    adjustment_factor = 1.1
                    result.weights = {
                        k: v * adjustment_factor for k, v in result.weights.items()
                    }
                    result.reasons.append("Weights increased for bull regime")

        except Exception as e:
            logger.warning("Regime adjustment error:", error=e)

    def _apply_constraints(
        self,
        constraints: Dict[str, Any],
        result: OptimizeResult,
    ) -> None:
        """Apply optimization constraints."""
        if not constraints:
            return

        # Max weight constraint
        max_weight = constraints.get("max_weight")
        if max_weight:
            result.weights = self._cap_weights(result.weights, max_weight)

        # Min weight constraint
        min_weight = constraints.get("min_weight")
        if min_weight:
            result.weights = self._floor_weights(result.weights, min_weight)

        # Re-normalize weights
        total_weight = sum(result.weights.values())
        if total_weight > 0:
            result.weights = {
                k: v / total_weight for k, v in result.weights.items()
            }

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def _cap_weights(
        self,
        weights: Dict[str, float],
        max_weight: float,
    ) -> Dict[str, float]:
        """Cap weights at maximum value."""
        capped = {}
        for symbol, weight in weights.items():
            capped[symbol] = min(weight, max_weight)
        return capped

    def _floor_weights(
        self,
        weights: Dict[str, float],
        min_weight: float,
    ) -> Dict[str, float]:
        """Floor weights at minimum value."""
        floored = {}
        for symbol, weight in weights.items():
            floored[symbol] = max(weight, min_weight)
        return floored

    def get_available_optimizers(self) -> List[str]:
        """Get list of available optimization methods."""
        optimizers = []

        if self._registry.is_available("portfolio_optimizer"):
            optimizers.append("chan_mean_variance")

        if self._registry.is_available("portfolio_constructor"):
            optimizers.append("narang_risk_parity")

        return optimizers

    def calculate_portfolio_metrics(
        self,
        weights: Dict[str, float],
        returns: pd.DataFrame,
    ) -> Dict[str, float]:
        """
        Calculate portfolio metrics given weights and returns.

        Args:
            weights: Dictionary of symbol -> weight
            returns: Returns DataFrame

        Returns:
            Dict with expected_return, risk, sharpe_ratio
        """
        try:
            # Calculate portfolio returns
            weight_series = pd.Series(weights)
            portfolio_returns = returns.dot(weight_series)

            expected_return = portfolio_returns.mean() * 252  # Annualized
            risk = portfolio_returns.std() * (252**0.5)  # Annualized
            sharpe_ratio = expected_return / risk if risk > 0 else 0

            return {
                "expected_return": float(expected_return),
                "risk": float(risk),
                "sharpe_ratio": float(sharpe_ratio),
            }

        except Exception as e:
            logger.warning("Portfolio metrics calculation error:", error=e)
            return {
                "expected_return": 0.0,
                "risk": 0.0,
                "sharpe_ratio": 0.0,
            }
