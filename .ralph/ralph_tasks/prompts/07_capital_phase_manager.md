#  Capital Phase Manager - Prompt

**Tarea ID:** 07_capital_phase_manager
**Propósito:** Implementar gestión de fases de capital (R25, R26, R27)
**Tiempo estimado:** 6 horas
**Depends on:** Nada (puede ejecutarse en paralelo)

---

##  OBJETIVO

Implementar gestión dinámica de riesgo según fase de capital:
- **R25:** Survival phase (€1k-€10k) - Conservador
- **R26:** Growth phase (€10k-€50k) - Moderado
- **R27:** Optimization phase (€50k+) - Agresivo

---

##  ENTREGABLES

### Archivos a crear:

1. **app/services/capital/capital_phase_manager.py**
   - CapitalPhaseManager
   - get_current_phase() - Determina fase según capital
   - get_risk_parameters() - Parámetros según fase
   - can_increase_position_size() - Valida incrementos

2. **app/services/capital/phase_config.py**
   - PhaseConfig dataclass
   - Configuraciones para cada fase
   - Survival/Growth/Optimization parameters

3. **app/services/capital/__init__.py**

---

##  REQUISITOS TÉCNICOS

### Phase Config

```python
from decimal import Decimal
from dataclasses import dataclass
from typing import Literal
from enum import Enum


class CapitalPhase(Enum):
    """Fases de capital"""
    SURVIVAL = "survival"      # €1k - €10k
    GROWTH = "growth"          # €10k - €50k
    OPTIMIZATION = "optimization"  # €50k+


@dataclass
class PhaseRiskParameters:
    """Parámetros de riesgo por fase"""
    max_risk_per_trade_pct: Decimal  # Máximo riesgo por trade
    max_portfolio_risk_pct: Decimal   # Máximo riesgo total
    max_positions: int                # Máximo de posiciones simultáneas
    max_correlation: Decimal          # Máxima correlación entre posiciones
    position_sizing_method: str       # Método de sizing
    leverage_allowed: bool            # Si se permite apalancamiento


# Configuración por fase (R25, R26, R27)
PHASE_CONFIGS: dict[CapitalPhase, PhaseRiskParameters] = {
    CapitalPhase.SURVIVAL: PhaseRiskParameters(
        max_risk_per_trade_pct=Decimal("0.01"),    # 1% - MUY CONSERVADOR
        max_portfolio_risk_pct=Decimal("0.05"),     # 5% total
        max_positions=3,
        max_correlation=Decimal("0.5"),
        position_sizing_method="kelly_half",        # Kelly/2 muy conservador
        leverage_allowed=False                       # NO apalancamiento
    ),

    CapitalPhase.GROWTH: PhaseRiskParameters(
        max_risk_per_trade_pct=Decimal("0.02"),     # 2% - Moderado
        max_portfolio_risk_pct=Decimal("0.10"),      # 10% total
        max_positions=5,
        max_correlation=Decimal("0.7"),
        position_sizing_method="kelly",              # Kelly completo
        leverage_allowed=False                       # NO apalancamiento
    ),

    CapitalPhase.OPTIMIZATION: PhaseRiskParameters(
        max_risk_per_trade_pct=Decimal("0.03"),      # 3% - Más agresivo
        max_portfolio_risk_pct=Decimal("0.15"),      # 15% total
        max_positions=8,
        max_correlation=Decimal("0.8"),
        position_sizing_method="kelly_optimized",    # Kelly optimizado
        leverage_allowed=True                        # Apalancamiento permitido
    )
}


# Umbrales de capital por fase
PHASE_THRESHOLDS = {
    CapitalPhase.SURVIVAL: (Decimal("1000"), Decimal("10000")),      # €1k-€10k
    CapitalPhase.GROWTH: (Decimal("10000"), Decimal("50000")),       # €10k-€50k
    CapitalPhase.OPTIMIZATION: (Decimal("50000"), Decimal("999999999"))  # €50k+
}
```

### Capital Phase Manager

```python
from datetime import datetime


class CapitalPhaseManager:
    """
    Gestiona fases de capital (R25, R26, R27)

    Ajusta parámetros de riesgo dinámicamente según
    el nivel de capital actual.
    """

    def __init__(self, initial_capital: Decimal):
        """
        Args:
            initial_capital: Capital inicial en EUR
        """
        self._initial_capital = initial_capital
        self._current_capital = initial_capital
        self._current_phase = self._determine_phase(initial_capital)
        self._phase_history: list[tuple[datetime, CapitalPhase]] = [
            (datetime.utcnow(), self._current_phase)
        ]

    def update_capital(self, new_capital: Decimal) -> CapitalPhase:
        """
        Actualiza capital y determina si cambió de fase

        Args:
            new_capital: Nuevo capital actual

        Returns:
            Nueva fase (puede ser igual que anterior)
        """
        self._current_capital = new_capital
        new_phase = self._determine_phase(new_capital)

        # Si cambió de fase, registrar en historia
        if new_phase != self._current_phase:
            self._current_phase = new_phase
            self._phase_history.append((datetime.utcnow(), new_phase))

        return new_phase

    def get_current_phase(self) -> CapitalPhase:
        """Retorna fase actual"""
        return self._current_phase

    def get_risk_parameters(self) -> PhaseRiskParameters:
        """
        Retorna parámetros de riesgo para fase actual

        Returns:
            PhaseRiskParameters con configuración actual
        """
        return PHASE_CONFIGS[self._current_phase]

    def can_increase_position_size(
        self,
        current_risk_pct: Decimal,
        proposed_risk_pct: Decimal
    ) -> tuple[bool, str]:
        """
        Valida si se puede incrementar tamaño de posición

        Args:
            current_risk_pct: Riesgo actual como % del capital
            proposed_risk_pct: Riesgo propuesto

        Returns:
            (puede_incrementar, razón)
        """
        params = self.get_risk_parameters()

        # Verificar que no excede máximo por trade
        if proposed_risk_pct > params.max_risk_per_trade_pct:
            return False, (
                f"Proposed risk {proposed_risk_pct:.1%} exceeds "
                f"max {params.max_risk_per_trade_pct:.1%} for {self._current_phase.value} phase"
            )

        # Verificar que no excede riesgo total de portfolio
        total_risk = current_risk_pct + proposed_risk_pct
        if total_risk > params.max_portfolio_risk_pct:
            return False, (
                f"Total risk {total_risk:.1%} would exceed "
                f"max {params.max_portfolio_risk_pct:.1%} for {self._current_phase.value} phase"
            )

        return True, "OK"

    def get_phase_summary(self) -> dict:
        """
        Retorna resumen de fase actual

        Returns:
            Diccionario con información de fase
        """
        params = self.get_risk_parameters()

        min_capital, max_capital = PHASE_THRESHOLDS[self._current_phase]

        return {
            "current_phase": self._current_phase.value,
            "capital_range": f"€{min_capital:,.0f} - €{max_capital:,.0f}",
            "current_capital": f"€{self._current_capital:,.2f}",
            "max_risk_per_trade": f"{params.max_risk_per_trade_pct:.1%}",
            "max_portfolio_risk": f"{params.max_portfolio_risk_pct:.1%}",
            "max_positions": params.max_positions,
            "leverage_allowed": params.leverage_allowed,
            "position_sizing": params.position_sizing_method,
            "phase_duration_days": self._calculate_phase_duration()
        }

    def _determine_phase(self, capital: Decimal) -> CapitalPhase:
        """
        Determina fase basado en capital

        Args:
            capital: Capital actual

        Returns:
            CapitalPhase correspondiente
        """
        if capital < Decimal("10000"):
            return CapitalPhase.SURVIVAL
        elif capital < Decimal("50000"):
            return CapitalPhase.GROWTH
        else:
            return CapitalPhase.OPTIMIZATION

    def _calculate_phase_duration(self) -> int:
        """Calcula días en fase actual"""
        if len(self._phase_history) < 2:
            return 0

        # Encontrar cuándo empezó fase actual
        current_phase = self._current_phase
        for timestamp, phase in reversed(self._phase_history):
            if phase == current_phase:
                phase_start = timestamp
                break

        duration = datetime.utcnow() - phase_start
        return duration.days
```

### Restricciones:

-   R25: Survival (€1k-€10k) → 1% max risk, NO leverage
-   R26: Growth (€10k-€50k) → 2% max risk, NO leverage
-   R27: Optimization (€50k+) → 3% max risk, leverage permitido

---

##  VALIDACIÓN

### Validación de archivos:

```bash
# 1. Verificar archivos creados
ls -la app/services/capital/

# 2. Validar cada archivo
for f in app/services/capital/*.py; do
  python .ralph/scripts/utils.py validate "$f" | jq '.success'
done

# 3. Verificar constantes
grep "SURVIVAL\|GROWTH\|OPTIMIZATION" app/services/capital/phase_config.py
grep "1000\|10000\|50000" app/services/capital/phase_config.py
```

### Tests manuales:

```python
# Test Phase Determination
manager = CapitalPhaseManager(initial_capital=Decimal("5000"))
assert manager.get_current_phase() == CapitalPhase.SURVIVAL

# Test Phase Transition
phase = manager.update_capital(Decimal("15000"))
assert phase == CapitalPhase.GROWTH

# Test Risk Validation
manager = CapitalPhaseManager(initial_capital=Decimal("5000"))
can, reason = manager.can_increase_position_size(
    current_risk_pct=Decimal("0.02"),
    proposed_risk_pct=Decimal("0.01")
)
assert not can  # 2% + 1% = 3% > 5% max (survival)

# Test Optimization Phase
manager = CapitalPhaseManager(initial_capital=Decimal("75000"))
params = manager.get_risk_parameters()
assert params.max_risk_per_trade_pct == Decimal("0.03")
assert params.leverage_allowed == True
```

---

##  CHECKPOINT

```json
{
  "task_id": "07_capital_phase_manager",
  "task_name": "Capital Phase Manager Implementation",
  "started_at": "2026-02-08T10:00:00Z",
  "completed_at": "2026-02-08T16:00:00Z",
  "status": "COMPLETED",
  "progress": {
    "total_files": 3,
    "created_files": 3,
    "validated_files": 3
  },
  "outputs": {
    "files_created": [
      "app/services/capital/__init__.py",
      "app/services/capital/capital_phase_manager.py",
      "app/services/capital/phase_config.py"
    ],
    "r25_survival_phase": true,
    "r26_growth_phase": true,
    "r27_optimization_phase": true,
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
  "timestamp": "2026-02-08T16:00:00Z"
}
```

---

##  SUCCESS CRITERIA

- [ ] 3 archivos creados
- [ ] 3 fases definidas (Survival/Growth/Optimization)
- [ ] Umbrales: €1k-€10k, €10k-€50k, €50k+
- [ ] Parámetros de riesgo por fase
- [ ] Todos los archivos validan
- [ ] Tests manuales pasan
- [ ] Checkpoint creado

---

##  REFERENCIAS

- `rules/trading/` - R25, R26, R27
- `rules/trading/` - Capital Management rules
