"""
Select Strategy Use Case - FASE 6.6

This use case orchestrates intelligent strategy selection based on:
- User investment profile
- Market regime detection
- Bayesian optimization
- Walk-forward validation
- Performance scoring

The StrategySelector analyzes and ranks strategies to recommend the most
suitable configuration for a given investment profile and market conditions.

References:
    - /rules/05-architecture.md - Clean Architecture principles
    - /rules/02-type-hints.md - Type hint requirements
    - /rules/04-solid.md - SOLID principles
    - AUDIT_PLAN_COMPLETO.md - FASE 6: Strategy Selection
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol, TypeVar, Union

from pandas import DataFrame
from typing_extensions import TypeAlias

# Type alias for market data - accepts DataFrame or dict with OHLCV data
MarketDataFrame: TypeAlias = DataFrame
MarketDict: TypeAlias = dict[str, Union[list[float], list[int], list[str]]]
MarketData: TypeAlias = Union[MarketDataFrame, MarketDict]


class StrategyProtocol(Protocol):
    """
    Protocol for trading strategies that can be created by factory.

    This protocol defines the interface that all trading strategies must implement.
    It uses structural subtyping (duck typing) - any class with these methods
    will satisfy the protocol, without explicit inheritance.

    Methods:
        generate_signals: Generate trading signals from market data
        get_parameters: Get current strategy parameters

    Example:
        ```python
        class MomentumStrategy:
            def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
                # Calculate momentum indicators
                return signals

            def get_parameters(self) -> dict[str, object]:
                return {"lookback": 20, "threshold": 1.5}
        ```
    """

    def generate_signals(self, data: MarketDataFrame) -> MarketDataFrame:
        """
        Generate trading signals from market data.

        Args:
            data: Historical market data with OHLCV columns

        Returns:
            DataFrame with signal columns added
        """
        ...

    def get_parameters(self) -> dict[str, object]:
        """
        Get current strategy parameters.

        Returns:
            Dictionary mapping parameter names to values
        """
        ...


class StrategyFactoryType(Protocol):
    """
    Protocol for strategy factory functions.

    A strategy factory is a callable that creates strategy instances
    from a parameter dictionary. This protocol allows type-safe
    dependency injection of strategy factories.

    Example:
        ```python
        def create_momentum_strategy(params: dict[str, object]) -> StrategyProtocol:
            return MomentumStrategy(
                lookback=params["lookback"],
                threshold=params["threshold"]
            )
        ```
    """

    def __call__(self, params: dict[str, object]) -> StrategyProtocol:
        """
        Create a strategy instance from parameters.

        Args:
            params: Strategy parameters

        Returns:
            Strategy instance implementing StrategyProtocol
        """
        ...


# Type alias for strategy factory callable
StrategyFactory = Callable[[dict[str, object]], StrategyProtocol]


# Type alias for strategy parameters
# Uses object as value type to accommodate int, float, str, Decimal, etc.
StrategyParameters = dict[str, object]


# Protocol for walk-forward validation results
class WalkForwardResultProtocol(Protocol):
    """Protocol for walk-forward validation results."""

    consistency_score: Decimal
    num_periods: int

    def get_degradation_summary(self) -> dict[str, object]:
        ...

    @property
    def os_performance(self) -> dict[str, object]:
        ...

    @property
    def is_performance(self) -> dict[str, object]:
        ...


# Type variable for generic strategy operations
S = TypeVar("S", bound=StrategyProtocol)

from ...backtesting.validation.models import WalkForwardConfig
from ...backtesting.validation.walk_forward import WalkForwardValidator
from ...core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from ...optimization.parameter.base_optimizer import OptimizationConfig
from ...optimization.parameter.bayesian_optimizer import BayesianOptimizer
from ...optimization.parameter.models import ParameterGrid, ParameterRange, ParameterType
from ...services.profile_driven_trading.profile_strategy_mapper import (
    ProfileStrategyMapper,
    StrategyMapping,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StrategyConfiguration:
    """
    Configuration for a strategy candidate.

    Attributes:
        strategy_name: Name of the strategy
        parameters: Strategy parameters (uses object to accommodate various types)
        weights: Capital allocation weights
        expected_return: Expected annual return
        expected_risk: Expected risk (volatility)
        sharpe_ratio: Risk-adjusted return metric
        max_drawdown: Maximum expected drawdown
        win_rate: Expected win rate
        suitability_score: Profile matching score (0-100)
        validation_score: Walk-forward validation score (0-100)
        total_score: Combined score (0-100)
    """

    strategy_name: str
    parameters: StrategyParameters = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)
    expected_return: Decimal = field(default=Decimal("0"))
    expected_risk: Decimal = field(default=Decimal("0"))
    sharpe_ratio: Decimal = field(default=Decimal("0"))
    max_drawdown: Decimal = field(default=Decimal("0"))
    win_rate: Decimal = field(default=Decimal("0"))
    suitability_score: Decimal = field(default=Decimal("0"))
    validation_score: Decimal = field(default=Decimal("0"))
    total_score: Decimal = field(default=Decimal("0"))

    def to_dict(self) -> dict[str, object]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with all configuration fields as JSON-serializable types
        """
        return {
            "strategy_name": self.strategy_name,
            "parameters": self.parameters,
            "weights": self.weights,
            "expected_return": float(self.expected_return),
            "expected_risk": float(self.expected_risk),
            "sharpe_ratio": float(self.sharpe_ratio),
            "max_drawdown": float(self.max_drawdown),
            "win_rate": float(self.win_rate),
            "suitability_score": float(self.suitability_score),
            "validation_score": float(self.validation_score),
            "total_score": float(self.total_score),
        }


@dataclass
class StrategySelectionCriteria:
    """
    Criteria for scoring and ranking strategies.

    Attributes:
        return_weight: Weight for expected return in scoring (0-1)
        risk_weight: Weight for risk in scoring (0-1)
        sharpe_weight: Weight for Sharpe ratio in scoring (0-1)
        validation_weight: Weight for validation score in scoring (0-1)
        suitability_weight: Weight for profile matching in scoring (0-1)
        min_sharpe_ratio: Minimum acceptable Sharpe ratio
        max_drawdown_limit: Maximum acceptable drawdown
        min_validation_score: Minimum validation score (0-100)
        require_walk_forward: Whether to require walk-forward validation
    """

    return_weight: float = 0.25
    risk_weight: float = 0.20
    sharpe_weight: float = 0.25
    validation_weight: float = 0.20
    suitability_weight: float = 0.10
    min_sharpe_ratio: Decimal = Decimal("0.5")
    max_drawdown_limit: Decimal = Decimal("0.30")
    min_validation_score: Decimal = Decimal("60")
    require_walk_forward: bool = True

    def validate(self) -> None:
        """Validate criteria weights sum to approximately 1.0."""
        total = (
            self.return_weight
            + self.risk_weight
            + self.sharpe_weight
            + self.validation_weight
            + self.suitability_weight
        )
        if not 0.9 <= total <= 1.1:
            raise ValueError(f"Criteria weights must sum to ~1.0, got {total:.2f}")


@dataclass
class StrategySelectionResult:
    """
    Result of strategy selection process.

    Attributes:
        selected_strategy: Best matching strategy configuration
        alternative_strategies: List of alternative strategies (ranked)
        selection_timestamp: When selection was performed
        selection_criteria: Criteria used for selection
        optimization_details: Details from Bayesian optimization
        validation_details: Details from walk-forward validation
    """

    selected_strategy: StrategyConfiguration
    alternative_strategies: list[StrategyConfiguration]
    selection_timestamp: datetime
    selection_criteria: StrategySelectionCriteria
    optimization_details: dict[str, object] = field(default_factory=dict)
    validation_details: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with all result fields as JSON-serializable types
        """
        return {
            "selected_strategy": self.selected_strategy.to_dict(),
            "alternative_strategies": [
                s.to_dict() for s in self.alternative_strategies[:5]
            ],  # Top 5 alternatives
            "selection_timestamp": self.selection_timestamp.isoformat(),
            "selection_criteria": {
                "return_weight": self.selection_criteria.return_weight,
                "risk_weight": self.selection_criteria.risk_weight,
                "sharpe_weight": self.selection_criteria.sharpe_weight,
                "validation_weight": self.selection_criteria.validation_weight,
                "suitability_weight": self.selection_criteria.suitability_weight,
            },
            "optimization_details": self.optimization_details,
            "validation_details": self.validation_details,
        }


class StrategySelector:
    """
    Selects optimal strategy based on profile and validation.

    The StrategySelector integrates multiple components:
    - ProfileStrategyMapper: Maps profile to candidate strategies
    - BayesianOptimizer: Optimizes strategy parameters
    - WalkForwardValidator: Validates out-of-sample performance
    - Scoring system: Ranks strategies by multiple criteria

    This is the core business logic for strategy selection.
    """

    def __init__(
        self,
        profile_mapper: ProfileStrategyMapper | None = None,
        optimizer: BayesianOptimizer | None = None,
        validator: WalkForwardValidator | None = None,
    ):
        """
        Initialize strategy selector with dependencies.

        Args:
            profile_mapper: Mapper for profile to strategies
            optimizer: Bayesian optimizer for parameter tuning
            validator: Walk-forward validator for robust testing
        """
        self._profile_mapper = profile_mapper or ProfileStrategyMapper()
        self._optimizer = optimizer
        self._validator = validator or WalkForwardValidator()

        logger.info("StrategySelector initialized")

    def select_strategy(
        self,
        profile: InputProfile,
        market_data: MarketData | None = None,
        criteria: StrategySelectionCriteria | None = None,
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> StrategySelectionResult:
        """
        Select optimal strategy for given profile and market conditions.

        Process:
        1. Map profile to candidate strategies
        2. Optimize parameters for each candidate
        3. Validate with walk-forward analysis
        4. Score and rank strategies
        5. Select best matching strategy

        Args:
            profile: User investment profile
            market_data: Historical market data for validation
            criteria: Selection criteria (uses defaults if None)
            progress_callback: Optional callback for progress updates

        Returns:
            StrategySelectionResult with selected strategy and alternatives

        Raises:
            ValueError: If profile is invalid or no strategies available
        """
        # Validate criteria
        if criteria is None:
            criteria = self._get_default_criteria(profile)
        criteria.validate()

        logger.info(
            f"Selecting strategy for profile: "
            f"objective={profile.objetivo_inversion.value}, "
            f"risk={profile.risk_tolerance.value}"
        )

        # Step 1: Map profile to candidate strategies
        if progress_callback:
            progress_callback("Mapping profile to strategies...", 0.1)

        strategy_mapping = self._profile_mapper.create_strategy_mapping(profile)
        candidate_strategies = strategy_mapping.enabled_strategies

        if not candidate_strategies:
            raise ValueError("No candidate strategies found for profile")

        logger.info(f"Found {len(candidate_strategies)} candidate strategies")

        # Step 2: Analyze each candidate strategy
        configurations: list[StrategyConfiguration] = []

        for i, strategy_name in enumerate(candidate_strategies):
            progress_step = 0.1 + (0.7 * (i + 1) / len(candidate_strategies))

            if progress_callback:
                progress_callback(f"Analyzing {strategy_name}...", progress_step)

            try:
                config = self._analyze_strategy(
                    strategy_name=strategy_name,
                    profile=profile,
                    strategy_mapping=strategy_mapping,
                    market_data=market_data,
                    criteria=criteria,
                )
                configurations.append(config)

            except (ValueError, TypeError, AttributeError, Exception) as e:
                logger.error(
                    f"Error analyzing strategy {strategy_name}: {e}",
                    exc_info=True,
                )
                # Create failed configuration with zero scores
                configurations.append(
                    StrategyConfiguration(
                        strategy_name=strategy_name,
                        total_score=Decimal("0"),
                        validation_score=Decimal("0"),
                    )
                )

        # Step 3: Rank strategies by total score
        if progress_callback:
            progress_callback("Ranking strategies...", 0.9)

        configurations.sort(key=lambda c: c.total_score, reverse=True)

        # Step 4: Select best strategy
        selected = configurations[0]
        alternatives = configurations[1:6]  # Top 5 alternatives

        logger.info(
            f"Selected strategy: {selected.strategy_name} " f"(score: {selected.total_score:.1f})"
        )

        if progress_callback:
            progress_callback("Strategy selection complete", 1.0)

        # Step 5: Build result
        return StrategySelectionResult(
            selected_strategy=selected,
            alternative_strategies=alternatives,
            selection_timestamp=datetime.now(),
            selection_criteria=criteria,
        )

    def _analyze_strategy(
        self,
        strategy_name: str,
        profile: InputProfile,
        strategy_mapping: StrategyMapping,
        market_data: MarketData | None,
        criteria: StrategySelectionCriteria,
    ) -> StrategyConfiguration:
        """
        Analyze a single strategy candidate.

        Args:
            strategy_name: Name of the strategy to analyze
            profile: User investment profile
            strategy_mapping: Strategy mapping from profile
            market_data: Market data for validation
            criteria: Selection criteria

        Returns:
            StrategyConfiguration with scores
        """
        # Step 1: Calculate suitability score
        suitability = self._calculate_suitability_score(strategy_name, profile, strategy_mapping)

        # Step 2: Optimize parameters (if optimizer available)
        optimized_params: StrategyParameters = {}
        optimization_metrics: dict[str, object] = {}

        if self._optimizer and market_data is not None:
            try:
                optimized_params, optimization_metrics = self._optimize_parameters(
                    strategy_name=strategy_name,
                    profile=profile,
                    market_data=market_data,
                )
            except (ValueError, TypeError, RuntimeError) as e:
                logger.warning(
                    f"Parameter optimization failed for {strategy_name}: {e}",
                    exc_info=True,
                )
                # Use default parameters from mapping
                optimized_params = {}
        else:
            logger.debug(f"No optimizer or market data, using defaults for {strategy_name}")

        # Step 3: Validate strategy (if validator available and required)
        validation_score = Decimal("100")  # Default if no validation
        validation_details: dict[str, object] = {}

        if criteria.require_walk_forward and self._validator and market_data is not None:
            try:
                validation_score, validation_details = self._validate_strategy(
                    strategy_name=strategy_name,
                    parameters=optimized_params,
                    market_data=market_data,
                )
            except (ValueError, TypeError, RuntimeError) as e:
                logger.warning(
                    f"Validation failed for {strategy_name}: {e}",
                    exc_info=True,
                )
                validation_score = Decimal("50")  # Mid score on validation failure

        # Step 4: Estimate performance metrics
        performance = self._estimate_performance(
            strategy_name=strategy_name,
            profile=profile,
            optimization_metrics=optimization_metrics,
            validation_details=validation_details,
        )

        # Step 5: Calculate total score
        total_score = self._calculate_total_score(
            suitability=suitability,
            validation_score=validation_score,
            performance=performance,
            criteria=criteria,
        )

        # Get strategy weights
        weights = strategy_mapping.strategy_weights.get(strategy_name, 1.0)

        # Create configuration
        return StrategyConfiguration(
            strategy_name=strategy_name,
            parameters=optimized_params,
            weights={strategy_name: weights},
            expected_return=performance.get("expected_return", Decimal("0")),
            expected_risk=performance.get("expected_risk", Decimal("0")),
            sharpe_ratio=performance.get("sharpe_ratio", Decimal("0")),
            max_drawdown=performance.get("max_drawdown", Decimal("0")),
            win_rate=performance.get("win_rate", Decimal("0")),
            suitability_score=suitability,
            validation_score=validation_score,
            total_score=total_score,
        )

    def _calculate_suitability_score(
        self,
        strategy_name: str,
        profile: InputProfile,
        strategy_mapping: StrategyMapping,
    ) -> Decimal:
        """
        Calculate how well a strategy matches the user profile.

        Args:
            strategy_name: Name of the strategy
            profile: User investment profile
            strategy_mapping: Strategy mapping from profile

        Returns:
            Suitability score (0-100)
        """
        score = Decimal("50")  # Base score

        # Check if strategy is enabled for this profile
        if strategy_name not in strategy_mapping.enabled_strategies:
            return Decimal("0")  # Not suitable

        # Adjust for risk tolerance
        score += self._adjust_score_for_risk_tolerance(strategy_name, profile.risk_tolerance)

        # Adjust for investment objective
        score += self._adjust_score_for_objective(strategy_name, profile.objetivo_inversion)

        # Adjust for capital tier
        score += self._adjust_score_for_capital(strategy_name, profile.capital_flag)

        # Clamp to valid range
        return max(Decimal("0"), min(Decimal("100"), score))

    def _adjust_score_for_risk_tolerance(
        self, strategy_name: str, risk_tolerance: RiskTolerance
    ) -> Decimal:
        """
        Adjust suitability score based on risk tolerance.

        Args:
            strategy_name: Name of the strategy
            risk_tolerance: User's risk tolerance level

        Returns:
            Score adjustment (can be negative)
        """
        if risk_tolerance == RiskTolerance.BAJO:
            # Conservative profiles prefer defensive strategies
            defensive_strategies = ["dividend_screener", "pairs_trading_modular"]
            if strategy_name in defensive_strategies:
                return Decimal("20")
            elif "momentum" in strategy_name:
                return Decimal("-10")
        elif risk_tolerance == RiskTolerance.ALTO:
            # Aggressive profiles prefer growth strategies
            aggressive_strategies = ["momentum_modular", "trend_following"]
            if strategy_name in aggressive_strategies:
                return Decimal("20")
            elif "dividend" in strategy_name:
                return Decimal("-10")

        return Decimal("0")

    def _adjust_score_for_objective(
        self, strategy_name: str, objective: ObjectivoInversion
    ) -> Decimal:
        """
        Adjust suitability score based on investment objective.

        Args:
            strategy_name: Name of the strategy
            objective: User's investment objective

        Returns:
            Score adjustment (can be negative)
        """
        if objective == ObjectivoInversion.MAXIMIZAR_DIVIDENDOS:
            if "dividend" in strategy_name:
                return Decimal("30")
        elif objective == ObjectivoInversion.MAXIMIZAR_CAPITAL:
            if "momentum" in strategy_name or "trend" in strategy_name:
                return Decimal("20")

        return Decimal("0")

    def _adjust_score_for_capital(self, strategy_name: str, capital_flag: str) -> Decimal:
        """
        Adjust suitability score based on capital tier.

        Args:
            strategy_name: Name of the strategy
            capital_flag: Capital tier flag (small/medium/large)

        Returns:
            Score adjustment (can be negative)
        """
        if capital_flag == "small":
            # Small capital needs simpler strategies
            if "ensemble" in strategy_name or "ml" in strategy_name:
                return Decimal("-15")
        elif capital_flag == "large":
            # Large capital can use complex strategies
            if "ensemble" in strategy_name or "ml" in strategy_name:
                return Decimal("15")

        return Decimal("0")

    def _optimize_parameters(
        self,
        strategy_name: str,
        profile: InputProfile,
        market_data: MarketData,
    ) -> tuple[StrategyParameters, dict[str, object]]:
        """
        Optimize strategy parameters using Bayesian optimization with backtest integration.

        Args:
            strategy_name: Name of the strategy
            profile: User investment profile
            market_data: Market data for optimization

        Returns:
            Tuple of (optimized_parameters, optimization_metrics)
        """
        if self._optimizer is None:
            return {}, {}

        # Define parameter search space
        param_grid = self._get_parameter_grid(strategy_name, profile)

        # Define optimization config
        opt_config = OptimizationConfig(
            max_iterations=50,
            metric="sharpe_ratio",
            maximize=True,
            random_seed=42,
        )

        # Create temporary optimizer for this strategy
        optimizer = BayesianOptimizer(config=opt_config, n_trials=50)

        # Define objective function with actual backtest integration
        def objective(params: StrategyParameters) -> float:
            """
            Objective function for Bayesian optimization.

            Evaluates strategy parameters by running a backtest and returning
            the Sharpe ratio for optimization.

            Args:
                params: Strategy parameters to evaluate

            Returns:
                float: Sharpe ratio from backtest (higher is better)
            """
            try:
                # Import backtesting components
                from decimal import Decimal

                from ....backtesting.engine import SimpleBacktester
                from ....backtesting.models import BacktestConfig
                from ....strategies.registry import StrategyRegistry

                # Convert market_data to DataFrame if needed
                if isinstance(market_data, dict):
                    import pandas as pd

                    market_df = pd.DataFrame(market_data)
                elif isinstance(market_data, DataFrame):
                    market_df = market_data
                else:
                    logger.warning(f"Unsupported market_data type: {type(market_data)}")
                    return 0.0

                # Validate we have data
                if market_df.empty or len(market_df) < 100:
                    logger.warning("Insufficient market data for backtest")
                    return 0.0

                # Create strategy instance
                registry = StrategyRegistry()
                try:
                    strategy = registry.load_strategy(strategy_name, dict(params))
                except (ValueError, KeyError, TypeError) as e:
                    logger.debug(f"Could not load strategy {strategy_name}: {e}")
                    # Fallback: create simple mock result based on parameter heuristics
                    return self._heuristic_objective(params, strategy_name)

                # Generate signals from strategy
                try:
                    signals_df = strategy.generate_signals(market_df)
                except Exception as e:
                    logger.debug(f"Could not generate signals: {e}")
                    return self._heuristic_objective(params, strategy_name)

                # Convert signals DataFrame to Signal objects
                signals = self._convert_df_to_signals(signals_df, strategy_name)

                if not signals:
                    logger.debug("No signals generated from strategy")
                    return self._heuristic_objective(params, strategy_name)

                # Create backtest config
                backtest_config = BacktestConfig(
                    strategy_name=strategy_name,
                    initial_capital=Decimal("100000"),
                    commission_per_trade=Decimal("1.0"),
                    slippage_percentage=Decimal("0.1"),
                    risk_free_rate=Decimal("0.02"),
                )

                # Create market data list for backtester
                market_data_list = self._convert_df_to_market_data(market_df)

                if not market_data_list:
                    return self._heuristic_objective(params, strategy_name)

                # Run backtest
                backtester = SimpleBacktester(
                    config=backtest_config,
                    strategy=strategy,
                    strategy_name=strategy_name,
                )

                result = backtester.run_backtest(
                    market_data=market_data_list,
                    signals=signals,
                )

                # Extract Sharpe ratio
                if result.performance and result.performance.sharpe_ratio is not None:
                    sharpe = float(result.performance.sharpe_ratio)
                    logger.debug(f"Backtest Sharpe: {sharpe:.3f} for params: {params}")
                    return max(0.0, sharpe)  # Ensure non-negative
                else:
                    # Fallback to total return if Sharpe unavailable
                    if result.total_return:
                        return max(0.0, float(result.total_return) / 100.0)

                return 0.0

            except (ImportError, ValueError, TypeError, KeyError, AttributeError) as e:
                logger.debug(f"Backtest objective failed: {e}")
                # Fallback to heuristic score
                return self._heuristic_objective(params, strategy_name)
            except Exception as e:
                logger.warning(f"Unexpected error in objective function: {e}")
                return 0.0

        # Run optimization (synchronous wrapper)
        import asyncio

        try:
            asyncio.get_running_loop()
            # If we're already in an async context, we can't use asyncio.run()
            # Create a task and let the caller handle it
            raise RuntimeError(
                "Cannot run async optimization from within an async context. "
                "Use 'await' instead."
            )
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            pass

        result = asyncio.run(optimizer.optimize(objective, param_grid))

        return result.best_params, {"trials": len(result.all_trials)}

    def _heuristic_objective(self, params: StrategyParameters, strategy_name: str) -> float:
        """
        Calculate heuristic objective score when backtest is unavailable.

        Provides a reasonable score based on parameter reasonableness
        for the given strategy type, following Ilmanen's rules.

        Args:
            params: Strategy parameters to evaluate
            strategy_name: Name of the strategy

        Returns:
            float: Heuristic score (0-2 range)
        """
        score = 0.5

        # FX Carry Trade specific heuristics (Ilmanen Rule 12.9)
        if "carry" in strategy_name or "fx_carry" in strategy_name:
            if "interest_rate_diff" in params:
                diff = params["interest_rate_diff"]
                if isinstance(diff, (int, float)) and diff > 0.01:
                    score += 0.3
            if "forward_premium" in params:
                premium = params["forward_premium"]
                if isinstance(premium, (int, float)) and abs(premium) < 0.05:
                    score += 0.2

        # Momentum specific heuristics
        elif "momentum" in strategy_name:
            if "lookback" in params:
                lookback_val = params["lookback"]
                if isinstance(lookback_val, (int, float)):
                    # Prefer medium lookback periods (20-60 days)
                    if 20 <= lookback_val <= 60:
                        score += 0.3
                    elif 10 <= lookback_val <= 90:
                        score += 0.1
            if "threshold" in params:
                threshold_val = params["threshold"]
                if isinstance(threshold_val, (int, float)):
                    if 0.5 <= threshold_val <= 2.0:
                        score += 0.2
            if "volatility_filter" in params:
                vol_filter = params["volatility_filter"]
                if isinstance(vol_filter, bool) and vol_filter:
                    score += 0.1

        # Mean reversion specific heuristics
        elif "mean_reversion" in strategy_name or "reversion" in strategy_name:
            if "lookback" in params:
                lookback_val = params["lookback"]
                if isinstance(lookback_val, (int, float)):
                    # Prefer shorter lookback for mean reversion (5-30 days)
                    if 5 <= lookback_val <= 30:
                        score += 0.3
            if "entry_threshold" in params:
                entry_val = params["entry_threshold"]
                if isinstance(entry_val, (int, float)):
                    if 1.5 <= entry_val <= 3.0:
                        score += 0.2

        # Pairs trading specific heuristics
        elif "pairs" in strategy_name:
            if "lookback" in params:
                lookback_val = params["lookback"]
                if isinstance(lookback_val, (int, float)):
                    if 20 <= lookback_val <= 60:
                        score += 0.3
            if "entry_zscore" in params:
                entry_z = params["entry_zscore"]
                if isinstance(entry_z, (int, float)):
                    if 1.5 <= entry_z <= 3.0:
                        score += 0.2

        # Multi-factor specific heuristics
        elif "multi_factor" in strategy_name or "factor" in strategy_name:
            if "lookback" in params:
                lookback_val = params["lookback"]
                if isinstance(lookback_val, (int, float)):
                    if 50 <= lookback_val <= 252:
                        score += 0.3
            if "rebalance_frequency" in params:
                rebalance = params["rebalance_frequency"]
                if isinstance(rebalance, (int, float)):
                    if 5 <= rebalance <= 30:
                        score += 0.2

        # Dividend specific heuristics
        elif "dividend" in strategy_name:
            if "min_dividend_yield" in params:
                min_yield = params["min_dividend_yield"]
                if isinstance(min_yield, (int, float)):
                    if 0.02 <= min_yield <= 0.08:
                        score += 0.3
            if "payout_ratio_max" in params:
                payout = params["payout_ratio_max"]
                if isinstance(payout, (int, float)):
                    if 0.3 <= payout <= 0.8:
                        score += 0.2

        # Low volatility specific heuristics
        elif "low_volatility" in strategy_name:
            if "volatility_percentile" in params:
                vol_pct = params["volatility_percentile"]
                if isinstance(vol_pct, (int, float)):
                    if vol_pct <= 0.3:
                        score += 0.3
            if "max_beta" in params:
                beta = params["max_beta"]
                if isinstance(beta, (int, float)):
                    if 0.5 <= beta <= 1.0:
                        score += 0.2

        # Default heuristics
        else:
            if "lookback" in params:
                lookback_val = params["lookback"]
                if isinstance(lookback_val, (int, float)):
                    if 20 <= lookback_val <= 50:
                        score += 0.2
            if "threshold" in params:
                threshold_val = params["threshold"]
                if isinstance(threshold_val, (int, float)):
                    if 0.5 <= threshold_val <= 2.0:
                        score += 0.2

        return max(0.0, min(2.0, score))

    def _convert_df_to_signals(self, signals_df: MarketDataFrame, strategy_name: str) -> list[Any]:
        """
        Convert signals DataFrame to Signal objects for backtesting.

        Args:
            signals_df: DataFrame with signals from strategy
            strategy_name: Name of the strategy

        Returns:
            List of Signal objects
        """
        from datetime import datetime
        from decimal import Decimal

        from app.models.signal import (  # pylint: disable=import-error
            Signal,
            SignalSource,
            SignalStrength,
            SignalType,
        )

        signals = []

        # Check if DataFrame has signal columns
        signal_cols = [col for col in signals_df.columns if "signal" in col.lower()]

        if not signal_cols:
            # Try to infer signals from price action
            if "close" in signals_df.columns:
                signals_df = signals_df.copy()
                signals_df["signal"] = 0
                signals_df.loc[signals_df["close"].pct_change() > 0.02, "signal"] = 1
                signals_df.loc[signals_df["close"].pct_change() < -0.02, "signal"] = -1
                signal_cols = ["signal"]

        for col in signal_cols:
            for idx, row in signals_df.iterrows():
                signal_value = row.get(col, 0)

                # Skip neutral signals
                if signal_value == 0:
                    continue

                # Determine signal type
                if signal_value > 0:
                    signal_type = SignalType.BUY
                else:
                    signal_type = SignalType.SELL

                # Get timestamp
                if hasattr(idx, "to_pydatetime"):
                    timestamp = idx.to_pydatetime()
                elif isinstance(idx, datetime):
                    timestamp = idx
                else:
                    continue

                # Get symbol from DataFrame or use default
                symbol = row.get("symbol", "DEFAULT")

                # Get confidence if available
                confidence = row.get("confidence", 0.7)
                if isinstance(confidence, Decimal):
                    confidence = float(confidence)
                confidence = max(0.0, min(1.0, abs(float(confidence))))

                # Create Signal object
                signal = Signal(
                    symbol=symbol,
                    signal_type=signal_type,
                    strength=SignalStrength.MODERATE,
                    source=SignalSource.TECHNICAL,  # Use valid enum value
                    timestamp=timestamp,
                    confidence=confidence * 100,  # Convert to 0-100 scale
                    liquidity_score=50.0,  # Default value
                    priority_score=50.0,  # Default value
                    price=Decimal("100.00"),  # Default placeholder price
                    volume=Decimal("1000"),  # Default placeholder volume
                    metadata={"strategy": strategy_name, "params": {}},
                )

                signals.append(signal)

        return signals

    def _convert_df_to_market_data(self, market_df: MarketDataFrame) -> list[Any]:
        """
        Convert market DataFrame to MarketData objects for backtesting.

        Args:
            market_df: DataFrame with OHLCV data

        Returns:
            List of MarketData or Quote objects
        """
        from datetime import datetime
        from decimal import Decimal

        from app.models.order import MarketData  # pylint: disable=import-error

        market_data_list = []

        required_cols = ["close"]
        if not all(col in market_df.columns for col in required_cols):
            logger.warning("Market DataFrame missing required columns")
            return []

        for idx, row in market_df.iterrows():
            try:
                # Get timestamp
                if hasattr(idx, "to_pydatetime"):
                    timestamp = idx.to_pydatetime()
                elif isinstance(idx, datetime):
                    timestamp = idx
                else:
                    continue

                # Get symbol
                symbol = row.get("symbol", "DEFAULT")

                # Get price data
                open_price = Decimal(str(row.get("open", row.get("close", 0))))
                high_price = Decimal(str(row.get("high", row.get("close", 0))))
                low_price = Decimal(str(row.get("low", row.get("close", 0))))
                close_price = Decimal(str(row.get("close", 0)))
                volume = Decimal(str(row.get("volume", 0)))
                bid = Decimal(str(row.get("bid", 0))) if row.get("bid") else None
                ask = Decimal(str(row.get("ask", 0))) if row.get("ask") else None

                # Create MarketData object
                md = MarketData(
                    symbol=symbol,
                    timestamp=timestamp,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume,
                    bid=bid,
                    ask=ask,
                )

                market_data_list.append(md)

            except (ValueError, TypeError, KeyError) as e:
                logger.debug(f"Could not convert row to MarketData: {e}")
                continue

        return market_data_list

    async def _optimize_parameters_async(
        self,
        strategy_name: str,
        profile: InputProfile,
        market_data: MarketData,
    ) -> tuple[StrategyParameters, dict[str, object]]:
        """
        Async version of parameter optimization for use in async contexts.

        This method should be called when already in an async context instead
        of using the sync _optimize_parameters which uses asyncio.run().

        Args:
            strategy_name: Name of the strategy
            profile: User investment profile
            market_data: Market data for optimization

        Returns:
            Tuple of (optimized_parameters, optimization_metrics)
        """
        if self._optimizer is None:
            return {}, {}

        # Define parameter search space
        param_grid = self._get_parameter_grid(strategy_name, profile)

        # Define optimization config
        opt_config = OptimizationConfig(
            max_iterations=50,
            metric="sharpe_ratio",
            maximize=True,
            random_seed=42,
        )

        # Create temporary optimizer for this strategy
        optimizer = BayesianOptimizer(config=opt_config, n_trials=50)

        # Define objective function with actual backtest integration
        def objective(params: StrategyParameters) -> float:
            """
            Objective function for Bayesian optimization (async version).

            Evaluates strategy parameters by running a backtest and returning
            the Sharpe ratio for optimization.

            Args:
                params: Strategy parameters to evaluate

            Returns:
                float: Sharpe ratio from backtest (higher is better)
            """
            try:
                # Import backtesting components
                from decimal import Decimal

                from ....backtesting.engine import SimpleBacktester
                from ....backtesting.models import BacktestConfig
                from ....strategies.registry import StrategyRegistry

                # Convert market_data to DataFrame if needed
                if isinstance(market_data, dict):
                    import pandas as pd

                    market_df = pd.DataFrame(market_data)
                elif isinstance(market_data, DataFrame):
                    market_df = market_data
                else:
                    logger.warning(f"Unsupported market_data type: {type(market_data)}")
                    return 0.0

                # Validate we have data
                if market_df.empty or len(market_df) < 100:
                    logger.warning("Insufficient market data for backtest")
                    return 0.0

                # Create strategy instance
                registry = StrategyRegistry()
                try:
                    strategy = registry.load_strategy(strategy_name, dict(params))
                except (ValueError, KeyError, TypeError) as e:
                    logger.debug(f"Could not load strategy {strategy_name}: {e}")
                    return self._heuristic_objective(params, strategy_name)

                # Generate signals from strategy
                try:
                    signals_df = strategy.generate_signals(market_df)
                except Exception as e:
                    logger.debug(f"Could not generate signals: {e}")
                    return self._heuristic_objective(params, strategy_name)

                # Convert signals DataFrame to Signal objects
                signals = self._convert_df_to_signals(signals_df, strategy_name)

                if not signals:
                    logger.debug("No signals generated from strategy")
                    return self._heuristic_objective(params, strategy_name)

                # Create backtest config
                backtest_config = BacktestConfig(
                    strategy_name=strategy_name,
                    initial_capital=Decimal("100000"),
                    commission_per_trade=Decimal("1.0"),
                    slippage_percentage=Decimal("0.1"),
                    risk_free_rate=Decimal("0.02"),
                )

                # Create market data list for backtester
                market_data_list = self._convert_df_to_market_data(market_df)

                if not market_data_list:
                    return self._heuristic_objective(params, strategy_name)

                # Run backtest
                backtester = SimpleBacktester(
                    config=backtest_config,
                    strategy=strategy,
                    strategy_name=strategy_name,
                )

                result = backtester.run_backtest(
                    market_data=market_data_list,
                    signals=signals,
                )

                # Extract Sharpe ratio
                if result.performance and result.performance.sharpe_ratio is not None:
                    sharpe = float(result.performance.sharpe_ratio)
                    logger.debug(f"Backtest Sharpe: {sharpe:.3f} for params: {params}")
                    return max(0.0, sharpe)
                else:
                    if result.total_return:
                        return max(0.0, float(result.total_return) / 100.0)

                return 0.0

            except (ImportError, ValueError, TypeError, KeyError, AttributeError) as e:
                logger.debug(f"Backtest objective failed: {e}")
                return self._heuristic_objective(params, strategy_name)
            except Exception as e:
                logger.warning(f"Unexpected error in objective function: {e}")
                return 0.0

        # Run optimization (async version)
        result = await optimizer.optimize(objective, param_grid)

        return result.best_params, {"trials": len(result.all_trials)}

    def _get_parameter_grid(self, strategy_name: str, profile: InputProfile) -> ParameterGrid:
        """
        Get parameter grid for strategy optimization.

        Provides comprehensive parameter definitions for all supported strategies
        following Ilmanen's rules and best practices.

        Args:
            strategy_name: Name of the strategy
            profile: User investment profile

        Returns:
            ParameterGrid for optimization
        """
        # ParameterRange is already imported at module level

        parameters: list[ParameterRange] = []

        # FX Carry Trade parameters (Ilmanen Rule 12.9)
        if strategy_name == "fx_carry_trade":
            parameters.extend(
                [
                    ParameterRange(
                        name="interest_rate_diff",
                        min_value=0.0,
                        max_value=0.10,
                        step=0.01,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="forward_premium",
                        min_value=-0.05,
                        max_value=0.05,
                        step=0.01,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="min_carry_threshold",
                        min_value=0.005,
                        max_value=0.03,
                        step=0.005,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="lookback",
                        min_value=20,
                        max_value=60,
                        step=5,
                        parameter_type=ParameterType.INTEGER,
                    ),
                ]
            )

        # Crypto Momentum parameters
        elif strategy_name == "crypto_momentum":
            parameters.extend(
                [
                    ParameterRange(
                        name="lookback",
                        min_value=7,
                        max_value=90,
                        step=7,
                        parameter_type=ParameterType.INTEGER,
                    ),
                    ParameterRange(
                        name="momentum_threshold",
                        min_value=0.02,
                        max_value=0.15,
                        step=0.01,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="volatility_filter",
                        min_value=0.5,
                        max_value=2.0,
                        step=0.1,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="volume_confirm",
                        values=[True, False],
                        parameter_type=ParameterType.CATEGORICAL,
                    ),
                ]
            )

        # Momentum Modular parameters (enhanced)
        elif strategy_name == "momentum_modular":
            parameters.extend(
                [
                    ParameterRange(
                        name="lookback",
                        min_value=10,
                        max_value=90,
                        step=5,
                        parameter_type=ParameterType.INTEGER,
                    ),
                    ParameterRange(
                        name="threshold",
                        min_value=0.5,
                        max_value=3.0,
                        step=0.25,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="rebalance_frequency",
                        min_value=1,
                        max_value=30,
                        step=1,
                        parameter_type=ParameterType.INTEGER,
                    ),
                    ParameterRange(
                        name="volatility_targeting",
                        values=[True, False],
                        parameter_type=ParameterType.CATEGORICAL,
                    ),
                    ParameterRange(
                        name="volatility_target",
                        min_value=0.10,
                        max_value=0.25,
                        step=0.05,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                ]
            )

        # Multi-Factor Strategy parameters
        elif strategy_name == "multi_factor":
            parameters.extend(
                [
                    ParameterRange(
                        name="momentum_weight",
                        min_value=0.0,
                        max_value=1.0,
                        step=0.1,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="value_weight",
                        min_value=0.0,
                        max_value=1.0,
                        step=0.1,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="quality_weight",
                        min_value=0.0,
                        max_value=1.0,
                        step=0.1,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="lookback",
                        min_value=50,
                        max_value=252,
                        step=20,
                        parameter_type=ParameterType.INTEGER,
                    ),
                    ParameterRange(
                        name="rebalance_frequency",
                        min_value=5,
                        max_value=40,
                        step=5,
                        parameter_type=ParameterType.INTEGER,
                    ),
                ]
            )

        # Dividend Screener parameters
        elif strategy_name == "dividend_screener":
            parameters.extend(
                [
                    ParameterRange(
                        name="min_dividend_yield",
                        min_value=0.01,
                        max_value=0.10,
                        step=0.01,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="payout_ratio_max",
                        min_value=0.3,
                        max_value=0.9,
                        step=0.1,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="dgr_threshold",
                        min_value=0.0,
                        max_value=0.15,
                        step=0.01,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="min_market_cap",
                        min_value=100,
                        max_value=10000,
                        step=100,
                        parameter_type=ParameterType.INTEGER,
                    ),
                ]
            )

        # Pairs Trading Modular parameters
        elif strategy_name == "pairs_trading_modular":
            parameters.extend(
                [
                    ParameterRange(
                        name="lookback",
                        min_value=20,
                        max_value=60,
                        step=5,
                        parameter_type=ParameterType.INTEGER,
                    ),
                    ParameterRange(
                        name="entry_threshold",
                        min_value=1.5,
                        max_value=3.0,
                        step=0.25,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="exit_threshold",
                        min_value=0.0,
                        max_value=1.0,
                        step=0.25,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="stop_loss",
                        min_value=2.0,
                        max_value=5.0,
                        step=0.5,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                ]
            )

        # Low Volatility Strategy parameters
        elif strategy_name == "low_volatility":
            parameters.extend(
                [
                    ParameterRange(
                        name="volatility_percentile",
                        min_value=0.1,
                        max_value=0.5,
                        step=0.1,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="max_beta",
                        min_value=0.5,
                        max_value=1.2,
                        step=0.1,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="lookback",
                        min_value=20,
                        max_value=60,
                        step=10,
                        parameter_type=ParameterType.INTEGER,
                    ),
                ]
            )

        # Covered Calls Strategy parameters
        elif strategy_name == "covered_calls":
            parameters.extend(
                [
                    ParameterRange(
                        name="otm_percentage",
                        min_value=0.01,
                        max_value=0.10,
                        step=0.01,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="expiration_days",
                        min_value=7,
                        max_value=60,
                        step=7,
                        parameter_type=ParameterType.INTEGER,
                    ),
                    ParameterRange(
                        name="roll_threshold",
                        min_value=0.2,
                        max_value=0.8,
                        step=0.1,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                ]
            )

        # FX Intermarket Strategy parameters
        elif strategy_name == "fx_intermarket":
            parameters.extend(
                [
                    ParameterRange(
                        name="correlation_threshold",
                        min_value=0.5,
                        max_value=0.95,
                        step=0.05,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="bull_stable_weight",
                        min_value=0.0,
                        max_value=1.0,
                        step=0.1,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="bear_weight",
                        min_value=0.0,
                        max_value=1.0,
                        step=0.1,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="lookback",
                        min_value=20,
                        max_value=100,
                        step=10,
                        parameter_type=ParameterType.INTEGER,
                    ),
                ]
            )

        # Generic momentum strategies
        elif "momentum" in strategy_name:
            parameters.extend(
                [
                    ParameterRange(
                        name="lookback",
                        min_value=10,
                        max_value=60,
                        step=5,
                        parameter_type=ParameterType.INTEGER,
                    ),
                    ParameterRange(
                        name="threshold",
                        min_value=0.5,
                        max_value=3.0,
                        step=0.25,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                ]
            )

        # Generic mean reversion strategies
        elif "mean_reversion" in strategy_name:
            parameters.extend(
                [
                    ParameterRange(
                        name="lookback",
                        min_value=5,
                        max_value=30,
                        step=5,
                        parameter_type=ParameterType.INTEGER,
                    ),
                    ParameterRange(
                        name="entry_threshold",
                        min_value=1.5,
                        max_value=3.0,
                        step=0.25,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="exit_threshold",
                        min_value=0.5,
                        max_value=1.5,
                        step=0.25,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                ]
            )

        # Generic pairs trading strategies
        elif "pairs_trading" in strategy_name:
            parameters.extend(
                [
                    ParameterRange(
                        name="lookback",
                        min_value=20,
                        max_value=60,
                        step=10,
                        parameter_type=ParameterType.INTEGER,
                    ),
                    ParameterRange(
                        name="entry_zscore",
                        min_value=1.5,
                        max_value=3.0,
                        step=0.25,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                    ParameterRange(
                        name="exit_zscore",
                        min_value=0.0,
                        max_value=1.0,
                        step=0.25,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                ]
            )

        # Default parameters for unknown strategies
        else:
            parameters.extend(
                [
                    ParameterRange(
                        name="lookback",
                        min_value=10,
                        max_value=50,
                        step=10,
                        parameter_type=ParameterType.INTEGER,
                    ),
                    ParameterRange(
                        name="threshold",
                        min_value=0.5,
                        max_value=2.0,
                        step=0.25,
                        parameter_type=ParameterType.CONTINUOUS,
                    ),
                ]
            )

        return ParameterGrid(parameters=parameters)

    def _validate_strategy(
        self,
        strategy_name: str,
        parameters: StrategyParameters,
        market_data: MarketData,
    ) -> tuple[Decimal, dict[str, object]]:
        """
        Validate strategy using walk-forward analysis with actual strategy integration.

        Args:
            strategy_name: Name of the strategy
            parameters: Optimized parameters
            market_data: Market data for validation

        Returns:
            Tuple of (validation_score, validation_details)
        """
        # Create walk-forward config
        wf_config = WalkForwardConfig(
            train_period_months=24,
            test_period_months=6,
            step_months=3,
            min_observations=252,
        )

        # Create validator with config
        validator = WalkForwardValidator(config=wf_config)

        # Import StrategyRegistry for actual strategy creation
        from app.strategies.registry import StrategyRegistry  # pylint: disable=import-error

        # Define strategy factory with actual strategy instantiation
        def strategy_factory(params: StrategyParameters) -> StrategyProtocol:
            """
            Create a strategy instance for walk-forward validation.

            Integrates with StrategyRegistry to create actual strategy
            implementations with the given parameters.

            Args:
                params: Strategy parameters from optimization

            Returns:
                Strategy instance implementing StrategyProtocol

            Raises:
                ValueError: If strategy cannot be created
            """
            registry = StrategyRegistry()

            try:
                # Load strategy with parameters
                strategy = registry.load_strategy(strategy_name, dict(params))
                # Type assertion: StrategyRegistry.load_strategy returns StrategyProtocol
                # isinstance check on Protocol requires @runtime_checkable, but we trust the registry
                return strategy  # type: ignore[return-value]
            except (ValueError, KeyError, TypeError) as e:
                logger.error(f"Failed to create strategy {strategy_name}: {e}")
                raise ValueError(f"Could not create strategy {strategy_name}: {e}")

        # Define parameter grid
        param_grid = {k: [v] for k, v in parameters.items()} if parameters else {}

        # Convert market_data to DataFrame if needed for validator
        if isinstance(market_data, dict):
            import pandas as pd

            market_df = pd.DataFrame(market_data)
        elif isinstance(market_data, DataFrame):
            market_df = market_data
        else:
            logger.warning(f"Unsupported market_data type for validation: {type(market_data)}")
            return Decimal("50"), {"error": "Unsupported market data type"}

        # Run validation
        try:
            result = validator.validate(
                strategy_factory=strategy_factory,
                param_grid=param_grid,
                data=market_df,
            )

            # Calculate validation score from result
            score, details = self._calculate_validation_score(result)

            return score, details

        except (ValueError, TypeError, RuntimeError) as e:
            logger.warning(
                f"Walk-forward validation failed: {e}",
                exc_info=True,
            )
            return Decimal("50"), {"error": str(e)}

    def _calculate_validation_score(
        self, result: WalkForwardResultProtocol
    ) -> tuple[Decimal, dict[str, object]]:
        """
        Calculate validation score from walk-forward result.

        Args:
            result: Walk-forward validation result

        Returns:
            Tuple of (validation_score, validation_details)
        """
        # Base score
        score = Decimal("50")

        # Adjust for consistency
        score += self._score_consistency(result.consistency_score)

        # Adjust for degradation
        degradation_summary = result.get_degradation_summary()
        sharpe_degradation_raw = degradation_summary.get("sharpe_degradation", Decimal("0"))
        sharpe_degradation = (
            sharpe_degradation_raw
            if isinstance(sharpe_degradation_raw, Decimal)
            else Decimal(str(sharpe_degradation_raw))
        )
        score += self._score_degradation(sharpe_degradation)

        # Adjust for OS Sharpe
        os_sharpe_raw = result.os_performance.get("sharpe_ratio", Decimal("0"))
        os_sharpe = (
            os_sharpe_raw if isinstance(os_sharpe_raw, Decimal) else Decimal(str(os_sharpe_raw))
        )
        score += self._score_os_sharpe(os_sharpe)

        # Clamp to valid range
        score = max(Decimal("0"), min(Decimal("100"), score))

        # Build details
        is_sharpe_raw = result.is_performance.get("sharpe_ratio", Decimal("0"))
        is_sharpe = (
            is_sharpe_raw if isinstance(is_sharpe_raw, Decimal) else Decimal(str(is_sharpe_raw))
        )

        details: dict[str, object] = {
            "num_periods": result.num_periods,
            "consistency_score": float(result.consistency_score),
            "sharpe_degradation": float(sharpe_degradation),
            "os_sharpe": float(os_sharpe),
            "is_sharpe": float(is_sharpe),
        }

        return score, details

    def _score_consistency(self, consistency_score: Decimal) -> Decimal:
        """
        Calculate score adjustment for consistency.

        Args:
            consistency_score: Consistency score from validation

        Returns:
            Score adjustment
        """
        if consistency_score > Decimal("80"):
            return Decimal("20")
        elif consistency_score > Decimal("60"):
            return Decimal("10")
        return Decimal("0")

    def _score_degradation(self, sharpe_degradation: Decimal) -> Decimal:
        """
        Calculate score adjustment for Sharpe degradation.

        Args:
            sharpe_degradation: Sharpe ratio degradation metric

        Returns:
            Score adjustment (can be negative)
        """
        if sharpe_degradation >= Decimal("0.85"):
            return Decimal("20")  # Minimal degradation
        elif sharpe_degradation >= Decimal("0.70"):
            return Decimal("10")
        elif sharpe_degradation < Decimal("0.50"):
            return Decimal("-20")  # Severe degradation
        return Decimal("0")

    def _score_os_sharpe(self, os_sharpe: Decimal) -> Decimal:
        """
        Calculate score adjustment for out-of-sample Sharpe.

        Args:
            os_sharpe: Out-of-sample Sharpe ratio

        Returns:
            Score adjustment (can be negative)
        """
        if os_sharpe > Decimal("1.5"):
            return Decimal("10")
        elif os_sharpe < Decimal("0.5"):
            return Decimal("-10")
        return Decimal("0")

    def _estimate_performance(
        self,
        strategy_name: str,
        profile: InputProfile,
        optimization_metrics: dict[str, object],
        validation_details: dict[str, object],
    ) -> dict[str, Decimal]:
        """
        Estimate strategy performance metrics.

        Args:
            strategy_name: Name of the strategy
            profile: User investment profile
            optimization_metrics: Metrics from optimization
            validation_details: Details from validation

        Returns:
            Dictionary with performance metrics
        """
        # Get base expectations by strategy type
        performance = self._get_base_performance(strategy_name)

        # Adjust for risk tolerance
        performance = self._adjust_performance_for_risk(performance, profile.risk_tolerance)

        # Override with validation results if available
        performance = self._apply_validation_results(performance, validation_details)

        return performance

    def _get_base_performance(self, strategy_name: str) -> dict[str, Decimal]:
        """
        Get base performance expectations for a strategy type.

        Args:
            strategy_name: Name of the strategy

        Returns:
            Dictionary with base performance metrics
        """
        if "momentum" in strategy_name:
            return self._estimate_momentum_performance()
        elif "mean_reversion" in strategy_name:
            return self._estimate_mean_reversion_performance()
        elif "pairs_trading" in strategy_name:
            return self._estimate_pairs_performance()
        elif "dividend" in strategy_name:
            return self._estimate_dividend_performance()
        elif "carry" in strategy_name:
            return self._estimate_carry_trade_performance()
        elif "low_volatility" in strategy_name:
            return self._estimate_low_volatility_performance()
        else:
            return self._estimate_default_performance()

    def _estimate_momentum_performance(self) -> dict[str, Decimal]:
        """
        Get base performance metrics for momentum strategies.

        Returns:
            Dictionary with momentum-specific performance metrics
        """
        return {
            "expected_return": Decimal("0.15"),  # 15% annual
            "expected_risk": Decimal("0.20"),  # 20% vol
            "sharpe_ratio": Decimal("0.75"),
            "max_drawdown": Decimal("0.25"),
            "win_rate": Decimal("0.55"),
        }

    def _estimate_carry_trade_performance(self) -> dict[str, Decimal]:
        """
        Get base performance metrics for carry trade strategies (Ilmanen Rule 12.9).

        Returns:
            Dictionary with carry trade-specific performance metrics
        """
        return {
            "expected_return": Decimal("0.08"),  # 8% annual from interest rate differential
            "expected_risk": Decimal("0.12"),  # 12% vol (FX can be volatile)
            "sharpe_ratio": Decimal("0.67"),
            "max_drawdown": Decimal("0.20"),
            "win_rate": Decimal("0.60"),
        }

    def _estimate_low_volatility_performance(self) -> dict[str, Decimal]:
        """
        Get base performance metrics for low volatility strategies.

        Returns:
            Dictionary with low volatility-specific performance metrics
        """
        return {
            "expected_return": Decimal("0.10"),  # Lower return but more stable
            "expected_risk": Decimal("0.10"),  # Lower volatility
            "sharpe_ratio": Decimal("1.00"),  # Better risk-adjusted return
            "max_drawdown": Decimal("0.15"),
            "win_rate": Decimal("0.55"),
        }

    def _estimate_mean_reversion_performance(self) -> dict[str, Decimal]:
        """
        Get base performance metrics for mean reversion strategies.

        Returns:
            Dictionary with mean reversion-specific performance metrics
        """
        return {
            "expected_return": Decimal("0.12"),
            "expected_risk": Decimal("0.15"),
            "sharpe_ratio": Decimal("0.80"),
            "max_drawdown": Decimal("0.20"),
            "win_rate": Decimal("0.60"),
        }

    def _estimate_pairs_performance(self) -> dict[str, Decimal]:
        """
        Get base performance metrics for pairs trading strategies.

        Returns:
            Dictionary with pairs trading-specific performance metrics
        """
        return {
            "expected_return": Decimal("0.10"),
            "expected_risk": Decimal("0.10"),
            "sharpe_ratio": Decimal("1.00"),
            "max_drawdown": Decimal("0.15"),
            "win_rate": Decimal("0.65"),
        }

    def _estimate_dividend_performance(self) -> dict[str, Decimal]:
        """
        Get base performance metrics for dividend strategies.

        Returns:
            Dictionary with dividend-specific performance metrics
        """
        return {
            "expected_return": Decimal("0.08"),
            "expected_risk": Decimal("0.12"),
            "sharpe_ratio": Decimal("0.67"),
            "max_drawdown": Decimal("0.18"),
            "win_rate": Decimal("0.50"),
        }

    def _estimate_default_performance(self) -> dict[str, Decimal]:
        """
        Get default performance metrics for unknown strategy types.

        Returns:
            Dictionary with default performance metrics
        """
        return {
            "expected_return": Decimal("0.10"),
            "expected_risk": Decimal("0.15"),
            "sharpe_ratio": Decimal("0.67"),
            "max_drawdown": Decimal("0.20"),
            "win_rate": Decimal("0.55"),
        }

    def _adjust_performance_for_risk(
        self,
        performance: dict[str, Decimal],
        risk_tolerance: RiskTolerance,
    ) -> dict[str, Decimal]:
        """
        Adjust performance metrics based on risk tolerance.

        Args:
            performance: Base performance metrics
            risk_tolerance: User's risk tolerance level

        Returns:
            Adjusted performance metrics
        """
        adjusted = performance.copy()

        if risk_tolerance == RiskTolerance.BAJO:
            adjusted["expected_return"] *= Decimal("0.8")
            adjusted["expected_risk"] *= Decimal("0.7")
            adjusted["max_drawdown"] *= Decimal("0.6")
        elif risk_tolerance == RiskTolerance.ALTO:
            adjusted["expected_return"] *= Decimal("1.2")
            adjusted["expected_risk"] *= Decimal("1.3")
            adjusted["max_drawdown"] *= Decimal("1.2")

        return adjusted

    def _apply_validation_results(
        self,
        performance: dict[str, Decimal],
        validation_details: dict[str, object],
    ) -> dict[str, Decimal]:
        """
        Override performance metrics with validation results if available.

        Args:
            performance: Current performance metrics
            validation_details: Details from walk-forward validation

        Returns:
            Performance metrics with validation overrides applied
        """
        result = performance.copy()

        if validation_details and "os_sharpe" in validation_details:
            os_sharpe = Decimal(str(validation_details["os_sharpe"]))
            if os_sharpe > 0:
                result["sharpe_ratio"] = os_sharpe

        return result

    def _calculate_total_score(
        self,
        suitability: Decimal,
        validation_score: Decimal,
        performance: dict[str, Decimal],
        criteria: StrategySelectionCriteria,
    ) -> Decimal:
        """
        Calculate total strategy score from components.

        Args:
            suitability: Profile matching score (0-100)
            validation_score: Walk-forward validation score (0-100)
            performance: Performance metrics
            criteria: Scoring criteria with weights

        Returns:
            Total score (0-100)
        """
        # Normalize performance metrics to 0-100 scale
        sharpe = performance.get("sharpe_ratio", Decimal("0"))
        sharpe_score = min(Decimal("100"), sharpe * Decimal("50"))  # Sharpe 2.0 = 100 points

        return_score = performance.get("expected_return", Decimal("0")) * Decimal(
            "500"
        )  # 20% = 100

        risk_score = Decimal("100") - (
            performance.get("expected_risk", Decimal("0")) * Decimal("200")
        )  # Lower is better

        # Calculate weighted score
        total = (
            return_score * Decimal(str(criteria.return_weight))
            + risk_score * Decimal(str(criteria.risk_weight))
            + sharpe_score * Decimal(str(criteria.sharpe_weight))
            + validation_score * Decimal(str(criteria.validation_weight))
            + suitability * Decimal(str(criteria.suitability_weight))
        )

        return max(Decimal("0"), min(Decimal("100"), total))

    def _get_default_criteria(self, profile: InputProfile) -> StrategySelectionCriteria:
        """
        Get default selection criteria based on profile.

        Args:
            profile: User investment profile

        Returns:
            Default selection criteria
        """
        # Adjust weights based on profile
        if profile.risk_tolerance == RiskTolerance.BAJO:
            return StrategySelectionCriteria(
                return_weight=0.20,
                risk_weight=0.30,  # Higher weight on risk
                sharpe_weight=0.25,
                validation_weight=0.15,
                suitability_weight=0.10,
                min_sharpe_ratio=Decimal("0.7"),
                max_drawdown_limit=Decimal("0.20"),
            )
        elif profile.risk_tolerance == RiskTolerance.ALTO:
            return StrategySelectionCriteria(
                return_weight=0.35,  # Higher weight on return
                risk_weight=0.15,
                sharpe_weight=0.25,
                validation_weight=0.15,
                suitability_weight=0.10,
                min_sharpe_ratio=Decimal("0.5"),
                max_drawdown_limit=Decimal("0.40"),
            )
        else:
            # Medium risk - balanced
            return StrategySelectionCriteria()


class SelectStrategyUseCase:
    """
    Use case wrapper for strategy selection.

    This class provides a simple interface for selecting strategies
    based on user profiles and market conditions.

    Example:
        ```python
        use_case = SelectStrategyUseCase()

        profile = InputProfile.create(
            capital_amount=100000,
            horizon_months=24,
            objective="maximize_capital",
            risk_tolerance="medium"
        )

        result = use_case.execute(profile, market_data)
        logger.debug(f"Selected: {result.selected_strategy.strategy_name}")
        logger.debug(f"Score: {result.selected_strategy.total_score}")
        ```
    """

    def __init__(
        self,
        selector: StrategySelector | None = None,
    ):
        """
        initialize use case with selector.

        Args:
            selector: Strategy selector instance (creates default if None)
        """
        self._selector = selector or StrategySelector()
        logger.info("SelectStrategyUseCase initialized")

    def execute(
        self,
        profile: InputProfile,
        market_data: MarketData | None = None,
        criteria: StrategySelectionCriteria | None = None,
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> StrategySelectionResult:
        """
        Execute strategy selection use case.

        Args:
            profile: User investment profile
            market_data: Market data for validation (optional)
            criteria: Selection criteria (uses defaults if None)
            progress_callback: Optional callback for progress updates

        Returns:
            StrategySelectionResult with selected strategy
        """
        logger.info(f"Executing SelectStrategyUseCase for profile: {profile.input_id[:8]}")

        result = self._selector.select_strategy(
            profile=profile,
            market_data=market_data,
            criteria=criteria,
            progress_callback=progress_callback,
        )

        logger.info(
            f"Strategy selection complete: {result.selected_strategy.strategy_name} "
            f"(score: {result.selected_strategy.total_score:.1f})"
        )

        return result

    def get_strategy_recommendations(
        self,
        profile: InputProfile,
        top_n: int = 3,
    ) -> list[dict[str, object]]:
        """
        Get top strategy recommendations without full validation.

        This is a faster method that skips walk-forward validation
        and parameter optimization, providing quick recommendations.

        Args:
            profile: User investment profile
            top_n: Number of top strategies to return

        Returns:
            List of strategy recommendations with scores
        """
        # Get strategy mapping
        strategy_mapping = self._selector._profile_mapper.create_strategy_mapping(profile)
        candidates = strategy_mapping.enabled_strategies[:top_n]

        recommendations = []
        for strategy_name in candidates:
            # Calculate suitability only
            suitability = self._selector._calculate_suitability_score(
                strategy_name, profile, strategy_mapping
            )

            # Get weight
            weight = strategy_mapping.strategy_weights.get(strategy_name, 1.0)

            recommendations.append(
                {
                    "strategy_name": strategy_name,
                    "weight": weight,
                    "suitability_score": float(suitability),
                    "enabled": True,
                }
            )

        # Sort by suitability
        recommendations.sort(
            key=lambda r: float(r["suitability_score"])
            if isinstance(r["suitability_score"], (int, float, str))
            else 0.0,
            reverse=True,
        )

        return recommendations[:top_n]
