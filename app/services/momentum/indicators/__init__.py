"""
Technical indicator calculators.

Each calculator has a single responsibility:
- SRP: One indicator per calculator class
- OCP: Extensible through new calculator implementations
- LSP: All calculators implement IndicatorCalculator protocol
- ISP: Focused interfaces for specific indicator types
- DIP: Depend on IndicatorCalculator protocol
"""

from app.services.momentum.indicators.calculator import TechnicalIndicatorCalculator

__all__ = ["TechnicalIndicatorCalculator"]
