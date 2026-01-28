"""
Baseline vs Optimization Comparison Reporter

Generates professional comparison reports between baseline and optimized strategies.
Produces HTML reports with interactive Plotly charts and detailed analysis.

Key Features:
- Side-by-side metric comparison
- Statistical significance testing
- Parameter impact analysis
- Interactive visualizations
- Implementation recommendations
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from jinja2 import Template

from app.core.models.input_profile import InputProfile

logger = logging.getLogger(__name__)


@dataclass
class ComparisonMetrics:
    """Comparison metrics between baseline and optimized results."""

    sharpe_ratio: Tuple[float, float]  # (baseline, optimized)
    total_return: Tuple[float, float]
    max_drawdown: Tuple[float, float]
    win_rate: Tuple[float, float]
    profit_factor: Tuple[float, float]
    sortino_ratio: Tuple[float, float]
    calmar_ratio: Tuple[float, float]
    omega_ratio: Tuple[float, float]

    # Out-of-sample metrics (if available)
    oos_sharpe: Optional[Tuple[float, float]] = None
    is_oos_ratio: Optional[float] = None


@dataclass
class ParameterChange:
    """A parameter that changed between baseline and optimization."""

    name: str
    before: Any
    after: Any
    impact: Optional[str] = None
    sensitivity: Optional[float] = None


@dataclass
class StatisticalTest:
    """Result of a statistical significance test."""

    metric_name: str
    baseline_mean: float
    optimized_mean: float
    p_value: float
    is_significant: bool
    test_statistic: float


@dataclass
class Recommendation:
    """Recommendation for strategy selection."""

    decision: str  # "USE_OPTIMIZED", "CONSIDER_OPTIMIZED", "USE_BASELINE"
    rationale: str
    confidence: float  # 0-1
    conditions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class BaselineOptimizationReporter:
    """
    Professional reporter for baseline vs optimization comparison.

    Generates HTML reports with:
    - Executive summary with key improvements
    - Detailed metrics comparison
    - Statistical significance analysis
    - Parameter impact analysis
    - Interactive charts (Plotly)
    - Implementation recommendations
    """

    def __init__(self, template_path: Optional[str] = None):
        """
        Initialize reporter.

        Args:
            template_path: Path to Jinja2 template. If None, uses default template.
        """
        if template_path is None:
            template_path = (
                Path(__file__).parent / "templates" / "baseline_optimization_report.html"
            )

        self.template_path = Path(template_path)

        # Load template
        try:
            with open(self.template_path, "r", encoding="utf-8") as f:
                self.template = Template(f.read())
        except FileNotFoundError:
            logger.error(f"Template not found: {template_path}")
            raise

        logger.info(f"BaselineOptimizationReporter initialized with template: {self.template_path}")

    def generate_report(
        self,
        profile: InputProfile,
        baseline_results: Dict[str, Any],
        optimization_results: Dict[str, Any],
        comparison: Optional[Dict[str, Any]] = None,
        walk_forward_results: Optional[Dict[str, Any]] = None,
        sensitivity_results: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate HTML comparison report.

        Args:
            profile: Input profile with trading parameters
            baseline_results: Baseline backtest results
            optimization_results: Optimized backtest results
            comparison: Pre-computed comparison metrics (optional)
            walk_forward_results: Walk-forward validation results (optional)
            sensitivity_results: Parameter sensitivity results (optional)

        Returns:
            HTML report as string
        """
        # Extract metrics
        baseline_metrics = self._extract_metrics(baseline_results)
        optimized_metrics = self._extract_metrics(optimization_results)

        # Calculate comparison if not provided
        if comparison is None:
            comparison = self._calculate_comparison(baseline_metrics, optimized_metrics)

        # Calculate statistical significance
        significance_tests = self._perform_significance_tests(
            baseline_results, optimization_results
        )

        # Extract parameter changes
        parameter_changes = self._extract_parameter_changes(
            baseline_results.get("parameters", {}),
            optimization_results.get("parameters", {}),
            comparison,
        )

        # Generate recommendation
        recommendation = self._generate_recommendation(
            baseline_metrics, optimized_metrics, comparison, walk_forward_results
        )

        # Prepare chart data
        chart_data = self._prepare_chart_data(
            baseline_results, optimization_results, walk_forward_results, sensitivity_results
        )

        # Render template
        html_content = self.template.render(
            # Profile info
            strategy_name=profile.objetivo_inversion.value.replace("_", " ").title(),
            profile_name=profile.risk_tolerance.value.title(),
            initial_capital=f"{profile.capital_initial:,.0f}",
            period_start=baseline_results.get("start_date", "N/A"),
            period_end=baseline_results.get("end_date", "N/A"),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            # Recommendation
            recommendation_class=self._get_recommendation_class(recommendation.decision),
            recommendation_icon=self._get_recommendation_icon(recommendation.decision),
            recommendation_text=recommendation.decision.replace("_", " ").title(),
            recommendation_rationale=recommendation.rationale,
            # Key metrics
            sharpe_improvement=f"{comparison['sharpe_improvement']:.1f}",
            return_improvement=f"{comparison['return_improvement']:.1f}",
            dd_change=f"{comparison['dd_change']:.1f}",
            winrate_improvement=f"{comparison['winrate_improvement']:.1f}",
            baseline_sharpe=f"{baseline_metrics['sharpe_ratio']:.2f}",
            optimized_sharpe=f"{optimized_metrics['sharpe_ratio']:.2f}",
            baseline_return=f"{baseline_metrics['total_return']:.2f}",
            optimized_return=f"{optimized_metrics['total_return']:.2f}",
            baseline_dd=f"{baseline_metrics['max_drawdown']:.2f}",
            optimized_dd=f"{optimized_metrics['max_drawdown']:.2f}",
            baseline_winrate=f"{baseline_metrics['win_rate']:.1f}",
            optimized_winrate=f"{optimized_metrics['win_rate']:.1f}",
            # Metric cards styling
            sharpe_card_class=self._get_card_class(
                comparison["sharpe_improvement"], higher_better=True
            ),
            return_card_class=self._get_card_class(
                comparison["return_improvement"], higher_better=True
            ),
            dd_card_class=self._get_card_class(comparison["dd_change"], higher_better=False),
            winrate_card_class=self._get_card_class(
                comparison["winrate_improvement"], higher_better=True
            ),
            # Key metrics table
            key_metrics=self._prepare_key_metrics_table(
                baseline_metrics, optimized_metrics, significance_tests
            ),
            # Parameters
            parameters=parameter_changes,
            # Drawdown metrics
            drawdown_metrics=self._prepare_drawdown_metrics(baseline_metrics, optimized_metrics),
            # Risk metrics
            risk_metrics=self._prepare_risk_metrics_table(baseline_metrics, optimized_metrics),
            # Walk-forward
            has_walk_forward=walk_forward_results is not None,
            walk_forward_metrics=(
                self._prepare_walk_forward_metrics(walk_forward_results)
                if walk_forward_results
                else []
            ),
            # Sensitivity
            has_sensitivity=sensitivity_results is not None,
            # Implementation
            implementation_decision=recommendation.decision.replace("_", " ").title(),
            implementation_steps=recommendation.conditions,
            recommended_config=self._format_recommended_config(optimization_results),
            monitoring_checks=recommendation.warnings,
            # Charts (convert datetime objects to strings for JSON serialization)
            chart_data=json.dumps(chart_data, default=str),
        )

        logger.info("Generated baseline vs optimization comparison report")
        return html_content

    def save_report(self, html: str, output_path: str) -> None:
        """
        Save HTML report to file.

        Args:
            html: HTML content
            output_path: Path to save report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"Report saved to: {output_path}")

    def generate_pdf(self, html: str, output_path: Optional[str] = None) -> bytes:
        """
        Generate PDF from HTML report.

        Note: This requires a headless browser or PDF library.
        Placeholder for future implementation.

        Args:
            html: HTML content
            output_path: Optional path to save PDF

        Returns:
            PDF bytes
        """
        # TODO: Implement PDF generation using weasyprint or similar
        logger.warning("PDF generation not yet implemented")
        return b""

    def _extract_metrics(self, results: Dict[str, Any]) -> Dict[str, float]:
        """Extract key metrics from results dictionary."""
        performance = results.get("performance", {})
        equity_curve = results.get("equity_curve", [])

        # Calculate returns if not provided
        if not equity_curve:
            total_return = 0.0
        else:
            initial = equity_curve[0][1] if isinstance(equity_curve[0], tuple) else equity_curve[0]
            final = equity_curve[-1][1] if isinstance(equity_curve[-1], tuple) else equity_curve[-1]
            total_return = (final - initial) / initial if initial > 0 else 0.0

        # Drawdown is stored as negative (e.g., -15%), but we want it as positive for comparisons
        max_dd = float(performance.get("max_drawdown_percentage", 0.0))
        if max_dd < 0:
            max_dd = abs(max_dd)

        return {
            "sharpe_ratio": float(performance.get("sharpe_ratio", 0.0)),
            "total_return": float(performance.get("total_return", total_return * 100)),
            "max_drawdown": max_dd,  # Store as positive value
            "win_rate": float(performance.get("win_rate", 0.0)),
            "profit_factor": float(performance.get("profit_factor", 0.0)),
            "sortino_ratio": float(performance.get("sortino_ratio", 0.0)),
            "calmar_ratio": float(performance.get("calmar_ratio", 0.0)),
            "omega_ratio": float(performance.get("omega_ratio", 0.0)),
            # Additional metrics that were missing
            "avg_drawdown": float(performance.get("avg_drawdown", 0.0)),
            "ulcer_index": float(performance.get("ulcer_index", 0.0)),
            "volatility": float(performance.get("volatility", 0.0)),
        }

    def _calculate_comparison(
        self, baseline: Dict[str, float], optimized: Dict[str, float]
    ) -> Dict[str, Any]:
        """Calculate comparison metrics."""
        return {
            "sharpe_improvement": self._pct_improvement(
                baseline["sharpe_ratio"], optimized["sharpe_ratio"], higher_better=True
            ),
            "return_improvement": self._pct_improvement(
                baseline["total_return"], optimized["total_return"], higher_better=True
            ),
            "dd_change": self._pct_improvement(
                baseline["max_drawdown"], optimized["max_drawdown"], higher_better=False
            ),
            "winrate_improvement": self._pct_improvement(
                baseline["win_rate"], optimized["win_rate"], higher_better=True
            ),
        }

    def _pct_improvement(
        self, baseline: float, optimized: float, higher_better: bool = True
    ) -> float:
        """Calculate percentage improvement."""
        if baseline == 0:
            return 0.0

        change = ((optimized - baseline) / abs(baseline)) * 100

        # For metrics where lower is better (like drawdown), invert the sign
        # This way, positive values always indicate improvement
        if not higher_better:
            change = -change

        # Round to 2 decimal places for consistent test assertions
        return round(change, 2)

    def _perform_significance_tests(
        self, baseline_results: Dict, optimized_results: Dict
    ) -> Dict[str, StatisticalTest]:
        """Perform statistical significance tests."""
        tests = {}

        # Extract returns series for testing
        baseline_returns = self._extract_returns_series(baseline_results)
        optimized_returns = self._extract_returns_series(optimized_results)

        if len(baseline_returns) > 0 and len(optimized_returns) > 0:
            # Perform t-test for Sharpe ratio difference
            tests["sharpe_ratio"] = self._t_test_means(
                baseline_returns, optimized_returns, "sharpe_ratio"
            )

            # Test for total return difference
            tests["total_return"] = self._t_test_means(
                baseline_returns, optimized_returns, "total_return"
            )

        return tests

    def _extract_returns_series(self, results: Dict) -> np.ndarray:
        """Extract returns series from results."""
        equity_curve = results.get("equity_curve", [])

        if not equity_curve:
            return np.array([])

        # Convert to returns
        values = [point[1] if isinstance(point, tuple) else point for point in equity_curve]
        values = np.array(values)

        returns = np.diff(values) / values[:-1]
        returns = returns[~np.isnan(returns)]

        return returns

    def _t_test_means(
        self, baseline_returns: np.ndarray, optimized_returns: np.ndarray, metric_name: str
    ) -> StatisticalTest:
        """
        Perform paired t-test for difference in means.

        Uses ttest_rel (paired) because both strategies are tested on the
        same underlying market data, making them paired samples rather
        than independent samples.
        """
        from scipy import stats

        baseline_mean = np.mean(baseline_returns)
        optimized_mean = np.mean(optimized_returns)

        # Ensure arrays have the same length for paired test
        min_len = min(len(baseline_returns), len(optimized_returns))
        baseline_returns_trimmed = baseline_returns[:min_len]
        optimized_returns_trimmed = optimized_returns[:min_len]

        # Perform PAIRED t-test (ttest_rel) since both tests use the same market data
        # This is more appropriate than ttest_ind (independent) for this use case
        t_stat, p_value = stats.ttest_rel(optimized_returns_trimmed, baseline_returns_trimmed)

        # Significant at 95% confidence level
        is_significant = p_value < 0.05

        return StatisticalTest(
            metric_name=metric_name,
            baseline_mean=float(baseline_mean),
            optimized_mean=float(optimized_mean),
            p_value=float(p_value),
            is_significant=is_significant,
            test_statistic=float(t_stat),
        )

    def _extract_parameter_changes(
        self,
        baseline_params: Dict[str, Any],
        optimized_params: Dict[str, Any],
        comparison: Dict[str, Any],
    ) -> List[ParameterChange]:
        """Extract and analyze parameter changes."""
        changes = []

        for key in set(list(baseline_params.keys()) + list(optimized_params.keys())):
            baseline_val = baseline_params.get(key)
            optimized_val = optimized_params.get(key)

            if baseline_val != optimized_val:
                # Determine impact
                impact = self._estimate_parameter_impact(
                    key, baseline_val, optimized_val, comparison
                )

                changes.append(
                    ParameterChange(
                        name=key,
                        before=baseline_val,
                        after=optimized_val,
                        impact=impact,
                    )
                )

        return changes

    def _estimate_parameter_impact(
        self, param_name: str, before: Any, after: Any, comparison: Dict[str, Any]
    ) -> str:
        """Estimate the impact of a parameter change."""
        # Simple heuristic-based impact estimation
        if "lookback" in param_name.lower() or "window" in param_name.lower():
            if isinstance(before, (int, float)) and isinstance(after, (int, float)):
                if after > before:
                    return "Longer period may reduce noise but increase lag"
                else:
                    return "Shorter period may increase responsiveness but more noise"

        elif "threshold" in param_name.lower():
            if isinstance(before, (int, float)) and isinstance(after, (int, float)):
                if after > before:
                    return "Higher threshold reduces trade frequency, may improve win rate"
                else:
                    return "Lower threshold increases trade frequency"

        elif "size" in param_name.lower() or "position" in param_name.lower():
            return "May affect risk-adjusted returns and drawdown"

        return "Impact analyzed in optimization results"

    def _generate_recommendation(
        self,
        baseline_metrics: Dict[str, float],
        optimized_metrics: Dict[str, float],
        comparison: Dict[str, Any],
        walk_forward_results: Optional[Dict[str, Any]],
    ) -> Recommendation:
        """
        Generate recommendation with confidence score.

        Logic:
        - USE_OPTIMIZED: Sharpe > 1.2x baseline AND OOS Sharpe > 0.8x IS Sharpe
        - CONSIDER_OPTIMIZED: Sharpe > 1.05x baseline but conditions not fully met
        - USE_BASELINE: Optimization doesn't significantly improve performance
        """
        baseline_sharpe = baseline_metrics["sharpe_ratio"]
        optimized_sharpe = optimized_metrics["sharpe_ratio"]
        sharpe_improvement = comparison["sharpe_improvement"]

        # Check walk-forward validation
        oos_stability = True
        if walk_forward_results:
            is_sharpe = walk_forward_results.get("is_sharpe", optimized_sharpe)
            oos_sharpe = walk_forward_results.get("oos_sharpe", optimized_sharpe * 0.7)
            oos_stability = oos_sharpe > 0.8 * is_sharpe if is_sharpe > 0 else False

        decision = "USE_BASELINE"
        rationale = ""
        confidence = 0.5
        conditions = []
        warnings = []

        # Decision logic
        if optimized_sharpe > 1.2 * baseline_sharpe and oos_stability:
            decision = "USE_OPTIMIZED"
            rationale = (
                f"Optimized strategy shows {sharpe_improvement:.1f}% Sharpe improvement "
                f"with stable out-of-sample performance. Recommended for deployment."
            )
            confidence = 0.85
            conditions = [
                "Deploy with paper trading for 2-4 weeks",
                "Monitor OOS performance closely",
                "Scale to full capital if metrics hold",
            ]
            warnings = [
                "Monitor maximum drawdown in live conditions",
                "Check slippage impact on optimized parameters",
                "Validate during different market regimes",
            ]

        elif optimized_sharpe > 1.05 * baseline_sharpe:
            decision = "CONSIDER_OPTIMIZED"
            rationale = (
                f"Optimized strategy shows {sharpe_improvement:.1f}% Sharpe improvement. "
                "Consider deployment with caution and extended validation."
            )
            confidence = 0.65
            conditions = [
                "Extended paper trading period (4-8 weeks) recommended",
                "Validate across different market conditions",
                "Consider hybrid approach (50% baseline, 50% optimized)",
            ]
            warnings = [
                "Improvement may not be statistically significant",
                "Monitor for overfitting indicators",
                "Prepare to revert to baseline if needed",
            ]

        else:
            decision = "USE_BASELINE"
            rationale = (
                f"Optimization shows marginal improvement ({sharpe_improvement:.1f}%). "
                "Baseline strategy is preferred for robustness and simplicity."
            )
            confidence = 0.75
            conditions = [
                "Continue with baseline strategy",
                "Consider re-optimization with different constraints",
                "Review parameter search space",
            ]
            warnings = [
                "Optimization may be overfitting to historical data",
                "Current parameters may not generalize well",
                "Consider broader parameter ranges",
            ]

        return Recommendation(
            decision=decision,
            rationale=rationale,
            confidence=confidence,
            conditions=conditions,
            warnings=warnings,
        )

    def _prepare_chart_data(
        self,
        baseline_results: Dict,
        optimized_results: Dict,
        walk_forward_results: Optional[Dict] = None,
        sensitivity_results: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Prepare Plotly chart data."""
        chart_data = {}

        # Baseline equity chart
        chart_data["baseline_equity"] = self._create_equity_chart(
            baseline_results.get("equity_curve", []), "Baseline", "#2c3e50"
        )

        # Optimized equity chart
        chart_data["optimized_equity"] = self._create_equity_chart(
            optimized_results.get("equity_curve", []), "Optimized", "#3498db"
        )

        # Dual equity chart
        chart_data["dual_equity"] = self._create_dual_equity_chart(
            baseline_results.get("equity_curve", []),
            optimized_results.get("equity_curve", []),
        )

        # Drawdown chart
        chart_data["drawdown"] = self._create_drawdown_chart(
            baseline_results.get("equity_curve", []),
            optimized_results.get("equity_curve", []),
        )

        # Risk radar chart
        chart_data["risk_radar"] = self._create_risk_radar_chart(
            self._extract_metrics(baseline_results),
            self._extract_metrics(optimized_results),
        )

        # Walk-forward chart
        if walk_forward_results:
            chart_data["walkforward"] = self._create_walk_forward_chart(walk_forward_results)

        # Sensitivity heatmap
        if sensitivity_results:
            chart_data["sensitivity"] = self._create_sensitivity_heatmap(sensitivity_results)

        return chart_data

    def _create_equity_chart(self, equity_curve: List, name: str, color: str) -> Dict[str, Any]:
        """Create equity chart for single strategy."""
        if not equity_curve:
            return {"data": [], "layout": {}}

        dates = [point[0] if isinstance(point, tuple) else point for point in equity_curve]
        values = [point[1] if isinstance(point, tuple) else point for point in equity_curve]

        return {
            "data": [
                {
                    "x": dates,
                    "y": values,
                    "mode": "lines",
                    "name": name,
                    "line": {"color": color, "width": 2},
                }
            ],
            "layout": {
                "title": f"{name} Equity Curve",
                "xaxis": {"title": "Date"},
                "yaxis": {"title": "Portfolio Value"},
                "hovermode": "x unified",
                "height": 350,
            },
        }

    def _create_dual_equity_chart(
        self, baseline_curve: List, optimized_curve: List
    ) -> Dict[str, Any]:
        """Create dual equity chart overlay."""
        if not baseline_curve or not optimized_curve:
            return {"data": [], "layout": {}}

        baseline_dates = [
            point[0] if isinstance(point, tuple) else point for point in baseline_curve
        ]
        baseline_values = [
            point[1] if isinstance(point, tuple) else point for point in baseline_curve
        ]

        optimized_dates = [
            point[0] if isinstance(point, tuple) else point for point in optimized_curve
        ]
        optimized_values = [
            point[1] if isinstance(point, tuple) else point for point in optimized_curve
        ]

        # Normalize to same starting value
        if baseline_values and optimized_values:
            baseline_norm = [v / baseline_values[0] * 100000 for v in baseline_values]
            optimized_norm = [v / optimized_values[0] * 100000 for v in optimized_values]
        else:
            baseline_norm = baseline_values
            optimized_norm = optimized_values

        return {
            "data": [
                {
                    "x": baseline_dates,
                    "y": baseline_norm,
                    "mode": "lines",
                    "name": "Baseline",
                    "line": {"color": "#2c3e50", "width": 2},
                },
                {
                    "x": optimized_dates,
                    "y": optimized_norm,
                    "mode": "lines",
                    "name": "Optimized",
                    "line": {"color": "#3498db", "width": 2},
                },
            ],
            "layout": {
                "title": "Baseline vs Optimized - Normalized Equity",
                "xaxis": {"title": "Date"},
                "yaxis": {"title": "Normalized Portfolio Value"},
                "hovermode": "x unified",
                "legend": {"x": 0.01, "y": 0.99},
            },
        }

    def _create_drawdown_chart(self, baseline_curve: List, optimized_curve: List) -> Dict[str, Any]:
        """Create underwater drawdown comparison chart."""
        if not baseline_curve or not optimized_curve:
            return {"data": [], "layout": {}}

        # Calculate drawdowns
        baseline_dd = self._calculate_drawdown(baseline_curve)
        optimized_dd = self._calculate_drawdown(optimized_curve)

        baseline_dates = [
            point[0] if isinstance(point, tuple) else point for point in baseline_curve
        ]
        optimized_dates = [
            point[0] if isinstance(point, tuple) else point for point in optimized_curve
        ]

        return {
            "data": [
                {
                    "x": baseline_dates,
                    "y": baseline_dd,
                    "mode": "lines",
                    "name": "Baseline DD",
                    "line": {"color": "#e74c3c", "width": 2},
                    "fill": "tozeroy",
                },
                {
                    "x": optimized_dates,
                    "y": optimized_dd,
                    "mode": "lines",
                    "name": "Optimized DD",
                    "line": {"color": "#27ae60", "width": 2},
                    "fill": "tozeroy",
                },
            ],
            "layout": {
                "title": "Underwater Drawdown Comparison",
                "xaxis": {"title": "Date"},
                "yaxis": {"title": "Drawdown (%)"},
                "hovermode": "x unified",
                "legend": {"x": 0.01, "y": 0.99},
            },
        }

    def _calculate_drawdown(self, equity_curve: List) -> List[float]:
        """Calculate drawdown series from equity curve."""
        values = [point[1] if isinstance(point, tuple) else point for point in equity_curve]

        if not values:
            return []

        # Calculate running maximum
        running_max = np.maximum.accumulate(values)

        # Calculate drawdown as percentage
        drawdown = ((values - running_max) / running_max) * 100

        return drawdown.tolist()

    def _create_risk_radar_chart(
        self, baseline_metrics: Dict, optimized_metrics: Dict
    ) -> Dict[str, Any]:
        """Create risk-adjusted returns radar chart."""
        # Normalize metrics to 0-1 scale for radar chart
        metrics_to_plot = ["sharpe_ratio", "sortino_ratio", "calmar_ratio", "omega_ratio"]

        baseline_values = [baseline_metrics.get(m, 0) for m in metrics_to_plot]
        optimized_values = [optimized_metrics.get(m, 0) for m in metrics_to_plot]

        # Normalize (min-max normalization)
        all_values = baseline_values + optimized_values
        min_val = min(all_values)
        max_val = max(all_values)
        range_val = max_val - min_val if max_val != min_val else 1

        baseline_norm = [(v - min_val) / range_val for v in baseline_values]
        optimized_norm = [(v - min_val) / range_val for v in optimized_values]

        return {
            "data": [
                {
                    "type": "scatterpolar",
                    "r": baseline_norm,
                    "theta": metrics_to_plot,
                    "name": "Baseline",
                    "fill": "toself",
                },
                {
                    "type": "scatterpolar",
                    "r": optimized_norm,
                    "theta": metrics_to_plot,
                    "name": "Optimized",
                    "fill": "toself",
                },
            ],
            "layout": {
                "polar": {"radialaxis": {"visible": True, "range": [0, 1]}},
                "showlegend": True,
                "title": "Risk-Adjusted Returns Comparison",
            },
        }

    def _create_walk_forward_chart(self, walk_forward_results: Dict) -> Dict[str, Any]:
        """Create walk-forward window performance chart."""
        windows = walk_forward_results.get("windows", [])

        if not windows:
            return {"data": [], "layout": {}}

        is_sharpes = [w.get("is_sharpe", 0) for w in windows]
        oos_sharpes = [w.get("oos_sharpe", 0) for w in windows]
        window_labels = [f"W{i+1}" for i in range(len(windows))]

        return {
            "data": [
                {"x": window_labels, "y": is_sharpes, "name": "IS Sharpe", "type": "bar"},
                {"x": window_labels, "y": oos_sharpes, "name": "OOS Sharpe", "type": "bar"},
            ],
            "layout": {
                "title": "Walk-Forward Validation: IS vs OOS Sharpe",
                "barmode": "group",
                "xaxis": {"title": "Validation Window"},
                "yaxis": {"title": "Sharpe Ratio"},
            },
        }

    def _create_sensitivity_heatmap(self, sensitivity_results: Dict) -> Dict[str, Any]:
        """Create parameter sensitivity heatmap."""
        # Placeholder - implement based on sensitivity data structure
        return {"data": [], "layout": {}}

    def _prepare_key_metrics_table(
        self,
        baseline: Dict[str, float],
        optimized: Dict[str, float],
        significance_tests: Dict[str, StatisticalTest],
    ) -> List[Dict[str, Any]]:
        """Prepare key metrics table data."""
        metrics_config = [
            ("Sharpe Ratio", "sharpe_ratio", "{:.2f}"),
            ("Total Return (%)", "total_return", "{:.2f}"),
            ("Max Drawdown (%)", "max_drawdown", "{:.2f}"),
            ("Win Rate (%)", "win_rate", "{:.1f}"),
            ("Profit Factor", "profit_factor", "{:.2f}"),
            ("Sortino Ratio", "sortino_ratio", "{:.2f}"),
            ("Calmar Ratio", "calmar_ratio", "{:.2f}"),
            ("Omega Ratio", "omega_ratio", "{:.2f}"),
        ]

        table_data = []

        for name, key, fmt in metrics_config:
            baseline_val = baseline.get(key, 0.0)
            optimized_val = optimized.get(key, 0.0)

            # Calculate improvement
            higher_better = key != "max_drawdown"
            improvement = self._pct_improvement(baseline_val, optimized_val, higher_better)

            # Determine class
            if improvement > 5:
                improvement_class = "positive"
            elif improvement < -5:
                improvement_class = "negative"
            else:
                improvement_class = "neutral"

            # Check significance
            significant = False
            if key in significance_tests:
                significant = significance_tests[key].is_significant

            table_data.append(
                {
                    "name": name,
                    "baseline": fmt.format(baseline_val),
                    "optimized": fmt.format(optimized_val),
                    "improvement": f"{improvement:+.1f}%",
                    "improvement_class": improvement_class,
                    "significant": significant,
                }
            )

        return table_data

    def _prepare_drawdown_metrics(
        self, baseline: Dict[str, float], optimized: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Prepare drawdown metrics table data."""
        metrics = [
            ("Max Drawdown", "max_drawdown", "{:.2f}%"),
            ("Avg Drawdown", "avg_drawdown", "{:.2f}%"),
            ("Ulcer Index", "ulcer_index", "{:.2f}"),
        ]

        table_data = []

        for name, key, fmt in metrics:
            baseline_val = baseline.get(key, 0.0)
            optimized_val = optimized.get(key, 0.0)

            # For drawdown, lower is better
            improvement = self._pct_improvement(baseline_val, optimized_val, higher_better=False)

            if improvement > 0:
                improvement_class = "positive"
            elif improvement < 0:
                improvement_class = "negative"
            else:
                improvement_class = "neutral"

            table_data.append(
                {
                    "name": name,
                    "baseline": fmt.format(baseline_val),
                    "optimized": fmt.format(optimized_val),
                    "improvement": f"{improvement:+.1f}%",
                    "improvement_class": improvement_class,
                }
            )

        return table_data

    def _prepare_risk_metrics_table(
        self, baseline: Dict[str, float], optimized: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Prepare risk metrics table data."""
        metrics = [
            ("Sharpe Ratio", "sharpe_ratio", "{:.2f}", 1.0),
            ("Sortino Ratio", "sortino_ratio", "{:.2f}", 1.0),
            ("Calmar Ratio", "calmar_ratio", "{:.2f}", 0.5),
            ("Omega Ratio", "omega_ratio", "{:.2f}", 1.0),
            ("Volatility (Ann.)", "volatility", "{:.2f}%", 0.2),
        ]

        table_data = []

        for name, key, fmt, threshold in metrics:
            baseline_val = baseline.get(key, 0.0)
            optimized_val = optimized.get(key, 0.0)

            improvement = self._pct_improvement(baseline_val, optimized_val, higher_better=True)

            improvement_class = "positive" if improvement > 0 else "neutral"

            # Status based on threshold
            if optimized_val >= threshold:
                status = "✓ Good"
            elif optimized_val >= threshold * 0.8:
                status = "⚠ Fair"
            else:
                status = "✗ Poor"

            table_data.append(
                {
                    "name": name,
                    "baseline": fmt.format(baseline_val),
                    "optimized": fmt.format(optimized_val),
                    "improvement": f"{improvement:+.1f}%",
                    "improvement_class": improvement_class,
                    "status": status,
                }
            )

        return table_data

    def _prepare_walk_forward_metrics(self, walk_forward_results: Dict) -> List[Dict[str, Any]]:
        """Prepare walk-forward validation metrics table."""
        if not walk_forward_results:
            return []

        is_sharpe = walk_forward_results.get("is_sharpe", 0.0)
        oos_sharpe = walk_forward_results.get("oos_sharpe", 0.0)
        ratio = oos_sharpe / is_sharpe if is_sharpe > 0 else 0.0

        ratio_class = "positive" if ratio >= 0.8 else "negative"
        assessment = (
            "✓ Stable" if ratio >= 0.8 else "⚠ Degradation" if ratio >= 0.6 else "✗ Unstable"
        )

        return [
            {
                "name": "Sharpe Ratio",
                "is_value": f"{is_sharpe:.2f}",
                "oos_value": f"{oos_sharpe:.2f}",
                "is_oos_ratio": f"{ratio:.2f}",
                "ratio_class": ratio_class,
                "assessment": assessment,
            }
        ]

    def _format_recommended_config(self, optimization_results: Dict) -> str:
        """Format recommended configuration as YAML."""
        params = optimization_results.get("parameters", {})

        lines = ["# Recommended Configuration"]
        lines.append("# Optimized parameters from backtesting")
        lines.append("")

        for key, value in sorted(params.items()):
            if isinstance(value, str):
                lines.append(f"{key}: \"{value}\"")
            else:
                lines.append(f"{key}: {value}")

        return "\n".join(lines)

    # Helper methods for template rendering
    def _get_recommendation_class(self, decision: str) -> str:
        """Get CSS class for recommendation banner."""
        mapping = {
            "USE_OPTIMIZED": "use-optimized",
            "CONSIDER_OPTIMIZED": "consider-optimized",
            "USE_BASELINE": "use-baseline",
        }
        return mapping.get(decision, "use-baseline")

    def _get_recommendation_icon(self, decision: str) -> str:
        """Get icon for recommendation."""
        mapping = {
            "USE_OPTIMIZED": "✅",
            "CONSIDER_OPTIMIZED": "⚠️",
            "USE_BASELINE": "🔄",
        }
        return mapping.get(decision, "🔄")

    def _get_card_class(self, improvement: float, higher_better: bool) -> str:
        """Get CSS class for metric card."""
        if improvement > 10:
            return "success"
        elif improvement > 0:
            return ""  # Default
        elif improvement > -10:
            return "warning"
        else:
            return "warning"
