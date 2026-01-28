"""
InputProfile Domain Model - User investment parameters

InputProfile represents the validated user input for the trading system.
It's a domain model that captures user investment intent and constraints.

Reference: Rule 05-architecture.md, Rule 02-type-hints.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from app.domain.value_objects.capital import Capital, CapitalTier
from app.domain.value_objects.investment_horizon import (
    HorizonCategory,
    InvestmentHorizon,
)
from app.domain.value_objects.money import Money


class InvestmentObjective(str, Enum):
    """User investment objectives."""

    MAXIMIZE_CAPITAL = "maximize_capital"
    MAXIMIZE_DIVIDENDS = "maximize_dividends"
    CAPITAL_PRESERVATION = "capital_preservation"
    BALANCED_GROWTH = "balanced_growth"
    INCOME_GENERATION = "income_generation"


class RiskTolerance(str, Enum):
    """User risk tolerance levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class InputProfile:
    """
    Domain model for user investment profile.

    InputProfile is the entry point to the parametrization framework.
    It captures and validates user investment parameters.

    This model is immutable to prevent unintended state changes.
    Use the builder pattern or factory methods for creation.
    """

    # Core investment parameters (using value objects) - required
    capital: Capital
    horizon: InvestmentHorizon
    objective: InvestmentObjective
    risk_tolerance: RiskTolerance

    # Optional parameters - with defaults
    constraints: Optional[Dict[str, Any]] = None
    tax_residence: Optional[Any] = None  # TaxResidence from value_objects

    # Identification - with defaults
    input_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(
        default_factory=lambda: __import__("datetime").datetime.now().isoformat()
    )

    def __post_init__(self):
        """Validate input profile invariants."""
        # Validate risk tolerance vs objective consistency
        if self.objective == InvestmentObjective.CAPITAL_PRESERVATION:
            if self.risk_tolerance == RiskTolerance.HIGH:
                raise ValueError(
                    "Capital preservation objective is inconsistent with high risk tolerance"
                )

        # Validate horizon allows for selected strategy
        if self.horizon.is_short_term and self.risk_tolerance == RiskTolerance.HIGH:
            # Warning only - allow but document
            pass

    # Domain behaviors - capital classification
    @property
    def capital_tier(self) -> CapitalTier:
        """Get capital tier for strategy gating."""
        return self.capital.tier

    @property
    def is_small_capital(self) -> bool:
        """Check if this is a small capital account."""
        return self.capital.amount < Decimal("50000")

    @property
    def is_large_capital(self) -> bool:
        """Check if this is a large capital account."""
        return self.capital.amount >= Decimal("250000")

    @property
    def is_institutional(self) -> bool:
        """Check if this is an institutional account."""
        return self.capital.tier == CapitalTier.INSTITUTIONAL

    # Domain behaviors - investment constraints
    @property
    def max_position_size(self) -> Decimal:
        """
        Get maximum position size based on capital and risk tolerance.

        Higher risk tolerance allows larger position sizes.
        """
        base_pct = Decimal("0.05")  # 5% base

        if self.risk_tolerance == RiskTolerance.LOW:
            multiplier = Decimal("0.5")  # 2.5% max
        elif self.risk_tolerance == RiskTolerance.MEDIUM:
            multiplier = Decimal("1.0")  # 5% max
        else:  # HIGH
            multiplier = Decimal("2.0")  # 10% max

        return self.capital.amount * base_pct * multiplier

    @property
    def max_portfolio_exposure(self) -> Decimal:
        """
        Get maximum portfolio exposure based on risk tolerance.

        Returns the percentage of capital that can be deployed at once.
        """
        if self.risk_tolerance == RiskTolerance.LOW:
            return Decimal("0.6")  # 60%
        elif self.risk_tolerance == RiskTolerance.MEDIUM:
            return Decimal("0.8")  # 80%
        else:  # HIGH
            return Decimal("1.0")  # 100%

    @property
    def requires_diversification(self) -> bool:
        """
        Check if portfolio requires strict diversification.

        Larger accounts and conservative profiles need more diversification.
        """
        return self.is_large_capital or self.risk_tolerance == RiskTolerance.LOW

    # Domain behaviors - strategy eligibility
    def allows_strategy(self, strategy_type: str) -> bool:
        """
        Check if profile allows a specific strategy.

        Args:
            strategy_type: Strategy identifier (momentum, pairs, etc.)

        Returns:
            True if strategy is allowed for this profile
        """
        # High-risk strategies require sufficient capital and horizon
        if strategy_type in ["leveraged_etf", "options", "futures"]:
            return self.is_large_capital and self.horizon.allows_high_risk()

        # Dividend strategies require minimum capital
        if strategy_type == "dividend_arbitrage":
            return self.capital.amount >= Decimal("25000")

        # Default: allow
        return True

    def requires_hedging(self) -> bool:
        """
        Check if currency hedging is recommended.

        Returns True if tax residence currency differs from trading currencies.
        """
        if self.tax_residence is None:
            return False

        # If base currency is not USD and trading US stocks, recommend hedging
        return (
            self.tax_residence.base_currency != "USD"
            and self.tax_residence.requires_currency_hedging
        )

    # Domain behaviors - validation
    def validate_consistency(self) -> list[str]:
        """
        Validate internal consistency of profile parameters.

        Returns:
            List of warnings (empty if consistent)
        """
        warnings = []

        # Check risk tolerance vs objective
        if self.objective == InvestmentObjective.CAPITAL_PRESERVATION:
            if self.risk_tolerance == RiskTolerance.HIGH:
                warnings.append(
                    "Capital preservation objective with high risk tolerance "
                    "may lead to inconsistent recommendations"
                )

        # Check horizon vs risk tolerance
        if self.horizon.is_short_term and self.risk_tolerance == RiskTolerance.HIGH:
            warnings.append(
                "Short investment horizon (< 12 months) with high risk tolerance "
                "may expose capital to unnecessary volatility"
            )

        # Check capital size vs objective
        if self.is_small_capital and self.objective == InvestmentObjective.MAXIMIZE_DIVIDENDS:
            warnings.append(
                "Small capital (< €50k) with dividend objective "
                "may have limited diversification opportunities"
            )

        # Check horizon vs objective
        if self.horizon.category == HorizonCategory.VERY_SHORT_TERM:
            if self.objective in [
                InvestmentObjective.MAXIMIZE_CAPITAL,
                InvestmentObjective.MAXIMIZE_DIVIDENDS,
            ]:
                warnings.append(
                    "Very short investment horizon may not allow sufficient time "
                    "for capital appreciation or dividend compounding"
                )

        return warnings

    # Factory methods
    @classmethod
    def create(
        cls,
        capital_amount: Decimal | str | int | float,
        horizon_months: int,
        objective: str | InvestmentObjective,
        risk_tolerance: str | RiskTolerance,
        currency: str = "USD",
        tax_country_code: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> InputProfile:
        """
        Factory method to create InputProfile with type conversions.

        Args:
            capital_amount: Initial capital amount
            horizon_months: Investment horizon in months
            objective: Investment objective
            risk_tolerance: Risk tolerance level
            currency: Base currency
            tax_country_code: ISO country code for tax residence
            constraints: Optional additional constraints

        Returns:
            Validated InputProfile instance
        """
        # Convert capital amount
        if isinstance(capital_amount, str):
            capital_amount = Decimal(capital_amount)
        elif isinstance(capital_amount, (int, float)):
            capital_amount = Decimal(str(capital_amount))

        # Create Capital value object
        capital = Capital.from_amount(Decimal(capital_amount), currency)

        # Create InvestmentHorizon value object
        horizon = InvestmentHorizon.from_months(horizon_months)

        # Convert enums
        if isinstance(objective, str):
            objective = InvestmentObjective(objective.lower())
        if isinstance(risk_tolerance, str):
            # Map Spanish to English
            tolerance_map = {
                "bajo": RiskTolerance.LOW,
                "medio": RiskTolerance.MEDIUM,
                "alto": RiskTolerance.HIGH,
                "low": RiskTolerance.LOW,
                "medium": RiskTolerance.MEDIUM,
                "high": RiskTolerance.HIGH,
            }
            risk_tolerance = tolerance_map.get(risk_tolerance.lower(), RiskTolerance.MEDIUM)

        # Handle tax residence
        tax_residence = None
        if tax_country_code:
            from app.domain.value_objects.tax_residence import TaxResidence

            # Use factory if available
            factory_map = {
                "ES": TaxResidence.spain,
                "US": TaxResidence.usa,
                "UK": TaxResidence.uk,
            }
            factory = factory_map.get(tax_country_code.upper())
            tax_residence = factory() if factory else None

        return cls(
            capital=capital,
            horizon=horizon,
            objective=objective,
            risk_tolerance=risk_tolerance,
            tax_residence=tax_residence,
            constraints=constraints,
        )

    # Serialization
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "input_id": self.input_id,
            "capital": {
                "amount": str(self.capital.amount),
                "currency": self.capital.currency,
                "tier": self.capital.tier.value,
            },
            "horizon": {
                "months": self.horizon.months,
                "years": self.horizon.years,
                "category": self.horizon.category.value,
            },
            "objective": self.objective.value,
            "risk_tolerance": self.risk_tolerance.value,
            "max_position_size": str(self.max_position_size),
            "max_portfolio_exposure": str(self.max_portfolio_exposure),
            "tax_residence": str(self.tax_residence) if self.tax_residence else None,
            "created_at": self.created_at,
        }

    def __str__(self) -> str:
        """String representation."""
        return (
            f"InputProfile(id={self.input_id[:8]}, "
            f"capital={self.capital.amount} {self.capital.currency}, "
            f"objective={self.objective.value}, "
            f"risk={self.risk_tolerance.value})"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"InputProfile(input_id='{self.input_id}', "
            f"capital=Capital(amount={self.capital.amount}, tier='{self.capital.tier.value}'), "
            f"horizon=InvestmentHorizon(months={self.horizon.months}), "
            f"objective={self.objective}, "
            f"risk_tolerance={self.risk_tolerance})"
        )


# Input processor for creating profiles from user input
class InputProfileValidator:
    """
    Validator for creating InputProfile from user input.

    This class handles validation and conversion of user input
    into a proper InputProfile domain model.
    """

    def __init__(self) -> None:
        """Initialize validator."""
        self._validated_count = 0
        self._error_count = 0

    def validate(
        self,
        user_input: Dict[str, Any],
    ) -> tuple[InputProfile, list[str]]:
        """
        Validate and create InputProfile from user input.

        Args:
            user_input: Dictionary with user parameters

        Returns:
            Tuple of (InputProfile, warnings)

        Raises:
            ValueError: If input is invalid
        """
        # Check required fields
        required_fields = [
            "capital_initial",
            "investment_horizon",
            "objetivo_inversion",
            "risk_tolerance",
        ]
        missing = [f for f in required_fields if f not in user_input]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        # Extract parameters
        capital = user_input["capital_initial"]
        horizon = user_input["investment_horizon"]

        # Map objective names (support both Spanish and English)
        objective_map = {
            "maximizar_capital": InvestmentObjective.MAXIMIZE_CAPITAL,
            "maximize_capital": InvestmentObjective.MAXIMIZE_CAPITAL,
            "maximizar_dividendos": InvestmentObjective.MAXIMIZE_DIVIDENDS,
            "maximize_dividends": InvestmentObjective.MAXIMIZE_DIVIDENDS,
            "capital_preservation": InvestmentObjective.CAPITAL_PRESERVATION,
            "balanced_growth": InvestmentObjective.BALANCED_GROWTH,
            "income_generation": InvestmentObjective.INCOME_GENERATION,
        }
        objective_raw = user_input["objetivo_inversion"]
        objective = objective_map.get(
            objective_raw.lower() if isinstance(objective_raw, str) else objective_raw,
            InvestmentObjective.BALANCED_GROWTH,
        )

        # Create profile
        profile = InputProfile.create(
            capital_amount=capital,
            horizon_months=horizon,
            objective=objective,
            risk_tolerance=user_input["risk_tolerance"],
            currency=user_input.get("currency", "USD"),
            tax_country_code=user_input.get("tax_country"),
            constraints=user_input.get("constraints"),
        )

        # Validate consistency
        warnings = profile.validate_consistency()

        self._validated_count += 1
        return profile, warnings

    @property
    def stats(self) -> Dict[str, int]:
        """Get validation statistics."""
        return {
            "validated": self._validated_count,
            "errors": self._error_count,
        }
