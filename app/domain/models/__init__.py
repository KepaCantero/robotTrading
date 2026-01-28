"""Domain models for the trading system.

This module contains pure domain models that represent business concepts
without dependencies on external frameworks or infrastructure.

Models:
- InputProfile: User investment parameters and constraints
- InvestmentObjective: User investment goal enum
- RiskTolerance: Risk tolerance level enum
- InputProfileValidator: Validator for creating InputProfile from user input
- StrategyType: Enum of available trading strategies
- RiskConfig: Risk parameters derived from risk tolerance
- TaxConfig: Tax optimization parameters
- SystemConfiguration: Complete system configuration
"""

from app.domain.models.input_profile import (
    InputProfile,
    InputProfileValidator,
    InvestmentObjective,
    RiskTolerance,
)
from app.domain.models.risk_config import RiskConfig
from app.domain.models.strategy_type import StrategyType
from app.domain.models.system_configuration import SystemConfiguration
from app.domain.models.tax_config import TaxConfig

__all__ = [
    "InputProfile",
    "InputProfileValidator",
    "InvestmentObjective",
    "RiskTolerance",
    "StrategyType",
    "RiskConfig",
    "TaxConfig",
    "SystemConfiguration",
]
