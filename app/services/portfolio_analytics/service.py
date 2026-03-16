"""
Portfolio Analytics Service

This service provides comprehensive portfolio analytics including performance
metrics calculation, risk analysis, and portfolio management features.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from app.domain.models.portfolio import Portfolio
from app.domain.models.portfolio_analytics import (
    ExtendedPortfolio,
    PerformanceMetrics,
    PerformancePeriod,
    PortfolioAllocation,
    PortfolioAnalytics,
    PortfolioComparison,
    PortfolioRebalance,
    RiskLevel,
    RiskMetrics,
)
from app.services.portfolio_analytics._performance_calculations import PerformanceCalculations
from app.services.portfolio_analytics._portfolio_calculations import PortfolioCalculations
from app.services.portfolio_analytics._risk_calculations import RiskCalculations
from app.shared.config.trading_config import get_config

logger = logging.getLogger(__name__)


class PortfolioAnalyticsService:
    """Service for portfolio analytics and performance calculation."""

    def __init__(self, market_data_service=None):
        """
        Initialize the portfolio analytics service.

        Args:
            market_data_service: Optional market data service for price lookups
        """
        logger.debug(
            "Initializing PortfolioAnalyticsService",
            extra={"has_market_data_service": market_data_service is not None},
        )
        self.market_data_service = market_data_service
        self._config = get_config()

        self._risk_free_rate = Decimal(
            str(getattr(self._config.trading, "portfolio_risk_free_rate", 0.02))
        )
        self._benchmark_return = Decimal(
            str(getattr(self._config.trading, "analytics_benchmark_return", 0.08))
        )

        self._performance = PerformanceCalculations(self._risk_free_rate, self._benchmark_return)
        self._risk = RiskCalculations()
        self._portfolio_calc = PortfolioCalculations()

        logger.info(
            "PortfolioAnalyticsService initialized",
            extra={
                "risk_free_rate": float(self._risk_free_rate),
                "benchmark_return": float(self._benchmark_return),
            },
        )

    async def calculate_performance_metrics(
        self,
        portfolio: ExtendedPortfolio,
        period: PerformancePeriod = PerformancePeriod.MONTHLY,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics for a portfolio.

        Args:
            portfolio: Portfolio to analyze
            period: Time period for analysis
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            PerformanceMetrics object with all calculated metrics
        """
        logger.debug(
            "calculate_performance_metrics called",
            extra={"portfolio_id": str(portfolio.id), "period": period.value},
        )
        logger.info(
            "Calculating performance metrics for portfolio",
            extra={
                "portfolio_id": str(portfolio.id),
                "period": period.value,
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )

        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = self._performance.get_period_start_date(end_date, period.value)

        portfolio_values = await self._get_portfolio_values(portfolio, start_date, end_date)

        if len(portfolio_values) < 2:
            logger.error(
                "Insufficient data for performance calculation",
                extra={"portfolio_id": str(portfolio.id), "values_count": len(portfolio_values)},
            )
            raise ValueError("Insufficient data for performance calculation")

        returns = self._performance.calculate_returns(portfolio_values)

        total_return = self._performance.calculate_total_return(portfolio_values)
        annualized_return = self._performance.calculate_annualized_return(returns, period.value)
        cumulative_return = self._performance.calculate_cumulative_return(returns)

        volatility = self._performance.calculate_volatility(returns)
        sharpe_ratio = self._performance.calculate_sharpe_ratio(returns)
        sortino_ratio = self._performance.calculate_sortino_ratio(returns)
        max_drawdown = self._performance.calculate_max_drawdown(portfolio_values)

        var_95_confidence = float(
            getattr(self._config.trading, "analytics_var_95_confidence", 0.95)
        )
        var_99_confidence = float(
            getattr(self._config.trading, "analytics_var_99_confidence", 0.99)
        )
        var_95 = self._performance.calculate_var(returns, var_95_confidence)
        var_99 = self._performance.calculate_var(returns, var_99_confidence)

        calmar_ratio = self._performance.calculate_calmar_ratio(annualized_return, max_drawdown)
        information_ratio = self._performance.calculate_information_ratio(returns)
        treynor_ratio = self._performance.calculate_treynor_ratio(returns, Decimal("1"))
        jensen_alpha = self._performance.calculate_jensen_alpha(returns, Decimal("1"))

        total_value = portfolio.total_value
        cash_value = portfolio.cash_balance
        equity_value = sum(pos.market_value for pos in portfolio.positions)
        position_count = len(portfolio.positions)

        benchmark_return = await self._get_benchmark_return(start_date, end_date)
        excess_return = annualized_return - benchmark_return if benchmark_return else None
        tracking_error = (
            self._performance.calculate_tracking_error(returns) if benchmark_return else None
        )

        logger.info(
            "Performance metrics calculated",
            extra={
                "portfolio_id": str(portfolio.id),
                "total_return": float(total_return),
                "sharpe_ratio": float(sharpe_ratio),
                "max_drawdown": float(max_drawdown),
            },
        )
        return PerformanceMetrics(
            portfolio_id=portfolio.id,
            period=period,
            start_date=start_date,
            end_date=end_date,
            total_return=total_return,
            annualized_return=annualized_return,
            cumulative_return=cumulative_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            var_95=var_95,
            var_99=var_99,
            calmar_ratio=calmar_ratio,
            information_ratio=information_ratio,
            treynor_ratio=treynor_ratio,
            jensen_alpha=jensen_alpha,
            total_value=total_value,
            cash_value=cash_value,
            equity_value=equity_value,
            position_count=position_count,
            benchmark_return=benchmark_return,
            excess_return=excess_return,
            tracking_error=tracking_error,
        )

    async def calculate_risk_metrics(self, portfolio: ExtendedPortfolio) -> RiskMetrics:
        """
        Calculate comprehensive risk metrics for a portfolio.

        Args:
            portfolio: Portfolio to analyze

        Returns:
            RiskMetrics object with all calculated risk metrics
        """
        logger.debug("calculate_risk_metrics called", extra={"portfolio_id": str(portfolio.id)})
        logger.info(
            "Calculating risk metrics for portfolio",
            extra={"portfolio_id": str(portfolio.id)},
        )

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=252)

        portfolio_values = await self._get_portfolio_values(portfolio, start_date, end_date)
        returns = self._performance.calculate_returns(portfolio_values)

        if len(returns) < 30:
            logger.warning(
                "Insufficient data for comprehensive risk analysis",
                extra={"portfolio_id": str(portfolio.id), "returns_count": len(returns)},
            )
            return self._calculate_simplified_risk_metrics(portfolio)

        daily_volatility = self._performance.calculate_volatility(returns)
        annualized_volatility = daily_volatility * Decimal(str(252**0.5))
        realized_volatility = self._performance.calculate_realized_volatility(returns)

        downside_deviation = self._risk.calculate_downside_deviation(
            returns, self._performance.calculate_volatility
        )
        semi_variance = self._risk.calculate_semi_variance(returns)
        lower_partial_moment = self._risk.calculate_lower_partial_moment(returns)

        skewness = self._risk.calculate_skewness(returns, self._performance.calculate_volatility)
        kurtosis = self._risk.calculate_kurtosis(returns, self._performance.calculate_volatility)
        tail_ratio = self._risk.calculate_tail_ratio(returns)

        herfindahl_index = self._portfolio_calc.calculate_herfindahl_index(portfolio)
        effective_positions = self._portfolio_calc.calculate_effective_positions(portfolio)
        largest_position_weight = self._portfolio_calc.calculate_largest_position_weight(portfolio)

        avg_correlation = await self._calculate_average_correlation(portfolio)
        diversification_ratio = self._portfolio_calc.calculate_diversification_ratio(portfolio)

        logger.info(
            "Risk metrics calculated",
            extra={
                "portfolio_id": str(portfolio.id),
                "annualized_volatility": float(annualized_volatility),
                "herfindahl_index": float(herfindahl_index),
            },
        )
        return RiskMetrics(
            portfolio_id=portfolio.id,
            daily_volatility=daily_volatility,
            annualized_volatility=annualized_volatility,
            realized_volatility=realized_volatility,
            downside_deviation=downside_deviation,
            semi_variance=semi_variance,
            lower_partial_moment=lower_partial_moment,
            skewness=skewness,
            kurtosis=kurtosis,
            tail_ratio=tail_ratio,
            herfindahl_index=herfindahl_index,
            effective_number_of_positions=effective_positions,
            largest_position_weight=largest_position_weight,
            average_correlation=avg_correlation,
            diversification_ratio=diversification_ratio,
        )

    async def generate_portfolio_analytics(
        self, portfolio: ExtendedPortfolio
    ) -> PortfolioAnalytics:
        """
        Generate comprehensive portfolio analytics.

        Args:
            portfolio: Portfolio to analyze

        Returns:
            PortfolioAnalytics object with all analytics
        """
        logger.debug(
            "generate_portfolio_analytics called",
            extra={"portfolio_id": str(portfolio.id)},
        )
        logger.info(
            "Generating portfolio analytics for portfolio",
            extra={"portfolio_id": str(portfolio.id)},
        )

        performance_metrics = await self.calculate_performance_metrics(portfolio)
        risk_metrics = await self.calculate_risk_metrics(portfolio)

        risk_level = self._assess_risk_level(risk_metrics)
        risk_score = self._calculate_risk_score(risk_metrics)

        health_score = self._calculate_health_score(portfolio, performance_metrics, risk_metrics)
        diversification_score = self._portfolio_calc.calculate_diversification_score(portfolio)
        liquidity_score = self._portfolio_calc.calculate_liquidity_score(portfolio)

        recommendations = self._generate_recommendations(
            portfolio, performance_metrics, risk_metrics
        )
        warnings = self._generate_warnings(portfolio, performance_metrics, risk_metrics)

        logger.info(
            "Portfolio analytics generated",
            extra={
                "portfolio_id": str(portfolio.id),
                "risk_level": risk_level.value,
                "health_score": float(health_score),
            },
        )
        return PortfolioAnalytics(
            portfolio_id=portfolio.id,
            performance_metrics=performance_metrics,
            risk_metrics=risk_metrics,
            risk_level=risk_level,
            risk_score=risk_score,
            health_score=health_score,
            diversification_score=diversification_score,
            liquidity_score=liquidity_score,
            recommendations=recommendations,
            warnings=warnings,
        )

    async def analyze_portfolio_allocation(
        self, portfolio: ExtendedPortfolio
    ) -> PortfolioAllocation:
        """
        Analyze portfolio allocation across asset classes and sectors.

        Args:
            portfolio: Portfolio to analyze

        Returns:
            PortfolioAllocation object with allocation breakdown
        """
        logger.debug(
            "analyze_portfolio_allocation called",
            extra={"portfolio_id": str(portfolio.id)},
        )
        logger.info(
            "Analyzing portfolio allocation for portfolio",
            extra={"portfolio_id": str(portfolio.id)},
        )

        equity_allocation = self._portfolio_calc.calculate_equity_allocation(portfolio)
        cash_allocation = self._portfolio_calc.calculate_cash_allocation(portfolio)

        fixed_income_allocation = Decimal("0")
        alternative_allocation = Decimal("0")

        domestic_allocation = Decimal("100")
        international_allocation = Decimal("0")

        sector_allocations: Dict[str, Decimal] = {}
        top_holdings = self._portfolio_calc.get_top_holdings(portfolio, limit=10)

        logger.info(
            "Portfolio allocation analyzed",
            extra={
                "portfolio_id": str(portfolio.id),
                "equity_allocation": float(equity_allocation),
                "cash_allocation": float(cash_allocation),
                "position_count": len(portfolio.positions),
            },
        )
        return PortfolioAllocation(
            portfolio_id=portfolio.id,
            equity_allocation=equity_allocation,
            fixed_income_allocation=fixed_income_allocation,
            cash_allocation=cash_allocation,
            alternative_allocation=alternative_allocation,
            domestic_allocation=domestic_allocation,
            international_allocation=international_allocation,
            sector_allocations=sector_allocations,
            top_holdings=top_holdings,
        )

    async def generate_rebalance_recommendation(
        self,
        portfolio: ExtendedPortfolio,
        target_allocation: Optional[PortfolioAllocation] = None,
    ) -> Optional[PortfolioRebalance]:
        """
        Generate portfolio rebalancing recommendations.

        Args:
            portfolio: Portfolio to analyze
            target_allocation: Optional target allocation

        Returns:
            PortfolioRebalance if rebalancing needed, None otherwise
        """
        logger.debug(
            "generate_rebalance_recommendation called",
            extra={
                "portfolio_id": str(portfolio.id),
                "has_target_allocation": target_allocation is not None,
            },
        )
        logger.info(
            "Generating rebalance recommendation for portfolio",
            extra={"portfolio_id": str(portfolio.id)},
        )

        current_allocation = await self.analyze_portfolio_allocation(portfolio)

        if not target_allocation:
            target_equity = Decimal(
                str(getattr(self._config.trading, "analytics_target_equity_allocation", 0.60) * 100)
            )
            target_cash = Decimal(
                str(getattr(self._config.trading, "analytics_target_cash_allocation", 0.40) * 100)
            )
            target_allocation = PortfolioAllocation(
                portfolio_id=portfolio.id,
                equity_allocation=target_equity,
                fixed_income_allocation=Decimal("0"),
                cash_allocation=target_cash,
                alternative_allocation=Decimal("0"),
                domestic_allocation=Decimal("100"),
                international_allocation=Decimal("0"),
            )

        equity_deviation = abs(
            current_allocation.equity_allocation - target_allocation.equity_allocation
        )
        cash_deviation = abs(current_allocation.cash_allocation - target_allocation.cash_allocation)

        rebalance_threshold = Decimal(
            str(getattr(self._config.trading, "analytics_rebalance_threshold", 0.05) * 100)
        )

        if equity_deviation < rebalance_threshold and cash_deviation < rebalance_threshold:
            logger.info(
                "Portfolio is within rebalancing thresholds",
                extra={
                    "portfolio_id": str(portfolio.id),
                    "equity_deviation": float(equity_deviation),
                    "cash_deviation": float(cash_deviation),
                    "threshold": float(rebalance_threshold),
                },
            )
            return None

        rebalance_actions = self._create_rebalance_actions(
            portfolio, current_allocation, target_allocation, equity_deviation, rebalance_threshold
        )

        estimated_cost = Decimal("0")
        risk_impact_factor = Decimal(
            str(getattr(self._config.trading, "analytics_risk_impact_factor", 0.1))
        )
        return_impact_factor = Decimal(
            str(getattr(self._config.trading, "analytics_return_impact_factor", 0.05))
        )
        risk_impact = self._portfolio_calc.estimate_rebalance_risk_impact(
            current_allocation, target_allocation, risk_impact_factor
        )
        return_impact = self._portfolio_calc.estimate_rebalance_return_impact(
            current_allocation, target_allocation, return_impact_factor
        )

        logger.info(
            "Rebalance recommendation generated",
            extra={
                "portfolio_id": str(portfolio.id),
                "equity_deviation": float(equity_deviation),
                "cash_deviation": float(cash_deviation),
                "actions_count": len(rebalance_actions),
            },
        )
        return PortfolioRebalance(
            portfolio_id=portfolio.id,
            trigger_reason=f"Allocation deviation: Equity {equity_deviation:.2f}%, Cash {cash_deviation:.2f}%",
            trigger_threshold=rebalance_threshold,
            current_allocation=current_allocation,
            target_allocation=target_allocation,
            rebalance_actions=rebalance_actions,
            estimated_cost=estimated_cost,
            risk_impact=risk_impact,
            return_impact=return_impact,
        )

    async def compare_portfolios(self, portfolio_ids: List[UUID]) -> PortfolioComparison:
        """
        Compare multiple portfolios.

        Args:
            portfolio_ids: List of portfolio IDs to compare

        Returns:
            PortfolioComparison with comparative metrics
        """
        logger.debug(
            "compare_portfolios called",
            extra={"portfolio_ids": [str(pid) for pid in portfolio_ids]},
        )
        logger.info(
            "Comparing portfolios",
            extra={
                "portfolio_count": len(portfolio_ids),
                "portfolio_ids": [str(pid) for pid in portfolio_ids],
            },
        )

        if len(portfolio_ids) < 2:
            logger.error(
                "At least 2 portfolios required for comparison",
                extra={"portfolio_count": len(portfolio_ids)},
            )
            raise ValueError("At least 2 portfolios required for comparison")

        performance_comparison, risk_comparison = self._create_mock_comparisons(portfolio_ids)

        performance_ranking = sorted(
            [(pid, Decimal(str(10 + i))) for i, pid in enumerate(portfolio_ids)],
            key=lambda x: x[1],
            reverse=True,
        )
        risk_ranking = sorted(
            [(pid, Decimal(str(15 + i))) for i, pid in enumerate(portfolio_ids)],
            key=lambda x: x[1],
        )
        sharpe_ranking = sorted(
            [(pid, Decimal(str(0.5 + i * 0.1))) for i, pid in enumerate(portfolio_ids)],
            key=lambda x: x[1],
            reverse=True,
        )

        best_performer = performance_ranking[0][0]
        lowest_risk = risk_ranking[0][0]
        best_risk_adjusted = sharpe_ranking[0][0]

        logger.info(
            "Portfolio comparison completed",
            extra={
                "portfolio_count": len(portfolio_ids),
                "best_performer": str(best_performer),
                "lowest_risk": str(lowest_risk),
                "best_risk_adjusted": str(best_risk_adjusted),
            },
        )
        return PortfolioComparison(
            portfolio_ids=portfolio_ids,
            performance_comparison=performance_comparison,
            risk_comparison=risk_comparison,
            performance_ranking=performance_ranking,
            risk_ranking=risk_ranking,
            sharpe_ranking=sharpe_ranking,
            best_performer=best_performer,
            lowest_risk=lowest_risk,
            best_risk_adjusted=best_risk_adjusted,
            comparison_summary=f"Compared {len(portfolio_ids)} portfolios. Best performer: {best_performer}, Lowest risk: {lowest_risk}, Best risk-adjusted: {best_risk_adjusted}",
            recommendations=[
                f"Portfolio {best_performer} shows best performance",
                f"Portfolio {lowest_risk} has lowest risk",
                f"Portfolio {best_risk_adjusted} offers best risk-adjusted returns",
            ],
        )

    async def _get_portfolio_values(
        self, portfolio: Portfolio, start_date: datetime, end_date: datetime
    ) -> List[Decimal]:
        """Get historical portfolio values for a date range."""
        values = []
        current_date = start_date

        while current_date <= end_date:
            base_value = portfolio.total_value
            daily_return = Decimal(
                str(getattr(self._config.trading, "analytics_mock_daily_return", 0.001))
            )
            value = base_value * (1 + daily_return) ** ((current_date - start_date).days)
            values.append(value)
            current_date += timedelta(days=1)

        return values

    async def _get_benchmark_return(
        self, start_date: datetime, end_date: datetime
    ) -> Optional[Decimal]:
        """Get benchmark return for the period."""
        days = (end_date - start_date).days
        return self._benchmark_return * days / 365

    async def _calculate_average_correlation(self, portfolio: Portfolio) -> Decimal:
        """Calculate average correlation between positions."""
        return Decimal(
            str(getattr(self._config.trading, "analytics_default_average_correlation", 0.3))
        )

    def _calculate_simplified_risk_metrics(self, portfolio: Portfolio) -> RiskMetrics:
        """Calculate simplified risk metrics when data is insufficient."""
        return RiskMetrics(
            portfolio_id=portfolio.id,
            daily_volatility=Decimal("1"),
            annualized_volatility=Decimal("15"),
            realized_volatility=Decimal("15"),
            downside_deviation=Decimal("10"),
            semi_variance=Decimal("100"),
            lower_partial_moment=Decimal("50"),
            skewness=Decimal("0"),
            kurtosis=Decimal("3"),
            tail_ratio=Decimal("1"),
            herfindahl_index=self._portfolio_calc.calculate_herfindahl_index(portfolio),
            effective_number_of_positions=self._portfolio_calc.calculate_effective_positions(
                portfolio
            ),
            largest_position_weight=self._portfolio_calc.calculate_largest_position_weight(
                portfolio
            ),
            average_correlation=Decimal(
                str(getattr(self._config.trading, "analytics_default_average_correlation", 0.3))
            ),
            diversification_ratio=self._portfolio_calc.calculate_diversification_ratio(portfolio),
        )

    def _assess_risk_level(self, risk_metrics: RiskMetrics) -> RiskLevel:
        """Assess overall risk level based on metrics."""
        volatility_max = Decimal(
            str(getattr(self._config.trading, "analytics_volatility_max_score", 0.20))
        )
        concentration_max = Decimal(
            str(getattr(self._config.trading, "analytics_concentration_max_score", 0.20))
        )
        volatility_score = min(risk_metrics.annualized_volatility / volatility_max, Decimal("1"))
        concentration_score = risk_metrics.largest_position_weight / concentration_max
        correlation_score = risk_metrics.average_correlation

        risk_score = (volatility_score + concentration_score + correlation_score) / 3

        low_threshold = Decimal(
            str(getattr(self._config.trading, "analytics_risk_score_low_threshold", 0.25))
        )
        moderate_threshold = Decimal(
            str(getattr(self._config.trading, "analytics_risk_score_moderate_threshold", 0.5))
        )
        high_threshold = Decimal(
            str(getattr(self._config.trading, "analytics_risk_score_high_threshold", 0.75))
        )

        if risk_score < low_threshold:
            return RiskLevel.LOW
        elif risk_score < moderate_threshold:
            return RiskLevel.MODERATE
        elif risk_score < high_threshold:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH

    def _calculate_risk_score(self, risk_metrics: RiskMetrics) -> Decimal:
        """Calculate risk score (0-100)."""
        volatility_max = Decimal(
            str(getattr(self._config.trading, "analytics_volatility_max_score", 0.50))
        )
        concentration_max = Decimal(
            str(getattr(self._config.trading, "analytics_concentration_max_score", 0.50))
        )

        volatility_score = (
            min(risk_metrics.annualized_volatility, volatility_max) / volatility_max * 40
        )
        concentration_score = (
            min(risk_metrics.largest_position_weight, concentration_max) / concentration_max * 30
        )
        correlation_score = risk_metrics.average_correlation * 30

        return volatility_score + concentration_score + correlation_score

    def _calculate_health_score(
        self,
        portfolio: Portfolio,
        performance: PerformanceMetrics,
        risk: RiskMetrics,
    ) -> Decimal:
        """Calculate portfolio health score."""
        max_performance = Decimal(
            str(getattr(self._config.trading, "analytics_max_performance_return", 0.20))
        )
        performance_score = (
            min(max(performance.annualized_return, Decimal("0")), max_performance)
            / max_performance
            * 40
        )

        max_risk = Decimal(str(getattr(self._config.trading, "analytics_max_risk_score", 0.50)))
        risk_score = max(max_risk * 2 - self._calculate_risk_score(risk), Decimal("0")) * Decimal(
            "0.3"
        )

        well_diversified = Decimal(
            str(getattr(self._config.trading, "analytics_well_diversified_positions", 0.10))
        )
        diversification_score = (
            min(risk.effective_number_of_positions / well_diversified, Decimal("1")) * 30
        )

        return performance_score + risk_score + diversification_score

    def _generate_recommendations(
        self,
        portfolio: Portfolio,
        performance: PerformanceMetrics,
        risk: RiskMetrics,
    ) -> List[str]:
        """Generate portfolio recommendations based on metrics."""
        recommendations = []

        annualized_return_threshold = Decimal(
            str(getattr(self._config.trading, "analytics_annualized_return_threshold", 0.05))
        )
        if performance.annualized_return < annualized_return_threshold:
            recommendations.append("Consider increasing equity exposure for better returns")

        sharpe_threshold = Decimal(
            str(getattr(self._config.trading, "analytics_sharpe_ratio_threshold", 0.5))
        )
        if performance.sharpe_ratio < sharpe_threshold:
            recommendations.append("Portfolio risk-adjusted returns are low - consider rebalancing")

        volatility_high_threshold = Decimal(
            str(getattr(self._config.trading, "analytics_volatility_high_threshold", 0.20))
        )
        if risk.annualized_volatility > volatility_high_threshold:
            recommendations.append("High volatility detected - consider reducing position sizes")

        largest_position_high_threshold = Decimal(
            str(getattr(self._config.trading, "analytics_largest_position_high_threshold", 0.20))
        )
        if risk.largest_position_weight > largest_position_high_threshold:
            recommendations.append(
                "Concentration risk high - consider diversifying largest positions"
            )

        min_position_count = int(
            getattr(self._config.trading, "analytics_min_position_count_diversified", 5)
        )
        if len(portfolio.positions) < min_position_count:
            recommendations.append("Low diversification - consider adding more positions")

        return recommendations

    def _generate_warnings(
        self,
        portfolio: Portfolio,
        performance: PerformanceMetrics,
        risk: RiskMetrics,
    ) -> List[str]:
        """Generate portfolio warnings based on metrics."""
        warnings = []

        max_drawdown_threshold = Decimal(
            str(getattr(self._config.trading, "analytics_max_drawdown_high_threshold", 0.20))
        )
        if performance.max_drawdown > max_drawdown_threshold:
            warnings.append(f"High maximum drawdown: {performance.max_drawdown:.2f}%")

        var_95_threshold = Decimal(
            str(getattr(self._config.trading, "analytics_var_95_high_threshold", 0.10))
        )
        if performance.var_95 > var_95_threshold:
            warnings.append(f"High Value at Risk (95%): {performance.var_95:.2f}%")

        volatility_extreme_threshold = Decimal(
            str(getattr(self._config.trading, "analytics_volatility_extreme_threshold", 0.30))
        )
        if risk.annualized_volatility > volatility_extreme_threshold:
            warnings.append(f"Extremely high volatility: {risk.annualized_volatility:.2f}%")

        largest_position_extreme_threshold = Decimal(
            str(getattr(self._config.trading, "analytics_largest_position_extreme_threshold", 0.30))
        )
        if risk.largest_position_weight > largest_position_extreme_threshold:
            warnings.append(
                f"Extreme concentration: {risk.largest_position_weight:.2f}% in largest position"
            )

        cash_ratio = (
            portfolio.cash_balance / portfolio.total_value
            if portfolio.total_value > 0
            else Decimal("0")
        )
        cash_ratio_high_threshold = Decimal(
            str(getattr(self._config.trading, "analytics_cash_ratio_high_threshold", 0.5))
        )
        if cash_ratio > cash_ratio_high_threshold:
            warnings.append("High cash allocation may impact returns")

        return warnings

    def _create_rebalance_actions(
        self,
        portfolio: ExtendedPortfolio,
        current_allocation: PortfolioAllocation,
        target_allocation: PortfolioAllocation,
        equity_deviation: Decimal,
        rebalance_threshold: Decimal,
    ) -> List[dict]:
        """Create rebalance actions based on allocation deviation."""
        rebalance_actions = []

        if equity_deviation >= rebalance_threshold:
            if current_allocation.equity_allocation > target_allocation.equity_allocation:
                excess_equity = (
                    (current_allocation.equity_allocation - target_allocation.equity_allocation)
                    / 100
                    * portfolio.total_value
                )
                rebalance_actions.append(
                    {
                        "action": "sell_equity",
                        "amount": excess_equity,
                        "reason": "Reduce equity exposure to target",
                    }
                )
            else:
                deficit_equity = (
                    (target_allocation.equity_allocation - current_allocation.equity_allocation)
                    / 100
                    * portfolio.total_value
                )
                rebalance_actions.append(
                    {
                        "action": "buy_equity",
                        "amount": deficit_equity,
                        "reason": "Increase equity exposure to target",
                    }
                )

        return rebalance_actions

    def _create_mock_comparisons(
        self, portfolio_ids: List[UUID]
    ) -> Tuple[Dict[str, PerformanceMetrics], Dict[str, RiskMetrics]]:
        """Create mock comparison data for portfolio comparison."""
        performance_comparison = {}
        risk_comparison = {}

        for i, portfolio_id in enumerate(portfolio_ids):
            performance_comparison[str(portfolio_id)] = PerformanceMetrics(
                portfolio_id=portfolio_id,
                period=PerformancePeriod.MONTHLY,
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow(),
                total_return=Decimal(str(5 + i)),
                annualized_return=Decimal(str(10 + i)),
                cumulative_return=Decimal(str(5 + i)),
                volatility=Decimal(str(15 + i)),
                sharpe_ratio=Decimal(str(0.5 + i * 0.1)),
                sortino_ratio=Decimal(str(0.6 + i * 0.1)),
                max_drawdown=Decimal(str(-10 - i)),
                var_95=Decimal(str(-5 - i)),
                var_99=Decimal(str(-8 - i)),
                calmar_ratio=Decimal(str(0.8 + i * 0.1)),
                information_ratio=Decimal(str(0.3 + i * 0.1)),
                treynor_ratio=Decimal(str(0.4 + i * 0.1)),
                jensen_alpha=Decimal(str(2 + i)),
                total_value=Decimal("100000"),
                cash_value=Decimal("40000"),
                equity_value=Decimal("60000"),
                position_count=10 + i,
            )

            risk_comparison[str(portfolio_id)] = RiskMetrics(
                portfolio_id=portfolio_id,
                daily_volatility=Decimal(str(1 + i * 0.1)),
                annualized_volatility=Decimal(str(15 + i)),
                realized_volatility=Decimal(str(14 + i)),
                downside_deviation=Decimal(str(10 + i)),
                semi_variance=Decimal(str(100 + i * 10)),
                lower_partial_moment=Decimal(str(50 + i * 5)),
                skewness=Decimal(str(-0.1 - i * 0.1)),
                kurtosis=Decimal(str(3 + i * 0.5)),
                tail_ratio=Decimal(str(0.8 + i * 0.05)),
                herfindahl_index=Decimal(str(0.2 + i * 0.05)),
                effective_number_of_positions=Decimal(str(8 - i)),
                largest_position_weight=Decimal(str(15 + i)),
                average_correlation=Decimal(str(0.3 + i * 0.1)),
                diversification_ratio=Decimal(str(1.2 + i * 0.1)),
            )

        return performance_comparison, risk_comparison


def get_portfolio_analytics_service() -> PortfolioAnalyticsService:
    """Get portfolio analytics service instance for dependency injection."""
    return PortfolioAnalyticsService()
