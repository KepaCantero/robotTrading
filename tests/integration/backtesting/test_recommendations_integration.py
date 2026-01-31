"""
Integration test for multiple testing correction, survivorship bias adjustment, and expectancy.

This test demonstrates the complete workflow for robust backtesting with all three
critical improvements integrated together.
"""

import pytest
from datetime import datetime
from decimal import Decimal

from app.backtesting.data_split import (
    MultipleTestingCorrector,
    TrainValTestSplitter,
    validate_out_of_sample_performance,
)
from app.backtesting.metrics import calculate_expectancy
from app.backtesting.models import Trade, TradeStatus
from app.backtesting.universe_manager import UniverseManager


class MockQuote:
    """Mock quote for testing."""

    def __init__(self, timestamp, symbol="TEST", close=100.0):
        self.timestamp = timestamp
        self.close = close
        self.symbol = symbol


class TestRecommendationsIntegration:
    """Integration test for all three recommendations."""

    def test_full_workflow_with_all_recommendations(self):
        """
        Test complete workflow integrating:
        1. Multiple testing correction
        2. Survivorship bias adjustment
        3. Expectancy calculation
        """
        # Step 1: Create survivorship-bias-adjusted universe
        manager = UniverseManager()
        start_date = datetime(2010, 1, 1)
        end_date = datetime(2024, 12, 31)

        universe_symbols = manager.get_universe(
            start_date=start_date,
            end_date=end_date,
            include_delisted=True,
            include_spun_off=True,
            include_penny_stocks=False,
        )

        # Should have more than just survivors
        assert len(universe_symbols) > len(manager.universe["survivors"])

        # Step 2: Split data to prevent overfitting
        splitter = TrainValTestSplitter()

        # Create mock data
        quotes = []
        base_time = datetime(2020, 1, 1)
        for i in range(1000):
            quotes.append(
                MockQuote(
                    timestamp=base_time + timedelta(hours=i),
                    symbol=universe_symbols[i % len(universe_symbols)],
                )
            )

        train_quotes, val_quotes, test_quotes = splitter.split_data(quotes)

        # Verify proper split
        assert len(train_quotes) + len(val_quotes) + len(test_quotes) == len(quotes)
        assert len(train_quotes) > len(val_quotes)
        assert len(val_quotes) >= len(test_quotes)  # Can be equal with 70/15/15 split

        # Step 3: Simulate multiple parameter tests
        param_results = []
        for i in range(20):  # 20 parameter combinations
            # Simulate Sharpe ratios (some good, some bad)
            import random

            train_sharpe = random.uniform(0.5, 2.5)
            val_sharpe = train_sharpe * random.uniform(0.7, 1.1)
            test_sharpe = val_sharpe * random.uniform(0.6, 1.0)

            param_results.append(
                {
                    "params": {"param_set": i},
                    "train_sharpe": train_sharpe,
                    "val_sharpe": val_sharpe,
                    "test_sharpe": test_sharpe,
                }
            )

        # Step 4: Apply multiple testing correction
        corrector = MultipleTestingCorrector(num_tests=20, base_confidence=0.95)
        adjusted_confidence = corrector.bonferroni_correction()

        # Should be much lower than base 95%
        assert adjusted_confidence < 0.20

        # Step 5: Select best parameters based on validation performance
        best_result = max(param_results, key=lambda x: x["val_sharpe"])

        # Step 6: Validate OOS performance
        oos_valid = validate_out_of_sample_performance(
            train_sharpe=best_result["train_sharpe"],
            val_sharpe=best_result["val_sharpe"],
            test_sharpe=best_result["test_sharpe"],
            min_performance_ratio=0.7,
        )

        # Step 7: Calculate expectancy for the best strategy
        # Create mock trades
        winning_trades = []
        losing_trades = []

        for i in range(50):
            if i < 20:  # 40% win rate
                trade = Trade(
                    trade_id=f"win_{i}",
                    symbol="AAPL",
                    side="buy",
                    quantity=Decimal("100"),
                    entry_price=Decimal("100"),
                    exit_price=Decimal("110"),
                    entry_time=datetime(2024, 1, 1),
                    exit_time=datetime(2024, 1, 2),
                    status=TradeStatus.CLOSED,
                    pnl=Decimal("500"),
                )
                winning_trades.append(trade)
            else:
                trade = Trade(
                    trade_id=f"loss_{i}",
                    symbol="AAPL",
                    side="buy",
                    quantity=Decimal("100"),
                    entry_price=Decimal("100"),
                    exit_price=Decimal("95"),
                    entry_time=datetime(2024, 1, 3),
                    exit_time=datetime(2024, 1, 4),
                    status=TradeStatus.CLOSED,
                    pnl=Decimal("-300"),
                )
                losing_trades.append(trade)

        expectancy = calculate_expectancy(winning_trades, losing_trades)

        # Verify all three recommendations worked together
        assert len(universe_symbols) > 10  # Survivorship bias adjustment
        assert adjusted_confidence < 0.20  # Multiple testing correction
        assert expectancy > 0  # Positive expectancy

        # The complete workflow provides a robust evaluation
        print(f"\n=== Integration Test Results ===")
        print(f"Universe size (with survivorship adjustment): {len(universe_symbols)}")
        print(f"Adjusted confidence (Bonferroni): {adjusted_confidence:.4f}")
        print(f"Best params: {best_result['params']}")
        print(
            f"Sharpe ratios - Train: {best_result['train_sharpe']:.2f}, "
            f"Val: {best_result['val_sharpe']:.2f}, "
            f"Test: {best_result['test_sharpe']:.2f}"
        )
        print(f"OOS validation: {'PASSED' if oos_valid else 'FAILED'}")
        print(f"Expectancy: ${expectancy:.2f} per trade")
        print(f"================================\n")

    def test_survivorship_bias_impact_on_returns(self):
        """Test that survivorship bias inflates returns."""
        manager = UniverseManager()

        # Simulate returns with and without failed companies
        survivor_returns = [0.01, 0.02, 0.015, 0.025, 0.03]  # Better performance
        full_universe_returns = [
            0.005,
            0.01,
            0.008,
            -0.02,  # Failed company
            0.012,
        ]  # Worse performance

        bias_metrics = manager.calculate_survivorship_bias(
            survivor_returns=survivor_returns,
            full_universe_returns=full_universe_returns,
        )

        # Bias should be detected
        assert bias_metrics["bias_detected"] == True
        assert bias_metrics["survivor_cagr"] > bias_metrics["full_universe_cagr"]

        # Bias percentage should be significant
        assert bias_metrics["bias_percentage"] > 10

    def test_expectancy_guides_strategy_selection(self):
        """Test that expectancy helps identify better strategies."""
        # Strategy A: High win rate but poor risk/reward
        winning_trades_a = [
            self._create_trade(100),
            self._create_trade(100),
            self._create_trade(100),
        ]
        losing_trades_a = [
            self._create_trade(-400),
            self._create_trade(-400),
        ]
        # Win rate: 60%, Avg win: 100, Avg loss: 400
        # Expectancy = (0.6 * 100) - (0.4 * 400) = 60 - 160 = -100

        expectancy_a = calculate_expectancy(winning_trades_a, losing_trades_a)

        # Strategy B: Lower win rate but better risk/reward
        winning_trades_b = [
            self._create_trade(500),
            self._create_trade(500),
        ]
        losing_trades_b = [
            self._create_trade(-300),
            self._create_trade(-300),
            self._create_trade(-300),
        ]
        # Win rate: 40%, Avg win: 500, Avg loss: 300
        # Expectancy = (0.4 * 500) - (0.6 * 300) = 200 - 180 = 20

        expectancy_b = calculate_expectancy(winning_trades_b, losing_trades_b)

        # Strategy B has better expectancy despite lower win rate
        assert expectancy_b > expectancy_a
        assert expectancy_b > 0
        assert expectancy_a < 0

    def _create_trade(self, pnl: float) -> Trade:
        """Helper to create a trade."""
        return Trade(
            trade_id=f"trade_{pnl}",
            symbol="TEST",
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            exit_price=Decimal("110") if pnl > 0 else Decimal("95"),
            entry_time=datetime(2024, 1, 1),
            exit_time=datetime(2024, 1, 2),
            status=TradeStatus.CLOSED,
            pnl=Decimal(str(pnl)),
        )


# Import timedelta
from datetime import timedelta
