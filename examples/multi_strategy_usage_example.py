#!/usr/bin/env python3
"""
Multi-Strategy Execution Example for ProfileBatchBacktester

This example demonstrates how to use the new multi-strategy execution
feature in ProfileBatchBacktester.

Usage:
    python examples/multi_strategy_usage_example.py
"""

from decimal import Decimal
import logging

from app.backtesting.profile_batch_backtester import ProfileBatchBacktester
from app.core.models.input_profile import (
    InputProfile,
    ObjectivoInversion,
    RiskTolerance,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_single_profile_multi_strategy():
    """Example: Run single profile with multi-strategy mode."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Single Profile Multi-Strategy Execution")
    print("=" * 80 + "\n")

    # Create backtester
    backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")

    # Create a test profile
    profile = InputProfile(
        capital_initial=Decimal("100000"),
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
        risk_tolerance=RiskTolerance.MEDIO,
        investment_horizon=24,
    )

    logger.info(f"Created profile: {profile.input_id}")
    logger.info(f"  Capital: €{profile.capital_initial:,.2f}")
    logger.info(f"  Objective: {profile.objetivo_inversion.value}")
    logger.info(f"  Risk Tolerance: {profile.risk_tolerance.value}")
    logger.info(f"  Horizon: {profile.investment_horizon} months")

    # Run with multi-strategy mode enabled
    logger.info("\nRunning multi-strategy backtest...")
    result = backtester.run_single_profile(profile, multi_strategy=True)

    # Display results
    logger.info("\n" + "-" * 80)
    logger.info("RESULTS SUMMARY")
    logger.info("-" * 80)

    if result.enabled_strategies:
        logger.info(f"Enabled Strategies: {', '.join(result.enabled_strategies)}")
    else:
        logger.info("Enabled Strategies: None (single-strategy mode)")

    if result.learning_engines:
        logger.info(f"Learning Engines: {', '.join(result.learning_engines)}")

    if result.ensemble_config:
        mode = result.ensemble_config.get('mode', 'N/A')
        logger.info(f"Ensemble Mode: {mode}")

    # Combined metrics
    logger.info("\nCombined Portfolio Metrics:")
    logger.info(f"  Total Return: {result.baseline_results.get('return_pct', 0):.2f}%")
    logger.info(f"  Sharpe Ratio: {result.baseline_results.get('sharpe_ratio', 0):.2f}")
    logger.info(f"  Max Drawdown: {result.baseline_results.get('max_drawdown', 0):.2f}%")
    logger.info(f"  Total Trades: {result.baseline_results.get('total_trades', 0)}")

    # Per-strategy breakdown
    if result.per_strategy_results:
        logger.info("\nPer-Strategy Breakdown:")
        for strategy_name, metrics in result.per_strategy_results.items():
            logger.info(f"\n  {strategy_name}:")
            logger.info(f"    Return: {metrics.get('return_pct', 0):.2f}%")
            logger.info(f"    Sharpe: {metrics.get('sharpe_ratio', 0):.2f}")
            logger.info(f"    Max DD: {metrics.get('max_drawdown', 0):.2f}%")
            logger.info(f"    Trades: {metrics.get('total_trades', 0)}")
            logger.info(f"    Capital Weight: {metrics.get('capital_weight', 0):.1%}")

    # Optimization results
    logger.info("\nOptimization Results:")
    logger.info(f"  Optimized Sharpe: {result.optimization_results.get('sharpe_ratio', 0):.2f}")
    logger.info(
        f"  Sharpe Improvement: {result.improvement_metrics.get('sharpe_improvement', 0):.1f}%"
    )

    # Recommendation
    logger.info(f"\nRecommendation: {result.recommendation}")
    logger.info(f"Ready for Paper Trading: {result.ready_for_paper_trading}")

    return result


def example_batch_multi_strategy():
    """Example: Run multiple profiles with multi-strategy mode."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Batch Multi-Strategy Execution")
    print("=" * 80 + "\n")

    # Create backtester
    backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")

    # Generate all profiles
    logger.info("Generating all profile combinations...")
    profiles = backtester.generate_all_profiles()
    logger.info(f"Generated {len(profiles)} profile combinations")

    # Run first 3 profiles with multi-strategy (for demonstration)
    test_profiles = profiles[:3]
    results = {}

    for i, profile in enumerate(test_profiles, 1):
        logger.info(f"\n[{i}/{len(test_profiles)}] Running profile: {profile.input_id}")

        try:
            result = backtester.run_single_profile(profile, multi_strategy=True)
            results[result.profile_id] = result

            logger.info(
                f"  ✓ Completed: Sharpe={result.baseline_results.get('sharpe_ratio', 0):.2f}"
            )

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"  ✗ Failed: {e}")

    # Summary statistics
    logger.info("\n" + "-" * 80)
    logger.info("BATCH SUMMARY")
    logger.info("-" * 80)

    if results:
        multi_strategy_count = sum(1 for r in results.values() if r.per_strategy_results)
        logger.info(f"Profiles executed: {len(results)}")
        logger.info(f"Multi-strategy results: {multi_strategy_count}")
        logger.info(f"Single-strategy results: {len(results) - multi_strategy_count}")

        # Average metrics
        avg_sharpe = sum(r.baseline_results.get('sharpe_ratio', 0) for r in results.values()) / len(
            results
        )
        avg_return = sum(r.baseline_results.get('return_pct', 0) for r in results.values()) / len(
            results
        )

        logger.info(f"\nAverage Sharpe Ratio: {avg_sharpe:.2f}")
        logger.info(f"Average Return: {avg_return:.2f}%")

        # Best performing
        best_result = max(results.values(), key=lambda r: r.baseline_results.get('sharpe_ratio', 0))
        logger.info(f"\nBest Profile: {best_result.profile_id}")
        logger.info(f"  Sharpe: {best_result.baseline_results.get('sharpe_ratio', 0):.2f}")
        logger.info(f"  Return: {best_result.baseline_results.get('return_pct', 0):.2f}%")

        if best_result.enabled_strategies:
            logger.info(f"  Strategies: {', '.join(best_result.enabled_strategies)}")

    return results


def example_ensemble_voting():
    """Example: Demonstrate ensemble voting logic."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Ensemble Voting Demonstration")
    print("=" * 80 + "\n")

    # Create backtester
    backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")

    # Create profile
    profile = InputProfile(
        capital_initial=Decimal("100000"),
        objetivo_inversion=ObjectivoInversion.CRECIMIENTO_BALANCEADO,
        risk_tolerance=RiskTolerance.MEDIO,
        investment_horizon=24,
    )

    # Get strategy mapping
    if backtester.profile_mapper:
        strategy_mapping = backtester.profile_mapper.create_strategy_mapping(profile)

        logger.info(f"Ensemble Configuration:")
        logger.info(f"  Mode: {strategy_mapping.ensemble_mode}")
        logger.info(f"  Min Strategies: {strategy_mapping.ensemble_min_strategies}")
        logger.info(f"  Min Confidence: {strategy_mapping.ensemble_confidence_threshold:.2f}")
        logger.info(f"  Strategy Weights: {strategy_mapping.strategy_weights}")

        # Simulate strategy signals
        signals = {
            "momentum_modular": {"action": "buy", "confidence": 0.75},
            "mean_reversion_modular": {"action": "buy", "confidence": 0.60},
            "dividend_screener": {"action": "hold", "confidence": 0.0},
        }

        logger.info(f"\nStrategy Signals:")
        for strategy, signal in signals.items():
            logger.info(
                f"  {strategy}: {signal['action']} (confidence: {signal['confidence']:.2f})"
            )

        # Apply ensemble voting
        decision = backtester._apply_ensemble_voting(profile, strategy_mapping, signals)

        logger.info(f"\nEnsemble Decision:")
        logger.info(f"  Action: {decision['action']}")
        logger.info(f"  Confidence: {decision['confidence']:.2f}")
        logger.info(f"  Meets Threshold: {decision['meets_threshold']}")
        logger.info(f"  Voting Breakdown: {decision['voting_breakdown']}")
    else:
        logger.warning("ProfileStrategyMapper not available")


def example_comparison_single_vs_multi():
    """Example: Compare single-strategy vs multi-strategy execution."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Single vs Multi-Strategy Comparison")
    print("=" * 80 + "\n")

    # Create backtester
    backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")

    # Create profile
    profile = InputProfile(
        capital_initial=Decimal("100000"),
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
        risk_tolerance=RiskTolerance.MEDIO,
        investment_horizon=24,
    )

    # Run single-strategy
    logger.info("Running single-strategy backtest...")
    single_result = backtester.run_single_profile(profile, multi_strategy=False)

    # Run multi-strategy
    logger.info("\nRunning multi-strategy backtest...")
    multi_result = backtester.run_single_profile(profile, multi_strategy=True)

    # Compare results
    logger.info("\n" + "-" * 80)
    logger.info("COMPARISON")
    logger.info("-" * 80)

    logger.info("\nSingle-Strategy Mode:")
    logger.info(f"  Sharpe: {single_result.baseline_results.get('sharpe_ratio', 0):.2f}")
    logger.info(f"  Return: {single_result.baseline_results.get('return_pct', 0):.2f}%")
    logger.info(f"  Max DD: {single_result.baseline_results.get('max_drawdown', 0):.2f}%")

    logger.info("\nMulti-Strategy Mode:")
    logger.info(f"  Sharpe: {multi_result.baseline_results.get('sharpe_ratio', 0):.2f}")
    logger.info(f"  Return: {multi_result.baseline_results.get('return_pct', 0):.2f}%")
    logger.info(f"  Max DD: {multi_result.baseline_results.get('max_drawdown', 0):.2f}%")
    logger.info(
        f"  Strategies: {len(multi_result.enabled_strategies) if multi_result.enabled_strategies else 0}"
    )

    # Calculate improvement
    if multi_result.baseline_results.get('sharpe_ratio', 0) > 0:
        sharpe_diff = multi_result.baseline_results.get(
            'sharpe_ratio', 0
        ) - single_result.baseline_results.get('sharpe_ratio', 0)
        logger.info(f"\nSharpe Ratio Difference: {sharpe_diff:+.2f}")

        if sharpe_diff > 0:
            logger.info("  → Multi-strategy performed better")
        elif sharpe_diff < 0:
            logger.info("  → Single-strategy performed better")
        else:
            logger.info("  → No significant difference")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("MULTI-STRATEGY EXECUTION EXAMPLES")
    print("ProfileBatchBacktester Demonstration")
    print("=" * 80)

    try:
        # Example 1: Single profile multi-strategy
        example_single_profile_multi_strategy()

        # Example 2: Batch multi-strategy
        # example_batch_multi_strategy()  # Uncomment to run (takes longer)

        # Example 3: Ensemble voting
        example_ensemble_voting()

        # Example 4: Comparison
        # example_comparison_single_vs_multi()  # Uncomment to run

        print("\n" + "=" * 80)
        print("EXAMPLES COMPLETED")
        print("=" * 80 + "\n")

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error running examples: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
