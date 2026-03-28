"""
Profile Batch Backtesting - Usage Examples

This module demonstrates how to use the ProfileBatchBacktester for comprehensive
baseline vs optimization testing across investor profiles.
"""

import logging
from decimal import Decimal

from app.backtesting.profile_batch_backtester import (
    ProfileBatchBacktester,
)
from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: Basic Usage - Run All Profiles
# ============================================================================


def example_1_run_all_profiles():
    """
    Example 1: Run all 180 profile combinations with parallel execution.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Run All Profiles")
    print("=" * 80)

    # Create backtester
    backtester = ProfileBatchBacktester(config_path="config/profile_batch_backtest.yaml")

    # Run all profiles (180 combinations)
    results = backtester.run_all_profiles(
        parallel=True,  # Use parallel execution
        max_workers=20,  # Up to 20 parallel workers
    )

    print(f"\nCompleted {len(results)} profiles")
    print(
        f"Ready for paper trading: {sum(1 for r in results.values() if r.ready_for_paper_trading)}"
    )

    # Export results
    json_path = backtester.export_results(format="json")
    print(f"Results exported to: {json_path}")


# ============================================================================
# Example 2: Single Profile Testing
# ============================================================================


def example_2_single_profile():
    """
    Example 2: Test a single profile with detailed output.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Single Profile Testing")
    print("=" * 80)

    # Create backtester
    backtester = ProfileBatchBacktester(config_path="config/profile_batch_backtest.yaml")

    # Define a specific profile
    profile = InputProfile(
        capital_initial=Decimal("100000"),
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
        risk_tolerance=RiskTolerance.MEDIO,
        investment_horizon=24,  # 2 years
    )

    print(f"\nTesting profile:")
    print(f"  Capital: €{profile.capital_initial:,.0f}")
    print(f"  Objective: {profile.objetivo_inversion.value}")
    print(f"  Risk: {profile.risk_tolerance.value}")
    print(f"  Horizon: {profile.investment_horizon} months")

    # Run profile
    result = backtester.run_single_profile(profile)

    print(f"\nResults:")
    print(f"  Baseline Sharpe: {result.baseline_results.get('sharpe_ratio', 0):.2f}")
    print(f"  Optimized Sharpe: {result.optimization_results.get('sharpe_ratio', 0):.2f}")
    print(f"  Improvement: {result.improvement_metrics.get('sharpe_improvement', 0):.1f}%")
    print(f"  Ready for paper trading: {result.ready_for_paper_trading}")
    print(f"  Recommendation: {result.recommendation}")


# ============================================================================
# Example 3: Get Best Strategy
# ============================================================================


def example_3_get_best_strategy():
    """
    Example 3: Get best strategy for specific criteria.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Get Best Strategy")
    print("=" * 80)

    # Create backtester
    backtester = ProfileBatchBacktester(config_path="config/profile_batch_backtest.yaml")

    # Run a subset first
    profiles = backtester.generate_all_profiles()[:20]  # Test 20 profiles
    for profile in profiles:
        try:
            result = backtester.run_single_profile(profile)
            print(
                f"  Completed profile: {profile.nombre_perfil} - {result.get('status', 'unknown')}"
            )
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Profile failed: {e}")

    # Get best strategy
    best_config = backtester.get_best_strategy(
        objective="maximizar_capital", tier="medio", risk="medio"
    )

    print(f"\nBest configuration for maximizar_capital, medio, medio:")
    print(f"  Profile ID: {best_config.get('profile_id')}")
    print(f"  Baseline Sharpe: {best_config['baseline_metrics']['sharpe_ratio']:.2f}")
    print(f"  Optimized Sharpe: {best_config['optimized_metrics']['sharpe_ratio']:.2f}")
    print(f"  Sharpe Improvement: {best_config['improvement']['sharpe']:.1f}%")
    print(f"  Best Parameters: {best_config['best_parameters']}")
    print(f"  Recommendation: {best_config['recommendation']}")


# ============================================================================
# Example 4: Generate Comparison Report
# ============================================================================


def example_4_comparison_report():
    """
    Example 4: Generate comprehensive comparison report.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Generate Comparison Report")
    print("=" * 80)

    # Create backtester
    backtester = ProfileBatchBacktester(config_path="config/profile_batch_backtest.yaml")

    # Run a few profiles for demo
    profiles = backtester.generate_all_profiles()[:10]
    for profile in profiles:
        try:
            backtester.run_single_profile(profile)
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Profile failed: {e}")

    # Generate HTML comparison report
    html_report = backtester.generate_comparison_report()

    print(f"\nComparison report generated:")
    print(f"  Length: {len(html_report):,} characters")
    print(f"  Report includes:")
    print(f"    - Baseline vs Optimized metrics comparison")
    print(f"    - Improvement percentages")
    print(f"    - Parameter importance analysis")
    print(f"    - Best strategies by objective")


# ============================================================================
# Example 5: Custom Profile Testing
# ============================================================================


def example_5_custom_profiles():
    """
    Example 5: Test custom profiles with specific parameters.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Custom Profile Testing")
    print("=" * 80)

    # Create backtester
    backtester = ProfileBatchBacktester(config_path="config/profile_batch_backtest.yaml")

    # Define custom profiles
    custom_profiles = [
        # Conservative retiree
        InputProfile(
            capital_initial=Decimal("250000"),
            objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
            risk_tolerance=RiskTolerance.BAJO,
            investment_horizon=60,  # 5 years
        ),
        # Young aggressive investor
        InputProfile(
            capital_initial=Decimal("50000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.ALTO,
            investment_horizon=36,  # 3 years
        ),
        # Balanced income investor
        InputProfile(
            capital_initial=Decimal("150000"),
            objetivo_inversion=ObjectivoInversion.INCOME_GENERATION,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=48,  # 4 years
        ),
    ]

    results = []
    for profile in custom_profiles:
        print(f"\nTesting: {profile.objetivo_inversion.value} - {profile.risk_tolerance.value}")
        result = backtester.run_single_profile(profile)
        results.append(result)

    # Summary
    print(f"\n{'Profile':<30} {'Baseline':<10} {'Optimized':<10} {'Improvement':<12} {'Ready'}")
    print("-" * 80)
    for result in results:
        profile_name = (
            f"{result.profile.objetivo_inversion.value}_{result.profile.risk_tolerance.value}"
        )
        baseline = result.baseline_results.get('sharpe_ratio', 0)
        optimized = result.optimization_results.get('sharpe_ratio', 0)
        improvement = result.improvement_metrics.get('sharpe_improvement', 0)
        ready = "YES" if result.ready_for_paper_trading else "NO"
        print(
            f"{profile_name:<30} {baseline:<10.2f} {optimized:<10.2f} {improvement:+<11.1f}% {ready}"
        )


# ============================================================================
# Example 6: Database Queries
# ============================================================================


def example_6_database_queries():
    """
    Example 6: Query results from database.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Database Queries")
    print("=" * 80)

    # Create backtester (connects to existing database)
    backtester = ProfileBatchBacktester(config_path="config/profile_batch_backtest.yaml")

    # Query database for all results
    session = backtester.Session()
    from app.backtesting.profile_batch_backtester import ProfileResultDB

    # Get all results
    all_results = session.query(ProfileResultDB).all()
    print(f"\nTotal profiles in database: {len(all_results)}")

    # Get results by objective
    for objective in ["maximizar_capital", "maximizar_dividendos", "balanced_growth"]:
        obj_results = (
            session.query(ProfileResultDB)
            .filter_by(objective=objective)
            .order_by(ProfileResultDB.optimized_sharpe.desc())
            .limit(5)
            .all()
        )
        print(f"\nTop 5 for {objective}:")
        for r in obj_results:
            print(
                f"  {r.profile_id}: Sharpe={r.optimized_sharpe:.2f}, Return={r.optimized_return:.2%}"
            )

    # Get approved profiles
    approved = session.query(ProfileResultDB).filter_by(ready_for_paper_trading=True).all()
    print(f"\nApproved for paper trading: {len(approved)}")

    session.close()


# ============================================================================
# Example 7: Export and Analysis
# ============================================================================


def example_7_export_analysis():
    """
    Example 7: Export results and perform analysis.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Export and Analysis")
    print("=" * 80)

    # Create backtester
    backtester = ProfileBatchBacktester(config_path="config/profile_batch_backtest.yaml")

    # Run some profiles
    profiles = backtester.generate_all_profiles()[:30]
    for profile in profiles:
        try:
            backtester.run_single_profile(profile)
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Profile failed: {e}")

    # Export in multiple formats
    print("\nExporting results...")

    # JSON
    json_path = backtester.export_results(format="json")
    print(f"  JSON: {json_path}")

    # CSV
    csv_path = backtester.export_results(format="csv")
    print(f"  CSV: {csv_path}")

    # Excel
    excel_path = backtester.export_results(format="excel")
    print(f"  Excel: {excel_path}")

    # Generate HTML report
    html_report = backtester.generate_comparison_report()
    print(f"  HTML Report: {len(html_report):,} characters")


# ============================================================================
# Example 8: Sequential Execution (Debug Mode)
# ============================================================================


def example_8_sequential_execution():
    """
    Example 8: Run profiles sequentially for debugging.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 8: Sequential Execution (Debug)")
    print("=" * 80)

    # Create backtester
    backtester = ProfileBatchBacktester(config_path="config/profile_batch_backtest.yaml")

    # Run a few profiles sequentially
    profiles = backtester.generate_all_profiles()[:5]

    print(f"\nRunning {len(profiles)} profiles sequentially...")
    results = backtester.run_all_profiles(parallel=False)

    for profile_id, result in results.items():
        print(f"\n{profile_id}:")
        print(f"  Baseline Sharpe: {result.baseline_results.get('sharpe_ratio', 0):.2f}")
        print(f"  Optimized Sharpe: {result.optimization_results.get('sharpe_ratio', 0):.2f}")
        print(f"  Status: {result.recommendation}")


# ============================================================================
# Main Function
# ============================================================================


def main():
    """Run all examples."""
    examples = [
        ("Example 1: Run All Profiles", example_1_run_all_profiles),
        ("Example 2: Single Profile", example_2_single_profile),
        ("Example 3: Get Best Strategy", example_3_get_best_strategy),
        ("Example 4: Comparison Report", example_4_comparison_report),
        ("Example 5: Custom Profiles", example_5_custom_profiles),
        ("Example 6: Database Queries", example_6_database_queries),
        ("Example 7: Export Analysis", example_7_export_analysis),
        ("Example 8: Sequential Execution", example_8_sequential_execution),
    ]

    print("\n" + "=" * 80)
    print("PROFILE BATCH BACKTESTING - USAGE EXAMPLES")
    print("=" * 80)

    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\nSelect example to run (1-8, or 'all'): ")
    choice = input().strip()

    if choice.lower() == "all":
        for name, func in examples:
            try:
                func()
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.error(f"{name} failed: {e}", exc_info=True)
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        _, func = examples[int(choice) - 1]
        try:
            func()
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Example failed: {e}", exc_info=True)
    else:
        print("Invalid choice. Please run again and select 1-8 or 'all'.")


if __name__ == "__main__":
    main()
