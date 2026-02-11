"""
Data Models for FX Intermarket Strategy.

This module defines data models for FX intermarket analysis including:
- Asset class enumeration for external markets
- Relationship types for intermarket correlations
- FX correlation pairs with statistical metrics
- Intermarket relationships with beta and significance
- Intermarket signals for trading
- Strategy configuration

References:
    Ilmanen, Antti. "Expected Returns: An Investor's Guide"
    Chapter on currency markets and intermarket relationships
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AssetClass(str, Enum):
    """
    Asset class enumeration for external markets.

    Defines the major asset classes that can have intermarket
    relationships with FX pairs.

    Attributes:
        EQUITY: Stock market indices and equities
        FIXED_INCOME: Bonds and interest rate instruments
        COMMODITY: Physical commodities (gold, oil, etc.)
        CURRENCY: Other currency pairs
        CRYPTO: Cryptocurrency assets

    Examples:
        >>> asset = AssetClass.EQUITY
        >>> print(asset.value)
        equity
    """

    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    COMMODITY = "commodity"
    CURRENCY = "currency"
    CRYPTO = "crypto"


class RelationshipType(str, Enum):
    """
    Types of intermarket relationships.

    Defines the various ways FX pairs can correlate with external assets.

    Attributes:
        POSITIVE_CORRELATION: Assets move in same direction
        NEGATIVE_CORRELATION: Assets move in opposite directions
        SAFE_HAVEN: FX appreciates when risk assets decline
        COMMODITY_LINK: Commodity-exporter currencies track commodities
        CARRY_TRADE: High-yield currencies correlate with risk assets
        YIELD_DIFFERENTIAL: Interest rate differential drives movement

    Examples:
        >>> rel = RelationshipType.SAFE_HAVEN
        >>> print(rel.value)
        safe_haven
    """

    POSITIVE_CORRELATION = "positive_correlation"
    NEGATIVE_CORRELATION = "negative_correlation"
    SAFE_HAVEN = "safe_haven"
    COMMODITY_LINK = "commodity_link"
    CARRY_TRADE = "carry_trade"
    YIELD_DIFFERENTIAL = "yield_differential"


class FXCorrelationPair(BaseModel):
    """
    Correlation between two FX pairs.

    Stores statistical metrics for the correlation between two currency pairs.

    Attributes:
        pair1: First currency pair (e.g., "EUR/USD")
        pair2: Second currency pair (e.g., "GBP/USD")
        correlation: Pearson correlation coefficient (-1 to 1)
        p_value: Statistical significance of the correlation
        lookback_days: Number of days used for calculation
        last_updated: Timestamp of last calculation

    Raises:
        ValueError: If correlation is not between -1 and 1

    Examples:
        >>> corr = FXCorrelationPair(
        ...     pair1="EUR/USD",
        ...     pair2="GBP/USD",
        ...     correlation=Decimal("0.85"),
        ...     p_value=Decimal("0.001"),
        ...     lookback_days=60
        ... )
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    pair1: str = Field(..., description="First currency pair")
    pair2: str = Field(..., description="Second currency pair")
    correlation: Decimal = Field(..., description="Pearson correlation coefficient")
    p_value: Decimal = Field(..., ge=0, le=1, description="Statistical p-value")
    lookback_days: int = Field(..., gt=0, description="Lookback period in days")
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )

    @field_validator("correlation")
    @classmethod
    def validate_correlation(cls, v: Any) -> Decimal:
        """Validate correlation is between -1 and 1."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Correlation must be a number")

        if not Decimal("-1") <= v <= Decimal("1"):
            raise ValueError(f"Correlation must be between -1 and 1, got {v}")

        return v

    @property
    def is_significant(self) -> bool:
        """Check if correlation is statistically significant (p < 0.05)."""
        return self.p_value < Decimal("0.05")

    @property
    def is_strong(self) -> bool:
        """Check if correlation is strong (|correlation| > 0.7)."""
        return abs(self.correlation) > Decimal("0.7")

    @property
    def direction(self) -> str:
        """Get correlation direction."""
        if self.correlation > 0:
            return "positive"
        elif self.correlation < 0:
            return "negative"
        return "neutral"


class IntermarketRelationship(BaseModel):
    """
    Relationship between an FX pair and an external asset.

    Stores the correlation metrics and relationship characteristics
    between a currency pair and an external market asset.

    Attributes:
        fx_pair: Currency pair (e.g., "USD/JPY")
        external_asset: External asset symbol (e.g., "SPX", "GOLD")
        asset_class: Class of external asset
        relationship_type: Type of intermarket relationship
        correlation: Correlation coefficient
        beta: Beta coefficient (sensitivity to external asset)
        significance: Statistical significance (0-100)
        lookback_days: Lookback period for calculation
        last_tested: Timestamp of last correlation test

    Raises:
        ValueError: If validation fails

    Examples:
        >>> rel = IntermarketRelationship(
        ...     fx_pair="USD/JPY",
        ...     external_asset="SPX",
        ...     asset_class=AssetClass.EQUITY,
        ...     relationship_type=RelationshipType.SAFE_HAVEN,
        ...     correlation=Decimal("-0.75"),
        ...     beta=Decimal("-0.5"),
        ...     significance=95
        ... )
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    fx_pair: str = Field(..., description="FX currency pair")
    external_asset: str = Field(..., description="External asset symbol")
    asset_class: AssetClass = Field(..., description="Asset class")
    relationship_type: RelationshipType = Field(..., description="Type of relationship")
    correlation: Decimal = Field(..., description="Correlation coefficient")
    beta: Decimal = Field(..., description="Beta coefficient")
    significance: Decimal = Field(..., ge=0, le=100, description="Significance score (0-100)")
    lookback_days: int = Field(..., gt=0, description="Lookback period")
    last_tested: datetime = Field(
        default_factory=datetime.utcnow, description="Last test timestamp"
    )

    @field_validator("correlation")
    @classmethod
    def validate_correlation(cls, v: Any) -> Decimal:
        """Validate correlation is between -1 and 1."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Correlation must be a number")

        if not Decimal("-1") <= v <= Decimal("1"):
            raise ValueError(f"Correlation must be between -1 and 1, got {v}")

        return v

    @model_validator(mode="after")
    def validate_relationship_consistency(self) -> "IntermarketRelationship":
        """Validate relationship type matches correlation direction."""
        # Safe haven should have negative correlation with equities
        if self.relationship_type == RelationshipType.SAFE_HAVEN:
            if self.asset_class == AssetClass.EQUITY:
                if self.correlation >= 0:
                    raise ValueError(
                        f"Safe haven relationship with equities should have "
                        f"negative correlation, got {self.correlation}"
                    )

        # Commodity link should have positive correlation
        if self.relationship_type == RelationshipType.COMMODITY_LINK:
            if self.asset_class == AssetClass.COMMODITY:
                if self.correlation <= 0:
                    raise ValueError(
                        f"Commodity link should have positive correlation, "
                        f"got {self.correlation}"
                    )

        return self

    @property
    def is_active(self) -> bool:
        """Check if relationship is currently active (significance > threshold)."""
        from app.core.config.base import get_config
        cfg = get_config()
        min_significance = Decimal(str(getattr(cfg.trading, 'fx_intermarket_min_significance', 70)))
        return self.significance >= min_significance

    @property
    def strength(self) -> str:
        """Get relationship strength category."""
        from app.core.config.base import get_config
        cfg = get_config()
        abs_corr = abs(self.correlation)

        # Get correlation thresholds from config
        very_strong = Decimal(str(getattr(cfg.trading, 'fx_corr_very_strong', 0.8)))
        strong = Decimal(str(getattr(cfg.trading, 'fx_corr_strong', 0.6)))
        moderate = Decimal(str(getattr(cfg.trading, 'fx_corr_moderate', 0.4)))

        if abs_corr >= very_strong:
            return "very_strong"
        elif abs_corr >= strong:
            return "strong"
        elif abs_corr >= moderate:
            return "moderate"
        else:
            return "weak"


class IntermarketSignal(BaseModel):
    """
    Trading signal based on intermarket relationships.

    Represents a trading signal generated from intermarket analysis
    when a significant move in an external asset is detected.

    Attributes:
        fx_pair: Currency pair to trade
        signal_type: Type of signal (buy/sell)
        strength: Signal strength (0-100)
        trigger_asset: External asset that triggered the signal
        relationship_type: Type of relationship that generated signal
        expected_move: Expected move in FX pair (decimal)
        confidence: Signal confidence (0-100)
        timestamp: Signal generation time
        rationale: Explanation of the signal

    Raises:
        ValueError: If validation fails

    Examples:
        >>> signal = IntermarketSignal(
        ...     fx_pair="USD/JPY",
        ...     signal_type="buy",
        ...     strength=80,
        ...     trigger_asset="SPX",
        ...     relationship_type=RelationshipType.SAFE_HAVEN,
        ...     expected_move= getattr(config.trading, 'max_risk_per_trade', 0.02)"),
        ...     confidence=85
        ... )
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    fx_pair: str = Field(..., description="FX currency pair to trade")
    signal_type: str = Field(..., description="Signal type (buy/sell)")
    strength: Decimal = Field(..., ge=0, le=100, description="Signal strength (0-100)")
    trigger_asset: str = Field(..., description="Triggering external asset")
    relationship_type: RelationshipType = Field(..., description="Relationship type")
    expected_move: Decimal = Field(..., description="Expected price move (decimal)")
    confidence: Decimal = Field(..., ge=0, le=100, description="Confidence (0-100)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Signal timestamp")
    rationale: str = Field(..., description="Signal rationale")

    @model_validator(mode="after")
    def validate_signal_consistency(self) -> "IntermarketSignal":
        """Validate signal consistency."""
        from app.core.config.base import get_config
        cfg = get_config()

        # Get thresholds from config
        strong_signal_threshold = Decimal(str(getattr(cfg.trading, 'fx_signal_strong_threshold', 80)))
        min_confidence_for_strong = Decimal(str(getattr(cfg.trading, 'fx_signal_min_confidence_strong', 70)))
        max_expected_move = Decimal(str(getattr(cfg.trading, 'fx_signal_max_expected_move', 0.1)))
        min_actionable_confidence = Decimal(str(getattr(cfg.trading, 'fx_signal_min_actionable_confidence', 60)))

        # Strong signals should have high confidence
        if self.strength >= strong_signal_threshold:
            if self.confidence < min_confidence_for_strong:
                raise ValueError(
                    f"Strong signal (strength={self.strength}) requires "
                    f"confidence >= {min_confidence_for_strong}%, got {self.confidence}"
                )

        # Expected move should be reasonable
        if abs(self.expected_move) > max_expected_move:
            raise ValueError(f"Expected move seems unrealistic: {self.expected_move}")

        return self

    @property
    def is_buy(self) -> bool:
        """Check if signal is a buy signal."""
        return self.signal_type.lower() in ("buy", "long")

    @property
    def is_sell(self) -> bool:
        """Check if signal is a sell signal."""
        return self.signal_type.lower() in ("sell", "short")

    @property
    def is_actionable(self) -> bool:
        """Check if signal is actionable (confidence > threshold)."""
        from app.core.config.base import get_config
        cfg = get_config()
        min_confidence = Decimal(str(getattr(cfg.trading, 'fx_signal_min_actionable_confidence', 60)))
        return self.confidence > min_confidence


class FXIntermarketConfig(BaseModel):
    """
    Configuration for FX Intermarket strategy.

    Defines all configurable parameters for the intermarket strategy
    including correlation thresholds, signal generation, and risk management.

    Attributes:
        correlation_lookback: Lookback period for correlation calculation
        min_correlation: Minimum absolute correlation to consider
        min_significance: Minimum statistical significance (0-100)
        signal_threshold: Minimum signal strength to trade (0-100)
        min_signal_strength: Minimum strength for actionable signals (0-100)
        max_positions: Maximum concurrent positions
        stop_loss: Stop loss threshold (decimal)
        take_profit: Take profit threshold (decimal)
        position_size: Position size as fraction of capital
        monitored_pairs: List of FX pairs to monitor
        monitored_assets: Dictionary of external assets to monitor
        active_relationships: List of relationship types to use

    Raises:
        ValueError: If configuration is invalid

    Examples:
        >>> config = FXIntermarketConfig(
        ...     correlation_lookback=60,
        ...     min_correlation=Decimal("0.7"),
        ...     min_significance=80,
        ...     max_positions=5
        ... )
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    # Correlation parameters
    correlation_lookback: int = Field(
        default=60,
        ge=20,
        le=252,
        description="Lookback period for correlation (days)",
    )
    min_correlation: Decimal = Field(
        default=Decimal("0.6"),
        ge=Decimal("0.3"),
        le=Decimal("1.0"),
        description="Minimum absolute correlation",
    )
    min_significance: Decimal = Field(
        default=Decimal("70"),
        ge=Decimal("50"),
        le=Decimal("100"),
        description="Minimum significance score (0-100)",
    )

    # Signal parameters
    signal_threshold: Decimal = Field(
        default=Decimal("60"),
        ge=Decimal("50"),
        le=Decimal("100"),
        description="Signal threshold for trading (0-100)",
    )
    min_signal_strength: Decimal = Field(
        default=Decimal("65"),
        ge=Decimal("50"),
        le=Decimal("100"),
        description="Minimum signal strength (0-100)",
    )

    # Risk management
    max_positions: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum concurrent positions",
    )
    stop_loss: Decimal = Field(
        default=Decimal("0.03"),
        ge=Decimal("0.01"),
        le=Decimal("0.20"),
        description="Stop loss threshold (decimal)",
    )
    take_profit: Decimal = Field(
        default=Decimal("0.08"),
        ge=Decimal("0.02"),
        le=Decimal("0.50"),
        description="Take profit threshold (decimal)",
    )
    position_size: Decimal = Field(
        default=Decimal("0.1"),
        ge=Decimal("0.01"),
        le=Decimal("0.5"),
        description="Position size as fraction of capital",
    )

    # Monitored assets
    monitored_pairs: list[str] = Field(
        default_factory=lambda: [
            "EUR/USD",
            "GBP/USD",
            "USD/JPY",
            "USD/CHF",
            "AUD/USD",
            "NZD/USD",
            "USD/CAD",
        ],
        description="FX pairs to monitor",
    )
    monitored_assets: dict[str, AssetClass] = Field(
        default_factory=lambda: {
            "SPX": AssetClass.EQUITY,
            "US10Y": AssetClass.FIXED_INCOME,
            "GOLD": AssetClass.COMMODITY,
            "OIL": AssetClass.COMMODITY,
            "VIX": AssetClass.EQUITY,
        },
        description="External assets to monitor by class",
    )
    active_relationships: list[RelationshipType] = Field(
        default_factory=lambda: [
            RelationshipType.SAFE_HAVEN,
            RelationshipType.COMMODITY_LINK,
            RelationshipType.CARRY_TRADE,
        ],
        description="Active relationship types",
    )

    @model_validator(mode="after")
    def validate_risk_parameters(self) -> "FXIntermarketConfig":
        """Validate risk parameter relationships."""
        # Stop loss should be less than take profit
        if self.stop_loss >= self.take_profit:
            raise ValueError(
                f"Stop loss ({self.stop_loss}) must be less than "
                f"take profit ({self.take_profit})"
            )

        # Min correlation should be reasonable
        if self.min_correlation < Decimal("0.5"):
            raise ValueError(
                f"Min correlation too low ({self.min_correlation}). "
                f"Use at least 0.5 for meaningful relationships"
            )

        return self

    def get_fx_pairs(self) -> list[str]:
        """
        Get list of monitored FX pairs.

        Returns:
            List of FX pair symbols
        """
        return self.monitored_pairs.copy()

    def get_external_assets(self) -> dict[str, AssetClass]:
        """
        Get dictionary of monitored external assets.

        Returns:
            Dictionary mapping asset symbols to asset classes
        """
        return self.monitored_assets.copy()

    def get_active_relationship_types(self) -> list[RelationshipType]:
        """
        Get list of active relationship types.

        Returns:
            List of relationship types to use
        """
        return self.active_relationships.copy()

    def __str__(self) -> str:
        """Return string representation of configuration."""
        return (
            f"FXIntermarketConfig("
            f"lookback={self.correlation_lookback}, "
            f"min_corr={self.min_correlation}, "
            f"max_pos={self.max_positions}, "
            f"stop_loss={self.stop_loss:.2%})"
        )
