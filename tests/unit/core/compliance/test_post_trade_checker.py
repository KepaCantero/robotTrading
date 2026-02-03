"""
Unit tests for post_trade_checker.py
=====================================

Tests for post-trade compliance checker.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from typing import Tuple
from unittest.mock import Mock, patch

from app.core.compliance.post_trade_checker import PostTradeComplianceChecker
from app.core.compliance.results import PostTradeCheckResult


@pytest.fixture
def checker():
    """Create PostTradeComplianceChecker instance."""
    return PostTradeComplianceChecker()


class TestPostTradeComplianceChecker:
    """Tests for PostTradeComplianceChecker class."""

    def test_init(self, checker):
        """Test checker initialization."""
        assert checker._registry is not None
        assert isinstance(checker._cache, dict)

    def test_check_trade_basic(self, checker):
        """Test basic trade check."""
        result = checker.check_trade(
            order_id="order-1",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
        )
        
        assert isinstance(result, PostTradeCheckResult)
        assert result.order_id == "order-1"
        assert result.symbol == "AAPL"
        assert result.side == "BUY"

    def test_check_trade_with_signal_price(self, checker):
        """Test trade check with signal price."""
        result = checker.check_trade(
            order_id="order-2",
            symbol="MSFT",
            side="SELL",
            quantity=Decimal("50"),
            execution_price=Decimal("200.00"),
            signal_price=Decimal("198.00"),
        )
        
        assert result.symbol == "MSFT"
        # Implementation shortfall would be calculated

    def test_check_trade_with_timestamps(self, checker):
        """Test trade check with execution timing."""
        signal_time = datetime(2024, 1, 1, 10, 0, 0)
        submission_time = datetime(2024, 1, 1, 10, 0, 5)
        execution_time = datetime(2024, 1, 1, 10, 0, 10)
        
        result = checker.check_trade(
            order_id="order-3",
            symbol="GOOGL",
            side="BUY",
            quantity=Decimal("25"),
            execution_price=Decimal("140.00"),
            signal_price=Decimal("139.50"),
            signal_time=signal_time,
            submission_time=submission_time,
            execution_time=execution_time,
        )
        
        assert isinstance(result, PostTradeCheckResult)

    def test_check_trade_with_nbbo(self, checker):
        """Test trade check with NBBO data."""
        nbbo = (Decimal("149.90"), Decimal("150.10"))
        
        result = checker.check_trade(
            order_id="order-4",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
            nbbo_at_execution=nbbo,
        )
        
        assert isinstance(result, PostTradeCheckResult)

    def test_track_slo_compliance_success(self, checker):
        """Test SLO tracking with successful execution."""
        result = checker.track_slo_compliance(
            order_id="order-1",
            latency_ms=50.0,
            fill_rate=100.0,
            error_occurred=False,
        )
        
        assert result["tracked"] is True
        assert result["slo_status"] == "OK"
        assert result["latency_ok"] is True
        assert result["fill_ok"] is True

    def test_track_slo_compliance_violation(self, checker):
        """Test SLO tracking with violations."""
        result = checker.track_slo_compliance(
            order_id="order-2",
            latency_ms=150.0,  # > 100ms threshold
            fill_rate=90.0,    # < 95% threshold
            error_occurred=True,
        )
        
        assert result["tracked"] is True
        assert result["slo_status"] == "VIOLATED"

    def test_get_available_analyses(self, checker):
        """Test getting available post-trade analyses."""
        analyses = checker.get_available_analyses()
        
        assert isinstance(analyses, list)

    def test_calculate_implementation_shortfall_buy(self, checker):
        """Test implementation shortfall calculation for BUY."""
        shortfall = checker.calculate_implementation_shortfall(
            signal_price=Decimal("100.00"),
            execution_price=Decimal("101.00"),
            side="BUY",
        )
        
        # Buy: (execution - signal) / signal * 10000
        expected = float((101 - 100) / 100 * 10000)
        assert shortfall == expected

    def test_calculate_implementation_shortfall_sell(self, checker):
        """Test implementation shortfall calculation for SELL."""
        shortfall = checker.calculate_implementation_shortfall(
            signal_price=Decimal("100.00"),
            execution_price=Decimal("99.00"),
            side="SELL",
        )
        
        # Sell: (signal - execution) / signal * 10000
        expected = float((100 - 99) / 100 * 10000)
        assert shortfall == expected

    def test_calculate_effective_spread(self, checker):
        """Test effective spread calculation."""
        execution_price = Decimal("150.05")
        nbbo = (Decimal("150.00"), Decimal("150.10"))  # bid, ask
        
        spread = checker.calculate_effective_spread(execution_price, nbbo)
        
        # Should calculate spread in bps
        assert isinstance(spread, float)
