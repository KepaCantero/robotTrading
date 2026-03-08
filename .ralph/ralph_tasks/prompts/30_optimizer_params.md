# Optimizer Parameters - Prompt

**Tarea ID:** 30_optimizer_params
**Propósito:** Optimizadores usan central config
**Tiempo estimado:** 4 horas
**Prioridad:** P1 (Importante)
**Depends on:** 26_central_config_consolidation

---

## OBJETIVO

Todos los optimizadores usan parámetros de central config (no hardcoded).

## ARCHIVOS A ACTUALIZAR

- app/optimization/parameter/optimizer.py
- app/optimization/parameter/grid_search.py
- app/optimization/parameter/bayesian_optimizer.py
- app/backtesting/optimization/strategy_optimizer.py

## PATRÓN

```python
# ANTES
class ParameterOptimizer:
    def __init__(self):
        self.param_ranges = {
            "position_size": (0.01, 0.05),  # Hardcoded!
        }

# DESPUÉS
from app.shared.config import CentralConfig

class ParameterOptimizer:
    def __init__(self, config: CentralConfig):
        self.config = config
        self.param_ranges = {
            "position_size": (
                config.trading.min_position_size_pct,
                config.trading.max_position_size_pct
            ),
        }
```

## SUCCESS CRITERIA

- [ ] No hardcoded parameter values
- [ ] All optimizers accept CentralConfig
- [ ] Tests updated and passing
