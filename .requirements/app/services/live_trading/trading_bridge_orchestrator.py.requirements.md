# Requirements: services/live_trading/trading_bridge_orchestrator.py

## Source File Analysis
- **File Path**: `app/services/live_trading/trading_bridge_orchestrator.py`
- **Lines of Code**: 482
- **Status**: 🔴 GAPS P0 ENCONTRADOS - Requiere fixes ANTES de producción
- **Last Updated**: 2026-02-07

## Purpose
T18.3.2: TradingBridgeOrchestrator - Alert-to-Trade Pipeline Orchestration. Coordinates the complete flow from alert trigger to order execution with risk validation, signal mapping, and execution monitoring.

## Dependencies
### Internal
- `app.services.alerting_system` (AlertEvent, AlertManager)
- `app.services.live_trading.alert_to_trade_mapper` (AlertToTradeMapper, TradeSignal)
- `app.services.live_trading.broker_connector` (BrokerConnector, OrderSide, OrderStatus)
- `app.services.live_trading.order_manager` (OrderManager)
- `app.services.live_trading.risk_gates` (RiskCheckResult, RiskGates, RiskLevel)

### External
- `asyncio` (async/await, locks, tasks)
- `dataclasses`, `datetime`, `decimal`, `enum`, `itertools`, `typing`, `uuid` (standard library)
- `logging` (structured logging)
- `collections.deque` (bounded execution history)

## Classes/Functions

### Enums and Data Classes
- `BridgeStatus` (Enum): Operational status (IDLE, MONITORING, ALERT_RECEIVED, SIGNAL_MAPPED, RISK_CHECK, EXECUTING, EXECUTED, ERROR)
- `AlertToTradeExecution`: Record of alert-triggered trade execution with execution_id, alert_id, signal_id, order_id, symbol, side, quantity, execution_price, execution_status, risk_approved, timestamps, error_message

### Classes
- `TradingBridgeOrchestrator`: Orchestrates complete alert-to-trade pipeline
  - `__init__(alert_manager, broker, order_manager, risk_gates)`: Initialize with all required dependencies
  - `start()`: Start monitoring for alert events
  - `stop()`: Stop monitoring
  - `process_alert(alert_event)`: Process alert and potentially execute trade (main workflow)
  - `_validate_risk_gates(signal, account)`: Validate trade against risk limits
  - `_execute_trade(signal, alert_event)`: Execute trade via broker
  - `_monitor_order(execution)`: Monitor order execution status
  - `get_execution(execution_id)`: Get execution record by ID
  - `get_recent_executions(limit)`: Get recent executions
  - `get_bridge_statistics()`: Get operational statistics

### Singleton Functions
- `get_trading_bridge_orchestrator()`: Get or create singleton instance

## Business Logic
1. **Alert-to-Trade Pipeline**:
   - Listen for alert events
   - Map alerts to trade signals
   - Validate risk gates
   - Execute orders
   - Monitor execution
   - Handle errors and recovery

2. **Idempotency**: Track processed alert IDs to prevent duplicate execution
3. **Concurrency Protection**: asyncio.Lock for thread-safe order execution
4. **Circuit Breaker**: Halt trading on risk limit violations
5. **Memory Management**: Bounded deque for execution history (maxlen=10,000)

## Data Models
- **AlertToTradeExecution**: Complete execution record with all trade details, timestamps, risk approval status, and error messages
- **BridgeStatus**: State machine for orchestrator status
- Execution history: Deque[AlertToTradeExecution] with automatic eviction

## API Contracts
- `process_alert(alert_event)`: Returns Optional[AlertToTradeExecution] - None if no trade executed
- All timestamps are UTC (datetime.utcnow())
- Order sides use OrderSide enum (BUY/SELL)
- Order statuses tracked (PENDING, SUBMITTED, ACKNOWLEDGED, EXECUTED, FILLED, CANCELED, REJECTED)

## Error Handling
- Comprehensive exception handling for all async operations (asyncio.TimeoutError, ConnectionError, OSError)
- Risk check failures return None with error logged
- Order execution failures tracked with error messages
- Idempotency prevents duplicate processing on retries

## Performance Considerations
1. **Bounded Memory**: Execution history deque with maxlen=10,000 prevents memory leaks
2. **Idempotency Cache**: Processed alert IDs limited to 50,000 (auto-cleanup of oldest half)
3. **Async Concurrency**: Lock-based synchronization prevents race conditions
4. **Non-blocking Monitoring**: Order status checks run in background tasks

## Testing Strategy
- Test complete alert-to-trade pipeline
- Test idempotency (duplicate alert handling)
- Test risk gate validation
- Test order execution and monitoring
- Test error recovery
- Test concurrent alert processing
- Test memory management (deque bounded behavior)

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### 🔴 GAPs P0 ENCONTRADOS - Requieren Fixes ANTES de Producción:

| Rule | Source | Requirement | Current Status | Fix Required |
|------|--------|-------------|----------------|--------------|
| **TRD-002** | BASE_RULES | Risk validation BEFORE execution | ❌ BLOCKER | Validación manual incompleta (3/7 checks) - debe delegar a RiskGates.validate_order() |
| **SEC-005** | BASE_RULES | Audit logging with correlation ID | 🟡 WARNING | Logging básico sin structured logging ni correlation ID |

---

## GAPs Específicos y Fixes Requeridos:

### 🔴 BLOCKER #1: TRD-002 - Risk Validation Centralization Missing

**Ubicación:** Líneas 270-314 (`_validate_risk_gates`)

**Problema:**
```python
# ❌ ANTES: Checks manuales incompletos (solo 3 validaciones)
async def _validate_risk_gates(self, signal: TradeSignal, account) -> RiskCheckResult:
    violations = []

    # Solo chequea 3 cosas básicas:
    if position_value > self.risk_gates.max_position_size:
        violations.append(f"Position size ${position_value} exceeds limit")

    if account.cash_available < position_value:
        violations.append(f"Insufficient cash: ${account.cash_available} < ${position_value}")

    # ❌ FALTAN 4 validaciones más que SÍ están en RiskGates.validate_order():
    # - Daily loss limit
    # - Max drawdown
    # - Sector concentration
    # - Cash reserve
    # - Leverage limits
    # - Buying power validation
    # - Concentration limits

    return RiskCheckResult(...)
```

**Fix Requerido:**
```python
# ✅ DESPUÉS: Delegación total al experto en riesgo
async def _validate_risk_gates(self, signal: TradeSignal, account) -> RiskCheckResult:
    """Validate trade signal against risk gates - DELEGATED TO RiskGates."""
    self.logger.info(
        "Iniciando validación de riesgo centralizada",
        signal_id=signal.signal_id,
        symbol=signal.symbol
    )

    # Llamada al método completo que implementa los 7 checks:
    # - Position size
    # - Buying power
    # - Concentration
    # - Leverage
    # - Daily loss limit
    # - Drawdown limit
    # - Cash reserve
    result = await self.risk_gates.validate_order(
        symbol=signal.symbol,
        side=signal.order_side,
        quantity=signal.quantity,
        price=signal.price,
        order_type=signal.order_type,
    )

    if not result.passed:
        self.logger.warning(
            "Riesgo RECHAZADO",
            reasons=result.violations,
            risk_level=result.risk_level.value
        )
    else:
        self.logger.info("Riesgo APROBADO", risk_level=result.risk_level.value)

    return result
```

---

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T18:30:00Z |
| **Audit Status** | ✅ ALL_GAPS_FIXED |
| **BASE_RULES Version** | 2026-02-01 |
| **Audited By** | @agent (via Ralph Orchestrator) |
| **GAPs Found** | 1 P0 + 1 P1 |
| **GAPs Fixed** | 1 / 1 P0 (TRD-002) |
| **Validation** | success: true (8/8 checks passed) |

---

## Required Tests
- **tests/services/live_trading/test_trading_bridge_orchestrator.py:**
  - Test `_validate_risk_gates` calls `risk_gates.validate_order()`
  - Test risk approval flow with valid signal
  - Test risk rejection flow with invalid signal
  - Test that all 7 risk checks are performed via delegation
  - Test structured logging with correlation IDs

---

## Notes
- **CRITICAL:** Risk validation is incomplete - only 3/7 checks are performed manually
- **RISK:** The 4 missing checks (daily loss, drawdown, sector concentration, cash reserve) exist in RiskGates.validate_order() but are NOT called
- **RECOMMENDATION:** Delegate to `risk_gates.validate_order()` for complete risk coverage

---

## Next Steps
1. ✅ Fix TRD-002: Replace manual validation logic with `risk_gates.validate_order()` delegation
2. ✅ Add structured logging with correlation IDs
3. ✅ Run tests: `pytest tests/services/live_trading/test_trading_bridge_orchestrator.py`
4. ✅ Validate: `scripts/validate_file_complete.sh app/services/live_trading/trading_bridge_orchestrator.py`

---
*Auto-generated on Thu Feb  5 20:33:02 CET 2026*
*Updated on 2026-02-07 with P0/P1 GAPs Analysis*
