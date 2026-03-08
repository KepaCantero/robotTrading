# Order Manager Integration - Prompt

**Tarea ID:** 11_order_manager_integration
**Propósito:** Integrar OrderManager con ComplianceEngine
**Tiempo estimado:** 4 horas
**Depends on:** 09_compliance_engine_refactor

---

## OBJETIVO

Integrar `OrderManager` para usar `execute_trade()` de `ComplianceEngine`, delegando validaciones R1-R4.

---

## ARCHIVO PRINCIPAL

`app/services/live_trading/order_manager.py`

---

## CAMBIOS REQUERIDOS

### 1. Inyectar ITradeExecutor

```python
from typing import Protocol

class ITradeExecutor(Protocol):
    async def execute_order(self, signal: 'TradeSignal') -> 'TradeResult': ...

class OrderManager:
    def __init__(self, trade_executor: ITradeExecutor):
        self._executor = trade_executor
```

### 2. Delegar validaciones

```python
async def place_order(self, signal):
    # Antes: validaciones R1-R4 aquí
    # Ahora: delegar a ComplianceEngine via ITradeExecutor
    return await self._executor.execute_order(signal)
```

### 3. Actualizar factory

```python
def create_order_manager(config) -> OrderManager:
    compliance_engine = ComplianceEngine(...)
    return OrderManager(trade_executor=compliance_engine)
```

---

## VALIDACION

```bash
python .ralph/scripts/utils.py validate app/services/live_trading/order_manager.py
python -c "from app.services.live_trading.order_manager import OrderManager; print('OK')"
```

---

## SUCCESS CRITERIA

- [ ] OrderManager usa ITradeExecutor via Protocol
- [ ] Validaciones R1-R4 delegadas a ComplianceEngine
- [ ] Factory actualizado con DI
- [ ] Archivo valida sin errores
- [ ] Imports funcionan
