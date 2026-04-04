# Ralph Tasks

**Actualizado:** 2026-04-02

## Tareas Activas

| ID | Tarea | Descripcion | Estado |
|----|-------|-------------|--------|
| 00 | Master Orchestrator | Orquestador principal AAA v14.0 | Lista para ejecutar |
| 23 | Profile Backtest Metrics Fix | Fix Sharpe ratio, metricas de backtesting | Pendiente |
| 31 | Production Audit | Audit de archivos contra .requirements/ + QA gates | Pendiente |
| 32 | Architecture Requirements Audit | Audit de arquitectura y estructura del sistema | Pendiente |
| 35 | Fix Pytest | Corregir 175 collection errors en tests/unit/ | Pendiente |
| 36 | Progressive Backtesting | Ejecutar tests/backtesting/ progresivo: 1->ALL stocks, min->5yr, 5 perfiles (foco dividendos). Se puede tocar app/. QA gates obligatorios. | Pendiente |
| 37 | Dashboard Backtesting | Integrar backtesting en dashboard: ejecutar, guardar historico, ver config, es profitable? | Pendiente |
| 99 | Final Cleanup | Limpieza final post-orquestador | Pendiente |

## Ejecutar

```bash
# Orquestador principal
ralph run -P .ralph/ralph_tasks/prompts/00_master_orchestrator.md

# Fix pytest (independiente)
ralph run -P .ralph/ralph_tasks/prompts/35_fix_pytest.md

# Fix metricas backtesting (independiente)
ralph run -P .ralph/ralph_tasks/prompts/23_profile_backtest_metrics_fix.md

# Progressive backtesting (independiente)
ralph run -P .ralph/ralph_tasks/prompts/36_progressive_backtesting.md
```

## Tareas Eliminadas (2026-04-02)

Las siguientes tareas se eliminaron por estar ya implementadas en el codigo
o por ser redundantes con el orquestador:

- 01-16, 19: Ya implementadas en app/
- 22, 24-25, 27-30: Redundantes con el orquestador
- 33-34: Auditorias redundantes con tasks 31/32
- 26: Config centralizada ya existe (centralized_config.py, 859 lineas)
