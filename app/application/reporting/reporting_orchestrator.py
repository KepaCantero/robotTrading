"""
T9.1.3: ReportingOrchestrator - Orchestrate complete report generation

Integrates templates, metrics, and portfolio data to generate comprehensive reports.
"""

import logging
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from app.application.reporting.quantstats_integration import get_quantstats_integration
from app.application.reporting.report_templates import get_report_templates

logger = logging.getLogger(__name__)


class ReportingOrchestrator:
    """
    T9.1.3: Orchestrates comprehensive performance report generation.

    Combines:
    1. HTML templates for presentation
    2. Advanced metrics from QuantStats
    3. Portfolio allocation visualization
    4. Risk analysis summaries
    """

    def __init__(self):
        """Initialize orchestrator."""
        self.templates = get_report_templates()
        self.metrics_calculator = get_quantstats_integration()
        logger.info("✅ ReportingOrchestrator initialized")

    async def generate_comprehensive_report(
        self,
        strategy_name: str,
        backtest_result: dict,
        portfolio_allocation: dict[str, float],
        returns: Optional[pd.Series] = None,
        recommendation: Optional[dict] = None,
    ) -> dict:
        """
        Generate complete performance report.

        Args:
            strategy_name: Strategy name
            backtest_result: Backtest results with metrics
            portfolio_allocation: Portfolio weights
            returns: Optional returns series for advanced metrics
            recommendation: Optional recommendation details

        Returns:
            Dict with complete report
        """
        try:
            report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Extract summary from backtest result
            summary = {
                "total_return": backtest_result.get("total_return", 0),
                "annual_return": backtest_result.get("total_return", 0),
                "sharpe_ratio": backtest_result.get("sharpe_ratio", 0),
                "max_drawdown": backtest_result.get("max_drawdown", 0),
                "win_rate": backtest_result.get("win_rate", 0),
            }

            # Extract basic metrics
            metrics = {
                "total_return": backtest_result.get("total_return", 0),
                "annual_return": backtest_result.get("total_return", 0),
                "sharpe_ratio": backtest_result.get("sharpe_ratio", 0),
                "sortino_ratio": backtest_result.get("sortino_ratio", 0),
                "max_drawdown": backtest_result.get("max_drawdown", 0),
                "win_rate": backtest_result.get("win_rate", 0),
                "profit_factor": backtest_result.get("profit_factor", 0),
                "total_trades": backtest_result.get("total_trades", 0),
            }

            # Calculate risk metrics
            risk_metrics = await self._calculate_risk_metrics(backtest_result)

            # Calculate advanced metrics if returns available
            advanced_metrics = {}
            if returns is not None and len(returns) > 0:
                advanced_metrics = self.metrics_calculator.calculate_advanced_metrics(returns)
                metrics.update(advanced_metrics)

            # Generate HTML report
            html_report = self.templates.generate_performance_report_html(
                strategy_name=strategy_name,
                summary=summary,
                metrics=metrics,
                risk_metrics=risk_metrics,
                allocation=portfolio_allocation,
            )

            result = {
                "report_id": report_id,
                "strategy_name": strategy_name,
                "generated_at": datetime.now().isoformat(),
                "summary": summary,
                "metrics": metrics,
                "risk_metrics": risk_metrics,
                "advanced_metrics": advanced_metrics,
                "allocation": portfolio_allocation,
                "html_report": html_report,
                "recommendation": recommendation or {},
            }

            logger.info(f"✅ Generated comprehensive report: {report_id}")
            return result

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"❌ Error generating report: {e}")
            raise

    async def _calculate_risk_metrics(self, backtest_result: dict) -> dict:
        """Calculate risk metrics from backtest result."""
        return {
            "volatility": backtest_result.get("volatility", 0),
            "max_drawdown": backtest_result.get("max_drawdown", 0),
            "var_95": self._calculate_var(backtest_result.get("monthly_returns", []), 0.95),
            "cvar_95": self._calculate_cvar(backtest_result.get("monthly_returns", []), 0.95),
            "calmar_ratio": self._calculate_calmar(
                backtest_result.get("total_return", 0),
                backtest_result.get("max_drawdown", -0.01),
            ),
        }

    @staticmethod
    def _calculate_var(returns: list, confidence: float = 0.95) -> float:
        """Calculate Value at Risk."""
        if not returns:
            return 0.0
        sorted_returns = sorted(returns)
        index = int(len(sorted_returns) * (1 - confidence))
        return float(sorted_returns[index] if index < len(sorted_returns) else 0.0)

    @staticmethod
    def _calculate_cvar(returns: list, confidence: float = 0.95) -> float:
        """Calculate Conditional Value at Risk."""
        if not returns:
            return 0.0
        sorted_returns = sorted(returns)
        index = int(len(sorted_returns) * (1 - confidence))
        tail = sorted_returns[: max(index, 1)]
        return float(np.mean(tail)) if tail else 0.0

    @staticmethod
    def _calculate_calmar(annual_return: float, max_drawdown: float) -> float:
        """Calculate Calmar ratio."""
        if max_drawdown >= -0.001 or max_drawdown == 0:
            return 0.0
        return float(annual_return / abs(max_drawdown))

    async def generate_executive_summary(
        self,
        strategy_name: str,
        total_return_pct: float,
        sharpe_ratio: float,
        max_drawdown_pct: float,
        recommendation_text: str = "",
    ) -> str:
        """Generate simple executive summary."""
        html = self.templates.generate_simple_summary_html(
            strategy_name=strategy_name,
            return_pct=total_return_pct,
            sharpe=sharpe_ratio,
            drawdown_pct=max_drawdown_pct,
        )

        if recommendation_text:
            # Add recommendation to summary
            html = html.replace(
                "</div>\n            </div>\n        </body>",
                """</div>
                <div class="summary">
                    <h3>Recommendation</h3>
                    <p>{recommendation_text}</p>
                </div>
            </div>
        </body>""",
            )

        return html


# Singleton
_orchestrator: Optional[ReportingOrchestrator] = None


def get_reporting_orchestrator() -> ReportingOrchestrator:
    """Get or create singleton ReportingOrchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ReportingOrchestrator()

    return _orchestrator
