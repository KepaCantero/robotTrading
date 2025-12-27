"""
T9.1: ReportingGenerator - Generate performance reports

Creates detailed performance analysis and visual reports.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PerformanceReport:
    """Performance report data."""

    report_id: str
    strategy_name: str
    generated_at: str
    summary: Dict
    metrics: Dict
    risk_metrics: Dict
    allocation: Dict[str, float]
    monthly_returns: List[float]
    html_report: str
    pdf_report: Optional[str] = None


class ReportingGenerator:
    """
    T9.1: Generates comprehensive performance reports.

    Creates:
    - Performance summaries
    - Risk analysis
    - Return attribution
    - Portfolio charts
    - HTML and PDF reports
    """

    def __init__(self):
        """Initialize ReportingGenerator."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("✅ ReportingGenerator initialized")

    async def generate_report(
        self,
        strategy_name: str,
        backtest_result: Dict,
        allocation: Dict[str, float],
        monthly_returns: List[float],
        recommendation: Optional[Dict] = None,
    ) -> PerformanceReport:
        """
        Generate comprehensive performance report.

        Args:
            strategy_name: Name of strategy
            backtest_result: Backtest results with metrics
            allocation: Portfolio allocation
            monthly_returns: Monthly returns for chart
            recommendation: Optional recommendation details

        Returns:
            PerformanceReport with full analysis
        """
        try:
            report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Extract and organize metrics
            summary = await self._generate_summary(strategy_name, backtest_result)
            metrics = await self._extract_metrics(backtest_result)
            risk_metrics = await self._calculate_risk_metrics(backtest_result, monthly_returns)

            # Generate HTML report
            html_report = await self._generate_html_report(
                strategy_name, summary, metrics, risk_metrics, allocation
            )

            self.logger.info(f"📊 Report generated: {report_id}")

            return PerformanceReport(
                report_id=report_id,
                strategy_name=strategy_name,
                generated_at=datetime.now().isoformat(),
                summary=summary,
                metrics=metrics,
                risk_metrics=risk_metrics,
                allocation=allocation,
                monthly_returns=monthly_returns,
                html_report=html_report,
            )

        except Exception as e:
            self.logger.error(f"❌ Error generating report: {e}")
            raise

    async def _generate_summary(self, strategy_name: str, backtest_result: Dict) -> Dict:
        """Generate summary statistics."""
        return {
            "strategy_name": strategy_name,
            "total_return": backtest_result.get("total_return", 0.0),
            "annual_return": backtest_result.get("total_return", 0.0),
            "sharpe_ratio": backtest_result.get("sharpe_ratio", 0.0),
            "max_drawdown": backtest_result.get("max_drawdown", 0.0),
            "final_capital": backtest_result.get("final_capital", 0.0),
            "win_rate": backtest_result.get("win_rate", 0.0),
        }

    async def _extract_metrics(self, backtest_result: Dict) -> Dict:
        """Extract performance metrics."""
        return {
            "total_return": self._safe_float(backtest_result.get("total_return", 0.0)),
            "annual_return": self._safe_float(backtest_result.get("total_return", 0.0)),
            "sharpe_ratio": self._safe_float(backtest_result.get("sharpe_ratio", 0.0)),
            "sortino_ratio": self._safe_float(backtest_result.get("sortino_ratio", 0.0)),
            "max_drawdown": self._safe_float(backtest_result.get("max_drawdown", 0.0)),
            "win_rate": self._safe_float(backtest_result.get("win_rate", 0.0)),
            "profit_factor": self._safe_float(backtest_result.get("profit_factor", 0.0)),
            "total_trades": int(backtest_result.get("total_trades", 0)),
        }

    async def _calculate_risk_metrics(
        self, backtest_result: Dict, monthly_returns: List[float]
    ) -> Dict:
        """Calculate risk metrics."""
        # Calculate volatility from monthly returns
        if monthly_returns:
            avg_return = sum(monthly_returns) / len(monthly_returns)
            variance = sum((r - avg_return) ** 2 for r in monthly_returns) / len(monthly_returns)
            volatility = variance**0.5
        else:
            volatility = 0.0

        return {
            "volatility": volatility,
            "max_drawdown": backtest_result.get("max_drawdown", 0.0),
            "var_95": self._calculate_var(monthly_returns, 0.95),
            "cvar_95": self._calculate_cvar(monthly_returns, 0.95),
            "calmar_ratio": self._calculate_calmar_ratio(
                backtest_result.get("total_return", 0.0),
                backtest_result.get("max_drawdown", -0.01),
            ),
        }

    def _calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """Calculate Value at Risk."""
        if not returns:
            return 0.0
        sorted_returns = sorted(returns)
        index = int(len(sorted_returns) * (1 - confidence))
        return sorted_returns[index] if index < len(sorted_returns) else 0.0

    def _calculate_cvar(self, returns: List[float], confidence: float = 0.95) -> float:
        """Calculate Conditional Value at Risk (CVaR)."""
        if not returns:
            return 0.0
        sorted_returns = sorted(returns)
        index = int(len(sorted_returns) * (1 - confidence))
        return sum(sorted_returns[:index]) / max(index, 1)

    def _calculate_calmar_ratio(self, annual_return: float, max_drawdown: float) -> float:
        """Calculate Calmar ratio."""
        if max_drawdown == 0 or max_drawdown > -0.001:
            return 0.0
        return annual_return / abs(max_drawdown)

    async def _generate_html_report(
        self,
        strategy_name: str,
        summary: Dict,
        metrics: Dict,
        risk_metrics: Dict,
        allocation: Dict[str, float],
    ) -> str:
        """Generate HTML report."""
        html = f"""
        <html>
            <head>
                <title>Strategy Report: {strategy_name}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #333; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .metric-value {{ font-weight: bold; }}
                </style>
            </head>
            <body>
                <h1>Strategy Performance Report: {strategy_name}</h1>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

                <h2>Performance Summary</h2>
                <table>
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Annual Return</td><td class="metric-value">{summary['annual_return']*100:.2f}%</td></tr>
                    <tr><td>Sharpe Ratio</td><td class="metric-value">{summary['sharpe_ratio']:.2f}</td></tr>
                    <tr><td>Max Drawdown</td><td class="metric-value">{summary['max_drawdown']*100:.2f}%</td></tr>
                    <tr><td>Win Rate</td><td class="metric-value">{summary['win_rate']*100:.1f}%</td></tr>
                </table>

                <h2>Risk Metrics</h2>
                <table>
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Volatility</td><td class="metric-value">{risk_metrics['volatility']*100:.2f}%</td></tr>
                    <tr><td>VaR (95%)</td><td class="metric-value">{risk_metrics['var_95']*100:.2f}%</td></tr>
                    <tr><td>CVaR (95%)</td><td class="metric-value">{risk_metrics['cvar_95']*100:.2f}%</td></tr>
                    <tr><td>Calmar Ratio</td><td class="metric-value">{risk_metrics['calmar_ratio']:.2f}</td></tr>
                </table>

                <h2>Portfolio Allocation</h2>
                <table>
                    <tr><th>Asset</th><th>Weight</th></tr>
        """

        for asset, weight in allocation.items():
            html += f"<tr><td>{asset}</td><td class='metric-value'>{weight*100:.1f}%</td></tr>"

        html += """
                </table>

                <footer>
                    <p>This report was automatically generated. Performance is not a guarantee of future results.</p>
                </footer>
            </body>
        </html>
        """

        return html

    @staticmethod
    def _safe_float(value) -> float:
        """Safely convert value to float."""
        try:
            return float(value) if value is not None else 0.0
        except (ValueError, TypeError):
            return 0.0
