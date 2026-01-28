# 🟠 29. "Algorithmic Trading & DMA" - Barry Johnson

## REGLAS DE EJECUCIÓN ALGORÍTMICA Y MICROESTRUCTURA

**Regla 29.1 — Modelo de Impacto Cuadrático**

Claude DEBE estimar el impacto de mercado ANTES de ejecutar.

**El costo NO es lineal.**

```python
def estimate_market_impact(
    self,
    order_size: float,
    adv: float,  # Average Daily Volume
    volatility: float,
    participation_rate: float = 0.10
) -> dict:
    """
    Estimar impacto de mercado usando modelo cuadrático.

    Barry Johnson: Impact = σ · √(Size/ADV).
    """
    # Tamaño relativo de la orden
    size_ratio = order_size / adv

    # Impacto cuadrático (Almgren-Chriss model)
    # Impacto temporal + impacto permanente
    temporary_impact = volatility * np.sqrt(size_ratio)

    # Impacto permanente (lineal con participation rate)
    permanent_impact = volatility * participation_rate * size_ratio

    total_impact_bps = (temporary_impact + permanent_impact) * 10000

    # Validar si impacto es aceptable
    max_acceptable_impact_bps = 5.0  # 5 bps

    if total_impact_bps > max_acceptable_impact_bps:
        logger.warning(
            f"⚠️ Market impact too high: {total_impact_bps:.1f} bps "
            f"> {max_acceptable_impact_bps} bps"
        )
        # Sugerir splitting
        recommended_slices = max(1, int(np.ceil(size_ratio / 0.05)))
        logger.info(f"Recommend splitting into {recommended_slices} slices")

    return {
        'temporary_impact_bps': temporary_impact * 10000,
        'permanent_impact_bps': permanent_impact * 10000,
        'total_impact_bps': total_impact_bps,
        'size_ratio': size_ratio,
        'acceptable': total_impact_bps <= max_acceptable_impact_bps
    }
```

**Regla 29.2 — Smart Order Routing (SOR)**

```python
class SmartOrderRouter:
    """
    Smart Order Router para fragmented liquidity.

    Barry Johnson: En Crypto, consolidar liquidez de múltiples exchanges.
    """

    def __init__(self, exchanges: List[str]):
        self.exchanges = exchanges
        self.order_books = {}  # exchange -> OrderBook

    def route_order(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        min_price_levels: int = 3
    ) -> List[dict]:
        """
        Rutea inteligentemente entre exchanges.
        """
        # Consolidar order books
        consolidated_bids = []
        consolidated_asks = []

        for exchange in self.exchanges:
            order_book = self.order_books[exchange].get(symbol)

            if side == 'BUY':
                # Agregar asks (ofertas de venta)
                for price, quantity in order_book['asks'][:min_price_levels]:
                    consolidated_asks.append({
                        'exchange': exchange,
                        'price': price,
                        'quantity': quantity
                    })

            elif side == 'SELL':
                # Agregar bids (ofertas de compra)
                for price, quantity in order_book['bids'][:min_price_levels]:
                    consolidated_bids.append({
                        'exchange': exchange,
                        'price': price,
                        'quantity': quantity
                    })

        # Ordenar por mejor precio
        if side == 'BUY':
            consolidated_asks.sort(key=lambda x: x['price'])
            order_book = consolidated_asks
        else:
            consolidated_bids.sort(key=lambda x: x['price'], reverse=True)
            order_book = consolidated_bids

        # Crear child orders
        child_orders = []
        remaining = total_quantity

        for level in order_book:
            if remaining <= 0:
                break

            # Tomar liquidez disponible
            qty = min(level['quantity'], remaining)

            child_orders.append({
                'exchange': level['exchange'],
                'side': side,
                'quantity': qty,
                'price': level['price']
            })

            remaining -= qty

        if remaining > 0:
            logger.warning(
                f"⚠️ Insufficient liquidity: {remaining:.4f} "
                f"remaining unfilled"
            )

        logger.info(
            f"SOR routed {total_quantity:.4f} to "
            f"{len(child_orders)} exchanges"
        )

        return child_orders
```

**Regla 29.3 — Detección de Gaming (Antisignaling)**

```python
def detect_order_gaming(
    self,
    order: Order,
    fill_progress: float,
    time_since_submission: float,
    avg_fill_time: float
) -> bool:
    """
    Detectar si están jugando contra tu orden.

    Barry Johnson: Si tarda demasiado → cancelar y esperar.
    """
    gaming_detected = False
    reasons = []

    # 1. Fill rate demasiado lento
    if time_since_submission > avg_fill_time * 3:
        if fill_progress < 0.5:  # Menos del 50% llenado
            gaming_detected = True
            reasons.append("Slow fill rate")

    # 2. Spoofing detection
    # Si el order book se mueve contra ti justo después de tu orden
    if self.detect_spoofing(order.symbol, order.side):
        gaming_detected = True
        reasons.append("Potential spoofing detected")

    # 3. Liquidity disappearing
    current_liquidity = self.get_liquidity_at_price(
        order.symbol,
        order.price,
        order.side
    )

    initial_liquidity = order.initial_liquidity

    if current_liquidity < initial_liquidity * 0.3:
        gaming_detected = True
        reasons.append("Liquidity evaporated")

    if gaming_detected:
        logger.warning(
            f"🎮 Gaming detected: {', '.join(reasons)}. "
            f"Cancelling order {order.id}"
        )
        self.cancel_order(order.id)
        # Inertia: esperar antes de re-enviar
        return True

    return False
```

**Regla 29.4 — Órdenes Post-Only (Maker-only)**

```python
def submit_post_only_order(
    self,
    symbol: str,
    side: str,
    quantity: float,
    price: float
) -> Order:
    """
    Orden Post-Only: Solo Maker, nunca Taker.

    Barry Johnson: Maker paga 0 fees, Taker paga fees.
    """
    order = Order(
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        order_type='LIMIT',
        time_in_force='POST_ONLY'  # Maker-only
    )

    # Si crossed, reject o adjust
    if self.would_cross_spread(order):
        logger.info(
            f"Order would cross spread. Adjusting price..."
        )

        if side == 'BUY':
            # Ajustar al mejor bid actual
            best_bid = self.get_best_bid(symbol)
            order.price = best_bid
        else:
            # Ajustar al mejor ask actual
            best_ask = self.get_best_ask(symbol)
            order.price = best_ask

        logger.info(f"Adjusted to post-only price: {order.price}")

    self.submit_order(order)

    return order
```

**Regla 29.5 — Iceberg Orders**

```python
class IcebergOrder:
    """
    Iceberg: Orden grande dividida en piezas ocultas.

    Barry Johnson: Ocultar tamaño real del order.
    """

    def __init__(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        display_quantity: float,
        price: float
    ):
        self.symbol = symbol
        self.side = side
        self.total_quantity = total_quantity
        self.display_quantity = display_quantity
        self.price = price
        self.remaining = total_quantity
        self.child_orders = []

    def execute(self, exchange) -> List[Fill]:
        """
        Ejecutar iceberg incrementalmente.
        """
        all_fills = []

        while self.remaining > 0:
            # Calcular tamaño a mostrar
            show_quantity = min(self.display_quantity, self.remaining)

            # Crear child order
            child_order = LimitOrder(
                symbol=self.symbol,
                side=self.side,
                quantity=show_quantity,
                price=self.price
            )

            # Submit
            exchange.submit_order(child_order)
            self.child_orders.append(child_order)

            # Esperar fill
            fills = exchange.wait_for_fill(child_order)

            for fill in fills:
                all_fills.append(fill)
                self.remaining -= fill.quantity

                # Loggear progreso
                filled_pct = (self.total_quantity - self.remaining) / self.total_quantity
                logger.info(
                    f"Iceberg progress: {filled_pct:.1%} "
                    f"({(self.total_quantity - self.remaining):.2f}/"
                    f"{self.total_quantity:.2f})"
                )

            # Si no llenó, cancelar y pausar
            if child_order.status != 'FILLED':
                exchange.cancel_order(child_order.id)

                # Detectar si debemos continuar
                if self.should_pause():
                    logger.info("Pausing iceberg execution")
                    break

        return all_fills
```

**Regla 29.6 — TWAP Adaptativo**

```python
def adaptive_twap(
    self,
    symbol: str,
    total_quantity: float,
    start_time: datetime,
    end_time: datetime,
    current_time: datetime
) -> float:
    """
    Time-Weighted Average Price con velocidad adaptativa.

    Barry Johnson: Ajustar según volatilidad horaria.
    """
    # Tiempo restante
    time_remaining = (end_time - current_time).total_seconds() / 60  # minutos
    total_duration = (end_time - start_time).total_seconds() / 60

    # Volatilidad actual
    current_vol = self.get_current_volatility(symbol, lookback=60)

    # Volatilidad promedio histórica para esta hora
    hour = current_time.hour
    historical_vol = self.get_historical_hourly_volatility(symbol, hour)

    # Ajustar velocidad según volatilidad
    vol_ratio = current_vol / historical_vol if historical_vol > 0 else 1.0

    if vol_ratio > 1.5:
        # Alta volatilidad → ir más lento
        speed_factor = 0.5
        logger.info("High volatility → slowing down TWAP")

    elif vol_ratio < 0.7:
        # Baja volatilidad → ir más rápido
        speed_factor = 1.5
        logger.info("Low volatility → speeding up TWAP")

    else:
        speed_factor = 1.0

    # Participación objetivo
    base_participation = total_quantity / total_duration  # por minuto
    adjusted_participation = base_participation * speed_factor

    return adjusted_participation
```

**Regla 29.7 — Slippage Tolerance Dinámico**

```python
def dynamic_slippage_tolerance(
    self,
    symbol: str,
    order_type: str,
    side: str
) -> float:
    """
    Slippage tolerable según volatilidad del instrumento.

    Barry Johnson: No usar 0.05% fijo para todo.
    """
    # Volatilidad realizada (20 días)
    realized_vol = self.get_realized_volatility(symbol, lookback=20)

    # ATR actual
    atr = self.get_atr(symbol, period=14)
    current_price = self.get_current_price(symbol)
    atr_pct = atr / current_price

    # Base slippage
    base_slippage = {
        'LIMIT': 0.0,      # Limit orders: 0 slippage
        'MARKET': 0.001,   # Market: 0.1%
        'STOP_MARKET': 0.002  # Stop market: 0.2%
    }

    # Ajustar según volatilidad
    vol_multiplier = max(1.0, realized_vol / 0.15)  # 15% vol base

    slippage = base_slippage.get(order_type, 0.001) * vol_multiplier

    # Más tolerancia enCrypto
    if self.is_crypto(symbol):
        slippage *= 2.0

    logger.info(
        f"Dynamic slippage for {symbol}: {slippage:.2%} "
        f"(vol={realized_vol:.1%})"
    )

    return slippage
```

**Regla 29.8 — Fill Probability Tracking**

```python
def track_fill_probability(
    self,
    order: Order,
    first_fill_pct: float
) -> None:
    """
    Trackear qué porcentaje se llenó en el primer intento.

    Barry Johnson: Si < 50%, bajar agresividad.
    """
    # Registrar fill probability
    self.fill_history[order.symbol].append(first_fill_pct)

    # Promedio de últimos N órdenes
    recent_fills = self.fill_history[order.symbol][-20:]

    if len(recent_fills) >= 10:
        avg_fill_pct = np.mean(recent_fills)

        if avg_fill_pct < 0.5:
            logger.warning(
                f"⚠️ Low fill probability: {avg_fill_pct:.1%} "
                f"for {order.symbol}"
            )

            # Bajar agresividad del bot
            self.reduce_aggression(order.symbol, factor=0.7)

        elif avg_fill_pct > 0.8:
            logger.info(
                f"✅ High fill probability: {avg_fill_pct:.1%} "
                f"for {order.symbol}"
            )

            # Podemos aumentar agresividad
            self.increase_aggression(order.symbol, factor=1.2)
```

**Regla 29.9 — Varianza de Ejecución**

```python
def measure_execution_variance(
    self,
    arrival_price: float,
    final_price: float,
    benchmark_volatility: float
) -> dict:
    """
    Mide diferencia entre arrival price y precio final.

    Barry Johnson: Si > 1 SD, pausar estrategia.
    """
    # Slippage realizado
    execution_slippage_bps = (
        (final_price - arrival_price) / arrival_price * 10000
    )

    # Desviación estándar esperada
    expected_sd_bps = benchmark_volatility * 10000

    # Z-score
    z_score = abs(execution_slippage_bps) / expected_sd_bps

    if z_score > 1.0:
        logger.warning(
            f"⚠️ Execution variance high: {execution_slippage_bps:.1f} bps "
            f"({z_score:.1f} SD)"
        )

        if z_score > 2.0:
            logger.critical(
                f"🚨 CRITICAL: Execution variance > 2 SD. "
                f"Pausing strategy."
            )
            self.pause_strategy()

    return {
        'slippage_bps': execution_slippage_bps,
        'z_score': z_score,
        'acceptable': z_score <= 1.0
    }
```

**Regla 29.10 — Re-pegging Lógico**

```python
def should_repeg(
    self,
    order: Order,
    current_market_price: float,
    momentum: float
) -> bool:
    """
    Decidir si "perseguir" el precio con la orden.

    Barry Johnson: Solo re-peg si momentum favorece.
    """
    price_distance = abs(current_market_price - order.price) / order.price

    # Si el precio se alejó mucho
    if price_distance > 0.001:  # 0.1%
        # Chequear momentum
        if order.side == 'BUY':
            # Estamos comprando: ¿el precio sigue subiendo?
            momentum_favors = momentum > 0

        else:  # SELL
            # Estamos vendiendo: ¿el precio sigue bajando?
            momentum_favors = momentum < 0

        if momentum_favors:
            logger.info(
                f"Momentum favors re-pegging: {momentum:.3f}"
            )
            return True

        else:
            logger.info(
                f"Momentum against us: cancel order. "
                f"Momentum={momentum:.3f}"
            )
            return False

    # Precio todavía cerca
    return False
```

**Regla 29.11 — Order Duration Limit**

```python
def enforce_order_duration(
    self,
    order: Order,
    max_duration_seconds: int = 60
) -> None:
    """
    Ninguna orden Limit debe vivir sin revisión.

    Barry Johnson: Crypto requiere revisión cada 60s.
    """
    order_age = (datetime.now() - order.submitted_at).total_seconds()

    if order_age > max_duration_seconds:
        logger.warning(
            f"⚠️ Order {order.id} age: {order_age:.0f}s "
            f"> {max_duration_seconds}s limit"
        )

        # Revisar orden
        if order.status == 'OPEN':
            # Opciones:
            # 1. Cancelar
            # 2. Re-peg
            # 3. Convertir a market

            # Decidir basado en estado actual
            current_price = self.get_mid_price(order.symbol)

            if abs(order.price - current_price) / current_price > 0.002:
                # Precio se movió mucho → cancelar
                logger.info("Cancelling stale order")
                self.cancel_order(order.id)

            else:
                # Precio cercano → re-peg
                logger.info("Re-pegging stale order")
                self.cancel_order(order.id)
                self.submit_limit_order(
                    symbol=order.symbol,
                    side=order.side,
                    quantity=order.remaining_quantity,
                    price=current_price * (0.999 if order.side == 'BUY' else 1.001)
                )
```

**Regla 29.12 — VWAP Benchmarking**

```python
def benchmark_vwap_execution(
    self,
    fills: List[Fill],
    session_start: datetime,
    session_end: datetime,
    symbol: str
) -> dict:
    """
    Comparar ejecución contra VWAP de la sesión.

    Barry Johnson: Evaluar proveedores de liquidez.
    """
    # Calcular VWAP de la ejecución
    total_volume = sum(f.quantity for f in fills)
    vwap_execution = sum(f.price * f.quantity for f in fills) / total_volume

    # Calcular VWAP de mercado
    market_data = self.get_ohlcv(symbol, session_start, session_end)

    # VWAP = Σ(Price × Volume) / Σ(Volume)
    vwap_market = (
        (market_data['close'] * market_data['volume']).sum() /
        market_data['volume'].sum()
    )

    # Comparación
    diff_bps = (vwap_execution - vwap_market) / vwap_market * 10000

    if diff_bps < 0:
        logger.info(
            f"✅ Beat VWAP: {diff_bps:.1f} bps "
            f"(Exec: {vwap_execution:.2f}, Market: {vwap_market:.2f})"
        )
    else:
        logger.warning(
            f"❌ Underperformed VWAP: {diff_bps:.1f} bps "
            f"(Exec: {vwap_execution:.2f}, Market: {vwap_market:.2f})"
        )

    return {
        'execution_vwap': vwap_execution,
        'market_vwap': vwap_market,
        'diff_bps': diff_bps,
        'improvement': diff_bps < 0
    }
```

**Regla 29.13 — Order Book Imbalance**

```python
def detect_order_book_imbalance(
    self,
    symbol: str,
    depth_levels: int = 10
) -> dict:
    """
    Detectar desbalance en el order book (L2).

    Barry Johnson: Pausar compras si hay muro de ventas.
    """
    order_book = self.get_order_book(symbol, depth=depth_levels)

    # Volumen en bids (compras)
    bid_volume = sum(level['quantity'] for level in order_book['bids'][:depth_levels])

    # Volumen en asks (ventas)
    ask_volume = sum(level['quantity'] for level in order_book['asks'][:depth_levels])

    # Imbalance ratio
    total_volume = bid_volume + ask_volume

    if total_volume == 0:
        return {'imbalance': 0, 'signal': 'NEUTRAL'}

    imbalance = (bid_volume - ask_volume) / total_volume

    # Interpretar
    if imbalance > 0.3:
        signal = 'STRONG_BUY'
        logger.info(f"🟢 Strong buy imbalance: {imbalance:.2f}")

    elif imbalance > 0.1:
        signal = 'BUY'
        logger.info(f"Buy imbalance: {imbalance:.2f}")

    elif imbalance < -0.3:
        signal = 'STRONG_SELL'
        logger.warning(f"🔴 Strong sell imbalance: {imbalance:.2f}")

    elif imbalance < -0.1:
        signal = 'SELL'
        logger.warning(f"Sell imbalance: {imbalance:.2f}")

    else:
        signal = 'NEUTRAL'

    return {
        'imbalance': imbalance,
        'bid_volume': bid_volume,
        'ask_volume': ask_volume,
        'signal': signal
    }
```

**Regla 29.14 — Minimum Quote Life**

```python
def filter_hft_noise(
    self,
    price_updates: pd.DataFrame,
    min_quote_life_ms: int = 20
) -> pd.DataFrame:
    """
    Ignorar cambios de precio que duran < 20ms.

    Barry Johnson: Filtrar spoofing de HFT.
    """
    # Detectar cambios de precio
    price_changes = price_updates[price_updates['price'].diff() != 0]

    # Calcular duración de cada nivel de precio
    price_changes['duration_ms'] = price_changes['timestamp'].diff().fillna(0)

    # Filtrar cambios muy cortos
    filtered = price_changes[
        price_changes['duration_ms'] >= min_quote_life_ms
    ]

    noise_ratio = 1 - len(filtered) / len(price_changes)

    if noise_ratio > 0.5:
        logger.info(
            f"Filtered {noise_ratio:.1%} noise quotes "
            f"(< {min_quote_life_ms}ms)"
        )

    return filtered
```
