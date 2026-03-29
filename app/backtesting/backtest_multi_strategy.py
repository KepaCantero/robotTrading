"""
Backtest Multi-Strategy Module - Multi-strategy backtest execution.

Extracted from comprehensive_backtest_runner.py for Single Responsibility.
Handles multi-strategy backtest execution:
- Profile to strategy mapping
- Capital allocation
- Concurrent strategy execution
- Portfolio-level metrics

Architecture:
- Integrates with ProfileStrategyMapper
- Uses MultiStrategyBacktester for execution
- Supports dynamic reallocation
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, ClassVar

logger = logging.getLogger(__name__)

from app.backtesting.engines.multi_strategy_engine import MultiStrategyBacktester
from app.backtesting.factories import StrategyFactory

if TYPE_CHECKING:
    from app.backtesting.core.memory_manager import AggressiveMemoryManager
    from app.backtesting.models import BacktestConfig


class BacktestMultiStrategyRunner:
    """
    Handles multi-strategy backtest execution.

    Provides methods for:
    - Profile to strategy mapping
    - Capital allocation across strategies
    - Concurrent strategy execution
    - Portfolio-level metrics calculation
    """

    # Strategy name mapping from YAML to factory names
    STRATEGY_NAME_MAP: ClassVar[dict] = {
        "momentum_modular": "modular_momentum",
        "mean_reversion_modular": "mean_reversion",
        "pairs_trading_modular": "pairs_trading",
        "dividend_screener": "modular_momentum",
        "portfolio_optimization": "modular_momentum",
        "dividend_predictor": "modular_momentum",
        "sector_rotation": "momentum",
        "ml_ensemble": "modular_momentum",
    }

    def __init__(
        self,
        backtest_config: BacktestConfig,
        memory_manager: AggressiveMemoryManager,
        raw_config: dict[str, Any],
        quotes: list,
    ):
        """
        Initialize BacktestMultiStrategyRunner.

        Args:
            backtest_config: Backtest configuration
            memory_manager: Memory manager for storing results
            raw_config: Raw YAML configuration
            quotes: Loaded market data quotes
        """
        self.backtest_config = backtest_config
        self.memory_manager = memory_manager
        self.raw_config = raw_config
        self.quotes = quotes

    def run_multi_strategy_backtest(
        self,
        thresholds_helper,
    ) -> list[dict[str, Any]]:
        """
        Execute multi-strategy backtest with capital allocation.

        Integrates with:
        - ProfileStrategyMapper for profile to strategy mapping
        - MultiStrategyBacktester for concurrent execution
        - MultiStrategyAllocationManager for capital distribution

        Returns:
            List of results with metrics per strategy and combined
        """
        logger.info("Running multi-strategy backtest...")

        try:
            # Step 1: Create InputProfile from configuration
            profile = self._create_input_profile_from_config()

            # Step 2: Create ProfileStrategyMapper
            from app.services.profile_driven_trading.profile_strategy_mapper import (
                ProfileStrategyMapper,
            )

            mapper = ProfileStrategyMapper()

            # Step 3: Get strategy mapping
            strategy_mapping = mapper.create_strategy_mapping(profile)

            logger.info(
                f"Profile mapped to {len(strategy_mapping.enabled_strategies)} strategies: "
                f"{', '.join(strategy_mapping.enabled_strategies)}"
            )

            # Step 4: Get capital allocation
            allocation_manager = mapper.get_capital_allocation(profile)
            capital_allocations = allocation_manager.allocate_capital()

            logger.info("Capital allocation:")
            for strategy_name, capital in capital_allocations.items():
                weight = float(capital / profile.capital_initial)
                logger.info(f"  {strategy_name}: ${capital:,.2f} ({weight:.1%})")

            # Step 5: Create strategy instances
            strategies = {}
            for strategy_name in strategy_mapping.enabled_strategies:
                try:
                    strategy_config = self._create_strategy_config_for_type(
                        strategy_name, strategy_mapping
                    )
                    strategy = StrategyFactory.create_strategy(strategy_config)
                    strategies[strategy_name] = strategy
                    logger.info(f"Created strategy instance: {strategy_name}")
                except Exception as e:
                    logger.error(f"Failed to create strategy {strategy_name}: {e}")
                    continue

            if not strategies:
                logger.error("No strategies could be created")
                return []

            # Step 6: Create MultiStrategyBacktester
            config_params = {
                "commission": self.backtest_config.commission_per_trade,
                "slippage": self.backtest_config.slippage_percentage,
                "stop_loss": self.backtest_config.stop_loss_percentage,
                "take_profit": self.backtest_config.take_profit_percentage,
                "max_position_size": self.backtest_config.max_position_size,
            }

            multi_strategy_backtester = MultiStrategyBacktester(
                allocation_manager=allocation_manager,
                strategies=strategies,
                config_params=config_params,
                enable_diagnostics=self.raw_config.get("diagnostics", {}).get("enabled", False),
                enable_dynamic_reallocation=self.raw_config.get("dynamic_reallocation", {}).get(
                    "enabled", True
                ),
            )

            # Step 7: Execute multi-strategy backtest
            start_date = datetime.strptime(self.raw_config["input"]["start_date"], "%Y-%m-%d")
            end_date = datetime.strptime(self.raw_config["input"]["end_date"], "%Y-%m-%d")

            logger.info(
                f"Running multi-strategy backtest from {start_date.date()} to {end_date.date()}"
            )

            consolidated_results = multi_strategy_backtester.run_multi_strategy_backtest(
                quotes=self.quotes, start_date=start_date, end_date=end_date
            )

            # Step 8: Convert results to expected format
            results = self._format_multi_strategy_results(
                consolidated_results=consolidated_results,
                strategy_mapping=strategy_mapping,
                profile=profile,
                thresholds_helper=thresholds_helper,
            )

            # Step 9: Save results
            for result in results:
                self.memory_manager.add_result(result)

            logger.info(f"Multi-strategy backtest completed: {len(results)} results generated")

            return results

        except Exception as e:
            logger.error(f"Error in multi-strategy backtest: {e}", exc_info=True)
            return []

    def _create_input_profile_from_config(self):
        """
        Create InputProfile from backtest configuration.

        Returns:
            InputProfile with parameters from config
        """
        from app.domain.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance

        initial_capital = Decimal(str(self.raw_config["input"]["initial_capital"]))

        objective_str = self.raw_config.get("profile", {}).get("objective", "balanced_growth")
        risk_str = self.raw_config.get("profile", {}).get("risk_tolerance", "medio")

        objective = ObjectivoInversion(objective_str)
        risk = RiskTolerance(risk_str)

        investment_horizon = self.raw_config.get("profile", {}).get("investment_horizon", 24)

        profile = InputProfile(
            capital_initial=initial_capital,
            objetivo_inversion=objective,
            risk_tolerance=risk,
            investment_horizon=investment_horizon,
        )

        logger.info(
            f"Created InputProfile: capital={initial_capital}, "
            f"objective={objective.value}, risk={risk.value}"
        )

        return profile

    def _create_strategy_config_for_type(
        self, strategy_name: str, strategy_mapping
    ) -> dict[str, Any]:
        """
        Create configuration for a specific strategy type.

        Args:
            strategy_name: Name of the strategy
            strategy_mapping: Strategy mapping from ProfileStrategyMapper

        Returns:
            Strategy configuration
        """
        mapped_strategy_name = self.STRATEGY_NAME_MAP.get(strategy_name, strategy_name)

        base_config = {
            "type": mapped_strategy_name,
            "symbols": self.raw_config["input"]["symbols"],
            "parameters": {
                "risk_profile": strategy_mapping.risk_profile,
                "leverage": strategy_mapping.leverage,
                "max_position_size": strategy_mapping.max_position_size,
                "max_sector_allocation": strategy_mapping.max_sector_allocation,
            },
            "thresholds": {
                "buy_threshold": 0.7,
                "sell_threshold": 0.3,
                "stop_loss": -0.05,
                "take_profit": 0.10,
            },
        }

        # Adjust based on strategy type
        if strategy_name == "momentum_modular":
            base_config.update(
                {
                    "preset": "custom",
                    "modules": self._get_filter_config(),
                    "presets": {
                        "custom": {
                            "combination_mode": "MAJORITY",
                            "min_confidence": 0.7,
                        }
                    },
                }
            )
        elif strategy_name == "mean_reversion_modular":
            base_config["parameters"].update(
                {
                    "lookback_period": 20,
                    "entry_threshold": 2.0,
                    "exit_threshold": 0.5,
                }
            )
        elif strategy_name == "dividend_screener":
            base_config["parameters"].update(
                {
                    "min_dividend_yield": 0.03,
                    "max_payout_ratio": 0.8,
                    "min_growth_rate": 0.05,
                }
            )

        return base_config

    def _get_filter_config(self) -> dict[str, Any]:
        """
        Get filter configuration from YAML config.

        Returns:
            Dictionary with filter configuration
        """
        filters_config = {}

        if "modules" in self.raw_config and "filters" in self.raw_config["modules"]:
            filters = self.raw_config["modules"]["filters"]

            for filter_name, filter_config in filters.items():
                if filter_config.get("enabled", False):
                    filter_params = {}
                    for param_name, param_config in filter_config.get("parameters", {}).items():
                        if "default" in param_config:
                            filter_params[param_name] = param_config["default"]

                    filters_config[filter_name] = {"enabled": True, **filter_params}

        return filters_config

    def _format_multi_strategy_results(
        self,
        consolidated_results: dict,
        strategy_mapping,
        profile,
        thresholds_helper,
    ) -> list[dict[str, Any]]:
        """
        Format multi-strategy backtest results.

        Args:
            consolidated_results: Consolidated results from MultiStrategyBacktester
            strategy_mapping: Strategy mapping from ProfileStrategyMapper
            profile: InputProfile used
            thresholds_helper: Helper to extract thresholds

        Returns:
            List of dictionaries with formatted results
        """
        results = []

        per_strategy = consolidated_results.get("per_strategy", {})
        combined = consolidated_results.get("combined", {})
        allocation_info = consolidated_results.get("allocation", {})

        # Create individual result for each strategy
        for strategy_name, strategy_metrics in per_strategy.items():
            result_dict = {
                "test_type": f"multi_strategy_{strategy_name}",
                "test_name": f"Multi-Strategy - {strategy_name}",
                "strategy_name": strategy_name,
                "modules_active": [strategy_name],
                "learning_engine": None,
                "thresholds": thresholds_helper({}),
                "total_pnl": (
                    strategy_metrics["final_capital"] - strategy_metrics["initial_capital"]
                ),
                "return_pct": strategy_metrics["total_return"],
                "win_rate": strategy_metrics.get("win_rate", 0.0),
                "sharpe_ratio": strategy_metrics.get("sharpe_ratio", 0.0),
                "max_drawdown": strategy_metrics.get("max_drawdown", 0.0),
                "total_trades": strategy_metrics.get("total_trades", 0),
                "avg_trade_pnl": (
                    (strategy_metrics["final_capital"] - strategy_metrics["initial_capital"])
                    / strategy_metrics.get("total_trades", 1)
                ),
                "final_capital": strategy_metrics["final_capital"],
                "allocated_capital": strategy_metrics["initial_capital"],
                "capital_weight": allocation_info.get(strategy_name, {}).get("weight", 0.0),
                "profile_objective": profile.objetivo_inversion.value,
                "profile_risk": profile.risk_tolerance.value,
                "profile_capital_tier": strategy_mapping.capital_tier,
            }

            results.append(result_dict)

        # Create combined result
        if combined:
            combined_result = {
                "test_type": "multi_strategy_combined",
                "test_name": "Multi-Strategy - Combined Portfolio",
                "strategy_name": "combined",
                "modules_active": strategy_mapping.enabled_strategies,
                "learning_engine": None,
                "thresholds": thresholds_helper({}),
                "total_pnl": (combined["total_final_capital"] - combined["total_initial_capital"]),
                "return_pct": combined["total_return"],
                "win_rate": 0.0,
                "sharpe_ratio": combined.get("weighted_sharpe", 0.0),
                "max_drawdown": combined.get("weighted_max_dd", 0.0),
                "total_trades": combined.get("total_trades", 0),
                "avg_trade_pnl": (
                    (combined["total_final_capital"] - combined["total_initial_capital"])
                    / combined.get("total_trades", 1)
                ),
                "final_capital": combined["total_final_capital"],
                "total_initial_capital": combined["total_initial_capital"],
                "num_strategies": len(per_strategy),
                "ensemble_mode": strategy_mapping.ensemble_mode,
                "ensemble_min_strategies": strategy_mapping.ensemble_min_strategies,
                "ensemble_confidence": strategy_mapping.ensemble_confidence_threshold,
                "profile_objective": profile.objetivo_inversion.value,
                "profile_risk": profile.risk_tolerance.value,
                "profile_capital_tier": strategy_mapping.capital_tier,
            }

            results.append(combined_result)

        return results
