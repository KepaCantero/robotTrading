"""
Demonstration of Kill Switch functionality (Hull Rule 13.1).

This script demonstrates how the kill switch activates when daily loss exceeds 5%.
"""

from decimal import Decimal
from app.core.compliance_engine import get_compliance_engine


def main():
    """Run kill switch demonstration."""
    print("=" * 80)
    print("KILL SWITCH DEMONSTRATION - Hull Rule 13.1")
    print("=" * 80)

    # Initialize engine with $100,000 starting capital
    engine = get_compliance_engine(enable_logging=True)
    engine.set_starting_capital(100000.0)

    print(f"\nStarting Capital: ${engine._starting_capital:,.2f}")
    print(f"Kill Switch Threshold: 5% = ${engine._starting_capital * 0.05:,.2f}\n")

    # Scenario 1: Normal trading with small profit
    print("-" * 80)
    print("SCENARIO 1: Small Profit Trade")
    print("-" * 80)

    engine.track_daily_pnl(
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("100"),
        entry_price=Decimal("150"),
        exit_price=Decimal("155"),
        realized_pnl=500.0,
    )

    summary = engine.get_daily_pnl_summary()
    print(f"Total P&L: ${summary['total_pnl']:,.2f}")
    print(f"Daily Return: {summary['daily_return_pct']:.2%}")
    print(f"Kill Switch Active: {summary['kill_switch_active']}")

    # Try to execute a trade
    analysis = engine.analyze_pre_trade(
        symbol="TSLA",
        side="BUY",
        quantity=Decimal("50"),
        price=Decimal("200"),
    )
    print(f"Can Execute Trade: {analysis.can_execute}")

    # Scenario 2: Accumulating losses but below threshold
    print("\n" + "-" * 80)
    print("SCENARIO 2: Accumulating Losses (4% total)")
    print("-" * 80)

    engine.track_daily_pnl(
        symbol="TSLA",
        side="BUY",
        quantity=Decimal("100"),
        entry_price=Decimal("200"),
        exit_price=Decimal("190"),
        realized_pnl=-1000.0,
    )

    engine.track_daily_pnl(
        symbol="MSFT",
        side="BUY",
        quantity=Decimal("50"),
        entry_price=Decimal("300"),
        exit_price=Decimal("290"),
        realized_pnl=-500.0,
    )

    engine.track_daily_pnl(
        symbol="GOOGL",
        side="BUY",
        quantity=Decimal("30"),
        entry_price=Decimal("2500"),
        exit_price=Decimal("2483.33"),
        realized_pnl=-500.0,
    )

    summary = engine.get_daily_pnl_summary()
    print(f"Total P&L: ${summary['total_pnl']:,.2f}")
    print(f"Daily Return: {summary['daily_return_pct']:.2%}")
    print(f"Win Rate: {summary['win_rate']:.1%}")
    print(f"Kill Switch Active: {summary['kill_switch_active']}")

    # Try to execute a trade
    analysis = engine.analyze_pre_trade(
        symbol="NVDA",
        side="BUY",
        quantity=Decimal("20"),
        price=Decimal("500"),
    )
    print(f"Can Execute Trade: {analysis.can_execute}")

    # Scenario 3: Loss exceeds 5% threshold - KILL SWITCH TRIGGERS
    print("\n" + "-" * 80)
    print("SCENARIO 3: Loss Exceeds 5% - KILL SWITCH TRIGGERED")
    print("-" * 80)

    engine.track_daily_pnl(
        symbol="AMZN",
        side="BUY",
        quantity=Decimal("100"),
        entry_price=Decimal("150"),
        exit_price=Decimal("135"),
        realized_pnl=-1500.0,
    )

    summary = engine.get_daily_pnl_summary()
    print(f"Total P&L: ${summary['total_pnl']:,.2f}")
    print(f"Daily Return: {summary['daily_return_pct']:.2%}")
    print(f"Kill Switch Active: {summary['kill_switch_active']}")
    print(f"Total Trades: {summary['total_trades']}")
    print(f"Winning Trades: {summary['winning_trades']}")
    print(f"Losing Trades: {summary['losing_trades']}")

    # Try to execute a trade - should be BLOCKED
    print("\nAttempting to execute trade while kill switch is active...")
    analysis = engine.analyze_pre_trade(
        symbol="META",
        side="BUY",
        quantity=Decimal("30"),
        price=Decimal("400"),
    )
    print(f"Can Execute Trade: {analysis.can_execute}")
    print(f"Confidence: {analysis.confidence:.0%}")
    print(f"Reasons: {'; '.join(analysis.reasons)}")

    # Scenario 4: Reset daily tracking for new day
    print("\n" + "-" * 80)
    print("SCENARIO 4: Reset Daily Tracking (New Trading Day)")
    print("-" * 80)

    engine.reset_daily_tracking(new_starting_capital=98000.0)  # Account for previous loss
    summary = engine.get_daily_pnl_summary()
    print(f"New Starting Capital: ${summary['starting_capital']:,.2f}")
    print(f"Total Trades Today: {summary['total_trades']}")
    print(f"Kill Switch Active: {summary['kill_switch_active']}")

    # Try to execute a trade - should be allowed now
    analysis = engine.analyze_pre_trade(
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("50"),
        price=Decimal("155"),
    )
    print(f"Can Execute Trade: {analysis.can_execute}")

    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
