# Ralph Task 31: Production Code Audit & Fix

## Objective
Audit ALL Python files in app/ (excluding tests) and fix them to pass 11 validation checks.

## Completed Phases

### Phase 1: Config Files (COMPLETED)
- 44 files processed, 31 passed initially, 4 fixed

### Phase 2: Protocols & Interfaces (COMPLETED)
- 18 files audited, 17 passed initially, 1 fixed (hurst_analysis/protocols.py)

### Phase 3: Utilities (COMPLETED 2026-03-15)
- 8 files audited in app/core/utils/ and app/shared/utils/
- 5 passed initially
- 3 files fixed:
  1. `decimal_utils.py` - mypy: sum() return type (added Decimal(0) as start)
  2. `subsystem_config_factory.py` - pylint: singleton pattern fix
  3. `symbol_mapper.py` - mypy: abstractmethod + removed forbidden pylint disables

### Phase 4: Models/Entities (COMPLETED 2026-03-15)
- 11 files audited in app/models/ and app/domain/entities/
- All 11 passed initially - NO FIXES NEEDED
- Files: signal.py, portfolio_analytics.py, trade.py, order.py, position.py, portfolio.py, backtest.py, portfolio_optimization.py, post_trade_analysis.py, pre_trade_analysis.py, __init__.py

### Phase 5: Core Services (IN PROGRESS 2026-03-15)
- 57 files audited in app/core/ and app/domain/services/
- 51 passed initially (89.5% pass rate)
- 3 execution adapters FIXED (2026-03-15):
  1. `execution_adapter.py` - FIXED
  2. `order_manager_adapter.py` - FIXED
  3. `trading_bridge_adapter.py` - FIXED

#### Execution Adapter Fix Summary:
**Problem:** Local dataclass `TradeResult` defined inside `execute_order()` method conflicted with `TradeResult = dict` type alias in TYPE_CHECKING block. Mypy expected dict return but got dataclass.

**Solution:**
1. Moved `TradeResultData` dataclass to module level (outside method)
2. Used `dataclasses.asdict()` to convert dataclass to dict before returning
3. Fixed union-attr errors by extracting `order_side` safely before accessing `.value`
4. For execution_adapter.py: Added `BacktestConfig` import and created default config for `PessimisticExecutionEngine`

**Pattern for future fixes:** When a protocol expects dict return type but you want structured data:
```python
@dataclass
class ResultData:
    field1: str
    field2: int

# Type alias for protocol compatibility
Result = Dict[str, Any]

def execute() -> Result:
    result = ResultData(field1="a", field2=1)
    return asdict(result)
```

#### Remaining Failing Files (3):
1. **compliance_engine.py** (HIGH complexity)
   - 28000+ tokens, needs architectural review
   - Issues: pylint import errors, mypy type mismatches, bandit MD5, MI=0
   - Local dataclass definitions inside methods cause mypy issues
   - Conditional imports cause "possibly used before assignment"

2. **technical_indicators.py** (MEDIUM complexity)
   - CC=10.34, MI=6.28
   - Issues: mypy numpy floating types, high CC in multiple functions
   - Needs refactoring: cci(), williams_r(), _validate_input(), roc()

## Remaining Phases
- Phase 5 fixes: 2 files remaining (compliance_engine.py, technical_indicators.py)
- Phases 6-10: Execution, strategies, backtesting, analysis, remaining

## Progress Tracking
- Progress file: .ralph/outputs/PRODUCTION_FIX_PROGRESS.json
