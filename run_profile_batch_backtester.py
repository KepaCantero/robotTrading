#!/usr/bin/env python
"""
Profile Batch Backtester - Quick Start Script

This script provides a quick way to run the ProfileBatchBacktester
with sensible defaults.

Usage:
    # Run all 180 profiles (parallel)
    python run_profile_batch_backtester.py --all --parallel

    # Run a single profile
    python run_profile_batch_backtester.py --single --objective maximizar_capital --risk medio

    # Generate comparison report only
    python run_profile_batch_backtester.py --report

    # Get best strategy
    python run_profile_batch_backtester.py --best --objective maximizar_capital --risk medio --tier medio
"""

import argparse
import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.backtesting.profile_batch_backtester import ProfileBatchBacktester
from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/profile_batch_backtesting.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def run_all_profiles(parallel: bool = True, max_workers: int = 20):
    """
    Run all 180 profile combinations.

    Args:
        parallel: Whether to run profiles in parallel
        max_workers: Maximum number of parallel workers
    """
    logger.info("=" * 80)
    logger.info("RUNNING ALL PROFILE COMBINATIONS")
    logger.info("=" * 80)

    backtester = ProfileBatchBacktester(
        config_path="config/profile_batch_backtest.yaml"
    )

    logger.info(f"Running with parallel={parallel}, max_workers={max_workers}")

    start_time = datetime.now()
    results = backtester.run_all_profiles(parallel=parallel, max_workers=max_workers)
    duration = (datetime.now() - start_time).total_seconds()

    logger.info("=" * 80)
    logger.info(f"COMPLETED: {len(results)} profiles in {duration:.1f} seconds")
    logger.info("=" * 80)

    # Summary stats
    ready_count = sum(1 for r in results.values() if r.ready_for_paper_trading)
    logger.info(f"Ready for paper trading: {ready_count}/{len(results)}")

    # Export results
    logger.info("\nExporting results...")
    json_path = backtester.export_results(format="json")
    csv_path = backtester.export_results(format="csv")
    excel_path = backtester.export_results(format="excel")

    logger.info(f"  JSON: {json_path}")
    logger.info(f"  CSV: {csv_path}")
    logger.info(f"  Excel: {excel_path}")

    # Generate comparison report
    logger.info("\nGenerating comparison report...")
    html = backtester.generate_comparison_report()
    report_path = backtester.output_dir / f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(report_path, "w") as f:
        f.write(html)
    logger.info(f"  HTML Report: {report_path}")

    logger.info("\n✅ All done!")


def run_single_profile(objective: str, risk: str, capital: Decimal = None, horizon: int = None):
    """
    Run a single profile test.

    Args:
        objective: Investment objective
        risk: Risk tolerance
        capital: Initial capital (default from config)
        horizon: Investment horizon in months (default 24)
    """
    logger.info("=" * 80)
    logger.info("RUNNING SINGLE PROFILE")
    logger.info("=" * 80)

    # Map strings to enums
    try:
        objective_enum = ObjectivoInversion(objective)
        risk_enum = RiskTolerance(risk)
    except ValueError as e:
        logger.error(f"Invalid objective or risk: {e}")
        sys.exit(1)

    # Determine capital tier
    backtester = ProfileBatchBacktester(
        config_path="config/profile_batch_backtest.yaml"
    )

    # Get capital from risk tier if not specified
    if capital is None:
        tier_map = {"bajo": 50000, "medio": 150000, "alto": 500000}
        # Determine tier from risk
        if risk == "bajo":
            capital = Decimal(str(tier_map["bajo"]))
        elif risk == "medio":
            capital = Decimal(str(tier_map["medio"]))
        else:
            capital = Decimal(str(tier_map["alto"]))

    if horizon is None:
        horizon = 24

    # Create profile
    profile = InputProfile(
        capital_initial=capital,
        objetivo_inversion=objective_enum,
        risk_tolerance=risk_enum,
        investment_horizon=horizon,
    )

    logger.info(f"Profile: {objective}_{risk}_{capital}_{horizon}m")

    # Run profile
    result = backtester.run_single_profile(profile)

    # Print results
    logger.info("\n" + "=" * 80)
    logger.info("RESULTS")
    logger.info("=" * 80)
    logger.info(f"Baseline Sharpe: {result.baseline_results.get('sharpe_ratio', 0):.2f}")
    logger.info(f"Optimized Sharpe: {result.optimization_results.get('sharpe_ratio', 0):.2f}")
    logger.info(f"Sharpe Improvement: {result.improvement_metrics.get('sharpe_improvement', 0):.1f}%")
    logger.info(f"Baseline Return: {result.baseline_results.get('return_pct', 0):.2f}%")
    logger.info(f"Optimized Return: {result.optimization_results.get('return_pct', 0):.2f}%")
    logger.info(f"Return Improvement: {result.improvement_metrics.get('return_improvement', 0):.1f}%")
    logger.info(f"\nReady for paper trading: {result.ready_for_paper_trading}")
    logger.info(f"Recommendation: {result.recommendation}")

    # Export
    json_path = backtester.export_results(format="json")
    logger.info(f"\nResults exported to: {json_path}")


def generate_report_only():
    """Generate comparison report from existing database."""
    logger.info("=" * 80)
    logger.info("GENERATING COMPARISON REPORT")
    logger.info("=" * 80)

    backtester = ProfileBatchBacktester(
        config_path="config/profile_batch_backtest.yaml"
    )

    # Load results from database
    session = backtester.Session()
    from app.backtesting.profile_batch_backtester import ProfileResultDB

    all_results = session.query(ProfileResultDB).all()
    logger.info(f"Found {len(all_results)} profiles in database")

    if not all_results:
        logger.error("No results found in database. Run backtests first.")
        sys.exit(1)

    # Convert to ProfileResult objects
    from app.backtesting.profile_batch_backtester import BaselineOptimizationComparison, ProfileResult
    from app.core.models.input_profile import ObjectivoInversion, RiskTolerance

    for db_result in all_results:
        # Reconstruct profile
        profile = InputProfile(
            capital_initial=Decimal("100000"),  # Placeholder
            objetivo_inversion=ObjectivoInversion(db_result.objective),
            risk_tolerance=RiskTolerance(db_result.risk_tolerance),
            investment_horizon=db_result.investment_horizon,
        )

        # Create ProfileResult
        result = ProfileResult(
            profile_id=db_result.profile_id,
            profile=profile,
            baseline_results={
                "sharpe_ratio": db_result.baseline_sharpe,
                "return_pct": db_result.baseline_return,
            },
            optimization_results={
                "sharpe_ratio": db_result.optimized_sharpe,
                "return_pct": db_result.optimized_return,
            },
            best_parameters=db_result.best_parameters or {},
            improvement_metrics={
                "sharpe_improvement": db_result.sharpe_improvement,
                "return_improvement": db_result.return_improvement,
            },
            comparison=BaselineOptimizationComparison(
                sharpe_improvement=db_result.sharpe_improvement,
                return_improvement=db_result.return_improvement,
                max_dd_improvement=db_result.max_dd_improvement or 0,
                win_rate_improvement=db_result.win_rate_improvement or 0,
                sharpe_significant=True,
                return_significant=True,
                parameter_importance={},
                recommended="optimized" if db_result.sharpe_improvement > 0 else "baseline",
                confidence=0.7,
                reason="From database",
            ),
            ready_for_paper_trading=db_result.ready_for_paper_trading,
            recommendation=db_result.recommendation,
        )

        backtester.results[result.profile_id] = result

    session.close()

    # Generate report
    html = backtester.generate_comparison_report()

    report_path = backtester.output_dir / f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(report_path, "w") as f:
        f.write(html)

    logger.info(f"Report generated: {report_path}")


def get_best_strategy(objective: str, risk: str, tier: str):
    """
    Get best strategy for specific criteria.

    Args:
        objective: Investment objective
        risk: Risk tolerance
        tier: Capital tier
    """
    logger.info("=" * 80)
    logger.info("GETTING BEST STRATEGY")
    logger.info("=" * 80)

    backtester = ProfileBatchBacktester(
        config_path="config/profile_batch_backtest.yaml"
    )

    best_config = backtester.get_best_strategy(
        objective=objective,
        tier=tier,
        risk=risk
    )

    if not best_config:
        logger.error(f"No results found for {objective}_{tier}_{risk}")
        logger.info("Run backtests first with --all")
        sys.exit(1)

    logger.info(f"\nBest configuration for {objective}_{tier}_{risk}:")
    logger.info(f"  Profile ID: {best_config['profile_id']}")
    logger.info(f"\n  Baseline Metrics:")
    logger.info(f"    Sharpe: {best_config['baseline_metrics']['sharpe_ratio']:.2f}")
    logger.info(f"    Return: {best_config['baseline_metrics']['total_return']:.2f}%")
    logger.info(f"    Max DD: {best_config['baseline_metrics']['max_drawdown']:.2f}%")
    logger.info(f"\n  Optimized Metrics:")
    logger.info(f"    Sharpe: {best_config['optimized_metrics']['sharpe_ratio']:.2f}")
    logger.info(f"    Return: {best_config['optimized_metrics']['total_return']:.2f}%")
    logger.info(f"    Max DD: {best_config['optimized_metrics']['max_drawdown']:.2f}%")
    logger.info(f"\n  Improvements:")
    logger.info(f"    Sharpe: {best_config['improvement']['sharpe']:.1f}%")
    logger.info(f"    Return: {best_config['improvement']['return']:.1f}%")
    logger.info(f"    Max DD: {best_config['improvement']['max_dd']:.1f}%")
    logger.info(f"\n  Best Parameters:")
    for param, value in best_config['best_parameters'].items():
        logger.info(f"    {param}: {value}")
    logger.info(f"\n  Recommendation: {best_config['recommendation']}")
    logger.info(f"  Ready for Paper Trading: {best_config['ready_for_paper_trading']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Profile Batch Backtester - Quick Start",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all 180 profiles
  python run_profile_batch_backtester.py --all

  # Run single profile
  python run_profile_batch_backtester.py --single --objective maximizar_capital --risk medio

  # Generate report only
  python run_profile_batch_backtester.py --report

  # Get best strategy
  python run_profile_batch_backtester.py --best --objective maximizar_capital --risk medio --tier medio
        """
    )

    parser.add_argument("--all", action="store_true", help="Run all 180 profiles")
    parser.add_argument("--single", action="store_true", help="Run a single profile")
    parser.add_argument("--report", action="store_true", help="Generate comparison report only")
    parser.add_argument("--best", action="store_true", help="Get best strategy for criteria")

    parser.add_argument("--objective", type=str, help="Investment objective (e.g., maximizar_capital)")
    parser.add_argument("--risk", type=str, help="Risk tolerance (bajo, medio, alto)")
    parser.add_argument("--tier", type=str, help="Capital tier (bajo, medio, alto)")
    parser.add_argument("--capital", type=Decimal, help="Initial capital (for single profile)")
    parser.add_argument("--horizon", type=int, help="Investment horizon in months (for single profile)")

    parser.add_argument("--parallel", action="store_true", default=True, help="Use parallel execution")
    parser.add_argument("--sequential", action="store_true", help="Use sequential execution")
    parser.add_argument("--workers", type=int, default=20, help="Max parallel workers")

    args = parser.parse_args()

    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # Validate arguments
    if not any([args.all, args.single, args.report, args.best]):
        parser.print_help()
        sys.exit(1)

    try:
        if args.all:
            parallel = not args.sequential
            run_all_profiles(parallel=parallel, max_workers=args.workers)

        elif args.single:
            if not args.objective or not args.risk:
                logger.error("--single requires --objective and --risk")
                sys.exit(1)
            run_single_profile(args.objective, args.risk, args.capital, args.horizon)

        elif args.report:
            generate_report_only()

        elif args.best:
            if not args.objective or not args.risk or not args.tier:
                logger.error("--best requires --objective, --risk, and --tier")
                sys.exit(1)
            get_best_strategy(args.objective, args.risk, args.tier)

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(1)
    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
