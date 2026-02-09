#!/usr/bin/env python3
"""
Simple Terminal Dashboard for AlgoTrading.

Displays real-time trading performance, positions, and system status.
Refreshes automatically every 5 seconds.

Usage:
    python scripts/simple_dashboard.py          # Auto-refresh every 5s
    python scripts/simple_dashboard.py --once   # Display once and exit
    python scripts/simple_dashboard.py --json   # Output as JSON
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.dashboard.dashboard_service import get_dashboard_service


def format_currency(value: float) -> str:
    """Format value as currency."""
    if value >= 0:
        return f"${value:,.2f}"
    return f"-${abs(value):,.2f}"


def format_pct(value: float) -> str:
    """Format value as percentage."""
    return f"{value:+.2%}"


def display_snapshot(snapshot, show_full: bool = True):
    """Display dashboard snapshot to terminal."""
    # Clear screen
    print("\033[2J\033[H", end="")

    # Header
    print("=" * 80)
    print(f"{'ALGOTRADING DASHBOARD':^80}")
    print(f"{snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'):^80}")
    print("=" * 80)
    print()

    # System Status
    print("SYSTEM STATUS")
    print("-" * 80)
    status = snapshot.system_status
    kill_status = "🔴 ACTIVE" if status.kill_switch_active else "🟢 NORMAL"
    print(f"  Kill Switch: {kill_status}")
    print(f"  Bridge Status: {status.bridge_status.upper()}")
    print(f"  Systems: {status.systems_available}/{status.systems_total} available")
    print(f"  SLO Compliance: {status.slo_compliance_rate:.1%}")
    print(f"  Active Orders: {status.active_orders}")
    print()

    # Performance Metrics
    print("PERFORMANCE")
    print("-" * 80)
    perf = snapshot.performance
    daily_pnl_color = "\033[92m" if perf.daily_pnl >= 0 else "\033[91m"
    print(
        f"  Portfolio Value:     {format_currency(float(perf.portfolio_value))}"
    )
    print(
        f"  Daily P&L:           {daily_pnl_color}{format_currency(float(perf.daily_pnl))} ({format_pct(perf.daily_return_pct)})\033[0m"
    )
    print(
        f"  Total P&L:           {format_currency(float(perf.total_pnl))}"
    )
    print(
        f"  Total Trades:        {perf.total_trades} ({perf.winning_trades}W/{perf.losing_trades}L)"
    )
    print(
        f"  Win Rate:            {perf.win_rate:.1%}"
    )
    print(
        f"  Current Drawdown:    {perf.current_drawdown:.2%} (max: {perf.max_drawdown:.2%})"
    )
    if perf.sharpe_ratio is not None:
        print(
            f"  Sharpe Ratio:        {perf.sharpe_ratio:.2f}"
        )
    print()

    # Positions
    print("POSITIONS")
    print("-" * 80)
    if snapshot.positions:
        print(
            f"  {'Symbol':<8} {'Side':<6} {'Qty':>6} {'Avg Price':>10} {'Curr Price':>10} {'Market Value':>12} {'P&L':>12}"
        )
        print("  " + "-" * 72)
        for pos in snapshot.positions:
            pnl_color = "\033[92m" if pos.unrealized_pnl >= 0 else "\033[91m"
            print(
                f"  {pos.symbol:<8} {pos.side:<6} {pos.quantity:>6} "
                f"${pos.avg_price:>8.2f} ${pos.current_price:>8.2f} "
                f"${float(pos.market_value):>10.2f} "
                f"{pnl_color}{format_currency(float(pos.unrealized_pnl)):>12} ({pos.unrealized_pnl_pct:+.1f}%)\033[0m"
            )
        total_market_value = sum(p.market_value for p in snapshot.positions)
        total_pnl = sum(p.unrealized_pnl for p in snapshot.positions)
        print("  " + "-" * 72)
        print(
            f"  {'TOTAL':<8} {'':<6} {'':>6} {'':>10} {'':>10} "
            f"${float(total_market_value):>10.2f} "
            f"{format_currency(float(total_pnl)):>12}"
        )
    else:
        print("  No open positions")
    print()

    # Recent Alerts
    if snapshot.recent_alerts and show_full:
        print("RECENT ALERTS")
        print("-" * 80)
        for alert in snapshot.recent_alerts[:5]:  # Show last 5
            severity = alert.get("severity", "INFO")
            message = alert.get("message", "")
            timestamp = alert.get("timestamp", "")
            print(f"  [{timestamp}] {severity}: {message}")
        print()

    print("=" * 80)
    print("Press Ctrl+C to exit".center(80))
    print("=" * 80)


async def main():
    """Main dashboard entry point."""
    parser = argparse.ArgumentParser(
        description="Simple Terminal Dashboard for AlgoTrading"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Display once and exit (don't auto-refresh)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output dashboard data as JSON",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Refresh interval in seconds (default: 5)",
    )
    args = parser.parse_args()

    dashboard = get_dashboard_service()

    if args.json:
        # Output as JSON and exit
        snapshot = await dashboard.get_snapshot()
        print(json.dumps(snapshot.to_display_dict(), indent=2))
        return

    if args.once:
        # Display once and exit
        snapshot = await dashboard.get_snapshot()
        display_snapshot(snapshot)
        return

    # Auto-refresh mode
    try:
        while True:
            snapshot = await dashboard.get_snapshot()
            display_snapshot(snapshot)
            await asyncio.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")


if __name__ == "__main__":
    asyncio.run(main())
