# 📕 10. "Systematic Trading" - Robert Carver

## REGLAS DE TRADING SISTEMÁTICO

**Regla 10.1 — Riesgo dominante**

Claude DEBE calcular tamaño de posición DESPUÉS de la señal.

**Target de volatilidad fijo.**

**Señales sin sizing → incompletas.**

```python
def size_position(
    signal: float,
    current_price: float,
    account_value: float,
    target_volatility: float = 0.15,  # 15% anual
    current_volatility: float = None,
    max_position_size: float = 0.20  # Max 20% por posición
) -> float:
    """
    Volatility Targeting: Ajustar tamaño para alcanzar volatilidad objetivo.

    Señal × (vol_target / vol_actual) = tamaño
    """
    # Default volatility si no se especifica
    if current_volatility is None:
        current_volatility = 0.20  # 20% anual (assumption)

    # Escalar señal por volatilidad
    vol_scalar = target_volatility / max(current_volatility, 0.01)  # Min 1%

    # Calcular position size (en unidades de account value)
    position_weight = signal * vol_scalar

    # Limitar a max position size
    position_weight = max(min(position_weight, max_position_size), -max_position_size)

    # Convertir a valor monetario
    position_value = account_value * position_weight

    # Calcular número de shares/contracts
    n_shares = int(position_value / current_price)

    return n_shares
```

**Regla 10.2 — Instrument Diversification: No sobre-concentres**

```python
def validate_instrument_diversification(
    self,
    positions: Dict[str, float],
    max_concentration: float = 0.25
) -> bool:
    """
    Verificar que no estás sobre-concentrado en pocos instrumentos.

    Max 25% en cualquier instrumento individual.
    """
    total_value = sum(abs(pos) for pos in positions.values())

    for instrument, value in positions.items():
        concentration = abs(value) / total_value

        if concentration > max_concentration:
            logger.error(
                f"❌ Over-concentrated: {instrument} = {concentration:.0%} "
                f">(max: {max_concentration:.0%})"
            )
            return False

    return True
```

**Regla 10.3 — Trading Rules: Use simple, robust rules**

```python
def simple_momentum_signal(
    prices: pd.Series,
    lookback_days: int = 90,
    long_threshold: float = 0.0,
    short_threshold: float = 0.0
) -> float:
    """
    Momentum simple: Return sobre últimos N días.

    Carver prefiere reglas simples con pocos parámetros.
    """
    # Return sobre lookback period
    momentum = prices.iloc[-1] / prices.iloc[-lookback_days] - 1

    # Normalizar a [-1, 1]
    # Pero Carver no usa normalización, usa raw returns
    if momentum > long_threshold:
        return momentum  # Señal positiva
    elif momentum < short_threshold:
        return momentum  # Señal negativa
    else:
        return 0.0  # Neutral
```

**Regla 10.4 — Fixed Timestamp Trading: No intraday timing**

```python
def fixed_timestamp_execution(
    self,
    signals: pd.Series,
    execution_time: str = "15:00"  # 3:00 PM
) -> pd.Series:
    """
    Ejecutar siempre a la misma hora del día.

    Ventajas:
    - No issues con intraday data quality
    - Más fácil backtesting
    - Menor transaction cost (más tiempo para execution)
    """
    # Filtrar datos a hora específica
    daily_data = signals.between_time(execution_time, execution_time)

    return daily_data
```

**Regla 10.5 — Handcrafting: No data mining**

```python
def handcrafted_signal(
    self,
    data: pd.DataFrame
) -> float:
    """
    Señal diseñada manualmente, no descubierta por data mining.

    Carver: "No busques patterns en datos, diseña basado en teoría económica."
    """
    # Ejemplo: Carry trade
    # https://www.investopedia.com/terms/c/carrytrade.asp

    # 1. Calcular interest rate differential
    domestic_rate = data['interest_rate_domestic'].iloc[-1]
    foreign_rate = data['interest_rate_foreign'].iloc[-1]

    # 2. Calcular forward premium
    spot = data['fx_spot'].iloc[-1]
    forward = data['fx_forward'].iloc[-1]

    forward_premium = (forward - spot) / spot

    # 3. Carry = interest differential - forward premium
    carry = (foreign_rate - domestic_rate) - forward_premium

    # Señal basada en teoría económica
    return carry
```

**Regla 10.6 —衰减因子 (Decay Factor) para patrones estacionales**

```python
def apply_decay_factor(
    self,
    returns: pd.Series,
    decay_factor: float = 0.94
) -> pd.Series:
    """
    Aplicar decay factor para dar más peso a datos recientes.

    EWM (Exponentially Weighted Moving) usa decay automáticamente.
    """
    # Pandas ewm usa span, no alpha directo
    # span = 2 / (1 - alpha) - 1
    # alpha = decay_factor

    span = 2 / (1 - decay_factor) - 1

    return returns.ewm(span=span, adjust=False).mean()
```

**Regla 10.7 — Portfolio Optimization: Use Handcrafted weights**

```python
def handcrafted_portfolio_weights(
    self,
    n_assets: int
) -> np.array:
    """
    Pesos handcrafting, no optimizado.

    Carver: "Equal weight es difícil de beat."
    """
    # Equal weight
    weights = np.ones(n_assets) / n_assets

    return weights

def risk_parity_weights(
    self,
    returns: pd.DataFrame
) -> np.array:
    """
    Risk Parity: Cada asset contribuye igualmente al riesgo total.

    Más robusto que mean-variance optimization.
    """
    # 1. Calcular matriz de covarianza
    cov_matrix = returns.cov()

    # 2. Inversa de volatilidad
    volatilities = np.sqrt(np.diag(cov_matrix))
    inv_vol = 1 / volatilities

    # 3. Pesos proporcinales a inversa de volatilidad
    weights = inv_vol / inv_vol.sum()

    return weights
```

**Regla 10.8 — Trading Costs: Include en TODOS los cálculos**

```python
def calculate_trading_costs(
    self,
    trades: List[Trade],
    account_value: float
) -> Dict[str, float]:
    """
    Carver: Trading costs son el enemigo #1 de estrategias sistemáticas.

    Si no incluyes costs, backtest es optimista irreal.
    """
    # 1. Commission (por trade)
    total_commission = sum(t.commission for t in trades)

    # 2. Spread cost (implícito en execution price)
    total_spread_cost = sum(
        (t.execution_price - t.mid_price) * t.quantity
        for t in trades
    )

    # 3. Slippage (diferencia entre desired y actual execution)
    total_slippage = sum(t.slippage_cost for t in trades)

    # 4. Market impact (para órdenes grandes)
    total_market_impact = sum(t.market_impact for t in trades)

    total_cost = total_commission + total_spread_cost + total_slippage + total_market_impact

    # Como % de account value
    cost_ratio = total_cost / account_value

    return {
        'total_cost': total_cost,
        'commission': total_commission,
        'spread_cost': total_spread_cost,
        'slippage': total_slippage,
        'market_impact': total_market_impact,
        'cost_ratio': cost_ratio
    }
```

**Regla 10.9 — Backtesting: Use out-of-sample data**

```python
def walk_forward_validation(
    self,
    strategy: Strategy,
    data: pd.DataFrame,
    train_size: int = 252 * 5,  # 5 años de training
    test_size: int = 252,      # 1 año de testing
    step_size: int = 63         # Recalibrar cada 3 meses
) -> pd.DataFrame:
    """
    Walk-forward validation: Simula trading real.

    No usar datos futuros para optimizar.
    """
    results = []

    for start_idx in range(0, len(data) - train_size - test_size, step_size):
        train_data = data.iloc[start_idx:start_idx + train_size]
        test_data = data.iloc[start_idx + train_size:start_idx + train_size + test_size]

        # Optimizar en training data
        strategy.optimize(train_data)

        # Test en out-of-sample data
        test_result = strategy.backtest(test_data)
        results.append(test_result)

    results_df = pd.DataFrame(results)

    # Calcular métricas aggregate
    avg_sharpe = results_df['sharpe'].mean()
    std_sharpe = results_df['sharpe'].std()

    logger.info(f"Walk-forward Sharpe: {avg_sharpe:.2f} ± {std_sharpe:.2f}")

    return results_df
```

**Regla 10.10 — Regla Final: Robustez > Performance**

```python
def prioritize_robustness(
    self,
    strategies: List[Strategy]
) -> Strategy:
    """
    Elegir estrategia basada en robustez, no solo performance.

    Métricas de robustez:
    - Consistencia across markets
    - Baja sensitivity a parámetros
    - Buen performance en stress periods
    """
    robust_scores = []

    for strategy in strategies:
        # 1. Cross-market consistency
        market_sharpes = [
            strategy.backtest(market_data)['sharpe']
            for market_data in self.get_multiple_markets()
        ]
        market_consistency = np.std(market_sharpes)  # Lower = better

        # 2. Parameter sensitivity
        param_variations = strategy.test_parameter_sensitivity()
        param_sensitivity = np.std([
            v['sharpe'] for v in param_variations.values()
        ])  # Lower = better

        # 3. Stress period performance
        stress_sharpe = strategy.backtest(self.get_stress_period_data())['sharpe']

        # Composite robustness score
        robust_score = (
            (1 / market_consistency) * 0.3 +
            (1 / param_sensitivity) * 0.3 +
            stress_sharpe * 0.4
        )

        robust_scores.append({
            'strategy': strategy,
            'robust_score': robust_score,
            'market_consistency': market_consistency,
            'param_sensitivity': param_sensitivity,
            'stress_sharpe': stress_sharpe
        })

    # Elegir estrategia con mejor robustness score
    best = max(robust_scores, key=lambda x: x['robust_score'])

    logger.info(
        f"Selected strategy: {best['strategy'].name} "
        f"(robust_score: {best['robust_score']:.2f})"
    )

    return best['strategy']
```
