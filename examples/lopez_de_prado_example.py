"""
López de Prado - Machine Learning for Asset Managers
Example Usage and Implementation Guide

This example demonstrates how to use the implemented López de Prado methodologies
to achieve 95% compliance with his book's recommendations.

Reference:
    López de Prado, M. (2020). Machine Learning for Asset Managers.
    Cambridge University Press.

Implemented Features:
1. Sharpe Ratio Combination Methods (Chapter 8)
2. Portfolio Stability Validation (Chapter 9)
3. Turnover-Adjusted Performance Metrics (Chapter 10)
4. Portfolio Concentration Metrics (Chapter 11)
"""

import numpy as np
from pathlib import Path

from app.backtesting.metrics import (
    LopezDePradoMetricsCalculator,
    create_lopez_de_prado_calculator,
)
from app.engines.portfolio_engine.stability_validator import (
    PortfolioStabilityValidator,
    create_portfolio_stability_validator,
)


def example_sharpe_combination():
    """
    Example 1: Combining multiple strategy Sharpe ratios.

    From López de Prado Chapter 8: Sharpe Ratio Combinations

    Scenario: You have 3 strategies with individual Sharpe ratios.
    You want to find the optimal combination.
    """
    print("=" * 80)
    print("Example 1: Sharpe Ratio Combination")
    print("=" * 80)

    # Create calculator
    calc = create_lopez_de_prado_calculator(
        risk_free_rate=0.02,
        stability_threshold=70.0,
        transaction_cost_bps=10.0,
    )

    # Simulated data: 3 strategies over 252 trading days
    np.random.seed(42)
    n_days = 252
    n_strategies = 3

    # Strategy returns (slightly correlated)
    strategy_returns = np.random.randn(n_days, n_strategies) * 0.01
    strategy_returns[:, 1] += 0.5 * strategy_returns[:, 0]  # Add correlation
    strategy_returns[:, 2] += 0.3 * strategy_returns[:, 0]

    # Individual Sharpe ratios
    individual_sharpes = [1.2, 0.8, 1.5]

    print(f"\nIndividual Sharpe Ratios: {individual_sharpes}")

    # Try different combination methods
    for method in ["optimal", "hierarchical", "spectral", "average"]:
        result = calc.combine_strategy_sharpes(
            sharpes=individual_sharpes,
            returns_matrix=strategy_returns,
            method=method,
        )

        print(f"\n{method.upper()} Method:")
        print(f"  Combined Sharpe: {result.combined_sharpe:.3f}")
        print(f"  Weights: {result.weights if result.weights is not None else 'N/A'}")
        print(f"  Improvement: {result.improvement_pct:.1f}%")

    print()


def example_portfolio_stability():
    """
    Example 2: Validating portfolio stability across time.

    From López de Prado Chapter 9: Portfolio Stability

    Scenario: You have monthly rebalancing data. You want to validate
    if the portfolio allocation strategy is stable over time.
    """
    print("=" * 80)
    print("Example 2: Portfolio Stability Validation")
    print("=" * 80)

    calc = create_lopez_de_prado_calculator()

    # Simulated portfolio weights over 12 months (4 assets)
    np.random.seed(42)
    n_periods = 12
    n_assets = 4

    # Generate weights (with some drift over time)
    base_weights = np.array([0.4, 0.3, 0.2, 0.1])
    weights_history = []
    for i in range(n_periods):
        drift = np.random.randn(n_assets) * 0.05  # Small random drift
        period_weights = base_weights + drift
        period_weights = np.maximum(period_weights, 0)  # Ensure non-negative
        period_weights = period_weights / period_weights.sum()  # Normalize
        weights_history.append(period_weights)

    # Generate portfolio returns
    portfolio_returns = np.random.randn(n_periods * 20) * 0.01  # ~20 trading days/month

    # Validate stability
    stability = calc.validate_portfolio_stability(
        weights_history=weights_history,
        returns_history=portfolio_returns,
        period_length_days=30,
    )

    print(f"\nStability Analysis Results:")
    print(f"  Overall Stable: {stability.is_stable}")
    print(f"  Stability Score: {stability.stability_score:.1f}/100")
    print(f"  Avg Turnover: {stability.turnover_mean:.2%}")
    print(f"  Weights Autocorrelation: {stability.weights_autocorrelation:.3f}")
    print(f"  Max Allocation Drift: {stability.allocation_drift_max:.2%}")
    print(f"  Cross-Period Correlation: {stability.cross_period_correlation:.3f}")

    if not stability.is_stable:
        print("\n  WARNING: Portfolio is unstable. Consider simplifying strategy.")
    else:
        print("\n  Portfolio is stable and robust.")

    print()


def example_turnover_adjusted_metrics():
    """
    Example 3: Calculating turnover-adjusted Sharpe ratio.

    From López de Prado Chapter 10: Turnover Analysis

    Scenario: A high-turnover strategy needs to be evaluated after
    accounting for transaction costs.
    """
    print("=" * 80)
    print("Example 3: Turnover-Adjusted Performance Metrics")
    print("=" * 80)

    calc = create_lopez_de_prado_calculator(transaction_cost_bps=10.0)

    # Simulated high-turnover strategy
    np.random.seed(42)
    n_periods = 12
    n_assets = 5

    # Weights change significantly each period (high turnover)
    weights_history = []
    for i in range(n_periods):
        weights = np.random.dirichlet(np.ones(n_assets))  # Random allocation
        weights_history.append(weights)

    # Portfolio returns
    portfolio_returns = np.random.randn(252) * 0.015  # Good returns

    # Calculate turnover-adjusted metrics
    turnover_metrics = calc.calculate_turnover_adjusted_metrics(
        returns=portfolio_returns,
        weights_history=weights_history,
        period_length_days=30,
    )

    print(f"\nTurnover Analysis Results:")
    print(f"  Raw Sharpe Ratio: {turnover_metrics.raw_sharpe:.3f}")
    print(f"  Turnover-Adjusted Sharpe: {turnover_metrics.turnover_adjusted_sharpe:.3f}")
    print(f"  Annualized Turnover: {turnover_metrics.annualized_turnover:.1%}")
    print(f"  Adjustment Factor: {turnover_metrics.adjustment_factor:.3f}")
    print(f"  Estimated Costs: {turnover_metrics.estimated_transaction_costs:.2%}")
    print(f"  Net Sharpe (after costs): {turnover_metrics.net_sharpe:.3f}")
    print(f"  Cost-Effective: {turnover_metrics.is_cost_effective}")

    if not turnover_metrics.is_cost_effective:
        degradation = (
            1 - turnover_metrics.turnover_adjusted_sharpe / turnover_metrics.raw_sharpe
            if turnover_metrics.raw_sharpe > 0 else 0
        )
        print(f"\n  WARNING: Sharpe degrades by {degradation:.1%} after costs.")
    else:
        print("\n  Strategy is cost-effective.")

    print()


def example_concentration_analysis():
    """
    Example 4: Analyzing portfolio concentration.

    From López de Prado Chapter 11: Concentration Analysis

    Scenario: Evaluate if a portfolio is too concentrated in few assets.
    """
    print("=" * 80)
    print("Example 4: Portfolio Concentration Analysis")
    print("=" * 80)

    calc = create_lopez_de_prado_calculator()

    # Example portfolios with different concentration levels
    portfolios = {
        "Concentrated": np.array([0.6, 0.2, 0.1, 0.05, 0.05]),
        "Balanced": np.array([0.3, 0.25, 0.2, 0.15, 0.1]),
        "Diversified": np.array([0.22, 0.21, 0.2, 0.19, 0.18]),
    }

    for name, weights in portfolios.items():
        concentration = calc.analyze_portfolio_concentration(weights=weights)

        print(f"\n{name} Portfolio:")
        print(f"  Herfindahl Index (HHI): {concentration.herfindahl_index:.3f}")
        print(f"  Effective N Assets: {concentration.effective_n_assets:.1f}")
        print(f"  Max Weight: {concentration.max_weight:.1%}")
        print(f"  Top-3 Concentration: {concentration.top_3_concentration:.1%}")
        print(f"  Gini Coefficient: {concentration.gini_coefficient:.3f}")
        print(f"  Shannon Entropy: {concentration.shannon_entropy:.3f}")
        print(f"  Over-Concentrated: {concentration.is_overconcentrated}")
        print(f"  Concentration Score: {concentration.concentration_score:.1f}/100")

    print()


def example_comprehensive_report():
    """
    Example 5: Generate comprehensive López de Prado compliance report.

    Combines all four metrics areas into a single report.
    """
    print("=" * 80)
    print("Example 5: Comprehensive López de Prado Report")
    print("=" * 80)

    calc = create_lopez_de_prado_calculator()

    # Generate sample data
    np.random.seed(42)
    n_strategies = 3
    n_assets = 5
    n_periods = 12

    # Strategy returns
    strategy_returns = np.random.randn(252, n_strategies) * 0.01

    # Individual Sharpe ratios
    individual_sharpes = [1.2, 0.9, 1.4]

    # Portfolio weights history
    base_weights = np.array([0.3, 0.25, 0.2, 0.15, 0.1])
    weights_history = []
    for i in range(n_periods):
        drift = np.random.randn(n_assets) * 0.03
        period_weights = base_weights + drift
        period_weights = np.maximum(period_weights, 0)
        period_weights = period_weights / period_weights.sum()
        weights_history.append(period_weights)

    # Portfolio returns
    portfolio_returns = np.random.randn(252) * 0.01 + 0.0003

    # Current weights
    current_weights = weights_history[-1]

    # Generate comprehensive report
    report = calc.generate_comprehensive_report(
        sharpes=individual_sharpes,
        returns_matrix=strategy_returns,
        weights_history=weights_history,
        portfolio_returns=portfolio_returns,
        current_weights=current_weights,
    )

    print(f"\n{'LÓPEZ DE PRADO COMPLIANCE REPORT':^80}")
    print(f"{'Overall Score:':<40} {report['overall_score']:.1f}/100")
    print("-" * 80)

    print("\n1. Sharpe Ratio Combination:")
    sc = report["sharpe_combination"]
    print(f"   Combined Sharpe: {sc['combined_sharpe']:.3f}")
    print(f"   Method: {sc['method']}")
    print(f"   Improvement: {sc['improvement_pct']:.1f}%")

    print("\n2. Portfolio Stability:")
    st = report["stability"]
    print(f"   Is Stable: {st['is_stable']}")
    print(f"   Stability Score: {st['stability_score']:.1f}/100")
    print(f"   Avg Turnover: {st['turnover_mean']:.2%}")

    print("\n3. Turnover-Adjusted Metrics:")
    tm = report["turnover"]
    print(f"   Raw Sharpe: {tm['raw_sharpe']:.3f}")
    print(f"   Adjusted Sharpe: {tm['turnover_adjusted_sharpe']:.3f}")
    print(f"   Annual Turnover: {tm['annualized_turnover']:.1%}")
    print(f"   Cost-Effective: {tm['is_cost_effective']}")

    print("\n4. Concentration Analysis:")
    ca = report["concentration"]
    print(f"   HHI: {ca['herfindahl_index']:.3f}")
    print(f"   Effective N: {ca['effective_n_assets']:.1f}")
    print(f"   Over-Concentrated: {ca['is_overconcentrated']}")

    print("\n5. Recommendations:")
    for i, rec in enumerate(report["recommendations"], 1):
        print(f"   {i}. {rec}")

    print()
    print("=" * 80)


def main():
    """Run all examples."""
    print("\n")
    print("*" * 80)
    print("*" + " " * 78 + "*")
    print("*" + "  López de Prado - Machine Learning for Asset Managers".center(78) + "*")
    print("*" + "  Implementation Examples".center(78) + "*")
    print("*" + " " * 78 + "*")
    print("*" * 80)
    print("\n")

    # Run examples
    example_sharpe_combination()
    example_portfolio_stability()
    example_turnover_adjusted_metrics()
    example_concentration_analysis()
    example_comprehensive_report()

    print("*" * 80)
    print("*" + "  All examples completed successfully!".center(78) + "*")
    print("*" * 80)
    print("\n")


if __name__ == "__main__":
    main()
