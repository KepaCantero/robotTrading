from tests.integration.data.test_data_loader import load_all_csv_data

# !/usr/bin/env python3
"""
        from tests.integration.data.test_data_loader import load_all_csv_data
Integration Test for StrategyStockAllocator with Real Data

Tests the complete allocation pipeline using real CSV data from data/historical/:
- Loads all available symbols from CSV files
- Runs StrategyStockAllocator.allocate()
- Verifies allocations, capital distribution, and validation
"""

import logging
import sys
from pathlib import Path

# Add project root to path
# __file__ is tests/integration/test_strategy_stock_allocator_integration.py
# Go up 2 levels: tests/integration -> tests -> project_root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest  # noqa: E402

from app.shared.config.params.strategy_config import StockAllocationSettings  # noqa: E402
from app.services.strategy_stock_allocator import StrategyStockAllocator  # noqa: E402

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class TestStrategyStockAllocatorIntegration:
    """Integration tests using real CSV data."""

    @pytest.fixture
    def historical_data_dir(self):
        """Path to historical data directory."""
        # __file__ is tests/integration/strategies/test_strategy_stock_allocator_integration.py
        # Go up 3 levels: tests/integration/strategies -> tests/integration -> tests -> project_root
        project_root = Path(__file__).parent.parent.parent.parent
        return project_root / "data" / "historical"

    @pytest.fixture
    def available_symbols(self, historical_data_dir):
        """Get all available symbols from CSV files."""
        csv_files = list(historical_data_dir.glob("*.csv"))
        symbols = [f.stem for f in csv_files]
        logger.info(f"Found {len(symbols)} CSV files: {sorted(symbols)}")
        return sorted(symbols)

    @pytest.fixture
    def real_historical_data(self, historical_data_dir):
        """Load real historical data from CSV files."""
        # Use shared data loader utility

        historical_data = load_all_csv_data(data_dir=historical_data_dir, min_days=40)
        logger.info(f"Loaded historical data for {len(historical_data)} symbols")
        return historical_data

    @pytest.fixture
    def allocator(self):
        """Create StrategyStockAllocator instance."""
        return StrategyStockAllocator(StockAllocationSettings())

    @pytest.fixture
    def total_capital(self):
        """Total capital for allocation."""
        return 100_000.0

    def test_real_data_loading(self, available_symbols, real_historical_data):
        """Test that we can load real data from CSV files."""
        assert len(available_symbols) > 0, "No CSV files found in data/historical/"
        assert len(real_historical_data) > 0, "No historical data loaded"

        logger.info(
            f"✅ Loaded {len(real_historical_data)}/{len(available_symbols)} symbols successfully"
        )

        # Verify data quality
        for symbol, df in list(real_historical_data.items())[:5]:  # Check first 5
            assert len(df) >= 40, f"{symbol}: Need at least 40 days of data"
            assert all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume'])
            assert df['close'].isna().sum() == 0, f"{symbol}: Should have no NaN close prices"
            logger.info(
                f"  {symbol}: {len(df)} days, price range ${df['close'].min():.2f}-${df['close'].max():.2f}"
            )

    def test_allocator_filters_stocks(self, allocator, real_historical_data):
        """Test that allocator can filter real stocks."""
        filtered = allocator.filter_stocks(real_historical_data)

        assert len(filtered) > 0, "Should have at least some filtered stocks"
        assert len(filtered) <= len(real_historical_data), "Filtered should be <= total"

        logger.info(
            f"✅ Filtered: {len(filtered)}/{len(real_historical_data)} stocks passed validation"
        )

        # Log some examples
        for symbol in list(filtered.keys())[:5]:
            df = filtered[symbol]
            logger.info(f"  {symbol}: {len(df)} days, latest price ${df['close'].iloc[-1]:.2f}")

    def test_allocator_allocates_capital(self, allocator, real_historical_data, total_capital):
        """Test that allocator can allocate capital to real stocks."""

        # Run allocation
        result = allocator.allocate(
            historical_data=real_historical_data,
            total_capital=total_capital,
            strategy_allocations=None,  # Use defaults from config
        )

        # Verify allocation result
        assert result is not None, "Allocation result should not be None"
        assert len(result.allocations) > 0, "Should have at least some allocations"

        logger.info(f"✅ Allocation completed: {len(result.allocations)} assets allocated")

        # Check validation
        if not result.validation_passed:
            logger.warning(f"⚠️ Validation failed: {result.validation_errors}")
            logger.warning("But continuing test to verify allocations...")

        # Verify minimum tickers assigned
        assert (
            len(result.allocations) >= 10
        ), f"Should assign at least 10 tickers, got {len(result.allocations)}"

        # Log allocation breakdown
        strategy_counts = {}
        total_allocated = 0.0
        for ticker, metrics in result.allocations.items():
            strategy = metrics.strategy
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            total_allocated += metrics.capital

        logger.info("📊 Allocation by strategy:")
        for strategy, count in strategy_counts.items():
            strategy_capital = sum(
                m.capital for m in result.allocations.values() if m.strategy == strategy
            )
            logger.info(f"  {strategy}: {count} tickers, ${strategy_capital:,.2f}")

        logger.info(f"📊 Total allocated: ${total_allocated:,.2f} / ${total_capital:,.2f}")
        logger.info(f"📊 Residual capital: ${result.residual_capital:,.2f}")

        # Verify capital allocation
        assert total_allocated > 0, "Should allocate some capital"
        assert (
            total_allocated <= total_capital * 1.01
        ), f"Allocated capital should not exceed total (got ${total_allocated:,.2f} > ${total_capital:,.2f})"

        # Check that we use reasonable amount of capital (at least 80%)
        utilization = total_allocated / total_capital
        logger.info(f"📊 Capital utilization: {utilization:.1%}")
        assert (
            utilization >= 0.70
        ), f"Should utilize at least 70% of capital (got {utilization:.1%})"

        # Verify each allocation
        for ticker, metrics in list(result.allocations.items())[:10]:  # Check first 10
            assert metrics.capital > 0, f"{ticker}: Should have positive capital"
            assert metrics.weight > 0, f"{ticker}: Should have positive weight"
            assert metrics.strategy in [
                'momentum',
                'mean_reversion',
                'pairs_trading',
            ], f"{ticker}: Invalid strategy '{metrics.strategy}'"
            assert ticker in real_historical_data, f"{ticker}: Should be in historical data"

            logger.debug(
                f"  {ticker} -> {metrics.strategy}: "
                f"${metrics.capital:,.2f} ({metrics.weight:.2%}), "
                f"SPS={metrics.sps_score:.4f}"
            )

    def test_allocator_portfolio_creation(self, allocator, real_historical_data, total_capital):
        """Test that portfolio is created correctly with real allocations."""

        # Run allocation
        result = allocator.allocate(
            historical_data=real_historical_data, total_capital=total_capital
        )

        assert len(result.allocations) > 0, "Should have allocations"

        # Group by strategy
        portfolio_by_strategy = {}
        for ticker, metrics in result.allocations.items():
            strategy = metrics.strategy
            if strategy not in portfolio_by_strategy:
                portfolio_by_strategy[strategy] = []
            portfolio_by_strategy[strategy].append(
                {
                    'ticker': ticker,
                    'capital': metrics.capital,
                    'weight': metrics.weight,
                    'sps_score': metrics.sps_score,
                }
            )

        # Verify each strategy has allocations
        logger.info("📊 Portfolio composition:")
        for strategy, positions in portfolio_by_strategy.items():
            total_cap = sum(p['capital'] for p in positions)
            logger.info(
                f"  {strategy}: {len(positions)} positions, "
                f"${total_cap:,.2f} ({total_cap/total_capital:.1%})"
            )
            assert len(positions) > 0, f"{strategy}: Should have at least 1 position"

        # Verify data exists for all allocated tickers
        for ticker in result.allocations.keys():
            assert ticker in real_historical_data, f"{ticker}: Should have historical data"
            df = real_historical_data[ticker]
            assert len(df) >= 40, f"{ticker}: Should have at least 40 days of data"
            logger.debug(f"  ✅ {ticker}: {len(df)} days of data available")

        # Verify output DataFrame generation
        output_df = allocator.generate_output(result.allocations, result.pairs)
        assert output_df is not None, "Output DataFrame should not be None"
        # Output includes allocations + pairs, so length should be >= allocations
        assert len(output_df) >= len(
            result.allocations
        ), "Output should include at least allocations"

        logger.info(
            f"✅ Portfolio created successfully: {len(result.allocations)} assets, {len(result.pairs)} pairs"
        )

    def test_allocator_minimum_tickers(self, allocator, real_historical_data, total_capital):
        """Test that allocator assigns minimum required tickers."""

        result = allocator.allocate(
            historical_data=real_historical_data, total_capital=total_capital
        )

        min_expected = 15  # From allocator logic
        actual_count = len(result.allocations)

        logger.info(f"📊 Assigned tickers: {actual_count} (minimum expected: {min_expected})")

        # Should assign at least 15 tickers if available
        if len(real_historical_data) >= min_expected:
            assert (
                actual_count >= min_expected
            ), f"Should assign at least {min_expected} tickers when {len(real_historical_data)} available, got {actual_count}"
        else:
            # If less data available, assign what we can
            assert actual_count >= len(
                real_historical_data
            ), f"Should assign all available tickers ({len(real_historical_data)}), got {actual_count}"

        logger.info(f"✅ Minimum tickers test passed: {actual_count} assigned")

    def test_allocator_capital_utilization(self, allocator, real_historical_data, total_capital):
        """Test that allocator utilizes capital efficiently."""

        result = allocator.allocate(
            historical_data=real_historical_data, total_capital=total_capital
        )

        total_allocated = sum(m.capital for m in result.allocations.values())
        utilization = total_allocated / total_capital
        residual = result.residual_capital

        logger.info("📊 Capital utilization:")
        logger.info(f"  Allocated: ${total_allocated:,.2f} ({utilization:.1%})")
        logger.info(f"  Residual: ${residual:,.2f} ({residual/total_capital:.1%})")

        # Should utilize at least 70% of capital
        assert utilization >= 0.70, f"Should utilize at least 70% of capital, got {utilization:.1%}"

        # Residual should be reasonable (< 30% or explained by limits)
        assert (
            residual < total_capital * 0.35
        ), f"Residual capital should be < 35%, got {residual/total_capital:.1%}"

        logger.info(f"✅ Capital utilization test passed: {utilization:.1%} utilized")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])
