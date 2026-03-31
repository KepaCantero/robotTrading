# 📄 Papers Fundamentales - Joel Hasbrouck: Algorithmic Trading & Market Microstructure (2007)

## Ejecución Avanzada y Calidad de Mercado

**Contexto:** ExecutionEngine / HFT / Microestructura Avanzada.

Joel Hasbrouck es una de las autoridades más importantes en microestructura de mercados. Sus investigaciones sobre price discovery, information share y VPIN son críticas para ejecución algorítmica avanzada.

---

### Regla 1 — Variance Ratio Test

Verificar si el precio sigue un camino aleatorio o tiene memoria a corto plazo. Si `VR < 1`, hay reversión a la media (Mean Reversion).

```python
def variance_ratio_test(
    self,
    prices: pd.Series,
    short_period: int = 1,
    long_period: int = 5
) -> dict:
    """
    Test de Ratio de Varianza para detectar memoria.

    Hasbrouck: VR < 1 = mean reversion, VR > 1 = momentum.
    """
    # Retornos de corto y largo plazo
    short_returns = prices.pct_change(short_period).dropna()
    long_returns = prices.pct_change(long_period).dropna()

    # Varianzas
    var_short = short_returns.var()
    var_long = long_returns.var()

    # Ratio de varianza (ajustado por periodos)
    vr = (var_long / var_short) / (long_period / short_period)

    # Test estadístico
    n = len(short_returns)
    se = np.sqrt(2 * (2 * long_period - short_period) * (long_period - short_period) / (3 * long_period * n))

    z_score = (vr - 1) / se

    # Interpretación
    if z_score < -1.96:  # p < 0.05
        regime = 'MEAN_REVERSION'
        logger.info(f"VR={vr:.3f}: Significant mean reversion")

    elif z_score > 1.96:
        regime = 'MOMENTUM'
        logger.info(f"VR={vr:.3f}: Significant momentum")

    else:
        regime = 'RANDOM_WALK'
        logger.info(f"VR={vr:.3f}: Random walk (no edge)")

    return {
        'variance_ratio': vr,
        'z_score': z_score,
        'regime': regime,
        'tradeable': abs(z_score) > 1.96
    }
```

### Regla 2 — Information Share (IS)

En activos que cotizan en múltiples mercados (ej. Crypto en Binance/Coinbase), calcular dónde se descubre el precio primero (Price Discovery Leadership).

```python
def calculate_information_share(
    self,
    prices_multiple_exchanges: dict,  # {'Binance': series, 'Coinbase': series}
    symbol: str
) -> dict:
    """
    Calcular Information Share de cada mercado.

    Hasbrouck: Qué mercado lidera el price discovery.
    """
    from statsmodels.tsa.api import VECM

    # Preparar datos
    combined = pd.DataFrame(prices_multiple_exchanges).dropna()

    if len(combined) < 100:
        raise ValueError("Insufficient data for VECM")

    # Modelo VECM (Vector Error Correction)
    model = VECM(combined, k_ar_diff=1, coint_rank=1)
    fitted = model.fit()

    # Information share basado en vectores de carga de error
    is_shares = {}

    for i, market in enumerate(combined.columns):
        # Contribución al price discovery
        alpha = fitted.alpha[i]  # Vector de corrección de error
        gamma = fitted.coint_vec  # Vector de cointegración

        # Information share (simplificado)
        is_share = abs(alpha[0]) / sum(abs(fitted.alpha[:, 0]))

        is_shares[market] = is_share

    # Ordenar por IS
    is_shares_sorted = dict(sorted(is_shares.items(), key=lambda x: x[1], reverse=True))

    logger.info(
        f"Information Share for {symbol}: {is_shares_sorted}"
    )

    return {
        'information_shares': is_shares_sorted,
        'leading_market': max(is_shares_sorted, key=is_shares_sorted.get),
        'lagging_markets': [m for m, s in is_shares_sorted.items() if s < 0.2]
    }
```

### Regla 3 — Effective Spread vs Quoted Spread

Calcular el costo real de ejecución `(2 × |Price - Mid|)`. Si Effective > Quoted, la calidad de ejecución es mala.

```python
def calculate_execution_quality(
    self,
    trades: list,
    order_book: dict
) -> dict:
    """
    Calcular Effective vs Quoted Spread.

    Hasbrouck: Effective > Quoted = mala ejecución.
    """
    quoted_bid = order_book['bids'][0]['price']
    quoted_ask = order_book['asks'][0]['price']

    quoted_spread = quoted_ask - quoted_bid
    quoted_spread_bps = quoted_spread / ((quoted_bid + quoted_ask) / 2) * 10000

    effective_spreads = []

    for trade in trades:
        trade_price = trade['price']
        trade_side = trade['side']

        # Precio medio (mid)
        mid_price = (quoted_bid + quoted_ask) / 2

        # Effective spread (ajustado por lado)
        if trade_side == 'buy':
            effective_spread = 2 * (trade_price - mid_price)
        else:
            effective_spread = 2 * (mid_price - trade_price)

        effective_spread_bps = effective_spread / mid_price * 10000

        effective_spreads.append(effective_spread_bps)

    avg_effective_spread = np.mean(effective_spreads)

    # Comparación
    quality_ratio = avg_effective_spread / quoted_spread_bps if quoted_spread_bps > 0 else 1.0

    if quality_ratio > 1.5:
        logger.warning(
            f"⚠️ Poor execution quality: "
            f"Effective={avg_effective_spread:.1f}bps > Quoted={quoted_spread_bps:.1f}bps"
        )

    return {
        'quoted_spread_bps': quoted_spread_bps,
        'effective_spread_bps': avg_effective_spread,
        'quality_ratio': quality_ratio,
        'execution_quality': 'POOR' if quality_ratio > 1.5 else 'GOOD'
    }
```

### Regla 4 — Price Impact Function

Modelar el impacto permanente como función lineal del volumen firmado (`λ · Q`).

```python
def estimate_permanent_impact(
    self,
    trades: list,
    mid_prices: pd.Series
) -> dict:
    """
    Estimar impacto permanente.

    Hasbrouck: Impacto permanente = λ · Q (lineal con volumen).
    """
    from sklearn.linear_model import LinearRegression

    impact_data = []

    for trade in trades:
        trade_time = trade['timestamp']
        trade_size = trade['quantity']

        # Precio medio antes y después (5 min ventana)
        window_before = 300  # segundos
        window_after = 300

        # Buscar índices
        idx_before = mid_prices.index.get_loc(trade_time) - int(window_before / mid_prices.index.freq.seconds)
        idx_after = mid_prices.index.get_loc(trade_time) + int(window_after / mid_prices.index.freq.seconds)

        if idx_before >= 0 and idx_after < len(mid_prices):
            price_before = mid_prices.iloc[idx_before]
            price_after = mid_prices.iloc[idx_after]

            # Impacto permanente
            permanent_impact = abs(price_after - price_before) / price_before

            impact_data.append({
                'size': trade_size,
                'impact': permanent_impact
            })

    if len(impact_data) < 10:
        logger.warning("Insufficient data for impact estimation")
        return None

    # Regresión: Impact = λ · Size
    df = pd.DataFrame(impact_data)

    X = df[['size']].values
    y = df['impact'].values

    model = LinearRegression(fit_intercept=False)
    model.fit(X, y)

    lambda_impact = model.coef_[0]

    logger.info(f"Permanent impact: λ={lambda_impact:.8f} per share")

    return {
        'lambda': lambda_impact,
        'model': model,
        'r_squared': model.score(X, y)
    }
```

### Regla 5 — VPIN (Volume-Synchronized Probability of Informed Trading)

Usar métricas de desbalance de volumen para predecir toxicidad de flujo y volatilidad inminente.

```python
def calculate_vpin(
    self,
    volume_buys: pd.Series,
    volume_sells: pd.Series,
    window: int = 50
) -> dict:
    """
    Calcular VPIN (Volume-Synchronized PIN).

    Hasbrouck: VPIN alto = toxic flow, volatilidad inminente.
    """
    # Volumen total por barra
    total_volume = volume_buys + volume_sells

    # Desbalance de volumen (abs(buy - sell) / total)
    volume_imbalance = (volume_buys - volume_sells).abs() / total_volume

    # VPIN = media móvil del desbalance
    vpin = volume_imbalance.rolling(window).mean()

    # VPIN actual
    current_vpin = vpin.iloc[-1]

    # Clasificación
    if current_vpin > 0.8:
        toxicity = 'EXTREME'
        logger.critical(f"🚨 EXTREME VPIN: {current_vpin:.3f} - Highly toxic flow")

    elif current_vpin > 0.5:
        toxicity = 'HIGH'
        logger.warning(f"⚠️ High VPIN: {current_vpin:.3f} - Toxic flow detected")

    else:
        toxicity = 'NORMAL'
        logger.info(f"VPIN: {current_vpin:.3f} - Normal flow")

    return {
        'vpin': current_vpin,
        'vpin_series': vpin,
        'toxicity': toxicity,
        'reduce_aggression': current_vpin > 0.5
    }
```

### Regla 6 — Latency Measurement

Medir el tiempo entre OrderSend y OrderAck. Si la varianza es alta, el exchange es inestable.

```python
def measure_latency_stats(
    self,
    order_latencies: list  # [sent_time, ack_time]
) -> dict:
    """
    Medir estadísticas de latencia.

    Hasbrouck: Varianza alta = exchange inestable.
    """
    latencies_ms = [
        (ack - sent).total_seconds() * 1000
        for sent, ack in order_latencies
    ]

    mean_latency = np.mean(latencies_ms)
    std_latency = np.std(latencies_ms)
    p50 = np.percentile(latencies_ms, 50)
    p95 = np.percentile(latencies_ms, 95)
    p99 = np.percentile(latencies_ms, 99)

    # Coeficiente de variación
    cv = std_latency / mean_latency if mean_latency > 0 else 0

    if cv > 0.5:  # Varianza > 50% de media
        logger.warning(
            f"⚠️ High latency variance: CV={cv:.2f} "
            f"(mean={mean_latency:.1f}ms, std={std_latency:.1f}ms)"
        )

        return {
            'stable': False,
            'coefficient_of_variation': cv,
            'action': 'Reduce order rate or switch exchange'
        }

    logger.info(
        f"Latency OK: mean={mean_latency:.1f}ms, "
        f"p95={p95:.1f}ms, CV={cv:.2f}"
    )

    return {
        'stable': True,
        'mean_ms': mean_latency,
        'std_ms': std_latency,
        'p50_ms': p50,
        'p95_ms': p95,
        'p99_ms': p99,
        'cv': cv
    }
```

### Regla 7 — Hidden Liquidity Detection

Inferir órdenes Iceberg si se ejecutan trades en el Best Bid/Ask sin que disminuya la cantidad mostrada.

```python
def detect_hidden_liquidity(
    self,
    order_book_snapshots: pd.DataFrame,
    trades: pd.DataFrame
) -> dict:
    """
    Detectar liquidez oculta (órdenes iceberg).

    Hasbrouck: Trades sin cambio de cantidad = iceberg.
    """
    hidden_liquidity_events = []

    for trade in trades.itertuples():
        trade_time = trade.timestamp
        trade_price = trade.price
        trade_size = trade.size
        trade_side = trade.side

        # Order book en momento del trade
        snapshot = order_book_snapshots[
            order_book_snapshots['timestamp'] == trade_time
        ]

        if len(snapshot) == 0:
            continue

        if trade_side == 'buy':
            best_bid_size = snapshot['bid_size_0'].values[0]
            best_bid_size_next = snapshot['bid_size_1'].values[0]

            # Si se ejecutó pero bid_size no cambió
            if trade_size >= best_bid_size and best_bid_size_next >= best_bid_size:
                hidden_liquidity_events.append({
                    'time': trade_time,
                    'type': 'iceberg_buy',
                    'min_hidden_size': best_bid_size_next - best_bid_size
                })

        elif trade_side == 'sell':
            best_ask_size = snapshot['ask_size_0'].values[0]
            best_ask_size_next = snapshot['ask_size_1'].values[0]

            if trade_size >= best_ask_size and best_ask_size_next >= best_ask_size:
                hidden_liquidity_events.append({
                    'time': trade_time,
                    'type': 'iceberg_sell',
                    'min_hidden_size': best_ask_size_next - best_ask_size
                })

    if len(hidden_liquidity_events) > 0:
        logger.warning(
            f"Detected {len(hidden_liquidity_events)} iceberg orders "
            f"({len(hidden_liquidity_events)/len(trades):.1%} of trades)"
        )

    return {
        'n_icebergs': len(hidden_liquidity_events),
        'events': hidden_liquidity_events
    }
```

### Regla 8 — Short-Term Alpha Decay

Las señales de microestructura decaen en segundos. Ejecutar inmediatamente o cancelar.

```python
def alpha_decay_analysis(
    self,
    signals: list,  # [{'signal': value, 'timestamp': t}, ...]
    subsequent_returns: pd.Series,
    max_horizon_seconds: int = 60
) -> dict:
    """
    Analizar decaimiento de alpha de señales.

    Hasbrouck: Alpha de microestructura decae en segundos.
    """
    decay_analysis = []

    for signal in signals:
        signal_time = signal['timestamp']
        signal_value = signal['signal']

        # Retornos subsequentes
        for horizon in [5, 15, 30, 60]:  # segundos
            end_time = signal_time + pd.Timedelta(seconds=horizon)

            if end_time in subsequent_returns.index:
                ret = subsequent_returns.loc[end_time]

                decay_analysis.append({
                    'horizon_sec': horizon,
                    'signal': signal_value,
                    'return': ret,
                    'signal_decay': signal_value * ret  # Correlación
                })

    # Analizar decaimiento
    df = pd.DataFrame(decay_analysis)

    if len(df) == 0:
        return None

    decay_by_horizon = df.groupby('horizon_sec')['signal_decay'].mean()

    # Horizonte óptimo (máxima correlación)
    optimal_horizon = decay_by_horizon.idxmax()

    logger.info(
        f"Alpha decay: Optimal horizon={optimal_horizon}s, "
        f"decay={decay_by_horizon.to_dict()}"
    )

    return {
        'optimal_horizon_seconds': optimal_horizon,
        'decay_curve': decay_by_horizon.to_dict(),
        'execute_within': optimal_horizon
    }
```

### Regla 9 — Adverse Selection Risk (Realized Spread)

Calcular el "Realized Spread" (Beneficio del Market Maker). Si es negativo, tus órdenes Limit están siendo "atropelladas" por traders informados.

```python
def calculate_adverse_selection(
    self,
    executed_trades: list,
    future_returns: pd.Series,
    offset_seconds: int = 300
) -> dict:
    """
    Calcular riesgo de selección adversa.

    Hasbrouck: Realized spread negativo = adverse selection.
    """
    realized_spreads = []

    for trade in executed_trades:
        trade_time = trade['timestamp']
        execution_price = trade['price']
        mid_at_execution = trade['mid_price']

        # Retorno futuro (5 min después)
        future_time = trade_time + pd.Timedelta(seconds=offset_seconds)

        if future_time in future_returns.index:
            future_mid = mid_at_execution * (1 + future_returns.loc[future_time])

            # Realized spread = (mid_future - execution) / mid_execution
            if trade['side'] == 'buy':
                realized_spread = (future_mid - execution_price) / mid_at_execution
            else:
                realized_spread = (execution_price - future_mid) / mid_at_execution

            realized_spreads.append(realized_spread)

    avg_realized_spread = np.mean(realized_spreads)

    if avg_realized_spread < 0:
        logger.error(
            f"❌ ADVERSE SELECTION: Realized spread={avg_realized_spread:.2%}. "
            f"Losing to informed traders."
        )

        return {
            'adverse_selection': True,
            'realized_spread': avg_realized_spread,
            'action': 'Widen spreads or reduce quoting'
        }

    logger.info(
        f"✅ No adverse selection: Realized spread={avg_realized_spread:.2%}"
    )

    return {
        'adverse_selection': False,
        'realized_spread': avg_realized_spread
    }
```

### Regla 10 — Volatility Decomposition

Separar volatilidad en componente eficiente (información) y transitoria (ruido/fricción).

```python
def decompose_volatility(
    self,
    mid_prices: pd.Series,
    trade_prices: pd.Series,
    window: int = 100
) -> dict:
    """
    Descomponer volatilidad en eficiente vs transitoria.

    Hasbrouck: Componentes de volatilidad.
    """
    # Volatilidad del mid-price (información)
    mid_returns = mid_prices.pct_change()
    efficient_vol = mid_returns.rolling(window).std()

    # Volatilidad de trade prices (incluye fricción)
    trade_returns = trade_prices.pct_change()
    total_vol = trade_returns.rolling(window).std()

    # Volatilidad transitoria = total - eficiente
    transitory_vol = np.sqrt(total_vol ** 2 - efficient_vol ** 2)

    # Componentes
    current_efficient = efficient_vol.iloc[-1]
    current_total = total_vol.iloc[-1]
    current_transitory = transitory_vol.iloc[-1]

    efficient_ratio = (current_efficient / current_total) ** 2
    transitory_ratio = (current_transitory / current_total) ** 2

    logger.info(
        f"Vol decomposition: Total={current_total:.2%}, "
        f"Efficient={current_efficient:.2%} ({efficient_ratio:.0%}), "
        f"Transitory={current_transitory:.2%} ({transitory_ratio:.0%})"
    )

    return {
        'efficient_vol': current_efficient,
        'transitory_vol': current_transitory,
        'total_vol': current_total,
        'efficient_ratio': efficient_ratio,
        'transitory_ratio': transitory_ratio
    }
```

### Regla 11 — Autocorrelation of Order Flow

Si las órdenes de compra están altamente autocorrelacionadas, esperar a que termine la ráfaga antes de vender (Ride the wave).

```python
def detect_order_flow_clustering(
    self,
    order_flow: pd.Series,  # +1 for buy, -1 for sell
    window: int = 20
) -> dict:
    """
    Detectar clustering de order flow.

    Hasbrouck: Autocorrelación alta = ráfaga, ride the wave.
    """
    # Autocorrelación de order flow
    autocorr_values = []

    for lag in range(1, window + 1):
        autocorr = order_flow.autocorr(lag)
        autocorr_values.append(autocorr)

    # ¿Hay autocorrelación significativa?
    significant_lags = [
        (lag + 1, ac) for lag, ac in enumerate(autocorr_values)
        if abs(ac) > 0.3  # Threshold
    ]

    if len(significant_lags) > 0:
        logger.info(
            f"Order flow clustering: {len(significant_lags)} lags "
            f"with |autocorr| > 0.3"
        )

        return {
            'clustering': True,
            'significant_lags': significant_lags,
            'recommendation': 'Wait for burst to end before fading'
        }

    return {'clustering': False}
```

### Regla 12 — Execution Benchmarks

Comparar precio de ejecución vs Arrival Price, VWAP y TWAP. Reportar desviación en puntos básicos (bps).

```python
def benchmark_execution(
    self,
    fills: list,
    arrival_price: float,
    vwap: float,
    twap: float
) -> dict:
    """
    Benchmarkear ejecución vs estándares.

    Hasbrouck: Arrival price es el benchmark principal.
    """
    # Calcular precio promedio de ejecución
    total_volume = sum(f['quantity'] for f in fills)
    avg_execution_price = sum(f['price'] * f['quantity'] for f in fills) / total_volume

    # Slippage vs benchmarks
    arrival_slippage_bps = (avg_execution_price - arrival_price) / arrival_price * 10000
    vwap_slippage_bps = (avg_execution_price - vwap) / vwap * 10000
    twap_slippage_bps = (avg_execution_price - twap) / twap * 10000

    logger.info(
        f"Execution benchmarks (bps): "
        f"Arrival={arrival_slippage_bps:.1f}, "
        f"VWAP={vwap_slippage_bps:.1f}, "
        f"TWAP={twap_slippage_bps:.1f}"
    )

    return {
        'arrival_slippage_bps': arrival_slippage_bps,
        'vwap_slippage_bps': vwap_slippage_bps,
        'twap_slippage_bps': twap_slippage_bps,
        'avg_execution_price': avg_execution_price
    }
```

### Regla 13 — Quote Stuffing Detection

Si la tasa de updates de quotes excede un umbral humano (ej. 50/seg) sin trades, filtrar esos datos como ruido HFT.

```python
def detect_quote_stuffing(
    self,
    quote_updates: pd.DataFrame,
    trades: pd.DataFrame,
    max_updates_per_sec: int = 50,
    window_seconds: int = 1
) -> dict:
    """
    Detectar quote stuffing (spam de quotes).

    Hasbrouck: Muchas quotes sin trades = manipulación HFT.
    """
    # Contar updates por segundo
    quote_counts = quote_updates.set_index('timestamp').resample(f'{window_seconds}s').size()

    # Contar trades por segundo
    trade_counts = trades.set_index('timestamp').resample(f'{window_seconds}s').size()

    # Combinar
    combined = pd.DataFrame({
        'quote_count': quote_counts,
        'trade_count': trade_counts
    }).fillna(0)

    # Detectar stuffing: muchos quotes, pocos trades
    combined['is_stuffing'] = (
        (combined['quote_count'] > max_updates_per_sec) &
        (combined['trade_count'] == 0)
    )

    stuffing_periods = combined[combined['is_stuffing']]

    if len(stuffing_periods) > 0:
        logger.warning(
            f"⚠️ Quote stuffing detected: {len(stuffing_periods)} periods "
            f"({len(stuffing_periods)/len(combined):.1%} of time)"
        )

        return {
            'stuffing_detected': True,
            'affected_periods': len(stuffing_periods),
            'action': 'Filter or slow down during these periods'
        }

    return {'stuffing_detected': False}
```

### Regla 14 — Limit Order Book Slope

Calcular la pendiente de la liquidez alrededor del spread. Pendiente plana = Fácil de mover el precio (Baja Resiliencia).

```python
def calculate_lob_slope(
    self,
    order_book: dict,
    n_levels: int = 5
) -> dict:
    """
    Calcular pendiente del libro de órdenes.

    Hasbrouck: Pendiente plana = baja resiliencia.
    """
    # Extraer bids y asks con precios y cantidades
    bids = order_book['bids'][:n_levels]
    asks = order_book['asks'][:n_levels]

    # Calcular pendientes
    bid_prices = [b['price'] for b in bids]
    bid_volumes = [b['quantity'] for b in bids]

    ask_prices = [a['price'] for a in asks]
    ask_volumes = [a['quantity'] for a in asks]

    # Regresión: Volume vs Distance from mid
    mid_price = (bid_prices[0] + ask_prices[0]) / 2

    bid_distances = [(mid_price - p) / mid_price for p in bid_prices]
    ask_distances = [(p - mid_price) / mid_price for p in ask_prices]

    # Ajustar línea
    from sklearn.linear_model import LinearRegression

    # Bid slope
    bid_lr = LinearRegression()
    bid_lr.fit(np.array(bid_distances).reshape(-1, 1), bid_volumes)
    bid_slope = bid_lr.coef_[0]

    # Ask slope
    ask_lr = LinearRegression()
    ask_lr.fit(np.array(ask_distances).reshape(-1, 1), ask_volumes)
    ask_slope = ask_lr.coef_[0]

    # Slope promedio
    avg_slope = (abs(bid_slope) + abs(ask_slope)) / 2

    if avg_slope < 1000:  # Pendiente muy plana (units depend on scale)
        logger.warning(
            f"⚠️ Flat LOB: Slope={avg_slope:.0f} - Low resiliency"
        )

    return {
        'bid_slope': bid_slope,
        'ask_slope': ask_slope,
        'avg_slope': avg_slope,
        'resilience': 'LOW' if avg_slope < 1000 else 'NORMAL'
    }
```

### Regla 15 — Smart Order Routing (SOR)

Enviar órdenes al mercado con mayor probabilidad de llenado (Fill Probability), no necesariamente al mejor precio visible si la liquidez es "fantasma".

```python
def smart_order_routing(
    self,
    order: dict,
    available_exchanges: list,
    exchange_order_books: dict
) -> dict:
    """
    Smart Order Routing considerando fill probability.

    Hasbrouck: Mejor probabilidad de llenado > mejor precio.
    """
    symbol = order['symbol']
    side = order['side']
    quantity = order['quantity']

    routing_scores = []

    for exchange in available_exchanges:
        ob = exchange_order_books[exchange]

        if side == 'buy':
            # Liquidez disponible en asks
            available_liquidity = sum(
                level['quantity'] for level in ob['asks']
            )

            # Mejor precio
            best_price = ob['asks'][0]['price']

        else:  # sell
            available_liquidity = sum(
                level['quantity'] for level in ob['bids']
            )

            best_price = ob['bids'][0]['price']

        # Fill probability
        fill_probability = min(1.0, available_liquidity / quantity)

        # Score = probabilidad ponderada por precio
        # (preferimos alta probabilidad)
        score = fill_probability * 0.7 + (10000 / best_price) * 0.3

        routing_scores.append({
            'exchange': exchange,
            'score': score,
            'fill_probability': fill_probability,
            'available_liquidity': available_liquidity,
            'best_price': best_price
        })

    # Seleccionar mejor exchange
    best = max(routing_scores, key=lambda x: x['score'])

    logger.info(
        f"SOR routing: {best['exchange']} "
        f"(score={best['score']:.2f}, fill_prob={best['fill_probability']:.2f})"
    )

    return {
        'selected_exchange': best['exchange'],
        'routing_analysis': routing_scores
    }
```

---

## Aplicación Práctica

### Pipeline de Microestructura Avanzada

```python
def microstructure_execution_pipeline(
    self,
    symbol: str,
    order_side: str,
    order_quantity: float,
    exchanges: list
) -> dict:
    """
    Pipeline de ejecución con microestructura avanzada.
    """
    # 1. Smart Order Routing
    order_books = {ex: self.get_order_book(ex, symbol) for ex in exchanges}

    sor_result = self.smart_order_routing(
        {'symbol': symbol, 'side': order_side, 'quantity': order_quantity},
        exchanges,
        order_books
    )

    selected_exchange = sor_result['selected_exchange']

    # 2. Calcular VPIN antes de ejecutar
    volume_data = self.get_volume_data(selected_exchange, symbol, hours=1)
    vpin_result = self.calculate_vpin(
        volume_data['buys'],
        volume_data['sells']
    )

    # 3. Ajustar agresividad según VPIN
    if vpin_result['reduce_aggression']:
        # Ensanchar spreads si flujo tóxico
        logger.info("Widening spreads due to high VPIN")
        spread_multiplier = 1.5
    else:
        spread_multiplier = 1.0

    # 4. Ejecutar orden
    execution_result = self.execute_order(
        symbol, order_side, order_quantity,
        selected_exchange,
        spread_multiplier=spread_multiplier
    )

    # 5. Analizar calidad de ejecución
    quality_result = self.calculate_execution_quality(
        execution_result['fills'],
        order_books[selected_exchange]
    )

    return {
        'exchange': selected_exchange,
        'vpin': vpin_result['vpin'],
        'execution_quality': quality_result,
        'fills': execution_result['fills']
    }
```
