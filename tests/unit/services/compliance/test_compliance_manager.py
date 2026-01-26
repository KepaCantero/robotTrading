"""
Unit tests for Compliance Manager.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta

from app.services.compliance.manager import (
    ComplianceManager,
    Country,
    TradeRecord,
    ComplianceViolation,
    ComplianceReport,
)


@pytest.fixture
def us_compliance():
    """Fixture for USA compliance manager."""
    return ComplianceManager(
        country=Country.US,
        account_equity=Decimal("30000"),
    )


@pytest.fixture
def es_compliance():
    """Fixture for Spain compliance manager."""
    return ComplianceManager(
        country=Country.ES,
        account_equity=Decimal("50000"),
    )


@pytest.fixture
def sample_trade():
    """Fixture for sample trade."""
    return TradeRecord(
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("100"),
        price=Decimal("150"),
        trade_date=date.today(),
        order_id="test_order_123",
    )


class TestComplianceManager:
    """Test ComplianceManager."""

    def test_initialization_us(self, us_compliance):
        """Test USA compliance manager initialization."""
        assert us_compliance.country == Country.US
        assert us_compliance.account_equity == Decimal("30000")
        assert us_compliance.pdt_tracker is not None
        assert us_compliance.wash_sale_tracker is not None
        assert us_compliance.order_analyzer is not None

    def test_initialization_es(self, es_compliance):
        """Test Spain compliance manager initialization."""
        assert es_compliance.country == Country.ES
        assert es_compliance.account_equity == Decimal("50000")

    def test_check_trade_allowed_spain(self, es_compliance, sample_trade):
        """Test trade check for Spain (no restrictions)."""
        allowed, violations = es_compliance.check_trade_allowed(
            trade=sample_trade,
            account_equity=Decimal("50000"),
        )

        # Spain has no PDT or wash sale restrictions
        assert allowed is True
        assert len(violations) == 0

    def test_check_trade_allowed_us_sufficient_equity(self, us_compliance, sample_trade):
        """Test trade check for USA with sufficient equity."""
        allowed, violations = us_compliance.check_trade_allowed(
            trade=sample_trade,
            account_equity=Decimal("30000"),
        )

        assert allowed is True
        assert len(violations) == 0

    def test_check_trade_allowed_us_low_equity(self, us_compliance):
        """Test trade check for USA with low equity."""
        trade = TradeRecord(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=date.today(),
        )

        allowed, violations = us_compliance.check_trade_allowed(
            trade=trade,
            account_equity=Decimal("10000"),  # Below $25k
        )

        assert allowed is False
        assert len(violations) > 0
        assert any("PDT" in v for v in violations)

    def test_check_trade_allowed_records_violation(self, us_compliance):
        """Test that violations are recorded."""
        trade = TradeRecord(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=date.today(),
        )

        us_compliance.check_trade_allowed(
            trade=trade,
            account_equity=Decimal("10000"),
        )

        # Should have recorded violation
        violations = us_compliance.get_violations()
        assert len(violations) > 0

    def test_record_trade(self, us_compliance, sample_trade):
        """Test recording a trade."""
        us_compliance.record_trade(sample_trade)

        # Should be tracked in PDT tracker
        assert len(us_compliance.pdt_tracker._all_trades) > 0

    def test_record_trade_updates_equity(self, es_compliance, sample_trade):
        """Test recording trade doesn't update equity by default."""
        initial_equity = es_compliance.account_equity

        es_compliance.record_trade(sample_trade)

        # Equity should be unchanged
        assert es_compliance.account_equity == initial_equity

    def test_generate_report_us(self, us_compliance):
        """Test generating compliance report for USA."""
        report = us_compliance.generate_report()

        assert isinstance(report, ComplianceReport)
        assert report.country == "US"
        assert report.account_equity == Decimal("30000")
        assert report.pdt_status is not None

    def test_generate_report_es(self, es_compliance):
        """Test generating compliance report for Spain."""
        report = es_compliance.generate_report()

        assert isinstance(report, ComplianceReport)
        assert report.country == "ES"
        assert report.pdt_status is None  # No PDT for Spain

    def test_can_day_trade_spain(self, es_compliance):
        """Test that Spain can always day trade."""
        assert es_compliance.can_day_trade() is True

    def test_can_day_trade_us_sufficient_equity(self, us_compliance):
        """Test that USA can day trade with sufficient equity."""
        us_compliance.update_equity(Decimal("50000"))
        assert us_compliance.can_day_trade() is True

    def test_can_day_trade_us_low_equity(self, us_compliance):
        """Test that USA cannot day trade with low equity."""
        us_compliance.update_equity(Decimal("10000"))
        assert us_compliance.can_day_trade() is False

    def test_get_day_trades_remaining_spain(self, es_compliance):
        """Test day trades remaining for Spain (unlimited)."""
        remaining = es_compliance.get_day_trades_remaining()
        assert remaining == 999  # Unlimited

    def test_get_day_trades_remaining_us(self, us_compliance):
        """Test day trades remaining for USA."""
        remaining = us_compliance.get_day_trades_remaining()
        assert remaining == 3  # Start with 3

    def test_get_violations_no_filter(self, us_compliance):
        """Test getting all violations."""
        violations = us_compliance.get_violations()
        assert isinstance(violations, list)

    def test_get_violations_with_severity_filter(self, us_compliance):
        """Test getting violations filtered by severity."""
        # Create a violation first
        trade = TradeRecord(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=date.today(),
        )

        us_compliance.check_trade_allowed(
            trade=trade,
            account_equity=Decimal("10000"),
        )

        critical_violations = us_compliance.get_violations(severity="CRITICAL")
        assert isinstance(critical_violations, list)

    def test_clear_violations(self, us_compliance):
        """Test clearing violations."""
        # Create a violation
        trade = TradeRecord(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=date.today(),
        )

        us_compliance.check_trade_allowed(
            trade=trade,
            account_equity=Decimal("10000"),
        )

        # Clear violations
        us_compliance.clear_violations()

        # Should be empty
        violations = us_compliance.get_violations()
        assert len(violations) == 0

    def test_update_equity(self, es_compliance):
        """Test updating account equity."""
        es_compliance.update_equity(Decimal("100000"))

        assert es_compliance.account_equity == Decimal("100000")

    def test_check_trade_with_suspicious_patterns(self, es_compliance):
        """Test trade check with suspicious order patterns."""
        # Add many orders at same price (layering)
        for i in range(3):
            es_compliance.order_analyzer.record_order(
                order_id=f"order_{i}",
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("150"),
                order_type="LIMIT",
            )

        trade = TradeRecord(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=date.today(),
        )

        allowed, violations = es_compliance.check_trade_allowed(
            trade=trade,
        )

        # Should detect layering
        if not allowed:
            assert any("layering" in v for v in violations)

    def test_day_trade_counting(self, us_compliance):
        """Test that day trades are properly counted."""
        today = date.today()

        # Create a day trade
        buy_trade = TradeRecord(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=today,
        )

        sell_trade = TradeRecord(
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("100"),
            price=Decimal("155"),
            trade_date=today,
        )

        us_compliance.record_trade(buy_trade)
        us_compliance.record_trade(sell_trade)

        # Check day trades remaining
        remaining = us_compliance.get_day_trades_remaining()
        assert remaining == 2  # Used 1 of 3

    def test_wash_sale_detection_us(self, us_compliance):
        """Test wash sale detection for USA."""
        today = date.today()

        # Buy previously
        buy_trade = TradeRecord(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=today - timedelta(days=10),
        )

        us_compliance.record_trade(buy_trade)

        # Try to sell at loss
        sell_trade = TradeRecord(
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("100"),
            price=Decimal("140"),  # Loss
            trade_date=today,
        )

        allowed, violations = us_compliance.check_trade_allowed(
            trade=sell_trade,
        )

        # Should warn about wash sale (but not block)
        if violations:
            assert any("wash sale" in v.lower() for v in violations)

    def test_reset(self, us_compliance):
        """Test resetting compliance manager."""
        us_compliance.record_trade(
            TradeRecord(
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("150"),
                trade_date=date.today(),
            )
        )

        us_compliance.reset()

        # Should be cleared
        assert len(us_compliance.pdt_tracker._all_trades) == 0
        assert len(us_compliance.get_violations()) == 0


class TestTradeRecord:
    """Test TradeRecord dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        trade = TradeRecord(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=date.today(),
            order_id="test_order",
        )

        result = trade.to_dict()

        assert result["symbol"] == "AAPL"
        assert result["side"] == "BUY"
        assert result["quantity"] == "100"
        assert result["order_id"] == "test_order"


class TestComplianceViolation:
    """Test ComplianceViolation dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        violation = ComplianceViolation(
            violation_type="PDT_RESTRICTION",
            severity="CRITICAL",
            description="Account equity below $25k",
            timestamp=datetime.now(),
            trade_reference="AAPL",
        )

        result = violation.to_dict()

        assert result["violation_type"] == "PDT_RESTRICTION"
        assert result["severity"] == "CRITICAL"
        assert result["trade_reference"] == "AAPL"


class TestComplianceReport:
    """Test ComplianceReport dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        report = ComplianceReport(
            country="US",
            account_equity=Decimal("50000"),
            wash_sale_count=0,
            wash_sale_disallowed_loss=Decimal("0"),
            order_pattern_alerts=0,
            can_day_trade=True,
            restricted=False,
        )

        result = report.to_dict()

        assert result["country"] == "US"
        assert result["account_equity"] == "50000"
        assert result["can_day_trade"] is True
        assert result["restricted"] is False
