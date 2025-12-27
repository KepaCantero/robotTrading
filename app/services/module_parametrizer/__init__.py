"""T3.1: ModuleParametrizer - Parametrizes trading modules for investment profiles

Applies profile parameters to 17+ trading modules based on capital tier, objective, and risk.
Implements capital-tier-aware gating to disable expensive/complex modules for small accounts.
"""

from .models import (
    ModuleParameterConfig,
    ModuleParameterSet,
    ParameterizationPreset,
    ParameterizationRequest,
    ParameterizationResult,
)
from .module_parametrizer import ModuleParametrizer, get_module_parametrizer

__all__ = [
    "ModuleParametrizer",
    "get_module_parametrizer",
    "ModuleParameterConfig",
    "ModuleParameterSet",
    "ParameterizationRequest",
    "ParameterizationResult",
    "ParameterizationPreset",
]
