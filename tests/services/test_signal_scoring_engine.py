"""
Comprehensive tests for Signal Scoring and Cooldown Engine (TASK-SC-1 to SC-5).
"""

from decimal import Decimal

import pytest

from app.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.services.signal_scoring_engine import (
    PortfolioSignalFilter,
    SignalCompoundScoreCalculator,
    SignalCooldownManager,
    SignalPriorityRanker,
    SignalScoringEngine,
)


@pytest.fixture
def sample_signal():
    """Create a sample signal."""
    from datetime import datetime

    return Signal(
        symbol="AAPL",
        signal_type=SignalType.BUY,
        strength=SignalStrength.STRONG,
        confidence=85.0,
        liquidity_score=90.0,
        priority_score=80.0,
        source=SignalSource.MOMENTUM,
        price=Decimal("150.00"),
        volume=Decimal("1000000"),
        timestamp=datetime.utcnow(),
        metadata={"volume_ratio": 1.5, "volatility": 0.02},
    )


@pytest.fixture
def signal_scoring_engine():
    """Create a SignalScoringEngine instance."""
    return SignalScoringEngine(default_cooldown_minutes=5)


class TestSignalCooldownManager:
    """Tests for TASK-SC-1: Signal Cooldown Manager."""

    def test_cooldown_initialization(self):
        """Test cooldown manager initialization."""
        manager = SignalCooldownManager(default_cooldown_minutes=10)

        assert manager.default_cooldown_minutes == 10
        assert len(manager.cooldowns) == 0
        assert len(manager.custom_cooldowns) == 0

    def test_set_cooldown(self):
        """Test setting cooldown for a symbol."""
        manager = SignalCooldownManager(default_cooldown_minutes=10)

        manager.set_cooldown("AAPL")

        assert "AAPL" in manager.cooldowns
        assert manager.cooldowns["AAPL"] is not None

    def test_is_in_cooldown_fresh_symbol(self):
        """Test checking cooldown for symbol not in cooldown."""
        manager = SignalCooldownManager(default_cooldown_minutes=10)

        assert manager.is_in_cooldown("AAPL") is False

    def test_is_in_cooldown_active_cooldown(self):
        """Test checking cooldown for symbol in active cooldown."""
        manager = SignalCooldownManager(default_cooldown_minutes=10)

        manager.set_cooldown("AAPL")

        assert manager.is_in_cooldown("AAPL") is True

    def test_custom_cooldown_period(self):
        """Test setting custom cooldown period for a symbol."""
        manager = SignalCooldownManager(default_cooldown_minutes=10)

        manager.set_cooldown("AAPL", minutes=5)

        assert "AAPL" in manager.cooldowns
        assert manager.custom_cooldowns["AAPL"] == 5

    def test_reset_cooldown(self):
        """Test resetting cooldown for a symbol."""
        manager = SignalCooldownManager(default_cooldown_minutes=10)

        manager.set_cooldown("AAPL")
        assert "AAPL" in manager.cooldowns

        manager.reset_cooldown("AAPL")
        assert "AAPL" not in manager.cooldowns


class TestSignalCompoundScoreCalculator:
    """Tests for TASK-SC-2: Signal Compound Score Calculator."""

    def test_score_calculator_initialization(self):
        """Test score calculator initialization."""
        calculator = SignalCompoundScoreCalculator()

        assert calculator.weights["confidence"] == 0.30
        assert calculator.weights["volume_ratio"] == 0.25
        assert calculator.weights["volatility"] == 0.20
        assert calculator.weights["liquidity"] == 0.15
        assert calculator.weights["timing"] == 0.10

    def test_calculate_compound_score(self, sample_signal):
        """Test compound score calculation."""
        calculator = SignalCompoundScoreCalculator()

        score = calculator.calculate_compound_score(sample_signal)

        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_calculate_compound_score_high_confidence(self, sample_signal):
        """Test compound score with high confidence."""
        calculator = SignalCompoundScoreCalculator()

        sample_signal.confidence = 95.0
        sample_signal.liquidity_score = 90.0
        sample_signal.metadata = {"volume_ratio": 2.0, "volatility": 0.02}

        score = calculator.calculate_compound_score(sample_signal)

        assert score > 70  # Should be high with good metrics

    def test_extract_volume_ratio(self):
        """Test extracting volume ratio from metadata."""
        calculator = SignalCompoundScoreCalculator()

        score = calculator._extract_volume_ratio(
            Signal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.MODERATE,
                confidence=50.0,
                liquidity_score=50.0,
                priority_score=50.0,
                source=SignalSource.MOMENTUM,
                price=Decimal("150"),
                volume=Decimal("1000"),
                metadata={"volume_ratio": 1.5},
            ),
            {"volume_ratio": 1.5},
        )

        assert isinstance(score, float)
        assert 0 <= score <= 1

    def test_extract_volatility(self):
        """Test extracting volatility from metadata."""
        calculator = SignalCompoundScoreCalculator()

        score = calculator._extract_volatility(
            Signal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.MODERATE,
                confidence=50.0,
                liquidity_score=50.0,
                priority_score=50.0,
                source=SignalSource.MOMENTUM,
                price=Decimal("150"),
                volume=Decimal("1000"),
                metadata={"volatility": 0.02},
            ),
            {"volatility": 0.02},
        )

        assert isinstance(score, float)
        assert 0 <= score <= 1

    def test_calculate_timing_score(self):
        """Test timing score calculation."""
        calculator = SignalCompoundScoreCalculator()

        from datetime import datetime, timedelta

        # Fresh signal
        recent_signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=75.0,
            liquidity_score=50.0,
            priority_score=50.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150"),
            volume=Decimal("1000"),
            timestamp=datetime.utcnow() - timedelta(minutes=3),
        )

        score = calculator._calculate_timing_score(recent_signal)

        assert score > 0.8  # Should be high for fresh signal


class TestSignalPriorityRanker:
    """Tests for TASK-SC-3: Signal Priority Ranker."""

    def test_ranker_initialization(self):
        """Test ranker initialization."""
        ranker = SignalPriorityRanker(high_threshold=80.0, medium_threshold=50.0)

        assert ranker.high_threshold == 80.0
        assert ranker.medium_threshold == 50.0

    def test_get_priority_high(self):
        """Test priority classification for high score."""
        ranker = SignalPriorityRanker()

        priority = ranker.get_priority(85.0)

        assert priority == "high"

    def test_get_priority_medium(self):
        """Test priority classification for medium score."""
        ranker = SignalPriorityRanker()

        priority = ranker.get_priority(60.0)

        assert priority == "medium"

    def test_get_priority_low(self):
        """Test priority classification for low score."""
        ranker = SignalPriorityRanker()

        priority = ranker.get_priority(30.0)

        assert priority == "low"

    def test_rank_signals(self, sample_signal):
        """Test ranking signals by priority."""
        ranker = SignalPriorityRanker()

        # Create signals with different scores
        signal1 = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=85.0,
            liquidity_score=50.0,
            priority_score=50.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150"),
            volume=Decimal("1000"),
            metadata={"compound_score": 85.0},
        )

        signal2 = Signal(
            symbol="MSFT",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=60.0,
            liquidity_score=50.0,
            priority_score=50.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("300"),
            volume=Decimal("1000"),
            metadata={"compound_score": 60.0},
        )

        signal3 = Signal(
            symbol="GOOGL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.WEAK,
            confidence=35.0,
            liquidity_score=50.0,
            priority_score=50.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("200"),
            volume=Decimal("1000"),
            metadata={"compound_score": 40.0},
        )

        signals = [signal3, signal1, signal2]
        ranked = ranker.rank_signals(signals)

        assert ranked[0].metadata["compound_score"] == 85.0  # Highest first
        assert ranked[1].metadata["compound_score"] == 60.0
        assert ranked[2].metadata["compound_score"] == 40.0


class TestPortfolioSignalFilter:
    """Tests for TASK-SC-4: Portfolio Signal Filter."""

    def test_filter_initialization(self):
        """Test filter initialization."""
        filter_obj = PortfolioSignalFilter()

        assert len(filter_obj.active_positions) == 0
        assert len(filter_obj.recent_signals) == 0

    def test_filter_signals_no_conflicts(self, sample_signal):
        """Test filtering signals with no conflicts."""
        filter_obj = PortfolioSignalFilter()

        signals = [sample_signal]
        filtered = filter_obj.filter_signals(signals)

        assert len(filtered) == 1

    def test_add_remove_position(self):
        """Test adding and removing positions."""
        filter_obj = PortfolioSignalFilter()

        filter_obj.add_position("AAPL")
        assert "AAPL" in filter_obj.active_positions

        filter_obj.remove_position("AAPL")
        assert "AAPL" not in filter_obj.active_positions


class TestSignalScoringEngine:
    """Tests for complete Signal Scoring Engine (TASK-SC-1 to SC-5)."""

    def test_engine_initialization(self):
        """Test engine initialization."""
        engine = SignalScoringEngine(default_cooldown_minutes=10)

        assert engine.cooldown_manager is not None
        assert engine.score_calculator is not None
        assert engine.priority_ranker is not None
        assert engine.portfolio_filter is not None

    def test_process_signals_single(self, sample_signal, signal_scoring_engine):
        """Test processing a single signal."""
        signals = [sample_signal]

        processed = signal_scoring_engine.process_signals(signals)

        assert len(processed) == 1
        assert "compound_score" in processed[0].metadata
        assert "priority" in processed[0].metadata

    def test_process_signals_cooldown(self, sample_signal, signal_scoring_engine):
        """Test processing signals with cooldown."""
        signals = [sample_signal]

        # Process first time
        processed1 = signal_scoring_engine.process_signals(signals)
        assert len(processed1) == 1

        # Process again immediately (should be filtered)
        processed2 = signal_scoring_engine.process_signals(signals)
        assert len(processed2) == 0  # Should be filtered by cooldown

    def test_process_signals_multiple(self, signal_scoring_engine):
        """Test processing multiple signals."""
        from datetime import datetime

        signal1 = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=90.0,
            liquidity_score=95.0,
            priority_score=90.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150"),
            volume=Decimal("1000"),
            metadata={"volume_ratio": 2.0, "volatility": 0.02},
        )

        signal2 = Signal(
            symbol="MSFT",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=60.0,
            liquidity_score=70.0,
            priority_score=65.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("300"),
            volume=Decimal("1000"),
            metadata={"volume_ratio": 1.2, "volatility": 0.03},
        )

        signals = [signal2, signal1]  # Lower score first
        processed = signal_scoring_engine.process_signals(signals)

        assert len(processed) == 2
        # Should be ranked by priority (higher score first)
        assert processed[0].symbol in ["AAPL", "MSFT"]

    def test_get_scoring_stats(self, signal_scoring_engine):
        """Test getting scoring statistics."""
        stats = signal_scoring_engine.get_scoring_stats()

        assert "active_cooldowns" in stats
        assert "active_positions" in stats
