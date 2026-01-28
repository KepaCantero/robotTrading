"""
T9.1: ReportingGenerator - Generate comprehensive performance reports

Creates HTML reports with performance metrics, visualizations, and recommendations.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from .models import AllocationSnapshot, PerformanceReport, ReportGenerationRequest, StrategyMetrics

logger = logging.getLogger(__name__)


class ReportingGenerator:
    """
    Generates comprehensive performance reports.

    Features:
    - HTML report generation
    - Performance metrics assessment
    - Strength/weakness identification
    - Improvement recommendations
    - Metric-to-rating mapping
    """

    # Metric thresholds for rating
    METRIC_THRESHOLDS = {
        "sharpe_ratio": {
            "excellent": Decimal("2.0"),
            "good": Decimal("1.0"),
            "neutral": Decimal("0.5"),
        },
        "annual_return_pct": {
            "excellent": Decimal("25"),
            "good": Decimal("15"),
            "neutral": Decimal("5"),
        },
        "max_drawdown_pct": {
            "excellent": Decimal("10"),
            "good": Decimal("20"),
            "neutral": Decimal("30"),
        },
        "win_rate_pct": {
            "excellent": Decimal("60"),
            "good": Decimal("50"),
            "neutral": Decimal("40"),
        },
    }

    def __init__(self):
        """Initialize reporting generator."""
        self.report_history: List[PerformanceReport] = []
        logger.info("✅ ReportingGenerator initialized")

    async def generate_report(
        self,
        request: ReportGenerationRequest,
    ) -> PerformanceReport:
        """
        Generate comprehensive performance report.

        Args:
            request: Report generation request with metrics and allocations

        Returns:
            PerformanceReport with HTML content and assessment
        """
        start_time = datetime.utcnow()

        try:
            # Assess metrics
            overall_rating = await self._assess_overall_performance(request.backtest_metrics)

            # Identify strengths
            strengths = await self._identify_strengths(
                request.backtest_metrics,
                request.target_annual_return_pct,
                request.max_acceptable_drawdown_pct,
            )

            # Identify weaknesses
            weaknesses = await self._identify_weaknesses(
                request.backtest_metrics,
                request.target_annual_return_pct,
                request.max_acceptable_drawdown_pct,
            )

            # Generate recommendations
            recommendations = await self._generate_recommendations(
                weaknesses,
                request.backtest_metrics,
                request.allocations,
            )

            # Generate summary
            summary = await self._generate_summary(
                request.strategy_name,
                overall_rating,
                request.backtest_metrics,
            )

            # Generate HTML content
            html_content = await self._generate_html_content(
                request,
                overall_rating,
                strengths,
                weaknesses,
                recommendations,
            )

            result = PerformanceReport(
                success=True,
                report_id=request.report_id,
                profile_id=request.profile_id,
                strategy_name=request.strategy_name,
                title=f"Performance Report: {request.strategy_name}",
                summary=summary,
                metrics=request.backtest_metrics,
                allocations=request.allocations,
                overall_rating=overall_rating,
                strengths=strengths,
                weaknesses=weaknesses,
                recommendations=recommendations,
                html_content=html_content,
                charts_data=self._prepare_charts_data(request.backtest_metrics),
            )

            self.report_history.append(result)

            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(
                f"✅ Report generated for {request.profile_id}, "
                f"rating={overall_rating}, elapsed={elapsed_ms:.0f}ms"
            )
            return result

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"❌ Error generating report: {e}")
            return PerformanceReport(
                success=False,
                report_id=request.report_id,
                profile_id=request.profile_id,
                strategy_name=request.strategy_name,
                title=f"Performance Report: {request.strategy_name}",
                summary="Report generation failed",
                metrics=request.backtest_metrics,
                allocations=request.allocations,
                error_message=str(e),
            )

    async def _assess_overall_performance(self, metrics: StrategyMetrics) -> str:
        """Assess overall performance rating."""
        scores = []

        # Sharpe ratio score (most important)
        if metrics.sharpe_ratio >= Decimal("2.0"):
            scores.append(3)  # Excellent
        elif metrics.sharpe_ratio >= Decimal("1.0"):
            scores.append(2)  # Good
        elif metrics.sharpe_ratio >= Decimal("0.5"):
            scores.append(1)  # Neutral
        else:
            scores.append(0)  # Poor

        # Annual return score
        if metrics.annual_return_pct >= Decimal("25"):
            scores.append(3)
        elif metrics.annual_return_pct >= Decimal("15"):
            scores.append(2)
        elif metrics.annual_return_pct >= Decimal("5"):
            scores.append(1)
        else:
            scores.append(0)

        # Drawdown score (inverse - lower is better)
        if metrics.max_drawdown_pct <= Decimal("10"):
            scores.append(3)
        elif metrics.max_drawdown_pct <= Decimal("20"):
            scores.append(2)
        elif metrics.max_drawdown_pct <= Decimal("30"):
            scores.append(1)
        else:
            scores.append(0)

        # Win rate score
        if metrics.win_rate_pct >= Decimal("60"):
            scores.append(3)
        elif metrics.win_rate_pct >= Decimal("50"):
            scores.append(2)
        elif metrics.win_rate_pct >= Decimal("40"):
            scores.append(1)
        else:
            scores.append(0)

        avg_score = sum(scores) / len(scores)

        if avg_score >= 2.5:
            return "excellent"
        elif avg_score >= 1.75:
            return "good"
        elif avg_score >= 0.75:
            return "neutral"
        else:
            return "poor"

    async def _identify_strengths(
        self,
        metrics: StrategyMetrics,
        target_return: Decimal,
        target_drawdown: Decimal,
    ) -> List[str]:
        """Identify strategy strengths."""
        strengths = []

        # High Sharpe ratio
        if metrics.sharpe_ratio >= Decimal("1.5"):
            strengths.append(
                f"Exceptional risk-adjusted returns (Sharpe: {metrics.sharpe_ratio:.2f})"
            )

        # High return
        if metrics.annual_return_pct >= target_return * Decimal("1.2"):
            strengths.append(
                f"Exceeds target return by {((metrics.annual_return_pct / target_return) - 1) * 100:.1f}%"
            )

        # Low drawdown
        if metrics.max_drawdown_pct <= target_drawdown * Decimal("0.5"):
            strengths.append(
                f"Excellent downside protection (Drawdown: {metrics.max_drawdown_pct:.1f}%)"
            )

        # High win rate
        if metrics.win_rate_pct >= Decimal("55"):
            strengths.append(f"Strong win rate ({metrics.win_rate_pct:.1f}% of trades profitable)")

        # High profit factor
        if metrics.profit_factor >= Decimal("2.0"):
            strengths.append(
                f"High profit factor ({metrics.profit_factor:.2f}x: wins exceed losses)"
            )

        # Sortino ratio
        if metrics.sortino_ratio >= Decimal("2.0"):
            strengths.append(
                f"Excellent downside-adjusted performance (Sortino: {metrics.sortino_ratio:.2f})"
            )

        return strengths if strengths else ["Baseline performance characteristics"]

    async def _identify_weaknesses(
        self,
        metrics: StrategyMetrics,
        target_return: Decimal,
        target_drawdown: Decimal,
    ) -> List[str]:
        """Identify strategy weaknesses."""
        weaknesses = []

        # Low Sharpe ratio
        if metrics.sharpe_ratio < Decimal("0.5"):
            weaknesses.append(f"Poor risk-adjusted returns (Sharpe: {metrics.sharpe_ratio:.2f})")

        # Below target return
        if metrics.annual_return_pct < target_return * Decimal("0.8"):
            weaknesses.append(
                f"Underperforming target return (Actual: {metrics.annual_return_pct:.1f}%, Target: {target_return:.1f}%)"
            )

        # High drawdown
        if metrics.max_drawdown_pct > target_drawdown * Decimal("1.2"):
            weaknesses.append(
                f"Exceeding acceptable drawdown limits (Actual: {metrics.max_drawdown_pct:.1f}%, Max: {target_drawdown:.1f}%)"
            )

        # Low win rate
        if metrics.win_rate_pct < Decimal("45"):
            weaknesses.append(
                f"Low win rate ({metrics.win_rate_pct:.1f}% - less than half trades profitable)"
            )

        # Low profit factor
        if metrics.profit_factor < Decimal("1.5"):
            weaknesses.append(
                f"Weak profit factor ({metrics.profit_factor:.2f}x - losses approach wins)"
            )

        # High volatility
        if metrics.volatility_pct > Decimal("25"):
            weaknesses.append(f"High portfolio volatility ({metrics.volatility_pct:.1f}% annual)")

        return weaknesses if weaknesses else []

    async def _generate_recommendations(
        self,
        weaknesses: List[str],
        metrics: StrategyMetrics,
        allocations: List[AllocationSnapshot],
    ) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []

        # If no weaknesses, suggest optimization
        if not weaknesses:
            recommendations.append("Consider rebalancing to optimize risk-return further")
            recommendations.append("Monitor performance regularly and adjust as needed")
            return recommendations

        # Address drawdown issues
        if any("drawdown" in w.lower() for w in weaknesses):
            recommendations.append(
                "Reduce allocation to high-volatility modules (momentum, transformer_engine)"
            )
            recommendations.append(
                "Increase allocation to defensive strategies (mean_reversion, pairs_trading)"
            )
            recommendations.append(
                "Consider adding mean reversion or pairs trading for downside protection"
            )

        # Address return issues
        if any("return" in w.lower() or "underperforming" in w.lower() for w in weaknesses):
            recommendations.append(
                "Increase allocation to higher-return modules (momentum, ML strategies)"
            )
            recommendations.append("Consider enabling additional growth-oriented strategies")
            recommendations.append("Review module parameters - may need more aggressive tuning")

        # Address win rate issues
        if any("win rate" in w.lower() for w in weaknesses):
            recommendations.append("Improve entry/exit logic in selected modules")
            recommendations.append(
                "Consider ensemble approach to combine strengths of multiple strategies"
            )
            recommendations.append("Reduce position size to protect against losing streaks")

        # Address volatility issues
        if any("volatility" in w.lower() for w in weaknesses):
            recommendations.append("Reduce leverage or position sizes")
            recommendations.append("Add less volatile strategies to portfolio mix")

        return recommendations if recommendations else ["Continue monitoring strategy performance"]

    async def _generate_summary(
        self,
        strategy_name: str,
        rating: str,
        metrics: StrategyMetrics,
    ) -> str:
        """Generate executive summary."""
        rating_text = {
            "excellent": "performs exceptionally well",
            "good": "performs well",
            "neutral": "shows mixed results",
            "poor": "underperforms expectations",
        }.get(rating, "shows neutral performance")

        summary = (
            f"The {strategy_name} strategy {rating_text} with an annual return of "
            f"{metrics.annual_return_pct:.1f}% and a Sharpe ratio of {metrics.sharpe_ratio:.2f}. "
            f"Maximum drawdown of {metrics.max_drawdown_pct:.1f}% and a win rate of "
            f"{metrics.win_rate_pct:.1f}% indicate a "
        )

        if metrics.sharpe_ratio >= Decimal("1.5"):
            summary += "strong risk-adjusted return profile. "
        elif metrics.sharpe_ratio >= Decimal("0.5"):
            summary += "moderate risk-adjusted return profile. "
        else:
            summary += "weak risk-adjusted return profile. "

        summary += f"The strategy executed {metrics.num_trades} trades with a profit factor of {metrics.profit_factor:.2f}."

        return summary

    async def _generate_html_content(
        self,
        request: ReportGenerationRequest,
        rating: str,
        strengths: List[str],
        weaknesses: List[str],
        recommendations: List[str],
    ) -> str:
        """Generate HTML report content."""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{request.strategy_name} Performance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
                .container {{ background: white; padding: 30px; border-radius: 8px; }}
                h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
                h2 {{ color: #555; margin-top: 30px; }}
                .metric {{ display: inline-block; margin: 20px; padding: 15px; background: #f9f9f9; border-radius: 5px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
                .metric-label {{ font-size: 12px; color: #666; }}
                .rating-excellent {{ color: #28a745; }}
                .rating-good {{ color: #17a2b8; }}
                .rating-neutral {{ color: #ffc107; }}
                .rating-poor {{ color: #dc3545; }}
                .strengths {{ background: #d4edda; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .weaknesses {{ background: #f8d7da; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .recommendations {{ background: #d1ecf1; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                ul {{ line-height: 1.8; }}
                .allocation-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .allocation-table th, .allocation-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .allocation-table th {{ background: #007bff; color: white; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{request.strategy_name} Performance Report</h1>
                <p><strong>Generated:</strong> {timestamp}</p>
                <p><strong>Profile ID:</strong> {request.profile_id}</p>

                <h2>Overall Rating: <span class="rating-{rating}">{rating.upper()}</span></h2>

                <h2>Key Metrics</h2>
                <div class="metric">
                    <div class="metric-label">Annual Return</div>
                    <div class="metric-value">{request.backtest_metrics.annual_return_pct:.2f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Sharpe Ratio</div>
                    <div class="metric-value">{request.backtest_metrics.sharpe_ratio:.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Max Drawdown</div>
                    <div class="metric-value">{request.backtest_metrics.max_drawdown_pct:.2f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Win Rate</div>
                    <div class="metric-value">{request.backtest_metrics.win_rate_pct:.2f}%</div>
                </div>

                <h2>Portfolio Allocation</h2>
                <table class="allocation-table">
                    <tr>
                        <th>Module</th>
                        <th>Allocation</th>
                        <th>Return Contribution</th>
                        <th>Risk Contribution</th>
                    </tr>
        """

        for alloc in request.allocations:
            html += f"""
                    <tr>
                        <td>{alloc.module_name}</td>
                        <td>{alloc.allocation_pct:.2f}%</td>
                        <td>{alloc.expected_return_contribution_pct:.2f}%</td>
                        <td>{alloc.risk_contribution_pct:.2f}%</td>
                    </tr>
            """

        html += """
                </table>
        """

        if strengths:
            html += """
                <h2>Strengths</h2>
                <div class="strengths">
                    <ul>
        """
            for strength in strengths:
                html += f"<li>{strength}</li>\n"
            html += """
                    </ul>
                </div>
        """

        if weaknesses:
            html += """
                <h2>Areas for Improvement</h2>
                <div class="weaknesses">
                    <ul>
        """
            for weakness in weaknesses:
                html += f"<li>{weakness}</li>\n"
            html += """
                    </ul>
                </div>
        """

        if recommendations:
            html += """
                <h2>Recommendations</h2>
                <div class="recommendations">
                    <ul>
        """
            for rec in recommendations:
                html += f"<li>{rec}</li>\n"
            html += """
                    </ul>
                </div>
        """

        html += """
            </div>
        </body>
        </html>
        """

        return html

    def _prepare_charts_data(self, metrics: StrategyMetrics) -> Dict:
        """Prepare data for charts and visualizations."""
        return {
            "performance": {
                "annual_return": float(metrics.annual_return_pct),
                "max_drawdown": float(metrics.max_drawdown_pct),
                "sharpe_ratio": float(metrics.sharpe_ratio),
            },
            "metrics": {
                "win_rate": float(metrics.win_rate_pct),
                "profit_factor": float(metrics.profit_factor),
                "volatility": float(metrics.volatility_pct),
            },
        }

    async def get_report_history(
        self,
        limit: Optional[int] = None,
    ) -> List[PerformanceReport]:
        """Get report history."""
        results = self.report_history
        if limit:
            results = results[-limit:]
        return results

    def get_generator_status(self) -> Dict:
        """Get generator operational status."""
        successful = sum(1 for r in self.report_history if r.success)
        total = len(self.report_history)

        ratings = {}
        for report in self.report_history:
            rating = report.overall_rating
            ratings[rating] = ratings.get(rating, 0) + 1

        return {
            "total_reports": total,
            "successful_reports": successful,
            "success_rate": successful / max(1, total),
            "rating_distribution": ratings,
            "history_size": total,
        }


# Singleton
_generator: Optional["ReportingGenerator"] = None


def get_reporting_generator() -> ReportingGenerator:
    """Get or create singleton ReportingGenerator."""
    global _generator
    if _generator is None:
        _generator = ReportingGenerator()

    return _generator
