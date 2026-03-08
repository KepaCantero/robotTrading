#  Critical Risk Validators - Prompt

**Tarea ID:** 04_risk_validators
**Propósito:** Implementar validadores críticos: Kelly + 2% (R1), Drawdown 15% (R2), R:R 2:1 (R4)
**Tiempo estimado:** 8 horas
**Depends on:** 01_protocol_interfaces

---

##  OBJETIVO

Implementar validadores de riesgo críticos para pre-trade:
- **R1:** Kelly Criterion + 2% máximo del capital
- **R2:** Drawdown 15% stop (kill switch)
- **R3:** Stop Loss SIEMPRE obligatorio
- **R4:** Risk:Reward 2:1 mínimo

---

##  ENTREGABLES

### Archivos a crear:

1. **app/services/risk/validators/kelly_criterion_validator.py**
   - KellyCriterionValidator
   - calculate_kelly_fraction()
   - validate(capital, order_value) → KellyResult
   - update_parameters()

2. **app/services/risk/validators/drawdown_validator.py**
   - DrawdownValidator
   - validate(current_equity) → DrawdownResult
   - activate_kill_switch()
   - deactivate_kill_switch()
   - is_kill_switch_active()

3. **app/services/risk/validators/risk_reward_validator.py**
   - RiskRewardValidator
   - validate(entry_price, target_price, stop_loss) → RiskRewardResult
   - calculate_minimum_stop()

4. **app/services/risk/__init__.py**
   - Exportaciones del módulo

5. **app/services/risk/validators/__init__.py**
   - Exportaciones de validators

---

##  REQUISITOS TÉCNICOS

### Kelly Criterion Validator (R1)

```python
from decimal import Decimal
from dataclasses import dataclass


@dataclass
class KellyResult:
    """Resultado del cálculo de Kelly"""
    kelly_fraction: Decimal  # Fracción de Kelly (0-1)
    max_position: Decimal    # Tamaño máximo de posición
    passes_kelly: bool       # Si pasa el criterio Kelly
    passes_2pct: bool        # Si pasa el límite del 2%
    passes: bool             # Si pasa TODAS las validaciones


class KellyCriterionValidator:
    """
    Validador de Kelly Criterion (R1)

    Kelly Criterion = (win_rate * avg_win - loss_rate * avg_loss) / avg_win

    Máximo riesgo: 2% del capital
    """

    MAX_RISK_PCT = Decimal("0.02")  # 2% máximo

    def calculate_kelly_fraction(self) -> Decimal:
        """Calcular fracción de Kelly"""
        loss_rate = Decimal("1") - self.win_rate
        numerator = (self.win_rate * self.avg_win) - (loss_rate * self.avg_loss)
        kelly = numerator / self.avg_win
        return max(kelly, Decimal("0"))

    def validate(self, capital: Decimal, order_value: Decimal) -> KellyResult:
        """Validar posición según Kelly Criterion + 2%"""
        kelly_fraction = self.calculate_kelly_fraction()
        kelly_half = kelly_fraction * Decimal("0.5")

        max_by_kelly = capital * kelly_half
        max_by_2pct = capital * self.MAX_RISK_PCT
        max_position = min(max_by_kelly, max_by_2pct)

        passes_kelly = order_value <= max_by_kelly
        passes_2pct = order_value <= max_by_2pct
        passes = order_value <= max_position

        return KellyResult(
            kelly_fraction=kelly_fraction,
            max_position=max_position,
            passes_kelly=passes_kelly,
            passes_2pct=passes_2pct,
            passes=passes
        )
```

### Drawdown Validator (R2)

```python
@dataclass
class DrawdownResult:
    """Resultado de validación de drawdown"""
    current_drawdown: Decimal  # Drawdown actual (%)
    peak_equity: Decimal       # Equity máximo
    current_equity: Decimal    # Equity actual
    passes: bool               # Si pasa (< 15%)
    kill_switch_active: bool   # Si kill switch está activo


class DrawdownValidator:
    """
    Validador de Drawdown (R2)

    Si drawdown >= 15% → halt trading (kill switch)
    """

    MAX_DRAWDOWN_PCT = Decimal("0.15")  # 15% máximo

    def validate(self, current_equity: Decimal) -> DrawdownResult:
        """Validar drawdown actual"""
        self.update_equity(current_equity)

        if self._peak_equity == 0:
            current_drawdown = Decimal("0")
        else:
            current_drawdown = (self._peak_equity - current_equity) / self._peak_equity

        passes = current_drawdown < self.MAX_DRAWDOWN_PCT

        if not passes and not self._kill_switch_active:
            self._kill_switch_active = True
            self._kill_switch_activated_at = datetime.utcnow()

        return DrawdownResult(
            current_drawdown=current_drawdown * 100,
            peak_equity=self._peak_equity,
            current_equity=current_equity,
            passes=passes,
            kill_switch_active=self._kill_switch_active
        )
```

### Risk:Reward Validator (R4)

```python
class RiskRewardValidator:
    """
    Validador de Risk:Reward (R4)

    Mínimo R:R = 2:1
    """

    MIN_RR_RATIO = Decimal("2.0")

    def validate(
        self,
        entry_price: Decimal,
        target_price: Decimal,
        stop_loss: Decimal
    ) -> RiskRewardResult:
        """Validar relación riesgo:retorno"""
        potential_profit = abs(target_price - entry_price)
        potential_loss = abs(entry_price - stop_loss)

        if potential_loss == 0:
            return RiskRewardResult(
                rr_ratio=Decimal("0"),
                min_rr_ratio=self.MIN_RR_RATIO,
                potential_profit=potential_profit,
                potential_loss=potential_loss,
                passes=False
            )

        rr_ratio = potential_profit / potential_loss
        passes = rr_ratio >= self.MIN_RR_RATIO

        return RiskRewardResult(
            rr_ratio=rr_ratio,
            min_rr_ratio=self.MIN_RR_RATIO,
            potential_profit=potential_profit,
            potential_loss=potential_loss,
            passes=passes
        )
```

### Restricciones:

-   Usar `Decimal` para todos los cálculos monetarios
-   MAX_RISK_PCT = 2% (R1)
-   MAX_DRAWDOWN_PCT = 15% (R2)
-   MIN_RR_RATIO = 2.0 (R4)
-   Todos los validadores deben retornar Result dataclasses

---

##  VALIDACIÓN

### Validación de archivos creados:

```bash
# 1. Verificar que todos los archivos existen
ls -la app/services/risk/validators/

# 2. Validar cada archivo
for f in app/services/risk/validators/*.py; do
  python scripts/utils.py validate "$f" | jq '.success'
done

# 3. Verificar constantes
grep "MAX_RISK_PCT\|MAX_DRAWDOWN_PCT\|MIN_RR_RATIO" app/services/risk/validators/*.py

# 4. Verificar que todos devuelven resultados
grep -l "Result" app/services/risk/validators/*.py
```

### Tests manuales:

```python
# Test Kelly Validator
kelly = KellyCriterionValidator(win_rate=0.55, avg_win=0.03, avg_loss=0.02)
result = kelly.validate(capital=Decimal("10000"), order_value=Decimal("200"))
assert result.passes  # 200 < 2% de 10000

result = kelly.validate(capital=Decimal("10000"), order_value=Decimal("300"))
assert not result.passes  # 300 > 2% de 10000

# Test Drawdown Validator
dd = DrawdownValidator()
dd._peak_equity = Decimal("10000")

result = dd.validate(current_equity=Decimal("9000"))
assert result.current_drawdown == 10  # 10%
assert result.passes  # < 15%

result = dd.validate(current_equity=Decimal("8000"))
assert not result.passes  # >= 15%
assert result.kill_switch_active

# Test R:R Validator
rr = RiskRewardValidator()
result = rr.validate(
    entry_price=Decimal("100"),
    target_price=Decimal("110"),
    stop_loss=Decimal("95")
)
assert result.rr_ratio == 2  # (110-100)/(100-95) = 10/5 = 2
assert result.passes  # >= 2:1

result = rr.validate(
    entry_price=Decimal("100"),
    target_price=Decimal("105"),
    stop_loss=Decimal("95")
)
assert result.rr_ratio == 1  # (105-100)/(100-95) = 5/5 = 1
assert not result.passes  # < 2:1
```

---

##  MANEJO DE @skip-import FLAGS

Si un import no existe, usar flag en el código:

```python
# @skip-import: IPreTradeValidator not implemented yet
# TODO: Create IPreTradeValidator in app/core/protocols/i_pre_trade_validator.py
from app.core.protocols.i_pre_trade_validator import IPreTradeValidator  # type: ignore
```

---

##  CHECKPOINT

Al completar, crear checkpoint:

```json
{
  "task_id": "04_risk_validators",
  "task_name": "Critical Risk Validators Implementation",
  "started_at": "2026-02-08T10:00:00Z",
  "completed_at": "2026-02-08T18:00:00Z",
  "status": "COMPLETED",
  "progress": {
    "total_files": 5,
    "created_files": 5,
    "validated_files": 5
  },
  "outputs": {
    "files_created": [
      "app/services/risk/__init__.py",
      "app/services/risk/validators/__init__.py",
      "app/services/risk/validators/kelly_criterion_validator.py",
      "app/services/risk/validators/drawdown_validator.py",
      "app/services/risk/validators/risk_reward_validator.py"
    ],
    "validators_created": 3,
    "max_risk_pct": "2%",
    "max_drawdown_pct": "15%",
    "min_rr_ratio": "2.0",
    "validation_passed": true
  },
  "validation": {
    "all_files_validated": true,
    "black_passed": true,
    "isort_passed": true,
    "ruff_passed": true,
    "mypy_passed": true
  },
  "next_task": "08_broker_adapters",
  "errors": [],
  "warnings": [],
  "timestamp": "2026-02-08T18:00:00Z"
}
```

---

##  SUCCESS CRITERIA

La tarea está COMPLETED cuando:

- [ ] 5 archivos creados (incluyendo __init__.py)
- [ ] KellyCriterionValidator: MAX_RISK_PCT = 2%
- [ ] DrawdownValidator: MAX_DRAWDOWN_PCT = 15%
- [ ] RiskRewardValidator: MIN_RR_RATIO = 2.0
- [ ] Todos devuelven Result dataclasses
- [ ] Todos los archivos validan con `python scripts/utils.py validate`
- [ ] Tests manuales pasan
- [ ] Checkpoint creado con status "COMPLETED"

---

##  REFERENCIAS

- `rules/trading/` - Risk Management
- `rules/trading/` - R1, R2, R4
- `rules/trading/` - Reglas R1, R2, R4
- `app/core/protocols/i_pre_trade_validator.py` - Protocol interface (debe existir de tarea 01)
