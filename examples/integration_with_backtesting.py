"""
Integration Example: Using BaselineOptimizationReporter with Existing Backtesting

This example shows how to integrate the BaselineOptimizationReporter
with the existing backtesting system to generate comparison reports.

Usage:
    python examples/integration_with_backtesting.py
"""

import logging
from decimal import Decimal
from pathlib import Path

from app.backtesting.reports.baseline_optimization_reporter import (
    BaselineOptimizationReporter,
)
from app.core.models.input_profile import InputProfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_from_backtest_results():
    """
    Example: Generate comparison report from actual backtest results.

    This shows the typical workflow after running backtests.
    """
    logger.info("=" * 80)
    logger.info("Integration Example: From Backtest Results")
    logger.info("=" * 80)

    # Step 1: Create your input profile (user parameters)
    profile = InputProfile(
        capital_initial=Decimal("250000"),
        objetivo_inversion="maximizar_capital",
        risk_tolerance="alto",
        investment_horizon=36,
    )

    # Step 2: Run your baseline backtest
    # (This would typically come from your backtesting engine)
    baseline_results = run_baseline_backtest(profile)

    # Step 3: Run your optimized backtest
    # (This would typically come from your optimization engine)
    optimized_results = run_optimized_backtest(profile)

    # Step 4: (Optional) Run walk-forward validation
    walk_forward_results = run_walk_forward_validation(profile)

    # Step 5: Generate comparison report
    reporter = BaselineOptimizationReporter()

    html = reporter.generate_report(
        profile=profile,
        baseline_results=baseline_results,
        optimization_results=optimized_results,
        walk_forward_results=walk_forward_results,
    )

    # Step 6: Save report
    output_path = Path("reports/integration_comparison.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    reporter.save_report(html, str(output_path))

    logger.info(f"✅ Comparison report saved to: {output_path}")

    return html


def run_baseline_backtest(profile: InputProfile) -> dict:
    """
    Simulate running a baseline backtest.

    In production, this would call your actual backtesting engine:
    - app/backtesting/comprehensive_backtest_runner.py
    - app/backtesting/execution_engine.py
    """
    logger.info("Running baseline backtest...")

    # Simulate backtest results
    # In production, these come from your backtesting system
    from datetime import datetime, timedelta

    import numpy as np

    np.random.seed(42)

    # Generate sample equity curve
    months = 36
    dates = [datetime.now() - timedelta(days=30 * (months - i)) for i in range(months)]

    # Simulate strategy performance
    returns = np.random.normal(0.015, 0.08, months)  # 1.5% monthly return, 8% vol
    values = [float(profile.capital_initial)]

    for ret in returns[1:]:
        values.append(values[-1] * (1 + ret))

    equity_curve = list(zip(dates, values))

    # Calculate metrics
    total_return = (values[-1] - values[0]) / values[0] * 100
    monthly_returns = np.diff(values) / values[:-1]
    sharpe = np.mean(monthly_returns) / np.std(monthly_returns) * np.sqrt(12)

    return {
        "start_date": dates[0].strftime("%Y-%m-%d"),
        "end_date": dates[-1].strftime("%Y-%m-%d"),
        "equity_curve": equity_curve,
        "performance": {
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sharpe * 1.3, 2),
            "calmar_ratio": round(abs(sharpe / 1.5), 2),
            "omega_ratio": round(sharpe * 0.9, 2),
            "total_return": round(total_return, 2),
            "max_drawdown_percentage": round(-abs(np.min(values) / np.max(values) - 1) * 100, 2),
            "win_rate": round(50 + np.random.uniform(-2, 2), 1),
            "profit_factor": round(1.3 + np.random.uniform(-0.1, 0.1), 2),
            "volatility_annualized": round(np.std(monthly_returns) * np.sqrt(12) * 100, 2),
            "ulcer_index": round(5.0 + np.random.uniform(-1, 1), 2),
            "var_95": round(-2.0, 2),
            "cvar_95": round(-3.5, 2),
        },
        "parameters": {
            # Default/baseline parameters
            "lookback_period": 20,
            "entry_threshold": 2.0,
            "exit_threshold": 1.0,
            "position_size": 0.02,
            "stop_loss": 0.05,
        },
    }


def run_optimized_backtest(profile: InputProfile) -> dict:
    """
    Simulate running an optimized backtest.

    In production, this would call your optimization engine:
    - Parameter optimization results
    - Grid search / Bayesian optimization
    - Walk-forward optimal parameters
    """
    logger.info("Running optimized backtest...")

    from datetime import datetime, timedelta

    import numpy as np

    np.random.seed(43)  # Different seed for optimized

    months = 36
    dates = [datetime.now() - timedelta(days=30 * (months - i)) for i in range(months)]

    # Optimized strategy: better returns, lower volatility
    returns = np.random.normal(0.019, 0.07, months)  # 1.9% monthly, 7% vol
    values = [float(profile.capital_initial)]

    for ret in returns[1:]:
        values.append(values[-1] * (1 + ret))

    equity_curve = list(zip(dates, values))

    total_return = (values[-1] - values[0]) / values[0] * 100
    monthly_returns = np.diff(values) / values[:-1]
    sharpe = np.mean(monthly_returns) / np.std(monthly_returns) * np.sqrt(12)

    return {
        "start_date": dates[0].strftime("%Y-%m-%d"),
        "end_date": dates[-1].strftime("%Y-%m-%d"),
        "equity_curve": equity_curve,
        "performance": {
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sharpe * 1.4, 2),
            "calmar_ratio": round(abs(sharpe / 1.2), 2),
            "omega_ratio": round(sharpe * 1.0, 2),
            "total_return": round(total_return, 2),
            "max_drawdown_percentage": round(-abs(np.min(values) / np.max(values) - 1) * 100, 2),
            "win_rate": round(54 + np.random.uniform(-1, 1), 1),
            "profit_factor": round(1.6 + np.random.uniform(-0.1, 0.1), 2),
            "volatility_annualized": round(np.std(monthly_returns) * np.sqrt(12) * 100, 2),
            "ulcer_index": round(3.5 + np.random.uniform(-0.5, 0.5), 2),
            "var_95": round(-1.6, 2),
            "cvar_95": round(-2.8, 2),
        },
        "parameters": {
            # Optimized parameters
            "lookback_period": 25,
            "entry_threshold": 2.2,
            "exit_threshold": 0.8,
            "position_size": 0.025,
            "stop_loss": 0.045,
        },
    }


def run_walk_forward_validation(profile: InputProfile) -> dict:
    """
    Simulate walk-forward validation.

    In production, this would come from:
    - app/backtesting/walk_forward_validator.py
    """
    logger.info("Running walk-forward validation...")

    import numpy as np

    np.random.seed(44)

    # Simulate walk-forward windows
    windows = []
    is_sharpes = []
    oos_sharpes = []

    for i in range(5):
        is_sharpe = 1.5 + np.random.uniform(0.1, 0.2)
        oos_sharpe = is_sharpe * (0.82 + np.random.uniform(-0.05, 0.05))

        windows.append(
            {
                "is_sharpe": round(is_sharpe, 2),
                "oos_sharpe": round(oos_sharpe, 2),
                "period": f"2024-Q{i+1}",
            }
        )
        is_sharpes.append(is_sharpe)
        oos_sharpes.append(oos_sharpe)

    return {
        "windows": windows,
        "is_sharpe": round(np.mean(is_sharpes), 2),
        "oos_sharpe": round(np.mean(oos_sharpes), 2),
        "is_oos_ratio": round(np.mean(oos_sharpes) / np.mean(is_sharpes), 2),
    }


def example_from_json_files():
    """
    Example: Load results from JSON files and generate report.

    Useful when you have saved backtest results to disk.
    """
    logger.info("=" * 80)
    logger.info("Integration Example: From JSON Files")
    logger.info("=" * 80)

    import json

    # Load baseline results
    baseline_file = Path("reports/baseline_backtest.json")
    if baseline_file.exists():
        with open(baseline_file) as f:
            baseline_results = json.load(f)
    else:
        logger.warning(f"Baseline file not found: {baseline_file}")
        return

    # Load optimized results
    optimized_file = Path("reports/optimized_backtest.json")
    if optimized_file.exists():
        with open(optimized_file) as f:
            optimized_results = json.load(f)
    else:
        logger.warning(f"Optimized file not found: {optimized_file}")
        return

    # Create profile (could also load from JSON)
    profile = InputProfile(
        capital_initial=Decimal("100000"),
        objetivo_inversion="maximizar_capital",
        risk_tolerance="medio",
        investment_horizon=24,
    )

    # Generate report
    reporter = BaselineOptimizationReporter()
    html = reporter.generate_report(
        profile=profile,
        baseline_results=baseline_results,
        optimization_results=optimized_results,
    )

    output_path = Path("reports/from_json_comparison.html")
    reporter.save_report(html, str(output_path))

    logger.info(f"✅ Report from JSON saved to: {output_path}")


def example_batch_comparison():
    """
    Example: Generate comparison reports for multiple strategies.

    Useful when comparing multiple optimization approaches.
    """
    logger.info("=" * 80)
    logger.info("Integration Example: Batch Comparison")
    logger.info("=" * 80)

    profile = InputProfile(
        capital_initial=Decimal("100000"),
        objetivo_inversion="balanced_growth",
        risk_tolerance="medio",
        investment_horizon=24,
    )

    baseline_results = run_baseline_backtest(profile)

    # Test multiple optimization approaches
    approaches = [
        ("grid_search", run_optimized_backtest(profile)),
        ("bayesian", run_optimized_backtest(profile)),
        ("genetic", run_optimized_backtest(profile)),
    ]

    reporter = BaselineOptimizationReporter()
    reports_dir = Path("reports/batch_comparisons")
    reports_dir.mkdir(parents=True, exist_ok=True)

    for approach_name, optimized_results in approaches:
        logger.info(f"Generating report for: {approach_name}")

        html = reporter.generate_report(
            profile=profile,
            baseline_results=baseline_results,
            optimization_results=optimized_results,
        )

        output_path = reports_dir / f"{approach_name}_comparison.html"
        reporter.save_report(html, str(output_path))

        logger.info(f"✅ Saved: {output_path}")

    logger.info(f"✅ Batch comparison complete. Reports in: {reports_dir}")


def main():
    """Run integration examples."""
    logger.info("Starting Integration Examples")
    logger.info("=" * 80)

    # Create reports directory
    Path("reports").mkdir(exist_ok=True)

    # Example 1: From backtest results
    try:
        example_from_backtest_results()
        print()
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error in backtest results example: {e}", exc_info=True)

    # Example 2: From JSON files (if they exist)
    try:
        example_from_json_files()
        print()
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error in JSON files example: {e}", exc_info=True)

    # Example 3: Batch comparison
    try:
        example_batch_comparison()
        print()
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error in batch comparison example: {e}", exc_info=True)

    logger.info("=" * 80)
    logger.info("✅ Integration examples completed!")
    logger.info("")
    logger.info("Generated reports:")
    logger.info("  - reports/integration_comparison.html")
    logger.info("  - reports/batch_comparisons/*.html")
    logger.info("")
    logger.info("These reports show how to integrate the reporter with your")
    logger.info("existing backtesting workflow.")


if __name__ == "__main__":
    main()
