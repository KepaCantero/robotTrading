# 📕 6. "Trading and Exchanges" - Larry Harris

## REGLAS DE MICROESTRUCTURA Y EJECUCIÓN

**Regla 6.1 — Entiende el Order Book antes de enviar órdenes**

```python
def analyze_order_book_depth(
    self,
    symbol: str,
    levels: int = 5
) -> Dict[str, any]:
    """
    Analizar profundidad del order book antes de ejecutar.

    Book poco profundo = high market impact.
    """
    book = self.get_order_book(symbol, levels=levels)

    # 1. Bid-ask spread
    spread_bps = (book['ask'][0] - book['bid'][0]) / book['bid'][0] * 10000

    # 2. Book imbalance (presión compra vs venta)
    total_bid_volume = sum(book['bid_sizes'])
    total_ask_volume = sum(book['ask_sizes'])
    imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)

    # 3. Effective spread (para orden de tamaño X)
    def effective_spread(quantity: Decimal) -> Decimal:
        """Precio efectivo para cruzar el book."""
        remaining = quantity
        total_cost = Decimal("0")

        for price, size in zip(book['ask'], book['ask_sizes']):
            fill = min(remaining, size)
            total_cost += price * fill
            remaining -= fill

            if remaining == 0:
                break

        avg_price = total_cost / quantity
        return (avg_price - book['bid'][0]) / book['bid'][0] * 10000  # bps

    return {
        'spread_bps': spread_bps,
        'imbalance': imbalance,  # +1 = todas compras, -1 = todas ventas
        'effective_spread_1000': effective_spread(Decimal("1000")),
        'book_depth': len(book['bid'])
    }
```

**Regla 6.2 — Bid-Ask Bounce: NO confundas noise con señal**

```python
def remove_bid_ask_bounce(
    self,
    prices: pd.Series,
    trades: pd.DataFrame
) -> pd.Series:
    """
    Bid-ask bounce crea volatilidad artificial.

    Trades alternan entre bid/ask → parece volatilidad pero es noise.
    """
    # Usar mid-price en lugar de last trade price
    mid_prices = pd.Series(index=prices.index)

    for timestamp in prices.index:
        quote = self.get_quote_at(timestamp)
        mid_prices[timestamp] = (quote.bid + quote.ask) / 2

    return mid_prices
```

**Regla 6.3 — NUNCA ignores el tiempo de ejecución (timing cost)**

```python
def calculate_timing_cost(
    self,
    entry_signal_time: datetime,
    actual_execution_time: datetime,
    signal_price: Decimal,
    execution_price: Decimal
) -> Decimal:
    """
    Timing cost = opportunity cost de NO ejecutar inmediatamente.

    Señal a 09:30, ejecución a 10:00 → precio se movió.
    """
    delay_seconds = (actual_execution_time - entry_signal_time).seconds

    if delay_seconds > 300:  # >5 minutos
        logger.warning(f"⚠️ Execution delay: {delay_seconds}s")

    # Calcular slippage debido a delay
    timing_slippage = abs(execution_price - signal_price) / signal_price

    return timing_slippage
```

**Regla 6.4 — Market Impact Model: Usa Almgren-Chriss**

```python
def almgren_chriss_impact(
    self,
    order_size: Decimal,
    total_shares: Decimal,
    volatility: float,
    adv: Decimal,
    trade_duration_minutes: int = 60
) -> Decimal:
    """
    Almgren-Chriss: Modelo de market impact académico estándar.

    Permanent impact + Temporary impact.
    """
    # Participation rate
    participation = float(order_size / adv)

    # Permanent impact (queda después de trade)
    # I_permanent = γ * σ * sqrt(participation)
    gamma = 0.1  # Calibrado empíricamente
    permanent_impact = gamma * volatility * np.sqrt(participation)

    # Temporary impact (desaparece rápido)
    # I_temporary = η * σ * (V / ADV)
    eta = 0.05
    temporary_impact = eta * volatility * participation

    # Total impact
    total_impact = permanent_impact + temporary_impact

    return Decimal(str(total_impact))
```

**Regla 6.5 — SIEMPRE monitorea Quote Stuffing (manipulación)**

```python
def detect_quote_stuffing(
    self,
    symbol: str,
    window_seconds: int = 10
) -> bool:
    """
    Quote stuffing = flood de quotes para confundir.

    >1000 quotes/segundo = posible manipulación.
    """
    recent_quotes = self.get_recent_quotes(symbol, seconds=window_seconds)

    quote_rate = len(recent_quotes) / window_seconds

    if quote_rate > 100:  # >100 quotes/segundo
        logger.warning(f"⚠️ Potential quote stuffing: {quote_rate:.0f} quotes/sec")

        # NO tradear durante quote stuffing
        return True

    return False
```

**Regla 6.6 — Limit Order Placement: Price improvement vs Fill rate tradeoff**

```python
def optimal_limit_price(
    self,
    side: str,
    current_bid: Decimal,
    current_ask: Decimal,
    urgency: float = 0.5  # 0 = patient, 1 = urgent
) -> Decimal:
    """
    Limit price optimization: balance fill probability vs price.

    Urgency alta → precio agresivo (near ask for buy)
    Urgency baja → precio pasivo (near bid for buy)
    """
    spread = current_ask - current_bid

    if side == "BUY":
        # Urgency 0 → bid (0% de spread pagado)
        # Urgency 1 → ask (100% de spread pagado)
        limit_price = current_bid + spread * Decimal(str(urgency))
    else:
        # SELL: inverso
        limit_price = current_ask - spread * Decimal(str(urgency))

    return limit_price
```

**Regla 6.7 — Dark Pools: Usa solo para órdenes grandes (>10% ADV)**

```python
def should_use_dark_pool(
    self,
    order_size: Decimal,
    adv: Decimal,
    information_leakage_risk: str = "HIGH"
) -> bool:
    """
    Dark pools útiles para órdenes grandes que quieres ocultar.

    Ventaja: No mueves el precio antes de ejecutar (no pre-running)
    Desventaja: Peor price discovery
    """
    participation = float(order_size / adv)

    # Solo usar dark pool si:
    # 1. Orden grande (>10% ADV)
    # 2. Information leakage risk alto

    if participation > 0.10 and information_leakage_risk == "HIGH":
        logger.info(f"✅ Using dark pool: {participation:.1%} of ADV")
        return True

    # Órdenes pequeñas → lit market (mejor price)
    return False
```

**Regla 6.8 — NUNCA asumas liquidez ilimitada**

```python
def validate_liquidity_assumption(
    self,
    symbol: str,
    order_size: Decimal,
    max_participation: float = 0.20
) -> bool:
    """
    Verificar que orden no exceda límite de liquidez.

    Muchas estrategias backtested asumen liquidez infinita = ERROR.
    """
    adv = self.get_average_daily_volume(symbol)
    participation = float(order_size / adv)

    if participation > max_participation:
        logger.error(
            f"❌ Order too large: {participation:.1%} of ADV "
            f"(max: {max_participation:.0%})"
        )
        return False

    # También verificar volatilidad recent
    recent_volatility = self.get_recent_volatility(symbol, days=5)

    if recent_volatility > 0.05:  # >5% daily volatility
        logger.warning(
            f"⚠️ High volatility ({recent_volatility:.1%}) - "
            "Reduce participation rate"
        )

    return True
```

**Regla 6.9 — Tick Size: Impacta bid-ask spread**

```python
def adjust_for_tick_size(
    self,
    price: Decimal,
    tick_size: Decimal = Decimal("0.01")
) -> Decimal:
    """
    Round price al tick size más cercano.

    NYSE: tick = $0.01
    Penny stocks: tick puede ser $0.0001
    """
    # Round down para BUY limit, round up para SELL limit
    rounded = (price // tick_size) * tick_size

    return rounded
```

**Regla 6.10 — Payment for Order Flow (PFOF): Entiende el conflicto de interés**

```python
def evaluate_execution_quality(
    self,
    executions: List[Execution],
    benchmark: str = "NBBO"  # National Best Bid Offer
) -> Dict[str, float]:
    """
    Medir execution quality vs benchmark.

    Broker con PFOF puede NO darte best price.
    """
    improvements = []

    for exec in executions:
        # Obtener NBBO en ese momento
        nbbo = self.get_nbbo_at(exec.symbol, exec.timestamp)

        if exec.side == "BUY":
            benchmark_price = nbbo['ask']
            improvement = float(benchmark_price - exec.price) / float(benchmark_price)
        else:
            benchmark_price = nbbo['bid']
            improvement = float(exec.price - benchmark_price) / float(benchmark_price)

        improvements.append(improvement)

    avg_improvement = np.mean(improvements)

    if avg_improvement < 0:
        logger.warning(f"⚠️ Average price worse than NBBO: {avg_improvement:.4%}")

    return {
        'avg_improvement_bps': avg_improvement * 10000,
        'pct_improved': sum(1 for i in improvements if i > 0) / len(improvements)
    }
```
