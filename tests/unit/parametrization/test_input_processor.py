"""
Unit tests for T1.1: InputProcessor

Tests input validation, enum constraints, and error handling.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from app.core.models.input_profile import (
    InputProfile,
    InputProcessor,
    ObjectivoInversion,
    RiskTolerance,
)


class TestInputProfileModel:
    """Test InputProfile Pydantic model validation."""

    def test_valid_input_profile_creation(self):
        """Test creating valid InputProfile."""
        profile = InputProfile(
            capital_initial=Decimal("250000"),
            objetivo_inversion="maximizar_capital",
            risk_tolerance="medio",
            investment_horizon=12
        )

        assert profile.capital_initial == Decimal("250000")
        assert profile.objetivo_inversion == ObjectivoInversion.MAXIMIZAR_CAPITAL
        assert profile.risk_tolerance == RiskTolerance.MEDIO
        assert profile.investment_horizon == 12
        assert profile.input_id is not None

    def test_capital_conversion_from_string(self):
        """Test capital conversion from string to Decimal."""
        profile = InputProfile(
            capital_initial="100000",
            objetivo_inversion="maximizar_capital",
            risk_tolerance="bajo",
            investment_horizon=24
        )

        assert isinstance(profile.capital_initial, Decimal)
        assert profile.capital_initial == Decimal("100000")

    def test_capital_conversion_from_int(self):
        """Test capital conversion from int to Decimal."""
        profile = InputProfile(
            capital_initial=50000,
            objetivo_inversion="maximizar_dividendos",
            risk_tolerance="medio",
            investment_horizon=12
        )

        assert isinstance(profile.capital_initial, Decimal)
        assert profile.capital_initial == Decimal("50000")

    def test_capital_conversion_from_float(self):
        """Test capital conversion from float to Decimal."""
        profile = InputProfile(
            capital_initial=250000.50,
            objetivo_inversion="capital_preservation",
            risk_tolerance="bajo",
            investment_horizon=36
        )

        assert isinstance(profile.capital_initial, Decimal)
        assert profile.capital_initial == Decimal("250000.5")

    def test_invalid_capital_zero(self):
        """Test capital validation rejects zero."""
        with pytest.raises(ValueError):
            InputProfile(
                capital_initial=0,
                objetivo_inversion="maximizar_capital",
                risk_tolerance="medio",
                investment_horizon=12
            )

    def test_invalid_capital_negative(self):
        """Test capital validation rejects negative values."""
        with pytest.raises(ValueError):
            InputProfile(
                capital_initial=Decimal("-100000"),
                objetivo_inversion="maximizar_capital",
                risk_tolerance="medio",
                investment_horizon=12
            )

    def test_invalid_capital_too_large(self):
        """Test capital validation rejects values > €10M."""
        with pytest.raises(ValueError):
            InputProfile(
                capital_initial=Decimal("11000000"),
                objetivo_inversion="maximizar_capital",
                risk_tolerance="medio",
                investment_horizon=12
            )

    def test_invalid_objetivo_inversion(self):
        """Test objetivo_inversion validation rejects invalid values."""
        with pytest.raises(ValueError):
            InputProfile(
                capital_initial=250000,
                objetivo_inversion="invalid_objetivo",
                risk_tolerance="medio",
                investment_horizon=12
            )

    def test_valid_objetivo_inversion_all_types(self):
        """Test all valid objetivo_inversion values."""
        for objetivo in [
            "maximizar_capital",
            "maximizar_dividendos",
            "capital_preservation",
            "balanced_growth",
            "income_generation"
        ]:
            profile = InputProfile(
                capital_initial=100000,
                objetivo_inversion=objetivo,
                risk_tolerance="medio",
                investment_horizon=12
            )
            assert profile.objetivo_inversion.value == objetivo

    def test_invalid_risk_tolerance(self):
        """Test risk_tolerance validation rejects invalid values."""
        with pytest.raises(ValueError):
            InputProfile(
                capital_initial=250000,
                objetivo_inversion="maximizar_capital",
                risk_tolerance="muy_alto",
                investment_horizon=12
            )

    def test_valid_risk_tolerance_all_types(self):
        """Test all valid risk_tolerance values."""
        for risk in ["bajo", "medio", "alto"]:
            profile = InputProfile(
                capital_initial=100000,
                objetivo_inversion="maximizar_capital",
                risk_tolerance=risk,
                investment_horizon=12
            )
            assert profile.risk_tolerance.value == risk

    def test_invalid_investment_horizon_zero(self):
        """Test investment_horizon validation rejects zero."""
        with pytest.raises(ValueError):
            InputProfile(
                capital_initial=250000,
                objetivo_inversion="maximizar_capital",
                risk_tolerance="medio",
                investment_horizon=0
            )

    def test_invalid_investment_horizon_too_long(self):
        """Test investment_horizon validation rejects > 600 months (50 years)."""
        with pytest.raises(ValueError):
            InputProfile(
                capital_initial=250000,
                objetivo_inversion="maximizar_capital",
                risk_tolerance="medio",
                investment_horizon=601
            )

    def test_valid_investment_horizon_range(self):
        """Test valid investment_horizon values."""
        for horizon in [1, 12, 60, 120, 360, 600]:
            profile = InputProfile(
                capital_initial=100000,
                objetivo_inversion="maximizar_capital",
                risk_tolerance="medio",
                investment_horizon=horizon
            )
            assert profile.investment_horizon == horizon

    def test_optional_constraints(self):
        """Test optional constraints field."""
        constraints = {"max_sector_allocation": 0.2, "exclude_sectors": ["tobacco"]}
        profile = InputProfile(
            capital_initial=250000,
            objetivo_inversion="maximizar_capital",
            risk_tolerance="medio",
            investment_horizon=12,
            constraints=constraints
        )
        assert profile.constraints == constraints

    def test_capital_flag_small(self):
        """Test capital_flag for small accounts (< €50k)."""
        profile = InputProfile(
            capital_initial=Decimal("25000"),
            objetivo_inversion="maximizar_capital",
            risk_tolerance="bajo",
            investment_horizon=12
        )
        assert profile.capital_flag == "small"

    def test_capital_flag_medium(self):
        """Test capital_flag for medium accounts (€50k-€250k)."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion="maximizar_capital",
            risk_tolerance="medio",
            investment_horizon=12
        )
        assert profile.capital_flag == "medium"

    def test_capital_flag_large(self):
        """Test capital_flag for large accounts (>= €250k)."""
        profile = InputProfile(
            capital_initial=Decimal("500000"),
            objetivo_inversion="maximizar_capital",
            risk_tolerance="alto",
            investment_horizon=12
        )
        assert profile.capital_flag == "large"

    def test_is_large_account_true(self):
        """Test is_large_account flag for >= €250k."""
        profile = InputProfile(
            capital_initial=Decimal("250000"),
            objetivo_inversion="maximizar_capital",
            risk_tolerance="medio",
            investment_horizon=12
        )
        assert profile.is_large_account is True

    def test_is_large_account_false(self):
        """Test is_large_account flag for < €250k."""
        profile = InputProfile(
            capital_initial=Decimal("249999"),
            objetivo_inversion="maximizar_capital",
            risk_tolerance="medio",
            investment_horizon=12
        )
        assert profile.is_large_account is False

    def test_to_dict_conversion(self):
        """Test conversion to dictionary."""
        profile = InputProfile(
            capital_initial=Decimal("250000"),
            objetivo_inversion="maximizar_capital",
            risk_tolerance="medio",
            investment_horizon=12
        )
        profile_dict = profile.to_dict()

        assert profile_dict["capital_initial"] == "250000"
        assert profile_dict["objetivo_inversion"] == "maximizar_capital"
        assert profile_dict["risk_tolerance"] == "medio"
        assert profile_dict["investment_horizon"] == 12
        assert profile_dict["capital_flag"] == "large"
        assert profile_dict["is_large_account"] is True


class TestInputProcessor:
    """Test InputProcessor class."""

    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        return InputProcessor()

    @pytest.fixture
    def valid_input(self):
        """Create valid input dict."""
        return {
            "capital_initial": 250000,
            "objetivo_inversion": "maximizar_capital",
            "risk_tolerance": "medio",
            "investment_horizon": 12
        }

    def test_processor_initialization(self, processor):
        """Test processor initializes correctly."""
        assert processor.processed_count == 0
        assert processor.error_count == 0

    def test_process_valid_input(self, processor, valid_input):
        """Test processing valid input."""
        profile = processor.process_input(valid_input)

        assert isinstance(profile, InputProfile)
        assert profile.capital_initial == Decimal("250000")
        assert processor.processed_count == 1
        assert processor.error_count == 0

    def test_process_input_with_string_capital(self, processor):
        """Test processing with string capital."""
        profile = processor.process_input({
            "capital_initial": "100000",
            "objetivo_inversion": "maximizar_dividendos",
            "risk_tolerance": "bajo",
            "investment_horizon": 24
        })

        assert profile.capital_initial == Decimal("100000")
        assert processor.processed_count == 1

    def test_process_input_missing_field(self, processor):
        """Test processing with missing required field."""
        with pytest.raises(ValueError, match="Missing required fields"):
            processor.process_input({
                "capital_initial": 250000,
                "objetivo_inversion": "maximizar_capital",
                "risk_tolerance": "medio"
                # missing investment_horizon
            })

        assert processor.error_count == 1

    def test_process_input_invalid_capital(self, processor):
        """Test processing with invalid capital."""
        with pytest.raises(ValueError):
            processor.process_input({
                "capital_initial": 0,
                "objetivo_inversion": "maximizar_capital",
                "risk_tolerance": "medio",
                "investment_horizon": 12
            })

        assert processor.error_count == 1

    def test_process_input_invalid_type(self, processor):
        """Test processing with invalid input type (not dict)."""
        with pytest.raises(ValueError, match="Input must be dictionary"):
            processor.process_input("invalid_input")

        assert processor.error_count == 1

    def test_validate_consistency_no_warnings(self, processor):
        """Test consistency validation with valid inputs."""
        profile = InputProfile(
            capital_initial=250000,
            objetivo_inversion="maximizar_capital",
            risk_tolerance="medio",
            investment_horizon=12
        )

        is_valid, warnings = processor.validate_consistency(profile)
        assert is_valid is True
        assert len(warnings) == 0

    def test_validate_consistency_contradiction_warning(self, processor):
        """Test consistency validation warns on contradictory inputs."""
        profile = InputProfile(
            capital_initial=250000,
            objetivo_inversion="capital_preservation",
            risk_tolerance="alto",
            investment_horizon=12
        )

        is_valid, warnings = processor.validate_consistency(profile)
        assert is_valid is True
        assert len(warnings) > 0
        assert "contradictory" in warnings[0].lower()

    def test_validate_consistency_short_horizon_warning(self, processor):
        """Test consistency validation warns on short horizon with high risk."""
        profile = InputProfile(
            capital_initial=250000,
            objetivo_inversion="maximizar_capital",
            risk_tolerance="alto",
            investment_horizon=6
        )

        is_valid, warnings = processor.validate_consistency(profile)
        assert is_valid is True
        assert len(warnings) > 0
        assert "short" in warnings[0].lower()

    def test_validate_consistency_small_capital_dividend_warning(self, processor):
        """Test consistency validation warns on small capital with dividend objective."""
        profile = InputProfile(
            capital_initial=Decimal("25000"),
            objetivo_inversion="maximizar_dividendos",
            risk_tolerance="bajo",
            investment_horizon=12
        )

        is_valid, warnings = processor.validate_consistency(profile)
        assert is_valid is True
        assert len(warnings) > 0
        assert "diversification" in warnings[0].lower()

    def test_processor_stats(self, processor, valid_input):
        """Test processor statistics tracking."""
        # Process some valid inputs
        processor.process_input(valid_input)
        processor.process_input(valid_input)

        # Attempt invalid input
        try:
            processor.process_input({"capital_initial": 0})
        except ValueError:
            pass

        stats = processor.get_stats()
        assert stats["processed"] == 2
        assert stats["errors"] == 1
        assert stats["success_rate"] == pytest.approx(2/3, rel=0.01)

    def test_processor_multiple_inputs(self, processor):
        """Test processor handles multiple inputs sequentially."""
        inputs = [
            {
                "capital_initial": 50000,
                "objetivo_inversion": "maximizar_capital",
                "risk_tolerance": "bajo",
                "investment_horizon": 24
            },
            {
                "capital_initial": 250000,
                "objetivo_inversion": "maximizar_dividendos",
                "risk_tolerance": "medio",
                "investment_horizon": 12
            },
            {
                "capital_initial": 1000000,
                "objetivo_inversion": "capital_preservation",
                "risk_tolerance": "bajo",
                "investment_horizon": 60
            }
        ]

        profiles = [processor.process_input(inp) for inp in inputs]

        assert len(profiles) == 3
        assert processor.processed_count == 3
        assert processor.error_count == 0
        assert profiles[0].capital_flag == "medium"  # €50k is medium (>= €50k, < €250k)
        assert profiles[1].capital_flag == "large"   # €250k is large (>= €250k)
        assert profiles[2].is_large_account is True  # €1M is large account
