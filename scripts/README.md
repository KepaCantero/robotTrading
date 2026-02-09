# 📁 AlgoTrading Scripts - Índice Completo

**Fecha:** 2026-02-08
**Objetivo:** Documentación unificada de todos los scripts del proyecto

---

## 🎯 Estructura de Directorios

```
scripts/
├── README.md                   # ESTE ARCHIVO
├── utils.py                    # CLI unificado
│
├── backtesting/                # Scripts de backtesting
│   ├── run_comprehensive_backtest.py
│   ├── run_all_backtests.py
│   └── ...
│
├── validation/                 # Scripts de validación
│   └── validate_file_complete.sh
│
├── audit/                      # Scripts de auditoría
│   ├── get_critical_files.py
│   ├── get_p1_files.py
│   └── ...
│
└── processing/                # Scripts de procesamiento
    ├── phase4_remove_all_fallbacks.py
    └── ...
```

---

## 🚀 CLI Unificado

### Uso

```bash
python scripts/utils.py <comando> [argumentos]
```

### Comandos Disponibles

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `validate` | Validar archivo | `python scripts/utils.py validate app/file.py` |
| `list_files` | Listar archivos por categoría | `python scripts/utils.py list_files --category critical` |
| `audit_files` | Auditar archivos | `python scripts/utils.py audit_files --category p1` |
| `check_progress` | Verificar progreso | `python scripts/utils.py check_progress --task compliance_refactor` |
| `mark_files` | Marcar archivos con estado | `python scripts/utils.py mark_files --status PASSED` |

---

## 📊 Scripts de Backtesting

### run_comprehensive_backtest.py

**Propósito:** Ejecutar backtest completo con todas las estrategias

**Uso:**
```bash
python scripts/backtesting/run_comprehensive_backtest.py
```

**Output:**
- Reporte de backtest
- Métricas de rendimiento
- Archivo de resultados JSON

### run_all_backtests.py

**Propósito:** Ejecutar TODOS los backtests

**Uso:**
```bash
python scripts/backtesting/run_all_backtests.py
```

---

## ✅ Scripts de Validación

### validate_file_complete.sh

**Propósito:** Validación completa de archivos Python

**Uso:**
```bash
scripts/validation/validate_file_complete.sh <archivo.py>
```

**Valida:**
- Formato (black, isort)
- Linting (ruff, flake8)
- Type hints (mypy)
- Seguridad (bandit)
- Complejidad (radon)

**Output:** JSON con `success: true/false`

---

## 🔍 Scripts de Auditoría

### get_critical_files.py

**Propósito:** Listar archivos críticos (P0)

**Uso:**
```bash
python scripts/audit/get_critical_files.py
```

### get_p1_files.py

**Propósito:** Listar archivos P1

**Uso:**
```bash
python scripts/audit/get_p1_files.py
```

---

## 🔧 Scripts de Procesamiento

### phase4_remove_all_fallbacks.py

**Propósito:** Eliminar todos los fallbacks de imports

**Uso:**
```bash
python scripts/processing/phase4_remove_all_fallbacks.py
```

**Qué hace:**
- Busca `try/except ImportError` patterns
- Reemplaza con `@skip-import` flags
- Actualiza imports para usar TYPE_CHECKING

---

## 📝 Estándares de Codificación

### Formato de Scripts

Todos los scripts deben seguir:

```python
#!/usr/bin/env python3
"""
Módulo: script_name.py
Propósito: Descripción breve del script
Uso: python scripts/utils.py <comando>
"""
```

### Validaciones

- ✅ Shebang `#!/usr/bin/env python3`
- ✅ Docstring con propósito y uso
- ✅ Type hints en funciones
- ✅ Error handling con try/except
- ✅ Logging con `structlog` si es necesario

---

## 🔗 Integración con Ralph

### Scripts como wrappers de tareas Ralph

Los scripts pueden ejecutar tareas Ralph:

```python
def run_ralph_task(task_id: str) -> dict:
    """Ejecuta tarea Ralph y retorna resultado"""
    result = subprocess.run(
        ["ralph", "run", f".ralph/ralph_tasks/{task_id}.yml"],
        capture_output=True,
        text=True
    )
    return json.loads(result.stdout)
```

---

## ⚠️ Scripts Duplicados

Los siguientes scripts están duplicados y deben fusionarse:

| Duplicado | Mantener | Eliminar |
|-----------|---------|---------|
| `phase4_remove_all_fallbacks.py` | ✅ | - |
| `phase5_eliminate_all_import_fallbacks.py` | - | ❌ |
| `run_comprehensive_backtest.py` | ✅ | - |
| `run_backtest.py` | - | ❌ (funcionalidad en comprehensive) |

---

## 🚨 Scripts Sin Mantenimiento

Los siguientes scripts necesitan actualización:

| Script | Última actualización | Acción |
|--------|---------------------|--------|
| `generate_report.py` | 2024-06 | Actualizar para nuevos formatos |
| `export_trades.py` | 2024-05 | Revisar para nuevo schema |
| `calculate_metrics.py` | 2024-04 | Añadir métricas faltantes |

---

## ✅ Checklist de Scripts

Antes de considerar el sistema de scripts completo:

- [ ] Todos los scripts tienen README individual
- [ ] Todos los scripts tienen docstrings
- [ ] Todos los scripts tienen type hints
- [ ] No hay scripts duplicados
- [ ] Todos los scripts están documentados aquí
- [ ] CLI unificado (`utils.py`) funciona
- [ ] Scripts de validación funcionan
- [ ] Scripts están integrados con Ralph

---

## 📈 Próximos Pasos

1. **Crear prompts faltantes** para tareas Ralph
2. **Eliminar scripts duplicados**
3. **Actualizar scripts desactualizados**
4. **Crear scripts de wrappers** para tareas Ralph
5. **Integrar sistema de checkpoints** con scripts

---

**Última actualización:** 2026-02-08
**Estado:** ✅ Documentación unificada creada
