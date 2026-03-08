"""
Test validation for fix applied at line 3289 in comprehensive_backtest_runner.py

Fix: Changed `quotes=` to `market_data=` parameter in split_data() call

This test validates:
1. The fix won't cause runtime errors
2. The parameter name matches the function signature
3. Quote objects with timestamp attribute work correctly
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.backtesting.data_split import DataSplit, TrainValTestSplitter
from app.domain.models.market_data import Quote


class TestLine3289Fix:
    """Test suite for validating the fix at line 3289."""

    def test_split_data_accepts_market_data_parameter(self):
        """Test that split_data accepts market_data as keyword argument."""
        splitter = TrainValTestSplitter()

        # Create mock Quote objects (Pydantic models with timestamp attribute)
        quotes = [
            Quote(
                symbol="TEST",
                timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                bid=Decimal("100.0"),
                ask=Decimal("100.5"),
                last=Decimal("100.25"),
                volume=Decimal("1000"),
            )
            for i in range(100)
        ]

        # This is the fixed call - using market_data= parameter
        train, val, test = splitter.split_data(
            market_data=quotes,  # This is the fix
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 3, 1),
        )

        # Verify split worked correctly
        assert len(train) > 0
        assert len(val) > 0
        assert len(test) > 0
        assert len(train) + len(val) + len(test) <= 100

    def test_split_data_with_quotes_attribute_name(self):
        """Test using the actual attribute name from ComprehensiveBacktestRunner."""
        splitter = TrainValTestSplitter(DataSplit(train_pct=0.6, val_pct=0.2, test_pct=0.2))

        # Simulate self.quotes from ComprehensiveBacktestRunner
        quotes = [
            Quote(
                symbol="AAPL",
                timestamp=datetime(2024, 1, 1) + timedelta(hours=i),
                bid=Decimal(str(150 + i)),
                ask=Decimal(str(150.5 + i)),
                last=Decimal(str(150.25 + i)),
                volume=Decimal("10000"),
            )
            for i in range(500)
        ]

        # This mimics the actual call at line 3288-3292
        train_quotes, val_quotes, test_quotes = splitter.split_data(
            market_data=quotes,
            start_date=datetime.strptime("2024-01-01", "%Y-%m-%d"),
            end_date=datetime.strptime("2024-01-31", "%Y-%m-%d"),
        )

        # Verify the split
        assert len(train_quotes) > 0
        assert len(val_quotes) > 0
        assert len(test_quotes) > 0

        # Verify temporal order (train <= val <= test)
        if train_quotes and val_quotes:
            assert train_quotes[-1].timestamp <= val_quotes[0].timestamp
        if val_quotes and test_quotes:
            assert val_quotes[-1].timestamp <= test_quotes[0].timestamp

    def test_split_data_preserves_quote_properties(self):
        """Test that Quote object properties are preserved after splitting."""
        splitter = TrainValTestSplitter()

        quotes = [
            Quote(
                symbol=f"SYM{i % 3}",
                timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                bid=Decimal("100.0"),
                ask=Decimal("101.0"),
                last=Decimal("100.5"),
                volume=Decimal(f"{i * 100}"),
            )
            for i in range(100)
        ]

        train, val, test = splitter.split_data(market_data=quotes)

        # All returned items should still be Quote objects
        all_items = train + val + test
        assert all(isinstance(item, Quote) for item in all_items)

        # All should have required attributes
        assert all(hasattr(item, 'timestamp') for item in all_items)
        assert all(hasattr(item, 'symbol') for item in all_items)
        assert all(hasattr(item, 'bid') for item in all_items)
        assert all(hasattr(item, 'ask') for item in all_items)
        assert all(hasattr(item, 'last') for item in all_items)

    def test_parameter_signature_matches(self):
        """Test that the parameter name matches the actual function signature."""
        import inspect

        from app.backtesting.data_split import TrainValTestSplitter

        sig = inspect.signature(TrainValTestSplitter.split_data)
        params = list(sig.parameters.keys())

        # First parameter after 'self' should be 'market_data'
        assert params[0] == 'self'
        assert params[1] == 'market_data'
        assert 'start_date' in params
        assert 'end_date' in params

    def test_positional_argument_still_works(self):
        """Test that positional argument still works (backward compatibility)."""
        splitter = TrainValTestSplitter()

        quotes = [
            Quote(
                symbol="TEST",
                timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                bid=Decimal("100.0"),
                ask=Decimal("100.5"),
                last=Decimal("100.25"),
                volume=Decimal("1000"),
            )
            for i in range(100)
        ]

        # Positional argument should still work
        train, val, test = splitter.split_data(quotes)

        assert len(train) + len(val) + len(test) == 100


class TestEdgeCasesForLine3289Fix:
    """Test edge cases related to the fix."""

    def test_empty_quotes_with_market_data_param(self):
        """Test that empty quotes raises ValueError with market_data parameter."""
        splitter = TrainValTestSplitter()

        with pytest.raises(ValueError, match="Market data is empty"):
            splitter.split_data(market_data=[])

    def test_date_filtering_with_market_data_param(self):
        """Test date filtering works correctly with market_data parameter."""
        splitter = TrainValTestSplitter()

        quotes = [
            Quote(
                symbol="TEST",
                timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                bid=Decimal("100.0"),
                ask=Decimal("100.5"),
                last=Decimal("100.25"),
                volume=Decimal("1000"),
            )
            for i in range(100)
        ]

        # Filter to only include days 10-50
        start = datetime(2024, 1, 11)
        end = datetime(2024, 1, 20)

        train, val, test = splitter.split_data(market_data=quotes, start_date=start, end_date=end)

        # All items should be within date range
        all_items = train + val + test
        for item in all_items:
            assert start <= item.timestamp <= end

    def test_all_quotes_outside_date_range(self):
        """Test when all quotes are outside the specified date range."""
        splitter = TrainValTestSplitter()

        quotes = [
            Quote(
                symbol="TEST",
                timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                bid=Decimal("100.0"),
                ask=Decimal("100.5"),
                last=Decimal("100.25"),
                volume=Decimal("1000"),
            )
            for i in range(100)
        ]

        # Date range that doesn't overlap with quotes
        with pytest.raises(ValueError, match="No data after applying date filters"):
            splitter.split_data(
                market_data=quotes, start_date=datetime(2025, 1, 1), end_date=datetime(2025, 12, 31)
            )
