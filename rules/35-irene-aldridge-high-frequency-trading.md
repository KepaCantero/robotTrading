# 🟡 35. "High-Frequency Trading" - Irene Aldridge

## REGLAS DE TRADING DE ALTA FRECUENCIA (HFT)

**Regla 35.1 — Adverse Selection Detection**

Claude DEBE detectar adverse selection ANTES de que dañe el P&L.

**Si órdenes se llenan solo en contra → DETENER bot.**

```python
def detect_adverse_selection(
    self,
    fills: List[Fill],
    market_moves_after_fill: pd.Series,
    adverse_threshold: float = 0.0001  # 1 basis point
) -> dict:
    """
    Detectar si estás siendo "arbitrado" por otros HFTs.

    Aldridge: Llenados solo cuando precio se mueve en contra = adverse selection.
    """
    adverse_signals = []

    for fill in fills:
        # Precio inmediatamente después del fill (100ms)
        post_fill_price = market_moves_after_fill.get(fill.timestamp + timedelta(milliseconds=100))

        if post_fill_price is None:
            continue

        # Calcular move adverso
        if fill.side == 'BUY':
            # Compramos: ¿precio bajó?
            adverse_move = (post_fill_price - fill.price) / fill.price
        else:
            # Vendimos: ¿precio subió?
            adverse_move = (fill.price - post_fill_price) / fill.price

        if adverse_move > adverse_threshold:
            adverse_signals.append({
                'fill_id': fill.id,
                'side': fill.side,
                'adverse_move': adverse_move,
                'timestamp': fill.timestamp
            })

    adverse_ratio = len(adverse_signals) / len(fills) if fills else 0

    if adverse_ratio > 0.3:  # > 30% adverse
        logger.critical(
            f"🚨 ADVERSE SELECTION: {adverse_ratio:.1%} of fills "
            f"are adverse. STOP bot."
        )

        return {
            'adverse_detected': True,
            'adverse_ratio': adverse_ratio,
            'action': 'HALT_TRADING'
        }

    logger.info(f"Adverse selection: {adverse_ratio:.1%} (acceptable)")

    return {
        'adverse_detected': False,
        'adverse_ratio': adverse_ratio
    }
```

**Regla 35.2 — Order Flow Imbalance (OFI)**

```python
def order_flow_imbalance_signal(
    self,
    order_book: dict,
    levels: int = 5
) -> dict:
    """
    Si volumen bid > ask persistente → probabilidad subida > 60%.

    Aldridge: OFI es predictor de próximos 100ms.
    """
    # Volumen en bids (compras)
    bid_volume = sum(
        level['quantity']
        for level in order_book['bids'][:levels]
    )

    # Volumen en asks (ventas)
    ask_volume = sum(
        level['quantity']
        for level in order_book['asks'][:levels]
    )

    # Order Flow Imbalance
    total_volume = bid_volume + ask_volume

    if total_volume == 0:
        return {'signal': 'NEUTRAL', 'ofi': 0}

    ofi = (bid_volume - ask_volume) / total_volume

    # Interpretar
    if ofi > 0.2:
        logger.info(f"🟢 Strong BUY imbalance: OFI={ofi:.2f}")
        signal = 'STRONG_BUY'
        prob_up = 0.60 + ofi * 0.2  # 60-80%

    elif ofi > 0.05:
        logger.info(f"BUY imbalance: OFI={ofi:.2f}")
        signal = 'BUY'
        prob_up = 0.55 + ofi * 0.2

    elif ofi < -0.2:
        logger.info(f"🔴 Strong SELL imbalance: OFI={ofi:.2f}")
        signal = 'STRONG_SELL'
        prob_up = 0.40 + ofi * 0.2

    elif ofi < -0.05:
        logger.info(f"SELL imbalance: OFI={ofi:.2f}")
        signal = 'SELL'
        prob_up = 0.45 + ofi * 0.2

    else:
        signal = 'NEUTRAL'
        prob_up = 0.5

    return {
        'ofi': ofi,
        'signal': signal,
        'prob_up_100ms': prob_up,
        'bid_volume': bid_volume,
        'ask_volume': ask_volume
    }
```

**Regla 35.3 — Bid-Ask Bounce Filter**

```python
def bid_ask_bounce_filter(
    self,
    price_change: float,
    current_spread: float,
    mid_price: float
) -> bool:
    """
    NO disparar señales si movimiento < spread actual.

    Aldridge: Bid-ask bounce = ruido, no señal.
    """
    # Movimiento como % del mid-price
    change_pct = abs(price_change) / mid_price

    # Spread como % del mid-price
    spread_pct = current_spread / mid_price

    if change_pct < spread_pct:
        logger.debug(
            f"Bid-ask bounce: Change={change_pct:.4f} "
            f"< Spread={spread_pct:.4f}. Ignore."
        )
        return False

    return True
```

**Regla 35.4 — Inventory Risk Scaling**

```python
def inventory_risk_adjustment(
    self,
    current_position: float,
    max_position: float,
    base_spread: float,
    risk_aversion: float = 0.5
) -> float:
    """
    A mayor posición → cotizar más lejos del mid-price.

    Aldridge: Reducir riesgo de inventario.
    """
    # Posición como % del máximo
    position_ratio = abs(current_position) / max_position

    # Ajustar spread según inventario
    # Más inventario = spread más ancho
    inventory_penalty = position_ratio * risk_aversion

    adjusted_spread = base_spread * (1 + inventory_penalty)

    logger.info(
        f"Inventory risk: Position={current_position:.0f} "
        f"({position_ratio:.1%}), Spread {base_spread:.4f} → "
        f"{adjusted_spread:.4f}"
    )

    return adjusted_spread
```

**Regla 35.5 — Tick-Level Statistics**

```python
def tick_level_statistics(
    self,
    tick_data: pd.DataFrame,  # columns: timestamp, price, size
    window_ticks: int = 100
) -> dict:
    """
    Calcular desviación estándar sobre TICKS, no velas.

    Aldridge: Micro-trend detection en nivel de tick.
    """
    # Últimos N ticks
    recent_ticks = tick_data.tail(window_ticks)

    # Tick returns
    tick_returns = recent_ticks['price'].pct_change()

    # Tick-level volatility
    tick_volatility = tick_returns.std()

    # Tick trend (up vs down ticks)
    up_ticks = (tick_returns > 0).sum()
    down_ticks = (tick_returns < 0).sum()

    tick_direction = (up_ticks - down_ticks) / window_ticks

    logger.info(
        f"Tick stats: Vol={tick_volatility:.6f}, "
        f"Direction={tick_direction:.2f} "
        f"(Up={up_ticks}, Down={down_ticks})"
    )

    return {
        'tick_volatility': tick_volatility,
        'tick_direction': tick_direction,
        'up_ticks': up_ticks,
        'down_ticks': down_ticks
    }
```

**Regla 35.6 — Latency Arbitrage Guard**

```python
def latency_guard(
    self,
    current_latency_ms: float,
    baseline_latency_ms: float,
    max_latency_increase: float = 50.0  # ms
) -> dict:
    """
    Si latencia aumenta > 50ms → modo "solo cerrar".

    Aldridge: Latencia alta = estás en desventaja competitiva.
    """
    latency_increase = current_latency_ms - baseline_latency_ms

    if latency_increase > max_latency_increase:
        logger.critical(
            f"🚨 LATENCY SPIKE: +{latency_increase:.0f}ms "
            f"(Baseline={baseline_latency_ms:.0f}ms). "
            f"Close-only mode."
        )

        return {
            'mode': 'CLOSE_ONLY',
            'latency_increase': latency_increase,
            'reason': 'Latency arbitrage risk'
        }

    return {'mode': 'NORMAL'}
```

**Regla 35.7 — Event Detection (Cancelation Spike)**

```python
def cancelation_spike_detection(
    self,
    order_cancellations: pd.Series,  # timestamp-indexed
    window_seconds: int = 10
) -> dict:
    """
    Aumento en cancelaciones = movimiento violento inminente.

    Aldridge: Algoritmos preparan posición antes de mover.
    """
    # Cancelaciones en ventana
    recent_time = datetime.now() - timedelta(seconds=window_seconds)
    recent_cancels = order_cancellations[order_cancellations.index >= recent_time]

    cancel_rate = len(recent_cancels) / window_seconds

    # Threshold dinámico (basado en media histórica)
    historical_avg = 2.0  # 2 cancels/sec baseline

    spike_multiplier = cancel_rate / historical_avg

    if spike_multiplier > 3.0:  # 3x normal
        logger.warning(
            f"⚠️ CANCELATION SPIKE: {cancel_rate:.1f}/sec "
            f"({spike_multiplier:.1f}x normal). "
            f"Volatility incoming."
        )

        return {
            'spike_detected': True,
            'spike_multiplier': spike_multiplier,
            'action': 'REDUCE_POSITION'
        }

    return {'spike_detected': False}
```

**Regla 35.8 — Market Impact Model**

```python
def large_order_impact_limit(
    self,
    order_size: float,
    level_volume: float,
    max_participation: float = 0.05  # 5%
) -> bool:
    """
    Para órdenes LARGE, nunca > 5% del volumen del nivel.

    Aldridge: Market impact = costo directo.
    """
    participation = order_size / level_volume

    if participation > max_participation:
        logger.error(
            f"❌ MARKET IMPACT: Order {order_size:.0f} "
            f"is {participation:.1%} of level volume "
            f">(max {max_participation:.0%}). "
            f"Split order."
        )
        return False

    return True
```

**Regla 35.9 — Volatility Clustering**

```python
def volatility_clustering_adjustment(
    self,
    recent_volatility: float,  # últimos 5 min
    baseline_volatility: float,
    current_stop_distance: float
) -> float:
    """
    Si volatilidad sube → ensanchar stop-loss proporcionalmente.

    Aldridge: Volatility clustering en HFT.
    """
    vol_ratio = recent_volatility / baseline_volatility

    if vol_ratio > 1.5:
        # Volatilidad 50% más alta
        adjusted_stop = current_stop_distance * vol_ratio

        logger.warning(
            f"Volatility spike: {vol_ratio:.1f}x baseline. "
            f"Stop: {current_stop_distance:.4f} → {adjusted_stop:.4f}"
        )

        return adjusted_stop

    return current_stop_distance
```

**Regla 35.10 — Spoofing Filter**

```python
def spoofing_filter(
    self,
    order_book_snapshots: List[dict],
    min_life_ms: int = 1000
) -> dict:
    """
    Ignorar órdenes masivas que aparecen/desaparecen < 1 segundo.

    Aldridge: Filtro de spoofing en Level 2.
    """
    suspicious_levels = []

    # Track niveles de volumen grande
    for snapshot in order_book_snapshots:
        large_bids = [
            level for level in snapshot['bids']
            if level['quantity'] > 10000  # > 10k shares
        ]

        large_asks = [
            level for level in snapshot['asks']
            if level['quantity'] > 10000
        ]

        # Chequear si persisten
        for level in large_bids + large_asks:
            # Buscar en snapshots siguientes
            level_life = self.get_level_lifetime(level, order_book_snapshots)

            if level_life < min_life_ms:
                suspicious_levels.append({
                    'price': level['price'],
                    'quantity': level['quantity'],
                    'lifetime_ms': level_life
                })

    if suspicious_levels:
        logger.info(
            f"Filtered {len(suspicious_levels)} spoofing levels "
            f"(<{min_life_ms}ms lifetime)"
        )

    return {
        'suspicious_count': len(suspicious_levels),
        'filtered_levels': suspicious_levels
    }
```

**Regla 35.11 — Time-of-Day Liquidity**

```python
def time_of_day_liquidity_adjustment(
    self,
    current_time: datetime,
    base_aggression: float
) -> float:
    """
    Reducir agresividad durante "almuerzo NY" (12:00-13:00 EST).

    Aldridge: Liquidez baja = spreads anchos.
    """
    # Convertir a EST
    est_hour = (current_time.hour - 5) % 24  # UTC → EST (aprox)

    # Almuerzo NY
    if 12 <= est_hour < 13:
        logger.info("NY Lunch hour: Reducing aggression (low liquidity)")

        return base_aggression * 0.5  # 50% reducción

    # Opening (9:30-10:00) y Closing (15:30-16:00): alta liquidez
    if (9 <= est_hour < 10) or (15 <= est_hour < 16):
        logger.info("Open/Close: High liquidity")

        return base_aggression * 1.2  # 20% más agresivo

    return base_aggression
```

**Regla 35.12 — Mean Reversion de Micro-spread**

```python
def micro_spread_mean_reversion(
    self,
    current_spread: float,
    spread_ma: float,
    std_spread: float,
    mid_price: float
) -> dict:
    """
    Comprar cuando spread se ensancha anormalmente.

    Aldridge: Spread revert to mean.
    """
    # Z-score del spread
    spread_zscore = (current_spread - spread_ma) / std_spread

    if spread_zscore > 2.0:
        # Spread anormalmente ancho → comprar spread
        logger.info(
            f"Spread wide: Z={spread_zscore:.1f}. "
            f"Expected reversion."
        )

        return {
            'signal': 'BUY_SPREAD',
            'zscore': spread_zscore,
            'expected_action': 'Provide liquidity'
        }

    elif spread_zscore < -2.0:
        # Spread anormalmente estrecho → evitar
        logger.info(f"Spread tight: Z={spread_zscore:.1f}. Reduce activity.")

        return {
            'signal': 'REDUCE_ACTIVITY',
            'zscore': spread_zscore
        }

    return {'signal': 'NORMAL'}
```

**Regla 35.13 — Cross-Exchange Correlation**

```python
def cross_exchange_correlation_check(
    self,
    spy_price: float,
    spy_move: float,
    future_price: float,
    future_move: float,
    threshold: float = 0.001  # 0.1%
) -> dict:
    """
    Si SPY sube pero E-mini no reacciona → ajuste inminente.

    Aldridge: Correlation break = opportunity.
    """
    # Divergencia
    divergence = abs(spy_move - future_move)

    if divergence > threshold:
        logger.warning(
            f"Correlation break: SPY {spy_move:+.2%}, "
            f"Future {future_move:+.2%}. "
            f"Ajuste esperado."
        )

        return {
            'divergence_detected': True,
            'divergence': divergence,
            'expected_direction': 'UP' if spy_move > 0 else 'DOWN'
        }

    return {'divergence_detected': False}
```

**Regla 35.14 — Co-location Logic**

```python
async def colocated_execution_optimization(
    self,
    market_data_update: dict
) -> None:
    """
    Optimizar para ejecución asíncrona; cada ms = slippage.

    Aldridge: Co-location + async code = ventaja.
    """
    import asyncio

    # Procesamiento ultra-rápido
    tasks = []

    # Task 1: Actualizar local book
    tasks.append(asyncio.create_task(
        self.update_local_book(market_data_update)
    ))

    # Task 2: Recalcular señales
    tasks.append(asyncio.create_task(
        self.recalculate_signals()
    ))

    # Task 3: Actualizar risk
    tasks.append(asyncio.create_task(
        self.update_risk_metrics()
    ))

    # Ejecutar en paralelo
    await asyncio.gather(*tasks)

    # Latencia de procesamiento (medir)
    processing_time = self.measure_latency()

    if processing_time > 1.0:  # > 1ms
        logger.warning(f"Slow processing: {processing_time:.3f}ms")
```

**Regla 35.15 — HFT Regime Switching**

```python
def hft_regime_detection(
    self,
    aggressive_volume: float,  # Volumen agresivo (market orders)
    passive_volume: float,  # Volumen pasivo (limit orders)
    price_trend: float  # Tendencia de precio
) -> dict:
    """
    Detectar si mercado dominado por trend o range algorithms.

    Aldridge: Ajustar estrategia según régimen.
    """
    # Ratio de agresividad
    aggressiveness_ratio = aggressive_volume / (aggressive_volume + passive_volume)

    # Regime
    if aggressiveness_ratio > 0.6 and abs(price_trend) > 0.001:
        regime = 'TREND_FOLLOWING_DOMINANT'
        optimal_strategy = 'MOMENTUM'

    elif aggressiveness_ratio < 0.4:
        regime = 'MEAN_REVERSION_DOMINANT'
        optimal_strategy = 'MEAN_REVERSION'

    else:
        regime = 'MIXED'
        optimal_strategy = 'NEUTRAL'

    logger.info(
        f"HFT Regime: {regime} "
        f"(Aggressive={aggressiveness_ratio:.1%}, "
        f"Trend={price_trend:+.3f})"
    )

    return {
        'regime': regime,
        'optimal_strategy': optimal_strategy,
        'aggressiveness_ratio': aggressiveness_ratio
    }
```
