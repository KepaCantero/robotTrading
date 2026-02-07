"""
Portfolio Construction - Rishi Narang "Inside the Black Box" Chapter 6

This module implements the Portfolio Construction architecture from Narang's framework:
- Portfolio optimization with constraints
- Alpha/risk/transaction cost balance
- Rebalancing logic
- Multi-asset allocation

Key concepts from "Inside the Black Box":
- Portfolio construction combines alpha, risk, and transaction cost models
- Optimization balances expected returns against risk and costs
- Constraints ensure practical, implementable portfolios
- Rebalancing trades off tracking error against transaction costs

From Narang: "Portfolio construction is the process of translating the outputs
of the alpha model and the risk model into a portfolio that can be traded."
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from app.services.risk_models_narang import RiskModel, get_risk_model
from app.services.transaction_costs import TransactionCostModel, get_transaction_cost_model

logger = logging.getLogger(__name__)


class OptimizationMethod(str, Enum):
    """Portfolio optimization methods."""

    MEAN_VARIANCE = "mean_variance"  # Markowitz mean-variance
    EQUAL_WEIGHT = "equal_weight"  # Naive 1/N
    RISK_PARITY = "risk_parity"  # Equal risk contribution
    MAX_SHARPE = "max_sharpe"  # Maximize Sharpe ratio
    MIN_VARIANCE = "min_variance"  # Minimize variance
    BLACK_LITTERMAN = "black_litterman"  # Black-Litterman model
    ALPHA_RANK = "alpha_rank"  # Rank-weighted by alpha


class RebalanceTrigger(str, Enum):
    """Triggers for portfolio rebalancing."""

    SCHEDULED = "scheduled"  # Time-based (daily, weekly, etc.)
    DRIFT = "drift"  # Weight drift exceeds threshold
    OPPORTUNITY = "opportunity"  # New alpha opportunity
    RISK_LIMIT = "risk_limit"  # Risk limits breached


@dataclass
class AlphaView:
    """
    Alpha view for portfolio construction.

    From Narang: Alpha views are the inputs to portfolio optimization,
    representing the expected returns and confidence from the alpha model.
    """

    symbol: str
    expected_return: float  # Expected return (in bps or %)
    confidence: float  # 0-1, confidence in alpha
    alpha_source: str  # Source of alpha
    holding_period: int  # Expected holding period in days
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioConstraints:
    """
    Constraints for portfolio optimization.

    From Narang: Constraints ensure portfolios are practical and implementable.
    """

    # Position constraints
    max_position_size: Decimal = Decimal("0.10")  # Max 10% per position
    min_position_size: Decimal = Decimal("0.01")  # Min 1% per position
    max_leverage: Decimal = Decimal("1.0")  # Max gross exposure

    # Turnover constraints
    max_turnover: Decimal = Decimal("0.20")  # Max 20% monthly turnover
    max_new_positions: int = 10  # Max new positions per rebalance

    # Concentration constraints
    max_sector_exposure: Decimal = Decimal("0.30")  # Max 30% per sector
    max_country_exposure: Decimal = Decimal("0.50")  # Max 50% per country

    # Trading constraints
    min_liquidity: Decimal = Decimal("1000000")  # Min $1M daily volume
    max_participation_rate: Decimal = Decimal("0.05")  # Max 5% of daily volume

    # Risk constraints
    max_beta: Decimal = Decimal("1.5")
    min_beta: Decimal = Decimal("0.5")
    max_volatility: Decimal = Decimal("0.30")  # Max 30% annual vol


@dataclass
class PortfolioWeights:
    """Portfolio weights and metadata."""

    weights: Dict[str, Decimal]  # symbol -> weight
    optimization_method: OptimizationMethod
    timestamp: datetime = field(default_factory=datetime.now)
    expected_return: Decimal = Decimal("0")
    expected_risk: Decimal = Decimal("0")
    transaction_costs: Decimal = Decimal("0")

    @property
    def long_exposure(self) -> Decimal:
        """Total long exposure."""
        return sum(w for w in self.weights.values() if w > 0)

    @property
    def short_exposure(self) -> Decimal:
        """Total short exposure."""
        return sum(abs(w) for w in self.weights.values() if w < 0)

    @property
    def gross_exposure(self) -> Decimal:
        """Gross exposure (long + short)."""
        return self.long_exposure + self.short_exposure

    @property
    def net_exposure(self) -> Decimal:
        """Net exposure (long - short)."""
        return sum(self.weights.values())


@dataclass
class RebalanceRecommendation:
    """Recommendation for portfolio rebalancing."""

    should_rebalance: bool
    trigger: RebalanceTrigger
    reason: str
    trades: List[Tuple[str, Decimal, Decimal]]  # (symbol, old_weight, new_weight)
    estimated_cost: Decimal
    expected_benefit: Decimal
    timestamp: datetime = field(default_factory=datetime.now)


class PortfolioConstructor:
    """
    Portfolio constructor implementing Narang's framework.

    From Narang Chapter 6: The portfolio constructor:
    1. Takes alpha signals from the alpha model
    2. Applies risk constraints from the risk model
    3. Accounts for transaction costs
    4. Outputs implementable portfolio weights

    This implements Narang's key insight: Portfolio construction is the
    "black box" that combines all other models.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", self.__class__.__name__)

        # Sub-models
        self.risk_model: Optional[RiskModel] = None
        self.cost_model: Optional[TransactionCostModel] = None

        # Optimization settings
        self.optimization_method = OptimizationMethod(
            config.get("optimization_method", "mean_variance")
        )
        self.constraints = PortfolioConstraints(**config.get("constraints", {}))

        # Rebalancing settings
        self.rebalance_frequency = config.get("rebalance_frequency", "weekly")
        self.drift_threshold = Decimal(str(config.get("drift_threshold", 0.05)))

        # History
        self.current_weights: Dict[str, Decimal] = {}
        self.rebalance_history: List[RebalanceRecommendation] = []

    def set_risk_model(self, risk_model: RiskModel) -> None:
        """Set the risk model for constraints."""
        self.risk_model = risk_model
        logger.info(f"Risk model set: {risk_model.name}")

    def set_cost_model(self, cost_model: TransactionCostModel) -> None:
        """Set the transaction cost model."""
        self.cost_model = cost_model
        logger.info(f"Cost model set: {cost_model.name}")

    def construct_portfolio(
        self,
        alpha_views: List[AlphaView],
        current_portfolio: Optional[Dict[str, Decimal]] = None,
        returns: Optional[pd.DataFrame] = None,
    ) -> PortfolioWeights:
        """
        Construct optimal portfolio from alpha views.

        From Narang: This is the core function that combines all models.

        Args:
            alpha_views: List of alpha views from alpha model
            current_portfolio: Current portfolio weights
            returns: Historical returns for risk estimation

        Returns:
            Optimal portfolio weights
        """
        if not alpha_views:
            return PortfolioWeights(weights={}, optimization_method=self.optimization_method)

        # Filter by constraints
        valid_views = self._filter_by_constraints(alpha_views)
        logger.info(f"Filtered to {len(valid_views)} valid views from {len(alpha_views)} total")

        if not valid_views:
            return PortfolioWeights(weights={}, optimization_method=self.optimization_method)

        # Select optimization method
        if self.optimization_method == OptimizationMethod.EQUAL_WEIGHT:
            weights = self._equal_weight(valid_views)
        elif self.optimization_method == OptimizationMethod.RISK_PARITY:
            weights = self._risk_parity(valid_views, returns)
        elif self.optimization_method == OptimizationMethod.ALPHA_RANK:
            weights = self._alpha_rank(valid_views)
        elif self.optimization_method == OptimizationMethod.MAX_SHARPE:
            weights = self._max_sharpe(valid_views, returns)
        elif self.optimization_method == OptimizationMethod.MIN_VARIANCE:
            weights = self._min_variance(valid_views, returns)
        else:  # MEAN_VARIANCE
            weights = self._mean_variance(valid_views, returns)

        # Apply risk model constraints
        if self.risk_model and returns is not None:
            weights = self._apply_risk_constraints(weights, returns)

        # Apply position-level constraints
        weights = self._apply_position_constraints(weights)

        # Estimate transaction costs
        transaction_costs = self._estimate_transaction_costs(
            current_portfolio or {}, weights, returns
        )

        # Calculate portfolio metrics
        expected_return = self._calculate_expected_return(weights, alpha_views)
        expected_risk = (
            self._calculate_expected_risk(weights, returns) if returns is not None else Decimal("0")
        )

        return PortfolioWeights(
            weights=weights,
            optimization_method=self.optimization_method,
            expected_return=expected_return,
            expected_risk=expected_risk,
            transaction_costs=transaction_costs,
        )

    def _filter_by_constraints(self, alpha_views: List[AlphaView]) -> List[AlphaView]:
        """Filter alpha views by constraints."""
        valid = []

        for view in alpha_views:
            # Check confidence threshold
            if view.confidence < self.config.get("min_confidence", 0.6):
                continue

            # Check minimum expected return
            if abs(view.expected_return) < self.config.get("min_expected_return", 0.01):
                continue

            # Check max positions
            if len(valid) >= self.constraints.max_new_positions:
                # Keep only the best views
                valid.sort(key=lambda v: v.confidence * abs(v.expected_return), reverse=True)
                valid = valid[: self.constraints.max_new_positions]
                if view.confidence * abs(view.expected_return) > valid[-1].confidence * abs(
                    valid[-1].expected_return
                ):
                    valid[-1] = view
                continue

            valid.append(view)

        return valid

    def _equal_weight(self, alpha_views: List[AlphaView]) -> Dict[str, Decimal]:
        """Equal weight (1/N) portfolio."""
        n = len(alpha_views)
        weight = Decimal("1.0") / Decimal(str(n))
        return {view.symbol: weight for view in alpha_views}

    def _alpha_rank(self, alpha_views: List[AlphaView]) -> Dict[str, Decimal]:
        """Rank-weighted portfolio by alpha."""
        # Sort by expected return * confidence
        sorted_views = sorted(
            alpha_views, key=lambda v: abs(v.expected_return) * v.confidence, reverse=True
        )

        # Exponential decay weights
        weights = {}
        decay_factor = 0.9

        for i, view in enumerate(sorted_views):
            weight = decay_factor**i
            weights[view.symbol] = Decimal(str(weight))

        # Normalize
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return weights

    def _risk_parity(
        self, alpha_views: List[AlphaView], returns: Optional[pd.DataFrame]
    ) -> Dict[str, Decimal]:
        """
        Risk parity portfolio (equal risk contribution).

        Simplified implementation using inverse volatility weighting.
        """
        if returns is None or len(returns) == 0:
            return self._equal_weight(alpha_views)

        # Get symbols from alpha views
        symbols = [view.symbol for view in alpha_views]

        # Get available returns
        available_symbols = [s for s in symbols if s in returns.columns]
        if not available_symbols:
            return self._equal_weight(alpha_views)

        # Calculate volatilities
        vols = returns[available_symbols].std() * np.sqrt(252)

        # Inverse volatility weights
        inv_vols = 1 / vols
        inv_vols = inv_vols / inv_vols.sum()

        weights = {
            symbol: Decimal(str(inv_vols.get(symbol, 1.0 / len(symbols)))) for symbol in symbols
        }

        # Normalize
        total = sum(abs(w) for w in weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return weights

    def _mean_variance(
        self, alpha_views: List[AlphaView], returns: Optional[pd.DataFrame]
    ) -> Dict[str, Decimal]:
        """
        Mean-variance optimization (Markowitz).

        Maximize: mu'w - lambda * w'Sigma*w
        Subject to: sum(w) = 1, bounds
        """
        if returns is None or len(returns) < 20:
            return self._alpha_rank(alpha_views)

        symbols = [view.symbol for view in alpha_views]
        available_symbols = [s for s in symbols if s in returns.columns]

        if len(available_symbols) < 2:
            return self._equal_weight(alpha_views)

        # Get expected returns from alpha views
        mu = np.array(
            [
                next(v.expected_return for v in alpha_views if v.symbol == s)
                for s in available_symbols
            ]
        )

        # Covariance matrix
        cov_matrix = returns[available_symbols].cov().values * 252  # Annualized

        # Risk aversion
        lambda_param = self.config.get("risk_aversion", 1.0)

        # Objective: minimize -mu'w + lambda * w'Sigma*w
        def objective(w):
            return -float(mu.T @ w) + lambda_param * float(w.T @ cov_matrix @ w)

        # Constraints
        n = len(available_symbols)
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]  # Fully invested

        # Bounds
        min_w = float(self.constraints.min_position_size)
        max_w = float(self.constraints.max_position_size)
        bounds = [(min_w, max_w) for _ in range(n)]

        # Initial guess (equal weight)
        w0 = np.ones(n) / n

        # Optimize
        try:
            result = minimize(
                objective,
                w0,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"maxiter": 100},
            )

            if result.success:
                weights = {
                    symbol: Decimal(str(w)) for symbol, w in zip(available_symbols, result.x)
                }
            else:
                logger.warning(f"Optimization failed: {result.message}")
                weights = self._alpha_rank(alpha_views)

        except Exception as e:
            logger.error(f"Optimization error: {e}")
            weights = self._alpha_rank(alpha_views)

        return weights

    def _max_sharpe(
        self, alpha_views: List[AlphaView], returns: Optional[pd.DataFrame]
    ) -> Dict[str, Decimal]:
        """Maximize Sharpe ratio portfolio."""
        if returns is None or len(returns) < 20:
            return self._alpha_rank(alpha_views)

        symbols = [view.symbol for view in alpha_views]
        available_symbols = [s for s in symbols if s in returns.columns]

        if len(available_symbols) < 2:
            return self._equal_weight(alpha_views)

        # Expected returns
        mu = np.array(
            [
                next(v.expected_return for v in alpha_views if v.symbol == s)
                for s in available_symbols
            ]
        )

        # Covariance matrix
        cov_matrix = returns[available_symbols].cov().values * 252

        # Risk-free rate
        rf = self.config.get("risk_free_rate", 0.02)

        # Objective: maximize Sharpe ratio = (mu'w - rf) / sqrt(w'Sigma*w)
        # Equivalent to minimizing: - (mu'w - rf) / sqrt(w'Sigma*w)
        def objective(w):
            portfolio_return = float(mu.T @ w)
            portfolio_risk = np.sqrt(float(w.T @ cov_matrix @ w))
            if portfolio_risk < 1e-6:
                return 1e6
            return -(portfolio_return - rf) / portfolio_risk

        # Constraints
        n = len(available_symbols)
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]

        # Bounds
        min_w = float(self.constraints.min_position_size)
        max_w = float(self.constraints.max_position_size)
        bounds = [(min_w, max_w) for _ in range(n)]

        w0 = np.ones(n) / n

        try:
            result = minimize(
                objective,
                w0,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
            )

            if result.success:
                weights = {
                    symbol: Decimal(str(w)) for symbol, w in zip(available_symbols, result.x)
                }
            else:
                weights = self._alpha_rank(alpha_views)

        except Exception as e:
            logger.error(f"Sharpe optimization error: {e}")
            weights = self._alpha_rank(alpha_views)

        return weights

    def _min_variance(
        self, alpha_views: List[AlphaView], returns: Optional[pd.DataFrame]
    ) -> Dict[str, Decimal]:
        """Minimum variance portfolio."""
        if returns is None or len(returns) < 20:
            return self._equal_weight(alpha_views)

        symbols = [view.symbol for view in alpha_views]
        available_symbols = [s for s in symbols if s in returns.columns]

        if len(available_symbols) < 2:
            return self._equal_weight(alpha_views)

        # Covariance matrix
        cov_matrix = returns[available_symbols].cov().values * 252

        # Objective: minimize w'Sigma*w
        def objective(w):
            return float(w.T @ cov_matrix @ w)

        n = len(available_symbols)
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]

        min_w = float(self.constraints.min_position_size)
        max_w = float(self.constraints.max_position_size)
        bounds = [(min_w, max_w) for _ in range(n)]

        w0 = np.ones(n) / n

        try:
            result = minimize(
                objective,
                w0,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
            )

            if result.success:
                weights = {
                    symbol: Decimal(str(w)) for symbol, w in zip(available_symbols, result.x)
                }
            else:
                weights = self._alpha_rank(alpha_views)

        except Exception as e:
            logger.error(f"Min variance optimization error: {e}")
            weights = self._alpha_rank(alpha_views)

        return weights

    def _apply_risk_constraints(
        self, weights: Dict[str, Decimal], returns: pd.DataFrame
    ) -> Dict[str, Decimal]:
        """Apply risk model constraints."""
        if not self.risk_model:
            return weights

        # Convert to pandas Series
        weight_series = pd.Series({k: float(v) for k, v in weights.items()})

        # Apply factor constraints if available
        # This is a simplified version
        constrained = weight_series.copy()

        # Apply max position size
        max_size = float(self.constraints.max_position_size)
        constrained = constrained.clip(-max_size, max_size)

        # Renormalize
        if constrained.sum() != 0:
            constrained = constrained / constrained.sum()

        return {k: Decimal(str(v)) for k, v in constrained.items()}

    def _apply_position_constraints(self, weights: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """Apply position-level constraints."""
        constrained = {}

        for symbol, weight in weights.items():
            # Apply max position size
            if abs(weight) > self.constraints.max_position_size:
                constrained[symbol] = (
                    self.constraints.max_position_size
                    if weight > 0
                    else -self.constraints.max_position_size
                )
            else:
                constrained[symbol] = weight

        # Normalize
        total = sum(abs(v) for v in constrained.values())
        if total > 0:
            constrained = {k: v / total for k, v in constrained.items()}

        return constrained

    def _estimate_transaction_costs(
        self,
        current_weights: Dict[str, Decimal],
        new_weights: Dict[str, Decimal],
        returns: Optional[pd.DataFrame],
    ) -> Decimal:
        """Estimate total transaction costs for rebalancing."""
        if not self.cost_model:
            return Decimal("0")

        total_cost = Decimal("0")

        # Calculate trades
        all_symbols = set(current_weights.keys()) | set(new_weights.keys())

        for symbol in all_symbols:
            old_weight = current_weights.get(symbol, Decimal("0"))
            new_weight = new_weights.get(symbol, Decimal("0"))

            if abs(new_weight - old_weight) < Decimal("0.01"):  # 1% threshold
                continue

            # Estimate cost (simplified - would use market data in practice)
            trade_value = abs(new_weight - old_weight) * 1000000  # Assume $1M portfolio
            estimated_cost_bps = 10  # Assume 10 bps average cost
            cost = trade_value * estimated_cost_bps / 10000
            total_cost += cost

        return total_cost

    def _calculate_expected_return(
        self, weights: Dict[str, Decimal], alpha_views: List[AlphaView]
    ) -> Decimal:
        """Calculate portfolio expected return."""
        total_return = Decimal("0")

        for symbol, weight in weights.items():
            # Find expected return from alpha views
            for view in alpha_views:
                if view.symbol == symbol:
                    total_return += weight * Decimal(str(view.expected_return))
                    break

        return total_return

    def _calculate_expected_risk(
        self, weights: Dict[str, Decimal], returns: pd.DataFrame
    ) -> Decimal:
        """Calculate portfolio expected risk (volatility)."""
        if returns is None or len(returns) == 0:
            return Decimal("0")

        # Convert weights to array
        symbols = list(weights.keys())
        available_symbols = [s for s in symbols if s in returns.columns]

        if not available_symbols:
            return Decimal("0")

        w = np.array([float(weights[s]) for s in available_symbols])
        cov_matrix = returns[available_symbols].cov().values * 252

        portfolio_variance = w.T @ cov_matrix @ w
        portfolio_volatility = np.sqrt(portfolio_variance)

        return Decimal(str(portfolio_volatility))

    def should_rebalance(
        self,
        current_weights: Dict[str, Decimal],
        target_weights: Dict[str, Decimal],
        portfolio_value: Decimal,
    ) -> RebalanceRecommendation:
        """
        Determine if portfolio should be rebalanced.

        From Narang: Rebalancing trades off tracking error against transaction costs.
        """
        # Calculate drift
        all_symbols = set(current_weights.keys()) | set(target_weights.keys())

        max_drift = Decimal("0")
        needs_rebalance = False
        trigger = RebalanceTrigger.DRIFT
        reason = ""

        for symbol in all_symbols:
            current = current_weights.get(symbol, Decimal("0"))
            target = target_weights.get(symbol, Decimal("0"))
            drift = abs(current - target)

            if drift > max_drift:
                max_drift = drift

        # Check if drift exceeds threshold
        if max_drift > self.drift_threshold:
            needs_rebalance = True
            trigger = RebalanceTrigger.DRIFT
            reason = f"Max drift {max_drift:.2%} exceeds threshold {self.drift_threshold:.2%}"

        # Calculate trades
        trades = []
        for symbol in all_symbols:
            old = current_weights.get(symbol, Decimal("0"))
            new = target_weights.get(symbol, Decimal("0"))
            if abs(new - old) > Decimal("0.01"):  # 1% threshold
                trades.append((symbol, old, new))

        # Estimate cost
        estimated_cost = self._estimate_transaction_costs(current_weights, target_weights, None)

        # Expected benefit from rebalancing
        expected_benefit = max_drift * portfolio_value

        return RebalanceRecommendation(
            should_rebalance=needs_rebalance,
            trigger=trigger,
            reason=reason,
            trades=trades,
            estimated_cost=estimated_cost,
            expected_benefit=expected_benefit,
        )


def get_portfolio_constructor(config: Dict[str, Any]) -> PortfolioConstructor:
    """
    Factory function to create portfolio constructor.

    Args:
        config: Configuration dictionary

    Returns:
        PortfolioConstructor instance
    """
    constructor = PortfolioConstructor(config)

    # Set up risk model if specified
    if "risk_model" in config:
        risk_model = get_risk_model(config["risk_model"])
        constructor.set_risk_model(risk_model)

    # Set up cost model if specified
    if "cost_model" in config:
        cost_model = get_transaction_cost_model(config["cost_model"])
        constructor.set_cost_model(cost_model)

    return constructor


__all__ = [
    "OptimizationMethod",
    "RebalanceTrigger",
    "AlphaView",
    "PortfolioConstraints",
    "PortfolioWeights",
    "RebalanceRecommendation",
    "PortfolioConstructor",
    "get_portfolio_constructor",
]
