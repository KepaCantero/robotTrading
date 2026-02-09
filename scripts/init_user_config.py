#!/usr/bin/env python3
"""
Initialize User Configuration Script

Creates and initializes user configuration file.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.user_config import UserConfigManager, UserSettings


def init_user_config(interactive: bool = True) -> None:
    """
    Initialize user configuration.

    Args:
        interactive: If True, prompt user for values. If False, use defaults.
    """
    config_dir = Path.home() / ".algotrading"
    config_file = config_dir / "user_config.yaml"

    print("AlgoTrading User Configuration Initialization")
    print("=" * 50)
    print(f"Config location: {config_file}")
    print()

    if config_file.exists():
        response = input("Config file already exists. Overwrite? (y/N): ")
        if response.lower() != "y":
            print("Aborted.")
            return

    if interactive:
        # Interactive setup
        user_name = input("Your name [Trader]: ") or "Trader"
        risk_tolerance = input("Risk tolerance (conservative/moderate/aggressive) [moderate]: ") or "moderate"
        broker_type = input("Broker (paper/alpaca/ibkr) [paper]: ") or "paper"
        paper_trading = input("Use paper trading? (Y/n): ").lower() != "n"

        settings = UserSettings(
            user_name=user_name,
            trading_profile={"risk_tolerance": risk_tolerance},
            broker_settings={
                "broker_type": broker_type,
                "paper_trading": paper_trading,
            },
        )
    else:
        # Use defaults
        settings = UserSettings()

    # Save config
    manager = UserConfigManager(config_file)
    manager.save(settings)

    print()
    print("Configuration saved successfully!")
    print(f"Config file: {config_file}")
    print()
    print("You can edit this file to customize your settings.")
    if settings.broker_settings.paper_trading:
        print()
        print("NOTE: Paper trading mode is enabled. To use live trading,")
        print("set paper_trading: false and add your API credentials.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize user configuration")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Use default values without prompting",
    )
    args = parser.parse_args()

    init_user_config(interactive=not args.non_interactive)
