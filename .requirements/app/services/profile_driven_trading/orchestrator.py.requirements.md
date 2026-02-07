# Requirements: services/profile_driven_trading/orchestrator.py

## Source File Analysis
- **File Path**: `app/services/profile_driven_trading/orchestrator.py`
- **Lines of Code**: 1065
- **Status**: PASSED
- **Audit Date**: 2026-02-07

---

## Purpose

**Profile-Driven Trading Orchestrator** - Main entry point for the complete 8-stage trading lifecycle.

Orchestrates the entire trading pipeline from investor profile to trade execution:
1. Profile Generation
2. Universe Selection
3. Capital Allocation
4. Signal Generation
5. Tax Optimization
6. Risk Validation
7. Backtest Validation
8. Trade Execution

**Key Features**:
- Lazy component initialization (imports only when needed)
- Comprehensive error handling with stage-by-stage execution
- Dry-run mode for testing
- Detailed logging and monitoring
- Optional stages (tax optimization, backtest validation, risk gates)

---

## BASE_RULES Compliance

See [../../BASE_RULES.md](../../BASE_RULES.md) for universal rules.

### Critical Rules Applied
- **ASYNC-001/ASYNC-002**: All async functions properly marked
- **ASYNC-003**: Uses async context managers for external resources
- **ASYNC-005**: Timeouts set for external calls
- **LOG-004**: All exceptions logged with context
- **DP-004**: Dependency injection via constructor (OrchestratorConfig)
- **ARCH-001**: Layered architecture with clean separation
- **CC-006**: Explicit error handling for all stages

### Audit Status: **PASSED**

---

## Dependencies

### Internal Dependencies (Lazy-Loaded)
- `app.services.profile_generator.profile_generator.ProfileGenerator`
- `app.services.market_universe_orchestrator.MarketUniverseOrchestrator`
- `app.services.strategy_stock_allocator.StrategyStockAllocator`
- `app.strategies.momentum_modular.learning.reinforcement_learning_engine.ReinforcementLearningEngine`
- `app.services.tax_efficiency.tax_optimized_builder.TaxOptimizedPortfolioBuilder`
- `app.services.live_trading.broker_connector.get_broker_connector`
- `app.services.live_trading.risk_gates.RiskGates`
- `app.services.backtest_orchestration.backtest_orchestrator.BacktestOrchestrator`
- `app.services.live_trading.trading_bridge_orchestrator.TradingBridgeOrchestrator`
- `app.data.real_market_data.RealMarketDataFetcher`
- `.models` - Local models (OrchestratorConfig, TradingResult, etc.)
- `.signal_integrator.SignalIntegrator`
- `.workflow_manager.WorkflowManager`

### External Dependencies
- `asyncio` - Async/await for concurrent operations
- `logging` - Structured logging
- `datetime` - Time handling
- `decimal.Decimal` - Precise financial calculations
- `typing` - Type hints (Dict, List, Optional, Any)
- `pandas` - Data manipulation

---

## Classes/Functions

### 1. `ProfileDrivenTradingOrchestrator` (Class)
**Purpose**: Main orchestrator for profile-driven trading lifecycle

**Attributes**:
- `config: OrchestratorConfig` - Configuration with feature flags
- `workflow_manager: WorkflowManager` - Stage execution coordinator
- `signal_integrator: SignalIntegrator` - Signal combination logic
- Lazy-loaded components (private attributes starting with `_`)

**Key Methods**:

#### `__init__(config: Optional[OrchestratorConfig] = None)`
- Initialize orchestrator with configuration
- Create workflow manager and signal integrator
- Initialize lazy-loaded component placeholders
- Log configuration summary

#### `async execute_trading_lifecycle(input_profile) -> TradingResult`
- **MAIN ENTRY POINT** for complete trading pipeline
- Executes all 8 stages in sequence
- Handles errors gracefully (continues on non-critical failures)
- Returns TradingResult with complete execution details
- Logs execution summary with timing

**Critical Stages** (must succeed for overall success):
1. Profile Generation
2. Capital Allocation
3. Risk Validation

**Optional Stages** (failures don't block pipeline):
4. Universe Selection (has fallback)
5. Signal Generation
6. Tax Optimization
7. Backtest Validation
8. Trade Execution

### 2. Lazy Loading Methods
**Purpose**: Load components only when needed (optimizes startup)

#### `_get_profile_generator()`
- Lazy load ProfileGenerator

#### `_get_market_universe_orchestrator()`
- Lazy load MarketUniverseOrchestrator

#### `_get_stock_allocator()`
- Lazy load StrategyStockAllocator

#### `_get_rl_engine()`
- Lazy load ReinforcementLearningEngine
- **IMPORTANT**: Checks for NumPy 2.x compatibility issues
- Returns None if RL engine unavailable (graceful degradation)

#### `_get_tax_optimizer()`
- Lazy load TaxOptimizedPortfolioBuilder

#### `_get_risk_gates()`
- Lazy load RiskGates with broker connector

#### `_get_backtest_orchestrator()`
- Lazy load BacktestOrchestrator

#### `_get_trading_bridge()`
- Lazy load TradingBridgeOrchestrator

### 3. Stage Methods

#### `async stage_1_generate_profile(input_profile) -> InvestmentProfile`
- Generate InvestmentProfile from InputProfile
- Map risk tolerance to RiskProfile enum
- Create ProfileGenerationRequest
- Call ProfileGenerator.generate()

#### `async stage_2_select_universe(profile=None) -> Dict[str, pd.DataFrame]`
- Select stock universe based on profile
- Filter by S&P 500, NASDAQ 100, IBEX 35, crypto
- Download period and interval configuration
- Fallback to test universe if no data available

#### `async stage_2_select_universe_with_real_data(...)`
- **REAL DATA VARIANT**: Uses Alpha Vantage API
- Fetches actual OHLCV data for top N S&P 500 stocks
- Implements caching to avoid re-fetching
- Rate limiting awareness (5 calls/minute for free tier)
- Falls back to test universe on error

#### `async stage_3_allocate_capital(profile=None, universe=None) -> Dict[str, Any]`
- Allocate capital to strategies and stocks
- Get universe and profile from workflow state
- Call StrategyStockAllocator.allocate()
- Log allocation summary

#### `async stage_4_generate_signals(profile=None, allocation=None) -> SignalSet`
- Generate trading signals from multiple sources
- RL signals (if enabled and available)
- Momentum signals
- Mean reversion signals
- Combine signals using SignalIntegrator
- Filter by quality

#### `async stage_5_optimize_taxes(allocation=None) -> TaxOptimizedAllocation`
- Optimize portfolio for tax efficiency
- Skipped if disabled in config
- Convert allocation format for tax optimizer
- Calculate tax benefit and after-tax return

#### `async stage_6_validate_risk(profile=None, allocation=None) -> RiskValidationResult`
- Validate portfolio against risk limits
- Check position sizes vs max_position_size_pct
- Check portfolio concentration
- Determine risk level (LOW/MEDIUM/HIGH/CRITICAL)
- Return violations and warnings

#### `async stage_7_backtest_validate(profile=None, allocation=None) -> BacktestOrchestrationResult`
- Validate strategy through backtesting
- Skipped if disabled in config
- Create BacktestOrchestrationRequest
- Run backtest and return results

#### `async stage_8_execute_trades(allocation=None, signals=None) -> ExecutionResult`
- Execute trades based on allocation and signals
- Dry-run mode if auto_execute_trades is False
- Process each allocation with signal
- Log order details
- Start/stop trading bridge for live execution

### 4. Utility Methods

#### `_create_test_universe() -> Dict[str, pd.DataFrame]`
- Create test universe for testing when no data available
- Uses 8 major tech stocks
- Generates 6 months of realistic OHLCV data

#### `get_status() -> Dict[str, Any]`
- Get orchestrator status and statistics
- Return config, execution counts, workflow statistics

---

## Business Logic

### 8-Stage Trading Pipeline

```
InputProfile
    ↓
[Stage 1] Profile Generation → InvestmentProfile
    ↓
[Stage 2] Universe Selection → Stock Universe
    ↓
[Stage 3] Capital Allocation → Allocations
    ↓
[Stage 4] Signal Generation → SignalSet
    ↓
[Stage 5] Tax Optimization (optional) → TaxOptimizedAllocation
    ↓
[Stage 6] Risk Validation → RiskValidationResult
    ↓
[Stage 7] Backtest Validation (optional) → BacktestOrchestrationResult
    ↓
[Stage 8] Trade Execution → ExecutionResult
    ↓
TradingResult (complete execution details)
```

### Critical vs Optional Stages

**Critical** (pipeline fails if these fail):
- Profile Generation (need profile to continue)
- Capital Allocation (need allocations to trade)
- Risk Validation (must not exceed risk limits)

**Optional** (pipeline continues with warnings):
- Universe Selection (has test universe fallback)
- Signal Generation (can use empty signal set)
- Tax Optimization (not required for trading)
- Backtest Validation (not required for trading)
- Trade Execution (dry-run mode available)

### Workflow State Management

- WorkflowManager maintains state between stages
- Each stage can access previous stage results
- Automatic state passing via workflow_manager.get_current_state()

### Error Handling Strategy

1. **Fatal Errors**: Mark TradingResult as failed, log error
2. **Stage Errors**: Continue to next stage if stop_on_error=False
3. **Optional Component Errors**: Log warning, use fallback
4. **Critical Component Errors**: Fail pipeline

---

## Data Models

### `OrchestratorConfig`
```python
@dataclass
class OrchestratorConfig:
    enable_rl_signals: bool = True
    enable_tax_optimization: bool = True
    enable_backtest_validation: bool = True
    enable_risk_gates: bool = True
    auto_execute_trades: bool = False
    use_ibkr: bool = True
    max_concurrent_stages: int = 3
    include_sp500: bool = True
    include_nasdaq100: bool = True
    include_ibex35: bool = True
    include_crypto: bool = False
    top_n_per_universe: int = 10
    download_period: str = "1y"
    download_interval: str = "1d"
    min_avg_volume: int = 1000000
    min_price: float = 10.0
    max_volatility: float = 0.6
    strategy_allocations: Dict[str, float] = None
    max_position_size_pct: float = 0.25
    marginal_tax_rate: float = 0.25
```

### `TradingResult`
```python
@dataclass
class TradingResult:
    success: bool
    profile_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_time_ms: float = 0.0
    investment_profile: Optional[InvestmentProfile] = None
    universe_data: Optional[Dict] = None
    allocation: Optional[Dict] = None
    signals: Optional[SignalSet] = None
    tax_optimized_allocation: Optional[Any] = None
    risk_validation: Optional[RiskValidationResult] = None
    backtest_result: Optional[Any] = None
    execution_result: Optional[ExecutionResult] = None
    stage_results: List[Any] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
```

### `SignalSet`
```python
class SignalSet:
    signals: Dict[str, str]  # symbol -> "BUY"/"SELL"/"HOLD"
    buy_count: int
    sell_count: int
    hold_count: int
```

### `RiskValidationResult`
```python
@dataclass
class RiskValidationResult:
    passed: bool
    risk_level: str  # "LOW"/"MEDIUM"/"HIGH"/"CRITICAL"
    violations: List[str]
    warnings: List[str]
    metrics: Dict[str, Any]
```

### `ExecutionResult`
```python
@dataclass
class ExecutionResult:
    executed: bool
    dry_run: bool
    orders_submitted: int
    orders_filled: int
    orders_failed: int
    total_value_eur: float
    execution_time_ms: float
    order_details: List[Dict]
    errors: List[str]
```

---

## API Contracts

### Main Entry Point
```python
orchestrator = ProfileDrivenTradingOrchestrator(
    config=OrchestratorConfig(
        enable_rl_signals=True,
        enable_tax_optimization=True,
        auto_execute_trades=False,  # Dry-run mode
    )
)

result = await orchestrator.execute_trading_lifecycle(input_profile)

if result.success:
    print(f"Execution time: {result.execution_time_ms}ms")
    print(f"Signals: {result.signals.buy_count} BUY, {result.signals.sell_count} SELL")
else:
    print(f"Errors: {result.errors}")
```

### Getting Status
```python
status = orchestrator.get_status()
print(status["config"]["enable_rl_signals"])
print(status["execution"]["total_executions"])
```

---

## Error Handling

### Stage-Level Error Handling

Each stage method catches and handles specific exceptions:

**Stage 1 (Profile Generation)**:
- Catches: ValueError, TypeError, KeyError, AttributeError
- Action: Raise exception (critical stage)

**Stage 2 (Universe Selection)**:
- Catches: ValueError, KeyError, AttributeError, IndexError, TypeError
- Action: Create test universe as fallback

**Stage 3 (Capital Allocation)**:
- Uses workflow state for data retrieval
- Action: Raise exception if allocation fails

**Stage 4 (Signal Generation)**:
- Catches: ValueError, KeyError, AttributeError, IndexError, TypeError
- Action: Log warning, return empty SignalSet

**Stage 5 (Tax Optimization)**:
- Catches: ValueError, TypeError, KeyError, AttributeError
- Action: Log error, return None (optional stage)

**Stage 6 (Risk Validation)**:
- Catches: ValueError, TypeError, KeyError, AttributeError
- Action: Return failed RiskValidationResult

**Stage 7 (Backtest Validation)**:
- Catches: ValueError, TypeError, KeyError, AttributeError, IndexError
- Action: Log error, return None (optional stage)

**Stage 8 (Trade Execution)**:
- Catches: asyncio.TimeoutError, ConnectionError, OSError
- Action: Return failed ExecutionResult

### Logging Strategy

- **INFO**: Stage start/completion, configuration
- **WARNING**: Optional component failures, fallbacks
- **ERROR**: Stage failures, critical errors
- **DEBUG**: Component loading, state management

---

## Performance Considerations

1. **Lazy Loading**: Components loaded only when needed
   - Reduces startup time
   - Saves memory for unused features

2. **Async Execution**: All I/O operations are async
   - Non-blocking database queries
   - Concurrent API calls

3. **Workflow Parallelism**: max_concurrent_stages parameter
   - Execute multiple stages concurrently when safe

4. **Data Caching**: RealMarketDataFetcher implements caching
   - Avoids re-downloading market data
   - Reduces API calls

5. **State Management**: WorkflowManager maintains state efficiently
   - No redundant calculations
   - Efficient state passing

---

## Testing Strategy

### Unit Tests Required

1. **Orchestrator Initialization**:
   - Test config parsing
   - Test lazy loading setup
   - Test workflow manager creation

2. **Stage Execution**:
   - Test each stage in isolation
   - Test stage error handling
   - Test fallback behavior

3. **Workflow Integration**:
   - Test complete pipeline execution
   - Test stage data passing
   - Test critical vs optional stages

4. **Lazy Loading**:
   - Test component loading only when accessed
   - Test RL engine graceful degradation

### Integration Tests Required

1. Test with real ProfileGenerator
2. Test with real MarketUniverseOrchestrator
3. Test with real StrategyStockAllocator
4. Test complete pipeline with all stages

### Test Coverage Target: >80%

---

## Configuration

### Feature Flags

```yaml
profile_driven_trading:
  # Features
  enable_rl_signals: true
  enable_tax_optimization: true
  enable_backtest_validation: true
  enable_risk_gates: true

  # Execution
  auto_execute_trades: false  # Dry-run by default
  use_ibkr: true              # Use Interactive Brokers (or mock)
  max_concurrent_stages: 3

  # Universe Selection
  include_sp500: true
  include_nasdaq100: true
  include_ibex35: true
  include_crypto: false
  top_n_per_universe: 10

  # Data Download
  download_period: "1y"
  download_interval: "1d"
  min_avg_volume: 1000000
  min_price: 10.0
  max_volatility: 0.6

  # Risk Management
  max_position_size_pct: 0.25  # 25% max position
  marginal_tax_rate: 0.25      # 25% tax rate

  # Strategy Allocations (optional)
  strategy_allocations:
    momentum: 0.5
    mean_reversion: 0.3
    trend_following: 0.2
```

---

## Deployment Notes

1. **Optional Dependencies**:
   - RL engine requires stable_baselines3 (may not work with NumPy 2.x)
   - Tax optimizer requires tax calculation modules
   - Backtest orchestrator requires backtesting infrastructure

2. **API Keys Required**:
   - Alpha Vantage API key for real market data
   - IBKR credentials for live trading

3. **Database Requirements**:
   - Profile storage (for InvestmentProfile)
   - Universe cache (for market data)
   - Trade history (for ExecutionResult)

4. **Process Management**:
   - Should run as async service
   - Monitor execution time per lifecycle
   - Track failure rates per stage

---

## Security Considerations

1. **No Hardcoded Secrets**: Uses environment-based config
2. **Dry-Run Mode**: Auto-execute disabled by default
3. **Risk Validation**: Enforces position limits
4. **Audit Trail**: All stage executions logged

---

## Compliance with Trading Rules

### TRD-002: Risk Validation
- Stage 6 enforces risk limits
- Position size checks
- Concentration checks

### TRD-004: Audit Trail
- All stages logged
- TradingResult stores complete execution history
- Order details tracked in ExecutionResult

### TRD-003: Position Limits
- Max position size enforced
- Portfolio concentration monitored

---

## Audit Status: **PASSED**

**Date**: 2026-02-07
**Auditor**: GAP Audit Batch 0104
**Violations**: 0
**Notes**: Excellent orchestration design with clean separation of concerns. Lazy loading pattern optimizes startup time and handles optional dependencies gracefully. Comprehensive error handling with appropriate fallbacks. Clear distinction between critical and optional stages. Well-structured async code with proper error handling throughout.

---
