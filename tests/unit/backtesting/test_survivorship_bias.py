"""
Unit tests for Survivorship Bias Correction.

Tests Ernest Chan's survivorship bias correction methodology from
"Algorithmic Trading" (Chapter 3).
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd

from app.backtesting.survivorship_bias_corrector import (
    DelistedStockInfo,
    SurvivorshipAdjustment,
    SurvivorshipBiasCorrector,
    adjust_backtest_for_survivorship,
)


class TestSurvivorshipBiasCorrector:
    """Test suite for SurvivorshipBiasCorrector."""

    @pytest.fixture
    def corrector(self):
        """Create a default corrector instance."""
        return SurvivorshipBiasCorrector()

    @pytest.fixture
    def sample_universe(self):
        """Create a sample current universe."""
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "JPM", "V", "JNJ"]

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns series."""
        np.random.seed(42)
        return pd.Series(np.random.randn(252) * 0.02)  # Daily returns

    def test_initialization(self, corrector):
        """Test corrector initialization."""
        assert corrector.ANNUAL_DELISTING_RATE == 0.03
        assert corrector.BANKRUPTCY_RATE == 0.01
        assert corrector.ACQUISITION_RATE == 0.015

    def test_calculate_survivorship_bias(
        self, corrector, sample_universe
    ):
        """Test survivorship bias calculation."""
        backtest_start = datetime(2020, 1, 1)
        backtest_end = datetime(2023, 1, 1)

        adjustment = corrector.calculate_survivorship_bias(
            sample_universe, backtest_start, backtest_end
        )

        # Check basic properties
        assert isinstance(adjustment, SurvivorshipAdjustment)
        assert adjustment.surviving_count == len(sample_universe)
        assert adjustment.delisted_count >= 0
        assert adjustment.total_universe_size >= adjustment.surviving_count
        assert adjustment.survivorship_bias_factor >= 1.0

    def test_adjust_returns_multiplicative(
        self, corrector, sample_returns, sample_universe
    ):
        """Test multiplicative return adjustment."""
        backtest_start = datetime(2020, 1, 1)
        backtest_end = datetime(2021, 1, 1)

        adjustment = corrector.calculate_survivorship_bias(
            sample_universe, backtest_start, backtest_end
        )

        adjusted_returns = corrector.adjust_returns_for_survivorship(
            sample_returns, adjustment, method="multiplicative"
        )

        # Adjusted returns should be smaller (bias factor > 1)
        assert len(adjusted_returns) == len(sample_returns)
        assert adjusted_returns.mean() <= sample_returns.mean()

    def test_adjust_returns_additive(
        self, corrector, sample_returns, sample_universe
    ):
        """Test additive return adjustment."""
        backtest_start = datetime(2020, 1, 1)
        backtest_end = datetime(2021, 1, 1)

        adjustment = corrector.calculate_survivorship_bias(
            sample_universe, backtest_start, backtest_end
        )

        adjusted_returns = corrector.adjust_returns_for_survivorship(
            sample_returns, adjustment, method="additive"
        )

        # Adjusted returns should be smaller
        assert len(adjusted_returns) == len(sample_returns)

    def test_bias_factor_calculation(self, corrector):
        """Test bias factor calculation logic."""
        # Test with no delisted stocks
        bias_factor = corrector._calculate_bias_factor(
            survivor_count=100, delisted_count=0, period_years=1.0
        )
        assert bias_factor == 1.0

        # Test with delisted stocks
        bias_factor = corrector._calculate_bias_factor(
            survivor_count=90, delisted_count=10, period_years=1.0
        )
        assert bias_factor > 1.0

        # Test bias factor is capped
        bias_factor = corrector._calculate_bias_factor(
            survivor_count=50, delisted_count=50, period_years=10.0
        )
        assert bias_factor <= 1.3  # Maximum for 10 years

    def test_bankruptcy_adjustment(self, corrector):
        """Test bankruptcy adjustment calculation."""
        # No bankruptcies
        adj = corrector._calculate_bankruptcy_adjustment(
            delisted_count=10, period_years=1.0
        )
        assert adj == 1.0

        # With bankruptcies (should reduce adjustment)
        adj = corrector._calculate_bankruptcy_adjustment(
            delisted_count=10, period_years=1.0
        )
        assert adj < 1.0

    def test_acquisition_adjustment(self, corrector):
        """Test acquisition adjustment calculation."""
        # No acquisitions
        adj = corrector._calculate_acquisition_adjustment(
            delisted_count=10, period_years=1.0
        )
        assert adj == 1.0

        # With acquisitions (should increase adjustment)
        adj = corrector._calculate_acquisition_adjustment(
            delisted_count=10, period_years=1.0
        )
        assert adj > 1.0

    def test_convenience_function(self, sample_returns, sample_universe):
        """Test convenience function for backtest adjustment."""
        backtest_start = datetime(2020, 1, 1)
        backtest_end = datetime(2021, 1, 1)

        adjusted_returns, adjustment = adjust_backtest_for_survivorship(
            sample_returns, sample_universe, backtest_start, backtest_end
        )

        assert isinstance(adjusted_returns, pd.Series)
        assert isinstance(adjustment, SurvivorshipAdjustment)
        assert len(adjusted_returns) == len(sample_returns)

    def test_empty_universe_handling(self, corrector):
        """Test handling of empty universe."""
        backtest_start = datetime(2020, 1, 1)
        backtest_end = datetime(2021, 1, 1)

        adjustment = corrector.calculate_survivorship_bias(
            [], backtest_start, backtest_end
        )

        # Should return neutral adjustment
        assert adjustment.surviving_count == 0
        assert adjustment.survivorship_bias_factor == 1.0

    def test_error_handling(self, corrector, sample_universe):
        """Test error handling in calculations."""
        # Invalid dates (end before start)
        backtest_start = datetime(2021, 1, 1)
        backtest_end = datetime(2020, 1, 1)

        adjustment = corrector.calculate_survivorship_bias(
            sample_universe, backtest_start, backtest_end
        )

        # Should handle gracefully
        assert isinstance(adjustment, SurvivorshipAdjustment)


class TestDelistedStockInfo:
    """Test DelistedStockInfo dataclass."""

    def test_creation(self):
        """Test creating DelistedStockInfo."""
        info = DelistedStockInfo(
            symbol="BANKRUPT",
            delisting_date=datetime(2020, 6, 15),
            delisting_reason="bankruptcy",
            last_price=Decimal("0.50"),
            recovery_rate=Decimal("0.10"),
            volatility_before_delisting=0.8,
        )

        assert info.symbol == "BANKRUPT"
        assert info.delisting_reason == "bankruptcy"
        assert info.recovery_rate == Decimal("0.10")


class TestSurvivorshipAdjustment:
    """Test SurvivorshipAdjustment dataclass."""

    def test_creation(self):
        """Test creating SurvivorshipAdjustment."""
        adjustment = SurvivorshipAdjustment(
            total_universe_size=110,
            surviving_count=100,
            delisted_count=10,
            survivorship_bias_factor=1.05,
            bankruptcy_adjustment=0.98,
            acquisition_adjustment=1.02,
            average_delisting_date=datetime(2020, 6, 1),
        )

        assert adjustment.total_universe_size == 110
        assert adjustment.surviving_count == 100
        assert adjustment.delisted_count == 10
        assert adjustment.survivorship_bias_factor == 1.05
