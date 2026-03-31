# 📕 11. "Quantitative Momentum" - Gray & Vogel

## REGLAS DE MOMENTUM CUANTITATIVO

**Regla 11.1 — Momentum robusto**

Claude DEBE:
- usar varias ventanas
- normalizar retornos

**Momentum simple de 1 ventana → insuficiente.**

```python
def robust_momentum_signal(
    self,
    prices: pd.Series,
    lookback_windows: List[int] = [21, 63, 126, 252]  # 1m, 3m, 6m, 12m
) -> float:
    """
    Momentum combinado de múltiples ventanas.

    Gray & Vogel: Single-window momentum es frágil.
    """
    signals = []

    for window in lookback_windows:
        if len(prices) < window + 20:
            continue

        # Return sobre ventana
        momentum = prices.iloc[-1] / prices.iloc[-window] - 1

        # Normalizar por volatilidad de la ventana
        returns = prices.pct_change()
        volatility = returns.iloc[-window:].std()

        # Volatility-adjusted momentum
        if volatility > 0:
            vol_adj_momentum = momentum / volatility
            signals.append(vol_adj_momentum)

    if not signals:
        return 0.0

    # Promedio de señales (ensemble simple)
    combined_signal = np.mean(signals)

    # Normalizar a [-1, 1]
    signal = np.tanh(combined_signal * 10)

    return signal
```

**Regla 11.2 — Skip-month para evitar reversión a corto plazo**

```python
def skip_month_momentum(
    self,
    prices: pd.Series,
    lookback_months: int = 12,
    skip_months: int = 1
) -> float:
    """
    Momentum excluyendo último mes (skip-month).

    Gray & Vogel: Momentum a 12 meses excluyendo último mes
    es más robusto que including el último mes.
    """
    if len(prices) < (lookback_months + skip_months) * 21:
        return 0.0

    # Precio hace skip_months meses
    skip_price = prices.iloc[-(skip_months + 1) * 21]

    # Precio hace lookback_months meses
    lookback_price = prices.iloc[-(lookback_months + skip_months) * 21]

    # Momentum sin último mes
    momentum = (skip_price - lookback_price) / lookback_price

    return momentum
```

**Regla 11.3 — Quality screening para momentum**

```python
def quality_screened_momentum(
    self,
    prices: pd.Series,
    fundamentals: pd.Series,  # e.g., ROE, earnings growth
    momentum: float
) -> float:
    """
    Momentum en empresas de calidad es más persistente.

    Gray & Vogel: Filtrar por calidad antes de momentum.
    """
    # Quality metrics
    # 1. Return on Equity (ROE)
    roe = fundamentals.get('roe', 0)

    # 2. Earnings stability
    earnings_stability = fundamentals.get('earnings_stability', 0)

    # Quality score
    quality_score = (
        (roe > 0.15) * 0.5 +
        (earnings_stability > 0.7) * 0.5
    )

    # Solo momentum si calidad es aceptable
    if quality_score < 0.5:
        return 0.0

    # Ajustar señal por calidad
    return momentum * quality_score
```

**Regla 11.4 — Risk-adjusted momentum**

```python
def risk_adjusted_momentum(
    self,
    prices: pd.Series,
    lookback_days: int = 252
) -> float:
    """
    Information Ratio = Momentum / Volatilidad.

    Gray & Vogel: Prefiero high momentum con baja volatilidad.
    """
    if len(prices) < lookback_days:
        return 0.0

    # Calcular retornos diarios
    returns = prices.pct_change().iloc[-lookback_days:]

    # Momentum total
    total_return = (prices.iloc[-1] / prices.iloc[-lookback_days] - 1)

    # Volatilidad annualizada
    volatility = returns.std() * np.sqrt(252)

    # Information Ratio (Sharpe sin risk-free)
    if volatility == 0:
        return 0.0

    ir = total_return / volatility

    # Signal based on IR
    return np.tanh(ir * 2)
```

**Regla 11.5 — Momentum residual (market-neutral)**

```python
def residual_momentum(
    self,
    prices: pd.Series,
    market_prices: pd.Series,
    lookback_days: int = 252
) -> float:
    """
    Momentum residual = momentum stock - beta * momentum market.

    Gray & Vogel: Residual momentum es más robusto que raw momentum.
    """
    if len(prices) < lookback_days or len(market_prices) < lookback_days:
        return 0.0

    # Calcular betas usando regresión
    stock_returns = prices.pct_change().iloc[-lookback_days:]
    market_returns = market_prices.pct_change().iloc[-lookback_days:]

    # Regression: stock = alpha + beta * market
    from sklearn.linear_model import LinearRegression

    X = market_returns.values.reshape(-1, 1)
    y = stock_returns.values

    model = LinearRegression()
    model.fit(X, y)

    beta = model.coef_[0]

    # Raw momentum
    stock_momentum = stock_returns.sum()
    market_momentum = market_returns.sum()

    # Residual momentum
    residual = stock_momentum - beta * market_momentum

    return residual
```

**Regla 11.6 — Sector-relative momentum**

```python
def sector_relative_momentum(
    self,
    stock_prices: pd.Series,
    sector_prices: pd.Series,
    lookback_days: int = 63
) -> float:
    """
    Momentum relativo al sector.

    Gray & Vogel: Stock que gana a su sector → señal más fuerte.
    """
    if len(stock_prices) < lookback_days or len(sector_prices) < lookback_days:
        return 0.0

    # Momentum stock
    stock_mom = (stock_prices.iloc[-1] / stock_prices.iloc[-lookback_days] - 1)

    # Momentum sector
    sector_mom = (sector_prices.iloc[-1] / sector_prices.iloc[-lookback_days] - 1)

    # Relative momentum
    relative = stock_mom - sector_mom

    return relative
```

**Regla 11.7 — Diversificación de factores momentum**

```python
def diversify_momentum_factors(
    self,
    price_momentum: float,
    earnings_momentum: float,
    revision_momentum: float
) -> float:
    """
    Combina múltiples factores de momentum.

    Gray & Vogel: Price momentum + Earnings momentum + Analyst revision.
    """
    # Normalizar cada factor
    factors = {
        'price': price_momentum,
        'earnings': earnings_momentum,
        'revision': revision_momentum
    }

    # Equal weight
    weights = {
        'price': 0.4,
        'earnings': 0.3,
        'revision': 0.3
    }

    combined = sum(
        weights[k] * np.tanh(factors[k] * 3)
        for k in factors
    )

    return combined
```

**Regla 11.8 — Rebalancing mensual para momentum**

```python
def should_rebalance_momentum(
    self,
    last_rebalance: datetime,
    frequency: str = "MONTHLY"
) -> bool:
    """
    Momentum portfolios se rebalancean mensualmente.

    Gray & Vogel: Rebalanceo más frecuente = high transaction costs.
    """
    if frequency == "MONTHLY":
        # Primera oportunidad del mes
        if last_rebalance.month != datetime.now().month:
            return True

    elif frequency == "QUARTERLY":
        current_quarter = (datetime.now().month - 1) // 3 + 1
        last_quarter = (last_rebalance.month - 1) // 3 + 1

        if current_quarter != last_quarter:
            return True

    return False
```

**Regla 11.9 — Position sizing por ranking momentum**

```python
def momentum_rank_sizing(
    self,
    momentum_scores: pd.Series,
    n_positions: int = 50
) -> pd.Series:
    """
    Posicionar en top N momentum stocks.

    Gray & Vogel: Equal-weight en top momentum.
    """
    # Ranking por momentum score
    ranked = momentum_scores.rank(ascending=False)

    # Top N
    top_n = ranked[ranked <= n_positions]

    # Equal weight
    weights = pd.Series(0.0, index=momentum_scores.index)
    weights[top_n.index] = 1.0 / n_positions

    return weights
```

**Regla 11.10 — Crash risk adjustment para momentum**

```python
def crash_risk_adjusted_momentum(
    self,
    momentum: float,
    volatility: float,
    skewness: float,
    max_skew_penalty: float = 0.3
) -> float:
    """
    Momentum con crash risk (skewness negativa) penalizado.

    Gray & Vogel: Momentum en high-skewness stocks es más riesgoso.
    """
    # Penalización por skewness negativa
    if skewness < -0.5:
        skew_penalty = min(abs(skew_penalty), max_skew_penalty)
    else:
        skew_penalty = 0.0

    # Ajustar momentum
    adjusted = momentum * (1 - skew_penalty)

    return adjusted
```
