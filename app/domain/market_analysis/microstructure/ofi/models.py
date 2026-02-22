# pylint: disable=unsupported-binary-operation
# mypy: ignore-errors
"""
Data models for Order Flow Imbalance (OFI) module.

This module defines all Pydantic and dataclass models used throughout the OFI
module, ensuring type safety and validation.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator


# Custom exception types for data model validation
class ModelValidationError(ValueError):
    """Raised when data model validation fails."""


class OFIHorizon(str, Enum):
    """OFI prediction horizon."""

    SHORT = "short"  # 1-5 minutes
    MEDIUM = "medium"  # 5-15 minutes
    LONG = "long"  # 15-60 minutes


class OrderSide(str, Enum):
    """Order side enumeration."""

    BUY = "buy"
    SELL = "sell"
    BID = "bid"
    ASK = "ask"


@dataclass(frozen=True)
class OrderBookSnapshot:
    """
    Order book snapshot at a point in time.

    This represents the state of the limit order book with bids and asks
    at various price levels.

    Attributes:
        symbol: Trading symbol
        timestamp: Snapshot timestamp
        bids: List of (price, quantity) tuples for bid levels
        asks: List of (price, quantity) tuples for ask levels

    Example:
        >>> bids = [(Decimal('100.50'), 100), (Decimal('100.49'), 200)]
        >>> asks = [(Decimal('100.51'), 150), (Decimal('100.52'), 300)]
        >>> snapshot = OrderBookSnapshot('AAPL', datetime.now(), bids, asks)
        >>> print(snapshot.spread_bps)  # Spread in basis points
    """

    symbol: str
    timestamp: datetime
    bids: list[tuple[Decimal, int]]
    asks: list[tuple[Decimal, int]]

    @property
    def best_bid(self) -> Decimal | None:
        """Get best (highest) bid price."""
        if not self.bids:
            return None
        return max(price for price, _ in self.bids)

    @property
    def best_ask(self) -> Decimal | None:
        """Get best (lowest) ask price."""
        if not self.asks:
            return None
        return min(price for price, _ in self.asks)

    @property
    def mid_price(self) -> Decimal | None:
        """Calculate mid price."""
        best_bid = self.best_bid
        best_ask = self.best_ask
        if best_bid is None or best_ask is None:
            return None
        return (best_bid + best_ask) / 2

    @property
    def bid_volume(self) -> int:
        """Calculate total bid volume across all levels."""
        return sum(quantity for _, quantity in self.bids)

    @property
    def ask_volume(self) -> int:
        """Calculate total ask volume across all levels."""
        return sum(quantity for _, quantity in self.asks)

    @property
    def total_volume(self) -> int:
        """Calculate total volume (bids + asks)."""
        return self.bid_volume + self.ask_volume

    @property
    def spread(self) -> Decimal | None:
        """Calculate bid-ask spread."""
        best_bid = self.best_bid
        best_ask = self.best_ask
        if best_bid is None or best_ask is None:
            return None
        return best_ask - best_bid

    @property
    def spread_bps(self) -> float | None:
        """Calculate bid-ask spread in basis points."""
        mid_price = self.mid_price
        spread = self.spread
        if mid_price is None or spread is None or mid_price == 0:
            return None
        # NOTE: Use OFIConfig().bps_multiplier when config is injected into this dataclass
        return float(spread / mid_price * 10000)

    @property
    def depth_imbalance(self) -> float | None:
        """
        Calculate depth imbalance.

        Returns (bid_vol - ask_vol) / (bid_vol + ask_vol)
        """
        total = self.total_volume
        if total == 0:
            return None
        return (self.bid_volume - self.ask_volume) / total

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "best_bid": str(self.best_bid) if self.best_bid else None,
            "best_ask": str(self.best_ask) if self.best_ask else None,
            "mid_price": str(self.mid_price) if self.mid_price else None,
            "bid_volume": self.bid_volume,
            "ask_volume": self.ask_volume,
            "total_volume": self.total_volume,
            "spread": str(self.spread) if self.spread else None,
            "spread_bps": self.spread_bps,
            "depth_imbalance": self.depth_imbalance,
        }


@dataclass(frozen=True)
class TickData:
    """
    Tick-level trade or quote data.

    Attributes:
        symbol: Trading symbol
        timestamp: Tick timestamp
        price: Trade price
        quantity: Trade quantity
        side: Order side (bid/ask or buy/sell)
        is_market_buy: True if aggressive buy (market buy hitting ask)
        is_market_sell: True if aggressive sell (market sell hitting bid)

    Example:
        >>> tick = TickData(
        ...     'AAPL',
        ...     datetime.now(),
        ...     Decimal('100.50'),
        ...     100,
        ...     OrderSide.BUY,
        ...     is_market_buy=True
        ... )
    """

    symbol: str
    timestamp: datetime
    price: Decimal
    quantity: int
    side: OrderSide
    is_market_buy: bool | None = None
    is_market_sell: bool | None = None

    @property
    def notional_value(self) -> Decimal:
        """Calculate notional value of the trade."""
        return self.price * self.quantity

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "price": str(self.price),
            "quantity": self.quantity,
            "side": self.side.value,
            "is_market_buy": self.is_market_buy,
            "is_market_sell": self.is_market_sell,
            "notional_value": str(self.notional_value),
        }


class OFIConfig(BaseModel):
    """
    Configuration for OFI calculations.

    Attributes:
        lookback_periods: Number of periods to look back for OFI history
        ofi_threshold: OFI threshold for signal generation
       ofi_threshold_buy: Buy threshold (positive OFI)
        ofi_threshold_sell: Sell threshold (negative OFI)
        confidence_scale: Scale factor for confidence calculation
        min_volume: Minimum volume for valid OFI calculation
        max_spread_bps: Maximum spread in bps for valid OFI
        use_weighted_ofi: Use volume-weighted OFI calculation
        top_levels: Number of top levels to consider in OFI
        smoothing_window: Window for exponential smoothing
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    lookback_periods: int = Field(
        default=20, ge=1, le=100, description="Lookback periods for OFI history"
    )
    ofi_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="OFI threshold for signal generation",
    )
    ofi_threshold_buy: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Buy signal threshold"
    )
    ofi_threshold_sell: float = Field(
        default=-0.15, ge=-1.0, le=0.0, description="Sell signal threshold"
    )
    confidence_scale: float = Field(
        default=0.5, ge=0.01, le=1.0, description="Scale for confidence calculation"
    )
    min_volume: int = Field(default=100, ge=1, description="Minimum volume for valid OFI")
    max_spread_bps: float = Field(default=50.0, ge=0.0, description="Maximum spread in bps")
    use_weighted_ofi: bool = Field(default=True, description="Use volume-weighted OFI")
    top_levels: int = Field(default=5, ge=1, le=20, description="Top levels to consider")
    smoothing_window: int = Field(default=3, ge=1, le=20, description="Smoothing window")

    # OFI value clamping (ofi_calculator.py line 176)
    ofi_min_value: float = Field(
        default=-1.0, ge=-1.0, le=0.0, description="Minimum OFI value for clamping"
    )
    ofi_max_value: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Maximum OFI value for clamping"
    )

    # Weight calculation constants (ofi_calculator.py lines 243, 251)
    weight_min: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Minimum weight for distance-based calculation"
    )
    weight_max: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Maximum weight for distance-based calculation"
    )
    distance_multiplier: float = Field(
        default=10.0, ge=1.0, le=100.0, description="Multiplier for distance in weight calculation"
    )

    # Window calculations (ofi_calculator.py lines 330, 334)
    window_size_multiplier: int = Field(
        default=2, ge=1, le=10, description="Multiplier for window size in momentum calculation"
    )

    # EMA calculation (ofi_calculator.py line 384)
    ema_alpha_numerator: float = Field(
        default=2.0, ge=1.0, le=10.0, description="Numerator for EMA alpha calculation (alpha = 2/(window+1))"
    )

    # Regime detection thresholds (ofi_calculator.py lines 441-443)
    regime_bullish_mean_threshold: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Mean OFI threshold for bullish regime"
    )
    regime_bearish_mean_threshold: float = Field(
        default=-0.1, ge=-1.0, le=0.0, description="Mean OFI threshold for bearish regime"
    )
    regime_stable_std_threshold: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Std threshold for stable regime"
    )
    regime_volatile_std_threshold: float = Field(
        default=0.4, ge=0.0, le=1.0, description="Std threshold for volatile regime"
    )

    # Autocorrelation settings (ofi_calculator.py lines 463, 677)
    max_lag_offset: int = Field(
        default=10, ge=1, le=100, description="Offset for max lag calculation"
    )
    default_max_lag: int = Field(
        default=20, ge=1, le=100, description="Default maximum lag for autocorrelation"
    )

    # Predictive power settings (ofi_calculator.py line 649)
    min_predictive_power_samples: int = Field(
        default=20, ge=5, le=100, description="Minimum samples for predictive power calculation"
    )

    # Basis points conversion (OrderBookSnapshot line 121)
    bps_multiplier: int = Field(
        default=10000, ge=1, le=100000, description="Multiplier for basis points conversion"
    )

    # ========== PREDICTOR CONFIGURATION (ofi_predictor.py) ==========

    # Threshold signal levels (ofi_predictor.py lines 179-188)
    threshold_strong_buy: float = Field(
        default=0.3, ge=0.0, le=1.0, description="OFI threshold for strong buy signal"
    )
    threshold_moderate_buy: float = Field(
        default=0.1, ge=0.0, le=1.0, description="OFI threshold for moderate buy signal"
    )
    threshold_strong_sell: float = Field(
        default=-0.3, ge=-1.0, le=0.0, description="OFI threshold for strong sell signal"
    )
    threshold_moderate_sell: float = Field(
        default=-0.1, ge=-1.0, le=0.0, description="OFI threshold for moderate sell signal"
    )

    # Model signal conversion (ofi_predictor.py lines 208-211)
    model_return_threshold: float = Field(
        default=0.001, ge=0.0, le=0.1, description="Return threshold for model signal"
    )
    model_signal_multiplier: int = Field(
        default=1000, ge=1, le=10000, description="Multiplier for converting return to signal"
    )

    # Momentum calculation windows (ofi_predictor.py lines 232, 236-237)
    momentum_min_samples: int = Field(
        default=5, ge=2, le=20, description="Minimum samples for momentum calculation"
    )
    momentum_recent_window: int = Field(
        default=3, ge=1, le=10, description="Recent window for momentum calculation"
    )
    momentum_previous_window: int = Field(
        default=10, ge=2, le=20, description="Previous window for momentum calculation"
    )

    # Momentum signal thresholds (ofi_predictor.py lines 242-249)
    momentum_strong: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Strong momentum threshold"
    )
    momentum_moderate: float = Field(
        default=0.05, ge=0.0, le=1.0, description="Moderate momentum threshold"
    )
    momentum_strong_negative: float = Field(
        default=-0.1, ge=-1.0, le=0.0, description="Strong negative momentum threshold"
    )
    momentum_moderate_negative: float = Field(
        default=-0.05, ge=-1.0, le=0.0, description="Moderate negative momentum threshold"
    )

    # Signal combination weights (ofi_predictor.py line 271)
    weight_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Weight for threshold signal"
    )
    weight_model: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Weight for model signal"
    )
    weight_momentum: float = Field(
        default=0.2, ge=0.0, le=1.0, description="Weight for momentum signal"
    )

    # Direction thresholds (ofi_predictor.py lines 283, 285)
    direction_up_threshold: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Combined signal threshold for up direction"
    )
    direction_down_threshold: float = Field(
        default=-0.3, ge=-1.0, le=0.0, description="Combined signal threshold for down direction"
    )

    # Confidence calculation (ofi_predictor.py lines 291, 530, 537)
    confidence_max: float = Field(
        default=1.0, ge=0.1, le=1.0, description="Maximum confidence value"
    )
    fallback_confidence_multiplier: float = Field(
        default=2.0, ge=0.1, le=10.0, description="Multiplier for fallback confidence calculation"
    )

    # Expected move calculation (ofi_predictor.py lines 336, 339, 342)
    expected_return_multiplier: int = Field(
        default=100, ge=1, le=1000, description="Multiplier for expected return calculation"
    )
    expected_bps_multiplier: int = Field(
        default=100, ge=1, le=1000, description="Multiplier to convert to basis points"
    )
    expected_bps_max: int = Field(
        default=500, ge=10, le=5000, description="Maximum expected move in bps"
    )
    expected_bps_min: int = Field(
        default=-500, ge=-5000, le=-10, description="Minimum expected move in bps"
    )

    # Horizon strings (ofi_predictor.py lines 362-364)
    horizon_short: str = Field(
        default="5m", description="Short horizon string"
    )
    horizon_medium: str = Field(
        default="15m", description="Medium horizon string"
    )
    horizon_long: str = Field(
        default="60m", description="Long horizon string"
    )

    # Training parameters (ofi_predictor.py lines 396, 421)
    min_training_samples: int = Field(
        default=10, ge=5, le=100, description="Minimum samples for model training"
    )
    logistic_random_state: int = Field(
        default=42, ge=1, le=1000, description="Random state for logistic regression"
    )

    # Prediction intervals (ofi_predictor.py lines 540, 563)
    default_confidence_level: float = Field(
        default=0.95, ge=0.5, le=0.99, description="Default confidence level for prediction intervals"
    )
    prediction_std_error_ratio: float = Field(
        default=0.5, ge=0.1, le=2.0, description="Ratio for std error estimation in prediction intervals"
    )

    # Regime detection parameters (ofi_predictor.py lines 607-640)
    regime_window_multiplier: int = Field(
        default=2, ge=1, le=5, description="Window multiplier for regime detection"
    )
    regime_shift_epsilon: float = Field(
        default=0.01, ge=0.001, le=0.1, description="Epsilon for regime shift calculation"
    )
    regime_mean_shift_threshold: float = Field(
        default=0.5, ge=0.1, le=2.0, description="Threshold for mean shift detection"
    )
    regime_vol_shift_threshold: float = Field(
        default=0.5, ge=0.1, le=2.0, description="Threshold for volatility shift detection"
    )
    regime_bullish_threshold: float = Field(
        default=0.2, ge=0.0, le=1.0, description="Mean OFI threshold for bullish regime"
    )
    regime_bearish_threshold: float = Field(
        default=-0.2, ge=-1.0, le=0.0, description="Mean OFI threshold for bearish regime"
    )
    regime_neutral_positive: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Positive threshold for neutral regime"
    )
    regime_neutral_negative: float = Field(
        default=-0.1, ge=-1.0, le=0.0, description="Negative threshold for neutral regime"
    )

    @field_validator("ofi_threshold_sell")
    @classmethod
    def sell_threshold_must_be_negative(cls, v: float) -> float:
        """Ensure sell threshold is negative or zero."""
        if v > 0:
            raise ValueError("ofi_threshold_sell must be <= 0")
        return v

    @field_validator("ofi_min_value")
    @classmethod
    def ofi_min_must_be_negative_or_zero(cls, v: float) -> float:
        """Ensure OFI min value is negative or zero."""
        if v > 0:
            raise ValueError("ofi_min_value must be <= 0")
        return v

    @field_validator("regime_bearish_mean_threshold")
    @classmethod
    def bearish_threshold_must_be_negative(cls, v: float) -> float:
        """Ensure bearish threshold is negative or zero."""
        if v > 0:
            raise ValueError("regime_bearish_mean_threshold must be <= 0")
        return v


class OFISignalConfig(BaseModel):
    """
    Configuration for OFI signal generation.

    Attributes:
        buy_threshold: OFI threshold for buy signals
        sell_threshold: OFI threshold for sell signals
        confidence_scale: Scale factor for confidence
        min_confidence: Minimum confidence to emit signal
        signal_horizon: Default signal horizon
        enable_mean_reversion: Enable mean reversion signals
        mean_reversion_threshold: Threshold for mean reversion
        enable_momentum: Enable momentum signals
        momentum_window: Window for momentum calculation
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    buy_threshold: float = Field(default=0.2, ge=0.0, le=1.0, description="Buy threshold")
    sell_threshold: float = Field(default=-0.2, ge=-1.0, le=0.0, description="Sell threshold")
    confidence_scale: float = Field(default=0.5, ge=0.01, le=1.0, description="Confidence scale")
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum confidence")
    signal_horizon: OFIHorizon = Field(default=OFIHorizon.SHORT, description="Signal horizon")
    enable_mean_reversion: bool = Field(default=True, description="Enable mean reversion signals")
    mean_reversion_threshold: float = Field(
        default=2.0, ge=0.1, description="Mean reversion threshold (std devs)"
    )
    enable_momentum: bool = Field(default=True, description="Enable momentum signals")
    momentum_window: int = Field(default=10, ge=2, le=50, description="Momentum window")

    @field_validator("sell_threshold")
    @classmethod
    def sell_threshold_must_be_negative(cls, v: float) -> float:
        """Ensure sell threshold is negative or zero."""
        if v > 0:
            raise ValueError("sell_threshold must be <= 0")
        return v


class OFIPrediction(BaseModel):
    """
    OFI-based price movement prediction.

    Attributes:
        symbol: Trading symbol
        timestamp: Prediction timestamp
        current_ofi: Current OFI value
        predicted_direction: Predicted direction (up/down/neutral)
        confidence: Confidence score (0-1)
        expected_move_bps: Expected price move in basis points
        prediction_horizon: Prediction horizon (e.g., "1m", "5m", "15m")
        model_used: Model type used for prediction
        features: Dictionary of features used in prediction
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    symbol: str = Field(..., description="Trading symbol")
    timestamp: datetime = Field(..., description="Prediction timestamp")
    current_ofi: float = Field(..., ge=-1.0, le=1.0, description="Current OFI value")
    predicted_direction: str = Field(..., description="Predicted direction (up/down/neutral)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    expected_move_bps: Decimal = Field(..., description="Expected price move in bps")
    prediction_horizon: str = Field(..., description="Prediction horizon (e.g., '1m', '5m')")
    model_used: str = Field(default="linear", description="Model used")
    features: dict = Field(default_factory=dict, description="Features used")

    @field_validator("predicted_direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        """Validate direction."""
        valid = {"up", "down", "neutral"}
        if v.lower() not in valid:
            raise ValueError(f"predicted_direction must be one of {valid}")
        return v.lower()

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "current_ofi": self.current_ofi,
            "predicted_direction": self.predicted_direction,
            "confidence": self.confidence,
            "expected_move_bps": str(self.expected_move_bps),
            "prediction_horizon": self.prediction_horizon,
            "model_used": self.model_used,
            "features": self.features,
        }


class OFISignal(BaseModel):
    """
    OFI-based trading signal.

    Attributes:
        symbol: Trading symbol
        timestamp: Signal timestamp
        action: Action (BUY/SELL/HOLD)
        ofi_value: OFI value that generated signal
        ofi_threshold_used: Threshold used for signal generation
        confidence: Signal confidence (0-1)
        expected_horizon: Expected holding period
        reasoning: Human-readable reasoning for signal
        prediction: Associated prediction (if available)
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    symbol: str = Field(..., description="Trading symbol")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Signal time"
    )
    action: str = Field(..., description="Action (BUY/SELL/HOLD)")
    ofi_value: float = Field(..., ge=-1.0, le=1.0, description="OFI value")
    ofi_threshold_used: float = Field(..., description="Threshold used for signal")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence")
    expected_horizon: str = Field(..., description="Expected horizon")
    reasoning: str = Field(..., description="Signal reasoning")
    prediction: OFIPrediction | None = Field(default=None, description="Associated prediction")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Validate action."""
        valid = {"BUY", "SELL", "HOLD"}
        if v.upper() not in valid:
            raise ValueError(f"action must be one of {valid}")
        return v.upper()

    def is_tradeable(self) -> bool:
        """Check if signal is tradeable (not HOLD)."""
        return self.action in ("BUY", "SELL")

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        result = {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "ofi_value": self.ofi_value,
            "ofi_threshold_used": self.ofi_threshold_used,
            "confidence": self.confidence,
            "expected_horizon": self.expected_horizon,
            "reasoning": self.reasoning,
        }
        if self.prediction:
            result["prediction"] = self.prediction.to_dict()
        return result


@dataclass(frozen=True)
class CumulativeOFI:
    """
    Cumulative OFI (COFI) tracker.

    COFI is the running sum of OFI values, useful for identifying
    sustained buying/selling pressure.

    Attributes:
        symbol: Trading symbol
        start_time: Start time of tracking
        current_cofi: Current cumulative OFI value
        history: List of (timestamp, cofi_value) tuples
        max_cofi: Maximum COFI observed
        min_cofi: Minimum COFI observed
        mean_cofi: Mean COFI value
        std_cofi: Standard deviation of COFI

    Example:
        >>> cofi_tracker = CumulativeOFI('AAPL', datetime.now())
        >>> cofi_tracker = cofi_tracker.update(0.15, datetime.now())
        >>> print(f"Current COFI: {cofi_tracker.current_cofi}")
        >>> print(f"Z-score: {cofi_tracker.z_score}")
    """

    symbol: str
    start_time: datetime
    current_cofi: float = 0.0
    history: tuple[tuple[datetime, float], ...] = ()
    max_cofi: float = 0.0
    min_cofi: float = 0.0
    mean_cofi: float = 0.0
    std_cofi: float = 0.0

    def __post_init__(self):
        """Initialize history if not provided."""
        # Convert to tuple if list was passed for frozen dataclass
        if isinstance(self.history, list):
            object.__setattr__(self, 'history', tuple(self.history))

    def update(self, ofi_value: float, timestamp: datetime) -> "CumulativeOFI":
        """
        Update COFI with new OFI value.

        Args:
            ofi_value: New OFI value to add
            timestamp: Timestamp of this update

        Returns:
            New CumulativeOFI instance with updated values
        """
        new_cofi = self.current_cofi + ofi_value
        new_history = self.history + ((timestamp, new_cofi),)

        # Update statistics
        new_max = max(self.max_cofi, new_cofi)
        new_min = min(self.min_cofi, new_cofi)

        if len(new_history) > 1:
            cofi_values = [v for _, v in new_history]
            new_mean = float(np.mean(cofi_values))
            new_std = float(np.std(cofi_values))
        else:
            new_mean = self.mean_cofi
            new_std = self.std_cofi

        return CumulativeOFI(
            symbol=self.symbol,
            start_time=self.start_time,
            current_cofi=new_cofi,
            history=new_history,
            max_cofi=new_max,
            min_cofi=new_min,
            mean_cofi=new_mean,
            std_cofi=new_std,
        )

    def z_score(self) -> float | None:
        """
        Calculate z-score of current COFI.

        Returns None if std_cofi is 0.
        """
        if self.std_cofi == 0:
            return None
        return (self.current_cofi - self.mean_cofi) / self.std_cofi

    def is_extreme_high(self, threshold: float = 2.0) -> bool:
        """Check if COFI is extremely high (mean reversion signal)."""
        z = self.z_score()
        return z is not None and z > threshold

    def is_extreme_low(self, threshold: float = 2.0) -> bool:
        """Check if COFI is extremely low (mean reversion signal)."""
        z = self.z_score()
        return z is not None and z < -threshold

    def reset(self, new_start_time: datetime) -> "CumulativeOFI":
        """
        Reset COFI tracking.

        Args:
            new_start_time: New start time for tracking

        Returns:
            New CumulativeOFI instance with reset values
        """
        return CumulativeOFI(
            symbol=self.symbol,
            start_time=new_start_time,
            current_cofi=0.0,
            history=(),
            max_cofi=0.0,
            min_cofi=0.0,
            mean_cofi=0.0,
            std_cofi=0.0,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "symbol": self.symbol,
            "start_time": self.start_time.isoformat(),
            "current_cofi": self.current_cofi,
            "max_cofi": self.max_cofi,
            "min_cofi": self.min_cofi,
            "mean_cofi": self.mean_cofi,
            "std_cofi": self.std_cofi,
            "z_score": self.z_score,
            "history_length": len(self.history),
        }


@dataclass
class OFIStatistics:
    """
    OFI statistics for a symbol over a period.

    Attributes:
        symbol: Trading symbol
        period_start: Start of period
        period_end: End of period
        mean_ofi: Mean OFI value
        std_ofi: Standard deviation of OFI
        max_ofi: Maximum OFI
        min_ofi: Minimum OFI
        median_ofi: Median OFI
        skewness: Skewness of OFI distribution
        kurtosis: Kurtosis of OFI distribution
        autocorr_1: Lag-1 autocorrelation
        predictive_power: Correlation with future returns
    """

    symbol: str
    period_start: datetime
    period_end: datetime
    mean_ofi: float
    std_ofi: float
    max_ofi: float
    min_ofi: float
    median_ofi: float
    skewness: float
    kurtosis: float
    autocorr_1: float
    predictive_power: float

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "symbol": self.symbol,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "mean_ofi": self.mean_ofi,
            "std_ofi": self.std_ofi,
            "max_ofi": self.max_ofi,
            "min_ofi": self.min_ofi,
            "median_ofi": self.median_ofi,
            "skewness": self.skewness,
            "kurtosis": self.kurtosis,
            "autocorr_1": self.autocorr_1,
            "predictive_power": self.predictive_power,
        }
