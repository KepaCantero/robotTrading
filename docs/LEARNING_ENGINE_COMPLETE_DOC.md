# ✅ LearningEngine - Sistema Completo de Aprendizaje

## Resumen

Se ha creado un **sistema completo de aprendizaje modular y híbrido** que incluye:

1. ✅ **SupervisedLearningEngine** - RandomForest, XGBoost, GradientBoosting, Neural Networks
2. ✅ **DeepLearningEngine** - LSTM, GRU, Transformers (estructura lista)
3. ✅ **ReinforcementLearningEngine** - PPO, A2C, DDPG con entorno de trading
4. ✅ **AutomatedBacktestRunner** - Sistema completo de backtesting automatizado

## Estructura de Archivos

```
app/strategies/momentum_modular/learning/
├── __init__.py                          ✅
├── base_learning_engine.py              ✅ Clase base abstracta
├── supervised_learning_engine.py        ✅ Supervised Learning
├── deep_learning_engine.py              ✅ Deep Learning (LSTM/GRU)
└── reinforcement_learning_engine.py     ✅ Reinforcement Learning

app/strategies/momentum_modular/
└── automated_backtest.py                ✅ Sistema de backtest automatizado

scripts/
└── run_automated_momentum_backtest.py   ✅ Script ejecutable
```

## Características Implementadas

### 1. SupervisedLearningEngine ✅

**Algoritmos soportados:**

- RandomForest
- XGBoost
- GradientBoosting
- Neural Networks (PyTorch)

**Funcionalidades:**

- Predice probabilidad de éxito de trades
- Optimiza thresholds de filtros
- Feature importance analysis
- Evaluación con métricas estándar (accuracy, precision, recall, F1, ROC-AUC)

### 2. DeepLearningEngine ✅

**Arquitecturas soportadas:**

- LSTM (Long Short-Term Memory)
- GRU (Gated Recurrent Unit)
- Transformers (estructura lista, implementación pendiente)

**Funcionalidades:**

- Predice movimientos de mercado usando series de tiempo
- Ajusta parámetros dinámicos de filtros
- Normalización automática de datos
- Soporte para PyTorch y TensorFlow

### 3. ReinforcementLearningEngine ✅

**Algoritmos soportados:**

- PPO (Proximal Policy Optimization)
- A2C (Advantage Actor-Critic)
- DDPG (Deep Deterministic Policy Gradient)

**Funcionalidades:**

- Entorno de trading personalizado (`TradingEnv`)
- Aprende políticas óptimas (BUY/SELL/HOLD)
- Ajusta stop-loss y take-profit dinámicamente
- Controla exposición al riesgo
- Recompensas basadas en P&L, Sharpe, drawdown

### 4. AutomatedBacktestRunner ✅

**Funcionalidades:**

- Selección automática de mejor stock (`PortfolioAnalyzer`)
- Backtest baseline con todos los módulos
- Ablation study (desactivar módulos uno por uno)
- Backtests con cada learning engine
- Generación de reporte comparativo automático

## Uso Rápido

### Ejecutar Backtest Automatizado

```bash
python scripts/run_automated_momentum_backtest.py
```

### Usar Learning Engines Programáticamente

```python
from app.strategies.momentum_modular.learning import (
    SupervisedLearningEngine,
    DeepLearningEngine,
    ReinforcementLearningEngine
)

# Supervised Learning
supervised_config = {
    "enabled": True,
    "algorithm": "random_forest",
    "model_parameters": {"n_estimators": 100}
}
supervised = SupervisedLearningEngine(supervised_config)

# Entrenar
training_data = {
    'features': X_train,  # DataFrame o array
    'labels': y_train     # 1 si exitoso, 0 si fallido
}
metrics = supervised.train(training_data)

# Predecir
prediction = supervised.predict({
    'indicators': {'rsi': 55, 'momentum_roc': 0.02},
    'filter_results': {...},
    'market_context': {...}
})

# Deep Learning
deep_config = {
    "enabled": True,
    "architecture": "lstm",
    "sequence_length": 60,
    "hidden_size": 64
}
deep = DeepLearningEngine(deep_config)

# Reinforcement Learning
rl_config = {
    "enabled": True,
    "algorithm": "ppo",
    "training_steps": 100000
}
rl = ReinforcementLearningEngine(rl_config)
```

## Requisitos de Librerías

```bash
# Core
pip install pandas numpy scikit-learn

# Supervised Learning
pip install xgboost

# Deep Learning
pip install torch  # o tensorflow

# Reinforcement Learning
pip install stable-baselines3 gym
```

## Próximos Pasos

1. ✅ **Completado**: Estructura modular de learning engines
2. ✅ **Completado**: Sistema de backtest automatizado
3. ⏳ **Pendiente**: Implementación completa de `ModularMomentumStrategy` que integre learning engines
4. ⏳ **Pendiente**: Testing y optimización de hyperparámetros
5. ⏳ **Pendiente**: Implementación de Transformers en DeepLearningEngine

## Documentación Completa

Ver:

- `docs/AUTOMATED_BACKTEST_GUIDE.md` - Guía de uso del backtest automatizado
- `app/strategies/momentum_modular/learning/` - Código fuente con docstrings detallados
