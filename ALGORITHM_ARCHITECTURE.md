# Algoritmo Completo de Trading Automatizado

## Índice
1. [Visión General](#visión-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Componentes del Algoritmo](#componentes-del-algoritmo)
4. [Flujo de Ejecución](#flujo-de-ejecución)
5. [Módulos de Aprendizaje](#módulos-de-aprendizaje)
6. [Gestión de Riesgo y Taxes](#gestión-de-riesgo-y-taxes)
7. [Integración de Reinforcement Learning](#integración-de-reinforcement-learning)

---

## Visión General

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ALGORITMO DE TRADING                                 │
│                                                                              │
│  INPUT PROFILE → STOCK SELECTION → CAPITAL ALLOCATION → TRADING → RISK/TAX  │
│       ↓                ↓                    ↓            ↓         ↓          │
│   [Módulo 1]      [Módulo 2]            [Módulo 3]    [Módulo 4]  [Módulo 5] │
│    + RL            + ML                 + Optim.      + Exec.    + Tax       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Arquitectura del Sistema

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                              INPUT PROFILE                                    │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐   │
│  │ Capital     │    │ Objetivo     │    │ Riesgo      │    │ Horizonte    │   │
│  │ €100k       │    │ Maximizar    │    │ Medio       │    │ 12 meses     │   │
│  └──────┬──────┘    └──────┬───────┘    └──────┬──────┘    └──────┬───────┘   │
└─────────┼──────────────────┼───────────────────┼───────────────────┼───────────┘
          │                  │                   │                   │
          ▼                  ▼                   ▼                   ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                         PROFILE GENERATOR                                     │
│  • Capital Tier: MEDIUM (€100k)                                               │
│  • Módulos Habilitados: momentum, mean_reversion, pairs, dividends          │
│  • Parámetros: max_leverage=1.5x, position_size=0.25%, stop_loss=3%          │
│  • Alpha Requerido: 30.83% anual (€2k/mes target)                            │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                        MARKET UNIVERSE SELECTION                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  1. Obtener Universo: S&P 500, NASDAQ 100, IBEX 35, Crypto             │ │
│  │  2. Filtrar por:                                                         │ │
│  │     • Liquidez mínima: $500K volumen promedio                           │ │
│  │     • Volatilidad máxima: 15%                                           │ │
│  │     • Precio mínimo: $5                                                 │ │
│  │  3. Descargar datos históricos (6 meses mínimo)                          │ │
│  │  4. Validar calidad de datos (NaNs, gaps, consistencia)                 │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                        STRATEGY STOCK ALLOCATOR                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  ANÁLISIS CUANTITATIVO DE ACCIONES                                      │ │
│  │                                                                         │ │
│  │  Para cada acción:                                                      │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │ │
│  │  │ Métricas de Regimen:                                               │ │ │
│  │  │ • Hurst Exponent (H)                                               │ │ │
│  │  │   - H > 0.55 → Momentum (tendencia)                                │ │ │
│  │  │   - H < 0.45 → Mean Reversion (reversión)                          │ │ │
│  │  │   - H ≈ 0.5 → Random Walk (neutro)                                │ │ │
│  │  │                                                                   │ │ │
│  │  │ • Half-Life (τ)                                                     │ │ │
│  │  │   - τ bajo (< 20 días) → reversión rápida                         │ │ │
│  │  │   - τ alto (> 120 días) → reversión lenta                          │ │ │
│  │  │                                                                   │ │ │
│  │  │ • Sortino Ratio                                                     │ │ │
│  │  │   - Sortino > 0.5 → aceptable para trading                        │ │ │
│  │  │                                                                   │ │ │
│  │  │ • GARCH Volatility                                                 │ │ │
│  │  │   - Predicción de volatilidad futura                              │ │ │
│  │  │                                                                   │ │ │
│  │  │ • Cointegration (para pares)                                        │ │ │
│  │  │   - ADF test p < 0.01 → cointegrados                              │ │ │
│  │  │   - Hedge ratio β                                                   │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                         │ │
│  │  CLASIFICACIÓN POR ESTRATEGIA:                                          │ │
│  │  ┌──────────────┬──────────────┬──────────────┐                        │ │
│  │  │   Momentum   │ Mean Rev.    │ Pairs Trading│                        │ │
│  │  ├──────────────┼──────────────┼──────────────┤                        │ │
│  │  │ H > 0.55     │ H < 0.45     │ Cointegrated  │                        │ │
│  │  │ Sortino alto │ τ bajo       │ τ bajo        │                        │ │
│  │  │ ROC positivo │ Z-score alto │ Correlación   │                        │ │
│  │  └──────────────┴──────────────┴──────────────┘                        │ │
│  │                                                                         │ │
│  │  ASIGNACIÓN DE CAPITAL (ERC - Equal Risk Contribution):                 │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │ │
│  │  │ Minimiza varianza de contribuciones de riesgo                     │ │ │
│  │  │                                                                    │ │ │
│  │  │ max w_i tal que:                                                  │ │ │
│  │  │   - w_i ≤ MAX_STRATEGY_EXPOSURE (50%)                             │ │ │
│  │  │   - Σ w_i = 1.0                                                   │ │ │
│  │  │   - Minimizar Var(RC_i)                                           │ │ │
│  │  │                                                                    │ │ │
│  │  │ Distribución típica:                                               │ │ │
│  │  │   • Momentum: 50% del capital                                     │ │ │
│  │  │   • Mean Reversion: 35% del capital                               │ │ │
│  │  │   • Pairs Trading: 15% del capital                                │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                      PORTFOLIO CONSTRUCTION                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  OPTIMIZACIÓN DEL PORTAFOLIO                                            │ │
│  │                                                                         │ │
│  │  1. Mean-Variance Optimization (Markowitz):                             │ │
│  │     max w'μ - λw'Σw                                                     │ │
│  │     s.t. Σw_i = 1, w_i ≥ 0                                             │ │
│  │                                                                         │ │
│  │  2. Risk Parity / ERC:                                                  │ │
│  │     w_i ∝ 1/σ_i                                                         │ │
│  │                                                                         │ │
│  │  3. Constraints:                                                        │ │
│  │     • MAX_POSITION_SIZE = 10% por acción                               │ │
│  │     • MAX_STRATEGY_EXPOSURE = 50% por estrategia                      │ │
│  │     • MAX_DRAWDOWN = 15%                                                │ │
│  │                                                                         │ │
│  │  4. Resultado: Cartera de N acciones con pesos óptimos                 │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                         TRADING EXECUTION                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  TRADING BRIDGE ORCHESTRATOR                                            │ │
│  │                                                                         │ │
│  │  1. Generación de Señales:                                              │ │
│  │     ┌─────────────────────────────────────────────────────────────┐    │ │
│  │     │ • Momentum: RSI, MACD, ROC, Slope, Spearman ρ              │    │ │
│  │     │ • Mean Reversion: Z-score, Half-life, Bollinger Bands       │    │ │
│  │     │ • Pairs: Spread Z-score, Cointegration β                     │    │ │
│  │     └─────────────────────────────────────────────────────────────┘    │ │
│  │                                                                         │ │
│  │  2. Risk Gates (Validación ANTES de ejecutar):                         │ │
│  │     ┌─────────────────────────────────────────────────────────────┐    │ │
│  │     │ ✓ Max Daily Loss: 5%                                         │    │ │
│  │     │ ✓ Max Drawdown: 15%                                          │    │ │
│  │     │ ✓ Max Position Size: 10%                                     │    │ │
│  │     │ ✓ Max Correlation: 0.7                                       │    │ │
│  │     │ ✓ Portfolio Beta: -0.5 a 1.5                                │    │ │
│  │     └─────────────────────────────────────────────────────────────┘    │ │
│  │                                                                         │ │
│  │  3. Order Management:                                                  │ │
│  │     ┌─────────────────────────────────────────────────────────────┐    │ │
│  │     │ • Market Orders (ejecución inmediata)                       │    │ │
│  │     │ • Limit Orders (precio específico)                          │    │ │
│  │     │ • Stop-Loss Orders (protección)                             │    │ │
│  │     │ • Take-Profit Orders (objetivo)                             │    │ │
│  │     └─────────────────────────────────────────────────────────────┘    │ │
│  │                                                                         │ │
│  │  4. Broker Integration:                                                │ │
│  │     • Paper Trading (simulación)                                       │ │
│  │     • Interactive Brokers (live)                                       │ │
│  │     • Alpaca (live)                                                    │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                    RISK & TAX MANAGEMENT                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  GESTIÓN DE RIESGO                                                       │ │
│  │                                                                         │ │
│  │  • Risk Gates (pre-trade)                                               │ │
│  │  • Real-time P&L tracking                                               │ │
│  │  • Drawdown monitoring                                                 │ │
│  │  • Position sizing dinámico                                             │ │
│  │  • Correlation clustering                                               │ │
│  │                                                                         │ │
│  │  GESTIÓN DE IMPUESTOS (TAXES)                                           │ │
│  │                                                                         │ │
│  │  • Capital Gain Tracker:                                                │ │
│  │    - FIFO / LIFO / Average Cost                                         │ │
│  │    - Short-term (< 1 año): 25-33%                                      │ │
│  │    - Long-term (≥ 1 año): 15-23%                                       │ │
│  │                                                                         │ │
│  │  • Tax Loss Harvesting:                                                 │ │
│  │    - Identificar pérdidas realizables                                  │ │
│  │    - Ejecutar harvesting manteniendo allocation                        │ │
│  │    - Sugerir reemplazos wash-sale compliant                            │ │
│  │                                                                         │ │
│  │  • After-Tax Returns:                                                   │ │
│  │    - Calcular retorno neto de impuestos                               │ │
│  │    - Optimizar para eficiencia fiscal                                  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                    REINFORCEMENT LEARNING (RL)                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  TRADING ENVIRONMENT                                                    │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │ │
│  │  │ State Space (Observaciones):                                       │ │ │
│  │  │ • Indicadores técnicos (RSI, MACD, ROC, etc.)                    │ │ │
│  │  │ • Contexto de mercado (VIX, tendencias, volumen)                   │ │ │
│  │  │ • Posición actual (long/short/flat)                                │ │ │
│  │  │ • P&L acumulado                                                    │ │ │
│  │  │ • Drawdown actual                                                  │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                         │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │ │
│  │  │ Action Space (Acciones):                                           │ │ │
│  │  │ • Discreta: HOLD, BUY, SELL, ADJUST_SL, ADJUST_TP                │ │ │
│  │  │ • Continua: [position_size, sl_adjust, tp_adjust]                 │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                         │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │ │
│  │  │ Reward Function (Recompensa):                                       │ │ │
│  │  │                                                                   │ │ │
│  │  │   R = w1 × P&L - w2 × Drawdown - w3 × Transacción                  │ │ │
│  │  │       + w4 × Sharpe                                                │ │ │
│  │  │                                                                   │ │ │
│  │  │ Donde:                                                            │ │ │
│  │  │   • P&L: Ganancia/pérdida del trade                              │ │ │
│  │  │   • Drawdown: Penalización por caídas                            │ │ │
│  │  │   • Transacción: Coste de comisión                               │ │ │
│  │  │   • Sharpe: Bonus por retorno ajustado por riesgo                 │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                         │ │
│  │  ALGORITMOS RL DISPONIBLES:                                            │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │ │
│  │  │ • PPO (Proximal Policy Optimization) - Para espacios continuos    │ │ │
│  │  │ • A2C (Advantage Actor-Critic) - Muestreo eficiente               │ │ │
│  │  │ • DDPG (Deep Deterministic Policy Gradient) - Acciones continuas  │ │ │
│  │  │ • DQN (Deep Q-Network) - Espacios discretos                       │ │ │
│  │  │ • TD3 (Twin Delayed DDPG) - Más estable que DDPG                 │ │ │
│  │  │ • SAC (Soft Actor-Critic) - Maximum entropy RL                   │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                         │ │
│  │  ENTRENAMIENTO:                                                          │ │
│  │  1. Recopilar datos históricos (entorno de simulación)                 │ │
│  │  2. Definir observación, acción, recompensa                             │ │
│  │  3. Entrenar agente con PPO/A2C/etc.                                   │ │
│  │  4. Validar con datos fuera de muestra                                 │ │
│  │  5. Desplegar en producción (con monitoreo)                            │ │
│  │                                                                         │ │
│  │  TRANSFER LEARNING:                                                      │ │
│  │  • Model Registry: Modelos pre-entrenados por régimen                │ │
│  │    - Bull market model                                                 │ │
│  │    - Bear market model                                                 │ │
│  │    - Sideways market model                                             │ │
│  │  • Fine-tuning: Adaptar modelo a nuevas condiciones                   │ │
│  │  • Knowledge Distillation: Comprimir modelo grande → pequeño          │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                    MONITOREO Y MEJORA CONTINUA                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  • Concept Drift Detection: Detectar degradación de modelo            │ │
│  │  • Hyperparameter Tuning: Optimizar parámetros automáticamente         │ │
│  │  • Feature Extraction: Ingeniería de features dinámica                │ │
│  │  • Backtesting Continuo: Validar con datos recientes                 │ │
│  │  • A/B Testing: Probar nuevas estrategias en producción               │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Componentes del Algoritmo

### 1. INPUT PROFILE (Módulo 1)

**Archivo**: `app/core/models/input_profile.py`

```python
InputProfile {
    input_id: str
    capital_initial: Decimal          # €1 - €10M
    objetivo_inversion: Enum          # maximizar_capital, dividendos, etc.
    risk_tolerance: Enum              # bajo, medio, alto
    investment_horizon: int           # 1 - 600 meses
    constraints: Dict (opcional)      # límites sectoriales, etc.
}

# Capital Tier Classification
capital < €25k    → MICRO
€25k - €100k     → SMALL
€100k - €500k    → MEDIUM
> €500k          → LARGE
```

### 2. STOCK SELECTION (Módulo 2)

**Archivos**:
- `app/services/market_universe_orchestrator.py`
- `app/services/market_universe_loader.py`
- `app/services/strategy_stock_allocator.py`

```python
MarketUniverseOrchestrator {
    # Universos disponibles
    - S&P 500 (500 acciones)
    - NASDAQ 100 (100 acciones)
    - IBEX 35 (35 acciones)
    - DOW JONES (30 acciones)
    - Crypto (BTC, ETH, etc.)

    # Filtros
    MIN_LIQUIDITY_USD = 500_000      # $500K volumen mínimo
    MIN_PRICE = 5.0                   # $5 mínimo
    MAX_VOLATILITY = 0.15            # 15% volatilidad máxima
    LOOKBACK_DAYS = 126               # ~6 meses de datos
}

StrategyStockAllocator {
    # Métricas calculadas por acción
    H_long (Hurst)        # 0 - 1 (0.5 = random walk)
    half_life (τ)         # días hasta reversión 50%
    sortino_ratio         # retorno / downside_dev
    garch_volatility      # volatilidad futura estimada
    cointegration_score   # para pares (0 - 1)

    # Clasificación
    if H > 0.55:
        strategy = "momentum"
    elif H < 0.45:
        strategy = "mean_reversion"
    else:
        strategy = "pairs_trading"  # si tiene par cointegrado
}
```

### 3. CAPITAL ALLOCATION (Módulo 3)

**Archivos**:
- `app/services/strategy_stock_allocator.py` (método `allocate_capital_ERC`)
- `app/services/portfolio_construction/portfolio_constructor.py`

```python
# ERC (Equal Risk Contribution) Optimization
def allocate_capital_ERC(
    scores: Dict[str, Dict[str, float]],
    total_capital: float,
    strategy_allocations: Dict[str, float]
) -> Dict[str, float]:

    # Construir matriz de covarianza
    returns_matrix = ...  # datos históricos
    cov_matrix = np.cov(returns_matrix)

    # Optimizar: minimizar varianza de contribuciones de riesgo
    def objective(weights):
        port_vol = sqrt(weights' @ cov_matrix @ weights)
        marginal_contrib = (cov_matrix @ weights) / port_vol
        risk_contrib = weights * marginal_contrib
        return var(risk_contrib)  # minimizar varianza

    # Constraints
    constraints = [
        {'type': 'eq', 'fun': lambda w: sum(w) - 1.0},  # suma = 1
    ]
    bounds = [(0, MAX_STRATEGY_EXPOSURE)] * n  # 0 ≤ w_i ≤ 50%

    result = minimize(objective, initial_weights, bounds, constraints)

    return {
        ticker: total_capital * weight
        for ticker, weight in result.x
    }
```

### 4. TRADING EXECUTION (Módulo 4)

**Archivos**:
- `app/services/live_trading/trading_bridge_orchestrator.py`
- `app/services/live_trading/broker_connector.py`
- `app/services/live_trading/order_manager.py`

```python
TradingBridgeOrchestrator {
    # Flujo de ejecución
    1. Recibir alerta de estrategia
    2. Validar con Risk Gates
    3. Calcular tamaño de posición
    4. Determinar orden (market/limit/stop)
    5. Enviar a broker
    6. Monitorear ejecución
    7. Actualizar portfolio

    # Risk Gates (pre-trade)
    validate_trade(trade) {
        assert trade.daily_loss < MAX_DAILY_LOSS (5%)
        assert trade.portfolio_drawdown < MAX_DRAWDOWN (15%)
        assert trade.position_size < MAX_POSITION_SIZE (10%)
        assert trade.correlation < MAX_CORRELATION (0.7)
        assert trade.portfolio_beta in [-0.5, 1.5]
    }
}
```

### 5. RISK & TAX MANAGEMENT (Módulo 5)

**Archivos**:
- `app/services/live_trading/risk_gates.py`
- `app/services/tax_efficiency/tax_optimized_builder.py`
- `app/services/tax_efficiency/capital_gain_tracker.py`
- `app/services/tax_efficiency/tax_loss_harvester.py`

```python
CapitalGainTracker {
    # Métodos de cost basis
    FIFO    # First In, First Out
    LIFO    # Last In, First Out
    AVERAGE # Cost basis promedio

    # Clasificación de ganancias
    if holding_period < 365 days:
        tax_rate = 0.25  # Short-term (25-33%)
    else:
        tax_rate = 0.15  # Long-term (15-23%)

    # Cálculo de tax liability
    tax_liability = (realized_gain * tax_rate)
}

TaxLossHarvester {
    # Identificar oportunidades de harvesting
    identify_harvestable_positions() {
        for position in portfolio:
            if position.unrealized_loss < 0:
                if position.overweight_target():
                    harvesting_candidates.add(position)
    }

    # Ejecutar harvesting manteniendo allocation
    harvest_losses(positions) {
        for position in positions:
            sell(position)
            buy(replacement)  # wash-sale compliant
    }
}

TaxOptimizedPortfolioBuilder {
    # Optimizar considerando taxes
    optimize_for_taxes(base_allocation, current_positions, cost_basis) {
        # 1. Calcular after-tax return
        after_tax_return = pre_tax_return * (1 - effective_tax_rate)

        # 2. Harvest losses en positions sobrepeso
        harvestable = harvester.identify_harvestable_positions()

        # 3. Ajustar allocation para eficiencia fiscal
        tax_adjusted = base_allocation.copy()
        for position in harvestable:
            tax_adjusted[position.symbol] *= 0.5  # reducir
            tax_benefit += position.loss * marginal_tax_rate

        # 4. Sugerir reemplazos wash-sale compliant
        replacements = wash_detector.find_replacements(harvestable)

        return TaxOptimizedAllocation(
            base_allocation,
            tax_adjusted,
            harvestable,
            tax_benefit,
            after_tax_return
        )
    }
}
```

---

## Módulos de Aprendizaje

### Reinforcement Learning (RL)

**Archivo**: `app/strategies/momentum_modular/learning/reinforcement_learning_engine.py`

```python
class TradingEnv(gym.Env):
    """
    Entorno de trading para RL
    """

    def __init__(self, config):
        # Espacio de observación (20 features)
        self.observation_space = gym.spaces.Box(
            low=-inf, high=inf, shape=(20,), dtype=float32
        )

        # Espacio de acción (5 acciones discretas)
        self.action_space = gym.spaces.Discrete(5)
        # 0 = HOLD, 1 = BUY, 2 = SELL, 3 = ADJUST_SL, 4 = ADJUST_TP

        # Configuración de recompensa
        self.reward_config = {
            "pnl_weight": 1.0,
            "sharpe_weight": 0.3,
            "drawdown_penalty": 0.5,
            "transaction_cost": 0.001,
        }

    def step(self, action):
        """
        Ejecutar acción y retornar (obs, reward, done, info)
        """
        # 1. Ejecutar acción
        if action == 1:  # BUY
            self.position = 1
        elif action == 2:  # SELL
            self.position = 0
        elif action == 3:  # ADJUST_SL
            self.stop_loss *= 0.95

        # 2. Calcular recompensa
        pnl = self.calculate_pnl()
        sharpe = self.calculate_sharpe()
        drawdown = self.calculate_drawdown()

        reward = (
            self.reward_config["pnl_weight"] * pnl
            - self.reward_config["drawdown_penalty"] * drawdown
            + self.reward_config["sharpe_weight"] * sharpe
            - self.reward_config["transaction_cost"] * self.trade_cost
        )

        # 3. Actualizar estado
        obs = self._get_observation()
        done = self.episode_ended()

        return obs, reward, done, {}

    def reset(self):
        """Resetear entorno"""
        self.position = 0
        self.cash = 100000
        self.equity = [100000]
        return self._get_observation()

    def _get_observation(self):
        """
        Obtener vector de observación (20 features)
        """
        return np.array([
            # Indicadores técnicos (10)
            self.rsi, self.macd, self.roc, self.slope,
            self.bb_upper, self.bb_lower, self.volatility,
            self.volume_sma, self.volume_ratio, self.gap,

            # Contexto de mercado (5)
            self.vix, self.market_trend, self.sector_performance,
            self.correlation_benchmark, self.beta,

            # Estado del portfolio (5)
            self.position, self.unrealized_pnl, self.drawdown,
            self.exposure, self.cash_ratio,
        ])

class ReinforcementLearningEngine(BaseLearningEngine):
    """
    Motor de RL para trading
    """

    def __init__(self, algorithm="PPO"):
        self.algorithm = algorithm
        self.env = TradingEnv(config={...})
        self.model = None

    def train(self, episodes=1000):
        """
        Entrenar agente RL
        """
        if self.algorithm == "PPO":
            from stable_baselines3 import PPO
            self.model = PPO("MlpPolicy", self.env, verbose=1)
            self.model.learn(total_timesteps=episodes)

        elif self.algorithm == "A2C":
            from stable_baselines3 import A2C
            self.model = A2C("MlpPolicy", self.env, verbose=1)
            self.model.learn(total_timesteps=episodes)

        # ... otros algoritmos

        return self.model

    def predict(self, observation):
        """
        Predecir acción dado estado actual
        """
        action, _states = self.model.predict(observation, deterministic=True)
        return action

    def save(self, path):
        """Guardar modelo entrenado"""
        self.model.save(path)

    def load(self, path):
        """Cargar modelo entrenado"""
        if self.algorithm == "PPO":
            from stable_baselines3 import PPO
            self.model = PPO.load(path)
        # ...
```

### Transfer Learning

**Archivo**: `app/strategies/momentum_modular/learning/transfer_learning.py`

```python
class TransferLearningManager:
    """
    Gestiona transfer learning entre modelos
    """

    def __init__(self):
        self.model_registry = ModelRegistry()
        self.fine_tuner = FineTuner()
        self.distiller = KnowledgeDistiller()

    def get_model_for_regime(self, regime: str) -> object:
        """
        Obtener modelo pre-entrenado para régimen

        Regímenes:
        - bull: mercado alcista
        - bear: mercado bajista
        - sideways: mercado lateral
        - high_vol: alta volatilidad
        """
        return self.model_registry.get_model(regime)

    def fine_tune(self, model, new_data, epochs=10):
        """
        Fine-tune modelo con nuevos datos
        """
        return self.fine_tuner.fine_tune(model, new_data, epochs)

    def distill(self, teacher_model, student_model):
        """
        Destilar conocimiento de modelo grande a pequeño
        """
        return self.distiller.distill(teacher_model, student_model)
```

### Supervised Learning

**Archivo**: `app/strategies/momentum_modular/learning/supervised_learning_engine.py`

```python
class SupervisedLearningEngine(BaseLearningEngine):
    """
    Motor de aprendizaje supervisado
    """

    def __init__(self, algorithm="RandomForest"):
        self.algorithm = algorithm
        self.model = None
        self.feature_extractor = FeatureExtractor()

    def train(self, X, y):
        """
        Entrenar modelo predictivo
        """
        if self.algorithm == "RandomForest":
            from sklearn.ensemble import RandomForestClassifier
            self.model = RandomForestClassifier(n_estimators=100)

        elif self.algorithm == "XGBoost":
            from xgboost import XGBClassifier
            self.model = XGBClassifier()

        elif self.algorithm == "LightGBM":
            from lightgbm import LGBMClassifier
            self.model = LGBMClassifier()

        self.model.fit(X, y)
        return self.model

    def predict_proba(self, X):
        """
        Predecir probabilidad de éxito del trade
        """
        return self.model.predict_proba(X)[:, 1]  # probabilidad de clase 1

    def get_feature_importance(self):
        """
        Obtener importancia de features
        """
        return self.model.feature_importances_
```

---

## Flujo de Ejecución

### Flujo Principal (Main Loop)

```python
async def main_trading_loop():
    """
    Loop principal de trading
    """
    while True:
        # 1. Obtener datos de mercado
        market_data = await market_data_service.get_quotes(symbols)

        # 2. Generar señales de estrategias
        signals = {}
        for strategy in strategies:
            signal = await strategy.generate_signal(market_data)
            signals[strategy.name] = signal

        # 3. Combinar señales (ensemble)
        ensemble_signal = ensemble.combine(signals)

        # 4. Validar con Risk Gates
        if risk_gates.validate(ensemble_signal):
            # 5. Ajustar por taxes
            tax_adjusted_signal = tax_optimizer.optimize(ensemble_signal)

            # 6. Ejecutar trade
            await trading_bridge.execute(tax_adjusted_signal)

        # 7. Actualizar modelo RL (si está entrenando)
        if rl_mode == "training":
            rl_agent.train_step()

        # 8. Monitorear y drift detection
        if drift_detector.detect_drift():
            logger.warning("Concept drift detected, retraining...")
            rl_agent = retrain_model()

        # 9. Esperar siguiente ciclo
        await asyncio.sleep(60)  # 1 minuto
```

### Flujo de Entrenamiento RL

```python
async def train_rl_agent():
    """
    Entrenar agente RL
    """
    # 1. Cargar datos históricos
    historical_data = await load_historical_data(
        symbols=selected_symbols,
        start_date=datetime.now() - timedelta(days=365*2),
        end_date=datetime.now()
    )

    # 2. Crear entorno de trading
    env = TradingEnv({
        "data": historical_data,
        "initial_capital": 100000,
        "commission": 0.001,
        "slippage": 0.0001,
    })

    # 3. Crear modelo RL
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        gamma=0.99,  # discount factor
        gae_lambda=0.95,
        clip_range=0.2,
    )

    # 4. Entrenar
    model.learn(total_timesteps=1_000_000)

    # 5. Validar
    mean_reward, std_reward = evaluate_model(model, env)

    # 6. Guardar
    model.save("models/rl_trading_model")

    return model
```

### Flujo de Optimización de Taxes

```python
async def optimize_portfolio_taxes():
    """
    Optimizar portfolio para eficiencia fiscal
    """
    # 1. Obtener posiciones actuales
    current_positions = portfolio.get_positions()

    # 2. Calcular ganancias/pérdidas no realizadas
    unrealized_gains = capital_gain_tracker.calculate_unrealized_gains(
        current_positions
    )

    # 3. Identificar oportunidades de harvesting
    harvestable = tax_loss_harvester.identify_harvestable_positions(
        current_positions,
        cost_basis,
        current_prices
    )

    # 4. Verificar wash sales
    for position in harvestable:
        wash_compliant = wash_sale_detector.check_replacement(
            position.symbol,
            candidate_replacements
        )

    # 5. Calcular beneficio fiscal
    tax_benefit = sum(
        position.loss * marginal_tax_rate
        for position in harvestable
    )

    # 6. Ejecutar harvesting
    for position in harvestable:
        # Vender posición con pérdida
        await trading_bridge.sell(position.symbol, position.quantity)

        # Comprar reemplazo wash-sale compliant
        replacement = find_replacement(position.symbol)
        await trading_bridge.buy(replacement, position.quantity)

    # 7. Recalcular after-tax return
    after_tax_return = calculate_after_tax_return(
        portfolio,
        harvested_losses=tax_benefit
    )

    return {
        "harvested_positions": len(harvestable),
        "tax_benefit": tax_benefit,
        "after_tax_return": after_tax_return,
    }
```

---

## Resumen de Módulos Existentes

| # | Módulo | Archivo | Propósito |
|---|--------|---------|-----------|
| 1 | InputProfile | `app/core/models/input_profile.py` | Validar entrada usuario |
| 2 | ProfileGenerator | `app/services/profile_generator/profile_generator.py` | Generar InvestmentProfile |
| 3 | ModuleParametrizer | `app/services/parametrization/module_parametrizer.py` | Mapear perfil a parámetros |
| 4 | MarketUniverseOrchestrator | `app/services/market_universe_orchestrator.py` | Seleccionar acciones |
| 5 | StrategyStockAllocator | `app/services/strategy_stock_allocator.py` | Asignar capital a estrategias |
| 6 | PortfolioConstructor | `app/services/portfolio_construction/portfolio_constructor.py` | Optimizar portfolio |
| 7 | TradingBridgeOrchestrator | `app/services/live_trading/trading_bridge_orchestrator.py` | Ejecutar trades |
| 8 | RiskGates | `app/services/live_trading/risk_gates.py` | Validar riesgos |
| 9 | BrokerConnector | `app/services/live_trading/broker_connector.py` | Conectar con broker |
| 10 | CapitalGainTracker | `app/services/tax_efficiency/capital_gain_tracker.py` | Tracking ganancias capital |
| 11 | TaxLossHarvester | `app/services/tax_efficiency/tax_loss_harvester.py` | Harvesting de pérdidas |
| 12 | WashSaleDetector | `app/services/tax_efficiency/wash_sale_detector.py` | Detectar wash sales |
| 13 | TaxOptimizedPortfolioBuilder | `app/services/tax_efficiency/tax_optimized_builder.py` | Optimizar portfolio taxes |
| 14 | ReinforcementLearningEngine | `app/strategies/momentum_modular/learning/reinforcement_learning_engine.py` | Aprendizaje por refuerzo |
| 15 | SupervisedLearningEngine | `app/strategies/momentum_modular/learning/supervised_learning_engine.py` | Aprendizaje supervisado |
| 16 | TransferLearningManager | `app/strategies/momentum_modular/learning/transfer_learning.py` | Transfer learning |
| 17 | DriftDetector | `app/strategies/momentum_modular/learning/drift_detector.py` | Detectar degradación |

---

## Conclusión

El sistema tiene **TODOS los componentes necesarios** para un trading automatizado completo:

1. ✅ **Input Profile** → Definir perfil del inversor
2. ✅ **Stock Selection** → Seleccionar acciones basado en análisis cuantitativo
3. ✅ **Capital Allocation** → Asignar capital con optimización ERC
4. ✅ **Trading** → Ejecutar órdenes con risk gates
5. ✅ **Risk Management** → Gestión de riesgo en tiempo real
6. ✅ **Taxes** → Optimización fiscal con tax loss harvesting
7. ✅ **Reinforcement Learning** → Agente RL que aprende políticas óptimas
8. ✅ **Supervised Learning** → Modelos predictivos para señales
9. ✅ **Transfer Learning** → Adaptación a cambios de mercado

**El algoritmo completo está implementado.** Solo falta integrar los componentes en el workflow principal que ya existe.
