"""
Tests for universe manager with survivorship bias adjustment.
"""

from datetime import datetime
from decimal import Decimal

from app.backtesting.universe_manager import BACKTEST_UNIVERSE, UniverseManager
from tests.backtesting.conftest import DEFAULT_SYMBOL


class TestUniverseManager:
    """Test universe manager functionality."""

    # For unittest-style tests that can't use pytest fixtures directly
    default_symbol = DEFAULT_SYMBOL

    def test_initialization(self):
        """Test universe manager initialization."""
        manager = UniverseManager()
        assert manager.universe == BACKTEST_UNIVERSE

    def test_custom_universe(self):
        """Test custom universe configuration."""
        custom_universe = {
            "survivors": [self.default_symbol, "MSFT"],
            "delisted": [],
            "spun_off": [],
            "penny_stocks": [],
        }

        manager = UniverseManager(universe_config=custom_universe)
        assert manager.universe == custom_universe

    def test_get_universe_basic(self):
        """Test getting universe for a period."""
        manager = UniverseManager()

        start_date = datetime(2020, 1, 1)
        end_date = datetime(2024, 12, 31)

        symbols = manager.get_universe(
            start_date=start_date,
            end_date=end_date,
            include_delisted=True,
            include_spun_off=True,
        )

        # Should include survivors
        assert self.default_symbol in symbols
        assert "MSFT" in symbols

        # Should be more than just survivors (includes delisted/spun_off)
        assert len(symbols) > len(BACKTEST_UNIVERSE["survivors"])

    def test_get_universe_excludes_delisted(self):
        """Test excluding delisted companies."""
        manager = UniverseManager()

        start_date = datetime(2000, 1, 1)
        end_date = datetime(2024, 12, 31)

        symbols_with_delisted = manager.get_universe(
            start_date=start_date,
            end_date=end_date,
            include_delisted=True,
            include_spun_off=False,
        )

        symbols_without_delisted = manager.get_universe(
            start_date=start_date,
            end_date=end_date,
            include_delisted=False,
            include_spun_off=False,
        )

        # With delisted should have more symbols
        assert len(symbols_with_delisted) > len(symbols_without_delisted)

    def test_get_universe_time_period(self):
        """Test that universe respects time period."""
        manager = UniverseManager()

        # Period before Toys R Us collapse
        start_date = datetime(2010, 1, 1)
        end_date = datetime(2016, 12, 31)

        symbols = manager.get_universe(
            start_date=start_date,
            end_date=end_date,
            include_delisted=True,
            include_spun_off=True,
        )

        # Should have symbols from this period
        assert len(symbols) > 0

        # Period after Toys R Us collapse (delisted 2017-09-18)
        start_date = datetime(2018, 1, 1)
        end_date = datetime(2024, 12, 31)

        symbols = manager.get_universe(
            start_date=start_date,
            end_date=end_date,
            include_delisted=True,
            include_spun_off=True,
        )

        # Toys R Us should NOT be included (already delisted)
        assert "TWXQ" not in symbols

    def test_filter_by_market_cap(self):
        """Test filtering by market cap."""
        manager = UniverseManager()

        symbols = [self.default_symbol, "MSFT", "GE", "F", "C"]

        # Filter to large caps only
        large_caps = manager.filter_by_market_cap(
            symbols=symbols,
            min_market_cap=Decimal("200"),  # $200B+
        )

        # Should include default_symbol, MSFT but exclude smaller
        assert self.default_symbol in large_caps
        assert "MSFT" in large_caps

        # Test with unknown symbol
        symbols_with_unknown = symbols + ["UNKNOWN"]
        filtered = manager.filter_by_market_cap(
            symbols=symbols_with_unknown,
            min_market_cap=Decimal("100"),
        )

        # Unknown symbols should be excluded
        assert "UNKNOWN" not in filtered

    def test_calculate_survivorship_bias(self):
        """Test survivorship bias calculation."""
        manager = UniverseManager()

        # Mock returns
        survivor_returns = [0.01, 0.02, 0.015, 0.03, 0.025]  # Better returns
        full_universe_returns = [0.005, 0.01, 0.008, 0.015, 0.012]  # Worse returns

        bias_metrics = manager.calculate_survivorship_bias(
            survivor_returns=survivor_returns,
            full_universe_returns=full_universe_returns,
        )

        assert "survivor_cagr" in bias_metrics
        assert "full_universe_cagr" in bias_metrics
        assert "bias_percentage" in bias_metrics
        assert "bias_detected" in bias_metrics

        # Survivor CAGR should be higher
        assert bias_metrics["survivor_cagr"] > bias_metrics["full_universe_cagr"]

        # Bias should be detected
        assert bias_metrics["bias_detected"] == True

    def test_calculate_survivorship_bias_no_bias(self):
        """Test survivorship bias calculation with minimal bias."""
        manager = UniverseManager()

        # Similar returns
        survivor_returns = [0.01, 0.015, 0.012]
        full_universe_returns = [0.01, 0.014, 0.013]

        bias_metrics = manager.calculate_survivorship_bias(
            survivor_returns=survivor_returns,
            full_universe_returns=full_universe_returns,
        )

        # Should not detect significant bias
        assert bias_metrics["bias_detected"] == False

    def test_get_sector_diversification(self):
        """Test getting sector breakdown."""
        manager = UniverseManager()

        symbols = [self.default_symbol, "MSFT", "JPM", "BAC", "XOM"]

        sectors = manager.get_sector_diversification(symbols)

        assert "Technology" in sectors
        assert "Financials" in sectors
        assert "Energy" in sectors

        # Check correct symbols in sectors
        assert self.default_symbol in sectors["Technology"]
        assert "JPM" in sectors["Financials"]
        assert "XOM" in sectors["Energy"]

    def test_get_universe_statistics(self):
        """Test getting universe statistics."""
        manager = UniverseManager()

        stats = manager.get_universe_statistics(
            start_date=datetime(2000, 1, 1),
            end_date=datetime(2024, 12, 31),
        )

        assert "total_symbols" in stats
        assert "sectors" in stats
        assert "delisted_included" in stats
        assert "acquired_included" in stats

        # Should have some symbols
        assert stats["total_symbols"] > 0

        # Should have delisted companies
        assert stats["delisted_included"] > 0

    def test_penny_stock_periods(self):
        """Test penny stock period inclusion."""
        manager = UniverseManager()

        # During financial crisis (2008-2009)
        start_date = datetime(2008, 1, 1)
        end_date = datetime(2009, 12, 31)

        symbols = manager.get_universe(
            start_date=start_date,
            end_date=end_date,
            include_delisted=True,
            include_spun_off=True,
            include_penny_stocks=True,
        )

        # Should include companies that fell to penny status
        # (they're also in survivors, so won't increase count)
        assert len(symbols) > 0

    def test_universe_logging(self, caplog):
        """Test that universe operations log appropriately."""
        import logging

        manager = UniverseManager()

        with caplog.at_level(logging.INFO):
            manager.get_universe(
                start_date=datetime(2020, 1, 1),
                end_date=datetime(2024, 12, 31),
            )

        # Should log universe size
        assert "Universe includes" in caplog.text
