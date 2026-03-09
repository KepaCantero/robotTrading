#!/usr/bin/env python3
"""
Unified Optimization CLI

Central entry point for all optimization backtests.

Usage:
    # List available optimization types and symbols
    python scripts/optimization/run_optimization.py --list

    # Run Bayesian optimization (Optuna) with ALL downloaded symbols
    python scripts/optimization/run_optimization.py --type bayesian --years 10 --trials 100

    # Run with specific symbols
    python scripts/optimization/run_optimization.py --type bayesian --symbols AAPL,MSFT,NVDA

    # Run Grid Search with all symbols
    python scripts/optimization/run_optimization.py --type grid --years 5

    # Run Multi-Strategy optimization
    python scripts/optimization/run_optimization.py --type multi-strategy

    # Run Hyperparameter optimization
    python scripts/optimization/run_optimization.py --type hyperparameter --metric sharpe_ratio

    # Run all optimizations
    python scripts/optimization/run_optimization.py --type all

Optimization Types:
    - bayesian:         Optuna-based multi-strategy optimization (TPE sampler)
    - grid:             Exhaustive grid search with walk-forward validation
    - multi-strategy:   Portfolio-level strategy optimization
    - hyperparameter:   Hyperparameter tuning for momentum strategies
    - all:              Run all optimization types sequentially

Note: By default, ALL downloaded symbols in data/historical/ are used.
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional, List

# Threading configuration (must be before any imports)
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Default output directory
DEFAULT_OUTPUT_DIR = Path("docs/OPTIMIZATION_RESULTS")

# Historical data directory
HISTORICAL_DATA_DIR = project_root / "data" / "historical"


def get_available_symbols() -> List[str]:
    """Get all available symbols from data/historical/ directory."""
    symbols = []
    if HISTORICAL_DATA_DIR.exists():
        for csv_file in HISTORICAL_DATA_DIR.glob("*.csv"):
            symbols.append(csv_file.stem)
    return sorted(symbols)


def parse_symbols(symbols_str: Optional[str]) -> List[str]:
    """Parse symbols from comma-separated string or return all available."""
    if symbols_str:
        return [s.strip().upper() for s in symbols_str.split(",")]
    return get_available_symbols()


def run_bayesian_optimization(args, symbols: List[str]) -> int:
    """Run Optuna-based Bayesian optimization across multiple symbols."""
    from app.optimization.multi_strategy_optimizer_v2 import MultiStrategyOptimizerV2

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * args.years)
    output_dir = Path(args.output_dir) / "bayesian"

    print("\n" + "=" * 80)
    print("BAYESIAN OPTIMIZATION (Optuna TPE)")
    print("=" * 80)
    print(f"Symbols: {len(symbols)} stocks")
    print(f"  {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({args.years} years)")
    print(f"Capital: ${args.capital:,.2f}")
    print(f"Trials: {args.trials}")
    print(f"Output: {output_dir}")
    print("=" * 80 + "\n")

    all_results = {}

    for symbol in symbols:
        print(f"\n--- Optimizing {symbol} ({symbols.index(symbol)+1}/{len(symbols)}) ---")

        try:
            optimizer = MultiStrategyOptimizerV2(
                start_date=start_date,
                end_date=end_date,
                total_capital=Decimal(str(args.capital)),
                output_dir=output_dir / symbol,
                max_runs=args.trials,
            )

            result = optimizer.run_optimization(
                n_trials=args.trials,
                timeout=args.timeout,
            )
            all_results[symbol] = result
            print(f"  {symbol} Best Score: {result['best_score']:.4f}")

        except Exception as e:
            logger.error(f"Error optimizing {symbol}: {e}")
            all_results[symbol] = {"error": str(e)}

    # Summary
    print("\n" + "=" * 80)
    print("BAYESIAN OPTIMIZATION COMPLETE - ALL SYMBOLS")
    print("=" * 80)

    successful = {k: v for k, v in all_results.items() if "error" not in v}
    if successful:
        best_symbol = max(successful.items(), key=lambda x: x[1].get('best_score', 0))
        print(f"Best Overall: {best_symbol[0]} with score {best_symbol[1].get('best_score', 0):.4f}")

    print(f"Successful: {len(successful)}/{len(symbols)}")
    print(f"Results saved to: {output_dir}")
    print("=" * 80)

    return 0


def run_grid_search(args, symbols: List[str]) -> int:
    """Run Grid Search optimization across multiple symbols."""
    from app.optimization.grid_search_optimizer import GridSearchOptimizer

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * args.years)
    output_dir = Path(args.output_dir) / "grid_search"

    print("\n" + "=" * 80)
    print("GRID SEARCH OPTIMIZATION")
    print("=" * 80)
    print(f"Symbols: {len(symbols)} stocks")
    print(f"  {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({args.years} years)")
    print(f"Capital: ${args.capital:,.2f}")
    print(f"Max Combinations: {args.max_combinations or 'All'}")
    print(f"Output: {output_dir}")
    print("=" * 80 + "\n")

    all_results = {}

    for symbol in symbols:
        print(f"\n--- Grid Search {symbol} ({symbols.index(symbol)+1}/{len(symbols)}) ---")

        try:
            optimizer = GridSearchOptimizer(
                start_date=start_date,
                end_date=end_date,
                total_capital=Decimal(str(args.capital)),
                output_dir=output_dir / symbol,
            )

            result = optimizer.optimize(max_combinations=args.max_combinations)
            all_results[symbol] = result
            print(f"  {symbol} Best Score: {result['best_score']:.4f}")

        except Exception as e:
            logger.error(f"Error in grid search for {symbol}: {e}")
            all_results[symbol] = {"error": str(e)}

    # Summary
    print("\n" + "=" * 80)
    print("GRID SEARCH COMPLETE - ALL SYMBOLS")
    print("=" * 80)

    successful = {k: v for k, v in all_results.items() if "error" not in v}
    if successful:
        best_symbol = max(successful.items(), key=lambda x: x[1].get('best_score', 0))
        print(f"Best Overall: {best_symbol[0]} with score {best_symbol[1].get('best_score', 0):.4f}")

    print(f"Successful: {len(successful)}/{len(symbols)}")
    print(f"Results saved to: {output_dir}")
    print("=" * 80)

    return 0


def run_multi_strategy(args, symbols: List[str]) -> int:
    """Run Multi-Strategy optimization across multiple symbols."""
    from app.optimization.multi_strategy_optimizer import MultiStrategyOptimizer

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * args.years)
    output_dir = Path(args.output_dir) / "multi_strategy"

    print("\n" + "=" * 80)
    print("MULTI-STRATEGY OPTIMIZATION")
    print("=" * 80)
    print(f"Symbols: {len(symbols)} stocks")
    print(f"  {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({args.years} years)")
    print(f"Capital: ${args.capital:,.2f}")
    print(f"Trials: {args.trials}")
    print(f"Metric: {args.metric}")
    print(f"Output: {output_dir}")
    print("=" * 80 + "\n")

    all_results = {}

    for symbol in symbols:
        print(f"\n--- Multi-Strategy {symbol} ({symbols.index(symbol)+1}/{len(symbols)}) ---")

        try:
            optimizer = MultiStrategyOptimizer(
                total_capital=Decimal(str(args.capital)),
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                n_trials=args.trials,
                objective_metric=args.metric,
            )

            study = optimizer.optimize(
                storage=args.storage,
                study_name=f"{args.study_name}_{symbol}",
                resume=args.resume,
            )

            best_config = optimizer.get_best_config()
            final_results = optimizer.run_backtest_with_best_params()

            all_results[symbol] = {
                "best_value": optimizer.best_value,
                "total_return": final_results['combined']['total_return'],
                "weighted_sharpe": final_results['combined']['weighted_sharpe'],
            }

            print(f"  {symbol} Best {args.metric}: {optimizer.best_value:.4f}")
            print(f"  Return: {final_results['combined']['total_return']:.2f}%")

            # Save config for this symbol
            import json
            config_path = output_dir / symbol / "best_config.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(best_config, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error in multi-strategy for {symbol}: {e}")
            all_results[symbol] = {"error": str(e)}

    # Summary
    print("\n" + "=" * 80)
    print("MULTI-STRATEGY OPTIMIZATION COMPLETE - ALL SYMBOLS")
    print("=" * 80)

    successful = {k: v for k, v in all_results.items() if "error" not in v}
    if successful:
        best_symbol = max(successful.items(), key=lambda x: x[1].get('best_value', 0))
        print(f"Best Overall: {best_symbol[0]} with {args.metric} {best_symbol[1].get('best_value', 0):.4f}")

    print(f"Successful: {len(successful)}/{len(symbols)}")
    print(f"Results saved to: {output_dir}")
    print("=" * 80)

    return 0


def run_hyperparameter(args, symbols: List[str]) -> int:
    """Run Hyperparameter optimization across multiple symbols."""
    from app.strategies.momentum_modular.optimization.hyperparameter_optimizer import HyperparameterOptimizer

    year = datetime.now().year - 1 if args.years == 1 else datetime.now().year - args.years
    start_date = datetime(year, 1, 1)
    end_date = datetime(year + args.years - 1, 12, 31)
    output_dir = Path(args.output_dir) / "hyperparameter"

    print("\n" + "=" * 80)
    print("HYPERPARAMETER OPTIMIZATION")
    print("=" * 80)
    print(f"Symbols: {len(symbols)} stocks")
    print(f"  {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Capital: ${args.capital:,.2f}")
    print(f"Metric: {args.metric}")
    print(f"Method: {args.method}")
    print(f"Iterations: {args.trials}")
    print(f"Output: {output_dir}")
    print("=" * 80 + "\n")

    all_results = {}

    for symbol in symbols:
        print(f"\n--- Hyperparameter {symbol} ({symbols.index(symbol)+1}/{len(symbols)}) ---")

        try:
            optimizer = HyperparameterOptimizer(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_capital=Decimal(str(args.capital)),
                optimization_metric=args.metric,
                optimization_method=args.method,
            )

            results = optimizer.optimize(
                max_iterations=args.trials,
                random_seed=args.seed,
            )

            all_results[symbol] = results
            print(f"  {symbol} Best Score: {results['best_score']:.4f}")

        except Exception as e:
            logger.error(f"Error in hyperparameter optimization for {symbol}: {e}")
            all_results[symbol] = {"error": str(e)}

    # Summary
    print("\n" + "=" * 80)
    print("HYPERPARAMETER OPTIMIZATION COMPLETE - ALL SYMBOLS")
    print("=" * 80)

    successful = {k: v for k, v in all_results.items() if "error" not in v}
    if successful:
        best_symbol = max(successful.items(), key=lambda x: x[1].get('best_score', 0))
        print(f"Best Overall: {best_symbol[0]} with score {best_symbol[1].get('best_score', 0):.4f}")

        print("\nTop 5 Configurations:")
        sorted_results = sorted(successful.items(), key=lambda x: x[1].get('best_score', 0), reverse=True)[:5]
        for sym, res in sorted_results:
            print(f"  {sym}: {res.get('best_score', 0):.4f}")

    print(f"\nSuccessful: {len(successful)}/{len(symbols)}")
    print(f"Results saved to: {output_dir}")
    print("=" * 80)

    return 0


def run_all_optimizations(args, symbols: List[str]) -> int:
    """Run all optimization types sequentially across all symbols."""
    print("\n" + "=" * 80)
    print("RUNNING ALL OPTIMIZATIONS")
    print(f"Symbols: {len(symbols)} stocks")
    print("=" * 80)

    results = {}

    # Run each optimization type
    for opt_type in ["bayesian", "grid", "multi-strategy", "hyperparameter"]:
        print(f"\n{'='*40}")
        print(f"Starting: {opt_type.upper()}")
        print(f"{'='*40}")

        try:
            if opt_type == "bayesian":
                result = run_bayesian_optimization(args, symbols)
            elif opt_type == "grid":
                result = run_grid_search(args, symbols)
            elif opt_type == "multi-strategy":
                result = run_multi_strategy(args, symbols)
            elif opt_type == "hyperparameter":
                result = run_hyperparameter(args, symbols)

            results[opt_type] = {"status": "success", "exit_code": result}
        except Exception as e:
            logger.error(f"Error in {opt_type}: {e}")
            results[opt_type] = {"status": "error", "message": str(e)}

    # Summary
    print("\n" + "=" * 80)
    print("ALL OPTIMIZATIONS COMPLETE")
    print("=" * 80)
    for opt_type, result in results.items():
        status = result["status"]
        if status == "success":
            print(f"  {opt_type}: SUCCESS")
        else:
            print(f"  {opt_type}: FAILED - {result.get('message', 'Unknown error')}")

    print("=" * 80)

    return 0


def list_optimization_types():
    """Print available optimization types and symbols."""
    available_symbols = get_available_symbols()

    print("\n" + "=" * 80)
    print("AVAILABLE OPTIMIZATION TYPES")
    print("=" * 80)

    types = [
        ("bayesian", "Optuna-based Bayesian optimization with TPE sampler. Best for finding optimal parameters efficiently."),
        ("grid", "Exhaustive grid search with walk-forward validation. Best for thorough parameter exploration."),
        ("multi-strategy", "Portfolio-level optimization across multiple strategies. Best for capital allocation."),
        ("hyperparameter", "Hyperparameter tuning for momentum strategies. Best for indicator parameters."),
        ("all", "Run all optimization types sequentially."),
    ]

    for name, desc in types:
        print(f"\n  {name}:")
        print(f"    {desc}")

    print("\n" + "=" * 80)
    print(f"AVAILABLE SYMBOLS ({len(available_symbols)} stocks)")
    print("=" * 80)

    # Print symbols in rows of 10
    for i in range(0, len(available_symbols), 10):
        row = available_symbols[i:i+10]
        print(f"  {', '.join(row)}")

    print("\n" + "=" * 80)
    print("EXAMPLES")
    print("=" * 80)
    print("""
    # Bayesian optimization with ALL symbols (default)
    python scripts/optimization/run_optimization.py --type bayesian --years 10 --trials 100

    # With specific symbols only
    python scripts/optimization/run_optimization.py --type bayesian --symbols AAPL,MSFT,NVDA

    # Grid search with all symbols
    python scripts/optimization/run_optimization.py --type grid --years 5 --max-combinations 500

    # Multi-strategy optimization
    python scripts/optimization/run_optimization.py --type multi-strategy --metric sharpe

    # Hyperparameter with random search
    python scripts/optimization/run_optimization.py --type hyperparameter --method random_search

    # Run all optimizations
    python scripts/optimization/run_optimization.py --type all --years 5 --trials 50
    """)
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Unified Optimization CLI - Central entry point for all optimization backtests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/optimization/run_optimization.py --list
    python scripts/optimization/run_optimization.py --type bayesian --years 10 --trials 100
    python scripts/optimization/run_optimization.py --type bayesian --symbols AAPL,MSFT,NVDA
    python scripts/optimization/run_optimization.py --type grid --years 5
    python scripts/optimization/run_optimization.py --type multi-strategy --metric sharpe
    python scripts/optimization/run_optimization.py --type hyperparameter --metric sharpe_ratio
    python scripts/optimization/run_optimization.py --type all
        """,
    )

    # Main argument
    parser.add_argument(
        "--type",
        type=str,
        choices=["bayesian", "grid", "multi-strategy", "hyperparameter", "all"],
        default="bayesian",
        help="Optimization type to run (default: bayesian)",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List available optimization types and symbols, then exit",
    )

    # Symbol selection
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated list of symbols (default: ALL downloaded symbols)",
    )

    # Common arguments
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
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )

    # Optimization-specific arguments
    parser.add_argument(
        "--trials",
        type=int,
        default=100,
        help="Number of optimization trials/iterations (default: 100)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Timeout in seconds (default: None)",
    )
    parser.add_argument(
        "--metric",
        type=str,
        choices=["sharpe", "sharpe_ratio", "return", "total_pnl", "win_rate", "calmar", "combined"],
        default="sharpe",
        help="Optimization metric (default: sharpe)",
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["grid_search", "random_search", "bayesian"],
        default="random_search",
        help="Optimization method for hyperparameter (default: random_search)",
    )
    parser.add_argument(
        "--max-combinations",
        type=int,
        default=None,
        help="Maximum combinations for grid search (default: all)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    # Multi-strategy specific
    parser.add_argument(
        "--storage",
        type=str,
        default=None,
        help="Path to SQLite storage for Optuna study persistence",
    )
    parser.add_argument(
        "--study-name",
        type=str,
        default="optimization_study",
        help="Name of the Optuna study",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing Optuna study",
    )

    args = parser.parse_args()

    # Normalize metric name
    if args.metric == "sharpe":
        args.metric = "sharpe"

    # List and exit
    if args.list:
        list_optimization_types()
        return 0

    # Parse symbols (use all available if not specified)
    symbols = parse_symbols(args.symbols)

    if not symbols:
        logger.error("No symbols found. Download data first or use --symbols option.")
        return 1

    logger.info(f"Using {len(symbols)} symbols: {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")

    # Ensure output directory exists
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Run selected optimization
    if args.type == "bayesian":
        return run_bayesian_optimization(args, symbols)
    elif args.type == "grid":
        return run_grid_search(args, symbols)
    elif args.type == "multi-strategy":
        return run_multi_strategy(args, symbols)
    elif args.type == "hyperparameter":
        return run_hyperparameter(args, symbols)
    elif args.type == "all":
        return run_all_optimizations(args, symbols)
    else:
        logger.error(f"Unknown optimization type: {args.type}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("\nOptimization interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
