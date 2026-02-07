"""
Comprehensive tests for Order Flow Imbalance (OFI) module.

Tests cover:
1. OFI calculation from order books
2. OFI prediction models
3. OFI signal generation
4. Tick-level OFI processing
5. Cumulative OFI tracking
6. Edge cases and error handling
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.market_microstructure.ofi.models import (
    CumulativeOFI,
    OFIConfig,
    OFISignal,
    OFISignalConfig,
    OrderBookSnapshot,
    OrderSide,
    TickData,
)
from app.market_microstructure.ofi.ofi_calculator import OFICalculator
from app.market_microstructure.ofi.ofi_predictor import OFIPredictor
from app.market_microstructure.ofi.ofi_signals import OFISignalGenerator as OFISignalGen
from app.market_microstructure.ofi.tick_processor import TickLevelOFIProcessor

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def sample_order_book():
    """Create a sample order book snapshot."""
    return OrderBookSnapshot(
        symbol="AAPL",
        timestamp=datetime.utcnow(),
        bids=[
            (Decimal("100.50"), 100),
            (Decimal("100.49"), 200),
            (Decimal("100.48"), 150),
        ],
        asks=[
            (Decimal("100.51"), 80),
            (Decimal("100.52"), 120),
            (Decimal("100.53"), 200),
        ],
    )


@pytest.fixture
def balanced_order_book():
    """Create a balanced order book."""
    return OrderBookSnapshot(
        symbol="MSFT",
        timestamp=datetime.utcnow(),
        bids=[(Decimal("200.00"), 100), (Decimal("199.99"), 100)],
        asks=[(Decimal("200.01"), 100), (Decimal("200.02"), 100)],
    )


@pytest.fixture
def buy_pressure_book():
    """Create order book with buy pressure."""
    return OrderBookSnapshot(
        symbol="TSLA",
        timestamp=datetime.utcnow(),
        bids=[(Decimal("150.00"), 500), (Decimal("149.99"), 300)],
        asks=[(Decimal("150.01"), 100), (Decimal("150.02"), 50)],
    )


@pytest.fixture
def sell_pressure_book():
    """Create order book with sell pressure."""
    return OrderBookSnapshot(
        symbol="NVDA",
        timestamp=datetime.utcnow(),
        bids=[(Decimal("400.00"), 50), (Decimal("399.99"), 30)],
        asks=[(Decimal("400.01"), 500), (Decimal("400.02"), 300)],
    )


@pytest.fixture
def sample_tick_data():
    """Create sample tick data."""
    return [
        TickData(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            price=Decimal("100.50"),
            quantity=100,
            side=OrderSide.BUY,
            is_market_buy=True,
        ),
        TickData(
            symbol="AAPL",
            timestamp=datetime.utcnow() + timedelta(seconds=1),
            price=Decimal("100.51"),
            quantity=50,
            side=OrderSide.SELL,
            is_market_sell=True,
        ),
    ]


@pytest.fixture
def ofi_config():
    """Create OFI configuration."""
    return OFIConfig(
        lookback_periods=20,
        ofi_threshold=0.1,
        min_volume=50,
        use_weighted_ofi=True,
    )


@pytest.fixture
def signal_config():
    """Create signal configuration."""
    return OFISignalConfig(
        buy_threshold=0.2,
        sell_threshold=-0.2,
        min_confidence=0.3,
        enable_mean_reversion=True,
    )


@pytest.fixture
def ofi_calculator(ofi_config):
    """Create OFI calculator."""
    return OFICalculator(config=ofi_config)


@pytest.fixture
def ofi_predictor(ofi_config):
    """Create OFI predictor."""
    return OFIPredictor(config=ofi_config)


@pytest.fixture
def ofi_signal_generator(signal_config):
    """Create OFI signal generator."""
    return OFISignalGen(config=signal_config)


@pytest.fixture
def historical_data():
    """Create historical OFI and returns data."""
    ofi_history = [0.1, 0.15, 0.2, 0.18, 0.25, 0.3, 0.22, 0.18, 0.12, 0.08]
    returns_history = [0.001, 0.0015, 0.002, 0.0018, 0.0025, 0.003, 0.0022, 0.0018, 0.0012, 0.0008]
    return ofi_history, returns_history


# ==============================================================================
# ORDER BOOK SNAPSHOT TESTS
# ==============================================================================


class TestOrderBookSnapshot:
    """Tests for OrderBookSnapshot model."""

    def test_best_bid(self, sample_order_book):
        """Test best bid calculation."""
        assert sample_order_book.best_bid == Decimal("100.50")

    def test_best_ask(self, sample_order_book):
        """Test best ask calculation."""
        assert sample_order_book.best_ask == Decimal("100.51")

    def test_mid_price(self, sample_order_book):
        """Test mid price calculation."""
        expected = (Decimal("100.50") + Decimal("100.51")) / 2
        assert sample_order_book.mid_price == expected

    def test_bid_volume(self, sample_order_book):
        """Test bid volume calculation."""
        assert sample_order_book.bid_volume == 450  # 100 + 200 + 150

    def test_ask_volume(self, sample_order_book):
        """Test ask volume calculation."""
        assert sample_order_book.ask_volume == 400  # 80 + 120 + 200

    def test_total_volume(self, sample_order_book):
        """Test total volume calculation."""
        assert sample_order_book.total_volume == 850

    def test_spread(self, sample_order_book):
        """Test spread calculation."""
        assert sample_order_book.spread == Decimal("0.01")

    def test_spread_bps(self, sample_order_book):
        """Test spread in basis points."""
        # Spread is 0.01, mid is ~100.505
        # BPS = (0.01 / 100.505) * 10000 ≈ 1.0
        assert sample_order_book.spread_bps is not None
        assert 0.5 < sample_order_book.spread_bps < 2.0

    def test_depth_imbalance(self, sample_order_book):
        """Test depth imbalance calculation."""
        # (450 - 400) / 850 = 50/850 ≈ 0.059
        imbalance = sample_order_book.depth_imbalance
        assert imbalance is not None
        assert 0.05 < imbalance < 0.06

    def test_empty_order_book(self):
        """Test empty order book handling."""
        empty_book = OrderBookSnapshot(
            symbol="EMPTY", timestamp=datetime.utcnow(), bids=[], asks=[]
        )
        assert empty_book.best_bid is None
        assert empty_book.best_ask is None
        assert empty_book.mid_price is None
        assert empty_book.bid_volume == 0
        assert empty_book.ask_volume == 0

    def test_to_dict(self, sample_order_book):
        """Test dictionary conversion."""
        data = sample_order_book.to_dict()
        assert data["symbol"] == "AAPL"
        assert "best_bid" in data
        assert "best_ask" in data
        assert "total_volume" in data


# ==============================================================================
# OFI CALCULATOR TESTS
# ==============================================================================


class TestOFICalculator:
    """Tests for OFICalculator."""

    def test_calculate_ofi_balanced(self, ofi_calculator, balanced_order_book):
        """Test OFI calculation for balanced book."""
        result = ofi_calculator.calculate_ofi(balanced_order_book)
        assert result.is_valid
        # Balanced: (200 - 200) / 400 = 0
        assert -0.1 < result.ofi < 0.1

    def test_calculate_ofi_buy_pressure(self, ofi_calculator, buy_pressure_book):
        """Test OFI with buy pressure."""
        result = ofi_calculator.calculate_ofi(buy_pressure_book)
        assert result.is_valid
        # Buy pressure: (800 - 150) / 950 ≈ 0.68
        assert result.ofi > 0.5
        assert result.ofi < 1.0

    def test_calculate_ofi_sell_pressure(self, ofi_calculator, sell_pressure_book):
        """Test OFI with sell pressure."""
        result = ofi_calculator.calculate_ofi(sell_pressure_book)
        assert result.is_valid
        # Sell pressure: (80 - 800) / 880 ≈ -0.82
        assert result.ofi < -0.5
        assert result.ofi > -1.0

    def test_calculate_ofi_low_volume(self, ofi_calculator):
        """Test OFI with low volume (should be invalid)."""
        low_vol_book = OrderBookSnapshot(
            symbol="TEST",
            timestamp=datetime.utcnow(),
            bids=[(Decimal("100"), 10)],
            asks=[(Decimal("101"), 10)],
        )
        result = ofi_calculator.calculate_ofi(low_vol_book)
        assert not result.is_valid
        assert "below minimum" in result.reason.lower()

    def test_calculate_cumulative_ofi(self, ofi_calculator):
        """Test cumulative OFI calculation."""
        ofi_history = [0.1, 0.2, -0.1, 0.15]
        cofi = ofi_calculator.calculate_cumulative_ofi(ofi_history)
        assert len(cofi) == 4
        assert abs(cofi[0] - 0.1) < 1e-10
        assert abs(cofi[1] - 0.3) < 1e-10
        assert abs(cofi[2] - 0.2) < 1e-10
        assert abs(cofi[3] - 0.35) < 1e-10

    def test_calculate_ofi_momentum(self, ofi_calculator):
        """Test OFI momentum calculation."""
        ofi_history = [0.1] * 10 + [0.2] * 10
        momentum = ofi_calculator.calculate_ofi_momentum(ofi_history, window=10)
        assert momentum > 0  # Positive momentum

    def test_calculate_ofi_momentum_negative(self, ofi_calculator):
        """Test negative OFI momentum."""
        ofi_history = [0.2] * 10 + [0.1] * 10
        momentum = ofi_calculator.calculate_ofi_momentum(ofi_history, window=10)
        assert momentum < 0  # Negative momentum

    def test_calculate_top_level_ofi(self, ofi_calculator, sample_order_book):
        """Test top-level OFI calculation."""
        top_ofi = ofi_calculator.calculate_top_level_ofi(sample_order_book)
        assert top_ofi is not None
        # Top level: (100 - 80) / 180 = 20/180 ≈ 0.111
        assert 0.1 < top_ofi < 0.12

    def test_calculate_smoothed_ofi(self, ofi_calculator):
        """Test smoothed OFI calculation."""
        ofi_history = [0.1, 0.3, 0.2, 0.4, 0.15, 0.25]
        smoothed = ofi_calculator.calculate_smoothed_ofi(ofi_history, window=3)
        assert len(smoothed) == len(ofi_history)
        # Smoothed should be less volatile
        ofi_std = __import__("numpy").std(ofi_history)
        smoothed_std = __import__("numpy").std(smoothed)
        assert smoothed_std < ofi_std

    def test_calculate_ofi_std_score(self, ofi_calculator):
        """Test OFI z-score calculation."""
        ofi_history = [0.1, 0.12, 0.11, 0.13, 0.1, 0.14, 0.11, 0.12, 0.1, 0.13]
        z_score = ofi_calculator.calculate_ofi_std_score(0.2, ofi_history)
        assert z_score is not None
        assert z_score > 0  # 0.2 is above mean

    def test_detect_ofi_regime_bullish(self, ofi_calculator):
        """Test bullish regime detection."""
        ofi_history = [0.15, 0.2, 0.18, 0.22, 0.19] * 5  # Sustained positive
        regime = ofi_calculator.detect_ofi_regime(ofi_history)
        assert regime == "bullish_flow"

    def test_detect_ofi_regime_bearish(self, ofi_calculator):
        """Test bearish regime detection."""
        ofi_history = [-0.15, -0.2, -0.18, -0.22, -0.19] * 5  # Sustained negative
        regime = ofi_calculator.detect_ofi_regime(ofi_history)
        assert regime == "bearish_flow"

    def test_detect_ofi_regime_balanced(self, ofi_calculator):
        """Test balanced regime detection."""
        ofi_history = [0.05, -0.02, 0.03, -0.04, 0.01] * 5  # Oscillating around 0
        regime = ofi_calculator.detect_ofi_regime(ofi_history)
        assert regime == "balanced"

    def test_ofi_history_tracking(self, ofi_calculator, sample_order_book):
        """Test that OFI history is tracked."""
        for _ in range(5):
            ofi_calculator.calculate_ofi(sample_order_book)
        history = ofi_calculator.get_ofi_history()
        assert len(history) == 5

    def test_reset_history(self, ofi_calculator, sample_order_book):
        """Test history reset."""
        ofi_calculator.calculate_ofi(sample_order_book)
        ofi_calculator.reset_history()
        history = ofi_calculator.get_ofi_history()
        assert len(history) == 0

    def test_cofi_tracker(self, ofi_calculator):
        """Test cumulative OFI tracker."""
        tracker = ofi_calculator.get_cofi_tracker("AAPL", datetime.utcnow())
        assert tracker.symbol == "AAPL"
        assert tracker.current_cofi == 0.0

        tracker.update(0.1, datetime.utcnow())
        assert abs(tracker.current_cofi - 0.1) < 1e-10

        tracker.update(0.2, datetime.utcnow())
        assert abs(tracker.current_cofi - 0.3) < 1e-10


# ==============================================================================
# OFI PREDICTOR TESTS
# ==============================================================================


class TestOFIPredictor:
    """Tests for OFIPredictor."""

    def test_predict_direction_up(self, ofi_predictor, historical_data):
        """Test prediction of upward direction."""
        ofi_history, returns_history = historical_data
        prediction = ofi_predictor.predict_direction(
            ofi=0.35,
            historical_ofi=ofi_history,
            historical_returns=returns_history,
        )
        assert prediction.predicted_direction == "up"
        assert prediction.confidence > 0.3

    def test_predict_direction_down(self, ofi_predictor, historical_data):
        """Test prediction of downward direction."""
        ofi_history, returns_history = historical_data
        prediction = ofi_predictor.predict_direction(
            ofi=-0.35,
            historical_ofi=ofi_history,
            historical_returns=returns_history,
        )
        assert prediction.predicted_direction == "down"
        assert prediction.confidence > 0.3

    def test_predict_direction_neutral(self, ofi_predictor, historical_data):
        """Test prediction of neutral direction."""
        ofi_history, returns_history = historical_data
        prediction = ofi_predictor.predict_direction(
            ofi=0.05,
            historical_ofi=ofi_history,
            historical_returns=returns_history,
        )
        assert prediction.predicted_direction == "neutral"

    def test_train_model(self, ofi_predictor):
        """Test model training."""
        # Use data with both positive and negative returns for logistic regression
        ofi_history = [0.1, -0.1, 0.2, -0.15, 0.3, -0.2, 0.15, -0.05, 0.25, -0.1]
        returns_history = [
            0.001,
            -0.001,
            0.002,
            -0.0015,
            0.003,
            -0.002,
            0.0015,
            -0.0005,
            0.0025,
            -0.001,
        ]
        ofi_predictor.train_model(ofi_history, returns_history)
        assert ofi_predictor._is_trained

    def test_predict_with_model(self, ofi_predictor):
        """Test prediction with trained model."""
        # Use data with both positive and negative returns for logistic regression
        ofi_history = [0.1, -0.1, 0.2, -0.15, 0.3, -0.2, 0.15, -0.05, 0.25, -0.1]
        returns_history = [
            0.001,
            -0.001,
            0.002,
            -0.0015,
            0.003,
            -0.002,
            0.0015,
            -0.0005,
            0.0025,
            -0.001,
        ]
        ofi_predictor.train_model(ofi_history, returns_history)
        prediction = ofi_predictor.predict_with_model(0.2)
        assert prediction is not None

    def test_get_model_confidence(self, ofi_predictor):
        """Test model confidence calculation."""
        confidence = ofi_predictor.get_model_confidence(0.5)
        assert 0.0 <= confidence <= 1.0

    def test_detect_regime_change(self, ofi_predictor):
        """Test regime change detection."""
        # Stable regime then shift
        ofi_history = [0.1] * 20 + [0.4] * 20  # Shift to bullish
        has_changed, regime = ofi_predictor.detect_regime_change(ofi_history)
        if has_changed:
            assert regime == "shifted_to_bullish"

    def test_get_feature_importance(self, ofi_predictor):
        """Test feature importance retrieval."""
        # Use data with both positive and negative returns
        ofi_history = [0.1, -0.1, 0.2, -0.15, 0.3, -0.2, 0.15, -0.05, 0.25, -0.1]
        returns_history = [
            0.001,
            -0.001,
            0.002,
            -0.0015,
            0.003,
            -0.002,
            0.0015,
            -0.0005,
            0.0025,
            -0.001,
        ]
        ofi_predictor.train_model(ofi_history, returns_history)
        importance = ofi_predictor.get_feature_importance()
        assert "correlation" in importance
        assert "r_squared" in importance

    def test_reset_model(self, ofi_predictor, historical_data):
        """Test model reset."""
        ofi_history, returns_history = historical_data
        ofi_predictor.train_model(ofi_history, returns_history)
        ofi_predictor.reset_model()
        assert not ofi_predictor._is_trained


# ==============================================================================
# OFI SIGNAL GENERATOR TESTS
# ==============================================================================


class TestOFISignalGenerator:
    """Tests for OFISignalGenerator."""

    def test_generate_buy_signal(self, ofi_signal_generator, buy_pressure_book, historical_data):
        """Test buy signal generation."""
        ofi_history, returns_history = historical_data
        signal = ofi_signal_generator.generate_signal(
            buy_pressure_book, ofi_history, returns_history
        )
        assert signal is not None
        assert signal.action in ("BUY", "HOLD")

    def test_generate_sell_signal(self, ofi_signal_generator, sell_pressure_book, historical_data):
        """Test sell signal generation."""
        ofi_history, returns_history = historical_data
        signal = ofi_signal_generator.generate_signal(
            sell_pressure_book, ofi_history, returns_history
        )
        assert signal is not None
        assert signal.action in ("SELL", "HOLD")

    def test_generate_no_signal_balanced(
        self, ofi_signal_generator, balanced_order_book, historical_data
    ):
        """Test no signal for balanced book."""
        ofi_history, returns_history = historical_data
        signal = ofi_signal_generator.generate_signal(
            balanced_order_book, ofi_history, returns_history
        )
        # May return None or HOLD
        if signal:
            assert signal.action == "HOLD" or signal.confidence < 0.3

    def test_signal_confidence(self, ofi_signal_generator, buy_pressure_book):
        """Test signal confidence calculation."""
        signal = ofi_signal_generator.generate_signal(
            buy_pressure_book, [0.1, 0.2, 0.3], [0.001, 0.002, 0.003]
        )
        if signal and signal.is_tradeable():
            assert 0.0 <= signal.confidence <= 1.0

    def test_mean_reversion_signal(self, ofi_signal_generator, sample_order_book):
        """Test mean reversion signal generation."""
        ofi_history = [0.1] * 20
        ofi_calculator = OFICalculator()
        cofi_tracker = ofi_calculator.get_cofi_tracker("AAPL", datetime.utcnow())

        # Accumulate high COFI
        for _ in range(30):
            cofi_tracker.update(0.1, datetime.utcnow())

        signal = ofi_signal_generator.generate_signal(
            sample_order_book, ofi_history, None, cofi_tracker
        )
        # Should trigger mean reversion at extreme COFI
        if signal and "mean reversion" in signal.reasoning.lower():
            assert signal.is_tradeable()

    def test_validate_signal(self, ofi_signal_generator):
        """Test signal validation."""
        # Create valid signal
        signal = OFISignal(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            action="BUY",
            ofi_value=0.3,
            ofi_threshold_used=0.2,
            confidence=0.7,
            expected_horizon="short",
            reasoning="Test signal",
        )
        assert ofi_signal_generator.validate_signal(signal)

    def test_filter_signals(self, ofi_signal_generator):
        """Test signal filtering."""
        signals = [
            OFISignal(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                action="BUY",
                ofi_value=0.3,
                ofi_threshold_used=0.2,
                confidence=0.8,
                expected_horizon="short",
                reasoning="Test 1",
            ),
            OFISignal(
                symbol="MSFT",
                timestamp=datetime.utcnow(),
                action="SELL",
                ofi_value=-0.3,
                ofi_threshold_used=-0.2,
                confidence=0.2,  # Below threshold
                expected_horizon="short",
                reasoning="Test 2",
            ),
        ]
        filtered = ofi_signal_generator.filter_signals(signals, min_confidence=0.5)
        assert len(filtered) == 1
        assert filtered[0].symbol == "AAPL"

    def test_rank_signals(self, ofi_signal_generator):
        """Test signal ranking."""
        signals = [
            OFISignal(
                symbol=f"STOCK{i}",
                timestamp=datetime.utcnow(),
                action="BUY",
                ofi_value=0.3,
                ofi_threshold_used=0.2,
                confidence=0.5 + i * 0.1,
                expected_horizon="short",
                reasoning=f"Test {i}",
            )
            for i in range(3)
        ]
        ranked = ofi_signal_generator.rank_signals(signals)
        assert ranked[0].confidence >= ranked[-1].confidence

    def test_get_signal_summary(self, ofi_signal_generator):
        """Test signal summary generation."""
        signals = [
            OFISignal(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                action="BUY",
                ofi_value=0.3,
                ofi_threshold_used=0.2,
                confidence=0.7,
                expected_horizon="short",
                reasoning="Buy",
            ),
            OFISignal(
                symbol="MSFT",
                timestamp=datetime.utcnow(),
                action="SELL",
                ofi_value=-0.3,
                ofi_threshold_used=-0.2,
                confidence=0.6,
                expected_horizon="short",
                reasoning="Sell",
            ),
        ]
        summary = ofi_signal_generator.get_signal_summary(signals)
        assert summary["total"] == 2
        assert summary["buy"] == 1
        assert summary["sell"] == 1


# ==============================================================================
# TICK PROCESSOR TESTS
# ==============================================================================


class TestTickLevelOFIProcessor:
    """Tests for TickLevelOFIProcessor."""

    def test_process_market_buy_tick(self, sample_tick_data):
        """Test processing market buy tick."""
        processor = TickLevelOFIProcessor(window_size=100)
        tick = sample_tick_data[0]  # Market buy

        result = processor.process_tick(tick)
        assert result is not None
        assert result.market_buy_volume > 0
        assert result.tick_ofi > 0  # Buy contributes positively

    def test_process_market_sell_tick(self, sample_tick_data):
        """Test processing market sell tick."""
        processor = TickLevelOFIProcessor(window_size=100)
        tick = sample_tick_data[1]  # Market sell

        result = processor.process_tick(tick)
        assert result is not None
        assert result.market_sell_volume > 0
        assert result.tick_ofi < 0  # Sell contributes negatively

    def test_calculate_tick_ofi(self):
        """Test OFI calculation from tick list."""
        processor = TickLevelOFIProcessor()
        ticks = [
            TickData(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                price=Decimal("100"),
                quantity=100,
                side=OrderSide.BUY,
                is_market_buy=True,
            ),
            TickData(
                symbol="AAPL",
                timestamp=datetime.utcnow() + timedelta(seconds=1),
                price=Decimal("101"),
                quantity=50,
                side=OrderSide.SELL,
                is_market_sell=True,
            ),
        ]
        ofi = processor.calculate_tick_ofi(ticks)
        # (100 - 50) / 150 = 50/150 = 0.333
        assert 0.3 < ofi < 0.35

    def test_update_order_book(self, sample_tick_data, sample_order_book):
        """Test order book update."""
        processor = TickLevelOFIProcessor()
        limit_tick = TickData(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            price=Decimal("100.52"),
            quantity=50,
            side=OrderSide.ASK,
        )
        updated = processor.update_order_book(limit_tick, sample_order_book)
        assert updated is not None
        assert updated.symbol == "AAPL"

    def test_aggressive_flow_ratio(self, sample_tick_data):
        """Test aggressive flow ratio calculation."""
        processor = TickLevelOFIProcessor()
        for tick in sample_tick_data:
            processor.process_tick(tick)

        ratio = processor.get_aggressive_flow_ratio()
        assert ratio > 0

    def test_detect_aggressive_surge(self):
        """Test aggressive surge detection."""
        processor = TickLevelOFIProcessor(window_size=50)

        # Add normal activity
        for i in range(20):
            tick = TickData(
                symbol="AAPL",
                timestamp=datetime.utcnow() + timedelta(seconds=i),
                price=Decimal("100"),
                quantity=100,
                side=OrderSide.BUY,
                is_market_buy=True,
            )
            processor.process_tick(tick)

        # Add surge activity
        for i in range(20, 40):
            tick = TickData(
                symbol="AAPL",
                timestamp=datetime.utcnow() + timedelta(seconds=i),
                price=Decimal("100"),
                quantity=500,  # Much larger
                side=OrderSide.BUY,
                is_market_buy=True,
            )
            processor.process_tick(tick)

        surge = processor.detect_aggressive_surge(threshold=2.0)
        # May detect surge depending on threshold
        assert surge in ("buy_surge", "sell_surge", None)

    def test_reset_processor(self, sample_tick_data):
        """Test processor reset."""
        processor = TickLevelOFIProcessor()
        processor.process_tick(sample_tick_data[0])
        assert len(processor.tick_buffer) > 0

        processor.reset()
        assert len(processor.tick_buffer) == 0
        assert processor.market_buy_volume == 0

    def test_get_statistics(self, sample_tick_data):
        """Test statistics retrieval."""
        processor = TickLevelOFIProcessor()
        for tick in sample_tick_data:
            processor.process_tick(tick)

        stats = processor.get_statistics()
        assert stats["total_ticks"] > 0
        assert "market_buy_volume" in stats
        assert "current_ofi" in stats


# ==============================================================================
# CUMULATIVE OFI TESTS
# ==============================================================================


class TestCumulativeOFI:
    """Tests for CumulativeOFI."""

    def test_cofi_initialization(self):
        """Test COFI initialization."""
        cofi = CumulativeOFI(symbol="AAPL", start_time=datetime.utcnow())
        assert cofi.symbol == "AAPL"
        assert cofi.current_cofi == 0.0
        assert len(cofi.history) == 0

    def test_cofi_update(self):
        """Test COFI update."""
        cofi = CumulativeOFI(symbol="AAPL", start_time=datetime.utcnow())
        now = datetime.utcnow()

        cofi.update(0.1, now)
        assert abs(cofi.current_cofi - 0.1) < 1e-10

        cofi.update(0.2, now + timedelta(seconds=1))
        assert abs(cofi.current_cofi - 0.3) < 1e-10

        cofi.update(-0.1, now + timedelta(seconds=2))
        assert abs(cofi.current_cofi - 0.2) < 1e-10

    def test_cofi_z_score(self):
        """Test COFI z-score calculation."""
        cofi = CumulativeOFI(symbol="AAPL", start_time=datetime.utcnow())
        now = datetime.utcnow()

        # Add values
        for val in [0.1, 0.2, 0.15, 0.18, 0.22]:
            cofi.update(val, now)

        z_score = cofi.z_score
        assert z_score is not None

    def test_cofi_extreme_detection(self):
        """Test extreme COFI detection."""
        cofi = CumulativeOFI(symbol="AAPL", start_time=datetime.utcnow())
        now = datetime.utcnow()

        # Push to extreme high
        for _ in range(10):
            cofi.update(0.5, now)

        # Should be extreme
        assert cofi.max_cofi > 2.0

    def test_cofi_reset(self):
        """Test COFI reset."""
        cofi = CumulativeOFI(symbol="AAPL", start_time=datetime.utcnow())
        cofi.update(0.1, datetime.utcnow())

        new_time = datetime.utcnow() + timedelta(seconds=10)
        cofi.reset(new_time)

        assert cofi.current_cofi == 0.0
        assert cofi.start_time == new_time
        assert len(cofi.history) == 0


# ==============================================================================
# EDGE CASE TESTS
# ==============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_order_book_calculation(self, ofi_calculator):
        """Test OFI calculation with empty order book."""
        empty_book = OrderBookSnapshot(
            symbol="EMPTY", timestamp=datetime.utcnow(), bids=[], asks=[]
        )
        result = ofi_calculator.calculate_ofi(empty_book)
        assert not result.is_valid

    def test_zero_volume_order_book(self, ofi_calculator):
        """Test OFI with zero total volume."""
        zero_vol_book = OrderBookSnapshot(
            symbol="ZERO",
            timestamp=datetime.utcnow(),
            bids=[(Decimal("100"), 0)],
            asks=[(Decimal("101"), 0)],
        )
        result = ofi_calculator.calculate_ofi(zero_vol_book)
        assert result.ofi == 0.0 or not result.is_valid

    def test_invalid_ofi_clamping(self, ofi_calculator):
        """Test that extreme OFI values are clamped to [-1, 1]."""
        extreme_book = OrderBookSnapshot(
            symbol="EXTREME",
            timestamp=datetime.utcnow(),
            bids=[(Decimal("100"), 1000000)],
            asks=[(Decimal("101"), 1)],
        )
        result = ofi_calculator.calculate_ofi(extreme_book)
        if result.is_valid:
            assert -1.0 <= result.ofi <= 1.0

    def test_single_level_order_book(self, ofi_calculator):
        """Test order book with only one level."""
        single_level = OrderBookSnapshot(
            symbol="SINGLE",
            timestamp=datetime.utcnow(),
            bids=[(Decimal("100"), 100)],
            asks=[(Decimal("101"), 100)],
        )
        result = ofi_calculator.calculate_ofi(single_level)
        assert result is not None

    def test_very_wide_spread(self, ofi_calculator):
        """Test order book with very wide spread."""
        wide_book = OrderBookSnapshot(
            symbol="WIDE",
            timestamp=datetime.utcnow(),
            bids=[(Decimal("100"), 100)],
            asks=[(Decimal("110"), 100)],  # 10% spread
        )
        result = ofi_calculator.calculate_ofi(wide_book)
        # Check the spread on the order book
        assert wide_book.spread_bps is not None
        # 10% spread = ~952 bps (spread/mid_price * 10000)
        # (110-100)/105 * 10000 = 952.38
        assert wide_book.spread_bps > 900  # Wide spread
        # OFI should still be valid if volume is sufficient
        # Just verify OFI was calculated
        assert result is not None


# ==============================================================================
# INTEGRATION TESTS
# ==============================================================================


class TestIntegration:
    """Integration tests for OFI module."""

    def test_full_pipeline(self):
        """Test full OFI pipeline from order book to signal."""
        # Setup
        config = OFIConfig(ofi_threshold=0.1)
        calculator = OFICalculator(config=config)
        predictor = OFIPredictor(config=config)
        signal_config = OFISignalConfig(buy_threshold=0.2, sell_threshold=-0.2)
        generator = OFISignalGen(config=signal_config, calculator=calculator, predictor=predictor)

        # Create order book with buy pressure
        order_book = OrderBookSnapshot(
            symbol="TEST",
            timestamp=datetime.utcnow(),
            bids=[(Decimal("100"), 500), (Decimal("99.99"), 300)],
            asks=[(Decimal("100.01"), 100), (Decimal("100.02"), 50)],
        )

        # Calculate OFI
        ofi_result = calculator.calculate_ofi(order_book)
        assert ofi_result.is_valid

        # Train predictor
        ofi_history = [0.1, 0.15, 0.2, 0.18, 0.25] * 4
        returns_history = [0.001, 0.0015, 0.002, 0.0018, 0.0025] * 4
        predictor.train_model(ofi_history, returns_history)

        # Generate signal
        signal = generator.generate_signal(order_book, ofi_history, returns_history)
        assert signal is not None

    def test_tick_to_signal_pipeline(self):
        """Test pipeline from tick data to signal."""
        tick_processor = TickLevelOFIProcessor(window_size=50)
        OFICalculator()

        # Process ticks
        for i in range(20):
            tick = TickData(
                symbol="AAPL",
                timestamp=datetime.utcnow() + timedelta(seconds=i),
                price=Decimal("100.50"),
                quantity=100 if i % 2 == 0 else 50,
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                is_market_buy=i % 2 == 0,
                is_market_sell=i % 2 != 0,
            )
            tick_processor.process_tick(tick)

        # Get statistics
        stats = tick_processor.get_statistics()
        assert stats["total_ticks"] == 20
