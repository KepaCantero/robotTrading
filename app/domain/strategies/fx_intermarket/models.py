"""
FX Intermarket Models.

Data models for the FX Intermarket strategy analyzing correlations
between FX pairs and external asset classes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class AssetClass(str, Enum):
    """External asset classes for intermarket analysis."""

    EQUITY = "equity"
    BOND = "bond"
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
    RISK_ON_OFF = "risk_on_off"
    LEADING_INDICATOR = "leading_indicator"
    LAGGING_INDICATOR = "lagging_indicator"


@dataclass
class FXCorrelationPair:
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
    p_value: Decimal
    lookback_days: int
    calculated_at: datetime | None = None

    @property
    def is_significant(self) -> bool:
        """Check if correlation is statistically significant (p < 0.05)."""
        return self.p_value < Decimal("0.05")

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


@dataclass
class IntermarketRelationship:
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
    significance: Decimal
    lookback_days: int
    last_updated: datetime | None = None

    @property
    def is_actionable(self) -> bool:
        """Check if relationship is strong enough for trading."""
        return abs(self.correlation) >= Decimal("0.5") and self.significance >= Decimal("70")


@dataclass
class IntermarketSignal:
    """
    Trading signal generated from intermarket analysis.

    Attributes:
        fx_pair: Target FX pair
        trigger_asset: Asset that triggered the signal
        signal_type: Type of signal (buy/sell/neutral)
        expected_move: Expected FX move (as decimal)
        confidence: Signal confidence (0-100)
        relationship: Relationship that generated signal
        trigger_move: Move in trigger asset
        timestamp: When signal was generated
        expiry: When signal expires
    """

    fx_pair: str
    trigger_asset: str
    signal_type: str  # "BUY", "SELL", "NEUTRAL"
    expected_move: Decimal
    confidence: Decimal
    relationship: IntermarketRelationship
    trigger_move: Decimal
    timestamp: datetime
    expiry: datetime | None = None

    @property
    def is_valid(self) -> bool:
        """Check if signal is still valid."""
        if self.expiry is None:
            return True
        return datetime.utcnow() < self.expiry

    @property
    def strength(self) -> str:
        """Return signal strength."""
        if self.confidence >= 80:
            return "STRONG"
        if self.confidence >= 60:
            return "MODERATE"
        if self.confidence >= 40:
            return "WEAK"
        return "NEGLIGIBLE"


@dataclass
class FXIntermarketConfig:
    """
    Configuration for FX Intermarket strategy.

    Attributes:
        correlation_lookback: Days for correlation calculation
        min_correlation: Minimum absolute correlation for relationship
        min_significance: Minimum significance score (0-100)
        signal_threshold: Minimum expected move to generate signal
        max_relationships: Maximum tracked relationships per pair
        update_frequency: How often to recalculate (hours)
        monitored_assets: Assets to monitor by class
    """

    correlation_lookback: int = 60
    min_correlation: Decimal = Decimal("0.6")
    min_significance: Decimal = Decimal("70")
    signal_threshold: Decimal = Decimal("0.005")
    max_relationships: int = 10
    update_frequency: int = 24
    monitored_assets: dict[AssetClass, list[str]] = field(
        default_factory=lambda: {
            AssetClass.EQUITY: ["SPX", "NDX", "DAX", "NKY"],
            AssetClass.COMMODITY: ["XAU", "XAG", "OIL", "GAS"],
            AssetClass.BOND: ["US10Y", "DE10Y", "JP10Y"],
            AssetClass.VOLATILITY: ["VIX"],
        }
    )
