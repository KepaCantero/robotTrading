"""Tests for the AlphaType → SignalSource mapping.

Guards against placeholder mappings: every alpha category that has a
same-named SignalSource must map to it, never to an unrelated value like
TECHNICAL (the bug this file was created for).
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.models.signal import SignalSource, SignalType
from app.domain.strategies.alpha_models import AlphaDecayRegime, AlphaSignal, AlphaType


def _signal(alpha_type: AlphaType) -> SignalSource:
    alpha = AlphaSignal(
        symbol="AAPL",
        alpha_type=alpha_type,
        direction=SignalType.BUY,
        raw_alpha=0.01,
        confidence=0.9,
        expected_return=100.0,
        holding_period_days=5,
        decay_regime=AlphaDecayRegime.NONE,
    )
    # Signal stores source as its plain string value; rebuild the enum
    return SignalSource(alpha.to_signal(price=Decimal("150")).source)


def test_sentiment_and_ml_map_to_their_own_sources() -> None:
    assert _signal(AlphaType.SENTIMENT) is SignalSource.SENTIMENT
    assert _signal(AlphaType.MACHINE_LEARNING) is SignalSource.MACHINE_LEARNING


def test_identity_mappings_stay_correct() -> None:
    assert _signal(AlphaType.MOMENTUM) is SignalSource.MOMENTUM
    assert _signal(AlphaType.MEAN_REVERSION) is SignalSource.MEAN_REVERSION
    assert _signal(AlphaType.FUNDAMENTAL) is SignalSource.FUNDAMENTAL
    assert _signal(AlphaType.STATISTICAL_ARBITRAGE) is SignalSource.ARBITRAGE


def test_new_signal_source_values_serialize_as_plain_strings() -> None:
    assert SignalSource.SENTIMENT.value == "sentiment"
    assert SignalSource.MACHINE_LEARNING.value == "machine_learning"
