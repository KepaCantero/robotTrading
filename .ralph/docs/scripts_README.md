# 📁 Scripts Directory - Organized Structure

**Fecha:** 2026-02-08
**Objetivo:** Scripts organizados por categoría con CLI unificado

---

## 🗂️ Estructura de Directorios

```
scripts/
├── utils.py                    # ⭐ CLI UNIFICADO - Usa este para todo
├── README.md                   (ESTE ARCHIVO)
│
├── validation/                 # Scripts de validación
│   ├── validate_file_complete.sh   # ⭐ Validación completa de archivo
│   ├── validate_file_comprehensive.sh
│   ├── validate_config.sh
│   └── verify_*.py               # Scripts de verificación
│
├── audit/                      # Scripts de auditoría
│   ├── get_critical_files.py      # Obtener archivos críticos
│   ├── get_p1_files.py            # Obtener archivos P1
│   ├── get_p2_files.py            # Obtener archivos P2
│   ├── gap_audit_scanner.py       # Escanear gaps
│   └── smart_rule_classifier.py   # Clasificador de reglas
│
├── data/                       # Scripts de datos
│   ├── download_*.py             # Descargar datos de mercado
│   └── evaluate_*.py             # Evaluar pares/estrategias
│
├── deployment/                 # Scripts de deployment
│   ├── deploy_*.sh               # Deploy a AWS/Docker
│   ├── setup_*.sh                # Setup de entorno
│   └── rollback_*.sh             # Rollback de deployment
│
├── db/                         # Scripts de base de datos
│   ├── database_manager.sh       # Gestión de DB
│   ├── migrate_*.py              # Migraciones
│   └── migrations/               # Archivos de migración
│
├── optimization/               # Scripts de optimización
│   ├── run_*.py                  # Ejecutar optimizaciones
│   └── optimize_*.py             # Optimizar estrategias
│
├── util/                       # Scripts varios
│   ├── fix_*.sh                  # Fixes rápidos
│   └── backup.sh                 # Backup
│
├── backtesting/                # Scripts de backtesting
│   └── (subcarpetas específicas)
│
└── archived/                   # Scripts obsoletos/archivados
    └── (ya no se usan)
```

---

## 🚀 Uso Rápido con CLI Unificado

```bash
# Validar archivo
python scripts/utils.py validate app/services/compliance_engine.py

# Validar y arreglar automáticamente
python scripts/utils.py validate app/services/compliance_engine.py --fix

# Listar archivos críticos
python scripts/utils.py list_files --category critical

# Auditar archivos críticos
python scripts/utils.py audit_files --category critical

# Verificar progreso de tarea
python scripts/utils.py check_progress --task compliance_refactor

# Marcar archivos como PASSED
python scripts/utils.py mark_files --status PASSED --category critical
```

---

## 📋 Scripts Principales

### Validación

| Script | Uso | Descripción |
|--------|-----|-------------|
| `utils.py validate` | `python scripts/utils.py validate <file>` | Validar archivo completo |
| `validation/validate_file_complete.sh` | `./scripts/validation/validate_file_complete.sh <file>` | Validación con JSON output |
| `validation/validate_config.sh` | `./scripts/validation/validate_config.sh` | Validar configuración |

### Auditoría

| Script | Uso | Descripción |
|--------|-----|-------------|
| `utils.py list_files` | `python scripts/utils.py list_files --category critical` | Listar archivos por categoría |
| `utils.py audit_files` | `python scripts/utils.py audit_files --category p1` | Auditar archivos |
| `audit/get_critical_files.py` | `python scripts/audit/get_critical_files.py` | Obtener archivos críticos |
| `audit/smart_rule_classifier.py` | `python scripts/audit/smart_rule_classifier.py <file>` | Clasificar reglas aplicables |

### Datos

| Script | Uso | Descripción |
|--------|-----|-------------|
| `data/download_yahoo_v8.py` | `python scripts/data/download_yahoo_v8.py` | Descargar datos Yahoo |
| `data/download_portfolio_data.py` | `python scripts/data/download_portfolio_data.py` | Descargar datos de portfolio |

---

## 🔧 Validación de Archivos

El script `validate_file_complete.sh` ejecuta TODOS estos checks:

- **Black** - Formato de código PEP8
- **Isort** - Orden de imports
- **Ruff** - Linting rápido
- **Flake8** - Linting completo
- **Pylint** - Calidad de código
- **Mypy** - Type checking
- **Bandit** - Security issues
- **Radon** - Complejidad ciclomática (< 10)

### Output JSON:

```json
{
  "file": "app/services/compliance_engine.py",
  "checks": {
    "black": {"status": "passed"},
    "isort": {"status": "passed"},
    "ruff": {"status": "passed"},
    "flake8": {"status": "passed"},
    "pylint": {"status": "passed"},
    "mypy": {"status": "passed"},
    "bandit": {"status": "passed"},
    "radon": {"status": "passed", "cc": 5.2}
  },
  "summary": {
    "total_checks": 8,
    "passed": 8,
    "failed": 0,
    "success": true
  }
}
```

---

## 📊 Categorías de Archivos

- **critical**: Archivos críticos para producción (bloquean)
- **p1**: Archivos importantes (mejoran viabilidad)
- **p2**: Archivos opcionales (mejoras adicionales)

---

**Última actualización:** 2026-02-08
