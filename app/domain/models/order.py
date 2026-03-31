"""
Order Models with Domain Validation

This module defines order models with comprehensive domain validation
for the algorithmic trading system.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class OrderType(str, Enum):
    """Order type enumeration."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    """Order side enumeration."""

    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Order status enumeration."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Order(BaseModel):
    """Trading order with comprehensive domain validation."""

    model_config = ConfigDict(
        strict=True,  # Prevenir conversiones implícitas
        validate_assignment=True,  # Validar en asignación
        extra="forbid",  # Prohibir campos extra
        str_strip_whitespace=True,  # Limpiar espacios en strings
        use_enum_values=True,  # Usar valores de enum
    )

    id: str = Field(..., description="Unique order identifier")
    order_id: Optional[str] = Field(None, description="Broker-specific order ID")
    symbol: str = Field(..., description="Trading symbol")
    side: OrderSide = Field(..., description="Order side (buy/sell)")
    order_type: OrderType = Field(..., description="Order type")
    quantity: Decimal = Field(..., description="Order quantity")
    price: Optional[Decimal] = Field(None, description="Order price (for limit orders)")
    stop_price: Optional[Decimal] = Field(None, description="Stop price (for stop orders)")
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="Order status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Order timestamp")
    filled_quantity: Decimal = Field(default=Decimal("0"), description="Filled quantity")
    filled_price: Optional[Decimal] = Field(None, description="Average filled price")
    filled_at: Optional[datetime] = Field(None, description="Timestamp when order was filled")
    cancelled_at: Optional[datetime] = Field(None, description="Timestamp when order was cancelled")
    rejected_reason: Optional[str] = Field(None, description="Reason for order rejection")
    commission: Decimal = Field(default=Decimal("0"), description="Commission paid")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional order metadata")

    @field_validator("quantity", "filled_quantity", "commission")
    @classmethod
    def validate_quantity_fields(cls, v) -> Decimal:
        """Validate quantity fields are positive - use config limit."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            logger.error(
                "Order quantity validation failed: invalid type",
                extra={"value_type": type(v).__name__, "value": str(v)},
            )
            raise ValueError("Quantity fields must be numbers")

        if v < 0:
            logger.error(
                "Order quantity validation failed: negative value",
                extra={"value": str(v)},
            )
            raise ValueError(f"Quantity fields must be non-negative, got {v}")
        # Use config for max quantity limit
        tt = get_config().trading_thresholds
        max_quantity = Decimal(str(tt.max_order_quantity_shares))
        if v > max_quantity:
            logger.error(
                "Order quantity validation failed: exceeds limit",
                extra={
                    "value": str(v),
                    "max_limit": str(max_quantity),
                },
            )
            raise ValueError(
                f"Quantity exceeds maximum limit of {tt.max_order_quantity_shares:,.0f} shares, got {v}"
            )

        logger.debug(
            "Order quantity validated",
            extra={"value": str(v)},
        )
        return v

    @field_validator("price", "stop_price", "filled_price")
    @classmethod
    def validate_price_fields(cls, v) -> Optional[Decimal]:
        """Validate price fields are positive - use config limit."""
        if v is None:
            return v

        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            logger.error(
                "Order price validation failed: invalid type",
                extra={"value_type": type(v).__name__, "value": str(v)},
            )
            raise ValueError("Price fields must be numbers")

        if v <= 0:
            logger.error(
                "Order price validation failed: non-positive value",
                extra={"value": str(v)},
            )
            raise ValueError(f"Price fields must be positive, got {v}")
        # Use config for max price limit
        tt = get_config().trading_thresholds
        max_price = Decimal(str(tt.max_order_price_usd))
        if v > max_price:
            logger.error(
                "Order price validation failed: exceeds limit",
                extra={
                    "value": str(v),
                    "max_limit": str(max_price),
                },
            )
            raise ValueError(
                f"Price exceeds maximum limit of ${tt.max_order_price_usd:,.0f}, got {v}"
            )

        logger.debug(
            "Order price validated",
            extra={"value": str(v)},
        )
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Validate timestamp is reasonable - use config for age limit."""
        now = datetime.utcnow()
        if v > now:
            logger.error(
                "Order timestamp validation failed: future timestamp",
                extra={"timestamp": v.isoformat(), "now": now.isoformat()},
            )
            raise ValueError(f"Timestamp cannot be in the future, got {v}")

        # Check if timestamp is too old - use config
        tt = get_config().trading_thresholds
        max_age_days = tt.max_order_timestamp_age_days
        oldest_allowed = now - timedelta(days=max_age_days)
        if v < oldest_allowed:
            logger.error(
                "Order timestamp validation failed: too old",
                extra={
                    "timestamp": v.isoformat(),
                    "oldest_allowed": oldest_allowed.isoformat(),
                    "max_age_days": max_age_days,
                },
            )
            raise ValueError(f"Timestamp is too old (more than {max_age_days} days), got {v}")

        logger.debug(
            "Order timestamp validated",
            extra={"timestamp": v.isoformat()},
        )
        return v

    @model_validator(mode="after")
    def validate_order_consistency(self) -> Order:
        """Validate order consistency rules."""
        # Validate filled quantity doesn't exceed order quantity
        if self.filled_quantity > self.quantity:
            logger.error(
                "Order consistency validation failed: filled exceeds quantity",
                extra={
                    "order_id": self.id,
                    "symbol": self.symbol,
                    "quantity": str(self.quantity),
                    "filled_quantity": str(self.filled_quantity),
                },
            )
            raise ValueError(
                f"Filled quantity ({self.filled_quantity}) cannot exceed order quantity ({self.quantity})"
            )

        # Validate price requirements based on order type
        if self.order_type == OrderType.LIMIT:
            if self.price is None:
                logger.error(
                    "Order consistency validation failed: limit order missing price",
                    extra={"order_id": self.id, "symbol": self.symbol},
                )
                raise ValueError("Limit orders must have a price")
            if self.price <= 0:
                logger.error(
                    "Order consistency validation failed: limit order non-positive price",
                    extra={"order_id": self.id, "symbol": self.symbol, "price": str(self.price)},
                )
                raise ValueError("Limit order price must be positive")

        elif self.order_type == OrderType.STOP:
            if self.stop_price is None:
                logger.error(
                    "Order consistency validation failed: stop order missing stop price",
                    extra={"order_id": self.id, "symbol": self.symbol},
                )
                raise ValueError("Stop orders must have a stop price")
            if self.stop_price <= 0:
                logger.error(
                    "Order consistency validation failed: stop order non-positive price",
                    extra={
                        "order_id": self.id,
                        "symbol": self.symbol,
                        "stop_price": str(self.stop_price),
                    },
                )
                raise ValueError("Stop order price must be positive")

        elif self.order_type == OrderType.STOP_LIMIT:
            if self.price is None or self.stop_price is None:
                logger.error(
                    "Order consistency validation failed: stop-limit missing prices",
                    extra={
                        "order_id": self.id,
                        "symbol": self.symbol,
                        "has_price": self.price is not None,
                        "has_stop_price": self.stop_price is not None,
                    },
                )
                raise ValueError("Stop-limit orders must have both price and stop price")
            if self.price <= 0 or self.stop_price <= 0:
                logger.error(
                    "Order consistency validation failed: stop-limit non-positive prices",
                    extra={
                        "order_id": self.id,
                        "symbol": self.symbol,
                        "price": str(self.price),
                        "stop_price": str(self.stop_price),
                    },
                )
                raise ValueError("Stop-limit order prices must be positive")
            if self.price <= self.stop_price:
                logger.error(
                    "Order consistency validation failed: stop-limit price logic",
                    extra={
                        "order_id": self.id,
                        "symbol": self.symbol,
                        "price": str(self.price),
                        "stop_price": str(self.stop_price),
                    },
                )
                raise ValueError("Stop-limit order price must be greater than stop price")

        # Validate stop price logic
        if self.stop_price is not None:
            if self.side == OrderSide.BUY and self.stop_price <= self.price:
                logger.error(
                    "Order consistency validation failed: buy stop price logic",
                    extra={
                        "order_id": self.id,
                        "symbol": self.symbol,
                        "side": self.side.value,
                        "price": str(self.price),
                        "stop_price": str(self.stop_price),
                    },
                )
                raise ValueError("Buy stop price must be greater than limit price")
            elif self.side == OrderSide.SELL and self.stop_price >= self.price:
                logger.error(
                    "Order consistency validation failed: sell stop price logic",
                    extra={
                        "order_id": self.id,
                        "symbol": self.symbol,
                        "side": self.side.value,
                        "price": str(self.price),
                        "stop_price": str(self.stop_price),
                    },
                )
                raise ValueError("Sell stop price must be less than limit price")

        # Validate filled price consistency
        if self.filled_quantity > 0 and self.filled_price is None:
            logger.error(
                "Order consistency validation failed: filled order missing price",
                extra={
                    "order_id": self.id,
                    "symbol": self.symbol,
                    "filled_quantity": str(self.filled_quantity),
                },
            )
            raise ValueError("Filled orders must have a filled price")

        if self.filled_price is not None and self.filled_price <= 0:
            logger.error(
                "Order consistency validation failed: non-positive filled price",
                extra={
                    "order_id": self.id,
                    "symbol": self.symbol,
                    "filled_price": str(self.filled_price),
                },
            )
            raise ValueError("Filled price must be positive")

        logger.debug(
            "Order consistency validated successfully",
            extra={
                "order_id": self.id,
                "symbol": self.symbol,
                "order_type": self.order_type.value,
                "side": self.side.value,
            },
        )
        return self

    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.filled_quantity == self.quantity

    @property
    def is_partially_filled(self) -> bool:
        """Check if order is partially filled."""
        return 0 < self.filled_quantity < self.quantity

    @property
    def remaining_quantity(self) -> Decimal:
        """Calculate remaining quantity to be filled."""
        return self.quantity - self.filled_quantity

    @property
    def total_value(self) -> Optional[Decimal]:
        """Calculate total order value."""
        if self.price is None:
            return None
        return self.quantity * self.price

    @property
    def filled_value(self) -> Optional[Decimal]:
        """Calculate filled value."""
        if self.filled_price is None:
            return None
        return self.filled_quantity * self.filled_price


class MarketData(BaseModel):
    """Market data with comprehensive validation."""

    symbol: str = Field(..., description="Trading symbol")
    timestamp: datetime = Field(..., description="Data timestamp")
    open_price: Decimal = Field(..., description="Opening price")
    high_price: Decimal = Field(..., description="High price")
    low_price: Decimal = Field(..., description="Low price")
    close_price: Decimal = Field(..., description="Closing price")
    volume: Decimal = Field(..., description="Trading volume")
    bid: Optional[Decimal] = Field(None, description="Best bid price")
    ask: Optional[Decimal] = Field(None, description="Best ask price")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional market data")

    @field_validator("open_price", "high_price", "low_price", "close_price", "volume", "bid", "ask")
    @classmethod
    def validate_price_fields(cls, v) -> Optional[Decimal]:
        """Validate price fields are positive."""
        if v is None:
            return v

        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            logger.error(
                "MarketData price validation failed: invalid type",
                extra={"value_type": type(v).__name__, "value": str(v)},
            )
            raise ValueError("Price fields must be numbers")

        if v <= 0:
            logger.error(
                "MarketData price validation failed: non-positive value",
                extra={"value": str(v)},
            )
            raise ValueError(f"Price fields must be positive, got {v}")
        if v > Decimal("1000000"):  # $1M per share limit
            logger.error(
                "MarketData price validation failed: exceeds limit",
                extra={"value": str(v), "limit": "1000000"},
            )
            raise ValueError(f"Price exceeds maximum limit of $1M, got {v}")

        logger.debug(
            "MarketData price validated",
            extra={"value": str(v)},
        )
        return v

    @field_validator("volume")
    @classmethod
    def validate_volume(cls, v) -> Decimal:
        """Validate volume is non-negative."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            logger.error(
                "MarketData volume validation failed: invalid type",
                extra={"value_type": type(v).__name__, "value": str(v)},
            )
            raise ValueError("Volume must be a number")

        if v < 0:
            logger.error(
                "MarketData volume validation failed: negative value",
                extra={"value": str(v)},
            )
            raise ValueError(f"Volume must be non-negative, got {v}")
        if v > Decimal("1000000000"):  # 1B shares limit
            logger.error(
                "MarketData volume validation failed: exceeds limit",
                extra={"value": str(v), "limit": "1000000000"},
            )
            raise ValueError(f"Volume exceeds maximum limit of 1B shares, got {v}")

        logger.debug(
            "MarketData volume validated",
            extra={"value": str(v)},
        )
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Validate timestamp is reasonable."""
        now = datetime.utcnow()
        if v > now:
            logger.error(
                "MarketData timestamp validation failed: future timestamp",
                extra={"timestamp": v.isoformat(), "now": now.isoformat()},
            )
            raise ValueError(f"Timestamp cannot be in the future, got {v}")

        # Check if timestamp is too old (more than 1 year)
        from datetime import timedelta

        one_year_ago = now - timedelta(days=365)
        if v < one_year_ago:
            logger.error(
                "MarketData timestamp validation failed: too old",
                extra={
                    "timestamp": v.isoformat(),
                    "one_year_ago": one_year_ago.isoformat(),
                },
            )
            raise ValueError(f"Timestamp is too old (more than 1 year), got {v}")

        logger.debug(
            "MarketData timestamp validated",
            extra={"timestamp": v.isoformat()},
        )
        return v

    @model_validator(mode="after")
    def validate_market_data_consistency(self) -> MarketData:
        """Validate market data consistency rules."""
        # Validate high >= low
        if self.high_price < self.low_price:
            logger.error(
                "MarketData consistency validation failed: high < low",
                extra={
                    "symbol": self.symbol,
                    "high_price": str(self.high_price),
                    "low_price": str(self.low_price),
                },
            )
            raise ValueError(
                f"High price ({self.high_price}) must be >= low price ({self.low_price})"
            )

        # Validate close price is within high-low range
        if not (self.low_price <= self.close_price <= self.high_price):
            logger.error(
                "MarketData consistency validation failed: close out of range",
                extra={
                    "symbol": self.symbol,
                    "close_price": str(self.close_price),
                    "low_price": str(self.low_price),
                    "high_price": str(self.high_price),
                },
            )
            raise ValueError(
                f"Close price ({self.close_price}) must be between low ({self.low_price}) "
                f"and high ({self.high_price})"
            )

        # Validate open price is within high-low range
        if not (self.low_price <= self.open_price <= self.high_price):
            logger.error(
                "MarketData consistency validation failed: open out of range",
                extra={
                    "symbol": self.symbol,
                    "open_price": str(self.open_price),
                    "low_price": str(self.low_price),
                    "high_price": str(self.high_price),
                },
            )
            raise ValueError(
                f"Open price ({self.open_price}) must be between low ({self.low_price}) "
                f"and high ({self.high_price})"
            )

        # Validate bid-ask spread
        if self.bid is not None and self.ask is not None:
            if self.bid >= self.ask:
                logger.error(
                    "MarketData consistency validation failed: bid >= ask",
                    extra={
                        "symbol": self.symbol,
                        "bid": str(self.bid),
                        "ask": str(self.ask),
                    },
                )
                raise ValueError(f"Bid price ({self.bid}) must be less than ask price ({self.ask})")

            # Check for excessive spread (>50% of mid price)
            mid_price = (self.bid + self.ask) / 2
            spread_percentage = ((self.ask - self.bid) / mid_price) * 100
            if spread_percentage > 50:
                logger.error(
                    "MarketData consistency validation failed: excessive spread",
                    extra={
                        "symbol": self.symbol,
                        "bid": str(self.bid),
                        "ask": str(self.ask),
                        "spread_percentage": spread_percentage,
                    },
                )
                raise ValueError(
                    f"Excessive spread detected: {spread_percentage:.2f}% "
                    f"(bid: {self.bid}, ask: {self.ask})"
                )

        logger.debug(
            "MarketData consistency validated successfully",
            extra={
                "symbol": self.symbol,
                "timestamp": self.timestamp.isoformat(),
            },
        )
        return self

    @property
    def mid_price(self) -> Optional[Decimal]:
        """Calculate mid price from bid-ask."""
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2
        return None

    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate bid-ask spread."""
        if self.bid is not None and self.ask is not None:
            return self.ask - self.bid
        return None

    @property
    def spread_percentage(self) -> Optional[Decimal]:
        """Calculate spread as percentage of mid price."""
        if self.mid_price is not None and self.mid_price > 0:
            return (self.spread / self.mid_price) * 100
        return None
