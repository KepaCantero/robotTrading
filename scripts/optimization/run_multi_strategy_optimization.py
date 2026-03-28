#!/usr/bin/env python3
"""
Run Multi-Strategy Automated Optimization.

Executes Optuna-based optimization of multi-strategy backtesting parameters.
"""

import sys
import argparse
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.optimization.multi_strategy_optimizer_v2 import MultiStrategyOptimizerV2


def main():
    parser = argparse.ArgumentParser(description="Multi-Strategy Backtest Optimization")
    parser.add_argument(
        "--years",
        type=int,
        default=10,
        help="Years of historical data (default: 10)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=100000,
        help="Total capital (default: 100000)",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=200,
        help="Maximum optimization runs (default: 200)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Timeout in seconds (default: None)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="docs/OPTIMIZATION_RESULTS",
        help="Output directory (default: docs/OPTIMIZATION_RESULTS)",
    )

    args = parser.parse_args()

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * args.years)

    print("=" * 80)
    print("🚀 MULTI-STRATEGY OPTIMIZATION")
    print("=" * 80)
    print(
        f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({args.years} years)"
    )
    print(f"Capital: ${args.capital:,.2f}")
    print(f"Max Runs: {args.max_runs}")
    print(f"Output: {args.output_dir}")
    print("=" * 80)

    # Initialize optimizer
    optimizer = MultiStrategyOptimizerV2(
        start_date=start_date,
        end_date=end_date,
        total_capital=Decimal(str(args.capital)),
        output_dir=Path(args.output_dir),
        max_runs=args.max_runs,
    )

    # Run optimization
    print("\n🔍 Starting optimization...")
    result = optimizer.run_optimization(
        n_trials=args.max_runs,
        timeout=args.timeout,
    )

    print("\n" + "=" * 80)
    print("✅ OPTIMIZATION COMPLETE")
    print("=" * 80)
    print(f"Best Score: {result['best_score']:.4f}")
    print(f"Trials: {result['n_trials']}")
    print(f"\nBest Config saved to: {Path(args.output_dir) / 'best_config.json'}")
    print(f"Full results saved to: {Path(args.output_dir) / 'opt_results.csv'}")
    print(f"Summary saved to: {Path(args.output_dir) / 'optimization_summary.json'}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
