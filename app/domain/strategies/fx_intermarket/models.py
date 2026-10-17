"""
FX Intermarket Models.

Data models for the FX Intermarket strategy analyzing correlations
between FX pairs and external asset classes.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class AssetClass(str, Enum):
    """External asset classes for intermarket analysis."""

    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    COMMODITY = "commodity"
    CURRENCY = "currency"
    VOLATILITY = "volatility"
    CRYPTO = "crypto"
    REAL_ESTATE = "real_estate"


class RelationshipType(str, Enum):
    """Types of intermarket relationships."""

    POSITIVE_CORRELATION = "positive_correlation"
    NEGATIVE_CORRELATION = "negative_correlation"
    SAFE_HAVEN = "safe_haven"
    CARRY_TRADE = "carry_trade"
    COMMODITY_LINK = "commodity_link"
    YIELD_DIFFERENTIAL = "yield_differential"
    RISK_ON_OFF = "risk_on_off"
    LEADING_INDICATOR = "leading_indicator"
    LAGGING_INDICATOR = "lagging_indicator"


class FXCorrelationPair(BaseModel):
    """
    Correlation metrics between two FX pairs.

    Attributes:
        pair1: First currency pair symbol
        pair2: Second currency pair symbol
        correlation: Pearson correlation coefficient (-1 to 1)
        p_value: Statistical significance (lower is more significant)
        lookback_days: Number of days used in calculation
        calculated_at: When correlation was calculated
    """

    pair1: str
    pair2: str
    correlation: Decimal
    p_value: Decimal = Field(ge=0, le=1)
    lookback_days: int = Field(gt=0)
    calculated_at: datetime | None = None
    last_updated: datetime = Field(default_factory=datetime.now)

    @field_validator("correlation")
    @classmethod
    def _validate_correlation(cls, v: Decimal) -> Decimal:
        """La correlación debe estar en [-1, 1]."""
        if not Decimal("-1") <= v <= Decimal("1"):
            raise ValueError("Correlation must be between -1 and 1")
        return v

    @property
    def is_significant(self) -> bool:
        """Check if correlation is statistically significant (p < 0.05)."""
        return self.p_value < Decimal("0.05")

    @property
    def is_strong(self) -> bool:
        """Check if correlation is strong (abs >= 0.7)."""
        return abs(self.correlation) >= Decimal("0.75")

    @property
    def direction(self) -> str:
        """Return correlation direction."""
        if self.correlation > 0:
            return "positive"
        if self.correlation < 0:
            return "negative"
        return "neutral"

    @property
    def strength(self) -> str:
        """Return correlation strength as string."""
        abs_corr = abs(self.correlation)
        if abs_corr >= 0.8:
            return "VERY_STRONG"
        if abs_corr >= 0.6:
            return "STRONG"
        if abs_corr >= 0.4:
            return "MODERATE"
        if abs_corr >= 0.2:
            return "WEAK"
        return "NEGLIGIBLE"


class IntermarketRelationship(BaseModel):
    """
    Correlation relationship between FX pair and external asset.

    Attributes:
        fx_pair: FX pair symbol
        external_asset: External asset symbol
        asset_class: Class of the external asset
        relationship_type: Type of relationship
        correlation: Correlation coefficient
        beta: Sensitivity coefficient (FX response to asset move)
        significance: Significance score (0-100)
        lookback_days: Days used in calculation
        last_updated: When relationship was last calculated
    """

    fx_pair: str
    external_asset: str
    asset_class: AssetClass
    relationship_type: RelationshipType
    correlation: Decimal
    beta: Decimal
    significance: Decimal = Field(ge=0, le=100)
    lookback_days: int = Field(gt=0)
    last_updated: datetime = Field(default_factory=datetime.now)
    last_tested: datetime = Field(default_factory=datetime.now)

    @field_validator("correlation")
    @classmethod
    def _validate_correlation(cls, v: Decimal) -> Decimal:
        """La correlación debe estar en [-1, 1]."""
        if not Decimal("-1") <= v <= Decimal("1"):
            raise ValueError("Correlation must be between -1 and 1")
        return v

    @model_validator(mode="after")
    def _validate_safe_haven(self) -> "IntermarketRelationship":
        """Un refugio (safe haven) con acciones debe tener correlación negativa."""
        if (
            self.relationship_type == RelationshipType.SAFE_HAVEN
            and self.asset_class == AssetClass.EQUITY
            and self.correlation >= 0
        ):
            raise ValueError(
                "Safe haven relationship with equities should have negative correlation"
            )
        if (
            self.relationship_type == RelationshipType.COMMODITY_LINK
            and self.asset_class == AssetClass.COMMODITY
            and self.correlation <= 0
        ):
            raise ValueError("Commodity link should have positive correlation")
        return self

    @property
    def strength(self) -> str:
        """Return relationship strength label."""
        abs_corr = abs(self.correlation)
        if abs_corr >= Decimal("0.8"):
            return "very_strong"
        if abs_corr >= Decimal("0.6"):
            return "strong"
        if abs_corr >= Decimal("0.4"):
            return "moderate"
        return "weak"

    @property
    def is_actionable(self) -> bool:
        """Check if relationship is strong enough for trading."""
        return abs(self.correlation) >= Decimal("0.5") and self.significance >= Decimal("70")

    @property
    def is_active(self) -> bool:
        """Check if relationship is currently active (actionable and not stale)."""
        return self.is_actionable


class IntermarketSignal(BaseModel):
    """
    Trading signal generated from intermarket analysis.
    """

    fx_pair: str
    trigger_asset: str
    signal_type: str  # "BUY", "SELL", "NEUTRAL"
    expected_move: Decimal
    confidence: Decimal = Field(ge=0, le=100)
    strength: Decimal = Field(default=Decimal("50"), ge=0, le=100)
    relationship_type: RelationshipType = RelationshipType.POSITIVE_CORRELATION
    rationale: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    relationship: IntermarketRelationship | None = None
    trigger_move: Decimal | None = None
    expiry: datetime | None = None

    @model_validator(mode="after")
    def _validate_signal_sanity(self) -> "IntermarketSignal":
        """Señales fuertes exigen alta confianza; el move esperado debe ser realista."""
        if self.strength >= 80 and self.confidence < 70:
            raise ValueError("Strong signal (strength >= 80) requires confidence >= 70%")
        if self.expected_move is not None and abs(self.expected_move) > Decimal("0.10"):
            raise ValueError("Expected move seems unrealistic (|move| > 10%)")
        return self

    @property
    def is_valid(self) -> bool:
        """Check if signal is still valid."""
        if self.expiry is None:
            return True
        return datetime.utcnow() < self.expiry

    @property
    def is_actionable(self) -> bool:
        """Check if signal is actionable (valid, no neutral, confianza >= 60)."""
        return self.is_valid and self.signal_type.upper() != "NEUTRAL" and self.confidence > 60

    @property
    def is_buy(self) -> bool:
        """Check if this is a buy signal."""
        return self.signal_type.upper() in ("BUY", "LONG")

    @property
    def is_sell(self) -> bool:
        """Check if this is a sell signal."""
        return self.signal_type.upper() in ("SELL", "SHORT")


class FXIntermarketConfig(BaseModel):
    """
    Configuration for FX Intermarket strategy.

    Attributes:
        correlation_lookback: Days for correlation calculation
        min_correlation: Minimum absolute correlation for relationship
        min_significance: Minimum significance score (0-100)
        signal_threshold: Minimum confidence score to pass risk check (0-100)
        min_signal_strength: Minimum signal strength to generate signal (0-100)
        max_positions: Maximum number of concurrent positions
        max_relationships: Maximum tracked relationships per pair
        update_frequency: How often to recalculate (hours)
        stop_loss: Stop loss as decimal fraction (e.g. 0.03)
        take_profit: Take profit as decimal fraction (e.g. 0.08)
        position_size: Position size as decimal fraction (e.g. 0.1)
        monitored_assets: Assets to monitor by class
        monitored_pairs: FX pairs to monitor
    """

    correlation_lookback: int = Field(default=60, ge=20, le=252)
    min_correlation: Decimal = Field(default=Decimal("0.6"), le=Decimal("1.0"))
    min_significance: Decimal = Decimal("70")
    signal_threshold: Decimal = Decimal("60")
    min_signal_strength: Decimal = Decimal("65")
    max_positions: int = 5
    max_relationships: int = 10
    update_frequency: int = 24
    stop_loss: Decimal = Decimal("0.03")
    take_profit: Decimal = Decimal("0.08")
    position_size: Decimal = Decimal("0.1")
    monitored_assets: dict[str, AssetClass] = Field(
        default_factory=lambda: {
            "SPX": AssetClass.EQUITY,
            "US10Y": AssetClass.FIXED_INCOME,
            "GOLD": AssetClass.COMMODITY,
            "OIL": AssetClass.COMMODITY,
            "VIX": AssetClass.EQUITY,
        }
    )
    active_relationships: list[RelationshipType] = Field(
        default_factory=lambda: [
            RelationshipType.SAFE_HAVEN,
            RelationshipType.NEGATIVE_CORRELATION,
            RelationshipType.POSITIVE_CORRELATION,
            RelationshipType.COMMODITY_LINK,
            RelationshipType.RISK_ON_OFF,
            RelationshipType.CARRY_TRADE,
        ]
    )
    monitored_pairs: list[str] = Field(
        default_factory=lambda: [
            "EUR/USD",
            "GBP/USD",
            "USD/JPY",
            "USD/CHF",
            "AUD/USD",
            "NZD/USD",
            "USD/CAD",
        ]
    )

    @model_validator(mode="after")
    def _validate_config_sanity(self) -> "FXIntermarketConfig":
        """Stop loss < take profit; correlación mínima razonable."""
        if self.stop_loss >= self.take_profit:
            raise ValueError("Stop loss (in decimal) must be less than take profit")
        if self.min_correlation < Decimal("0.5"):
            raise ValueError("Min correlation too low. Use at least 0.5")
        return self

    def get_active_relationship_types(self) -> list[RelationshipType]:
        """Return a copy of the active relationship types."""
        return list(self.active_relationships)

    def __str__(self) -> str:
        return (
            f"FXIntermarketConfig(lookback={self.correlation_lookback}, "
            f"min_corr={self.min_correlation}, max_pos={self.max_positions}, "
            f"stop_loss={self.stop_loss * 100:.2f}%)"
        )

    def get_fx_pairs(self) -> list[str]:
        """Return list of monitored FX pairs."""
        return list(self.monitored_pairs)

    def get_external_assets(self) -> dict[str, AssetClass]:
        """Return dictionary mapping asset symbol to its asset class."""
        return dict(self.monitored_assets)
