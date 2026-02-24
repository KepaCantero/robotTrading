"""
Data models for Multi-Asset Portfolio Management.

This module defines the core data structures used throughout the multi-asset
portfolio system, including portfolio definitions, allocations, metrics, and trades.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.config.centralized_config import get_config


class RiskTolerance(str, Enum):
    """Risk tolerance levels for strategic allocation."""

    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class RebalanceFrequency(str, Enum):
    """Rebalancing frequency options."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUALLY = "semi_annually"
    ANNUALLY = "annually"


class AllocationStrategy(str, Enum):
    """Portfolio allocation strategies."""

    STRATEGIC = "strategic"
    TACTICAL = "tactical"
    RISK_PARITY = "risk_parity"
    MOMENTUM = "momentum"
    EQUAL_WEIGHT = "equal_weight"
    CUSTOM = "custom"


class PortfolioMetrics(BaseModel):
    """
    Portfolio performance and risk metrics.

    Attributes:
        total_return: Total portfolio return
        annualized_return: Annualized return
        volatility: Annualized volatility
        sharpe_ratio: Sharpe ratio (risk-adjusted return)
        sortino_ratio: Sortino ratio (downside risk-adjusted)
        max_drawdown: Maximum drawdown
        beta: Portfolio beta
        alpha: Portfolio alpha
        information_ratio: Information ratio
        tracking_error: Tracking error
        var_95: Value at Risk at 95% confidence
        cvar_95: Conditional VaR at 95% confidence
        skewness: Return distribution skewness
        kurtosis: Return distribution kurtosis
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    total_return: Decimal = Field(..., description="Total portfolio return")
    annualized_return: Decimal = Field(..., description="Annualized return")
    volatility: Decimal = Field(..., description="Annualized volatility")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio")
    sortino_ratio: Optional[Decimal] = Field(None, description="Sortino ratio")
    max_drawdown: Optional[Decimal] = Field(None, description="Maximum drawdown")
    beta: Optional[Decimal] = Field(None, description="Portfolio beta")
    alpha: Optional[Decimal] = Field(None, description="Portfolio alpha")
    information_ratio: Optional[Decimal] = Field(None, description="Information ratio")
    tracking_error: Optional[Decimal] = Field(None, description="Tracking error")
    var_95: Optional[Decimal] = Field(None, description="Value at Risk at 95%")
    cvar_95: Optional[Decimal] = Field(None, description="Conditional VaR at 95%")
    skewness: Optional[Decimal] = Field(None, description="Return skewness")
    kurtosis: Optional[Decimal] = Field(None, description="Return kurtosis")
    calculated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When metrics were calculated"
    )

    @field_validator("volatility", "sharpe_ratio", "sortino_ratio")
    @classmethod
    def validate_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Validate that risk metrics are non-negative."""
        if v is not None and v < 0:
            raise ValueError(f"Risk metric must be non-negative, got {v}")
        return v

    @field_validator("max_drawdown")
    @classmethod
    def validate_drawdown(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Validate that drawdown is non-positive (losses)."""
        if v is not None and v > 0:
            raise ValueError(f"Max drawdown must be non-positive (a loss), got {v}")
        return v


# Trade class moved to app.backtesting.models as the canonical implementation
# Use: from app.backtesting.models import Trade
# The canonical Trade now includes all fields: asset_class, value, currency, priority, estimated_cost


@dataclass
class MultiAssetAllocation:
    """
    Allocation for a single asset class.

    This represents both the allocation to an asset class and the
    distribution of that allocation among specific assets within the class.

    Attributes:
        asset_class: Asset class definition
        weight: Weight allocated to this asset class (0-1)
        assets: Dictionary mapping symbols to weights within the asset class
        expected_return: Expected return for this allocation
        risk: Risk level for this allocation
    """

    asset_class: AssetClass
    weight: Decimal
    assets: Dict[str, Decimal]
    expected_return: Optional[Decimal] = None
    risk: Optional[Decimal] = None

    @property
    def total_weight(self) -> Decimal:
        """
        Calculate total weight including sub-allocations.

        This should equal the asset class weight if properly normalized.
        """
        return Decimal(sum(self.assets.values())) if self.assets else Decimal("0")

    @property
    def asset_symbols(self) -> List[str]:
        """Get list of asset symbols in this allocation."""
        return list(self.assets.keys())

    def get_asset_weight(self, symbol: str) -> Optional[Decimal]:
        """Get weight of a specific asset within this class."""
        return self.assets.get(symbol)

    def get_absolute_weight(self, symbol: str) -> Decimal:
        """
        Get absolute weight of asset in total portfolio.

        Absolute weight = asset_class_weight * within_class_weight
        """
        within_weight = self.get_asset_weight(symbol)
        if within_weight is None:
            return Decimal("0")
        return self.weight * within_weight

    def validate(self) -> bool:
        """
        Validate the allocation.

        Returns:
            True if allocation is valid

        Raises:
            ValueError: If allocation is invalid
        """
        # Check weight is in valid range
        if self.weight < 0 or self.weight > 1:
            raise ValueError(f"Asset class weight must be between 0 and 1, got {self.weight}")

        # Check sub-allocations sum to approximately 1
        if self.assets:
            total = self.total_weight
            tolerance = Decimal("0.01")  # 1% tolerance
            if abs(total - Decimal("1")) > tolerance:
                raise ValueError(
                    f"Sub-allocations must sum to 1, got {total} " f"(tolerance: {tolerance})"
                )

        # Check all asset weights are non-negative
        for symbol, weight in self.assets.items():
            if weight < 0 or weight > 1:
                raise ValueError(f"Asset weight for {symbol} must be between 0 and 1, got {weight}")

        return True


@dataclass
class MultiAssetPortfolio:
    """
    Multi-asset portfolio with allocations across different asset classes.

    This is the main portfolio data structure that holds all allocations
    and provides methods for querying portfolio state.

    Attributes:
        name: Portfolio name/identifier
        allocations: Dictionary of asset class name to allocation
        total_value: Total portfolio value
        last_rebalanced: Last rebalance timestamp
        rebalance_threshold: Threshold for triggering rebalancing (e.g., 0.05 = 5%)
        currency: Portfolio base currency
        metadata: Additional portfolio metadata
        created_at: Portfolio creation timestamp
        updated_at: Last update timestamp
    """

    name: str
    allocations: Dict[str, MultiAssetAllocation]
    total_value: Decimal
    last_rebalanced: datetime
    rebalance_threshold: Decimal = Decimal("0.05")
    currency: str = "USD"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def get_asset_class_weights(self) -> Dict[str, Decimal]:
        """
        Get weights by asset class.

        Returns:
            Dictionary mapping asset class name to its weight
        """
        return {name: alloc.weight for name, alloc in self.allocations.items()}

    def get_all_assets(self) -> Dict[str, Decimal]:
        """
        Get all assets and their absolute weights.

        Returns:
            Dictionary mapping symbol to absolute weight in portfolio
        """
        all_assets: Dict[str, Decimal] = {}
        for alloc in self.allocations.values():
            for symbol in alloc.assets:
                abs_weight = alloc.get_absolute_weight(symbol)
                all_assets[symbol] = abs_weight
        return all_assets

    def get_total_allocation(self, symbol: str) -> Decimal:
        """
        Get total allocation for a symbol across all asset classes.

        Args:
            symbol: Asset symbol

        Returns:
            Total absolute weight of symbol in portfolio
        """
        total = Decimal("0")
        for alloc in self.allocations.values():
            if symbol in alloc.assets:
                total += alloc.get_absolute_weight(symbol)
        return total

    def get_asset_class_for_symbol(self, symbol: str) -> Optional[str]:
        """
        Get the asset class that contains a given symbol.

        Args:
            symbol: Asset symbol

        Returns:
            Asset class name or None if symbol not found
        """
        for name, alloc in self.allocations.items():
            if symbol in alloc.assets:
                return name
        return None

    def get_portfolio_allocations(self) -> Dict[str, Decimal]:
        """
        Get complete portfolio allocation as symbol -> weight mapping.

        Returns:
            Dictionary of all symbols and their absolute weights
        """
        return self.get_all_assets()

    def calculate_total_weights(self) -> Decimal:
        """
        Calculate sum of all asset class weights.

        Returns:
            Sum of weights (should be approximately 1.0)
        """
        return Decimal(sum(alloc.weight for alloc in self.allocations.values()))

    def validate(self) -> bool:
        """
        Validate portfolio state.

        Returns:
            True if portfolio is valid

        Raises:
            ValueError: If portfolio is invalid
        """
        # Check weights sum to approximately 1
        total_weight = self.calculate_total_weights()
        tolerance = Decimal("0.01")
        if abs(total_weight - Decimal("1")) > tolerance:
            raise ValueError(
                f"Portfolio weights must sum to 1, got {total_weight} " f"(tolerance: {tolerance})"
            )

        # Validate each allocation
        for alloc in self.allocations.values():
            alloc.validate()

        return True

    def needs_rebalancing(self) -> bool:
        """
        Check if portfolio needs rebalancing based on current state.

        This compares current allocations with target allocations and checks
        if any deviation exceeds the rebalance threshold.

        Returns:
            True if rebalancing is needed
        """
        # This would require current market data to compare
        # For now, return False - this is typically checked by the manager
        return False

    def get_asset_class_allocation(self, asset_class_name: str) -> Optional[MultiAssetAllocation]:
        """
        Get allocation for a specific asset class.

        Args:
            asset_class_name: Name of the asset class

        Returns:
            Allocation object or None if not found
        """
        return self.allocations.get(asset_class_name)

    def add_allocation(self, allocation: MultiAssetAllocation) -> None:
        """
        Add or update an asset class allocation.

        Args:
            allocation: Allocation to add
        """
        # Validate before adding
        allocation.validate()
        self.allocations[allocation.asset_class.name] = allocation
        self.updated_at = datetime.utcnow()

    def remove_allocation(self, asset_class_name: str) -> bool:
        """
        Remove an asset class allocation.

        Args:
            asset_class_name: Name of the asset class to remove

        Returns:
            True if allocation was removed, False if not found
        """
        if asset_class_name in self.allocations:
            del self.allocations[asset_class_name]
            self.updated_at = datetime.utcnow()
            return True
        return False

    def calculate_portfolio_metrics(
        self, returns: pd.DataFrame, risk_free_rate: float = getattr(config.trading, 'max_risk_per_trade', 0.02)
    ) -> PortfolioMetrics:
        """
        Calculate portfolio-level metrics.

        Args:
            returns: DataFrame of asset returns (datetime index, symbols as columns)
            risk_free_rate: Annual risk-free rate

        Returns:
            PortfolioMetrics object with calculated metrics
        """
        # Get portfolio weights
        weights_dict = self.get_all_assets()
        symbols = list(weights_dict.keys())

        # Align returns with portfolio symbols
        aligned_returns = returns[symbols] if symbols else pd.DataFrame()

        if aligned_returns.empty:
            # Return default metrics if no data
            return PortfolioMetrics(
                total_return=Decimal("0"),
                annualized_return=Decimal("0"),
                volatility=Decimal("0"),
                sharpe_ratio=None,
                sortino_ratio=None,
                max_drawdown=None,
                beta=None,
                alpha=None,
                information_ratio=None,
                tracking_error=None,
                var_95=None,
                cvar_95=None,
                skewness=None,
                kurtosis=None,
            )

        # Calculate weights array
        weights = np.array([float(weights_dict[s]) for s in symbols])

        # Portfolio returns
        portfolio_returns = aligned_returns.dot(weights)

        # Calculate metrics
        total_return = Decimal(str(portfolio_returns.sum()))
        len(portfolio_returns)

        # Annualized return (assuming daily returns) - use config value
        tt = get_config().trading_thresholds
        annualized_return = Decimal(
            str((1 + portfolio_returns.mean()) ** tt.annual_trading_days - 1)
        )

        # Volatility
        volatility = Decimal(str(portfolio_returns.std() * np.sqrt(tt.annual_trading_days)))

        # Sharpe ratio
        excess_returns = portfolio_returns.mean() - risk_free_rate / tt.annual_trading_days
        sharpe = Decimal(
            str(excess_returns / portfolio_returns.std() * np.sqrt(tt.annual_trading_days))
        )

        # Max drawdown
        cumulative = (1 + portfolio_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_dd = Decimal(str(drawdown.min()))

        return PortfolioMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            sortino_ratio=None,
            beta=None,
            alpha=None,
            information_ratio=None,
            tracking_error=None,
            var_95=None,
            cvar_95=None,
            skewness=None,
            kurtosis=None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert portfolio to dictionary representation.

        Returns:
            Dictionary representation of portfolio
        """
        return {
            "name": self.name,
            "allocations": {
                name: {
                    "weight": str(alloc.weight),
                    "assets": {sym: str(w) for sym, w in alloc.assets.items()},
                    "expected_return": (
                        str(alloc.expected_return) if alloc.expected_return else None
                    ),
                    "risk": str(alloc.risk) if alloc.risk else None,
                }
                for name, alloc in self.allocations.items()
            },
            "total_value": str(self.total_value),
            "last_rebalanced": self.last_rebalanced.isoformat(),
            "rebalance_threshold": str(self.rebalance_threshold),
            "currency": self.currency,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# Import numpy at the end to avoid circular dependencies
import numpy as np

from .asset_class import AssetClass
