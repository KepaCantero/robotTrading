# Estrategia Momentum Modular e Inteligente - Diseño Técnico

## Arquitectura General

```
┌─────────────────────────────────────────────────────────────┐
│                    MARKET CONTEXT ANALYZER                  │
│  Detecta: Trend / Range / High Volatility / Low Volatility │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                      SIGNAL GENERATOR                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ EMA Filter  │  │ RSI Filter  │  │Volume Filter│        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │StochRSI Flt │  │Momentum Flt │  │ ATR Filter  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                      RISK MANAGER                            │
│  - Stop Loss (dinámico o fijo)                              │
│  - Take Profit                                              │
│  - Max Exposure                                             │
│  - Position Sizing                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
                    SIGNAL
```

---

## Pseudocódigo: Flujo de Generación de Señales

```python
class ModularMomentumStrategy:

    def generate_signal(self, market_data):
        # PASO 1: Analizar contexto de mercado
        market_context = self.market_analyzer.analyze(market_data)
        # Retorna: {
        #     'type': 'trend_up' | 'trend_down' | 'range' | 'high_vol' | 'low_vol',
        #     'confidence': 0.0-1.0,
        #     'volatility_regime': 'high' | 'normal' | 'low'
        # }

        # PASO 2: Obtener todos los indicadores
        indicators = self.calculate_indicators(market_data)
        # indicators = {
        #     'rsi': float,
        #     'ema_fast': float,
        #     'ema_slow': float,
        #     'stoch_rsi_k': float,
        #     'stoch_rsi_d': float,
        #     'momentum_roc': float,
        #     'volume_ratio': float,
        #     'atr': float,
        #     'atr_percentile': float  # percentil 30, 60, 90
        # }

        # PASO 3: Aplicar filtros modulares (cada uno decide si aplica según contexto)
        buy_conditions = []
        sell_conditions = []

        # EMA Filter - solo en mercados de tendencia
        if self.ema_filter.enabled:
            if market_context['type'] in ['trend_up', 'trend_down']:
                ema_result = self.ema_filter.evaluate(
                    indicators,
                    market_context,
                    signal_type='BUY'
                )
                buy_conditions.append(ema_result['passed'])

        # RSI Filter - adaptativo según régimen
        if self.rsi_filter.enabled:
            rsi_result = self.rsi_filter.evaluate(
                indicators,
                market_context,
                signal_type='BUY'
            )
            buy_conditions.append(rsi_result['passed'])

        # StochRSI Filter - solo si está habilitado
        if self.stoch_rsi_filter.enabled:
            stoch_result = self.stoch_rsi_filter.evaluate(
                indicators,
                market_context,
                signal_type='BUY'
            )
            buy_conditions.append(stoch_result['passed'])

        # Momentum Filter - crítico en tendencias
        if self.momentum_filter.enabled:
            momentum_result = self.momentum_filter.evaluate(
                indicators,
                market_context,
                signal_type='BUY'
            )
            buy_conditions.append(momentum_result['passed'])

        # Volume Filter - siempre importante
        if self.volume_filter.enabled:
            volume_result = self.volume_filter.evaluate(
                indicators,
                market_context,
                signal_type='BUY'
            )
            buy_conditions.append(volume_result['passed'])

        # ATR Filter - adaptativo según volatilidad
        if self.atr_filter.enabled:
            atr_result = self.atr_filter.evaluate(
                indicators,
                market_context,
                signal_type='BUY'
            )
            buy_conditions.append(atr_result['passed'])

        # PASO 4: Combinar condiciones según modo de combinación
        # Combinación puede ser: 'ALL' (AND), 'ANY' (OR), 'MAJORITY' (>50%)
        combined_buy = self.combine_conditions(
            buy_conditions,
            mode=self.config['combination_mode']  # 'ALL' | 'MAJORITY' | 'ANY'
        )

        # PASO 5: Aplicar Risk Manager
        if combined_buy:
            risk_check = self.risk_manager.validate_signal(
                signal_type='BUY',
                market_data=market_data,
                indicators=indicators,
                portfolio_state=self.portfolio
            )

            if risk_check['allowed']:
                return self.create_buy_signal(
                    market_data,
                    indicators,
                    confidence=self.calculate_confidence(buy_conditions),
                    risk_params=risk_check['params']
                )

        # Similar para SELL...
        return None
```

---

## YAML de Configuración Modular

```yaml
# momentum_modular.yaml
strategy_name: momentum_modular
enabled: true
version: "2.0.0"

# MARKET CONTEXT ANALYZER
market_analyzer:
  enabled: true
  lookback_period: 60 # días para slotify régimen
  trend_detection:
    method: "ema_cross" # 'ema_cross' | 'adx' | 'macd'
    ema_fast_period: 12
    ema_slow_period: 26
    min_trend_strength: 0.6 # 0-1
  volatility_detection:
    method: "atr_percentile" # 'atr_percentile' | 'std_dev'
    percentile_window: 30
    high_vol_threshold: 75 # percentil
    low_vol_threshold: 25
  range_detection:
    method: "bollinger_squeeze"
    lookback_period: 20
    squeeze_threshold: 0.1

# PRESET DE CONFIGURACIÓN
preset: "balanced" # 'conservative' | 'balanced' | 'aggressive'

presets:
  conservative:
    combination_mode: "ALL" # Todos los filtros deben pasar
    min_confidence: 0.75
    risk_adjustment: 1.2 # Más conservador (reduce tamaño de posición 20%)

  balanced:
    combination_mode: "MAJORITY" # Mayoría de filtros (>= 50%)
    min_confidence: 0.60
    risk_adjustment: 1.0

  aggressive:
    combination_mode: "MAJORITY" # Mayoría, pero thresholds más relajados
    min_confidence: 0.50
    risk_adjustment: 0.85 # Permite posiciones 15% más grandes

# MÓDULOS DE FILTRO
modules:
  # EMA FILTER - Filtro de tendencia
  ema_filter:
    enabled: true
    priority: "high" # 'high' | 'medium' | 'low' (para combinación MAJORITY)

    # Condiciones de activación según contexto
    active_in_contexts:
      - "trend_up"
      - "trend_down"
      - "high_vol"
    inactive_in_contexts:
      - "low_vol" # Desactivar en baja volatilidad

    parameters:
      fast_period: 12
      slow_period: 26
      trend_confirmation:
        method: "price_above" # 'price_above' | 'crossover' | 'distance'
        min_distance_pct: 0.005 # 0.5% mínimo

    # Thresholds por preset
    thresholds:
      conservative:
        min_distance_pct: 0.01 # 1%
        require_crossover: true
      balanced:
        min_distance_pct: 0.005 # 0.5%
        require_crossover: false
      aggressive:
        min_distance_pct: 0.002 # 0.2%
        require_crossover: false

  # RSI FILTER - Filtro de momentum relativo
  rsi_filter:
    enabled: true
    priority: "high"

    active_in_contexts:
      - "trend_up"
      - "trend_down"
      - "range"
      - "high_vol"
    inactive_in_contexts: []

    parameters:
      period: 14
      adaptive: true # Ajusta thresholds según volatilidad

    thresholds:
      # En tendencias fuertes: RSI más permisivo
      trend_up:
        buy_min: 45
        buy_max: 70 # No comprar si ya está sobrecomprado
        sell_min: 55
        sell_max: 80

      trend_down:
        buy_min: 30
        buy_max: 50
        sell_min: 40
        sell_max: 65

      range:
        buy_min: 30
        buy_max: 50
        sell_min: 50
        sell_max: 70

      high_vol:
        buy_min: 35 # Más permisivo en alta volatilidad
        buy_max: 65
        sell_min: 45
        sell_max: 75

  # STOCHASTIC RSI FILTER
  stoch_rsi_filter:
    enabled: true
    priority: "medium"

    active_in_contexts:
      - "trend_up"
      - "range"
    inactive_in_contexts:
      - "low_vol" # Menos útil en baja volatilidad

    parameters:
      rsi_period: 14
      stoch_period: 14
      k_period: 3
      d_period: 3

    thresholds:
      conservative:
        buy_min: 20
        buy_max: 80
        sell_min: 20
        sell_max: 80
      balanced:
        buy_min: 15
        buy_max: 85
        sell_min: 15
        sell_max: 85
      aggressive:
        buy_min: 10
        buy_max: 90
        sell_min: 10
        sell_max: 90

  # MOMENTUM FILTER (ROC - Rate of Change)
  momentum_filter:
    enabled: true
    priority: "high"

    active_in_contexts:
      - "trend_up" # Crítico en tendencias
      - "trend_down"
    inactive_in_contexts:
      - "range" # Menos relevante en rangos

    parameters:
      period: 12
      method: "roc" # 'roc' | 'momentum' | 'price_change'

    thresholds:
      conservative:
        min_positive_momentum: 0.03 # 3%
        min_negative_momentum: -0.03
      balanced:
        min_positive_momentum: 0.015 # 1.5%
        min_negative_momentum: -0.015
      aggressive:
        min_positive_momentum: 0.01 # 1%
        min_negative_momentum: -0.01

  # VOLUME FILTER
  volume_filter:
    enabled: true
    priority: "high"

    active_in_contexts:
      - "ALL" # Siempre activo

    parameters:
      lookback_period: 20
      method: "ratio" # 'ratio' | 'percentile' | 'sma_cross'

    thresholds:
      conservative:
        min_volume_ratio: 沃尔.2 # 20% sobre promedio
      balanced:
        min_volume_ratio: 1.1 # 10% sobre promedio
      aggressive:
        min_volume_ratio: 1.05 # 5% sobre promedio

  # ATR FILTER - Filtro de volatilidad
  atr_filter:
    enabled: true
    priority: "medium"

    active_in_contexts:
      - "ALL"

    parameters:
      period: 14
      method: "relative_percentile" # 'relative' | 'absolute' | 'percentile'
      use_relative_atr: true # ATR como % del precio

    thresholds:
      # En alta volatilidad: más permisivo
      high_vol:
        min_atr_percentile: 50 # Percentil 50
        min_relative_atr: 0.004 # 0.4%

      normal_vol:
        min_atr_percentile: 60 # Percentil 60
        min_relative_atr: 0.006 # 0.6%

      low_vol:
        min_atr_percentile: 70 # Percentil 70 (solo entrar en movimientos significativos)
        min_relative_atr: 0.008 # 0.8%

      conservative:
        min_atr_percentile: 70
        min_relative_atr: 0.008
      balanced:
        min_atr_percentile: 60
        min_relative_atr: 0.006
      aggressive:
        min_atr_percentile: 50
        min_relative_atr: 0.004

# RISK MANAGER
risk_manager:
  enabled: true

  position_sizing:
    method: "fixed_percentage" # 'fixed_percentage' | 'volatility_target' | 'kelly'
    base_percentage: 0.10 # 10% del capital por posición

    volatility_targeting:
      enabled: false
      target_volatility: 0.10 # 10% anualizada
      lookback_period: 30

    kelly_criterion:
      enabled: false
      kelly_fraction: 0.25 # Usar 25% de Kelly completo

  stop_loss:
    enabled: true
    method: "dynamic_atr" # 'fixed_percentage' | 'dynamic_atr' | 'trailing'

    fixed_percentage:
      value: 0.025 # 2.5%

    dynamic_atr:
      multiplier: 2.0 # ATR * 2.0
      min_percentage: 0.015 # Mínimo 1.5%
      max_percentage: 0.05 # Máximo 5%

    trailing:
      activation_pct_above_entry: 0.02 # Activar después de +2%
      trail_distance_pct: 0.01 # Trail a 1% del máximo

  take_profit:
    enabled: true
    method: "fixed_percentage" # 'fixed_percentage' | 'atr_multiple' | 'trailing'

    fixed_percentage:
      value: 0.08 # 8% (risk/reward ~3:1 si stop es 2.5%)

    atr_multiple:
      multiplier: 4.0
      min_percentage: 0.05
      max_percentage: 0.15

  max_exposure:
    total_portfolio: 0.50 # Máximo 50% del capital total invertido
    per_strategy: 0.40 # Máximo 40% por estrategia
    per_symbol: 0.15 # Máximo 15% por símbolo

  max_positions:
    total: 10
    per_strategy: 7

# COOLDOWN Y FRECUENCIA DE SEÑALES
signal_frequency:
  cooldown_bars: 5 # Mínimo 5 barras entre señales del mismo tipo
  max_signals_per_day: 3
  max_signals_per_symbol_per_day: 1

# ADAPTIVE LEARNING (Reservado para futura IA)
adaptive_learning:
  enabled: false

  # Cuando se habilite, estos módulos aprenderán de resultados
  modules_for_adaptation:
    - "ema_filter"
    - "rsi_filter"
    - "momentum_filter"

  adaptation_method: "reinforcement_learning" # 'rl' | 'genetic_algorithm' | 'neural_net'

  parameters_to_adapt:
    thresholds: true
    period: false # Mantener períodos fijos por ahora
    combination_weights: true # Aprender pesos para combinación MAJORITY

  learning_window:
    lookback_days: 90
    reoptimize_frequency_days: 30
    min_trades_for_learning: 20
```

---

## Especificación Técnica de Módulos

### MarketAnalyzer

```python
class MarketAnalyzer:
    """
    Detecta el régimen de mercado actual para adaptar filtros.
    """

    def analyze(self, market_data: Quote, price_history: List[float]) -> Dict:
        """
        Retorna contexto de mercado.

        Returns:
            {
                'type': 'trend_up' | 'trend_down' | 'range' | 'high_vol' | 'low_vol',
                'confidence': float,  # 0.0-1.0
                'volatility_regime': 'high' | 'normal' | 'low',
                'trend_strength': float,  # 0.0-1.0
                'volatility_percentile': int  # 0-100
            }
        """
        # 1. Detectar tendencia
        trend_info = self._detect_trend(price_history)

        # 2. Detectar volatilidad
        vol_info = self._detect_volatility(price_history)

        # 3. Detectar rango
        range_info = self._detect_range(price_history)

        # 4. Combinar información
        return self._combine_context(trend_info, vol_info, range_info)
```

### BaseFilter (Clase abstracta para todos los filtros)

```python
class BaseFilter:
    """
    Interfaz base para todos los filtros modulares.
    """

    def evaluate(
        self,
        indicators: Dict,
        market_context: Dict,
        signal_type: str
    ) -> Dict:
        """
        Evalúa si el filtro pasa para el signal_type dado.

        Returns:
            {
                'passed': bool,
                'confidence': float,  # 0.0-1.0
                'reason': str,
                'metadata': Dict
            }
        """
        # 1. Verificar si este filtro está activo en este contexto
        if not self._is_active_in_context(market_context):
            return {
                'passed': True,  # Si no está activo, no bloquea
                'confidence': 1.0,
                'reason': f"Filter inactive in {market_context['type']}",
                'metadata': {}
            }

        # 2. Aplicar lógica específica del filtro
        return self._apply_filter_logic(indicators, market_context, signal_type)
```

---

## Evolución con IA (Futuro)

### Opción 1: Reinforcement Learning (RL)

```python
class AdaptiveFilterManager:
    """
    Sistema de aprendizaje por refuerzo para ajustar parámetros.
    """

    def __init__(self):
        self.agent = RLAgent()  # Q-Learning o PPO
        self.state_space = {
            'market_type': ['trend_up', 'trend_down', 'range'],
            'volatility': ['low', 'normal', 'high'],
            'filter_states': {}  # Estado de cada filtro
        }
        self.action_space = {
            'adjust_threshold': [-0.1, -0.05, 0, +0.05, +0.1],
            'toggle_filter': [True, False],
            'adjust_combination_weight': [0.0-1.0]
        }

    def learn_from_trade(self, trade_result: Trade, signals_history: List):
        """
        Aprende de cada trade completado.
        """
        reward = self._calculate_reward(trade_result)  # P&L ajustado por riesgo

        state = self._get_state_at_signal_time(trade_result.entry_time)
        action = self._get_action_taken(signals_history)

        self.agent.update_q_value(state, action, reward)

    def get_optimal_parameters(self, current_market_state):
        """
        Retorna parámetros optimizados según estado de mercado.
        """
        return self.agent.get_best_action(current_market_state)
```

**Reward Function:**

```python
def _calculate_reward(self, trade: Trade) -> float:
    """
    Reward = (PnL / Risk) * WinRate_Bonus - Overtrading_Penalty
    """
    risk_adjusted_pnl = trade.pnl / max(trade.risk_taken, 0.01)
    win_bonus = 1.5 if trade.pnl > 0 else 1.0
    frequency_penalty = 0.9 if self._trades_too_frequent() else 1.0

    return risk_adjusted_pnl * win_bonus * frequency_penalty
```

### Opción 2: Genetic Algorithm

```python
class GeneticOptimizer:
    """
    Optimiza combinaciones de parámetros usando algoritmos genéticos.
    """

    def evolve_parameters(self, population_size=50, generations=20):
        """
        Evoluciona parámetros de filtros durante múltiples generaciones.
        """
        population = self._initialize_population(population_size)

        for generation in range(generations):
            # Evaluar fitness de cada individuo
            fitness_scores = [
                self._evaluate_individual(individual)
                for individual in population
            ]

            # Seleccionar mejores (top 30%)
            elite = self._select_elite(population, fitness_scores, top_pct=0.3)

            # Cruzar y mutar
            new_population = self._crossover_and_mutate(elite, population_size)

            population = new_population

        return self._get_best_individual(population)
```

**Genome Structure:**

```python
genome = {
    'ema_filter': {
        'enabled': bool,
        'fast_period': int,  # 8-20
        'slow_period':采用了,  # 20-50
        'min_distance_pct': float  # 0.001-0.02
    },
    'rsi_filter': {
        'enabled': bool,
        'period': int,  # 10-20
        'buy_min': int,  # 30-50
        'buy_max': int  # 60-80
    },
    # ... otros filtros
    'combination_mode': str,  # 'ALL' | 'MAJORITY' | 'ANY'
    'combination_weights': Dict[float]  # Pesos por filtro
}
```

### Opción 3: Neural Network para Context Detection

```python
class MarketContextNeuralNet:
    """
    Red neuronal para detectar régimen de mercado y sugerir filtros activos.
    """

    def __init__(self):
        self.model = Sequential([
            LSTM(64, input_shape=(timesteps, features)),
            Dense(32, activation='relu'),
            Dense(16, activation='relu'),
            Dense(num_market_types, activation='softmax')  # 5 tipos de mercado
        ])

    def predict_market_context(self, price_sequence, volume_sequence, indicators):
        """
        Predice probabilidades de cada tipo de mercado.
        """
        input_data = self._prepare_input(price_sequence, volume_sequence, indicators)
        probabilities = self.model.predict(input_data)

        return {
            'trend_up': probabilities[0],
            'trend_down': probabilities[1],
            'range': probabilities[2],
            'high_vol': probabilities[3],
            'low_vol': probabilities[4],
            'recommended_filters': self._get_filter_recommendations(probabilities)
        }
```

---

## Presets Optimizados por Estilo de Trading

### 1. Conservative (Conservador)

- **Objetivo**: Alta win rate (>50%), bajo drawdown (<10%)
- **Combinación**: `ALL` - Todos los filtros deben pasar
- **Filtros activos**: Todos, con thresholds estrictos
- **Risk**: Stop-loss fijo 2.5%, Take-profit 6%, Max exposure 30%
- **Uso**: Cuentas pequeñas, traders que priorizan capital preservation

### 2. Balanced (Balanceado)

- **Objetivo**: Win rate 40-45%, Sharpe >1.0
- **Combinación**: `MAJORITY` - Mayoría de filtros (>= 50%)
- **Filtros activos**: Todos, con thresholds moderados
- **Risk**: Stop-loss dinámico ATR\*2.0, Take-profit 8%, Max exposure 50%
- **Uso**: Cuentas medianas, traders experimentados

### 3. Aggressive (Ag 高产 ivo)

- **Objetivo**: Máximo retorno, acepta más riesgo
- **Combinación**: `MAJORITY` con thresholds relajados
- **Filtros activos**: Todos, pero thresholds más permisivos
- **Risk**: Stop-loss dinámico ATR\*1.5, Take-profit 10%, Max exposure 70%
- **Uso**: Cuentas grandes, traders profesionales con alta tolerancia al riesgo

### 4. Trend-Following Specialized

- **Objetivo**: Capturar tendencias fuertes
- **Combinación**: `ALL` para EMA + Momentum + Volume
- **Filtros activos**: EMA (alta prioridad), Momentum, Volume, ATR (modo adaptativo)
- **Desactivados**: StochRSI (puede filtrar demasiado en tendencias)
- **Risk**: Trailing stop, Take-profit dinámico basado en ATR

### 5. Range Trading Specialized

- **Objetivo**: Reversiones en mercados laterales
- **Combinación**: `MAJORITY`
- **Filtros activos**: RSI (umbrales 30-70), StochRSI, Volume, ATR (para evitar rangos muy estrechos)
- **Desactivados**: EMA (menos útil en rangos), Momentum (puede ser débil)
- **Risk**: Stop-loss más ajustado (1.5%), Take-profit conservador (4%)

---

## Implementación Recomendada

### Estructura de Archivos

```
app/strategies/momentum_modular/
├── __init__.py
├── strategy.py              # Clase principal ModularMomentumStrategy
├── modules/
│   ├── __init__.py
│   ├── base_filter.py       # BaseFilter abstract class
│   ├── market_analyzer.py   # MarketAnalyzer
│   ├── filters/
│   │   ├── ema_filter.py
│   │   ├── rsi_filter.py
│   │   ├── stoch_rsi_filter.py
│   │   ├── momentum_filter.py
│   │   ├── volume_filter.py
│   │   └── scalable atr_filter.py
│   └── risk_manager.py
├── adaptive/
│   ├── rl_agent.py          # Reinforcement Learning (futuro)
│   ├── genetic_optimizer.py # Genetic Algorithm (futuro)
│   └── neural_context.py    # Neural Network (futuro)
└── config/
    └── momentum_modular.yaml
```

---

## Checklist de Implementación

- [ ] Implementar `MarketAnalyzer` con detección de tendencia, volatilidad y rango
- [ ] Crear `BaseFilter` como clase abstracta
- [ ] Implementar cada filtro modular como subclase de `BaseFilter`
- [ ] Implementar `RiskManager` con stop-loss, take-profit y position sizing
- [ ] Crear sistema de combinación de condiciones (ALL/MAJORITY/ANY)
- [ ] Integrar presets (conservative/balanced/aggressive)
- [ ] Cargar configuración desde YAML
- [ ] Agregar logging detallado por módulo
- [ ] Testing unitario por módulo
- [ ] Testing de integración con diferentes contextos de mercado
- [ ] Backtesting comparativo con versión anterior
- [ ] (Opcional) Implementar RL agent para adaptación
- [ ] (Opcional) Implementar Genetic Algorithm para optimización

---

## Métricas de Éxito

1. **Win Rate**: >40% (balanced), >50% (conservative)
2. **Sharpe Ratio**: >1.0 en todos los presets
3. **Max Drawdown**: <15% (conservative), <20% (balanced)
4. **Trades por mes**: 10-30 (según preset y régimen de mercado)
5. **Adaptabilidad**: La estrategia debe generar señales en diferentes regímenes de mercado

---

## Notas Técnicas Importantes

1. **Orden de Evaluación**: Los filtros se evalúan en orden de prioridad. Si un filtro de alta prioridad falla, puede saltarse evaluación de baja prioridad en modo `MAJORITY`.

2. **Caching**: Los indicadores se calculan una vez por bar y se cachean para todos los filtros.

3. **Thread Safety**: Si se implementa en tiempo real, cada módulo debe ser thread-safe.

4. **Performance**: En backtesting, el `MarketAnalyzer` puede ejecutarse una vez por día en lugar de por bar para optimizar.

5. **Debugging**: Cada módulo debe retornar metadata detallada para debugging y análisis post-backtest.

Este diseño permite una estrategia completamente modular, adaptativa y preparada para evolución con IA en el futuro.
