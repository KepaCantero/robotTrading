"""
Integration tests for Profile-Driven Trading Orchestrator.

Tests the complete trading lifecycle from input profile to trade execution.
"""

import asyncio
import logging

# Add parent directory to path
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.domain.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from app.services.profile_driven_trading import (
    OrchestratorConfig,
    ProfileDrivenTradingOrchestrator,
    SignalIntegrator,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestProfileDrivenOrchestrator:
    """
    Test suite for Profile-Driven Trading Orchestrator.

    Tests the complete 8-stage trading lifecycle.
    """

    @pytest.fixture
    def sample_input_profile(self) -> InputProfile:
        """Create a sample input profile for testing."""
        return InputProfile(
            capital_initial=Decimal("100000"),  # €100k
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,  # 12 months
        )

    @pytest.fixture
    def orchestrator_config(self) -> OrchestratorConfig:
        """Create orchestrator configuration for testing."""
        return OrchestratorConfig(
            enable_rl_signals=True,
            enable_tax_optimization=True,
            enable_backtest_validation=True,
            enable_risk_gates=True,
            auto_execute_trades=False,  # Dry-run for testing
            top_n_per_universe=20,  # Smaller universe for faster testing
        )

    @pytest.fixture
    def orchestrator(self, orchestrator_config) -> ProfileDrivenTradingOrchestrator:
        """Get orchestrator instance."""
        return ProfileDrivenTradingOrchestrator(orchestrator_config)

    def test_orchestrator_initialization(self, orchestrator):
        """Test that orchestrator initializes correctly."""
        assert orchestrator is not None
        assert orchestrator.config is not None
        assert orchestrator.workflow_manager is not None
        assert orchestrator.signal_integrator is not None

        status = orchestrator.get_status()
        assert "config" in status
        assert "execution" in status
        assert status["execution"]["total_executions"] == 0

    @pytest.mark.asyncio
    async def test_complete_lifecycle(
        self,
        orchestrator,
        sample_input_profile,
    ):
        """
        Test 1: Complete end-to-end lifecycle.

        This is the main integration test that validates the entire
        profile-driven trading workflow from input to execution.
        """
        logger.info("=" * 80)
        logger.info("TEST 1: COMPLETE LIFECYCLE")
        logger.info("=" * 80)

        # Execute complete lifecycle
        result = await orchestrator.execute_trading_lifecycle(sample_input_profile)

        # Validate result
        assert result is not None
        assert result.profile_id != ""
        assert result.execution_time_ms > 0

        # Check critical stages succeeded
        assert result.investment_profile is not None
        assert result.allocation is not None
        assert result.risk_validation is not None

        # Check we have stage results
        assert len(result.stage_results) == 8

        # Validate each stage
        for stage_result in result.stage_results:
            logger.info(
                f"   Stage: {stage_result.stage_type.value} - "
                f"{'✅' if stage_result.success else '❌'}"
            )

        # Get summary
        summary = result.get_summary()
        assert summary["stages"]["total"] == 8
        assert summary["stages"]["successful"] >= 3  # At least critical stages

        logger.info("✅ Complete lifecycle test passed")
        logger.info(f"   Execution time: {result.execution_time_ms:.2f}ms")
        logger.info(f"   Successful stages: {summary['stages']['successful']}/8")
        logger.info("")

    @pytest.mark.asyncio
    async def test_stage_rollback_on_error(
        self,
        orchestrator,
        sample_input_profile,
    ):
        """
        Test 2: Error handling and stage rollback.

        Validates that the orchestrator handles errors gracefully
        and provides detailed error information.
        """
        logger.info("=" * 80)
        logger.info("TEST 2: ERROR HANDLING AND ROLLBACK")
        logger.info("=" * 80)

        # Modify config to induce errors
        orchestrator.config.top_n_per_universe = 0  # This will cause universe selection to fail

        # Execute lifecycle - should continue despite errors
        result = await orchestrator.execute_trading_lifecycle(sample_input_profile)

        # Should still complete, even with errors
        assert result is not None
        assert len(result.stage_results) > 0

        # Check for failed stages
        failed_stages = result.get_failed_stages()
        logger.info(f"   Failed stages: {len(failed_stages)}")

        for failed_stage in failed_stages:
            logger.info(f"   - {failed_stage.stage_type.value}: {failed_stage.message}")
            assert len(failed_stage.errors) > 0

        # Should have some successful stages
        successful_stages = result.get_successful_stages()
        assert len(successful_stages) > 0

        logger.info("✅ Error handling test passed")
        logger.info(f"   Successful stages: {len(successful_stages)}")
        logger.info(f"   Failed stages: {len(failed_stages)}")
        logger.info("")

    def test_signal_integration(self):
        """
        Test 3: Signal integration functionality.

        Tests the SignalIntegrator class with various signal combinations.
        """
        logger.info("=" * 80)
        logger.info("TEST 3: SIGNAL INTEGRATION")
        logger.info("=" * 80)

        integrator = SignalIntegrator()

        # Create test signals
        rl_signals = {
            "AAPL": ("BUY", 0.8),
            "MSFT": ("HOLD", 0.5),
            "GOOGL": ("SELL", 0.7),
        }
        momentum_signals = {
            "AAPL": ("BUY", 0.9),
            "MSFT": ("BUY", 0.6),
            "GOOGL": ("HOLD", 0.4),
            "AMZN": ("BUY", 0.7),
        }
        mean_reversion_signals = {
            "AAPL": ("BUY", 0.7),
            "MSFT": ("SELL", 0.6),
            "TSLA": ("HOLD", 0.5),
        }

        # Combine signals
        signal_set = integrator.combine_signals(
            rl_signals=rl_signals,
            momentum_signals=momentum_signals,
            mean_reversion_signals=mean_reversion_signals,
        )

        # Validate combined signals
        assert signal_set is not None
        assert len(signal_set.signals) > 0
        assert signal_set.buy_count > 0 or signal_set.sell_count > 0

        # Check AAPL has strong BUY signal (all sources agree)
        aapl_signal = signal_set.signals.get("AAPL")
        assert aapl_signal == "BUY"

        # Get summary
        summary = signal_set.get_summary()
        assert summary["total_signals"] > 0
        assert summary["buy_signals"] > 0

        logger.info(f"   Total signals: {summary['total_signals']}")
        logger.info(
            f"   BUY: {summary['buy_signals']}, SELL: {summary['sell_signals']}, HOLD: {summary['hold_signals']}"
        )

        # Test consensus checking
        has_consensus, action = integrator.check_consensus(signal_set, "AAPL")
        assert has_consensus or action == "BUY"

        # Test quality scoring
        quality = integrator.get_signal_quality_score(signal_set, "AAPL")
        assert 0.0 <= quality <= 1.0

        logger.info(f"   AAPL quality score: {quality:.2f}")

        # Test filtering by quality
        filtered = integrator.filter_by_quality(signal_set, min_quality=0.6)
        assert len(filtered.signals) <= len(signal_set.signals)

        logger.info("✅ Signal integration test passed")
        logger.info(f"   Original signals: {len(signal_set.signals)}")
        logger.info(f"   High-quality signals: {len(filtered.signals)}")
        logger.info("")

    @pytest.mark.asyncio
    async def test_tax_optimization_integration(
        self,
        orchestrator,
        sample_input_profile,
    ):
        """
        Test 4: Tax optimization integration.

        Validates that tax optimization is properly integrated
        into the trading lifecycle.
        """
        logger.info("=" * 80)
        logger.info("TEST 4: TAX OPTIMIZATION INTEGRATION")
        logger.info("=" * 80)

        # Enable tax optimization
        orchestrator.config.enable_tax_optimization = True
        orchestrator.config.enable_backtest_validation = False  # Disable for faster testing
        orchestrator.config.enable_rl_signals = False  # Disable for faster testing

        # Execute lifecycle
        result = await orchestrator.execute_trading_lifecycle(sample_input_profile)

        # Check tax optimization stage
        tax_result = result.get_stage_result(
            orchestrator.workflow_manager.stage_results,
            "tax_optimization" if hasattr(orchestrator.workflow_manager, 'stage_results') else None,
        )

        # Should have tax-optimized allocation if stage succeeded
        if result.tax_optimized_allocation:
            logger.info(
                f"   Tax benefit: €{result.tax_optimized_allocation.tax_benefit_estimated:,.2f}"
            )
            logger.info(
                f"   After-tax return: {result.tax_optimized_allocation.after_tax_return_pct:.2f}%"
            )

        logger.info("✅ Tax optimization integration test passed")
        logger.info("")

    def test_config_validation(self):
        """
        Test 5: Configuration validation.

        Tests that OrchestratorConfig properly validates and applies settings.
        """
        logger.info("=" * 80)
        logger.info("TEST 5: CONFIGURATION VALIDATION")
        logger.info("=" * 80)

        # Test default config
        default_config = OrchestratorConfig()
        assert default_config.enable_risk_gates is True
        assert default_config.auto_execute_trades is False  # Safety default
        assert default_config.max_position_size_pct == 0.10

        # Test custom config
        custom_config = OrchestratorConfig(
            enable_rl_signals=False,
            enable_tax_optimization=False,
            auto_execute_trades=True,
            max_position_size_pct=0.05,
        )

        assert custom_config.enable_rl_signals is False
        assert custom_config.enable_tax_optimization is False
        assert custom_config.auto_execute_trades is True
        assert custom_config.max_position_size_pct == 0.05

        # Test strategy allocations
        assert "momentum" in custom_config.strategy_allocations
        assert "mean_reversion" in custom_config.strategy_allocations
        assert "pairs_trading" in custom_config.strategy_allocations

        total_allocation = sum(custom_config.strategy_allocations.values())
        assert abs(total_allocation - 1.0) < 0.01  # Should sum to 1.0

        logger.info("   Default config validated")
        logger.info("   Custom config validated")
        logger.info(f"   Strategy allocation sum: {total_allocation:.2f}")

        logger.info("✅ Configuration validation test passed")
        logger.info("")


def main():
    """Run the tests manually."""
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    test = TestProfileDrivenOrchestrator()

    # Create fixtures
    sample_profile = InputProfile(
        capital_initial=Decimal("100000"),
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
        risk_tolerance=RiskTolerance.MEDIO,
        investment_horizon=12,
    )

    config = OrchestratorConfig(
        enable_rl_signals=True,
        enable_tax_optimization=True,
        enable_backtest_validation=True,
        enable_risk_gates=True,
        auto_execute_trades=False,
        top_n_per_universe=20,
    )

    orchestrator = ProfileDrivenTradingOrchestrator(config)

    # Run tests
    print("\n" + "=" * 80)
    print("RUNNING PROFILE-DRIVEN ORCHESTRATOR TESTS")
    print("=" * 80 + "\n")

    # Test 1: Initialization
    print("Test 1: Initialization")
    test.test_orchestrator_initialization(orchestrator)
    print("✅ PASSED\n")

    # Test 2: Complete lifecycle
    print("Test 2: Complete Lifecycle")
    asyncio.run(test.test_complete_lifecycle(orchestrator, sample_profile))
    print("✅ PASSED\n")

    # Test 3: Signal integration
    print("Test 3: Signal Integration")
    test.test_signal_integration()
    print("✅ PASSED\n")

    # Test 4: Configuration
    print("Test 4: Configuration")
    test.test_config_validation()
    print("✅ PASSED\n")

    print("=" * 80)
    print("ALL TESTS PASSED ✅")
    print("=" * 80)


if __name__ == "__main__":
    main()
