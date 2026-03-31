# 📄 Papers Fundamentales - Algorithmic Trading and DMA (Barry Johnson, 2010)

## Ejecución Directa al Mercado y Gestión de Órdenes Algorítmicas

**Contexto:** Execution Algorithms y Low-Latency Trading.

Barry Johnson estableció el estándar para la ejecución algorítmica profesional, cubriendo DMA, slicing de órdenes, Smart Order Routing y gestión de impacto de mercado.

---

### Regla 1 — DMA Routing (Direct Market Access)

Enviar órdenes directamente al exchange con menor latencia.

```python
def dma_router(
    self,
    order: dict,
    venue_priorities: List[str]
) -> dict:
    """
    Enviar orden por ruta directa al exchange.

    Johnson: DMA = latencia mínima, sin intermediarios.
    """
    # Seleccionar venue con prioridad
    selected_venue = None

    for venue in venue_priorities:
        # Verificar disponibilidad
        if self.check_venue_availability(venue):
            # Verificar latencia
            latency_ms = self.get_venue_latency(venue)

            if latency_ms < 10:  # < 10ms
                selected_venue = venue
                break

    if selected_venue is None:
        # Fallback a broker
        return {
            'method': 'broker',
            'latency_ms': None,
            'warning': 'No DMA available'
        }

    # Construir mensaje FIX
    fix_message = self.build_fix_message(
        order_type=order['type'],
        symbol=order['symbol'],
        quantity=order['quantity'],
        price=order.get('price'),
        venue=selected_venue
    )

    # Enviar
    start_time = pd.Timestamp.now()

    order_id = self.send_fix_order(
        fix_message,
        venue=selected_venue,
        connection='direct'
    )

    end_time = pd.Timestamp.now()
    actual_latency = (end_time - start_time).total_seconds() * 1000

    logger.info(
        f"DMA Route: {order['symbol']} → {selected_venue}, "
        f"latency={actual_latency:.2f}ms, order_id={order_id}"
    )

    return {
        'method': 'DMA',
        'venue': selected_venue,
        'order_id': order_id,
        'latency_ms': actual_latency,
        'status': 'submitted'
    }
```

### Regla 2 — Slice-and-Dice (Child Orders)

Fragmentar órdenes grandes en trozos < 5% del volumen del minuto.

```python
def slice_and_dice(
    self,
    parent_order: dict,
    max_participation: float = 0.05
) -> List[dict]:
    """
    Dividir orden grande en child orders.

    Johnson: Slicing = minimizar impacto de mercado.
    """
    symbol = parent_order['symbol']
    total_quantity = parent_order['quantity']
    side = parent_order['side']

    # Obtener volumen promedio por minuto
    avg_minute_volume = self.get_average_volume(
        symbol,
        minutes=20
    )

    # Tamaño máximo de child order
    max_child_size = avg_minute_volume * max_participation

    # Número de child orders
    n_children = max(1, int(np.ceil(total_quantity / max_child_size)))

    # Tamaño de cada child
    child_size = total_quantity / n_children

    # Generar child orders
    child_orders = []

    for i in range(n_children):
        child_order = {
            'parent_id': parent_order['order_id'],
            'child_id': f"{parent_order['order_id']}_C{i}",
            'symbol': symbol,
            'side': side,
            'quantity': child_size,
            'type': parent_order.get('child_type', 'limit'),
            'status': 'pending',
            'sequence': i
        }

        child_orders.append(child_order)

    logger.info(
        f"Slice-and-dice: {total_quantity:.0f} shares → {n_children} children, "
        f"max_participation={max_participation:.1%}, "
        f"child_size={child_size:.0f}"
    )

    return child_orders
```

### Regla 3 — Iceberg Order Detection

Si volumen ejecutado > volumen visible, hay orden iceberg.

```python
def detect_iceberg_orders(
    self,
    lob_snapshot: dict,
    threshold_ratio: float = 2.0
) -> dict:
    """
    Detectar órdenes iceberg en el libro.

    Johnson: Iceberg = liquidez oculta, cuidado.
    """
    detected_icebergs = []

    # Analizar bid levels
    for level in range(10):
        bid_price = lob_snapshot['bids'][level]['price']
        bid_visible = lob_snapshot['bids'][level]['quantity']

        # Calcular volumen ejecutado recientemente a este precio
        executed_at_level = self.get_executed_volume_at_price(
            bid_price,
            minutes=1
        )

        if executed_at_level > 0:
            ratio = executed_at_level / bid_visible

            if ratio > threshold_ratio:
                detected_icebergs.append({
                    'side': 'bid',
                    'level': level,
                    'price': bid_price,
                    'visible': bid_visible,
                    'executed': executed_at_level,
                    'estimated_hidden': executed_at_level - bid_visible,
                    'ratio': ratio
                })

    # Analizar ask levels (similar)
    for level in range(10):
        ask_price = lob_snapshot['asks'][level]['price']
        ask_visible = lob_snapshot['asks'][level]['quantity']

        executed_at_level = self.get_executed_volume_at_price(
            ask_price,
            minutes=1
        )

        if executed_at_level > 0:
            ratio = executed_at_level / ask_visible

            if ratio > threshold_ratio:
                detected_icebergs.append({
                    'side': 'ask',
                    'level': level,
                    'price': ask_price,
                    'visible': ask_visible,
                    'executed': executed_at_level,
                    'estimated_hidden': executed_at_level - ask_visible,
                    'ratio': ratio
                })

    if detected_icebergs:
        logger.warning(
            f"⚠️ Icebergs detected: {len(detected_icebergs)} levels, "
            f"ratio={threshold_ratio:.1f}×"
        )

    return {
        'detected': len(detected_icebergs) > 0,
        'icebergs': detected_icebergs,
        'recommendation': 'caution_when_crossing' if detected_icebergs else 'normal'
    }
```

### Regla 4 — Pegged Orders

Órdenes que se mueven automáticamente con el Mid-price.

```python
def create_pegged_order(
    self,
    side: str,
    quantity: float,
    peg_offset: float,  # Offset del mid-price en ticks
    min_price: float = None,
    max_price: float = None
) -> dict:
    """
    Crear orden pegada al mid-price.

    Johnson: Pegged = asegurar ejecución cerca de mid.
    """
    # Mid-price actual
    mid_price = self.get_mid_price()

    # Calcular precio pegado
    tick_size = self.get_tick_size()

    if side == 'buy':
        pegged_price = mid_price - peg_offset * tick_size
    else:
        pegged_price = mid_price + peg_offset * tick_size

    # Aplicar límites
    if min_price is not None:
        pegged_price = max(pegged_price, min_price)

    if max_price is not None:
        pegged_price = min(pegged_price, max_price)

    # Crear orden monitoreada
    pegged_order = {
        'order_id': f"PEG_{pd.Timestamp.now().timestamp()}",
        'type': 'pegged',
        'side': side,
        'quantity': quantity,
        'peg_offset': peg_offset,
        'initial_price': pegged_price,
        'min_price': min_price,
        'max_price': max_price,
        'status': 'active'
    }

    logger.info(
        f"Pegged order: {side} {quantity:.0f} @ {pegged_price:.2f} "
        f"(mid={mid_price:.2f}, offset={peg_offset} ticks)"
    )

    return pegged_order
```

### Regla 5 — Dark Pool Aggregator

Si Stock es poco líquida, buscar liquidez en pools oscuros.

```python
def dark_pool_aggregator(
    self,
    order: dict,
    min_liquidity_threshold: float = 10000
) -> dict:
    """
    Agregar liquidez de dark pools.

    Johnson: Dark pools = ejecución sin impacto público.
    """
    # Obtener liquidez consolidada
    public_liquidity = self.get_public_liquidity(
        order['symbol']
    )

    if public_liquidity > order['quantity'] * 1.5:
        # Suficiente liquidez pública
        return {
            'use_dark': False,
            'reason': 'sufficient_public_liquidity'
        }

    # Buscar dark pools disponibles
    dark_pools = [
        'crossfinder',
        'liquidnet',
        'bids_trading',
        'instinet'
    ]

    dark_quotes = []

    for pool in dark_pools:
        quote = self.get_dark_pool_quote(
            pool=pool,
            symbol=order['symbol'],
            quantity=order['quantity'],
            side=order['side']
        )

        if quote:
            dark_quotes.append({
                'pool': pool,
                'price': quote['price'],
                'quantity': quote['quantity'],
                'fee': quote.get('fee', 0)
            })

    if not dark_quotes:
        return {
            'use_dark': False,
            'reason': 'no_dark_liquidity'
        }

    # Seleccionar mejor quote
    best_quote = min(dark_quotes, key=lambda x: x['price']) if order['side'] == 'buy' else max(dark_quotes, key=lambda x: x['price'])

    logger.info(
        f"Dark pool aggregator: {order['symbol']}, "
        f"best={best_quote['pool']} @ {best_quote['price']:.2f}, "
        f"qty={best_quote['quantity']:.0f}"
    )

    return {
        'use_dark': True,
        'selected_pool': best_quote['pool'],
        'price': best_quote['price'],
        'quantity': best_quote['quantity'],
        'fee': best_quote['fee'],
        'all_quotes': dark_quotes
    }
```

### Regla 6 — Smart Order Router (SOR)

En Forex, elegir proveedor de liquidez con spread más bajo en tiempo real.

```python
def smart_order_router(
    self,
    fx_pair: str,
    quantity: float,
    side: str
) -> dict:
    """
    Enrutador inteligente de órdenes FX.

    Johnson: SOR = mejor ejecución multi-venue.
    """
    # Obtener quotes de múltiples venues
    venues = [
        'ebs',
        'reuters',
        'currenex',
        'fxall',
        'hotspot_fx'
    ]

    quotes = []

    for venue in venues:
        quote = self.get_fx_quote(
            venue=venue,
            pair=fx_pair,
            quantity=quantity,
            side=side
        )

        if quote:
            # Calcular costo total
            spread = quote['ask'] - quote['bid']
            commission = quote.get('commission', 0)

            # Costo estimado de ejecución
            if side == 'buy':
                execution_cost = quote['ask'] - quote['mid'] + commission
            else:
                execution_cost = quote['mid'] - quote['bid'] + commission

            quotes.append({
                'venue': venue,
                'price': quote['ask'] if side == 'buy' else quote['bid'],
                'quantity': quote['quantity'],
                'spread': spread,
                'commission': commission,
                'execution_cost': execution_cost,
                'latency_ms': quote.get('latency', 10)
            })

    if not quotes:
        return {
            'routable': False,
            'reason': 'no_quotes_available'
        }

    # Seleccionar venue con menor costo total
    best_venue = min(quotes, key=lambda x: x['execution_cost'])

    logger.info(
        f"SOR: {fx_pair} {side} {quantity:.0f}, "
        f"best={best_venue['venue']} @ {best_venue['price']:.5f}, "
        f"cost={best_venue['execution_cost']:.5f}"
    )

    return {
        'routable': True,
        'selected_venue': best_venue['venue'],
        'price': best_venue['price'],
        'execution_cost': best_venue['execution_cost'],
        'all_quotes': quotes
    }
```

### Regla 7 — Post-Trade Analysis (VWAP Comparison)

Comparar precio de ejecución con VWAP del mercado.

```python
def post_trade_analysis(
    self,
    execution: dict,
    market_data: pd.DataFrame
) -> dict:
    """
    Analizar calidad de ejecución vs VWAP.

    Johnson: VWAP comparison = benchmark de calidad.
    """
    # Obtener ventana de ejecución
    execution_start = execution['start_time']
    execution_end = execution['end_time']

    # Calcular VWAP del mercado durante ventana
    market_window = market_data[
        (market_data.index >= execution_start) &
        (market_data.index <= execution_end)
    ]

    if len(market_window) == 0:
        return {
            'analyzable': False,
            'reason': 'no_market_data'
        }

    market_vwap = (
        (market_window['close'] * market_window['volume']).sum() /
        market_window['volume'].sum()
    )

    # Precio de ejecución promedio
    execution_vwap = execution['avg_price']

    # Comparación
    if execution['side'] == 'buy':
        # Para buys, menor es mejor
        slippage_vs_vwap = (execution_vwap - market_vwap) / market_vwap

    else:
        # Para sells, mayor es mejor
        slippage_vs_vwap = (market_vwap - execution_vwap) / market_vwap

    # Calificación
    if slippage_vs_vwap < 0.0001:  # < 1 bps
        grade = 'EXCELLENT'
    elif slippage_vs_vwap < 0.0005:  # < 5 bps
        grade = 'GOOD'
    elif slippage_vs_vwap < 0.0010:  # < 10 bps
        grade = 'ACCEPTABLE'
    else:
        grade = 'POOR'

    logger.info(
        f"Post-trade analysis: {grade}, "
        f"exec_vwap={execution_vwap:.4f}, mkt_vwap={market_vwap:.4f}, "
        f"slippage={slippage_vs_vwap:+.4f}"
    )

    return {
        'analyzable': True,
        'grade': grade,
        'execution_vwap': execution_vwap,
        'market_vwap': market_vwap,
        'slippage_vs_vwap': slippage_vs_vwap,
        'improvement_ideas': self.get_execution_improvements(slippage_vs_vwap)
    }
```

### Regla 8 — Fill Rate Optimization

Si órdenes limitadas no se ejecutan, aumentar agresividad.

```python
def fill_rate_optimizer(
    self,
    pending_orders: List[dict],
    fill_threshold: float = 0.3,
    aggression_increment: float = 0.0001
) -> dict:
    """
    Optimizar tasa de ejecución ajustando agresividad.

    Johnson: Fill rate bajo = ajustar precio.
    """
    optimizations = []

    for order in pending_orders:
        if order['type'] != 'limit':
            continue

        # Calcular fill rate actual
        filled_qty = order.get('filled_quantity', 0)
        total_qty = order['quantity']
        fill_rate = filled_qty / total_qty

        if fill_rate < fill_threshold:
            # Aumentar agresividad
            current_price = order['price']
            side = order['side']

            if side == 'buy':
                new_price = current_price * (1 + aggression_increment)
            else:
                new_price = current_price * (1 - aggression_increment)

            optimizations.append({
                'order_id': order['order_id'],
                'current_fill_rate': fill_rate,
                'current_price': current_price,
                'new_price': new_price,
                'action': 'increase_aggression'
            })

            logger.info(
                f"Fill rate optimization: {order['order_id']}, "
                f"fill={fill_rate:.1%}, {current_price:.2f} → {new_price:.2f}"
            )

    return {
        'optimizations': optimizations,
        'n_optimized': len(optimizations)
    }
```

### Regla 9 — Order Interaction Filter

Evitar que propias órdenes de compra y venta se crucen.

```python
def order_interaction_filter(
    self,
    pending_buys: List[dict],
    pending_sells: List[dict]
) -> dict:
    """
    Prevenir wash trading accidental.

    Johnson: Auto-crossing = regulatorio problemático.
    """
    conflicts = []

    for buy in pending_buys:
        for sell in pending_sells:
            # Mismo símbolo
            if buy['symbol'] != sell['symbol']:
                continue

            # Precios se cruzan
            if buy['price'] >= sell['price']:
                conflicts.append({
                    'buy_order': buy['order_id'],
                    'sell_order': sell['order_id'],
                    'symbol': buy['symbol'],
                    'buy_price': buy['price'],
                    'sell_price': sell['price'],
                    'action': 'cancel_one'
                })

    if conflicts:
        logger.warning(
            f"⚠️ Order interactions detected: {len(conflicts)} conflicts"
        )

        # Resolver conflictos
        for conflict in conflicts:
            # Cancelar orden más reciente
            buy_time = self.get_order_time(conflict['buy_order'])
            sell_time = self.get_order_time(conflict['sell_order'])

            if buy_time > sell_time:
                to_cancel = conflict['buy_order']
            else:
                to_cancel = conflict['sell_order']

            self.cancel_order(to_cancel)

            logger.info(f"Cancelled {to_cancel} to prevent interaction")

    return {
        'conflicts_detected': len(conflicts),
        'conflicts': conflicts,
        'resolved': len(conflicts) > 0
    }
```

### Regla 10 — Market Impact Decay

Esperar N segundos entre child orders para que liquidez se reponga.

```python
def market_impact_decay_wait(
    self,
    last_execution_time: pd.Timestamp,
    symbol: str,
    min_seconds: int = 30
) -> float:
    """
    Calcular tiempo de espera basado en decaimiento de impacto.

    Johnson: Impact decay = evitar auto-impacto.
    """
    # Tiempo desde última ejecución
    elapsed = (pd.Timestamp.now() - last_execution_time).total_seconds()

    if elapsed >= min_seconds:
        wait_time = 0
    else:
        wait_time = min_seconds - elapsed

    # Ajustar según liquidez del symbol
    liquidity_score = self.get_liquidity_score(symbol)

    if liquidity_score < 0.3:  # Baja liquidez
        wait_time = wait_time * 1.5

    logger.debug(
        f"Impact decay wait: {wait_time:.1f}s "
        f"(elapsed={elapsed:.1f}s, liquidity={liquidity_score:.2f})"
    )

    return wait_time
```

### Regla 11 — Venue Toxicity Monitoring

Dejar de enviar órdenes a exchanges donde slippage sea sistemáticamente alto.

```python
def venue_toxicity_monitor(
    self,
    venue_executions: List[dict],
    toxicity_threshold: float = 0.0010  # 10 bps
) -> dict:
    """
    Monitorear toxicidad de venues.

    Johnson: Venue alto slippage = blacklisting.
    """
    # Agrupar por venue
    venue_stats = {}

    for exec in venue_executions:
        venue = exec['venue']

        if venue not in venue_stats:
            venue_stats[venue] = {
                'executions': [],
                'slippages': []
            }

        # Calcular slippage
        expected_price = exec['expected_price']
        actual_price = exec['actual_price']

        side = exec['side']

        if side == 'buy':
            slippage = (actual_price - expected_price) / expected_price
        else:
            slippage = (expected_price - actual_price) / expected_price

        venue_stats[venue]['executions'].append(exec)
        venue_stats[venue]['slippages'].append(slippage)

    # Analizar cada venue
    toxic_venues = []

    for venue, stats in venue_stats.items():
        avg_slippage = np.mean(stats['slippages'])

        if avg_slippage > toxicity_threshold:
            toxic_venues.append({
                'venue': venue,
                'avg_slippage': avg_slippage,
                'n_executions': len(stats['executions']),
                'action': 'blacklist'
            })

            logger.warning(
                f"🚨 Toxic venue: {venue}, "
                f"avg_slippage={avg_slippage:.4f} > {toxicity_threshold:.4f}"
            )

    return {
        'toxic_venues': toxic_venues,
        'blacklist': [v['venue'] for v in toxic_venues]
    }
```

### Regla 12 — Tick Size Awareness

Poner órdenes un tick por encima de números redondos.

```python
def tick_size_aware_ordering(
    self,
    symbol: str,
    side: str,
    reference_price: float
) -> float:
    """
    Poner orden en nivel óptimo del libro.

    Johnson: Números redondos = más liquidez.
    """
    tick_size = self.get_tick_size(symbol)

    # Encontrar número redondo más cercano
    round_numbers = [10, 25, 50, 100, 500, 1000]

    # Para precios > 1
    if reference_price > 1:
        round_price = min(
            round_numbers,
            key=lambda x: abs(x - reference_price)
        )

    # Para precios < 1
    else:
        round_price = round(reference_price, 2)

    # Calcular óptimo
    ticks_from_round = int((round_price - reference_price) / tick_size)

    if side == 'buy':
        # Comprar un tick antes de soporte
        optimal_price = round_price - tick_size

    else:
        # Vender un tick antes de resistencia
        optimal_price = round_price + tick_size

    logger.debug(
        f"Tick-aware: {symbol} {side}, "
        f"ref={reference_price:.2f}, round={round_price:.2f}, "
        f"optimal={optimal_price:.2f}"
    )

    return optimal_price
```

### Regla 13 — Trading Schedule (Avoid Open/Close)

Evitar primeros y últimos 5 minutos de bolsa por volatilidad ciega.

```python
def trading_schedule_filter(
    self,
    current_time: pd.Timestamp,
    asset_class: str
) -> dict:
    """
    Filtrar horarios de alta volatilidad.

    Johnson: Open/Close = evitarse para ejecución.
    """
    tradable = True
    reason = None

    if asset_class == 'STOCKS':
        # Obtener horario de mercado
        market_open = self.get_market_open()
        market_close = self.get_market_close()

        # Primeros 5 minutos
        if current_time < market_open + pd.Timedelta(minutes=5):
            tradable = False
            reason = 'opening_volatility'

        # Últimos 5 minutos
        elif current_time > market_close - pd.Timedelta(minutes=5):
            tradable = False
            reason = 'closing_volatility'

    elif asset_class == 'CRYPTO':
        # Crypto es 24/7, pero evitar times específicos
        hour = current_time.hour

        # Evitar open de London (8am GMT = 3am EST)
        if hour == 3:
            tradable = False
            reason = 'london_open'

        # Evitar open de NY (9:30am EST)
        elif hour == 9 and current_time.minute < 30:
            tradable = False
            reason = 'ny_open'

    logger.info(
        f"Schedule filter: {asset_class}, {current_time}, "
        f"tradable={tradable}, reason={reason}"
    )

    return {
        'tradable': tradable,
        'reason': reason,
        'current_time': current_time,
        'asset_class': asset_class
    }
```

### Regla 14 — GTC vs IOC

Usar Immediate or Cancel para evitar órdenes huérfanas.

```python
def order_type_selection(
    self,
    symbol: str,
    order_size: float,
    market_condition: str
) -> str:
    """
    Seleccionar tipo de orden (GTC/IOC/FOK).

    Johnson: IOC = evitar órdenes zombie.
    """
    # Liquidez del symbol
    liquidity = self.get_liquidity_score(symbol)

    # Tamaño relativo
    avg_daily_volume = self.get_avg_daily_volume(symbol)
    size_ratio = order_size / avg_daily_volume

    # Decisión
    if market_condition == 'fast_market' or size_ratio > 0.10:
        # Mercado rápido o orden grande → IOC
        order_type = 'IOC'
        reason = 'fast_market_or_large_order'

    elif liquidity < 0.3:
        # Baja liquidez → FOK (Fill or Kill)
        order_type = 'FOK'
        reason = 'low_liquidity'

    else:
        # Condiciones normales → GTC (Good Till Cancel)
        order_type = 'GTC'
        reason = 'normal_conditions'

    logger.debug(
        f"Order type: {symbol}, {order_type}, "
        f"liquidity={liquidity:.2f}, size_ratio={size_ratio:.2%}"
    )

    return order_type
```

### Regla 15 — FIX Protocol Implementation

Usar protocolo FIX para comunicación ultra-rápida con brokers.

```python
def fix_protocol_manager(
    self,
    order: dict,
    target_venue: str
) -> dict:
    """
    Gestor de comunicación FIX.

    Johnson: FIX = estándar de comunicación pro.
    """
    from quickfix import Application, Message, SessionID

    class TradingApp(Application):
        def __init__(self):
            Application.__init__(self)

        def onCreate(self, session_id):
            logger.info(f"FIX session created: {session_id}")

        def onLogon(self, session_id):
            logger.info(f"FIX logon: {session_id}")

        def toAdmin(self, message, session_id):
            pass

        def fromAdmin(self, message, session_id):
            pass

        def toApp(self, message, session_id):
            pass

        def fromApp(self, message, session_id):
            pass

    # Construir mensaje FIX
    msg_type = 'D'  # New Order Single

    fix_fields = {
        '35': msg_type,
        '49': self.get_sender_comp_id(),  # SenderCompID
        '56': self.get_target_comp_id(target_venue),  # TargetCompID
        '11': order['order_id'],  # ClOrdID
        '55': order['symbol'],  # Symbol
        '54': order['side'],  # Side (1=buy, 2=sell)
        '38': order['quantity'],  # OrderQty
        '40': order.get('type', '2'),  # OrdType (2=limit)
        '44': order.get('price', 0),  # Price
        '59': order.get('time_in_force', '0'),  # TimeInForce (0=DAY, 3=IOC)
        '21': '1',  # HandlInst (1=auto)
        '100': self.get_executing_broker()  # ExDestination
    }

    # Enviar
    try:
        app = TradingApp()
        session_id = SessionID(
            fix_fields['49'],
            fix_fields['56']
        )

        # Enviar orden
        # (En producción, usar librería FIX real)
        logger.info(
            f"FIX Order: {order['order_id']} → {target_venue}, "
            f"{order['side']} {order['quantity']:.0f} @ {order.get('price', 'MKT')}"
        )

        return {
            'sent': True,
            'fix_message': fix_fields,
            'session_id': str(session_id)
        }

    except Exception as e:
        logger.error(f"FIX send failed: {e}")
        return {
            'sent': False,
            'error': str(e)
        }
```

---

## Aplicación Práctica

### Pipeline Completo DMA/Algorithmic Trading

```python
def dma_execution_pipeline(
    self,
    parent_order: dict,
    asset_class: str = 'STOCKS'
) -> dict:
    """
    Pipeline completo de ejecución DMA.
    """
    # 1. Verificar schedule
    schedule_check = self.trading_schedule_filter(
        pd.Timestamp.now(),
        asset_class
    )

    if not schedule_check['tradable']:
        return {
            'action': 'DEFER',
            'reason': schedule_check['reason']
        }

    # 2. Check dark pool availability
    dark_pool = self.dark_pool_aggregator(parent_order)

    if dark_pool['use_dark']:
        # Ejecutar en dark pool
        execution = self.execute_dark_pool_order(
            parent_order,
            dark_pool['selected_pool']
        )

        return execution

    # 3. Slice parent order
    child_orders = self.slice_and_dice(
        parent_order,
        max_participation=0.05
    )

    # 4. Ejecutar child orders con delay
    executions = []

    for child in child_orders:
        # Market impact decay wait
        if executions:
            wait_time = self.market_impact_decay_wait(
                executions[-1]['end_time'],
                child['symbol']
            )

            if wait_time > 0:
                time.sleep(wait_time)

        # DMA routing
        dma_result = self.dma_router(
            child,
            venue_priorities=self.get_venue_priorities(child['symbol'])
        )

        if dma_result['method'] == 'DMA':
            executions.append({
                'child_id': child['child_id'],
                'venue': dma_result['venue'],
                'order_id': dma_result['order_id'],
                'latency_ms': dma_result['latency_ms'],
                'start_time': pd.Timestamp.now(),
                'end_time': pd.Timestamp.now()
            })

    # 5. Post-trade analysis
    consolidated_execution = self.consolidate_executions(executions)

    analysis = self.post_trade_analysis(
        consolidated_execution,
        self.get_market_data(parent_order['symbol'])
    )

    # 6. Venue toxicity check
    toxicity = self.venue_toxicity_monitor(executions)

    if toxicity['toxic_venues']:
        self.update_venue_blacklist(toxicity['blacklist'])

    return {
        'parent_order_id': parent_order['order_id'],
        'executions': executions,
        'analysis_grade': analysis['grade'],
        'slippage_vs_vwap': analysis['slippage_vs_vwap'],
        'toxic_venues': toxicity['toxic_venues']
    }
```
