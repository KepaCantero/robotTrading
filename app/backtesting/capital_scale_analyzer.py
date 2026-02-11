"""
Capital Scale Analyzer for Professional Backtesting System (Req #1)

Analyzes strategy performance across multiple capital levels to detect:
- Scalability issues
- Liquidity constraints (2% ADV rule)
- Commission impact degradation
- Alpha degradation across capital levels

Capital Levels: €1K, €5K, €10K, €50K, €100K
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.backtesting.constants import BACKTESTING_CONSTANTS
from app.backtesting.cost_calculator import AssetType, CostCalculator
from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig, BacktestResult, PerformanceMetrics
from app.models.market_data import Quote

logger = logging.getLogger(__name__)

# Constants from configuration
CS_CONSTANTS = BACKTESTING_CONSTANTS.capital_scale
DEFAULT_CAPITAL_LEVELS = CS_CONSTANTS.DEFAULT_CAPITAL_LEVELS


@dataclass
class CapitalLevelResult:
    """Result for a single capital level."""

    capital_level: Decimal
    initial_capital: Decimal
    final_capital: Decimal
    total_return: Decimal
    total_return_pct: Decimal
    cagr: Decimal
    sharpe_ratio: Optional[Decimal]
    max_drawdown_pct: Decimal
    total_trades: int
    win_rate: Decimal
    total_commissions: Decimal
    gross_profit: Decimal
    gross_return: Decimal
    commission_impact_ratio: Decimal  # Commissions / Gross Return
    partial_fills: int  # Number of trades reduced by ADV rule
    rejected_orders: int  # Number of orders rejected (< 50% fill)
    performance_metrics: Optional[PerformanceMetrics] = None
    equity_curve: List[Tuple[datetime, Decimal]] = field(default_factory=list)


@dataclass
class CapitalScaleAnalysisReport:
    """Complete capital scale analysis report."""

    strategy_name: str
    timestamp: datetime
    start_date: datetime
    end_date: datetime
    capital_level_results: List[CapitalLevelResult]
    adv_rule_enabled: bool
    adv_limit_pct: Decimal

    # Comparative metrics
    alpha_degradation: Decimal  # CAGR difference between smallest and largest
    commission_impact_gradient: List[Decimal]  # Commission impact by level
    scalability_score: Decimal  # 0-100 score
    recommended_capital: Decimal  # Optimal capital level
    warnings: List[str] = field(default_factory=list)
    passed: bool = True


class CapitalScaleAnalyzer:
    """
    Multi-Scale Capital Analysis (Req #1 - CRITICAL).

    Simulates strategy simultaneously with different capital sizes to detect
    scalability and liquidity issues.
    """

    def __init__(
        self,
        capital_levels: Optional[List[Decimal]] = None,
        adv_limit_pct: Optional[Decimal] = None,  # Uses config default if None
        enable_adv_rule: bool = True,
        enable_adaptive_commission: bool = True,
    ):
        """
        Initialize capital scale analyzer.

        Args:
            capital_levels: List of capital levels to test (default: from config)
            adv_limit_pct: Maximum order size as % of ADV (default: from config)
            enable_adv_rule: Whether to enforce ADV liquidity constraints
            enable_adaptive_commission: Whether to use adaptive commission by capital level
        """
        self.capital_levels = capital_levels or DEFAULT_CAPITAL_LEVELS
        self.adv_limit_pct = (
            adv_limit_pct if adv_limit_pct is not None else CS_CONSTANTS.ADV_LIMIT_PCT_DEFAULT
        )
        self.enable_adv_rule = enable_adv_rule
        self.enable_adaptive_commission = enable_adaptive_commission
        self.cost_calculator = CostCalculator(use_dynamic_costs=True)

        # Commission models by capital level (from config)
        self._commission_models = CS_CONSTANTS.COMMISSION_MODELS

    def calculate_commission_for_level(
        self, capital_level: Decimal, trade_value: Decimal
    ) -> Decimal:
        """
        Calculate adaptive commission based on capital level.

        Args:
            capital_level: Capital level for this simulation
            trade_value: Value of the trade

        Returns:
            Commission amount
        """
        if not self.enable_adaptive_commission:
            return self.cost_calculator.calculate_commission(AssetType.EQUITY, trade_value)

        # Find closest capital level model
        closest_level = min(self._commission_models.keys(), key=lambda x: abs(x - capital_level))
        model = self._commission_models[closest_level]

        if model["type"] == "fixed":
            return model["cost"]
        elif model["type"] == "hybrid":
            pct_cost = trade_value * model["rate"]
            return max(model["min_cost"], pct_cost)
        elif model["type"] == "tiered":
            # Find applicable bracket
            for bracket in model["brackets"]:
                if trade_value <= bracket.get("volume_max", float("inf")):
                    pct_cost = trade_value * bracket["rate"]
                    return max(bracket["min"], pct_cost)

        return self.cost_calculator.calculate_commission(AssetType.EQUITY, trade_value)

    def apply_adv_limit(
        self,
        order_size: Decimal,
        adv: Decimal,
        symbol: str,
    ) -> Tuple[Decimal, bool, bool]:
        """
        Apply 2% ADV rule to order size.

        Args:
            order_size: Requested order size
            adv: Average Daily Volume (20-day)
            symbol: Trading symbol

        Returns:
            Tuple of (adjusted_size, was_partial_fill, was_rejected)
        """
        if not self.enable_adv_rule or adv <= 0:
            return order_size, False, False

        max_size = adv * self.adv_limit_pct

        if order_size <= max_size:
            return order_size, False, False

        # Order exceeds ADV limit
        adjusted_size = max_size
        fill_ratio = adjusted_size / order_size

        # If fill is below threshold, reject order (configurable)
        if fill_ratio < CS_CONSTANTS.ADV_FILL_RATIO_REJECT_THRESHOLD:
            return Decimal("0"), False, True

        return adjusted_size, True, False

    def simulate_single_capital_level(
        self,
        quotes: List[Quote],
        signals: List[Any],
        base_config: BacktestConfig,
        capital_level: Decimal,
        adv_data: Optional[Dict[str, Decimal]] = None,
    ) -> CapitalLevelResult:
        """
        Simulate strategy for a single capital level.

        Args:
            quotes: Historical market data
            signals: Trading signals
            base_config: Base backtest configuration
            capital_level: Capital level for this simulation
            adv_data: Dictionary of ADV by symbol (20-day average)

        Returns:
            CapitalLevelResult with metrics
        """
        # Create config for this capital level
        config = BacktestConfig(**base_config.model_dump())
        config.initial_capital = capital_level

        # Adjust commission for capital level
        original_commission = config.commission_per_trade
        config.commission_per_trade = self.calculate_commission_for_level(
            capital_level, capital_level
        )

        logger.info(f"Simulating capital level: €{capital_level:,.0f}")

        # Run backtest
        backtester = SimpleBacktester(config)
        result: BacktestResult = backtester.run_backtest(
            quotes,
            signals,
            datetime.now(),  # start_date
            datetime.now(),  # end_date
        )

        # Calculate commission impact
        perf = result.performance
        if perf:
            gross_return = perf.gross_profit + abs(perf.gross_loss)
            commission_impact = (
                (original_commission * perf.total_trades / gross_return)
                if gross_return > 0
                else Decimal("0")
            )
        else:
            commission_impact = Decimal("0")
            gross_return = Decimal("0")

        # Count partial fills and rejections from ADV rule
        partial_fills = 0
        rejected_orders = 0

        if adv_data and self.enable_adv_rule:
            for trade in result.trades:
                adv = adv_data.get(trade.symbol, Decimal("0"))
                if adv > 0:
                    order_value = trade.quantity * trade.entry_price
                    _, was_partial, was_rejected = self.apply_adv_limit(
                        order_value, adv, trade.symbol
                    )
                    if was_partial:
                        partial_fills += 1
                    if was_rejected:
                        rejected_orders += 1

        return CapitalLevelResult(
            capital_level=capital_level,
            initial_capital=capital_level,
            final_capital=result.final_capital,
            total_return=result.final_capital - capital_level,
            total_return_pct=result.total_return,
            cagr=result.annualized_return or result.total_return,
            sharpe_ratio=perf.sharpe_ratio if perf else None,
            max_drawdown_pct=perf.max_drawdown_percentage if perf else Decimal("0"),
            total_trades=perf.total_trades if perf else 0,
            win_rate=perf.win_rate if perf else Decimal("0"),
            total_commissions=original_commission * (perf.total_trades if perf else 0),
            gross_profit=perf.gross_profit if perf else Decimal("0"),
            gross_return=gross_return,
            commission_impact_ratio=commission_impact,
            partial_fills=partial_fills,
            rejected_orders=rejected_orders,
            performance_metrics=perf,
            equity_curve=result.equity_curve,
        )

    def analyze_capital_scaling(
        self,
        quotes: List[Quote],
        signals: List[Any],
        config: BacktestConfig,
        start_date: datetime,
        end_date: datetime,
        adv_data: Optional[Dict[str, Decimal]] = None,
    ) -> CapitalScaleAnalysisReport:
        """
        Run complete multi-scale capital analysis.

        Args:
            quotes: Historical market data
            signals: Trading signals
            config: Base backtest configuration
            start_date: Analysis start date
            end_date: Analysis end date
            adv_data: Optional ADV data for liquidity constraints

        Returns:
            Complete CapitalScaleAnalysisReport
        """
        logger.info(f"Starting capital scale analysis with {len(self.capital_levels)} levels")

        results: List[CapitalLevelResult] = []
        warnings: List[str] = []

        # Simulate each capital level
        for capital_level in sorted(self.capital_levels):
            try:
                level_result = self.simulate_single_capital_level(
                    quotes, signals, config, capital_level, adv_data
                )
                results.append(level_result)

                # Check for commission impact warning (using config threshold)
                if (
                    level_result.commission_impact_ratio
                    > CS_CONSTANTS.COMMISSION_IMPACT_WARNING_THRESHOLD
                ):
                    warnings.append(
                        f"€{capital_level:,.0f}: Commission impact {level_result.commission_impact_ratio:.1%} "
                        f"exceeds {CS_CONSTANTS.COMMISSION_IMPACT_WARNING_THRESHOLD:.1%} threshold - "
                        f"strategy may not be viable at this level"
                    )

            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.error(f"Error simulating capital level {capital_level}: {e}", exc_info=True)
                warnings.append(f"€{capital_level:,.0f}: Simulation failed - {str(e)}")

        if not results:
            return CapitalScaleAnalysisReport(
                strategy_name=config.strategy_name or "unknown",
                timestamp=datetime.now(),
                start_date=start_date,
                end_date=end_date,
                capital_level_results=[],
                adv_rule_enabled=self.enable_adv_rule,
                adv_limit_pct=self.adv_limit_pct,
                alpha_degradation=Decimal("0"),
                commission_impact_gradient=[],
                scalability_score=Decimal("0"),
                recommended_capital=self.capital_levels[0],
                warnings=["No valid capital level results"],
                passed=False,
            )

        # Calculate comparative metrics
        alpha_degradation = self._calculate_alpha_degradation(results)
        commission_impact_gradient = [r.commission_impact_ratio for r in results]
        scalability_score = self._calculate_scalability_score(results, alpha_degradation)
        recommended_capital = self._find_optimal_capital(results)

        # Check acceptance criteria (using config thresholds)
        passed = True
        if max(commission_impact_gradient) > CS_CONSTANTS.COMMISSION_IMPACT_CRITICAL_THRESHOLD:
            passed = False
            warnings.append(
                f"REJECTED: Commissions exceed {CS_CONSTANTS.COMMISSION_IMPACT_CRITICAL_THRESHOLD:.1%} "
                f"of gross profit at some capital levels"
            )

        if alpha_degradation > CS_CONSTANTS.ALPHA_DEGRADATION_THRESHOLD:
            passed = False
            warnings.append(
                f"REJECTED: Alpha degradation {alpha_degradation:.1%} exceeds "
                f"{CS_CONSTANTS.ALPHA_DEGRADATION_THRESHOLD:.1%} threshold"
            )

        logger.info(
            f"Capital scale analysis complete. Scalability score: {scalability_score:.0f}/100"
        )

        return CapitalScaleAnalysisReport(
            strategy_name=config.strategy_name or "unknown",
            timestamp=datetime.now(),
            start_date=start_date,
            end_date=end_date,
            capital_level_results=results,
            adv_rule_enabled=self.enable_adv_rule,
            adv_limit_pct=self.adv_limit_pct,
            alpha_degradation=alpha_degradation,
            commission_impact_gradient=commission_impact_gradient,
            scalability_score=scalability_score,
            recommended_capital=recommended_capital,
            warnings=warnings,
            passed=passed,
        )

    def _calculate_alpha_degradation(self, results: List[CapitalLevelResult]) -> Decimal:
        """
        Calculate alpha degradation between smallest and largest capital.

        Alpha Degradation = (CAGR_small - CAGR_large) / |CAGR_small|
        """
        if len(results) < 2:
            return Decimal("0")

        smallest = min(results, key=lambda r: r.capital_level)
        largest = max(results, key=lambda r: r.capital_level)

        if smallest.cagr == 0:
            return Decimal("0")

        degradation = (smallest.cagr - largest.cagr) / abs(smallest.cagr)
        return max(Decimal("0"), degradation)  # Non-negative

    def _calculate_scalability_score(
        self, results: List[CapitalLevelResult], alpha_degradation: Decimal
    ) -> Decimal:
        """
        Calculate overall scalability score (0-100).

        Factors:
        - Alpha degradation (lower is better)
        - Commission impact consistency
        - Win rate stability across levels
        """
        if len(results) < 2:
            return Decimal("100")

        # Alpha degradation score (using config weights)
        degradation_score = max(
            Decimal("0"),
            CS_CONSTANTS.SCALABILITY_ALPHA_DEGRADATION_MAX_POINTS
            - (
                alpha_degradation
                * CS_CONSTANTS.SCALABILITY_ALPHA_DEGRADATION_MAX_POINTS
                * Decimal("2")
            ),
        )

        # Commission impact score (using config thresholds)
        commission_scores = []
        for r in results:
            if r.commission_impact_ratio < CS_CONSTANTS.COMMISSION_IMPACT_EXCELLENT_THRESHOLD:
                commission_scores.append(CS_CONSTANTS.SCALABILITY_COMMISSION_MAX_POINTS)
            elif r.commission_impact_ratio < CS_CONSTANTS.COMMISSION_IMPACT_GOOD_THRESHOLD:
                commission_scores.append(
                    CS_CONSTANTS.SCALABILITY_COMMISSION_MAX_POINTS * Decimal("2") / Decimal("3")
                )
            else:
                commission_scores.append(Decimal("10"))
        commission_score = (
            np.mean(commission_scores) if commission_scores else Decimal("0")
        )

        # Win rate stability (using config penalty factor)
        win_rates = [float(r.win_rate) for r in results if r.total_trades > 0]
        if win_rates:
            win_rate_std = Decimal(str(np.std(win_rates)))
            stability_score = max(
                Decimal("0"),
                CS_CONSTANTS.SCALABILITY_STABILITY_MAX_POINTS
                - (win_rate_std * CS_CONSTANTS.WIN_RATE_STABILITY_PENALTY_FACTOR),
            )
        else:
            stability_score = Decimal("0")

        total_score = degradation_score + commission_score + stability_score
        return min(Decimal("100"), max(Decimal("0"), total_score))

    def _find_optimal_capital(self, results: List[CapitalLevelResult]) -> Decimal:
        """
        Find optimal capital level based on:
        - Highest risk-adjusted return (Sharpe)
        - Acceptable commission impact (from config)
        - Minimal partial fills/rejections
        """
        valid_results = [
            r
            for r in results
            if r.commission_impact_ratio < CS_CONSTANTS.COMMISSION_IMPACT_OPTIMAL_THRESHOLD
        ]

        if not valid_results:
            return results[0].capital_level if results else self.capital_levels[0]

        # Score each valid result
        scored = []
        for r in valid_results:
            sharpe = float(r.sharpe_ratio or 0)
            liquidity_penalty = r.partial_fills + r.rejected_orders

            score = sharpe * 10 - liquidity_penalty
            scored.append((r.capital_level, score))

        # Return capital with highest score
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    def generate_summary_table(self, report: CapitalScaleAnalysisReport) -> str:
        """Generate markdown summary table of results."""
        lines = [
            "# Capital Scale Analysis Report",
            "",
            f"**Strategy:** {report.strategy_name}",
            f"**Date:** {report.timestamp.strftime('%Y-%m-%d %H:%M')}",
            f"**Period:** {report.start_date.strftime('%Y-%m-%d')} to {report.end_date.strftime('%Y-%m-%d')}",
            "",
            "## Results Summary",
            "",
            "| Capital | Return | CAGR | Sharpe | Max DD | Win Rate | Commissions | Impact | Partial Fills |",
            "|---------|--------|------|--------|--------|----------|-------------|--------|---------------|",
        ]

        for r in report.capital_level_results:
            lines.append(
                f"| €{r.capital_level:,.0f} | {r.total_return_pct:+.2f}% | "
                f"{r.cagr:+.2f}% | {r.sharpe_ratio or 0:.2f} | "
                f"{r.max_drawdown_pct:.2f}% | {r.win_rate:.1f}% | "
                f"€{r.total_commissions:,.2f} | {r.commission_impact_ratio:.1%} | "
                f"{r.partial_fills} |"
            )

        lines.extend(
            [
                "",
                "## Analysis Metrics",
                "",
                f"- **Alpha Degradation:** {report.alpha_degradation:.1%}",
                f"- **Scalability Score:** {report.scalability_score:.0f}/100",
                f"- **Recommended Capital:** €{report.recommended_capital:,.0f}",
                f"- **Status:** {'✅ PASSED' if report.passed else '❌ FAILED'}",
                "",
            ]
        )

        if report.warnings:
            lines.extend(
                [
                    "## Warnings",
                    "",
                ]
            )
            for warning in report.warnings:
                lines.append(f"- ⚠️ {warning}")

        return "\n".join(lines)
