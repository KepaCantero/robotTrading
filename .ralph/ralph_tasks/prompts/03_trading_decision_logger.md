#  Trading Decision Logger - Prompt

**Tarea ID:** 03_trading_decision_logger
**Propósito:** Implementar logger append-only con correlation ID (R15, R28)
**Tiempo estimado:** 6 horas
**Depends on:** 01_protocol_interfaces

---

##  OBJETIVO

Implementar logging append-only con correlation ID para auditoría:
- **R15:** Logging append-only + correlation ID obligatorio
- **R28:** Registrar para Hacienda (5 años mínimo)
- **LOG-001:** Structured logging con timestamp
- **AUD-001:** Audit trail completo

---

##  ENTREGABLES

### Archivos a crear:

1. **app/services/logging/log_entry.py**
   - LogEntry inmutable (frozen dataclass)
   - correlation_id único (UUID)
   - timestamp ISO 8601
   - event_type, data, metadata

2. **app/services/logging/append_only_log.py**
   - AppendOnlyLog storage
   - Solo append (no delete, no update)
   - Persistencia en disco
   - Rotación por fecha

3. **app/services/logging/trading_decision_logger.py**
   - TradingDecisionLogger (implementa ITradingDecisionLogger)
   - log_signal(), log_execution(), log_validation_result()
   - export_for_hacienda() - 5 años de datos

4. **app/services/logging/__init__.py**
   - Exportaciones del módulo

---

##  REQUISITOS TÉCNICOS

### LogEntry Inmutable

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any
import uuid


@dataclass(frozen=True)
class LogEntry:
    """
    Entrada de log inmutable (append-only)

    Atributos:
        correlation_id: ID único que relaciona todas las entradas de una operación
        timestamp: Timestamp ISO 8601
        event_type: Tipo de evento (signal, validation, execution, result)
        data: Datos del evento (JSON serializable)
        metadata: Metadatos adicionales
    """
    correlation_id: str
    timestamp: str
    event_type: str
    data: dict[str, Any]
    metadata: dict[str, Any]

    @classmethod
    def create(cls, event_type: str, data: dict, metadata: Optional[dict] = None) -> "LogEntry":
        """Crear nueva entrada de log con correlation ID único"""
        correlation_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"

        return cls(
            correlation_id=correlation_id,
            timestamp=timestamp,
            event_type=event_type,
            data=data,
            metadata=metadata or {}
        )
```

### Append-Only Storage

```python
from typing import List
from pathlib import Path
import json


class AppendOnlyLog:
    """
    Log append-only para decisiones de trading

    Características:
    - Solo append (no delete, no update)
    - Persistencia en disco
    - Rotación por fecha
    """

    def __init__(self, log_dir: str = ".ralph/logs/trading"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def append(self, entry: LogEntry) -> None:
        """Añadir entrada al log (append-only)"""
        # Añadir entrada al archivo (append-only)
        with open(self._current_file, "a") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")
```

### Restricciones:

-   LogEntry debe ser `frozen=True` (inmutable)
-   AppendOnlyLog NO puede tener métodos delete() o update()
-   correlation_id debe ser UUID v4
-   timestamp debe ser ISO 8601 con sufijo "Z"
-   R28: Exportar mínimo 5 años de datos

---

##  VALIDACIÓN

### Validación de archivos creados:

```bash
# 1. Verificar que todos los archivos existen
ls -la app/services/logging/

# 2. Validar cada archivo
for f in app/services/logging/*.py; do
  python scripts/utils.py validate "$f" | jq '.success'
done

# 3. Verificar que LogEntry es inmutable (frozen=True)
grep "@dataclass(frozen=True)" app/services/logging/log_entry.py

# 4. Verificar correlation ID
grep "correlation_id" app/services/logging/log_entry.py | wc -l  # Debe ser >= 3

# 5. Verificar append-only
grep "append" app/services/logging/append_only_log.py | wc -l  # Debe ser >= 2
grep -E "def (delete|update)" app/services/logging/append_only_log.py
# No debe retornar nada (no existir delete/update)
```

### Test manual:

```python
# Test básico
from app.services.logging.trading_decision_logger import TradingDecisionLogger

logger = TradingDecisionLogger()

# Log signal
signal = {"symbol": "SAN", "action": "BUY", "quantity": 100, "price": 3.50}
correlation_id = logger.log_signal(signal)
print(f"Correlation ID: {correlation_id}")

# Log execution
result = {"order_id": "12345", "status": "FILLED", "filled_price": 3.52}
logger.log_execution(correlation_id, result)

# Log validation
logger.log_validation_result(correlation_id, "R1_Kelly", True)

# Obtener logs
logs = logger.get_logs_by_correlation_id(correlation_id)
print(f"Logs: {len(logs)} entries")

# Exportar para Hacienda
hacienda_logs = logger.export_for_hacienda(2026)
print(f"Hacienda logs: {len(hacienda_logs)} operations")
```

---

##  MANEJO DE @skip-import FLAGS

Si un import no existe, usar flag en el código:

```python
# @skip-import: ITradingDecisionLogger not implemented yet
# TODO: Create ITradingDecisionLogger in app/core/protocols/i_trading_decision_logger.py
from app.core.protocols.i_trading_decision_logger import ITradingDecisionLogger  # type: ignore
```

---

##  CHECKPOINT

Al completar, crear checkpoint:

```json
{
  "task_id": "03_trading_decision_logger",
  "task_name": "Trading Decision Logger Implementation",
  "started_at": "2026-02-08T10:00:00Z",
  "completed_at": "2026-02-08T16:00:00Z",
  "status": "COMPLETED",
  "progress": {
    "total_files": 4,
    "created_files": 4,
    "validated_files": 4
  },
  "outputs": {
    "files_created": [
      "app/services/logging/__init__.py",
      "app/services/logging/log_entry.py",
      "app/services/logging/append_only_log.py",
      "app/services/logging/trading_decision_logger.py"
    ],
    "log_entry_frozen": true,
    "append_only_enforced": true,
    "validation_passed": true
  },
  "validation": {
    "all_files_validated": true,
    "black_passed": true,
    "isort_passed": true,
    "ruff_passed": true,
    "mypy_passed": true
  },
  "next_task": "04_risk_validators",
  "errors": [],
  "warnings": [],
  "timestamp": "2026-02-08T16:00:00Z"
}
```

---

##  SUCCESS CRITERIA

La tarea está COMPLETED cuando:

- [ ] 4 archivos creados (incluyendo __init__.py)
- [ ] LogEntry es `frozen=True` (inmutable)
- [ ] AppendOnlyLog NO tiene delete() ni update()
- [ ] correlation_id usa UUID v4
- [ ] timestamps son ISO 8601 + "Z"
- [ ] export_for_hacienda() exporta 5 años
- [ ] Todos los archivos validan con `python scripts/utils.py validate`
- [ ] Test manual pasa
- [ ] Checkpoint creado con status "COMPLETED"

---

##  REFERENCIAS

- `.ralph/docs/requirements/SERVICE_REQUIREMENTS.md` - R15 (Logging), R28 (Registro Hacienda)
- `.ralph/rules/rules_mapping.yml` - R15, R28, LOG-001, AUD-001
- `app/core/protocols/i_trading_decision_logger.py` - Protocol interface (debe existir de tarea 01)
