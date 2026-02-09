# Backtesting Tests

Tests para el módulo de backtesting.

## Estructura

```
tests/backtesting/
├── batch/              # Tests de batch backtesting (profile-based)
├── services/           # Tests de servicios internos del engine
├── unit/               # Tests unitarios de componentes individuales
└── integration/        # Tests de integración de backtesting
```

## Categorías

### `batch/`
Tests para ejecución de backtests en batch (múltiples profiles):
- `test_profile_batch_backtester.py` - Batch backtester original
- `test_profile_batch_backtester_refactored.py` - Versión refactorizada
- `test_baseline_optimization_reporter.py` - Reporter de optimización

### `services/`
Tests de los servicios internos del BacktestEngine:
- `test_equity_tracker.py` - Seguimiento de equity curve
- `test_exit_monitor.py` - Monitoreo de condiciones de salida
- `test_performance_calculator.py` - Cálculo de métricas
- `test_pnl_calculator.py` - Cálculo de P&L
- `test_position_manager.py` - Gestión de posiciones
- `test_signal_processor.py` - Procesamiento de señales
- `test_trade_executor.py` - Ejecución de trades

### `unit/`
Tests unitarios de componentes individuales del backtesting.

### `integration/`
Tests de integración que verifican el funcionamiento completo del pipeline.

## Arquitectura

```
InputProfile → InvestmentProfile → ProfileBatchBacktester
                                               ↓
                                         BacktestEngine
                                               ↓
                                         ComplianceEngine
                                               ↓
                                         BacktestResult
```

## Trading Rules Compliance

Todos los tests de backtesting deben cumplir:
- ✅ CHAN-002: Max Drawdown < 25% (ComplianceEngine)
- ✅ RET-003: Transaction Costs incluidos (ComplianceEngine)
- ✅ ARCH-001: Usar BacktestEngine (no ComprehensiveBacktestRunner)
- ✅ TOM-001: Event-driven backtesting
