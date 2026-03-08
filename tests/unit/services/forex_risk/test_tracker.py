"""
Unit tests for Forex Risk Tracker.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.models.portfolio import AssetClass, HedgingMetadata, Portfolio, Position
from app.services.forex_risk.tracker import CurrencyExposure, ForexExposureReport, ForexRiskTracker


# Mock forex service
class MockForexService:
    """Mock forex data service for testing."""

    def __init__(self):
        self.rates = {
            "EUR/USD": Decimal("1.08"),
            "EUR/GBP": Decimal("0.86"),
            "EUR/JPY": Decimal("162.0"),
            "EUR/CHF": Decimal("0.94"),
        }

    def get_current_rates(self, pairs):
        """Get mock FX rates."""
        result = {}
        for pair in pairs:
            if pair in self.rates:
                result[pair] = self.rates[pair]
        return result


@pytest.fixture
def forex_service():
    """Fixture for forex service."""
    return MockForexService()


@pytest.fixture
def tracker(forex_service):
    """Fixture for ForexRiskTracker."""
    return ForexRiskTracker(
        base_currency="EUR",
        forex_service=forex_service,
        min_hedge_threshold=Decimal("10000"),
    )


@pytest.fixture
def sample_portfolio():
    """Create a sample portfolio for testing."""
    positions = [
        Position(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("150"),
            market_price=Decimal("175"),
            unrealized_pnl=Decimal("2500"),  # 100 * (175 - 150)
            currency="USD",
            broker="ibkr",
        ),
        Position(
            symbol="MSFT",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("50"),
            avg_price=Decimal("300"),
            market_price=Decimal("330"),
            unrealized_pnl=Decimal("1500"),  # 50 * (330 - 300)
            currency="USD",
            broker="ibkr",
        ),
        Position(
            symbol="TSLA",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("20"),
            avg_price=Decimal("200"),
            market_price=Decimal("180"),
            unrealized_pnl=Decimal("-400"),  # 20 * (180 - 200)
            currency="USD",
            broker="ibkr",
        ),
        Position(
            symbol="SAN.MC",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("200"),
            avg_price=Decimal("4"),
            market_price=Decimal("4.50"),
            unrealized_pnl=Decimal("100"),  # 200 * (4.50 - 4)
            currency="EUR",
            broker="ibkr",
        ),
    ]

    return Portfolio(
        portfolio_id="test_portfolio",
        cash=Decimal("10000"),
        positions=positions,
        timestamp=datetime.now(timezone.utc),
        broker="ibkr",
        currency="EUR",
    )


class TestCurrencyExposure:
    """Test CurrencyExposure dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        exposure = CurrencyExposure(
            currency="USD",
            exposure_eur=Decimal("50000"),
            hedge_eur=Decimal("25000"),
            net_exposure_eur=Decimal("25000"),
            hedge_ratio=Decimal("0.5"),
            unrealized_pnl_eur=Decimal("500"),
            unrealized_pnl_pct=Decimal("1.0"),
            position_count=3,
        )

        result = exposure.to_dict()

        assert result["currency"] == "USD"
        assert result["exposure_eur"] == "50000"
        assert result["hedge_eur"] == "25000"
        assert result["net_exposure_eur"] == "25000"
        assert result["hedge_ratio"] == "0.5"
        assert result["unrealized_pnl_eur"] == "500"
        assert result["unrealized_pnl_pct"] == "1.0"
        assert result["position_count"] == 3

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "currency": "USD",
            "exposure_eur": "50000",
            "hedge_eur": "25000",
            "net_exposure_eur": "25000",
            "hedge_ratio": "0.5",
            "unrealized_pnl_eur": "500",
            "unrealized_pnl_pct": "1.0",
            "position_count": 3,
        }

        exposure = CurrencyExposure.from_dict(data)

        assert exposure.currency == "USD"
        assert exposure.exposure_eur == Decimal("50000")
        assert exposure.hedge_eur == Decimal("25000")
        assert exposure.net_exposure_eur == Decimal("25000")
        assert exposure.hedge_ratio == Decimal("0.5")


class TestForexRiskTracker:
    """Test ForexRiskTracker."""

    @pytest.mark.asyncio
    async def test_initialization(self, forex_service):
        """Test tracker initialization."""
        tracker = ForexRiskTracker(
            base_currency="EUR",
            forex_service=forex_service,
            min_hedge_threshold=Decimal("10000"),
        )

        assert tracker.base_currency == "EUR"
        assert tracker.forex_service == forex_service
        assert tracker.min_hedge_threshold == Decimal("10000")

    @pytest.mark.asyncio
    async def test_calculate_fx_exposure(self, tracker, sample_portfolio):
        """Test FX exposure calculation."""
        exposures = await tracker.calculate_fx_exposure(sample_portfolio)

        # Should have USD and EUR exposures
        assert "USD" in exposures
        assert "EUR" in exposures

        # Check USD exposure
        usd_exposure = exposures["USD"]
        assert usd_exposure.currency == "USD"
        assert usd_exposure.position_count == 3  # AAPL, MSFT, TSLA
        assert usd_exposure.exposure_eur > 0

        # Check EUR exposure
        eur_exposure = exposures["EUR"]
        assert eur_exposure.currency == "EUR"
        assert eur_exposure.position_count == 1  # SAN.MC

    @pytest.mark.asyncio
    async def test_calculate_fx_exposure_with_hedge(self, tracker, sample_portfolio):
        """Test FX exposure with hedged positions."""
        # Add hedge to first position
        hedging = HedgingMetadata(
            is_hedge=False,
            hedge_ratio=Decimal("0.5"),
            hedge_currency_pair="EUR/USD",
            hedge_cost_bps=Decimal("2"),
        )
        sample_portfolio.positions[0].hedging = hedging

        exposures = await tracker.calculate_fx_exposure(sample_portfolio)

        usd_exposure = exposures["USD"]
        # Should have some hedge
        assert usd_exposure.hedge_eur > 0
        assert usd_exposure.hedge_ratio > 0

    @pytest.mark.asyncio
    async def test_calculate_unhedged_exposure(self, tracker, sample_portfolio):
        """Test unhedged exposure calculation."""
        exposures = await tracker.calculate_fx_exposure(sample_portfolio)

        unhedged = tracker.calculate_unhedged_exposure(exposures)

        # Should be positive (USD exposure)
        assert unhedged >= 0
        # Should roughly equal USD exposure (EUR excluded)
        assert "USD" in exposures
        expected = abs(exposures["USD"].net_exposure_eur)
        assert abs(unhedged - expected) < Decimal("100")  # Allow small rounding diff

    @pytest.mark.asyncio
    async def test_get_hedging_recommendation(self, tracker, sample_portfolio):
        """Test hedging recommendations."""
        exposures = await tracker.calculate_fx_exposure(sample_portfolio)

        recommendations = await tracker.get_hedging_recommendation(exposures)

        # Check that recommendations are returned (may be empty if below threshold)
        assert isinstance(recommendations, list)

        # If we have USD exposure above threshold, check recommendation
        usd_exposure = exposures.get("USD")
        if usd_exposure and usd_exposure.net_exposure_eur >= tracker.min_hedge_threshold:
            usd_recs = [r for r in recommendations if r["currency"] == "USD"]
            assert len(usd_recs) > 0

            rec = usd_recs[0]
            assert rec["action"] == "hedge"
            assert rec["currency"] == "USD"
            assert "amount_eur" in rec
            assert "recommended_instrument" in rec
            assert "priority" in rec

    @pytest.mark.asyncio
    async def test_get_hedging_recommendation_below_threshold(self, tracker):
        """Test that small exposures don't get recommendations."""
        # Create portfolio with small USD exposure
        positions = [
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("10"),  # Small position
                avg_price=Decimal("150"),
                market_price=Decimal("175"),
                unrealized_pnl=Decimal("250"),
                currency="USD",
                broker="ibkr",
            ),
        ]

        portfolio = Portfolio(
            portfolio_id="small",
            cash=Decimal("10000"),
            positions=positions,
            timestamp=datetime.now(timezone.utc),
            broker="ibkr",
            currency="EUR",
        )

        exposures = await tracker.calculate_fx_exposure(portfolio)
        recommendations = await tracker.get_hedging_recommendation(exposures)

        # Should not recommend hedge for small exposure
        assert len(recommendations) == 0

    @pytest.mark.asyncio
    async def test_calculate_forward_cost(self, tracker):
        """Test forward cost calculation."""
        forward_rate, cost_eur = await tracker.calculate_forward_cost(
            currency="USD",
            amount_eur=Decimal("50000"),
            months=3,
        )

        assert forward_rate > 0
        assert isinstance(cost_eur, Decimal)

        # Cost should be reasonable (typically 0-1% annually)
        # For 3 months, should be 0-0.25%
        cost_pct = cost_eur / Decimal("50000") * 100
        assert -1 < cost_pct < 1  # Allow small negative (positive carry)

    @pytest.mark.asyncio
    async def test_generate_report(self, tracker, sample_portfolio):
        """Test complete report generation."""
        report = await tracker.generate_report(sample_portfolio)

        assert isinstance(report, ForexExposureReport)
        assert report.base_currency == "EUR"
        assert report.total_portfolio_eur > 0
        assert report.total_exposure_eur > 0
        assert report.total_unhedged_eur >= 0
        assert report.overall_hedge_ratio >= 0
        assert report.by_currency is not None
        assert report.hedging_recommendations is not None
        assert report.risk_level in ["low", "medium", "high", "critical"]

    @pytest.mark.asyncio
    async def test_risk_level_determination(self, tracker, sample_portfolio):
        """Test risk level calculation."""
        report = await tracker.generate_report(sample_portfolio)

        # Risk level should be one of the valid values
        assert report.risk_level in ["low", "medium", "high", "critical"]

    @pytest.mark.asyncio
    async def test_get_position_currency_detection(self, tracker):
        """Test automatic currency detection from symbol."""
        # Test USD (default)
        usd_position = Position(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("150"),
            market_price=Decimal("175"),
            unrealized_pnl=Decimal("2500"),
            currency="",
            broker="ibkr",
        )
        assert tracker._get_position_currency(usd_position) == "USD"

        # Test EUR from suffix
        eur_position = Position(
            symbol="SAN.MC",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("4"),
            market_price=Decimal("4.50"),
            unrealized_pnl=Decimal("50"),
            currency="",
            broker="ibkr",
        )
        assert tracker._get_position_currency(eur_position) == "EUR"

        # Test .L suffix - could be GBP or EUR, defaults to EUR in CURRENCY_SUFFIXES
        # but returns GBP in _get_position_currency special case
        gbp_position = Position(
            symbol="BP.L",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("500"),
            market_price=Decimal("550"),
            unrealized_pnl=Decimal("5000"),
            currency="",
            broker="ibkr",
        )
        # .L defaults to GBP due to special handling
        assert tracker._get_position_currency(gbp_position) == "GBP"

        # Test another .L stock
        london_position = Position(
            symbol="HSBA.L",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("600"),
            market_price=Decimal("650"),
            unrealized_pnl=Decimal("5000"),
            currency="",
            broker="ibkr",
        )
        assert tracker._get_position_currency(london_position) == "GBP"

    @pytest.mark.asyncio
    async def test_fx_rate_cache(self, tracker):
        """Test FX rate caching."""
        # First call should get from service
        rate1 = await tracker._get_fx_rate("USD")
        assert rate1 is not None

        # Second call should use cache
        rate2 = await tracker._get_fx_rate("USD")
        assert rate1 == rate2

        # Clear cache and verify
        tracker.clear_rate_cache()
        rate3 = await tracker._get_fx_rate("USD")
        assert rate3 is not None

    @pytest.mark.asyncio
    async def test_convert_to_eur(self, tracker):
        """Test currency conversion."""
        # Convert EUR to EUR (should be same)
        amount = Decimal("1000")
        converted = await tracker._convert_to_eur(amount, "EUR")
        assert converted == amount

        # Convert USD to EUR
        usd_amount = Decimal("1000")
        eur_amount = await tracker._convert_to_eur(usd_amount, "USD")
        assert eur_amount > 0
        # Should be roughly 1000 / 1.08 = 926
        assert 900 < eur_amount < 950

    @pytest.mark.asyncio
    async def test_excludes_hedge_positions(self, tracker, sample_portfolio):
        """Test that hedge positions are excluded from exposure calculation."""
        # Mark a position as a hedge
        hedging = HedgingMetadata(
            is_hedge=True,
            base_position_id="some_id",
        )
        sample_portfolio.positions[0].hedging = hedging

        exposures = await tracker.calculate_fx_exposure(sample_portfolio)

        # The hedged position should not be counted
        usd_exposure = exposures["USD"]
        assert usd_exposure.position_count == 2  # Only MSFT and TSLA


class TestForexExposureReport:
    """Test ForexExposureReport dataclass."""

    def test_to_dict(self):
        """Test report conversion to dictionary."""
        report = ForexExposureReport(
            timestamp=datetime.now(timezone.utc),
            base_currency="EUR",
            total_portfolio_eur=Decimal("100000"),
            total_exposure_eur=Decimal("60000"),
            total_unhedged_eur=Decimal("60000"),
            overall_hedge_ratio=Decimal("0"),
            fx_pnl_eur=Decimal("500"),
            by_currency={
                "USD": CurrencyExposure(
                    currency="USD",
                    exposure_eur=Decimal("50000"),
                    hedge_eur=Decimal("0"),
                    net_exposure_eur=Decimal("50000"),
                    hedge_ratio=Decimal("0"),
                    unrealized_pnl_eur=Decimal("500"),
                    unrealized_pnl_pct=Decimal("1.0"),
                    position_count=3,
                )
            },
            hedging_recommendations=[],
            risk_level="medium",
        )

        result = report.to_dict()

        assert result["base_currency"] == "EUR"
        assert result["total_portfolio_eur"] == "100000"
        assert result["risk_level"] == "medium"
        assert "USD" in result["by_currency"]
