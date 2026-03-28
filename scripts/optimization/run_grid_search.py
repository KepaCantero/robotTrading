#!/usr/bin/env python3
"""
Run Grid Search Optimization with Walk-Forward Validation - TASK-PARAM-2

Executes grid search over parameter combinations with walk-forward validation.
"""

import sys
import argparse
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.optimization.grid_search_optimizer import GridSearchOptimizer


def main():
    parser = argparse.ArgumentParser(description="Grid Search Optimization with Walk-Forward")
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
        "--max-combinations",
        type=int,
        default=None,
        help="Maximum combinations to test (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="docs/GRID_SEARCH_RESULTS",
        help="Output directory (default: docs/GRID_SEARCH_RESULTS)",
    )

    args = parser.parse_args()

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * args.years)

    print("=" * 80)
    print("🔍 GRID SEARCH OPTIMIZATION")
    print("=" * 80)
    print(
        f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({args.years} years)"
    )
    print(f"Capital: ${args.capital:,.2f}")
    print(f"Max Combinations: {args.max_combinations or 'All'}")
    print(f"Output: {args.output_dir}")
    print("=" * 80)

    # Initialize optimizer
    optimizer = GridSearchOptimizer(
        start_date=start_date,
        end_date=end_date,
        total_capital=Decimal(str(args.capital)),
        output_dir=Path(args.output_dir),
    )

    # Run optimization
    print("\n🔍 Starting grid search...")
    result = optimizer.optimize(max_combinations=args.max_combinations)

    print("\n" + "=" * 80)
    print("✅ GRID SEARCH COMPLETE")
    print("=" * 80)
    print(f"Best Score: {result['best_score']:.4f}")
    print(f"Combinations Tested: {result['total_tested']}")
    print(f"\nBest Config saved to: {Path(args.output_dir) / 'best_grid_search_config_*.json'}")
    print(f"Full results saved to: {Path(args.output_dir) / 'grid_search_results_*.csv'}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
