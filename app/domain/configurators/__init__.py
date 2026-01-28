"""
Domain Configurators Package.

This package contains configurator classes that translate user preferences
into concrete configuration parameters.

Modules:
    risk_config: RiskConfig value object containing risk parameters
    risk_configurator: RiskConfigurator for mapping risk tolerance to config
"""

from app.domain.configurators.risk_config import RiskConfig
from app.domain.configurators.risk_configurator import RiskConfigurator

__all__ = [
    "RiskConfig",
    "RiskConfigurator",
]
