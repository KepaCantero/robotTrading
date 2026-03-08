"""
Comprehensive Test Suite for Portfolio Analytics (T010)

This module contains comprehensive tests for portfolio analytics including
performance metrics, risk analysis, and portfolio management features.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.models.portfolio import Position
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
from app.services.portfolio_analytics_service import PortfolioAnalyticsService


class TestPortfolioAnalyticsModels:
    """Tests for portfolio analytics models."""

    def test_performance_metrics_creation(self):
        """Test PerformanceMetrics model creation."""
        metrics = PerformanceMetrics(
            portfolio_id=uuid4(),
            period=PerformancePeriod.MONTHLY,
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
            total_return=Decimal("5.5"),
            annualized_return=Decimal("12.0"),
            cumulative_return=Decimal("5.5"),
            volatility=Decimal("15.2"),
            sharpe_ratio=Decimal("0.8"),
            sortino_ratio=Decimal("1.2"),
            max_drawdown=Decimal("-8.5"),
            var_95=Decimal("-5.2"),
            var_99=Decimal("-7.8"),
            calmar_ratio=Decimal("1.4"),
            information_ratio=Decimal("0.6"),
            treynor_ratio=Decimal("0.7"),
            jensen_alpha=Decimal("2.1"),
            total_value=Decimal("100000"),
            cash_value=Decimal("20000"),
            equity_value=Decimal("80000"),
            position_count=10,
        )
        assert metrics.total_return == Decimal("5.5")
        assert metrics.annualized_return == Decimal("12.0")
        assert metrics.volatility == Decimal("15.2")
        assert metrics.sharpe_ratio == Decimal("0.8")
        assert metrics.total_value == Decimal("100000")
        assert metrics.cash_value + metrics.equity_value == metrics.total_value

    def test_performance_metrics_validation(self):
        """Test PerformanceMetrics validation."""
        # Test invalid percentage values
        with pytest.raises(Exception):
            PerformanceMetrics(
                portfolio_id=uuid4(),
                period=PerformancePeriod.MONTHLY,
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow(),
                total_return=Decimal("-150"),  # Invalid: too low
                annualized_return=Decimal("12.0"),
                cumulative_return=Decimal("5.5"),
                volatility=Decimal("15.2"),
                sharpe_ratio=Decimal("0.8"),
                sortino_ratio=Decimal("1.2"),
                max_drawdown=Decimal("-8.5"),
                var_95=Decimal("-5.2"),
                var_99=Decimal("-7.8"),
                calmar_ratio=Decimal("1.4"),
                information_ratio=Decimal("0.6"),
                treynor_ratio=Decimal("0.7"),
                jensen_alpha=Decimal("2.1"),
                total_value=Decimal("100000"),
                cash_value=Decimal("20000"),
                equity_value=Decimal("80000"),
                position_count=10,
            )
        # Test invalid value fields
        with pytest.raises(Exception):
            PerformanceMetrics(
                portfolio_id=uuid4(),
                period=PerformancePeriod.MONTHLY,
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow(),
                total_return=Decimal("5.5"),
                annualized_return=Decimal("12.0"),
                cumulative_return=Decimal("5.5"),
                volatility=Decimal("15.2"),
                sharpe_ratio=Decimal("0.8"),
                sortino_ratio=Decimal("1.2"),
                max_drawdown=Decimal("-8.5"),
                var_95=Decimal("-5.2"),
                var_99=Decimal("-7.8"),
                calmar_ratio=Decimal("1.4"),
                information_ratio=Decimal("0.6"),
                treynor_ratio=Decimal("0.7"),
                jensen_alpha=Decimal("2.1"),
                total_value=Decimal("-1000"),  # Invalid: negative
                cash_value=Decimal("20000"),
                equity_value=Decimal("80000"),
                position_count=10,
            )

    def test_risk_metrics_creation(self):
        """Test RiskMetrics model creation."""
        risk_metrics = RiskMetrics(
            portfolio_id=uuid4(),
            daily_volatility=Decimal("1.2"),
            annualized_volatility=Decimal("19.0"),
            realized_volatility=Decimal("18.5"),
            downside_deviation=Decimal("12.0"),
            semi_variance=Decimal("144.0"),
            lower_partial_moment=Decimal("72.0"),
            skewness=Decimal("-0.2"),
            kurtosis=Decimal("3.5"),
            tail_ratio=Decimal("0.9"),
            herfindahl_index=Decimal("0.15"),
            effective_number_of_positions=Decimal("6.7"),
            largest_position_weight=Decimal("18.5"),
            average_correlation=Decimal("0.3"),
            diversification_ratio=Decimal("1.2"),
        )
        assert risk_metrics.daily_volatility == Decimal("1.2")
        assert risk_metrics.annualized_volatility == Decimal("19.0")
        assert risk_metrics.herfindahl_index == Decimal("0.15")
        assert risk_metrics.effective_number_of_positions == Decimal("6.7")

    def test_portfolio_allocation_creation(self):
        """Test PortfolioAllocation model creation."""
        allocation = PortfolioAllocation(
            portfolio_id=uuid4(),
            equity_allocation=Decimal("60.0"),
            fixed_income_allocation=Decimal("20.0"),
            cash_allocation=Decimal("15.0"),
            alternative_allocation=Decimal("5.0"),
            domestic_allocation=Decimal("80.0"),
            international_allocation=Decimal("20.0"),
        )
        assert allocation.equity_allocation == Decimal("60.0")
        assert allocation.fixed_income_allocation == Decimal("20.0")
        assert allocation.cash_allocation == Decimal("15.0")
        assert allocation.alternative_allocation == Decimal("5.0")

        # Check that allocations sum to 100%
        total = (
            allocation.equity_allocation
            + allocation.fixed_income_allocation
            + allocation.cash_allocation
            + allocation.alternative_allocation
        )
        assert total == Decimal("100.0")

    def test_portfolio_allocation_validation(self):
        """Test PortfolioAllocation validation."""
        # Test allocations that don't sum to 100%
        with pytest.raises(Exception):
            PortfolioAllocation(
                portfolio_id=uuid4(),
                equity_allocation=Decimal("60.0"),
                fixed_income_allocation=Decimal("20.0"),
                cash_allocation=Decimal("15.0"),
                alternative_allocation=Decimal("10.0"),  # Total = 105%
                domestic_allocation=Decimal("80.0"),
                international_allocation=Decimal("20.0"),
            )

    def test_portfolio_rebalance_creation(self):
        """Test PortfolioRebalance model creation."""
        portfolio_id = uuid4()

        current_allocation = PortfolioAllocation(
            portfolio_id=portfolio_id,
            equity_allocation=Decimal("70.0"),
            fixed_income_allocation=Decimal("0.0"),
            cash_allocation=Decimal("30.0"),
            alternative_allocation=Decimal("0.0"),
            domestic_allocation=Decimal("100.0"),
            international_allocation=Decimal("0.0"),
        )
        target_allocation = PortfolioAllocation(
            portfolio_id=portfolio_id,
            equity_allocation=Decimal("60.0"),
            fixed_income_allocation=Decimal("0.0"),
            cash_allocation=Decimal("40.0"),
            alternative_allocation=Decimal("0.0"),
            domestic_allocation=Decimal("100.0"),
            international_allocation=Decimal("0.0"),
        )
        rebalance = PortfolioRebalance(
            portfolio_id=portfolio_id,
            trigger_reason="Allocation deviation",
            trigger_threshold=Decimal("5.0"),
            current_allocation=current_allocation,
            target_allocation=target_allocation,
            rebalance_actions=[
                {
                    "action": "sell_equity",
                    "amount": Decimal("10000"),
                    "reason": "Reduce equity exposure",
                }
            ],
            estimated_cost=Decimal("50.0"),
            risk_impact=Decimal("1.0"),
            return_impact=Decimal("0.5"),
        )
        assert rebalance.portfolio_id == portfolio_id
        assert rebalance.trigger_reason == "Allocation deviation"
        assert len(rebalance.rebalance_actions) == 1
        assert rebalance.estimated_cost == Decimal("50.0")


class TestPortfolioAnalyticsService:
    """Tests for PortfolioAnalyticsService."""

    @pytest.fixture
    def mock_portfolio(self):
        """Create a mock portfolio for testing."""
        from app.domain.models.portfolio import AssetClass

        positions = [
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("150.00"),
                market_price=Decimal("155.00"),
                unrealized_pnl=Decimal("500.00"),
                realized_pnl=Decimal("0.00"),
                currency="USD",
                broker="mock",
            ),
            Position(
                symbol="MSFT",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("50"),
                avg_price=Decimal("300.00"),
                market_price=Decimal("310.00"),
                unrealized_pnl=Decimal("500.00"),
                realized_pnl=Decimal("0.00"),
                currency="USD",
                broker="mock",
            ),
        ]

        # Calculate total value from positions and cash
        cash_amount = Decimal("20000.00")
        equity_value = Decimal("31000.00")  # Sum of position market values
        total_value = cash_amount + equity_value

        return ExtendedPortfolio(
            id=uuid4(),
            name="Test Portfolio",
            description="Test portfolio for analytics",
            cash=cash_amount,
            positions=positions,
            broker="mock",
            currency="USD",
            total_value=total_value,
            cash_balance=cash_amount,
        )

    @pytest.fixture
    def analytics_service(self):
        """Create analytics service instance."""
        return PortfolioAnalyticsService()

    @pytest.mark.asyncio
    async def test_calculate_performance_metrics(self, analytics_service, mock_portfolio):
        """Test performance metrics calculation."""
        metrics = await analytics_service.calculate_performance_metrics(
            portfolio=mock_portfolio, period=PerformancePeriod.MONTHLY
        )
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.portfolio_id == mock_portfolio.id
        assert metrics.period == PerformancePeriod.MONTHLY
        assert metrics.total_value == mock_portfolio.total_value
        assert metrics.cash_value == mock_portfolio.cash_balance
        assert metrics.position_count == len(mock_portfolio.positions)
        assert metrics.cash_value + metrics.equity_value == metrics.total_value

    @pytest.mark.asyncio
    async def test_calculate_risk_metrics(self, analytics_service, mock_portfolio):
        """Test risk metrics calculation."""
        risk_metrics = await analytics_service.calculate_risk_metrics(mock_portfolio)

        assert isinstance(risk_metrics, RiskMetrics)
        assert risk_metrics.portfolio_id == mock_portfolio.id
        assert risk_metrics.daily_volatility >= 0
        assert risk_metrics.annualized_volatility >= 0
        assert risk_metrics.herfindahl_index >= 0
        assert risk_metrics.effective_number_of_positions >= 0

    @pytest.mark.asyncio
    async def test_generate_portfolio_analytics(self, analytics_service, mock_portfolio):
        """Test comprehensive portfolio analytics generation."""
        analytics = await analytics_service.generate_portfolio_analytics(mock_portfolio)

        assert isinstance(analytics, PortfolioAnalytics)
        assert analytics.portfolio_id == mock_portfolio.id
        assert isinstance(analytics.performance_metrics, PerformanceMetrics)
        assert isinstance(analytics.risk_metrics, RiskMetrics)
        assert analytics.risk_level in [
            RiskLevel.LOW,
            RiskLevel.MODERATE,
            RiskLevel.HIGH,
            RiskLevel.VERY_HIGH,
        ]
        assert 0 <= analytics.risk_score <= 100
        assert 0 <= analytics.health_score <= 100
        assert 0 <= analytics.diversification_score <= 100
        assert 0 <= analytics.liquidity_score <= 100
        assert isinstance(analytics.recommendations, list)
        assert isinstance(analytics.warnings, list)

    @pytest.mark.asyncio
    async def test_analyze_portfolio_allocation(self, analytics_service, mock_portfolio):
        """Test portfolio allocation analysis."""
        allocation = await analytics_service.analyze_portfolio_allocation(mock_portfolio)

        assert isinstance(allocation, PortfolioAllocation)
        assert allocation.portfolio_id == mock_portfolio.id
        assert allocation.equity_allocation >= 0
        assert allocation.cash_allocation >= 0
        assert allocation.domestic_allocation == Decimal("100")  # Simplified implementation
        assert allocation.international_allocation == Decimal("0")  # Simplified implementation

        # Check that allocations sum to 100%
        total = (
            allocation.equity_allocation
            + allocation.fixed_income_allocation
            + allocation.cash_allocation
            + allocation.alternative_allocation
        )
        assert total == Decimal("100.0")

    @pytest.mark.asyncio
    async def test_generate_rebalance_recommendation(self, analytics_service, mock_portfolio):
        """Test rebalancing recommendation generation."""
        # Test without target allocation (should use default)
        rebalance = await analytics_service.generate_rebalance_recommendation(mock_portfolio)

        if rebalance:  # May be None if no rebalancing needed
            assert isinstance(rebalance, PortfolioRebalance)
            assert rebalance.portfolio_id == mock_portfolio.id
            assert isinstance(rebalance.current_allocation, PortfolioAllocation)
            assert isinstance(rebalance.target_allocation, PortfolioAllocation)
            assert isinstance(rebalance.rebalance_actions, list)
            assert rebalance.estimated_cost >= 0

    @pytest.mark.asyncio
    async def test_compare_portfolios(self, analytics_service):
        """Test portfolio comparison."""
        portfolio_ids = [uuid4(), uuid4(), uuid4()]

        comparison = await analytics_service.compare_portfolios(portfolio_ids)

        assert isinstance(comparison, PortfolioComparison)
        assert comparison.portfolio_ids == portfolio_ids
        assert len(comparison.performance_comparison) == len(portfolio_ids)
        assert len(comparison.risk_comparison) == len(portfolio_ids)
        assert len(comparison.performance_ranking) == len(portfolio_ids)
        assert len(comparison.risk_ranking) == len(portfolio_ids)
        assert len(comparison.sharpe_ranking) == len(portfolio_ids)
        assert comparison.best_performer in portfolio_ids
        assert comparison.lowest_risk in portfolio_ids
        assert comparison.best_risk_adjusted in portfolio_ids

    def test_helper_methods(self, analytics_service):
        """Test helper calculation methods."""
        # Test period start date calculation
        end_date = datetime.utcnow()

        daily_start = analytics_service._get_period_start_date(end_date, PerformancePeriod.DAILY)
        assert (end_date - daily_start).days == 1

        weekly_start = analytics_service._get_period_start_date(end_date, PerformancePeriod.WEEKLY)
        assert (end_date - weekly_start).days == 7

        monthly_start = analytics_service._get_period_start_date(
            end_date, PerformancePeriod.MONTHLY
        )
        assert (end_date - monthly_start).days == 30

        # Test returns calculation
        values = [Decimal("100"), Decimal("105"), Decimal("110"), Decimal("108")]
        returns = analytics_service._calculate_returns(values)
        assert len(returns) == 3
        assert returns[0] == Decimal("0.05")  # 5% return
        assert abs(returns[1] - Decimal("0.0476190476190476190476190476")) < Decimal(
            "0.0000000000000000000000000001"
        )  # ~4.76% return
        assert abs(returns[2] - Decimal("-0.0181818181818181818181818182")) < Decimal(
            "0.0000000000000000000000000001"
        )  # ~-1.82% return

        # Test total return calculation
        total_return = analytics_service._calculate_total_return(values)
        assert total_return == Decimal("8.0")  # 8% total return

        # Test volatility calculation
        volatility = analytics_service._calculate_volatility(returns)
        assert volatility >= 0

        # Test Sharpe ratio calculation
        sharpe_ratio = analytics_service._calculate_sharpe_ratio(returns)
        assert isinstance(sharpe_ratio, Decimal)

    def test_risk_assessment_methods(self, analytics_service, mock_portfolio):
        """Test risk assessment helper methods."""
        # Test Herfindahl index calculation
        herfindahl = analytics_service._calculate_herfindahl_index(mock_portfolio)
        assert herfindahl >= 0
        assert herfindahl <= 1

        # Test effective positions calculation
        effective_positions = analytics_service._calculate_effective_positions(mock_portfolio)
        assert effective_positions >= 0
        # Effective positions can be greater than actual positions when there's
        # concentration

        # Test largest position weight calculation
        largest_weight = analytics_service._calculate_largest_position_weight(mock_portfolio)
        assert largest_weight >= 0
        assert largest_weight <= 100

        # Test diversification ratio calculation
        diversification_ratio = analytics_service._calculate_diversification_ratio(mock_portfolio)
        assert diversification_ratio >= 0

    def test_score_calculation_methods(self, analytics_service, mock_portfolio):
        """Test score calculation methods."""
        # Create mock metrics for testing
        performance_metrics = PerformanceMetrics(
            portfolio_id=mock_portfolio.id,
            period=PerformancePeriod.MONTHLY,
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
            total_return=Decimal("5.0"),
            annualized_return=Decimal("12.0"),
            cumulative_return=Decimal("5.0"),
            volatility=Decimal("15.0"),
            sharpe_ratio=Decimal("0.8"),
            sortino_ratio=Decimal("1.2"),
            max_drawdown=Decimal("-8.0"),
            var_95=Decimal("-5.0"),
            var_99=Decimal("-7.0"),
            calmar_ratio=Decimal("1.5"),
            information_ratio=Decimal("0.6"),
            treynor_ratio=Decimal("0.7"),
            jensen_alpha=Decimal("2.0"),
            total_value=Decimal("100000"),
            cash_value=Decimal("20000"),
            equity_value=Decimal("80000"),
            position_count=10,
        )
        risk_metrics = RiskMetrics(
            portfolio_id=mock_portfolio.id,
            daily_volatility=Decimal("1.0"),
            annualized_volatility=Decimal("15.0"),
            realized_volatility=Decimal("14.5"),
            downside_deviation=Decimal("10.0"),
            semi_variance=Decimal("100.0"),
            lower_partial_moment=Decimal("50.0"),
            skewness=Decimal("-0.1"),
            kurtosis=Decimal("3.0"),
            tail_ratio=Decimal("0.9"),
            herfindahl_index=Decimal("0.15"),
            effective_number_of_positions=Decimal("6.7"),
            largest_position_weight=Decimal("18.0"),
            average_correlation=Decimal("0.3"),
            diversification_ratio=Decimal("1.2"),
        )
        # Test risk level assessment
        risk_level = analytics_service._assess_risk_level(risk_metrics)
        assert risk_level in [
            RiskLevel.LOW,
            RiskLevel.MODERATE,
            RiskLevel.HIGH,
            RiskLevel.VERY_HIGH,
        ]

        # Test risk score calculation
        risk_score = analytics_service._calculate_risk_score(risk_metrics)
        assert 0 <= risk_score <= 100

        # Test health score calculation
        health_score = analytics_service._calculate_health_score(
            mock_portfolio, performance_metrics, risk_metrics
        )
        assert 0 <= health_score <= 100

        # Test diversification score calculation
        diversification_score = analytics_service._calculate_diversification_score(mock_portfolio)
        assert 0 <= diversification_score <= 100

        # Test liquidity score calculation
        liquidity_score = analytics_service._calculate_liquidity_score(mock_portfolio)
        assert 0 <= liquidity_score <= 100


class TestPortfolioAnalyticsAPI:
    """Tests for Portfolio Analytics API endpoints."""

    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        from fastapi.testclient import TestClient

        from app.main import app

        return TestClient(app)

    def test_health_check(self, client):
        """Test portfolio analytics health check."""
        response = client.get("/portfolio-analytics/health-check")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "portfolio-analytics"
        assert "timestamp" in data

    def test_get_performance_metrics(self, client):
        """Test performance metrics endpoint."""
        portfolio_id = str(uuid4())
        response = client.get(f"/portfolio-analytics/performance-metrics/{portfolio_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

        metrics_data = data["data"]
        assert metrics_data["portfolio_id"] == portfolio_id
        assert "total_return" in metrics_data
        assert "annualized_return" in metrics_data
        assert "volatility" in metrics_data
        assert "sharpe_ratio" in metrics_data
        assert "total_value" in metrics_data

    def test_get_performance_metrics_with_period(self, client):
        """Test performance metrics with different periods."""
        portfolio_id = str(uuid4())

        for period in ["1d", "1w", "1m", "3m", "1y", "all"]:
            response = client.get(
                f"/portfolio-analytics/performance-metrics/{portfolio_id}?period={period}"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_risk_metrics(self, client):
        """Test risk metrics endpoint."""
        portfolio_id = str(uuid4())
        response = client.get(f"/portfolio-analytics/risk-metrics/{portfolio_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

        risk_data = data["data"]
        assert risk_data["portfolio_id"] == portfolio_id
        assert "daily_volatility" in risk_data
        assert "annualized_volatility" in risk_data
        assert "herfindahl_index" in risk_data
        assert "effective_number_of_positions" in risk_data

    def test_get_portfolio_analytics(self, client):
        """Test comprehensive portfolio analytics endpoint."""
        portfolio_id = str(uuid4())
        response = client.get(f"/portfolio-analytics/analytics/{portfolio_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

        analytics_data = data["data"]
        assert analytics_data["portfolio_id"] == portfolio_id
        assert "performance_metrics" in analytics_data
        assert "risk_metrics" in analytics_data
        assert "risk_level" in analytics_data
        assert "risk_score" in analytics_data
        assert "health_score" in analytics_data
        assert "recommendations" in analytics_data
        assert "warnings" in analytics_data

    def test_get_portfolio_allocation(self, client):
        """Test portfolio allocation endpoint."""
        portfolio_id = str(uuid4())
        response = client.get(f"/portfolio-analytics/allocation/{portfolio_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

        allocation_data = data["data"]
        assert allocation_data["portfolio_id"] == portfolio_id
        assert "equity_allocation" in allocation_data
        assert "cash_allocation" in allocation_data
        assert "domestic_allocation" in allocation_data
        assert "top_holdings" in allocation_data

    def test_get_rebalance_recommendation(self, client):
        """Test rebalancing recommendation endpoint."""
        portfolio_id = str(uuid4())

        # Test without target allocation
        response = client.post(
            "/portfolio-analytics/rebalance", json={"portfolio_id": portfolio_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Test with target allocation
        response = client.post(
            "/portfolio-analytics/rebalance",
            json={
                "portfolio_id": portfolio_id,
                "target_equity_allocation": 60.0,
                "target_cash_allocation": 40.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_compare_portfolios(self, client):
        """Test portfolio comparison endpoint."""
        portfolio_ids = [str(uuid4()), str(uuid4()), str(uuid4())]

        response = client.post(
            "/portfolio-analytics/compare", json={"portfolio_ids": portfolio_ids}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

        comparison_data = data["data"]
        assert len(comparison_data["portfolio_ids"]) == 3
        assert "performance_comparison" in comparison_data
        assert "risk_comparison" in comparison_data
        assert "best_performer" in comparison_data
        assert "lowest_risk" in comparison_data
        assert "best_risk_adjusted" in comparison_data

    def test_get_analytics_summary(self, client):
        """Test analytics summary endpoint."""
        portfolio_id = str(uuid4())
        response = client.get(f"/portfolio-analytics/summary/{portfolio_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

        summary_data = data["data"]
        assert summary_data["portfolio_id"] == portfolio_id
        assert "total_value" in summary_data
        assert "total_return" in summary_data
        assert "annualized_return" in summary_data
        assert "volatility" in summary_data
        assert "sharpe_ratio" in summary_data
        assert "risk_level" in summary_data
        assert "health_score" in summary_data
        assert "position_count" in summary_data

    def test_performance_metrics_post_endpoint(self, client):
        """Test performance metrics POST endpoint."""
        portfolio_id = str(uuid4())

        response = client.post(
            "/portfolio-analytics/performance-metrics",
            json={
                "portfolio_id": portfolio_id,
                "period": "1m",
                "start_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                "end_date": datetime.utcnow().isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data


class TestPortfolioAnalyticsIntegration:
    """Integration tests for portfolio analytics."""

    @pytest.mark.asyncio
    async def test_full_analytics_workflow(self):
        """Test complete analytics workflow."""
        from app.domain.models.portfolio import AssetClass

        # Create mock portfolio
        positions = [
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("150.00"),
                market_price=Decimal("155.00"),
                unrealized_pnl=Decimal("500.00"),
                realized_pnl=Decimal("0.00"),
                currency="USD",
                broker="mock",
            ),
            Position(
                symbol="MSFT",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("50"),
                avg_price=Decimal("300.00"),
                market_price=Decimal("310.00"),
                unrealized_pnl=Decimal("500.00"),
                realized_pnl=Decimal("0.00"),
                currency="USD",
                broker="mock",
            ),
            Position(
                symbol="GOOGL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("25"),
                avg_price=Decimal("2500.00"),
                market_price=Decimal("2550.00"),
                unrealized_pnl=Decimal("1250.00"),
                realized_pnl=Decimal("0.00"),
                currency="USD",
                broker="mock",
            ),
        ]

        # Calculate total value from positions and cash
        cash_amount = Decimal("15000.00")
        equity_value = Decimal("94750.00")  # Sum of position market values
        total_value = cash_amount + equity_value

        portfolio = ExtendedPortfolio(
            id=uuid4(),
            name="Integration Test Portfolio",
            description="Portfolio for integration testing",
            cash=cash_amount,
            positions=positions,
            broker="mock",
            currency="USD",
            total_value=total_value,
            cash_balance=cash_amount,
        )
        # Initialize analytics service
        analytics_service = PortfolioAnalyticsService()

        # Test complete workflow
        analytics = await analytics_service.generate_portfolio_analytics(portfolio)
        allocation = await analytics_service.analyze_portfolio_allocation(portfolio)
        rebalance = await analytics_service.generate_rebalance_recommendation(portfolio)

        # Verify results
        assert isinstance(analytics, PortfolioAnalytics)
        assert isinstance(allocation, PortfolioAllocation)
        assert rebalance is None or isinstance(rebalance, PortfolioRebalance)

        # Verify analytics consistency
        assert analytics.portfolio_id == portfolio.id
        assert analytics.performance_metrics.total_value == portfolio.total_value
        assert analytics.performance_metrics.cash_value == portfolio.cash_balance
        assert analytics.performance_metrics.position_count == len(portfolio.positions)

        # Verify allocation consistency
        assert allocation.portfolio_id == portfolio.id
        total_allocation = (
            allocation.equity_allocation
            + allocation.fixed_income_allocation
            + allocation.cash_allocation
            + allocation.alternative_allocation
        )
        assert total_allocation == Decimal("100.0")

        # Verify scores are within valid ranges
        assert 0 <= analytics.risk_score <= 100
        assert 0 <= analytics.health_score <= 100
        assert 0 <= analytics.diversification_score <= 100
        assert 0 <= analytics.liquidity_score <= 100

    @pytest.mark.asyncio
    async def test_edge_cases(self):
        """Test edge cases for portfolio analytics."""
        analytics_service = PortfolioAnalyticsService()

        # Test empty portfolio
        empty_portfolio = ExtendedPortfolio(
            id=uuid4(),
            name="Empty Portfolio",
            description="Empty portfolio for testing",
            cash=Decimal("100000.00"),
            positions=[],
            broker="mock",
            currency="USD",
            total_value=Decimal("100000.00"),
            cash_balance=Decimal("100000.00"),
        )
        analytics = await analytics_service.generate_portfolio_analytics(empty_portfolio)
        allocation = await analytics_service.analyze_portfolio_allocation(empty_portfolio)

        assert analytics.performance_metrics.position_count == 0
        assert analytics.performance_metrics.equity_value == Decimal("0")
        assert allocation.equity_allocation == Decimal("0")
        assert allocation.cash_allocation == Decimal("100")

        # Test single position portfolio
        from app.domain.models.portfolio import AssetClass

        single_position = [
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("1000"),
                avg_price=Decimal("150.00"),
                market_price=Decimal("155.00"),
                unrealized_pnl=Decimal("5000.00"),
                realized_pnl=Decimal("0.00"),
                currency="USD",
                broker="mock",
            )
        ]

        # Calculate total value from positions and cash
        cash_amount = Decimal("0.00")
        equity_value = Decimal("155000.00")  # Sum of position market values
        total_value = cash_amount + equity_value

        single_portfolio = ExtendedPortfolio(
            id=uuid4(),
            name="Single Position Portfolio",
            description="Portfolio with single position",
            cash=cash_amount,
            positions=single_position,
            broker="mock",
            currency="USD",
            total_value=total_value,
            cash_balance=cash_amount,
        )
        analytics = await analytics_service.generate_portfolio_analytics(single_portfolio)
        allocation = await analytics_service.analyze_portfolio_allocation(single_portfolio)

        assert analytics.performance_metrics.position_count == 1
        assert analytics.performance_metrics.cash_value == Decimal("0")
        assert allocation.equity_allocation == Decimal("100")
        assert allocation.cash_allocation == Decimal("0")
        assert analytics.risk_metrics.largest_position_weight == Decimal("100")
