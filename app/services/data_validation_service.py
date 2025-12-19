"""
Data Validation Service - TASK-DV-1, DV-2, DV-3, DV-4

Provides comprehensive data quality checks for market data before backtesting:
- Gap detection (price changes >5%)
- Outlier identification (z-score >3)
- OHLC consistency validation
- Pre-backtest data quality checks
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class DataQualityIssue(BaseModel):
    """Represents a single data quality issue."""

    issue_type: str = Field(..., description="Type of issue")
    severity: str = Field(..., description="severity: critical, warning, info")
    timestamp: datetime = Field(..., description="Timestamp of the issue")
    symbol: str = Field(..., description="Symbol affected")
    message: str = Field(..., description="Description of the issue")
    details: Dict = Field(default_factory=dict, description="Additional details")


class DataQualityReport(BaseModel):
    """Complete data quality report."""

    symbol: str
    total_records: int
    issues: List[DataQualityIssue] = Field(default_factory=list)
    gaps_detected: int = 0
    outliers_detected: int = 0
    consistency_errors: int = 0
    is_valid: bool = True
    quality_score: float = 100.0


@dataclass
class OHLCData:
    """OHLC data point for validation."""

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


class DataValidationService:
    """
    Comprehensive data validation service for market data.

    Implements:
    - TASK-DV-1: Gap detection (>5% price changes)
    - TASK-DV-2: Outlier identification (z-score >3)
    - TASK-DV-3: OHLC consistency validation
    - TASK-DV-4: Pre-backtest data quality checks
    """

    def __init__(
        self,
        gap_threshold: float = 0.05,
        outlier_zscore_threshold: float = 3.0,
        consistency_tolerance: float = 0.01,
    ):
        """
        Initialize validation service.

        Args:
            gap_threshold: Threshold for gap detection (default 5%)
            outlier_zscore_threshold: Z-score threshold for outliers (default 3.0)
            consistency_tolerance: Tolerance for price consistency (default 1%)
        """
        self.gap_threshold = gap_threshold
        self.outlier_zscore_threshold = outlier_zscore_threshold
        self.consistency_tolerance = consistency_tolerance

    def detect_price_gaps(self, data: List[OHLCData], symbol: str) -> List[DataQualityIssue]:
        """
        TASK-DV-1: Detect price gaps > threshold.

        A gap is detected when the price change between consecutive bars
        exceeds the threshold (default 5%).

        Args:
            data: List of OHLC data points
            symbol: Symbol to validate

        Returns:
            List of gap issues detected
        """
        issues = []

        for i in range(1, len(data)):
            prev_close = data[i - 1].close
            curr_open = data[i].open

            if prev_close == 0:
                continue

            # Calculate gap as percentage
            gap_pct = abs(float(curr_open - prev_close) / float(prev_close))

            if gap_pct > self.gap_threshold:
                issues.append(
                    DataQualityIssue(
                        issue_type="price_gap",
                        severity="warning",
                        timestamp=data[i].timestamp,
                        symbol=symbol,
                        message=f"Price gap detected: {gap_pct*100:.2f}% "
                        f"(prev_close={prev_close}, curr_open={curr_open})",
                        details={
                            "gap_percentage": gap_pct * 100,
                            "previous_close": float(prev_close),
                            "current_open": float(curr_open),
                            "threshold": self.gap_threshold * 100,
                        },
                    )
                )

        return issues

    def identify_outliers(self, data: List[OHLCData], symbol: str) -> List[DataQualityIssue]:
        """
        TASK-DV-2: Identify outliers using z-score method.

        Calculates z-score for price changes and flags outliers with
        z-score > threshold (default 3.0).

        Args:
            data: List of OHLC data points
            symbol: Symbol to validate

        Returns:
            List of outlier issues detected
        """
        issues = []

        if len(data) < 10:
            # Need at least 10 data points for meaningful z-score calculation
            return issues

        # Calculate price changes
        price_changes = []
        for i in range(1, len(data)):
            change = abs(float(data[i].close - data[i - 1].close) / float(data[i - 1].close))
            price_changes.append(change)

        # Calculate mean and std
        mean_change = sum(price_changes) / len(price_changes)
        variance = sum((x - mean_change) ** 2 for x in price_changes) / len(price_changes)
        std_change = variance**0.5

        if std_change == 0:
            return issues

        # Identify outliers
        for i, change in enumerate(price_changes):
            z_score = abs((change - mean_change) / std_change)

            if z_score > self.outlier_zscore_threshold:
                issues.append(
                    DataQualityIssue(
                        issue_type="outlier",
                        severity="warning",
                        timestamp=data[i + 1].timestamp,
                        symbol=symbol,
                        message=f"Outlier detected: z-score={z_score:.2f}, "
                        f"price_change={change*100:.2f}%",
                        details={
                            "z_score": z_score,
                            "price_change_pct": change * 100,
                            "mean_change": mean_change,
                            "std_change": std_change,
                            "threshold": self.outlier_zscore_threshold,
                        },
                    )
                )

        return issues

    def validate_ohlc_consistency(
        self, data: List[OHLCData], symbol: str
    ) -> List[DataQualityIssue]:
        """
        TASK-DV-3: Validate OHLC consistency.

        Checks:
        - High >= Low
        - Open and Close within [Low, High]
        - Volume >= 0

        Args:
            data: List of OHLC data points
            symbol: Symbol to validate

        Returns:
            List of consistency issues detected
        """
        issues = []

        for ohlc in data:
            # Check high >= low
            if ohlc.high < ohlc.low:
                issues.append(
                    DataQualityIssue(
                        issue_type="consistency_error",
                        severity="critical",
                        timestamp=ohlc.timestamp,
                        symbol=symbol,
                        message=f"High ({ohlc.high}) < Low ({ohlc.low})",
                        details={
                            "high": float(ohlc.high),
                            "low": float(ohlc.low),
                        },
                    )
                )

            # Check open within [low, high]
            if not (ohlc.low <= ohlc.open <= ohlc.high):
                issues.append(
                    DataQualityIssue(
                        issue_type="consistency_error",
                        severity="critical",
                        timestamp=ohlc.timestamp,
                        symbol=symbol,
                        message=f"Open ({ohlc.open}) outside [Low={ohlc.low}, High={ohlc.high}]",
                        details={
                            "open": float(ohlc.open),
                            "low": float(ohlc.low),
                            "high": float(ohlc.high),
                        },
                    )
                )

            # Check close within [low, high]
            if not (ohlc.low <= ohlc.close <= ohlc.high):
                issues.append(
                    DataQualityIssue(
                        issue_type="consistency_error",
                        severity="critical",
                        timestamp=ohlc.timestamp,
                        symbol=symbol,
                        message=f"Close ({ohlc.close}) outside [Low={ohlc.low}, High={ohlc.high}]",
                        details={
                            "close": float(ohlc.close),
                            "low": float(ohlc.low),
                            "high": float(ohlc.high),
                        },
                    )
                )

            # Check volume >= 0
            if ohlc.volume < 0:
                issues.append(
                    DataQualityIssue(
                        issue_type="consistency_error",
                        severity="critical",
                        timestamp=ohlc.timestamp,
                        symbol=symbol,
                        message=f"Volume ({ohlc.volume}) is negative",
                        details={
                            "volume": float(ohlc.volume),
                        },
                    )
                )

        return issues

    def validate_data_quality(self, data: List[OHLCData], symbol: str) -> DataQualityReport:
        """
        TASK-DV-4: Complete data quality check before backtest.

        Runs all validation checks and generates a comprehensive report.

        Args:
            data: List of OHLC data points
            symbol: Symbol to validate

        Returns:
            Complete data quality report
        """
        all_issues = []

        # Run all validation checks
        gap_issues = self.detect_price_gaps(data, symbol)
        outlier_issues = self.identify_outliers(data, symbol)
        consistency_issues = self.validate_ohlc_consistency(data, symbol)

        all_issues.extend(gap_issues)
        all_issues.extend(outlier_issues)
        all_issues.extend(consistency_issues)

        # Count issues by type
        gaps_detected = len([i for i in all_issues if i.issue_type == "price_gap"])
        outliers_detected = len([i for i in all_issues if i.issue_type == "outlier"])
        consistency_errors = len([i for i in all_issues if i.issue_type == "consistency_error"])

        # Calculate quality score
        total_issues = len(all_issues)
        quality_score = max(0, 100 - (total_issues / len(data) * 100))

        # Data is valid if no critical consistency errors
        is_valid = consistency_errors == 0

        return DataQualityReport(
            symbol=symbol,
            total_records=len(data),
            issues=all_issues,
            gaps_detected=gaps_detected,
            outliers_detected=outliers_detected,
            consistency_errors=consistency_errors,
            is_valid=is_valid,
            quality_score=quality_score,
        )

    def validate_bulk_data(
        self, data_dict: Dict[str, List[OHLCData]]
    ) -> Dict[str, DataQualityReport]:
        """
        Validate multiple symbols at once.

        Args:
            data_dict: Dictionary of symbol -> OHLC data list

        Returns:
            Dictionary of symbol -> quality report
        """
        reports = {}

        for symbol, data in data_dict.items():
            reports[symbol] = self.validate_data_quality(data, symbol)

        return reports
