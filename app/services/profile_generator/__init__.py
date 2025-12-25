"""T2.1: ProfileGenerator - Maps user input to investment profiles

Generates investment profiles based on user capital, objective, and risk tolerance.
"""

from .profile_generator import (
    ProfileGenerator,
    get_profile_generator,
)
from .models import (
    CapitalTier,
    InvestmentObjective,
    RiskProfile,
    InvestmentProfile,
    ModuleConfig,
    ProfileGenerationRequest,
    ProfileGenerationResult,
)

__all__ = [
    "ProfileGenerator",
    "get_profile_generator",
    "CapitalTier",
    "InvestmentObjective",
    "RiskProfile",
    "InvestmentProfile",
    "ModuleConfig",
    "ProfileGenerationRequest",
    "ProfileGenerationResult",
]
