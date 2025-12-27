"""
Portfolio Analytics Service

This service provides comprehensive portfolio analytics including performance
metrics calculation, risk analysis, and portfolio management features.
"""

import statistics
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from loguru import logger

from app.models.portfolio import Portfolio
from app.models.portfolio_analytics import (
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
from app.services.market_data_service import MarketDataService


class PortfolioAnalyticsService:
    """Service for portfolio analytics and performance calculation."""

    def __init__(self, market_data_service: Optional[MarketDataService] = None):
        """Initialize the portfolio analytics service."""
        self.market_data_service = market_data_service
        self._risk_free_rate = Decimal("0.02")  # 2% risk-free rate
        self._benchmark_return = Decimal("0.08")  # 8% benchmark return

    async def calculate_performance_metrics(
        self,
        portfolio: ExtendedPortfolio,
        period: PerformancePeriod = PerformancePeriod.MONTHLY,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics for a portfolio."""
        logger.info(f"Calculating performance metrics for portfolio {portfolio.id}")

        # Set default dates if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = self._get_period_start_date(end_date, period)

        # Get historical portfolio values
        portfolio_values = await self._get_portfolio_values(portfolio, start_date, end_date)

        if len(portfolio_values) < 2:
            raise ValueError("Insufficient data for performance calculation")

        # Calculate returns
        returns = self._calculate_returns(portfolio_values)

        # Calculate metrics
        total_return = self._calculate_total_return(portfolio_values)
        annualized_return = self._calculate_annualized_return(returns, period)
        cumulative_return = self._calculate_cumulative_return(returns)

        # Risk metrics
        volatility = self._calculate_volatility(returns)
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        sortino_ratio = self._calculate_sortino_ratio(returns)
        max_drawdown = self._calculate_max_drawdown(portfolio_values)
        var_95 = self._calculate_var(returns, 0.95)
        var_99 = self._calculate_var(returns, 0.99)

        # Additional metrics
        calmar_ratio = self._calculate_calmar_ratio(annualized_return, max_drawdown)
        information_ratio = self._calculate_information_ratio(returns)
        treynor_ratio = self._calculate_treynor_ratio(returns)
        jensen_alpha = self._calculate_jensen_alpha(returns)

        # Portfolio composition
        total_value = portfolio.total_value
        cash_value = portfolio.cash_balance
        equity_value = sum(pos.market_value for pos in portfolio.positions)
        position_count = len(portfolio.positions)

        # Benchmark comparison
        benchmark_return = await self._get_benchmark_return(start_date, end_date)
        excess_return = annualized_return - benchmark_return if benchmark_return else None
        tracking_error = self._calculate_tracking_error(returns) if benchmark_return else None

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
        """Calculate comprehensive risk metrics for a portfolio."""
        logger.info(f"Calculating risk metrics for portfolio {portfolio.id}")

        # Get historical returns for risk calculation
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=252)  # 1 year of trading days

        portfolio_values = await self._get_portfolio_values(portfolio, start_date, end_date)
        returns = self._calculate_returns(portfolio_values)

        if len(returns) < 30:
            logger.warning("Insufficient data for comprehensive risk analysis")
            # Use simplified risk metrics
            return self._calculate_simplified_risk_metrics(portfolio)

        # Volatility metrics
        daily_volatility = self._calculate_volatility(returns)
        annualized_volatility = daily_volatility * Decimal(str(252**0.5))
        realized_volatility = self._calculate_realized_volatility(returns)

        # Downside risk
        downside_deviation = self._calculate_downside_deviation(returns)
        semi_variance = self._calculate_semi_variance(returns)
        lower_partial_moment = self._calculate_lower_partial_moment(returns)

        # Tail risk
        skewness = self._calculate_skewness(returns)
        kurtosis = self._calculate_kurtosis(returns)
        tail_ratio = self._calculate_tail_ratio(returns)

        # Concentration risk
        herfindahl_index = self._calculate_herfindahl_index(portfolio)
        effective_positions = self._calculate_effective_positions(portfolio)
        largest_position_weight = self._calculate_largest_position_weight(portfolio)

        # Correlation risk
        avg_correlation = await self._calculate_average_correlation(portfolio)
        diversification_ratio = self._calculate_diversification_ratio(portfolio)

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
        """Generate comprehensive portfolio analytics."""
        logger.info(f"Generating portfolio analytics for portfolio {portfolio.id}")

        # Calculate performance and risk metrics
        performance_metrics = await self.calculate_performance_metrics(portfolio)
        risk_metrics = await self.calculate_risk_metrics(portfolio)

        # Assess risk level
        risk_level = self._assess_risk_level(risk_metrics)
        risk_score = self._calculate_risk_score(risk_metrics)

        # Calculate health scores
        health_score = self._calculate_health_score(portfolio, performance_metrics, risk_metrics)
        diversification_score = self._calculate_diversification_score(portfolio)
        liquidity_score = self._calculate_liquidity_score(portfolio)

        # Generate recommendations and warnings
        recommendations = self._generate_recommendations(
            portfolio, performance_metrics, risk_metrics
        )
        warnings = self._generate_warnings(portfolio, performance_metrics, risk_metrics)

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
        """Analyze portfolio allocation across asset classes and sectors."""
        logger.info(f"Analyzing portfolio allocation for portfolio {portfolio.id}")

        # Calculate asset class allocations
        total_value = portfolio.total_value
        equity_value = sum(pos.market_value for pos in portfolio.positions)
        cash_value = portfolio.cash_balance

        equity_allocation = (equity_value / total_value * 100) if total_value > 0 else Decimal("0")
        cash_allocation = (cash_value / total_value * 100) if total_value > 0 else Decimal("0")

        # For now, assume all positions are equity (can be enhanced later)
        fixed_income_allocation = Decimal("0")
        alternative_allocation = Decimal("0")

        # Geographic allocation (simplified - assume domestic for now)
        domestic_allocation = Decimal("100")
        international_allocation = Decimal("0")

        # Sector allocation (simplified - would need sector data)
        sector_allocations = {}

        # Top holdings
        top_holdings = []
        for position in sorted(portfolio.positions, key=lambda p: p.market_value, reverse=True)[:10
        ]:
            top_holdings.append(
                {
                    "symbol": position.symbol,
                    "weight": (
                        (position.market_value / total_value * 100)
                        if total_value > 0
                        else Decimal("0")
                    ),
                    "market_value": position.market_value,
                    "quantity": position.quantity,
                }
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
        """Generate portfolio rebalancing recommendations."""
        logger.info(f"Generating rebalance recommendation for portfolio {portfolio.id}")

        current_allocation = await self.analyze_portfolio_allocation(portfolio)

        # Default target allocation (60/40 equity/cash)
        if not target_allocation:
            target_allocation = PortfolioAllocation(
                portfolio_id=portfolio.id,
                equity_allocation=Decimal("60"),
                fixed_income_allocation=Decimal("0"),
                cash_allocation=Decimal("40"),
                alternative_allocation=Decimal("0"),
                domestic_allocation=Decimal("100"),
                international_allocation=Decimal("0"),
            )

        # Check if rebalancing is needed
        equity_deviation = abs(
            current_allocation.equity_allocation - target_allocation.equity_allocation
        )
        cash_deviation = abs(current_allocation.cash_allocation - target_allocation.cash_allocation)

        rebalance_threshold = Decimal("5")  # 5% threshold

        if equity_deviation < rebalance_threshold and cash_deviation < rebalance_threshold:
            logger.info("Portfolio is within rebalancing thresholds")
            return None

        # Generate rebalancing actions
        rebalance_actions = []

        if equity_deviation >= rebalance_threshold:
            if current_allocation.equity_allocation > target_allocation.equity_allocation:
                # Reduce equity exposure
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
                # Increase equity exposure
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

        # Estimate costs and impacts
        # Simplified - would need transaction cost data
        estimated_cost = Decimal("0")
        risk_impact = self._estimate_rebalance_risk_impact(current_allocation, target_allocation)
        return_impact = self._estimate_rebalance_return_impact(
            current_allocation, target_allocation
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
        """Compare multiple portfolios."""
        logger.info(f"Comparing portfolios: {portfolio_ids}")

        if len(portfolio_ids) < 2:
            raise ValueError("At least 2 portfolios required for comparison")

        # This would need portfolio data - simplified for now
        performance_comparison = {}
        risk_comparison = {}

        # Simplified comparison logic
        performance_ranking = []
        risk_ranking = []
        sharpe_ranking = []

        for i, portfolio_id in enumerate(portfolio_ids):
            # Mock data for demonstration
            performance_comparison[str(portfolio_id)] = PerformanceMetrics(
                portfolio_id=portfolio_id,
                period=PerformancePeriod.MONTHLY,
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow(),
                total_return=Decimal(str(5 + i)),  # Mock returns
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

            # Rankings
            performance_ranking.append((portfolio_id, Decimal(str(10 + i))))
            risk_ranking.append((portfolio_id, Decimal(str(15 + i))))
            sharpe_ranking.append((portfolio_id, Decimal(str(0.5 + i * 0.1))))

        # Sort rankings
        performance_ranking.sort(key=lambda x: x[1], reverse=True)
        risk_ranking.sort(key=lambda x: x[1])  # Lower risk is better
        sharpe_ranking.sort(key=lambda x: x[1], reverse=True)

        best_performer = performance_ranking[0][0]
        lowest_risk = risk_ranking[0][0]
        best_risk_adjusted = sharpe_ranking[0][0]

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

    # Helper methods for calculations

    def _get_period_start_date(self, end_date: datetime, period: PerformancePeriod) -> datetime:
        """Get start date based on period."""
        if period == PerformancePeriod.DAILY:
            return end_date - timedelta(days=1)
        elif period == PerformancePeriod.WEEKLY:
            return end_date - timedelta(weeks=1)
        elif period == PerformancePeriod.MONTHLY:
            return end_date - timedelta(days=30)
        elif period == PerformancePeriod.QUARTERLY:
            return end_date - timedelta(days=90)
        elif period == PerformancePeriod.YEARLY:
            return end_date - timedelta(days=365)
        else:  # ALL_TIME
            return end_date - timedelta(days=365 * 5)  # 5 years

    async def _get_portfolio_values(
        self, portfolio: Portfolio, start_date: datetime, end_date: datetime
    ) -> List[Decimal]:
        """Get historical portfolio values."""
        # Simplified implementation - would need historical position data
        values = []
        current_date = start_date

        while current_date <= end_date:
            # Mock portfolio value calculation
            base_value = portfolio.total_value
            daily_return = Decimal(str(0.001))  # 0.1% daily return
            value = base_value * (1 + daily_return) ** ((current_date - start_date).days)
            values.append(value)
            current_date += timedelta(days=1)

        return values

    def _calculate_returns(self, values: List[Decimal]) -> List[Decimal]:
        """Calculate returns from portfolio values."""
        if len(values) < 2:
            return []

        returns = []
        for i in range(1, len(values)):
            if values[i - 1] > 0:
                return_val = (values[i] - values[i - 1]) / values[i - 1]
                returns.append(return_val)

        return returns

    def _calculate_total_return(self, values: List[Decimal]) -> Decimal:
        """Calculate total return."""
        if len(values) < 2:
            return Decimal("0")

        return (values[-1] - values[0]) / values[0] * 100

    def _calculate_annualized_return(
        self, returns: List[Decimal], period: PerformancePeriod
    ) -> Decimal:
        """Calculate annualized return."""
        if not returns:
            return Decimal("0")

        avg_return = sum(returns) / len(returns)

        # Convert to annualized based on period
        if period == PerformancePeriod.DAILY:
            annualized = avg_return * 252
        elif period == PerformancePeriod.WEEKLY:
            annualized = avg_return * 52
        elif period == PerformancePeriod.MONTHLY:
            annualized = avg_return * 12
        else:
            annualized = avg_return * 365

        return annualized * 100

    def _calculate_cumulative_return(self, returns: List[Decimal]) -> Decimal:
        """Calculate cumulative return."""
        if not returns:
            return Decimal("0")

        cumulative = Decimal("1")
        for ret in returns:
            cumulative *= 1 + ret

        return (cumulative - 1) * 100

    def _calculate_volatility(self, returns: List[Decimal]) -> Decimal:
        """Calculate volatility (standard deviation)."""
        if len(returns) < 2:
            return Decimal("0")

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)

        return (variance ** Decimal("0.5")) * 100

    def _calculate_sharpe_ratio(self, returns: List[Decimal]) -> Decimal:
        """Calculate Sharpe ratio."""
        if not returns:
            return Decimal("0")

        avg_return = sum(returns) / len(returns)
        volatility = self._calculate_volatility(returns) / 100

        if volatility == 0:
            return Decimal("0")

        # Ensure reasonable values
        risk_free_daily = self._risk_free_rate / 252
        excess_return = avg_return - risk_free_daily

        # Cap the Sharpe ratio to reasonable range
        sharpe = excess_return / volatility
        return max(min(sharpe, Decimal("10")), Decimal("-10"))

    def _calculate_sortino_ratio(self, returns: List[Decimal]) -> Decimal:
        """Calculate Sortino ratio."""
        if not returns:
            return Decimal("0")

        avg_return = sum(returns) / len(returns)
        downside_returns = [r for r in returns if r < 0]

        if not downside_returns:
            return Decimal("0")

        downside_deviation = statistics.stdev([float(r) for r in downside_returns])

        if downside_deviation == 0:
            return Decimal("0")

        return (avg_return - self._risk_free_rate / 252) / Decimal(str(downside_deviation))

    def _calculate_max_drawdown(self, values: List[Decimal]) -> Decimal:
        """Calculate maximum drawdown."""
        if len(values) < 2:
            return Decimal("0")

        peak = values[0]
        max_dd = Decimal("0")

        for value in values:
            if value > peak:
                peak = value
            else:
                drawdown = (peak - value) / peak
                if drawdown > max_dd:
                    max_dd = drawdown

        return max_dd * 100

    def _calculate_var(self, returns: List[Decimal], confidence: float) -> Decimal:
        """Calculate Value at Risk."""
        if not returns:
            return Decimal("0")

        sorted_returns = sorted(returns)
        index = int((1 - confidence) * len(sorted_returns))

        if index >= len(sorted_returns):
            return Decimal("0")

        return sorted_returns[index] * 100

    def _calculate_calmar_ratio(self, annualized_return: Decimal, max_drawdown: Decimal) -> Decimal:
        """Calculate Calmar ratio."""
        if max_drawdown == 0:
            return Decimal("0")

        return annualized_return / abs(max_drawdown)

    def _calculate_information_ratio(self, returns: List[Decimal]) -> Decimal:
        """Calculate Information ratio."""
        if not returns:
            return Decimal("0")

        avg_return = sum(returns) / len(returns)
        benchmark_return = self._benchmark_return / 252  # Daily benchmark return

        excess_return = avg_return - benchmark_return
        tracking_error = self._calculate_tracking_error(returns)

        if tracking_error == 0:
            return Decimal("0")

        # Cap the information ratio to reasonable range
        info_ratio = excess_return / tracking_error
        return max(min(info_ratio, Decimal("10")), Decimal("-10"))

    def _calculate_treynor_ratio(self, returns: List[Decimal]) -> Decimal:
        """Calculate Treynor ratio."""
        if not returns:
            return Decimal("0")

        avg_return = sum(returns) / len(returns)
        beta = Decimal("1")  # Simplified - would need beta calculation

        if beta == 0:
            return Decimal("0")

        # Cap the Treynor ratio to reasonable range
        treynor = (avg_return - self._risk_free_rate / 252) / beta
        return max(min(treynor, Decimal("10")), Decimal("-10"))

    def _calculate_jensen_alpha(self, returns: List[Decimal]) -> Decimal:
        """Calculate Jensen's alpha."""
        if not returns:
            return Decimal("0")

        avg_return = sum(returns) / len(returns)
        benchmark_return = self._benchmark_return / 252
        beta = Decimal("1")  # Simplified

        # Cap the Jensen's alpha to reasonable range
        alpha = (avg_return - self._risk_free_rate / 252) - beta * (
            benchmark_return - self._risk_free_rate / 252
        )
        return max(min(alpha, Decimal("1")), Decimal("-1"))

    def _calculate_tracking_error(self, returns: List[Decimal]) -> Decimal:
        """Calculate tracking error."""
        if not returns:
            return Decimal("0")

        benchmark_return = self._benchmark_return / 252
        excess_returns = [r - benchmark_return for r in returns]

        return self._calculate_volatility(excess_returns) / 100

    async def _get_benchmark_return(
        self, start_date: datetime, end_date: datetime
    ) -> Optional[Decimal]:
        """Get benchmark return for the period."""
        # Simplified - would need benchmark data
        days = (end_date - start_date).days
        return self._benchmark_return * days / 365

    def _calculate_realized_volatility(self, returns: List[Decimal]) -> Decimal:
        """Calculate realized volatility."""
        return self._calculate_volatility(returns)

    def _calculate_downside_deviation(self, returns: List[Decimal]) -> Decimal:
        """Calculate downside deviation."""
        negative_returns = [r for r in returns if r < 0]
        if not negative_returns:
            return Decimal("0")

        return self._calculate_volatility(negative_returns)

    def _calculate_semi_variance(self, returns: List[Decimal]) -> Decimal:
        """Calculate semi-variance."""
        mean_return = sum(returns) / len(returns) if returns else Decimal("0")
        negative_deviations = [(r - mean_return) ** 2 for r in returns if r < mean_return]

        if not negative_deviations:
            return Decimal("0")

        return sum(negative_deviations) / len(negative_deviations)

    def _calculate_lower_partial_moment(self, returns: List[Decimal]) -> Decimal:
        """Calculate lower partial moment."""
        target_return = Decimal("0")  # Risk-free rate
        negative_deviations = [(target_return - r) ** 2 for r in returns if r < target_return]

        if not negative_deviations:
            return Decimal("0")

        return sum(negative_deviations) / len(negative_deviations)

    def _calculate_skewness(self, returns: List[Decimal]) -> Decimal:
        """Calculate skewness."""
        if len(returns) < 3:
            return Decimal("0")

        mean_return = sum(returns) / len(returns)
        std_dev = self._calculate_volatility(returns) / 100

        if std_dev == 0:
            return Decimal("0")

        skewness = sum(((r - mean_return) / std_dev) ** 3 for r in returns) / len(returns)
        return Decimal(str(skewness))

    def _calculate_kurtosis(self, returns: List[Decimal]) -> Decimal:
        """Calculate kurtosis."""
        if len(returns) < 4:
            return Decimal("0")

        mean_return = sum(returns) / len(returns)
        std_dev = self._calculate_volatility(returns) / 100

        if std_dev == 0:
            return Decimal("0")

        kurtosis = sum(((r - mean_return) / std_dev) ** 4 for r in returns) / len(returns)
        return Decimal(str(kurtosis))

    def _calculate_tail_ratio(self, returns: List[Decimal]) -> Decimal:
        """Calculate tail ratio."""
        if len(returns) < 20:
            return Decimal("0")

        sorted_returns = sorted(returns)
        tail_size = len(returns) // 10  # Top and bottom 10%

        if tail_size == 0:
            return Decimal("0")

        upper_tail = sorted_returns[-tail_size:]
        lower_tail = sorted_returns[:tail_size]

        upper_avg = sum(upper_tail) / len(upper_tail)
        lower_avg = sum(lower_tail) / len(lower_tail)

        if lower_avg == 0:
            return Decimal("0")

        return abs(upper_avg / lower_avg)

    def _calculate_herfindahl_index(self, portfolio: Portfolio) -> Decimal:
        """Calculate Herfindahl concentration index."""
        if not portfolio.positions:
            return Decimal("0")

        total_value = portfolio.total_value
        if total_value == 0:
            return Decimal("0")

        weights = [pos.market_value / total_value for pos in portfolio.positions]
        herfindahl = sum(w**2 for w in weights)

        return herfindahl

    def _calculate_effective_positions(self, portfolio: Portfolio) -> Decimal:
        """Calculate effective number of positions."""
        herfindahl = self._calculate_herfindahl_index(portfolio)

        if herfindahl == 0:
            return Decimal("0")

        return Decimal("1") / herfindahl

    def _calculate_largest_position_weight(self, portfolio: Portfolio) -> Decimal:
        """Calculate weight of largest position."""
        if not portfolio.positions:
            return Decimal("0")

        total_value = portfolio.total_value
        if total_value == 0:
            return Decimal("0")

        largest_position = max(portfolio.positions, key=lambda p: p.market_value)
        return largest_position.market_value / total_value * 100

    async def _calculate_average_correlation(self, portfolio: Portfolio) -> Decimal:
        """Calculate average correlation between positions."""
        # Simplified - would need historical correlation data
        return Decimal("0.3")  # Mock value

    def _calculate_diversification_ratio(self, portfolio: Portfolio) -> Decimal:
        """Calculate diversification ratio."""
        # Simplified calculation
        effective_positions = self._calculate_effective_positions(portfolio)
        actual_positions = len(portfolio.positions)

        if actual_positions == 0:
            return Decimal("0")

        return effective_positions / actual_positions

    def _assess_risk_level(self, risk_metrics: RiskMetrics) -> RiskLevel:
        """Assess overall risk level."""
        volatility_score = min(risk_metrics.annualized_volatility / 20, Decimal("1"))  # 20% = max
        concentration_score = risk_metrics.largest_position_weight / 20  # 20% = max
        correlation_score = risk_metrics.average_correlation

        risk_score = (volatility_score + concentration_score + correlation_score) / 3

        if risk_score < Decimal("0.25"):
            return RiskLevel.LOW
        elif risk_score < Decimal("0.5"):
            return RiskLevel.MODERATE
        elif risk_score < Decimal("0.75"):
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH

    def _calculate_risk_score(self, risk_metrics: RiskMetrics) -> Decimal:
        """Calculate risk score (0-100)."""
        volatility_score = (
            min(risk_metrics.annualized_volatility, Decimal("50")) / Decimal("50") * 40
        )
        concentration_score = (
            min(risk_metrics.largest_position_weight, Decimal("50")) / Decimal("50") * 30
        )
        correlation_score = risk_metrics.average_correlation * 30

        return volatility_score + concentration_score + correlation_score

    def _calculate_health_score(
        self, portfolio: Portfolio, performance: PerformanceMetrics, risk: RiskMetrics
    ) -> Decimal:
        """Calculate portfolio health score."""
        # Performance component (40%)
        performance_score = (
            min(max(performance.annualized_return, Decimal("0")), Decimal("20"))
            / Decimal("20")
            * 40
        )

        # Risk component (30%)
        risk_score = max(Decimal("100") - self._calculate_risk_score(risk), Decimal("0")) * Decimal(
            "0.3"
        )

        # Diversification component (30%)
        diversification_score = (
            min(risk.effective_number_of_positions / Decimal("10"), Decimal("1")) * 30
        )

        return performance_score + risk_score + diversification_score

    def _calculate_diversification_score(self, portfolio: Portfolio) -> Decimal:
        """Calculate diversification score."""
        if not portfolio.positions:
            return Decimal("0")

        effective_positions = self._calculate_effective_positions(portfolio)
        # Assume 20 positions is well diversified
        max_positions = Decimal("20")

        return min(effective_positions / max_positions, Decimal("1")) * 100

    def _calculate_liquidity_score(self, portfolio: Portfolio) -> Decimal:
        """Calculate liquidity score."""
        cash_ratio = (
            portfolio.cash_balance / portfolio.total_value
            if portfolio.total_value > 0
            else Decimal("0")
        )

        # Higher cash ratio = higher liquidity score
        return min(cash_ratio * 100, Decimal("100"))

    def _generate_recommendations(
        self, portfolio: Portfolio, performance: PerformanceMetrics, risk: RiskMetrics
    ) -> List[str]:
        """Generate portfolio recommendations."""
        recommendations = []

        # Performance recommendations
        if performance.annualized_return < Decimal("5"):
            recommendations.append("Consider increasing equity exposure for better returns")

        if performance.sharpe_ratio < Decimal("0.5"):
            recommendations.append("Portfolio risk-adjusted returns are low - consider rebalancing")

        # Risk recommendations
        if risk.annualized_volatility > Decimal("20"):
            recommendations.append("High volatility detected - consider reducing position sizes")

        if risk.largest_position_weight > Decimal("20"):
            recommendations.append(
                "Concentration risk high - consider diversifying largest positions"
            )

        # Diversification recommendations
        if len(portfolio.positions) < 5:
            recommendations.append("Low diversification - consider adding more positions")

        return recommendations

    def _generate_warnings(
        self, portfolio: Portfolio, performance: PerformanceMetrics, risk: RiskMetrics
    ) -> List[str]:
        """Generate portfolio warnings."""
        warnings = []

        # Performance warnings
        if performance.max_drawdown > Decimal("20"):
            warnings.append(f"High maximum drawdown: {performance.max_drawdown:.2f}%")

        if performance.var_95 > Decimal("10"):
            warnings.append(f"High Value at Risk (95%): {performance.var_95:.2f}%")

        # Risk warnings
        if risk.annualized_volatility > Decimal("30"):
            warnings.append(f"Extremely high volatility: {risk.annualized_volatility:.2f}%")

        if risk.largest_position_weight > Decimal("30"):
            warnings.append(
                f"Extreme concentration: {risk.largest_position_weight:.2f}% in largest position"
            )

        # Cash warnings
        cash_ratio = (
            portfolio.cash_balance / portfolio.total_value
            if portfolio.total_value > 0
            else Decimal("0")
        )
        if cash_ratio > Decimal("0.5"):
            warnings.append("High cash allocation may impact returns")

        return warnings

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
            herfindahl_index=self._calculate_herfindahl_index(portfolio),
            effective_number_of_positions=self._calculate_effective_positions(portfolio),
            largest_position_weight=self._calculate_largest_position_weight(portfolio),
            average_correlation=Decimal("0.3"),
            diversification_ratio=self._calculate_diversification_ratio(portfolio),
        )

    def _estimate_rebalance_risk_impact(
        self, current: PortfolioAllocation, target: PortfolioAllocation
    ) -> Decimal:
        """Estimate risk impact of rebalancing."""
        # Simplified calculation
        equity_change = abs(current.equity_allocation - target.equity_allocation)
        # 0.1% risk impact per 1% allocation change
        return equity_change * Decimal("0.1")

    def _estimate_rebalance_return_impact(
        self, current: PortfolioAllocation, target: PortfolioAllocation
    ) -> Decimal:
        """Estimate return impact of rebalancing."""
        # Simplified calculation
        equity_change = target.equity_allocation - current.equity_allocation
        # 0.05% return impact per 1% allocation change
        return equity_change * Decimal("0.05")


# Dependency injection
def get_portfolio_analytics_service() -> PortfolioAnalyticsService:
    """Get portfolio analytics service instance."""
    return PortfolioAnalyticsService()
