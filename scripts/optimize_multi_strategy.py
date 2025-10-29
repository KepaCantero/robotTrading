#!/usr/bin/env python3
"""
Script to optimize multi-strategy parameters using Optuna.

Usage:
    python scripts/optimize_multi_strategy.py --symbol AAPL --trials 100 --metric sharpe
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.optimization.multi_strategy_optimizer import MultiStrategyOptimizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Optimize multi-strategy parameters")
    parser.add_argument(
        "--symbol",
        type=str,
        default="AAPL",
        help="Symbol to backtest (default: AAPL)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=100000.0,
        help="Total capital (default: 100000)",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=50,
        help="Number of optimization trials (default: 50)",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=10,
        help="Number of years to backtest (default: 10)",
    )
    parser.add_argument(
        "--metric",
        type=str,
        choices=["sharpe", "return", "calmar"],
        default="sharpe",
        help="Metric to optimize (default: sharpe)",
    )
    parser.add_argument(
        "--storage",
        type=str,
        default=None,
        help="Path to SQLite storage for study persistence",
    )
    parser.add_argument(
        "--study-name",
        type=str,
        default="multi_strategy_optimization",
        help="Name of the Optuna study",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing study",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="optimized_strategy_config.json",
        help="Output file for best configuration (default: optimized_strategy_config.json)",
    )
    
    args = parser.parse_args()
    
    # Calculate dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * args.years)
    
    logger.info("=" * 80)
    logger.info("Multi-Strategy Parameter Optimization")
    logger.info("=" * 80)
    logger.info(f"Symbol: {args.symbol}")
    logger.info(f"Capital: ${args.capital:,.2f}")
    logger.info(f"Period: {start_date.date()} to {end_date.date()} ({args.years} years)")
    logger.info(f"Trials: {args.trials}")
    logger.info(f"Metric: {args.metric}")
    logger.info("=" * 80)
    
    # Create optimizer
    optimizer = MultiStrategyOptimizer(
        total_capital=Decimal(str(args.capital)),
        symbol=args.symbol,
        start_date=start_date,
        end_date=end_date,
        n_trials=args.trials,
        objective_metric=args.metric,
    )
    
    # Run optimization
    study = optimizer.optimize(
        storage=args.storage,
        study_name=args.study_name,
        resume=args.resume,
    )
    
    # Get best configuration
    best_config = optimizer.get_best_config()
    
    # Run final backtest
    logger.info("\nRunning final backtest with optimized parameters...")
    final_results = optimizer.run_backtest_with_best_params()
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("OPTIMIZATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Best {args.metric}: {optimizer.best_value:.4f}")
    logger.info(f"\nBest Parameters:")
    
    # Strategy parameters
    for strategy_name, strategy_params in best_config.items():
        if strategy_name == "allocation":
            continue
        logger.info(f"\n{strategy_name.upper()}:")
        for param, value in strategy_params.items():
            logger.info(f"  {param}: {value}")
    
    # Allocation
    logger.info(f"\nCAPITAL ALLOCATION:")
    for strategy_name, weight in best_config["allocation"].items():
        allocated = args.capital * weight
        logger.info(f"  {strategy_name}: {weight:.1%} (${allocated:,.2f})")
    
    # Final results
    logger.info(f"\nFINAL BACKTEST RESULTS:")
    logger.info(f"  Total Return: {final_results['combined']['total_return']:.2f}%")
    logger.info(f"  Total Trades: {final_results['combined']['total_trades']}")
    logger.info(f"  Weighted Sharpe: {final_results['combined']['weighted_sharpe']:.4f}")
    logger.info(f"  Weighted Max DD: {final_results['combined']['weighted_max_dd']:.2f}%")
    
    # Per-strategy results
    logger.info(f"\nPER-STRATEGY RESULTS:")
    for strategy_name, result in final_results["per_strategy"].items():
        logger.info(f"  {strategy_name}:")
        logger.info(f"    Return: {result['total_return']:.2f}%")
        logger.info(f"    Trades: {result['total_trades']}")
        logger.info(f"    Win Rate: {result['win_rate']:.1%}")
        if result.get('sharpe_ratio'):
            logger.info(f"    Sharpe: {result['sharpe_ratio']:.4f}")
        logger.info(f"    Max DD: {result.get('max_drawdown', 0):.2f}%")
    
    # Save best configuration
    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(best_config, f, indent=2, default=str)
    
    logger.info(f"\nBest configuration saved to: {output_path}")
    
    # Save study visualization
    try:
        import optuna.visualization as vis
        
        # Create output directory
        output_dir = Path("docs/OPTIMIZATION_RESULTS")
        output_dir.mkdir(exist_ok=True)
        
        # Save optimization history plot
        fig = vis.plot_optimization_history(study)
        fig.write_html(str(output_dir / "optimization_history.html"))
        logger.info(f"Optimization history saved to: {output_dir / 'optimization_history.html'}")
        
        # Save parameter importance plot
        try:
            fig = vis.plot_param_importances(study)
            fig.write_html(str(output_dir / "param_importances.html"))
            logger.info(f"Parameter importance saved to: {output_dir / 'param_importances.html'}")
        except Exception as e:
            logger.warning(f"Could not generate parameter importance plot: {e}")
        
    except ImportError:
        logger.warning("optuna.visualization not available, skipping plots")
    
    logger.info("\n" + "=" * 80)
    logger.info("Optimization complete!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

