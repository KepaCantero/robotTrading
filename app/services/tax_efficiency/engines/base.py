"""
Base Tax Engine - Abstract interface for country-specific tax calculations.

This module defines the abstract base class that all tax engine implementations
must follow. It provides a consistent interface for tax calculations across
different jurisdictions.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


class TaxEngine(ABC):
    """
    Abstract base class for country-specific tax calculations.

    All tax engine implementations must inherit from this class and implement
    the required methods for calculating capital gains taxes, dividend taxes,
    and handling country-specific tax rules.
    """

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize tax engine with optional configuration.

        Args:
            config: Optional configuration dictionary with tax parameters
        """
        self.config = config or {}
        logger.info(f"Initialized {self.__class__.__name__}")

    @abstractmethod
    def calculate_capital_gains_tax(
        self,
        gain: Decimal,
        holding_period_days: int = 0,
    ) -> Decimal:
        """
        Calculate capital gains tax.

        Args:
            gain: Capital gain amount (positive for gains, negative for losses)
            holding_period_days: Holding period in days

        Returns:
            Tax amount
        """

    @abstractmethod
    def calculate_dividend_tax(self, dividend: Decimal) -> Decimal:
        """
        Calculate dividend tax.

        Args:
            dividend: Dividend amount

        Returns:
            Tax amount
        """

    @abstractmethod
    def applies_wash_sale(self) -> bool:
        """
        Check if wash sale rule applies in this jurisdiction.

        Returns:
            True if wash sale rule applies
        """

    def get_tax_summary(self, capital_gains: Decimal, dividends: Decimal) -> dict:
        """
        Get a summary of tax liability.

        Args:
            capital_gains: Total capital gains
            dividends: Total dividends

        Returns:
            Dictionary with tax summary
        """
        capital_gains_tax = self.calculate_capital_gains_tax(capital_gains)
        dividend_tax = self.calculate_dividend_tax(dividends)

        return {
            "capital_gains": float(capital_gains),
            "dividends": float(dividends),
            "capital_gains_tax": float(capital_gains_tax),
            "dividend_tax": float(dividend_tax),
            "total_tax": float(capital_gains_tax + dividend_tax),
            "country": self.__class__.__name__.replace("TaxEngine", ""),
        }

    def get_withholding_tax_rate(self, country: str) -> Decimal:
        """
        Get withholding tax rate for foreign dividends.

        Default implementation returns 0%. Override for country-specific rates.

        Args:
            country: Country code (e.g., "US", "FR", "DE")

        Returns:
            Withholding tax rate
        """
        return Decimal("0")

    def get_tax_brackets(self) -> list[dict]:
        """
        Get all tax brackets for display purposes.

        Returns:
            List of tax bracket dictionaries
        """
        return []

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(config={self.config})"
