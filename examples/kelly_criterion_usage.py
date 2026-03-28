"""
Kelly Criterion Position Sizing - Usage Examples

This example demonstrates how to use the Kelly Criterion position sizing
implementation in accordance with Ernest Chan Rule 1.9.

Key Features:
- Half-Kelly conservative approach (reduces volatility and drawdown)
- 25% maximum position cap (prevents overconcentration)
- Fallback to 2% rule when metrics unavailable
- Integration with backtesting performance metrics

Author: Algorithmic Trading System
Date: 2026-01-28
Compliance: Ernest Chan Rule 1.9
"""

from decimal import Decimal
from app.services.position_sizing_engine import PositionSizingEngine


def example_basic_kelly_calculation():
    """
    Example 1: Basic Kelly Criterion calculation.

    Scenario: 55% win rate, $100 avg win, $75 avg loss
    """
    print("\n" + "=" * 60)
    print("Example 1: Basic Kelly Criterion Calculation")
    print("=" * 60)

    engine = PositionSizingEngine()

    result = engine.calculate_kelly_position_size(
        win_rate=0.55,
        avg_win=100.0,
        avg_loss=75.0,
        capital=Decimal("10000"),
    )

    print(f"Win Rate: 55%")
    print(f"Avg Win: $100.00")
    print(f"Avg Loss: $75.00")
    print(f"\nKelly Results:")
    print(f"  Raw Kelly Fraction: {result['kelly_fraction']:.4f}")
    print(f"  Half-Kelly Fraction: {result['half_kelly_fraction']:.4f}")
    print(f"  Position %: {result['position_percentage']:.2f}%")
    print(f"  Position Value: ${result['position_value']:.2f}")
    print(f"  Recommendation: {result['recommendation']}")

    # Calculation:
    # Kelly = (0.55 * 100 - 0.45 * 75) / 100
    # Kelly = (55 - 33.75) / 100 = 21.25 / 100 = 0.2125
    # Half-Kelly = 0.2125 * 0.5 = 0.10625
    # Position Size = $10,000 * 0.10625 = $1,062.50


def example_from_backtest_metrics():
    """
    Example 2: Calculate Kelly from backtest performance metrics.

    Scenario: Strategy backtested with 60% win rate
    """
    print("\n" + "=" * 60)
    print("Example 2: Kelly from Backtest Metrics")
    print("=" * 60)

    engine = PositionSizingEngine()

    # Simulated backtest results
    backtest_metrics = {
        "win_rate": Decimal("60.0"),  # 60% win rate
        "avg_win": Decimal("120.0"),  # $120 average win
        "avg_loss": Decimal("-80.0"),  # $80 average loss
        "total_trades": 100,
        "winning_trades": 60,
        "losing_trades": 40,
    }

    capital = Decimal("50000")

    result = engine.calculate_kelly_from_backtest(
        performance_metrics=backtest_metrics,
        capital=capital,
    )

    print(f"Backtest Performance:")
    print(f"  Total Trades: {backtest_metrics['total_trades']}")
    print(f"  Win Rate: {backtest_metrics['win_rate']}%")
    print(f"  Avg Win: ${backtest_metrics['avg_win']}")
    print(f"  Avg Loss: ${backtest_metrics['avg_loss']}")
    print(f"\nKelly Position Sizing:")
    print(f"  Recommendation: {result['recommendation']}")
    print(f"  Position Size: ${result['position_value']:.2f}")
    print(f"  % of Capital: {result['position_percentage']:.2f}%")


def example_negative_expectancy():
    """
    Example 3: Negative expectancy system (should avoid trading).

    Scenario: 40% win rate with unfavorable risk/reward
    """
    print("\n" + "=" * 60)
    print("Example 3: Negative Expectancy (AVOID)")
    print("=" * 60)

    engine = PositionSizingEngine()

    result = engine.calculate_kelly_position_size(
        win_rate=0.40,
        avg_win=50.0,
        avg_loss=100.0,
    )

    print(f"Win Rate: 40%")
    print(f"Avg Win: $50.00")
    print(f"Avg Loss: $100.00")
    print(f"\nKelly Results:")
    print(f"  Raw Kelly: {result['kelly_fraction']:.4f}")
    print(f"  Half-Kelly: {result['half_kelly_fraction']:.4f}")
    print(f"  Recommendation: {result['recommendation']}")
    print(f"\n→ Kelly indicates NEGATIVE EXPECTANCY - DO NOT TRADE")


def example_25_percent_cap():
    """
    Example 4: 25% maximum position cap enforcement.

    Scenario: Excellent strategy that would suggest >25% position
    """
    print("\n" + "=" * 60)
    print("Example 4: 25% Maximum Position Cap")
    print("=" * 60)

    engine = PositionSizingEngine()

    result = engine.calculate_kelly_position_size(
        win_rate=0.80,  # 80% win rate
        avg_win=200.0,
        avg_loss=50.0,
        capital=Decimal("100000"),
    )

    print(f"Win Rate: 80%")
    print(f"Avg Win: $200.00")
    print(f"Avg Loss: $50.00")
    print(f"\nKelly Results:")
    print(f"  Raw Kelly: {result['kelly_fraction']:.4f} (very high!)")
    print(f"  Half-Kelly (capped): {result['half_kelly_fraction']:.4f}")
    print(f"  Position %: {result['position_percentage']:.2f}%")
    print(f"  Position Value: ${result['position_value']:,.2f}")
    print(f"\n→ Despite excellent metrics, position CAPPED at 25% for risk management")


def example_fallback_to_2_percent():
    """
    Example 5: Fallback to 2% rule when metrics unavailable.

    Scenario: New strategy with insufficient backtest data
    """
    print("\n" + "=" * 60)
    print("Example 5: Fallback to 2% Rule")
    print("=" * 60)

    engine = PositionSizingEngine()

    # Insufficient data (no losing trades recorded yet)
    insufficient_metrics = {
        "win_rate": Decimal("100.0"),
        "avg_win": Decimal("50.0"),
        "avg_loss": Decimal("0.0"),  # No losses yet
    }

    result = engine.calculate_kelly_from_backtest(
        performance_metrics=insufficient_metrics,
        capital=Decimal("10000"),
    )

    print(f"Insufficient Backtest Data:")
    print(f"  Win Rate: {insufficient_metrics['win_rate']}%")
    print(f"  Avg Win: ${insufficient_metrics['avg_win']}")
    print(f"  Avg Loss: ${insufficient_metrics['avg_loss']} (no losses recorded)")
    print(f"\nFallback Results:")
    print(f"  Recommendation: {result['recommendation']}")
    print(f"  Position Size: ${result['position_value']:.2f}")
    print(f"  Position %: {result['position_percentage']:.2f}%")
    print(f"  Reason: {result['fallback_reason']}")
    print(f"\n→ Using conservative 2% rule until more data available")


def example_kelly_vs_traditional_sizing():
    """
    Example 6: Compare Kelly with traditional 2% rule.

    Scenario: Which approach provides better position sizing?
    """
    print("\n" + "=" * 60)
    print("Example 6: Kelly vs Traditional 2% Rule")
    print("=" * 60)

    engine = PositionSizingEngine()

    # Good strategy metrics
    metrics = {
        "win_rate": Decimal("58.0"),
        "avg_win": Decimal("110.0"),
        "avg_loss": Decimal("-75.0"),
    }

    capital = Decimal("25000")

    # Kelly-based sizing
    kelly_result = engine.calculate_kelly_from_backtest(
        performance_metrics=metrics,
        capital=capital,
    )

    # Traditional 2% rule
    traditional_2pct = capital * Decimal("0.02")

    print(f"Strategy: 58% win rate, $110 win, $75 loss")
    print(f"\nPosition Sizing Comparison:")
    print(f"  Traditional 2% Rule: ${traditional_2pct:.2f}")
    print(f"  Kelly Criterion: ${kelly_result['position_value']:.2f}")
    print(f"  Difference: ${kelly_result['position_value'] - traditional_2pct:.2f}")
    print(f"  Kelly vs Traditional: {(kelly_result['position_value'] / traditional_2pct):.2f}x")
    print(f"\n→ Kelly provides OPTIMAL position sizing based on actual performance")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("KELLY CRITERION POSITION SIZING EXAMPLES")
    print("Ernest Chan Rule 1.9 Compliance")
    print("=" * 60)

    example_basic_kelly_calculation()
    example_from_backtest_metrics()
    example_negative_expectancy()
    example_25_percent_cap()
    example_fallback_to_2_percent()
    example_kelly_vs_traditional_sizing()

    print("\n" + "=" * 60)
    print("KEY TAKEAWAYS")
    print("=" * 60)
    print("1. Half-Kelly reduces volatility while maintaining growth")
    print("2. 25% cap prevents overconcentration risk")
    print("3. AVOID negative expectancy systems entirely")
    print("4. Fallback to 2% rule when metrics unavailable")
    print("5. Kelly provides optimal growth vs traditional fixed %")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
