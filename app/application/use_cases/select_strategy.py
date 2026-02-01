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
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pandas as pd

# Type alias for market data - accepts DataFrame or Any for flexibility
MarketData = Union[pd.DataFrame, Any]

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
        parameters: Strategy parameters
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
    parameters: Dict[str, Any] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)
    expected_return: Decimal = field(default=Decimal("0"))
    expected_risk: Decimal = field(default=Decimal("0"))
    sharpe_ratio: Decimal = field(default=Decimal("0"))
    max_drawdown: Decimal = field(default=Decimal("0"))
    win_rate: Decimal = field(default=Decimal("0"))
    suitability_score: Decimal = field(default=Decimal("0"))
    validation_score: Decimal = field(default=Decimal("0"))
    total_score: Decimal = field(default=Decimal("0"))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
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
    alternative_strategies: List[StrategyConfiguration]
    selection_timestamp: datetime
    selection_criteria: StrategySelectionCriteria
    optimization_details: Dict[str, Any] = field(default_factory=dict)
    validation_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
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
        profile_mapper: Optional[ProfileStrategyMapper] = None,
        optimizer: Optional[BayesianOptimizer] = None,
        validator: Optional[WalkForwardValidator] = None,
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
        market_data: Optional[MarketData] = None,
        criteria: Optional[StrategySelectionCriteria] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
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
        configurations: List[StrategyConfiguration] = []

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

            except Exception as e:
                logger.error(f"Error analyzing strategy {strategy_name}: {e}")
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
        market_data: Optional[MarketData],
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
        optimized_params: Dict[str, Any] = {}
        optimization_metrics: Dict[str, Any] = {}

        if self._optimizer and market_data is not None:
            try:
                optimized_params, optimization_metrics = self._optimize_parameters(
                    strategy_name=strategy_name,
                    profile=profile,
                    market_data=market_data,
                )
            except Exception as e:
                logger.warning(f"Parameter optimization failed for {strategy_name}: {e}")
                # Use default parameters from mapping
                optimized_params = {}
        else:
            logger.debug(f"No optimizer or market data, using defaults for {strategy_name}")

        # Step 3: Validate strategy (if validator available and required)
        validation_score = Decimal("100")  # Default if no validation
        validation_details: Dict[str, Any] = {}

        if criteria.require_walk_forward and self._validator and market_data is not None:
            try:
                validation_score, validation_details = self._validate_strategy(
                    strategy_name=strategy_name,
                    parameters=optimized_params,
                    market_data=market_data,
                )
            except Exception as e:
                logger.warning(f"Validation failed for {strategy_name}: {e}")
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
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Optimize strategy parameters using Bayesian optimization.

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

        # Define objective function
        def objective(params: Dict[str, Any]) -> float:
            """
            Objective function for Bayesian optimization.

            NOTE: This is a placeholder implementation. In production, this should:
            1. Run a backtest with the given parameters
            2. Calculate the Sharpe ratio or other metrics
            3. Return the metric value for optimization

            Args:
                params: Strategy parameters to evaluate

            Returns:
                float: Objective value (higher is better)

            Raises:
                NotImplementedError: When used in production without proper implementation
            """
            # TODO: Implement proper backtest integration
            # This requires integration with the backtesting engine to:
            # - Create a strategy instance with the given parameters
            # - Run historical backtest
            # - Calculate Sharpe ratio or other performance metrics
            # - Return the metric value for optimization

            # For now, provide a simple heuristic-based placeholder
            # This allows the optimization framework to be tested
            # without requiring full backtest integration

            # Placeholder: score based on param reasonableness
            score = 0.5
            if "lookback" in params:
                # Prefer medium lookback periods
                lookback = params["lookback"]
                if 20 <= lookback <= 50:
                    score += 0.2
            if "threshold" in params:
                # Prefer moderate thresholds
                threshold = params["threshold"]
                if 0.5 <= threshold <= 2.0:
                    score += 0.2

            return min(2.0, max(0.0, score))

        # Run optimization (synchronous wrapper)
        import asyncio

        try:
            loop = asyncio.get_running_loop()
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

    def _get_parameter_grid(self, strategy_name: str, profile: InputProfile) -> ParameterGrid:
        """
        Get parameter grid for strategy optimization.

        Args:
            strategy_name: Name of the strategy
            profile: User investment profile

        Returns:
            ParameterGrid for optimization
        """
        parameters: List[ParameterRange] = []

        # Common parameters
        if "momentum" in strategy_name:
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
                    ),
                ]
            )
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
                    ),
                    ParameterRange(
                        name="exit_threshold",
                        min_value=0.5,
                        max_value=1.5,
                        step=0.25,
                    ),
                ]
            )
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
                    ),
                    ParameterRange(
                        name="exit_zscore",
                        min_value=0.0,
                        max_value=1.0,
                        step=0.25,
                    ),
                ]
            )
        else:
            # Default parameters for unknown strategies
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
                    ),
                ]
            )

        return ParameterGrid(parameters=parameters)

    def _validate_strategy(
        self,
        strategy_name: str,
        parameters: Dict[str, Any],
        market_data: MarketData,
    ) -> Tuple[Decimal, Dict[str, Any]]:
        """
        Validate strategy using walk-forward analysis.

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

        # Define strategy factory
        def strategy_factory(params: Dict[str, Any]) -> Any:
            # This would create actual strategy instance
            # For now, return placeholder
            return {"name": strategy_name, "params": params}

        # Define parameter grid
        param_grid = {k: [v] for k, v in parameters.items()} if parameters else {}

        # Run validation
        try:
            result = validator.validate(
                strategy_factory=strategy_factory,
                param_grid=param_grid,
                data=market_data,
            )

            # Calculate validation score from result
            score, details = self._calculate_validation_score(result)

            return score, details

        except Exception as e:
            logger.warning(f"Walk-forward validation failed: {e}")
            return Decimal("50"), {"error": str(e)}

    def _calculate_validation_score(self, result: Any) -> Tuple[Decimal, Dict[str, Any]]:
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
        sharpe_degradation = degradation_summary.get("sharpe_degradation", Decimal("0"))
        score += self._score_degradation(sharpe_degradation)

        # Adjust for OS Sharpe
        os_sharpe = result.os_performance.get("sharpe_ratio", Decimal("0"))
        score += self._score_os_sharpe(os_sharpe)

        # Clamp to valid range
        score = max(Decimal("0"), min(Decimal("100"), score))

        # Build details
        details = {
            "num_periods": result.num_periods,
            "consistency_score": float(result.consistency_score),
            "sharpe_degradation": float(sharpe_degradation),
            "os_sharpe": float(os_sharpe),
            "is_sharpe": float(result.is_performance.get("sharpe_ratio", Decimal("0"))),
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
        optimization_metrics: Dict[str, Any],
        validation_details: Dict[str, Any],
    ) -> Dict[str, Decimal]:
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

    def _get_base_performance(self, strategy_name: str) -> Dict[str, Decimal]:
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
        else:
            return self._estimate_default_performance()

    def _estimate_momentum_performance(self) -> Dict[str, Decimal]:
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

    def _estimate_mean_reversion_performance(self) -> Dict[str, Decimal]:
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

    def _estimate_pairs_performance(self) -> Dict[str, Decimal]:
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

    def _estimate_dividend_performance(self) -> Dict[str, Decimal]:
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

    def _estimate_default_performance(self) -> Dict[str, Decimal]:
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
        performance: Dict[str, Decimal],
        risk_tolerance: RiskTolerance,
    ) -> Dict[str, Decimal]:
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
        performance: Dict[str, Decimal],
        validation_details: Dict[str, Any],
    ) -> Dict[str, Decimal]:
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
        performance: Dict[str, Decimal],
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
        print(f"Selected: {result.selected_strategy.strategy_name}")
        print(f"Score: {result.selected_strategy.total_score}")
        ```
    """

    def __init__(
        self,
        selector: Optional[StrategySelector] = None,
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
        market_data: Optional[MarketData] = None,
        criteria: Optional[StrategySelectionCriteria] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
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
    ) -> List[Dict[str, Any]]:
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
