# 🪙 39. "Market Making in Crypto" - Sasha Stoikov

## REGLAS DE MARKET MAKING EN CRYPTO (CEX/PERPETUALS)

**Regla 39.1 — Closing the Loop (Inventory Zero)**

Claude DEBE terminar cada hora con inventario neto cercano a cero.

**Market Making NO es posicionamiento; esMAKE spreads.**

```python
def hourly_inventory_target(
    self,
    current_inventory: float,
    max_inventory: float,
    hour_elapsed: bool
) -> dict:
    """
    Terminar hora con inventario ~ 0.

    Stoikov: MM no es directional trading.
    """
    inventory_ratio = current_inventory / max_inventory

    # Si pasó la hora y hay inventario significativo
    if hour_elapsed and abs(inventory_ratio) > 0.1:
        logger.warning(
            f"Hour end: Inventory={inventory_ratio:.1%}. "
            f"FLATTEN position."
        )

        return {
            'action': 'FLATTEN',
            'target_inventory': 0,
            'urgency': 'HIGH'
        }

    # Ajuste progresivo hacia 0
    target_inventory = -current_inventory * 0.1

    return {
        'action': 'GRADUAL_ADJUST',
        'target_inventory': target_inventory
    }
```

**Regla 39.2 — Gamma Adjustment**

```python
def gamma_inventory_skew(
    self,
    market_trend: float,  # -1 to 1
    current_inventory: float
) -> float:
    """
    En mercados alcistas → sesgo positivo de inventario.

    Stoikov: Beneficiarse de drift.
    """
    # Ajuste gamma según tendencia
    if market_trend > 0.3:  # Strong uptrend
        target_inventory_ratio = 0.3  # 30% long bias
        logger.info("Bull market: Positive inventory bias")

    elif market_trend < -0.3:  # Strong downtrend
        target_inventory_ratio = -0.3  # 30% short bias
        logger.info("Bear market: Negative inventory bias")

    else:
        target_inventory_ratio = 0.0

    return target_inventory_ratio
```

**Regla 39.3 — Funding Rate Capture**

```python
def funding_rate_priority(
    self,
    funding_rates: dict,  # symbol -> funding rate
    inventory_capacity: float
) -> List[str]:
    """
    Priorizar MM donde funding rate te paga.

    Stoikov: Funding = revenue extra.
    """
    # Filtrar funding positivos (te pagan a ti)
    positive_funding = {
        symbol: rate
        for symbol, rate in funding_rates.items()
        if rate > 0
    }

    # Ordenar por funding rate
    sorted_symbols = sorted(
        positive_funding.items(),
        key=lambda x: x[1],
        reverse=True
    )

    if sorted_symbols:
        logger.info(
            f"Funding priority: {sorted_symbols[0][0]} "
            f"({sorted_symbols[0][1]:.2%} funding)"
        )

        return [s[0] for s in sorted_symbols]

    return []
```

**Regla 39.4 — Order Thickness (Laddering)**

```python
def laddering_strategy(
    self,
    total_inventory: float,
    n_levels: int = 5
) -> List[dict]:
    """
    Distribuir liquidez en escala exponencial.

    Stoikov: No todo en primer nivel.
    """
    levels = []
    base_size = total_inventory / n_levels

    for i in range(n_levels):
        # Tamaños exponencialmente decrecientes
        size = base_size * (0.5 ** i)

        # Distancia del mid
        distance_ticks = (i + 1) * 2  # 2, 4, 6, 8, 10 ticks

        levels.append({
            'level': i + 1,
            'size': size,
            'distance_ticks': distance_ticks
        })

    logger.info(f"Laddering: {n_levels} levels, exponential decay")

    return levels
```

**Regla 39.5 — Correlation-Based Quoting**

```python
def correlation_quote_adjustment(
    self,
    btc_move: float,
    altcoin_prices: dict
) -> dict:
    """
    Si BTC baja → mover bids en ALTCOINS abajo ANTES de ejecutar.

    Stoikov: Correlation ajusta quotes en tiempo real.
    """
    adjustments = {}

    if abs(btc_move) > 0.02:  # BTC moved > 2%
        logger.info(f"BTC move {btc_move:+.2%}: Adjusting altcoin quotes")

        for symbol, _ in altcoin_prices.items():
            # Beta ajustado (altcoins más volátiles)
            beta = 1.5

            expected_move = btc_move * beta

            # Mover quotes
            adjustments[symbol] = {
                'bid_adjustment': -expected_move if btc_move < 0 else 0,
                'ask_adjustment': -expected_move if btc_move > 0 else 0
            }

    return adjustments
```

**Regla 39.6 — Execution Probability (Avellaneda-Stoikov)**

```python
def avellaneda_stoikov_quotes(
    self,
    mid_price: float,
    inventory: float,
    volatility: float,
    risk_aversion: float = 0.5
) -> dict:
    """
    Calcular spreads óptimos usando modelo de Avellaneda-Stoikov.

    Stoikov: Modelos cuantitativos para MM.
    """
    # Reservation price (ajustado por inventario)
    reservation_price = mid_price - inventory * risk_aversion * volatility**2

    # Optimal spread
    gamma = risk_aversion
    k = 1.0  # Intensidad de llegadas de órdenes

    half_spread = (1 / gamma) * np.log(1 + gamma * volatility**2 / k)

    bid_price = reservation_price - half_spread
    ask_price = reservation_price + half_spread

    logger.info(
        f"AS model: Mid={mid_price:.2f}, "
        f"Reserv={reservation_price:.2f}, "
        f"Spread={2*half_spread:.4f}"
    )

    return {
        'bid_price': bid_price,
        'ask_price': ask_price,
        'reservation_price': reservation_price,
        'half_spread': half_spread
    }
```

**Regla 39.7 — Tail Risk Management**

```python
def tail_risk_stops(
    self,
    position: float,
    current_price: float,
    entry_price: float
) -> dict:
    """
    Cripto tiene movimientos 10-20%. Stop-loss emergencia obligatorio.

    Stoikov: Tail risk = posibilidad de liquidación.
    """
    # PnL no realizado
    unrealized_pnl = (current_price - entry_price) * position

    # Si pérdida > 20%
    if position > 0 and unrealized_pnl < -0.20 * entry_price * position:
        logger.critical(
            f"🚨 TAIL LOSS: {unrealized_pnl/entry_price/position:.1%}. "
            f"EMERGENCY CLOSE."
        )

        return {
            'emergency': True,
            'action': 'IMMEDIATE_CLOSE',
            'reason': 'TAIL_RUIT'
        }

    return {'emergency': False}
```

**Regla 39.8 — Real-time Alpha (Social Signals)**

```python
def social_sentiment_multiplier(
    self,
    twitter_sentiment: float,  # -1 to 1
    base_aggression: float
) -> float:
    """
    Integrar señales sociales como multiplicador de agresividad.

    Stoikov: Sentimiento = alpha para MM.
    """
    if abs(twitter_sentiment) > 0.5:  # Sentimiento fuerte
        multiplier = 1.0 + twitter_sentiment * 0.5

        adjusted_aggression = base_aggression * multiplier

        logger.info(
            f"Social sentiment: {twitter_sentiment:+.2f}, "
            f"Aggression {base_aggression:.2f} → {adjusted_aggression:.2f}"
        )

        return adjusted_aggression

    return base_aggression
```

**Regla 39.9 — WebSocket Latency (C++/Rust)**

```python
def websocket_performance_check(
    self,
    processing_latency_ms: float,
    max_latency_ms: float = 5.0
) -> dict:
    """
    C++/Rust para WebSockets. Python demasiado lento.

    Stoikov: 100k updates/sec requiere código nativo.
    """
    if processing_latency_ms > max_latency_ms:
        logger.error(
            f"❌ SLOW PROCESSING: {processing_latency_ms:.1f}ms "
            f"> {max_latency_ms:.1f}ms. "
            f"Python bottleneck. Use C++/Rust."
        )

        return {
            'performance_ok': False,
            'recommendation': 'REWRITE_CRITICAL_PATH_IN_RUST',
            'latency': processing_latency_ms
        }

    return {'performance_ok': True}
```

**Regla 39.10 — Liquidation Hunting**

```python
def liquidation_level_avoidance(
    self,
    liquidation_levels: List[dict],  # {price, amount}
    current_price: float,
    inventory: float
) -> dict:
    """
    Identificar niveles con muchas liquidaciones → ensanchar spreads.

    Stoikov: No ser arrastrado por cascade.
    """
    for level in liquidation_levels:
        # Si nivel cerca de nuestro inventario
        if abs(level['price'] - current_price) / current_price < 0.01:  # < 1%
            logger.warning(
                f"Liquidation level near: ${level['price']:.0f} "
                f"(${level['amount']:,.0f} to liquidate). "
                f"Widen spreads."
            )

            return {
                'liquidation_near': True,
                'action': 'WIDEN_SPREADS',
                'spread_multiplier': 2.0
            }

    return {'liquidation_near': False}
```

**Regla 39.11 — Round Number Bias**

```python
def round_number_quoting(
    self,
    round_numbers: List[float],  # [50000, 60000, etc.]
    current_price: float
) -> dict:
    """
    Ballenas ponen muros en números redondos. Operar 1 tick antes.

    Stoikov: Psicología de mercado.
    """
    for rn in round_numbers:
        # Si cerca de número redondo
        if abs(current_price - rn) / rn < 0.001:  # < 0.1%
            tick_size = current_price * 0.0001  # 0.01% para crypto

            if current_price < rn:
                # Comprar 1 tick antes del soporte
                bid_price = rn - tick_size * 2
                logger.info(f"Round number support ${rn:,.0f}: Bid at ${bid_price:.0f}")

                return {'quote': 'AGGRESSIVE_BID', 'price': bid_price}

            else:
                # Vender 1 tick antes de resistencia
                ask_price = rn + tick_size * 2
                logger.info(f"Round number resistance ${rn:,.0f}: Ask at ${ask_price:.0f}")

                return {'quote': 'AGGRESSIVE_ASK', 'price': ask_price}

    return {'quote': 'NORMAL'}
```

**Regla 39.12 — Exchange Fee Tier**

```python
def fee_tier_profitability(
    self,
    volume_30d: float,
    maker_fee: float,
    taker_fee: float,
    expected_spread_capture: float
) -> bool:
    """
    Calcular rentabilidad según nivel de comisión Maker.

    Stoikov: Fees negativos = profit directo.
    """
    # Fees esperados (asumiendo 50% maker, 50% taker)
    avg_fee = (maker_fee + taker_fee) / 2

    # Profit neto
    net_profit = expected_spread_capture - avg_fee

    if net_profit > 0:
        logger.info(
            f"Profitable: Spread={expected_spread_capture:.4f}, "
            f"Fee={avg_fee:.4f}, Net={net_profit:.4f}"
        )
        return True

    logger.warning(
        f"Unprofitable: Spread={expected_spread_capture:.4f} "
        f"< Fee={avg_fee:.4f}"
    )

    return False
```

**Regla 39.13 — Stablecoin Peg Risk**

```python
def stablecoin_depeg_monitor(
    self,
    usdt_price: float,
    peg_threshold: float = 0.99
) -> bool:
    """
    Monitorear paridad USDT/USD. Si cae < 0.99 → detener bot.

    Stoikov: Stablecoin depeg = riesgo sistémico.
    """
    if usdt_price < peg_threshold:
        logger.critical(
            f"🚨 STABLECOIN DEPEG: USDT=${usdt_price:.4f} "
            f"< ${peg_threshold:.2f}. HALT bot."
        )

        return False

    return True
```

**Regla 39.14 — High Kurtosis Factor**

```python
def kurtosis_adjusted_risk(
    self,
    returns: pd.Series,
    confidence_level: float = 0.99
) -> float:
    """
    Cripto tiene colas pesadas. Ajustar modelos de riesgo.

    Stoikov: Distribución normal NO funciona en crypto.
    """
    from scipy.stats import kurtosis

    # Kurtosis de los returns
    kurt = kurtosis(returns, fisher=False)

    # Si kurtosis > 3 (normal = 3)
    if kurt > 10:  # Colas muy pesadas
        logger.warning(
            f"Heavy tails: Kurtosis={kurt:.1f} "
            f"(Normal=3). Fat tail risk."
        )

        # VaR ajustado por colas pesadas
        var_percentile = 1 - confidence_level

        # Usar percentil empírico, no asumir normal
        fat_tail_var = returns.quantile(var_percentile)

        return fat_tail_var

    # VaR normal como fallback
    return returns.quantile(0.01)
```

**Regla 39.15 — Adaptive Spread**

```python
def adaptive_spread_calculation(
    self,
    volatility: float,
    inventory_ratio: float,  # -1 to 1
    time_to_funding: int,  # seconds
    base_spread: float = 0.001
) -> dict:
    """
    Spread = f(volatilidad + inventario + tiempo a funding).

    Stoikov: Spread dinámico = maximiza profit.
    """
    # Volatility component
    vol_component = volatility * 0.5

    # Inventory component (más inventario = spread más ancho)
    inv_component = abs(inventory_ratio) * 0.0005

    # Time to funding (cerca de funding = spread más estrecho)
    funding_component = max(0, (time_to_funding - 3600) / 3600 * 0.0002)

    total_spread = base_spread + vol_component + inv_component - funding_component

    logger.info(
        f"Adaptive spread: {total_spread:.4f} "
        f"(Vol={vol_component:.4f}, Inv={inv_component:.4f}, "
        f"Funding={funding_component:.4f})"
    )

    return {
        'spread': total_spread,
        'components': {
            'volatility': vol_component,
            'inventory': inv_component,
            'funding': funding_component
        }
    }
```
