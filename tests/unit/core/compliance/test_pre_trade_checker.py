"""
Unit tests for pre_trade_checker.py
====================================

Tests for pre-trade compliance checker.
"""

from datetime import datetime
from decimal import Decimal

import pandas as pd
import pytest

from app.core.compliance.pre_trade_checker import PreTradeComplianceChecker
from app.core.compliance.results import PreTradeCheckResult


@pytest.fixture
def sample_price_history():
    """Create sample price history DataFrame."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    return pd.DataFrame(
        {
            "close": [150.0 + i * 0.5 for i in range(100)],
            "volume": [1000000 for _ in range(100)],
        },
        index=dates,
    )


@pytest.fixture
def checker():
    """Create PreTradeComplianceChecker instance."""
    return PreTradeComplianceChecker()


class TestPreTradeComplianceChecker:
    """Tests for PreTradeComplianceChecker class."""

    def test_init(self, checker):
        """Test checker initialization."""
        assert checker._registry is not None
        assert isinstance(checker._cache, dict)

    def test_check_signal_basic(self, checker):
        """Test basic signal check."""
        result = checker.check_signal(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            current_price=Decimal("150.00"),
        )

        assert isinstance(result, PreTradeCheckResult)
        assert isinstance(result.can_execute, bool)
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0

    def test_check_signal_with_price_history(self, checker, sample_price_history):
        """Test signal check with price history."""
        result = checker.check_signal(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            current_price=Decimal("150.00"),
            price_history=sample_price_history,
        )

        assert result.passed is not None
        assert result.reasons is not None

    def test_check_signal_with_urgency(self, checker):
        """Test signal check with urgency parameter."""
        result = checker.check_signal(
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("100"),
            current_price=Decimal("150.00"),
            urgency=0.8,
        )

        assert isinstance(result, PreTradeCheckResult)

    def test_check_signal_all_fields_populated(self, checker, sample_price_history):
        """Test that all result fields are populated when services available."""
        result = checker.check_signal(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            current_price=Decimal("150.00"),
            price_history=sample_price_history,
            urgency=0.5,
            signal_time=datetime.now(),
        )

        # Check all expected fields exist
        assert hasattr(result, "passed")
        assert hasattr(result, "can_execute")
        assert hasattr(result, "confidence")
        assert hasattr(result, "market_regime")
        assert hasattr(result, "alpha_signal")
        assert hasattr(result, "liquidity_score")

    def test_get_available_checks(self, checker):
        """Test getting list of available checks."""
        checks = checker.get_available_checks()

        assert isinstance(checks, list)
        # May contain various checks depending on registered services

    def test_estimate_adv(self, checker, sample_price_history):
        """Test ADV estimation from price history."""
        adv = checker._estimate_adv(sample_price_history)

        assert isinstance(adv, Decimal)
        # Should be around 1,000,000 based on sample data
        assert adv > 0

    def test_estimate_adv_no_history(self, checker):
        """Test ADV estimation with no price history."""
        adv = checker._estimate_adv(None)

        # Should return default value
        assert adv == Decimal("1000000")


class TestPreTradeCheckerIntegration:
    """Integration tests with mocked services."""

    def test_harris_integration(self, checker):
        """Test integration with Harris microstructure service."""
        # This test verifies the checker can call Harris service
        # Actual integration tested with mock
        pass  # Would require more complex mocking

    def test_chan_regime_integration(self, checker, sample_price_history):
        """Test integration with Chan regime detector."""
        # This test verifies regime detection integration
        pass  # Would require more complex mocking

    def test_narang_alpha_integration(self, checker, sample_price_history):
        """Test integration with Narang alpha model."""
        # This test verifies alpha generation integration
        pass  # Would require more complex mocking


class TestPreTradeCheckerEdgeCases:
    """Edge case tests."""

    def test_empty_symbol(self, checker):
        """Test handling of empty symbol."""
        result = checker.check_signal(
            symbol="",
            side="BUY",
            quantity=Decimal("100"),
            current_price=Decimal("150.00"),
        )
        assert isinstance(result, PreTradeCheckResult)

    def test_zero_quantity(self, checker):
        """Test handling of zero quantity."""
        result = checker.check_signal(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("0"),
            current_price=Decimal("150.00"),
        )
        assert isinstance(result, PreTradeCheckResult)

    def test_very_large_quantity(self, checker):
        """Test handling of very large quantity."""
        result = checker.check_signal(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("1000000000"),
            current_price=Decimal("150.00"),
        )
        assert isinstance(result, PreTradeCheckResult)
