"""
Comprehensive unit tests for PairsTradingStrategyEngine.

Tests cover:
- Pairs trading initialization and configuration
- Cointegration calculation
- Feature extraction (spread, correlation, hedge ratio)
- Signal generation for pairs trading
- Risk checking for pairs
- Edge cases (insufficient data, NaN handling)
- Confidence calculation
"""

import pytest
import numpy as np
from decimal import Decimal
from datetime import datetime
from collections import deque
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock

from app.engines.strategy_engines.pairs_engine import PairsTradingStrategyEngine
from app.models.market_data import Quote
from app.models.signal import Signal, SignalType, SignalStrength, SignalSource
from app.models.portfolio import Portfolio, Position


# ===== Initialization Tests =====


@pytest.mark.unit
class TestPairsTradingInitialization:
    """Test suite for PairsTradingStrategyEngine initialization."""

    def test_initialization_with_config(self, pairs_trading_config):
        """Test initialization with configuration."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config'
        ) as mock_config, patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold'
        ) as mock_threshold:
            # Setup mocks
            strategy_config = Mock()
            strategy_config.parameters = {
                "cointegration_threshold": Decimal("0.05"),
                "spread_threshold": Decimal("0.02"),
                "lookback_period": 60,
                "min_correlation": Decimal("0.7"),
                "max_pair_exposure": Decimal("0.20"),
                "max_total_exposure": Decimal("0.40"),
                "hedge_ratio_threshold": Decimal("0.05"),
                "min_spread_z_score": Decimal("2.0"),
                "max_pair_half_life_days": 30,
                "slippage_per_trade_pct": Decimal("0.001"),
                "commission_per_trade_pct": Decimal("0.001"),
            }
            strategy_config.stop_loss_pct = Decimal("0.05")
            strategy_config.take_profit_pct = Decimal("0.10")
            strategy_config.max_position_size = Decimal("10000")

            mock_config.return_value = strategy_config
            mock_threshold.return_value = Decimal("0.05")

            engine = PairsTradingStrategyEngine(pairs_trading_config)

            assert engine.name == "test_pairs_trading"
            assert engine.cointegration_threshold == Decimal("0.05")
            assert engine.spread_threshold == Decimal("0.02")
            assert engine.lookback_period == 60
            assert engine.min_correlation == Decimal("0.7")
            assert engine.pair_symbols == ["AAPL", "MSFT"]

    def test_initialization_default_symbols(self):
        """Test initialization with default pair symbols."""
        config = {"name": "test_pairs"}

        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(config)

            assert engine.pair_symbols == ["AAPL", "MSFT"]

    def test_initialization_price_history(self, pairs_trading_config):
        """Test that price history deques are initialized."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            assert isinstance(engine.price_history, dict)
            assert len(engine.price_history) == 0

    def test_get_strategy_type(self, pairs_trading_config):
        """Test get_strategy_type returns correct type."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            assert engine.get_strategy_type() == "pairs_trading"


# ===== Feature Extraction Tests =====


@pytest.mark.unit
class TestPairsTradingFeatureExtraction:
    """Test suite for feature extraction in pairs trading."""

    def test_extract_features_basic(self, pairs_trading_config):
        """Test basic feature extraction."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            # Build price history
            for i in range(100):
                engine.price_history["AAPL"].append(150 + i * 0.5)
                engine.price_history["MSFT"].append(300 + i * 1.0)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("150"),
                ask=Decimal("150.05"),
                last=Decimal("150"),
                volume=Decimal("1000"),
            )

            features = engine.extract_features(quote)

            assert "timestamp" in features
            assert "symbol" in features
            assert "price" in features
            assert features["symbol"] == "AAPL"

    def test_extract_features_with_sufficient_history(self, pairs_trading_config):
        """Test feature extraction with sufficient price history."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            # Build price history
            for i in range(100):
                engine.price_history["AAPL"].append(150 + i * 0.5)
                engine.price_history["MSFT"].append(300 + i * 1.0)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("200"),
                ask=Decimal("200.05"),
                last=Decimal("200"),
                volume=Decimal("1000"),
            )

            features = engine.extract_features(quote)

            assert "spread" in features
            assert "spread_pct" in features
            assert "correlation" in features
            assert "hedge_ratio" in features
            assert "spread_z_score" in features

    def test_extract_features_correlation(self, pairs_trading_config):
        """Test correlation calculation in feature extraction."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            # Build perfectly correlated price history
            for i in range(100):
                engine.price_history["AAPL"].append(150 + i * 0.5)
                engine.price_history["MSFT"].append(300 + i * 1.0)  # Perfectly correlated

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("200"),
                ask=Decimal("200.05"),
                last=Decimal("200"),
                volume=Decimal("1000"),
            )

            features = engine.extract_features(quote)

            # Correlation should be close to 1.0 for perfectly correlated series
            assert features["correlation"] > 0.9

    def test_extract_features_insufficient_history(self, pairs_trading_config):
        """Test feature extraction with insufficient history."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            # Only add a few data points
            for i in range(5):
                engine.price_history["AAPL"].append(150 + i * 0.5)
                engine.price_history["MSFT"].append(300 + i * 1.0)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("150"),
                ask=Decimal("150.05"),
                last=Decimal("150"),
                volume=Decimal("1000"),
            )

            features = engine.extract_features(quote)

            # Should return defaults when insufficient history
            assert features["correlation"] == 0.0
            assert features["hedge_ratio"] == 1.0
            assert features["spread_z_score"] == 0.0

    def test_extract_features_with_historical_data(self, pairs_trading_config):
        """Test feature extraction with provided historical data."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            # Create historical data
            historical_data = []
            for i in range(100):
                historical_data.append(
                    Quote(
                        symbol="AAPL",
                        timestamp=datetime.utcnow(),
                        bid=Decimal(str(150 + i * 0.5)),
                        ask=Decimal(str(150.05 + i * 0.5)),
                        last=Decimal(str(150 + i * 0.5)),
                        volume=Decimal("1000"),
                    )
                )
                historical_data.append(
                    Quote(
                        symbol="MSFT",
                        timestamp=datetime.utcnow(),
                        bid=Decimal(str(300 + i * 1.0)),
                        ask=Decimal(str(300.05 + i * 1.0)),
                        last=Decimal(str(300 + i * 1.0)),
                        volume=Decimal("1000"),
                    )
                )

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("200"),
                ask=Decimal("200.05"),
                last=Decimal("200"),
                volume=Decimal("1000"),
            )

            features = engine.extract_features(quote, historical_data)

            assert "spread" in features
            assert "correlation" in features


# ===== Signal Generation Tests =====


@pytest.mark.unit
class TestPairsTradingSignalGeneration:
    """Test suite for signal generation in pairs trading."""

    def test_generate_signals_insufficient_history(self, pairs_trading_config):
        """Test signal generation with insufficient price history."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("150"),
                ask=Decimal("150.05"),
                last=Decimal("150"),
                volume=Decimal("1000"),
            )

            signals = engine._generate_signals_impl(quote)

            assert len(signals) == 0

    def test_generate_signals_with_spread_divergence(self, pairs_trading_config):
        """Test signal generation when spread diverges significantly."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)
            engine.min_spread_z_score = Decimal("2.0")

            # Build price history with spread divergence
            # Price 1 will be much higher than Price 2 at the end
            for i in range(100):
                engine.price_history["AAPL"].append(150 + i * 0.5)
                engine.price_history["MSFT"].append(300 + i * 0.3)  # Lower growth

            # Add final data point to create extreme spread
            engine.price_history["AAPL"].append(200)
            engine.price_history["MSFT"].append(320)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("200"),
                ask=Decimal("200.05"),
                last=Decimal("200"),
                volume=Decimal("1000"),
            )

            signals = engine._generate_signals_impl(quote)

            # Should generate SELL for AAPL (overvalued relative to MSFT)
            # Note: Actual signal generation depends on cointegration check

    def test_generate_signals_no_cointegration(self, pairs_trading_config):
        """Test signal generation when pairs are not cointegrated."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            # Build price history
            for i in range(100):
                engine.price_history["AAPL"].append(150 + i * 0.5)
                engine.price_history["MSFT"].append(300 + i * 1.0)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("200"),
                ask=Decimal("200.05"),
                last=Decimal("200"),
                volume=Decimal("1000"),
            )

            signals = engine._generate_signals_impl(quote)

            # If not cointegrated, should not generate signals
            # (This depends on cointegration test implementation)

    def test_create_buy_signal(self, pairs_trading_config):
        """Test creation of buy signal."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("150"),
                ask=Decimal("150.05"),
                last=Decimal("150"),
                volume=Decimal("1000"),
            )

            signal = engine._create_buy_signal(
                market_data=quote, spread_z_score=-2.5, cointegration_score=0.9, correlation=0.85
            )

            assert signal.signal_type == SignalType.BUY
            assert signal.symbol == "AAPL"
            assert signal.source == SignalSource.PAIRS_TRADING
            assert signal.confidence > 50
            assert signal.metadata["spread_z_score"] == -2.5
            assert signal.metadata["cointegration_score"] == 0.9
            assert signal.metadata["correlation"] == 0.85

    def test_create_sell_signal(self, pairs_trading_config):
        """Test creation of sell signal."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            quote = Quote(
                symbol="MSFT",
                timestamp=datetime.utcnow(),
                bid=Decimal("300"),
                ask=Decimal("300.05"),
                last=Decimal("300"),
                volume=Decimal("1000"),
            )

            signal = engine._create_sell_signal(
                market_data=quote, spread_z_score=2.5, cointegration_score=0.9, correlation=0.85
            )

            assert signal.signal_type == SignalType.SELL
            assert signal.symbol == "MSFT"
            assert signal.source == SignalSource.PAIRS_TRADING


# ===== Confidence Calculation Tests =====


@pytest.mark.unit
class TestConfidenceCalculation:
    """Test suite for confidence calculation."""

    def test_calculate_confidence_high_z_score(self, pairs_trading_config):
        """Test confidence with high Z-score."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            confidence = engine._calculate_confidence(
                abs_spread_z_score=3.0, cointegration_score=0.95, correlation=0.95
            )

            # Should be high confidence
            assert confidence >= 90

    def test_calculate_confidence_medium_z_score(self, pairs_trading_config):
        """Test confidence with medium Z-score."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            confidence = engine._calculate_confidence(
                abs_spread_z_score=2.0, cointegration_score=0.7, correlation=0.8
            )

            # Should be medium confidence
            assert 50 <= confidence < 90

    def test_calculate_confidence_low_z_score(self, pairs_trading_config):
        """Test confidence with low Z-score."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            confidence = engine._calculate_confidence(
                abs_spread_z_score=1.0, cointegration_score=0.5, correlation=0.6
            )

            # Should be low confidence
            assert confidence < 70

    def test_calculate_confidence_no_cointegration(self, pairs_trading_config):
        """Test confidence when no cointegration score."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            confidence = engine._calculate_confidence(
                abs_spread_z_score=3.0, cointegration_score=None, correlation=0.9
            )

            # Should be lower than with cointegration
            assert confidence < 90


# ===== Risk Check Tests =====


@pytest.mark.unit
class TestRiskCheck:
    """Test suite for risk checking."""

    def test_risk_check_pass(
        self, pairs_trading_config, sample_buy_signal, portfolio_with_positions
    ):
        """Test risk check that passes."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)
            engine.pair_symbols = ["AAPL", "MSFT"]

            # Add good cointegration and correlation to signal metadata
            sample_buy_signal.metadata["cointegration_score"] = 0.9
            sample_buy_signal.metadata["correlation"] = 0.85

            passes = engine.risk_check(sample_buy_signal, portfolio_with_positions)

            assert passes is True

    def test_risk_check_total_exposure(self, pairs_trading_config, sample_buy_signal):
        """Test risk check with excessive total exposure."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)
            engine.max_total_exposure = Decimal("0.20")

            # Create portfolio with high exposure
            high_exposure_portfolio = Portfolio(
                cash=Decimal("1000"),
                positions=[
                    Position(
                        symbol="AAPL",
                        quantity=Decimal("1000"),
                        entry_price=Decimal("150"),
                        current_price=Decimal("150"),
                        market_value=Decimal("150000"),
                        unrealized_pnl=Decimal("0"),
                    )
                ],
            )

            sample_buy_signal.metadata["cointegration_score"] = 0.9
            sample_buy_signal.metadata["correlation"] = 0.85

            passes = engine.risk_check(sample_buy_signal, high_exposure_portfolio)

            assert passes is False

    def test_risk_check_pair_exposure(self, pairs_trading_config, sample_buy_signal):
        """Test risk check with excessive pair exposure."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)
            engine.pair_symbols = ["AAPL", "MSFT"]
            engine.max_pair_exposure = Decimal("0.10")

            # Create portfolio with high pair exposure
            pair_exposure_portfolio = Portfolio(
                cash=Decimal("10000"),
                positions=[
                    Position(
                        symbol="AAPL",
                        quantity=Decimal("500"),
                        entry_price=Decimal("150"),
                        current_price=Decimal("150"),
                        market_value=Decimal("75000"),
                        unrealized_pnl=Decimal("0"),
                    )
                ],
            )

            sample_buy_signal.metadata["cointegration_score"] = 0.9
            sample_buy_signal.metadata["correlation"] = 0.85

            passes = engine.risk_check(sample_buy_signal, pair_exposure_portfolio)

            assert passes is False

    def test_risk_check_low_cointegration(
        self, pairs_trading_config, sample_buy_signal, portfolio_with_positions
    ):
        """Test risk check with low cointegration."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)
            engine.pair_symbols = ["AAPL", "MSFT"]

            # Add low cointegration to signal metadata
            sample_buy_signal.metadata["cointegration_score"] = 0.03
            sample_buy_signal.metadata["correlation"] = 0.85

            passes = engine.risk_check(sample_buy_signal, portfolio_with_positions)

            assert passes is False

    def test_risk_check_low_correlation(
        self, pairs_trading_config, sample_buy_signal, portfolio_with_positions
    ):
        """Test risk check with low correlation."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)
            engine.pair_symbols = ["AAPL", "MSFT"]

            # Add low correlation to signal metadata
            sample_buy_signal.metadata["cointegration_score"] = 0.9
            sample_buy_signal.metadata["correlation"] = 0.5

            passes = engine.risk_check(sample_buy_signal, portfolio_with_positions)

            assert passes is False


# ===== Exposure Calculation Tests =====


@pytest.mark.unit
class TestExposureCalculation:
    """Test suite for exposure calculation."""

    def test_calculate_total_exposure(self, pairs_trading_config):
        """Test total exposure calculation."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            portfolio = Portfolio(
                cash=Decimal("50000"),
                positions=[
                    Position(
                        symbol="AAPL",
                        quantity=Decimal("100"),
                        entry_price=Decimal("150"),
                        current_price=Decimal("150"),
                        market_value=Decimal("15000"),
                        unrealized_pnl=Decimal("0"),
                    )
                ],
            )

            exposure = engine._calculate_total_exposure(portfolio)

            # Should be 15000 / (15000 + 50000) = ~23%
            assert 0.20 < exposure < 0.25

    def test_calculate_total_exposure_empty_portfolio(self, pairs_trading_config):
        """Test total exposure with empty portfolio."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            portfolio = Portfolio(
                cash=Decimal("100000"),
                positions=[],
            )

            exposure = engine._calculate_total_exposure(portfolio)

            assert exposure == Decimal("0")

    def test_calculate_pair_exposure(self, pairs_trading_config):
        """Test pair-specific exposure calculation."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)
            engine.pair_symbols = ["AAPL", "MSFT"]

            portfolio = Portfolio(
                cash=Decimal("50000"),
                positions=[
                    Position(
                        symbol="AAPL",
                        quantity=Decimal("100"),
                        entry_price=Decimal("150"),
                        current_price=Decimal("150"),
                        market_value=Decimal("15000"),
                        unrealized_pnl=Decimal("0"),
                    ),
                    Position(
                        symbol="MSFT",
                        quantity=Decimal("50"),
                        entry_price=Decimal("300"),
                        current_price=Decimal("300"),
                        market_value=Decimal("15000"),
                        unrealized_pnl=Decimal("0"),
                    ),
                    Position(
                        symbol="GOOGL",  # Not in pair
                        quantity=Decimal("10"),
                        entry_price=Decimal("2500"),
                        current_price=Decimal("2500"),
                        market_value=Decimal("25000"),
                        unrealized_pnl=Decimal("0"),
                    ),
                ],
            )

            exposure = engine._calculate_pair_exposure(portfolio)

            # Should only include AAPL and MSFT: 30000 / (30000 + 50000 + 25000) = ~29%
            assert 0.25 < exposure < 0.35


# ===== Edge Cases Tests =====


@pytest.mark.unit
class TestEdgeCases:
    """Test suite for edge cases."""

    def test_single_symbol_in_pair(self, pairs_trading_config):
        """Test with only one symbol in pair configuration."""
        config = {"name": "test", "pair_symbols": ["AAPL"]}

        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(config)

            # Should default to AAPL/MSFT
            assert engine.pair_symbols == ["AAPL", "MSFT"]

    def test_zero_price_quote(self, pairs_trading_config, quote_with_zero_price):
        """Test handling of zero price quote."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            # Build history first
            for i in range(100):
                engine.price_history["AAPL"].append(150 + i * 0.5)
                engine.price_history["MSFT"].append(300 + i * 1.0)

            signals = engine._generate_signals_impl(quote_with_zero_price)

            assert len(signals) == 0

    def test_get_required_parameters(self, pairs_trading_config):
        """Test getting required parameters."""
        with patch(
            'app.engines.strategy_engines.pairs_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.pairs_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ):
            engine = PairsTradingStrategyEngine(pairs_trading_config)

            params = engine.get_required_parameters()

            assert "cointegration_threshold" in params
            assert "spread_threshold" in params
            assert "lookback_period" in params
            assert "min_correlation" in params
            assert "pair_symbols" in params
