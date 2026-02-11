# Ralph Task 21: Backtesting Compliance Audit & Fix

## Overview

Esta tarea audita y corrige todos los tests de backtesting para cumplir con las reglas de trading definidas en `rules/trading/`.

## Contexto Crítico

### Arquitectura Correcta

```python
# ✅ CORRECTO - Usar BacktestEngine
from app.backtesting.engine import BacktestEngine

engine = BacktestEngine(config)
# BacktestEngine YA tiene ComplianceEngine integrado:
# - analyze_pre_trade() se llama antes de cada trade
# - analyze_post_trade() se llama después de cada trade
# - check_kill_switch() valida drawdown
# - track_daily_pnl() monitorea pérdidas

result = engine.run_backtest(market_data, signals)

# ❌ INCORRECTO - NO usar ComprehensiveBacktestRunner directamente
from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
runner = ComprehensiveBacktestRunner(config)  # ← Arquitectura deprecada
```

### Reglas de Trading a Cumplir

| ID | Regla | Fuente |
|----|-------|--------|
| CHAN-001 | Sharpe Ratio > 1.0 requerido | Ernest Chan |
| CHAN-002 | Max Drawdown < 25% | Ernest Chan |
| CHAN-003 | Mínimo 5 años de datos | Ernest Chan |
| TOM-001 | Event-driven backtesting | Tomasini & Jaekle |
| ARCH-001 | Usar BacktestEngine | Arquitectura actual |
| RET-001 | Walk-forward validation | Realistic Retail |
| RET-002 | Monte Carlo (1000 sims) | Realistic Retail |
| RET-003 | Transaction costs incluidos | Realistic Retail |

## Flujo de Trabajo

### Fase 1: AUDIT
```bash
python .ralph/scripts/audit_backtesting_rules.py --test-dir tests/backtesting --output .ralph/outputs/BACKTESTING_AUDIT.json
```

### Fase 2: CLEANUP
```bash
# Dry run primero
python .ralph/scripts/cleanup_obsolete_backtests.py --dry-run --audit-file .ralph/outputs/BACKTESTING_AUDIT.json

# Revisar .ralph/outputs/CLEANUP_PLAN.md

# Si estás seguro:
python .ralph/scripts/cleanup_obsolete_backtests.py --clean
```

### Fase 3: FIX
Para cada archivo con violaciones:
1. Leer el archivo
2. Identificar violaciones específicas
3. Aplicar correcciones
4. Validar con `python .ralph/scripts/utils.py validate <file>`
5. Re-auditar para verificar

### Fase 4: VALIDATE
```bash
python .ralph/scripts/audit_backtesting_rules.py --test-dir tests/backtesting --output .ralph/outputs/FINAL_AUDIT.json

# Verificar:
# - total_critical_violations == 0
# - average_compliance_score > 80%
```

## Completion Promise

**BACKTESTING_COMPLIANCE_COMPLETE** se emitirá cuando:
- ✅ Cero violaciones críticas
- ✅ Compliance score promedio > 80%
- ✅ Todos los tests usan BacktestEngine
- ✅ Validaciones de Sharpe y Drawdown implementadas
- ✅ Tests obsoletos eliminados/archivados

## Archivos Generados

- `.ralph/outputs/BACKTESTING_AUDIT.json` - Resultados de auditoría
- `.ralph/outputs/BACKTESTING_AUDIT.md` - Reporte legible
- `.ralph/outputs/CLEANUP_PLAN.json` - Plan de limpieza
- `.ralph/outputs/CLEANUP_PLAN.md` - Plan legible
- `.ralph/outputs/FINAL_AUDIT.json` - Auditoría final
- `.ralph/outputs/BACKTESTING_COMPLIANCE_REPORT.md` - Reporte final
- `.ralph/outputs/TASK21_EXECUTIVE_SUMMARY.md` - Resumen ejecutivo
