"""
Example: Baseline vs Optimization Comparison Reporter

This example demonstrates how to use the BaselineOptimizationReporter
to generate professional comparison reports between baseline and optimized strategies.

Usage:
    python examples/baseline_optimization_reporter_example.py
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

from app.backtesting.reports.baseline_optimization_reporter import (
    BaselineOptimizationReporter,
)
from app.core.models.input_profile import InputProfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def generate_sample_equity_curve(
    initial_capital: float,
    monthly_return: float,
    volatility: float,
    months: int = 24,
) -> list:
    """
    Generate sample equity curve for testing.

    Args:
        initial_capital: Starting capital
        monthly_return: Average monthly return (as decimal)
        volatility: Monthly volatility (as decimal)
        months: Number of months

    Returns:
        List of (date, value) tuples
    """
    np.random.seed(42)  # For reproducibility

    dates = [datetime.now() - timedelta(days=30 * (months - i)) for i in range(months)]
    values = [initial_capital]

    for i in range(1, months):
        # Random walk with drift
        daily_return = np.random.normal(
            monthly_return / 30, volatility / np.sqrt(30)
        )
        new_value = values[-1] * (1 + daily_return)
        values.append(new_value)

    return list(zip(dates, values))


def create_sample_baseline_results() -> dict:
    """Create sample baseline backtest results."""
    equity_curve = generate_sample_equity_curve(
        initial_capital=100000,
        monthly_return=0.015,  # 1.5% per month
        volatility=0.10,  # 10% monthly vol
        months=24,
    )

    return {
        "start_date": "2024-01-01",
        "end_date": "2025-12-31",
        "equity_curve": equity_curve,
        "performance": {
            "sharpe_ratio": 1.2,
            "sortino_ratio": 1.8,
            "calmar_ratio": 0.9,
            "omega_ratio": 1.3,
            "total_return": 42.5,
            "max_drawdown_percentage": -15.2,
            "win_rate": 52.0,
            "profit_factor": 1.4,
            "volatility_annualized": 12.5,
            "ulcer_index": 5.2,
            "var_95": -2.1,
            "cvar_95": -3.5,
            "avg_win": 1.8,
            "avg_loss": -1.3,
            "largest_win": 8.5,
            "largest_loss": -6.2,
            "total_trades": 156,
            "winning_trades": 81,
            "losing_trades": 75,
        },
        "parameters": {
            "lookback_period": 20,
            "entry_threshold": 2.0,
            "exit_threshold": 1.0,
            "position_size": 0.02,
            "stop_loss": 0.05,
        },
    }


def create_sample_optimized_results() -> dict:
    """Create sample optimized backtest results."""
    equity_curve = generate_sample_equity_curve(
        initial_capital=100000,
        monthly_return=0.019,  # 1.9% per month (better)
        volatility=0.09,  # 9% monthly vol (lower)
        months=24,
    )

    return {
        "start_date": "2024-01-01",
        "end_date": "2025-12-31",
        "equity_curve": equity_curve,
        "performance": {
            "sharpe_ratio": 1.65,  # 37.5% improvement
            "sortino_ratio": 2.4,  # 33% improvement
            "calmar_ratio": 1.3,  # 44% improvement
            "omega_ratio": 1.6,  # 23% improvement
            "total_return": 58.3,  # 37% improvement
            "max_drawdown_percentage": -12.1,  # 20% improvement
            "win_rate": 54.5,  # 4.8% improvement
            "profit_factor": 1.6,  # 14% improvement
            "volatility_annualized": 11.2,  # 10% improvement
            "ulcer_index": 3.8,  # 27% improvement
            "var_95": -1.8,  # 14% improvement
            "cvar_95": -2.9,  # 17% improvement
            "avg_win": 1.9,
            "avg_loss": -1.2,
            "largest_win": 8.2,
            "largest_loss": -5.1,
            "total_trades": 142,  # Fewer trades
            "winning_trades": 77,
            "losing_trades": 65,
        },
        "parameters": {
            "lookback_period": 25,  # Increased
            "entry_threshold": 2.2,  # Increased (more selective)
            "exit_threshold": 0.8,  # Decreased (faster exits)
            "position_size": 0.025,  # Increased slightly
            "stop_loss": 0.045,  # Tighter stops
        },
    }


def create_sample_walk_forward_results() -> dict:
    """Create sample walk-forward validation results."""
    return {
        "windows": [
            {"is_sharpe": 1.55, "oos_sharpe": 1.35, "period": "2024-Q1"},
            {"is_sharpe": 1.62, "oos_sharpe": 1.42, "period": "2024-Q2"},
            {"is_sharpe": 1.70, "oos_sharpe": 1.38, "period": "2024-Q3"},
            {"is_sharpe": 1.68, "oos_sharpe": 1.40, "period": "2024-Q4"},
            {"is_sharpe": 1.65, "oos_sharpe": 1.45, "period": "2025-Q1"},
        ],
        "is_sharpe": 1.64,  # Average in-sample
        "oos_sharpe": 1.40,  # Average out-of-sample
        "is_oos_ratio": 0.85,  # OOS/IS ratio (stability indicator)
    }


def create_sample_sensitivity_results() -> dict:
    """Create sample parameter sensitivity results."""
    return {
        "parameters": ["lookback_period", "entry_threshold", "exit_threshold"],
        "sharpe_matrix": [
            [1.2, 1.3, 1.4, 1.35, 1.3],
            [1.4, 1.5, 1.65, 1.55, 1.45],
            [1.3, 1.45, 1.6, 1.5, 1.4],
            [1.25, 1.35, 1.45, 1.4, 1.35],
        ],
        "optimal_region": {"lookback_period": [20, 30], "entry_threshold": [2.0, 2.5]},
    }


def example_basic_usage():
    """Example 1: Basic usage with minimal inputs."""
    logger.info("=" * 60)
    logger.info("Example 1: Basic Usage")
    logger.info("=" * 60)

    # Create input profile
    profile = InputProfile(
        capital_initial=Decimal("100000"),
        objetivo_inversion="maximizar_capital",
        risk_tolerance="medio",
        investment_horizon=24,  # 24 months
    )

    # Get sample results
    baseline_results = create_sample_baseline_results()
    optimized_results = create_sample_optimized_results()

    # Initialize reporter
    reporter = BaselineOptimizationReporter()

    # Generate report
    html = reporter.generate_report(
        profile=profile,
        baseline_results=baseline_results,
        optimization_results=optimized_results,
    )

    # Save report
    output_path = Path("reports/baseline_optimization_basic.html")
    reporter.save_report(html, output_path)

    logger.info(f"✅ Basic report saved to: {output_path}")


def example_with_walk_forward():
    """Example 2: With walk-forward validation."""
    logger.info("=" * 60)
    logger.info("Example 2: With Walk-Forward Validation")
    logger.info("=" * 60)

    profile = InputProfile(
        capital_initial=Decimal("250000"),
        objetivo_inversion="balanced_growth",
        risk_tolerance="medio",
        investment_horizon=36,
    )

    baseline_results = create_sample_baseline_results()
    optimized_results = create_sample_optimized_results()
    walk_forward_results = create_sample_walk_forward_results()

    reporter = BaselineOptimizationReporter()

    html = reporter.generate_report(
        profile=profile,
        baseline_results=baseline_results,
        optimization_results=optimized_results,
        walk_forward_results=walk_forward_results,
    )

    output_path = Path("reports/baseline_optimization_with_walkforward.html")
    reporter.save_report(html, output_path)

    logger.info(f"✅ Report with walk-forward saved to: {output_path}")


def example_with_sensitivity():
    """Example 3: With parameter sensitivity analysis."""
    logger.info("=" * 60)
    logger.info("Example 3: With Sensitivity Analysis")
    logger.info("=" * 60)

    profile = InputProfile(
        capital_initial=Decimal("50000"),
        objetivo_inversion="capital_preservation",
        risk_tolerance="bajo",
        investment_horizon=12,
    )

    baseline_results = create_sample_baseline_results()
    optimized_results = create_sample_optimized_results()
    sensitivity_results = create_sample_sensitivity_results()

    reporter = BaselineOptimizationReporter()

    html = reporter.generate_report(
        profile=profile,
        baseline_results=baseline_results,
        optimization_results=optimized_results,
        sensitivity_results=sensitivity_results,
    )

    output_path = Path("reports/baseline_optimization_with_sensitivity.html")
    reporter.save_report(html, output_path)

    logger.info(f"✅ Report with sensitivity saved to: {output_path}")


def example_comprehensive():
    """Example 4: Comprehensive report with all features."""
    logger.info("=" * 60)
    logger.info("Example 4: Comprehensive Report")
    logger.info("=" * 60)

    profile = InputProfile(
        capital_initial=Decimal("250000"),
        objetivo_inversion="maximizar_capital",
        risk_tolerance="alto",
        investment_horizon=48,
        tax_residence={
            "country_code": "ES",
            "country_name": "Spain",
            "capital_gains_rate_short": "0.19",
            "capital_gains_rate_long": "0.19",
            "dividend_tax_rate": "0.19",
        },
    )

    baseline_results = create_sample_baseline_results()
    optimized_results = create_sample_optimized_results()
    walk_forward_results = create_sample_walk_forward_results()
    sensitivity_results = create_sample_sensitivity_results()

    reporter = BaselineOptimizationReporter()

    html = reporter.generate_report(
        profile=profile,
        baseline_results=baseline_results,
        optimization_results=optimized_results,
        walk_forward_results=walk_forward_results,
        sensitivity_results=sensitivity_results,
    )

    output_path = Path("reports/baseline_optimization_comprehensive.html")
    reporter.save_report(html, output_path)

    logger.info(f"✅ Comprehensive report saved to: {output_path}")


def example_custom_template():
    """Example 5: Using custom template."""
    logger.info("=" * 60)
    logger.info("Example 5: Custom Template")
    logger.info("=" * 60)

    # You can create a custom Jinja2 template
    custom_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Custom Comparison Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .metric { display: inline-block; margin: 20px; padding: 20px; background: #f0f0f0; border-radius: 8px; }
            h1 { color: #2c3e50; }
        </style>
    </head>
    <body>
        <h1>{{ strategy_name }}</h1>
        <p>Comparison Report</p>

        <div class="metric">
            <h3>Sharpe Ratio</h3>
            <p>Baseline: {{ baseline_sharpe }}</p>
            <p>Optimized: {{ optimized_sharpe }}</p>
            <p>Improvement: {{ sharpe_improvement }}%</p>
        </div>

        <div class="metric">
            <h3>Return</h3>
            <p>Baseline: {{ baseline_return }}%</p>
            <p>Optimized: {{ optimized_return }}%</p>
            <p>Improvement: {{ return_improvement }}%</p>
        </div>
    </body>
    </html>
    """

    # Save custom template
    template_path = Path("reports/templates/custom_report.html")
    template_path.parent.mkdir(parents=True, exist_ok=True)

    with open(template_path, "w") as f:
        f.write(custom_template)

    # Use custom template
    reporter = BaselineOptimizationReporter(template_path=str(template_path))

    profile = InputProfile(
        capital_initial=Decimal("100000"),
        objetivo_inversion="maximizar_capital",
        risk_tolerance="medio",
        investment_horizon=24,
    )

    baseline_results = create_sample_baseline_results()
    optimized_results = create_sample_optimized_results()

    # Note: Custom template needs to match expected variables
    # For simplicity, this example shows the pattern

    logger.info(f"✅ Custom template example created at: {template_path}")


def main():
    """Run all examples."""
    logger.info("Starting Baseline vs Optimization Reporter Examples")
    logger.info("=" * 80)

    # Create reports directory
    Path("reports").mkdir(exist_ok=True)

    # Run examples
    try:
        example_basic_usage()
        print()
        example_with_walk_forward()
        print()
        example_with_sensitivity()
        print()
        example_comprehensive()
        print()
        example_custom_template()
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error running examples: {e}", exc_info=True)
        return 1

    logger.info("=" * 80)
    logger.info("✅ All examples completed successfully!")
    logger.info("")
    logger.info("Generated reports:")
    logger.info("  - reports/baseline_optimization_basic.html")
    logger.info("  - reports/baseline_optimization_with_walkforward.html")
    logger.info("  - reports/baseline_optimization_with_sensitivity.html")
    logger.info("  - reports/baseline_optimization_comprehensive.html")
    logger.info("")
    logger.info("Open these files in a web browser to view the interactive reports.")

    return 0


if __name__ == "__main__":
    exit(main())
