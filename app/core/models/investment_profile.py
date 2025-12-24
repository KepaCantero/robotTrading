"""
T2.1: InvestmentProfile - Investment Strategy Profile Generated from User Input

Maps user InputProfile → InvestmentProfile with dynamically generated strategy parameters.

Capabilities:
- Maps capital tier (micro|small|medium|large) to user capital
- Applies objective-specific parameter mappings
- Selects modules based on capital & objective
- Determines leverage & risk scaling factors
"""

import logging
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance

logger = logging.getLogger(__name__)


class CapitalTier(str, Enum):
    """Capital-based account tier classification."""

    MICRO = "micro"      # < €15k
    SMALL = "small"      # €15k-€50k
    MEDIUM = "medium"    # €50k-€250k
    LARGE = "large"      # >= €250k


class InvestmentProfile(BaseModel):
    """
    Investment strategy profile generated from user InputProfile.

    This is the "intelligence" layer - determines which modules activate
    based on capital tier and user objective_inversion.

    Generated from InputProfile, provides parameters for T3.1 (ModuleParametrizer).
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    # Identification
    profile_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this investment profile"
    )
    input_id: str = Field(
        ...,
        description="Reference to source InputProfile"
    )

    # Capital Classification
    capital_initial: Decimal = Field(
        ...,
        gt=Decimal("0"),
        description="Initial capital in EUR"
    )
    capital_tier: CapitalTier = Field(
        ...,
        description="Tier classification (micro|small|medium|large)"
    )

    # User Objectives
    objetivo_inversion: ObjectivoInversion = Field(
        ...,
        description="Investment objective mapped from user input"
    )
    risk_tolerance: RiskTolerance = Field(
        ...,
        description="Risk tolerance level"
    )

    # Investment Profile Parameters
    risk_profile: int = Field(
        ...,
        ge=1,
        le=7,
        description="Risk scale 1-7 (conservative=1, aggressive=7)"
    )

    investment_horizon: int = Field(
        ...,
        ge=1,
        le=600,
        description="Investment horizon in months"
    )

    # Module Activation
    enabled_modules: List[str] = Field(
        ...,
        description="Which strategy modules to activate based on capital tier & objective"
    )

    # Risk & Leverage
    leverage_factor: Decimal = Field(
        default=Decimal("1.0"),
        ge=Decimal("0"),
        le=Decimal("3.0"),
        description="Leverage factor (1.0 = no leverage, 2.5 = max recommended)"
    )

    max_position_size: Decimal = Field(
        ...,
        gt=Decimal("0"),
        description="Maximum position size as % of capital (0.0-1.0)"
    )

    max_sector_allocation: Decimal = Field(
        default=Decimal("0.30"),
        ge=Decimal("0"),
        le=Decimal("1.0"),
        description="Max allocation to single sector"
    )

    # Execution Parameters
    order_splitting_strategy: str = Field(
        default="vwap",
        description="Order splitting strategy (vwap|twap|poi)"
    )

    commission_negotiation: bool = Field(
        default=True,
        description="Whether to negotiate commissions by volume"
    )

    # Risk Scaling
    risk_scaling_enabled: bool = Field(
        default=False,
        description="Whether to apply dynamic risk scaling (if PHASE 3 available)"
    )

    volatility_scale_range: tuple = Field(
        default=(Decimal("0.5"), Decimal("1.5")),
        description="Range for volatility-based position scaling"
    )

    # Metadata
    created_at: str = Field(
        default_factory=lambda: __import__('datetime').datetime.now().isoformat(),
        description="Timestamp of profile generation"
    )

    @field_validator('capital_tier', mode='before')
    @classmethod
    def validate_capital_tier(cls, v):
        """Validate capital tier is in enum."""
        if isinstance(v, CapitalTier):
            return v
        if isinstance(v, str):
            try:
                return CapitalTier(v.lower())
            except ValueError:
                valid = [e.value for e in CapitalTier]
                raise ValueError(f"Invalid capital tier: {v}. Must be one of: {', '.join(valid)}")
        return v

    @field_validator('objetivo_inversion', mode='before')
    @classmethod
    def validate_objetivo(cls, v):
        """Validate objective is in enum."""
        if isinstance(v, ObjectivoInversion):
            return v
        if isinstance(v, str):
            try:
                return ObjectivoInversion(v.lower().strip())
            except ValueError:
                valid = [e.value for e in ObjectivoInversion]
                raise ValueError(f"Invalid objetivo: {v}. Must be one of: {', '.join(valid)}")
        return v

    @field_validator('risk_tolerance', mode='before')
    @classmethod
    def validate_risk_tolerance(cls, v):
        """Validate risk tolerance is in enum."""
        if isinstance(v, RiskTolerance):
            return v
        if isinstance(v, str):
            try:
                return RiskTolerance(v.lower().strip())
            except ValueError:
                valid = [e.value for e in RiskTolerance]
                raise ValueError(f"Invalid risk_tolerance: {v}. Must be one of: {', '.join(valid)}")
        return v

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/storage."""
        return {
            "profile_id": self.profile_id,
            "input_id": self.input_id,
            "capital_initial": str(self.capital_initial),
            "capital_tier": self.capital_tier.value,
            "objetivo_inversion": self.objetivo_inversion.value,
            "risk_tolerance": self.risk_tolerance.value,
            "risk_profile": self.risk_profile,
            "investment_horizon": self.investment_horizon,
            "enabled_modules": self.enabled_modules,
            "leverage_factor": str(self.leverage_factor),
            "max_position_size": str(self.max_position_size),
            "max_sector_allocation": str(self.max_sector_allocation),
            "order_splitting_strategy": self.order_splitting_strategy,
            "commission_negotiation": self.commission_negotiation,
            "risk_scaling_enabled": self.risk_scaling_enabled,
        }


class ProfileGenerator:
    """
    Generate InvestmentProfile from InputProfile using configuration-driven mapping.

    Maps:
    - Capital → CapitalTier
    - (CapitalTier, ObjectivoInversion) → Strategy Parameters
    - Capital & Objective → Module Activation
    """

    def __init__(self, config: Dict):
        """
        Initialize ProfileGenerator with config.

        Args:
            config: Investment profiles configuration (either raw dict or dict with 'profiles' key)
        """
        # Handle both formats: raw profiles dict or dict with 'profiles' key
        if 'profiles' in config:
            self.config = config['profiles']
        else:
            self.config = config
        logger.info("ProfileGenerator initialized with configuration")

    @staticmethod
    def determine_capital_tier(capital: Decimal) -> CapitalTier:
        """Classify capital into tiers."""
        if capital < Decimal("15000"):
            return CapitalTier.MICRO
        elif capital < Decimal("50000"):
            return CapitalTier.SMALL
        elif capital < Decimal("250000"):
            return CapitalTier.MEDIUM
        else:
            return CapitalTier.LARGE

    def generate(self, input_profile: InputProfile) -> InvestmentProfile:
        """
        Generate InvestmentProfile from InputProfile.

        Args:
            input_profile: User input (capital, objective, risk tolerance, horizon)

        Returns:
            InvestmentProfile: Generated investment strategy profile

        Raises:
            ValueError: If configuration invalid or objective not supported
        """
        try:
            # 1. Determine capital tier
            capital_tier = self.determine_capital_tier(input_profile.capital_initial)

            # 2. Load profile config for objective + tier
            objective_value = input_profile.objetivo_inversion.value
            if objective_value not in self.config:
                raise ValueError(f"Objective not configured: {objective_value}")

            tier_value = capital_tier.value
            if tier_value not in self.config[objective_value]:
                raise ValueError(
                    f"No configuration for {objective_value} + {tier_value}"
                )

            profile_config = self.config[objective_value][tier_value]

            # 3. Extract parameters
            risk_profile = profile_config.get("risk_profile", 4)
            enabled_modules = profile_config.get("enabled_modules", [])
            leverage = Decimal(str(profile_config.get("leverage", 1.0)))
            max_position = Decimal(str(profile_config.get("max_position_size", 0.25)))
            max_sector = Decimal(str(profile_config.get("max_sector_allocation", 0.30)))
            order_splitting = profile_config.get("order_splitting_strategy", "vwap")
            commission_negotiation = profile_config.get("commission_negotiation", True)

            # 4. Determine if risk scaling available (check if PHASE 3 exists)
            risk_scaling_enabled = self._check_risk_scaling_available()

            # 5. Create InvestmentProfile
            investment_profile = InvestmentProfile(
                profile_id=str(__import__('uuid').uuid4()),
                input_id=input_profile.input_id,
                capital_initial=input_profile.capital_initial,
                capital_tier=capital_tier,
                objetivo_inversion=input_profile.objetivo_inversion,
                risk_tolerance=input_profile.risk_tolerance,
                risk_profile=risk_profile,
                investment_horizon=input_profile.investment_horizon,
                enabled_modules=enabled_modules,
                leverage_factor=leverage,
                max_position_size=max_position,
                max_sector_allocation=max_sector,
                order_splitting_strategy=order_splitting,
                commission_negotiation=commission_negotiation,
                risk_scaling_enabled=risk_scaling_enabled,
            )

            logger.info(
                f"Generated InvestmentProfile: tier={capital_tier.value}, "
                f"objetivo={objective_value}, modules={len(enabled_modules)}"
            )

            return investment_profile

        except Exception as e:
            logger.error(f"Failed to generate InvestmentProfile: {e}")
            raise

    @staticmethod
    def _check_risk_scaling_available() -> bool:
        """Check if PHASE 3 (risk scaling) is available in codebase."""
        import os
        path = "/Users/kepa.cantero/Projects/algoTrading/app/services/risk_scaling"
        return os.path.exists(path)
