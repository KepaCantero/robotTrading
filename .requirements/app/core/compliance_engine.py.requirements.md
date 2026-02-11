# compliance_engine.py Requirements

**File Path:** `app/core/compliance_engine.py`  
**Last Updated:** 2025-02-06  
**Audit Status:** PASSED
**Audit Timestamp:** 2026-02-06T19:41:12.289630

## Purpose

THE Compliance Engine - Unified single engine that integrates ALL existing functionality and ALL 12 compliance rule systems. This is the ONLY engine that should be used in the entire system.

## Type Definitions

### Configuration
```python
class ComplianceConfig(BaseModel):
    """Configuration for compliance engine thresholds and limits."""
    max_position_ratio: float = Field(default=0.10, ge=0.01, le=1.0)
    max_drawdown_ratio: float = Field(default=0.25, ge=0.01, le=1.0)
    max_leverage_ratio: float = Field(default=2.0, ge=1.0, le=10.0)
    kill_switch_threshold: float = Field(default=-0.05, ge=-1.0, le=0.0)
    min_data_quality_score: float = Field(default=80.0, ge=0.0, le=100.0)
    max_data_age_days: float = Field(default=1.0, ge=0.0)
    max_portfolio_volatility: float = Field(default=0.30, ge=0.0, le=1.0)
    max_daily_var_95: float = Field(default=0.05, ge=0.0, le=1.0)
    slo_latency_ms: float = Field(default=100.0, ge=1.0)
    data_quality_nan_penalty: float = Field(default=15.0, ge=0.0, le=100.0)
    data_quality_stale_penalty: float = Field(default=20.0, ge=0.0, le=100.0)
```

### Classes
```python
class SystemAvailability:
    """Track availability of all 17 systems."""
    def __init__(self, enable_logging: bool = False)
    def get_availability(self) -> Dict[str, bool]
    def is_available(self, system_name: str) -> bool
    def get_summary(self) -> Dict[str, Any]

class SystemBus:
    """System Bus pattern for orchestrating ALL 17 systems."""
    def execute_pre_trade_analysis(...) -> PreTradeAnalysis

class ComplianceEngine:
    """THE ONLY ENGINE that should be used."""
    def __init__(self, asset_class: str = "equity", strict_mode: bool = False, 
                 enable_logging: bool = True, config: Optional[ComplianceConfig] = None)
```

## Function Signatures

### ComplianceEngine - Main API
```python
def analyze_pre_trade(
    self,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    price_history: Optional[pd.DataFrame] = None,
    urgency: float = 0.5,
    signal_time: Optional[datetime] = None,
) -> PreTradeAnalysis:
    """THE main pre-trade analysis method."""

def analyze_post_trade(
    self,
    order_id: str,
    symbol: str,
    side: str,
    quantity: Decimal,
    execution_price: Decimal,
    signal_price: Optional[Decimal],
    signal_time: Optional[datetime],
    submission_time: datetime,
    execution_time: datetime,
    nbbo: Optional[Tuple[Decimal, Decimal]] = None,
) -> PostTradeAnalysis:
    """THE main post-trade analysis method."""

def optimize_portfolio(
    self,
    symbols: List[str],
    returns: pd.DataFrame,
    current_prices: Dict[str, Decimal],
) -> PortfolioOptimization:
    """THE ONLY portfolio optimization method."""
```

### Kill Switch (Hull Rule 13.1)
```python
def check_kill_switch(self) -> bool:
    """Check if kill switch is triggered."""

def track_daily_pnl(
    self,
    symbol: str,
    side: str,
    quantity: Decimal,
    entry_price: Decimal,
    exit_price: Optional[Decimal] = None,
    realized_pnl: Optional[float] = None,
) -> None:
    """Track daily P&L for kill switch monitoring."""

def reset_daily_tracking(self, new_starting_capital: Optional[float] = None) -> None:
    """Reset daily tracking at start of new trading day."""

def set_starting_capital(self, capital: float) -> None:
    """Set the starting capital for kill switch calculations."""

def get_daily_pnl_summary(self) -> Dict[str, Any]:
    """Get summary of daily P&L for kill switch monitoring."""
```

### Tracking
```python
def track_order_submission(
    self,
    order_id: str,
    symbol: str,
    side: str,
    quantity: Decimal,
    submission_time: datetime,
) -> None:
    """Track order submission for SLO monitoring."""

def track_order_completion(
    self,
    order_id: str,
    execution_price: Decimal,
    execution_time: datetime,
    filled_quantity: Optional[Decimal] = None,
) -> None:
    """Track order completion for SLO monitoring."""

def get_slo_metrics(self) -> Dict[str, Any]:
    """Get current SLO metrics."""
```

### Singleton Access
```python
def get_compliance_engine(
    asset_class: str = "equity",
    strict_mode: bool = False,
    enable_logging: bool = True,
    config: Optional[ComplianceConfig] = None,
) -> ComplianceEngine:
    """Get THE ONLY Compliance Engine instance."""

def quick_check(
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
) -> Tuple[bool, str]:
    """Quick pre-trade check."""

def get_execution_plan(
    symbol: str,
    quantity: Decimal,
    price: Decimal,
) -> Dict[str, Any]:
    """Get execution plan."""
```

## Acceptance Criteria

### AC-COMP-001: Kill Switch Activation
```bash
# Test: Kill switch triggers at threshold
python -c "
from app.core.compliance_engine import get_compliance_engine, ComplianceConfig
config = ComplianceConfig(kill_switch_threshold=-0.03)
engine = get_compliance_engine(config=config)
engine.set_starting_capital(100000)
engine.track_daily_pnl('AAPL', 'BUY', Decimal('100'), Decimal('150'), 
                        exit_price=Decimal('145'), realized_pnl=-500)
engine.track_daily_pnl('AAPL', 'SELL', Decimal('100'), Decimal('145'),
                        exit_price=Decimal('140'), realized_pnl=-500)
engine.track_daily_pnl('AAPL', 'BUY', Decimal('100'), Decimal('140'),
                        exit_price=Decimal('135'), realized_pnl=-500)
# Total: -1500, -1.5% of 100k = -0.015, not triggered yet
assert engine.check_kill_switch() == False
# More losses needed to trigger
"
```

### AC-COMP-002: Position Limit Enforcement
```bash
# Test: Position limit check blocks oversized orders
python -c "
from app.core.compliance_engine import get_compliance_engine
engine = get_compliance_engine()
analysis = engine.analyze_pre_trade(
    symbol='AAPL',
    side='BUY',
    quantity=Decimal('1000000'),  # Very large
    price=Decimal('150'),
)
assert analysis.position_limit_ok == False
assert analysis.can_execute == False
"
```

### AC-COMP-003: Data Quality Validation
```bash
# Test: Low data quality blocks trading
python -c "
import pandas as pd
import numpy as np
from app.core.compliance_engine import get_compliance_engine
engine = get_compliance_engine()
price_history = pd.DataFrame({'close': [np.nan, np.nan, np.nan]})
analysis = engine.analyze_pre_trade(
    symbol='AAPL',
    side='BUY',
    quantity=Decimal('100'),
    price=Decimal('150'),
    price_history=price_history,
)
assert analysis.can_execute == False
assert 'data quality' in str(analysis.reasons).lower()
"
```

### AC-COMP-004: System Availability Tracking
```bash
# Test: System availability correctly tracked
python -c "
from app.core.compliance_engine import get_compliance_engine
engine = get_compliance_engine()
status = engine.get_system_status()
assert 'availability' in status
assert status['availability']['total_systems'] == 17
"
```

## Critical Rules

### Rule COMP-001: Single Engine Pattern
**Priority:** P0  
**Description:** ComplianceEngine must be a singleton. Only one instance per process.  
**Enforcement:** Using `__new__` method for singleton pattern.

### Rule COMP-002: Kill Switch Priority
**Priority:** P0  
**Description:** Kill switch check MUST be first in `analyze_pre_trade()`. Blocks all trading if triggered.

### Rule COMP-003: Configuration Centralization
**Priority:** P0  
**Description:** All trading thresholds must come from `ComplianceConfig`, not hardcoded. Addresses GAP-CFG-002.

### Rule COMP-004: System Bus Orchestration
**Priority:** P1  
**Description:** All 17 systems must execute through SystemBus in optimal order with failure handling.

### Rule COMP-005: Lazy Subsystem Loading
**Priority:** P2  
**Description:** Subsystems loaded lazily on first use to reduce startup time.

## Dependencies

### Internal Dependencies
```python
from app.domain.entities.portfolio_optimization import PortfolioOptimization
from app.domain.entities.post_trade_analysis import PostTradeAnalysis
from app.domain.entities.pre_trade_analysis import PreTradeAnalysis
```

### External Dependencies
```python
import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from pydantic import BaseModel, Field, field_validator
```

## Required Tests

### Unit Tests (app/tests/core/test_compliance_engine.py)
```python
def test_compliance_config_validation():
    """Test ComplianceConfig field validation."""
    
def test_compliance_config_kill_switch_must_be_negative():
    """Test kill switch threshold validation."""
    
def test_system_availability_initialization():
    """Test SystemAvailability checks all systems."""
    
def test_system_availability_summary():
    """Test SystemAvailability summary calculation."""
    
def test_system_bus_execution_order():
    """Test SystemBus executes systems in correct order."""
    
def test_system_bus_critical_failure_handling():
    """Test SystemBus handles critical system failures."""
    
def test_kill_switch_not_triggered_below_threshold():
    """Test kill switch not triggered below threshold."""
    
def test_kill_switch_triggered_above_threshold():
    """Test kill switch triggered above threshold."""
    
def test_daily_pnl_tracking():
    """Test daily P&L tracking."""
    
def test_daily_tracking_reset():
    """Test daily tracking reset."""
    
def test_starting_capital_validation():
    """Test starting capital must be positive."""
    
def test_position_limit_check():
    """Test position limit enforcement."""
    
def test_drawdown_limit_check():
    """Test drawdown limit enforcement."""
    
def test_leverage_ratio_check():
    """Test leverage ratio enforcement."""
    
def test_data_quality_nan_penalty():
    """Test NaN values reduce quality score."""
    
def test_data_quality_stale_penalty():
    """Test stale data reduces quality score."""
    
def test_data_quality_blocks_trading():
    """Test low quality blocks trading."""
    
def test_analyze_pre_trade_checks_kill_switch_first():
    """Test kill switch checked first."""
    
def test_analyze_pre_trade_returns_analysis():
    """Test pre-trade analysis returns complete object."""
    
def test_analyze_post_trade_calculates_latency():
    """Test post-trade calculates latency."""
    
def test_optimize_portfolio_returns_weights():
    """Test portfolio optimization returns weights."""
    
def test_track_order_submission():
    """Test order submission tracking."""
    
def test_track_order_completion():
    """Test order completion tracking."""
    
def test_slo_violation_logged():
    """Test SLO violations are logged."""
    
def test_singleton_pattern():
    """Test only one engine instance exists."""
```

### Integration Tests
```python
def test_full_pre_trade_workflow():
    """Test complete pre-trade analysis workflow."""
    
def test_full_post_trade_workflow():
    """Test complete post-trade analysis workflow."""
    
def test_kill_switch_blocks_all_trading():
    """Test activated kill switch blocks all trades."""
    
def test_concurrent_engine_access():
    """Test thread-safe concurrent access."""
    
def test_all_17_systems_executed():
    """Test all 17 systems contribute to analysis."""
```

## File-Specific Rules

### Rule COMP-FS-001: Timeout Handling Delegation
**Priority:** P1  
**Description:** Timeout handling is delegated to individual subsystems. Each subsystem handles its own timeouts. When async refactoring is implemented (ASYNC-001), timeouts will be added at façade level using `asyncio.wait_for()`.

### Rule COMP-FS-002: Configuration Injection
**Priority:** P0  
**Description:** `ComplianceConfig` must be injectable via constructor parameter, not hardcoded.

### Rule COMP-FS-003: Initialization Order
**Priority:** P1  
**Description:** Must initialize simple attributes before complex ones to avoid attribute errors during `__init__`.

## Compliance Rules Integrated

### 12 Compliance Rule Systems
1. **Ernest Chan (Rule 1)** - Factor Models, Portfolio Optimization, Regime Detection
2. **Narang (Rule 2)** - Alpha Models, Risk Models, Transaction Costs
3. **López de Prado (Rule 3)** - Sample Weights, Purged CV, Meta-Labeling
4. **Tomasini (Rule 4)** - Trading Systems Architecture
5. **Hastie (Rule 5)** - Statistical Learning
6. **Harris (Rule 6)** - Order Book, Bid-Ask Bounce, Market Impact
7. **O'Hara (Rule 7)** - Order Flow, Liquidity, Price Discovery
8. **Percival (Rule 8)** - Architecture Patterns
9. **Hull (Rule 13)** - Greeks, VaR, Stress Scenarios
10. **Google SRE (Rule 20)** - Golden Signals, SLOs
11. **Beck TDD (Rule 21)** - Test-Driven Development
12. **Martin Clean Arch (Rule 18)** - Clean Architecture

## References

- **BASE_RULES.md:** See ../../BASE_RULES.md for universal rules
- **Related Files:**
  - `app/domain/entities/pre_trade_analysis.py` - Pre-trade result entity
  - `app/domain/entities/post_trade_analysis.py` - Post-trade result entity
  - `app/domain/entities/portfolio_optimization.py` - Portfolio optimization entity

## Changelog

### 2025-02-06
- Initial requirements documentation created
- Documented kill switch implementation (Hull Rule 13.1)
- Documented configuration centralization (addresses GAP-CFG-002)
- Audit Status: NEEDS_AUDIT
