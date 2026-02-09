# 📁 Ralph Checkpoints System

**Fecha:** 2026-02-08
**Propósito:** Sistema de checkpoints para persistencia de estado entre ejecuciones de Ralph

---

## 🎯 Sistema de Checkpoints

### Estructura de Directorio

```
.ralph/checkpoints/
├── README.md                    # ESTE ARCHIVO
├── 00_master_orchestrator_checkpoint.json    # Checkpoint global
├── 01_protocol_interfaces_checkpoint.json
├── 02_spain_tax_engine_checkpoint.json
├── 03_trading_decision_logger_checkpoint.json
├── 04_risk_validators_checkpoint.json
├── 05_broker_adapters_checkpoint.json
└── ... (uno por tarea)
```

---

## 📋 Formato de Checkpoint

### Checkpoint de Tarea Individual

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
    "modified_files": 0,
    "validated_files": 10
  },
  "outputs": {
    "files_created": [
      "app/core/protocols/i_pre_trade_validator.py",
      "app/core/protocols/i_trade_executor.py",
      "..."
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

### Estados de Tarea

| Estado | Descripción |
|--------|-------------|
| `PENDING` | Tarea no iniciada |
| `IN_PROGRESS` | Tarea en ejecución |
| `COMPLETED` | Tarea completada exitosamente |
| `FAILED` | Tarea falló |
| `BLOCKED` | Tarea bloqueada por dependencias |
| `SKIPPED` | Tarea saltada |

---

## 🔄 Checkpoint Global (Master Orchestrator)

```json
{
  "master_orchestrator": {
    "started_at": "2026-02-08T10:00:00Z",
    "current_phase": 1,
    "current_task": "01_protocol_interfaces",
    "total_tasks": 18,
    "completed_tasks": 0,
    "failed_tasks": 0,
    "blocked_tasks": 0,
    "skipped_tasks": 0
  },
  "phases": {
    "phase_1_foundation": {
      "name": "Foundation Layer",
      "tasks": ["01_protocol_interfaces", "02_spain_tax_engine", "03_trading_decision_logger", "04_risk_validators"],
      "status": "IN_PROGRESS",
      "completed": 0,
      "total": 4
    },
    "phase_2_infrastructure": {
      "name": "Infrastructure & Services",
      "status": "PENDING",
      "completed": 0,
      "total": 4
    }
  },
  "tasks": {
    "01_protocol_interfaces": {
      "status": "COMPLETED",
      "phase": 1,
      "started_at": "2026-02-08T10:00:00Z",
      "completed_at": "2026-02-08T14:00:00Z"
    },
    "02_spain_tax_engine": {
      "status": "PENDING",
      "phase": 1,
      "depends_on": ["01_protocol_interfaces"]
    }
  }
}
```

---

## 🛠️ Uso del Sistema de Checkpoints

### Leer Checkpoint

```bash
# Leer checkpoint de tarea específica
cat .ralph/checkpoints/01_protocol_interfaces_checkpoint.json | jq

# Leer checkpoint global
cat .ralph/checkpoints/00_master_orchestrator_checkpoint.json | jq
```

### Actualizar Checkpoint

```python
import json
from pathlib import Path
from datetime import datetime

def update_checkpoint(task_id: str, status: str, **kwargs):
    """Actualiza checkpoint de tarea"""
    checkpoint_file = Path(f".ralph/checkpoints/{task_id}_checkpoint.json")

    # Leer existente o crear nuevo
    if checkpoint_file.exists():
        with open(checkpoint_file) as f:
            checkpoint = json.load(f)
    else:
        checkpoint = {
            "task_id": task_id,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "status": "PENDING"
        }

    # Actualizar
    checkpoint["status"] = status
    checkpoint["timestamp"] = datetime.utcnow().isoformat() + "Z"
    checkpoint.update(kwargs)

    # Guardar
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoint, f, indent=2)

    return checkpoint
```

### Validar Checkpoint

```bash
# Verificar que una tarea está completada
jq '.status == "COMPLETED"' .ralph/checkpoints/01_protocol_interfaces_checkpoint.json

# Verificar que todos los archivos validaron
jq '.validation.all_files_validated' .ralph/checkpoints/01_protocol_interfaces_checkpoint.json

# Obtener siguiente tarea
jq -r '.next_task' .ralph/checkpoints/01_protocol_interfaces_checkpoint.json
```

---

## ✅ Validación de Checkpoints

Antes de marcar una tarea como COMPLETED:

1. **Todos los archivos creados existen**
   ```bash
   for file in $(jq -r '.outputs.files_created[]' checkpoint.json); do
     [ -f "$file" ] || echo "MISSING: $file"
   done
   ```

2. **Todos los archivos validan**
   ```bash
   jq '.validation.all_files_validated == true' checkpoint.json
   ```

3. **No hay flags sin resolver**
   ```bash
   grep -r "@todo\|@skip-import\|@clarify" app/ | wc -l  # Debe ser 0
   ```

4. **Tests manuales pasan**
   ```bash
   # Ejecutar tests en documentation de tarea
   ```

---

## 🚨 Manejo de Errores

### Si una tarea falla:

1. **Marcar como FAILED en checkpoint**
   ```json
   {
     "status": "FAILED",
     "errors": [
       {
         "type": "ValidationError",
         "message": "File app/core/protocols/x.py does not validate",
         "timestamp": "2026-02-08T..."
       }
     ]
   }
   ```

2. **No continuar a siguientes tareas**
   - El master orchestrator debe detenerse
   - Revisar errores y corregir
   - Reintentar desde tarea fallida

3. **Opción de reanudar**
   ```bash
   # Reanudar desde tarea fallida
   ralph run .ralph/ralph_tasks/01_protocol_interfaces.yml --resume
   ```

---

## 📊 Reportes

### Resumen de Progreso

```bash
# Generar reporte de progreso
python scripts/utils.py check_progress --task master_orchestrator
```

Output:
```json
{
  "total_tasks": 18,
  "completed_tasks": 4,
  "failed_tasks": 0,
  "blocked_tasks": 0,
  "progress_percentage": 22.2,
  "estimated_remaining_hours": 130,
  "current_phase": "phase_2_infrastructure"
}
```

---

**Última actualización:** 2026-02-08
**Estado:** ✅ Sistema de checkpoints documentado
