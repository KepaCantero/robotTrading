# Strategy Engines

Motores de estrategias refactorizados que extienden `BaseStrategy` con capacidades adicionales para integración con Learning Engines, composición de estrategias, y feature extraction estandarizado.

## Arquitectura

### BaseStrategyEngine

Clase base abstracta que proporciona:

- **Integración con Learning Engines**: Métodos para obtener predicciones y aplicar ajustes
- **Feature extraction estandarizado**: Método abstracto `extract_features()` que cada engine implementa
- **Callbacks para aprendizaje continuo**: Sistema de callbacks para señales, trades y market data
- **Soporte para ensembles**: Peso en ensemble, flags de participación
- **Métricas y tracking**: Métricas del engine, estado completo

### Engines Disponibles

#### 1. MomentumStrategyEngine

Engine de estrategia de momentum basada en RSI, EMA y volumen.

**Features extraídos:**
- RSI, EMA, Momentum/ROC
- Volume ratio
- ATR y relative ATR
- Price position relative to EMA

**Tipo**: `"momentum"`

#### 2. MeanReversionStrategyEngine

Engine de estrategia de reversión a la media basada en Z-score.

**Features extraídos:**
- Z-score (adaptativo)
- Mean y std del precio
- Volatilidad (ATR relativo)
- Price range metrics
- Price position in range

**Tipo**: `"mean_reversion"`

#### 3. PairsTradingStrategyEngine

Engine de estrategia de pairs trading basada en cointegración.

**Features extraídos:**
- Spread y spread Z-score
- Correlación entre activos del par
- Hedge ratio (OLS)
- Cointegración score
- Spread mean/std

**Tipo**: `"pairs_trading"`

#### 4. ModularMomentumStrategyEngine

Engine de momentum modular con filtros modulares y Learning Engines integrados.

**Features extraídos:**
- Todos los indicadores técnicos (RSI, EMA, Momentum, Volume, ATR)
- Resultados de todos los filtros modulares
- Contexto de mercado (MarketAnalyzer)
- Metadata completa (trades recientes, win rate)

**Tipo**: `"modular_momentum"`

## Uso Básico

```python
from app.engines.strategy_engines import MomentumStrategyEngine

# Crear engine con configuración
config = {
    "name": "momentum_engine",
    "rsi_threshold": 40,
    "momentum_threshold": 0.02,
    "volume_threshold": 1.5,
    "rsi_period": 14,
    "ema_period": 20,
}

engine = MomentumStrategyEngine(config)

# Generar señales (el wrapper aplica learning automáticamente)
signals = engine.generate_signals(market_data)

# Obtener features para learning
features = engine.extract_features(market_data)

# Obtener estado del engine
status = engine.get_status()
```

## Integración con Learning Engines

```python
from app.engines.strategy_engines import MomentumStrategyEngine
from app.strategies.momentum_modular.learning.supervised_learning_engine import SupervisedLearningEngine

# Crear engine
engine = MomentumStrategyEngine(config)

# Configurar Learning Engine
learning_engine = SupervisedLearningEngine(learning_config)
engine.set_learning_engine(learning_engine)

# Ahora generate_signals() aplicará ajustes de learning automáticamente
signals = engine.generate_signals(market_data)
```

## Callbacks para Aprendizaje Continuo

```python
def on_signal_generated(signal, market_data):
    print(f"Señal generada: {signal.symbol} - {signal.signal_type}")

def on_trade_executed(signal, execution_result):
    print(f"Trade ejecutado: {signal.symbol} - PnL: {execution_result.get('pnl', 0)}")

# Registrar callbacks
engine.register_signal_callback(on_signal_generated)
engine.register_trade_callback(on_trade_executed)

# Los callbacks se ejecutarán automáticamente cuando se generen señales/trades
```

## Ensembles (Composición de Estrategias)

```python
from app.engines.strategy_engines import MomentumStrategyEngine, MeanReversionStrategyEngine

# Crear múltiples engines
momentum_engine = MomentumStrategyEngine(momentum_config)
mean_reversion_engine = MeanReversionStrategyEngine(mean_reversion_config)

# Configurar pesos en ensemble
momentum_engine.set_ensemble_weight(Decimal("0.6"))  # 60% peso
mean_reversion_engine.set_ensemble_weight(Decimal("0.4"))  # 40% peso

# Los engines pueden combinarse usando StrategyCompositor (Tarea 3.3)
```

## Métricas

```python
# Obtener métricas del engine
metrics = engine.get_metrics()
# {
#     'signals_generated': 150,
#     'trades_executed': 45,
#     'learning_adjustments_applied': 120,
#     'last_update': datetime(...)
# }

# Resetear métricas
engine.reset_metrics()

# Obtener estado completo
status = engine.get_status()
```

## Migración desde Estrategias Antiguas

Las estrategias antiguas (`MomentumStrategy`, `MeanReversionStrategy`, etc.) siguen funcionando. Los nuevos engines son una versión mejorada que:

1. ✅ Mantienen compatibilidad con la lógica original
2. ✅ Añaden capacidades de Learning Engine integration
3. ✅ Proporcionan feature extraction estandarizado
4. ✅ Soportan callbacks y composición

**Plan de migración:**
1. Las estrategias antiguas siguen en `app/strategies/`
2. Los nuevos engines están en `app/engines/strategy_engines/`
3. Migración gradual: se pueden usar ambos sistemas en paralelo
4. Eventualmente, las estrategias antiguas pueden ser wrappers de los engines

## Próximos Pasos (Tarea 3.2)

- [ ] `BreakoutStrategyEngine` (nuevo)
- [ ] `TrendFollowingStrategyEngine` (nuevo)
- [ ] `ArbitrageStrategyEngine` (nuevo)

## Composición de Estrategias (Tarea 3.3)

- [ ] `StrategyCompositor` para ensembles
- [ ] Strategy selector basado en régimen de mercado
- [ ] Meta-strategy que combina múltiples engines

