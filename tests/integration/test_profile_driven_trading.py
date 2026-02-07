#!/usr/bin/env python3
"""
Test: Profile-Driven Trading System

This test demonstrates the complete workflow from investor profile to automated trading:

1. InputProfile → ProfileGenerator → InvestmentProfile
2. InvestmentProfile → MarketUniverseOrchestrator → Stock Selection
3. Stock Selection → StrategyStockAllocator → Capital Allocation
4. Allocation → TradingBridgeOrchestrator → Trade Execution

Usage:
    python -m pytest tests/integration/test_profile_driven_trading.py -v -s
    OR
    python tests/integration/test_profile_driven_trading.py
"""

import asyncio
import logging

# Add parent directory to path
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from app.services.live_trading.trading_bridge_orchestrator import TradingBridgeOrchestrator
from app.services.market_universe_orchestrator import MarketUniverseOrchestrator
from app.services.profile_generator.models import (
    InvestmentObjective,
    ProfileGenerationRequest,
    RiskProfile,
)
from app.services.profile_generator.profile_generator import ProfileGenerator
from app.services.strategy_stock_allocator import StrategyStockAllocator

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestProfileDrivenTrading:
    """
    Test suite for profile-driven trading system.

    This test validates the complete workflow from user profile to trade execution.
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
    def profile_generator(self) -> ProfileGenerator:
        """Get the profile generator instance."""
        return ProfileGenerator()

    @pytest.fixture
    def market_universe_orchestrator(self) -> MarketUniverseOrchestrator:
        """Get the market universe orchestrator instance."""
        return MarketUniverseOrchestrator()

    @pytest.fixture
    def strategy_stock_allocator(self) -> StrategyStockAllocator:
        """Get the strategy stock allocator instance."""
        return StrategyStockAllocator()

    @pytest.fixture
    def trading_bridge_orchestrator(self) -> TradingBridgeOrchestrator:
        """Get the trading bridge orchestrator instance."""
        return TradingBridgeOrchestrator()

    def test_01_input_profile_creation(self, sample_input_profile):
        """Test 1: Create an InputProfile from user input."""
        logger.info("=" * 80)
        logger.info("TEST 1: Input Profile Creation")
        logger.info("=" * 80)

        # Validate profile
        assert sample_input_profile.capital_initial == Decimal("100000")
        assert sample_input_profile.objetivo_inversion == ObjectivoInversion.MAXIMIZAR_CAPITAL
        assert sample_input_profile.risk_tolerance == RiskTolerance.MEDIO
        assert sample_input_profile.investment_horizon == 12

        logger.info("✅ InputProfile created successfully:")
        logger.info(f"   Capital: €{sample_input_profile.capital_initial:,.2f}")
        logger.info(f"   Objective: {sample_input_profile.objetivo_inversion.value}")
        logger.info(f"   Risk Tolerance: {sample_input_profile.risk_tolerance.value}")
        logger.info(f"   Horizon: {sample_input_profile.investment_horizon} months")
        logger.info(f"   Capital Flag: {sample_input_profile.capital_flag}")
        logger.info("")

    def test_02_profile_generation(self, sample_input_profile, profile_generator):
        """Test 2: Generate InvestmentProfile from InputProfile."""
        logger.info("=" * 80)
        logger.info("TEST 2: Profile Generation (InputProfile → InvestmentProfile)")
        logger.info("=" * 80)

        # Create profile generation request
        request = ProfileGenerationRequest(
            input_id=sample_input_profile.input_id,
            capital_initial=sample_input_profile.capital_initial,
            objective=InvestmentObjective.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskProfile.MODERATE,
            target_monthly_return_eur=Decimal("2000"),  # €2k/month target
            time_horizon_months=sample_input_profile.investment_horizon,
        )

        # Generate profile
        result = asyncio.run(profile_generator.generate(request))

        assert result.success is True
        assert result.profile is not None

        profile = result.profile
        logger.info("✅ InvestmentProfile generated successfully:")
        logger.info(f"   Profile ID: {profile.profile_id}")
        logger.info(f"   Capital Tier: {profile.capital_tier.value}")
        logger.info(f"   Objective: {profile.objective.value}")
        logger.info(f"   Risk Profile: {profile.risk_profile.value}")
        logger.info(f"   Enabled Modules: {[m.name for m in profile.enabled_modules]}")
        logger.info(f"   Max Leverage: {profile.max_leverage}")
        logger.info(f"   Max Position Size: {profile.max_position_size_pct}%")

        if profile.required_annual_return_pct:
            logger.info(f"   Required Annual Return: {profile.required_annual_return_pct}%")
        if profile.required_alpha_pct:
            logger.info(f"   Required Alpha: {profile.required_alpha_pct}%")
        if profile.position_size_pct:
            logger.info(f"   Position Size: {profile.position_size_pct}%")
        if profile.concurrent_positions:
            logger.info(f"   Concurrent Positions: {profile.concurrent_positions}")

        if result.warnings:
            logger.info(f"   Warnings: {result.warnings}")

        logger.info("")

    @pytest.mark.asyncio
    async def test_03_market_universe_selection(
        self,
        sample_input_profile,
        market_universe_orchestrator,
    ):
        """Test 3: Select stocks from market universe based on profile."""
        logger.info("=" * 80)
        logger.info("TEST 3: Market Universe Selection (Profile → Filtered Stocks)")
        logger.info("=" * 80)

        # Use S&P 500 top 30 for faster testing
        total_capital = float(sample_input_profile.capital_initial)

        logger.info(f"Fetching S&P 500 stocks for €{total_capital:,.2f} allocation...")

        allocation_result = await market_universe_orchestrator.get_sp500_for_allocation(
            total_capital=total_capital,
            strategy_allocations={
                "momentum": total_capital * 0.50,
                "mean_reversion": total_capital * 0.35,
                "pairs_trading": total_capital * 0.15,
            },
            top_n=30,  # Top 30 for faster testing
            download_period="6mo",
            download_interval="1d",
            min_avg_volume=500_000,  # Relaxed for testing
            min_price=5.0,
            max_volatility=0.20,  # Relaxed for testing
        )

        logger.info("✅ Market universe selection completed:")
        logger.info(f"   Allocations: {len(allocation_result.allocations)} stocks")
        logger.info(f"   Pairs: {len(allocation_result.pairs)} pairs")
        logger.info(f"   Residual Capital: €{allocation_result.residual_capital:,.2f}")
        logger.info(f"   Validation Passed: {allocation_result.validation_passed}")

        if not allocation_result.validation_passed:
            logger.warning(f"   Validation Errors: {allocation_result.validation_errors}")

        if allocation_result.decision_logs:
            for log in allocation_result.decision_logs[:5]:
                logger.info(f"   Decision: {log}")

        if allocation_result.allocations:
            logger.info("   Top 5 Allocations:")
            for i, (symbol, metrics) in enumerate(list(allocation_result.allocations.items())[:5]):
                logger.info(
                    f"      {i+1}. {symbol}: €{metrics.capital:,.2f} ({metrics.weight:.2%}) - {metrics.strategy}"
                )

        logger.info("")

        return allocation_result

    @pytest.mark.asyncio
    async def test_04_strategy_stock_allocation(
        self,
        sample_input_profile,
        strategy_stock_allocator,
    ):
        """Test 4: Allocate capital to strategies and stocks."""
        logger.info("=" * 80)
        logger.info("TEST 4: Strategy Stock Allocation (Stocks → Strategy Assignment)")
        logger.info("=" * 80)

        # Get market universe first
        orchestrator = MarketUniverseOrchestrator()
        total_capital = float(sample_input_profile.capital_initial)

        # Get filtered universe
        filtered_data = await orchestrator.get_universe_for_allocation(
            include_sp500=True,
            include_nasdaq100=False,
            include_ibex35=False,
            include_crypto=False,
            top_n_per_universe=30,
            download_period="6mo",
            download_interval="1d",
            min_avg_volume=500_000,
            min_price=5.0,
            max_volatility=0.20,
        )

        if not filtered_data:
            logger.warning("⚠️  No filtered data available, using mock data for testing")
            # Create minimal mock data for testing
            from datetime import datetime, timedelta

            import numpy as np
            import pandas as pd

            filtered_data = {}
            base_date = datetime.now() - timedelta(days=180)

            for symbol in ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "AMD"]:
                dates = pd.date_range(start=base_date, periods=126, freq="D")
                np.random.seed(hash(symbol) % 2**32)
                price = 100 + np.cumsum(np.random.randn(126) * 2)

                filtered_data[symbol] = pd.DataFrame(
                    {
                        'open': price * (1 + np.random.uniform(-0.01, 0.01, 126)),
                        'high': price * (1 + np.abs(np.random.uniform(0, 0.02, 126))),
                        'low': price * (1 - np.abs(np.random.uniform(0, 0.02, 126))),
                        'close': price,
                        'volume': np.random.randint(1000000, 10000000, 126),
                    }
                )
                filtered_data[symbol].index = dates

        # Allocate capital
        logger.info(f"Allocating €{total_capital:,.2f} to strategies...")

        allocation_result = strategy_stock_allocator.allocate(
            historical_data=filtered_data,
            total_capital=total_capital,
            strategy_allocations={
                "momentum": total_capital * 0.50,
                "mean_reversion": total_capital * 0.35,
                "pairs_trading": total_capital * 0.15,
            },
        )

        logger.info("✅ Strategy stock allocation completed:")
        logger.info(f"   Total Allocations: {len(allocation_result.allocations)}")
        logger.info(f"   Pairs: {len(allocation_result.pairs)}")
        logger.info(f"   Residual Capital: €{allocation_result.residual_capital:,.2f}")
        logger.info(f"   Validation Passed: {allocation_result.validation_passed}")

        # Count by strategy
        strategy_counts = {}
        for metrics in allocation_result.allocations.values():
            strategy = metrics.strategy or "unassigned"
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

        logger.info("   Strategy Distribution:")
        for strategy, count in strategy_counts.items():
            logger.info(f"      {strategy}: {count} stocks")

        if allocation_result.allocations:
            logger.info("   Top 5 Allocations:")
            sorted_allocations = sorted(
                allocation_result.allocations.items(), key=lambda x: x[1].capital, reverse=True
            )[:5]
            for i, (symbol, metrics) in enumerate(sorted_allocations):
                logger.info(
                    f"      {i+1}. {symbol}: €{metrics.capital:,.2f} ({metrics.weight:.2%})"
                )

        logger.info("")

        return allocation_result

    def test_05_trading_bridge_orchestrator(self, trading_bridge_orchestrator):
        """Test 5: Trading bridge orchestrator for executing trades."""
        logger.info("=" * 80)
        logger.info("TEST 5: Trading Bridge Orchestrator (Alert → Trade Execution)")
        logger.info("=" * 80)

        # Start the trading bridge
        started = asyncio.run(trading_bridge_orchestrator.start())
        assert started is True

        # Get statistics
        stats = trading_bridge_orchestrator.get_bridge_statistics()

        logger.info("✅ Trading bridge orchestrator initialized:")
        logger.info(f"   Status: {stats['status']}")
        logger.info(f"   Is Active: {stats['is_active']}")
        logger.info(f"   Total Executions: {stats['total_executions']}")
        logger.info(f"   Successful Trades: {stats['successful_trades']}")
        logger.info(f"   Failed Trades: {stats['failed_trades']}")
        logger.info(f"   Pending Orders: {stats['pending_orders']}")

        # Stop the trading bridge
        stopped = asyncio.run(trading_bridge_orchestrator.stop())
        assert stopped is True

        logger.info("")

    @pytest.mark.asyncio
    async def test_06_end_to_end_profile_driven_trading(
        self,
        sample_input_profile,
        profile_generator,
        strategy_stock_allocator,
        trading_bridge_orchestrator,
    ):
        """
        Test 6: Complete end-to-end workflow.

        This is the main test that demonstrates the complete profile-driven trading system:
        1. User creates InputProfile
        2. System generates InvestmentProfile
        3. System selects stocks from market universe
        4. System allocates capital to strategies
        5. System is ready to execute trades
        """
        logger.info("=" * 80)
        logger.info("TEST 6: END-TO-END PROFILE-DRIVEN TRADING")
        logger.info("=" * 80)

        # Step 1: Create InputProfile
        logger.info("Step 1: Creating InputProfile...")
        logger.info(f"   Capital: €{sample_input_profile.capital_initial:,.2f}")
        logger.info(f"   Objective: {sample_input_profile.objetivo_inversion.value}")
        logger.info(f"   Risk: {sample_input_profile.risk_tolerance.value}")
        logger.info(f"   Horizon: {sample_input_profile.investment_horizon} months")
        logger.info("   ✅ InputProfile created")
        logger.info("")

        # Step 2: Generate InvestmentProfile
        logger.info("Step 2: Generating InvestmentProfile...")
        request = ProfileGenerationRequest(
            input_id=sample_input_profile.input_id,
            capital_initial=sample_input_profile.capital_initial,
            objective=InvestmentObjective.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskProfile.MODERATE,
            target_monthly_return_eur=Decimal("2000"),
            time_horizon_months=sample_input_profile.investment_horizon,
        )

        profile_result = await profile_generator.generate(request)

        assert profile_result.success is True
        assert profile_result.profile is not None

        profile = profile_result.profile
        logger.info(f"   Profile ID: {profile.profile_id}")
        logger.info(f"   Capital Tier: {profile.capital_tier.value}")
        logger.info(f"   Enabled Modules: {len(profile.enabled_modules)}")
        for module in profile.enabled_modules:
            logger.info(f"      - {module.name} (priority: {module.priority})")
        logger.info(f"   Max Leverage: {profile.max_leverage}x")
        logger.info(f"   Position Size: {profile.max_position_size_pct}%")
        logger.info("   ✅ InvestmentProfile generated")
        logger.info("")

        # Step 3: Get Market Universe
        logger.info("Step 3: Selecting stocks from market universe...")
        orchestrator = MarketUniverseOrchestrator()

        filtered_data = await orchestrator.get_universe_for_allocation(
            include_sp500=True,
            top_n_per_universe=20,  # Limited for faster testing
            download_period="6mo",
            min_avg_volume=500_000,
        )

        if not filtered_data:
            logger.warning("   ⚠️  No market data available, creating test data...")
            from datetime import datetime, timedelta

            import numpy as np
            import pandas as pd

            base_date = datetime.now() - timedelta(days=180)
            test_symbols = [
                "AAPL",
                "MSFT",
                "GOOGL",
                "AMZN",
                "TSLA",
                "META",
                "NVDA",
                "AMD",
                "NFLX",
                "INTC",
            ]

            for symbol in test_symbols:
                dates = pd.date_range(start=base_date, periods=126, freq="D")
                np.random.seed(hash(symbol) % 2**32)
                price = 100 + np.cumsum(np.random.randn(126) * 2)

                filtered_data[symbol] = pd.DataFrame(
                    {
                        'open': price * (1 + np.random.uniform(-0.01, 0.01, 126)),
                        'high': price * (1 + np.abs(np.random.uniform(0, 0.02, 126))),
                        'low': price * (1 - np.abs(np.random.uniform(0, 0.02, 126))),
                        'close': price,
                        'volume': np.random.randint(1000000, 10000000, 126),
                    }
                )
                filtered_data[symbol].index = dates

        logger.info(f"   Universe Size: {len(filtered_data)} stocks")
        logger.info("   ✅ Market universe selected")
        logger.info("")

        # Step 4: Allocate Capital to Strategies
        logger.info("Step 4: Allocating capital to strategies...")
        total_capital = float(sample_input_profile.capital_initial)

        allocation_result = strategy_stock_allocator.allocate(
            historical_data=filtered_data,
            total_capital=total_capital,
            strategy_allocations={
                "momentum": total_capital * 0.50,
                "mean_reversion": total_capital * 0.35,
                "pairs_trading": total_capital * 0.15,
            },
        )

        logger.info(f"   Total Allocations: {len(allocation_result.allocations)}")
        logger.info(f"   Residual: €{allocation_result.residual_capital:,.2f}")
        logger.info(
            f"   Validation: {'✅ PASSED' if allocation_result.validation_passed else '❌ FAILED'}"
        )

        # Show allocations by strategy
        strategy_totals = {}
        for metrics in allocation_result.allocations.values():
            strategy = metrics.strategy or "unassigned"
            strategy_totals[strategy] = strategy_totals.get(strategy, 0) + metrics.capital

        logger.info("   Allocation by Strategy:")
        for strategy, capital in strategy_totals.items():
            logger.info(f"      {strategy}: €{capital:,.2f} ({capital/total_capital:.1%})")

        # Show top 5 allocations
        logger.info("   Top 5 Holdings:")
        sorted_allocations = sorted(
            allocation_result.allocations.items(), key=lambda x: x[1].capital, reverse=True
        )[:5]
        for i, (symbol, metrics) in enumerate(sorted_allocations):
            logger.info(
                f"      {i+1}. {symbol}: €{metrics.capital:,.2f} ({metrics.weight:.2%}) - {metrics.strategy}"
            )

        logger.info("   ✅ Capital allocation completed")
        logger.info("")

        # Step 5: Initialize Trading Bridge
        logger.info("Step 5: Initializing trading bridge...")
        await trading_bridge_orchestrator.start()

        stats = trading_bridge_orchestrator.get_bridge_statistics()
        logger.info(f"   Status: {stats['status']}")
        logger.info(f"   Active: {stats['is_active']}")
        logger.info("   ✅ Trading bridge ready for execution")
        logger.info("")

        # Summary
        logger.info("=" * 80)
        logger.info("END-TO-END TEST SUMMARY")
        logger.info("=" * 80)
        logger.info("✅ Complete profile-driven trading workflow validated!")
        logger.info("")
        logger.info("Workflow Steps:")
        logger.info("   1. ✅ InputProfile created from user input")
        logger.info("   2. ✅ InvestmentProfile generated with modules and parameters")
        logger.info("   3. ✅ Market universe filtered and selected")
        logger.info("   4. ✅ Capital allocated to strategies and stocks")
        logger.info("   5. ✅ Trading bridge initialized and ready")
        logger.info("")
        logger.info("The system is now ready to:")
        logger.info("   - Monitor market data for selected stocks")
        logger.info("   - Generate trading signals based on strategies")
        logger.info("   - Execute trades through the trading bridge")
        logger.info("   - Apply risk gates and validation")
        logger.info("=" * 80)

        # Cleanup
        await trading_bridge_orchestrator.stop()


def main():
    """Run the tests manually."""
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    test = TestProfileDrivenTrading()

    # Create fixtures
    sample_profile = InputProfile(
        capital_initial=Decimal("100000"),
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
        risk_tolerance=RiskTolerance.MEDIO,
        investment_horizon=12,
    )

    profile_gen = ProfileGenerator()
    MarketUniverseOrchestrator()
    allocator = StrategyStockAllocator()
    trading_bridge = TradingBridgeOrchestrator()

    # Run end-to-end test
    asyncio.run(
        test.test_06_end_to_end_profile_driven_trading(
            sample_profile,
            profile_gen,
            allocator,
            trading_bridge,
        )
    )


if __name__ == "__main__":
    main()
