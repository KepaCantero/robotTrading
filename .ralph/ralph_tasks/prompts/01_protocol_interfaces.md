# 🔧 Protocol Interfaces Foundation - Prompt

**Tarea ID:** 01_protocol_interfaces
**Propósito:** Crear interfaces Protocol para arquitectura SOLID
**Tiempo estimado:** 4 horas
**Depends on:** Nada (es la primera tarea)

---

## 📋 OBJETIVO

Crear 9 interfaces Protocol siguiendo los principios SOLID:
- **ISP-001:** Cada Protocol < 5 métodos (Interface Segregation)
- **LSP-001:** Usar typing.Protocol, no abc.ABC (Liskov Substitution)
- **DIP-001:** Todas las dependencias usarán estos Protocol (Dependency Inversion)

---

## 🎯 ENTREGABLES

### Archivos a crear:

1. **app/core/protocols/i_pre_trade_validator.py**
   - Validaciones pre-trade (R1, R2, R4)
   - Máximo 5 métodos

2. **app/core/protocols/i_trade_executor.py**
   - Ejecuta trades vía broker
   - Máximo 5 métodos

3. **app/core/protocols/i_post_trade_analyzer.py**
   - Análisis post-trade (R11, R12, R13)
   - Máximo 5 métodos

4. **app/core/protocols/i_broker_adapter.py**
   - Adapter para broker
   - Máximo 5 métodos

5. **app/core/protocols/i_spain_tax_engine.py**
   - Motor de impuestos España
   - Máximo 5 métodos

6. **app/core/protocols/i_trading_decision_logger.py**
   - Logger append-only con correlation ID (R15, R28)
   - Máximo 5 métodos

7. **app/core/protocols/i_kill_switch_monitor.py**
   - Monitor de drawdown máximo (R2)
   - Máximo 5 métodos

8. **app/core/protocols/i_alert_processor.py**
   - Procesa alertas de mercado
   - Máximo 5 métodos

9. **app/core/protocols/i_strategy_cycle_runner.py**
   - Ejecuta ciclos de estrategia
   - Máximo 5 métodos

10. **app/core/protocols/__init__.py**
    - Exporta todos los Protocol

---

## 📐 REQUISITOS TÉCNICOS

### Protocol Interface Structure

```python
from typing import Protocol

class IName(Protocol):
    """Descripción del Protocol"""

    def method_name(self, param: type) -> return_type:
        """Descripción del método"""
        ...

    # Máximo 5 métodos por Protocol (ISP-001)
```

### Restricciones:

- ✅ Usar `typing.Protocol`
- ❌ NO usar `abc.ABC` o `abc.ABCMeta`
- ✅ Máximo 5 métodos por Protocol
- ✅ Todos los métodos deben tener type hints
- ✅ Usar `...` (ellipsis) para cuerpos de método vacíos

---

## ✅ VALIDACIÓN

### Validación de archivos creados:

```bash
# 1. Verificar que todos los archivos existen
ls -la app/core/protocols/i_*.py
# Debe mostrar 9 archivos

# 2. Verificar que todos usan typing.Protocol
grep "class.*Protocol" app/core/protocols/*.py | wc -l
# Debe ser 9

# 3. Verificar que ninguno usa abc.ABC
grep "abc.ABC" app/core/protocols/*.py
# No debe retornar nada

# 4. Verificar que cada Protocol tiene <= 5 métodos
for file in app/core/protocols/i_*.py; do
  echo "Checking $file..."
  grep -A 20 "class.*Protocol" "$file" | grep "def " | wc -l
  # Cada uno debe ser <= 5
done

# 5. Validar con python utils.py
for file in app/core/protocols/*.py; do
  python scripts/utils.py validate "$file" | jq '.success'
  # Todos deben retornar true
done

# 6. Verificar imports
python -c "from app.core.protocols import IPreTradeValidator; print('✅ IPreTradeValidator')"
python -c "from app.core.protocols import ITradeExecutor; print('✅ ITradeExecutor')"
python -c "from app.core.protocols import IPostTradeAnalyzer; print('✅ IPostTradeAnalyzer')"
python -c "from app.core.protocols import IBrokerAdapter; print('✅ IBrokerAdapter')"
python -c "from app.core.protocols import ISpainTaxEngine; print('✅ ISpainTaxEngine')"
python -c "from app.core.protocols import ITradingDecisionLogger; print('✅ ITradingDecisionLogger')"
python -c "from app.core.protocols import IKillSwitchMonitor; print('✅ IKillSwitchMonitor')"
python -c "from app.core.protocols import IAlertProcessor; print('✅ IAlertProcessor')"
python -c "from app.core.protocols import IStrategyCycleRunner; print('✅ IStrategyCycleRunner')"
```

---

## 🚨 MANEJO DE @skip-import FLAGS

Si un import no existe, usar flag en el código:

```python
# @skip-import: TradeResult not implemented yet
# TODO: Create TradeResult in app/core/trade_result.py
from app.core.trade_result import TradeResult  # type: ignore
```

---

## 📝 CHECKPOINT

Al completar, crear checkpoint:

```json
{
  "task_id": "01_protocol_interfaces",
  "task_name": "Protocol Interfaces Foundation",
  "started_at": "2026-02-08T10:00:00Z",
  "completed_at": "2026-02-08T14:00:00Z",
  "status": "COMPLETED",
  "progress": {
    "total_files": 10,
    "created_files": 10,
    "validated_files": 10
  },
  "outputs": {
    "files_created": [
      "app/core/protocols/i_pre_trade_validator.py",
      "app/core/protocols/i_trade_executor.py",
      "app/core/protocols/i_post_trade_analyzer.py",
      "app/core/protocols/i_broker_adapter.py",
      "app/core/protocols/i_spain_tax_engine.py",
      "app/core/protocols/i_trading_decision_logger.py",
      "app/core/protocols/i_kill_switch_monitor.py",
      "app/core/protocols/i_alert_processor.py",
      "app/core/protocols/i_strategy_cycle_runner.py",
      "app/core/protocols/__init__.py"
    ],
    "protocols_created": 9,
    "validation_passed": true
  },
  "validation": {
    "all_files_validated": true,
    "black_passed": true,
    "isort_passed": true,
    "ruff_passed": true,
    "mypy_passed": true
  },
  "next_task": "02_spain_tax_engine",
  "errors": [],
  "warnings": [],
  "timestamp": "2026-02-08T14:00:00Z"
}
```

---

## 🎯 SUCCESS CRITERIA

La tarea está COMPLETED cuando:

- [ ] 9 archivos de Protocol creados
- [ ] 1 archivo __init__.py creado
- [ ] Todos los archivos validan con `python scripts/utils.py validate`
- [ ] Todos usan `typing.Protocol` (ninguno usa `abc.ABC`)
- [ ] Cada Protocol tiene <= 5 métodos
- [ ] Todos los imports funcionan
- [ ] Checkpoint creado con status "COMPLETED"

---

## 📚 REFERENCIAS

- `rules/trading/` - SOLID Principles
- `rules/trading/` - SOLID rules
- `.ralph/ralph_templates/agents/requirement_generator_agent.yml` - Requirement generator
