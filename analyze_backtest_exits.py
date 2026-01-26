#!/usr/bin/env python3
"""
Analyze backtest results to show exit reasons (stop_loss, take_profit, signals).
"""
import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

def analyze_backtest_result(json_file: str):
    """
    Analyze backtest result JSON file and show exit reason statistics.

    Args:
        json_file: Path to backtest result JSON file
    """
    print(f"Loading backtest results from: {json_file}")
    print("=" * 80)

    with open(json_file, 'r') as f:
        result = json.load(f)

    # Get trades
    trades = result.get('trades', [])
    print(f"\nTotal Trades: {len(trades)}")

    if not trades:
        print("No trades found in results.")
        return

    # Analyze exit reasons
    exit_reasons = Counter()
    stop_loss_trades = []
    take_profit_trades = []
    signal_trades = []
    end_of_backtest_trades = []

    for trade in trades:
        reason = trade.get('reason', 'unknown')
        exit_reasons[reason] += 1

        if 'stop_loss' in reason.lower():
            stop_loss_trades.append(trade)
        elif 'take_profit' in reason.lower():
            take_profit_trades.append(trade)
        elif 'end_of_backtest' in reason.lower():
            end_of_backtest_trades.append(trade)
        else:
            signal_trades.append(trade)

    # Display exit reason statistics
    print("\n" + "=" * 80)
    print("EXIT REASON BREAKDOWN:")
    print("=" * 80)

    total_closed = len(trades)

    print(f"\n1. Stop Loss Exits: {len(stop_loss_trades)} ({len(stop_loss_trades)/total_closed*100:.1f}%)")
    if stop_loss_trades:
        avg_pnl = sum(t.get('pnl', 0) for t in stop_loss_trades) / len(stop_loss_trades)
        print(f"   Average P&L: ${avg_pnl:.2f}")
        print(f"   Description: Positions automatically closed at -5% loss")
        # Show example
        example = stop_loss_trades[0]
        print(f"   Example: {example.get('symbol')} entry=${example.get('entry_price'):.2f} "
              f"exit=${example.get('exit_price'):.2f} pnl=${example.get('pnl'):.2f}")

    print(f"\n2. Take Profit Exits: {len(take_profit_trades)} ({len(take_profit_trades)/total_closed*100:.1f}%)")
    if take_profit_trades:
        avg_pnl = sum(t.get('pnl', 0) for t in take_profit_trades) / len(take_profit_trades)
        print(f"   Average P&L: ${avg_pnl:.2f}")
        print(f"   Description: Positions automatically closed at +10% gain")
        # Show example
        example = take_profit_trades[0]
        print(f"   Example: {example.get('symbol')} entry=${example.get('entry_price'):.2f} "
              f"exit=${example.get('exit_price'):.2f} pnl=${example.get('pnl'):.2f}")

    print(f"\n3. Signal Exits: {len(signal_trades)} ({len(signal_trades)/total_closed*100:.1f}%)")
    if signal_trades:
        avg_pnl = sum(t.get('pnl', 0) for t in signal_trades) / len(signal_trades)
        print(f"   Average P&L: ${avg_pnl:.2f}")
        print(f"   Description: Positions closed by SELL signals")

    print(f"\n4. End of Backtest: {len(end_of_backtest_trades)} ({len(end_of_backtest_trades)/total_closed*100:.1f}%)")
    if end_of_backtest_trades:
        avg_pnl = sum(t.get('pnl', 0) for t in end_of_backtest_trades) / len(end_of_backtest_trades)
        print(f"   Average P&L: ${avg_pnl:.2f}")
        print(f"   Description: Positions still open at end of backtest")

    # Risk Management Effectiveness
    print("\n" + "=" * 80)
    print("RISK MANAGEMENT EFFECTIVENESS:")
    print("=" * 80)

    total_auto_exits = len(stop_loss_trades) + len(take_profit_trades)
    auto_exit_pct = total_auto_exits / total_closed * 100

    print(f"\nAutomatic Exits (Stop Loss + Take Profit): {total_auto_exits} ({auto_exit_pct:.1f}%)")

    if auto_exit_pct == 0:
        print("\n❌ WARNING: No automatic exits detected!")
        print("   This suggests stop-loss/take-profit may not be configured.")
        print("   Run 'python verify_risk_config.py' to check configuration.")
    elif auto_exit_pct < 20:
        print(f"\n⚠️  Low automatic exit rate ({auto_exit_pct:.1f}%)")
        print("   Most positions are closed by signals rather than risk management.")
        print("   Consider tightening stop-loss/take-profit thresholds.")
    elif auto_exit_pct >= 20 and auto_exit_pct < 50:
        print(f"\n✅ Moderate automatic exit rate ({auto_exit_pct:.1f}%)")
        print("   Risk management is active but not dominating.")
    else:
        print(f"\n✅ High automatic exit rate ({auto_exit_pct:.1f}%)")
        print("   Risk management is actively protecting capital.")

    # Check if stop-loss is working
    if stop_loss_trades:
        print(f"\n✅ Stop-loss is WORKING - {len(stop_loss_trades)} positions saved from larger losses")
    else:
        print("\n⚠️  No stop-loss exits - either:")
        print("   - No positions dropped 5% (good performance)")
        print("   - Stop-loss not configured (run verify_risk_config.py)")

    # Check if take-profit is working
    if take_profit_trades:
        print(f"\n✅ Take-profit is WORKING - {len(take_profit_trades)} positions captured profits at 10%")
    else:
        print("\n⚠️  No take-profit exits - positions may be held too long")

    # Overall statistics
    print("\n" + "=" * 80)
    print("OVERALL STATISTICS:")
    print("=" * 80)

    performance = result.get('performance', {})
    print(f"\nFinal Capital:     ${result.get('final_capital', 0):,.2f}")
    print(f"Total Return:      {result.get('total_return', 0):.2f}%")
    print(f"Max Drawdown:      {performance.get('max_drawdown_percentage', 0):.2f}%")
    print(f"Sharpe Ratio:      {performance.get('sharpe_ratio', 'N/A')}")
    print(f"Win Rate:          {performance.get('win_rate', 0):.1f}%")
    print(f"Total Trades:      {performance.get('total_trades', 0)}")
    print(f"Profit Factor:     {performance.get('profit_factor', 'N/A')}")

    # Risk assessment
    print("\n" + "=" * 80)
    print("RISK ASSESSMENT:")
    print("=" * 80)

    max_dd = performance.get('max_drawdown_percentage', 0)
    if max_dd < -20:
        print(f"\n❌ EXCESSIVE DRAWDOWN: {max_dd:.2f}%")
        print("   Risk management may need adjustment:")
        print("   - Reduce stop-loss (e.g., 3% instead of 5%)")
        print("   - Reduce max_position_size (e.g., 5% instead of 10%)")
    elif max_dd < -10:
        print(f"\n⚠️  HIGH DRAWDOWN: {max_dd:.2f}%")
        print("   Consider tightening risk parameters.")
    else:
        print(f"\n✅ ACCEPTABLE DRAWDOWN: {max_dd:.2f}%")
        print("   Risk management is working well.")

    print("\n" + "=" * 80)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_backtest_exits.py <backtest_result.json>")
        print("\nExample:")
        print("  python analyze_backtest_exits.py reports/backtesting_real_data_20260125_071043.json")
        sys.exit(1)

    json_file = sys.argv[1]

    if not Path(json_file).exists():
        print(f"❌ ERROR: File not found: {json_file}")
        sys.exit(1)

    try:
        analyze_backtest_result(json_file)
        return 0
    except Exception as e:
        print(f"\n❌ ERROR analyzing results: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
