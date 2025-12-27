"""
T1.1: InputProfile - User Input Validation & Parsing

Parse user inputs (capital, objective_inversion) into structured InputProfile.
Entry point for the parametrization framework.

Capabilities:
- Validate user inputs (capital, objective)
- Type conversion (JSON → Pydantic models)
- Constraint checking (capital limits, risk tolerance consistency)
- Clear error messages for invalid inputs
"""

import logging
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


class ObjectivoInversion(str, Enum):
    """User investment objectives."""

    MAXIMIZAR_CAPITAL = "maximizar_capital"
    MAXIMIZAR_DIVIDENDOS = "maximizar_dividendos"
    CAPITAL_PRESERVATION = "capital_preservation"
    BALANCED_GROWTH = "balanced_growth"
    INCOME_GENERATION = "income_generation"


class RiskTolerance(str, Enum):
    """User risk tolerance levels."""

    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"


class InputProfile(BaseModel):
    """
    Parsed and validated user input for parametrization framework.

    This is the entry point to the system. It captures user intent:
    - How much capital are they investing?
    - What's their goal (maximize capital, dividends, etc.)?
    - What's their risk appetite?
    - How long will they invest?

    These inputs drive the entire parametrization framework (T1.1-T14.1).
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    # Identification
    input_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique identifier for this input"
    )

    # Core Investment Parameters
    capital_initial: Decimal = Field(
        ...,
        gt=Decimal("0"),
        le=Decimal("10000000"),
        description="Initial capital in EUR (€1 to €10M)",
    )

    objetivo_inversion: ObjectivoInversion = Field(
        ..., description="User investment objective (maximizar_capital, etc.)"
    )

    risk_tolerance: RiskTolerance = Field(..., description="User risk tolerance (bajo/medio/alto)")

    investment_horizon: int = Field(
        ..., ge=1, le=600, description="Investment horizon in months (1-50 years)"
    )

    # Optional Parameters
    constraints: Optional[Dict] = Field(
        default=None, description="Optional constraints (sector limits, etc.)"
    )

    # Metadata
    created_at: str = Field(
        default_factory=lambda: __import__('datetime').datetime.now().isoformat(),
        description="Timestamp of input creation",
    )

    @field_validator('capital_initial', mode='before')
    @classmethod
    def validate_capital(cls, v):
        """Convert capital to Decimal if needed."""
        if isinstance(v, str):
            try:
                v = Decimal(v)
            except Exception as e:
                raise ValueError(f"Invalid capital format: {e}")
        elif isinstance(v, (int, float)):
            v = Decimal(str(v))
        return v

    @field_validator('objetivo_inversion', mode='before')
    @classmethod
    def validate_objetivo(cls, v):
        """Validate objective is in enum."""
        if isinstance(v, ObjectivoInversion):
            return v
        if isinstance(v, str):
            # Try to convert string to enum
            v = v.lower().strip()
            try:
                return ObjectivoInversion(v)
            except ValueError:
                valid_values = [e.value for e in ObjectivoInversion]
                raise ValueError(
                    f"Invalid objetivo_inversion: {v}. "
                    f"Must be one of: {', '.join(valid_values)}"
                )
        return v

    @field_validator('investment_horizon', mode='before')
    @classmethod
    def validate_horizon(cls, v):
        """Validate investment horizon."""
        if isinstance(v, str):
            try:
                v = int(v)
            except ValueError:
                raise ValueError(f"Investment horizon must be integer months: {v}")
        return v

    @field_validator('risk_tolerance', mode='before')
    @classmethod
    def validate_risk_tolerance(cls, v):
        """Validate risk tolerance is in enum."""
        if isinstance(v, RiskTolerance):
            return v
        if isinstance(v, str):
            # Try to convert string to enum
            v = v.lower().strip()
            try:
                return RiskTolerance(v)
            except ValueError:
                valid_values = [e.value for e in RiskTolerance]
                raise ValueError(
                    f"Invalid risk_tolerance: {v}. " f"Must be one of: {', '.join(valid_values)}"
                )
        return v

    @property
    def capital_flag(self) -> str:
        """Flag capital as small, medium, or large for gating purposes."""
        if self.capital_initial < Decimal("50000"):
            return "small"
        elif self.capital_initial < Decimal("250000"):
            return "medium"
        else:
            return "large"

    @property
    def is_large_account(self) -> bool:
        """Check if this is a large account (>€250k)."""
        return self.capital_initial >= Decimal("250000")

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/storage."""
        return {
            "input_id": self.input_id,
            "capital_initial": str(self.capital_initial),
            "objetivo_inversion": self.objetivo_inversion.value,
            "risk_tolerance": self.risk_tolerance.value,
            "investment_horizon": self.investment_horizon,
            "constraints": self.constraints,
            "capital_flag": self.capital_flag,
            "is_large_account": self.is_large_account,
        }


class InputProcessor:
    """
    Parse and validate user inputs into InputProfile.

    This is the foundation task (T1.1) - no dependencies.
    Provides clear error messages for invalid inputs.

    Usage:
        processor = InputProcessor()
        profile = processor.process_input({
            "capital_initial": 250000,
            "objetivo_inversion": "maximizar_capital",
            "risk_tolerance": "medio",
            "investment_horizon": 12
        })
    """

    def __init__(self):
        """Initialize processor."""
        self.processed_count = 0
        self.error_count = 0

    def process_input(self, user_input: dict) -> InputProfile:
        """
        Parse and validate user input.

        Args:
            user_input: Dictionary with user parameters

        Returns:
            InputProfile: Validated input profile

        Raises:
            ValueError: If input is invalid (with clear error message)
        """
        try:
            # Validate input is dict
            if not isinstance(user_input, dict):
                raise ValueError(f"Input must be dictionary, got {type(user_input)}")

            # Check required fields
            required_fields = [
                "capital_initial",
                "objetivo_inversion",
                "risk_tolerance",
                "investment_horizon",
            ]
            missing = [f for f in required_fields if f not in user_input]
            if missing:
                raise ValueError(f"Missing required fields: {', '.join(missing)}")

            # Create InputProfile (validates all constraints)
            profile = InputProfile(**user_input)

            logger.info(
                f"Successfully processed input: capital={profile.capital_initial}, "
                f"objetivo={profile.objetivo_inversion.value}, "
                f"risk={profile.risk_tolerance.value}"
            )

            self.processed_count += 1
            return profile

        except ValueError as e:
            self.error_count += 1
            logger.error(f"Input validation error: {e}")
            raise
        except Exception as e:
            self.error_count += 1
            logger.error(f"Unexpected error processing input: {e}")
            raise ValueError(f"Failed to process input: {e}")

    def validate_consistency(self, profile: InputProfile) -> tuple[bool, list[str]]:
        """
        Additional consistency checks beyond field validation.

        Args:
            profile: InputProfile to validate

        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []

        # Check risk tolerance vs objective consistency
        if profile.objetivo_inversion == ObjectivoInversion.CAPITAL_PRESERVATION:
            if profile.risk_tolerance == RiskTolerance.ALTO:
                warnings.append(
                    "Warning: capital_preservation objective with alto risk tolerance "
                    "may be contradictory. Consider lowering risk tolerance."
                )

        # Check investment horizon vs risk tolerance
        if profile.investment_horizon < 12 and profile.risk_tolerance == RiskTolerance.ALTO:
            warnings.append(
                "Warning: short investment horizon (< 12 months) with alto risk tolerance "
                "may expose capital to unnecessary volatility."
            )

        # Check capital size vs objective
        if (
            profile.capital_initial < Decimal("50000")
            and profile.objetivo_inversion == ObjectivoInversion.MAXIMIZAR_DIVIDENDOS
        ):
            warnings.append(
                "Warning: small capital (< €50k) with dividend objective "
                "may have limited diversification."
            )

        is_valid = True
        return is_valid, warnings

    def get_stats(self) -> dict:
        """Get processing statistics."""
        return {
            "processed": self.processed_count,
            "errors": self.error_count,
            "success_rate": (
                self.processed_count / (self.processed_count + self.error_count)
                if (self.processed_count + self.error_count) > 0
                else 0
            ),
        }
