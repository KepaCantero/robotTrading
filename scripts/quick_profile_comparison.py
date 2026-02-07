#!/usr/bin/env python3
"""
Quick Profile Comparison - Small Time Sample

Compares different investor profiles to see which generates more money.
Uses a small time sample (3 months) for quick verification.
"""

import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.backtesting.profile_batch_backtester import ProfileBatchBacktester
from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_quick_test_config():
    """Create a minimal config for quick testing (3 months)."""
    return {
        "database": {
            "url": "sqlite:///results/quick_profile_test.db"
        },
        "output_dir": "results/quick_profile_comparison",
        "capital_tiers": {
            "bajo": 50000,
            "medio": 150000,
            "alto": 500000,
        },
        "investment_horizons": [12],  # Just 1 horizon for testing
        "backtest_period": {
            "start_date": "2023-01-01",   # Only 3 months for quick test
            "end_date": "2023-03-31"
        },
        "symbols": ["AAPL", "MSFT", "GOOGL"],  # Just 3 symbols for speed
        "risk_parameters": {
            "bajo": {
                "max_position_pct": 0.05,
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.08,
            },
            "medio": {
                "max_position_pct": 0.10,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.12,
            },
            "alto": {
                "max_position_pct": 0.20,
                "stop_loss_pct": 0.05,
                "take_profit_pct": 0.20,
            },
        },
        "objective_parameters": {
            "maximizar_capital": {
                "primary_metric": "sharpe_ratio",
            },
            "capital_preservation": {
                "primary_metric": "max_drawdown",
            },
            "balanced_growth": {
                "primary_metric": "sharpe_ratio",
            },
        },
        "optimization": {
            "n_trials": 5,  # Very low for quick test
            "timeout": None,
            "enable_baseline": True,
            "enable_optimization": False,  # Skip optimization for speed
            "compare_baseline_vs_opt": False,
        },
        "validation": {
            "walk_forward": {"enabled": False, "n_windows": 2, "train_percentage": 0.6},
            "monte_carlo": {"enabled": False, "n_simulations": 100},
            "out_of_sample": {"enabled": False, "start_date": "2023-04-01", "end_date": "2023-06-30"},
            "thresholds": {
                "min_sharpe": 0.1,
                "max_drawdown": 0.5,
                "min_win_rate": 0.3,
                "min_trades": 5,
            },
        },
        "acceptance_criteria": {
            "min_sharpe": 0.3,
            "min_return": 0.01,
            "max_drawdown": -0.30,
        },
        "reporting": {
            "output_directory": "results/quick_profile_comparison",
            "output_formats": ["json"],
        },
    }


def main():
    """Run quick profile comparison."""
    print("\n" + "=" * 70)
    print("QUICK PROFILE COMPARISON - Small Time Sample")
    print("=" * 70)
    print("\nConfiguration:")
    print("  - Period: Jan 2023 - Mar 2023 (3 months)")
    print("  - Symbols: AAPL, MSFT, GOOGL")
    print("  - Optimization: DISABLED (baseline only)")
    print("  - Validation: DISABLED")
    print("")

    # Create temp config file
    config = create_quick_test_config()
    config_path = Path("results/quick_profile_config.yaml")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    # Create backtester
    print("Creating backtester...")
    backtester = ProfileBatchBacktester(str(config_path))

    # Define a few key profiles to compare
    profiles = [
        # Profile 1: Aggressive - Maximize Capital
        InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.ALTO,
            investment_horizon=12,
        ),
        # Profile 2: Balanced - Balanced Growth
        InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        ),
        # Profile 3: Conservative - Capital Preservation
        InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
            risk_tolerance=RiskTolerance.BAJO,
            investment_horizon=12,
        ),
    ]

    # Run profiles
    results = []
    print(f"\nRunning {len(profiles)} profiles...\n")

    for i, profile in enumerate(profiles, 1):
        print(f"[{i}/{len(profiles)}] Testing: {profile.objetivo_inversion.value} ({profile.risk_tolerance.value})")

        try:
            result = backtester.run_single_profile(
                profile,
                multi_strategy=False
            )
            results.append(result)
            print(f"  ✓ Completed - Sharpe: {result.baseline_results.get('sharpe_ratio', 0):.2f}")
        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")

    # Print comparison table
    print("\n" + "=" * 70)
    print("RESULTS COMPARISON")
    print("=" * 70)
    print(f"\n{'Profile':<30} {'Return':<12} {'Sharpe':<10} {'Max DD':<12} {'Win Rate':<10}")
    print("-" * 80)

    # Sort by total return (money made)
    results_by_return = sorted(
        results,
        key=lambda r: r.baseline_results.get('return_pct', 0),
        reverse=True
    )

    for result in results_by_return:
        profile_name = f"{result.profile.objetivo_inversion.value} ({result.profile.risk_tolerance.value})"
        ret = result.baseline_results.get('return_pct', 0) * 100
        sharpe = result.baseline_results.get('sharpe_ratio', 0)
        dd = result.baseline_results.get('max_drawdown', 0) * 100
        wr = result.baseline_results.get('win_rate', 0) * 100

        # Mark winner
        marker = " 👑" if result == results_by_return[0] else ""
        print(f"{profile_name:<30} {ret:>10.2f}%{marker} {sharpe:>9.2f} {dd:>10.2f}% {wr:>9.1f}%")

    # Calculate profit in EUR
    print("\n" + "-" * 80)
    print("PROFIT (EUR) with €100,000 initial capital:")
    print("-" * 80)

    for result in results_by_return:
        profile_name = f"{result.profile.objetivo_inversion.value} ({result.profile.risk_tolerance.value})"
        ret_pct = result.baseline_results.get('return_pct', 0)
        profit = 100000 * ret_pct
        marker = " 👑" if result == results_by_return[0] else ""
        print(f"  {profile_name:<45} €{profit:>10,.2f}{marker}")

    # Summary
    winner = results_by_return[0]
    print("\n" + "=" * 70)
    print("WINNER:")
    print("=" * 70)
    print(f"  Profile: {winner.profile.objetivo_inversion.value} ({winner.profile.risk_tolerance.value})")
    print(f"  Profit: €{100000 * winner.baseline_results.get('return_pct', 0):,.2f}")
    print(f"  Return: {winner.baseline_results.get('return_pct', 0) * 100:.2f}%")
    print(f"  Sharpe: {winner.baseline_results.get('sharpe_ratio', 0):.2f}")
    print(f"  Max Drawdown: {winner.baseline_results.get('max_drawdown', 0) * 100:.2f}%")
    print(f"  Win Rate: {winner.baseline_results.get('win_rate', 0) * 100:.1f}%")

    print("\n✅ Quick test completed successfully!")
    print(f"Config saved to: {config_path}")
    print(f"Results saved to: {config['output_dir']}/")


if __name__ == "__main__":
    main()
