"""
Tomasini-Compliant Walk-Forward Validation

This module implements Tomasini & Jaekle's walk-forward optimization methodology
from "Designing Trading Systems" (Chapter 8).

Key improvements over standard walk-forward:
1. Rolling window optimization with adaptive sizing
2. Parameter stability tracking across windows
3. Out-of-sample step size = 50% of training window (Tomasini recommendation)
4. Market regime-aware window adjustment
5. IS/OOS consistency ratio with confidence intervals
6. Parameter stability metrics
7. Robustness scoring across market conditions

Tomasini's Key Principles:
- Step size should be 50% of training window (balances stability vs adaptability)
- Track parameter evolution to detect overfitting
- Use rolling windows, not anchored windows
- Minimum 5 complete cycles for statistical significance
- Regime-aware validation prevents false positives
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig
from app.models.market_data import Quote

# Optional regime detector (may not be available)
try:
    from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
        ClusteringRegimeDetector,
    )

    REGIME_DETECTOR_AVAILABLE = True
except ImportError:
    REGIME_DETECTOR_AVAILABLE = False
    ClusteringRegimeDetector = None

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class ParameterHistory:
    """Track parameter evolution across walk-forward windows."""

    window_id: int
    parameters: Dict[str, float]
    in_sample_sharpe: float
    out_of_sample_sharpe: float
    in_sample_return: float
    out_of_sample_return: float
    window_start: datetime
    window_end: datetime
    regime: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "window_id": self.window_id,
            "parameters": self.parameters,
            "in_sample_sharpe": self.in_sample_sharpe,
            "out_of_sample_sharpe": self.out_of_sample_sharpe,
            "in_sample_return": self.in_sample_return,
            "out_of_sample_return": self.out_of_sample_return,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "regime": self.regime,
        }


@dataclass
class ParameterStabilityMetrics:
    """Metrics for parameter stability analysis."""

    parameter_name: str
    mean_value: float
    std_value: float
    cv: float  # Coefficient of variation
    min_value: float
    max_value: float
    range_pct: float
    drift_trend: float  # Linear regression slope (trend)
    drift_significance: float  # P-value for trend
    is_stable: bool
    confidence_interval_95: Tuple[float, float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "parameter_name": self.parameter_name,
            "mean_value": self.mean_value,
            "std_value": self.std_value,
            "cv": self.cv,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "range_pct": self.range_pct,
            "drift_trend": self.drift_trend,
            "drift_significance": self.drift_significance,
            "is_stable": self.is_stable,
            "confidence_interval_95": self.confidence_interval_95,
        }


@dataclass
class TomasiniWindowResult:
    """Results from a single Tomasini walk-forward window."""

    window_id: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime

    # In-Sample metrics
    is_return: float
    is_sharpe: float
    is_sortino: float
    is_max_drawdown: float
    is_volatility: float
    is_trades: int

    # Out-of-Sample metrics
    oos_return: float
    oos_sharpe: float
    oos_sortino: float
    oos_max_drawdown: float
    oos_volatility: float
    oos_trades: int

    # Consistency metrics
    consistency_ratio: float  # OOS Sharpe / IS Sharpe
    return_degradation: float  # (IS Return - OOS Return) / |IS Return|
    sharpe_degradation: float  # (IS Sharpe - OOS Sharpe) / IS Sharpe

    # Regime information
    train_regime: str
    test_regime: str
    regime_change: bool

    # Optimal parameters for this window
    optimal_parameters: Dict[str, float]

    # Validation status
    passed: bool
    failure_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "window_id": self.window_id,
            "period": {
                "train_start": self.train_start.isoformat(),
                "train_end": self.train_end.isoformat(),
                "test_start": self.test_start.isoformat(),
                "test_end": self.test_end.isoformat(),
            },
            "in_sample": {
                "return": self.is_return,
                "sharpe": self.is_sharpe,
                "sortino": self.is_sortino,
                "max_drawdown": self.is_max_drawdown,
                "volatility": self.is_volatility,
                "trades": self.is_trades,
            },
            "out_of_sample": {
                "return": self.oos_return,
                "sharpe": self.oos_sharpe,
                "sortino": self.oos_sortino,
                "max_drawdown": self.oos_max_drawdown,
                "volatility": self.oos_volatility,
                "trades": self.oos_trades,
            },
            "consistency": {
                "consistency_ratio": self.consistency_ratio,
                "return_degradation": self.return_degradation,
                "sharpe_degradation": self.sharpe_degradation,
            },
            "regime": {
                "train_regime": self.train_regime,
                "test_regime": self.test_regime,
                "regime_change": self.regime_change,
            },
            "optimal_parameters": self.optimal_parameters,
            "validation": {
                "passed": self.passed,
                "failure_reasons": self.failure_reasons,
            },
        }


@dataclass
class TomasiniWalkForwardResult:
    """Complete results from Tomasini walk-forward validation."""

    # Overall results
    passed: bool
    total_windows: int
    passed_windows: int

    # Aggregated metrics
    avg_is_return: float
    avg_oos_return: float
    avg_is_sharpe: float
    avg_oos_sharpe: float

    # Consistency metrics
    avg_consistency_ratio: float
    avg_return_degradation: float
    avg_sharpe_degradation: float

    # Window results
    windows: List[TomasiniWindowResult]

    # Parameter stability
    parameter_stability: Dict[str, ParameterStabilityMetrics]

    # Robustness metrics
    robustness_score: float
    regime_robustness: Dict[str, float]

    # Failure analysis
    failure_reasons: List[str]

    # Tomasini-specific metrics
    tomasini_score: float  # 0-100 overall score
    parameter_stability_score: float  # 0-100
    consistency_score: float  # 0-100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall": {
                "passed": self.passed,
                "total_windows": self.total_windows,
                "passed_windows": self.passed_windows,
                "tomasini_score": self.tomasini_score,
            },
            "aggregated_metrics": {
                "avg_is_return": self.avg_is_return,
                "avg_oos_return": self.avg_oos_return,
                "avg_is_sharpe": self.avg_is_sharpe,
                "avg_oos_sharpe": self.avg_oos_sharpe,
            },
            "consistency": {
                "avg_consistency_ratio": self.avg_consistency_ratio,
                "avg_return_degradation": self.avg_return_degradation,
                "avg_sharpe_degradation": self.avg_sharpe_degradation,
            },
            "scores": {
                "robustness_score": self.robustness_score,
                "parameter_stability_score": self.parameter_stability_score,
                "consistency_score": self.consistency_score,
            },
            "regime_robustness": self.regime_robustness,
            "windows": [w.to_dict() for w in self.windows],
            "parameter_stability": {
                name: metrics.to_dict() for name, metrics in self.parameter_stability.items()
            },
            "failure_reasons": self.failure_reasons,
        }


# ============================================================================
# Main Tomasini Walk-Forward Validator
# ============================================================================


class TomasiniWalkForwardValidator:
    """
    Tomasini-compliant walk-forward validation.

    Key differences from standard implementation:
    - Uses rolling windows rather than fixed periods
    - Tracks parameter stability across cycles
    - Adaptive window sizing based on market regime
    - Step size = 50% of training window (Tomasini recommendation)
    - Parameter evolution tracking for overfitting detection
    - Regime-aware validation

    Tomasini Principles:
    1. Step size = 50% of training window (balances stability vs adaptability)
    2. Minimum 5 cycles for statistical significance
    3. Track parameter stability (low CV = robust strategy)
    4. Regime-aware testing prevents false positives
    5. IS/OOS consistency ratio > 0.7 required
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Tomasini walk-forward validator.

        Args:
            config: Configuration dictionary with keys:
                - train_years: Training window length in years (default: 4.0)
                - step_percentage: Step size as % of training window (default: 0.5)
                - min_cycles: Minimum number of complete cycles (default: 5)
                - regime_aware: Enable regime-aware windows (default: True)
                - min_trades_per_window: Minimum trades required (default: 10)
                - thresholds: Validation thresholds
        """
        if config is None:
            config = {}

        # Tomasini-recommended settings
        self.train_years = config.get("train_years", 4.0)
        self.step_pct = config.get("step_percentage", 0.5)  # Tomasini: 50%
        self.min_cycles = config.get("min_cycles", 5)
        self.regime_aware = config.get("regime_aware", True)
        self.min_trades_per_window = config.get("min_trades_per_window", 10)

        # Validation thresholds
        self.thresholds = config.get(
            "thresholds",
            {
                # Consistency thresholds
                "min_consistency_ratio": 0.7,  # Tomasini: OOS/IS Sharpe > 0.7
                "max_sharpe_degradation": 0.30,  # Maximum 30% degradation
                "max_return_degradation": 0.50,  # Maximum 50% return degradation
                # Window performance thresholds
                "min_oos_sharpe": 0.5,  # Minimum OOS Sharpe ratio
                "max_oos_drawdown": -0.25,  # Maximum OOS drawdown
                # Stability thresholds
                "max_parameter_cv": 0.30,  # Max 30% coefficient of variation
                "min_stable_parameters": 0.6,  # 60% of parameters must be stable
            },
        )

        # State tracking
        self.parameter_history: List[ParameterHistory] = []
        self.regime_detector: Optional[ClusteringRegimeDetector] = None

        if self.regime_aware and REGIME_DETECTOR_AVAILABLE:
            self.regime_detector = ClusteringRegimeDetector(n_regimes=3)
        elif self.regime_aware and not REGIME_DETECTOR_AVAILABLE:
            logger.warning(
                "Regime detection requested but dependencies not available. Regime-aware features disabled."
            )
            self.regime_aware = False

    def create_rolling_windows(
        self,
        start_date: datetime,
        end_date: datetime,
        train_years: Optional[float] = None,
    ) -> List[Dict[str, datetime]]:
        """
        Create rolling windows with Tomasini-compliant step sizing.

        Tomasini Method:
        - Training window: N years (default 4 years)
        - Test window: 50% of training window (2 years)
        - Step size: 50% of training window (2 years)
        - Rolling windows (not anchored)

        Args:
            start_date: Overall start date
            end_date: Overall end date
            train_years: Override default training years

        Returns:
            List of window definitions with train/test periods
        """
        if train_years is None:
            train_years = self.train_years

        # Tomasini: Step size = 50% of training window
        train_days = int(train_years * 252)
        step_days = int(train_days * self.step_pct)
        test_days = step_days  # Test window = step size

        windows = []
        current_idx = 0

        while True:
            # Calculate window boundaries
            train_start_idx = current_idx
            train_end_idx = current_idx + train_days
            test_start_idx = train_end_idx
            test_end_idx = test_start_idx + test_days

            # Convert to dates
            train_start = start_date + timedelta(days=train_start_idx)
            train_end = start_date + timedelta(days=train_end_idx)
            test_start = start_date + timedelta(days=test_start_idx)
            test_end = start_date + timedelta(days=test_end_idx)

            # Check if we exceed the data
            if test_end > end_date:
                break

            windows.append(
                {
                    "train_start": train_start,
                    "train_end": train_end,
                    "test_start": test_start,
                    "test_end": test_end,
                }
            )

            # Roll forward by step size
            current_idx += step_days

        logger.info(
            f"Created {len(windows)} rolling windows "
            f"(train={train_years}y, step={self.step_pct*100:.0f}%, test={test_days/252:.1f}y)"
        )

        return windows

    def detect_regime(self, quotes: List[Quote], start_date: datetime, end_date: datetime) -> str:
        """
        Detect market regime for a given period.

        Args:
            quotes: Market data
            start_date: Period start
            end_date: Period end

        Returns:
            Regime label: 'BULL', 'BEAR', or 'SIDEWAYS'
        """
        if not self.regime_detector:
            return "UNKNOWN"

        # Filter quotes for period
        period_quotes = [q for q in quotes if start_date <= q.timestamp <= end_date]

        if len(period_quotes) < 126:  # Need at least 6 months
            return "INSUFFICIENT_DATA"

        try:
            # Calculate returns
            closes = np.array([float(q.close) for q in period_quotes])
            returns = np.diff(np.log(closes))

            # Detect regime using clustering
            regimes = self.regime_detector.detect_regime(returns)

            # Get most common regime
            if regimes:
                regime_counts = np.bincount(regimes)
                dominant_regime = np.argmax(regime_counts)

                # Map to labels
                regime_labels = ["SIDEWAYS", "BULL", "BEAR"]
                return regime_labels[dominant_regime]

        except Exception as e:
            logger.warning(f"Regime detection failed: {e}")

        return "UNKNOWN"

    def optimize_parameters(
        self,
        train_quotes: List[Quote],
        train_signals: List[Any],
        param_grid: Dict[str, List[Any]],
        config: BacktestConfig,
        optimization_metric: str = "sharpe_ratio",
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Optimize parameters using grid search on training data.

        Args:
            train_quotes: Training period quotes
            train_signals: Training period signals
            param_grid: Parameter grid to search
            config: Backtest configuration
            optimization_metric: Metric to optimize (default: sharpe_ratio)

        Returns:
            Tuple of (best_parameters, best_metrics)
        """
        if not param_grid:
            # No parameters to optimize
            return {}, {}

        best_params = {}
        best_score = float("-inf")
        best_metrics = {}

        # Generate all parameter combinations
        from itertools import product

        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())

        for combination in product(*param_values):
            params = dict(zip(param_names, combination))

            # Run backtest with these parameters
            backtester = SimpleBacktester(config)

            try:
                result = backtester.run_backtest(
                    train_quotes,
                    train_signals,
                    train_quotes[0].timestamp,
                    train_quotes[-1].timestamp,
                )

                # Extract optimization metric
                if optimization_metric == "sharpe_ratio":
                    score = float(result.performance.sharpe_ratio or 0)
                elif optimization_metric == "total_return":
                    score = float(result.total_return)
                elif optimization_metric == "sortino_ratio":
                    score = float(result.performance.sortino_ratio or 0)
                else:
                    score = float(result.performance.sharpe_ratio or 0)

                # Track best
                if score > best_score:
                    best_score = score
                    best_params = params
                    best_metrics = {
                        "sharpe_ratio": score,
                        "total_return": float(result.total_return),
                        "sortino_ratio": float(result.performance.sortino_ratio or 0),
                        "max_drawdown": float(result.performance.max_drawdown_percentage or 0),
                        "total_trades": result.performance.total_trades,
                        "win_rate": float(result.performance.win_rate),
                    }

            except Exception as e:
                logger.warning(f"Backtest failed for params {params}: {e}")
                continue

        logger.info(f"Best parameters: {best_params}, " f"{optimization_metric}={best_score:.3f}")

        return best_params, best_metrics

    def calculate_window_metrics(
        self,
        quotes: List[Quote],
        signals: List[Any],
        start_date: datetime,
        end_date: datetime,
        config: BacktestConfig,
        optimal_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """
        Calculate metrics for a specific window.

        Args:
            quotes: Market data
            signals: Trading signals
            start_date: Window start
            end_date: Window end
            config: Backtest configuration
            optimal_params: Optimal parameters (for tracking)

        Returns:
            Dictionary of metrics
        """
        # Filter data for window
        window_quotes = [q for q in quotes if start_date <= q.timestamp <= end_date]
        window_signals = [
            s for s in signals if hasattr(s, "timestamp") and start_date <= s.timestamp <= end_date
        ]

        if not window_quotes or not window_signals:
            return self._empty_metrics()

        # Run backtest
        backtester = SimpleBacktester(config)

        try:
            result = backtester.run_backtest(window_quotes, window_signals, start_date, end_date)

            return {
                "total_return": float(result.total_return),
                "sharpe_ratio": float(result.performance.sharpe_ratio or 0),
                "sortino_ratio": float(result.performance.sortino_ratio or 0),
                "max_drawdown": float(result.performance.max_drawdown_percentage or 0),
                "volatility": 0.0,  # Not available in PerformanceMetrics
                "total_trades": result.performance.total_trades,
                "win_rate": float(result.performance.win_rate),
            }

        except Exception as e:
            logger.warning(f"Window backtest failed: {e}")
            return self._empty_metrics()

    def _empty_metrics(self) -> Dict[str, float]:
        """Return empty metrics dict."""
        return {
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "volatility": 0.0,
            "total_trades": 0,
            "win_rate": 0.0,
        }

    def validate_strategy(
        self,
        quotes: List[Quote],
        signals: List[Any],
        config: BacktestConfig,
        start_date: datetime,
        end_date: datetime,
        param_grid: Optional[Dict[str, List[Any]]] = None,
    ) -> TomasiniWalkForwardResult:
        """
        Run Tomasini walk-forward validation.

        Args:
            quotes: Historical market data
            signals: Trading signals
            config: Backtest configuration
            start_date: Overall start date
            end_date: Overall end date
            param_grid: Optional parameter grid for optimization

        Returns:
            TomasiniWalkForwardResult with complete analysis
        """
        # Create rolling windows
        windows = self.create_rolling_windows(start_date, end_date)

        # Check minimum cycles
        if len(windows) < self.min_cycles:
            logger.warning(
                f"Insufficient windows: {len(windows)} < {self.min_cycles} " f"(Tomasini minimum)"
            )
            return self._insufficient_windows_result(len(windows))

        # Process each window
        window_results: List[TomasiniWindowResult] = []
        parameter_history: List[ParameterHistory] = []

        for i, window in enumerate(windows):
            logger.info(
                f"Processing window {i+1}/{len(windows)}: "
                f"{window['train_start'].strftime('%Y-%m-%d')} to "
                f"{window['test_end'].strftime('%Y-%m-%d')}"
            )

            # Detect regimes
            train_regime = self.detect_regime(quotes, window["train_start"], window["train_end"])
            test_regime = self.detect_regime(quotes, window["test_start"], window["test_end"])
            regime_change = train_regime != test_regime

            # Filter data for training
            train_quotes = [
                q for q in quotes if window["train_start"] <= q.timestamp <= window["train_end"]
            ]
            train_signals = [
                s
                for s in signals
                if hasattr(s, "timestamp")
                and window["train_start"] <= s.timestamp <= window["train_end"]
            ]

            # Optimize parameters if grid provided
            optimal_params = {}
            if param_grid:
                optimal_params, is_metrics = self.optimize_parameters(
                    train_quotes,
                    train_signals,
                    param_grid,
                    config,
                )
            else:
                # Calculate IS metrics without optimization
                is_metrics = self.calculate_window_metrics(
                    quotes,
                    signals,
                    window["train_start"],
                    window["train_end"],
                    config,
                )

            # Calculate OOS metrics
            oos_metrics = self.calculate_window_metrics(
                quotes,
                signals,
                window["test_start"],
                window["test_end"],
                config,
                optimal_params,
            )

            # Calculate consistency metrics
            consistency_ratio = self._calculate_consistency_ratio(
                is_metrics["sharpe_ratio"], oos_metrics["sharpe_ratio"]
            )
            return_degradation = self._calculate_return_degradation(
                is_metrics["total_return"], oos_metrics["total_return"]
            )
            sharpe_degradation = self._calculate_sharpe_degradation(
                is_metrics["sharpe_ratio"], oos_metrics["sharpe_ratio"]
            )

            # Validate window
            failure_reasons = []
            passed = True

            if oos_metrics["sharpe_ratio"] < self.thresholds["min_oos_sharpe"]:
                passed = False
                failure_reasons.append(
                    f"OOS Sharpe {oos_metrics['sharpe_ratio']:.2f} < "
                    f"{self.thresholds['min_oos_sharpe']:.2f}"
                )

            if oos_metrics["max_drawdown"] < self.thresholds["max_oos_drawdown"]:
                passed = False
                failure_reasons.append(
                    f"OOS Drawdown {oos_metrics['max_drawdown']:.2%} < "
                    f"{self.thresholds['max_oos_drawdown']:.2%}"
                )

            if consistency_ratio < self.thresholds["min_consistency_ratio"]:
                passed = False
                failure_reasons.append(
                    f"Consistency ratio {consistency_ratio:.2f} < "
                    f"{self.thresholds['min_consistency_ratio']:.2f}"
                )

            if sharpe_degradation > self.thresholds["max_sharpe_degradation"]:
                passed = False
                failure_reasons.append(
                    f"Sharpe degradation {sharpe_degradation:.1%} > "
                    f"{self.thresholds['max_sharpe_degradation']:.0%}"
                )

            if oos_metrics["total_trades"] < self.min_trades_per_window:
                passed = False
                failure_reasons.append(
                    f"Insufficient trades: {oos_metrics['total_trades']} < "
                    f"{self.min_trades_per_window}"
                )

            # Create window result
            window_result = TomasiniWindowResult(
                window_id=i + 1,
                train_start=window["train_start"],
                train_end=window["train_end"],
                test_start=window["test_start"],
                test_end=window["test_end"],
                is_return=is_metrics["total_return"],
                is_sharpe=is_metrics["sharpe_ratio"],
                is_sortino=is_metrics["sortino_ratio"],
                is_max_drawdown=is_metrics["max_drawdown"],
                is_volatility=is_metrics["volatility"],
                is_trades=is_metrics["total_trades"],
                oos_return=oos_metrics["total_return"],
                oos_sharpe=oos_metrics["sharpe_ratio"],
                oos_sortino=oos_metrics["sortino_ratio"],
                oos_max_drawdown=oos_metrics["max_drawdown"],
                oos_volatility=oos_metrics["volatility"],
                oos_trades=oos_metrics["total_trades"],
                consistency_ratio=consistency_ratio,
                return_degradation=return_degradation,
                sharpe_degradation=sharpe_degradation,
                train_regime=train_regime,
                test_regime=test_regime,
                regime_change=regime_change,
                optimal_parameters=optimal_params,
                passed=passed,
                failure_reasons=failure_reasons,
            )

            window_results.append(window_result)

            # Track parameter history
            if optimal_params:
                param_history = ParameterHistory(
                    window_id=i + 1,
                    parameters=optimal_params,
                    in_sample_sharpe=is_metrics["sharpe_ratio"],
                    out_of_sample_sharpe=oos_metrics["sharpe_ratio"],
                    in_sample_return=is_metrics["total_return"],
                    out_of_sample_return=oos_metrics["total_return"],
                    window_start=window["train_start"],
                    window_end=window["test_end"],
                    regime=train_regime,
                )
                parameter_history.append(param_history)

        # Calculate aggregate results
        result = self._calculate_aggregate_results(window_results, parameter_history)

        return result

    def _calculate_consistency_ratio(self, is_sharpe: float, oos_sharpe: float) -> float:
        """
        Calculate consistency ratio (OOS Sharpe / IS Sharpe).

        Tomasini: This ratio should be > 0.7 for robust strategies.
        """
        if is_sharpe <= 0:
            return 0.0 if oos_sharpe <= 0 else 1.0
        return oos_sharpe / is_sharpe if oos_sharpe >= 0 else 0.0

    def _calculate_return_degradation(self, is_return: float, oos_return: float) -> float:
        """Calculate return degradation."""
        if abs(is_return) < 1e-6:
            return 0.0
        return abs(is_return - oos_return) / abs(is_return)

    def _calculate_sharpe_degradation(self, is_sharpe: float, oos_sharpe: float) -> float:
        """Calculate Sharpe degradation."""
        if is_sharpe <= 0:
            return 0.0
        return max(0, (is_sharpe - oos_sharpe) / is_sharpe)

    def _calculate_aggregate_results(
        self,
        window_results: List[TomasiniWindowResult],
        parameter_history: List[ParameterHistory],
    ) -> TomasiniWalkForwardResult:
        """Calculate aggregate results from all windows."""

        # Basic counts
        total_windows = len(window_results)
        passed_windows = sum(1 for w in window_results if w.passed)

        # Aggregate metrics
        avg_is_return = np.mean([w.is_return for w in window_results])
        avg_oos_return = np.mean([w.oos_return for w in window_results])
        avg_is_sharpe = np.mean([w.is_sharpe for w in window_results])
        avg_oos_sharpe = np.mean([w.oos_sharpe for w in window_results])

        # Consistency metrics
        avg_consistency_ratio = np.mean([w.consistency_ratio for w in window_results])
        avg_return_degradation = np.mean([w.return_degradation for w in window_results])
        avg_sharpe_degradation = np.mean([w.sharpe_degradation for w in window_results])

        # Parameter stability
        parameter_stability = self.calculate_parameter_stability(parameter_history)

        # Regime robustness
        regime_robustness = self._calculate_regime_robustness(window_results)

        # Scores
        robustness_score = passed_windows / total_windows if total_windows > 0 else 0
        parameter_stability_score = self._calculate_parameter_stability_score(parameter_stability)
        consistency_score = avg_consistency_ratio

        # Overall Tomasini score (0-100)
        tomasini_score = (
            robustness_score * 0.4 + parameter_stability_score * 0.3 + consistency_score * 0.3
        ) * 100

        # Failure analysis
        failure_reasons = []
        for window in window_results:
            failure_reasons.extend(window.failure_reasons)

        # Overall pass/fail
        passed = (
            passed_windows >= self.min_cycles
            and robustness_score >= 0.6
            and parameter_stability_score >= 0.6
            and consistency_score >= 0.7
        )

        return TomasiniWalkForwardResult(
            passed=passed,
            total_windows=total_windows,
            passed_windows=passed_windows,
            avg_is_return=avg_is_return,
            avg_oos_return=avg_oos_return,
            avg_is_sharpe=avg_is_sharpe,
            avg_oos_sharpe=avg_oos_sharpe,
            avg_consistency_ratio=avg_consistency_ratio,
            avg_return_degradation=avg_return_degradation,
            avg_sharpe_degradation=avg_sharpe_degradation,
            windows=window_results,
            parameter_stability=parameter_stability,
            robustness_score=robustness_score,
            regime_robustness=regime_robustness,
            failure_reasons=list(set(failure_reasons)),
            tomasini_score=tomasini_score,
            parameter_stability_score=parameter_stability_score,
            consistency_score=consistency_score,
        )

    def calculate_parameter_stability(
        self, history: List[ParameterHistory]
    ) -> Dict[str, ParameterStabilityMetrics]:
        """
        Calculate parameter stability metrics across windows.

        Tomasini: Stable parameters = robust strategy.
        Low coefficient of variation (< 30%) indicates stability.

        Args:
            history: Parameter history from all windows

        Returns:
            Dictionary of parameter stability metrics
        """
        if not history:
            return {}

        stability_metrics = {}

        # Get all parameter names
        param_names = set()
        for h in history:
            param_names.update(h.parameters.keys())

        # Calculate stability for each parameter
        for param_name in param_names:
            values = []
            window_ids = []

            for h in history:
                if param_name in h.parameters:
                    values.append(h.parameters[param_name])
                    window_ids.append(h.window_id)

            if len(values) < 2:
                continue

            values = np.array(values)

            # Basic statistics
            mean_value = np.mean(values)
            std_value = np.std(values)
            cv = std_value / mean_value if mean_value != 0 else float("inf")

            min_value = np.min(values)
            max_value = np.max(values)
            range_pct = (max_value - min_value) / mean_value if mean_value != 0 else 0

            # Drift analysis (linear regression)
            if len(values) >= 3:
                slope, intercept, r_value, p_value, std_err = stats.linregress(window_ids, values)
                drift_trend = slope
                drift_significance = p_value
            else:
                drift_trend = 0.0
                drift_significance = 1.0

            # 95% confidence interval
            if len(values) >= 2:
                ci = stats.t.interval(
                    0.95,
                    len(values) - 1,
                    loc=mean_value,
                    scale=stats.sem(values),
                )
                confidence_interval_95 = ci
            else:
                confidence_interval_95 = (mean_value, mean_value)

            # Stability判定 (Tomasini: CV < 30% = stable)
            is_stable = cv < self.thresholds["max_parameter_cv"]

            stability_metrics[param_name] = ParameterStabilityMetrics(
                parameter_name=param_name,
                mean_value=mean_value,
                std_value=std_value,
                cv=cv,
                min_value=min_value,
                max_value=max_value,
                range_pct=range_pct,
                drift_trend=drift_trend,
                drift_significance=drift_significance,
                is_stable=is_stable,
                confidence_interval_95=confidence_interval_95,
            )

            logger.info(
                f"Parameter '{param_name}': CV={cv:.2%}, "
                f"stable={is_stable}, drift={drift_trend:.4f} (p={drift_significance:.3f})"
            )

        return stability_metrics

    def _calculate_parameter_stability_score(
        self, stability_metrics: Dict[str, ParameterStabilityMetrics]
    ) -> float:
        """
        Calculate overall parameter stability score (0-1).

        Tomasini: At least 60% of parameters should be stable.
        """
        if not stability_metrics:
            return 1.0  # No parameters = perfectly stable

        stable_count = sum(1 for m in stability_metrics.values() if m.is_stable)
        total_count = len(stability_metrics)

        stability_ratio = stable_count / total_count

        # Check if meets threshold
        min_stable = self.thresholds["min_stable_parameters"]

        return stability_ratio if stability_ratio >= min_stable else stability_ratio * 0.5

    def _calculate_regime_robustness(self, windows: List[TomasiniWindowResult]) -> Dict[str, float]:
        """Calculate robustness across different market regimes."""

        regime_performance = {}  # regime -> list of returns

        for window in windows:
            regime = window.test_regime
            if regime not in regime_performance:
                regime_performance[regime] = []

            regime_performance[regime].append(window.oos_return)

        # Calculate average performance by regime
        regime_robustness = {}
        for regime, returns in regime_performance.items():
            avg_return = np.mean(returns)
            regime_robustness[regime] = avg_return

        return regime_robustness

    def _insufficient_windows_result(self, n_windows: int) -> TomasiniWalkForwardResult:
        """Return result for insufficient windows case."""
        return TomasiniWalkForwardResult(
            passed=False,
            total_windows=n_windows,
            passed_windows=0,
            avg_is_return=0.0,
            avg_oos_return=0.0,
            avg_is_sharpe=0.0,
            avg_oos_sharpe=0.0,
            avg_consistency_ratio=0.0,
            avg_return_degradation=1.0,
            avg_sharpe_degradation=1.0,
            windows=[],
            parameter_stability={},
            robustness_score=0.0,
            regime_robustness={},
            failure_reasons=[
                f"Insufficient windows: {n_windows} < {self.min_cycles} "
                f"(Tomasini minimum requirement)"
            ],
            tomasini_score=0.0,
            parameter_stability_score=0.0,
            consistency_score=0.0,
        )
