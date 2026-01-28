# 📄 Papers Fundamentales - Adaptive Markets Hypothesis (Andrew Lo, 2017)

## Evolución de Estrategias y Cambio de Régimen en Mercados Adaptativos

**Contexto:** Meta-Strategy Management y Regime Detection.

Andrew Lo revolucionó la teoría financiera al proponer que los mercados son como ecosistemas evolutivos donde las estrategias compiten y mutan según las condiciones del entorno.

---

### Regla 1 — Regime Detection with HMM

Implementar clasificador HMM para detectar mercados "Eficientes" vs "Irracionales".

```python
def hmm_regime_detection(
    self,
    returns: pd.Series,
    n_regimes: int = 3,
    window: int = 252
) -> dict:
    """
    Detectar régimen de mercado usando Hidden Markov Model.

    Lo: Mercados cambian entre regímenes (bull/bear/choppy).
    """
    from hmmlearn import hmm

    # Preparar datos: retornos con features
    features = pd.DataFrame({
        'returns': returns,
        'volatility': returns.rolling(20).std(),
        'volume_ratio': self.get_volume_ratio(),
        'trend': returns.rolling(50).mean()
    }).dropna()

    # HMM con distribuciones Gaussianas
    model = hmm.GaussianHMM(
        n_components=n_regimes,
        covariance_type="full",
        n_iter=1000,
        random_state=42
    )

    # Fit
    model.fit(features.values)

    # Estados más probables recientes
    recent_states = model.predict(features.values[-30:])
    current_regime = max(set(recent_states), key=list(recent_states).count)

    # Interpretar regímenes
    regime_means = model.means_

    regimes = []
    for i, mean in enumerate(regime_means):
        if mean[0] > 0.001:  # Positive drift
            regime_type = 'BULL'
        elif mean[0] < -0.001:  # Negative drift
            regime_type = 'BEAR'
        else:
            regime_type = 'CHOPPY/SIDEWAYS'

        regimes.append({
            'state': i,
            'type': regime_type,
            'mean_return': mean[0],
            'volatility': np.sqrt(model.covars_[i][0, 0])
        })

    current_regime_info = regimes[current_regime]

    logger.info(
        f"HMM Regime: {current_regime_info['type']}, "
        f"state={current_regime}, "
        f"μ={current_regime_info['mean_return']:.4f}, "
        f"σ={current_regime_info['volatility']:.4f}"
    )

    return {
        'current_regime': current_regime,
        'regime_info': current_regime_info,
        'all_regimes': regimes,
        'regime_probability': model.predict_proba(features.values[-1:])[0],
        'model': model
    }
```

### Regla 2 — Strategy Pool Management

El robot debe tener un "pool" de sub-estrategias y activar las que mejor funcionen en el régimen actual.

```python
def strategy_pool_manager(
    self,
    current_regime: str,
    strategy_performance: dict
) -> dict:
    """
    Seleccionar estrategia según régimen.

    Lo: Diferentes estrategias para diferentes regímenes.
    """
    # Pool de estrategias
    strategy_pool = {
        'BULL': [
            'momentum_long',
            'growth_stocks',
            'leverage_etf'
        ],
        'BEAR': [
            'volatility_short',
            'put_options',
            'cash_preservation',
            'inverse_etf'
        ],
        'CHOPPY/SIDEWAYS': [
            'mean_reversion',
            'options_sell',
            'market_neutral'
        ],
        'HIGH_VOLATILITY': [
            'stop_loss_tight',
            'reduce_size',
            'vix_based'
        ]
    }

    # Estrategias activas para este régimen
    active_strategies = strategy_pool.get(current_regime, [])

    # Evaluar desempeño reciente de cada estrategia
    strategy_scores = {}

    for strategy in active_strategies:
        perf = strategy_performance.get(strategy, {})

        # Score = sharpe * win_rate * recent_profit
        sharpe = perf.get('sharpe', 0)
        win_rate = perf.get('win_rate', 0.5)
        recent_profit = perf.get('recent_7d_return', 0)

        score = sharpe * win_rate * (1 + recent_profit)
        strategy_scores[strategy] = score

    # Seleccionar top 2
    sorted_strategies = sorted(
        strategy_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )[:2]

    selected_strategies = [s[0] for s in sorted_strategies]

    logger.info(
        f"Strategy pool: Regime={current_regime}, "
        f"selected={selected_strategies}"
    )

    return {
        'active_strategies': selected_strategies,
        'all_candidate_strategies': active_strategies,
        'strategy_scores': strategy_scores,
        'regime': current_regime
    }
```

### Regla 3 — Biological Competition (Evolution)

Tratar estrategias como especies que compiten por el capital del robot.

```python
def evolutionary_strategy_competition(
    self,
    strategies: dict,
    capital_pool: float,
    generations: int = 10
) -> dict:
    """
    Competencia evolutiva entre estrategias.

    Lo: Estrategias exitosas = más capital, fallidas = extinción.
    """
    # Capital inicial por estrategia
    n_strategies = len(strategies)
    initial_capital = capital_pool / n_strategies

    # Allocación de capital actual
    allocation = {s: initial_capital for s in strategies.keys()}

    # Evolución por generaciones
    for gen in range(generations):
        # Evaluar fitness de cada estrategia
        fitness = {}

        for strategy, capital in allocation.items():
            if capital <= 0:
                fitness[strategy] = 0
                continue

            # Fitness = retorno ajustado por riesgo
            returns = self.get_strategy_returns(strategy, periods=30)
            sharpe = returns.mean() / (returns.std() + 1e-8)

            fitness[strategy] = sharpe * capital

        # Seleccionar y reproducir
        total_fitness = sum(fitness.values())

        if total_fitness == 0:
            break

        # Nueva allocación = fitness / total_fitness
        new_allocation = {}

        for strategy in strategies.keys():
            if fitness[strategy] > 0:
                new_allocation[strategy] = (
                    fitness[strategy] / total_fitness * capital_pool
                )
            else:
                new_allocation[strategy] = 0

        allocation = new_allocation

        logger.info(
            f"Evolution gen {gen+1}: "
            f"{sum(1 for v in allocation.values() if v > 0)} survivors"
        )

    # Estrategias sobrevivientes
    survivors = [s for s, v in allocation.items() if v > 0]

    logger.info(
        f"Evolution result: {len(survivors)} survivors out of {n_strategies}"
    )

    return {
        'survivors': survivors,
        'final_allocation': allocation,
        'extinct': [s for s in strategies.keys() if s not in survivors]
    }
```

### Regla 4 — Volatility Trigger for Strategy Switch

Si volatilidad sube 200%, cambiar de trading tendencial a reversión.

```python
def volatility_strategy_switch(
    self,
    current_volatility: float,
    baseline_volatility: float,
    switch_threshold: float = 2.0
) -> dict:
    """
    Cambiar estrategia si volatilidad cambia drásticamente.

    Lo: Volatilidad extrema = cambio de enfoque.
    """
    vol_ratio = current_volatility / baseline_volatility

    if vol_ratio > switch_threshold:
        # Volatilidad alta → cambio a mean reversion
        new_strategy = 'mean_reversion'
        new_params = {
            'lookback': 10,  # Más corto
            'entry_threshold': 2.0,  # Más exigente
            'position_size': 0.5,  # Reducir tamaño
            'stop_loss': 'tight'  # Stops más ajustados
        }

        logger.warning(
            f"⚠️ Volatility spike: {vol_ratio:.1f}× baseline. "
            f"Switching to {new_strategy}"
        )

    elif vol_ratio < 0.5:
        # Volatilidad baja → trend following
        new_strategy = 'trend_following'
        new_params = {
            'lookback': 50,  # Más largo
            'entry_threshold': 1.0,
            'position_size': 1.0,
            'stop_loss': 'wide'
        }

        logger.info(
            f"Low volatility: {vol_ratio:.1f}× baseline. "
            f"Switching to {new_strategy}"
        )

    else:
        new_strategy = 'maintain_current'
        new_params = {}

    return {
        'strategy': new_strategy,
        'params': new_params,
        'volatility_ratio': vol_ratio,
        'triggered': vol_ratio > switch_threshold or vol_ratio < 0.5
    }
```

### Regla 5 — Innovation Risk Management

Probar nuevas reglas con 1% del capital mientras 99% sigue reglas probadas.

```python
def innovation_risk_allocation(
    self,
    new_strategy: str,
    proven_strategy: str,
    total_capital: float,
    innovation_allocation: float = 0.01
) -> dict:
    """
    Gestionar riesgo de innovación.

    Lo: Nuevas estrategias = riesgo controlado.
    """
    # Allocación
    innovation_capital = total_capital * innovation_allocation
    proven_capital = total_capital * (1 - innovation_allocation)

    # Monitorizar nueva estrategia
    monitoring_period_days = 30
    min_trades = 20

    # Evaluar desempeño
    new_strategy_perf = self.evaluate_strategy(
        new_strategy,
        days=monitoring_period_days
    )

    # Criterios para escalar
    criteria = {
        'positive_return': new_strategy_perf['total_return'] > 0,
        'sharpe_acceptable': new_strategy_perf['sharpe'] > 0.5,
        'min_trades': new_strategy_perf['n_trades'] >= min_trades,
        'max_drawdown': new_strategy_perf['max_drawdown'] < 0.10
    }

    all_met = all(criteria.values())

    if all_met:
        # Escalar innovación
        new_allocation = innovation_allocation * 2  # Duplicar
        action = 'scale_innovation'

    elif new_strategy_perf['total_return'] < -0.05:
        # Perdiendo dinero → eliminar
        new_allocation = 0
        action = 'kill_innovation'

    else:
        # Mantener evaluación
        new_allocation = innovation_allocation
        action = 'continue_monitoring'

    logger.info(
        f"Innovation risk: {new_strategy}, "
        f"action={action}, "
        f"allocation={innovation_allocation:.1%} → {new_allocation:.1%}"
    )

    return {
        'action': action,
        'new_allocation': new_allocation,
        'proven_allocation': 1 - new_allocation,
        'criteria_met': criteria,
        'performance': new_strategy_perf
    }
```

### Regla 6 — Environmental Context Integration

Incluir datos macro (tipos) para Forex y on-chain para Cripto.

```python
def multi_asset_context_features(
    self,
    asset_class: str,
    current_features: dict
) -> dict:
    """
    Añadir contexto específico del asset class.

    Lo: Contexto ambiental = mejor predicción de régimen.
    """
    enhanced_features = current_features.copy()

    if asset_class == 'FOREX':
        # Contexto macro para FX
        enhanced_features.update({
            'interest_rate_differential': self.get_rate_differential(),
            'cpi_expectation': self.get_cpi_forecast(),
            'gdp_growth': self.get_gdp_forecast(),
            'central_bank_stance': self.central_bank_policy(),  # Hawkish/Dovish
            'safe_haven_demand': self.get_safe_haven_flow()
        })

    elif asset_class == 'CRYPTO':
        # Contexto on-chain para crypto
        enhanced_features.update({
            'active_addresses': self.get_active_addresses(),
            'exchange_inflows': self.get_exchange_inflows(),
            'whale_transactions': self.get_whale_activity(),
            'hash_rate': self.get_network_hash_rate(),
            'mvrvm_ratio': self.get_mvrvm_ratio(),
            'funding_rates': self.get_funding_rates()
        })

    elif asset_class == 'STOCKS':
        # Contexto de mercado accionario
        enhanced_features.update({
            'vix_level': self.get_vix(),
            'put_call_ratio': self.get_put_call_ratio(),
            'insider_trading': self.get_insider_activity(),
            'earnings_season': self.is_earnings_season(),
            'index_benchmark': self.get_relative_performance()
        })

    logger.debug(
        f"Context features added: {asset_class}, "
        f"n_features={len(enhanced_features)}"
    )

    return enhanced_features
```

### Regla 7 — Survival Bias Prevention

No confiar en estrategias que solo funcionan en mercados alcistas.

```python
def survival_bias_check(
    self,
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series
) -> dict:
    """
    Detectar sesgo de supervivencia (solo funciona en bull markets).

    Lo: Estrategia debe funcionar en TODOS los regímenes.
    """
    # Calcular retornos por régimen
    bull_mask = benchmark_returns > 0
    bear_mask = benchmark_returns < 0

    strategy_bull = strategy_returns[bull_mask]
    strategy_bear = strategy_returns[bear_mask]

    # Métricas por régimen
    bull_return = strategy_bull.mean()
    bear_return = strategy_bear.mean()

    bull_sharpe = strategy_bull.mean() / strategy_bull.std()
    bear_sharpe = strategy_bear.mean() / strategy_bear.std()

    # Ratio de desempeño bear/bull
    regime_ratio = abs(bear_sharpe) / (bull_sharpe + 1e-8)

    # Detección de sesgo
    if bull_sharpe > 1.0 and bear_sharpe < -0.5:
        has_survival_bias = True
        assessment = 'BULL_ONLY'
        recommendation = 'NEEDS_HEDGE'

    elif regime_ratio > 0.5:
        has_survival_bias = False
        assessment = 'BALANCED'
        recommendation = 'GOOD'

    else:
        has_survival_bias = False
        assessment = 'WEAK_IN_BEAR'
        recommendation = 'IMPROVE_BEAR_PERFORMANCE'

    logger.info(
        f"Survival bias check: {assessment}, "
        f"bull_sharpe={bull_sharpe:.2f}, bear_sharpe={bear_sharpe:.2f}, "
        f"regime_ratio={regime_ratio:.2f}"
    )

    return {
        'has_survival_bias': has_survival_bias,
        'assessment': assessment,
        'recommendation': recommendation,
        'bull_sharpe': bull_sharpe,
        'bear_sharpe': bear_sharpe,
        'regime_ratio': regime_ratio
    }
```

### Regla 8 — Learning Speed Adjustment

Aumentar velocidad de aprendizaje durante crisis financieras.

```python
def adaptive_learning_rate(
    self,
    market_stress_level: float,  # 0 to 1
    base_lr: float = 0.001,
    max_lr_multiplier: float = 10.0
) -> dict:
    """
    Ajustar learning rate según estrés del mercado.

    Lo: Crisis = aprender más rápido.
    """
    # Learning rate adaptativo
    lr_multiplier = 1 + market_stress_level * (max_lr_multiplier - 1)

    adaptive_lr = base_lr * lr_multiplier

    # También ajustar其他 hyperparámetros
    batch_size_reduction = int(32 * (1 - market_stress_level * 0.5))
    lookback_reduction = int(252 * (1 - market_stress_level * 0.7))

    logger.info(
        f"Adaptive learning: stress={market_stress_level:.2f}, "
        f"lr={adaptive_lr:.4f} (×{lr_multiplier:.1f}), "
        f"batch={batch_size_reduction}, lookback={lookback_reduction}"
    )

    return {
        'learning_rate': adaptive_lr,
        'batch_size': max(16, batch_size_reduction),
        'lookback_period': max(50, lookback_reduction),
        'stress_level': market_stress_level
    }
```

### Regla 9 — Efficiency Gap Detection

Buscar ineficiencias en mercados menos maduros y arbitrar con maduros.

```python
def cross_market_efficiency_arbitrage(
    self,
    mature_market: str,  # e.g., SPY
    emerging_market: str  # e.g., BTC
) -> dict:
    """
    Detectar ineficiencias entre mercados maduros y emergentes.

    Lo: Mercados emergentes = ineficiencias explotables.
    """
    # Medir eficiencia (proxy: autocorrelación de retornos)
    mature_returns = self.get_returns(mature_market, days=60)
    emerging_returns = self.get_returns(emerging_market, days=60)

    from statsmodels.tsa.stattools import acf

    mature_acf = abs(acf(mature_returns, nlags=5)[1:]).max()
    emerging_acf = abs(acf(emerging_returns, nlags=5)[1:]).max()

    # Gap de eficiencia
    efficiency_gap = emerging_acf - mature_acf

    if efficiency_gap > 0.1:  # Ineficiencia significativa
        opportunity = True

        # Estrategia: arbitrar ineficiencia
        if emerging_acf > 0:  # Momentum
            strategy = 'momentum_arbitrage'
            direction = 'follow_trend'

        else:  # Mean reversion
            strategy = 'reversion_arbitrage'
            direction = 'fade_moves'

    else:
        opportunity = False
        strategy = None
        direction = None

    logger.info(
        f"Efficiency gap: {mature_market} vs {emerging_market}, "
        f"gap={efficiency_gap:.3f}, opportunity={opportunity}"
    )

    return {
        'opportunity': opportunity,
        'strategy': strategy,
        'direction': direction,
        'efficiency_gap': efficiency_gap,
        'mature_acf': mature_acf,
        'emerging_acf': emerging_acf
    }
```

### Regla 10 — Adaptive Stop-Loss

Stop estrecho en mercados eficientes, amplio en ruidosos.

```python
def adaptive_stop_loss(
    self,
    entry_price: float,
    current_price: float,
    market_efficiency: float,  # 0 to 1
    position_side: str = 'long'
) -> dict:
    """
    Stop-loss adaptativo según eficiencia del mercado.

    Lo: Mercados eficientes = stops ajustados, ruidosos = amplios.
    """
    # Base stop en %
    base_stop = 0.02  # 2%

    # Ajustar según eficiencia
    # Alta eficiencia → stop más estrecho
    # Baja eficiencia → stop más amplio

    if market_efficiency > 0.7:
        stop_multiplier = 0.5  # Más estrecho
        stop_type = 'tight'

    elif market_efficiency < 0.3:
        stop_multiplier = 2.0  # Más amplio
        stop_type = 'wide'

    else:
        stop_multiplier = 1.0
        stop_type = 'normal'

    stop_distance = base_stop * stop_multiplier

    if position_side == 'long':
        stop_price = entry_price * (1 - stop_distance)
    else:
        stop_price = entry_price * (1 + stop_distance)

    # Trailing stop adjustment
    if position_side == 'long' and current_price > entry_price:
        unrealized_pnl = (current_price - entry_price) / entry_price

        # Mover stop a break-even si ganancia > stop_distance
        if unrealized_pnl > stop_distance:
            stop_price = max(stop_price, entry_price)

    logger.info(
        f"Adaptive SL: {stop_type}, eff={market_efficiency:.2f}, "
        f"stop={stop_price:.2f} ({stop_distance:.2%} from {entry_price:.2f})"
    )

    return {
        'stop_price': stop_price,
        'stop_distance_pct': stop_distance,
        'stop_type': stop_type,
        'efficiency': market_efficiency
    }
```

### Regla 11 — Behavioral Panic Detection

Detectar patrones de "pánico" (velas rojas masivas) y ejecutar estrategias de liquidez.

```python
def behavioral_panic_detection(
    self,
    recent_candles: pd.DataFrame,
    volume_spike_threshold: float = 2.0
) -> dict:
    """
    Detectar pánico del mercado.

    Lo: Pánico = oportunidad contraria o riesgo sistémico.
    """
    # Análisis de velas recientes
    n_red_candles = sum(recent_candles['close'] < recent_candles['open'])

    # Volumen
    avg_volume = recent_candles['volume'].rolling(20).mean().iloc[-1]
    current_volume = recent_candles['volume'].iloc[-1]
    volume_ratio = current_volume / avg_volume

    # Rango de velas (volatilidad)
    avg_range = (recent_candles['high'] - recent_candles['low']).rolling(20).mean().iloc[-1]
    current_range = recent_candles['high'].iloc[-1] - recent_candles['low'].iloc[-1]
    range_ratio = current_range / avg_range

    # Indicadores de pánico
    panic_indicators = {
        'consecutive_red': n_red_candles >= 3,
        'volume_spike': volume_ratio > volume_spike_threshold,
        'range_expansion': range_ratio > 1.5
    }

    n_indicators = sum(panic_indicators.values())

    if n_indicators >= 3:
        panic_level = 'EXTREME'
        action = 'emergency_liquidity'
        position_adjustment = -0.5  # Reducir 50%

    elif n_indicators >= 2:
        panic_level = 'HIGH'
        action = 'reduce_exposure'
        position_adjustment = -0.3

    elif n_indicators >= 1:
        panic_level = 'MODERATE'
        action = 'prepare_exit'
        position_adjustment = 0

    else:
        panic_level = 'NORMAL'
        action = 'maintain'
        position_adjustment = 0

    logger.warning(
        f"Panic detection: {panic_level} ({n_indicators}/3 indicators), "
        f"action={action}"
    )

    return {
        'panic_level': panic_level,
        'action': action,
        'position_adjustment': position_adjustment,
        'indicators': panic_indicators,
        'n_indicators': n_indicators
    }
```

### Regla 12 — History-Dependent Logic

El bot debe recordar cómo reaccionó el mercado a la última subida de tipos.

```python
def history_dependent_response(
    self,
    event_type: str,  # 'rate_hike', 'earnings', etc.
    lookback_events: int = 5
) -> dict:
    """
    Aprender de eventos históricos similares.

    Lo: Memoria del mercado = predicción mejor.
    """
    # Buscar eventos similares históricos
    historical_events = self.find_similar_events(
        event_type=event_type,
        n_events=lookback_events
    )

    if len(historical_events) == 0:
        return {
            'has_history': False,
            'recommendation': 'use_default_rules'
        }

    # Analizar reacción del mercado
    market_reactions = []

    for event in historical_events:
        # Retorno pre-evento (días antes)
        pre_return = self.get_return_around_event(
            event['date'],
            days_before=5,
            days_after=0
        )

        # Retorno post-evento
        post_return = self.get_return_around_event(
            event['date'],
            days_before=0,
            days_after=5
        )

        market_reactions.append({
            'date': event['date'],
            'pre_return': pre_return,
            'post_return': post_return,
            'volatility': event.get('volatility', 0)
        })

    # Patrones de reacción
    avg_post_return = np.mean([r['post_return'] for r in market_reactions])
    positive_outcomes = sum(1 for r in market_reactions if r['post_return'] > 0)

    if positive_outcomes >= lookback_events * 0.7:
        pattern = 'generally_positive'
        recommendation = 'position_for_positive_reaction'

    elif positive_outcomes <= lookback_events * 0.3:
        pattern = 'generally_negative'
        recommendation = 'position_for_negative_reaction'

    else:
        pattern = 'mixed'
        recommendation = 'wait_for_initial_reaction'

    logger.info(
        f"History-dependent: {event_type}, pattern={pattern}, "
        f"avg_post={avg_post_return:+.2%}"
    )

    return {
        'has_history': True,
        'pattern': pattern,
        'recommendation': recommendation,
        'avg_post_return': avg_post_return,
        'historical_reactions': market_reactions
    }
```

### Regla 13 — Dynamic Sizing

Reducir tamaño de posición si la estrategia ha fallado en los últimos 3 intentos.

```python
def dynamic_position_sizing(
    self,
    strategy: str,
    recent_trades: List[dict],
    base_size: float = 1.0,
    lookback_trades: int = 3
) -> dict:
    """
    Ajustar tamaño según desempeño reciente.

    Lo: Fracaso repetido = reducir exposición.
    """
    # Últimos N trades de esta estrategia
    strategy_trades = [
        t for t in recent_trades
        if t.get('strategy') == strategy
    ][-lookback_trades:]

    if len(strategy_trades) < lookback_trades:
        # No hay suficientes trades
        return {
            'size_multiplier': 1.0,
            'reason': 'insufficient_history'
        }

    # Contar fracasos
    n_losses = sum(1 for t in strategy_trades if t.get('pnl', 0) < 0)

    if n_losses == lookback_trades:
        # Todos los trades recientes perdieron
        multiplier = 0.5  # Reducir a 50%
        reason = 'recent_losses_all'

    elif n_losses >= lookback_trades * 0.7:
        # Mayoría perdieron
        multiplier = 0.7
        reason = 'recent_losses_majority'

    elif n_losses == 0:
        # Todos ganaron
        multiplier = 1.2  # Aumentar 20%
        reason = 'recent_wins_all'

    else:
        multiplier = 1.0
        reason = 'mixed_performance'

    adjusted_size = base_size * multiplier

    logger.info(
        f"Dynamic sizing: {strategy}, "
        f"losses={n_losses}/{lookback_trades}, "
        f"multiplier={multiplier:.1f}, size={adjusted_size:.2f}"
    )

    return {
        'adjusted_size': adjusted_size,
        'multiplier': multiplier,
        'reason': reason,
        'recent_losses': n_losses
    }
```

### Regla 14 — Complexity Penalty

Preferir reglas simples si el mercado se vuelve errático.

```python
def complexity_penalty(
    self,
    candidate_strategies: List[dict],
    market_regime: str
) -> dict:
    """
    Penalizar complejidad en mercados erráticos.

    Lo: Simplicidad = robustez en incertidumbre.
    """
    # Medir erraticidad del mercado
    market_choppiness = self.measure_choppiness()

    scored_strategies = []

    for strategy in candidate_strategies:
        # Complejidad de la estrategia
        complexity = strategy.get('complexity_score', 1.0)

        # Desempeño esperado
        expected_return = strategy.get('expected_return', 0)
        expected_risk = strategy.get('expected_risk', 0.1)

        # Penalty por complejidad
        if market_choppiness > 0.7:  # Mercado errático
            penalty_factor = 1 / (1 + complexity)

        else:
            penalty_factor = 1.0

        # Score ajustado
        sharpe = expected_return / expected_risk
        adjusted_score = sharpe * penalty_factor

        scored_strategies.append({
            'strategy': strategy,
            'original_score': sharpe,
            'adjusted_score': adjusted_score,
            'penalty_factor': penalty_factor,
            'complexity': complexity
        })

    # Seleccionar mejor ajustado
    best = max(scored_strategies, key=lambda x: x['adjusted_score'])

    logger.info(
        f"Complexity penalty: choppiness={market_choppiness:.2f}, "
        f"selected={best['strategy']['name']}, "
        f"penalty={best['penalty_factor']:.2f}"
    )

    return {
        'selected_strategy': best['strategy'],
        'adjusted_scores': scored_strategies,
        'choppiness': market_choppiness
    }
```

### Regla 15 — Meta-Strategy Obsolescence Monitoring

Un proceso externo debe auditar si el robot se ha quedado "obsoleto".

```python
def meta_strategy_obsolescence_check(
    self,
    strategy_performance: dict,
    benchmark_performance: dict
) -> dict:
    """
    Monitorear obsolescencia de la estrategia.

    Lo: Estrategias mueren; detectarlo a tiempo.
    """
    # Métricas de desempeño relativo
    strat_return = strategy_performance.get('total_return', 0)
    bench_return = benchmark_performance.get('total_return', 0)

    strat_sharpe = strategy_performance.get('sharpe', 0)
    bench_sharpe = benchmark_performance.get('sharpe', 0)

    strat_max_dd = strategy_performance.get('max_drawdown', 0)
    bench_max_dd = benchmark_performance.get('max_drawdown', 0)

    # Criterios de obsolescencia
    criteria = {
        'underperforming_benchmark': strat_return < bench_return - 0.05,  # -5%
        'negative_sharpe': strat_sharpe < 0,
        'excessive_drawdown': strat_max_dd > bench_max_dd + 0.10,  # +10%
        'declining_sharpe': strategy_performance.get('sharpe_trend', 0) < -0.1,
        'high_volatility_low_return': (
            strategy_performance.get('volatility', 0) > 0.2 and
            strat_return < 0.05
        )
    }

    n_failed = sum(criteria.values())

    if n_failed >= 4:
        status = 'OBSOLETE'
        action = 'retire_strategy'
        urgency = 'immediate'

    elif n_failed >= 2:
        status = 'DECLINING'
        action = 'review_and_retrain'
        urgency = 'moderate'

    elif n_failed >= 1:
        status = 'WARNING'
        action = 'monitor_closely'
        urgency = 'low'

    else:
        status = 'HEALTHY'
        action = 'continue'
        urgency = 'none'

    logger.info(
        f"Obsolescence check: {status}, "
        f"failed={n_failed}/5 criteria, {action}"
    )

    return {
        'status': status,
        'action': action,
        'urgency': urgency,
        'failed_criteria': [k for k, v in criteria.items() if v],
        'all_criteria': criteria
    }
```

---

## Aplicación Práctica

### Pipeline Completo Adaptive Markets

```python
def adaptive_markets_pipeline(
    self,
    current_market_data: dict,
    active_strategies: dict
) -> dict:
    """
    Pipeline completo de Adaptive Markets Hypothesis.
    """
    # 1. Detectar régimen
    regime_result = self.hmm_regime_detection(
        current_market_data['returns'],
        n_regimes=3
    )

    current_regime = regime_result['regime_info']['type']

    # 2. Seleccionar estrategias del pool
    strategy_selection = self.strategy_pool_manager(
        current_regime,
        active_strategies
    )

    # 3. Verificar obsolescencia de meta-estrategia
    obsolescence = self.meta_strategy_obsolescence_check(
        self.get_strategy_performance(),
        self.get_benchmark_performance()
    )

    if obsolescence['status'] == 'OBSOLETE':
        return {
            'action': 'STOP_TRADING',
            'reason': 'Strategy obsolete',
            'urgency': obolescence['urgency']
        }

    # 4. Ajustar parámetros según volatilidad
    vol_adjustment = self.volatility_strategy_switch(
        current_market_data['volatility'],
        current_market_data['baseline_volatility']
    )

    # 5. Detectar pánico comportamental
    panic = self.behavioral_panic_detection(
        current_market_data['recent_candles']
    )

    # 6. Ajustar tamaño dinámico
    for strategy in strategy_selection['active_strategies']:
        size = self.dynamic_position_sizing(
            strategy,
            self.get_recent_trades(),
            base_size=1.0
        )

    # 7. Decisión final
    if panic['panic_level'] == 'EXTREME':
        final_action = 'REDUCE_EXPOSURE'
        target_exposure = 0.5

    elif obsolescence['status'] == 'DECLINING':
        final_action = 'REDUCE_EXPOSURE'
        target_exposure = 0.7

    elif vol_adjustment['triggered']:
        final_action = 'APPLY_NEW_PARAMS'
        target_exposure = 1.0
        new_params = vol_adjustment['params']

    else:
        final_action = 'NORMAL_OPERATION'
        target_exposure = 1.0
        new_params = {}

    return {
        'action': final_action,
        'target_exposure': target_exposure,
        'regime': current_regime,
        'active_strategies': strategy_selection['active_strategies'],
        'new_params': new_params,
        'panic_level': panic['panic_level'],
        'obsolescence_status': obsolescence['status']
    }
```
