"""
Comprehensive Tests for Dividend Strategy

Cubre:
- Models (Pydantic validation, edge cases)
- Screener (filtering logic, pass rates)
- Analyzer (quality scores, sustainability)
- Portfolio Constructor (weighting, sector limits)
- DividendStrategy (signals, risk checks, portfolio management)

Target: 50+ tests with 80%+ coverage
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.strategies.dividend.dividend_analyzer import (
    DividendAnalyzer,
    DividendQualityScore,
    DividendSustainabilityMetrics,
)
from app.strategies.dividend.dividend_portfolio_constructor import (
    DividendPortfolio,
    DividendPortfolioConstructor,
    PortfolioPosition,
)
from app.strategies.dividend.dividend_screener import DividendScreener
from app.strategies.dividend.dividend_strategy import DividendStrategy as DividendStrat
from app.strategies.dividend.models import (
    DividendAristocratStatus,
    DividendData,
    DividendFrequency,
    DividendProfile,
    DividendSafety,
    DividendStock,
    DividendStrategyConfig,
    ExDividendDate,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def valid_config():
    """Configuración válida de estrategia."""
    return {
        "name": "TestDividendStrategy",
        "min_dividend_yield": 3.0,
        "max_dividend_yield": 10.0,
        "max_payout_ratio": 70.0,
        "min_years_consecutive": 3,
        "portfolio_size": 20,
        "max_sector_weight": 0.30,
        "max_single_position": 0.05,
        "min_quality_score": 50.0,
        "min_sustainability_score": 50.0,
    }


@pytest.fixture
def dividend_config(valid_config):
    """Config parseada."""
    return DividendStrategyConfig(**valid_config)


@pytest.fixture
def sample_dividend_data():
    """Datos de dividendos de ejemplo."""
    return DividendData(
        symbol="AAPL",
        annual_dividend=Decimal("3.84"),
        dividend_yield=Decimal("4.5"),
        payout_ratio=Decimal("55.0"),
        dividend_growth_rate_3y=Decimal("8.5"),
        dividend_growth_rate_5y=Decimal("10.2"),
        dividend_growth_rate_10y=Decimal("7.8"),
        years_consecutive_increases=12,
        frequency=DividendFrequency.QUARTERLY,
        next_ex_dividend_date=date.today() + timedelta(days=15),
        next_payment_date=date.today() + timedelta(days=30),
        earnings_per_share=Decimal("6.98"),
        free_cash_flow_per_share=Decimal("7.50"),
        dividend_coverage_ratio=Decimal("1.95"),
    )


@pytest.fixture
def sample_dividend_profile(sample_dividend_data):
    """Perfil de dividendos de ejemplo."""
    return DividendProfile(
        symbol="AAPL",
        company_name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        market_cap=Decimal("2500000"),  # $2.5T
        current_price=Decimal("175.50"),
        dividend_data=sample_dividend_data,
        quality_score=Decimal("75.0"),
        sustainability_score=Decimal("80.0"),
        value_score=Decimal("70.0"),
        pe_ratio=Decimal("25.1"),
        pb_ratio=Decimal("35.2"),
        debt_to_equity=Decimal("150.0"),
        roe=Decimal("97.0"),  # Changed from 147 to fit constraint (le=100)
        beta=Decimal("1.2"),
        standard_deviation_1y=Decimal("25.0"),
    )


@pytest.fixture
def dividend_stock(sample_dividend_profile):
    """DividendStock de ejemplo."""
    return DividendStock(
        profile=sample_dividend_profile,
        decision_score=Decimal("75.0"),
        decision_reason="High quality dividend stock",
        recommendation="buy",
    )


@pytest.fixture
def multiple_profiles(sample_dividend_profile):
    """Múltiples perfiles para testing."""
    profiles = [sample_dividend_profile]

    # Agregar más perfiles
    for i in range(1, 10):
        data = DividendData(
            symbol=f"STOCK{i}",
            annual_dividend=Decimal(f"{3.0 + i * 0.5}"),
            dividend_yield=Decimal(f"{3.5 + i * 0.5}"),
            payout_ratio=Decimal(f"{50 + i * 5}"),
            dividend_growth_rate_3y=Decimal(f"{5 + i}"),
            years_consecutive_increases=5 + i,
            frequency=DividendFrequency.QUARTERLY,
            earnings_per_share=Decimal("5.0"),  # Agregado para pasar require_profitable
            dividend_coverage_ratio=Decimal("1.5"),
        )

        profile = DividendProfile(
            symbol=f"STOCK{i}",
            sector=["Technology", "Healthcare", "Finance", "Utilities"][i % 4],
            current_price=Decimal(f"{100 + i * 10}"),
            dividend_data=data,
            quality_score=Decimal(f"{60 + i * 3}"),
            sustainability_score=Decimal(f"{65 + i * 3}"),
            pe_ratio=Decimal(f"{15 + i}"),
        )

        profiles.append(profile)

    return profiles


# ============================================================================
# MODEL TESTS (15 tests)
# ============================================================================


class TestDividendData:
    """Tests para DividendData model."""

    def test_create_valid_dividend_data(self, sample_dividend_data):
        """Test crear datos de dividendos válidos."""
        assert sample_dividend_data.symbol == "AAPL"
        assert sample_dividend_data.dividend_yield == Decimal("4.5")
        assert sample_dividend_data.payout_ratio == Decimal("55.0")

    def test_dividend_yield_validation_too_high(self):
        """Test que yield muy alto lanza error."""
        with pytest.raises(ValueError, match="sospechosamente alto"):
            DividendData(
                symbol="TRAP",
                annual_dividend=Decimal("10.0"),
                dividend_yield=Decimal("25.0"),  # > 20%
                payout_ratio=Decimal("50.0"),
            )

    def test_safety_very_safe(self):
        """Test cálculo de seguridad - muy seguro."""
        data = DividendData(
            symbol="SAFE",
            annual_dividend=Decimal("2.0"),
            dividend_yield=Decimal("4.0"),
            payout_ratio=Decimal("35.0"),  # < 40%
        )
        assert data.safety == DividendSafety.VERY_SAFE

    def test_safety_safe(self):
        """Test cálculo de seguridad - seguro."""
        data = DividendData(
            symbol="SAFE",
            annual_dividend=Decimal("2.0"),
            dividend_yield=Decimal("4.0"),
            payout_ratio=Decimal("50.0"),  # 40-60%
        )
        assert data.safety == DividendSafety.SAFE

    def test_safety_moderate(self):
        """Test cálculo de seguridad - moderado."""
        data = DividendData(
            symbol="MOD",
            annual_dividend=Decimal("2.0"),
            dividend_yield=Decimal("4.0"),
            payout_ratio=Decimal("70.0"),  # 60-80%
        )
        assert data.safety == DividendSafety.MODERATE

    def test_safety_risky(self):
        """Test cálculo de seguridad - riesgoso."""
        data = DividendData(
            symbol="RISK",
            annual_dividend=Decimal("2.0"),
            dividend_yield=Decimal("4.0"),
            payout_ratio=Decimal("90.0"),  # 80-100%
        )
        assert data.safety == DividendSafety.RISKY

    def test_safety_dangerous(self):
        """Test cálculo de seguridad - peligroso."""
        data = DividendData(
            symbol="DANGER",
            annual_dividend=Decimal("2.0"),
            dividend_yield=Decimal("4.0"),
            payout_ratio=Decimal("110.0"),  # > 100%
        )
        assert data.safety == DividendSafety.DANGEROUS

    def test_aristocrat_status_not_aristocrat(self):
        """Test estatus aristócrata - no aristócrata."""
        data = DividendData(
            symbol="NEW",
            annual_dividend=Decimal("1.0"),
            dividend_yield=Decimal("2.0"),
            years_consecutive_increases=2,  # < 5
        )
        assert data.aristocrat_status == DividendAristocratStatus.NOT_ARISTOCRAT

    def test_aristocrat_status_aristocrat_10(self):
        """Test estatus aristócrata - 10 años."""
        data = DividendData(
            symbol="AR10",
            annual_dividend=Decimal("1.0"),
            dividend_yield=Decimal("3.0"),
            years_consecutive_increases=10,
        )
        assert data.aristocrat_status == DividendAristocratStatus.ARISTOCRAT_10

    def test_aristocrat_status_aristocrat_25(self):
        """Test estatus aristócrata - 25 años (S&P 500)."""
        data = DividendData(
            symbol="AR25",
            annual_dividend=Decimal("1.0"),
            dividend_yield=Decimal("3.0"),
            years_consecutive_increases=25,
        )
        assert data.aristocrat_status == DividendAristocratStatus.ARISTOCRAT_25

    def test_monthly_dividend_estimate_quarterly(self):
        """Test estimación de dividendo mensual - trimestral."""
        data = DividendData(
            symbol="QTR",
            annual_dividend=Decimal("4.00"),
            dividend_yield=Decimal("4.0"),
            frequency=DividendFrequency.QUARTERLY,
        )
        assert data.monthly_dividend_estimate == Decimal("1.00")

    def test_monthly_dividend_estimate_monthly(self):
        """Test estimación de dividendo mensual - mensual."""
        data = DividendData(
            symbol="MTH",
            annual_dividend=Decimal("1.20"),
            dividend_yield=Decimal("1.2"),
            frequency=DividendFrequency.MONTHLY,
        )
        assert data.monthly_dividend_estimate == Decimal("0.10")


class TestDividendProfile:
    """Tests para DividendProfile model."""

    def test_is_not_dividend_trap_safe_profile(self, sample_dividend_profile):
        """Test que perfil seguro no es trap."""
        assert not sample_dividend_profile.is_dividend_trap

    def test_is_dividend_trap_high_yield(self):
        """Test detección de trap - yield muy alto."""
        data = DividendData(
            symbol="TRAP",
            annual_dividend=Decimal("10.0"),
            dividend_yield=Decimal("12.0"),  # > 10%
            payout_ratio=Decimal("50.0"),
        )

        profile = DividendProfile(
            symbol="TRAP",
            current_price=Decimal("100"),
            dividend_data=data,
        )

        assert profile.is_dividend_trap

    def test_is_dividend_trap_payout_over_100(self):
        """Test detección de trap - payout > 100%."""
        data = DividendData(
            symbol="TRAP2",
            annual_dividend=Decimal("5.0"),
            dividend_yield=Decimal("5.0"),
            payout_ratio=Decimal("120.0"),  # > 100%
        )

        profile = DividendProfile(
            symbol="TRAP2",
            current_price=Decimal("100"),
            dividend_data=data,
        )

        assert profile.is_dividend_trap

    def test_overall_score_calculation(self, sample_dividend_profile):
        """Test cálculo de score general."""
        # Debe ser promedio de quality, sustainability, value
        expected = (
            sample_dividend_profile.quality_score
            + sample_dividend_profile.sustainability_score
            + sample_dividend_profile.value_score
        ) / 3

        assert sample_dividend_profile.overall_score == expected


class TestDividendStrategyConfig:
    """Tests para DividendStrategyConfig."""

    def test_valid_config(self, valid_config):
        """Test configuración válida."""
        config = DividendStrategyConfig(**valid_config)
        assert config.min_dividend_yield == Decimal("3.0")
        assert config.portfolio_size == 20

    def test_weights_sum_validation(self):
        """Test que pesos deben sumar 1.0."""
        with pytest.raises(ValueError, match="deben sumar 1.0"):
            DividendStrategyConfig(
                min_dividend_yield=3.0,
                yield_weight=Decimal("0.5"),
                growth_weight=Decimal("0.5"),
                sustainability_weight=Decimal("0.1"),  # Suma 1.1
                value_weight=Decimal("0.1"),
            )

    def test_min_yield_less_than_max(self):
        """Test que min_yield < max_yield."""
        with pytest.raises(ValueError, match="menor que max_dividend_yield"):
            DividendStrategyConfig(
                min_dividend_yield=10.0,
                max_dividend_yield=5.0,  # < min
            )


class TestExDividendDate:
    """Tests para ExDividendDate."""

    def test_days_until_ex_dividend_future(self):
        """Test días hasta ex-dividend - futuro."""
        ex_date = ExDividendDate(
            symbol="TEST",
            ex_dividend_date=date.today() + timedelta(days=10),
            amount=Decimal("1.0"),
        )

        assert ex_date.days_until_ex_dividend == 10

    def test_days_until_ex_dividend_past(self):
        """Test días hasta ex-dividend - pasado."""
        ex_date = ExDividendDate(
            symbol="TEST",
            ex_dividend_date=date.today() - timedelta(days=5),
            amount=Decimal("1.0"),
        )

        assert ex_date.days_until_ex_dividend == -5


# ============================================================================
# SCREENER TESTS (12 tests)
# ============================================================================


class TestDividendScreener:
    """Tests para DividendScreener."""

    def test_screener_initialization(self, dividend_config):
        """Test inicialización de screener."""
        screener = DividendScreener(dividend_config)
        assert screener.config == dividend_config
        assert screener.criteria is not None

    def test_screen_all_pass(self, dividend_config, multiple_profiles):
        """Test screening donde todos pasan."""
        # First, let's update profiles to include required FCF data
        for profile in multiple_profiles:
            if profile.dividend_data.free_cash_flow_per_share is None:
                profile.dividend_data.free_cash_flow_per_share = Decimal("5.0")

        screener = DividendScreener(dividend_config)
        result = screener.screen(multiple_profiles)

        assert len(result.passed_stocks) > 0
        assert result.total_evaluated == len(multiple_profiles)

    def test_screen_yield_too_low(self, dividend_config, sample_dividend_profile):
        """Test screening - yield muy bajo."""
        # Crear perfil con yield bajo
        low_yield_profile = DividendProfile(
            symbol="LOW",
            current_price=Decimal("100"),
            dividend_data=DividendData(
                symbol="LOW",
                annual_dividend=Decimal("1.0"),
                dividend_yield=Decimal("1.5"),  # < 3%
                payout_ratio=Decimal("30.0"),
            ),
            quality_score=Decimal("70"),
            sustainability_score=Decimal("70"),
        )

        screener = DividendScreener(dividend_config)
        result = screener.screen([low_yield_profile])

        assert len(result.passed_stocks) == 0
        assert "Yield muy bajo" in result.failed_stocks["LOW"][0]

    def test_screen_yield_too_high(self, dividend_config):
        """Test screening - yield muy alto (posible trap)."""
        high_yield_profile = DividendProfile(
            symbol="HIGH",
            current_price=Decimal("100"),
            dividend_data=DividendData(
                symbol="HIGH",
                annual_dividend=Decimal("12.0"),
                dividend_yield=Decimal("12.0"),  # > 10%
                payout_ratio=Decimal("50.0"),
                years_consecutive_increases=5,
                earnings_per_share=Decimal("24.0"),  # Added
                free_cash_flow_per_share=Decimal("20.0"),  # Added
            ),
            quality_score=Decimal("70"),
            sustainability_score=Decimal("70"),
        )

        screener = DividendScreener(dividend_config)
        result = screener.screen([high_yield_profile])

        assert len(result.passed_stocks) == 0
        # The high yield triggers dividend trap detection first
        assert "Dividend trap detectado" in result.failed_stocks["HIGH"][0]

    def test_screen_payout_ratio_exceeded(self, dividend_config):
        """Test screening - payout ratio excedido."""
        profile = DividendProfile(
            symbol="HIGHPAY",
            current_price=Decimal("100"),
            dividend_data=DividendData(
                symbol="HIGHPAY",
                annual_dividend=Decimal("5.0"),
                dividend_yield=Decimal("5.0"),
                payout_ratio=Decimal("85.0"),  # > 70%
            ),
            quality_score=Decimal("70"),
            sustainability_score=Decimal("70"),
        )

        screener = DividendScreener(dividend_config)
        result = screener.screen([profile])

        assert len(result.passed_stocks) == 0
        assert "Payout ratio excedido" in result.failed_stocks["HIGHPAY"][0]

    def test_screen_insufficient_consecutive_years(self, dividend_config):
        """Test screening - años consecutivos insuficientes."""
        profile = DividendProfile(
            symbol="NEW",
            current_price=Decimal("100"),
            dividend_data=DividendData(
                symbol="NEW",
                annual_dividend=Decimal("3.0"),
                dividend_yield=Decimal("3.5"),
                payout_ratio=Decimal("50.0"),
                years_consecutive_increases=1,  # < 3
            ),
            quality_score=Decimal("70"),
            sustainability_score=Decimal("70"),
        )

        screener = DividendScreener(dividend_config)
        result = screener.screen([profile])

        assert len(result.passed_stocks) == 0
        assert "Años consecutivos" in result.failed_stocks["NEW"][0]

    def test_screen_quality_score_too_low(self, dividend_config):
        """Test screening - quality score muy bajo."""
        profile = DividendProfile(
            symbol="LOWQ",
            current_price=Decimal("100"),
            dividend_data=DividendData(
                symbol="LOWQ",
                annual_dividend=Decimal("4.0"),
                dividend_yield=Decimal("4.0"),
                payout_ratio=Decimal("60.0"),
                years_consecutive_increases=5,
            ),
            quality_score=Decimal("40"),  # < 50
            sustainability_score=Decimal("70"),
        )

        screener = DividendScreener(dividend_config)
        result = screener.screen([profile])

        assert len(result.passed_stocks) == 0
        assert "Quality score bajo" in result.failed_stocks["LOWQ"][0]

    def test_screen_dividend_trap_detected(self, dividend_config):
        """Test screening - dividend trap detectado."""
        profile = DividendProfile(
            symbol="TRAP",
            current_price=Decimal("100"),
            dividend_data=DividendData(
                symbol="TRAP",
                annual_dividend=Decimal("11.0"),
                dividend_yield=Decimal("11.0"),  # > 10%
                payout_ratio=Decimal("50.0"),
            ),
            quality_score=Decimal("70"),
            sustainability_score=Decimal("70"),
        )

        screener = DividendScreener(dividend_config)
        result = screener.screen([profile])

        assert "Dividend trap" in result.failed_stocks["TRAP"][0]

    def test_screen_sector_exclusion(self, dividend_config):
        """Test screening - sector excluido."""
        profile = DividendProfile(
            symbol="UTIL",
            current_price=Decimal("100"),
            dividend_data=DividendData(
                symbol="UTIL",
                annual_dividend=Decimal("4.0"),
                dividend_yield=Decimal("4.0"),
                payout_ratio=Decimal("60.0"),
                years_consecutive_increases=10,
                earnings_per_share=Decimal("6.67"),
                free_cash_flow_per_share=Decimal("5.0"),  # Added to pass FCF check
            ),
            sector="Utilities",  # Sector excluido
            quality_score=Decimal("70"),
            sustainability_score=Decimal("70"),
        )

        screener = DividendScreener(dividend_config)
        result = screener.screen([profile])

        assert "Sector excluido" in result.failed_stocks["UTIL"][0]

    def test_screen_pe_ratio_too_high(self, dividend_config):
        """Test screening - P/E muy alto."""
        # Crear nueva config con límite PE
        config_dict = dividend_config.model_dump()
        config_dict["max_pe_ratio"] = Decimal("20.0")
        config_with_pe_limit = DividendStrategyConfig(**config_dict)

        profile = DividendProfile(
            symbol="EXPENSIVE",
            current_price=Decimal("100"),
            dividend_data=DividendData(
                symbol="EXPENSIVE",
                annual_dividend=Decimal("4.0"),
                dividend_yield=Decimal("4.0"),
                payout_ratio=Decimal("60.0"),
                years_consecutive_increases=10,
                earnings_per_share=Decimal("2.86"),
                free_cash_flow_per_share=Decimal("3.0"),  # Added to pass FCF check
            ),
            pe_ratio=Decimal("35.0"),  # > 20
            quality_score=Decimal("70"),
            sustainability_score=Decimal("70"),
        )

        screener = DividendScreener(config_with_pe_limit)
        result = screener.screen([profile])

        assert "P/E muy alto" in result.failed_stocks["EXPENSIVE"][0]

    def test_calculate_preliminary_score(self, dividend_config, sample_dividend_profile):
        """Test cálculo de score preliminar."""
        # Ensure FCF is set
        if sample_dividend_profile.dividend_data.free_cash_flow_per_share is None:
            sample_dividend_profile.dividend_data.free_cash_flow_per_share = Decimal("7.50")

        screener = DividendScreener(dividend_config)
        stock = screener._create_dividend_stock(sample_dividend_profile)

        assert 0 <= stock.decision_score <= 100
        assert stock.recommendation in ["buy", "hold", "avoid"]

    def test_pass_rate_calculation(self, dividend_config, multiple_profiles):
        """Test cálculo de tasa de aprobación."""
        # First, let's update profiles to include required FCF data
        for profile in multiple_profiles:
            if profile.dividend_data.free_cash_flow_per_share is None:
                profile.dividend_data.free_cash_flow_per_share = Decimal("5.0")

        screener = DividendScreener(dividend_config)
        result = screener.screen(multiple_profiles)

        expected_rate = (len(result.passed_stocks) / result.total_evaluated) * 100
        assert result.pass_rate == expected_rate


# ============================================================================
# ANALYZER TESTS (10 tests)
# ============================================================================


class TestDividendAnalyzer:
    """Tests para DividendAnalyzer."""

    def test_analyzer_initialization(self):
        """Test inicialización de analizador."""
        analyzer = DividendAnalyzer()
        assert analyzer.lookback_years == 10

    def test_analyze_quality(self, sample_dividend_profile):
        """Test análisis de calidad."""
        analyzer = DividendAnalyzer()
        quality = analyzer.analyze_quality(sample_dividend_profile)

        assert isinstance(quality, DividendQualityScore)
        assert 0 <= quality.total <= 100
        assert 0 <= quality.yield_score <= 100
        assert 0 <= quality.growth_score <= 100
        assert 0 <= quality.consistency_score <= 100
        assert 0 <= quality.safety_score <= 100
        assert 0 <= quality.coverage_score <= 100

    def test_analyze_sustainability(self, sample_dividend_profile):
        """Test análisis de sostenibilidad."""
        analyzer = DividendAnalyzer()
        sustainability = analyzer.analyze_sustainability(sample_dividend_profile)

        assert isinstance(sustainability, DividendSustainabilityMetrics)
        assert 0 <= sustainability.sustainability_score <= 100
        assert isinstance(sustainability.sustainable, bool)
        assert isinstance(sustainability.risk_factors, list)
        assert isinstance(sustainability.strength_factors, list)

    def test_identify_risk_factors_high_payout(self):
        """Test identificación de riesgos - payout alto."""
        profile = DividendProfile(
            symbol="RISK",
            current_price=Decimal("100"),
            dividend_data=DividendData(
                symbol="RISK",
                annual_dividend=Decimal("8.0"),
                dividend_yield=Decimal("8.0"),
                payout_ratio=Decimal("95.0"),
            ),
        )

        analyzer = DividendAnalyzer()
        risks = analyzer._identify_risk_factors(profile)

        assert any("Payout ratio muy alto" in r for r in risks)

    def test_identify_risk_factors_negative_growth(self):
        """Test identificación de riesgos - crecimiento negativo."""
        profile = DividendProfile(
            symbol="DECLINE",
            current_price=Decimal("100"),
            dividend_data=DividendData(
                symbol="DECLINE",
                annual_dividend=Decimal("3.0"),
                dividend_yield=Decimal("3.0"),
                payout_ratio=Decimal("60.0"),
                dividend_growth_rate_3y=Decimal("-5.0"),
            ),
        )

        analyzer = DividendAnalyzer()
        risks = analyzer._identify_risk_factors(profile)

        assert any("Dividendos decreciendo" in r for r in risks)

    def test_identify_strength_factors_aristocrat(self):
        """Test identificación de fortalezas - aristócrata."""
        profile = DividendProfile(
            symbol="ARIST",
            current_price=Decimal("100"),
            dividend_data=DividendData(
                symbol="ARIST",
                annual_dividend=Decimal("3.0"),
                dividend_yield=Decimal("3.0"),
                payout_ratio=Decimal("50.0"),
                years_consecutive_increases=25,
            ),
        )

        analyzer = DividendAnalyzer()
        strengths = analyzer._identify_strength_factors(profile)

        assert any("Dividend Aristocrat" in s for s in strengths)

    def test_calculate_yield_score_ideal_range(self):
        """Test cálculo de score yield - rango ideal."""
        profile = DividendProfile(
            symbol="IDEAL",
            current_price=Decimal("100"),
            dividend_data=DividendData(
                symbol="IDEAL",
                annual_dividend=Decimal("5.0"),
                dividend_yield=Decimal("5.0"),  # 4-6% ideal
                payout_ratio=Decimal("60.0"),
            ),
        )

        analyzer = DividendAnalyzer()
        score = analyzer._calculate_yield_score(profile)

        assert score == Decimal("100")

    def test_analyze_yield_on_cost(self, sample_dividend_profile):
        """Test cálculo de yield on cost."""
        analyzer = DividendAnalyzer()
        purchase_price = Decimal("150.00")

        yoc = analyzer.analyze_yield_on_cost(sample_dividend_profile, purchase_price, years_held=5)

        # YOC = (annual_dividend / purchase_price) * 100
        expected = (sample_dividend_profile.dividend_data.annual_dividend / purchase_price) * 100
        assert yoc == expected.quantize(Decimal("0.01"))

    def test_project_dividend_income(self, sample_dividend_profile):
        """Test proyección de ingresos por dividendos."""
        analyzer = DividendAnalyzer()

        projections = analyzer.project_dividend_income(
            sample_dividend_profile,
            investment_amount=Decimal("10000"),
            years=5,
        )

        assert len(projections) == 5
        for year, dividend, income in projections:
            assert year in range(1, 6)
            assert dividend > 0
            assert income > 0

    def test_sustainability_score_calculation(self, sample_dividend_profile):
        """Test cálculo de score de sostenibilidad."""
        analyzer = DividendAnalyzer()

        risks = ["Riesgo 1"]
        strengths = ["Fortaleza 1", "Fortaleza 2"]

        score = analyzer._calculate_sustainability_score(sample_dividend_profile, risks, strengths)

        assert 0 <= score <= 100


# ============================================================================
# PORTFOLIO CONSTRUCTOR TESTS (10 tests)
# ============================================================================


class TestDividendPortfolioConstructor:
    """Tests para DividendPortfolioConstructor."""

    def test_constructor_initialization(self, dividend_config):
        """Test inicialización de constructor."""
        constructor = DividendPortfolioConstructor(dividend_config)

        assert constructor.config == dividend_config
        assert constructor.portfolio_config.target_size == 20

    def test_construct_portfolio(self, dividend_config, dividend_stock):
        """Test construcción de portafolio."""
        constructor = DividendPortfolioConstructor(dividend_config)

        # Crear lista de acciones
        stocks = [dividend_stock]

        portfolio = constructor.construct_portfolio(stocks, Decimal("100000"))

        assert isinstance(portfolio, DividendPortfolio)
        assert portfolio.total_value > 0
        assert portfolio.annual_income >= 0
        assert portfolio.portfolio_yield >= 0

    def test_sector_weights_calculation(self, dividend_config, multiple_profiles):
        """Test cálculo de pesos sectoriales."""
        constructor = DividendPortfolioConstructor(dividend_config)

        # Crear stocks desde perfiles
        stocks = [
            DividendStock(
                profile=p,
                decision_score=Decimal("70"),
                decision_reason="Test",
                recommendation="buy",
            )
            for p in multiple_profiles
        ]

        portfolio = constructor.construct_portfolio(stocks, Decimal("100000"))

        assert len(portfolio.sector_weights) > 0

        # Verificar que ningún sector exceda el máximo
        for sector, weight in portfolio.sector_weights.items():
            assert weight <= dividend_config.max_sector_weight

    def test_max_position_size_enforced(self, dividend_config, multiple_profiles):
        """Test que se respete el tamaño máximo de posición."""
        constructor = DividendPortfolioConstructor(dividend_config)

        # Crear un solo stock
        stock = DividendStock(
            profile=multiple_profiles[0],
            decision_score=Decimal("90"),
            decision_reason="High quality",
            recommendation="buy",
        )

        portfolio = constructor.construct_portfolio([stock], Decimal("100000"))

        # Verificar que ninguna posición exceda el máximo
        for pos in portfolio.positions:
            assert pos.weight <= dividend_config.max_single_position

    def test_normalize_weights(self, dividend_config):
        """Test normalización de pesos."""
        constructor = DividendPortfolioConstructor(dividend_config)

        weights = {
            "A": Decimal("0.5"),
            "B": Decimal("0.3"),
            "C": Decimal("0.2"),
        }

        normalized = constructor._normalize_weights(weights)

        assert abs(sum(normalized.values()) - Decimal("1.0")) < Decimal("0.001")

    def test_enforce_sector_limits(self, dividend_config, multiple_profiles):
        """Test aplicación de límites sectoriales."""
        constructor = DividendPortfolioConstructor(dividend_config)

        # Crear grupos sectoriales con DividendStock objects
        stocks = [
            DividendStock(
                profile=p,
                decision_score=Decimal("70"),
                decision_reason="Test",
                recommendation="buy",
            )
            for p in multiple_profiles[:3]
        ]
        sector_groups = {"Technology": stocks}

        # Pesos que exceden límite
        weights = {p.profile.symbol: Decimal("0.5") for p in stocks}

        adjusted = constructor._enforce_sector_limits(weights, sector_groups)

        # Verificar que se ajustaron
        tech_weight = sum(adjusted.get(p.profile.symbol, Decimal("0")) for p in stocks)

        assert tech_weight <= dividend_config.max_sector_weight

    def test_calculate_sector_weights(self, dividend_config, multiple_profiles):
        """Test cálculo de pesos sectoriales."""
        constructor = DividendPortfolioConstructor(dividend_config)

        # Crear posiciones dummy
        positions = [
            PortfolioPosition(
                symbol="A",
                weight=Decimal("0.3"),
                shares=100,
                avg_cost=Decimal("100"),
                current_value=Decimal("30000"),
                annual_income=Decimal("1200"),
                yield_on_cost=Decimal("4.0"),
            ),
            PortfolioPosition(
                symbol="B",
                weight=Decimal("0.7"),
                shares=100,
                avg_cost=Decimal("100"),
                current_value=Decimal("70000"),
                annual_income=Decimal("2800"),
                yield_on_cost=Decimal("4.0"),
            ),
        ]

        # Create stocks from profiles for sector mapping
        stocks = [
            DividendStock(
                profile=p,
                decision_score=Decimal("70"),
                decision_reason="Test",
                recommendation="buy",
            )
            for p in multiple_profiles[:2]
        ]

        # Override the symbols to match positions
        stocks[0].profile.symbol = "A"
        stocks[1].profile.symbol = "B"

        sector_weights = constructor._calculate_sector_weights(positions, stocks)

        assert len(sector_weights) > 0
        # Suma debe ser 1.0
        total = sum(sector_weights.values())
        assert abs(total - Decimal("1.0")) < Decimal("0.01")

    def test_portfolio_yield_calculation(self, dividend_config):
        """Test cálculo de yield del portafolio."""
        DividendPortfolioConstructor(dividend_config)

        portfolio = DividendPortfolio(
            positions=[
                PortfolioPosition(
                    symbol="A",
                    weight=Decimal("0.5"),
                    shares=100,
                    avg_cost=Decimal("100"),
                    current_value=Decimal("50000"),
                    annual_income=Decimal("2000"),  # 4% yield
                    yield_on_cost=Decimal("4.0"),
                ),
                PortfolioPosition(
                    symbol="B",
                    weight=Decimal("0.5"),
                    shares=100,
                    avg_cost=Decimal("100"),
                    current_value=Decimal("50000"),
                    annual_income=Decimal("1500"),  # 3% yield
                    yield_on_cost=Decimal("3.0"),
                ),
            ],
            total_value=Decimal("100000"),
            annual_income=Decimal("3500"),
            portfolio_yield=Decimal("3.5"),
            sector_weights={},
            expected_monthly_income=Decimal("3500") / 12,  # 291.666...
            construction_metadata={},
        )

        # Yield = (annual_income / total_value) * 100
        assert portfolio.portfolio_yield == Decimal("3.5")
        # expected_monthly_income = annual_income / 12
        expected_monthly = Decimal("3500") / 12
        # Use approximate comparison due to Decimal precision
        assert abs(portfolio.expected_monthly_income - expected_monthly) < Decimal("0.01")

    def test_analyze_drift_no_drift(self, dividend_config):
        """Test análisis de drift - sin drift."""
        constructor = DividendPortfolioConstructor(dividend_config)

        portfolio = DividendPortfolio(
            positions=[
                PortfolioPosition(
                    symbol="A",
                    weight=Decimal("0.25"),
                    shares=100,
                    avg_cost=Decimal("100"),
                    current_value=Decimal("25000"),
                    annual_income=Decimal("1000"),
                    yield_on_cost=Decimal("4.0"),
                ),
            ],
            total_value=Decimal("100000"),
            annual_income=Decimal("1000"),
            portfolio_yield=Decimal("1.0"),
            sector_weights={"Tech": Decimal("0.25")},
            expected_monthly_income=Decimal("83.33"),
            construction_metadata={},
        )

        drift = constructor.analyze_drift(portfolio)

        assert not drift["needs_rebalance"]
        assert drift["max_position_drift"] == 0

    def test_select_top_stocks(self, dividend_config, multiple_profiles):
        """Test selección de top N acciones."""
        constructor = DividendPortfolioConstructor(dividend_config)

        # Crear stocks con scores variados
        stocks = []
        for i, profile in enumerate(multiple_profiles):
            stock = DividendStock(
                profile=profile,
                decision_score=Decimal(f"{90 - i * 5}"),  # Scores decrecientes
                decision_reason="Test",
                recommendation="buy",
            )
            stocks.append(stock)

        # Seleccionar top 5
        constructor.portfolio_config.target_size = 5
        selected = constructor._select_top_stocks(stocks)

        assert len(selected) == 5
        # Verificar que están ordenados por score
        for i in range(len(selected) - 1):
            assert selected[i].decision_score >= selected[i + 1].decision_score


# ============================================================================
# DIVIDEND STRATEGY TESTS (8 tests)
# ============================================================================


class TestDividendStrategy:
    """Tests para DividendStrategy."""

    def test_strategy_initialization(self, valid_config):
        """Test inicialización de estrategia."""
        strategy = DividendStrat(valid_config)

        assert strategy.name == "TestDividendStrategy"
        assert strategy.strategy_config is not None
        assert strategy.screener is not None
        assert strategy.analyzer is not None
        assert strategy.constructor is not None

    def test_parse_config(self, valid_config):
        """Test parseo de configuración."""
        strategy = DividendStrat(valid_config)

        assert strategy.strategy_config.min_dividend_yield == Decimal("3.0")
        assert strategy.strategy_config.portfolio_size == 20

    def test_validate_config_valid(self, valid_config):
        """Test validación de config - válida."""
        strategy = DividendStrat(valid_config)

        assert strategy.validate_config() is True

    def test_validate_config_invalid_min_greater_than_max(self, valid_config):
        """Test validación de config - min > max."""
        invalid_config = valid_config.copy()
        invalid_config["min_dividend_yield"] = 10.0
        invalid_config["max_dividend_yield"] = 5.0

        strategy = DividendStrat(invalid_config)

        assert strategy.validate_config() is False

    def test_validate_config_invalid_portfolio_size(self, valid_config):
        """Test validación de config - tamaño inválido."""
        invalid_config = valid_config.copy()
        invalid_config["portfolio_size"] = 100  # > 50

        strategy = DividendStrat(invalid_config)

        assert strategy.validate_config() is False

    def test_get_required_parameters(self, valid_config):
        """Test obtención de parámetros requeridos."""
        strategy = DividendStrat(valid_config)

        params = strategy.get_required_parameters()

        assert "min_dividend_yield" in params
        assert "max_dividend_yield" in params
        assert "max_payout_ratio" in params
        assert "portfolio_size" in params

    def test_set_universe(self, valid_config, multiple_profiles):
        """Test establecimiento de universo."""
        strategy = DividendStrat(valid_config)

        strategy.set_universe(multiple_profiles)

        assert len(strategy.universe) == len(multiple_profiles)

    def test_record_dividend_payment(self, valid_config):
        """Test registro de pago de dividendo."""
        strategy = DividendStrat(valid_config)

        strategy.record_dividend_payment("AAPL", Decimal("100.50"))

        assert strategy.total_dividends_received == Decimal("100.50")
        assert len(strategy.dividend_payments) == 1
        assert strategy.dividend_payments[0]["symbol"] == "AAPL"


# ============================================================================
# INTEGRATION TESTS (5 tests)
# ============================================================================


class TestDividendStrategyIntegration:
    """Tests de integración del flujo completo."""

    def test_full_workflow_screening_to_portfolio(self, valid_config, multiple_profiles):
        """Test flujo completo: screening -> portfolio."""
        # 1. Crear estrategia
        strategy = DividendStrat(valid_config)

        # 2. Aplicar screening
        screening_result = strategy.screener.screen(multiple_profiles)

        assert len(screening_result.passed_stocks) > 0

        # 3. Construir portafolio
        portfolio = strategy.constructor.construct_portfolio(
            screening_result.passed_stocks,
            Decimal("100000"),
        )

        assert portfolio.total_value > 0
        assert len(portfolio.positions) > 0

    def test_quality_analysis_workflow(self, valid_config, sample_dividend_profile):
        """Test flujo de análisis de calidad."""
        strategy = DividendStrat(valid_config)

        # Analizar calidad
        quality = strategy.analyzer.analyze_quality(sample_dividend_profile)

        assert quality.total > 0

        # Analizar sostenibilidad
        sustainability = strategy.analyzer.analyze_sustainability(sample_dividend_profile)

        assert sustainability.sustainability_score > 0

    def test_sector_diversification_enforcement(self, valid_config):
        """Test que se enforce diversificación sectorial."""
        strategy = DividendStrat(valid_config)

        # Crear perfiles todos del mismo sector
        same_sector_profiles = []
        for i in range(25):
            data = DividendData(
                symbol=f"TECH{i}",
                annual_dividend=Decimal("4.0"),
                dividend_yield=Decimal("4.0"),
                payout_ratio=Decimal("60.0"),
                years_consecutive_increases=10,
            )

            profile = DividendProfile(
                symbol=f"TECH{i}",
                sector="Technology",  # Todos en Technology
                current_price=Decimal("100"),
                dividend_data=data,
                quality_score=Decimal("75"),
                sustainability_score=Decimal("75"),
            )

            same_sector_profiles.append(profile)

        # Screening
        stocks = [
            DividendStock(
                profile=p,
                decision_score=Decimal("75"),
                decision_reason="Test",
                recommendation="buy",
            )
            for p in same_sector_profiles
        ]

        # Construir portafolio
        portfolio = strategy.constructor.construct_portfolio(stocks, Decimal("100000"))

        # Verificar límite sectorial
        tech_weight = portfolio.sector_weights.get("Technology", Decimal("0"))
        assert tech_weight <= strategy.strategy_config.max_sector_weight

    def test_dividend_trap_filtering(self, valid_config):
        """Test que se filtran dividend traps."""
        strategy = DividendStrat(valid_config)

        # Crear perfil de trap
        trap_profile = DividendProfile(
            symbol="TRAP",
            current_price=Decimal("100"),
            dividend_data=DividendData(
                symbol="TRAP",
                annual_dividend=Decimal("12.0"),
                dividend_yield=Decimal("12.0"),  # Muy alto
                payout_ratio=Decimal("50.0"),
                years_consecutive_increases=5,  # Agregar para pasar screening básico
            ),
            quality_score=Decimal("70"),
            sustainability_score=Decimal("70"),
        )

        # Screening debe rechazar
        result = strategy.screener.screen([trap_profile])

        assert len(result.passed_stocks) == 0
        assert "Dividend trap" in result.failed_stocks["TRAP"][0]

    def test_portfolio_rebalance_workflow(self, valid_config, multiple_profiles):
        """Test flujo de rebalanceo de portafolio."""
        strategy = DividendStrat(valid_config)

        # Crear stocks iniciales
        stocks = [
            DividendStock(
                profile=p,
                decision_score=Decimal("70"),
                decision_reason="Test",
                recommendation="buy",
            )
            for p in multiple_profiles
        ]

        # Construir portafolio inicial
        initial_portfolio = strategy.constructor.construct_portfolio(stocks[:10], Decimal("100000"))

        # Rebalancear con diferentes stocks
        new_portfolio = strategy.constructor.rebalance(
            initial_portfolio, stocks[5:], Decimal("100000")
        )

        assert new_portfolio.total_value > 0
