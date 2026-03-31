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

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import numpy as np
from jinja2 import Template

from app.domain.models.input_profile import InputProfile

# Recursive type for nested JSON-like data structures used in report dicts
JsonValue = Union[int, float, str, bool, list["JsonValue"], dict[str, "JsonValue"], None]

# Type for chart-like nested structures returned by chart-building methods
# Uses object because the actual values are recursive JSON-like structures that
# cannot be expressed with invariant recursive type aliases in mypy.
ChartDict = dict[str, object]

logger = logging.getLogger(__name__)


def _to_float(value: JsonValue) -> float:
    """Safely convert a JsonValue to float, returning 0.0 for non-numeric types."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


@dataclass
class ComparisonMetrics:
    """Comparison metrics between baseline and optimized results."""

    sharpe_ratio: tuple[float, float]  # (baseline, optimized)
    total_return: tuple[float, float]
    max_drawdown: tuple[float, float]
    win_rate: tuple[float, float]
    profit_factor: tuple[float, float]
    sortino_ratio: tuple[float, float]
    calmar_ratio: tuple[float, float]
    omega_ratio: tuple[float, float]

    # Out-of-sample metrics (if available)
    oos_sharpe: Optional[tuple[float, float]] = None
    is_oos_ratio: Optional[float] = None


@dataclass
class ParameterChange:
    """A parameter that changed between baseline and optimization."""

    name: str
    before: Union[int, float, str, bool]
    after: Union[int, float, str, bool]
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
    conditions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


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
            resolved_path = (
                Path(__file__).parent / "templates" / "baseline_optimization_report.html"
            )
        else:
            resolved_path = Path(template_path)

        self.template_path: Path = resolved_path

        # Load template
        try:
            with open(self.template_path, encoding="utf-8") as f:
                self.template = Template(f.read())
        except FileNotFoundError:
            logger.error(f"Template not found: {template_path}")
            raise

        logger.info(f"BaselineOptimizationReporter initialized with template: {self.template_path}")

    def generate_report(
        self,
        profile: InputProfile,
        baseline_results: dict[str, JsonValue],
        optimization_results: dict[str, JsonValue],
        comparison: Optional[dict[str, JsonValue]] = None,
        walk_forward_results: Optional[dict[str, JsonValue]] = None,
        sensitivity_results: Optional[dict[str, JsonValue]] = None,
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
        baseline_params_raw = baseline_results.get("parameters", {})
        optimized_params_raw = optimization_results.get("parameters", {})
        baseline_params = baseline_params_raw if isinstance(baseline_params_raw, dict) else {}
        optimized_params = optimized_params_raw if isinstance(optimized_params_raw, dict) else {}
        parameter_changes = self._extract_parameter_changes(
            baseline_params,
            optimized_params,
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
        html_content: str = self.template.render(
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
                (
                    float(comparison["sharpe_improvement"])
                    if isinstance(comparison["sharpe_improvement"], (int, float))
                    else 0.0
                ),
                higher_better=True,
            ),
            return_card_class=self._get_card_class(
                (
                    float(comparison["return_improvement"])
                    if isinstance(comparison["return_improvement"], (int, float))
                    else 0.0
                ),
                higher_better=True,
            ),
            dd_card_class=self._get_card_class(
                (
                    float(comparison["dd_change"])
                    if isinstance(comparison["dd_change"], (int, float))
                    else 0.0
                ),
                higher_better=False,
            ),
            winrate_card_class=self._get_card_class(
                (
                    float(comparison["winrate_improvement"])
                    if isinstance(comparison["winrate_improvement"], (int, float))
                    else 0.0
                ),
                higher_better=True,
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

        Raises:
            OSError: If directory cannot be created or file cannot be written
            ValueError: If html is empty
        """
        if not html:
            logger.error("Cannot save empty HTML report")
            raise ValueError("HTML content is required for saving report")

        path = Path(output_path)

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(
                f"Failed to create output directory: {path.parent}",
                extra={"error": str(e), "path": str(path.parent)},
            )
            raise

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            logger.info(f"Report saved to: {path}")
        except OSError as e:
            logger.error(
                f"Failed to write report to file: {path}",
                extra={"error": str(e), "path": str(path)},
            )
            raise

    def generate_pdf(self, html: str, output_path: Optional[str] = None) -> bytes:
        """
        Generate PDF from HTML report.

        Note: PDF generation requires the optional weasyprint library.
        The feature is available but not enabled by default.

        To enable PDF generation:
        1. Install weasyprint: pip install weasyprint
        2. Ensure system dependencies (GTK, Cairo) are installed
        3. PDF generation will automatically work

        Args:
            html: HTML content to convert to PDF
            output_path: Optional path to save PDF file

        Returns:
            PDF bytes, or empty bytes if weasyprint is not available

        Example:
            >>> pdf_bytes = reporter.generate_pdf(html_report, output_path="report.pdf")
            >>> if pdf_bytes:
            ...     with open("report.pdf", "wb") as f:
            ...         f.write(pdf_bytes)
        """
        try:
            from weasyprint import HTML

            # Generate PDF from HTML
            html_doc = HTML(string=html)
            pdf_bytes: bytes = html_doc.write_pdf()

            # Save to file if output path provided
            if output_path:
                Path(output_path).write_bytes(pdf_bytes)
                logger.info(f"PDF report saved to {output_path}")

            return pdf_bytes

        except ImportError:
            logger.debug(
                "PDF generation requires weasyprint. "
                "Install with: pip install weasyprint. "
                "HTML reports are fully functional without PDF export."
            )
            return b""

        except Exception as e:
            logger.error(f"Error generating PDF: {e}", exc_info=True)
            return b""

    def _extract_metrics(self, results: dict[str, JsonValue]) -> dict[str, float]:
        """Extract key metrics from results dictionary."""
        performance_raw = results.get("performance", {})
        performance: dict[str, JsonValue] = (
            performance_raw if isinstance(performance_raw, dict) else {}
        )
        raw_equity = results.get("equity_curve", [])
        equity_curve: list[JsonValue] = raw_equity if isinstance(raw_equity, list) else []

        # Calculate returns if not provided
        if not equity_curve:
            total_return = 0.0
        else:
            first = equity_curve[0]
            last = equity_curve[-1]
            initial: float = (
                float(first[1])
                if isinstance(first, tuple)
                else float(first) if isinstance(first, (int, float)) else 0.0
            )
            final: float = (
                float(last[1])
                if isinstance(last, tuple)
                else float(last) if isinstance(last, (int, float)) else 0.0
            )
            total_return = (final - initial) / initial if initial > 0 else 0.0

        # Drawdown is stored as negative (e.g., -15%), but we want it as positive for comparisons
        max_dd = _to_float(performance.get("max_drawdown_percentage", 0.0) or 0.0)
        if max_dd < 0:
            max_dd = abs(max_dd)

        return {
            "sharpe_ratio": _to_float(performance.get("sharpe_ratio", 0.0) or 0.0),
            "total_return": _to_float(
                performance.get("total_return", total_return * 100) or total_return * 100
            ),
            "max_drawdown": max_dd,  # Store as positive value
            "win_rate": _to_float(performance.get("win_rate", 0.0) or 0.0),
            "profit_factor": _to_float(performance.get("profit_factor", 0.0) or 0.0),
            "sortino_ratio": _to_float(performance.get("sortino_ratio", 0.0) or 0.0),
            "calmar_ratio": _to_float(performance.get("calmar_ratio", 0.0) or 0.0),
            "omega_ratio": _to_float(performance.get("omega_ratio", 0.0) or 0.0),
            # Additional metrics that were missing
            "avg_drawdown": _to_float(performance.get("avg_drawdown", 0.0) or 0.0),
            "ulcer_index": _to_float(performance.get("ulcer_index", 0.0) or 0.0),
            "volatility": _to_float(performance.get("volatility", 0.0) or 0.0),
        }

    def _calculate_comparison(
        self, baseline: dict[str, float], optimized: dict[str, float]
    ) -> dict[str, JsonValue]:
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
        self, baseline_results: dict, optimized_results: dict
    ) -> dict[str, StatisticalTest]:
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

    def _extract_returns_series(self, results: dict) -> np.ndarray:
        """Extract returns series from results."""
        equity_curve = results.get("equity_curve", [])

        if not equity_curve:
            return np.array([], dtype=np.float64)

        # Convert to returns - extract numeric values from equity curve points
        raw_values: list[float] = []
        for point in equity_curve:
            val = point[1] if isinstance(point, tuple) and len(point) > 1 else point
            raw_values.append(float(val) if isinstance(val, (int, float)) else 0.0)
        values: np.ndarray = np.array(raw_values, dtype=np.float64)

        with np.errstate(divide="ignore", invalid="ignore"):
            returns: np.ndarray = np.diff(values) / values[:-1]
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
        baseline_params: dict[str, JsonValue],
        optimized_params: dict[str, JsonValue],
        comparison: dict[str, JsonValue],
    ) -> list[ParameterChange]:
        """Extract and analyze parameter changes."""
        changes: list[ParameterChange] = []

        for key in set(list(baseline_params.keys()) + list(optimized_params.keys())):
            baseline_val = baseline_params.get(key)
            optimized_val = optimized_params.get(key)

            if baseline_val != optimized_val:
                # Determine impact
                impact = self._estimate_parameter_impact(
                    key, baseline_val, optimized_val, comparison
                )

                # Only include scalar values (not lists or dicts or None)
                before_scalar = (
                    baseline_val
                    if isinstance(baseline_val, (int, float, str, bool))
                    else str(baseline_val)
                )
                after_scalar = (
                    optimized_val
                    if isinstance(optimized_val, (int, float, str, bool))
                    else str(optimized_val)
                )

                changes.append(
                    ParameterChange(
                        name=key,
                        before=before_scalar,
                        after=after_scalar,
                        impact=impact,
                    )
                )

        return changes

    def _estimate_parameter_impact(
        self,
        param_name: str,
        before: JsonValue,
        after: JsonValue,
        comparison: dict[str, JsonValue],
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
        baseline_metrics: dict[str, float],
        optimized_metrics: dict[str, float],
        comparison: dict[str, JsonValue],
        walk_forward_results: Optional[dict[str, JsonValue]],
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
            is_sharpe_raw = walk_forward_results.get("is_sharpe", optimized_sharpe)
            oos_sharpe_raw = walk_forward_results.get("oos_sharpe", optimized_sharpe * 0.7)
            is_sharpe: float = (
                float(is_sharpe_raw)
                if isinstance(is_sharpe_raw, (int, float))
                else optimized_sharpe
            )
            oos_sharpe: float = (
                float(oos_sharpe_raw)
                if isinstance(oos_sharpe_raw, (int, float))
                else optimized_sharpe * 0.7
            )
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
        baseline_results: dict,
        optimized_results: dict,
        walk_forward_results: Optional[dict] = None,
        sensitivity_results: Optional[dict] = None,
    ) -> ChartDict:
        """Prepare Plotly chart data."""
        chart_data = {
            "baseline_equity": self._create_equity_chart(
                baseline_results.get("equity_curve", []), "Baseline", "#2c3e50"
            ),
            "optimized_equity": self._create_equity_chart(
                optimized_results.get("equity_curve", []), "Optimized", "#3498db"
            ),
            "dual_equity": self._create_dual_equity_chart(
                baseline_results.get("equity_curve", []),
                optimized_results.get("equity_curve", []),
            ),
            "drawdown": self._create_drawdown_chart(
                baseline_results.get("equity_curve", []),
                optimized_results.get("equity_curve", []),
            ),
            "risk_radar": self._create_risk_radar_chart(
                self._extract_metrics(baseline_results),
                self._extract_metrics(optimized_results),
            ),
        }

        # Walk-forward chart
        if walk_forward_results:
            chart_data["walkforward"] = self._create_walk_forward_chart(walk_forward_results)

        # Sensitivity heatmap
        if sensitivity_results:
            chart_data["sensitivity"] = self._create_sensitivity_heatmap(sensitivity_results)

        return chart_data

    def _create_equity_chart(self, equity_curve: list, name: str, color: str) -> ChartDict:
        """Create equity chart for single strategy."""
        if not equity_curve:
            logger.warning(f"Empty equity curve for {name}")
            return {"data": [], "layout": {}}

        try:
            dates = [point[0] if isinstance(point, tuple) else point for point in equity_curve]
            values = [point[1] if isinstance(point, tuple) else point for point in equity_curve]
        except (IndexError, TypeError) as e:
            logger.error(f"Failed to extract chart data for {name}: {e}")
            return {"data": [], "layout": {}}

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

    def _create_dual_equity_chart(self, baseline_curve: list, optimized_curve: list) -> ChartDict:
        """Create dual equity chart overlay."""
        if not baseline_curve or not optimized_curve:
            logger.warning("Empty curve data for dual equity chart")
            return {"data": [], "layout": {}}

        try:
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
        except (IndexError, TypeError) as e:
            logger.error(f"Failed to extract dual chart data: {e}")
            return {"data": [], "layout": {}}

        # Normalize to same starting value
        if baseline_values and optimized_values:
            try:
                baseline_norm = [v / baseline_values[0] * 100000 for v in baseline_values]
                optimized_norm = [v / optimized_values[0] * 100000 for v in optimized_values]
            except (ZeroDivisionError, TypeError) as e:
                logger.error(f"Failed to normalize chart data: {e}")
                return {"data": [], "layout": {}}
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

    def _create_drawdown_chart(self, baseline_curve: list, optimized_curve: list) -> ChartDict:
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

    def _calculate_drawdown(self, equity_curve: list) -> list[float]:
        """Calculate drawdown series from equity curve."""
        raw_values: list[float] = []
        for point in equity_curve:
            val = point[1] if isinstance(point, tuple) and len(point) > 1 else point
            raw_values.append(float(val) if isinstance(val, (int, float)) else 0.0)

        if not raw_values:
            return []

        values_arr: np.ndarray = np.array(raw_values, dtype=np.float64)

        # Calculate running maximum
        running_max: np.ndarray = np.maximum.accumulate(values_arr)

        # Calculate drawdown as percentage
        drawdown: np.ndarray = ((values_arr - running_max) / running_max) * 100

        return [float(d) for d in drawdown]

    def _create_risk_radar_chart(
        self, baseline_metrics: dict, optimized_metrics: dict
    ) -> ChartDict:
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

    def _create_walk_forward_chart(self, walk_forward_results: dict) -> ChartDict:
        """Create walk-forward window performance chart."""
        windows = walk_forward_results.get("windows", [])

        if not windows:
            return {"data": [], "layout": {}}

        is_sharpes = [w.get("is_sharpe", 0) for w in windows]
        oos_sharpes = [w.get("oos_sharpe", 0) for w in windows]
        window_labels = [f"W{i + 1}" for i in range(len(windows))]

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

    def _create_sensitivity_heatmap(self, sensitivity_results: dict) -> ChartDict:
        """Create parameter sensitivity heatmap."""
        # Placeholder - implement based on sensitivity data structure
        return {"data": [], "layout": {}}

    def _prepare_key_metrics_table(
        self,
        baseline: dict[str, float],
        optimized: dict[str, float],
        significance_tests: dict[str, StatisticalTest],
    ) -> list[dict[str, Union[str, bool]]]:
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
        self, baseline: dict[str, float], optimized: dict[str, float]
    ) -> list[dict[str, str]]:
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
        self, baseline: dict[str, float], optimized: dict[str, float]
    ) -> list[dict[str, str]]:
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

    def _prepare_walk_forward_metrics(self, walk_forward_results: dict) -> list[dict[str, str]]:
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

    def _format_recommended_config(self, optimization_results: dict) -> str:
        """Format recommended configuration as YAML."""
        params = optimization_results.get("parameters", {})

        lines = ["# Recommended Configuration"]
        lines.append("# Optimized parameters from backtesting")
        lines.append("")

        for key, value in sorted(params.items()):
            if isinstance(value, str):
                lines.append(f'{key}: "{value}"')
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
