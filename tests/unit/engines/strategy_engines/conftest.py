"""
Test configuration and fixtures for strategy engines unit tests.

This module provides common fixtures and utilities for testing all strategy engines.
"""

import pytest
from collections import deque
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock, patch

import numpy as np
import pandas as pd

from app.models.market_data import Quote
from app.models.signal import Signal, SignalType, SignalStrength, SignalSource
from app.models.portfolio import Portfolio, Position


# ===== Market Data Fixtures =====


@pytest.fixture
def sample_quote() -> Quote:
    """Create a sample market quote for testing."""
    return Quote(
        symbol="AAPL",
        timestamp=datetime.utcnow(),
        bid=Decimal("150.00"),
        ask=Decimal("150.05"),
        last=Decimal("150.02"),
        open=Decimal("149.00"),
        high=Decimal("151.00"),
        low=Decimal("148.50"),
        close=Decimal("150.00"),
        volume=Decimal("1000000"),
        spread=Decimal("0.05"),
    )


@pytest.fixture
def sample_quotes_multiple() -> List[Quote]:
    """Create multiple sample quotes for testing."""
    base_time = datetime.utcnow()
    quotes = []
    for i in range(50):
        price = 150 + i * 0.5
        quotes.append(
            Quote(
                symbol="AAPL",
                timestamp=base_time - timedelta(minutes=50 - i),
                bid=Decimal(str(price - 0.02)),
                ask=Decimal(str(price + 0.02)),
                last=Decimal(str(price)),
                open=Decimal(str(price - 0.5)),
                high=Decimal(str(price + 0.3)),
                low=Decimal(str(price - 0.3)),
                close=Decimal(str(price)),
                volume=Decimal("1000000"),
            )
        )
    return quotes


@pytest.fixture
def price_history_trending_up() -> deque:
    """Create trending up price history for testing."""
    prices = deque(maxlen=200)
    base_price = 100.0
    for i in range(100):
        prices.append(base_price + i * 0.5)
    return prices


@pytest.fixture
def price_history_trending_down() -> deque:
    """Create trending down price history for testing."""
    prices = deque(maxlen=200)
    base_price = 150.0
    for i in range(100):
        prices.append(base_price - i * 0.5)
    return prices


@pytest.fixture
def price_history_sideways() -> deque:
    """Create sideways (ranging) price history for testing."""
    prices = deque(maxlen=200)
    for i in range(100):
        # Random walk around 150
        prices.append(150 + np.random.randn() * 2)
    return prices


@pytest.fixture
def price_history_mean_reverting() -> deque:
    """Create mean-reverting price history for testing."""
    prices = deque(maxlen=200)
    for i in range(100):
        # Oscillate around mean
        prices.append(150 + 10 * np.sin(i * 0.2))
    return prices


# ===== Pairs Trading Fixtures =====


@pytest.fixture
def cointegrated_pair_prices() -> Dict[str, deque]:
    """Create cointegrated price series for pairs trading testing."""
    # Create two series that move together but may diverge temporarily
    np.random.seed(42)
    n = 100

    # Common trend
    trend = np.cumsum(np.random.randn(n) * 0.5)

    # Pair 1: trend + noise
    prices1 = deque(maxlen=300)
    for i in range(n):
        prices1.append(100 + trend[i] + np.random.randn() * 2)

    # Pair 2: trend * hedge_ratio + noise (cointegrated)
    prices2 = deque(maxlen=300)
    hedge_ratio = 1.5
    for i in range(n):
        prices2.append(50 + trend[i] * hedge_ratio + np.random.randn() * 3)

    return {
        "symbol1": prices1,
        "symbol2": prices2,
        "hedge_ratio": hedge_ratio,
    }


# ===== Portfolio Fixtures =====


@pytest.fixture
def empty_portfolio() -> Portfolio:
    """Create an empty portfolio for testing."""
    return Portfolio(
        cash=Decimal("100000"),
        positions=[],
    )


@pytest.fixture
def portfolio_with_positions() -> Portfolio:
    """Create a portfolio with some positions for testing."""
    positions = [
        Position(
            symbol="AAPL",
            quantity=Decimal("100"),
            entry_price=Decimal("150.00"),
            current_price=Decimal("155.00"),
            market_value=Decimal("15500"),
            unrealized_pnl=Decimal("500"),
        ),
        Position(
            symbol="MSFT",
            quantity=Decimal("50"),
            entry_price=Decimal("300.00"),
            current_price=Decimal("295.00"),
            market_value=Decimal("14750"),
            unrealized_pnl=Decimal("-250"),
        ),
    ]
    return Portfolio(
        cash=Decimal("70000"),
        positions=positions,
    )


# ===== Signal Fixtures =====


@pytest.fixture
def sample_buy_signal() -> Signal:
    """Create a sample BUY signal for testing."""
    return Signal(
        symbol="AAPL",
        signal_type=SignalType.BUY,
        strength=SignalStrength.STRONG,
        confidence=75.0,
        liquidity_score=80.0,
        priority_score=77.5,
        source=SignalSource.MOMENTUM,
        price=Decimal("150.00"),
        volume=Decimal("1000"),
        timestamp=datetime.utcnow(),
        metadata={
            "strategy": "test_strategy",
            "rsi": 35.0,
            "momentum": 0.03,
        },
    )


@pytest.fixture
def sample_sell_signal() -> Signal:
    """Create a sample SELL signal for testing."""
    return Signal(
        symbol="AAPL",
        signal_type=SignalType.SELL,
        strength=SignalStrength.MODERATE,
        confidence=60.0,
        liquidity_score=70.0,
        priority_score=64.0,
        source=SignalSource.MEAN_REVERSION,
        price=Decimal("150.00"),
        volume=Decimal("1000"),
        timestamp=datetime.utcnow(),
        metadata={
            "strategy": "test_strategy",
            "z_score": 2.5,
        },
    )


# ===== Mock Engine Fixtures =====


@pytest.fixture
def mock_learning_engine():
    """Create a mock learning engine for testing."""
    mock_engine = Mock()
    mock_engine.predict = Mock(
        return_value={
            "confidence": 0.8,
            "success_probability": 0.75,
            "recommended_action": "BUY",
        }
    )
    mock_engine.is_ready = Mock(return_value=True)
    return mock_engine


@pytest.fixture
def mock_context_engine():
    """Create a mock context engine for testing."""
    mock_engine = Mock()
    mock_engine.get_current_regime = Mock(
        return_value={
            "regime": "bull",
            "confidence": 0.8,
            "regime_probabilities": {"bull": 0.7, "bear": 0.2, "neutral": 0.1},
        }
    )
    mock_engine.get_volatility_regime = Mock(
        return_value={
            "regime": "normal",
            "percentile": 50,
        }
    )
    return mock_engine


@pytest.fixture
def mock_data_engine():
    """Create a mock data engine for testing."""
    mock_engine = Mock()
    mock_engine.get_ohlcv = Mock(return_value=sample_quotes_multiple(None)[:-1])
    mock_engine.get_status = Mock(return_value={"status": "active"})
    return mock_engine


# ===== Configuration Fixtures =====


@pytest.fixture
def momentum_config() -> Dict[str, Any]:
    """Create momentum strategy configuration."""
    return {
        "name": "test_momentum",
        "rsi_period": 14,
        "ema_period": 20,
        "lookback_period": 5,
        "rsi_threshold": Decimal("0.3"),  # 30%
        "momentum_threshold": Decimal("0.02"),
        "volume_threshold": Decimal("1.5"),
        "atr_filter_enabled": True,
        "min_atr_threshold": Decimal("0.015"),
        "max_exposure": Decimal("0.60"),
        "stop_loss": Decimal("0.05"),
        "take_profit": Decimal("0.10"),
        "max_position_size": Decimal("10000"),
    }


@pytest.fixture
def mean_reversion_config() -> Dict[str, Any]:
    """Create mean reversion strategy configuration."""
    return {
        "name": "test_mean_reversion",
        "z_score_threshold": Decimal("2.0"),
        "lookback_period": 20,
        "volatility_threshold": Decimal("0.02"),
        "min_z_score": Decimal("1.5"),
        "stop_loss": Decimal("0.05"),
        "take_profit": Decimal("0.10"),
        "max_position_size": Decimal("10000"),
    }


@pytest.fixture
def pairs_trading_config() -> Dict[str, Any]:
    """Create pairs trading strategy configuration."""
    return {
        "name": "test_pairs_trading",
        "pair_symbols": ["AAPL", "MSFT"],
        "cointegration_threshold": Decimal("0.05"),
        "spread_threshold": Decimal("0.02"),
        "lookback_period": 60,
        "min_correlation": Decimal("0.7"),
        "max_pair_exposure": Decimal("0.20"),
        "max_total_exposure": Decimal("0.40"),
        "min_spread_z_score": Decimal("2.0"),
        "stop_loss": Decimal("0.05"),
        "take_profit": Decimal("0.10"),
        "max_position_size": Decimal("10000"),
    }


@pytest.fixture
def modular_momentum_config() -> Dict[str, Any]:
    """Create modular momentum strategy configuration."""
    return {
        "name": "test_modular_momentum",
        "preset": "balanced",
        "presets": {
            "balanced": {
                "min_confidence": 0.6,
                "combination_mode": "MAJORITY",
            }
        },
        "modules": {
            "ema_filter": {
                "enabled": True,
                "period": 20,
            },
            "rsi_filter": {
                "enabled": True,
                "period": 14,
            },
            "momentum_filter": {
                "enabled": True,
                "period": 14,
            },
            "volume_filter": {
                "enabled": True,
                "period": 20,
            },
            "atr_filter": {
                "enabled": True,
                "period": 14,
            },
        },
        "adaptive_learning": {
            "enabled": False,
        },
    }


# ===== Utility Fixtures =====


@pytest.fixture
def mock_centralized_config():
    """Mock centralized configuration system."""
    with patch('app.engines.strategy_engines.base.get_strategy_config') as mock_config, patch(
        'app.engines.strategy_engines.base.get_trading_threshold'
    ) as mock_threshold:
        # Mock strategy config
        strategy_config = Mock()
        strategy_config.parameters = {
            "rsi_threshold_buy": Decimal("0.3"),
            "momentum_threshold": Decimal("0.02"),
            "volume_threshold": Decimal("1.5"),
            "max_exposure": Decimal("0.60"),
            "ema_period": 20,
            "rsi_period": 14,
            "lookback_period": 5,
            "atr_filter_enabled": True,
            "use_relative_atr": True,
            "min_atr_threshold": Decimal("0.015"),
        }
        strategy_config.stop_loss_pct = Decimal("0.05")
        strategy_config.take_profit_pct = Decimal("0.10")
        strategy_config.max_position_size = Decimal("10000")

        mock_config.return_value = strategy_config

        # Mock trading thresholds
        mock_threshold.side_effect = lambda key: {
            "stop_loss_pct": Decimal("0.05"),
            "take_profit_pct": Decimal("0.10"),
            "max_position_size": Decimal("10000"),
        }.get(key, Decimal("0.05"))

        yield mock_config, mock_threshold


@pytest.fixture
def mock_pandas_ta():
    """Mock pandas-ta calculations."""
    with patch('app.engines.strategy_engines.mean_reversion_engine.pd') as mock_pd:
        # Mock DataFrame creation
        mock_df = Mock()
        mock_df.__getitem__ = Mock(return_value=Mock())

        # Mock rolling calculations
        mock_rolling = Mock()
        mock_mean_series = Mock()
        mock_mean_series.iloc = Mock()
        mock_mean_series.iloc.__getitem__ = Mock(return_value=150.0)

        mock_std_series = Mock()
        mock_std_series.iloc = Mock()
        mock_std_series.iloc.__getitem__ = Mock(return_value=5.0)

        mock_rolling.mean = Mock(return_value=mock_mean_series)
        mock_rolling.std = Mock(return_value=mock_std_series)
        mock_df.rolling = Mock(return_value=mock_rolling)

        mock_pd.DataFrame = Mock(return_value=mock_df)
        mock_pd.isna = Mock(return_value=False)

        yield mock_pd


# ===== Edge Case Fixtures =====


@pytest.fixture
def quote_with_nan():
    """Create a quote with NaN values for testing edge cases."""
    return Quote(
        symbol="TEST",
        timestamp=datetime.utcnow(),
        bid=Decimal("150.00"),
        ask=Decimal("150.05"),
        last=Decimal("150.02"),
        open=Decimal("0"),  # Missing data
        high=Decimal("0"),
        low=Decimal("0"),
        close=Decimal("150.00"),
        volume=Decimal("0"),  # Missing volume
    )


@pytest.fixture
def quote_with_zero_price():
    """Create a quote with zero price for testing edge cases."""
    return Quote(
        symbol="TEST",
        timestamp=datetime.utcnow(),
        bid=Decimal("0"),
        ask=Decimal("0"),
        last=Decimal("0"),
        open=Decimal("0"),
        high=Decimal("0"),
        low=Decimal("0"),
        close=Decimal("0"),
        volume=Decimal("1000"),
    )


@pytest.fixture
def empty_price_history() -> deque:
    """Create empty price history for testing edge cases."""
    return deque(maxlen=200)


@pytest.fixture
def single_price_history() -> deque:
    """Create price history with single value for testing edge cases."""
    prices = deque(maxlen=200)
    prices.append(150.0)
    return prices
