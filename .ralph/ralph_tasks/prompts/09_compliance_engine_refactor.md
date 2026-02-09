#  Compliance Engine Refactor - Prompt

**Tarea ID:** 09_compliance_engine_refactor
**Propósito:** Refactorizar ComplianceEngine para SOLID + R1-R29 + Spain Tax
**Tiempo estimado:** 16 horas
**Depends on:** 01, 02, 03, 04 (Protocol interfaces, Spain Tax, Logger, Risk Validators)

---

##  OBJETIVO

Convertir ComplianceEngine en coordinator SOLID con:
- **5 principios SOLID**
- **Reglas R1-R29** de trading
- **Spain Tax** (IRPF 19/21/23%)

---

##  ENTREGABLES

### Archivos a crear/modificar:

1. **app/services/compliance/protocols.py** (NUEVO o verificar)
   - IPreTradeValidator (R1, R2, R4)
   - ITradeExecutor
   - ISpainTaxEngine
   - ITradingDecisionLogger
   - IKillSwitchMonitor

2. **app/services/compliance/pre_trade_validator.py** (NUEVO)
   - PreTradeValidator
   - validate_kelly() - R1: Kelly + 2%
   - validate_drawdown() - R2: Drawdown 15%
   - validate_rr_ratio() - R4: R:R 2:1

3. **app/services/compliance/spain_tax_engine.py** (NUEVO)
   - SpainTaxEngine
   - calculate_capital_gains_tax() - IRPF progresivo
   - is_eu_dividend() - UE vs No-UE

4. **app/services/compliance/trading_decision_logger.py** (NUEVO)
   - TradingDecisionLogger
   - log_signal() - con correlation_id
   - log_execution() - resultados

5. **app/services/compliance/compliance_engine.py** (MODIFICAR)
   - ComplianceEngine como Coordinator
   - process_alert() - nuevo
   - execute_trade() - nuevo
   - run_strategy_cycle() - nuevo

---

##  REQUISITOS TÉCNICOS

### SOLID Principles

```python
# === ISP: Interface Segregation (< 5 métodos por Protocol) ===

class IPreTradeValidator(Protocol):
    """Validaciones pre-trade (R1, R2, R4) - Máximo 5 métodos"""
    async def validate_kelly(self, capital: Decimal, order_value: Decimal) -> bool: ...
    async def validate_drawdown(self) -> bool: ...
    async def validate_rr_ratio(self, entry: Decimal, target: Decimal, stop: Decimal) -> bool: ...

class ITradeExecutor(Protocol):
    """Ejecuta trades vía broker - Máximo 5 métodos"""
    async def execute_order(self, signal: TradeSignal) -> ExecutionResult: ...

class ISpainTaxEngine(Protocol):
    """Cálculo impuestos España - Máximo 5 métodos"""
    def calculate_capital_gains_tax(self, profit: Decimal) -> Decimal: ...
    def is_eu_dividend(self, symbol: str) -> bool: ...
```

### SRP: Single Responsibility Principle

```python
# Cada clase UNA responsabilidad

class PreTradeValidator:
    """ÚNICA responsabilidad: Validaciones pre-trade"""
    async def validate_kelly(self, capital: Decimal, order_value: Decimal) -> bool:
        """R1: Kelly + 2% max"""
        max_risk = capital * Decimal("0.02")
        return order_value <= max_risk

class SpainTaxEngine:
    """ÚNICA responsabilidad: Cálculo de impuestos España"""
    TAX_BRACKETS = [
        (Decimal("0"), Decimal("6000"), Decimal("0.19")),    # 19%
        (Decimal("6000"), Decimal("50000"), Decimal("0.21")),  # 21%
        (Decimal("50000"), Decimal("999999"), Decimal("0.23")), # 23%
    ]

    def calculate_capital_gains_tax(self, profit: Decimal) -> Decimal:
        """IRPF progresivo sin distinción LT/ST"""
        tax = Decimal("0")
        remaining = profit
        for min_amt, max_amt, rate in self.TAX_BRACKETS:
            if remaining <= 0: break
            taxable = min(remaining, max_amt - min_amt)
            tax += taxable * rate
            remaining -= taxable
        return tax
```

### DIP: Dependency Inversion Principle

```python
class ComplianceEngine:
    """
    Coordinator del flujo completo de trading.
    ÚNICA responsabilidad: Coordinar ciclo con compliance.
    DEPENDE DE ABSTRACCIONES (Protocol), NO CONCRETAS.
    """

    def __init__(
        self,
        pre_trade_validator: IPreTradeValidator,  # Abstracción
        trade_executor: ITradeExecutor,            # Abstracción
        spain_tax_engine: ISpainTaxEngine,         # Abstracción
        decision_logger: ITradingDecisionLogger,   # Abstracción
        kill_switch: IKillSwitchMonitor,           # Abstracción
    ):
        self.pre_trade_validator = pre_trade_validator
        self.trade_executor = trade_executor
        self.spain_tax_engine = spain_tax_engine
        self.decision_logger = decision_logger
        self.kill_switch = kill_switch
```

### Coordinator Pattern

```python
class ComplianceEngine:
    """
    Coordinator: NO hace lógica de negocio, SOLO coordina.

    Responsabilidades:
    - Coordinar flujo: validation → execution → logging → tax
    - NO implementar validaciones (delega a PreTradeValidator)
    - NO ejecutar trades (delega a TradeExecutor)
    - NO calcular impuestos (delega a SpainTaxEngine)
    """

    async def execute_trade(self, signal: TradeSignal, portfolio: Portfolio) -> TradeResult:
        """Coordina ciclo completo con compliance"""
        # 1. Log signal (R15)
        correlation_id = self.decision_logger.log_signal(signal, {})

        # 2. Kill switch check (R2)
        if await self.kill_switch.check_kill_switch():
            raise TradingHaltedError("Drawdown >= 15%")

        # 3. Validaciones pre-trade
        if not await self.pre_trade_validator.validate_drawdown():
            raise DrawdownExceededError("Drawdown >= 15%")

        if not await self.pre_trade_validator.validate_rr_ratio(
            signal.price, signal.target_price, signal.stop_loss
        ):
            raise InsufficientRiskRewardRatioError("R:R < 2:1")

        # 4. Ejecutar
        result = await self.trade_executor.execute_order(signal)

        # 5. Spain Tax
        pnl = self._calculate_pnl(signal, result)
        spain_tax = self.spain_tax_engine.calculate_capital_gains_tax(pnl)

        # 6. Log execution (R15)
        self.decision_logger.log_execution(correlation_id, {
            "gross_pnl": str(pnl),
            "spain_tax": str(spain_tax),
            "net_pnl": str(pnl - spain_tax),
        })

        return TradeResult(..., net_pnl=pnl - spain_tax)

    async def process_alert(self, alert: MarketAlert) -> AlertResult:
        """Procesa alerta de mercado"""
        # Validar alerta
        if not self._validate_alert(alert):
            return AlertResult(status="INVALID")

        # Generar señal desde alerta
        signal = self._alert_to_signal(alert)

        # Ejecutar trade
        return await self.execute_trade(signal, alert.portfolio)

    async def run_strategy_cycle(self, strategy: Strategy) -> CycleResult:
        """Ejecuta ciclo completo de estrategia"""
        # 1. Obtener señales
        signals = await strategy.generate_signals()

        # 2. Para cada señal: validar → ejecutar → log
        results = []
        for signal in signals:
            try:
                result = await self.execute_trade(signal, strategy.portfolio)
                results.append(result)
            except Exception as e:
                self.decision_logger.log_error(signal.correlation_id, e)

        return CycleResult(results=results)
```

### Restricciones:

-   Usar `typing.Protocol`, NO `abc.ABC`
-   Máximo 5 métodos por Protocol (ISP)
-   Cada clase UNA responsabilidad (SRP)
-   ComplianceEngine DEPENDE de Protocol (DIP)
-   NO fallbacks, usar flags @skip-import

---

##  VALIDACIÓN

### Validación de archivos:

```bash
# 1. Verificar archivos creados
ls app/services/compliance/protocols.py
ls app/services/compliance/pre_trade_validator.py
ls app/services/compliance/spain_tax_engine.py
ls app/services/compliance/trading_decision_logger.py
ls app/services/compliance/compliance_engine.py

# 2. Validar TODOS
for f in app/services/compliance/*.py; do
  python scripts/utils.py validate "$f" | jq '.success'
done

# 3. Verificar SOLID
grep "class.*:" app/services/compliance/*.py | wc -l  # >= 5 clases
grep -A 5 "class.*Protocol" app/services/compliance/protocols.py | grep "def " | wc -l  # <= 5 por Protocol

# 4. Verificar R1-R29
grep -n "0.02\|2%" app/services/compliance/pre_trade_validator.py  # R1
grep -n "0.15\|15%" app/services/compliance/pre_trade_validator.py  # R2
grep -n "2.0\|2:1" app/services/compliance/pre_trade_validator.py  # R4
grep -n "correlation_id" app/services/compliance/trading_decision_logger.py  # R15
grep -n "0.19\|0.21\|0.23" app/services/compliance/spain_tax_engine.py  # Spain Tax

# 5. Verificar que NO usa abc.ABC
grep "abc.ABC" app/services/compliance/*.py
# No debe retornar nada
```

---

##  MANEJO DE @skip-import FLAGS

Si un import no existe, usar flag:

```python
# @skip-import: IPreTradeValidator not implemented yet
from app.core.protocols.i_pre_trade_validator import IPreTradeValidator  # type: ignore
```

---

##  CHECKPOINT

Al completar, crear checkpoint:

```json
{
  "task_id": "09_compliance_engine_refactor",
  "task_name": "Compliance Engine Refactor",
  "started_at": "2026-02-08T10:00:00Z",
  "completed_at": "2026-02-09T02:00:00Z",
  "status": "COMPLETED",
  "progress": {
    "total_files": 5,
    "created_files": 4,
    "modified_files": 1,
    "validated_files": 5
  },
  "outputs": {
    "files_created": [
      "app/services/compliance/protocols.py",
      "app/services/compliance/pre_trade_validator.py",
      "app/services/compliance/spain_tax_engine.py",
      "app/services/compliance/trading_decision_logger.py"
    ],
    "files_modified": [
      "app/services/compliance/compliance_engine.py"
    ],
    "solid_principles": ["SRP", "OCP", "LSP", "ISP", "DIP"],
    "trading_rules": ["R1", "R2", "R4", "R15", "R28"],
    "validation_passed": true
  },
  "validation": {
    "all_files_validated": true,
    "solid_verified": true,
    "black_passed": true,
    "isort_passed": true,
    "ruff_passed": true,
    "mypy_passed": true
  },
  "next_task": "10_execution_engine_integration",
  "errors": [],
  "warnings": [],
  "timestamp": "2026-02-09T02:00:00Z"
}
```

---

##  SUCCESS CRITERIA

La tarea está COMPLETED cuando:

- [ ] 5 archivos creados/modificados
- [ ] Todos los Protocol usan `typing.Protocol` (no abc.ABC)
- [ ] Cada Protocol tiene <= 5 métodos (ISP)
- [ ] ComplianceEngine es coordinator (no hace lógica de negocio)
- [ ] R1: Kelly + 2% implementado
- [ ] R2: Drawdown 15% implementado
- [ ] R4: R:R 2:1 implementado
- [ ] R15: correlation_id implementado
- [ ] Spain Tax: IRPF progresivo implementado
- [ ] process_alert() implementado
- [ ] execute_trade() implementado
- [ ] run_strategy_cycle() implementado
- [ ] Todos los archivos validan
- [ ] Checkpoint creado con status "COMPLETED"

---

##  REFERENCIAS

- `.ralph/docs/requirements/SERVICE_REQUIREMENTS.md` - SOLID Principles
- `.ralph/rules/rules_mapping.yml` - SOLID rules
- `.ralph/docs/architecture/compliance_engine_solid_audit.md` - Audit de ComplianceEngine
