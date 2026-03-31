"""
Compliance Service Protocol Interfaces
======================================

Defines the protocol interfaces for all compliance services.
This enables Dependency Inversion Principle - high-level modules depend on abstractions.

Author: Compliance Integration System
Date: 2026-02-03
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal

    import pandas as pd

logger = logging.getLogger(__name__)

# =============================================================================
# BASE PROTOCOLS
# =============================================================================


@runtime_checkable
class ComplianceService(Protocol):
    """
    Base protocol for all compliance services.

    All compliance services must implement this interface.
    """

    def is_available(self) -> bool:
        """Check if the service is available and operational."""
        ...

    def get_service_name(self) -> str:
        """Get the name of the service."""
        ...

    def initialize(self) -> None:
        """Initialize the service (lazy initialization)."""
        logger.debug(
            "Initializing compliance service",
            extra={"service_name": self.get_service_name()},
        )


# =============================================================================
# PRE-TRADE CHECK PROTOCOLS
# =============================================================================


@runtime_checkable
class PreTradeCheckable(ComplianceService, Protocol):
    """
    Protocol for services that can perform pre-trade checks.

    Pre-trade checks validate trading decisions BEFORE execution.
    """

    def check_pre_trade(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        current_price: Decimal,
        price_history: pd.DataFrame | None = None,
        **kwargs: (
            str | int | float | bool | Decimal | datetime
        ),  # Extension point for service-specific parameters
    ) -> dict[str, bool | float | list[str] | dict[str, float]]:
        """
        Perform pre-trade compliance check.

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Order quantity
            current_price: Current market price
            price_history: Historical price data
            **kwargs: Additional service-specific parameters

        Returns:
            Dict containing:
                - can_execute (bool): Whether trade can proceed
                - confidence (float): Confidence score (0-1)
                - reasons (List[str]): Reasons for decision
                - risk_factors (Dict[str, float]): Risk factors
        """
        logger.debug(
            "Performing pre-trade check",
            extra={
                "symbol": symbol,
                "side": side,
                "quantity": str(quantity),
                "current_price": str(current_price),
                "has_price_history": price_history is not None,
            },
        )
        ...


# =============================================================================
# POST-TRADE CHECK PROTOCOLS
# =============================================================================


@runtime_checkable
class PostTradeCheckable(ComplianceService, Protocol):
    """
    Protocol for services that can perform post-trade analysis.

    Post-trade checks analyze execution quality AFTER execution.
    """

    def check_post_trade(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        execution_price: Decimal,
        signal_price: Decimal | None = None,
        signal_time: datetime | None = None,
        submission_time: datetime | None = None,
        execution_time: datetime | None = None,
        **kwargs: (
            str | int | float | bool | Decimal | datetime
        ),  # Extension point for service-specific parameters
    ) -> dict[str, float]:
        """
        Perform post-trade compliance analysis.

        Args:
            order_id: Unique order identifier
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Executed quantity
            execution_price: Actual execution price
            signal_price: Original signal price
            signal_time: Original signal timestamp
            submission_time: Order submission timestamp
            execution_time: Order execution timestamp
            **kwargs: Additional service-specific parameters

        Returns:
            Dict containing:
                - implementation_shortfall_bps (float): Implementation shortfall
                - market_impact_bps (float): Market impact in bps
                - timing_cost_bps (float): Timing cost in bps
                - execution_quality_score (float): Quality score (0-100)
        """
        logger.debug(
            "Performing post-trade check",
            extra={
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": str(quantity),
                "execution_price": str(execution_price),
                "signal_price": str(signal_price) if signal_price else None,
            },
        )
        ...


# =============================================================================
# OPTIMIZATION PROTOCOLS
# =============================================================================


class Optimizable(ComplianceService, Protocol):
    """
    Protocol for services that can perform portfolio optimization.

    Optimization services calculate optimal portfolio weights.
    """

    def optimize_portfolio(
        self,
        symbols: list[str],
        returns: pd.DataFrame,
        current_prices: dict[str, Decimal],
        constraints: dict[str, float] | None = None,
        **kwargs: (
            str | int | float | bool | Decimal | datetime
        ),  # Extension point for service-specific parameters
    ) -> dict[str, float | dict[str, float]]:
        """
        Optimize portfolio weights.

        Args:
            symbols: List of symbols in portfolio
            returns: Returns DataFrame (symbols x dates)
            current_prices: Current market prices
            constraints: Optimization constraints
            **kwargs: Additional service-specific parameters

        Returns:
            Dict containing:
                - weights (Dict[str, float]): Optimized weights
                - expected_return (float): Expected portfolio return
                - expected_risk (float): Expected portfolio risk
                - sharpe_ratio (float): Sharpe ratio
        """
        logger.debug(
            "Optimizing portfolio",
            extra={
                "num_symbols": len(symbols),
                "returns_shape": returns.shape if returns is not None else None,
                "has_constraints": constraints is not None,
            },
        )
        ...


# =============================================================================
# SPECIALIZED PROTOCOLS
# =============================================================================


class RegimeDetectable(ComplianceService, Protocol):
    """Protocol for services that can detect market regimes."""

    def detect_regime(
        self,
        price_history: pd.DataFrame,
        **kwargs: (
            str | int | float | bool | Decimal | datetime
        ),  # Extension point for service-specific parameters
    ) -> str:
        """
        Detect current market regime.

        Returns:
            Regime label (e.g., "BULL", "BEAR", "NEUTRAL")
        """
        logger.debug(
            "Detecting market regime",
            extra={
                "price_history_shape": (price_history.shape if price_history is not None else None),
            },
        )
        ...


class AlphaGeneratable(ComplianceService, Protocol):
    """Protocol for services that can generate alpha signals."""

    def generate_alpha(
        self,
        symbol: str,
        market_data: pd.DataFrame,
        **kwargs: (
            str | int | float | bool | Decimal | datetime
        ),  # Extension point for service-specific parameters
    ) -> dict[str, float | int]:
        """
        Generate alpha signal.

        Returns:
            Dict containing:
                - confidence (float): Alpha confidence
                - signal (float): Signal strength
                - horizon (int): Recommended holding period
        """
        logger.debug(
            "Generating alpha signal",
            extra={
                "symbol": symbol,
                "market_data_shape": market_data.shape if market_data is not None else None,
            },
        )
        ...


class RiskCalculable(ComplianceService, Protocol):
    """Protocol for services that can calculate risk metrics."""

    def calculate_risk_metrics(
        self,
        returns: pd.DataFrame,
        **kwargs: (
            str | int | float | bool | Decimal | datetime
        ),  # Extension point for service-specific parameters
    ) -> dict[str, float]:
        """
        Calculate risk metrics.

        Returns:
            Dict containing:
                - var_95 (float): 95% VaR
                - beta (float): Beta coefficient
                - volatility (float): Annualized volatility
        """
        logger.debug(
            "Calculating risk metrics",
            extra={
                "returns_shape": returns.shape if returns is not None else None,
            },
        )
        ...


class LiquidityAnalyzable(ComplianceService, Protocol):
    """Protocol for services that can analyze liquidity."""

    def analyze_liquidity(
        self,
        symbol: str,
        quantity: Decimal,
        order_book: dict[str, float | int | Decimal] | None = None,
        **kwargs: (
            str | int | float | bool | Decimal | datetime
        ),  # Extension point for service-specific parameters
    ) -> dict[str, float | str]:
        """
        Analyze liquidity conditions.

        Returns:
            Dict containing:
                - liquidity_score (float): Liquidity score (0-100)
                - liquidity_regime (str): Regime label
                - estimated_impact_bps (float): Estimated market impact
        """
        logger.debug(
            "Analyzing liquidity",
            extra={
                "symbol": symbol,
                "quantity": str(quantity),
                "has_order_book": order_book is not None,
            },
        )
        ...


class ExecutionAlgorithm(ComplianceService, Protocol):
    """Protocol for execution algorithm services."""

    def get_execution_params(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        urgency: float = 0.5,
        **kwargs: (
            str | int | float | bool | Decimal | datetime
        ),  # Extension point for service-specific parameters
    ) -> dict[str, str | (Decimal | None)]:
        """
        Get execution parameters.

        Returns:
            Dict containing:
                - algorithm (str): Algorithm name
                - venue (str): Execution venue
                - limit_price (Optional[Decimal]): Limit price if applicable
        """
        logger.debug(
            "Getting execution parameters",
            extra={
                "symbol": symbol,
                "side": side,
                "quantity": str(quantity),
                "urgency": urgency,
            },
        )
        ...


class TransactionCostModel(ComplianceService, Protocol):
    """Protocol for transaction cost models."""

    def estimate_costs(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        current_price: Decimal,
        **kwargs: (
            str | int | float | bool | Decimal | datetime
        ),  # Extension point for service-specific parameters
    ) -> dict[str, float]:
        """
        Estimate transaction costs.

        Returns:
            Dict containing:
                - market_impact_bps (float): Market impact
                - timing_cost_bps (float): Timing cost
                - commission_bps (float): Commission
                - total_cost_bps (float): Total cost
        """
        logger.debug(
            "Estimating transaction costs",
            extra={
                "symbol": symbol,
                "side": side,
                "quantity": str(quantity),
                "current_price": str(current_price),
            },
        )
        ...


class MetaLabelingService(ComplianceService, Protocol):
    """Protocol for meta-labeling services."""

    def apply_meta_labels(
        self,
        predictions: pd.DataFrame,
        **kwargs: (
            str | int | float | bool | Decimal | datetime
        ),  # Extension point for service-specific parameters
    ) -> pd.DataFrame:
        """
        Apply meta-labeling to predictions.

        Returns:
            DataFrame with meta-labels applied
        """
        logger.debug(
            "Applying meta-labels",
            extra={
                "predictions_shape": predictions.shape if predictions is not None else None,
            },
        )
        ...


class CrossValidationService(ComplianceService, Protocol):
    """Protocol for cross-validation services."""

    def get_splits(
        self,
        data: pd.DataFrame,
        **kwargs: (
            str | int | float | bool | Decimal | datetime
        ),  # Extension point for service-specific parameters
    ) -> list[tuple]:
        """
        Get cross-validation splits.

        Returns:
            List of (train_idx, test_idx) tuples
        """
        logger.debug(
            "Getting cross-validation splits",
            extra={
                "data_shape": data.shape if data is not None else None,
            },
        )
        ...
