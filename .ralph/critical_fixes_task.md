# TAREA: Fixes Críticos P0 - Trading System Production Readiness

## OBJETIVO

Implementar **4 fixes críticos P0** requeridos ANTES de poner dinero real en el sistema de trading. Estos fixes previenen:
- Pérdida de fondos por validación incompleta
- Saturación de Rate Limits
- Acoplamiento que dificulta testing
- Duplicación de órdenes por reinicio rápido

---

## 🎯 FIX #1: Centralización del Riesgo (TRD-002)

### Archivo: `app/services/live_trading/trading_bridge_orchestrator.py`
### Ubicación: Líneas 270-314 (`_validate_risk_gates`)

### Problema:
```python
# ❌ ANTES: Checks manuales incompletos (solo 3 validaciones)
async def _validate_risk_gates(self, signal: TradeSignal, account) -> RiskCheckResult:
    violations = []

    # Solo chequea 3 cosas básicas:
    if position_value > self.risk_gates.max_position_size:
        violations.append(f"Position size ${position_value} exceeds limit")

    if account.cash_available < position_value:
        violations.append(f"Insufficient cash: ${account.cash_available} < ${position_value}")

    # ❌ FALTAN 4 validaciones más:
    # - Daily loss limit
    # - Max drawdown
    # - Sector concentration
    # - Cash reserve

    return RiskCheckResult(...)
```

### Solución:
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

### Validación:
```bash
# Después del fix, verificar que:
# 1. No hay lógica manual de validación en _validate_risk_gates
# 2. Solo llama a self.risk_gates.validate_order()
grep -n "validate_order" app/services/live_trading/trading_bridge_orchestrator.py
```

---

## 🎯 FIX #2: Resiliencia en Comunicaciones (ASYNC-004)

### Archivo: `app/services/live_trading/order_manager.py`
### Ubicación: Línea 223 (`poll_order_status`)

### Problema:
```python
# ❌ ANTES: Polling fijo satura Rate Limits
async def poll_order_status(self, order_id: str, max_polls: int = 60):
    for poll_count in range(max_polls):
        # ... validation code ...

        if poll_count < max_polls - 1:
            await asyncio.sleep(1)  # ⚠️ 60 polls × 1s = 60 segundos de Rate Limit abuse
```

### Solución:
```python
# ✅ DESPUÉS: Exponential Backoff con techo
async def poll_order_status(
    self,
    order_id: str,
    max_polls: int = 60,
    max_wait_seconds: int = 30,  # Nuevo parámetro
) -> Optional[BrokerOrder]:
    """
    Poll order status with exponential backoff.

    Backoff strategy:
    - Poll 1: 1s wait
    - Poll 2: 2s wait
    - Poll 3: 4s wait
    - Poll 4: 8s wait
    - Poll 5: 16s wait
    - Poll 6+: 30s wait (techo)
    """
    for poll_count in range(max_polls):
        order = self.pending_orders.get(order_id)
        if not order:
            logger.warning(f"⚠️ Order not found: {order_id}")
            return None

        status = await self.get_order_status(order_id)
        if status in (
            OrderStatus.FILLED,
            OrderStatus.EXECUTED,
            OrderStatus.CANCELED,
            OrderStatus.REJECTED,
        ):
            self.pending_orders.pop(order_id, None)
            self.executed_orders[order_id] = order
            logger.info(
                f"✅ Order {order_id} reached terminal status: {status.value}",
                poll_count=poll_count + 1,
            )
            return order

        # ✅ Exponential backoff con techo de 30 segundos
        if poll_count < max_polls - 1:
            wait_time = min(2 ** poll_count, max_wait_seconds)
            logger.debug(
                f"Poll {poll_count + 1}/{max_polls}: waiting {wait_time}s",
                order_id=order_id,
            )
            await asyncio.sleep(wait_time)

    logger.warning(f"⚠️ Order polling timeout for {order_id}")
    return None
```

### Validación:
```bash
# Después del fix, verificar exponential backoff:
grep -A5 "2 \*\|2 \*\* poll_count" app/services/live_trading/order_manager.py
```

---

## 🎯 FIX #3: Desacoplamiento de Arquitectura (SOL-005)

### Archivo: `app/strategies/execution_engine.py`
### Ubicación: Líneas 19-37 (`__init__`)

### Problema:
```python
# ❌ ANTES: Depende de clases concretas (no testeable con mocks)
from .registry import StrategyRegistry      # Clase concreta
from .strategy_logger import StrategyLogger  # Clase concreta

class ExecutionEngine:
    def __init__(self, registry: StrategyRegistry, logger: StrategyLogger):
        # ❌ Acoplamiento alto - difícil de testear
        self.registry = registry
        self.logger = logger
```

### Solución - Paso 1: Crear Protocol

**Archivo nuevo: `app/strategies/protocols.py`**
```python
"""Protocols for Strategy Registry and Logger - Dependency Inversion."""

from typing import Protocol, Any, Optional
from app.models.signal import Signal
from app.models.portfolio import Portfolio


class StrategyRegistryProto(Protocol):
    """Protocol for strategy registry - allows mocking in tests."""

    def get_strategy(self, name: str) -> Optional[Any]:
        """Get strategy by name."""
        ...

    def get_active_strategy(self) -> Optional[Any]:
        """Get currently active strategy."""
        ...

    @property
    def active_strategy(self) -> Optional[str]:
        """Name of active strategy."""
        ...


class StrategyLoggerProto(Protocol):
    """Protocol for strategy logger - allows mocking in tests."""

    def log_signal_generated(
        self,
        strategy_name: str,
        signal: Signal,
        **kwargs
    ) -> None:
        """Log signal generation event."""
        ...

    def log_signal_rejected(
        self,
        strategy_name: str,
        signal: Signal,
        reason: str,
        **kwargs
    ) -> None:
        """Log signal rejection event."""
        ...

    def log_signal_executed(
        self,
        strategy_name: str,
        signal: Signal,
        execution_price: Any,
        **kwargs
    ) -> None:
        """Log signal execution event."""
        ...

    def log_strategy_error(
        self,
        strategy_name: str,
        error: str,
        context: str,
        **kwargs
    ) -> None:
        """Log strategy error event."""
        ...
```

### Solución - Paso 2: Actualizar ExecutionEngine

```python
# ✅ DESPUÉS: Depende de abstracciones (Protocol)
from .protocols import StrategyRegistryProto, StrategyLoggerProto

class ExecutionEngine:
    """
    Centralized execution engine - Coordinates strategy execution.

    NOW TESTABLE with Protocol-based dependency injection.
    """

    def __init__(
        self,
        registry: StrategyRegistryProto,  # ✅ Protocol, not concrete class
        logger: StrategyLoggerProto,      # ✅ Protocol, not concrete class
    ):
        """
        Initialize execution engine with dependency injection.

        Args:
            registry: Strategy registry (Protocol-based for testability)
            logger: Strategy logger (Protocol-based for testability)
        """
        self.registry = registry
        self.logger = logger
        self.is_running = False
        self.cycle_count = 0
        self.total_signals_generated = 0
        self.total_signals_executed = 0
        self.execution_stats = {}

        logger.info("✅ ExecutionEngine initialized with Protocol-based DI")
```

### Validación:
```bash
# Después del fix:
# 1. Verificar que existe protocols.py
ls app/strategies/protocols.py

# 2. Verificar que ExecutionEngine usa Protocol
grep "Proto" app/strategies/execution_engine.py

# 3. Verificar que tests pueden usar mocks
grep -l "StrategyRegistryProto\|StrategyLoggerProto" tests/
```

---

## 🎯 FIX #4: Client Order ID - Idempotencia (SILNT KILLER)

### Archivo: `app/services/live_trading/broker_connector.py` o similar
### Ubicación: Método `place_order`

### Problema:
```
ESCENARIO "ORDEN EN LIMBO":
1. Sistema genera señal: BUY AAPL 100 shares
2. Llama a broker.place_order()
3. ✅ Orden se envía al exchange
4. ❌ Proceso CRASHA (kill -9) antes de recibir confirmación
5. Sistema reinicia
6. BootReconciler NO ve la orden en estado local
7. ❌ Sistema re-envía la MISMA orden
8. ❌ DUPLICACIÓN: Compra 200 shares en vez de 100
```

### Solución:

```python
# ✅ SOLUCIÓN: Client Order ID (Idempotencia Key)

async def place_order(
    self,
    symbol: str,
    side: OrderSide,
    quantity: Decimal,
    order_type: OrderType = OrderType.MARKET,
    price: Optional[Decimal] = None,
    stop_price: Optional[Decimal] = None,
    client_order_id: Optional[str] = None,  # ✅ NUEVO PARÁMETRO
) -> Optional[BrokerOrder]:
    """
    Place order with broker using client_order_id for idempotency.

    El client_order_id es generado por NOSOTROS (no por el broker).
    Si el sistema reinicia y re-envía la misma orden con el mismo client_order_id:
    - Exchange detecta duplicado
    - Rechaza la orden con "Duplicate Order ID"
    - Retorna la orden ORIGINAL ya existente

    Esto previene duplicaciones por "orden en limbo" tras crash.
    """
    import uuid

    # Si no se proporciona, generar desde signal_id o UUID
    if client_order_id is None:
        client_order_id = f"trade_{uuid.uuid4().hex}"

    logger.info(
        "Placing order with idempotency key",
        symbol=symbol,
        side=side.value,
        quantity=str(quantity),
        client_order_id=client_order_id,
    )

    try:
        # Llamar al broker con client_order_id
        order = await self._broker_api.place_order(
            symbol=symbol,
            side=side.value,
            qty=float(quantity),
            order_type=order_type.value,
            client_order_id=client_order_id,  # ✅ IDempotencia key
        )

        if order:
            logger.info(
                "✅ Order placed successfully",
                order_id=order.order_id,
                client_order_id=client_order_id,
            )
            return order
        else:
            logger.error("❌ Order placement failed")
            return None

    except Exception as e:
        # Si el error es "Duplicate Order ID", NO es error fatal
        if "duplicate" in str(e).lower():
            logger.warning(
                "⚠️ Duplicate order detected - fetching original",
                client_order_id=client_order_id,
            )
            # Buscar orden existente y retornarla
            return await self._get_order_by_client_id(client_order_id)

        logger.error(f"❌ Error placing order: {e}")
        return None
```

### Validación:
```bash
# Después del fix:
# 1. Verificar que place_order acepta client_order_id
grep -A5 "def place_order" app/services/live_trading/broker_connector.py | grep client_order_id

# 2. Verificar que se genera UUID si no se proporciona
grep "uuid.uuid4" app/services/live_trading/broker_connector.py

# 3. Verificar manejo de duplicados
grep -i "duplicate" app/services/live_trading/broker_connector.py
```

---

## EJECUCIÓN DE LOS FIXES

### Orden recomendado:
1. **FIX #3 primero** (Protocol) - Prepara el terreno para testear
2. **FIX #1 segundo** (Risk centralization) - Crítico para seguridad
3. **FIX #2 tercero** (Backoff) - Previene saturación
4. **FIX #4 cuarto** (Idempotency) - Previene duplicación

### Por cada fix:
1. Leer el archivo actual
2. Aplicar el fix según el código de arriba
3. Ejecutar validación: `scripts/validate_file_complete.sh <archivo>`
4. Si hay errores, corregir y re-validar
5. Solo continuar cuando `success: true`

---

## VALIDACIÓN FINAL

```bash
# 1. Validar todos los archivos modificados
for file in \
  app/services/live_trading/trading_bridge_orchestrator.py \
  app/services/live_trading/order_manager.py \
  app/strategies/execution_engine.py \
  app/strategies/protocols.py \
  app/services/live_trading/broker_connector.py
do
  scripts/validate_file_complete.sh "$file" | jq '.summary.success'
done
# Debe retornar "true" para TODOS

# 2. Ejecutar tests OBLIGATORIAMENTE
.venv/bin/pytest tests/ -v --tb=short -k "order_manager or execution_engine or trading_bridge"
# TODOS los tests deben PASAR

# 3. Verificar cambios específicos
# Fix #1: Centralización de riesgo
grep -n "validate_order" app/services/live_trading/trading_bridge_orchestrator.py

# Fix #2: Exponential backoff
grep -n "2 \*\* poll_count" app/services/live_trading/order_manager.py

# Fix #3: Protocol-based DI
grep -n "Proto" app/strategies/execution_engine.py
ls app/strategies/protocols.py

# Fix #4: Client Order ID
grep -n "client_order_id" app/services/live_trading/broker_connector.py
```

---

## OUTPUT FINAL: **CRITICAL_FIXES_COMPLETE**

Cuando:
- ✅ Los 4 fixes están implementados
- ✅ Todos los archivos validan con `success: true`
- ✅ Todos los tests pasan
- ✅ No hay bloqueos async
- ✅ Hay idempotencia con client_order_id

---

## MÉTRICAS DE ÉXITO

### Por Fix:
| Fix | Archivo | Validación | Status |
|-----|---------|------------|--------|
| #1 Risk Centralization | trading_bridge_orchestrator.py | `validate_order()` delegado | ⬜ |
| #2 Exponential Backoff | order_manager.py | `2**poll_count` implementado | ⬜ |
| #3 Protocol DI | execution_engine.py + protocols.py | `*Proto` usado | ⬜ |
| #4 Client Order ID | broker_connector.py | `client_order_id` parameter | ⬜ |

### General:
- [ ] **validate_file_complete.sh**: 5/5 archivos con success: true
- [ ] **pytest**: TODOS los tests pasan
- [ ] **TRD-002**: Risk validation centralizada
- [ ] **ASYNC-004**: Exponential backoff implementado
- [ ] **SOL-005**: Dependency Inversion cumplida
- [ ] **SEC-005**: Idempotencia implementada
