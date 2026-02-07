# TAREA: Auditoría GAP Críticos P0/P1 - Trading & Risk Management

## OBJETIVO

Ejecutar auditoría y corrección de **GAPs P0 y P1** en archivos críticos de trading y risk management que representan riesgos inminentes de:
- Pérdida de fondos
- Ejecución sin validación
- Falta de auditoría
- Bloqueos en async

**Archivos objetivo:**
1. `app/services/live_trading/order_manager.py` (408 líneas)
2. `app/strategies/execution_engine.py` (309 líneas)
3. `app/services/live_trading/trading_bridge_orchestrator.py` (408 líneas)

## REGLAS DE ORO

1. ❌ **NO** marcar GAP como FIXED si la validación falla
2. ❌ **NO** confiar en tu "juicio" - solo confía en las herramientas
3. ❌ **NO** inventar resultados de validación
4. ✅ **SOLO** marcar FIXED si `validate_file_complete.sh` devuelve `success: true`
5. ✅ **EJECUTAR** las herramientas de validación después de cada fix

---

## POR CADA ARCHIVO:

### Paso 1: Leer el archivo `.requirements.md` actual
```bash
cat .requirements/app/path/to/file.py.requirements.md
```

### Paso 2: Ejecutar validación COMPLETA (OBLIGATORIO)
```bash
scripts/validate_file_complete.sh <archivo>
```

**Esto EJECUTA las siguientes herramientas:**
- ✅ **Black** - Formateador PEP8
- ✅ **Isort** - Organizador de imports
- ✅ **Ruff** - Linter ultra-rápido
- ✅ **Flake8** - Linter clásico
- ✅ **Pylint** - Análisis profundo
- ✅ **Mypy** - Type checker (SOLO el archivo, no imports)
- ✅ **Bandit** - Security scanner
- ✅ **Radon** - Complejidad ciclomática (CC < 10)

### Paso 3: Identificar GAPs P0/P1 según BASE_RULES.md

**Revisar estas reglas críticas:**
- **TRD-002 (P0):** Risk validation - Validate orders BEFORE execution
- **TRD-003 (P0):** Position limits - Enforce max position size
- **TRD-004 (P0):** Audit trail - Log all trade decisions
- **EXE-001 (P0):** Order validation - Validate order parameters
- **ASYNC-004 (P0):** No blocking in async - No `time.sleep()` in async functions
- **SOL-005 (P0):** Dependency Inversion - Depend on abstractions (Protocol/ABC)
- **DP-004 (P0):** Dependency injection - All services
- **SEC-005 (P0):** Audit logging - Log all trading operations

### Paso 4: Actualizar el archivo `.requirements.md`

**Añadir/actualizar la sección "Critical Rules" con:**

```markdown
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### GAPs P0/P1 ENCONTRADOS:

| Rule | Source | Requirement | Current Status | GAP Fix Required |
|------|--------|-------------|----------------|-----------------|
| TRD-002 | BASE_RULES | Risk validation before execution | ❌ BLOCKER | Validate with risk_gates.validate_order() |
| ASYNC-004 | BASE_RULES | No blocking in async | ❌ BLOCKER | Implement exponential backoff |
| SOL-005 | BASE_RULES | Dependency Inversion | ❌ BLOCKER | Extract Protocol/ABC |
| SEC-005 | BASE_RULES | Audit logging | ❌ BLOCKER | Add structured logging + correlation ID |
```

### Paso 5: Arreglar los GAPs según BASE_RULES.md

**Estrategia de fix:**
1. **Auto-fix** (formateo): black, isort, ruff --fix
2. **Re-validar**: `validate_file_complete.sh`
3. **Fix manual** para cada GAP P0/P1
4. **Re-validar** hasta `success: true`

### Paso 6: Actualizar la sección "Audit Status" del requirements.md

```markdown
## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T... |
| **Audit Status** | GAPS_FOUND / FIXED |
| **BASE_RULES Version** | 2026-02-01 |
| **Audited By** @agent (via Ralph Orchestrator) |
| **GAPs Fixed** | X / Y total |
```

---

## GAPs ESPECÍFICOS A ARREGLAR:

### 🔴 BLOCKER #1: order_manager.py - TRD-002 (Risk validation)

**Ubicación:** Líneas 78-124
**Problema:** `place_order()` NO valida capital/límites antes de enviar al broker

**Fix requerido:**
```python
# ANTES de self.broker.place_order(), añadir:
# Validar capital disponible
available_cash = await self.broker.get_available_cash()
order_value = quantity * (price or current_price)

if order_value > available_cash:
    raise InsufficientFundsError(
        f"Order ${order_value:,.2f} exceeds available ${available_cash:,.2f}"
    )
```

### 🔴 BLOCKER #2: order_manager.py - ASYNC-004 (Blocking in async)

**Ubicación:** Línea 223
**Problema:** `await asyncio.sleep(1)` polling fijo

**Fix requerido:**
```python
# Reemplazar:
await asyncio.sleep(1)
# Con exponential backoff:
await asyncio.sleep(min(2 ** poll_count, 30))  # Max 30s
```

### 🔴 BLOCKER #3: order_manager.py - SEC-005 (Audit logging)

**Ubicación:** Líneas 104-124
**Problema:** Logging básico sin structured logging ni correlation ID

**Fix requerido:**
```python
import uuid

correlation_id = str(uuid.uuid4())

log.info(
    "Order placed",
    order_id=order.order_id,
    symbol=symbol,
    side=side.value,
    quantity=str(quantity),
    correlation_id=correlation_id,
    risk_checks=result.risk_level.value,
)
```

### 🔴 BLOCKER #4: execution_engine.py - SOL-005/DP-004 (Dependency Inversion)

**Ubicación:** Líneas 19-37
**Problema:** Depende de clases concretas StrategyRegistry y StrategyLogger

**Fix requerido:**
```python
# Crear Protocol:
class StrategyRegistryProto(Protocol):
    def get_active_strategy(self) -> Optional[Strategy]: ...
    @property
    def active_strategy(self) -> Optional[str]: ...

# Cambiar __init__:
def __init__(
    self,
    registry: StrategyRegistryProto,  # Protocol, not concrete class
    logger: StrategyLoggerProto
):
    self.registry = registry
    self.logger = logger
```

### 🔴 BLOCKER #5: trading_bridge_orchestrator.py - TRD-002 (Risk validation)

**Ubicación:** Líneas 270-314
**Problema:** `_validate_risk_gates()` NO llama a `self.risk_gates.validate_order()`

**Fix requerido:**
```python
async def _validate_risk_gates(self, signal: TradeSignal, account) -> RiskCheckResult:
    # REEMPLAZAR implementación simplificada con:
    return await self.risk_gates.validate_order(
        symbol=signal.symbol,
        side=signal.order_side,
        quantity=signal.quantity,
        price=signal.price,
        order_type=signal.order_type,
    )
```

---

## EJECUCIÓN:

```bash
# Para cada archivo en el batch:
ralph run -c .ralph/ralph_config_critical_gaps.yml
```

---

## OUTPUT FINAL: **TRADING_CRITICAL_GAPS_COMPLETE**

Cuando TODOS los GAPs P0/P1 estén FIXED y los 3 archivos validen con `success: true`.

---

## MÉTRICAS DE ÉXITO:

### Por archivo:
- [ ] **validate_file_complete.sh**: success: true (8/8 checks passed)
- [ ] **TRD-002**: Risk validation implementado
- [ ] **TRD-004**: Audit trail completo
- [ ] **ASYNC-004**: Sin bloqueos en async
- [ ] **SOL-005/DP-004**: Dependency Inversion implementado
- [ ] **SEC-005**: Structured logging con correlation IDs

### Tests:
- [ ] **pytest**: TODOS los tests pasan
