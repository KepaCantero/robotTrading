# 📗 7. "Market Microstructure Theory" - Maureen O'Hara

## REGLAS DE MICROESTRUCTURA DE MERCADO

**Regla 7.1 — Liquidez primero**

Claude DEBE comprobar antes de operar:
- volumen medio diario (ADV)
- bid/ask spread
- profundidad de mercado

```python
def check_liquidity(symbol: str) -> bool:
    adv = get_average_daily_volume(symbol)
    spread = get_bid_ask_spread(symbol)

    if adv < MIN_VOLUME_THRESHOLD:
        return False  # Liquidez insuficiente

    if spread > MAX_SPREAD_THRESHOLD:
        return False  # Spread demasiado amplio

    return True
```

**Regla 7.2 — Adverse Selection: Evita trading contra informados**

```python
def detect_adverse_selection(
    self,
    symbol: str,
    fills: List[Fill],
    window_minutes: int = 30
) -> bool:
    """
    Adverse selection: Estás perdiendo contra traders mejor informados.

    Síntomas:
    - Price se mueve en tu contra DESPUÉS de tu fill
    - Tus fills son en el "worst" lado del spread consistentemente
    """
    if len(fills) < 10:
        return False

    # Para cada fill, medir price movement 5-30 min después
    adverse_moves = 0

    for fill in fills:
        subsequent_price = self.get_future_price(
            symbol,
            fill.timestamp + timedelta(minutes=window_minutes)
        )

        if fill.side == "BUY":
            # Compraste, precio bajó → adverse selection
            if subsequent_price < fill.price:
                adverse_moves += 1
        else:
            # Vendiste, precio subió → adverse selection
            if subsequent_price > fill.price:
                adverse_moves += 1

    adverse_rate = adverse_moves / len(fills)

    if adverse_rate > 0.60:  # >60% de tus fills son malos
        logger.warning(
            f"⚠️ High adverse selection: {adverse_rate:.0%} - "
            "You're being picked off"
        )
        return True

    return False
```

**Regla 7.3 — Order Flow Toxicity: Mide calidad de contraparte**

```python
def calculate_order_toxicity(
    self,
    trades: List[Trade],
    mid_prices: pd.Series
) -> float:
    """
    Order Flow Toxicity = ¿El flujo de órdenes es "tóxico"?

    Flujo tóxico: Trades que indican información privada (adverse selection).
    """
    if len(trades) < 20:
        return 0.0

    toxic_trades = []

    for trade in trades:
        # Obtener mid-price en timestamp del trade
        mid = mid_prices.loc[trade.timestamp]

        # Trade fue en el "wrong" lado del mid?
        # BUY @ ask > mid, SELL @ bid < mid
        if trade.side == "BUY" and trade.price > mid:
            # Compraste por encima del mid → overpaid
            toxicity = (trade.price - mid) / mid
            toxic_trades.append(toxicity)
        elif trade.side == "SELL" and trade.price < mid:
            # Vendiste por debajo del mid → oversold
            toxicity = (mid - trade.price) / mid
            toxic_trades.append(toxicity)

    if not toxic_trades:
        return 0.0

    # Toxicity promedio
    avg_toxicity = np.mean(toxic_trades)

    if avg_toxicity > 0.001:  # >10 bps de toxicity promedio
        logger.warning(
            f"⚠️ High order flow toxicity: {avg_toxicity:.4%} - "
            "Reduce trading frequency"
        )

    return avg_toxicity
```

**Regla 7.4 — Market Impact es asimétrico**

```python
def asymmetric_market_impact(
    self,
    order_size: Decimal,
    adv: Decimal,
    volatility: float,
    side: str
) -> Decimal:
    """
    Market impact es diferente para BUY vs SELL.

    BUY orders típicamente tienen MÁS impact que SELL orders.
    """
    participation = float(order_size / adv)

    # Base impact (Almgren-Chriss)
    base_impact = 0.1 * volatility * np.sqrt(participation)

    # Asymmetry factor (empírico)
    # Buys: 1.2x impact, Sells: 0.8x impact
    if side == "BUY":
        asymmetry_multiplier = 1.2
    else:
        asymmetry_multiplier = 0.8

    adjusted_impact = base_impact * asymmetry_multiplier

    return Decimal(str(adjusted_impact))
```

**Regla 7.5 — Latencia matters: Tiempo entre señal y ejecución**

```python
def model_execution_latency(
    self,
    signal_time: datetime,
    execution_time: datetime,
    symbol: str
) -> Decimal:
    """
    Latency = opportunity cost.

    Entre señal y ejecución, el precio puede moverse en tu contra.
    """
    delay_ms = (execution_time - signal_time).total_seconds() * 1000

    # Latency típica por execution type
    latency_benchmarks = {
        "MARKET": 10,      # 10 ms
        "LIMIT": 100,      # 100 ms
        "VWAP": 1000,      # 1 segundo
        "TWAP": 1000,      # 1 segundo
    }

    # Simular price movement durante delay
    volatility_per_ms = self.get_volatility(symbol) / np.sqrt(252 * 6.5 * 3600 * 1000)

    # Price movement esperado durante delay
    expected_move = volatility_per_ms * delay_ms

    # Latency cost = adverse move esperado
    # Asumimos 50% chance de moves en tu contra
    latency_cost = expected_move * 0.5

    return Decimal(str(latency_cost))
```

**Regla 7.6 — Spread es información, no solo costo**

```python
def interpret_spread_signal(
    self,
    symbol: str,
    current_spread: Decimal,
    historical_spreads: pd.Series
) -> Dict[str, any]:
    """
    Spread changes contienen información.

    Spread widening = uncertainty aumentando = NO operar.
    Spread narrowing = confianza aumentando = OK operar.
    """
    # 1. Comparar con spread histórico (percentile)
    spread_percentile = (current_spread < historical_spreads).sum() / len(historical_spreads)

    # 2. Spread regime
    if spread_percentile > 0.90:
        regime = "EXTREME_WIDENING"
        action = "HALT_TRADING"
    elif spread_percentile > 0.75:
        regime = "WIDENING"
        action = "REDUCE_SIZE"
    elif spread_percentile < 0.25:
        regime = "NARROWING"
        action = "NORMAL"
    else:
        regime = "NORMAL"
        action = "NORMAL"

    # 3. Verificar si spread change es statistically significant
    z_score = (current_spread - historical_spreads.mean()) / historical_spreads.std()

    return {
        'regime': regime,
        'action': action,
        'percentile': spread_percentile,
        'z_score': z_score
    }
```

**Regla 7.7 — Depth matters más que top-of-book**

```python
def analyze_book_depth(
    self,
    symbol: str,
    levels: int = 10
) -> Dict[str, any]:
    """
    Top-of-book (bid/ask) no cuenta la historia completa.

    Profundidad del book indica liquidez REAL disponible.
    """
    book = self.get_order_book(symbol, levels=levels)

    # 1. Cumulative depth en cada nivel
    bid_depth_cumulative = np.cumsum(book['bid_sizes'])
    ask_depth_cumulative = np.cumsum(book['ask_sizes'])

    # 2. Depth slope: ¿Qué tan rápido aumenta profundidad?
    bid_slope = np.diff(bid_depth_cumulative)
    ask_slope = np.diff(ask_depth_cumulative)

    # 3. Depth imbalance
    total_bid_depth = bid_depth_cumulative[-1]
    total_ask_depth = ask_depth_cumulative[-1]
    depth_imbalance = (total_bid_depth - total_ask_depth) / (total_bid_depth + total_ask_depth)

    # 4. Liquidez check: ¿Puedes ejecutar tamaño X sin mover precio?
    target_size = Decimal("1000")

    def can_execute_at_or_better(size, side, levels, sizes, is_buy):
        remaining = size
        total_cost = Decimal("0")

        for i, (level, level_size) in enumerate(zip(levels, sizes)):
            fill = min(remaining, Decimal(str(level_size)))
            total_cost += Decimal(str(level)) * fill
            remaining -= fill

            if remaining == 0:
                avg_price = total_cost / size
                return True, avg_price

        return False, None

    can_buy, buy_price = can_execute_at_or_better(
        target_size, "BUY", book['ask'], book['ask_sizes'], True
    )
    can_sell, sell_price = can_execute_at_or_better(
        target_size, "SELL", book['bid'], book['bid_sizes'], False
    )

    return {
        'total_bid_depth': total_bid_depth,
        'total_ask_depth': total_ask_depth,
        'depth_imbalance': depth_imbalance,
        'can_buy_1000_at_avg': buy_price if can_buy else None,
        'can_sell_1000_at_avg': sell_price if can_sell else None
    }
```

**Regla 7.8 — Tick Size Constraint: Impacta liquidity**

```python
def evaluate_tick_size_regime(
    self,
    symbol: str,
    tick_size: Decimal
) -> Dict[str, any]:
    """
    Tick size muy grande = spreads amplios = menos liquidez.

    Tick size muy pequeño = too much granularity = market fragmentation.
    """
    # Obtener average spread en este tick size
    spreads = self.get_recent_spreads(symbol, days=20)
    avg_spread = spreads.mean()

    # Spread en ticks
    spread_in_ticks = avg_spread / tick_size

    # Evaluar régimen
    if spread_in_ticks < 1:
        regime = "SUB-TICK"
        implication = "Market makers compiten agresivamente"
    elif spread_in_ticks < 3:
        regime = "TIGHT"
        implication = "Buena liquidez"
    elif spread_in_ticks < 10:
        regime = "NORMAL"
        implication = "Liquidez adequate"
    else:
        regime = "WIDE"
        implication = "Poor liquidity"

    # También evaluar si tick size permite price discovery
    price_range = self.get_recent_price_range(symbol, days=5)
    n_price_levels = price_range / tick_size

    return {
        'regime': regime,
        'avg_spread_ticks': spread_in_ticks,
        'n_price_levels': n_price_levels,
        'implication': implication
    }
```

**Regla 7.9 — Market Quality Metrics**

```python
def calculate_market_quality_metrics(
    self,
    symbol: str
) -> Dict[str, float]:
    """
    Métricas de calidad de mercado.

    Útiles para decidir SI operar en este market.
    """
    # 1. Bid-ask spread (promedio 20 días)
    spreads = self.get_recent_spreads(symbol, days=20)
    avg_spread_bps = (spreads.mean() / self.get_mid_price(symbol)) * 10000

    # 2. Depth (promedio)
    order_books = [self.get_order_book(symbol, levels=5) for _ in range(100)]
    avg_depth = np.mean([sum(book['bid_sizes'] + book['ask_sizes']) for book in order_books])

    # 3. Volatility (realized)
    returns = self.get_recent_returns(symbol, days=20)
    realized_vol = returns.std() * np.sqrt(252)

    # 4. Trading activity
    avg_daily_volume = self.get_average_daily_volume(symbol)

    # 5. Price impact function (regresión)
    # impact ~ a * (size / ADV)^b
    impact_regression = self.estimate_market_impact_function(symbol)

    # Composite quality score (0-100)
    quality_score = (
        (1 / avg_spread_bps) * 20 +  # Spread más bajo = mejor
        (avg_depth / 1_000_000) * 20 +  # Depth más alto = mejor
        (1 / realized_vol) * 20 +  # Vol más baja = mejor
        min(avg_daily_volume / 1_000_000, 1) * 20 +  # Volume más alto = mejor
        (1 / impact_regression['slope']) * 20  # Impact más bajo = mejor
    )

    return {
        'avg_spread_bps': avg_spread_bps,
        'avg_depth': avg_depth,
        'realized_volatility': realized_vol,
        'avg_daily_volume': avg_daily_volume,
        'market_quality_score': min(quality_score, 100)
    }
```

**Regla 7.10 — Information-Driven Trades vs Noise Trades**

```python
def classify_trade_type(
    self,
    trade: Trade,
    order_book_snapshot: dict
) -> str:
    """
    Clasificar trades: ¿Informed o Noise?

    Informed traders: Trade en dirección de price movement futuro.
    Noise traders: Random, no predictive power.
    """
    # Obtener order flow antes del trade
    order_imbalance_before = (
        sum(order_book_snapshot['bid_sizes'][:5]) -
        sum(order_book_snapshot['ask_sizes'][:5])
    ) / (
        sum(order_book_snapshot['bid_sizes'][:5]) +
        sum(order_book_snapshot['ask_sizes'][:5])
    )

    # Trade fue consistent con order imbalance?
    if trade.side == "BUY":
        consistent_with_imbalance = order_imbalance_before < 0
    else:
        consistent_with_imbalance = order_imbalance_before > 0

    # Verificar price movement POST-trade (5 min después)
    future_price = self.get_future_price(
        trade.symbol,
        trade.timestamp + timedelta(minutes=5)
    )

    if trade.side == "BUY":
        price_increased = future_price > trade.price
    else:
        price_increased = future_price < trade.price

    # Informed trade: Consistent con imbalance Y price moved en tu dirección
    if consistent_with_imbalance and price_increased:
        return "INFORMED"
    elif not consistent_with_imbalance and not price_increased:
        return "NOISE"
    else:
        return "UNCERTAIN"
```
