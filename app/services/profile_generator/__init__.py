"""T2.1: ProfileGenerator - Maps user input to investment profiles

Generates investment profiles based on user capital, objective, and risk tolerance.
"""

from .models import (
    CapitalTier,
    InvestmentObjective,
    InvestmentProfile,
    ModuleConfig,
    ProfileGenerationRequest,
    ProfileGenerationResult,
    RiskProfile,
)
from .profile_generator import ProfileGenerator, get_profile_generator

__all__ = [
    "CapitalTier",
    "InvestmentObjective",
    "InvestmentProfile",
    "ModuleConfig",
    "ProfileGenerationRequest",
    "ProfileGenerationResult",
    "ProfileGenerator",
    "RiskProfile",
    "get_profile_generator",
]
