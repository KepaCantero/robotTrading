"""
Test Summary Report Generator for Backtesting Tests

This module provides comprehensive test summary reporting for backtesting tests.
It captures test metadata, input data, configuration, output metrics, and validation
results in both JSON (machine-readable) and human-readable formats.

Example Usage:
    ```python
    from app.backtesting.test_summary import TestSummaryReporter, TestMetadata

    # Create reporter
    reporter = TestSummaryReporter()

    # Create test metadata
    metadata = TestMetadata(
        test_name="test_backtest_basic",
        test_description="Basic backtest with GBM data",
        test_file="test_backtest_basic.py",
        test_type="integration"
    )

    # Add input data
    reporter.add_input_data(
        symbols=["AAPL"],
        date_range=(datetime(2023, 1, 1), datetime(2023, 12, 31)),
        data_points=500,
        market_regime="bullish",
        data_source="GBM simulation (drift=5%, vol=20%)"
    )

    # Add configuration
    reporter.add_config(
        initial_capital=Decimal("100000"),
        commission=Decimal("1.0"),
        slippage=Decimal("0.1"),
        strategy="SMA Crossover"
    )

    # Add results
    reporter.add_results(
        final_capital=Decimal("115000"),
        total_pnl=Decimal("15000"),
        sharpe_ratio=Decimal("1.5"),
        max_drawdown=Decimal("-0.08"),
        win_rate=Decimal("60.0"),
        total_trades=50
    )

    # Mark as passed with reason
    reporter.mark_passed("All metrics within acceptable ranges")

    # Generate and save reports
    reporter.save_reports()
    ```
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


class TestMetadata(BaseModel):
    """Metadata about the test."""

    test_name: str = Field(..., description="Test function name")
    test_description: str = Field(..., description="Test description")
    test_file: str = Field(..., description="Test file path")
    test_type: str = Field(
        ...,
        description="Test type (unit, integration, functional)",
    )
    test_id: Optional[str] = Field(None, description="Unique test identifier")
    author: Optional[str] = Field(None, description="Test author")
    tags: List[str] = Field(default_factory=list, description="Test tags")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")


class InputDataSummary(BaseModel):
    """Summary of input data used in the test."""

    symbols: List[str] = Field(..., description="Trading symbols tested")
    date_range: Tuple[datetime, datetime] = Field(..., description="Date range (start, end)")
    data_points: int = Field(..., ge=0, description="Number of data points")
    market_regime: str = Field(..., description="Market regime description")
    data_source: str = Field(..., description="Data source description")
    price_range: Optional[Tuple[Decimal, Decimal]] = Field(None, description="Price range (min, max)")
    volume_stats: Optional[Dict[str, Decimal]] = Field(None, description="Volume statistics")
    volatility: Optional[Decimal] = Field(None, description="Volatility measure")
    notes: List[str] = Field(default_factory=list, description="Additional notes about data")


class TestConfig(BaseModel):
    """Test configuration parameters."""

    initial_capital: Decimal = Field(..., gt=0, description="Initial capital")
    commission: Decimal = Field(..., ge=0, description="Commission per trade")
    slippage: Decimal = Field(..., ge=0, description="Slippage percentage")
    strategy: str = Field(..., description="Strategy name")
    strategy_params: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")
    risk_management: Optional[Dict[str, Decimal]] = Field(None, description="Risk management settings")
    additional_params: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")


class OutputMetrics(BaseModel):
    """Output metrics from the test."""

    # Basic metrics
    final_capital: Decimal = Field(..., description="Final capital")
    total_pnl: Decimal = Field(..., description="Total profit/loss")
    total_pnl_percentage: Optional[Decimal] = Field(None, description="Total P&L percentage")

    # Risk metrics
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio")
    sortino_ratio: Optional[Decimal] = Field(None, description="Sortino ratio")
    max_drawdown: Optional[Decimal] = Field(None, description="Maximum drawdown")
    max_drawdown_percentage: Optional[Decimal] = Field(None, description="Max drawdown percentage")

    # Trade metrics
    win_rate: Optional[Decimal] = Field(None, description="Win rate percentage")
    total_trades: int = Field(..., ge=0, description="Total number of trades")
    winning_trades: int = Field(0, ge=0, description="Number of winning trades")
    losing_trades: int = Field(0, ge=0, description="Number of losing trades")

    # Advanced metrics
    calmar_ratio: Optional[Decimal] = Field(None, description="Calmar ratio")
    omega_ratio: Optional[Decimal] = Field(None, description="Omega ratio")
    profit_factor: Optional[Decimal] = Field(None, description="Profit factor")
    expectancy: Optional[Decimal] = Field(None, description="Expectancy per trade")

    # Additional metrics
    additional_metrics: Dict[str, Union[Decimal, float, int, str]] = Field(
        default_factory=dict, description="Additional metrics"
    )


class ValidationCriteria(BaseModel):
    """Validation criteria for test results."""

    criteria_name: str = Field(..., description="Criteria name")
    expected_value: Union[Decimal, float, int, str, bool] = Field(..., description="Expected value")
    actual_value: Union[Decimal, float, int, str, bool] = Field(..., description="Actual value")
    passed: bool = Field(..., description="Whether criteria passed")
    tolerance: Optional[Decimal] = Field(None, description="Tolerance for comparison")
    reason: Optional[str] = Field(None, description="Reason for failure if not passed")


class TestSummaryReport(BaseModel):
    """Complete test summary report."""

    # Test metadata
    metadata: TestMetadata = Field(..., description="Test metadata")

    # Input data
    input_data: InputDataSummary = Field(..., description="Input data summary")

    # Configuration
    config: TestConfig = Field(..., description="Test configuration")

    # Output metrics
    output: OutputMetrics = Field(..., description="Output metrics")

    # Validation results
    validation_criteria: List[ValidationCriteria] = Field(
        default_factory=list, description="Validation criteria results"
    )

    # Test status
    passed: bool = Field(..., description="Whether test passed")
    pass_reason: Optional[str] = Field(None, description="Reason for pass/fail")

    # Warnings and anomalies
    warnings: List[str] = Field(default_factory=list, description="Warnings generated during test")
    anomalies: List[str] = Field(default_factory=list, description="Anomalies detected")

    # Timing information
    start_time: datetime = Field(default_factory=datetime.now, description="Test start time")
    end_time: Optional[datetime] = Field(None, description="Test end time")
    duration_seconds: Optional[float] = Field(None, description="Test duration in seconds")

    # Additional information
    notes: List[str] = Field(default_factory=list, description="Additional notes")
    attachments: List[str] = Field(default_factory=list, description="Paths to attachments (charts, etc)")


# ============================================================================
# Reporter Class
# ============================================================================


class TestSummaryReporter:
    """
    Test summary reporter for backtesting tests.

    This class collects test information and generates comprehensive summary
    reports in both JSON and human-readable formats.
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        test_name: Optional[str] = None,
        test_description: Optional[str] = None,
        test_file: Optional[str] = None,
        test_type: str = "integration",
    ):
        """
        Initialize the test summary reporter.

        Args:
            output_dir: Directory to save reports (default: reports/test_summaries/)
            test_name: Name of the test
            test_description: Description of the test
            test_file: File containing the test
            test_type: Type of test (unit, integration, functional)
        """
        self.output_dir = output_dir or Path("reports/test_summaries")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate test ID from timestamp if not provided
        test_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Initialize metadata
        self.metadata = TestMetadata(
            test_name=test_name or "unknown_test",
            test_description=test_description or "No description provided",
            test_file=test_file or "unknown.py",
            test_type=test_type,
            test_id=test_id,
        )

        # Initialize placeholders
        self.input_data: Optional[InputDataSummary] = None
        self.config: Optional[TestConfig] = None
        self.output: Optional[OutputMetrics] = None
        self.validation_criteria: List[ValidationCriteria] = []
        self.warnings: List[str] = []
        self.anomalies: List[str] = []
        self.notes: List[str] = []
        self.attachments: List[str] = []

        # Timing
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.passed: Optional[bool] = None
        self.pass_reason: Optional[str] = None

    def add_input_data(
        self,
        symbols: List[str],
        date_range: Tuple[datetime, datetime],
        data_points: int,
        market_regime: str,
        data_source: str,
        price_range: Optional[Tuple[Decimal, Decimal]] = None,
        volume_stats: Optional[Dict[str, Decimal]] = None,
        volatility: Optional[Decimal] = None,
        notes: Optional[List[str]] = None,
    ) -> None:
        """
        Add input data summary.

        Args:
            symbols: Trading symbols tested
            date_range: Date range (start, end)
            data_points: Number of data points
            market_regime: Market regime description
            data_source: Data source description
            price_range: Price range (min, max)
            volume_stats: Volume statistics
            volatility: Volatility measure
            notes: Additional notes about data
        """
        self.input_data = InputDataSummary(
            symbols=symbols,
            date_range=date_range,
            data_points=data_points,
            market_regime=market_regime,
            data_source=data_source,
            price_range=price_range,
            volume_stats=volume_stats,
            volatility=volatility,
            notes=notes or [],
        )
        logger.debug(f"Added input data: {len(symbols)} symbols, {data_points} data points")

    def add_config(
        self,
        initial_capital: Decimal,
        commission: Decimal,
        slippage: Decimal,
        strategy: str,
        strategy_params: Optional[Dict[str, Any]] = None,
        risk_management: Optional[Dict[str, Decimal]] = None,
        **kwargs,
    ) -> None:
        """
        Add test configuration.

        Args:
            initial_capital: Initial capital
            commission: Commission per trade
            slippage: Slippage percentage
            strategy: Strategy name
            strategy_params: Strategy parameters
            risk_management: Risk management settings
            **kwargs: Additional configuration parameters
        """
        self.config = TestConfig(
            initial_capital=initial_capital,
            commission=commission,
            slippage=slippage,
            strategy=strategy,
            strategy_params=strategy_params or {},
            risk_management=risk_management,
            additional_params=kwargs,
        )
        logger.debug(f"Added config: {strategy} with ${initial_capital} capital")

    def add_results(
        self,
        final_capital: Decimal,
        total_pnl: Decimal,
        total_pnl_percentage: Optional[Decimal] = None,
        sharpe_ratio: Optional[Decimal] = None,
        sortino_ratio: Optional[Decimal] = None,
        max_drawdown: Optional[Decimal] = None,
        max_drawdown_percentage: Optional[Decimal] = None,
        win_rate: Optional[Decimal] = None,
        total_trades: int = 0,
        winning_trades: int = 0,
        losing_trades: int = 0,
        calmar_ratio: Optional[Decimal] = None,
        omega_ratio: Optional[Decimal] = None,
        profit_factor: Optional[Decimal] = None,
        expectancy: Optional[Decimal] = None,
        **kwargs,
    ) -> None:
        """
        Add test results/metrics.

        Args:
            final_capital: Final capital
            total_pnl: Total profit/loss
            total_pnl_percentage: Total P&L percentage
            sharpe_ratio: Sharpe ratio
            sortino_ratio: Sortino ratio
            max_drawdown: Maximum drawdown
            max_drawdown_percentage: Max drawdown percentage
            win_rate: Win rate percentage
            total_trades: Total number of trades
            winning_trades: Number of winning trades
            losing_trades: Number of losing trades
            calmar_ratio: Calmar ratio
            omega_ratio: Omega ratio
            profit_factor: Profit factor
            expectancy: Expectancy per trade
            **kwargs: Additional metrics
        """
        self.output = OutputMetrics(
            final_capital=final_capital,
            total_pnl=total_pnl,
            total_pnl_percentage=total_pnl_percentage,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_percentage=max_drawdown_percentage,
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            calmar_ratio=calmar_ratio,
            omega_ratio=omega_ratio,
            profit_factor=profit_factor,
            expectancy=expectancy,
            additional_metrics=kwargs,
        )
        logger.debug(f"Added results: PnL={total_pnl}, Trades={total_trades}")

    def add_validation_criteria(
        self,
        criteria_name: str,
        expected_value: Union[Decimal, float, int, str, bool],
        actual_value: Union[Decimal, float, int, str, bool],
        passed: bool,
        tolerance: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> None:
        """
        Add validation criteria result.

        Args:
            criteria_name: Name of the criteria
            expected_value: Expected value
            actual_value: Actual value
            passed: Whether criteria passed
            tolerance: Tolerance for comparison
            reason: Reason for failure if not passed
        """
        criteria = ValidationCriteria(
            criteria_name=criteria_name,
            expected_value=expected_value,
            actual_value=actual_value,
            passed=passed,
            tolerance=tolerance,
            reason=reason,
        )
        self.validation_criteria.append(criteria)
        logger.debug(f"Added validation: {criteria_name} - {'PASSED' if passed else 'FAILED'}")

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)
        logger.warning(f"Test warning: {warning}")

    def add_anomaly(self, anomaly: str) -> None:
        """Add an anomaly detection."""
        self.anomalies.append(anomaly)
        logger.warning(f"Test anomaly: {anomaly}")

    def add_note(self, note: str) -> None:
        """Add a note to the report."""
        self.notes.append(note)

    def add_attachment(self, path: str) -> None:
        """Add an attachment path (e.g., chart image)."""
        self.attachments.append(path)

    def mark_passed(self, reason: Optional[str] = None) -> None:
        """Mark test as passed."""
        self.passed = True
        self.pass_reason = reason or "Test passed successfully"
        self.end_time = datetime.now()

    def mark_failed(self, reason: str) -> None:
        """Mark test as failed."""
        self.passed = False
        self.pass_reason = reason
        self.end_time = datetime.now()

    def generate_report(self) -> TestSummaryReport:
        """
        Generate the complete test summary report.

        Returns:
            TestSummaryReport object

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        if self.input_data is None:
            raise ValueError("Input data not set. Call add_input_data() first.")
        if self.config is None:
            raise ValueError("Config not set. Call add_config() first.")
        if self.output is None:
            raise ValueError("Output not set. Call add_results() first.")
        if self.passed is None:
            raise ValueError("Test status not set. Call mark_passed() or mark_failed() first.")

        # Calculate duration
        duration = None
        if self.end_time is not None:
            duration = (self.end_time - self.start_time).total_seconds()

        return TestSummaryReport(
            metadata=self.metadata,
            input_data=self.input_data,
            config=self.config,
            output=self.output,
            validation_criteria=self.validation_criteria,
            passed=self.passed,
            pass_reason=self.pass_reason,
            warnings=self.warnings,
            anomalies=self.anomalies,
            start_time=self.start_time,
            end_time=self.end_time,
            duration_seconds=duration,
            notes=self.notes,
            attachments=self.attachments,
        )

    def save_reports(self) -> Tuple[Path, Path]:
        """
        Save reports in both JSON and human-readable formats.

        Returns:
            Tuple of (json_path, txt_path)

        Raises:
            ValueError: If report generation fails
        """
        report = self.generate_report()

        # Generate filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{self.metadata.test_name}_{timestamp}"

        json_path = self.output_dir / f"{base_name}.json"
        txt_path = self.output_dir / f"{base_name}.txt"

        # Save JSON report
        try:
            with open(json_path, "w") as f:
                json.dump(report.model_dump(mode="json"), f, indent=2, default=str)
            logger.info(f"JSON report saved to {json_path}")
        except Exception as e:
            logger.error(f"Failed to save JSON report: {e}")
            raise

        # Save human-readable report
        try:
            with open(txt_path, "w") as f:
                f.write(self._format_human_readable(report))
            logger.info(f"Text report saved to {txt_path}")
        except Exception as e:
            logger.error(f"Failed to save text report: {e}")
            raise

        return json_path, txt_path

    def _format_human_readable(self, report: TestSummaryReport) -> str:
        """Format report as human-readable text."""
        lines = [
            "=" * 80,
            f"TEST SUMMARY REPORT: {report.metadata.test_name.upper()}",
            "=" * 80,
            "",
        ]

        # Metadata section
        lines.extend([
            "## METADATA",
            "-" * 40,
            f"Test Name:        {report.metadata.test_name}",
            f"Description:      {report.metadata.test_description}",
            f"Test File:        {report.metadata.test_file}",
            f"Test Type:        {report.metadata.test_type}",
            f"Test ID:          {report.metadata.test_id}",
            f"Created:          {report.metadata.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ])

        # Status section
        status_icon = "✓" if report.passed else "✗"
        status_text = "PASSED" if report.passed else "FAILED"
        lines.extend([
            "## TEST STATUS",
            "-" * 40,
            f"{status_icon} Status:          {status_text}",
            f"Reason:           {report.pass_reason or 'N/A'}",
            f"Duration:         {report.duration_seconds:.2f} seconds" if report.duration_seconds else "Duration:         N/A",
            "",
        ])

        # Input data section
        lines.extend([
            "## INPUT DATA",
            "-" * 40,
            f"Symbols:          {', '.join(report.input_data.symbols)}",
            f"Date Range:       {report.input_data.date_range[0].strftime('%Y-%m-%d')} to "
            f"{report.input_data.date_range[1].strftime('%Y-%m-%d')}",
            f"Data Points:      {report.input_data.data_points:,}",
            f"Market Regime:    {report.input_data.market_regime}",
            f"Data Source:      {report.input_data.data_source}",
        ])

        if report.input_data.price_range:
            lines.append(f"Price Range:      ${report.input_data.price_range[0]:.2f} - "
                        f"${report.input_data.price_range[1]:.2f}")

        if report.input_data.volatility is not None:
            lines.append(f"Volatility:       {report.input_data.volatility:.2%}")

        if report.input_data.notes:
            lines.extend(["", "Notes:"] + [f"  - {note}" for note in report.input_data.notes])

        lines.append("")

        # Configuration section
        lines.extend([
            "## CONFIGURATION",
            "-" * 40,
            f"Initial Capital:  ${report.config.initial_capital:,.2f}",
            f"Commission:       ${report.config.commission:.2f} per trade",
            f"Slippage:         {report.config.slippage:.2%}",
            f"Strategy:         {report.config.strategy}",
        ])

        if report.config.strategy_params:
            lines.append("Strategy Parameters:")
            for key, value in report.config.strategy_params.items():
                lines.append(f"  {key}: {value}")

        if report.config.risk_management:
            lines.append("Risk Management:")
            for key, value in report.config.risk_management.items():
                lines.append(f"  {key}: {value}")

        lines.append("")

        # Output metrics section
        lines.extend([
            "## OUTPUT METRICS",
            "-" * 40,
            "",
            "### Financial Performance",
            f"Final Capital:     ${report.output.final_capital:,.2f}",
            f"Total P&L:        ${report.output.total_pnl:,.2f}",
        ])

        if report.output.total_pnl_percentage is not None:
            lines.append(f"Total Return:      {report.output.total_pnl_percentage:.2f}%")

        lines.extend([
            "",
            "### Risk Metrics",
        ])

        if report.output.sharpe_ratio is not None:
            lines.append(f"Sharpe Ratio:      {report.output.sharpe_ratio:.2f}")
        if report.output.sortino_ratio is not None:
            lines.append(f"Sortino Ratio:     {report.output.sortino_ratio:.2f}")
        if report.output.max_drawdown is not None:
            lines.append(f"Max Drawdown:      ${report.output.max_drawdown:,.2f}")
        if report.output.max_drawdown_percentage is not None:
            lines.append(f"Max Drawdown %:    {report.output.max_drawdown_percentage:.2f}%")

        lines.extend([
            "",
            "### Trade Statistics",
            f"Total Trades:      {report.output.total_trades:,}",
            f"Winning Trades:    {report.output.winning_trades:,}",
            f"Losing Trades:     {report.output.losing_trades:,}",
        ])

        if report.output.win_rate is not None:
            lines.append(f"Win Rate:          {report.output.win_rate:.1f}%")

        # Advanced metrics
        advanced_metrics = [
            ("Calmar Ratio", report.output.calmar_ratio),
            ("Omega Ratio", report.output.omega_ratio),
            ("Profit Factor", report.output.profit_factor),
            ("Expectancy", report.output.expectancy),
        ]

        has_advanced = any(v is not None for _, v in advanced_metrics)
        if has_advanced:
            lines.extend([
                "",
                "### Advanced Metrics",
            ])
            for name, value in advanced_metrics:
                if value is not None:
                    lines.append(f"{name}:       {value:.2f}")

        # Additional metrics
        if report.output.additional_metrics:
            lines.extend([
                "",
                "### Additional Metrics",
            ])
            for key, value in report.output.additional_metrics.items():
                lines.append(f"{key}:       {value}")

        lines.append("")

        # Validation criteria section
        if report.validation_criteria:
            lines.extend([
                "## VALIDATION CRITERIA",
                "-" * 40,
            ])

            for criteria in report.validation_criteria:
                status_icon = "✓" if criteria.passed else "✗"
                status_text = "PASSED" if criteria.passed else "FAILED"
                lines.extend([
                    f"{status_icon} {criteria.criteria_name}: {status_text}",
                    f"   Expected: {criteria.expected_value}",
                    f"   Actual:   {criteria.actual_value}",
                ])

                if criteria.tolerance is not None:
                    lines.append(f"   Tolerance: ±{criteria.tolerance}")

                if criteria.reason:
                    lines.append(f"   Reason: {criteria.reason}")

                lines.append("")

        # Warnings section
        if report.warnings:
            lines.extend([
                "## WARNINGS",
                "-" * 40,
            ])
            for warning in report.warnings:
                lines.append(f"⚠ {warning}")
            lines.append("")

        # Anomalies section
        if report.anomalies:
            lines.extend([
                "## ANOMALIES",
                "-" * 40,
            ])
            for anomaly in report.anomalies:
                lines.append(f"⚠ {anomaly}")
            lines.append("")

        # Additional notes
        if report.notes:
            lines.extend([
                "## ADDITIONAL NOTES",
                "-" * 40,
            ])
            for note in report.notes:
                lines.append(f"• {note}")
            lines.append("")

        # Attachments
        if report.attachments:
            lines.extend([
                "## ATTACHMENTS",
                "-" * 40,
            ])
            for attachment in report.attachments:
                lines.append(f"📎 {attachment}")
            lines.append("")

        # Footer
        lines.extend([
            "=" * 80,
            f"End of Report - Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 80,
        ])

        return "\n".join(lines)


# ============================================================================
# Convenience Functions
# ============================================================================


def create_backtest_summary(
    test_name: str,
    symbols: List[str],
    date_range: Tuple[datetime, datetime],
    initial_capital: Decimal,
    final_capital: Decimal,
    total_pnl: Decimal,
    total_trades: int,
    passed: bool,
    reason: str,
    **kwargs,
) -> TestSummaryReporter:
    """
    Convenience function to quickly create a backtest summary.

    Args:
        test_name: Name of the test
        symbols: Trading symbols
        date_range: Date range (start, end)
        initial_capital: Initial capital
        final_capital: Final capital
        total_pnl: Total profit/loss
        total_trades: Total number of trades
        passed: Whether test passed
        reason: Reason for pass/fail
        **kwargs: Additional parameters (config, metrics, etc.)

    Returns:
        TestSummaryReporter instance

    Example:
        ```python
        reporter = create_backtest_summary(
            test_name="test_sma_crossover",
            symbols=["AAPL"],
            date_range=(datetime(2023, 1, 1), datetime(2023, 12, 31)),
            initial_capital=Decimal("100000"),
            final_capital=Decimal("115000"),
            total_pnl=Decimal("15000"),
            total_trades=50,
            passed=True,
            reason="All metrics acceptable",
            sharpe_ratio=Decimal("1.5"),
            win_rate=Decimal("60.0")
        )
        reporter.save_reports()
        ```
    """
    reporter = TestSummaryReporter(test_name=test_name)

    # Add input data
    reporter.add_input_data(
        symbols=symbols,
        date_range=date_range,
        data_points=kwargs.get("data_points", 252),
        market_regime=kwargs.get("market_regime", "unknown"),
        data_source=kwargs.get("data_source", "backtest"),
    )

    # Add config
    reporter.add_config(
        initial_capital=initial_capital,
        commission=kwargs.get("commission", Decimal("1.0")),
        slippage=kwargs.get("slippage", Decimal("0.1")),
        strategy=kwargs.get("strategy", "unknown"),
    )

    # Add results
    reporter.add_results(
        final_capital=final_capital,
        total_pnl=total_pnl,
        total_trades=total_trades,
        sharpe_ratio=kwargs.get("sharpe_ratio"),
        win_rate=kwargs.get("win_rate"),
        max_drawdown=kwargs.get("max_drawdown"),
    )

    # Set status
    if passed:
        reporter.mark_passed(reason)
    else:
        reporter.mark_failed(reason)

    return reporter
