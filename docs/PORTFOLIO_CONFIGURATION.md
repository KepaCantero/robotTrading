# 📊 Portfolio Configuration System

Sistema de configuración automática para backtesting multi-estrategia con asignación por sectores y tipos de mercado.

## 📋 Características

- **Asignación Automática de Capital**: Porcentajes configurables por estrategia
- **Filtrado por Sectores**: Cada estrategia opera solo en sectores específicos
- **Filtrado por Tipo de Mercado**: Trending, sideways, correlated
- **Rebalanceo Configurable**: Mensual, trimestral o anual
- **Reporting Consolidado**: Métricas por estrategia y portfolio global

## 🗂️ Archivos de Configuración

### `config/portfolio.yaml`

Configuración principal del portfolio con:

```yaml
# Definición de sectores
sectors:
  technology:
    symbols: ["AAPL", "MSFT", "GOOGL"]
    
# Tipos de mercado
market_types:
  trending:
    description: "Mercado tendencial"
    
# Asignación por estrategia
strategy_allocations:
  momentum:
    capital_allocation:
      target_weight: 0.50  # 50%
    sectors:
      - technology
      - growth
    market_types:
      - trending
    rebalancing:
      frequency: monthly
```

## 🔧 Uso

### En el Dashboard

El sistema se integra automáticamente con el backtest multi-estrategia:

```python
from app.services.portfolio_config_manager import get_portfolio_config_manager

# Cargar configuración
portfolio_config = get_portfolio_config_manager()

# Obtener allocation manager configurado
allocation_manager = portfolio_config.get_allocation_manager()

# Filtrar símbolos por estrategia
symbols = portfolio_config.get_strategy_symbols("momentum")
# Returns: ["AAPL", "MSFT", "GOOGL", ...] based on sectors
```

### En MultiStrategyBacktester

El filtrado por sectores se aplica automáticamente:

```python
from app.backtesting.multi_strategy_engine import MultiStrategyBacktester
from app.services.portfolio_config_manager import get_portfolio_config_manager

# El PortfolioConfigManager se integra automáticamente
portfolio_config = get_portfolio_config_manager()
allocation_manager = portfolio_config.get_allocation_manager()

backtester = MultiStrategyBacktester(
    allocation_manager=allocation_manager,
    strategies=strategies,
    config_params={},
    portfolio_config_manager=portfolio_config,  # Opcional, se carga automáticamente
)

# El backtest filtra automáticamente por sectores
results = backtester.run_multi_strategy_backtest(quotes, start_date, end_date)
```

## 📊 Configuración Actual

### Momentum Strategy
- **Capital**: 50% (configurable 30-70%)
- **Sectores**: Technology, Growth, Energy
- **Tipo de Mercado**: Trending
- **Rebalanceo**: Mensual

### Mean Reversion Strategy
- **Capital**: 25% (configurable 10-40%)
- **Sectores**: Utilities, Consumer Staples, REITs
- **Tipo de Mercado**: Sideways
- **Rebalanceo**: Trimestral

### Pairs Trading Strategy
- **Capital**: 25% (configurable 10-40%)
- **Sectores**: Banks, Energy, Technology
- **Tipo de Mercado**: Correlated
- **Rebalanceo**: Mensual

## 🔄 Rebalanceo Automático

El sistema soporta rebalanceo basado en:

1. **Frecuencia**: monthly, quarterly, yearly
2. **Threshold**: Drift mínimo para trigger (default: 5%)
3. **Performance-based**: Optimización futura por métricas históricas

```yaml
rebalancing:
  frequency: monthly
  threshold: 0.05
  enabled: true
```

## 📈 Reporting

El reporting consolidado incluye:

```python
results = {
    "per_strategy": {
        "momentum": {
            "initial_capital": 50000.0,
            "final_capital": 51429.0,
            "total_trades": 56,
            "win_rate": 0.518,
            "total_return": 2.86,
            "sharpe_ratio": -0.104,
            "max_drawdown": -8.46,
        },
        # ... otras estrategias
    },
    "combined": {
        "total_initial_capital": 100000.0,
        "total_final_capital": 93601.38,
        "total_return": -6.40,
        "total_trades": 437,
        "weighted_sharpe": -0.057,
        "weighted_max_dd": -14.09,
    },
    "allocation": {
        "momentum": {"capital": 50000.0, "weight": 0.50},
        # ...
    },
}
```

## 🎯 Extensión para Nuevos Sectores

Para añadir nuevos sectores:

1. Editar `config/portfolio.yaml`:

```yaml
sectors:
  new_sector:
    symbols: ["SYMB1", "SYMB2"]
    description: "Descripción del sector"

strategy_allocations:
  strategy_name:
    sectors:
      - new_sector
```

2. El sistema detecta automáticamente y filtra símbolos.

## 🚀 Integración con Optimización

El sistema de optimización (`MultiStrategyOptimizer`) puede usar este sistema para:

1. Optimizar pesos de asignación por sector
2. Optimizar parámetros considerando sectores
3. Optimizar rebalanceo frequency basado en performance

```python
from app.optimization.multi_strategy_optimizer import MultiStrategyOptimizer

optimizer = MultiStrategyOptimizer(
    total_capital=Decimal("100000"),
    symbol="AAPL",  # Puede optimizar por sector
    # ...
)
```

## 📝 Notas Técnicas

- **Filtrado Lazy**: Los quotes se filtran antes de generar señales
- **Sectores Opcionales**: Si no se configuran sectores, se usa todo el universo
- **Symbol Override**: Puedes especificar `symbols` explícitos en vez de sectores
- **Market Type**: Actualmente es metadata; futura implementación detectará automáticamente

---

*Última actualización: 2025-10-28*

