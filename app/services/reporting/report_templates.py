"""
T9.1.1: ReportTemplates - HTML report templates for performance reporting

Provides professional HTML templates for strategy performance reports.
"""

import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ReportTemplates:
    """
    Generates professional HTML report templates for trading strategy analysis.

    Includes:
    - Performance summary table
    - Risk metrics dashboard
    - Portfolio allocation visualization
    - Trade analysis and statistics
    """

    # CSS Styling
    CSS_STYLE = """
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f7fa;
            color: #2c3e50;
            line-height: 1.6;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 40px;
        }

        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
            margin-bottom: 30px;
            font-size: 2.2em;
        }

        h2 {
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 1.5em;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }

        .header-info {
            background: #ecf0f1;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 30px;
            font-size: 0.9em;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }

        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }

        .metric-card.positive {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }

        .metric-card.negative {
            background: linear-gradient(135deg, #ee0979 0%, #ff6a00 100%);
        }

        .metric-value {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }

        .metric-label {
            font-size: 0.9em;
            opacity: 0.9;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
        }

        th {
            background-color: #34495e;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }

        td {
            padding: 12px;
            border-bottom: 1px solid #ecf0f1;
        }

        tr:hover {
            background-color: #f9f9f9;
        }

        tr:last-child td {
            border-bottom: none;
        }

        .number {
            font-family: 'Courier New', monospace;
            text-align: right;
            font-weight: 500;
        }

        .positive {
            color: #27ae60;
        }

        .negative {
            color: #e74c3c;
        }

        .allocation-bar {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            height: 20px;
            border-radius: 4px;
            display: inline-block;
        }

        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            font-size: 0.85em;
            color: #7f8c8d;
            text-align: center;
        }

        .summary {
            background: #ecf0f1;
            padding: 20px;
            border-radius: 4px;
            margin: 20px 0;
        }

        @media print {
            body {
                background: white;
            }
            .container {
                box-shadow: none;
                padding: 0;
            }
        }
    </style>
    """

    def __init__(self):
        """Initialize report templates."""
        logger.info("✅ ReportTemplates initialized")

    def generate_performance_report_html(
        self,
        strategy_name: str,
        summary: Dict,
        metrics: Dict,
        risk_metrics: Dict,
        allocation: Dict[str, float],
    ) -> str:
        """
        Generate complete HTML performance report.

        Args:
            strategy_name: Name of strategy
            summary: Performance summary dict
            metrics: Performance metrics dict
            risk_metrics: Risk metrics dict
            allocation: Portfolio allocation dict

        Returns:
            Complete HTML string
        """
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Strategy Report: {strategy_name}</title>
            {self.CSS_STYLE}
        </head>
        <body>
            <div class="container">
                <h1>📊 Strategy Performance Report</h1>
                <div class="header-info">
                    <strong>Strategy:</strong> {strategy_name}<br>
                    <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}<br>
                    <strong>Report Type:</strong> Comprehensive Performance Analysis
                </div>

                {self._generate_performance_summary_html(summary)}
                {self._generate_metrics_table_html(metrics)}
                {self._generate_risk_metrics_table_html(risk_metrics)}
                {self._generate_allocation_table_html(allocation)}

                <div class="footer">
                    <p>This report was automatically generated. Past performance does not guarantee future results.</p>
                    <p>© 2025 AlgoTrading System | Confidential</p>
                </div>
            </div>
        </body>
        </html>
        """
        logger.info(f"Generated HTML report for strategy: {strategy_name}")
        return html

    def _generate_performance_summary_html(self, summary: Dict) -> str:
        """Generate performance summary cards."""
        total_return_pct = (summary.get("total_return", 0) or 0) * 100
        sharpe = summary.get("sharpe_ratio", 0) or 0
        max_dd_pct = (summary.get("max_drawdown", 0) or 0) * 100
        win_rate_pct = (summary.get("win_rate", 0) or 0) * 100

        return f"""
        <h2>📈 Performance Summary</h2>
        <div class="metrics-grid">
            <div class="metric-card {'positive' if total_return_pct >= 0 else 'negative'}">
                <div class="metric-label">Total Return</div>
                <div class="metric-value">{total_return_pct:+.2f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Sharpe Ratio</div>
                <div class="metric-value">{sharpe:.2f}</div>
            </div>
            <div class="metric-card negative">
                <div class="metric-label">Max Drawdown</div>
                <div class="metric-value">{max_dd_pct:.2f}%</div>
            </div>
            <div class="metric-card {'positive' if win_rate_pct >= 50 else 'negative'}">
                <div class="metric-label">Win Rate</div>
                <div class="metric-value">{win_rate_pct:.1f}%</div>
            </div>
        </div>
        """

    def _generate_metrics_table_html(self, metrics: Dict) -> str:
        """Generate performance metrics table."""
        html = """
        <h2>📊 Performance Metrics</h2>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th class="number">Value</th>
                </tr>
            </thead>
            <tbody>
        """

        metric_definitions = {
            "total_return": ("Total Return", lambda x: f"{x*100:+.2f}%"),
            "annual_return": ("Annual Return", lambda x: f"{x*100:+.2f}%"),
            "sharpe_ratio": ("Sharpe Ratio", lambda x: f"{x:.3f}"),
            "sortino_ratio": ("Sortino Ratio", lambda x: f"{x:.3f}"),
            "max_drawdown": ("Max Drawdown", lambda x: f"{x*100:.2f}%"),
            "win_rate": ("Win Rate", lambda x: f"{x*100:.1f}%"),
            "profit_factor": ("Profit Factor", lambda x: f"{x:.2f}"),
            "total_trades": ("Total Trades", lambda x: f"{int(x)}"),
        }

        for key, (label, formatter) in metric_definitions.items():
            value = metrics.get(key, 0)
            if value is not None:
                formatted = formatter(value)
                html += f"""
                <tr>
                    <td>{label}</td>
                    <td class="number">{formatted}</td>
                </tr>
                """

        html += """
            </tbody>
        </table>
        """
        return html

    def _generate_risk_metrics_table_html(self, risk_metrics: Dict) -> str:
        """Generate risk metrics table."""
        html = """
        <h2>⚠️ Risk Metrics</h2>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th class="number">Value</th>
                </tr>
            </thead>
            <tbody>
        """

        risk_definitions = {
            "volatility": ("Volatility", lambda x: f"{x*100:.2f}%"),
            "max_drawdown": ("Max Drawdown", lambda x: f"{x*100:.2f}%"),
            "var_95": ("Value at Risk (95%)", lambda x: f"{x*100:.2f}%"),
            "cvar_95": ("Conditional VaR (95%)", lambda x: f"{x*100:.2f}%"),
            "calmar_ratio": ("Calmar Ratio", lambda x: f"{x:.2f}"),
        }

        for key, (label, formatter) in risk_definitions.items():
            value = risk_metrics.get(key, 0)
            if value is not None:
                formatted = formatter(value)
                html += f"""
                <tr>
                    <td>{label}</td>
                    <td class="number">{formatted}</td>
                </tr>
                """

        html += """
            </tbody>
        </table>
        """
        return html

    def _generate_allocation_table_html(self, allocation: Dict[str, float]) -> str:
        """Generate allocation table."""
        html = """
        <h2>🎯 Portfolio Allocation</h2>
        <table>
            <thead>
                <tr>
                    <th>Asset</th>
                    <th class="number">Weight</th>
                    <th style="width: 200px;">Visual</th>
                </tr>
            </thead>
            <tbody>
        """

        sorted_allocation = sorted(allocation.items(), key=lambda x: x[1], reverse=True)

        for asset, weight in sorted_allocation:
            weight_pct = weight * 100
            html += f"""
            <tr>
                <td><strong>{asset}</strong></td>
                <td class="number">{weight_pct:.1f}%</td>
                <td>
                    <div class="allocation-bar" style="width: {weight_pct * 2}px;"></div>
                </td>
            </tr>
            """

        html += """
            </tbody>
        </table>
        """
        return html

    def generate_simple_summary_html(
        self,
        strategy_name: str,
        return_pct: float,
        sharpe: float,
        drawdown_pct: float,
    ) -> str:
        """Generate simple one-page summary."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{strategy_name} Summary</title>
            {self.CSS_STYLE}
        </head>
        <body>
            <div class="container">
                <h1>{strategy_name} - Quick Summary</h1>
                <div class="summary">
                    <p><strong>Return:</strong> {return_pct:+.2f}%</p>
                    <p><strong>Sharpe Ratio:</strong> {sharpe:.2f}</p>
                    <p><strong>Max Drawdown:</strong> {drawdown_pct:.2f}%</p>
                </div>
            </div>
        </body>
        </html>
        """


# Singleton
_templates: Optional[ReportTemplates] = None


def get_report_templates() -> ReportTemplates:
    """Get or create singleton ReportTemplates."""
    global _templates
    if _templates is None:
        _templates = ReportTemplates()
    return _templates
