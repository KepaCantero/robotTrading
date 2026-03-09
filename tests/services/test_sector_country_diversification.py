"""
Unit tests for Sector and Country Diversification Validators
TASK-5.6-SECTOR-COUNTRY-DIVERSIFICATION - PHASE 3: Portfolio and Risk
"""

from decimal import Decimal

import pytest

from app.shared.config.centralized_config import SectorCountryDiversificationConfig
from app.domain.models.portfolio import AssetClass, HedgingMetadata, Portfolio, Position
from app.services.country_diversification_validator import CountryDiversificationValidator
from app.services.sector_diversification_validator import SectorDiversificationValidator


@pytest.fixture
def diversification_config():
    """Create test configuration for diversification."""
    return SectorCountryDiversificationConfig(
        enabled=True,
        enforcement_mode="soft",
        max_single_sector=0.30,
        max_total_sector_concentration=0.70,
        minimum_sector_count=3,
        max_single_country=0.50,
        max_region_concentration=0.80,
        minimum_country_count=2,
    )


@pytest.fixture
def sector_validator(diversification_config):
    """Create sector diversification validator."""
    return SectorDiversificationValidator(diversification_config)


@pytest.fixture
def country_validator(diversification_config):
    """Create country diversification validator."""
    return CountryDiversificationValidator(diversification_config)


@pytest.fixture
def position_aapl():
    """Create AAPL position (Technology, USA)."""
    return Position(
        symbol="AAPL",
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("100"),
        avg_price=Decimal("150"),
        market_price=Decimal("150"),
        unrealized_pnl=Decimal("0"),
        realized_pnl=Decimal("0"),
        currency="USD",
        broker="paper_trading",
        sector="technology",
        country="USA",
    )


@pytest.fixture
def position_msft():
    """Create MSFT position (Technology, USA)."""
    return Position(
        symbol="MSFT",
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("100"),
        avg_price=Decimal("300"),
        market_price=Decimal("300"),
        unrealized_pnl=Decimal("0"),
        realized_pnl=Decimal("0"),
        currency="USD",
        broker="paper_trading",
        sector="technology",
        country="USA",
    )


@pytest.fixture
def position_jpm():
    """Create JPM position (Banking, USA)."""
    return Position(
        symbol="JPM",
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("100"),
        avg_price=Decimal("150"),
        market_price=Decimal("150"),
        unrealized_pnl=Decimal("0"),
        realized_pnl=Decimal("0"),
        currency="USD",
        broker="paper_trading",
        sector="banking",
        country="USA",
    )


@pytest.fixture
def position_asml():
    """Create ASML position (Technology, Netherlands)."""
    return Position(
        symbol="ASML",
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("50"),
        avg_price=Decimal("600"),
        market_price=Decimal("600"),
        unrealized_pnl=Decimal("0"),
        realized_pnl=Decimal("0"),
        currency="EUR",
        broker="paper_trading",
        sector="technology",
        country="Netherlands",
    )


@pytest.fixture
def position_nestle():
    """Create Nestle position (Consumer Staples, Switzerland)."""
    return Position(
        symbol="NSRGY",
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("100"),
        avg_price=Decimal("120"),
        market_price=Decimal("120"),
        unrealized_pnl=Decimal("0"),
        realized_pnl=Decimal("0"),
        currency="CHF",
        broker="paper_trading",
        sector="consumer_staples",
        country="Switzerland",
    )


class TestSectorDiversificationValidator:
    """Test suite for SectorDiversificationValidator."""

    def test_initialization(self, sector_validator, diversification_config):
        """Test validator initialization."""
        assert sector_validator.config == diversification_config
        assert sector_validator.checks_performed == 0
        assert sector_validator.violations_found == 0

    def test_well_diversified_portfolio(
        self, sector_validator, position_aapl, position_jpm, position_nestle
    ):
        """Test portfolio with good sector diversification."""
        # Total positions: 15000 + 15000 + 12000 = 42000
        # For 30% limit: need total >= 50000, so cash = 8000
        portfolio = Portfolio(
            portfolio_id="test_001",
            cash=Decimal("8000"),
            positions=[position_aapl, position_jpm, position_nestle],
            broker="paper_trading",
            currency="USD",
        )

        violations = sector_validator.validate_sector_limits(portfolio)
        assert len(violations) == 0

    def test_sector_concentration_violation(self, sector_validator, position_aapl, position_msft):
        """Test detection of sector concentration (both tech)."""
        portfolio = Portfolio(
            portfolio_id="test_002",
            cash=Decimal("10000"),
            positions=[position_aapl, position_msft],
            broker="paper_trading",
            currency="USD",
        )

        violations = sector_validator.validate_sector_limits(portfolio)
        # Both are technology, should have violations
        sector_violations = [v for v in violations if v["type"] == "sector_exposure"]
        assert len(sector_violations) > 0

    def test_get_sector_statistics(
        self, sector_validator, position_aapl, position_jpm, position_nestle
    ):
        """Test calculation of sector statistics."""
        portfolio = Portfolio(
            portfolio_id="test_003",
            cash=Decimal("8000"),
            positions=[position_aapl, position_jpm, position_nestle],
            broker="paper_trading",
            currency="USD",
        )

        stats = sector_validator.get_sector_statistics(portfolio)

        assert stats["total_sectors"] == 3
        assert "herfindahl_index" in stats
        assert "effective_sectors" in stats

    def test_position_with_no_sector(self, sector_validator, position_aapl):
        """Test handling of positions without sector."""
        pos_no_sector = Position(
            symbol="TEST",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("100"),
            market_price=Decimal("100"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            currency="USD",
            broker="paper_trading",
            sector=None,
            country="USA",
        )

        portfolio = Portfolio(
            portfolio_id="test_004",
            cash=Decimal("5000"),
            positions=[position_aapl, pos_no_sector],
            broker="paper_trading",
            currency="USD",
        )

        stats = sector_validator.get_sector_statistics(portfolio)
        assert stats["total_sectors"] == 1

    def test_hedge_positions_excluded(self, sector_validator, position_aapl):
        """Test that hedge positions are excluded."""
        hedge_position = Position(
            symbol="HEDGE",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("-100"),
            avg_price=Decimal("150"),
            market_price=Decimal("150"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            currency="USD",
            broker="paper_trading",
            sector="technology",
            country="USA",
            hedging=HedgingMetadata(is_hedge=True, base_position_id="AAPL"),
        )

        portfolio = Portfolio(
            portfolio_id="test_005",
            cash=Decimal("10000"),
            positions=[position_aapl, hedge_position],
            broker="paper_trading",
            currency="USD",
        )

        stats = sector_validator.get_sector_statistics(portfolio)
        assert stats["total_sectors"] == 1


class TestCountryDiversificationValidator:
    """Test suite for CountryDiversificationValidator."""

    def test_initialization(self, country_validator, diversification_config):
        """Test validator initialization."""
        assert country_validator.config == diversification_config
        assert country_validator.checks_performed == 0
        assert country_validator.violations_found == 0

    def test_well_diversified_countries(
        self, country_validator, position_aapl, position_asml, position_nestle
    ):
        """Test portfolio with good country diversification."""
        portfolio = Portfolio(
            portfolio_id="test_006",
            cash=Decimal("5000"),
            positions=[position_aapl, position_asml, position_nestle],
            broker="paper_trading",
            currency="USD",
        )

        violations = country_validator.validate_country_limits(portfolio)
        assert len(violations) == 0

    def test_country_concentration_violation(self, country_validator, position_aapl, position_jpm):
        """Test detection of country concentration (both USA)."""
        portfolio = Portfolio(
            portfolio_id="test_007",
            cash=Decimal("10000"),
            positions=[position_aapl, position_jpm],
            broker="paper_trading",
            currency="USD",
        )

        violations = country_validator.validate_country_limits(portfolio)
        # Both USA, should have insufficient country count violations
        concentration_violations = [v for v in violations if v["type"] == "country_concentration"]
        assert len(concentration_violations) > 0

    def test_get_country_statistics(
        self, country_validator, position_aapl, position_asml, position_nestle
    ):
        """Test calculation of country statistics."""
        portfolio = Portfolio(
            portfolio_id="test_008",
            cash=Decimal("5000"),
            positions=[position_aapl, position_asml, position_nestle],
            broker="paper_trading",
            currency="USD",
        )

        stats = country_validator.get_country_statistics(portfolio)

        assert stats["total_countries"] == 3
        assert "herfindahl_index" in stats
        assert "effective_countries" in stats

    def test_position_with_no_country(self, country_validator, position_aapl):
        """Test handling of positions without country."""
        pos_no_country = Position(
            symbol="TEST",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("100"),
            market_price=Decimal("100"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            currency="USD",
            broker="paper_trading",
            sector="technology",
            country=None,
        )

        portfolio = Portfolio(
            portfolio_id="test_009",
            cash=Decimal("5000"),
            positions=[position_aapl, pos_no_country],
            broker="paper_trading",
            currency="USD",
        )

        stats = country_validator.get_country_statistics(portfolio)
        assert stats["total_countries"] == 1

    def test_hedge_positions_excluded(self, country_validator, position_aapl):
        """Test that hedge positions are excluded."""
        hedge_position = Position(
            symbol="HEDGE",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("-100"),
            avg_price=Decimal("150"),
            market_price=Decimal("150"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            currency="USD",
            broker="paper_trading",
            sector="technology",
            country="USA",
            hedging=HedgingMetadata(is_hedge=True, base_position_id="AAPL"),
        )

        portfolio = Portfolio(
            portfolio_id="test_010",
            cash=Decimal("10000"),
            positions=[position_aapl, hedge_position],
            broker="paper_trading",
            currency="USD",
        )

        stats = country_validator.get_country_statistics(portfolio)
        assert stats["total_countries"] == 1


class TestDiversificationIntegration:
    """Integration tests for sector and country diversification."""

    def test_combined_diversification_check(
        self,
        sector_validator,
        country_validator,
        position_aapl,
        position_jpm,
        position_asml,
        position_nestle,
    ):
        """Test combined sector and country validation."""
        # Total: AAPL(15000) + JPM(15000) + ASML(30000) + Nestle(12000) = 72000
        # Tech: 45000/total, need < 30% → 45000/x < 0.30 → x > 150000
        # So need cash = 150000 - 72000 = 78000
        portfolio = Portfolio(
            portfolio_id="test_011",
            cash=Decimal("78000"),
            positions=[position_aapl, position_jpm, position_asml, position_nestle],
            broker="paper_trading",
            currency="USD",
        )

        sector_violations = sector_validator.validate_sector_limits(portfolio)
        country_violations = country_validator.validate_country_limits(portfolio)

        assert len(sector_violations) == 0
        assert len(country_violations) == 0

    def test_diversification_metrics_comparison(
        self,
        sector_validator,
        country_validator,
        position_aapl,
        position_jpm,
        position_asml,
        position_nestle,
    ):
        """Compare diversification metrics between sector and country."""
        # Same allocation as test_combined_diversification_check
        portfolio = Portfolio(
            portfolio_id="test_012",
            cash=Decimal("78000"),
            positions=[position_aapl, position_jpm, position_asml, position_nestle],
            broker="paper_trading",
            currency="USD",
        )

        sector_stats = sector_validator.get_sector_statistics(portfolio)
        country_stats = country_validator.get_country_statistics(portfolio)

        # Both should have good diversification
        assert sector_stats["effective_sectors"] > 1
        assert country_stats["effective_countries"] > 1
        assert sector_stats["diversification_ratio"] > 0.3
        assert country_stats["diversification_ratio"] > 0.3
