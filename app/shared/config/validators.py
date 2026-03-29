"""
Configuration Validators

Implements ConfigValidator protocol with specific validation logic.
Each validator has a single responsibility: validating specific config aspects.

TASK-24: SRP Compliance - Separate validators for different aspects
"""

import logging
from datetime import datetime
from typing import Any

from app.shared.config.protocols import ConfigValidator

logger = logging.getLogger(__name__)


class ATRMultiplierValidator:
    """Validates ATR multiplier configuration."""

    def __init__(self):
        self._errors: list[str] = []

    def validate(self, config: dict[str, Any]) -> bool:
        """
        Validate ATR multiplier configuration.

        Args:
            config: Dictionary of ATR multiplier names to values

        Returns:
            True if all multipliers are positive, False otherwise
        """
        self._errors = []

        if not config:
            self._errors.append("ATR multipliers configuration is empty")
            return False

        is_valid = True
        for key, value in config.items():
            if not isinstance(value, (int, float)):
                self._errors.append(f"ATR multiplier '{key}' is not a number")
                is_valid = False
            elif value <= 0:
                self._errors.append(f"ATR multiplier '{key}' must be positive, got {value}")
                is_valid = False

        return is_valid

    def get_errors(self) -> list[str]:
        """Get validation errors."""
        return self._errors.copy()


class RiskPercentageValidator:
    """Validates risk percentage configuration."""

    def __init__(self):
        self._errors: list[str] = []

    def validate(self, config: dict[str, Any]) -> bool:
        """
        Validate risk percentage configuration.

        Args:
            config: Dictionary of risk configuration values

        Returns:
            True if all percentages are between 0 and 1, False otherwise
        """
        self._errors = []

        if not config:
            self._errors.append("Risk percentage configuration is empty")
            return False

        is_valid = True
        for key, value in config.items():
            if not isinstance(value, (int, float)):
                self._errors.append(f"Risk percentage '{key}' is not a number")
                is_valid = False
            elif not (0 < value <= 1.0):
                self._errors.append(f"Risk percentage '{key}' must be between 0 and 1, got {value}")
                is_valid = False

        return is_valid

    def get_errors(self) -> list[str]:
        """Get validation errors."""
        return self._errors.copy()


class TradingSymbolsValidator:
    """Validates trading symbols list."""

    def __init__(self):
        self._errors: list[str] = []

    def validate(self, config: dict[str, Any]) -> bool:
        """
        Validate trading symbols list.

        Args:
            config: Dictionary with 'symbols' key containing list of symbols

        Returns:
            True if symbols list is valid (non-empty, unique items), False otherwise
        """
        self._errors = []

        symbols = config.get("symbols", [])
        if not symbols or not isinstance(symbols, list):
            self._errors.append("Symbols list is empty or not a list")
            return False

        # Check for non-empty and all strings
        for symbol in symbols:
            if not isinstance(symbol, str) or not symbol.strip():
                self._errors.append(f"Invalid symbol: {symbol}")
                return False

        # Check for duplicates
        if len(symbols) != len(set(symbols)):
            self._errors.append("Duplicate symbols found in list")
            return False

        return True

    def get_errors(self) -> list[str]:
        """Get validation errors."""
        return self._errors.copy()


class DateRangeValidator:
    """Validates backtesting date configuration."""

    def __init__(self):
        self._errors: list[str] = []

    def validate(self, config: dict[str, Any]) -> bool:
        """
        Validate backtesting date configuration.

        Args:
            config: Dictionary containing start_date and end_date

        Returns:
            True if dates are valid and in correct order, False otherwise
        """
        self._errors = []

        if not config:
            self._errors.append("Date configuration is empty")
            return False

        start_date = config.get("start_date")
        end_date = config.get("end_date")

        if not start_date or not end_date:
            self._errors.append("Both start_date and end_date are required")
            return False

        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            if start >= end:
                self._errors.append(
                    f"Start date ({start_date}) must be before end date ({end_date})"
                )
                return False

            return True
        except (ValueError, TypeError) as e:
            self._errors.append(f"Invalid date format: {e}")
            return False

    def get_errors(self) -> list[str]:
        """Get validation errors."""
        return self._errors.copy()


class CompositeConfigValidator:
    """
    Composite validator that combines multiple validators.
    Validates complete configuration objects.
    """

    def __init__(self):
        self._validators: dict[str, ConfigValidator] = {
            "atr_multipliers": ATRMultiplierValidator(),
            "risk_percentages": RiskPercentageValidator(),
            "trading_symbols": TradingSymbolsValidator(),
            "date_range": DateRangeValidator(),
        }
        self._errors: list[str] = []

    def validate(self, config: dict[str, Any]) -> bool:
        """
        Validate complete configuration object.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if all validations pass, False otherwise
        """
        self._errors = []
        is_valid = True

        # Validate risk management section
        if "risk_management" in config:
            rm = config["risk_management"]

            if "atr_multipliers" in rm and not self._validators["atr_multipliers"].validate(
                rm["atr_multipliers"]
            ):
                self._errors.extend(self._validators["atr_multipliers"].get_errors())
                is_valid = False

            if "position_sizing" in rm and not self._validators["risk_percentages"].validate(
                rm["position_sizing"]
            ):
                self._errors.extend(self._validators["risk_percentages"].get_errors())
                is_valid = False

        # Validate trading section
        if "trading" in config and not self._validators["trading_symbols"].validate(
            config["trading"]
        ):
            self._errors.extend(self._validators["trading_symbols"].get_errors())
            is_valid = False

        # Validate backtesting section
        if "backtesting" in config and not self._validators["date_range"].validate(
            config["backtesting"]
        ):
            self._errors.extend(self._validators["date_range"].get_errors())
            is_valid = False

        return is_valid

    def get_errors(self) -> list[str]:
        """Get all validation errors."""
        return self._errors.copy()

    def register_validator(self, name: str, validator: ConfigValidator) -> None:
        """Register a custom validator."""
        self._validators[name] = validator
