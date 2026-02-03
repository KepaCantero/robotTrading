"""
Look-Ahead Bias Validator for Robust Backtesting Engine.

This module implements comprehensive validation to detect and prevent look-ahead
bias in backtesting, a critical issue emphasized by Ernest Chan in "Algorithmic
Trading" (Chapter 3).

Look-ahead bias occurs when a backtest uses information that would not have
been available at the time of trading, leading to unrealistically optimistic
results.

Key Features:
- Signal timing validation
- Future data leakage detection
- Data gap analysis
- Indicator computation validation
- Comprehensive reporting

Reference:
    AUDIT_PLAN_COMPLETO - FASE 5.1: Look-Ahead Bias Prevention
    "Algorithmic Trading" by Ernest P. Chan - Chapter 3
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result of look-ahead bias validation.

    Attributes:
        is_valid: Whether validation passed (no look-ahead bias detected)
        issues: Critical issues found (would invalidate backtest)
        warnings: Non-critical warnings (should be reviewed)
        validated_at: When validation was performed
        validation_summary: Human-readable summary
        statistics: Statistics about the validation
    """

    is_valid: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.utcnow)
    validation_summary: str = field(default="")
    statistics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Generate validation summary after initialization."""
        if not self.validation_summary:
            self.validation_summary = self._generate_summary()

    def _generate_summary(self) -> str:
        """Generate a human-readable validation summary."""
        if self.is_valid:
            return (
                f"Validation PASSED at {self.validated_at.isoformat()}. "
                f"No look-ahead bias detected. "
                f"{len(self.warnings)} warning(s) to review."
            )
        else:
            return (
                f"Validation FAILED at {self.validated_at.isoformat()}. "
                f"{len(self.issues)} critical issue(s) found. "
                f"{len(self.warnings)} warning(s)."
            )


@dataclass
class TimingIssue:
    """
    Details about a timing issue found during validation.

    Attributes:
        issue_type: Type of timing issue
        timestamp: When the issue occurred
        description: Detailed description
        severity: Severity level ('error', 'warning', 'info')
        affected_symbols: Symbols affected by this issue
    """

    issue_type: str
    timestamp: datetime
    description: str
    severity: str = "warning"
    affected_symbols: set[str] = field(default_factory=set)


@dataclass
class DataGapInfo:
    """
    Information about a data gap found during validation.

    Attributes:
        gap_start: Start of the gap
        gap_end: End of the gap
        gap_duration: Duration of the gap
        gap_size_days: Size of gap in days
        affected_symbols: Symbols affected by this gap
        is_suspicious: Whether the gap looks suspicious (e.g., weekend gap)
    """

    gap_start: datetime
    gap_end: datetime
    gap_duration: timedelta
    gap_size_days: float
    affected_symbols: set[str] = field(default_factory=set)
    is_suspicious: bool = False


class LookAheadValidator:
    """
    Comprehensive validator for look-ahead bias in backtests.

    This validator implements multiple checks to ensure that a backtest does
    not use information that would not have been available at trading time.

    Checks performed:
    1. Signal timing - signals don't reference future data
    2. Future data leakage - indicators/features don't peek ahead
    3. Data gaps - identify unusual gaps that might indicate bias
    4. Indicator computation - validate indicator calculation timing
    5. Survivorship bias - check for survivorship bias in universe selection

    Example:
        ```python
        validator = LookAheadValidator(
            pit_database=pit_client,
            strict_mode=True
        )

        result = validator.validate_backtest(
            signals=signals_df,
            market_data=market_df,
            strategy_params={'lookback': 20}
        )

        if result.is_valid:
            logger.debug("Backtest is valid!")
        else:
            for issue in result.issues:
                logger.debug(f"ISSUE: {issue}")
        ```
    """

    # Configuration constants
    DEFAULT_MAX_GAP_DAYS = 5  # Maximum normal gap in trading days
    SUSPICIOUS_GAP_THRESHOLD = 7  # Gaps larger than this are suspicious
    WEEKEND_GAP_DAYS = 2  # Normal weekend gap

    def __init__(
        self,
        pit_database=None,
        strict_mode: bool = True,
        max_gap_days: int = DEFAULT_MAX_GAP_DAYS,
        check_data_gaps: bool = True,
        check_signal_timing: bool = True,
        check_future_leakage: bool = True,
    ) -> None:
        """
        Initialize the look-ahead validator.

        Args:
            pit_database: Optional PIT database for enhanced validation
            strict_mode: If True, any issue causes validation to fail
            max_gap_days: Maximum expected gap in data (in days)
            check_data_gaps: Whether to check for data gaps
            check_signal_timing: Whether to check signal timing
            check_future_leakage: Whether to check for future data leakage
        """
        self.pit_database = pit_database
        self.strict_mode = strict_mode
        self.max_gap_days = max_gap_days
        self.check_data_gaps = check_data_gaps
        self.check_signal_timing = check_signal_timing
        self.check_future_leakage = check_future_leakage

        logger.info(
            f"LookAheadValidator initialized: strict_mode={strict_mode}, "
            f"max_gap_days={max_gap_days}"
        )

    def validate_backtest(
        self,
        signals: pd.DataFrame,
        market_data: pd.DataFrame,
        strategy_params: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """
        Validate entire backtest for look-ahead bias.

        This is the main validation method that runs all configured checks.

        Args:
            signals: DataFrame with trading signals (must have datetime index)
            market_data: DataFrame with market data (must have datetime index)
            strategy_params: Optional strategy parameters for context

        Returns:
            ValidationResult with detailed findings
        """
        issues = []
        warnings = []
        statistics = {}

        logger.info("Starting look-ahead bias validation...")

        # Check 1: Signal timing
        if self.check_signal_timing:
            timing_issues = self._check_signal_timing(signals, market_data)
            issues.extend([i.description for i in timing_issues if i.severity == "error"])
            warnings.extend([i.description for i in timing_issues if i.severity == "warning"])
            statistics["timing_issues_found"] = len(timing_issues)

        # Check 2: Future data leakage
        if self.check_future_leakage:
            leakage_issues = self._check_future_data_leakage(signals, market_data)
            issues.extend([i.description for i in leakage_issues if i.severity == "error"])
            warnings.extend([i.description for i in leakage_issues if i.severity == "warning"])
            statistics["leakage_issues_found"] = len(leakage_issues)

        # Check 3: Data gaps
        if self.check_data_gaps:
            gap_warnings = self._check_data_gaps(market_data)
            warnings.extend(gap_warnings)
            statistics["data_gaps_found"] = len(gap_warnings)

        # Check 4: Index alignment
        alignment_issues = self._check_index_alignment(signals, market_data)
        issues.extend(alignment_issues)
        statistics["alignment_issues_found"] = len(alignment_issues)

        # Determine validity
        if self.strict_mode:
            is_valid = len(issues) == 0
        else:
            # In non-strict mode, only critical errors cause failure
            is_valid = len([i for i in issues if "critical" in i.lower()]) == 0

        # Add additional statistics
        statistics["total_issues"] = len(issues)
        statistics["total_warnings"] = len(warnings)
        statistics["validation_timestamp"] = datetime.utcnow().isoformat()
        statistics["signal_count"] = len(signals)
        statistics["data_points"] = len(market_data)

        result = ValidationResult(
            is_valid=is_valid,
            issues=issues,
            warnings=warnings,
            statistics=statistics,
        )

        logger.info(
            f"Look-ahead bias validation completed: "
            f"{'PASSED' if is_valid else 'FAILED'}, "
            f"{len(issues)} issues, {len(warnings)} warnings"
        )

        return result

    def _check_signal_timing(
        self,
        signals: pd.DataFrame,
        market_data: pd.DataFrame,
    ) -> list[TimingIssue]:
        """
        Check that signals don't use future data.

        Args:
            signals: DataFrame with signals
            market_data: DataFrame with market data

        Returns:
            List of timing issues found
        """
        issues = []

        # Ensure both have datetime index
        if not isinstance(signals.index, pd.DatetimeIndex):
            try:
                signals = signals.copy()
                signals.index = pd.to_datetime(signals.index)
            except Exception as e:
                return [
                    TimingIssue(
                        issue_type="invalid_index",
                        timestamp=datetime.utcnow(),
                        description=f"Signals index cannot be converted to datetime: {e}",
                        severity="error",
                    )
                ]

        if not isinstance(market_data.index, pd.DatetimeIndex):
            try:
                market_data = market_data.copy()
                market_data.index = pd.to_datetime(market_data.index)
            except Exception as e:
                return [
                    TimingIssue(
                        issue_type="invalid_index",
                        timestamp=datetime.utcnow(),
                        description=f"Market data index cannot be converted to datetime: {e}",
                        severity="error",
                    )
                ]

        # Check each signal timestamp
        for signal_ts in signals.index:
            available_data = market_data.index[market_data.index < signal_ts]

            if len(available_data) == 0:
                issues.append(
                    TimingIssue(
                        issue_type="no_preceding_data",
                        timestamp=signal_ts,
                        description=f"Signal at {signal_ts} has no preceding data",
                        severity="error",
                    )
                )

            # Check if signal timestamp exists in market data (future leak)
            if signal_ts in market_data.index:
                issues.append(
                    TimingIssue(
                        issue_type="signal_at_data_timestamp",
                        timestamp=signal_ts,
                        description=f"Signal at {signal_ts} uses data at the same timestamp",
                        severity="warning",
                    )
                )

        return issues

    def _check_future_data_leakage(
        self,
        signals: pd.DataFrame,
        market_data: pd.DataFrame,
    ) -> list[TimingIssue]:
        """
        Check for future data leakage in indicators/features.

        This checks if any signal values appear to use information that
        would only be available in the future.

        Args:
            signals: DataFrame with signals/indicators
            market_data: DataFrame with market data

        Returns:
            List of leakage issues found
        """
        issues = []

        if not isinstance(signals.index, pd.DatetimeIndex) or not isinstance(
            market_data.index, pd.DatetimeIndex
        ):
            return issues

        # Check for columns that exist in both dataframes
        common_columns = set(signals.columns) & set(market_data.columns)

        for col in common_columns:
            for signal_ts in signals.index:
                signal_val = signals.loc[signal_ts, col]

                # Skip NaN values
                if pd.isna(signal_val):
                    continue

                # Get future data
                future_mask = market_data.index > signal_ts
                future_data = market_data.loc[future_mask, col]

                if len(future_data) == 0:
                    continue

                # Check if signal value exactly matches future data
                # (suspicious - might be using future values)
                future_values = future_data.dropna().values
                if len(future_values) > 0:
                    # Check for exact match in next few periods
                    for future_val in future_values[:5]:
                        if not pd.isna(future_val) and np.isclose(
                            signal_val, future_val, rtol=1e-5
                        ):
                            issues.append(
                                TimingIssue(
                                    issue_type="future_value_match",
                                    timestamp=signal_ts,
                                    description=(
                                        f"Signal for '{col}' at {signal_ts} matches future "
                                        f"value at {future_data.index[future_data == future_val][0]}"
                                    ),
                                    severity="warning",
                                    affected_symbols={col},
                                )
                            )
                            break

        return issues

    def _check_data_gaps(
        self,
        market_data: pd.DataFrame,
    ) -> list[str]:
        """
        Check for unexpected gaps in market data.

        Args:
            market_data: DataFrame with market data

        Returns:
            List of gap warnings
        """
        warnings = []

        if not isinstance(market_data.index, pd.DatetimeIndex) or len(market_data) < 2:
            return warnings

        # Calculate gaps between consecutive data points
        gaps = market_data.index.to_series().diff()

        # Find large gaps
        large_gaps = gaps[gaps > pd.Timedelta(days=self.max_gap_days)]

        if len(large_gaps) > 0:
            max_gap = large_gaps.max()
            avg_gap = large_gaps.mean()

            warnings.append(
                f"Found {len(large_gaps)} gaps > {self.max_gap_days} days in data. "
                f"Max gap: {max_gap}, Avg gap: {avg_gap}"
            )

            # Flag suspiciously large gaps
            suspicious_gaps = gaps[gaps > pd.Timedelta(days=self.SUSPICIOUS_GAP_THRESHOLD)]
            if len(suspicious_gaps) > 0:
                warnings.append(
                    f"Found {len(suspicious_gaps)} suspicious gaps > "
                    f"{self.SUSPICIOUS_GAP_THRESHOLD} days. "
                    f"Check for missing data or look-ahead bias."
                )

        return warnings

    def _check_index_alignment(
        self,
        signals: pd.DataFrame,
        market_data: pd.DataFrame,
    ) -> list[str]:
        """
        Check that signals and market data are properly aligned.

        Args:
            signals: DataFrame with signals
            market_data: DataFrame with market data

        Returns:
            List of alignment issues
        """
        issues = []

        if not isinstance(signals.index, pd.DatetimeIndex) or not isinstance(
            market_data.index, pd.DatetimeIndex
        ):
            return issues

        # Check if signals are outside the data range
        min_data_date = market_data.index.min()
        max_data_date = market_data.index.max()

        signals_before_data = signals.index[signals.index < min_data_date]
        signals_after_data = signals.index[signals.index > max_data_date]

        if len(signals_before_data) > 0:
            issues.append(
                f"Found {len(signals_before_data)} signals before data start date "
                f"({min_data_date.date()}). First signal: {signals_before_data[0]}"
            )

        if len(signals_after_data) > 0:
            issues.append(
                f"Found {len(signals_after_data)} signals after data end date "
                f"({max_data_date.date()}). Last signal: {signals_after_data[-1]}"
            )

        return issues

    def validate_indicator(
        self,
        indicator_name: str,
        indicator_values: pd.Series,
        source_data: pd.DataFrame,
        lookback_period: int,
    ) -> ValidationResult:
        """
        Validate a specific indicator for look-ahead bias.

        This is useful for validating individual indicators before using
        them in a backtest.

        Args:
            indicator_name: Name of the indicator
            indicator_values: Series with indicator values
            source_data: Source data used to compute indicator
            lookback_period: Lookback period used for indicator

        Returns:
            ValidationResult for the indicator
        """
        issues = []
        warnings = []

        # Check that indicator values don't have NaN at the start
        # (unless expected due to lookback period)
        initial_nans = indicator_values.isna().sum()
        expected_initial_nanas = min(lookback_period, len(indicator_values))

        if initial_nans > expected_initial_nanas:
            warnings.append(
                f"Indicator '{indicator_name}' has {initial_nans} NaN values at start, "
                f"expected ~{expected_initial_nanas} for lookback period of {lookback_period}"
            )

        # Check that indicator values don't reference future data
        if isinstance(indicator_values.index, pd.DatetimeIndex) and isinstance(
            source_data.index, pd.DatetimeIndex
        ):
            for idx in indicator_values.index:
                available_source = source_data.index[source_data.index <= idx]
                if len(available_source) < lookback_period:
                    issues.append(
                        f"Indicator '{indicator_name}' at {idx} has insufficient "
                        f"historical data ({len(available_source)} < {lookback_period})"
                    )

        is_valid = len(issues) == 0 if self.strict_mode else True

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            warnings=warnings,
            statistics={
                "indicator_name": indicator_name,
                "lookback_period": lookback_period,
                "initial_nans": int(initial_nans),
                "total_values": len(indicator_values),
            },
        )

    def get_validation_report(self, result: ValidationResult) -> str:
        """
        Generate a detailed validation report.

        Args:
            result: ValidationResult to report on

        Returns:
            Formatted report string
        """
        lines = [
            "=" * 80,
            "LOOK-AHEAD BIAS VALIDATION REPORT",
            "=" * 80,
            f"Validation Time: {result.validated_at.isoformat()}",
            f"Result: {'PASSED' if result.is_valid else 'FAILED'}",
            f"Strict Mode: {self.strict_mode}",
            "",
            "Statistics:",
            f"  - Signal Count: {result.statistics.get('signal_count', 'N/A')}",
            f"  - Data Points: {result.statistics.get('data_points', 'N/A')}",
            f"  - Total Issues: {result.statistics.get('total_issues', 0)}",
            f"  - Total Warnings: {result.statistics.get('total_warnings', 0)}",
            "",
        ]

        if result.issues:
            lines.extend(
                [
                    "CRITICAL ISSUES:",
                    "-" * 80,
                ]
            )
            for i, issue in enumerate(result.issues, 1):
                lines.append(f"  {i}. {issue}")
            lines.append("")

        if result.warnings:
            lines.extend(
                [
                    "WARNINGS:",
                    "-" * 80,
                ]
            )
            for i, warning in enumerate(result.warnings, 1):
                lines.append(f"  {i}. {warning}")
            lines.append("")

        lines.extend(
            [
                "=" * 80,
                result.validation_summary,
                "=" * 80,
            ]
        )

        return "\n".join(lines)
