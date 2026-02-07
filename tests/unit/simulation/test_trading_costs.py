"""
Unit Tests for Trading Costs Analysis - Harris Trading and Exchanges

Tests for the trading cost analysis framework following Harris's
cost components and evaluation methods.
"""

from decimal import Decimal

import pytest

from app.simulation.trading_costs import (
    BidAskSpreadAnalyzer,
    CostBreakdown,
    CostComponent,
    ImpactModel,
    MarketImpactModel,
    TimingRiskCalculator,
    TradingCostAnalyzer,
    create_trading_cost_analyzer,
)


class TestMarketImpactModel:
    """Test MarketImpactModel class."""

    def test_linear_impact_model(self):
        """Test linear impact model."""
        model = MarketImpactModel(
            model_type=ImpactModel.LINEAR,
            daily_volume=1_000_000,
            k_permanent=0.1,
        )

        temp, perm = model.calculate_impact(
            order_quantity=10000,
            current_price=100.0,
            adv=1_000_000,
        )

        # Participation rate = 1%
        # Linear impact = 0.1 * 0.01 = 0.001 = 10 bps
        assert perm > 0
        assert temp > 0
        assert temp < perm  # Temporary should be smaller

    def test_square_root_impact_model(self):
        """Test square root impact model."""
        model = MarketImpactModel(
            model_type=ImpactModel.SQUARE_ROOT,
            daily_volume=1_000_000,
            k_permanent=0.1,
        )

        temp, perm = model.calculate_impact(
            order_quantity=10000,
            current_price=100.0,
            adv=1_000_000,
        )

        # Square root model should give different impact than linear
        assert perm > 0

    def test_power_law_impact_model(self):
        """Test power law impact model."""
        model = MarketImpactModel(
            model_type=ImpactModel.POWER_LAW,
            alpha=0.6,  # Custom exponent
            k_permanent=0.1,
        )

        temp, perm = model.calculate_impact(
            order_quantity=10000,
            current_price=100.0,
            adv=1_000_000,
        )

        assert perm > 0
        assert temp > 0

    def test_impact_scales_with_participation(self):
        """Test that impact scales with participation rate."""
        model = MarketImpactModel(
            model_type=ImpactModel.SQUARE_ROOT,
            daily_volume=1_000_000,
        )

        # Small order
        temp1, perm1 = model.calculate_impact(
            order_quantity=1000,
            current_price=100.0,
            adv=1_000_000,
        )

        # Large order
        temp2, perm2 = model.calculate_impact(
            order_quantity=100000,
            current_price=100.0,
            adv=1_000_000,
        )

        # Larger order should have more impact
        assert perm2 > perm1
        assert temp2 > temp1


class TestBidAskSpreadAnalyzer:
    """Test BidAskSpreadAnalyzer class."""

    def test_add_spread_observation(self):
        """Test adding spread observations."""
        analyzer = BidAskSpreadAnalyzer()

        analyzer.add_spread_observation(
            timestamp=datetime.now(),
            bid=Decimal("149.50"),
            ask=Decimal("150.50"),
        )

        stats = analyzer.get_spread_statistics()
        assert "mean_spread" in stats
        assert stats["mean_spread"] == 1.0

    def test_get_average_spread(self):
        """Test calculating average spread."""
        analyzer = BidAskSpreadAnalyzer()

        analyzer.add_spread_observation(
            timestamp=datetime.now(),
            bid=Decimal("149.50"),
            ask=Decimal("150.50"),
        )

        analyzer.add_spread_observation(
            timestamp=datetime.now(),
            bid=Decimal("149.75"),
            ask=Decimal("150.25"),
        )

        avg_spread = analyzer.get_average_spread()
        assert avg_spread == Decimal("1.00")

    def test_spread_statistics(self):
        """Test comprehensive spread statistics."""
        analyzer = BidAskSpreadAnalyzer()

        # Add observations with varying spreads
        for i in range(10):
            bid = Decimal(f"149.{i}0")
            ask = Decimal(f"150.{10-i}0")
            analyzer.add_spread_observation(
                timestamp=datetime.now(),
                bid=bid,
                ask=ask,
            )

        stats = analyzer.get_spread_statistics()

        assert "mean_spread" in stats
        assert "std_spread" in stats
        assert "median_spread" in stats
        assert "mean_relative_spread_bps" in stats
        assert "min_spread" in stats
        assert "max_spread" in stats

    def test_adverse_selection_cost(self):
        """Test adverse selection cost calculation."""
        analyzer = BidAskSpreadAnalyzer()

        # Buy at 150, price moves to 150.50 = adverse
        cost = analyzer.estimate_adverse_selection_cost(
            trade_price=Decimal("150.00"),
            subsequent_mid_price=Decimal("150.50"),
            is_buy=True,
        )

        assert cost == Decimal("0.50")  # Unfavorable move

        # Sell at 150, price moves to 149.50 = adverse
        cost = analyzer.estimate_adverse_selection_cost(
            trade_price=Decimal("150.00"),
            subsequent_mid_price=Decimal("149.50"),
            is_buy=False,
        )

        assert cost == Decimal("0.50")  # Unfavorable move


class TestTimingRiskCalculator:
    """Test TimingRiskCalculator class."""

    def test_calculate_timing_risk(self):
        """Test timing risk calculation."""
        calculator = TimingRiskCalculator(confidence_level=0.95)

        risk = calculator.calculate_timing_risk(
            target_quantity=Decimal("10000"),
            execution_price=Decimal("150.00"),
            volatility=0.2,
            execution_period_hours=0.5,
        )

        assert "timing_risk_absolute" in risk
        assert "timing_risk_bps" in risk
        assert "period_volatility" in risk
        assert risk["timing_risk_bps"] > 0

    def test_timing_risk_with_arrival_price(self):
        """Test timing risk with arrival price."""
        calculator = TimingRiskCalculator()

        risk = calculator.calculate_timing_risk(
            target_quantity=Decimal("10000"),
            execution_price=Decimal("150.50"),
            volatility=0.2,
            execution_period_hours=0.5,
            arrival_price=Decimal("150.00"),
        )

        assert "arrival_cost" in risk
        assert "arrival_cost_bps" in risk

        # Bought higher than arrival = cost
        assert risk["arrival_cost"] > 0

    def test_implicit_cost(self):
        """Test implicit cost calculation."""
        calculator = TimingRiskCalculator()

        # Buy: paid more than decision price
        cost = calculator.calculate_implicit_cost(
            execution_price=Decimal("150.50"),
            decision_price=Decimal("150.00"),
            is_buy=True,
        )
        assert cost == Decimal("0.50")

        # Sell: received less than decision price
        cost = calculator.calculate_implicit_cost(
            execution_price=Decimal("149.50"),
            decision_price=Decimal("150.00"),
            is_buy=False,
        )
        assert cost == Decimal("0.50")


class TestTradingCostAnalyzer:
    """Test TradingCostAnalyzer class."""

    def test_analyze_execution_basic(self):
        """Test basic execution cost analysis."""
        analyzer = create_trading_cost_analyzer(
            impact_model=ImpactModel.SQUARE_ROOT,
            daily_volume=1_000_000,
        )

        cost = analyzer.analyze_execution(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("1000"),
            execution_price=Decimal("150.50"),
            benchmark_price=Decimal("150.00"),
            commission=Decimal("5.00"),
            bid_at_arrival=Decimal("149.90"),
            ask_at_arrival=Decimal("150.10"),
            adv=1_000_000,
            volatility=0.2,
        )

        assert cost.symbol == "AAPL"
        assert cost.quantity == Decimal("1000")
        assert cost.execution_price == Decimal("150.50")
        assert cost.benchmark_price == Decimal("150.00")
        assert cost.total_cost > 0

    def test_cost_components(self):
        """Test that cost components are calculated."""
        analyzer = TradingCostAnalyzer()

        cost = analyzer.analyze_execution(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("1000"),
            execution_price=Decimal("150.50"),
            benchmark_price=Decimal("150.00"),
            commission=Decimal("10.00"),
            fees=Decimal("2.00"),
            bid_at_arrival=Decimal("149.90"),
            ask_at_arrival=Decimal("150.10"),
        )

        # Should have commission cost
        assert CostComponent.COMMISSION in cost.components
        assert cost.components[CostComponent.COMMISSION] == Decimal("12.00")

        # Should have spread cost
        assert CostComponent.SPREAD in cost.components

    def test_evaluate_execution_quality(self):
        """Test execution quality evaluation."""
        analyzer = TradingCostAnalyzer()

        cost_breakdown = CostBreakdown(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("1000"),
            execution_price=Decimal("150.02"),
            benchmark_price=Decimal("150.00"),
        )

        quality = analyzer.evaluate_execution_quality(
            cost_breakdown=cost_breakdown,
            fill_rate=Decimal("100"),
        )

        assert quality.symbol == "AAPL"
        assert quality.fill_rate == Decimal("100")
        assert 0 <= quality.execution_score <= 100

    def test_quality_score_excellent(self):
        """Test execution quality score for excellent execution."""
        analyzer = TradingCostAnalyzer()

        # Price improvement scenario
        cost_breakdown = CostBreakdown(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("1000"),
            execution_price=Decimal("149.98"),  # Better than benchmark
            benchmark_price=Decimal("150.00"),
        )

        quality = analyzer.evaluate_execution_quality(
            cost_breakdown=cost_breakdown,
            fill_rate=Decimal("100"),
        )

        # Should have good score due to price improvement
        assert quality.execution_score > 50
        assert quality.price_improvement_bps > 0

    def test_quality_score_poor(self):
        """Test execution quality score for poor execution."""
        analyzer = TradingCostAnalyzer()

        # High cost scenario
        cost_breakdown = CostBreakdown(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("1000"),
            execution_price=Decimal("151.00"),  # Much worse than benchmark
            benchmark_price=Decimal("150.00"),
        )
        cost_breakdown.total_cost = Decimal("1000")  # $1 higher = 1000 cents
        cost_breakdown.total_cost_bps = Decimal("66.67")  # 66.67 bps

        quality = analyzer.evaluate_execution_quality(
            cost_breakdown=cost_breakdown,
            fill_rate=Decimal("80"),  # Poor fill rate
        )

        # Should have poor score
        assert quality.execution_score < 80


class TestCreateTradingCostAnalyzer:
    """Test factory function."""

    def test_factory_function(self):
        """Test create_trading_cost_analyzer factory."""
        analyzer = create_trading_cost_analyzer(
            impact_model=ImpactModel.SQUARE_ROOT,
            daily_volume=1_000_000,
        )

        assert isinstance(analyzer, TradingCostAnalyzer)
        assert isinstance(analyzer.market_impact_model, MarketImpactModel)


@pytest.mark.parametrize(
    "impact_model",
    [
        ImpactModel.LINEAR,
        ImpactModel.SQUARE_ROOT,
        ImpactModel.POWER_LAW,
        ImpactModel.ALMGREN_CHRISS,
        ImpactModel.STATIC,
    ],
)
def test_all_impact_models(impact_model):
    """Test that all impact models work."""
    model = MarketImpactModel(model_type=impact_model)

    temp, perm = model.calculate_impact(
        order_quantity=10000,
        current_price=100.0,
        adv=1_000_000,
    )

    # All models should produce some impact
    assert temp >= 0
    assert perm >= 0


# Import datetime for BidAskSpreadAnalyzer tests
from datetime import datetime
