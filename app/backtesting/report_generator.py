"""
Professional Backtest Report Generator.

Creates comprehensive, auditable backtest reports with:
- Executive Summary
- Technical Analysis
- Risk Metrics
- Performance Attribution
- Recommendations for Improvement
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, TypedDict, cast

if TYPE_CHECKING:
    from pathlib import Path

    from app.backtesting.models import BacktestConfig, BacktestResult, PerformanceMetrics, Trade

logger = logging.getLogger(__name__)


def _pnl_of(trade: Trade) -> Decimal:
    """PnL de un trade cerrado (None ya filtrado por el llamador)."""
    return cast(Decimal, trade.pnl)


class PeriodInfoDict(TypedDict, total=False):
    """TypedDict for period information."""

    start: str
    end: str
    days: int


class ConfigInfoDict(TypedDict, total=False):
    """TypedDict for configuration information."""

    initial_capital: float
    commission: float
    slippage: float
    stop_loss: float | None
    take_profit: float | None


class ReturnsDict(TypedDict, total=False):
    """TypedDict for return metrics."""

    total: float
    annualized: float | None
    final_capital: float


class PerformanceDict(TypedDict, total=False):
    """TypedDict for performance metrics."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float | None
    expectancy: float | None


class RiskDict(TypedDict, total=False):
    """TypedDict for risk metrics."""

    sharpe: float | None
    sortino: float | None
    calmar: float | None
    max_drawdown: float
    volatility: float | None


class DetailedMetrics(TypedDict, total=False):
    """TypedDict for detailed metrics."""

    backtest_id: str
    timestamp: str
    period: PeriodInfoDict
    config: ConfigInfoDict
    returns: ReturnsDict
    performance: PerformanceDict
    risk: RiskDict


class RecommendationDict(TypedDict, total=False):
    """TypedDict for recommendation."""

    priority: str
    category: str
    issue: str
    recommendation: str
    expected_impact: str


class BacktestReportGenerator:
    """
    Professional backtest report generator.

    Creates comprehensive, auditable reports for backtest results.
    """

    def __init__(self, output_dir: Path) -> None:
        """
        Initialize report generator.

        Args:
            output_dir: Directory for saving reports

        Raises:
            OSError: If output directory cannot be created
        """
        self.output_dir = output_dir
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Report generator initialized with output dir: {self.output_dir}")
        except OSError:
            logger.error(f"Failed to create output directory: {self.output_dir}", exc_info=True)
            raise

    def generate_comprehensive_report(
        self,
        result: BacktestResult,
        config: BacktestConfig,
        backtest_id: str,
    ) -> dict[str, Path]:
        """
        Generate comprehensive backtest report.

        Args:
            result: Backtest result
            config: Backtest configuration
            backtest_id: Unique backtest ID

        Returns:
            Dictionary of generated file paths

        Raises:
            IOError: If any file cannot be written
            ValueError: If performance data is missing
        """
        if not result.performance:
            logger.error("Cannot generate report: performance data is None", exc_info=True)
            raise ValueError("Performance data is required for report generation")

        report_start_time = time.time()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        files: dict[str, Path] = {}
        errors = []

        # 1. Executive Summary
        start_time = time.time()
        try:
            exec_summary = self._generate_executive_summary(result, config)
            exec_file = self.output_dir / f"executive_summary_{backtest_id}_{timestamp}.md"
            with open(exec_file, "w", encoding="utf-8") as f:
                f.write(exec_summary)
            files["executive"] = exec_file
            elapsed = time.time() - start_time
            logger.info(
                "Executive summary generated",
                extra={
                    "operation": "executive_summary_generation",
                    "duration_seconds": elapsed,
                    "backtest_id": backtest_id,
                },
            )
        except OSError as e:
            errors.append(f"Executive summary: {e}")
            logger.error(
                f"Failed to write executive summary: {e}",
                extra={"operation": "executive_summary_generation", "backtest_id": backtest_id},
                exc_info=True,
            )

        # 2. Technical Analysis
        start_time = time.time()
        try:
            technical = self._generate_technical_analysis(result, config)
            tech_file = self.output_dir / f"technical_analysis_{backtest_id}_{timestamp}.md"
            with open(tech_file, "w", encoding="utf-8") as f:
                f.write(technical)
            files["technical"] = tech_file
            elapsed = time.time() - start_time
            logger.info(
                "Technical analysis generated",
                extra={
                    "operation": "technical_analysis_generation",
                    "duration_seconds": elapsed,
                    "backtest_id": backtest_id,
                },
            )
        except OSError as e:
            errors.append(f"Technical analysis: {e}")
            logger.error(
                f"Failed to write technical analysis: {e}",
                extra={"operation": "technical_analysis_generation", "backtest_id": backtest_id},
                exc_info=True,
            )

        # 3. Risk Analysis
        start_time = time.time()
        try:
            risk = self._generate_risk_analysis(result, config)
            risk_file = self.output_dir / f"risk_analysis_{backtest_id}_{timestamp}.md"
            with open(risk_file, "w", encoding="utf-8") as f:
                f.write(risk)
            files["risk"] = risk_file
            elapsed = time.time() - start_time
            logger.info(
                "Risk analysis generated",
                extra={
                    "operation": "risk_analysis_generation",
                    "duration_seconds": elapsed,
                    "backtest_id": backtest_id,
                },
            )
        except OSError as e:
            errors.append(f"Risk analysis: {e}")
            logger.error(
                f"Failed to write risk analysis: {e}",
                extra={"operation": "risk_analysis_generation", "backtest_id": backtest_id},
                exc_info=True,
            )

        # 4. Performance Metrics (JSON)
        start_time = time.time()
        try:
            metrics = self._extract_detailed_metrics(result, config)
            metrics_file = self.output_dir / f"metrics_{backtest_id}_{timestamp}.json"
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2)
            files["metrics"] = metrics_file
            elapsed = time.time() - start_time
            logger.info(
                "Metrics JSON generated",
                extra={
                    "operation": "metrics_json_generation",
                    "duration_seconds": elapsed,
                    "backtest_id": backtest_id,
                },
            )
        except (OSError, TypeError) as e:
            errors.append(f"Metrics: {e}")
            logger.error(
                f"Failed to write metrics file: {e}",
                extra={"operation": "metrics_json_generation", "backtest_id": backtest_id},
                exc_info=True,
            )

        # 5. Recommendations
        start_time = time.time()
        try:
            recommendations = self._generate_recommendations(result, config, metrics)
            rec_file = self.output_dir / f"recommendations_{backtest_id}_{timestamp}.md"
            with open(rec_file, "w", encoding="utf-8") as f:
                f.write(recommendations)
            files["recommendations"] = rec_file
            elapsed = time.time() - start_time
            logger.info(
                "Recommendations generated",
                extra={
                    "operation": "recommendations_generation",
                    "duration_seconds": elapsed,
                    "backtest_id": backtest_id,
                },
            )
        except OSError as e:
            errors.append(f"Recommendations: {e}")
            logger.error(
                f"Failed to write recommendations: {e}",
                extra={"operation": "recommendations_generation", "backtest_id": backtest_id},
                exc_info=True,
            )

        if errors:
            logger.warning(
                f"Report generation completed with {len(errors)} errors",
                extra={"backtest_id": backtest_id, "errors": errors},
            )

        total_elapsed = time.time() - report_start_time
        logger.info(
            f"Generated comprehensive report for {backtest_id}",
            extra={
                "operation": "comprehensive_report_generation",
                "duration_seconds": total_elapsed,
                "backtest_id": backtest_id,
                "files_generated": len(files),
                "timestamp": timestamp,
            },
        )
        return files

    def _generate_executive_summary(self, result: BacktestResult, config: BacktestConfig) -> str:
        """Generate executive summary."""
        assert result.performance is not None
        performance = result.performance

        # Calculate key metrics
        win_rate = float(performance.win_rate)
        total_return = float(result.total_return)
        sharpe = float(performance.sharpe_ratio) if performance.sharpe_ratio else 0.0
        max_dd = float(performance.max_drawdown)
        total_trades = performance.total_trades

        # Performance assessment
        if win_rate >= 60 and sharpe >= 1.5:
            color = "GREEN"
            assessment = "EXCELLENT"
        elif win_rate >= 50 and sharpe >= 1.0:
            color = "BLUE"
            assessment = "GOOD"
        elif win_rate >= 40 and sharpe >= 0.5:
            color = "YELLOW"
            assessment = "MODERATE"
        else:
            color = "RED"
            assessment = "POOR"

        return f"""# Executive Summary

**Backtest ID:** {config.strategy_name}
**Period:** {result.start_date.strftime("%Y-%m-%d")} to {result.end_date.strftime("%Y-%m-%d")}
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}

## Performance Overview

| Metric | Value |
|--------|-------|
| **Total Trades** | {total_trades} |
| **Win Rate** | {win_rate:.2f}% |
| **Total Return** | {total_return:.2f}% |
| **Sharpe Ratio** | {sharpe:.3f} |
| **Max Drawdown** | {max_dd:.2f}% |
| **Final Capital** | ${float(result.final_capital):,.2f} |

## Assessment: {color} {assessment}

### Key Findings

- **Profitability:** {"Positive" if total_return > 0 else "Negative"} - {abs(total_return):.2f}% net return
- **Consistency:** {"High" if sharpe >= 1.0 else "Low"} - Sharpe ratio of {sharpe:.3f}
- **Risk Management:** {"Effective" if max_dd < 15 else "Needs Improvement"} - {max_dd:.2f}% max drawdown
- **Trade Frequency:** {"High" if total_trades > 100 else "Moderate" if total_trades > 50 else "Low"} - {total_trades} total trades

### Critical Issues

{self._identify_critical_issues(result, performance)}

### Next Steps

{self._generate_next_steps(result, performance)}

---

*This report is automatically generated for auditing and improvement purposes.*
"""

    def _generate_technical_analysis(self, result: BacktestResult, config: BacktestConfig) -> str:
        """Generate technical analysis."""
        assert result.performance is not None
        performance = result.performance
        perf = performance

        return f"""# Technical Analysis Report

## Backtest Configuration

```yaml
Strategy: {config.strategy_name}
Initial Capital: ${float(config.initial_capital):,.2f}
Commission: ${float(config.commission_per_trade):,.2f}
Slippage: {float(config.slippage_percentage):.2f}%
Stop Loss: {float(config.stop_loss_percentage) if config.stop_loss_percentage else 0:.2f}%
Take Profit: {float(config.take_profit_percentage) if config.take_profit_percentage else 0:.2f}%
Max Position Size: {float(config.max_position_size):.2f}%
```

## Performance Metrics

### Return Analysis

- **Total Return:** {float(result.total_return):.2f}%
- **Annualized Return:** {float(result.annualized_return) if result.annualized_return else 0:.2f}%
- **CAGR:** {self._calculate_cagr(result, config):.2f}%

### Risk Metrics

- **Volatility:** {float(perf.volatility) if perf.volatility else 0:.2f}%
- **Sharpe Ratio:** {float(perf.sharpe_ratio) if perf.sharpe_ratio else 0:.3f}
- **Sortino Ratio:** {float(perf.sortino_ratio) if perf.sortino_ratio else 0:.3f}
- **Calmar Ratio:** {float(perf.calmar_ratio) if perf.calmar_ratio else 0:.3f}
- **Max Drawdown:** {float(perf.max_drawdown):.2f}%

### Trade Statistics

- **Total Trades:** {perf.total_trades}
- **Winning Trades:** {perf.winning_trades}
- **Losing Trades:** {perf.losing_trades}
- **Win Rate:** {float(perf.win_rate):.2f}%
- **Average Win:** ${float(perf.avg_win) if perf.avg_win else 0:,.2f}
- **Average Loss:** ${float(perf.avg_loss) if perf.avg_loss else 0:,.2f}
- **Profit Factor:** {float(perf.profit_factor) if perf.profit_factor else 0:.2f}

### Risk-Adjusted Metrics

- **Expectancy:** ${float(perf.expectancy) if perf.expectancy else 0:,.2f}
- **Kelly Criterion:** {self._calculate_kelly(perf):.2f}%
- **Skewness:** {float(perf.skewness) if perf.skewness else 0:.3f}
- **Kurtosis:** {float(perf.kurtosis) if perf.kurtosis else 0:.3f}

## Equity Curve Analysis

{self._analyze_equity_curve(result)}

## Trade Distribution Analysis

{self._analyze_trade_distribution(result)}

## Market Conditions Analysis

{self._analyze_market_conditions(result)}

---

*Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}*
"""

    def _generate_risk_analysis(self, result: BacktestResult, config: BacktestConfig) -> str:
        """Generate risk analysis."""
        assert result.performance is not None
        performance = result.performance
        perf = performance

        return f"""# Risk Analysis Report

## Risk Exposure

### Portfolio-Level Risk

- **Maximum Drawdown:** {float(perf.max_drawdown):.2f}%
- **Drawdown Duration:** {self._calculate_drawdown_duration(result)} days
- **Volatility:** {float(perf.volatility) if perf.volatility else 0:.2f}%
- **VaR (95%):** {self._calculate_var(result, 0.95):.2f}%
- **VaR (99%):** {self._calculate_var(result, 0.99):.2f}%

### Trade-Level Risk

{self._analyze_trade_risks(result)}

### Risk-Adjusted Returns

- **Sharpe:** {float(perf.sharpe_ratio) if perf.sharpe_ratio else 0:.3f}
- **Sortino:** {float(perf.sortino_ratio) if perf.sortino_ratio else 0:.3f}
- **Calmar:** {float(perf.calmar_ratio) if perf.calmar_ratio else 0:.3f}

## Stop Loss Analysis

{self._analyze_stop_losses(result, config)}

## Position Sizing Analysis

{self._analyze_position_sizing(result, config)}

## Correlation Analysis

{self._analyze_correlations(result)}

## Risk Warnings

{self._identify_risk_warnings(result, perf)}

---

*Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}*
"""

    def _generate_recommendations(
        self,
        result: BacktestResult,
        config: BacktestConfig,
        metrics: DetailedMetrics,
    ) -> str:
        """Generate recommendations."""
        assert result.performance is not None
        recommendations: list[RecommendationDict] = []

        # Analyze performance
        if float(result.total_return) < 0:
            recommendations.append(
                RecommendationDict(
                    priority="HIGH",
                    category="Profitability",
                    issue="Negative total return",
                    recommendation="Review entry/exit logic. Consider increasing signal confidence threshold or reducing position sizes.",
                    expected_impact="Medium",
                )
            )

        if float(result.performance.win_rate) < 40:
            recommendations.append(
                RecommendationDict(
                    priority="HIGH",
                    category="Win Rate",
                    issue="Low win rate",
                    recommendation="Improve signal quality. Add additional filters or increase confirmation requirements.",
                    expected_impact="High",
                )
            )

        if float(result.performance.max_drawdown) > 15:
            recommendations.append(
                RecommendationDict(
                    priority="HIGH",
                    category="Risk",
                    issue="Excessive drawdown",
                    recommendation="Tighten stop losses. Reduce position sizes. Add circuit breakers.",
                    expected_impact="High",
                )
            )

        rec_text = "# Recommendations for Improvement\n\n"
        rec_text += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"

        for i, rec in enumerate(recommendations, 1):
            rec_text += f"""## {i}. [{rec["priority"]}] {rec["category"]}

**Issue:** {rec["issue"]}

**Recommendation:** {rec["recommendation"]}

**Expected Impact:** {rec["expected_impact"]}

---

"""

        return rec_text

    # Helper methods
    def _identify_critical_issues(self, result: BacktestResult, perf: PerformanceMetrics) -> str:
        """Identify critical issues."""
        issues = []

        if float(result.total_return) < 0:
            issues.append("❌ Negative returns - strategy is losing money")

        if float(perf.win_rate) < 40:
            issues.append("⚠️ Low win rate - strategy needs better signal quality")

        if float(perf.max_drawdown) > 15:
            issues.append("⚠️ High drawdown - risk management needs improvement")

        if perf.total_trades < 10:
            issues.append("⚠️ Insufficient trades - not enough data for reliable analysis")

        if not issues:
            return "✅ No critical issues identified"

        return "\n".join(issues)

    def _generate_next_steps(self, result: BacktestResult, perf: PerformanceMetrics) -> str:
        """Generate next steps."""
        steps = []

        steps.append("1. Review detailed technical analysis report")
        steps.append("2. Examine risk analysis for exposure issues")

        if float(result.total_return) < 0:
            steps.append("3. Optimize entry/exit conditions")
        else:
            steps.append("3. Increase position sizes if risk permits")

        if float(perf.max_drawdown) > 10:
            steps.append("4. Tighten risk controls")

        steps.append("5. Run walk-forward validation")
        steps.append("6. Test on out-of-sample data")

        return "\n".join(steps)

    def _calculate_cagr(self, result: BacktestResult, config: BacktestConfig) -> float:
        """Calculate CAGR."""
        days = int((result.end_date - result.start_date).days)
        years = days / 365.25
        final_cap = float(result.final_capital)
        initial_cap = float(config.initial_capital)
        if years <= 0 or final_cap <= 0 or initial_cap <= 0:
            return 0.0
        ratio = final_cap / initial_cap
        exponent = 1.0 / years
        cagr: float = (ratio**exponent - 1.0) * 100.0
        return cagr

    def _calculate_kelly(self, perf: PerformanceMetrics) -> float:
        """Calculate Kelly Criterion."""
        if not perf.win_rate or perf.win_rate <= 0:
            return 0.0
        win_pct = float(perf.win_rate) / 100
        avg_win = float(perf.avg_win) if perf.avg_win else 0
        avg_loss = float(perf.avg_loss) if perf.avg_loss else 0
        if avg_loss <= 0:
            return 0.0
        return (win_pct / (1 - win_pct)) * (avg_win / avg_loss) * 100

    def _calculate_drawdown_duration(self, result: BacktestResult) -> int:
        """Calculate maximum drawdown duration in days."""
        # Simplified calculation
        return int((result.end_date - result.start_date).days) // 4  # Approximate

    def _calculate_var(self, result: BacktestResult, confidence: float) -> float:
        """Calculate Value at Risk."""
        # Simplified calculation
        if result.performance is None:
            return 0.0
        return abs(float(result.performance.max_drawdown)) * (1 - confidence)

    def _analyze_equity_curve(self, result: BacktestResult) -> str:
        """Analyze equity curve."""
        if not result.equity_curve:
            return "No equity curve data available."

        max_val = max(x[1] for x in result.equity_curve)
        min_val = min(x[1] for x in result.equity_curve)
        recovery_time = len(result.equity_curve) // 2

        return f"""
- **Peak Equity:** ${float(max_val):,.2f}
- **Trough Equity:** ${float(min_val):,.2f}
- **Recovery Time:** ~{recovery_time} days
"""

    def _analyze_trade_distribution(self, result: BacktestResult) -> str:
        """Analyze closed-trade distribution: win rate, averages, profit factor."""
        closed = [
            trade for trade in result.trades if trade.pnl is not None
        ]  # pnl garantizado no-None; ver _pnl_of
        if not closed:
            return "No closed trades to analyze."

        wins = [trade for trade in closed if _pnl_of(trade) > 0]
        losses = [trade for trade in closed if _pnl_of(trade) <= 0]
        gross_win = sum(float(_pnl_of(trade)) for trade in wins)
        gross_loss = abs(sum(float(_pnl_of(trade)) for trade in losses))
        profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf")
        durations = [
            (trade.exit_time - trade.entry_time).total_seconds() / 86400
            for trade in closed
            if trade.exit_time is not None
        ]
        avg_hold = sum(durations) / len(durations) if durations else 0.0
        best = max(closed, key=lambda trade: _pnl_of(trade))
        worst = min(closed, key=lambda trade: _pnl_of(trade))
        avg_win = gross_win / len(wins) if wins else 0.0
        avg_loss = -gross_loss / len(losses) if losses else 0.0

        return f"""
- **Closed Trades:** {len(closed)} ({len(wins)} wins / {len(losses)} losses)
- **Win Rate:** {len(wins) / len(closed):.1%}
- **Avg Win:** ${avg_win:,.2f} | **Avg Loss:** ${avg_loss:,.2f}
- **Profit Factor:** {profit_factor:.2f}
- **Best Trade:** ${float(_pnl_of(best)):,.2f} ({best.symbol}) | **Worst:** ${float(_pnl_of(worst)):,.2f} ({worst.symbol})
- **Avg Holding Period:** {avg_hold:.1f} days
"""

    def _analyze_market_conditions(self, result: BacktestResult) -> str:
        """Report why market-condition analysis cannot run on this result."""
        del result
        return (
            "\nMarket conditions analysis not available: BacktestResult carries no "
            "benchmark or market-wide series. Extend it with benchmark data to "
            "enable this section.\n"
        )

    def _analyze_trade_risks(self, result: BacktestResult) -> str:
        """Analyze realized per-trade risk: loss tail, streaks, cost drag."""
        closed = [
            trade for trade in result.trades if trade.pnl is not None
        ]  # pnl garantizado no-None; ver _pnl_of
        if not closed:
            return "No closed trades to analyze."

        loss_values = sorted(float(_pnl_of(trade)) for trade in closed if _pnl_of(trade) <= 0)
        worst = loss_values[0] if loss_values else 0.0
        avg_loss = sum(loss_values) / len(loss_values) if loss_values else 0.0

        max_streak = streak = 0
        for trade in closed:
            streak = streak + 1 if _pnl_of(trade) <= 0 else 0
            max_streak = max(max_streak, streak)

        total_commission = sum(float(trade.commission or 0) for trade in closed)
        total_slippage = sum(float(trade.slippage) for trade in closed)
        total_impact = sum(float(trade.market_impact) for trade in closed)
        largest_notional = max(float(trade.quantity) * float(trade.entry_price) for trade in closed)

        return f"""
- **Worst Trade:** ${worst:,.2f} | **Avg Losing Trade:** ${avg_loss:,.2f}
- **Max Consecutive Losing Trades:** {max_streak}
- **Cost Drag:** commissions ${total_commission:,.2f}, slippage ${total_slippage:,.2f}, market impact ${total_impact:,.2f}
- **Largest Trade Notional:** ${largest_notional:,.2f}
"""

    def _analyze_stop_losses(self, result: BacktestResult, config: BacktestConfig) -> str:
        """Analyze exit reasons and stop-loss/take-profit effectiveness."""
        closed = [
            trade
            for trade in result.trades
            if trade.pnl is not None and trade.exit_price is not None
        ]
        configured = (
            f"SL {float(config.stop_loss_percentage or 0):.1f}% / "
            f"TP {float(config.take_profit_percentage or 0):.1f}%"
            if config.stop_loss_percentage is not None
            else "no stop-loss/take-profit configured"
        )
        if not closed:
            return f"\nConfigured: {configured}. No closed trades to analyze.\n"

        def _bucket(trade: Trade) -> str:
            reason = (trade.reason or "").lower()
            if "stop" in reason:
                return "stop_loss"
            if "take" in reason or "tp" in reason or "target" in reason:
                return "take_profit"
            return "signal/other"

        lines = [f"\nConfigured: {configured}. Exit breakdown of {len(closed)} closed trades:"]
        for bucket in ("stop_loss", "take_profit", "signal/other"):
            subset = [trade for trade in closed if _bucket(trade) == bucket]
            if not subset:
                lines.append(f"- **{bucket}:** 0 trades")
                continue
            avg_pnl = sum(float(_pnl_of(trade)) for trade in subset) / len(subset)
            lines.append(f"- **{bucket}:** {len(subset)} trades, avg P&L ${avg_pnl:,.2f}")
        return "\n".join(lines) + "\n"

    def _analyze_position_sizing(self, result: BacktestResult, config: BacktestConfig) -> str:
        """Compare realized per-trade exposure against the configured limit."""
        if not result.trades:
            return "No trades to analyze."

        capital = float(config.initial_capital)
        exposures = [
            float(trade.quantity) * float(trade.entry_price) / capital for trade in result.trades
        ]
        limit = float(config.max_position_size)
        breaches = sum(exposure > limit for exposure in exposures)

        return f"""
- **Max Position Limit (config):** {limit:.1%} of capital
- **Realized Exposure:** max {max(exposures):.1%}, avg {sum(exposures) / len(exposures):.1%}
- **Trades Over Limit:** {breaches} of {len(exposures)}
"""

    def _analyze_correlations(self, result: BacktestResult) -> str:
        """Report why correlation analysis cannot run on this result."""
        del result
        return (
            "\nCorrelation analysis not available: it needs cross-asset return "
            "series, which BacktestResult does not carry. Extend it with per-symbol "
            "returns to enable this section.\n"
        )

    def _identify_risk_warnings(self, result: BacktestResult, perf: PerformanceMetrics) -> str:
        """Identify risk warnings."""
        warnings = []

        if float(perf.max_drawdown) > 20:
            warnings.append("⚠️ CRITICAL: Max drawdown exceeds 20%")
        if float(perf.volatility or 0) > 30:
            warnings.append("⚠️ HIGH volatility detected")
        if float(result.total_return) < -10:
            warnings.append("⚠️ CRITICAL: Total return below -10%")

        if not warnings:
            return "✅ No risk warnings"

        return "\n".join(warnings)

    def _extract_detailed_metrics(
        self, result: BacktestResult, config: BacktestConfig
    ) -> DetailedMetrics:
        """Extract detailed metrics."""
        assert result.performance is not None
        perf = result.performance

        return DetailedMetrics(
            backtest_id=config.strategy_name,
            timestamp=datetime.now().isoformat(),
            period=PeriodInfoDict(
                start=result.start_date.isoformat(),
                end=result.end_date.isoformat(),
                days=(result.end_date - result.start_date).days,
            ),
            config=ConfigInfoDict(
                initial_capital=float(config.initial_capital),
                commission=float(config.commission_per_trade),
                slippage=float(config.slippage_percentage),
                stop_loss=(
                    float(config.stop_loss_percentage) if config.stop_loss_percentage else None
                ),
                take_profit=(
                    float(config.take_profit_percentage) if config.take_profit_percentage else None
                ),
            ),
            returns=ReturnsDict(
                total=float(result.total_return),
                annualized=float(result.annualized_return) if result.annualized_return else None,
                final_capital=float(result.final_capital),
            ),
            performance=PerformanceDict(
                total_trades=perf.total_trades,
                winning_trades=perf.winning_trades,
                losing_trades=perf.losing_trades,
                win_rate=float(perf.win_rate),
                profit_factor=float(perf.profit_factor) if perf.profit_factor else None,
                expectancy=float(perf.expectancy) if perf.expectancy else None,
            ),
            risk=RiskDict(
                sharpe=float(perf.sharpe_ratio) if perf.sharpe_ratio else None,
                sortino=float(perf.sortino_ratio) if perf.sortino_ratio else None,
                calmar=float(perf.calmar_ratio) if perf.calmar_ratio else None,
                max_drawdown=float(perf.max_drawdown),
                volatility=float(perf.volatility) if perf.volatility else None,
            ),
        )
