"""
Unit tests for Hedging Engine.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.services.forex_risk.hedging_engine import (
    HedgeDirection,
    HedgeEffectiveness,
    HedgeInstrument,
    HedgeInstrumentType,
    HedgeRecommendation,
    HedgingEngine,
)


@pytest.fixture
def forex_service():
    """Mock forex service."""

    class MockForexService:
        def get_current_rates(self, pairs):
            return {
                "EUR/USD": Decimal("1.08"),
                "EUR/GBP": Decimal("0.86"),
            }

    return MockForexService()


@pytest.fixture
def hedging_engine(forex_service):
    """Fixture for HedgingEngine."""
    return HedgingEngine(
        forex_service=forex_service,
        base_currency="EUR",
    )


class TestHedgeInstrument:
    """Test HedgeInstrument dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        instrument = HedgeInstrument(
            type=HedgeInstrumentType.FORWARD,
            currency_pair="EUR/USD",
            contract_size=Decimal("100000"),
            liquidity=100,
            typical_spread_bps=Decimal("2"),
            symbol="EURUSD",
            tick_size=Decimal("0.0001"),
            tick_value=Decimal("10"),
            tenor_options=[1, 3, 6, 12],
            is_exchange_traded=False,
        )

        result = instrument.to_dict()

        assert result["type"] == "forward"
        assert result["currency_pair"] == "EUR/USD"
        assert result["contract_size"] == "100000"
        assert result["liquidity"] == 100
        assert result["is_exchange_traded"] is False


class TestHedgeRecommendation:
    """Test HedgeRecommendation dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        instrument = HedgeInstrument(
            type=HedgeInstrumentType.FORWARD,
            currency_pair="EUR/USD",
            contract_size=Decimal("100000"),
            liquidity=100,
            typical_spread_bps=Decimal("2"),
        )

        recommendation = HedgeRecommendation(
            currency="USD",
            direction=HedgeDirection.SHORT,
            amount_eur=Decimal("50000"),
            optimal_ratio=Decimal("0.85"),
            instrument=instrument,
            contracts=None,
            tenor_months=3,
            expected_cost_eur=Decimal("125"),
            expected_cost_bps=Decimal("2.5"),
            effectiveness=Decimal("0.85"),
            roll_schedule="Roll quarterly",
            reasoning="Hedge USD exposure",
            priority="high",
        )

        result = recommendation.to_dict()

        assert result["currency"] == "USD"
        assert result["direction"] == "short"
        assert result["amount_eur"] == "50000"
        assert result["optimal_ratio"] == "0.85"
        assert result["priority"] == "high"


class TestHedgeEffectiveness:
    """Test HedgeEffectiveness dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        effectiveness = HedgeEffectiveness(
            currency="USD",
            hedge_ratio=Decimal("0.85"),
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc) + timedelta(days=90),
            portfolio_return_eur=Decimal("5000"),
            hedge_return_eur=Decimal("-425"),
            combined_return_eur=Decimal("4575"),
            variance_reduction=Decimal("0.85"),
            effectiveness=Decimal("0.85"),
            basis_risk=Decimal("0.15"),
        )

        result = effectiveness.to_dict()

        assert result["currency"] == "USD"
        assert result["hedge_ratio"] == "0.85"
        assert result["effectiveness"] == "0.85"
        assert result["basis_risk"] == "0.15"


class TestHedgingEngine:
    """Test HedgingEngine."""

    def test_initialization(self, forex_service):
        """Test engine initialization."""
        engine = HedgingEngine(
            forex_service=forex_service,
            base_currency="EUR",
        )

        assert engine.base_currency == "EUR"
        assert engine.forex_service == forex_service

    @pytest.mark.asyncio
    async def test_calculate_optimal_hedge_ratio_naive(self, hedging_engine):
        """Test naive hedge ratio calculation."""
        ratio = await hedging_engine.calculate_optimal_hedge_ratio(
            exposure_eur=Decimal("50000"),
            currency="USD",
            method="naive",
        )

        assert ratio == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_calculate_optimal_hedge_ratio_partial(self, hedging_engine):
        """Test partial hedge ratio calculation."""
        ratio = await hedging_engine.calculate_optimal_hedge_ratio(
            exposure_eur=Decimal("50000"),
            currency="USD",
            method="partial",
        )

        assert ratio == Decimal("0.5")

    @pytest.mark.asyncio
    async def test_calculate_optimal_hedge_ratio_minimum_variance(self, hedging_engine):
        """Test minimum variance hedge ratio calculation."""
        ratio = await hedging_engine.calculate_optimal_hedge_ratio(
            exposure_eur=Decimal("50000"),
            currency="USD",
            method="minimum_variance",
        )

        # Should be between 0 and 1
        assert Decimal("0") <= ratio <= Decimal("1")

    @pytest.mark.asyncio
    async def test_calculate_optimal_hedge_ratio_with_parameters(self, hedging_engine):
        """Test minimum variance with custom parameters."""
        ratio = await hedging_engine.calculate_optimal_hedge_ratio(
            exposure_eur=Decimal("50000"),
            currency="USD",
            method="minimum_variance",
            correlation=Decimal("0.9"),
            volatility_asset=Decimal("0.20"),
            volatility_fx=Decimal("0.10"),
        )

        # h* = 0.9 * (0.20 / 0.10) = 1.8, but capped at 1.0
        assert ratio == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_get_recommendation(self, hedging_engine):
        """Test hedge recommendation generation."""
        recommendation = await hedging_engine.get_recommendation(
            exposure_eur=Decimal("50000"),
            currency="USD",
            risk_tolerance=Decimal("0.8"),
            preferred_tenor_months=3,
        )

        assert isinstance(recommendation, HedgeRecommendation)
        assert recommendation.currency == "USD"
        assert recommendation.amount_eur > 0
        assert recommendation.optimal_ratio > 0
        assert recommendation.tenor_months == 3
        assert recommendation.instrument is not None

    @pytest.mark.asyncio
    async def test_get_recommendation_low_risk_tolerance(self, hedging_engine):
        """Test recommendation with low risk tolerance."""
        recommendation = await hedging_engine.get_recommendation(
            exposure_eur=Decimal("50000"),
            currency="USD",
            risk_tolerance=Decimal("0.5"),  # Low risk tolerance
        )

        # Hedge amount should be lower with low risk tolerance
        assert recommendation.amount_eur < Decimal("50000")
        assert recommendation.optimal_ratio < Decimal("0.9")

    @pytest.mark.asyncio
    async def test_get_recommendation_high_risk_tolerance(self, hedging_engine):
        """Test recommendation with high risk tolerance."""
        recommendation = await hedging_engine.get_recommendation(
            exposure_eur=Decimal("50000"),
            currency="USD",
            risk_tolerance=Decimal("1.0"),  # Full risk tolerance
        )

        # Should hedge more with high risk tolerance
        assert recommendation.amount_eur > 0

    def test_calculate_effectiveness_perfect_hedge(self, hedging_engine):
        """Test effectiveness with perfect hedge."""
        # Perfect hedge: FX moves offset asset moves
        portfolio_return = Decimal("0.10")  # 10% up in local currency
        fx_return = Decimal("-0.10")  # 10% down in FX
        hedge_ratio = Decimal("1.0")

        effectiveness = hedging_engine.calculate_effectiveness(
            portfolio_return_local=portfolio_return,
            fx_return=fx_return,
            hedge_ratio=hedge_ratio,
        )

        # Perfect hedge should have high effectiveness
        assert effectiveness > Decimal("0.8")

    def test_calculate_effectiveness_no_hedge(self, hedging_engine):
        """Test effectiveness with no hedge."""
        portfolio_return = Decimal("0.10")
        fx_return = Decimal("-0.05")
        hedge_ratio = Decimal("0")  # No hedge

        effectiveness = hedging_engine.calculate_effectiveness(
            portfolio_return_local=portfolio_return,
            fx_return=fx_return,
            hedge_ratio=hedge_ratio,
        )

        # No hedge = no effectiveness
        assert effectiveness == Decimal("0")

    def test_calculate_effectiveness_partial_hedge(self, hedging_engine):
        """Test effectiveness with partial hedge."""
        # Use different returns that show effectiveness
        portfolio_return = Decimal("0.10")  # Asset up 10%
        fx_return = Decimal("-0.10")  # FX down 10% (harmful for long foreign)
        hedge_ratio = Decimal("0.5")  # 50% hedge

        effectiveness = hedging_engine.calculate_effectiveness(
            portfolio_return_local=portfolio_return,
            fx_return=fx_return,
            hedge_ratio=hedge_ratio,
        )

        # Partial hedge should have partial effectiveness
        # With perfect correlation, a 50% hedge reduces variance by ~50%
        assert effectiveness >= Decimal("0")

    def test_track_effectiveness(self, hedging_engine):
        """Test effectiveness tracking."""
        period_start = datetime.now(timezone.utc)
        period_end = period_start + timedelta(days=90)

        effectiveness = hedging_engine.track_effectiveness(
            currency="USD",
            hedge_ratio=Decimal("0.85"),
            period_start=period_start,
            period_end=period_end,
            portfolio_return_eur=Decimal("5000"),
            hedge_return_eur=Decimal("-425"),
            combined_return_eur=Decimal("4575"),
        )

        assert isinstance(effectiveness, HedgeEffectiveness)
        assert effectiveness.currency == "USD"
        assert effectiveness.hedge_ratio == Decimal("0.85")
        assert Decimal("0") <= effectiveness.effectiveness <= Decimal("1")

    def test_get_effectiveness_history(self, hedging_engine):
        """Test retrieving effectiveness history."""
        # Track some effectiveness
        period_start = datetime.now(timezone.utc)
        period_end = period_start + timedelta(days=90)

        hedging_engine.track_effectiveness(
            currency="USD",
            hedge_ratio=Decimal("0.85"),
            period_start=period_start,
            period_end=period_end,
            portfolio_return_eur=Decimal("5000"),
            hedge_return_eur=Decimal("-425"),
            combined_return_eur=Decimal("4575"),
        )

        history = hedging_engine.get_effectiveness_history("USD")

        assert len(history) == 1
        assert history[0].currency == "USD"

    def test_clear_effectiveness_history(self, hedging_engine):
        """Test clearing effectiveness history."""
        # Track some effectiveness
        period_start = datetime.now(timezone.utc)
        period_end = period_start + timedelta(days=90)

        hedging_engine.track_effectiveness(
            currency="USD",
            hedge_ratio=Decimal("0.85"),
            period_start=period_start,
            period_end=period_end,
            portfolio_return_eur=Decimal("5000"),
            hedge_return_eur=Decimal("-425"),
            combined_return_eur=Decimal("4575"),
        )

        # Clear specific currency
        hedging_engine.clear_effectiveness_history("USD")

        history = hedging_engine.get_effectiveness_history("USD")
        assert len(history) == 0

    def test_clear_all_effectiveness_history(self, hedging_engine):
        """Test clearing all effectiveness history."""
        # Track effectiveness for multiple currencies
        period_start = datetime.now(timezone.utc)
        period_end = period_start + timedelta(days=90)

        hedging_engine.track_effectiveness(
            currency="USD",
            hedge_ratio=Decimal("0.85"),
            period_start=period_start,
            period_end=period_end,
            portfolio_return_eur=Decimal("5000"),
            hedge_return_eur=Decimal("-425"),
            combined_return_eur=Decimal("4575"),
        )

        hedging_engine.track_effectiveness(
            currency="GBP",
            hedge_ratio=Decimal("0.8"),
            period_start=period_start,
            period_end=period_end,
            portfolio_return_eur=Decimal("3000"),
            hedge_return_eur=Decimal("-240"),
            combined_return_eur=Decimal("2760"),
        )

        # Clear all
        hedging_engine.clear_effectiveness_history()

        assert len(hedging_engine.get_effectiveness_history("USD")) == 0
        assert len(hedging_engine.get_effectiveness_history("GBP")) == 0

    def test_select_instrument_default(self, hedging_engine):
        """Test instrument selection for currency without defaults."""
        instrument = hedging_engine._select_instrument(
            currency="CHF",  # Not in defaults
            amount_eur=Decimal("50000"),
            tenor_months=3,
        )

        assert instrument is not None
        assert instrument.type == HedgeInstrumentType.FORWARD

    def test_select_instrument_with_tenor(self, hedging_engine):
        """Test instrument selection with specific tenor."""
        instrument = hedging_engine._select_instrument(
            currency="USD",
            amount_eur=Decimal("50000"),
            tenor_months=6,
        )

        # Should select an instrument that supports 6-month tenor
        assert 6 in instrument.tenor_options

    def test_calculate_contracts_for_forward(self, hedging_engine):
        """Test contract calculation for forwards (non-exchange traded)."""
        instrument = HedgeInstrument(
            type=HedgeInstrumentType.FORWARD,
            currency_pair="EUR/USD",
            contract_size=Decimal("100000"),
            liquidity=100,
            typical_spread_bps=Decimal("2"),
            is_exchange_traded=False,
        )

        contracts = hedging_engine._calculate_contracts(
            instrument=instrument,
            amount_eur=Decimal("50000"),
        )

        # Forwards don't use contracts
        assert contracts is None

    def test_calculate_contracts_for_future(self, hedging_engine):
        """Test contract calculation for futures."""
        instrument = HedgeInstrument(
            type=HedgeInstrumentType.FUTURE,
            symbol="6E",
            currency_pair="EUR/USD",
            contract_size=Decimal("125000"),
            liquidity=95,
            typical_spread_bps=Decimal("1"),
            is_exchange_traded=True,
        )

        contracts = hedging_engine._calculate_contracts(
            instrument=instrument,
            amount_eur=Decimal("50000"),
        )

        # 50000 / 125000 = 0.4, should round up to 1
        assert contracts == 1

    def test_generate_roll_schedule(self, hedging_engine):
        """Test roll schedule generation."""
        # Monthly
        schedule_1m = hedging_engine._generate_roll_schedule(1)
        assert "monthly" in schedule_1m.lower()

        # Quarterly
        schedule_3m = hedging_engine._generate_roll_schedule(3)
        assert "quarterly" in schedule_3m.lower()

        # Semi-annual
        schedule_6m = hedging_engine._generate_roll_schedule(6)
        assert "semi" in schedule_6m.lower() or "annually" in schedule_6m.lower()

    def test_determine_priority(self, hedging_engine):
        """Test priority determination."""
        # Critical: large exposure, low hedge
        priority = hedging_engine._determine_priority(
            exposure_eur=Decimal("50000"),
            hedge_ratio=Decimal("0.3"),
        )
        assert priority == "critical"

        # High: medium exposure
        priority = hedging_engine._determine_priority(
            exposure_eur=Decimal("30000"),
            hedge_ratio=Decimal("0.8"),
        )
        assert priority == "high"

        # Low: small exposure
        priority = hedging_engine._determine_priority(
            exposure_eur=Decimal("5000"),
            hedge_ratio=Decimal("0.5"),
        )
        assert priority == "low"
