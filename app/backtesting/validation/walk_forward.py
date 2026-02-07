"""
Walk-forward validation implementation (FASE 5.3).

This module implements rolling window walk-forward validation for robust
strategy testing, preventing look-ahead bias while measuring true out-of-sample
performance.

Key Features:
- Rolling window optimization with configurable train/test periods
- Multiple IS/OS periods for robust validation
- Aggregate IS vs OS metrics with degradation analysis
- Consistency scoring across periods
- Actionable recommendations based on validation results

References:
    - AUDIT_PLAN_COMPLETO.md - FASE 5.3: Validation
    - "Advances in Financial Machine Learning" - Marcos López de Prado
    - "Expected Returns" - Antti Ilmanen
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from typing import ParamSpec
except ImportError:
    from typing_extensions import ParamSpec

from .models import PeriodResult, WalkForwardConfig, WalkForwardResult

logger = logging.getLogger(__name__)

P = ParamSpec("P")


class WalkForwardValidator:
    """
    Walk-forward validator for robust strategy validation.

    This class implements rolling window walk-forward validation, which
    simulates real-world trading by periodically optimizing parameters
    on in-sample data and testing on out-of-sample data.

    Example:
        ```python
        validator = WalkForwardValidator(config)

        result = validator.validate(
            strategy_factory=lambda params: MyStrategy(params),
            param_grid={"window": [10, 20, 30], "threshold": [0.5, 1.0, 1.5]},
            data=price_data,
            optimizer=optimizer
        )

        logger.debug(f"IS Sharpe: {result.is_performance['sharpe_ratio']}")
        logger.debug(f"OS Sharpe: {result.os_performance['sharpe_ratio']}")
        logger.debug(f"Degradation: {result.is_os_ratio}")
        ```
    """

    def __init__(
        self,
        config: Optional[WalkForwardConfig] = None,
        optimizer: Optional[Any] = None,
    ):
        """
        Initialize walk-forward validator.

        Args:
            config: Walk-forward configuration
            optimizer: Parameter optimizer instance
        """
        self.config = config or WalkForwardConfig()
        self.optimizer = optimizer

    def validate(
        self,
        strategy_factory: Callable[[Dict[str, Any]], Any],
        param_grid: Dict[str, List[Any]],
        data: pd.DataFrame,
        optimizer: Optional[Any] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> WalkForwardResult:
        """
        Perform walk-forward validation.

        Process:
        1. Split data into rolling windows
        2. For each window:
           a. Optimize parameters on IS period
           b. Test on OS period
           c. Record results
        3. Aggregate results across all windows

        Args:
            strategy_factory: Function that creates strategy from parameters
            param_grid: Parameter grid for optimization
            data: Historical price data with datetime index
            optimizer: Parameter optimizer (overrides instance optimizer)
            progress_callback: Optional callback for progress updates

        Returns:
            WalkForwardResult with aggregated IS and OS performance
        """
        if len(data) < self.config.min_observations:
            raise ValueError(
                f"Insufficient data: {len(data)} observations. "
                f"Minimum required: {self.config.min_observations}"
            )

        optimizer = optimizer or self.optimizer
        if optimizer is None:
            raise ValueError("Optimizer must be provided")

        # Generate rolling windows
        windows = self._generate_rolling_windows(data)

        if not windows:
            raise ValueError("No valid windows generated from data")

        logger.info(f"Generated {len(windows)} rolling windows for validation")

        # Validate each window
        is_results: List[PeriodResult] = []
        os_results: List[PeriodResult] = []

        for i, (train_data, test_data) in enumerate(windows):
            try:
                # Optimize on training data
                best_params = optimizer.optimize(
                    strategy_factory=strategy_factory,
                    param_grid=param_grid,
                    data=train_data,
                )

                # Test on training data (IS)
                is_result = self._test_period(
                    strategy_factory=strategy_factory,
                    params=best_params,
                    data=train_data,
                    is_in_sample=True,
                    period_id=i,
                )
                is_results.append(is_result)

                # Test on test data (OS)
                os_result = self._test_period(
                    strategy_factory=strategy_factory,
                    params=best_params,
                    data=test_data,
                    is_in_sample=False,
                    period_id=i,
                )
                os_results.append(os_result)

                if progress_callback:
                    progress_callback(i + 1, len(windows))

            except Exception as e:
                logger.error(f"Error validating window {i}: {e}")
                continue

        # Aggregate results
        result = self._aggregate_results(is_results, os_results)
        result.num_periods = len(is_results)
        result.total_days = sum(len(r.equity_curve) for r in os_results)
        result.recommendations = self._generate_recommendations(result)

        return result

    def _generate_rolling_windows(
        self, data: pd.DataFrame
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Generate rolling train/test windows from data.

        Args:
            data: Historical price data

        Returns:
            List of (train_data, test_data) tuples

        Raises:
            ValueError: If insufficient data to generate any windows
        """
        windows = []

        # Convert months to approximate days
        train_days = self.config.train_period_months * 21  # ~21 trading days/month
        test_days = self.config.test_period_months * 21
        step_days = self.config.step_months * 21

        # Check if we have enough data for at least one window
        min_required = train_days + test_days
        if len(data) < min_required:
            raise ValueError(
                f"Insufficient data: need at least {min_required} rows "
                f"({self.config.train_period_months} months train + "
                f"{self.config.test_period_months} months test), "
                f"got {len(data)} rows"
            )

        # Generate windows
        start_idx = 0
        while True:
            train_end = start_idx + train_days
            test_start = train_end
            test_end = test_start + test_days

            # Check if we have enough data
            if test_end > len(data):
                break

            train_data = data.iloc[start_idx:train_end]
            test_data = data.iloc[test_start:test_end]

            # Check minimum observations
            if len(train_data) >= self.config.min_observations:
                windows.append((train_data, test_data))

            # Roll forward
            start_idx += step_days

        return windows

    def _test_period(
        self,
        strategy_factory: Callable[[Dict[str, Any]], Any],
        params: Dict[str, Any],
        data: pd.DataFrame,
        is_in_sample: bool,
        period_id: int,
    ) -> PeriodResult:
        """
        Test strategy on a single period.

        Args:
            strategy_factory: Strategy factory function
            params: Strategy parameters
            data: Price data for the period
            is_in_sample: Whether this is IS or OS testing
            period_id: Period identifier

        Returns:
            PeriodResult with performance metrics
        """
        # Create and run strategy
        strategy_factory(params)

        # Run backtest (this would call the actual backtesting engine)
        # For now, we'll create a placeholder result
        # In production, this would integrate with the robust backtesting engine

        result = PeriodResult(
            start_date=data.index[0].date(),
            end_date=data.index[-1].date(),
            is_in_sample=is_in_sample,
            parameters=params,
        )

        # Placeholder: In production, extract real metrics from backtest
        # result.total_trades = backtest.total_trades
        # result.total_return = backtest.total_return
        # etc.

        return result

    def _aggregate_results(
        self,
        is_results: List[PeriodResult],
        os_results: List[PeriodResult],
    ) -> WalkForwardResult:
        """
        Aggregate results across all periods.

        Args:
            is_results: List of in-sample results
            os_results: List of out-of-sample results

        Returns:
            WalkForwardResult with aggregated metrics
        """
        result = WalkForwardResult(
            is_results=is_results,
            os_results=os_results,
        )

        # Calculate aggregate IS metrics
        result.is_performance = self._calculate_aggregate_metrics(is_results)

        # Calculate aggregate OS metrics
        result.os_performance = self._calculate_aggregate_metrics(os_results)

        # Calculate IS/OS ratio (degradation metric)
        result.is_os_ratio = self._calculate_is_os_ratio(result)

        # Calculate consistency score
        result.consistency_score = self._calculate_consistency_score(os_results)

        return result

    def _calculate_aggregate_metrics(self, results: List[PeriodResult]) -> Dict[str, Any]:
        """
        Calculate aggregate performance metrics from period results.

        Args:
            results: List of period results

        Returns:
            Dictionary of aggregate metrics
        """
        if not results:
            return {}

        metrics = {
            "total_trades": sum(r.total_trades for r in results),
            "avg_return": Decimal(str(np.mean([float(r.total_return) for r in results]))),
            "std_return": Decimal(str(np.std([float(r.total_return) for r in results]))),
            "median_return": Decimal(str(np.median([float(r.total_return) for r in results]))),
        }

        # Calculate Sharpe ratio (simplified)
        if metrics["std_return"] > 0:
            # Assuming 2% annual risk-free rate
            risk_free = Decimal("0.02")
            annual_return = metrics["avg_return"] * Decimal("12")  # Monthly to annual
            annual_std = metrics["std_return"] * Decimal("12").sqrt()
            metrics["sharpe_ratio"] = (annual_return - risk_free) / annual_std
        else:
            metrics["sharpe_ratio"] = Decimal("0")

        # Calculate max drawdown across all periods
        all_equity = []
        for r in results:
            all_equity.extend([float(eq[1]) for eq in r.equity_curve])

        if all_equity:
            equity_series = pd.Series(all_equity)
            rolling_max = equity_series.expanding().max()
            drawdown = (equity_series - rolling_max) / rolling_max
            metrics["max_drawdown"] = Decimal(str(drawdown.min()))
        else:
            metrics["max_drawdown"] = Decimal("0")

        # Calculate win rate
        total_trades = metrics["total_trades"]
        winning_trades = sum(r.total_trades * (r.win_rate / Decimal("100")) for r in results)
        if total_trades > 0:
            metrics["win_rate"] = Decimal("100") * winning_trades / total_trades
        else:
            metrics["win_rate"] = Decimal("0")

        # Calculate profit factor
        Decimal("0")
        Decimal("0")
        for r in results:
            if r.profit_factor:
                # Approximate from profit factor
                continue

        metrics["total_return"] = metrics["avg_return"]

        return metrics

    def _calculate_is_os_ratio(self, result: WalkForwardResult) -> Decimal:
        """
        Calculate IS/OS performance ratio (degradation metric).

        Args:
            result: Walk-forward result

        Returns:
            IS/OS ratio (OS/IS, values < 1 indicate degradation)
        """
        is_sharpe = result.is_performance.get("sharpe_ratio", Decimal("0"))
        os_sharpe = result.os_performance.get("sharpe_ratio", Decimal("0"))

        if is_sharpe > 0:
            return os_sharpe / is_sharpe
        return Decimal("0")

    def _calculate_consistency_score(self, os_results: List[PeriodResult]) -> Decimal:
        """
        Calculate consistency score across OS periods.

        A higher score indicates more consistent performance.

        Args:
            os_results: List of out-of-sample results

        Returns:
            Consistency score (0-100)
        """
        if not os_results:
            return Decimal("0")

        # Calculate coefficient of variation of returns
        returns = [float(r.total_return) for r in os_results]
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if mean_return == 0:
            return Decimal("0")

        cv = std_return / abs(mean_return)

        # Convert CV to consistency score (0-100)
        # Lower CV = higher consistency
        consistency = max(0, 100 * (1 - cv))

        return Decimal(str(consistency))

    def _generate_recommendations(self, result: WalkForwardResult) -> List[str]:
        """
        Generate actionable recommendations based on validation results.

        Args:
            result: Walk-forward validation result

        Returns:
            List of recommendations
        """
        recommendations = []

        # Check degradation
        degradation_summary = result.get_degradation_summary()
        sharpe_degradation = degradation_summary.get("sharpe_degradation", Decimal("0"))

        if sharpe_degradation < Decimal("0.5"):
            recommendations.append(
                "SEVERE: OS Sharpe is less than 50% of IS Sharpe. "
                "Strategy is likely overfitted. Consider simplifying parameters."
            )
        elif sharpe_degradation < Decimal("0.7"):
            recommendations.append(
                "MODERATE: OS Sharpe is less than 70% of IS Sharpe. "
                "Some overfitting detected. Review parameter complexity."
            )
        elif sharpe_degradation < Decimal("0.85"):
            recommendations.append(
                "MILD: OS Sharpe is less than 85% of IS Sharpe. "
                "Minor overfitting. Monitor closely."
            )

        # Check consistency
        if result.consistency_score < Decimal("50"):
            recommendations.append(
                "LOW CONSISTENCY: Out-of-sample performance varies significantly "
                "across periods. Strategy may be regime-dependent."
            )
        elif result.consistency_score > Decimal("80"):
            recommendations.append(
                "HIGH CONSISTENCY: Strategy performs consistently across periods. "
                "This is a positive sign for robustness."
            )

        # Check number of periods
        if result.num_periods < 5:
            recommendations.append(
                "LOW SAMPLE SIZE: Fewer than 5 validation periods. "
                "Consider using longer data history or shorter windows."
            )

        # Check win rate
        os_win_rate = result.os_performance.get("win_rate", Decimal("0"))
        if os_win_rate < Decimal("40"):
            recommendations.append(
                "LOW WIN RATE: Out-of-sample win rate below 40%. "
                "Review strategy logic and risk management."
            )

        if not recommendations:
            recommendations.append(
                "VALIDATION PASSED: Strategy shows good out-of-sample performance "
                "with minimal degradation."
            )

        return recommendations


class RollingWindowOptimizer:
    """
    Optimizer for walk-forward validation with rolling windows.

    This class handles parameter optimization on rolling windows,
    ensuring that optimization is always done on in-sample data only.
    """

    def __init__(
        self,
        optimization_metric: str = "sharpe_ratio",
        maximize: bool = True,
    ):
        """
        Initialize rolling window optimizer.

        Args:
            optimization_metric: Metric to optimize (e.g., 'sharpe_ratio', 'total_return')
            maximize: Whether to maximize or minimize the metric
        """
        self.optimization_metric = optimization_metric
        self.maximize = maximize

    def optimize(
        self,
        strategy_factory: Callable[[Dict[str, Any]], Any],
        param_grid: Dict[str, List[Any]],
        data: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        Optimize strategy parameters on in-sample data.

        Args:
            strategy_factory: Strategy factory function
            param_grid: Parameter grid for optimization
            data: In-sample price data

        Returns:
            Best parameter combination
        """
        # Generate all parameter combinations
        param_combinations = self._generate_param_combinations(param_grid)

        best_score = None
        best_params = None

        for params in param_combinations:
            try:
                # Test strategy with these parameters
                strategy = strategy_factory(params)
                score = self._evaluate_strategy(strategy, data)

                # Update best if improvement
                if best_score is None:
                    best_score = score
                    best_params = params
                elif self.maximize:
                    if score > best_score:
                        best_score = score
                        best_params = params
                else:
                    if score < best_score:
                        best_score = score
                        best_params = params

            except Exception as e:
                logger.warning(f"Error evaluating params {params}: {e}")
                continue

        if best_params is None:
            # Fallback to first combination
            best_params = param_combinations[0] if param_combinations else {}

        return best_params

    def _generate_param_combinations(
        self, param_grid: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate all combinations of parameters from grid.

        Args:
            param_grid: Parameter grid

        Returns:
            List of parameter dictionaries
        """
        import itertools

        keys = list(param_grid.keys())
        values = list(param_grid.values())

        combinations = list(itertools.product(*values))

        return [dict(zip(keys, combo)) for combo in combinations]

    def _evaluate_strategy(self, strategy: Any, data: pd.DataFrame) -> float:
        """
        Evaluate strategy and return optimization metric.

        Args:
            strategy: Strategy instance
            data: Price data

        Returns:
            Metric value to optimize
        """
        # This would integrate with the backtesting engine
        # For now, return a placeholder
        return 0.0


def calculate_degradation(is_value: float, os_value: float) -> float:
    """
    Calculate degradation ratio between in-sample and out-of-sample values.

    Args:
        is_value: In-sample value
        os_value: Out-of-sample value

    Returns:
        Degradation ratio (OS/IS). Values < 1 indicate degradation.
    """
    if is_value == 0:
        return 0.0
    return os_value / is_value


def calculate_consistency_score(values: List[float]) -> float:
    """
    Calculate consistency score for a list of values.

    Higher score = more consistent (lower coefficient of variation).

    Args:
        values: List of values

    Returns:
        Consistency score (0-100)
    """
    if not values:
        return 0.0

    mean_val = np.mean(values)
    std_val = np.std(values)

    if mean_val == 0:
        return 0.0

    cv = std_val / abs(mean_val)
    consistency = max(0, 100 * (1 - cv))

    return consistency
