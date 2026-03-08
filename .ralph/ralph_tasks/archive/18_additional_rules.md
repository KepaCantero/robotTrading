# Additional Trading Rules - Prompt

**Tarea ID:** 18_additional_rules
**Propósito:** Implementar reglas adicionales de trading R6-R24
**Tiempo estimado:** 24 horas
**Depends on:** 01_protocol_interfaces (Foundation)
**Prioridad:** P2 (Opcional)

---

## OBJETIVO

Implementar reglas adicionales de trading que mejoran la robustez del sistema pero no son críticas para producción.

---

## REGLAS A IMPLEMENTAR

### R6: Overfitting Prevention
```python
# app/services/trading_rules/overfitting_prevention.py
class OverfittingPrevention:
    def validate_parameters_ratio(self, n_params: int, n_observations: int) -> bool:
        """Ratio debe ser < 1:30"""
        return n_params / n_observations < 0.033

    def walk_forward_validation(self, data, n_splits: int = 5) -> dict:
        """Walk-forward cross-validation"""
        pass
```

### R7: Monte Carlo Simulation
```python
# app/services/trading_rules/monte_carlo.py
class MonteCarloSimulator:
    def run_simulations(self, returns: pd.Series, n_sims: int = 1000) -> dict:
        """Ejecutar simulaciones Monte Carlo"""
        pass

    def calculate_var(self, confidence: float = 0.95) -> Decimal:
        """Value at Risk"""
        pass
```

### R9: Execution Timing
```python
# app/services/trading_rules/execution_timing.py
class ExecutionTimingValidator:
    AVOID_HOURS = [
        (9, 30, 10, 0),   # Market open volatility
        (12, 0, 13, 0),   # Lunch trap
        (15, 30, 16, 0),  # Market close volatility
    ]

    def is_good_execution_time(self, dt: datetime) -> bool:
        """Verificar si es buen momento para ejecutar"""
        pass
```

### R14: Data Quality
```python
# app/services/trading_rules/data_quality.py
class DataQualityValidator:
    def check_missing_data(self, data: pd.DataFrame, threshold: float = 0.05) -> bool:
        """Verificar datos faltantes"""
        pass

    def detect_outliers(self, data: pd.Series, n_std: float = 3.0) -> pd.Series:
        """Detectar outliers"""
        pass
```

### R17-R24: Additional implementations
Ver estructura de archivos en la tarea YAML.

---

## SUCCESS CRITERIA

- [ ] Todas las reglas implementadas
- [ ] Tests unitarios creados
- [ ] Validación con utils.py pasa
- [ ] Documentación actualizada

---

## CHECKPOINT

```json
{
  "task_id": "18_additional_rules",
  "rules_implemented": [],
  "rules_pending": [],
  "validation_passed": true
}
```
