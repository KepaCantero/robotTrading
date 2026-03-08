"""
Professional Reporter for Backtesting System (Req #16)

Generates professional reports including:
- Executive Summary (PDF - 1 page)
- Complete Interactive Report (HTML)
- Performance, Risk, Trades, and Robustness tabs
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, TypedDict, Union

import numpy as np

from app.backtesting.acceptance_criteria import AcceptanceReport
from app.backtesting.capital_scale_analyzer import CapitalScaleAnalysisReport
from app.backtesting.models import BacktestResult
from app.backtesting.walk_forward_validator import ValidationWindow

logger = logging.getLogger(__name__)


# ============================================================================
# TYPED DICT DEFINITIONS
# ============================================================================


class ChartDataDict(TypedDict, total=False):
    """TypedDict for chart data."""

    dates: List[str]
    strategy: List[float]
    benchmark: List[float]


class ChartDict(TypedDict, total=False):
    """TypedDict for chart information."""

    type: str
    title: str
    data: ChartDataDict


class ReportSectionCharts(TypedDict):
    """TypedDict for report section charts."""

    type: str
    title: str
    data: ChartDataDict


@dataclass
class ReportSection:
    """A section of the report."""

    title: str
    content: str
    charts: List[ChartDict] = field(default_factory=list)


@dataclass
class ProfessionalReport:
    """Complete professional backtesting report."""

    strategy_name: str
    timestamp: datetime
    period_start: datetime
    period_end: datetime

    # Core results
    backtest_result: Optional[BacktestResult] = None
    walk_forward_results: Optional[List[ValidationWindow]] = None
    capital_scale_results: Optional[CapitalScaleAnalysisReport] = None
    acceptance_report: Optional[AcceptanceReport] = None

    # Report sections
    executive_summary: Optional[ReportSection] = None
    performance_section: Optional[ReportSection] = None
    risk_section: Optional[ReportSection] = None
    trades_section: Optional[ReportSection] = None
    robustness_section: Optional[ReportSection] = None

    # Warnings and notes
    survivorship_bias_warning: bool = False
    look_ahead_bias_warning: bool = False


class ProfessionalReporter:
    """
    Professional Report Generator (Req #16).

    Generates institutional-quality reports:
    - Executive Summary PDF (1 page)
    - Complete Interactive HTML
    """

    def __init__(
        self,
        include_pdf: bool = True,
        include_html: bool = True,
        pdf_template_path: Optional[str] = None,
    ):
        """
        Initialize reporter.

        Args:
            include_pdf: Whether to generate PDF report
            include_html: Whether to generate HTML report
            pdf_template_path: Optional path to PDF template
        """
        self.include_pdf = include_pdf
        self.include_html = include_html
        self.pdf_template_path = pdf_template_path

    def generate_executive_summary(
        self,
        backtest_result: BacktestResult,
        acceptance_report: AcceptanceReport,
        benchmark_return: float,
    ) -> ReportSection:
        """
        Generate executive summary (Req #16 - 1 page PDF).

        Includes:
        - KPIs clave (CAGR, Sharpe, MaxDD)
        - Gráfico de Equidad vs Benchmark
        - Veredicto Automático
        - Recomendación de Capital Óptimo

        Args:
            backtest_result: Complete backtest result
            acceptance_report: Acceptance criteria report
            benchmark_return: Benchmark return for comparison

        Returns:
            ReportSection with executive summary

        Raises:
            ValueError: If performance data is missing or invalid
        """
        perf = backtest_result.performance
        if not perf:
            logger.error(
                "Cannot generate executive summary: performance data is None",
                extra={"strategy": backtest_result.strategy_name},
            )
            raise ValueError("Performance data is required for executive summary generation")

        # Extract key metrics
        total_return = float(backtest_result.total_return)
        sharpe = float(perf.sharpe_ratio or 0)
        max_dd = float(perf.max_drawdown_percentage or 0)
        profit_factor = float(perf.profit_factor or 0)
        win_rate = float(perf.win_rate or 0)

        # Generate verdict
        verdict = acceptance_report.verdict.value
        score = acceptance_report.overall_score

        content = f"""
# Executive Summary

## Strategy Performance

| Metric | Value | Status |
|--------|-------|--------|
| **Total Return** | {total_return:+.2%} | {'✅' if total_return > 0 else '❌'} |
| **Sharpe Ratio** | {sharpe:.2f} | {'✅' if sharpe > 1.0 else '⚠️' if sharpe > 0.5 else '❌'} |
| **Max Drawdown** | {max_dd:.2%} | {'✅' if abs(max_dd) < 0.25 else '❌'} |
| **Profit Factor** | {profit_factor:.2f} | {'✅' if profit_factor > 1.3 else '❌'} |
| **Win Rate** | {win_rate:.1f}% | {'✅' if win_rate > 50 else '⚠️'} |

## Verdict

**Status: {verdict}**
**Score: {score:.0f}/100**

{self._get_verdict_description(verdict, score)}

## Benchmark Comparison

- Strategy Return: {total_return:+.2%}
- Benchmark Return: {benchmark_return:+.2%}
- Excess Return: {total_return - benchmark_return:+.2%}

## Recommendation

{self._generate_capital_recommendation(sharpe, max_dd, profit_factor)}
"""

        try:
            chart_data = self._prepare_equity_chart_data(backtest_result, benchmark_return)
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(
                "Failed to prepare equity chart data",
                extra={"strategy": backtest_result.strategy_name, "error": str(e)},
            )
            chart_data = ChartDataDict(dates=[], strategy=[], benchmark=[])

        return ReportSection(
            title="Executive Summary",
            content=content,
            charts=[
                ChartDict(
                    type="equity_curve",
                    title="Equity Curve vs Benchmark",
                    data=chart_data,
                )
            ],
        )

    def generate_complete_report(
        self,
        backtest_result: BacktestResult,
        acceptance_report: AcceptanceReport,
        walk_forward_results: Optional[List[ValidationWindow]] = None,
        capital_scale_results: Optional[CapitalScaleAnalysisReport] = None,
        benchmark_return: float = 0.0,
    ) -> ProfessionalReport:
        """
        Generate complete professional report (Req #16).

        Args:
            backtest_result: Complete backtest result
            acceptance_report: Acceptance criteria report
            walk_forward_results: Optional walk-forward validation results
            capital_scale_results: Optional capital scale analysis
            benchmark_return: Benchmark return

        Returns:
            Complete ProfessionalReport
        """
        report = ProfessionalReport(
            strategy_name=backtest_result.strategy_name or "unknown",
            timestamp=datetime.now(),
            period_start=backtest_result.start_date,
            period_end=backtest_result.end_date,
            backtest_result=backtest_result,
            walk_forward_results=walk_forward_results,
            capital_scale_results=capital_scale_results,
            acceptance_report=acceptance_report,
        )

        # Generate sections
        report.executive_summary = self.generate_executive_summary(
            backtest_result, acceptance_report, benchmark_return
        )
        report.performance_section = self._generate_performance_section(backtest_result)
        report.risk_section = self._generate_risk_section(backtest_result)
        report.trades_section = self._generate_trades_section(backtest_result)
        report.robustness_section = self._generate_robustness_section(
            walk_forward_results, capital_scale_results
        )

        return report

    def _generate_performance_section(self, result: BacktestResult) -> ReportSection:
        """Generate performance metrics section."""
        perf = result.performance
        if not perf:
            return ReportSection(title="Performance", content="No data available")

        content = f"""
## Performance Metrics

### Basic Metrics
- **Total Trades:** {perf.total_trades}
- **Winning Trades:** {perf.winning_trades} ({perf.win_rate:.1f}%)
- **Losing Trades:** {perf.losing_trades}
- **Win Rate:** {perf.win_rate:.1f}%

### Return Metrics
- **Total Return:** {float(result.total_return):.2%}
- **Gross Profit:** {float(perf.gross_profit):.2f}
- **Gross Loss:** {float(perf.gross_loss):.2f}
- **Net Profit:** {float(perf.net_profit):.2f}

### Risk-Adjusted Returns
- **Sharpe Ratio:** {float(perf.sharpe_ratio or 0):.2f}
- **Sortino Ratio:** {float(perf.sortino_ratio or 0):.2f}
- **Calmar Ratio:** {float(perf.calmar_ratio or 0):.2f}
- **Omega Ratio:** {float(perf.omega_ratio or 0):.2f}
"""
        return ReportSection(title="Performance", content=content)

    def _generate_risk_section(self, result: BacktestResult) -> ReportSection:
        """Generate risk analysis section."""
        perf = result.performance
        if not perf:
            return ReportSection(title="Risk Analysis", content="No data available")

        content = f"""
## Risk Analysis

### Drawdown Metrics
- **Max Drawdown:** {float(perf.max_drawdown_percentage or 0):.2%}
- **Avg Drawdown:** {float(perf.max_drawdown_percentage or 0):.2%}
- **Ulcer Index:** {float(perf.ulcer_index or 0):.2f}

### Tail Risk
- **VaR (95%):** {float(perf.var_95 or 0):.2%}
- **CVaR (95%):** {float(perf.cvar_95 or 0):.2%}

### Volatility
- **Annualized Volatility:** {float(perf.volatility_annualized or 0):.2%}
"""
        return ReportSection(title="Risk Analysis", content=content)

    def _generate_trades_section(self, result: BacktestResult) -> ReportSection:
        """Generate trades analysis section."""
        perf = result.performance
        if not perf:
            return ReportSection(title="Trades Analysis", content="No data available")

        content = f"""
## Trades Analysis

### Trade Statistics
- **Total Trades:** {perf.total_trades}
- **Avg Win:** {float(perf.avg_win):.2f}
- **Avg Loss:** {float(perf.avg_loss):.2f}
- **Largest Win:** {float(perf.largest_win):.2f}
- **Largest Loss:** {float(perf.largest_loss):.2f}

### Trade Duration
- **Avg Trade Duration:** {float(perf.avg_trade_duration):.1f} days
- **Total Trading Days:** {perf.total_days}
"""
        return ReportSection(title="Trades Analysis", content=content)

    def _generate_robustness_section(
        self,
        walk_forward: Optional[Union[List[ValidationWindow], Dict]],
        capital_scale: Optional[CapitalScaleAnalysisReport],
    ) -> ReportSection:
        """Generate robustness analysis section."""
        content = "## Robustness Analysis\n\n"

        if walk_forward:
            content += "### Walk-Forward Analysis\n"
            # Handle both dict (from WalkForwardValidator.validate_strategy()) and list formats
            if isinstance(walk_forward, dict):
                windows = walk_forward.get("windows", [])
            else:
                windows = walk_forward
            content += f"- **Windows Tested:** {len(windows)}\n"

            if windows:
                # Handle both dict and object window representations
                sharpes = []
                dds = []
                for w in windows:
                    if isinstance(w, dict):
                        if w.get("sharpe_ratio") is not None:
                            sharpes.append(float(w.get("sharpe_ratio", 0)))
                        if w.get("max_drawdown") is not None:
                            dds.append(float(w.get("max_drawdown", 0)))
                    else:
                        # Object with attributes
                        if hasattr(w, "sharpe_ratio") and w.sharpe_ratio is not None:
                            sharpes.append(float(w.sharpe_ratio))
                        if hasattr(w, "max_drawdown") and w.max_drawdown is not None:
                            dds.append(float(w.max_drawdown))

                if sharpes:
                    avg_sharpe = np.mean(sharpes)
                    content += f"- **Avg Sharpe (OOS):** {avg_sharpe:.2f}\n"
                if dds:
                    avg_dd = np.mean(dds)
                    content += f"- **Avg Max DD:** {avg_dd:.2%}\n"

        if capital_scale:
            content += "\n### Capital Scale Analysis\n"
            content += (
                f"- **Scalability Score:** {float(capital_scale.scalability_score):.0f}/100\n"
            )
            content += f"- **Alpha Degradation:** {float(capital_scale.alpha_degradation):.1%}\n"
            content += (
                f"- **Recommended Capital:** €{float(capital_scale.recommended_capital):,.0f}\n"
            )

        return ReportSection(title="Robustness Analysis", content=content)

    def _get_verdict_description(self, verdict: str, score: float) -> str:
        """Get description for verdict."""
        if verdict == "APPROVED":
            return "✅ Strategy meets all institutional acceptance criteria."
        elif verdict == "REVISION":
            return "⚠️ Strategy partially meets criteria. Review recommended before deployment."
        else:
            return "❌ Strategy fails acceptance criteria. Not recommended for deployment."

    def _generate_capital_recommendation(
        self, sharpe: float, max_dd: float, profit_factor: float
    ) -> str:
        """Generate capital recommendation based on metrics."""
        if sharpe > 1.5 and abs(max_dd) < 0.15 and profit_factor > 1.5:
            return "Strategy shows excellent risk-adjusted returns. **Recommended for full capital allocation.**"
        elif sharpe > 1.0 and abs(max_dd) < 0.25:
            return (
                "Strategy shows good performance. **Recommended for moderate capital allocation.**"
            )
        elif sharpe > 0.5:
            return "Strategy shows marginal performance. **Start with minimal capital and monitor closely.**"
        else:
            return "Strategy performance is insufficient. **Not recommended for live trading.**"

    def _prepare_equity_chart_data(
        self, result: BacktestResult, benchmark_return: float
    ) -> ChartDataDict:
        """Prepare equity curve chart data."""
        if not result.equity_curve:
            return ChartDataDict(dates=[], strategy=[], benchmark=[])

        dates = [d.isoformat() for d, _ in result.equity_curve]
        strategy_values = [float(v) for _, v in result.equity_curve]

        # Generate synthetic benchmark curve
        initial = strategy_values[0] if strategy_values else 100000
        benchmark_values = [
            initial * (1 + benchmark_return) ** (i / len(strategy_values))
            for i in range(len(strategy_values))
        ]

        return ChartDataDict(
            dates=dates,
            strategy=strategy_values,
            benchmark=benchmark_values,
        )

    def export_to_html(self, report: ProfessionalReport) -> str:
        """Export report to HTML (Req #16)."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{report.strategy_name} - Backtesting Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #f9f9f9; border-radius: 5px; }}
        .verdict-APPROVED {{ color: green; font-weight: bold; }}
        .verdict-REVISION {{ color: orange; font-weight: bold; }}
        .verdict-REJECTED {{ color: red; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{report.strategy_name}</h1>
        <p>Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M')}</p>
        <p>Period: {report.period_start.strftime('%Y-%m-%d')} to {report.period_end.strftime('%Y-%m-%d')}</p>
    </div>

    {self._section_to_html(report.executive_summary)}
    {self._section_to_html(report.performance_section)}
    {self._section_to_html(report.risk_section)}
    {self._section_to_html(report.trades_section)}
    {self._section_to_html(report.robustness_section)}
</body>
</html>
"""
        return html

    def _convert_markdown_tables_to_html(self, content: str) -> str:
        """Convert markdown tables to HTML tables."""
        lines = content.split("\n")
        result = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Detect markdown table: line starts with | and has at least one |
            if line.strip().startswith("|") and "|" in line.strip():
                # Collect all consecutive table rows
                table_rows = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    # Skip separator lines (|---|---|---|)
                    if not set(lines[i].replace(" ", "")) <= {"|", "-"}:
                        table_rows.append(lines[i].strip())
                    i += 1

                # Convert to HTML table if we have at least 2 rows (header + data)
                if len(table_rows) >= 2:
                    html_table = ["<table>"]

                    # Header row
                    header_cells = [cell.strip() for cell in table_rows[0].split("|")[1:-1]]
                    html_table.append("  <tr>")
                    for cell in header_cells:
                        html_table.append(f"    <th>{cell}</th>")
                    html_table.append("  </tr>")

                    # Data rows
                    for row in table_rows[1:]:
                        cells = [cell.strip() for cell in row.split("|")[1:-1]]
                        html_table.append("  <tr>")
                        for cell in cells:
                            html_table.append(f"    <td>{cell}</td>")
                        html_table.append("  </tr>")

                    html_table.append("</table>")
                    result.append("\n".join(html_table))
                else:
                    # Not enough rows for a table, keep as is
                    for row in table_rows:
                        result.append(row)
            else:
                result.append(line)
                i += 1

        return "\n".join(result)

    def _section_to_html(self, section: Optional[ReportSection]) -> str:
        """Convert section to HTML."""
        if not section:
            return ""

        # Convert markdown tables to HTML tables first
        content = self._convert_markdown_tables_to_html(section.content)

        # Then handle remaining line breaks
        content = content.replace("\n", "<br>\n")

        return f"""
    <div class="section">
        <h2>{section.title}</h2>
        {content}
    </div>
"""
