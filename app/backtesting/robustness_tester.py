"""
Robustness Tester for Professional Backtesting (Req #14 - HIGH PRIORITY)

Analyzes strategy robustness through:
- Parameter sensitivity analysis (±20% variation)
- Stability Maps (3D surfaces showing parameter performance)
- Start date sensitivity (12 different start dates)

Helps identify whether a strategy is genuinely robust or overfitted.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Callable, Union

import numpy as np
from scipy.interpolate import griddata

from app.backtesting.models import BacktestConfig, BacktestResult
from app.domain.models.market_data import Quote

logger = logging.getLogger(__name__)


@dataclass
class ParameterSensitivityResult:
    """Result of parameter sensitivity analysis."""

    parameter_name: str
    base_value: Union[int, float, Decimal]
    tested_values: list[Union[int, float, Decimal]]
    returns: list[float]  # Return for each parameter value
    sharpe_ratios: list[float]  # Sharpe for each parameter value
    max_drawdowns: list[float]  # Max DD for each parameter value

    # Sensitivity metrics
    return_std: float  # Std dev of returns (lower = more robust)
    return_range: float  # Max - Min return
    sharpe_std: float  # Std dev of Sharpe ratios

    # Stability assessment
    is_stable: bool  # True if variation within acceptable bounds
    stability_score: float  # 0-100 score


@dataclass
class StabilityMapPoint:
    """Single point on stability map (3D surface)."""

    param1_value: float
    param2_value: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float


@dataclass
class StabilityMapResult:
    """Result of stability map generation (3D surface)."""

    param1_name: str
    param2_name: str
    param1_range: tuple[float, float]  # (min, max)
    param2_range: tuple[float, float]  # (min, max)
    points: list[StabilityMapPoint]

    # Stability metrics
    has_plateau: bool  # True if stable plateau exists
    plateau_size: float  # Size of stable region as % of total
    best_region: dict[str, float]  # Best performing region

    # Visualization data (for 3D plotting)
    mesh_x: np.ndarray = field(default_factory=lambda: np.array([]))
    mesh_y: np.ndarray = field(default_factory=lambda: np.array([]))
    mesh_z_return: np.ndarray = field(default_factory=lambda: np.array([]))
    mesh_z_sharpe: np.ndarray = field(default_factory=lambda: np.array([]))


@dataclass
class StartDateSensitivityResult:
    """Result of start date sensitivity analysis (Req #14)."""

    start_dates: list[datetime]
    returns: list[float]
    sharpe_ratios: list[float]
    max_drawdowns: list[float]

    # Sensitivity metrics
    return_variation: float  # Std dev of returns across start dates
    return_range_pct: float  # (Max - Min) / Avg as percentage
    sharpe_variation: float

    # Robustness assessment (Req #14)
    is_robust: bool  # True if CAGR variation < 20%
    robustness_score: float  # 0-100 score


@dataclass
class RobustnessReport:
    """Complete robustness analysis report."""

    strategy_name: str
    timestamp: datetime
    parameter_sensitivity: list[ParameterSensitivityResult]
    stability_maps: list[StabilityMapResult]
    start_date_sensitivity: StartDateSensitivityResult

    # Overall assessment
    overall_robustness_score: float  # 0-100
    is_robust: bool
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class RobustnessTester:
    """
    Robustness Testing System (Req #14 - HIGH PRIORITY).

    Tests strategy robustness through:
    1. Parameter sensitivity analysis (±20% variation)
    2. Stability Maps (3D surfaces showing parameter performance)
    3. Start date sensitivity (12 different start dates)

    A robust strategy should:
    - Have low sensitivity to parameter changes
    - Show a stable plateau in performance (not a single peak)
    - Perform consistently across different start dates
    """

    def __init__(
        self,
        parameter_variation_pct: float = 0.20,  # ±20% variation (Req #14)
        min_stability_score: float = 60.0,  # Minimum score for "stable"
        max_return_variation: float = 0.20,  # Max 20% variation for robust (Req #14)
        n_start_dates: int = 12,  # 12 start dates to test (Req #14)
    ):
        """
        Initialize robustness tester.

        Args:
            parameter_variation_pct: Percentage to vary parameters (default 20%)
            min_stability_score: Minimum score for "stable" classification
            max_return_variation: Max return variation for "robust" classification
            n_start_dates: Number of start dates to test
        """
        self.parameter_variation_pct = parameter_variation_pct
        self.min_stability_score = min_stability_score
        self.max_return_variation = max_return_variation
        self.n_start_dates = n_start_dates

    def analyze_parameter_sensitivity(
        self,
        parameter_name: str,
        base_value: Union[int, float, Decimal],
        param_type: str,  # "int", "float", "decimal"
        run_backtest_fn: Callable,  # Function to run backtest with given param
        n_steps: int = 5,
    ) -> ParameterSensitivityResult:
        """
        Analyze sensitivity to a single parameter (Req #14).

        Varies parameter by ±20% and measures impact on performance.

        Args:
            parameter_name: Name of parameter to test
            base_value: Base value of parameter
            param_type: Type of parameter ("int", "float", "decimal")
            run_backtest_fn: Function that runs backtest with given param value
            n_steps: Number of steps to test

        Returns:
            ParameterSensitivityResult with sensitivity metrics
        """
        # Calculate test range (base +/- 20%)
        if param_type == "int":
            base_num = float(base_value)
            min_val_i = int(base_num * (1 - self.parameter_variation_pct))
            max_val_i = int(base_num * (1 + self.parameter_variation_pct))
            step_size = max(1, (max_val_i - min_val_i) // (n_steps - 1))
            tested_values: list[Union[int, float, Decimal]] = []
            for v in range(min_val_i, max_val_i + 1, step_size):
                tested_values.append(v)
            tested_values = tested_values[:n_steps]
        elif param_type == "float":
            base_num = float(base_value)
            min_val_f = base_num * (1 - self.parameter_variation_pct)
            max_val_f = base_num * (1 + self.parameter_variation_pct)
            float_vals = np.linspace(min_val_f, max_val_f, n_steps).tolist()
            tested_values = [float(v) for v in float_vals]
        else:  # decimal
            base_num = float(base_value)
            min_val_d = Decimal(str(base_num * (1 - self.parameter_variation_pct)))
            max_val_d = Decimal(str(base_num * (1 + self.parameter_variation_pct)))
            step = (max_val_d - min_val_d) / (n_steps - 1)
            tested_values = [min_val_d + step * i for i in range(n_steps)]

        logger.info(f"Testing parameter {parameter_name} with {len(tested_values)} values")

        results = []
        returns = []
        sharpes = []
        drawdowns = []

        for value in tested_values:
            try:
                result = run_backtest_fn({parameter_name: value})

                if isinstance(result, BacktestResult):
                    total_return = float(result.total_return)
                    sharpe = float(result.performance.sharpe_ratio or 0)
                    dd = float(result.performance.max_drawdown_percentage or 0)
                else:
                    # Assume dict-like result
                    total_return = float(result.get("total_return", 0))
                    sharpe = float(result.get("sharpe_ratio", 0))
                    dd = float(result.get("max_drawdown", 0))

                returns.append(total_return)
                sharpes.append(sharpe)
                drawdowns.append(dd)
                results.append(value)

            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.warning(f"Backtest failed for {parameter_name}={value}: {e}")
                returns.append(0.0)
                sharpes.append(0.0)
                drawdowns.append(-1.0)

        # Calculate sensitivity metrics
        return_std: float = float(np.std(returns)) if len(returns) > 1 else 0.0
        return_range = max(returns) - min(returns) if returns else 0.0
        sharpe_std: float = float(np.std(sharpes)) if len(sharpes) > 1 else 0.0

        # Assess stability
        is_stable: bool = return_std < (float(np.mean(np.abs(returns))) * 0.3 if returns else 1.0)
        stability_score: float = float(max(0, 100 - (return_std * 100)))

        return ParameterSensitivityResult(
            parameter_name=parameter_name,
            base_value=base_value,
            tested_values=tested_values,
            returns=returns,
            sharpe_ratios=sharpes,
            max_drawdowns=drawdowns,
            return_std=return_std,
            return_range=return_range,
            sharpe_std=sharpe_std,
            is_stable=is_stable,
            stability_score=stability_score,
        )

    def generate_stability_map(
        self,
        param1_name: str,
        param1_range: tuple[float, float],
        param2_name: str,
        param2_range: tuple[float, float],
        run_backtest_fn: Callable,
        n_points_per_dim: int = 10,
    ) -> StabilityMapResult:
        """
        Generate 3D stability map (Req #14).

        Creates a 3D surface showing performance across parameter combinations.
        A robust strategy shows a stable plateau, not a single sharp peak.

        Args:
            param1_name: Name of first parameter
            param1_range: (min, max) range for first parameter
            param2_name: Name of second parameter
            param2_range: (min, max) range for second parameter
            run_backtest_fn: Function that runs backtest with given params
            n_points_per_dim: Points per dimension (total = n²)

        Returns:
            StabilityMapResult with 3D surface data
        """
        param1_values = np.linspace(param1_range[0], param1_range[1], n_points_per_dim)
        param2_values = np.linspace(param2_range[0], param2_range[1], n_points_per_dim)

        points = []
        grid_data: dict[str, list[float]] = {"x": [], "y": [], "return": [], "sharpe": []}

        logger.info(
            f"Generating stability map: {len(param1_values) * len(param2_values)} combinations"
        )

        for p1 in param1_values:
            for p2 in param2_values:
                try:
                    result = run_backtest_fn({param1_name: p1, param2_name: p2})

                    if isinstance(result, BacktestResult):
                        total_return = float(result.total_return)
                        sharpe = float(result.performance.sharpe_ratio or 0)
                        dd = float(result.performance.max_drawdown_percentage or 0)
                    else:
                        total_return = float(result.get("total_return", 0))
                        sharpe = float(result.get("sharpe_ratio", 0))
                        dd = float(result.get("max_drawdown", 0))

                    point = StabilityMapPoint(
                        param1_value=float(p1),
                        param2_value=float(p2),
                        total_return=total_return,
                        sharpe_ratio=sharpe,
                        max_drawdown=dd,
                    )
                    points.append(point)

                    grid_data["x"].append(float(p1))
                    grid_data["y"].append(float(p2))
                    grid_data["return"].append(total_return)
                    grid_data["sharpe"].append(sharpe)

                except (ValueError, TypeError, KeyError, AttributeError) as e:
                    logger.warning(
                        f"Stability map failed for {param1_name}={p1}, {param2_name}={p2}: {e}"
                    )

        # Create mesh for 3D plotting
        if len(grid_data["x"]) > 0:
            x = np.array(grid_data["x"])
            y = np.array(grid_data["y"])
            z_return = np.array(grid_data["return"])
            z_sharpe = np.array(grid_data["sharpe"])

            # Create regular grid for interpolation
            xi = np.linspace(param1_range[0], param1_range[1], n_points_per_dim)
            yi = np.linspace(param2_range[0], param2_range[1], n_points_per_dim)
            xi_grid, yi_grid = np.meshgrid(xi, yi)

            # Interpolate to create smooth surface
            zi_return = griddata(
                (x, y), z_return, (xi_grid, yi_grid), method="cubic", fill_value=np.nan
            )
            zi_sharpe = griddata(
                (x, y), z_sharpe, (xi_grid, yi_grid), method="cubic", fill_value=np.nan
            )
        else:
            xi_grid = yi_grid = zi_return = zi_sharpe = np.array([])

        # Check for stable plateau
        has_plateau = self._detect_stable_plateau(points)
        plateau_size = self._calculate_plateau_size(points)

        # Find best region
        best_region = self._find_best_region(points)

        return StabilityMapResult(
            param1_name=param1_name,
            param2_name=param2_name,
            param1_range=param1_range,
            param2_range=param2_range,
            points=points,
            has_plateau=has_plateau,
            plateau_size=plateau_size,
            best_region=best_region,
            mesh_x=xi_grid,
            mesh_y=yi_grid,
            mesh_z_return=zi_return,
            mesh_z_sharpe=zi_sharpe,
        )

    def analyze_start_date_sensitivity(
        self,
        quotes: list[Quote],
        signals: list[object],
        config: BacktestConfig,
        start_date_base: datetime,
        end_date: datetime,
        run_backtest_fn: Callable,
    ) -> StartDateSensitivityResult:
        """
        Analyze sensitivity to start date (Req #14).

        Tests strategy with 12 different start dates.
        A robust strategy should not vary significantly (>20%) based on start date.

        Args:
            quotes: Historical market data
            signals: Trading signals
            config: Backtest configuration
            start_date_base: Base start date
            end_date: Common end date
            run_backtest_fn: Function to run backtest for a period

        Returns:
            StartDateSensitivityResult with sensitivity metrics
        """
        # Calculate monthly intervals for start dates
        total_months = (end_date.year - start_date_base.year) * 12 + (
            end_date.month - start_date_base.month
        )
        interval_months = max(1, total_months // self.n_start_dates)

        start_dates = []
        returns = []
        sharpes = []
        drawdowns = []

        for i in range(self.n_start_dates):
            # Calculate start date
            start_date = start_date_base + timedelta(days=i * interval_months * 30)

            # Ensure we have enough data
            if start_date >= end_date - timedelta(days=90):
                break

            try:
                # Filter data for this period
                period_quotes = [q for q in quotes if start_date <= q.timestamp <= end_date]
                period_signals = [
                    s
                    for s in signals
                    if hasattr(s, "timestamp") and start_date <= s.timestamp <= end_date
                ]

                if len(period_quotes) < 100:  # Need minimum data
                    continue

                result = run_backtest_fn(period_quotes, period_signals, start_date, end_date)

                if isinstance(result, BacktestResult):
                    total_return = float(result.total_return)
                    sharpe = float(result.performance.sharpe_ratio or 0)
                    dd = float(result.performance.max_drawdown_percentage or 0)
                else:
                    total_return = float(result.get("total_return", 0))
                    sharpe = float(result.get("sharpe_ratio", 0))
                    dd = float(result.get("max_drawdown", 0))

                start_dates.append(start_date)
                returns.append(total_return)
                sharpes.append(sharpe)
                drawdowns.append(dd)

            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.warning(f"Start date sensitivity failed for {start_date}: {e}")

        # Calculate sensitivity metrics
        return_std: float = float(np.std(returns)) if len(returns) > 1 else 0.0
        avg_return: float = float(np.mean(returns)) if returns else 0.0
        return_range_pct: float = (
            ((max(returns) - min(returns)) / abs(avg_return) * 100) if avg_return != 0 else 0.0
        )
        sharpe_variation: float = float(np.std(sharpes)) if len(sharpes) > 1 else 0.0

        # Robustness assessment (Req #14): variation < 20%
        is_robust = return_range_pct < (self.max_return_variation * 100)
        robustness_score = max(0, 100 - return_range_pct)

        return StartDateSensitivityResult(
            start_dates=start_dates,
            returns=returns,
            sharpe_ratios=sharpes,
            max_drawdowns=drawdowns,
            return_variation=return_std,
            return_range_pct=return_range_pct,
            sharpe_variation=sharpe_variation,
            is_robust=is_robust,
            robustness_score=robustness_score,
        )

    def _detect_stable_plateau(self, points: list[StabilityMapPoint]) -> bool:
        """Detect if there's a stable plateau (not just a single peak)."""
        if len(points) < 10:
            return False

        returns = [p.total_return for p in points]
        max_return = max(returns)
        threshold = max_return * 0.9  # Within 90% of max

        # Count points near peak
        near_peak = sum(1 for r in returns if r >= threshold)

        # Stable if >20% of points are near peak
        return (near_peak / len(points)) > 0.2

    def _calculate_plateau_size(self, points: list[StabilityMapPoint]) -> float:
        """Calculate size of stable plateau as percentage of total."""
        if not points:
            return 0.0

        returns = [p.total_return for p in points]
        max_return = max(returns)
        threshold = max_return * 0.9

        near_peak = sum(1 for r in returns if r >= threshold)
        return (near_peak / len(points)) * 100

    def _find_best_region(self, points: list[StabilityMapPoint]) -> dict[str, float]:
        """Find best performing region in parameter space."""
        if not points:
            return {}

        # Sort by Sharpe ratio
        sorted_points = sorted(points, key=lambda p: p.sharpe_ratio, reverse=True)

        # Top 10% of points
        top_n = max(1, len(sorted_points) // 10)
        top_points = sorted_points[:top_n]

        return {
            "avg_sharpe": float(np.mean([p.sharpe_ratio for p in top_points])),
            "avg_return": float(np.mean([p.total_return for p in top_points])),
            "param1_center": float(np.mean([p.param1_value for p in top_points])),
            "param2_center": float(np.mean([p.param2_value for p in top_points])),
            "param1_std": float(np.std([p.param1_value for p in top_points])),
            "param2_std": float(np.std([p.param2_value for p in top_points])),
        }

    def generate_robustness_report(
        self,
        strategy_name: str,
        parameter_sensitivity: list[ParameterSensitivityResult],
        stability_maps: list[StabilityMapResult],
        start_date_sensitivity: StartDateSensitivityResult,
    ) -> RobustnessReport:
        """Generate complete robustness report."""
        warnings = []
        recommendations = []

        # Check parameter sensitivity
        unstable_params = [p for p in parameter_sensitivity if not p.is_stable]
        if unstable_params:
            warnings.append(f"Unstable parameters: {[p.parameter_name for p in unstable_params]}")
            recommendations.append(
                "Consider reducing parameter sensitivity or using fewer parameters"
            )

        # Check stability maps
        no_plateau_maps = [m for m in stability_maps if not m.has_plateau]
        if no_plateau_maps:
            warnings.append("No stable plateau found in parameter space")
            recommendations.append("Strategy may be overfitted - lacks robust parameter region")

        # Check start date sensitivity
        if not start_date_sensitivity.is_robust:
            warnings.append(
                f"High start date sensitivity: {start_date_sensitivity.return_range_pct:.1f}% variation"
            )
            recommendations.append(
                "Strategy performance depends heavily on start date - not robust"
            )

        # Calculate overall score
        param_score: float = (
            float(np.mean([p.stability_score for p in parameter_sensitivity]))
            if parameter_sensitivity
            else 50.0
        )
        map_score = 100.0 if not no_plateau_maps else 50.0
        date_score = start_date_sensitivity.robustness_score

        overall_score: float = param_score * 0.4 + map_score * 0.3 + date_score * 0.3
        is_robust: bool = overall_score >= self.min_stability_score

        return RobustnessReport(
            strategy_name=strategy_name,
            timestamp=datetime.now(),
            parameter_sensitivity=parameter_sensitivity,
            stability_maps=stability_maps,
            start_date_sensitivity=start_date_sensitivity,
            overall_robustness_score=overall_score,
            is_robust=is_robust,
            warnings=warnings,
            recommendations=recommendations,
        )
