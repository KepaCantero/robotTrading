"""
Strategy Validator Module (FASE 5 Task 1)

This module provides validation for trading strategies based on key performance
metrics as specified by Chan (Algorithmic Trading, 2013):

- Sharpe Ratio >= 1.0 (Chan #8)
- Maximum Drawdown <= 25% (Chan #10)

These are critical acceptance criteria for any viable trading strategy.

Reference:
    Chan, E. (2013). "Algorithmic Trading: Winning Strategies and Their
    Rationale." Wiley, Chapters 8, 10.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    """Severity level of validation result."""

    PASS = "pass"  # Strategy meets all criteria
    FAIL = "fail"  # Strategy fails critical criteria
    WARNING = "warning"  # Strategy passes but with warnings


@dataclass
class ValidationResult:
    """
    Result of strategy validation.

    Attributes:
        is_valid: Whether the strategy passes all validation criteria
        sharpe_ratio: Calculated Sharpe ratio
        max_drawdown: Maximum drawdown (as negative decimal, e.g., -0.15 for -15%)
        sharpe_passes: Whether Sharpe ratio meets threshold (>= 1.0)
        drawdown_passes: Whether max drawdown meets threshold (<= -25%)
        validation_level: Overall validation level (PASS/FAIL/WARNING)
        warnings: List of warning messages
        errors: List of error messages
        metadata: Additional validation metadata
    """

    is_valid: bool
    sharpe_ratio: Optional[Decimal]
    max_drawdown: Optional[Decimal]
    sharpe_passes: bool
    drawdown_passes: bool
    validation_level: ValidationLevel
    warnings: List[str]
    errors: List[str]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_valid": self.is_valid,
            "sharpe_ratio": float(self.sharpe_ratio) if self.sharpe_ratio else None,
            "max_drawdown": float(self.max_drawdown) if self.max_drawdown else None,
            "sharpe_passes": self.sharpe_passes,
            "drawdown_passes": self.drawdown_passes,
            "validation_level": self.validation_level.value,
            "warnings": self.warnings,
            "errors": self.errors,
            "metadata": self.metadata,
        }


class StrategyValidator:
    """
    Validates trading strategies against key performance criteria.

    This validator enforces the critical acceptance criteria from Chan (2013):

    **Sharpe Ratio Threshold (Chan #8):**
    - Minimum Sharpe ratio of 1.0 for out-of-sample performance
    - Sharpe < 1.0 indicates strategy does not provide adequate risk-adjusted returns

    **Maximum Drawdown Threshold (Chan #10):**
    - Maximum drawdown must not exceed 25% (-0.25)
    - Drawdowns > 25% indicate excessive risk exposure

    Example:
        >>> validator = StrategyValidator()
        >>> result = validator.validate(
        ...     sharpe_ratio=Decimal("1.35"),
        ...     max_drawdown=Decimal("-0.18")
        ... )
        >>> if result.is_valid:
        ...     print("Strategy meets acceptance criteria")
    """

    # Minimum Sharpe ratio (Chan #8)
    MIN_SHARPE_RATIO = Decimal("1.0")

    # Maximum acceptable drawdown (Chan #10) - negative for loss
    MAX_MAX_DRAWDOWN = Decimal("-0.25")  # -25%

    def __init__(
        self,
        min_sharpe: Optional[Decimal] = None,
        max_drawdown: Optional[Decimal] = None,
    ):
        """
        Initialize the strategy validator.

        Args:
            min_sharpe: Minimum acceptable Sharpe ratio (default: 1.0)
            max_drawdown: Maximum acceptable drawdown (default: -0.25 for -25%)
        """
        self.min_sharpe = min_sharpe or self.MIN_SHARPE_RATIO
        self.max_drawdown = max_drawdown or self.MAX_MAX_DRAWDOWN

    def validate_sharpe_ratio(self, sharpe: Decimal) -> bool:
        """
        Validate Sharpe ratio against minimum threshold.

        Per Chan (2013), Chapter 8, a Sharpe ratio below 1.0 indicates
        the strategy does not provide adequate risk-adjusted returns to
        justify deployment.

        Args:
            sharpe: Sharpe ratio to validate

        Returns:
            True if Sharpe ratio >= 1.0, False otherwise
        """
        return sharpe >= self.min_sharpe

    def validate_max_drawdown(self, max_dd: Decimal) -> bool:
        """
        Validate maximum drawdown against threshold.

        Per Chan (2013), Chapter 10, maximum drawdown should not exceed 25%
        to ensure acceptable risk exposure. Drawdowns greater than 25% indicate
        the strategy may be over-leveraged or has flawed risk management.

        Args:
            max_dd: Maximum drawdown (negative decimal, e.g., -0.15 for -15%)

        Returns:
            True if max drawdown >= -25% (less negative), False otherwise

        Note:
            Drawdowns are negative numbers representing losses. A drawdown of
            -0.20 (-20%) passes the threshold, while -0.30 (-30%) fails.
        """
        # Less negative is better (e.g., -0.20 > -0.30)
        return max_dd >= self.max_drawdown

    def validate(
        self,
        sharpe_ratio: Optional[Decimal] = None,
        max_drawdown: Optional[Decimal] = None,
        **metadata,
    ) -> ValidationResult:
        """
        Perform complete strategy validation.

        Validates all strategy performance metrics against the acceptance
        criteria. A strategy passes only if ALL criteria are met.

        Args:
            sharpe_ratio: Strategy's Sharpe ratio
            max_drawdown: Strategy's maximum drawdown (negative decimal)
            **metadata: Additional metadata to include in result

        Returns:
            ValidationResult with detailed validation status

        Raises:
            ValueError: If neither sharpe_ratio nor max_drawdown provided
        """
        if sharpe_ratio is None and max_drawdown is None:
            raise ValueError(
                "At least one metric (sharpe_ratio or max_drawdown) must be provided"
            )

        warnings: List[str] = []
        errors: List[str] = []

        # Validate Sharpe ratio
        sharpe_passes = True
        if sharpe_ratio is not None:
            sharpe_passes = self.validate_sharpe_ratio(sharpe_ratio)
            if not sharpe_passes:
                errors.append(
                    f"Sharpe ratio {sharpe_ratio:.2f} below minimum {self.min_sharpe:.2f}"
                )
                warnings.append(
                    "Low Sharpe ratio indicates inadequate risk-adjusted returns (Chan #8)"
                )
            elif sharpe_ratio < Decimal("1.5"):
                warnings.append(
                    f"Sharpe ratio {sharpe_ratio:.2f} is marginal (>= 1.5 recommended)"
                )
        else:
            warnings.append("Sharpe ratio not provided for validation")

        # Validate max drawdown
        drawdown_passes = True
        if max_drawdown is not None:
            drawdown_passes = self.validate_max_drawdown(max_drawdown)
            if not drawdown_passes:
                errors.append(
                    f"Max drawdown {max_drawdown:.2%} exceeds threshold {self.max_drawdown:.2%}"
                )
                warnings.append(
                    "Excessive drawdown indicates over-leveraging or poor risk management (Chan #10)"
                )
            elif max_drawdown < Decimal("-0.20"):
                warnings.append(
                    f"Max drawdown {max_drawdown:.2%} is elevated (>= -20% recommended)"
                )
        else:
            warnings.append("Max drawdown not provided for validation")

        # Determine overall validation level
        is_valid = sharpe_passes and drawdown_passes

        if is_valid:
            validation_level = ValidationLevel.PASS
        elif errors:
            validation_level = ValidationLevel.FAIL
        else:
            validation_level = ValidationLevel.WARNING

        # Build metadata
        result_metadata = {
            "min_sharpe_threshold": float(self.min_sharpe),
            "max_drawdown_threshold": float(self.max_drawdown),
            **metadata,
        }

        return ValidationResult(
            is_valid=is_valid,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            sharpe_passes=sharpe_passes,
            drawdown_passes=drawdown_passes,
            validation_level=validation_level,
            warnings=warnings,
            errors=errors,
            metadata=result_metadata,
        )

    def validate_backtest_result(
        self, backtest_result: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate a backtest result dictionary.

        Convenience method to validate backtest results returned by the
        backtesting engine.

        Args:
            backtest_result: Dictionary containing backtest metrics with keys:
                - 'sharpe_ratio': Sharpe ratio (float or Decimal)
                - 'max_drawdown': Maximum drawdown (float or Decimal, negative)

        Returns:
            ValidationResult with detailed validation status
        """
        sharpe = None
        max_dd = None

        if "sharpe_ratio" in backtest_result:
            sr_value = backtest_result["sharpe_ratio"]
            sharpe = Decimal(str(sr_value)) if sr_value is not None else None

        if "max_drawdown" in backtest_result:
            dd_value = backtest_result["max_drawdown"]
            max_dd = Decimal(str(dd_value)) if dd_value is not None else None

        return self.validate(sharpe_ratio=sharpe, max_drawdown=max_dd)


# Convenience function for quick validation
def validate_strategy(
    sharpe_ratio: Optional[Decimal] = None,
    max_drawdown: Optional[Decimal] = None,
) -> ValidationResult:
    """
    Quick validation function for strategy metrics.

    Args:
        sharpe_ratio: Strategy's Sharpe ratio
        max_drawdown: Strategy's maximum drawdown (negative decimal)

    Returns:
        ValidationResult with detailed validation status
    """
    validator = StrategyValidator()
    return validator.validate(sharpe_ratio=sharpe_ratio, max_drawdown=max_drawdown)


# Module-level exports for common thresholds
MIN_SHARPE_RATIO = Decimal("1.0")  # Chan #8
MAX_MAX_DRAWDOWN = Decimal("-0.25")  # Chan #10 (25% max drawdown)
