# Integration Tests

## Estructura

Los tests de integración están organizados en las siguientes categorías:

### 📊 Data (`data/`)
- `test_data_loader.py` - Carga de datos históricos desde CSV

### 🔄 Backtesting (`backtesting/`)
- `test_advanced_backtesting.py` - Tests avanzados de backtesting

### 🎯 Strategies (`strategies/`)
- `test_strategy_engines.py` - Tests de Strategy Engines (Módulo 3)
- `test_strategy_comparison_backtest.py` - Comparación de estrategias
- `test_strategy_stock_allocator_integration.py` - Allocation de stocks
- `test_momentum_strategy.py` - Tests específicos de momentum
- `test_signal_generation_integration.py` - Generación de señales
- `test_strategies_risk_check.py` - Risk checks

### 🧠 Learning (`learning/`)
- `test_drift_detection.py` - Detección de drift y overfitting (Módulo 4.2)
- `test_feature_importance.py` - Feature importance system (Módulo 4.3)
- `test_transfer_learning.py` - Transfer learning (Módulo 4.4)

### ⚙️ Engines (`engines/`)
- `test_data_context_integration.py` - Integración de DataEngine y ContextEngine con Strategy Engines (Módulos 1 y 2)
- `test_multi_strategy_integration.py` - Tests de multi-strategy con engines integrados
- `test_portfolio_engine_integration.py` - Tests de Portfolio Engine (Fase 3, Módulo 5)
- `test_risk_engine_integration.py` - Tests de Risk Engine (Fase 3, Módulo 6)
- `test_portfolio_risk_strategy_integration.py` - Integración de Portfolio Engine y Risk Engine con Strategy Engines (Fase 3)

### ✅ Validation (`validation/`)
- `test_validation_block1_data_integrity.py` - Validación de integridad de datos

## Tests de Integración Fase 3: Portfolio y Risk

### Portfolio Engine Integration (`test_portfolio_engine_integration.py`)

Tests para verificar que Portfolio Engine (Fase 3, Módulo 5) funciona correctamente:

- `test_portfolio_engine_initialization` - Inicialización de PortfolioEngine
- `test_set_optimizer` - Configuración de optimizadores
- `test_set_rebalancer` - Configuración de rebalanceadores
- `test_set_meta_learner` - Configuración de meta-learners
- `test_get_allocation_by_asset_class` - Asignación por clase de activo
- `test_markowitz_optimizer` - Optimizador Markowitz
- `test_risk_parity_optimizer` - Optimizador Risk Parity
- `test_black_litterman_optimizer` - Optimizador Black-Litterman
- `test_kelly_criterion_optimizer` - Optimizador Kelly Criterion
- `test_threshold_rebalancer` - Rebalanceador por umbral
- `test_time_based_rebalancer` - Rebalanceador por tiempo
- `test_volatility_targeting_rebalancer` - Rebalanceador por volatilidad
- `test_transaction_cost_aware_rebalancer` - Rebalanceador con costos
- `test_historical_performance_learner` - Meta-learner de performance histórica
- `test_ensemble_meta_learner` - Meta-learner ensemble

### Risk Engine Integration (`test_risk_engine_integration.py`)

Tests para verificar que Risk Engine (Fase 3, Módulo 6) funciona correctamente:

- `test_risk_engine_initialization` - Inicialización de RiskEngine
- `test_assess_risk` - Evaluación básica de riesgo
- `test_set_components` - Configuración de componentes
- `test_historical_var_calculator` - Calculador VaR histórico
- `test_parametric_var_calculator` - Calculador VaR paramétrico
- `test_monte_carlo_var_calculator` - Calculador VaR Monte Carlo
- `test_stress_tester_initialization` - Inicialización de StressTester
- `test_run_historical_stress_tests` - Stress tests históricos
- `test_drawdown_controller_initialization` - Inicialización de DrawdownController
- `test_assess_drawdown` - Evaluación de drawdown
- `test_exposure_manager_initialization` - Inicialización de ExposureManager
- `test_analyze_exposure` - Análisis de exposición
- `test_correlation_analyzer_initialization` - Inicialización de CorrelationAnalyzer
- `test_analyze_correlations` - Análisis de correlaciones
- `test_risk_attributor_initialization` - Inicialización de RiskAttributor
- `test_attribute_risk` - Atribución de riesgo
- `test_alert_system_initialization` - Inicialización de AlertSystem
- `test_check_thresholds` - Verificación de umbrales

### Portfolio & Risk Integration with Strategy Engines (`test_portfolio_risk_strategy_integration.py`)

Tests para verificar que Portfolio Engine y Risk Engine se integran correctamente con Strategy Engines:

- `test_portfolio_engine_with_strategy_engine` - Strategy Engine puede usar Portfolio Engine
- `test_portfolio_optimization_with_strategy_signals` - Optimización usando señales de estrategias
- `test_risk_engine_with_strategy_engine` - Strategy Engine puede usar Risk Engine
- `test_risk_assessment_with_strategy_portfolio` - Evaluación de riesgo usando portfolio de estrategia
- `test_portfolio_risk_strategy_integration` - Integración completa Portfolio + Risk + Strategy
- `test_multi_strategy_with_portfolio_risk_engines` - Multi-strategy con Portfolio y Risk Engines

## Tests de Integración Módulos 1 y 2

### DataEngine Integration (`test_data_context_integration.py`)

Tests para verificar que DataEngine (Módulo 1) se integra correctamente con Strategy Engines:

- `test_data_engine_initialization_in_strategy` - Inicialización de DataEngine en Strategy Engine
- `test_set_data_engine_externally` - Configuración externa de DataEngine
- `test_context_engine_initialization_in_strategy` - Inicialización de ContextEngine
- `test_set_context_engine_externally` - Configuración externa de ContextEngine
- `test_get_context_analysis` - Obtención de análisis de contexto
- `test_get_volatility_regime` - Obtención de régimen de volatilidad
- `test_strategy_with_both_engines` - Strategy Engine con ambos engines
- `test_strategy_metrics_include_engines` - Métricas incluyen llamadas a engines
- `test_strategy_status_includes_engines` - Status incluye información de engines
- `test_multiple_engines_share_context_engine` - Múltiples engines comparten ContextEngine
- `test_multiple_engines_share_data_engine` - Múltiples engines comparten DataEngine

### Multi-Strategy Integration (`test_multi_strategy_integration.py`)

Tests para verificar que los engines funcionan en backtests multi-strategy:

- `test_multi_strategy_backtest_with_context` - Backtest multi-strategy con ContextEngine
- `test_modular_momentum_with_context_engine` - ModularMomentumStrategyEngine con ContextEngine
- `test_engines_use_context_for_signal_adjustment` - Los engines usan contexto para ajustar señales

## Ejecutar Tests

### Todos los tests de integración
```bash
pytest tests/integration/ -v
```

### Tests específicos de engines
```bash
pytest tests/integration/engines/ -v
```

### Tests de estrategias
```bash
pytest tests/integration/strategies/ -v
```

### Tests de learning
```bash
pytest tests/integration/learning/ -v
```

## Verificación de Integración

Los tests verifican que:

1. ✅ **DataEngine** puede ser inicializado y usado por Strategy Engines
2. ✅ **ContextEngine** puede ser inicializado y usado por Strategy Engines
3. ✅ **PortfolioEngine** puede ser inicializado y usado por Strategy Engines
4. ✅ **RiskEngine** puede ser inicializado y usado por Strategy Engines
5. ✅ Los Strategy Engines pueden compartir instancias de todos los engines
6. ✅ Las métricas incluyen llamadas a los engines
7. ✅ El status incluye información de todos los engines
8. ✅ ModularMomentumStrategyEngine usa ContextEngine cuando está disponible
9. ✅ Los backtests multi-strategy funcionan con los engines integrados
10. ✅ Portfolio Engine puede optimizar asignación usando señales de estrategias
11. ✅ Risk Engine puede evaluar riesgo de portfolios generados por estrategias

## Notas

- Los tests son opcionales si DataEngine, ContextEngine, PortfolioEngine o RiskEngine no están disponibles (usando `pytest.skip`)
- Los engines pueden funcionar sin otros engines (fallback a métodos tradicionales)
- Portfolio Engine y Risk Engine son completamente opcionales y pueden ser configurados externamente
- Strategy Engines pueden usar múltiples engines simultáneamente
- La integración es retrocompatible: si los engines no están disponibles, los Strategy Engines funcionan normalmente
