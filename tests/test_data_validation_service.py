"""
Tests for Data Validation Service - TASK-DV-1, DV-2, DV-3, DV-4

Tests all data quality checks:
- Gap detection (>5%)
- Outlier identification (z-score >3)
- OHLC consistency validation
- Pre-backtest data quality checks
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.services.data_validation_service import (
    DataValidationService,
    OHLCData,
    DataQualityIssue,
)


class TestDataValidationService:
    """Tests for Data Validation Service."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return DataValidationService(
            gap_threshold=0.05,
            outlier_zscore_threshold=3.0,
            consistency_tolerance=0.01,
        )

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLC data."""
        base_date = datetime(2024, 1, 1)
        data = []

        # Create 100 days of normal data
        for i in range(100):
            close_price = Decimal("100") + Decimal(str(i * 0.1))
            data.append(
                OHLCData(
                    timestamp=base_date + timedelta(days=i),
                    open=close_price - Decimal("0.5"),
                    high=close_price + Decimal("1.0"),
                    low=close_price - Decimal("1.0"),
                    close=close_price,
                    volume=Decimal("1000000"),
                )
            )
        return data

    def test_detect_price_gaps_no_gaps(self, service, sample_data):
        """TASK-DV-1: Test gap detection with no gaps."""
        issues = service.detect_price_gaps(sample_data, "TEST")
        assert len(issues) == 0

    def test_detect_price_gaps_with_gap(self, service):
        """TASK-DV-1: Test gap detection with gap >5%."""
        data = [
            OHLCData(
                timestamp=datetime(2024, 1, 1),
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
                volume=Decimal("1000"),
            ),
            OHLCData(
                timestamp=datetime(2024, 1, 2),
                open=Decimal("110"),  # Gap of 10% (>5%)
                high=Decimal("111"),
                low=Decimal("109"),
                close=Decimal("110"),
                volume=Decimal("1000"),
            ),
        ]
        issues = service.detect_price_gaps(data, "TEST")
        assert len(issues) == 1
        assert issues[0].issue_type == "price_gap"
        assert issues[0].severity == "warning"
        assert issues[0].details["gap_percentage"] > 5

    def test_identify_outliers_no_outliers(self, service, sample_data):
        """TASK-DV-2: Test outlier identification with no outliers."""
        issues = service.identify_outliers(sample_data, "TEST")
        assert len(issues) == 0

    def test_identify_outliers_with_outlier(self, service):
        """TASK-DV-2: Test outlier identification with outlier (z-score >3)."""
        # Create data with one extreme outlier
        data = []
        base_date = datetime(2024, 1, 1)
        base_price = Decimal("100")

        # Normal prices
        for i in range(20):
            price = base_price + Decimal(str(i * 0.1))
            data.append(
                OHLCData(
                    timestamp=base_date + timedelta(days=i),
                    open=price,
                    high=price + Decimal("0.5"),
                    low=price - Decimal("0.5"),
                    close=price,
                    volume=Decimal("1000"),
                )
            )

        # Add extreme outlier
        data.append(
            OHLCData(
                timestamp=base_date + timedelta(days=20),
                open=Decimal("200"),  # Massive jump
                high=Decimal("201"),
                low=Decimal("199"),
                close=Decimal("200"),
                volume=Decimal("1000"),
            )
        )

        issues = service.identify_outliers(data, "TEST")
        assert len(issues) >= 1  # Should detect at least one outlier

    def test_validate_ohlc_consistency_valid(self, service, sample_data):
        """TASK-DV-3: Test OHLC consistency with valid data."""
        issues = service.validate_ohlc_consistency(sample_data, "TEST")
        assert len(issues) == 0

    def test_validate_ohlc_consistency_invalid_high_low(self, service):
        """TASK-DV-3: Test OHLC consistency with invalid high < low."""
        data = [
            OHLCData(
                timestamp=datetime(2024, 1, 1),
                open=Decimal("100"),
                high=Decimal("99"),  # Invalid: high < low
                low=Decimal("101"),
                close=Decimal("100"),
                volume=Decimal("1000"),
            ),
        ]
        issues = service.validate_ohlc_consistency(data, "TEST")
        # Should detect high < low error
        assert len(issues) >= 1
        assert any(i.issue_type == "consistency_error" for i in issues)
        assert any(i.severity == "critical" for i in issues)

    def test_validate_ohlc_consistency_invalid_open(self, service):
        """TASK-DV-3: Test OHLC consistency with open outside [low, high]."""
        data = [
            OHLCData(
                timestamp=datetime(2024, 1, 1),
                open=Decimal("110"),  # Invalid: outside [low, high]
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
                volume=Decimal("1000"),
            ),
        ]
        issues = service.validate_ohlc_consistency(data, "TEST")
        assert len(issues) >= 1
        assert any(i.issue_type == "consistency_error" for i in issues)

    def test_validate_data_quality_complete_check(self, service, sample_data):
        """TASK-DV-4: Test complete data quality check."""
        report = service.validate_data_quality(sample_data, "TEST")
        assert report.symbol == "TEST"
        assert report.total_records == 100
        assert report.is_valid is True
        assert report.quality_score > 90  # High quality data

    def test_validate_data_quality_with_issues(self, service):
        """TASK-DV-4: Test complete check with quality issues."""
        data = []
        base_date = datetime(2024, 1, 1)
        base_price = Decimal("100")

        # Add some valid data
        for i in range(10):
            price = base_price + Decimal(str(i * 0.1))
            data.append(
                OHLCData(
                    timestamp=base_date + timedelta(days=i),
                    open=price,
                    high=price + Decimal("0.5"),
                    low=price - Decimal("0.5"),
                    close=price,
                    volume=Decimal("1000"),
                )
            )

        # Add data with gap
        data.append(
            OHLCData(
                timestamp=base_date + timedelta(days=10),
                open=Decimal("120"),  # 20% gap
                high=Decimal("121"),
                low=Decimal("119"),
                close=Decimal("120"),
                volume=Decimal("1000"),
            )
        )

        report = service.validate_data_quality(data, "TEST")
        assert report.gaps_detected > 0
        assert report.quality_score < 100

    def test_validate_bulk_data(self, service, sample_data):
        """Test bulk data validation for multiple symbols."""
        data_dict = {
            "AAPL": sample_data,
            "MSFT": sample_data,
            "GOOGL": sample_data,
        }
        reports = service.validate_bulk_data(data_dict)

        assert len(reports) == 3
        assert "AAPL" in reports
        assert "MSFT" in reports
        assert "GOOGL" in reports

        for symbol, report in reports.items():
            assert report.symbol == symbol
            assert report.total_records == 100
