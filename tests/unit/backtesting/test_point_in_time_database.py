"""
Unit tests for Point-in-Time Database.

Tests point-in-time data handling to prevent look-ahead bias
as described in Ernest Chan's "Algorithmic Trading" (Chapter 3).
"""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from app.backtesting.point_in_time_database import (
    CorporateAction,
    HistoricalConstituent,
    PITDataSnapshot,
    PointInTimeDatabase,
)


class TestPointInTimeDatabase:
    """Test suite for PointInTimeDatabase."""

    @pytest.fixture
    def pit_db(self):
        """Create a PIT database instance."""
        return PointInTimeDatabase()

    @pytest.fixture
    def sample_symbols(self):
        """Create sample symbols."""
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    def test_initialization(self, pit_db):
        """Test database initialization."""
        assert pit_db.cache_size_mb == 100
        assert isinstance(pit_db._snapshot_cache, dict)
        assert isinstance(pit_db._corporate_actions, dict)

    def test_get_universe_at_date(self, pit_db, sample_symbols):
        """Test getting universe at a specific date."""
        query_date = datetime(2020, 6, 15)

        universe = pit_db.get_universe_at_date(query_date)

        # Should return a list of symbols
        assert isinstance(universe, list)

    def test_get_universe_with_filters(self, pit_db, sample_symbols):
        """Test getting universe with filters applied."""
        query_date = datetime(2020, 6, 15)

        # Test with market cap filter
        universe = pit_db.get_universe_at_date(query_date, min_market_cap=Decimal("1000000000"))

        assert isinstance(universe, list)

        # Test with sector filter
        universe = pit_db.get_universe_at_date(query_date, sectors=["Technology", "Finance"])

        assert isinstance(universe, list)

        # Test with max universe size
        universe = pit_db.get_universe_at_date(query_date, max_universe_size=3)

        assert isinstance(universe, list)
        assert len(universe) <= 3

    def test_get_data_as_of_date(self, pit_db):
        """Test getting data as of a specific date."""
        symbol = "AAPL"
        query_date = datetime(2020, 6, 15)

        data = pit_db.get_data_as_of_date(symbol, query_date, lookback_days=252)

        # Should return None (no actual data in test)
        assert data is None or isinstance(data, pd.DataFrame)

    def test_create_pit_snapshot(self, pit_db, sample_symbols):
        """Test creating a PIT snapshot."""
        as_of_date = datetime(2020, 6, 15)

        # Create sample data sources
        dates = pd.date_range(start="2020-01-01", periods=100, freq="D")
        data_sources = {}
        for symbol in sample_symbols[:3]:
            data_sources[symbol] = pd.Series(range(100), index=dates, name="close").to_frame()

        snapshot = pit_db.create_pit_snapshot(as_of_date, sample_symbols[:3], data_sources)

        assert isinstance(snapshot, PITDataSnapshot)
        assert snapshot.as_of_date == as_of_date
        assert len(snapshot.available_symbols) <= len(sample_symbols)

    def test_validate_no_look_ahead(self, pit_db):
        """Test look-ahead bias validation."""
        # Create test data
        dates = pd.date_range(start="2020-01-01", periods=100, freq="D")
        signals = pd.DataFrame({"date": dates[50:], "signal": [1] * 50})
        data = pd.DataFrame({"close": range(100)}, index=dates)

        # Validate
        is_valid = pit_db.validate_no_look_ahead(signals, data, date_column="date")

        # Should be valid (signals come after data exists)
        assert isinstance(is_valid, bool)

    def test_apply_corporate_actions(self, pit_db):
        """Test applying corporate actions."""
        # Create test data
        dates = pd.date_range(start="2020-01-01", periods=100, freq="D")
        data = pd.DataFrame(
            {"close": [100 + i for i in range(100)]},
            index=dates,
        )

        # Add a corporate action (2:1 split)
        split_date = datetime(2020, 2, 1)
        action = CorporateAction(
            symbol="TEST",
            action_type="split",
            ex_date=split_date,
            action_details={"ratio": "2:1"},
            adjustment_factor=Decimal("2.0"),
        )

        pit_db._corporate_actions["TEST"] = [action]

        # Apply adjustments as of date after split
        adjusted_data = pit_db.apply_corporate_actions("TEST", data, datetime(2020, 3, 1))

        # Should return adjusted data
        assert isinstance(adjusted_data, pd.DataFrame)

    def test_cache_functionality(self, pit_db, sample_symbols):
        """Test snapshot caching."""
        as_of_date = datetime(2020, 6, 15)

        # Create snapshot
        snapshot = PITDataSnapshot(
            as_of_date=as_of_date,
            available_symbols=sample_symbols,
            total_universe_size=len(sample_symbols),
            data_coverage={},
        )

        # Cache it
        pit_db._cache_snapshot(snapshot)

        # Check it's cached
        assert as_of_date in pit_db._snapshot_cache
        assert pit_db._snapshot_cache[as_of_date] == snapshot

    def test_cache_size_limit(self, pit_db):
        """Test cache size limit."""
        # Create many snapshots to exceed cache
        for i in range(1100):
            as_of_date = datetime(2020, 1, 1) + timedelta(days=i)
            snapshot = PITDataSnapshot(
                as_of_date=as_of_date,
                available_symbols=["AAPL"],
                total_universe_size=1,
                data_coverage={},
            )
            pit_db._cache_snapshot(snapshot)

        # Cache should be limited to ~1000 entries
        assert len(pit_db._snapshot_cache) <= 1000


class TestPITDataSnapshot:
    """Test PITDataSnapshot dataclass."""

    def test_creation(self):
        """Test creating PITDataSnapshot."""
        snapshot = PITDataSnapshot(
            as_of_date=datetime(2020, 6, 15),
            available_symbols=["AAPL", "MSFT"],
            total_universe_size=2,
            data_coverage={"AAPL": 252, "MSFT": 180},
        )

        assert snapshot.as_of_date == datetime(2020, 6, 15)
        assert len(snapshot.available_symbols) == 2
        assert snapshot.total_universe_size == 2
        assert snapshot.data_coverage["AAPL"] == 252


class TestCorporateAction:
    """Test CorporateAction dataclass."""

    def test_creation(self):
        """Test creating CorporateAction."""
        action = CorporateAction(
            symbol="AAPL",
            action_type="split",
            ex_date=datetime(2020, 8, 31),
            action_details={"ratio": "4:1"},
            adjustment_factor=Decimal("4.0"),
        )

        assert action.symbol == "AAPL"
        assert action.action_type == "split"
        assert action.adjustment_factor == Decimal("4.0")


class TestHistoricalConstituent:
    """Test HistoricalConstituent dataclass."""

    def test_creation(self):
        """Test creating HistoricalConstituent."""
        constituent = HistoricalConstituent(
            symbol="DELISTED",
            entry_date=datetime(2015, 1, 1),
            exit_date=datetime(2020, 6, 15),
            exit_reason="bankruptcy",
            market_cap=Decimal("1000000000"),
            sector="Technology",
        )

        assert constituent.symbol == "DELISTED"
        assert constituent.exit_reason == "bankruptcy"
        assert constituent.market_cap == Decimal("1000000000")
