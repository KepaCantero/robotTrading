# 📐 SERVICE REQUIREMENTS - Nueva Arquitectura ComplianceEngine

**Fecha:** 2026-02-08
**Objetivo:** Definir requisitos SOLID + R1-R29 + Spain Tax para refactorización

---

## 🎯 OBJETIVO DEL SERVICIO

**Nombre:** ComplianceEngine Refactorizado
**Propósito:** Coordinar TODO el flujo de trading con validaciones completas
**Usuario:** Único usuario (residencia España)
**Meta:** 1000€/mes netos (escala: 1000€ → 500k)

---

## 📋 REQUISITOS GENERALES

### 1. Principio SOLID (5 requisitos)

| Principio | Estado Actual | Requerimiento |
|-----------|--------------|---------------|
| **S** - SRP | ❌ 9 responsabilidades | ✅ 1 responsabilidad por clase |
| **O** - OCP | ❌ Hardcoded systems | ✅ Extensible sin modificar código |
| **L** - LSP | ⚠️ USA ABC | ✅ Usar Protocol (más flexible) |
| **I** - ISP | ❌ Fat interface 14 métodos | ✅ Interfaces segregadas |
| **D** - DIP | ❌ Crea dependencias directamente | ✅ Protocol-based DI |

---

### 2. Trading Rules R1-R29 (29 requisitos)

#### 🔴 P0 - CRÍTICOS (Bloquean producción)

| # | Regla | Estado Actual | Requerimiento |
|---|-------|--------------|---------------|
| **R1** | Kelly Criterion + 2% max | ❌ NO validado | ✅ Validar en `execute_trade()` |
| **R2** | Drawdown 15% stop | ⚠️ Parcial | ✅ Validar antes de cada trade |
| **R3** | Stop Loss SIEMPRE | ⚠️ Parcial | ✅ Rechazar sin SL |
| **R4** | R:R 2:1 mínimo | ❌ NO validado | ✅ Validar en `execute_trade()` |
| **R15** | Logging append-only + correlation ID | ❌ NO implementado | ✅ `TradingDecisionLogger` |
| **R28** | Registro para Hacienda | ❌ NO implementado | ✅ Log completo en SpainTaxEngine |

#### 🟡 P1 - IMPORTANTES (Mejoran viabilidad)

| # | Regla | Estado Actual | Requerimiento |
|---|-------|--------------|---------------|
| **R7** | Costes transacción | ❌ NO considerado | ✅ Incluir en P&L calculation |
| **R10** | Slippage máximo | ⚠️ Parcial (post-trade) | ✅ Validar pre-trade también |
| **R11** | Trailing Stop Dinámico | ❌ NO implementado | ✅ `TrailingStopManager` |
| **R12** | Take Profit Parcial | ❌ NO implementado | ✅ `TakeProfitPartial` |
| **R16** | Reconciliación Diaria | ❌ NO implementado | ✅ `DailyReconciliation` |
| **R22** | Revisión Mensual | ❌ NO implementado | ✅ Auto-ajuste de parámetros |
| **R25-R27** | Capital Phases | ❌ NO implementado | ✅ `CapitalPhaseManager` |
| **R29** | Seguridad API Keys | ⚠️ Parcial | ✅ `SecretsManager` + encriptación |

#### 🟢 P2 - OPCIONALES (Mejoras adicionales)

| # | Regla | Estado Actual | Requerimiento |
|---|-------|--------------|---------------|
| **R5** | No averaging down | ❌ NO implementado | ✅ Validar en `execute_trade()` |
| **R6** | No romper reglas | ⚠️ Parcial | ✅ Sistema automático |
| **R8** | Tipo orden óptimo | ⚠️ Parcial | ✅ MARKET vs LIMIT según volatilidad |
| **R9** | Timing ejecución | ❌ NO implementado | ✅ Evitar horas baja liquidez |
| **R13** | Pyramiding | ❌ NO implementado | ✅ Añadir a ganadores |
| **R14** | Calidad de Datos | ⚠️ Parcial | ✅ Validar missing/stale |
| **R17** | Sin Emociones | ⚠️ Parcial | ✅ Control automático total |
| **R18** | Journal de Trades | ❌ NO implementado | ✅ `TradeJournal` |
| **R19** | Régimen de Mercado | ❌ NO implementado | ✅ `RegimeDetector` |
| **R20** | Confirmación Múltiple | ❌ NO implementado | ✅ 2-3 confirmaciones |
| **R21** | Volumen como Filtro | ❌ NO implementado | ✅ Alto volumen requerido |
| **R23** | A/B Testing | ❌ NO implementado | ✅ Test mejoras gradualmente |
| **R24** | Diversificación | ⚠️ Parcial | ✅ Múltiples estrategias |
| **R26** | Fase 10k-50k | ❌ NO implementado | ✅ Growth mode |
| **R27** | Fase 50k-500k | ❌ NO implementado | ✅ Optimization mode |

---

### 3. Spain Tax Rules (3 requisitos)

| # | Regla | Estado Actual | Requerimiento |
|---|-------|--------------|---------------|
| **IRPF** | Progresivo 19/21/23% | ⚠️ Parcial | ✅ Integrar en `execute_trade()` |
| **Dividendos UE** | 0% withholding | ❌ NO discriminado | ✅ UE vs No-UE en SpainTaxEngine |
| **Modelo 720** | Reportar >€50k extranjeros | ❌ NO implementado | ✅ `Modelo720Generator` |

---

## 🏗️ ARQUITECTURA REQUERIDA

### Servicio: ComplianceEngine (Coordinator)

**Responsabilidad única (SRP):** Coordinar el flujo completo de trading

**Interfaces requeridas (ISP):**
```python
class IAlertProcessor(Protocol):
    """Procesa alertas y genera señales"""
    async def process_alert(self, alert: AlertEvent) -> Optional[TradeSignal]: ...

class ITradeExecutor(Protocol):
    """Ejecuta trades con compliance completo"""
    async def execute_trade(self, signal: TradeSignal, portfolio: Portfolio) -> TradeResult: ...

class IStrategyCycleRunner(Protocol):
    """Ejecuta ciclos de estrategia"""
    async def run_strategy_cycle(self, market_data, portfolio) -> CycleResult: ...
```

**Dependencias (DIP):** Todas inyectadas via Protocol:
```python
class ComplianceEngine:
    def __init__(
        self,
        pre_trade_validator: IPreTradeValidator,      # R1, R2, R4
        post_trade_analyzer: IPostTradeAnalyzer,      # R10
        broker_adapter: IBrokerAdapter,               # Abstracción
        spain_tax_engine: ISpainTaxEngine,           # IRPF, Modelo 720
        decision_logger: ITradingDecisionLogger,    # R15
        kill_switch: IKillSwitchMonitor,             # R2
    ):
        ...
```

---

## 📋 MÉTODOS REQUERIDOS

### 1. process_alert() - Entry Point para Alertas

```python
async def process_alert(
    self,
    alert_event: AlertEvent,
) -> Optional[TradeSignal]:
    """
    Procesa alerta y genera señal con compliance completo.

    Flujo:
        1. Idempotency check
        2. Kill switch check (R2)
        3. Map alert to signal
        4. Pre-trade validation (R1, R4)
        5. Return signal or None

    Args:
        alert_event: Alert event de TradingBridgeOrchestrator

    Returns:
        TradeSignal si aprobado, None si rechazado
    """
```

### 2. execute_trade() - Ciclo Completo

```python
async def execute_trade(
    self,
    signal: TradeSignal,
    portfolio: Portfolio,
) -> TradeResult:
    """
    Ejecuta ciclo completo con compliance.

    Flujo:
        1. Kill switch (R2)
        2. Pre-trade validation (R1, R2, R3, R4)
        3. Execute via broker
        4. Post-trade analysis (R10)
        5. Track daily P&L
        6. Calculate Spain tax (19/21/23%)
        7. Log decision (R15)

    Args:
        signal: Trade signal
        portfolio: Current portfolio

    Returns:
        TradeResult con execution, compliance, tax
    """
```

### 3. run_strategy_cycle() - Estrategias

```python
async def run_strategy_cycle(
    self,
    market_data: MarketData,
    portfolio: Portfolio,
) -> CycleResult:
    """
    Ejecuta ciclo de estrategia con compliance.

    Flujo:
        1. Kill switch (R2)
        2. Get active strategy
        3. Generate signals
        4. Validate each signal (R1, R2, R4)
        5. Return approved signals

    Returns:
        CycleResult con señales aprobadas
    """
```

---

## 🔧 VALIDACIONES REQUERIDAS EN execute_trade()

### R1: Kelly Criterion + 2% Max

```python
# Validar antes de ejecutar:
available_cash = portfolio.available_cash
order_value = signal.quantity * signal.price
max_risk = available_cash * Decimal("0.02")  # R1: 2% máximo

if order_value > max_risk:
    raise PositionSizeExceedsRiskError(
        f"Order {order_value} exceeds 2% max ({max_risk})"
    )
```

### R2: Drawdown 15% Stop

```python
# Validar antes de ejecutar:
current_drawdown = await self.drawdown_monitor.get_current_drawdown()
if current_drawdown >= 0.15:
    raise DrawdownExceededError(
        f"Drawdown {current_drawdown:.1%} >= 15% - Trading halted"
    )
```

### R4: R:R 2:1 Minimum

```python
# Validar antes de ejecutar:
if not signal.stop_loss or not signal.target_price:
    raise InvalidSignalError("Missing SL/TP for R:R validation (R4)")

risk_per_share = abs(signal.price - signal.stop_loss)
reward_per_share = abs(signal.target_price - signal.price)
rr_ratio = reward_per_share / risk_per_share

if rr_ratio < Decimal("2.0"):
    raise InsufficientRiskRewardRatioError(
        f"R:R {rr_ratio} < 2.0 minimum (R4)"
    )
```

### R15: Logging Append-Only + Correlation ID

```python
# Antes de ejecutar, generar correlation ID:
correlation_id = str(uuid.uuid4())

# Después de ejecutar, log completo:
self.decision_logger.log_signal(
    signal=signal,
    metadata={
        "correlation_id": correlation_id,
        "risk_validation": {
            "kelly_fraction": "0.02",  # R1
            "rr_ratio": str(rr_ratio),  # R4
            "drawdown": current_drawdown,  # R2
        },
        "execution": {...},
        "tax": {
            "gross_pnl": str(estimated_pnl),
            "spain_tax": str(spain_tax),
            "tax_rate": str(tax_rate),
            "net_pnl": str(net_pnl),
        },
    }
)
```

---

## 📊 MÉTRICAS DE ÉXITO

### Antes de Refactorización (Actual)

| Métrica | Valor | Estado |
|---------|-------|--------|
| Win Rate | 40% | ❌ Bajo |
| Sharpe Ratio | 1.2 | ❌ Marginal |
| Consistencia | Pierde 56% años | ❌ Inestable |
| Capital mínimo viable | €20,000 | ⚠️ Alto |

### Después de Refactorización (Meta)

| Métrica | Meta | Estado |
|---------|------|--------|
| Win Rate | >50% | ✅ Objetivo |
| Sharpe Ratio | >2.0 | ✅ Objetivo |
| Consistencia | Gana >70% años | ✅ Objetivo |
| Capital mínimo viable | €10,000 | ✅ Mejorado |

---

## ✅ CHECKLIST DE VALIDACIÓN

Antes de marcar como COMPLETE, validar:

**SOLID:**
- [ ] Cada clase tiene 1 responsabilidad
- [ ] No modifica clases existentes (OCP)
- [ ] Usa Protocol (no clases concretas)
- [ ] Interfaces segregadas (< 5 métodos)
- [ ] Todas las dependencias inyectadas

**R1-R29:**
- [ ] R1: Kelly + 2% validado
- [ ] R2: Drawdown 15% validado
- [ ] R4: R:R 2:1 validado
- [ ] R15: Logging append-only implementado
- [ ] R28: Registro para Hacienda implementado

**Spain Tax:**
- [ ] IRPF progresivo integrado
- [ ] Dividendos UE vs No-UE discriminados
- [ ] Modelo 720 generator implementado

**Testing:**
- [ ] Tests unitarios pasan
- [ ] Tests integración pasan
- [ ] `validate_file_complete.sh` returns success: true

---

**Fin del Service Requirements**

**Versión:** 1.0
**Fecha:** 2026-02-08
**Estado:** ✅ Requirements definidos, pendiente implementación
