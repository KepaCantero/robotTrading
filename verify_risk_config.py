#!/usr/bin/env python3
"""
Verify that risk management configuration is properly loaded from YAML.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.backtesting.core.config_loader import BacktestConfigLoader

def main():
    """Load and display risk management configuration."""
    config_path = "config/backtesting/comprehensive_backtest.yaml"

    print(f"Loading configuration from: {config_path}")
    print("=" * 80)

    try:
        loader = BacktestConfigLoader(config_path)
        config = loader.get_backtest_config()

        print("\n✅ Configuration loaded successfully!\n")
        print("RISK MANAGEMENT SETTINGS:")
        print("-" * 80)
        print(f"Stop Loss:          {config.stop_loss_percentage}%")
        print(f"Take Profit:        {config.take_profit_percentage}%")
        print(f"Max Position Size:  {config.max_position_size * 100}% of capital")
        print(f"Commission:         ${config.commission_per_trade} per trade")
        print(f"Slippage:           {config.slippage_percentage}%")
        print(f"Initial Capital:    ${config.initial_capital:,.2f}")
        print(f"Risk Free Rate:     {config.risk_free_rate * 100}%")

        # Validate configuration logic
        print("\n" + "=" * 80)
        print("VALIDATION:")
        print("-" * 80)

        if config.stop_loss_percentage is None:
            print("❌ WARNING: Stop loss is NOT configured!")
            print("   This can lead to UNLIMITED LOSSES per position.")
        else:
            print(f"✅ Stop loss is enabled at {config.stop_loss_percentage}%")

        if config.take_profit_percentage is None:
            print("❌ WARNING: Take profit is NOT configured!")
            print("   Positions will only close on SELL signals.")
        else:
            print(f"✅ Take profit is enabled at {config.take_profit_percentage}%")

        if config.stop_loss_percentage and config.take_profit_percentage:
            ratio = config.take_profit_percentage / config.stop_loss_percentage
            print(f"✅ Risk/Reward ratio: 1:{ratio:.1f}")

            if ratio < 2.0:
                print("   ⚠️  WARNING: Risk/Reward ratio is less than 1:2")
            elif ratio >= 2.0 and ratio < 3.0:
                print("   ✅ Risk/Reward ratio is acceptable (1:2 or better)")
            else:
                print("   ✅ Excellent Risk/Reward ratio (1:3 or better)")

        print("\n" + "=" * 80)
        print("EXPECTED BEHAVIOR:")
        print("-" * 80)

        if config.stop_loss_percentage:
            print(f"• Positions will be automatically CLOSED if price drops {config.stop_loss_percentage}% from entry")
        if config.take_profit_percentage:
            print(f"• Positions will be automatically CLOSED if price rises {config.take_profit_percentage}% from entry")
        print(f"• Maximum position size is {config.max_position_size * 100}% of capital (${config.initial_capital * config.max_position_size:,.2f})")
        print(f"• Each trade costs ${config.commission_per_trade} in commission")
        print(f"• Each trade has {config.slippage_percentage}% slippage")

        print("\n" + "=" * 80)
        print("CONFIGURATION STATUS: ", end="")

        if config.stop_loss_percentage and config.take_profit_percentage:
            print("✅ PROPERLY CONFIGURED")
            print("\nThe backtest should now have proper risk management with")
            print("limited drawdown per position.")
        else:
            print("❌ INCOMPLETE")
            print("\nWARNING: Risk management is not fully configured!")
            print("This may lead to excessive drawdown.")

        print("=" * 80)

        return 0

    except Exception as e:
        print(f"\n❌ ERROR loading configuration: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
