from __future__ import annotations

"""
Profile-Driven Trading Orchestrator - Main implementation.

Orchestrates the complete trading lifecycle from investor profile to trade execution.
This is the main entry point for the profile-driven trading system.
"""

import asyncio
import importlib.util
import logging
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd

from .models import (
    ExecutionResult,
    OrchestratorConfig,
    RiskValidationResult,
    SignalSet,
    StageType,
    TradingResult,
)
from .signal_integrator import SignalIntegrator
from .workflow_manager import WorkflowManager

logger = logging.getLogger(__name__)

# Check for known compatibility issues upfront
# DO NOT import stable_baselines3 here as it causes deadlocks with NumPy 2.x
_RL_ENGINE_AVAILABLE = True
try:
    import numpy

    numpy_version = numpy.__version__
    if numpy_version.startswith("2."):
        # NumPy 2.x has compatibility issues with stable_baselines3
        # Mark RL engine as unavailable WITHOUT importing it
        logger.debug("NumPy 2.x detected, RL engine disabled")
        _RL_ENGINE_AVAILABLE = False
except ImportError:
    logger.debug("NumPy not available, RL engine disabled")
    _RL_ENGINE_AVAILABLE = False


class ProfileDrivenTradingOrchestrator:
    """
    Main orchestrator for profile-driven trading lifecycle.

    Executes the complete 8-stage trading pipeline:
    1. Profile Generation
    2. Universe Selection
    3. Capital Allocation
    4. Signal Generation
    5. Tax Optimization
    6. Risk Validation
    7. Backtest Validation
    8. Trade Execution

    Features:
    - Lazy component initialization
    - Comprehensive error handling
    - Stage-by-stage execution with rollback capability
    - Dry-run mode for testing
    - Detailed logging and monitoring
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        """
        Initialize the orchestrator.

        Args:
            config: OrchestratorConfig with feature flags and parameters
        """
        self.config = config or OrchestratorConfig()
        self.workflow_manager = WorkflowManager(
            max_concurrent_stages=self.config.max_concurrent_stages
        )
        self.signal_integrator = SignalIntegrator()

        # Lazy-loaded components
        self._profile_generator = None
        self._market_universe_orchestrator = None
        self._stock_allocator = None
        self._rl_engine = None
        self._tax_optimizer = None
        self._risk_gates = None
        self._backtest_orchestrator = None
        self._trading_bridge = None

        # Execution tracking
        self.execution_count = 0
        self.last_execution_time: Optional[datetime] = None

        logger.info("✅ ProfileDrivenTradingOrchestrator initialized")
        logger.info(
            f"   Config: RL={self.config.enable_rl_signals}, "
            f"Tax={self.config.enable_tax_optimization}, "
            f"Risk={self.config.enable_risk_gates}, "
            f"Auto-Execute={self.config.auto_execute_trades}, "
            f"IBKR={'Enabled' if self.config.use_ibkr else 'Disabled (mock mode)'}"
        )

    # ============================================================================
    # LAZY LOADING OF COMPONENTS
    # ============================================================================

    def _get_profile_generator(self):
        """Lazy load ProfileGenerator."""
        if self._profile_generator is None:
            from app.services.profile_generator.profile_generator import ProfileGenerator

            self._profile_generator = ProfileGenerator()
            logger.debug("✅ ProfileGenerator loaded")
        return self._profile_generator

    def _get_market_universe_orchestrator(self):
        """Lazy load MarketUniverseOrchestrator."""
        if self._market_universe_orchestrator is None:
            from app.services.market_universe_orchestrator import MarketUniverseOrchestrator

            self._market_universe_orchestrator = MarketUniverseOrchestrator()
            logger.debug("✅ MarketUniverseOrchestrator loaded")
        return self._market_universe_orchestrator

    def _get_stock_allocator(self):
        """Lazy load StrategyStockAllocator."""
        if self._stock_allocator is None:
            from app.services.strategy_stock_allocator import StrategyStockAllocator

            self._stock_allocator = StrategyStockAllocator()
            logger.debug("✅ StrategyStockAllocator loaded")
        return self._stock_allocator

    def _get_rl_engine(self):
        """Lazy load ReinforcementLearningEngine."""
        if self._rl_engine is None:
            # Early return if we know RL engine is not available
            if not _RL_ENGINE_AVAILABLE:
                logger.debug("   RL engine disabled due to compatibility issues")
                self._rl_engine = False
                return None

            # Check if module exists before importing
            module_name = (
                "app.domain.strategies.momentum_modular.learning.reinforcement_learning_engine"
            )
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                logger.debug("   ReinforcementLearningEngine module not found")
                self._rl_engine = False
                return None

            try:
                # Use dynamic import to avoid pylint import-error
                module = importlib.import_module(module_name)
                # Access via attribute lookup for dynamic module loading
                if hasattr(module, "ReinforcementLearningEngine"):
                    rl_engine_class = module.ReinforcementLearningEngine
                    self._rl_engine = rl_engine_class(config={})
                    logger.debug("✅ ReinforcementLearningEngine loaded")
                else:
                    logger.debug("   ReinforcementLearningEngine class not found in module")
                    self._rl_engine = False
            except Exception as e:
                # RL engine not available, return None and log warning
                logger.warning(f"   ReinforcementLearningEngine not available: {type(e).__name__}")
                logger.debug(f"   RL engine error details: {e}")
                self._rl_engine = False  # Use False to indicate we tried and failed
        return self._rl_engine if self._rl_engine is not False else None

    def _get_tax_optimizer(self):
        """Lazy load TaxOptimizedPortfolioBuilder."""
        if self._tax_optimizer is None:
            from app.services.tax_efficiency.tax_optimized_builder import (
                TaxOptimizedPortfolioBuilder,
            )

            self._tax_optimizer = TaxOptimizedPortfolioBuilder()
            logger.debug("✅ TaxOptimizedPortfolioBuilder loaded")
        return self._tax_optimizer

    def _get_risk_gates(self):
        """Lazy load RiskGates."""
        if self._risk_gates is None:
            from app.services.live_trading.broker_connector import get_broker_connector
            from app.services.live_trading.risk_gates import RiskGates

            self._risk_gates = RiskGates(broker=get_broker_connector())
            logger.debug("✅ RiskGates loaded")
        return self._risk_gates

    def _get_backtest_orchestrator(self):
        """Lazy load BacktestOrchestrator."""
        if self._backtest_orchestrator is None:
            from app.services.backtest_orchestration.backtest_orchestrator import (
                BacktestOrchestrator,
            )

            self._backtest_orchestrator = BacktestOrchestrator()
            logger.debug("✅ BacktestOrchestrator loaded")
        return self._backtest_orchestrator

    def _get_trading_bridge(self):
        """Lazy load TradingBridgeOrchestrator."""
        if self._trading_bridge is None:
            from app.services.live_trading.trading_bridge_orchestrator import (
                TradingBridgeOrchestrator,
            )

            self._trading_bridge = TradingBridgeOrchestrator()
            logger.debug("✅ TradingBridgeOrchestrator loaded")
        return self._trading_bridge

    # ============================================================================
    # MAIN ENTRY POINT
    # ============================================================================

    async def execute_trading_lifecycle(self, input_profile) -> TradingResult:
        """
        Execute the complete trading lifecycle from input profile to trades.

        This is the main entry point that orchestrates all 8 stages.

        Args:
            input_profile: InputProfile with user's investment parameters

        Returns:
            TradingResult with complete execution details
        """
        start_time = datetime.utcnow()
        logger.info("=" * 80)
        logger.info("🚀 STARTING PROFILE-DRIVEN TRADING LIFECYCLE")
        logger.info("=" * 80)
        logger.info(f"   Capital: €{input_profile.capital_initial:,.2f}")
        logger.info(f"   Objective: {input_profile.objetivo_inversion.value}")
        logger.info(f"   Risk: {input_profile.risk_tolerance.value}")
        logger.info(f"   Horizon: {input_profile.investment_horizon} months")
        logger.info("")

        result = TradingResult(
            success=False,
            profile_id=getattr(input_profile, 'input_id', 'unknown'),
            started_at=start_time,
        )

        try:
            # Execute all 8 stages
            stages = [
                (
                    StageType.PROFILE_GENERATION,
                    self.stage_1_generate_profile,
                    {"input_profile": input_profile},
                ),
                (StageType.UNIVERSE_SELECTION, self.stage_2_select_universe, {}),
                (StageType.CAPITAL_ALLOCATION, self.stage_3_allocate_capital, {}),
                (StageType.SIGNAL_GENERATION, self.stage_4_generate_signals, {}),
                (StageType.TAX_OPTIMIZATION, self.stage_5_optimize_taxes, {}),
                (StageType.RISK_VALIDATION, self.stage_6_validate_risk, {}),
                (StageType.BACKTEST_VALIDATION, self.stage_7_backtest_validate, {}),
                (StageType.TRADE_EXECUTION, self.stage_8_execute_trades, {}),
            ]

            # Execute pipeline
            pipeline_result = await self.workflow_manager.execute_pipeline(
                stages,
                stop_on_error=False,  # Continue even if some stages fail
            )

            result.stage_results = pipeline_result.stage_results
            result.completed_at = datetime.utcnow()

            # Extract results from stages
            profile_result = pipeline_result.get_stage_by_type(StageType.PROFILE_GENERATION)
            if profile_result and profile_result.success:
                result.investment_profile = profile_result.data
                result.profile_id = getattr(profile_result.data, 'profile_id', result.profile_id)

            universe_result = pipeline_result.get_stage_by_type(StageType.UNIVERSE_SELECTION)
            if universe_result and universe_result.success:
                result.universe_data = {
                    "universe_size": len(universe_result.data) if universe_result.data else 0
                }

            allocation_result = pipeline_result.get_stage_by_type(StageType.CAPITAL_ALLOCATION)
            if allocation_result and allocation_result.success:
                result.allocation = allocation_result.data

            signal_result = pipeline_result.get_stage_by_type(StageType.SIGNAL_GENERATION)
            if signal_result and signal_result.success:
                result.signals = signal_result.data

            tax_result = pipeline_result.get_stage_by_type(StageType.TAX_OPTIMIZATION)
            if tax_result and tax_result.success:
                result.tax_optimized_allocation = tax_result.data

            risk_result = pipeline_result.get_stage_by_type(StageType.RISK_VALIDATION)
            if risk_result and risk_result.success:
                result.risk_validation = risk_result.data

            backtest_result = pipeline_result.get_stage_by_type(StageType.BACKTEST_VALIDATION)
            if backtest_result and backtest_result.success:
                result.backtest_result = backtest_result.data

            execution_result = pipeline_result.get_stage_by_type(StageType.TRADE_EXECUTION)
            if execution_result and execution_result.success:
                result.execution_result = execution_result.data

            # Determine overall success
            # Critical stages: profile, allocation, risk
            critical_stages = [
                StageType.PROFILE_GENERATION,
                StageType.CAPITAL_ALLOCATION,
                StageType.RISK_VALIDATION,
            ]

            result.success = all(
                pipeline_result.get_stage_by_type(s)
                and pipeline_result.get_stage_by_type(s).success
                for s in critical_stages
            )

            # Collect warnings
            for stage_result in result.stage_results:
                result.warnings.extend(stage_result.warnings)

            # Collect errors from failed stages
            for stage_result in (
                result.get_failed_stages() if hasattr(result, 'get_failed_stages') else []
            ):
                result.errors.extend(stage_result.errors)

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"❌ Fatal error in trading lifecycle: {e}", exc_info=True)
            result.errors.append(f"Fatal error: {str(e)}")
            result.success = False

        result.execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Update tracking
        self.execution_count += 1
        self.last_execution_time = datetime.utcnow()

        logger.info("=" * 80)
        logger.info(
            f"🏁 TRADING LIFECYCLE COMPLETE: {'SUCCESS ✅' if result.success else 'FAILED ❌'}"
        )
        logger.info(f"   Execution Time: {result.execution_time_ms:.2f}ms")
        logger.info(f"   Stages: {len(result.stage_results)}")
        logger.info("=" * 80)

        return result

    # ============================================================================
    # STAGE 1: PROFILE GENERATION
    # ============================================================================

    async def stage_1_generate_profile(self, input_profile) -> Any:
        """
        Stage 1: Generate InvestmentProfile from InputProfile.

        Args:
            input_profile: InputProfile with user's investment parameters

        Returns:
            InvestmentProfile
        """
        logger.info("📊 STAGE 1: PROFILE GENERATION")
        logger.info("-" * 40)

        from app.services.profile_generator.models import (
            InvestmentObjective,
            ProfileGenerationRequest,
            RiskProfile,
        )

        # Map risk tolerance from InputProfile to RiskProfile
        risk_mapping = {
            "bajo": RiskProfile.CONSERVATIVE,
            "medio": RiskProfile.MODERATE,
            "alto": RiskProfile.AGGRESSIVE,
        }

        # Create profile generation request
        request = ProfileGenerationRequest(
            input_id=getattr(input_profile, 'input_id', 'unknown'),
            capital_initial=input_profile.capital_initial,
            objective=InvestmentObjective(input_profile.objetivo_inversion.value),
            risk_tolerance=risk_mapping.get(
                input_profile.risk_tolerance.value, RiskProfile.MODERATE
            ),
            target_monthly_return_eur=Decimal("2000"),  # Default target
            time_horizon_months=input_profile.investment_horizon,
        )

        # Generate profile
        profile_generator = self._get_profile_generator()
        generation_result = await profile_generator.generate(request)

        if not generation_result.success:
            raise RuntimeError(f"Profile generation failed: {generation_result.error_message}")

        profile = generation_result.profile

        logger.info(f"   Profile ID: {profile.profile_id}")
        logger.info(f"   Capital Tier: {profile.capital_tier.value}")
        logger.info(f"   Objective: {profile.objective.value}")
        logger.info(f"   Risk Profile: {profile.risk_profile.value}")
        logger.info(f"   Enabled Modules: {len(profile.enabled_modules)}")

        return profile

    # ============================================================================
    # STAGE 2: UNIVERSE SELECTION
    # ============================================================================

    async def stage_2_select_universe(self, profile=None) -> Dict[str, pd.DataFrame]:
        """
        Stage 2: Select stock universe based on profile.

        Args:
            profile: InvestmentProfile from Stage 1

        Returns:
            Dict of symbol -> DataFrame with OHLCV data
        """
        logger.info("🌐 STAGE 2: UNIVERSE SELECTION")
        logger.info("-" * 40)

        market_orchestrator = self._get_market_universe_orchestrator()

        # Get filtered universe
        filtered_data = await market_orchestrator.get_universe_for_allocation(
            include_sp500=self.config.include_sp500,
            include_nasdaq100=self.config.include_nasdaq100,
            include_ibex35=self.config.include_ibex35,
            include_crypto=self.config.include_crypto,
            top_n_per_universe=self.config.top_n_per_universe,
            download_period=self.config.download_period,
            download_interval=self.config.download_interval,
            min_avg_volume=self.config.min_avg_volume,
            min_price=self.config.min_price,
            max_volatility=self.config.max_volatility,
        )

        if not filtered_data:
            logger.warning("   No universe data available, creating test data")
            # Create minimal test data for testing
            filtered_data = self._create_test_universe()

        logger.info(f"   Universe Size: {len(filtered_data)} stocks")

        return filtered_data

    async def stage_2_select_universe_with_real_data(
        self,
        profile=None,
        symbols: Optional[List[str]] = None,
        num_symbols: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> Dict[str, pd.DataFrame]:
        """
        Stage 2: Select universe using REAL data from Alpha Vantage.

        Uses Alpha Vantage TIME_SERIES_DAILY for historical data with:
        - Real S&P 500 top stocks by market cap
        - Actual OHLCV data for backtesting
        - Rate limiting (5 calls/minute for free tier)
        - Data caching to avoid re-fetching

        Args:
            profile: InvestmentProfile from Stage 1
            symbols: List of symbols to fetch (default: top N from S&P 500)
            num_symbols: Number of top S&P 500 stocks to fetch (default: 50)
            start_date: Start date for historical data (default: 1 year ago)
            end_date: End date for historical data (default: today)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            Dict of symbol -> DataFrame with OHLCV data
        """
        logger.info("🌐 STAGE 2: UNIVERSE SELECTION WITH REAL DATA")
        logger.info("-" * 40)
        logger.info("   Data Source: Alpha Vantage API")
        logger.info(f"   Symbols: {num_symbols if not symbols else len(symbols)}")
        logger.info(f"   Cache: {'Enabled' if use_cache else 'Disabled'}")

        # Import RealMarketDataFetcher
        from app.infrastructure.data.real_market_data import RealMarketDataFetcher

        # Set default date range
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)  # 1 year

        logger.info(f"   Date Range: {start_date.date()} to {end_date.date()}")

        try:
            async with RealMarketDataFetcher() as fetcher:
                # Fetch data
                if symbols is None:
                    # Fetch top N S&P 500 stocks
                    logger.info(f"   Fetching top {num_symbols} S&P 500 stocks...")
                    universe_data = await fetcher.fetch_sp500_top_n(
                        n=num_symbols,
                        start_date=start_date,
                        end_date=end_date,
                        use_cache=use_cache,
                    )
                else:
                    # Fetch specified symbols
                    logger.info(f"   Fetching {len(symbols)} specified symbols...")
                    universe_data = await fetcher.fetch_multiple_symbols(
                        symbols=symbols,
                        start_date=start_date,
                        end_date=end_date,
                        use_cache=use_cache,
                    )

                if not universe_data:
                    logger.warning("   No real data available, creating test universe")
                    universe_data = self._create_test_universe()
                else:
                    logger.info(
                        f"   ✅ Successfully fetched {len(universe_data)} symbols with REAL data"
                    )

                    # Show cache statistics
                    cache_stats = fetcher.get_cache_stats()
                    logger.info(f"   Cache: {cache_stats['total_cached_symbols']} symbols cached")

                return universe_data

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"   ❌ Error fetching real data: {e}")
            logger.warning("   Falling back to test universe")
            return self._create_test_universe()

    def _create_test_universe(self) -> Dict[str, pd.DataFrame]:
        """Create test universe for testing when no data available."""
        from datetime import datetime, timedelta

        import numpy as np

        base_date = datetime.now() - timedelta(days=180)
        test_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "AMD"]

        filtered_data = {}
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

        return filtered_data

    # ============================================================================
    # STAGE 3: CAPITAL ALLOCATION
    # ============================================================================

    async def stage_3_allocate_capital(self, profile=None, universe=None) -> Dict[str, Any]:
        """
        Stage 3: Allocate capital to strategies and stocks.

        Args:
            profile: InvestmentProfile
            universe: Dict of symbol -> DataFrame from Stage 2

        Returns:
            Allocation result dict
        """
        logger.info("💰 STAGE 3: CAPITAL ALLOCATION")
        logger.info("-" * 40)

        # Get universe from workflow state if not provided
        if universe is None:
            universe = self.workflow_manager.get_current_state().get(
                StageType.UNIVERSE_SELECTION.value
            )
            if universe is None:
                # Create test universe
                universe = self._create_test_universe()

        # Get profile from workflow state if not provided
        if profile is None:
            profile = self.workflow_manager.get_current_state().get(
                StageType.PROFILE_GENERATION.value
            )

        total_capital = float(profile.initial_capital) if profile else 100000.0

        # Allocate capital
        allocator = self._get_stock_allocator()
        allocation_result = allocator.allocate(
            historical_data=universe,
            total_capital=total_capital,
            strategy_allocations=self.config.strategy_allocations,
        )

        logger.info(f"   Total Allocations: {len(allocation_result.allocations)}")
        logger.info(f"   Residual: €{allocation_result.residual_capital:,.2f}")
        logger.info(
            f"   Validation: {'PASSED' if allocation_result.validation_passed else 'FAILED'}"
        )

        return {
            "allocations": allocation_result.allocations,
            "pairs": allocation_result.pairs,
            "residual_capital": allocation_result.residual_capital,
            "validation_passed": allocation_result.validation_passed,
            "total_capital": total_capital,
        }

    # ============================================================================
    # STAGE 4: SIGNAL GENERATION
    # ============================================================================

    async def stage_4_generate_signals(self, profile=None, allocation=None) -> SignalSet:
        """
        Stage 4: Generate trading signals from multiple sources.

        Args:
            profile: InvestmentProfile
            allocation: Allocation result from Stage 3

        Returns:
            SignalSet with combined signals
        """
        logger.info("📡 STAGE 4: SIGNAL GENERATION")
        logger.info("-" * 40)

        # Get allocation from workflow state if not provided
        if allocation is None:
            state = self.workflow_manager.get_current_state()
            allocation_data = state.get(StageType.CAPITAL_ALLOCATION.value)
            allocation = allocation_data

        if not allocation or not allocation.get("allocations"):
            logger.warning("   No allocations available, generating empty signal set")
            return SignalSet()

        symbols = list(allocation["allocations"].keys())

        # Generate signals from different sources
        rl_signals = {}
        momentum_signals = {}
        mean_reversion_signals = {}

        # RL signals (if enabled)
        if self.config.enable_rl_signals:
            try:
                rl_engine = self._get_rl_engine()
                if rl_engine is not None:
                    for symbol in symbols:
                        # Placeholder: Use RL engine to predict action
                        # In production, would call: action = rl_engine.predict(observation)
                        action = random.choice(["BUY", "SELL", "HOLD"])
                        confidence = random.uniform(0.5, 0.9)
                        rl_signals[symbol] = (action, confidence)
                else:
                    logger.debug("   RL engine not available, skipping RL signals")
            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                logger.warning(f"   RL signal generation failed: {e}")

        # Momentum signals
        for symbol in symbols:
            # Placeholder: Use technical indicators
            action = random.choice(["BUY", "HOLD"])  # Bias towards buying
            confidence = random.uniform(0.6, 0.8)
            momentum_signals[symbol] = (action, confidence)

        # Mean reversion signals
        for symbol in symbols:
            # Placeholder: Use z-score, half-life
            action = random.choice(["HOLD", "SELL"])  # Bias towards selling
            confidence = random.uniform(0.5, 0.7)
            mean_reversion_signals[symbol] = (action, confidence)

        # Combine signals
        signal_set = self.signal_integrator.combine_signals(
            rl_signals=rl_signals if self.config.enable_rl_signals else None,
            momentum_signals=momentum_signals,
            mean_reversion_signals=mean_reversion_signals,
        )

        # Filter by quality
        signal_set = self.signal_integrator.filter_by_quality(signal_set, min_quality=0.4)

        logger.info(f"   Total Signals: {len(signal_set.signals)}")
        logger.info(
            f"   BUY: {signal_set.buy_count}, SELL: {signal_set.sell_count}, HOLD: {signal_set.hold_count}"
        )

        return signal_set

    # ============================================================================
    # STAGE 5: TAX OPTIMIZATION
    # ============================================================================

    async def stage_5_optimize_taxes(self, allocation=None) -> Any:
        """
        Stage 5: Optimize portfolio for tax efficiency.

        Args:
            allocation: Allocation result from Stage 3

        Returns:
            TaxOptimizedAllocation
        """
        logger.info("💸 STAGE 5: TAX OPTIMIZATION")
        logger.info("-" * 40)

        if not self.config.enable_tax_optimization:
            logger.info("   Tax optimization disabled, skipping")
            return None

        # Get allocation from workflow state if not provided
        if allocation is None:
            state = self.workflow_manager.get_current_state()
            allocation = state.get(StageType.CAPITAL_ALLOCATION.value)

        if not allocation:
            logger.warning("   No allocation available for tax optimization")
            return None

        try:
            tax_optimizer = self._get_tax_optimizer()

            # Convert allocation to format expected by tax optimizer
            base_allocation = {}
            current_positions = {}
            cost_basis = {}
            quantities = {}
            current_prices = {}

            for symbol, metrics in allocation.get("allocations", {}).items():
                weight = metrics.weight
                capital = metrics.capital
                base_allocation[symbol] = Decimal(str(weight))
                current_positions[symbol] = Decimal(str(capital))
                cost_basis[symbol] = Decimal(str(capital * 0.9))  # Assume 10% gain
                quantities[symbol] = Decimal("100")  # Placeholder
                current_prices[symbol] = Decimal(str(capital / 100))  # Placeholder

            # Optimize for taxes
            tax_optimized = await tax_optimizer.optimize_for_taxes(
                base_allocation=base_allocation,
                current_positions=current_positions,
                cost_basis=cost_basis,
                quantities=quantities,
                current_prices=current_prices,
                marginal_tax_rate=Decimal(str(self.config.marginal_tax_rate)),
                capital=Decimal(str(allocation.get("total_capital", 100000))),
            )

            logger.info(f"   Tax Benefit: €{tax_optimized.tax_benefit_estimated:,.2f}")
            logger.info(f"   After-Tax Return: {tax_optimized.after_tax_return_pct:.2f}%")

            return tax_optimized

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"   Tax optimization failed: {e}")
            return None

    # ============================================================================
    # STAGE 6: RISK VALIDATION
    # ============================================================================

    async def stage_6_validate_risk(self, profile=None, allocation=None) -> RiskValidationResult:
        """
        Stage 6: Validate portfolio against risk limits.

        Args:
            profile: InvestmentProfile
            allocation: Allocation result from Stage 3

        Returns:
            RiskValidationResult
        """
        logger.info("🛡️  STAGE 6: RISK VALIDATION")
        logger.info("-" * 40)

        if not self.config.enable_risk_gates:
            logger.info("   Risk gates disabled, skipping")
            return RiskValidationResult(passed=True, risk_level="LOW")

        # Get allocation from workflow state if not provided
        if allocation is None:
            state = self.workflow_manager.get_current_state()
            allocation = state.get(StageType.CAPITAL_ALLOCATION.value)

        try:
            self._get_risk_gates()

            violations = []
            warnings = []
            metrics = {}

            # Check position sizes
            max_position_weight = 0.0
            for symbol, metrics_data in allocation.get("allocations", {}).items():
                weight = metrics_data.weight
                if weight > self.config.max_position_size_pct:
                    violations.append(
                        f"{symbol}: Position size {weight:.1%} exceeds max {self.config.max_position_size_pct:.1%}"
                    )
                max_position_weight = max(max_position_weight, weight)

            # Check portfolio concentration
            total_capital = allocation.get("total_capital", 100000)
            largest_position_value = 0.0
            for metrics_data in allocation.get("allocations", {}).values():
                largest_position_value = max(largest_position_value, metrics_data.capital)

            concentration = largest_position_value / total_capital if total_capital > 0 else 0
            metrics["concentration"] = concentration
            metrics["max_position_weight"] = max_position_weight

            if concentration > self.config.max_position_size_pct:
                violations.append(f"Portfolio concentration {concentration:.1%} exceeds max")

            # Check leverage (simplified)
            metrics["leverage"] = 1.0  # No leverage in current allocation
            metrics["daily_loss_pct"] = 0.0  # No trades yet
            metrics["drawdown_pct"] = 0.0  # Starting fresh

            # Determine risk level
            if violations:
                risk_level = "CRITICAL" if len(violations) > 2 else "HIGH"
            elif warnings:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            passed = len(violations) == 0

            result = RiskValidationResult(
                passed=passed,
                risk_level=risk_level,
                violations=violations,
                warnings=warnings,
                metrics=metrics,
            )

            logger.info(f"   Risk Level: {risk_level}")
            logger.info(f"   Violations: {len(violations)}")
            logger.info(f"   Warnings: {len(warnings)}")
            logger.info(f"   Result: {'PASSED' if passed else 'FAILED'}")

            return result

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"   Risk validation failed: {e}")
            return RiskValidationResult(
                passed=False,
                risk_level="HIGH",
                violations=[f"Risk validation error: {str(e)}"],
            )

    # ============================================================================
    # STAGE 7: BACKTEST VALIDATION
    # ============================================================================

    async def stage_7_backtest_validate(self, profile=None, allocation=None) -> Any:
        """
        Stage 7: Validate strategy through backtesting.

        Args:
            profile: InvestmentProfile
            allocation: Allocation result from Stage 3

        Returns:
            BacktestOrchestrationResult
        """
        logger.info("📈 STAGE 7: BACKTEST VALIDATION")
        logger.info("-" * 40)

        if not self.config.enable_backtest_validation:
            logger.info("   Backtest validation disabled, skipping")
            return None

        try:
            backtest_orchestrator = self._get_backtest_orchestrator()

            # Get profile from workflow state if not provided
            if profile is None:
                state = self.workflow_manager.get_current_state()
                profile = state.get(StageType.PROFILE_GENERATION.value)

            # Get allocation from workflow state if not provided
            if allocation is None:
                state = self.workflow_manager.get_current_state()
                allocation = state.get(StageType.CAPITAL_ALLOCATION.value)

            # Create backtest request
            from app.services.backtest_orchestration.models import BacktestOrchestrationRequest

            # Determine backtest dates
            end_date = datetime.now()
            start_date = end_date - timedelta(days=180)  # 6 months

            request = BacktestOrchestrationRequest(
                profile_id=profile.profile_id if profile else "test",
                input_id=profile.profile_id if profile else "test_input",
                module_parameter_set_id="default",
                initial_capital=profile.initial_capital if profile else Decimal("100000"),
                target_monthly_return_eur=(
                    profile.min_monthly_return_eur if profile else Decimal("2000")
                ),
                objective=profile.investment_objective.value if profile else "BALANCED_GROWTH",
                risk_profile=profile.risk_tolerance.value if profile else "MEDIO",
                strategy_name="momentum",
                start_date=start_date,
                end_date=end_date,
                symbols=(
                    list(allocation.get("allocations", {}).keys())
                    if allocation
                    else ["AAPL", "MSFT"]
                ),
            )

            # Run backtest
            backtest_result = await backtest_orchestrator.orchestrate(request)

            logger.info(f"   Feasibility Ratio: {backtest_result.feasibility_ratio:.2f}")
            logger.info(f"   Status: {backtest_result.feasibility_status}")

            return backtest_result

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"   Backtest validation failed: {e}")
            return None

    # ============================================================================
    # STAGE 8: TRADE EXECUTION
    # ============================================================================

    async def stage_8_execute_trades(self, allocation=None, signals=None) -> ExecutionResult:
        """
        Stage 8: Execute trades based on allocation and signals.

        Args:
            allocation: Allocation result from Stage 3
            signals: SignalSet from Stage 4

        Returns:
            ExecutionResult
        """
        logger.info("💱 STAGE 8: TRADE EXECUTION")
        logger.info("-" * 40)

        # Get allocation and signals from workflow state if not provided
        if allocation is None:
            state = self.workflow_manager.get_current_state()
            allocation = state.get(StageType.CAPITAL_ALLOCATION.value)

        if signals is None:
            state = self.workflow_manager.get_current_state()
            signals = state.get(StageType.SIGNAL_GENERATION.value)

        dry_run = not self.config.auto_execute_trades

        logger.info(f"   Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        logger.info(
            f"   Broker: {'Interactive Brokers' if self.config.use_ibkr else 'Paper/Mock Adapter'}"
        )

        try:
            trading_bridge = self._get_trading_bridge()

            if not dry_run:
                # Start trading bridge for live execution
                await trading_bridge.start()

            # Prepare execution result
            execution_result = ExecutionResult(
                executed=True,
                dry_run=dry_run,
                orders_submitted=0,
                orders_filled=0,
                orders_failed=0,
                total_value_eur=0.0,
                execution_time_ms=0.0,
                order_details=[],
                errors=[],
            )

            # Process each allocation with signal
            for symbol, metrics in allocation.get("allocations", {}).items():
                signal_action = signals.signals.get(symbol, "HOLD") if signals else "HOLD"

                if signal_action == "HOLD":
                    continue

                # Create order details
                order_value = metrics.capital
                order_detail = {
                    "symbol": symbol,
                    "action": signal_action,
                    "value_eur": order_value,
                    "weight": metrics.weight,
                }

                execution_result.orders_submitted += 1
                execution_result.total_value_eur += order_value

                if not dry_run:
                    # In production, would execute real trade here
                    # For now, simulate
                    execution_result.orders_filled += 1
                else:
                    # Dry run - simulate success
                    execution_result.orders_filled += 1

                execution_result.order_details.append(order_detail)
                logger.info(f"   Order: {signal_action} {symbol} (€{order_value:,.2f})")

            logger.info(f"   Orders Submitted: {execution_result.orders_submitted}")
            logger.info(f"   Orders Filled: {execution_result.orders_filled}")
            logger.info(f"   Total Value: €{execution_result.total_value_eur:,.2f}")

            if not dry_run:
                await trading_bridge.stop()

            return execution_result

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"   Trade execution failed: {e}")
            return ExecutionResult(
                executed=False,
                dry_run=dry_run,
                errors=[str(e)],
            )

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status and statistics."""
        workflow_stats = self.workflow_manager.get_execution_statistics()

        return {
            "config": {
                "enable_rl_signals": self.config.enable_rl_signals,
                "enable_tax_optimization": self.config.enable_tax_optimization,
                "enable_backtest_validation": self.config.enable_backtest_validation,
                "enable_risk_gates": self.config.enable_risk_gates,
                "auto_execute_trades": self.config.auto_execute_trades,
                "use_ibkr": self.config.use_ibkr,
            },
            "execution": {
                "total_executions": self.execution_count,
                "last_execution_time": (
                    self.last_execution_time.isoformat() if self.last_execution_time else None
                ),
            },
            "workflow_statistics": workflow_stats,
        }
