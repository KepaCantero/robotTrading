#!/usr/bin/env python3
"""
Demonstration of risk management impact on backtesting results.

This script shows the difference between running a backtest WITH and WITHOUT
proper risk management (stop-loss, take-profit, position sizing).
"""
import sys
from decimal import Decimal
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.backtesting.core.config_loader import BacktestConfigLoader
from app.backtesting.core.orchestrator import BacktestDefaults


def print_comparison(title: str, config, defaults):
    """Print configuration comparison."""
    print(f"\n{title}")
    print("=" * 80)

    # Stop Loss
    if config.stop_loss_percentage:
        sl = f"{config.stop_loss_percentage}%"
    else:
        sl = f"{defaults.STOP_LOSS_PERCENTAGE}% (default)"

    # Take Profit
    if config.take_profit_percentage:
        tp = f"{config.take_profit_percentage}%"
    else:
        tp = f"{defaults.TAKE_PROFIT_PERCENTAGE}% (default)"

    # Position Size
    ps = f"{config.max_position_size * 100}%"

    # Commission
    comm = f"${config.commission_per_trade}"

    # Slippage
    slip = f"{config.slippage_percentage}%"

    print(f"Stop Loss:          {sl}")
    print(f"Take Profit:        {tp}")
    print(f"Max Position Size:  {ps}")
    print(f"Commission:         {comm} per trade")
    print(f"Slippage:           {slip}")
    print(f"Initial Capital:    ${config.initial_capital:,.2f}")


def calculate_impact(config):
    """Calculate theoretical impact of risk management."""
    print("\n" + "=" * 80)
    print("THEORETICAL IMPACT ANALYSIS")
    print("=" * 80)

    # Calculate position value
    position_value = config.initial_capital * config.max_position_size
    print(f"\nMax Position Value: ${position_value:,.2f}")

    # Calculate max loss per position
    if config.stop_loss_percentage:
        max_loss_per_position = position_value * (config.stop_loss_percentage / 100)
        print(f"Max Loss per Position: ${max_loss_per_position:,.2f} ({config.stop_loss_percentage}%)")
    else:
        max_loss_per_position = position_value  # Could lose entire position
        print(f"Max Loss per Position: ${max_loss_per_position:,.2f} (UNLIMITED RISK!)")

    # Calculate max gain per position
    if config.take_profit_percentage:
        max_gain_per_position = position_value * (config.take_profit_percentage / 100)
        print(f"Max Gain per Position: ${max_gain_per_position:,.2f} ({config.take_profit_percentage}%)")
    else:
        max_gain_per_position = position_value * 2  # Assume 2x if no take-profit
        print(f"Max Gain per Position: Unlimited (no take-profit set)")

    # Calculate trading costs
    commission_cost = config.commission_per_trade * 2  # Buy + Sell
    position_pct = (commission_cost / position_value) * 100
    print(f"\nTrading Costs per Round-trip: ${commission_cost:.2f} ({position_pct:.2f}% of position)")

    # Calculate risk/reward
    if config.stop_loss_percentage and config.take_profit_percentage:
        rr_ratio = config.take_profit_percentage / config.stop_loss_percentage
        print(f"\nRisk/Reward Ratio: 1:{rr_ratio:.1f}")
        print(f"  Risk: {config.stop_loss_percentage}% per position")
        print(f"  Reward: {config.take_profit_percentage}% per position")

        # Calculate required win rate
        required_win_rate = 1 / (1 + rr_ratio)
        print(f"  Required Win Rate: {required_win_rate * 100:.1f}% to break even")
    else:
        print(f"\nRisk/Reward Ratio: UNDEFINED (missing stop-loss or take-profit)")


def demonstrate_scenario():
    """Demonstrate a trading scenario with and without risk management."""
    print("\n" + "=" * 80)
    print("TRADING SCENARIO DEMONSTRATION")
    print("=" * 80)

    print("\nScenario: Buy AAPL at $150.00")
    print("Initial Capital: $100,000")
    print("-" * 80)

    # Without risk management
    print("\n1️⃣  WITHOUT RISK MANAGEMENT (old configuration):")
    print("   Stop Loss: None")
    print("   Take Profit: None")
    print("   Position Size: 20% = $20,000 (133 shares)")

    print("\n   Price Movement:")
    print("   Day 1:  $150.00 → Buy 133 shares @ $150 = $20,000")
    print("   Day 30: $140.00 → Still holding (no stop-loss)")
    print("   Day 60: $130.00 → Still holding (no stop-loss)")
    print("   Day 90: $100.00 → Still holding (no stop-loss)")
    print("   Day 120: $80.00 → Still holding (no stop-loss)")
    print("   Day 150: SELL signal → Sell 133 shares @ $80 = $10,640")

    loss = 20000 - 10640
    loss_pct = (loss / 20000) * 100
    print(f"\n   Result: ${loss:,.2f} loss ({loss_pct:.1f}%)")
    print(f"   Portfolio Impact: -{loss_pct:.1f}% of total capital")

    # With risk management
    print("\n2️⃣  WITH RISK MANAGEMENT (new configuration):")
    print("   Stop Loss: 5% @ $142.50")
    print("   Take Profit: 10% @ $165.00")
    print("   Position Size: 10% = $10,000 (66 shares)")

    print("\n   Price Movement:")
    print("   Day 1:  $150.00 → Buy 66 shares @ $150 = $10,000")
    print("   Day 30: $140.00 → Stop Loss Hit! → Sell 66 shares @ $140")

    loss2 = 10000 - (66 * 140)
    loss_pct2 = (loss2 / 10000) * 100
    print(f"\n   Result: ${loss2:,.2f} loss ({loss_pct2:.1f}%)")
    print(f"   Portfolio Impact: -{loss_pct2 * 0.1:.1f}% of total capital")
    print(f"   Capital Saved: ${loss - loss2:,.2f}")

    print("\n" + "=" * 80)
    print("COMPARISON:")
    print("=" * 80)
    print(f"Loss Without Risk Management: ${loss:,.2f} ({loss_pct:.1f}% of position)")
    print(f"Loss With Risk Management:    ${loss2:,.2f} ({loss_pct2:.1f}% of position)")
    print(f"Capital Saved:                ${loss - loss2:,.2f}")


def main():
    """Main demonstration."""
    print("=" * 80)
    print("RISK MANAGEMENT DEMONSTRATION")
    print("=" * 80)
    print("\nThis demonstration shows the impact of proper risk management")
    print("on backtesting results and portfolio protection.")

    # Load current configuration
    config_path = "config/backtesting/comprehensive_backtest.yaml"
    print(f"\nLoading configuration from: {config_path}")

    try:
        loader = BacktestConfigLoader(config_path)
        config = loader.get_backtest_config()
        print("✅ Configuration loaded successfully")
    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        print(f"❌ ERROR loading configuration: {e}")
        return 1

    # Get defaults
    defaults = BacktestDefaults

    # Display current configuration
    print_comparison("CURRENT CONFIGURATION (from YAML)", config, defaults)

    # Calculate impact
    calculate_impact(config)

    # Demonstrate scenario
    demonstrate_scenario()

    # Final summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print("\n✅ Current Configuration:")
    print(f"   • Stop Loss: {config.stop_loss_percentage}% (limits losses)")
    print(f"   • Take Profit: {config.take_profit_percentage}% (captures gains)")
    print(f"   • Max Position: {config.max_position_size * 100}% (diversification)")
    print(f"   • Commission: ${config.commission_per_trade} (realistic costs)")

    print("\n📊 Expected Benefits:")
    print("   • Controlled maximum loss per position")
    print("   • Automatic profit capture")
    print("   • Reduced portfolio drawdown")
    print("   • More realistic trading simulation")

    print("\n⚠️  Without Risk Management:")
    print("   • Unlimited losses per position")
    print("   • Profits not captured (held too long)")
    print("   • Catastrophic drawdown possible")
    print("   • Unrealistic performance expectations")

    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("\n1. Verify configuration:")
    print("   python verify_risk_config.py")
    print("\n2. Run backtest with new configuration:")
    print("   python run_backtesting_with_real_data.py")
    print("\n3. Analyze results:")
    print("   python analyze_backtest_exits.py reports/backtesting_real_data_*.json")
    print("\n4. Compare max drawdown:")
    print("   Before: -6345.32% (without risk management)")
    print("   After: ~15-30% (with risk management)")
    print("\n" + "=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
