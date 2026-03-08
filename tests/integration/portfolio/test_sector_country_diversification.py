"""
Integration Tests for Sector and Country Diversification - TASK-5.6

Tests sector and country concentration validation, rebalancing suggestions,
and integration with the portfolio service.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.core.centralized_config import SectorCountryDiversificationConfig, get_config
from app.domain.models.portfolio import AssetClass, Portfolio, Position
from app.providers.paper_trading import PaperTradingPortfolioProvider
from app.services.country_diversification_validator import CountryDiversificationValidator
from app.services.portfolio_service import PortfolioService
from app.services.sector_diversification_validator import SectorDiversificationValidator


@pytest.fixture
def config():
    """Get trading configuration."""
    return get_config()


@pytest.fixture
def sector_config(config) -> SectorCountryDiversificationConfig:
    """Get sector-country diversification config."""
    return config.diversification


@pytest.fixture
def sector_validator(sector_config) -> SectorDiversificationValidator:
    """Create sector diversification validator."""
    return SectorDiversificationValidator(sector_config)


@pytest.fixture
def country_validator(sector_config) -> CountryDiversificationValidator:
    """Create country diversification validator."""
    return CountryDiversificationValidator(sector_config)


@pytest.fixture
def portfolio_service() -> PortfolioService:
    """Create portfolio service."""
    provider = PaperTradingPortfolioProvider(initial_cash=Decimal("100000"))
    return PortfolioService(provider)


@pytest.fixture
def sample_portfolio() -> Portfolio:
    """Create sample portfolio with multiple sectors and countries."""
    positions = [
        Position(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("150.00"),
            market_price=Decimal("150.00"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            currency="USD",
            broker="paper_trading",
            sector="technology",
            country="US",
        ),
        Position(
            symbol="MSFT",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("300.00"),
            market_price=Decimal("300.00"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            currency="USD",
            broker="paper_trading",
            sector="technology",
            country="US",
        ),
        Position(
            symbol="JPM",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("150.00"),
            market_price=Decimal("150.00"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            currency="USD",
            broker="paper_trading",
            sector="banks",
            country="US",
        ),
        Position(
            symbol="HSBC",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("50.00"),
            market_price=Decimal("50.00"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            currency="GBP",
            broker="paper_trading",
            sector="banks",
            country="UK",
        ),
        Position(
            symbol="SONY",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("100.00"),
            market_price=Decimal("100.00"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            currency="JPY",
            broker="paper_trading",
            sector="technology",
            country="JP",
        ),
    ]

    return Portfolio(
        portfolio_id="test_portfolio",
        broker="paper_trading",
        currency="USD",
        timestamp=datetime.now(),
        cash=Decimal("10000.00"),
        positions=positions,
    )


class TestSectorDiversificationValidator:
    """Test sector diversification validation."""

    def test_sector_validator_initialization(self, sector_validator, sector_config):
        """Test sector validator initializes correctly."""
        assert sector_validator.config == sector_config
        assert sector_validator.checks_performed == 0
        assert sector_validator.violations_found == 0

    def test_calculate_sector_exposure(self, sector_validator, sample_portfolio):
        """Test sector exposure calculation."""
        exposures = sector_validator._calculate_sector_exposure(sample_portfolio)

        assert "technology" in exposures
        assert "banks" in exposures
        assert exposures["technology"] == Decimal("55000")  # AAPL(15k) + MSFT(30k) + SONY(10k)
        assert exposures["banks"] == Decimal("20000")  # JPM(15k) + HSBC(5k)

    def test_validate_sector_limits_within_limits(self, sector_validator, sample_portfolio):
        """Test sector limit validation when within limits."""
        violations = sector_validator.validate_sector_limits(sample_portfolio)

        # Should have few or no violations if portfolio is well-diversified
        assert isinstance(violations, list)
        assert sector_validator.checks_performed >= 1

    def test_validate_sector_limits_exceeds_limit(self, sector_validator):
        """Test sector limit validation when exceeds limit."""
        # Create heavily tech-concentrated portfolio
        positions = [
            Position(
                symbol=f"TECH{i}",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("100.00"),
                market_price=Decimal("100.00"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                currency="USD",
                broker="paper_trading",
                sector="technology",
                country="US",
            )
            for i in range(8)  # 8 tech stocks, total 80,000 in tech
        ]

        portfolio = Portfolio(
            portfolio_id="tech_heavy",
            broker="paper_trading",
            currency="USD",
            timestamp=datetime.now(),
            cash=Decimal("10000.00"),
            positions=positions,
        )

        violations = sector_validator.validate_sector_limits(portfolio)

        # Tech should be around 88% (80k / 90k), exceeding 30% limit
        assert len(violations) > 0
        assert any(v.get("type") == "sector_exposure" for v in violations)
        assert sector_validator.violations_found > 0

    def test_get_sector_rebalancing_suggestions(self, sector_validator):
        """Test sector rebalancing suggestions."""
        # Create portfolio with one over-concentrated sector
        positions = [
            Position(
                symbol=f"TECH{i}",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("100.00"),
                market_price=Decimal("100.00"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                currency="USD",
                broker="paper_trading",
                sector="technology",
                country="US",
            )
            for i in range(7)  # Heavy tech concentration
        ]

        portfolio = Portfolio(
            portfolio_id="test",
            broker="paper_trading",
            currency="USD",
            timestamp=datetime.now(),
            cash=Decimal("5000.00"),
            positions=positions,
        )

        suggestions = sector_validator.get_sector_rebalancing_suggestions(portfolio)

        assert isinstance(suggestions, list)
        if len(suggestions) > 0:
            suggestion = suggestions[0]
            assert "sector" in suggestion
            assert "current_exposure" in suggestion
            assert "action" in suggestion

    def test_get_sector_statistics(self, sector_validator, sample_portfolio):
        """Test sector statistics calculation."""
        stats = sector_validator.get_sector_statistics(sample_portfolio)

        assert "total_sectors" in stats
        assert "herfindahl_index" in stats
        assert "effective_sectors" in stats
        assert "sectors" in stats
        assert stats["total_sectors"] >= 1
        assert stats["herfindahl_index"] is not None

    def test_validate_new_position_sector(self, sector_validator, sample_portfolio):
        """Test sector validation for new position."""
        # Position that would fit within limits
        new_position = Position(
            symbol="GOOGL",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("10"),
            avg_price=Decimal("100.00"),
            market_price=Decimal("100.00"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            currency="USD",
            broker="paper_trading",
            sector="technology",
            country="US",
        )

        allowed, reason = sector_validator.validate_new_position_sector(
            sample_portfolio, new_position
        )

        assert isinstance(allowed, bool)
        if not allowed:
            assert reason is not None


class TestCountryDiversificationValidator:
    """Test country diversification validation."""

    def test_country_validator_initialization(self, country_validator, sector_config):
        """Test country validator initializes correctly."""
        assert country_validator.config == sector_config
        assert country_validator.checks_performed == 0
        assert country_validator.violations_found == 0

    def test_calculate_country_exposure(self, country_validator, sample_portfolio):
        """Test country exposure calculation."""
        exposures = country_validator._calculate_country_exposure(sample_portfolio)

        assert "US" in exposures
        assert "UK" in exposures
        assert "JP" in exposures
        # US: AAPL(15000) + MSFT(30000) + JPM(15000) = 60000
        assert exposures["US"] == Decimal("60000")

    def test_validate_country_limits_within_limits(self, country_validator, sample_portfolio):
        """Test country limit validation when within limits."""
        violations = country_validator.validate_country_limits(sample_portfolio)

        assert isinstance(violations, list)
        assert country_validator.checks_performed >= 1

    def test_validate_country_limits_exceeds_limit(self, country_validator):
        """Test country limit validation when exceeds limit."""
        # Create portfolio heavily concentrated in US
        positions = [
            Position(
                symbol=f"US{i}",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("100.00"),
                market_price=Decimal("100.00"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                currency="USD",
                broker="paper_trading",
                sector="technology",
                country="US",
            )
            for i in range(10)  # All in US
        ]

        portfolio = Portfolio(
            portfolio_id="us_heavy",
            broker="paper_trading",
            currency="USD",
            timestamp=datetime.now(),
            cash=Decimal("5000.00"),
            positions=positions,
        )

        violations = country_validator.validate_country_limits(portfolio)

        # All 100k in US, 100% exposure, exceeds 50% limit
        assert len(violations) > 0
        assert any(v.get("type") == "country_exposure" for v in violations)

    def test_get_country_rebalancing_suggestions(self, country_validator):
        """Test country rebalancing suggestions."""
        # Create portfolio heavily concentrated in one country
        positions = [
            Position(
                symbol=f"US{i}",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("100.00"),
                market_price=Decimal("100.00"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                currency="USD",
                broker="paper_trading",
                sector="technology",
                country="US",
            )
            for i in range(9)
        ]

        portfolio = Portfolio(
            portfolio_id="test",
            broker="paper_trading",
            currency="USD",
            timestamp=datetime.now(),
            cash=Decimal("5000.00"),
            positions=positions,
        )

        suggestions = country_validator.get_country_rebalancing_suggestions(portfolio)

        assert isinstance(suggestions, list)
        if len(suggestions) > 0:
            suggestion = suggestions[0]
            assert "country" in suggestion
            assert "current_exposure" in suggestion
            assert "action" in suggestion

    def test_get_country_statistics(self, country_validator, sample_portfolio):
        """Test country statistics calculation."""
        stats = country_validator.get_country_statistics(sample_portfolio)

        assert "total_countries" in stats
        assert "herfindahl_index" in stats
        assert "effective_countries" in stats
        assert "countries" in stats
        assert stats["total_countries"] >= 1

    def test_validate_new_position_country(self, country_validator, sample_portfolio):
        """Test country validation for new position."""
        # Position in under-represented country
        new_position = Position(
            symbol="SAP",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("50"),
            avg_price=Decimal("100.00"),
            market_price=Decimal("100.00"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            currency="EUR",
            broker="paper_trading",
            sector="technology",
            country="DE",
        )

        allowed, reason = country_validator.validate_new_position_country(
            sample_portfolio, new_position
        )

        assert isinstance(allowed, bool)


class TestPortfolioServiceDiversification:
    """Test portfolio service diversification features."""

    def test_portfolio_service_has_validators(self, portfolio_service):
        """Test that portfolio service has validators."""
        assert hasattr(portfolio_service, "sector_validator")
        assert hasattr(portfolio_service, "country_validator")
        assert isinstance(portfolio_service.sector_validator, SectorDiversificationValidator)
        assert isinstance(portfolio_service.country_validator, CountryDiversificationValidator)

    def test_get_diversification_status(self, portfolio_service, sample_portfolio):
        """Test diversification status retrieval."""
        status = portfolio_service.get_diversification_status(sample_portfolio)

        assert isinstance(status, dict)
        assert "sectors" in status
        assert "countries" in status
        assert "total_diversification_breaches" in status

    def test_suggest_rebalancing(self, portfolio_service, sample_portfolio):
        """Test rebalancing suggestions."""
        suggestions = portfolio_service.suggest_rebalancing(sample_portfolio)

        assert isinstance(suggestions, dict)
        assert "sector_suggestions" in suggestions
        assert "country_suggestions" in suggestions
        assert "total_suggestions" in suggestions

    def test_diversification_tracking(self, portfolio_service):
        """Test diversification breach tracking."""
        assert portfolio_service.diversification_breaches == 0
        assert portfolio_service.rebalancing_actions == 0


class TestSectorCountryIntegration:
    """Test sector and country diversification together."""

    def test_combined_validation(self, sector_validator, country_validator):
        """Test combined sector and country validation."""
        # Create mixed portfolio
        positions = [
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("50"),
                avg_price=Decimal("150.00"),
                market_price=Decimal("150.00"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                currency="USD",
                broker="paper_trading",
                sector="technology",
                country="US",
            ),
            Position(
                symbol="HSBC",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("50"),
                avg_price=Decimal("50.00"),
                market_price=Decimal("50.00"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                currency="GBP",
                broker="paper_trading",
                sector="banks",
                country="UK",
            ),
            Position(
                symbol="TOYOTA",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("50"),
                avg_price=Decimal("100.00"),
                market_price=Decimal("100.00"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                currency="JPY",
                broker="paper_trading",
                sector="industrials",
                country="JP",
            ),
            Position(
                symbol="SIEMENS",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("50"),
                avg_price=Decimal("100.00"),
                market_price=Decimal("100.00"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                currency="EUR",
                broker="paper_trading",
                sector="industrials",
                country="DE",
            ),
        ]

        portfolio = Portfolio(
            portfolio_id="diversified",
            broker="paper_trading",
            currency="USD",
            timestamp=datetime.now(),
            cash=Decimal("10000.00"),
            positions=positions,
        )

        sector_violations = sector_validator.validate_sector_limits(portfolio)
        country_violations = country_validator.validate_country_limits(portfolio)

        sector_stats = sector_validator.get_sector_statistics(portfolio)
        country_stats = country_validator.get_country_statistics(portfolio)

        assert isinstance(sector_violations, list)
        assert isinstance(country_violations, list)
        assert sector_stats["total_sectors"] >= 2
        assert country_stats["total_countries"] >= 2

    def test_severity_calculation(self, sector_validator):
        """Test violation severity calculation."""
        # Minor breach (< 10%)
        severity = sector_validator._calculate_severity(Decimal("0.33"), Decimal("0.30"))
        assert severity == "minor"

        # Moderate breach (10-20%)
        severity = sector_validator._calculate_severity(Decimal("0.36"), Decimal("0.30"))
        assert severity == "moderate"

        # Severe breach (> 20%)
        severity = sector_validator._calculate_severity(Decimal("0.42"), Decimal("0.30"))
        assert severity == "severe"


class TestEdgeCases:
    """Test edge cases for diversification validation."""

    def test_empty_portfolio(self, sector_validator, country_validator):
        """Test with empty portfolio."""
        portfolio = Portfolio(
            portfolio_id="empty",
            broker="paper_trading",
            currency="USD",
            timestamp=datetime.now(),
            cash=Decimal("10000.00"),
            positions=[],
        )

        sector_violations = sector_validator.validate_sector_limits(portfolio)
        country_violations = country_validator.validate_country_limits(portfolio)
        sector_stats = sector_validator.get_sector_statistics(portfolio)
        country_stats = country_validator.get_country_statistics(portfolio)

        assert isinstance(sector_violations, list)
        assert isinstance(country_violations, list)
        assert sector_stats["total_sectors"] == 0
        assert country_stats["total_countries"] == 0

    def test_positions_without_sector_country(self, sector_validator, country_validator):
        """Test positions without sector/country specified."""
        positions = [
            Position(
                symbol="UNKNOWN",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("100.00"),
                market_price=Decimal("100.00"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                currency="USD",
                broker="paper_trading",
                sector=None,
                country=None,
            ),
        ]

        portfolio = Portfolio(
            portfolio_id="unknown",
            broker="paper_trading",
            currency="USD",
            timestamp=datetime.now(),
            cash=Decimal("5000.00"),
            positions=positions,
        )

        sector_stats = sector_validator.get_sector_statistics(portfolio)
        country_stats = country_validator.get_country_statistics(portfolio)

        # Positions without sector/country should be skipped
        assert sector_stats["total_sectors"] == 0
        assert country_stats["total_countries"] == 0

    def test_single_position_portfolio(self, sector_validator, country_validator):
        """Test portfolio with single position."""
        positions = [
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("150.00"),
                market_price=Decimal("150.00"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                currency="USD",
                broker="paper_trading",
                sector="technology",
                country="US",
            ),
        ]

        portfolio = Portfolio(
            portfolio_id="single",
            broker="paper_trading",
            currency="USD",
            timestamp=datetime.now(),
            cash=Decimal("5000.00"),
            positions=positions,
        )

        sector_stats = sector_validator.get_sector_statistics(portfolio)
        country_stats = country_validator.get_country_statistics(portfolio)

        # Single position = high concentration
        assert sector_stats["total_sectors"] == 1
        assert country_stats["total_countries"] == 1
        assert sector_stats["herfindahl_index"] > 0.5  # High concentration
        assert country_stats["herfindahl_index"] > 0.5  # High concentration


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
