"""
Multi-Asset Allocation Strategies.

This module provides various allocation strategies for distributing capital
across different asset classes in a multi-asset portfolio.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from .asset_class import AssetClass, AssetClassType
from .models import AllocationStrategy, RiskTolerance

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    """Market regime for tactical allocation."""

    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"
    RECOVERY = "recovery"


@dataclass
class StrategicAllocationParams:
    """
    Parameters for strategic asset allocation.

    Attributes:
        risk_tolerance: Investor risk tolerance
        time_horizon: Investment time horizon in years
        income_need: Annual income need as percentage of portfolio
        liquidity_need: Liquidity need (0-1)
        inflation_protection: Need for inflation protection (0-1)
        target_return: Target annual return
        max_volatility: Maximum acceptable volatility
    """

    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE
    time_horizon: int = 10  # years
    income_need: Decimal = Decimal("0.04")  # 4% annual withdrawal
    liquidity_need: Decimal = Decimal("0.10")  # 10% liquid assets
    inflation_protection: Decimal = Decimal("0.50")  # 50% inflation protected
    target_return: Optional[Decimal] = None
    max_volatility: Optional[Decimal] = None


@dataclass
class TacticalAllocationParams:
    """
    Parameters for tactical asset allocation.

    Attributes:
        strategic_weights: Strategic base weights
        market_conditions: Current market conditions by asset class
        signals: Trading signals for each asset class
        max_tilt: Maximum tilt from strategic weight
        lookback_period: Lookback period for signal calculation
        momentum_threshold: Minimum momentum signal to act
        valuation_threshold: Valuation signal threshold
    """

    strategic_weights: Dict[str, Decimal]
    market_conditions: Dict[str, MarketRegime]
    signals: Dict[str, float]
    max_tilt: Decimal = Decimal("0.20")  # 20% max tilt
    lookback_period: int = 252  # 1 year of daily data
    momentum_threshold: float = 0.02  # 2% momentum threshold
    valuation_threshold: float = 0.1  # 10% valuation threshold


@dataclass
class RiskParityAllocationParams:
    """
    Parameters for risk parity allocation.

    Attributes:
        asset_class_returns: Historical returns for each asset class
        risk_free_rate: Risk-free rate
        target_volatility: Target portfolio volatility
        min_weight: Minimum weight for any asset class
        max_weight: Maximum weight for any asset class
        risk_measure: Risk measure ('volatility', 'var', 'cvar')
    """

    asset_class_returns: pd.DataFrame
    risk_free_rate: float = 0.02
    target_volatility: Optional[float] = None
    min_weight: float = 0.0
    max_weight: float = 1.0
    risk_measure: str = "volatility"


@dataclass
class AllocationResult:
    """
    Result of allocation calculation.

    Attributes:
        weights: Calculated weights for each asset class
        expected_return: Portfolio expected return
        expected_volatility: Portfolio expected volatility
        sharpe_ratio: Expected Sharpe ratio
        risk_contributions: Risk contribution by asset class
        method: Allocation method used
        metadata: Additional metadata
    """

    weights: Dict[str, Decimal]
    expected_return: Decimal
    expected_volatility: Decimal
    sharpe_ratio: Optional[Decimal]
    risk_contributions: Optional[Dict[str, Decimal]]
    method: AllocationStrategy
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiAssetAllocator:
    """
    Allocate capital across asset classes.

    This class provides multiple allocation strategies:
    1. Strategic allocation - Long-term target weights based on investor profile
    2. Tactical allocation - Short-term tilts based on market conditions
    3. Risk parity - Equal risk contribution across asset classes
    4. Momentum - Overweight performing asset classes
    5. Equal weight - Simple equal allocation across classes

    Example:
        >>> allocator = MultiAssetAllocator(asset_classes)
        >>>
        >>> # Strategic allocation
        >>> params = StrategicAllocationParams(
        ...     risk_tolerance=RiskTolerance.MODERATE,
        ...     time_horizon=10
        ... )
        >>> result = allocator.strategic_allocation(params)
        >>>
        >>> # Tactical tilt
        >>> tactical_params = TacticalAllocationParams(...)
        >>> result = allocator.tactical_allocation(tactical_params)
    """

    def __init__(self, asset_classes: Dict[str, AssetClass]):
        """
        Initialize allocator.

        Args:
            asset_classes: Dictionary of asset class name to AssetClass
        """
        self.asset_classes = asset_classes

    def strategic_allocation(self, params: StrategicAllocationParams) -> AllocationResult:
        """
        Calculate strategic asset allocation.

        Strategic allocation is based on long-term investor characteristics:
        - Risk tolerance (conservative, moderate, aggressive)
        - Time horizon
        - Income needs
        - Liquidity needs
        - Inflation protection

        Rules of thumb:
        - Aggressive: 80%+ equities, 10-20% alternatives
        - Moderate: 60% equities, 30% bonds, 10% alternatives
        - Conservative: 40% equities, 50% bonds, 10% cash

        Args:
            params: Strategic allocation parameters

        Returns:
            AllocationResult with strategic weights
        """
        # Get weights based on risk tolerance
        base_weights = self._get_base_strategic_weights(params.risk_tolerance)

        # Adjust for time horizon (longer horizon = more equities)
        adjusted_weights = self._adjust_for_time_horizon(base_weights, params.time_horizon)

        # Adjust for income need (more bonds for income)
        adjusted_weights = self._adjust_for_income_need(adjusted_weights, params.income_need)

        # Ensure liquidity need is met
        adjusted_weights = self._adjust_for_liquidity(adjusted_weights, params.liquidity_need)

        # Normalize to sum to 1
        total = sum(adjusted_weights.values())
        if total > 0:
            weights = {k: v / total for k, v in adjusted_weights.items()}
        else:
            weights = adjusted_weights

        # Apply asset class constraints
        weights = self._apply_asset_class_constraints(weights)

        # Calculate portfolio metrics
        metrics = self._calculate_portfolio_metrics(weights)

        return AllocationResult(
            weights=weights,
            expected_return=metrics["expected_return"],
            expected_volatility=metrics["expected_volatility"],
            sharpe_ratio=metrics.get("sharpe_ratio"),
            risk_contributions=None,  # Not calculated for strategic
            method=AllocationStrategy.STRATEGIC,
            metadata={
                "risk_tolerance": params.risk_tolerance,
                "time_horizon": params.time_horizon,
                "base_weights": base_weights,
            },
        )

    def tactical_allocation(self, params: TacticalAllocationParams) -> AllocationResult:
        """
        Apply tactical tilts to strategic allocation.

        Tactical allocation makes short-term adjustments to strategic weights
        based on market conditions and signals:

        Signals by asset class:
        - Equities: momentum, valuation metrics (P/E, P/B), earnings trends
        - Bonds: yield curve, credit spreads, inflation expectations
        - Crypto: BTC dominance, DeFi TVL, network activity
        - Forex: carry trade returns, momentum, purchasing power parity
        - Commodities: momentum, inventory levels, demand indicators

        Max tilt: ±max_tilt from strategic weight

        Args:
            params: Tactical allocation parameters

        Returns:
            AllocationResult with tactically adjusted weights
        """
        weights = params.strategic_weights.copy()
        tilts: Dict[str, Decimal] = {}

        # Calculate tilts based on signals
        for asset_class, signal in params.signals.items():
            if asset_class not in self.asset_classes:
                continue

            # Convert signal to tilt
            # Positive signal = overweight, negative = underweight
            tilt = self._calculate_tilt_from_signal(
                asset_class=asset_class,
                signal=signal,
                max_tilt=params.max_tilt,
                market_regime=params.market_conditions.get(asset_class, MarketRegime.NEUTRAL),
            )
            tilts[asset_class] = tilt

        # Apply tilts
        for asset_class, tilt in tilts.items():
            if asset_class in weights:
                weights[asset_class] += tilt

        # Normalize to maintain sum = 1
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        # Apply constraints
        weights = self._apply_asset_class_constraints(weights)

        # Calculate metrics
        metrics = self._calculate_portfolio_metrics(weights)

        return AllocationResult(
            weights=weights,
            expected_return=metrics["expected_return"],
            expected_volatility=metrics["expected_volatility"],
            sharpe_ratio=metrics.get("sharpe_ratio"),
            risk_contributions=None,
            method=AllocationStrategy.TACTICAL,
            metadata={
                "strategic_weights": params.strategic_weights,
                "tilts": tilts,
                "signals": params.signals,
            },
        )

    def risk_parity_allocation(self, params: RiskParityAllocationParams) -> AllocationResult:
        """
        Calculate risk parity allocation across asset classes.

        Risk parity allocates so that each asset class contributes equal risk
        to the portfolio. For a simple implementation using volatility:

        w_i ∝ 1/σ_i

        For more sophisticated versions, we use the risk budgeting equation:
        w_i * (Σw)_i = w_j * (Σw)_j  for all i, j

        This requires solving a system of equations iteratively.

        Args:
            params: Risk parity parameters

        Returns:
            AllocationResult with risk parity weights
        """
        # Calculate volatilities from returns
        volatilities = {}
        for asset_class in params.asset_class_returns.columns:
            returns = params.asset_class_returns[asset_class].dropna()
            if len(returns) > 0:
                vol = returns.std() * np.sqrt(252)  # Annualized
                volatilities[asset_class] = Decimal(str(vol))

        # Simple inverse volatility weighting
        # w_i = 1/σ_i / Σ(1/σ_j)
        inv_vols = {}
        for asset_class, vol in volatilities.items():
            if vol > 0:
                inv_vols[asset_class] = Decimal("1") / vol
            else:
                inv_vols[asset_class] = Decimal("0")

        # Normalize
        total_inv_vol = sum(inv_vols.values())
        if total_inv_vol > 0:
            weights = {k: v / total_inv_vol for k, v in inv_vols.items()}
        else:
            # Fallback to equal weight
            n = len(self.asset_classes)
            weights = {k: Decimal("1") / Decimal(str(n)) for k in self.asset_classes}

        # Apply constraints
        weights = self._apply_asset_class_constraints(weights)
        weights = self._apply_weight_bounds(
            weights,
            min_weight=Decimal(str(params.min_weight)),
            max_weight=Decimal(str(params.max_weight)),
        )

        # Recalculate risk contributions
        risk_contribs = self._calculate_risk_contributions(weights, params.asset_class_returns)

        # Calculate metrics
        metrics = self._calculate_portfolio_metrics(weights, params.asset_class_returns)

        return AllocationResult(
            weights=weights,
            expected_return=metrics["expected_return"],
            expected_volatility=metrics["expected_volatility"],
            sharpe_ratio=metrics.get("sharpe_ratio"),
            risk_contributions=risk_contribs,
            method=AllocationStrategy.RISK_PARITY,
            metadata={
                "volatilities": {k: float(v) for k, v in volatilities.items()},
                "risk_measure": params.risk_measure,
            },
        )

    def momentum_allocation(
        self,
        lookback_returns: pd.DataFrame,
        lookback_period: int = 126,  # 6 months
        top_n: Optional[int] = None,
    ) -> AllocationResult:
        """
        Allocate based on momentum.

        Overweight asset classes with positive recent momentum,
        underweight or exclude those with negative momentum.

        Args:
            lookback_returns: Historical returns by asset class
            lookback_period: Period to calculate momentum over (days)
            top_n: Number of top asset classes to include (None = all)

        Returns:
            AllocationResult with momentum-based weights
        """
        # Calculate momentum scores
        momentum_scores = {}
        for asset_class in lookback_returns.columns:
            returns = lookback_returns[asset_class].dropna()
            if len(returns) >= lookback_period:
                # Cumulative return over lookback period
                momentum = (1 + returns.tail(lookback_period)).prod() - 1
                momentum_scores[asset_class] = momentum

        # Filter to only positive momentum assets
        positive_momentum = {k: v for k, v in momentum_scores.items() if v > 0}

        if not positive_momentum:
            # No positive momentum, equal weight all
            n = len(self.asset_classes)
            weights = {k: Decimal("1") / Decimal(str(n)) for k in self.asset_classes}
        else:
            # Select top N if specified
            if top_n and top_n < len(positive_momentum):
                sorted_assets = sorted(positive_momentum.items(), key=lambda x: x[1], reverse=True)
                positive_momentum = dict(sorted_assets[:top_n])

            # Weight by momentum strength
            total_momentum = sum(positive_momentum.values())
            weights = {k: Decimal(str(v / total_momentum)) for k, v in positive_momentum.items()}

        # Add zero weights for excluded assets
        for asset_class in self.asset_classes:
            if asset_class not in weights:
                weights[asset_class] = Decimal("0")

        # Apply constraints
        weights = self._apply_asset_class_constraints(weights)

        # Calculate metrics
        metrics = self._calculate_portfolio_metrics(weights)

        return AllocationResult(
            weights=weights,
            expected_return=metrics["expected_return"],
            expected_volatility=metrics["expected_volatility"],
            sharpe_ratio=metrics.get("sharpe_ratio"),
            risk_contributions=None,
            method=AllocationStrategy.MOMENTUM,
            metadata={
                "momentum_scores": {k: float(v) for k, v in momentum_scores.items()},
                "lookback_period": lookback_period,
                "top_n": top_n,
            },
        )

    def equal_weight_allocation(self) -> AllocationResult:
        """
        Create equal-weight allocation across all asset classes.

        Returns:
            AllocationResult with equal weights
        """
        n = len(self.asset_classes)
        if n == 0:
            raise ValueError("No asset classes available for equal weight allocation")

        weights = {k: Decimal("1") / Decimal(str(n)) for k in self.asset_classes}

        # Apply constraints
        weights = self._apply_asset_class_constraints(weights)

        # Calculate metrics
        metrics = self._calculate_portfolio_metrics(weights)

        return AllocationResult(
            weights=weights,
            expected_return=metrics["expected_return"],
            expected_volatility=metrics["expected_volatility"],
            sharpe_ratio=metrics.get("sharpe_ratio"),
            risk_contributions=None,
            method=AllocationStrategy.EQUAL_WEIGHT,
            metadata={"n_asset_classes": n},
        )

    def _get_base_strategic_weights(self, risk_tolerance: RiskTolerance) -> Dict[str, Decimal]:
        """Get base strategic weights by risk tolerance."""
        # Map common asset class types to weights
        # This is a simplified version - real implementation would be more sophisticated

        if risk_tolerance == RiskTolerance.AGGRESSIVE:
            # 80% equities, 15% alternatives, 5% cash
            return {
                AssetClassType.EQUITY: Decimal("0.80"),
                AssetClassType.FIXED_INCOME: Decimal("0.00"),
                AssetClassType.CRYPTO: Decimal("0.05"),
                AssetClassType.COMMODITY: Decimal("0.05"),
                AssetClassType.REAL_ESTATE: Decimal("0.05"),
                AssetClassType.FOREX: Decimal("0.00"),
                AssetClassType.CASH: Decimal("0.05"),
            }
        elif risk_tolerance == RiskTolerance.CONSERVATIVE:
            # 40% equities, 50% bonds, 10% cash
            return {
                AssetClassType.EQUITY: Decimal("0.40"),
                AssetClassType.FIXED_INCOME: Decimal("0.50"),
                AssetClassType.CRYPTO: Decimal("0.00"),
                AssetClassType.COMMODITY: Decimal("0.00"),
                AssetClassType.REAL_ESTATE: Decimal("0.00"),
                AssetClassType.FOREX: Decimal("0.00"),
                AssetClassType.CASH: Decimal("0.10"),
            }
        else:  # MODERATE
            # 60% equities, 30% bonds, 5% alternatives, 5% cash
            return {
                AssetClassType.EQUITY: Decimal("0.60"),
                AssetClassType.FIXED_INCOME: Decimal("0.30"),
                AssetClassType.CRYPTO: Decimal("0.02"),
                AssetClassType.COMMODITY: Decimal("0.01"),
                AssetClassType.REAL_ESTATE: Decimal("0.02"),
                AssetClassType.FOREX: Decimal("0.00"),
                AssetClassType.CASH: Decimal("0.05"),
            }

    def _adjust_for_time_horizon(
        self, weights: Dict[str, Decimal], time_horizon: int
    ) -> Dict[str, Decimal]:
        """Adjust weights for time horizon."""
        # Longer horizon = more equities, less bonds
        # Shorter horizon = more bonds, less equities

        if time_horizon < 3:
            # Short horizon: shift to bonds
            equity_shift = Decimal("-0.10")
            bond_shift = Decimal("0.10")
        elif time_horizon > 15:
            # Long horizon: shift to equities
            equity_shift = Decimal("0.10")
            bond_shift = Decimal("-0.10")
        else:
            return weights

        adjusted = {}
        for asset_class, weight in weights.items():
            if asset_class == AssetClassType.EQUITY:
                adjusted[asset_class] = max(Decimal("0"), min(Decimal("1"), weight + equity_shift))
            elif asset_class == AssetClassType.FIXED_INCOME:
                adjusted[asset_class] = max(Decimal("0"), min(Decimal("1"), weight + bond_shift))
            else:
                adjusted[asset_class] = weight

        return adjusted

    def _adjust_for_income_need(
        self, weights: Dict[str, Decimal], income_need: Decimal
    ) -> Dict[str, Decimal]:
        """Adjust weights for income need."""
        # Higher income need = more bonds/dividend stocks
        if income_need <= Decimal("0.03"):
            return weights  # No adjustment needed

        # Shift from equities to bonds based on income need
        income_factor = (income_need - Decimal("0.03")) / Decimal("0.05")  # 0 to 1
        bond_shift = income_factor * Decimal("0.10")  # Up to 10% shift

        adjusted = {}
        for asset_class, weight in weights.items():
            if asset_class == AssetClassType.FIXED_INCOME:
                adjusted[asset_class] = min(Decimal("1"), weight + bond_shift)
            elif asset_class == AssetClassType.EQUITY:
                adjusted[asset_class] = max(Decimal("0"), weight - bond_shift)
            else:
                adjusted[asset_class] = weight

        return adjusted

    def _adjust_for_liquidity(
        self, weights: Dict[str, Decimal], liquidity_need: Decimal
    ) -> Dict[str, Decimal]:
        """Adjust weights for liquidity need."""
        # Ensure minimum cash allocation
        current_cash = weights.get(AssetClassType.CASH, Decimal("0"))

        if current_cash >= liquidity_need:
            return weights

        # Need to increase cash, reduce other allocations proportionally
        cash_shortfall = liquidity_need - current_cash
        total_reduce = sum(w for k, w in weights.items() if k not in [AssetClassType.CASH])

        if total_reduce == 0:
            return weights

        adjusted = {}
        for asset_class, weight in weights.items():
            if asset_class == AssetClassType.CASH:
                adjusted[asset_class] = liquidity_need
            else:
                reduction = weight * (cash_shortfall / total_reduce)
                adjusted[asset_class] = weight - reduction

        return adjusted

    def _calculate_tilt_from_signal(
        self,
        asset_class: str,
        signal: float,
        max_tilt: Decimal,
        market_regime: MarketRegime,
    ) -> Decimal:
        """Calculate tactical tilt from signal."""
        # Normalize signal to [-1, 1]
        normalized_signal = max(-1, min(1, signal))

        # Adjust for market regime
        regime_multiplier = self._get_regime_multiplier(market_regime)
        adjusted_signal = normalized_signal * regime_multiplier

        # Calculate tilt
        tilt = Decimal(str(adjusted_signal)) * max_tilt

        return tilt

    def _get_regime_multiplier(self, regime: MarketRegime) -> float:
        """Get signal multiplier based on market regime."""
        multipliers = {
            MarketRegime.BULL: 1.2,  # Amplify signals in bull market
            MarketRegime.BEAR: 0.8,  # Dampen signals in bear market
            MarketRegime.NEUTRAL: 1.0,
            MarketRegime.VOLATILE: 0.5,  # Reduce signals in volatile markets
            MarketRegime.RECOVERY: 1.1,  # Slightly amplify in recovery
        }
        return multipliers.get(regime, 1.0)

    def _apply_asset_class_constraints(self, weights: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """Apply asset class min/max weight constraints."""
        constrained = {}

        for asset_class_name, weight in weights.items():
            # Find the asset class
            asset_class = self.asset_classes.get(asset_class_name)
            if asset_class is None:
                # No constraints, use as-is
                constrained[asset_class_name] = weight
                continue

            # Apply constraints
            constrained_weight = max(asset_class.min_weight, min(asset_class.max_weight, weight))
            constrained[asset_class_name] = constrained_weight

        # Renormalize
        total = sum(constrained.values())
        if total > 0:
            constrained = {k: v / total for k, v in constrained.items()}

        return constrained

    def _apply_weight_bounds(
        self,
        weights: Dict[str, Decimal],
        min_weight: Decimal,
        max_weight: Decimal,
    ) -> Dict[str, Decimal]:
        """Apply min/max weight bounds."""
        bounded = {k: max(min_weight, min(max_weight, v)) for k, v in weights.items()}

        # Renormalize
        total = sum(bounded.values())
        if total > 0:
            bounded = {k: v / total for k, v in bounded.items()}

        return bounded

    def _calculate_risk_contributions(
        self,
        weights: Dict[str, Decimal],
        returns: pd.DataFrame,
    ) -> Dict[str, Decimal]:
        """Calculate risk contributions for allocation."""
        try:
            # Get weights as array
            symbols = list(weights.keys())
            weight_array = np.array([float(weights[s]) for s in symbols])

            # Get returns
            alloc_returns = returns[symbols]
            cov_matrix = alloc_returns.cov().values

            # Portfolio variance
            portfolio_var = float(weight_array.T @ cov_matrix @ weight_array)

            if portfolio_var == 0:
                # Equal contributions
                n = len(weights)
                return {k: Decimal("1") / Decimal(str(n)) for k in weights}

            # Marginal contributions
            marginal_contrib = (cov_matrix @ weight_array) / portfolio_var

            # Risk contributions
            risk_contrib = {}
            for i, symbol in enumerate(symbols):
                contrib = weight_array[i] * marginal_contrib[i]
                risk_contrib[symbol] = Decimal(str(contrib))

            return risk_contrib

        except Exception as e:
            logger.warning(f"Risk contribution calculation failed: {e}")
            # Return equal contributions
            n = len(weights)
            return {k: Decimal("1") / Decimal(str(n)) for k in weights}

    def _calculate_portfolio_metrics(
        self,
        weights: Dict[str, Decimal],
        returns: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """Calculate portfolio metrics."""
        # Expected return
        expected_return = Decimal("0")
        for asset_class_name, weight in weights.items():
            asset_class = self.asset_classes.get(asset_class_name)
            if asset_class:
                expected_return += weight * asset_class.expected_return

        # Expected volatility (simplified - assumes uncorrelated)
        expected_volatility = Decimal("0")
        for asset_class_name, weight in weights.items():
            asset_class = self.asset_classes.get(asset_class_name)
            if asset_class:
                expected_volatility += (weight * asset_class.volatility) ** 2

        if expected_volatility > 0:
            expected_volatility = expected_volatility.sqrt()

        metrics = {
            "expected_return": expected_return,
            "expected_volatility": expected_volatility,
        }

        # Calculate Sharpe ratio
        if expected_volatility > 0:
            rf = Decimal("0.02")  # 2% risk-free rate
            sharpe = (expected_return - rf) / expected_volatility
            metrics["sharpe_ratio"] = sharpe

        return metrics
