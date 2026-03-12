"""Data models for Avellaneda-Stoikov market making.

This module defines the Pydantic data models used throughout the AS model implementation.
All models use Decimal for financial precision and include comprehensive validation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import Field, field_validator
from pydantic.dataclasses import dataclass as pydantic_dataclass

logger = logging.getLogger(__name__)


@pydantic_dataclass
class ASConfig:
    """
    Avellaneda-Stoikov model configuration.

    The AS model requires careful parameter tuning based on the asset being traded,
    market conditions, and the trader's risk appetite.

    Attributes:
        gamma: Risk aversion parameter (0.001 - 0.1).
            Higher values = more inventory averse = wider spreads when holding inventory.
            Typical values: 0.001-0.01 for conservative, 0.01-0.1 for aggressive.
        sigma: Volatility of the asset (annualized).
            Should be estimated from historical data or implied volatility.
            For crypto: 0.5-2.0, For stocks: 0.15-0.5, For forex: 0.05-0.15.
        k: Order book depth parameter (0.001 - 0.1).
            Represents how quickly order flow impacts prices.
            Higher k = deeper book = less impact = tighter spreads possible.
            Can be estimated from market impact regression.
        T: Time horizon for inventory liquidation (in seconds).
            The trading window over which we want to flatten inventory.
            Intraday: 300-3600 (5 min to 1 hour), Daily: 86400 (1 day).
        max_inventory: Maximum position size (in shares/contracts).
            Absolute limit on inventory to control risk.
            Should be set based on capital and risk tolerance.
        target_inventory: Target inventory level (usually 0).
            Most MM strategies target 0 inventory (flat position).
        min_spread_bps: Minimum spread in basis points.
            Ensures quotes are profitable even when model suggests tight spread.
            Typical: 1-5 bps for liquid assets, 5-20 bps for illiquid.
        max_spread_bps: Maximum spread in basis points.
            Prevents quotes from becoming too wide and uncompetitive.
            Typical: 50-200 bps depending on asset class.
    """

    gamma: Decimal = Field(
        default=Decimal("0.01"),
        ge=Decimal("0.001"),
        le=Decimal("0.1"),
        description="Risk aversion parameter",
    )
    sigma: Decimal = Field(
        default=Decimal("0.3"),
        ge=Decimal("0.01"),
        le=Decimal("5.0"),
        description="Annualized volatility",
    )
    k: Decimal = Field(
        default=Decimal("0.01"),
        ge=Decimal("0.001"),
        le=Decimal("0.5"),
        description="Order book depth parameter",
    )
    T: Decimal = Field(
        default=Decimal("3600"),
        gt=Decimal("0"),
        description="Time horizon in seconds",
    )
    max_inventory: int = Field(
        default=100,
        ge=1,
        le=100000,
        description="Maximum position size",
    )
    target_inventory: int = Field(
        default=0,
        ge=-100000,
        le=100000,
        description="Target inventory level",
    )
    min_spread_bps: Decimal = Field(
        default=Decimal("5"),
        ge=Decimal("0.1"),
        le=Decimal("100"),
        description="Minimum spread in basis points",
    )
    max_spread_bps: Decimal = Field(
        default=Decimal("100"),
        ge=Decimal("1"),
        le=Decimal("1000"),
        description="Maximum spread in basis points",
    )

    @field_validator("T")
    @classmethod
    def validate_time_horizon(cls, v: Decimal) -> Decimal:
        """Validate time horizon is reasonable."""
        logger.debug(
            "Validating time horizon",
            extra={"time_horizon": float(v), "validator": "validate_time_horizon"}
        )
        if v < Decimal("1"):
            logger.warning(
                "Time horizon validation failed - too short",
                extra={"time_horizon": float(v), "min_allowed": 1.0}
            )
            raise ValueError("Time horizon must be at least 1 second")
        if v > Decimal("604800"):  # 1 week
            logger.warning(
                "Time horizon validation failed - too long",
                extra={"time_horizon": float(v), "max_allowed": 604800.0}
            )
            raise ValueError("Time horizon should not exceed 1 week")
        logger.debug(
            "Time horizon validated successfully",
            extra={"time_horizon": float(v)}
        )
        return v


@pydantic_dataclass
class ASQuoteParams:
    """
    Parameters for generating a single quote.

    Attributes:
        symbol: Trading symbol (e.g., 'BTC-USD', 'AAPL').
        mid_price: Current mid-price of the asset.
        inventory: Current inventory position (positive = long, negative = short).
        current_timestamp: Current time for quote generation.
        volatility_override: Optional volatility override (defaults to config sigma).
        time_remaining: Optional time remaining in trading window (defaults to T).
    """

    symbol: str = Field(..., min_length=1, description="Trading symbol")
    mid_price: Decimal = Field(..., gt=Decimal("0"), description="Current mid-price")
    inventory: int = Field(..., description="Current inventory position")
    current_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Quote timestamp",
    )
    volatility_override: Optional[Decimal] = Field(
        default=None,
        description="Override volatility for this quote",
    )
    time_remaining: Optional[Decimal] = Field(
        default=None,
        description="Time remaining in trading window (seconds)",
    )


@pydantic_dataclass
class ASQuote:
    """
    Result from Avellaneda-Stoikov quote generation.

    This contains all information about the generated quotes and the
    calculations that went into them.

    Attributes:
        symbol: Trading symbol.
        timestamp: When the quote was generated.
        mid_price: The mid price used for calculations.
        reservation_price: The inventory-adjusted mid price.
            This is where we would want to transact given our inventory.
            Lower than mid when long, higher than mid when short.
        optimal_bid: Optimal bid price to post.
            Usually: reservation_price - optimal_spread/2
        optimal_ask: Optimal ask price to post.
            Usually: reservation_price + optimal_spread/2
        optimal_spread_bps: Optimal half-spread in basis points.
        inventory: Current inventory level.
        inventory_skew: Adjustment applied to reservation price due to inventory.
            Negative when long (lower bid), positive when short (higher bid).
        time_to_expiry: Time remaining until end of trading window.
        spread_adjustment: Any adjustment applied to spread (e.g., min/max limits).
        is_bid_enabled: Whether bid quote is enabled (False if at max long).
        is_ask_enabled: Whether ask quote is enabled (False if at max short).
    """

    symbol: str = Field(..., description="Trading symbol")
    mid_price: Decimal = Field(..., gt=Decimal("0"), description="Mid price")
    reservation_price: Decimal = Field(..., gt=Decimal("0"), description="Inventory-adjusted price")
    optimal_bid: Decimal = Field(..., gt=Decimal("0"), description="Optimal bid quote")
    optimal_ask: Decimal = Field(..., gt=Decimal("0"), description="Optimal ask quote")
    optimal_spread_bps: Decimal = Field(..., ge=Decimal("0"), description="Half-spread in bps")
    inventory: int = Field(..., description="Current inventory")
    inventory_skew: Decimal = Field(..., description="Inventory price adjustment")
    time_to_expiry: Decimal = Field(..., ge=Decimal("0"), description="Time remaining (seconds)")
    spread_adjustment: Decimal = Field(
        default=Decimal("0"),
        description="Spread adjustment applied",
    )
    is_bid_enabled: bool = Field(default=True, description="Whether bid is enabled")
    is_ask_enabled: bool = Field(default=True, description="Whether ask is enabled")
    timestamp: Optional[datetime] = Field(default=None, description="Quote generation time")

    def get_full_spread_bps(self) -> Decimal:
        """Calculate full spread in basis points."""
        full_spread = self.optimal_spread_bps * Decimal("2")
        logger.debug(
            "Calculated full spread",
            extra={
                "symbol": self.symbol,
                "half_spread_bps": float(self.optimal_spread_bps),
                "full_spread_bps": float(full_spread),
                "operation": "get_full_spread_bps"
            }
        )
        return full_spread

    def get_spread_value(self) -> Decimal:
        """Calculate spread in price units."""
        spread_value = self.optimal_ask - self.optimal_bid
        logger.debug(
            "Calculated spread value",
            extra={
                "symbol": self.symbol,
                "bid": float(self.optimal_bid),
                "ask": float(self.optimal_ask),
                "spread_value": float(spread_value),
                "operation": "get_spread_value"
            }
        )
        return spread_value

    def is_inventory_neutral(self) -> bool:
        """Check if position is inventory neutral."""
        is_neutral = abs(self.inventory_skew) < Decimal("0.0001")
        logger.debug(
            "Checking inventory neutrality",
            extra={
                "symbol": self.symbol,
                "inventory_skew": float(self.inventory_skew),
                "is_neutral": is_neutral,
                "operation": "is_inventory_neutral"
            }
        )
        return is_neutral

    def to_dict(self) -> dict[str, str | float | int | bool]:
        """Convert quote to dictionary for serialization."""
        logger.debug(
            "Converting quote to dict",
            extra={"symbol": self.symbol, "operation": "quote_to_dict"}
        )
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "mid_price": float(self.mid_price),
            "reservation_price": float(self.reservation_price),
            "optimal_bid": float(self.optimal_bid),
            "optimal_ask": float(self.optimal_ask),
            "optimal_spread_bps": float(self.optimal_spread_bps),
            "full_spread_bps": float(self.get_full_spread_bps()),
            "inventory": self.inventory,
            "inventory_skew": float(self.inventory_skew),
            "time_to_expiry": float(self.time_to_expiry),
            "is_bid_enabled": self.is_bid_enabled,
            "is_ask_enabled": self.is_ask_enabled,
        }


@dataclass(frozen=True)
class InventoryConfig:
    """
    Configuration for inventory management.

    Attributes:
        max_inventory: Maximum allowed inventory (absolute value).
        min_inventory: Minimum allowed inventory (can be negative for short).
        target_inventory: Desired inventory level (usually 0).
        warning_threshold: Fraction of max_inventory at which to warn.
        liquidation_threshold: Fraction of max_inventory at which to force liquidation.
        decay_rate: Rate at which target inventory adjusts (0-1).
        risk_multiplier: Multiplier for inventory risk calculations.
    """

    max_inventory: int = 100
    min_inventory: int = -100
    target_inventory: int = 0
    warning_threshold: float = 0.7
    liquidation_threshold: float = 0.9
    decay_rate: float = 0.1
    risk_multiplier: float = 1.5


@dataclass
class InventoryState:
    """
    Current state of inventory for a symbol.

    Attributes:
        symbol: Trading symbol.
        current_inventory: Current inventory position.
        target_inventory: Current target (may change over time).
        inventory_value: Total value of inventory at current price.
        inventory_risk: Risk metric (|inventory| × price × volatility × sqrt(T)).
        liquidation_horizon: Time to flatten position (seconds).
        max_inventory: Maximum allowed inventory.
        min_inventory: Minimum allowed inventory.
        is_at_warning_level: Whether inventory exceeds warning threshold.
        is_at_liquidation_level: Whether inventory exceeds liquidation threshold.
        timestamp: When this state was captured.
    """

    symbol: str
    current_inventory: int
    target_inventory: int
    inventory_value: Decimal
    inventory_risk: Decimal
    liquidation_horizon: Decimal
    max_inventory: int
    min_inventory: int
    is_at_warning_level: bool
    is_at_liquidation_level: bool
    timestamp: datetime

    def get_inventory_utilization(self) -> Decimal:
        """Calculate inventory utilization as fraction of max allowed."""
        max_abs = max(abs(self.max_inventory), abs(self.min_inventory))
        if max_abs == 0:
            logger.warning(
                "Inventory utilization calculation - max_abs is zero",
                extra={"symbol": self.symbol, "max_inventory": self.max_inventory, "min_inventory": self.min_inventory}
            )
            return Decimal("0")
        utilization = Decimal(abs(self.current_inventory)) / Decimal(max_abs)
        logger.debug(
            "Calculated inventory utilization",
            extra={
                "symbol": self.symbol,
                "current_inventory": self.current_inventory,
                "max_abs": max_abs,
                "utilization": float(utilization),
                "operation": "get_inventory_utilization"
            }
        )
        return utilization

    def needs_inventory_reduction(self) -> bool:
        """Check if inventory should be reduced."""
        needs_reduction = self.is_at_warning_level or self.is_at_liquidation_level
        if needs_reduction:
            logger.warning(
                "Inventory reduction needed",
                extra={
                    "symbol": self.symbol,
                    "current_inventory": self.current_inventory,
                    "is_at_warning_level": self.is_at_warning_level,
                    "is_at_liquidation_level": self.is_at_liquidation_level,
                    "operation": "needs_inventory_reduction"
                }
            )
        return needs_reduction

    def to_dict(self) -> dict[str, str | float | int | bool]:
        """Convert state to dictionary for serialization."""
        logger.debug(
            "Converting inventory state to dict",
            extra={"symbol": self.symbol, "operation": "inventory_state_to_dict"}
        )
        return {
            "symbol": self.symbol,
            "current_inventory": self.current_inventory,
            "target_inventory": self.target_inventory,
            "inventory_value": float(self.inventory_value),
            "inventory_risk": float(self.inventory_risk),
            "liquidation_horizon": float(self.liquidation_horizon),
            "max_inventory": self.max_inventory,
            "min_inventory": self.min_inventory,
            "is_at_warning_level": self.is_at_warning_level,
            "is_at_liquidation_level": self.is_at_liquidation_level,
            "inventory_utilization": float(self.get_inventory_utilization()),
            "timestamp": self.timestamp.isoformat(),
        }
