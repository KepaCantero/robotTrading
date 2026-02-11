# test_summary.py

## Purpose
Comprehensive test summary reporting for backtesting tests with JSON (machine-readable) and human-readable formats, capturing test metadata, input data, configuration, output metrics, and validation results.

---

## Type Definitions / Data Classes

### TestMetadata (Pydantic BaseModel)
```python
class TestMetadata(BaseModel):
    test_name: str                      # REQUIRED - Test function name
    test_description: str               # REQUIRED - Test description
    test_file: str                      # REQUIRED - Test file path
    test_type: str                      # REQUIRED - Test type (unit/integration/functional)
    test_id: Optional[str] = None       # Optional unique test identifier
    author: Optional[str] = None        # Optional test author
    tags: List[str] = []                # Optional test tags
    created_at: datetime = Field(default_factory=datetime.now)
```

### InputDataSummary (Pydantic BaseModel)
```python
class InputDataSummary(BaseModel):
    symbols: List[str]                  # REQUIRED - Trading symbols tested
    date_range: Tuple[datetime, datetime]  # REQUIRED - Start/end dates
    data_points: int                    # REQUIRED - Number of data points (>=0)
    market_regime: str                  # REQUIRED - Market regime description
    data_source: str                    # REQUIRED - Data source description
    price_range: Optional[Tuple[Decimal, Decimal]] = None
    volume_stats: Optional[Dict[str, Decimal]] = None
    volatility: Optional[Decimal] = None
    notes: List[str] = []
```

### TestConfig (Pydantic BaseModel)
```python
class TestConfig(BaseModel):
    initial_capital: Decimal            # REQUIRED - Starting capital (>0)
    commission: Decimal                 # REQUIRED - Commission per trade (>=0)
    slippage: Decimal                   # REQUIRED - Slippage percentage (>=0)
    strategy: str                       # REQUIRED - Strategy name
    strategy_params: Dict[str, Any] = {}
    risk_management: Optional[Dict[str, Decimal]] = None
    additional_params: Dict[str, Any] = {}
```

### OutputMetrics (Pydantic BaseModel)
```python
class OutputMetrics(BaseModel):
    # Basic metrics
    final_capital: Decimal              # REQUIRED
    total_pnl: Decimal                  # REQUIRED
    total_pnl_percentage: Optional[Decimal] = None

    # Risk metrics
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    max_drawdown_percentage: Optional[Decimal] = None

    # Trade metrics
    win_rate: Optional[Decimal] = None
    total_trades: int                   # REQUIRED (>=0)
    winning_trades: int = 0             # REQUIRED (>=0)
    losing_trades: int = 0              # REQUIRED (>=0)

    # Advanced metrics
    calmar_ratio: Optional[Decimal] = None
    omega_ratio: Optional[Decimal] = None
    profit_factor: Optional[Decimal] = None
    expectancy: Optional[Decimal] = None

    additional_metrics: Dict[str, Union[Decimal, float, int, str]] = {}
```

### ValidationCriteria (Pydantic BaseModel)
```python
class ValidationCriteria(BaseModel):
    criteria_name: str                 # REQUIRED
    expected_value: Union[Decimal, float, int, str, bool]
    actual_value: Union[Decimal, float, int, str, bool]
    passed: bool
    tolerance: Optional[Decimal] = None
    reason: Optional[str] = None
```

**Validation Rules:**
- `initial_capital` must be > 0
- `data_points` must be >= 0
- `total_trades` must be >= 0

---

## Function Signatures (Contracts)

### `TestSummaryReporter.__init__(output_dir: Optional[Path] = None, test_name: Optional[str] = None, test_description: Optional[str] = None, test_file: Optional[str] = None, test_type: str = "integration")`
**Pre:** None
**Post:** Reporter initialized with generated test_id
**Raises:** None
**Retry:** No
**Side Effects:** Creates output_dir

### `add_input_data(symbols: List[str], date_range: Tuple[datetime, datetime], data_points: int, market_regime: str, data_source: str, price_range: Optional[Tuple[Decimal, Decimal]] = None, volume_stats: Optional[Dict[str, Decimal]] = None, volatility: Optional[Decimal] = None, notes: Optional[List[str]] = None) -> None`
**Pre:** symbols non-empty, data_points >= 0
**Post:** Input data stored
**Raises:** None
**Retry:** No
**Side Effects:** Sets self.input_data

### `add_config(initial_capital: Decimal, commission: Decimal, slippage: Decimal, strategy: str, strategy_params: Optional[Dict[str, Any]] = None, risk_management: Optional[Dict[str, Decimal]] = None, **kwargs) -> None`
**Pre:** initial_capital > 0, commission >= 0, slippage >= 0
**Post:** Config stored
**Raises:** None
**Retry:** No
**Side Effects:** Sets self.config

### `add_results(final_capital: Decimal, total_pnl: Decimal, total_pnl_percentage: Optional[Decimal] = None, sharpe_ratio: Optional[Decimal] = None, sortino_ratio: Optional[Decimal] = None, max_drawdown: Optional[Decimal] = None, max_drawdown_percentage: Optional[Decimal] = None, win_rate: Optional[Decimal] = None, total_trades: int = 0, winning_trades: int = 0, losing_trades: int = 0, calmar_ratio: Optional[Decimal] = None, omega_ratio: Optional[Decimal] = None, profit_factor: Optional[Decimal] = None, expectancy: Optional[Decimal] = None, **kwargs) -> None`
**Pre:** final_capital > 0, total_trades >= 0
**Post:** Output metrics stored
**Raises:** None
**Retry:** No
**Side Effects:** Sets self.output

### `add_validation_criteria(criteria_name: str, expected_value: Union[Decimal, float, int, str, bool], actual_value: Union[Decimal, float, int, str, bool], passed: bool, tolerance: Optional[Decimal] = None, reason: Optional[str] = None) -> None`
**Pre:** criteria_name non-empty
**Post:** Validation criteria added to list
**Raises:** None
**Retry:** No
**Side Effects:** Appends to self.validation_criteria

### `add_warning(warning: str) -> None`
**Pre:** warning non-empty
**Post:** Warning added to list
**Raises:** None
**Retry:** No
**Side Effects:** Appends to self.warnings

### `add_anomaly(anomaly: str) -> None`
**Pre:** anomaly non-empty
**Post:** Anomaly added to list
**Raises:** None
**Retry:** No
**Side Effects:** Appends to self.anomalies

### `add_note(note: str) -> None`
**Pre:** note non-empty
**Post:** Note added to list
**Raises:** None
**Retry:** No
**Side Effects:** Appends to self.notes

### `add_attachment(path: str) -> None`
**Pre:** path valid file path
**Post:** Attachment path added to list
**Raises:** None
**Retry:** No
**Side Effects:** Appends to self.attachments

### `mark_passed(reason: Optional[str] = None) -> None`
**Pre:** None
**Post:** Test marked as passed, end_time set
**Raises:** None
**Retry:** No
**Side Effects:** Sets self.passed = True, self.end_time

### `mark_failed(reason: str) -> None`
**Pre:** reason non-empty
**Post:** Test marked as failed, end_time set
**Raises:** None
**Retry:** No
**Side Effects:** Sets self.passed = False, self.end_time

### `generate_report() -> TestSummaryReport`
**Pre:** input_data, config, output, passed all set
**Post:** Returns complete TestSummaryReport
**Raises:** ValueError if required fields missing
**Retry:** No
**Side Effects:** Calculates duration if end_time set

### `save_reports() -> Tuple[Path, Path]`
**Pre:** generate_report() succeeds
**Post:** JSON and TXT reports saved
**Raises:** ValueError if report generation fails, OSError on write failure
**Retry:** No
**Side Effects:** Creates two files (JSON and TXT)

### `create_backtest_summary(test_name: str, symbols: List[str], date_range: Tuple[datetime, datetime], initial_capital: Decimal, final_capital: Decimal, total_pnl: Decimal, total_trades: int, passed: bool, reason: str, **kwargs) -> TestSummaryReporter`
**Pre:** All required params valid
**Post:** Returns configured TestSummaryReporter
**Raises:** None
**Retry:** No
**Side Effects:** Creates reporter, calls add_input_data, add_config, add_results, mark_passed/failed

---

## Acceptance Criteria
- [ ] Test metadata captured (name, description, file, type, ID, author, tags)
- [ ] Input data summary complete (symbols, dates, data points, regime, source)
- [ ] Configuration captured (capital, commission, slippage, strategy, params)
- [ ] Output metrics captured (financial, risk, trade, advanced)
- [ ] Validation criteria tracked (name, expected, actual, passed, tolerance)
- [ ] Warnings and anomalies tracked
- [ ] Test status set (passed/failed) with reason
- [ ] Reports saved in both JSON and TXT formats
- [ ] JSON report machine-readable (with default=str for serialization)
- [ ] TXT report human-readable (formatted sections)
- [ ] Duration calculated (end_time - start_time)
- [ ] Attachments listed (chart files, etc.)
- [ ] Convenience function creates complete report
- [ ] Validation errors raised if required fields missing

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-007 | 01-formatting-style.md | No mutable default arguments | ✅ OK - Uses default_factory |
| TYP-001 | 02-type-hints.md | All functions have type hints | ✅ OK |
| ARCH-004 | 05-architecture.md | Functions < 20 lines (ideally) | ⚠️ NOT APPLIED - Some long functions |
| SOL-001 | 03-solid-principles.md | Single Responsibility Principle | ✅ OK - Report generation only |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ✅ OK |
| LOG-005 | 09-logging-observability.md | Never log sensitive data | ✅ OK |
| TST-005 | 06-testing.md | Test coverage > 80% | ⚠️ NOT APPLIED - Needs tests |
| JSON-001 | Custom | JSON serialization with default=str | ✅ OK |
| REPORT-001 | Custom | Dual format output (JSON + TXT) | ✅ OK |

**NOTE:** This analysis should consider ALL 200+ rules from /rules directory.

---

## Dependencies
- **External:** json, logging, datetime, decimal, pathlib, typing, pydantic
- **Internal:** None (standalone reporting module)

---

## Required Tests
- **test_test_summary.py:**
  - Success: Create complete report with all fields
  - Success: Add input data
  - Success: Add config
  - Success: Add results (all metrics)
  - Success: Add validation criteria (passed)
  - Success: Add validation criteria (failed)
  - Success: Add warnings
  - Success: Add anomalies
  - Success: Add notes
  - Success: Add attachments
  - Success: Mark as passed
  - Success: Mark as failed
  - Success: Generate report
  - Success: Save JSON report
  - Success: Save TXT report
  - Success: TXT report formatted correctly
  - Success: Convenience function (create_backtest_summary)
  - Error: Missing input_data (ValueError)
  - Error: Missing config (ValueError)
  - Error: Missing output (ValueError)
  - Error: Missing passed status (ValueError)
  - Edge: Optional fields all None
  - Edge: Zero trades
  - Edge: Negative P&L
  - Integration: Round-trip (create, save, load JSON)

---

## Notes
- Default output_dir: reports/test_summaries/
- Filename format: {test_name}_YYYYMMDD_HHMMSS.{json|txt}
- Test ID format: test_YYYYMMDD_HHMMSS
- TXT report sections: METADATA, TEST STATUS, INPUT DATA, CONFIGURATION, OUTPUT METRICS, VALIDATION CRITERIA, WARNINGS, ANOMALIES, ATTACHMENTS
- JSON uses default=str for Decimal/datetime serialization
- Duration only calculated if end_time set
