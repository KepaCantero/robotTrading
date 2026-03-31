"""
Insight Generation & Reporting - Template-based insights and alerts.

Provides:
- Statistical insight generation
- Risk warning system
- Actionable recommendations
- Comprehensive markdown reporting
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

import numpy as np

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class InsightGenerator:
    """
    Generate data-driven insights, warnings, and recommendations.

    Uses template-based generation with statistical analysis to provide
    actionable insights without LLM/NLP (deterministic, traceable output).
    """

    def __init__(self, risk_free_rate: Optional[float] = None):
        """
        Initialize InsightGenerator.

        Args:
            risk_free_rate: Risk-free rate for calculations (default: from CentralizedConfig)
        """
        self.risk_free_rate = (
            risk_free_rate
            if risk_free_rate is not None
            else float(get_config().backtesting.default_risk_free_rate)
        )
        self.insights: list[str] = []
        self.warnings: list[dict[str, Any]] = []
        self.recommendations: list[dict[str, Any]] = []

        logger.info(f"InsightGenerator initialized: risk_free_rate={risk_free_rate}")

    def generate_statistical_insights(self, metrics: dict[str, float]) -> list[str]:
        """
        Generate key statistical insights from performance metrics.

        Args:
            metrics: Dict with performance metrics (sharpe_ratio, return, volatility, etc)

        Returns:
            List of insight strings
        """
        self.insights = []

        if not metrics:
            logger.warning("Empty metrics dict provided")
            return self.insights

        try:
            # Return insight
            total_return = metrics.get("return_pct", 0)
            if total_return > 0.2:
                self.insights.append(f"✅ Excellent returns: +{total_return * 100:.1f}% (>20%)")
            elif total_return > 0.1:
                self.insights.append(f"✅ Good returns: +{total_return * 100:.1f}% (10-20%)")
            elif total_return > 0:
                self.insights.append(f"⚠️ Positive returns: +{total_return * 100:.1f}% (0-10%)")
            else:
                self.insights.append(f"❌ Negative returns: {total_return * 100:.1f}%")

            # Sharpe ratio insight
            sharpe = metrics.get("sharpe_ratio", 0)
            if sharpe > 2.0:
                self.insights.append(
                    f"✅ Exceptional risk-adjusted returns (Sharpe: {sharpe:.2f} > 2.0)"
                )
            elif sharpe > 1.0:
                self.insights.append(f"✅ Good risk-adjusted returns (Sharpe: {sharpe:.2f})")
            elif sharpe > 0:
                self.insights.append(f"⚠️ Marginal risk-adjusted returns (Sharpe: {sharpe:.2f})")
            else:
                self.insights.append(f"❌ Poor risk-adjusted returns (Sharpe: {sharpe:.2f})")

            # Drawdown insight
            max_dd = metrics.get("max_drawdown", 0)
            if max_dd > -0.1:
                self.insights.append(f"✅ Minimal drawdown: {max_dd * 100:.1f}% (<10%)")
            elif max_dd > -0.2:
                self.insights.append(f"⚠️ Moderate drawdown: {max_dd * 100:.1f}% (10-20%)")
            elif max_dd > -0.5:
                self.insights.append(f"⚠️ Significant drawdown: {max_dd * 100:.1f}% (20-50%)")
            else:
                self.insights.append(f"❌ Severe drawdown: {max_dd * 100:.1f}% (>50%)")

            # Win rate insight
            win_rate = metrics.get("win_rate", 0)
            if win_rate > 0.6:
                self.insights.append(f"✅ Strong win rate: {win_rate * 100:.1f}% (>60%)")
            elif win_rate > 0.55:
                self.insights.append(f"✅ Positive win rate: {win_rate * 100:.1f}% (55-60%)")
            elif win_rate > 0.5:
                self.insights.append(f"⚠️ Marginal win rate: {win_rate * 100:.1f}% (50-55%)")
            else:
                self.insights.append(f"❌ Poor win rate: {win_rate * 100:.1f}% (<50%)")

            # Volatility insight
            volatility = metrics.get("volatility", 0)
            if volatility < 0.1:
                self.insights.append(f"✅ Low volatility: {volatility * 100:.1f}% (<10%)")
            elif volatility < 0.2:
                self.insights.append(f"✅ Moderate volatility: {volatility * 100:.1f}%")
            elif volatility < 0.3:
                self.insights.append(f"⚠️ Elevated volatility: {volatility * 100:.1f}%")
            else:
                self.insights.append(f"⚠️ High volatility: {volatility * 100:.1f}%")

            # Profit factor insight
            profit_factor = metrics.get("profit_factor", 0)
            if profit_factor > 2.0:
                self.insights.append(f"✅ Excellent profit factor: {profit_factor:.2f} (>2.0)")
            elif profit_factor > 1.5:
                self.insights.append(f"✅ Strong profit factor: {profit_factor:.2f}")
            elif profit_factor > 1.0:
                self.insights.append(f"⚠️ Marginal profit factor: {profit_factor:.2f}")
            else:
                self.insights.append(f"❌ Poor profit factor: {profit_factor:.2f}")

            logger.info(f"Generated {len(self.insights)} statistical insights")
            return self.insights

        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            logger.error(f"Error generating statistical insights: {e}", exc_info=True)
            return self.insights

    def generate_risk_warnings(self, metrics: dict[str, float]) -> list[dict[str, Any]]:
        """
        Generate risk warnings based on metric thresholds.

        Args:
            metrics: Dict with performance metrics

        Returns:
            List of warning dicts with level, message, metric, value
        """
        self.warnings = []

        if not metrics:
            return self.warnings

        try:
            # Maximum drawdown warning
            max_dd = metrics.get("max_drawdown", 0)
            if max_dd < -0.5:
                self.warnings.append(
                    {
                        "level": "CRITICAL",
                        "metric": "max_drawdown",
                        "value": max_dd,
                        "message": f"CRITICAL: Catastrophic drawdown {max_dd * 100:.1f}% - Strategy at severe risk",
                    }
                )
            elif max_dd < -0.3:
                self.warnings.append(
                    {
                        "level": "WARNING",
                        "metric": "max_drawdown",
                        "value": max_dd,
                        "message": f"WARNING: Significant drawdown {max_dd * 100:.1f}% - Consider risk reduction",
                    }
                )
            elif max_dd < -0.2:
                self.warnings.append(
                    {
                        "level": "INFO",
                        "metric": "max_drawdown",
                        "value": max_dd,
                        "message": f"INFO: Moderate drawdown {max_dd * 100:.1f}% - Monitor closely",
                    }
                )

            # Sharpe ratio warning
            sharpe = metrics.get("sharpe_ratio", 0)
            if sharpe < 0:
                self.warnings.append(
                    {
                        "level": "CRITICAL",
                        "metric": "sharpe_ratio",
                        "value": sharpe,
                        "message": f"CRITICAL: Negative Sharpe ratio {sharpe:.2f} - Returns below risk-free rate",
                    }
                )
            elif sharpe < 0.5:
                self.warnings.append(
                    {
                        "level": "WARNING",
                        "metric": "sharpe_ratio",
                        "value": sharpe,
                        "message": f"WARNING: Poor risk-adjusted returns (Sharpe {sharpe:.2f}) - Insufficient compensation",
                    }
                )

            # Volatility warning
            volatility = metrics.get("volatility", 0)
            if volatility > 0.5:
                self.warnings.append(
                    {
                        "level": "WARNING",
                        "metric": "volatility",
                        "value": volatility,
                        "message": f"WARNING: Extremely high volatility {volatility * 100:.1f}% - Risk management recommended",
                    }
                )

            # Win rate warning
            win_rate = metrics.get("win_rate", 0)
            if win_rate < 0.4:
                self.warnings.append(
                    {
                        "level": "WARNING",
                        "metric": "win_rate",
                        "value": win_rate,
                        "message": f"WARNING: Low win rate {win_rate * 100:.1f}% - Losing more trades than winning",
                    }
                )

            # Profit factor warning
            profit_factor = metrics.get("profit_factor", 0)
            if profit_factor < 1.0:
                self.warnings.append(
                    {
                        "level": "WARNING",
                        "metric": "profit_factor",
                        "value": profit_factor,
                        "message": f"WARNING: Profit factor < 1.0 ({profit_factor:.2f}) - Losing strategy",
                    }
                )
            elif profit_factor < 1.2:
                self.warnings.append(
                    {
                        "level": "INFO",
                        "metric": "profit_factor",
                        "value": profit_factor,
                        "message": f"INFO: Marginal profit factor {profit_factor:.2f} - Limited edge",
                    }
                )

            # Return warning
            returns = metrics.get("return_pct", 0)
            if returns < 0:
                self.warnings.append(
                    {
                        "level": "WARNING",
                        "metric": "return_pct",
                        "value": returns,
                        "message": f"WARNING: Negative returns {returns * 100:.1f}% - Strategy underperforming",
                    }
                )

            logger.info(f"Generated {len(self.warnings)} risk warnings")
            return self.warnings

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Error generating risk warnings: {e}", exc_info=True)
            return self.warnings

    def generate_recommendations(
        self, metrics: dict[str, float], regimes: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """
        Generate actionable recommendations based on analysis.

        Args:
            metrics: Dict with performance metrics
            regimes: Optional dict with regime analysis

        Returns:
            List of recommendation dicts with priority, action, rationale
        """
        self.recommendations = []

        if not metrics:
            return self.recommendations

        try:
            sharpe = metrics.get("sharpe_ratio", 0)
            max_dd = metrics.get("max_drawdown", 0)
            win_rate = metrics.get("win_rate", 0)
            volatility = metrics.get("volatility", 0)
            profit_factor = metrics.get("profit_factor", 1)

            # Risk management recommendations
            if max_dd < -0.3:
                self.recommendations.append(
                    {
                        "priority": "HIGH",
                        "action": "Implement Stop-Loss",
                        "rationale": f"Maximum drawdown {max_dd * 100:.1f}% exceeds threshold. Add position-level stop-losses.",
                    }
                )

            if volatility > 0.3:
                self.recommendations.append(
                    {
                        "priority": "HIGH",
                        "action": "Reduce Position Size",
                        "rationale": f"Volatility {volatility * 100:.1f}% is elevated. Reduce leverage or position sizing.",
                    }
                )

            if sharpe < 0.5:
                self.recommendations.append(
                    {
                        "priority": "MEDIUM",
                        "action": "Enhance Signal Quality",
                        "rationale": "Risk-adjusted returns are poor. Review signal generation and entry logic.",
                    }
                )

            # Win rate recommendations
            if win_rate < 0.45:
                self.recommendations.append(
                    {
                        "priority": "MEDIUM",
                        "action": "Improve Entry Timing",
                        "rationale": f"Win rate {win_rate * 100:.1f}% is low. Refine entry criteria and timing.",
                    }
                )

            # Profitability recommendations
            if profit_factor < 1.2:
                self.recommendations.append(
                    {
                        "priority": "MEDIUM",
                        "action": "Optimize Position Management",
                        "rationale": f"Profit factor {profit_factor:.2f} is marginal. Improve trade sizing or profit-taking.",
                    }
                )

            # Diversification recommendations
            if regimes and len(regimes) > 0:
                regime_performance = list(regimes.values())
                sharpe_variance = np.var(
                    [r.get("sharpe_ratio", 0) for r in regime_performance if isinstance(r, dict)]
                )
                if sharpe_variance > 0.5:
                    self.recommendations.append(
                        {
                            "priority": "MEDIUM",
                            "action": "Add Regime Filters",
                            "rationale": "Performance varies significantly by regime. Implement regime-based filters.",
                        }
                    )

            # Out-of-sample testing
            if metrics.get("backtest_only", True):
                self.recommendations.append(
                    {
                        "priority": "HIGH",
                        "action": "Paper Trade Before Live",
                        "rationale": "Strategy has only been backtested. Conduct extensive paper trading validation.",
                    }
                )

            # Positive recommendations
            if sharpe > 1.0 and profit_factor > 1.5:
                self.recommendations.append(
                    {
                        "priority": "LOW",
                        "action": "Consider Scaling Up",
                        "rationale": f"Strong metrics (Sharpe: {sharpe:.2f}, PF: {profit_factor:.2f}). Consider position increase.",
                    }
                )

            if max_dd > -0.1 and volatility < 0.15:
                self.recommendations.append(
                    {
                        "priority": "LOW",
                        "action": "Increase Leverage (Cautiously)",
                        "rationale": f"Good risk metrics (DD: {max_dd * 100:.1f}%, Vol: {volatility * 100:.1f}%). Consider modest leverage.",
                    }
                )

            logger.info(f"Generated {len(self.recommendations)} recommendations")
            return self.recommendations

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Error generating recommendations: {e}", exc_info=True)
            return self.recommendations

    def format_markdown_report(
        self,
        strategy_name: str,
        metrics: dict[str, float],
        regimes: Optional[dict[str, Any]] = None,
        include_warnings: bool = True,
        include_recommendations: bool = True,
    ) -> str:
        """
        Generate comprehensive markdown report.

        Args:
            strategy_name: Strategy name for the report
            metrics: Performance metrics dict
            regimes: Optional regime analysis
            include_warnings: Include risk warnings section
            include_recommendations: Include recommendations section

        Returns:
            Markdown formatted report string
        """
        try:
            report_lines = []

            # Header
            report_lines.append(f"# Strategy Report: {strategy_name}")
            report_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            # Performance Summary
            report_lines.append("## 📊 Performance Summary\n")
            report_lines.append("| Metric | Value |")
            report_lines.append("|--------|-------|")

            metric_keys = [
                ("return_pct", "Total Return", ".1%"),
                ("sharpe_ratio", "Sharpe Ratio", ".2"),
                ("sortino_ratio", "Sortino Ratio", ".2"),
                ("max_drawdown", "Max Drawdown", ".1%"),
                ("volatility", "Volatility", ".1%"),
                ("win_rate", "Win Rate", ".1%"),
                ("profit_factor", "Profit Factor", ".2"),
                ("total_trades", "Total Trades", "d"),
                ("avg_trade_pnl", "Avg Trade P&L", ".0"),
                ("calmar_ratio", "Calmar Ratio", ".2"),
            ]

            for key, label, fmt in metric_keys:
                if key in metrics:
                    value = metrics[key]
                    if fmt == ".1%":
                        formatted = f"{value * 100:.1f}%"
                    elif fmt == ".2":
                        formatted = f"{value:.2f}"
                    elif fmt == "d":
                        formatted = f"{int(value)}"
                    elif fmt == ".0":
                        formatted = f"{value:.0f}"
                    else:
                        formatted = str(value)
                    report_lines.append(f"| {label} | {formatted} |")

            report_lines.append("")

            # Statistical Insights
            insights = self.generate_statistical_insights(metrics)
            if insights:
                report_lines.append("## 📈 Key Insights\n")
                for insight in insights:
                    report_lines.append(f"- {insight}")
                report_lines.append("")

            # Risk Warnings
            if include_warnings:
                warnings = self.generate_risk_warnings(metrics)
                if warnings:
                    report_lines.append("## ⚠️ Risk Warnings\n")
                    for warning in warnings:
                        level = warning.get("level", "INFO")
                        message = warning.get("message", "")
                        emoji = {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "🔵"}.get(level, "⚪")
                        report_lines.append(f"{emoji} **{level}:** {message}")
                    report_lines.append("")

            # Recommendations
            if include_recommendations:
                recommendations = self.generate_recommendations(metrics, regimes)
                if recommendations:
                    report_lines.append("## 💡 Recommendations\n")

                    # Sort by priority
                    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
                    sorted_recs = sorted(
                        recommendations,
                        key=lambda x: priority_order.get(x.get("priority", "LOW"), 3),
                    )

                    for rec in sorted_recs:
                        priority = rec.get("priority", "LOW")
                        action = rec.get("action", "")
                        rationale = rec.get("rationale", "")
                        emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(priority, "⚪")
                        report_lines.append(f"{emoji} **{action}** [{priority}]")
                        report_lines.append(f"   - {rationale}")
                        report_lines.append("")

            # Regime Analysis (if provided)
            if regimes:
                report_lines.append("## 🔄 Regime Analysis\n")
                for regime_name, regime_data in regimes.items():
                    if isinstance(regime_data, dict):
                        report_lines.append(f"### {regime_name}")
                        report_lines.append(
                            f"- Time in regime: {regime_data.get('pct_time', 0):.1f}%"
                        )
                        report_lines.append(
                            f"- Return: {regime_data.get('total_return', 0) * 100:.2f}%"
                        )
                        report_lines.append(f"- Sharpe: {regime_data.get('sharpe_ratio', 0):.2f}")
                        report_lines.append(
                            f"- Max DD: {regime_data.get('max_drawdown', 0) * 100:.1f}%"
                        )
                        report_lines.append("")

            # Footer
            report_lines.append("---")
            report_lines.append("*Report generated by InsightGenerator*")

            report = "\n".join(report_lines)
            logger.info("Markdown report formatted successfully")
            return report

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error formatting markdown report: {e}", exc_info=True)
            return f"# Error Generating Report\n\n{e!s}"

    def get_insights(self) -> list[str]:
        """Get last generated insights."""
        return self.insights

    def get_warnings(self) -> list[dict[str, Any]]:
        """Get last generated warnings."""
        return self.warnings

    def get_recommendations(self) -> list[dict[str, Any]]:
        """Get last generated recommendations."""
        return self.recommendations
