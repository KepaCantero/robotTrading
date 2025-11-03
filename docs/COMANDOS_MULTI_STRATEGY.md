# Comandos para Ejecutar Multi-Strategy Tests

## Comando Principal

Para ejecutar **solo** los multi-strategy backtests:

```bash
python scripts/run_comprehensive_backtest.py multi_strategy
```

## Verificación de Configuración

Antes de ejecutar, asegúrate de que `multi_strategy` está habilitado en `config/backtesting/comprehensive_backtest.yaml`:

```yaml
multi_strategy:
  enabled: true
  strategies: ["momentum", "mean_reversion", "pairs_trading"]
  enable_dynamic_reallocation: true
  reallocation_frequency_days: 30
```

## Otros Comandos Útiles

### Ejecutar múltiples tipos de backtests

```bash
# Multi-strategy + baseline
python scripts/run_comprehensive_backtest.py multi_strategy baseline

# Multi-strategy + learning engines
python scripts/run_comprehensive_backtest.py multi_strategy learning_engines
```

### Ejecutar todos los backtests habilitados

```bash
python scripts/run_comprehensive_backtest.py
```

### Backtests disponibles

Los nombres válidos son:

- `baseline` - Línea base con todos los módulos activos
- `learning_engines` - Prueba cada learning engine individualmente
- `walk_forward` - Optimización por ventana temporal
- `monte_carlo` - Stress test con simulaciones aleatorias
- `transformer_optimization` - Optimización iterativa con Transformer
- `ablation` - Impacto individual de cada módulo
- `grid_search` - Búsqueda de parámetros óptimos
- `out_of_sample` - Validación forward
- **`multi_strategy`** - Prueba múltiples estrategias simultáneamente ⭐
- `regime_test` - Desempeño por régimen de mercado

## Resultados

Los resultados se guardan en:

- `reports/comprehensive_backtest/comprehensive_backtest_results_<timestamp>.csv`
- `reports/comprehensive_backtest/comprehensive_backtest_results_<timestamp>.json`
- `reports/comprehensive_backtest/summary_<timestamp>.txt`

Si están instaladas las librerías profesionales:

- `reports/comprehensive_backtest/quantstats_reports/` - Reportes HTML
- `reports/comprehensive_backtest/pyfolio_reports/` - Análisis de portfolio
