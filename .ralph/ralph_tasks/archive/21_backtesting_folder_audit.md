# Comprehensive Backtest Test Creation - Prompt

**Tarea ID:** 21_backtesting_folder_audit
**Propósito:** Crear test completo de backtesting usando ComplianceEngine
**Tiempo estimado:** 6-8 horas
**Depends on:** 09_compliance_engine_refactor, 17_backtest_fixes

---

## OBJETIVO

Crear un test completo de backtesting (`tests/backtesting/test_comprehensive_backtesting_via_compliance.py`) que reemplace `scripts/archived/comprehensive_oneYear_test.py` pero usando **ComplianceEngine** en lugar de usar `ComprehensiveBacktestRunner` directamente.

---

## CONTEXTO

### Problema Identificado

El archivo `scripts/archived/comprehensive_oneYear_test.py` tiene 41 violaciones de reglas:

- ❌ Usa `ComprehensiveBacktestRunner` directamente (viola DIP-001)
- ❌ NO usa ComplianceEngine
- ❌ NO valida R1, R2, R4
- ❌ NO calcula Spain Tax
- ❌ NO loguea con correlation ID (R15)

Ver: `.ralph/outputs/COMPREHENSIVE_ONYEART_TEST_AUDIT.md`

### Solución

Crear nuevo test que:
- ✅ Use **ComplianceEngine** (NO runner directo)
- ✅ Pruebe los **10 tipos de backtests**
- ✅ Valide R1, R2, R4 (via ComplianceEngine)
- ✅ Calcule Spain Tax (IRPF 19/21/23%)
- ✅ Loguee con correlation ID (R15)
- ✅ Siga SOLID principles

---

## LOS 10 TIPOS DE BACKTEST

```python
class BacktestType(Enum):
    BASELINE = "baseline"              # 1. Referencia sin ML
    LEARNING_ENGINES = "learning_engines"  # 2. supervised, deep, RL, transformer
    WALK_FORWARD = "walk_forward"      # 3. Optimización temporal
    MONTE_CARLO = "monte_carlo"        # 4. Stress test (100 sims)
    GRID_SEARCH = "grid_search"        # 5. Exploración de parámetros
    ABLATION = "ablation"              # 6. Impacto de módulos
    OUT_OF_SAMPLE = "out_of_sample"    # 7. Validación forward (70/15/15)
    MULTI_STRATEGY = "multi_strategy"  # 8. Todas las estrategias
    REGIME_TEST = "regime_test"        # 9. Performance por régimen (HMM)
    HYPERPARAMETER = "hyperparameter"   # 10. Optimización Optuna (50 trials)
```

---

## REQUISITOS TÉCNICOS

### 1. Usar ComplianceEngine

```python
# ✅ CORRECTO
from app.core.compliance_engine import ComplianceEngine

engine = ComplianceEngine.from_config(config)
result = engine.run_backtest(
    backtest_type=bt_type.value,
    config=config,
    profile=profile,
    correlation_id=str(uuid.uuid4()),
)
```

### 2. Spain Tax Calculator

```python
class SpainTaxCalculator:
    """IRPF Progresivo (sin distinción LT/ST)"""
    TAX_BRACKETS = [
        (Decimal("0"), Decimal("6000"), Decimal("0.19")),     # 19%
        (Decimal("6000"), Decimal("50000"), Decimal("0.21")),   # 21%
        (Decimal("50000"), Decimal("999999999"), Decimal("0.23")), # 23%
    ]
```

### 3. SOLID Principles

- **SRP:** `SpainTaxCalculator` (1 responsabilidad), `ComplianceBacktestOrchestrator` (1 responsabilidad)
- **DIP:** Usar Protocol para dependencias
- **ISP:** Interfaces con < 5 métodos

---

## FLUJO DE EJECUCIÓN

Esta tarea usa el flujo estándar de Ralph con 4 hats:

### HAT 1: Requirement Generator
- Lee `.ralph/outputs/COMPREHENSIVE_ONYEART_TEST_AUDIT.md`
- Extrae los 10 tipos de backtest
- Verifica que ComplianceEngine existe
- Genera lista de requisitos

### HAT 2: Implementer
- Crea `tests/backtesting/test_comprehensive_backtesting_via_compliance.py`
- Implementa los 10 tipos de backtest
- Implementa SpainTaxCalculator
- Implementa correlation ID logging
- Valida con `scripts/utils.py validate`

### HAT 3: Validator
- Verifica que usa ComplianceEngine
- Verifica que NO usa ComprehensiveBacktestRunner
- Verifica los 10 tipos de backtest
- Verifica Spain Tax
- Verifica correlation ID
- Verifica SOLID principles

### HAT 4: Final Reviewer
- Genera reporte final
- Genera `.ralph/outputs/COMPREHENSIVE_BACKTEST_TEST_REPORT.md`

---

## VALIDACIONES REQUERIDAS

```bash
# 1. ComplianceEngine import
grep -n "from.*compliance_engine import ComplianceEngine" \
  tests/backtesting/test_comprehensive_backtesting_via_compliance.py

# 2. NO ComprehensiveBacktestRunner
! grep -q "ComprehensiveBacktestRunner" \
  tests/backtesting/test_comprehensive_backtesting_via_compliance.py

# 3. 10 tipos de backtest
types=$(grep -o "BASELINE\|LEARNING_ENGINES\|WALK_FORWARD\|MONTE_CARLO\|GRID_SEARCH\|ABLATION\|OUT_OF_SAMPLE\|MULTI_STRATEGY\|REGIME_TEST\|HYPERPARAMETER" \
  tests/backtesting/test_comprehensive_backtesting_via_compliance.py | sort -u | wc -l)
[ "$types" -eq 10 ]

# 4. Spain Tax
grep -n "0.19\|0.21\|0.23\|IRPF\|SpainTaxCalculator" \
  tests/backtesting/test_comprehensive_backtesting_via_compliance.py

# 5. Correlation ID
grep -n "correlation_id\|uuid.uuid4()" \
  tests/backtesting/test_comprehensive_backtesting_via_compliance.py

# 6. SOLID (Protocol)
grep -n "Protocol" tests/backtesting/test_comprehensive_backtesting_via_compliance.py

# 7. Validación
python .ralph/scripts/utils.py validate \
  tests/backtesting/test_comprehensive_backtesting_via_compliance.py
```

---

## OUTPUT FINAL

**Completion Promise:** `COMPREHENSIVE_BACKTEST_TEST_COMPLETE`

**Test File:** `tests/backtesting/test_comprehensive_backtesting_via_compliance.py`

**Report:** `.ralph/outputs/COMPREHENSIVE_BACKTEST_TEST_REPORT.md`

---

## EJECUCIÓN

```bash
# Ejecutar la tarea Ralph
ralph run -P .ralph/ralph_tasks/prompts/21_backtesting_folder_audit.md

# O ejecutar el test directamente cuando esté creado
python tests/backtesting/test_comprehensive_backtesting_via_compliance.py
```

---

**Fin del Prompt**

**Versión:** 3.0
**Fecha:** 2026-02-09
**Estado:** ✅ Ready for implementation
