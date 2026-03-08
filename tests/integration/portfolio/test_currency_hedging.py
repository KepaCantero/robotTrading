"""
Integration Tests: Currency Hedging [TASK-5.5-CURRENCY-HEDGING]

Tests para:
- ForexDataFetcher (rates, correlations, spreads)
- CurrencyHedgingEngine (exposure calculation, recommendations)
- Risk manager FX violation detection
- Portfolio service hedging integration
"""

import logging
from decimal import Decimal

import pytest

from app.domain.models.portfolio import AssetClass, HedgingMetadata, Portfolio, Position
from app.services.currency_hedging_engine import (
    CurrencyHedgingEngine,
    HedgeRecommendation,
    HedgeUrgency,
)
from app.services.forex_data_service import ForexDataFetcher, reset_forex_fetcher
from app.services.portfolio_risk_manager import PortfolioRiskManager, RiskViolation
from app.services.portfolio_service import PortfolioService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestForexDataFetcher:
    """Tests para ForexDataFetcher."""

    def setup_method(self):
        """Reset forex fetcher before each test."""
        reset_forex_fetcher()

    def test_get_available_pairs(self):
        """Test obtener pares disponibles."""
        fetcher = ForexDataFetcher()
        pairs = fetcher.get_available_pairs()

        assert isinstance(pairs, dict)
        assert "EUR" in pairs
        assert "GBP" in pairs
        assert pairs["EUR"] == "EUR/USD"
        logger.info(f"Available pairs: {len(pairs)}")

    def test_get_correlations_defaults(self):
        """Test obtener correlaciones (returns defaults)."""
        fetcher = ForexDataFetcher()
        corr = fetcher.get_correlations("USD")

        assert isinstance(corr, dict)
        assert "EUR" in corr
        assert isinstance(corr["EUR"], Decimal)
        assert Decimal("0") <= corr["EUR"] <= Decimal("1")
        logger.info(f"Correlation EUR/USD: {corr['EUR']}")

    def test_get_current_rates_fallback(self):
        """Test obtener tasas (fallback a valores por defecto)."""
        fetcher = ForexDataFetcher()
        rates = fetcher.get_current_rates(["EUR/USD", "GBP/USD"])

        assert isinstance(rates, dict)
        assert "EUR/USD" in rates
        assert isinstance(rates["EUR/USD"], Decimal)
        logger.info(f"EUR/USD rate: {rates['EUR/USD']}")

    def test_get_bid_ask_spread(self):
        """Test obtener spread bid-ask."""
        fetcher = ForexDataFetcher()
        spread = fetcher.get_bid_ask_spread("EUR/USD")

        assert isinstance(spread, Decimal)
        assert spread > Decimal("0")
        assert spread <= Decimal("10")  # Reasonable max spread
        logger.info(f"EUR/USD spread: {spread} bps")

    def test_invalidate_cache(self):
        """Test invalidar cache."""
        fetcher = ForexDataFetcher()
        # Get some data
        fetcher.get_correlations("USD")
        assert fetcher.correlation_cache is not None

        # Invalidate
        fetcher.invalidate_cache("correlations")
        assert fetcher.correlation_cache is None
        logger.info("Cache invalidated successfully")


class TestCurrencyHedgingEngine:
    """Tests para CurrencyHedgingEngine."""

    @pytest.fixture
    def engine(self):
        """Create hedging engine instance."""
        return CurrencyHedgingEngine()

    @pytest.fixture
    def portfolio_multi_currency(self):
        """Create portfolio with multiple currencies."""
        portfolio = Portfolio(
            portfolio_id="test_portfolio",
            cash=Decimal("100000"),
            broker="TEST",
            currency="USD",
        )

        # USD position (base currency - should be ignored)
        portfolio.positions.append(
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("150"),
                market_price=Decimal("155"),
                unrealized_pnl=Decimal("500"),
                currency="USD",
                broker="TEST",
            )
        )

        # EUR position
        portfolio.positions.append(
            Position(
                symbol="SAP",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("50"),
                avg_price=Decimal("100"),
                market_price=Decimal("105"),
                unrealized_pnl=Decimal("250"),
                currency="EUR",
                broker="TEST",
            )
        )

        # GBP position
        portfolio.positions.append(
            Position(
                symbol="HSBC",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("80"),
                market_price=Decimal("85"),
                unrealized_pnl=Decimal("500"),
                currency="GBP",
                broker="TEST",
            )
        )

        return portfolio

    def test_calculate_currency_exposure(self, engine, portfolio_multi_currency):
        """Test calcular exposición por moneda."""
        exposure = engine.calculate_currency_exposure(portfolio_multi_currency)

        assert isinstance(exposure, dict)
        assert "EUR" in exposure
        assert "GBP" in exposure
        assert "USD" not in exposure  # Base currency ignored
        assert exposure["EUR"] == Decimal("5250")  # 50 * 105
        assert exposure["GBP"] == Decimal("8500")  # 100 * 85
        logger.info(f"Currency exposure: {exposure}")

    def test_calculate_hedge_recommendations(self, engine, portfolio_multi_currency):
        """Test generar recomendaciones de cobertura."""
        recommendations = engine.calculate_hedge_recommendations(portfolio_multi_currency)

        assert isinstance(recommendations, list)
        assert all(isinstance(r, HedgeRecommendation) for r in recommendations)
        assert all(r.hedge_ratio > Decimal("0") for r in recommendations)
        assert all(r.estimated_cost_bps >= Decimal("0") for r in recommendations)

        logger.info(f"Recommendations: {len(recommendations)}")
        for rec in recommendations:
            logger.info(
                f"  {rec.currency}: ratio={rec.hedge_ratio}, cost={rec.estimated_cost_bps} bps"
            )

    def test_hedge_ratio_calculation(self, engine):
        """Test calcular ratio de cobertura."""
        # High exposure, high correlation = lower ratio needed
        ratio = engine._calculate_hedge_ratio(
            exposure_pct=Decimal("0.3"),
            correlation=Decimal("0.9"),
            urgency=HedgeUrgency.NORMAL,
        )

        assert Decimal("0") <= ratio <= Decimal("1")
        logger.info(f"Hedge ratio (high corr): {ratio}")

        # Low correlation = higher ratio needed
        ratio_low = engine._calculate_hedge_ratio(
            exposure_pct=Decimal("0.3"),
            correlation=Decimal("0.3"),
            urgency=HedgeUrgency.NORMAL,
        )

        assert ratio_low > ratio  # Lower correlation = higher hedge needed
        logger.info(f"Hedge ratio (low corr): {ratio_low}")

    def test_hedge_cost_estimation(self, engine):
        """Test estimar costo de cobertura."""
        cost = engine._estimate_hedge_cost("EUR/USD", Decimal("100000"))

        assert isinstance(cost, Decimal)
        assert cost > Decimal("0")
        assert cost <= Decimal("100")  # Capped at 100 bps
        logger.info(f"Hedge cost: {cost} bps")

    def test_statistics(self, engine, portfolio_multi_currency):
        """Test estadísticas del motor."""
        # Generate some recommendations
        engine.calculate_hedge_recommendations(portfolio_multi_currency)

        stats = engine.get_statistics()
        assert isinstance(stats, dict)
        assert "total_recommendations_generated" in stats
        logger.info(f"Stats: {stats}")


class TestRiskManagerFXViolations:
    """Tests para detección de violaciones FX en RiskManager."""

    @pytest.fixture
    def risk_manager(self):
        """Create risk manager."""
        return PortfolioRiskManager()

    @pytest.fixture
    def portfolio_high_fx(self):
        """Create portfolio with high FX exposure."""
        portfolio = Portfolio(
            portfolio_id="high_fx",
            cash=Decimal("50000"),
            broker="TEST",
            currency="USD",
        )

        # 60% EUR exposure (triggers violation)
        for i in range(10):
            portfolio.positions.append(
                Position(
                    symbol=f"EUR_STOCK_{i}",
                    asset_class=AssetClass.EQUITY,
                    quantity=Decimal("100"),
                    avg_price=Decimal("100"),
                    market_price=Decimal("100"),
                    unrealized_pnl=Decimal("0"),
                    currency="EUR",
                    broker="TEST",
                )
            )

        return portfolio

    def test_currency_exposure_calculation(self, risk_manager, portfolio_high_fx):
        """Test calcular exposición de moneda en risk manager."""
        exposure = risk_manager._calculate_currency_exposure(portfolio_high_fx, None)

        assert "by_currency" in exposure
        assert "total_unhedged" in exposure
        assert "total_portfolio_pct" in exposure
        assert exposure["by_currency"]["EUR"] > Decimal("0")
        logger.info(f"FX exposure: {exposure}")

    def test_fx_violation_detection(self, risk_manager, portfolio_high_fx):
        """Test detectar violaciones FX."""
        exposure = risk_manager._calculate_currency_exposure(portfolio_high_fx, None)
        violations = risk_manager._detect_fx_violations(exposure)

        assert isinstance(violations, list)
        # Should have some FX violations
        assert any(
            v["type"]
            in [
                RiskViolation.UNHEDGED_FX_EXPOSURE,
                RiskViolation.EXCESSIVE_FX_CONCENTRATION,
            ]
            for v in violations
        )
        logger.info(f"FX violations: {len(violations)}")

    def test_full_risk_assessment_with_fx(self, risk_manager, portfolio_high_fx):
        """Test evaluación de riesgo completa con FX."""
        assessment = risk_manager.assess_portfolio_risk(portfolio_high_fx)

        assert "currency_exposures" in assessment["risk_metrics"]
        assert "violations" in assessment

        # Should have FX-related violations
        fx_violations = [
            v
            for v in assessment["violations"]
            if v["type"]
            in [
                RiskViolation.UNHEDGED_FX_EXPOSURE,
                RiskViolation.EXCESSIVE_FX_CONCENTRATION,
            ]
        ]
        assert len(fx_violations) > 0
        logger.info(f"Risk assessment FX violations: {len(fx_violations)}")


class TestPortfolioServiceHedging:
    """Tests para integración de hedging en PortfolioService."""

    @pytest.fixture
    def portfolio_provider_mock(self):
        """Mock portfolio provider."""
        from unittest.mock import AsyncMock, MagicMock

        provider = MagicMock()
        provider.get_portfolio = AsyncMock(
            return_value=Portfolio(
                portfolio_id="test",
                cash=Decimal("100000"),
                broker="TEST",
                currency="USD",
                positions=[
                    Position(
                        symbol="SAP",
                        asset_class=AssetClass.EQUITY,
                        quantity=Decimal("50"),
                        avg_price=Decimal("100"),
                        market_price=Decimal("105"),
                        unrealized_pnl=Decimal("250"),
                        currency="EUR",
                        broker="TEST",
                    )
                ],
            )
        )
        return provider

    def test_hedging_statistics(self, portfolio_provider_mock):
        """Test obtener estadísticas de hedging."""
        service = PortfolioService(portfolio_provider_mock)

        stats = service.get_hedging_statistics()
        assert isinstance(stats, dict)
        assert "total_hedges_created" in stats
        assert "total_hedge_cost_bps" in stats
        logger.info(f"Hedging stats: {stats}")

    @pytest.mark.asyncio
    async def test_apply_auto_hedging(self, portfolio_provider_mock):
        """Test aplicar auto-hedging."""
        service = PortfolioService(portfolio_provider_mock)
        portfolio = await service.get_portfolio()

        result = await service.apply_auto_hedging(portfolio)

        assert isinstance(result, dict)
        assert "success" in result
        assert "recommendations_count" in result
        logger.info(f"Auto-hedging result: {result}")


class TestHedgingMetadata:
    """Tests para HedgingMetadata model."""

    def test_hedging_metadata_creation(self):
        """Test crear HedgingMetadata."""
        metadata = HedgingMetadata(
            is_hedge=True,
            base_position_id="pos_123",
            hedge_ratio=Decimal("0.5"),
            hedge_currency_pair="EUR/USD",
            hedge_cost_bps=Decimal("5"),
        )

        assert metadata.is_hedge is True
        assert metadata.base_position_id == "pos_123"
        assert metadata.hedge_ratio == Decimal("0.5")
        assert metadata.hedge_currency_pair == "EUR/USD"
        logger.info(f"HedgingMetadata: {metadata}")

    def test_hedging_metadata_validation(self):
        """Test validación de HedgingMetadata."""
        # Invalid hedge ratio > 1
        with pytest.raises(ValueError):
            HedgingMetadata(
                is_hedge=True,
                hedge_ratio=Decimal("1.5"),  # Invalid
            )

        # Invalid cost > 1000 bps
        with pytest.raises(ValueError):
            HedgingMetadata(
                is_hedge=True,
                hedge_cost_bps=Decimal("2000"),  # Invalid
            )

        logger.info("HedgingMetadata validation tests passed")

    def test_position_with_hedging(self):
        """Test Position con hedging metadata."""
        position = Position(
            symbol="SAP",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("50"),
            avg_price=Decimal("100"),
            market_price=Decimal("105"),
            unrealized_pnl=Decimal("250"),
            currency="EUR",
            broker="TEST",
            hedging=HedgingMetadata(
                is_hedge=False,
                hedge_ratio=Decimal("0.5"),
            ),
        )

        assert position.hedging.is_hedge is False
        assert position.hedging.hedge_ratio == Decimal("0.5")
        logger.info(
            f"Position with hedging: {position.symbol} (hedge_ratio={position.hedging.hedge_ratio})"
        )
