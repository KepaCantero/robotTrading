"""
Compliance Service Protocol Interfaces
======================================

Defines the protocol interfaces for all compliance services.
This enables Dependency Inversion Principle - high-level modules depend on abstractions.

Author: Compliance Integration System
Date: 2026-02-03
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol
from decimal import Decimal
from datetime import datetime

import pandas as pd


# =============================================================================
# BASE PROTOCOLS
# =============================================================================


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
        ...


# =============================================================================
# PRE-TRADE CHECK PROTOCOLS
# =============================================================================


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
        price_history: Optional[pd.DataFrame] = None,
        **kwargs: Any,  # Extension point for service-specific parameters
    ) -> Dict[str, Any]:
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
        ...


# =============================================================================
# POST-TRADE CHECK PROTOCOLS
# =============================================================================


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
        signal_price: Optional[Decimal] = None,
        signal_time: Optional[datetime] = None,
        submission_time: Optional[datetime] = None,
        execution_time: Optional[datetime] = None,
        **kwargs: Any,  # Extension point for service-specific parameters
    ) -> Dict[str, Any]:
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
        symbols: List[str],
        returns: pd.DataFrame,
        current_prices: Dict[str, Decimal],
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,  # Extension point for service-specific parameters
    ) -> Dict[str, Any]:
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
        ...


# =============================================================================
# SPECIALIZED PROTOCOLS
# =============================================================================


class RegimeDetectable(ComplianceService, Protocol):
    """Protocol for services that can detect market regimes."""

    def detect_regime(
        self,
        price_history: pd.DataFrame,
        **kwargs: Any,  # Extension point for service-specific parameters
    ) -> str:
        """
        Detect current market regime.

        Returns:
            Regime label (e.g., "BULL", "BEAR", "NEUTRAL")
        """
        ...


class AlphaGeneratable(ComplianceService, Protocol):
    """Protocol for services that can generate alpha signals."""

    def generate_alpha(
        self,
        symbol: str,
        market_data: pd.DataFrame,
        **kwargs: Any,  # Extension point for service-specific parameters
    ) -> Dict[str, Any]:
        """
        Generate alpha signal.

        Returns:
            Dict containing:
                - confidence (float): Alpha confidence
                - signal (float): Signal strength
                - horizon (int): Recommended holding period
        """
        ...


class RiskCalculable(ComplianceService, Protocol):
    """Protocol for services that can calculate risk metrics."""

    def calculate_risk_metrics(
        self,
        returns: pd.DataFrame,
        **kwargs: Any,  # Extension point for service-specific parameters
    ) -> Dict[str, Any]:
        """
        Calculate risk metrics.

        Returns:
            Dict containing:
                - var_95 (float): 95% VaR
                - beta (float): Beta coefficient
                - volatility (float): Annualized volatility
        """
        ...


class LiquidityAnalyzable(ComplianceService, Protocol):
    """Protocol for services that can analyze liquidity."""

    def analyze_liquidity(
        self,
        symbol: str,
        quantity: Decimal,
        order_book: Optional[Any] = None,
        **kwargs: Any,  # Extension point for service-specific parameters
    ) -> Dict[str, Any]:
        """
        Analyze liquidity conditions.

        Returns:
            Dict containing:
                - liquidity_score (float): Liquidity score (0-100)
                - liquidity_regime (str): Regime label
                - estimated_impact_bps (float): Estimated market impact
        """
        ...


class ExecutionAlgorithm(ComplianceService, Protocol):
    """Protocol for execution algorithm services."""

    def get_execution_params(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        urgency: float = 0.5,
        **kwargs: Any,  # Extension point for service-specific parameters
    ) -> Dict[str, Any]:
        """
        Get execution parameters.

        Returns:
            Dict containing:
                - algorithm (str): Algorithm name
                - venue (str): Execution venue
                - limit_price (Optional[Decimal]): Limit price if applicable
        """
        ...


class TransactionCostModel(ComplianceService, Protocol):
    """Protocol for transaction cost models."""

    def estimate_costs(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        current_price: Decimal,
        **kwargs: Any,  # Extension point for service-specific parameters
    ) -> Dict[str, Any]:
        """
        Estimate transaction costs.

        Returns:
            Dict containing:
                - market_impact_bps (float): Market impact
                - timing_cost_bps (float): Timing cost
                - commission_bps (float): Commission
                - total_cost_bps (float): Total cost
        """
        ...


class MetaLabelingService(ComplianceService, Protocol):
    """Protocol for meta-labeling services."""

    def apply_meta_labels(
        self,
        predictions: pd.DataFrame,
        **kwargs: Any,  # Extension point for service-specific parameters
    ) -> pd.DataFrame:
        """
        Apply meta-labeling to predictions.

        Returns:
            DataFrame with meta-labels applied
        """
        ...


class CrossValidationService(ComplianceService, Protocol):
    """Protocol for cross-validation services."""

    def get_splits(
        self,
        data: pd.DataFrame,
        **kwargs: Any,  # Extension point for service-specific parameters
    ) -> List[tuple]:
        """
        Get cross-validation splits.

        Returns:
            List of (train_idx, test_idx) tuples
        """
        ...
