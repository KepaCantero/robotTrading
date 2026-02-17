# 🎯 ANÁLISIS DE READINESS: 3 MERCADOS

## 📊 RESUMEN EJECUTIVO

El sistema tiene una **fundación excelente** (framework completo, SRE production-ready, fiscalidad España avanzada) pero **carece de integraciones reales con brokers** para trading en vivo.

| Mercado | Listo para Producción | Tiempo hasta Producción | Mej Estrategia |
|---------|------------------------|--------------------------|-----------------|
| **Crypto** | 15% ⚠️ | 6-8 semanas básico / 12-16 avanzado | Arbitraje, Grid Trading |
| **Forex** | 10% ⚠️ | 17-24 semanas | Trend Following, Carry Trade |
| **Stocks/ETFs** | 25% ✅ | 9-13 semanas | Smart Beta, Momentum |

**Veredicto**: El sistema está listo para **DESARROLLO Y TESTING**, pero requiere **trabajo adicional** para producción real en cualquier mercado.

---

## 1️⃣ CRIPTOMONEDAS: "El Laboratorio Ideal"

### ✅ LO QUE ESTÁ LISTO

**Componentes SRE Production-Ready:**
- ✅ **WAL Persistence** (`app/sre/state_machine/wal_persistence.py`)
  - Write-Ahead Logging previene posiciones huérfanas
  - Estado persistido ANTES de llamar al broker
  - Previene pérdida de $100,000+ por crash

- ✅ **Boot Reconciliation** (`app/sre/reconciliation/boot_reconciler.py`)
  - Detección de posiciones huérfanas al arranque
  - Protección automática con stop-loss
  - Comparación broker vs BD local

- ✅ **Data Sanity Layer** (`app/sre/data_integrity/sanity_layer.py`)
  - Validación de precios contra segunda fuente
  - Filtro de desviación >50% (flash crash protection)
  - Heartbeat de feeds de datos

**Fiscalidad España (Modelo 721):**
- ✅ **FIFO Database Schema** completo
  - Multi-exchange tracking (Binance, Coinbase, Kraken, wallets)
  - Todos los tipos de transacciones crypto (staking, mining, airdrops, forks)
  - Auditoría inmutable para Hacienda

- ✅ **CSV Exporter** (`app/tax/exporters/modelo_721_exporter.py`)
  - Compatible con Coinpanda/Koinly
  - Snapshot 31 de diciembre
  - Exportación automática

**Data Framework:**
- ✅ **Crypto Data Service** (`app/services/crypto_data_service.py`)
  - 10 criptomonedas principales (BTC, ETH, BNB, SOL, XRP...)
  - Risk metrics específicos crypto (volatilidad 60-120%)
  - Cache y fallback mechanisms

**Multi-Market:**
- ✅ **Orchestrator** incluye crypto (max 10% para España)
  - Asignación dinámica de capital
  - News sentiment con Marketaux API
  - Estrategia adaptativa por régimen

### ❌ LO QUE FALTA (CRÍTICO)

**Integraciones de Brokers:**
```python
# ESTO ES LO QUE HAY:
def _fetch_price_from_api(self, pair: str) -> Optional[Decimal]:
    raise NotImplementedError("API price fetching not yet implemented")

# ESTO ES LO QUE NECESITAS:
async def fetch_binance_price(self, symbol: str) -> Decimal:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        ) as response:
            data = await response.json()
            return Decimal(data['price'])
```

| Broker | Estado | Prioridad | Tiempo |
|--------|--------|-----------|--------|
| **Binance** | ❌ No implementado | 🔴 CRÍTICA | 2 semanas |
| **Coinbase Pro** | ❌ No implementado | 🟡 ALTA | 1 semana |
| **Kraken** | ❌ No implementado | 🟡 ALTA | 1 semana |

**Infraestructura 24/7:**
- ❌ **Memory leak prevention** - Sin monitoreo de RAM
- ❌ **Auto-reconnection** - Sin lógica de reconexión
- ❌ **Process monitoring** - Sin health checks

**Datos Real-Time:**
- ❌ **Level 2 Order Book** - Solo OHLCV disponible
- ❌ **Funding Rates** - Sin datos de perpetual futures
- ❌ **WebSocket streaming** - Framework existe pero sin implementación real

### 🔧 QUÉ HAY QUE CONSTRUIR

**Fase 1: Integración Binance (2 semanas)**
```python
# app/api/brokers/crypto/binance_adapter.py

class BinanceAdapter(BrokerConnector):
    async def connect(self) -> bool:
        """Conectar a Binance API"""
        self.session = aiohttp.ClientSession()

        # API Key setup
        headers = {
            'X-MBX-APIKEY': self.api_key,
        }

        # Test connection
        async with self.session.get(
            f"{self.base_url}/api/v3/account",
            headers=headers
        ) as response:
            if response.status == 200:
                self.is_connected = True
                return True
        return False

    async def get_account_balance(self) -> Dict[str, Decimal]:
        """Obtener balance de la cuenta"""
        params = {'timestamp': int(time.time() * 1000)}
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()

        url = f"{self.base_url}/api/v3/account?{query_string}&signature={signature}"

        async with self.session.get(url, headers=self._get_headers()) as response:
            data = await response.json()
            balances = {}
            for balance in data['balances']:
                if float(balance['free']) > 0:
                    balances[balance['asset']] = Decimal(balance['free'])
            return balances

    async def place_order(self, order: Order) -> OrderResult:
        """Colocar orden en Binance"""
        # Implementación con WAL
        await self.wal.write(OrderLog(
            transaction_id=order.id,
            state="SUBMITTING",
            timestamp=datetime.utcnow()
        ))

        try:
            result = await self._execute_binance_order(order)
            await self.wal.write(OrderLog(state="ACK_RECEIVED", ...))
            return result
        except Exception as e:
            await self.wal.write(OrderLog(state="FAILED", error=str(e)))
            raise
```

**Fase 2: Position Monitor 24/7 (1 semana)**
```python
# app/services/position_monitor/crypto_position_monitor.py

class CryptoPositionMonitor:
    """Monitoreo de posiciones crypto 24/7"""

    def __init__(self):
        self.check_interval = 1  # 1 segundo
        self.stale_threshold = 60  # 60 segundos

    async def monitor_continuously(self):
        """Loop infinito de monitoreo"""
        while self.is_running:
            try:
                # Check positions
                for position in self.get_all_open_positions():
                    await self.check_position_health(position)

                # Check data freshness
                await self.verify_data_feeds()

                # Memory health check
                await self.check_memory_usage()

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

            await asyncio.sleep(self.check_interval)
```

**Fase 3: Level 2 Data (2 semanas)**
```python
# app/data/order_book/binance_order_book.py

class BinanceOrderBook:
    """Order Book Level 2 para Binance"""

    async def get_order_book(self, symbol: str, limit: int = 100):
        """Obtener order book depth"""
        url = f"{self.base_url}/api/v3/depth"
        params = {'symbol': symbol, 'limit': limit}

        async with self.session.get(url, params=params) as response:
            data = await response.json()

            return {
                'bids': [[Decimal(p), Decimal(q)] for p, q in data['bids']],
                'asks': [[Decimal(p), Decimal(q)] for p, q in data['asks']],
                'last_update_id': data['lastUpdateId']
            }
```

### ⏱️ TIMELINE CRYPTO

``+------------------+-------------------------------+
| Fase             | Duración                     |
+------------------+-------------------------------+
| Integración Binance   | 2 semanas                 |
| Position Monitor 24/7  | 1 semana                  |
| Level 2 Data          | 2 semanas                 |
| Testing & Staging     | 1-2 semanas               |
+------------------+-------------------------------+
| TOTAL BÁSICO          | 6-8 semanas                |
+------------------+-------------------------------+

+------------------+-------------------------------+
| Arbitraje HF          | +4 semanas (latencia)      |
| Grid Trading          | +3 semanas (estado)        |
| Multi-Exchange        | +3 semanas                 |
+------------------+-------------------------------+
| TOTAL AVANZADO        | 16-19 semanas              |
+------------------+-------------------------------+
```

### 🎯 RECOMENDACIÓN CRYPTO

**Para empezar (6-8 semanas):**
1. Empezar con **Binance** (mejor API crypto)
2. Operar solo **BTC, ETH** (más líquidos)
3. Estrategia **Grid Trading** (sencilla, 24/7)
4. Empezar con **$100-500** (aprender sin riesgo catastrófico)

**Por qué Crypto es el "Laboratorio Ideal":**
- ✅ Funciona 24/7 (perfecto para probar Position Monitor)
- ✅ APIs son modernas y gratuitas
- ✅ Level 2 data gratis o muy barato
- ✅ Fiscalidad obliga FIFO (perfecto para probar tax engine)

---

## 2️⃣ FOREX: "El Mercado de la Estabilidad"

### ✅ LO QUE ESTÁ LISTO

**Data Framework:**
- ✅ **Forex Data Service** (`app/services/forex_data_service.py`)
  - 10 pares mayores (EUR/USD, GBP/USD, USD/JPY...)
  - Default correlations y spreads
  - Cache mechanisms

**Multi-Market:**
- ✅ **Orchestrator** incluye forex (15% asignación)
  - Trend Following como estrategia default
  - Currency hedging references

**Broker Partial:**
- ✅ **Interactive Brokers** adapter existe
  - Soporta forex a través de IBKR
  - Pero NO es especializado en forex

### ❌ LO QUE FALTA (CRÍTICO)

**Integraciones de Brokers Forex:**
| Broker | Estado | Prioridad | Tiempo |
|--------|--------|-----------|--------|
| **OANDA** | ❌ No implementado | 🔴 CRÍTICA | 2 semanas |
| **FXCM** | ❌ No implementado | 🟡 ALTA | 1.5 semanas |
| **Forex.com** | ❌ No implementado | 🟢 MEDIA | 1 semana |

**Riesgos Específicos Forex:**
- ❌ **Weekend Gap Handling** - Mercado cierra viernes, abre domingo
- ❌ **Swap/Rollover Rates** - Intereses por posiciones overnight
- ❌ **Currency Hedging** - Sin implementación real
- ❌ **Slippage Forex** - Spreads se ensanchan en noticias

**Datos Real-Time:**
- ❌ **Live forex feeds** - Solo fallback defaults
- ❌ **Tick-by-tick data** - Necesario para scalping
- ❌ **Spread monitoring** - Crítico para costes

### 🔧 QUÉ HAY QUE CONSTRUIR

**Fase 1: OANDA Integration (2 semanas)**
```python
# app/api/brokers/forex/oanda_adapter.py

class OandaAdapter(BrokerConnector):
    """OANDA v20 REST API para Forex"""

    async def get_instruments(self) -> List[str]:
        """Obtener pares disponibles"""
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

        url = f"{self.base_url}/v3/instruments"
        params = {'instruments': 'EUR_USD,GBP_USD,USD_JPY'}

        async with self.session.get(url, headers=headers, params=params) as response:
            data = await response.json()
            return [inst['name'] for inst in data['instruments']]

    async def get_candles(self, instrument: str, granularity: str = "M15"):
        """OHLCV data para forex"""
        url = f"{self.base_url}/v3/instruments/{instrument}/candles"
        params = {
            'priceComponent': 'M',
            'granularity': granularity
        }

        async with self.session.get(url, params=params) as response:
            data = await response.json()

            return {
                'o': float(c['mid']['o']),  # Open
                'h': float(c['mid']['h']),  # High
                'l': float(c['mid']['l']),  # Low
                'c': float(c['mid']['c']),  # Close
                'v': int(c['volume'])      # Volume
            } for c in data['candles']
```

**Fase 2: Weekend Gap Handling (1.5 semanas)**
```python
# app/services/forex/weekend_gap_handler.py

class WeekendGapHandler:
    """Manejo del gap de fin de semana en Forex"""

    async def check_gap_risk(self, positions: List[Position]) -> GapRiskReport:
        """Analizar riesgo de gap para posiciones abiertas"""

        # Histórico de gaps
        gap_history = await self.get_historical_gaps(
            pair="EUR_USD",
            weeks_back=52  # Último año
        )

        avg_gap_pct = statistics.mean([g['gap_pct'] for g in gap_history])
        max_gap_pct = max([g['gap_pct'] for g in gap_history])

        for position in positions:
            gap_loss = position.quantity * position.entry_price * avg_gap_pct / 100

            if gap_loss > position.max_acceptable_loss:
                logger.warning(
                    f"{position.symbol}: Weekend gap risk {gap_loss:.2f} "
                    f"exceeds threshold {position.max_acceptable_loss:.2f}"
                )

        return GapRiskReport(
            avg_gap_pct=avg_gap_pct,
            max_gap_pct=max_gap_pct,
            positions_at_risk=[p for p in positions if gap_loss > p.max_acceptable_loss]
        )

    async def close_before_weekend(self, positions: List[Position]):
        """Cerrar posiciones antes del fin de semana"""

        # Forex cierra viernes 17:00 EST
        # Abrimos domingo 17:00 EST

        now = datetime.utcnow()
        est_tz = pytz.timezone('US/Eastern')
        now_est = now.astimezone(est_tz)

        # Viernes 16:30 EST - cerrar antes del cierre
        if now_est.weekday() == 4 and now_est.hour >= 16:  # Viernes
            if now_est.minute >= 30:
                logger.info("Friday evening - closing positions before weekend")
                for position in positions:
                    await self.close_position(position)
```

**Fase 3: Swap/Rollover Calculator (1 semana)**
```python
# app/services/forex/swap_calculator.py

class SwapRateCalculator:
    """Calculadora de costes de carry trade"""

    async def calculate_swap_cost(
        self,
        pair: str,
        position_size: Decimal,
        nights: int
    ) -> SwapCost:
        """Calcular coste/beneficio de mantener posición overnight"""

        # Obtener diferencial de tasas de interés
        base_rate = await self.get_interest_rate(pair[:3])  # EUR
        quote_rate = await self.get_interest_rate(pair[3:])  # USD

        rate_differential = quote_rate - base_rate

        # Fórmula de swap aproximada
        # Swap = position_size * rate_differential * days / 365
        swap_cost = position_size * Decimal(str(rate_differential)) * Decimal(nights) / 365

        # Bid/ask spread en swap
        swap_spread = position_size * Decimal("0.0001")  # 1 pip approx

        total_cost = swap_cost + swap_spread

        return SwapCost(
            pair=pair,
            position_size=position_size,
            nights=nights,
            base_rate=base_rate,
            quote_rate=quote_rate,
            swap_cost=swap_cost,
            total_cost=total_cost
        )
```

### ⏱️ TIMELINE FOREX

```
+------------------+-------------------------------+
| Fase             | Duración                     |
+------------------+-------------------------------+
| OANDA Integration     | 2 semanas                 |
| Weekend Gap Handling  | 1.5 semanas               |
| Swap Calculator       | 1 semana                   |
| 24/5 Monitoring       | 1.5 semanas               |
+------------------+-------------------------------+
| TOTAL BÁSICO          | 6 semanas                   |
+------------------+-------------------------------+

+------------------+-------------------------------+
| Carry Trade           | +4 semanas                 |
| Multi-Currency Hedging| +3 semanas                 |
| Advanced Strategies   | +4 semanas                 |
+------------------+-------------------------------+
| TOTAL AVANZADO        | 17 semanas                  |
+------------------+-------------------------------+
```

### 🎯 RECOMENDACIÓN FOREX

**Para empezar (6 semanas):**
1. **OANDA** como broker principal (mejor API forex)
2. Operar solo **3 pares mayores** (EUR/USD, GBP/USD, USD/JPY)
3. Estrategia **Trend Following** (más predecible)
4. **CERRAR posiciones el viernes** (evitar gap risk)

**Por qué Forex es "El Mercado de la Estabilidad":**
- ✅ $6+ billones diarios (siempre liquidez)
- ✅ Volatilidad más predecible que crypto
- ✅ Perfecto para probar strategies macro
- ⚠️ **CUIDADO**: Weekend gaps son reales y peligrosos

---

## 3️⃣ ACCIONES/ETFs: "El Terreno de la Inversión"

### ✅ LO QUE ESTÁ LISTO

**Brokers (PARCIALMENTE):**
- ✅ **Alpaca** - Completo para US stocks
- ✅ **Interactive Brokers** - Para US y algunos mercados globales
- ✅ **BrokerConnector** - Abstracción unificada

**Motor de Trading:**
- ✅ **Stock Allocator** - Screener técnico completo
- ✅ **Portfolio Construction** - WCM scoring, diversificación sectorial
- ✅ **Rebalancing Engine** - Smart Beta rebalanceo
- ✅ **Market Regimes** - Detección automática de tendencias

**Gestión de Riesgo:**
- ✅ **Circuit Breakers** - Detección de market halts
- ✅ **Drawdown Controllers** - Múltiples estrategias de protección
- ✅ **Position Sizing** - Kelly Criterion, ATR-based
- ✅ **Portfolio Risk Manager** - Monitoreo en tiempo real

**Fiscalidad España:**
- ✅ **Modelo 720** - Para activos extranjeros >€50k
- ✅ **FIFO** - Cost basis tracking
- ✅ **Dividend Tracking** - Framework para ingresos

### ❌ LO QUE FALTA (CRÍTICO)

**Brokers Europeos:**
| Broker | Estado | Prioridad | Tiempo |
|--------|--------|-----------|--------|
| **Degiro** | ❌ No implementado | 🔴 CRÍTICA | 2 semanas |
| **Trading 212** | ❌ No implementado | 🟡 ALTA | 1.5 semanas |
| **Saxo (España)** | ❌ No implementado | 🟡 ALTA | 2 semanas |

**Regulatorio US:**
- ❌ **PDT Rule Enforcement** - < $25k = max 3 day trades
- ❌ **W-8BEN Form** - Para evitar withholding de dividendos US
- ❌ **Pattern Day Trader Counter** - Sin contador de day trades

**Corporate Actions:**
- ❌ **Stock Splits** - Ajuste automático de posiciones
- ❌ **Mergers & Acquisitions** - Manejo de adquisiciones
- ❌ **Dividend Reinvestment** - Automatización DRIP

**Market Hours:**
- ❌ **Holiday Calendar** - Días festivos US/EU
- ❌ **Pre-market/After-hours** - Trading extendido
- ❌ **Earnings Calendar** - Evitar volatilidad de earnings

### 🔧 QUÉ HAY QUE CONSTRUIR

**Fase 1: Degiro Integration (2 semanas)**
```python
# app/api/brokers/stocks/degiro_adapter.py

class DegiroAdapter(BrokerConnector):
    """Degiro API para mercado europeo"""

    """
    Por qué Degiro:
    - Comisiones más bajas de Europa (~€1/trade)
    - Acceso a 50+ exchanges europeos
    - Perfecto para residentes España
    - Sin Pattern Day Trader rule
    """

    async def get_products(self, exchange: str = "Euronext") -> List[Product]:
        """Obtener lista de productos disponibles"""
        url = f"{self.base_url}/v5/products/search"
        params = {
            'intuitive': True,
            'continent': 'EU',
            'exchange': exchange
        }

        async with self.session.get(url, params=params) as response:
            data = await response.json()

            return [
                Product(
                    product_id=item['id'],
                    symbol=item['symbol'],
                    name=item['name'],
                    currency=item['currency'],
                    exchange=item['exchange']
                )
                for item in data['data']
            ]

    async def place_order(self, order: Order) -> OrderResult:
        """Colocar orden en Degiro"""

        # Degiro usa un sistema 2-step:
        # 1. Validar orden (check limits, etc.)
        # 2. Confirmar orden

        url = f"{self.base_url}/v5/orders"

        # Step 1: Validate
        validate_payload = {
            'orderId': order.id,
            'orderType': order.type.value,  # MARKET, LIMIT
            'product_id': order.symbol_id,
            'size': order.quantity,
            'price': order.price if order.type == OrderType.LIMIT else None
        }

        async with self.session.post(url, json=validate_payload) as response:
            validation = await response.json()

            if not validation.get('confirmationRequired', False):
                return OrderResult(
                    order_id=order.id,
                    status='REJECTED',
                    reason=validation.get('rejectReason', 'Unknown')
                )

        # Step 2: Confirm
        confirm_payload = {
            'orderId': order.id,
            'confirmed': True
        }

        async with self.session.put(url, json=confirm_payload) as response:
            result = await response.json()

            return OrderResult(
                order_id=order.id,
                status='FILLED',
                execution_price=Decimal(result['price']),
                filled_quantity=Decimal(result['size'])
            )
```

**Fase 2: PDT Rule Enforcement (1 semana)**
```python
# app/services/compliance/pdt_rule_enforcer.py

class PDTRuleEnforcer:
    """
    Pattern Day Trader Rule Enforcement (USA)

    Regla: < $25k equity = máximo 3 day trades en 5 días
    Si excedes → cuenta bloqueada
    """

    def __init__(self, account_value: Decimal):
        self.account_value = account_value
        self.pdt_threshold = Decimal("25000")
        self.max_day_trades = 3
        self.lookback_days = 5

    async def check_pdt_limit(
        self,
        proposed_trade: ProposedTrade
    ) -> PDTCheckResult:
        """Verificar si trade viola regla PDT"""

        # Si account_value > $25k, sin restricción
        if self.account_value >= self.pdt_threshold:
            return PDTCheckResult(
                allowed=True,
                reason="Account value above $25k threshold",
                remaining_trades=None
            )

        # Contar day trades en últimos 5 días
        day_trades = await self.count_day_trades(
            account_id=self.account_id,
            days_back=self.lookback_days
        )

        if day_trades >= self.max_day_trades:
            return PDTCheckResult(
                allowed=False,
                reason=f"Day trade limit reached ({day_trades}/{self.max_day_trades})",
                remaining_trades=0
            )

        remaining = self.max_day_trades - day_trades

        return PDTCheckResult(
            allowed=True,
            reason=f"PDT check passed ({day_trades}/{self.max_day_trades} used)",
            remaining_trades=remaining
        )

    async def count_day_trades(
        self,
        account_id: str,
        days_back: int
    ) -> int:
        """Contar day trades en ventana móvil"""

        # Day trade = abrir y cerrar MISMA posición en mismo día

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)

        trades = await self.db.get_trades_in_window(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date
        )

        # Agrupar por symbol y día
        day_trades_by_symbol = {}

        for trade in trades:
            trade_date = trade.executed_at.date()

            # Buscar closing trade
            closing_trade = await self.db.find_closing_trade(
                symbol=trade.symbol,
                opening_trade_id=trade.id,
                same_day=True
            )

            if closing_trade:
                key = f"{trade.symbol}_{trade_date}"
                day_trades_by_symbol[key] = trade

        return len(day_trades_by_symbol)
```

**Fase 3: Corporate Actions Handler (2 semanas)**
```python
# app/services/corporate_actions/handler.py

class CorporateActionsHandler:
    """Manejo de eventos corporativos (splits, mergers, dividendos)"""

    async def handle_stock_split(
        self,
        split: StockSplitEvent
    ) -> SplitAdjustment:
        """
        Manejar stock split (ej: 2:1, 3:2)

        Ejemplo:
        - Tienes 100 acciones a $200 = $20,000
        - Split 2:1 → 200 acciones a $100 = $20,000
        """

        logger.warning(
            f"Stock split detected: {split.symbol} ratio {split.split_ratio}"
        )

        # Obtener posiciones afectadas
        positions = await self.db.get_open_positions(symbol=split.symbol)

        for position in positions:
            # Ajustar cantidad
            old_quantity = position.quantity
            new_quantity = old_quantity * split.split_ratio

            # Ajustar cost basis (mantiene total)
            old_cost_basis = position.cost_basis
            new_cost_per_share = old_cost_basis / split.split_ratio

            # Actualizar posición
            await self.db.update_position(
                position_id=position.id,
                quantity=new_quantity,
                cost_per_share=new_cost_per_share,
                split_ratio=split.split_ratio,
                split_ex_date=split.ex_date
            )

            logger.info(
                f"Adjusted position {position.id}: "
                f"{old_quantity} → {new_quantity} shares, "
                f"${old_cost_basis} → ${new_cost_per_share}/share"
            )

        return SplitAdjustment(
            symbol=split.symbol,
            split_ratio=split.split_ratio,
            positions_adjusted=len(positions)
        )

    async def handle_merger(
        self,
        merger: MergerEvent
    ) -> MergerAdjustment:
        """
        Manejar adquisición (ej: Company A comprada por B)

        Ejemplo:
        - Tienes 100 acciones de Company A
        - Company B adquiere Company A
        - Acciones A se convierten en acciones B
        """

        logger.warning(
            f"Merger detected: {merger.target} acquiring {merger.acquired}"
        )

        # Obtener posiciones en acquired company
        positions = await self.db.get_open_positions(symbol=merger.acquired)

        for position in positions:
            # Calcular ratio de conversión
            conversion_ratio = merger.conversion_price / position.entry_price

            # Nuevas acciones en target company
            new_quantity = position.quantity * conversion_ratio

            # Mover posición a nuevo symbol
            await self.db.convert_position(
                position_id=position.id,
                old_symbol=merger.acquired,
                new_symbol=merger.target,
                new_quantity=new_quantity,
                cost_basis_transfer=position.cost_basis
            )

            logger.info(
                f"Converted position: {position.quantity} {merger.acquired} → "
                f"{new_quantity} {merger.target}"
            )

        return MergerAdjustment(
            target=merger.target,
            acquired=merger.acquired,
            positions_converted=len(positions)
        )
```

### ⏱️ TIMELINE STOCKS/ETFs

```
+------------------+-------------------------------+
| Fase             | Duración                     |
+------------------+-------------------------------+
| Degiro Integration    | 2 semanas                 |
| PDT Rule Enforcer      | 1 semana                   |
| Corporate Actions      | 2 semanas                 |
| 24/5 Monitoring       | 1.5 semanas               |
+------------------+-------------------------------+
| TOTAL BÁSICO          | 6.5 semanas                |
+------------------+-------------------------------+

+------------------+-------------------------------+
| W-8BEN Automation     | +1 semana                   |
| Smart Beta Strategies  | +3 semanas                 |
| Advanced Order Types   | +1.5 semanas               |
+------------------+-------------------------------+
| TOTAL AVANZADO        | 12 semanas                  |
+------------------+-------------------------------+
```

### 🎯 RECOMENDACIÓN STOCKS/ETFs

**Para empezar (6.5 semanas):**
1. **Degiro** para mercado europeo (comisiones ~€1, sin PDT)
2. **Alpaca** para mercado US (paper trading primero)
3. Estrategia **Momentum** (mejor probada en backtesting)
4. **Empezar con $1,000-5,000** (aprender sin arriesgar capital)

**Por qué Stocks es "El Terreno de la Inversión":**
- ✅ Más regulado y estable
- ✅ APIs profesionales (IBKR, Alpaca)
- ✅ Fiscalidad España más simple que crypto
- ✅ Perfecto para **Smart Beta** (rebalanceo automático)

---

## 📊 TABLA COMPARATIVA FINAL

| Aspecto | Crypto | Forex | Stocks/ETFs |
|---------|--------|-------|--------------|
| **Estado Actual** | 15% listo | 10% listo | 25% listo ✅ |
| **Tiempo Básico** | 6-8 semanas | 6 semanas | 6.5 semanas |
| **Tiempo Avanzado** | 12-16 semanas | 17 semanas | 12 semanas |
| **Broker Principal** | Binance | OANDA | Degiro/Alpaca |
| **Mejor Estrategia** | Arbitraje, Grid | Trend Following | Momentum, Smart Beta |
| **SRE Readiness** | ⭐⭐⭐⭐⭐ Excelente | ⭐⭐⭐⭐ Muy Bueno | ⭐⭐⭐⭐ Muy Bueno |
| **Tax Spain Ready** | ⭐⭐⭐⭐⭐ Modelo 721 | ⭐⭐⭐ Modelo 720 | ⭐⭐⭐ Modelo 100/720 |
| **Comisión** | 0.1% (Binance) | 1-2 pips spread | ~€1/trade (Degiro) |
| **Volatilidad** | Extrema (60-120%) | Media (5-15%) | Baja-Media (10-25%) |
| **Horario** | 24/7 | 24/5 | Market hours |
| **Ideal Para** | Aprender SRE | Macros | Inversión |

---

## 🎯 RECOMENDACIÓN FINAL: QUÉ MERCADO EMPEZAR PRIMERO

### 🥇 PRIMERO: CRIPTOMONEDAS (6-8 semanas)
**Por qué:**
- ✅ APIs modernas y gratuitas
- ✅ 24/7 (perfecto para probar Position Monitor)
- ✅ FIFO/Modelo 721 obligatorio (excelente práctica tax)
- ✅ Binance tiene excelente API

**Plan:**
1. Semana 1-2: Integración Binance API
2. Semana 3: Position Monitor 24/7
3. Semana 4: Grid Trading simple (BTC/ETH)
4. Semana 5-8: Testing con €100-500

**Riesgo:** Solo capital que puedas perder ($100-500)

---

### 🥈 SEGUNDO: STOCKS EUROPEOS (6.5 semanas)
**Por qué:**
- ✅ Degiro tiene comisiones bajas
- ✅ Sin PDT rule (Europa)
- ✅ Menor volatilidad que crypto
- ✅ Perfecto para Smart Beta

**Plan:**
1. Semana 1-2: Integración Degiro
2. Semana 3: PDT rule enforcement (si usas US)
3. Semana 4: Corporate actions handler
4. Semana 5-6: Momentum strategy
5. Semana 7: Testing con €1,000-5,000

---

### 🥉 TERCERO: FOREX (6 semanas)
**Por qué:**
- ✅ Más estable y predecible
- ✅ Trend Following funciona bien
- ✅ Bueno para diversificación

**Plan:**
1. Semana 1-2: Integración OANDA
2. Semana 3: Weekend gap handler
3. Semana 4: Swap calculator
4. Semana 5-6: Trend Following strategy

**ADVERTENCIA:** Cerrar posiciones el viernes (weekend gap risk)

---

## 📋 PLAN DE ACCIÓN INMEDIATO

### Esta Semana:
- [ ] Leer `MASTER_ACTION_PLAN.md` (30 min)
- [ ] Leer `SRE_CRITICAL_COMPONENTS.md` (20 min)
- [ ] Decidir mercado prioritario

### Próximas 2 Semanas:
- [ ] Revisar código SRE creado (WAL, Reconciliation, Sanity)
- [ ] Crear environment de desarrollo
- [ ] Setup cuenta broker (Binance/Degiro/OANDA)

### Próximas 8 Semanas (Fase 0-1):
- [ ] Implementar integración broker elegido
- [ ] Position Monitor 24/7 (crypto) o market hours (stocks/forex)
- [ ] Testing con capital mínimo

---

## 💡 CONCLUSIÓN

**El sistema tiene una fundación EXCELENTE** para los 3 mercados:

✅ **SRE Production-Ready** (WAL, Boot Reconciliation, Data Sanity)
✅ **Tax Compliance Spain** (Modelo 720/721, FIFO, CSV export)
✅ **Multi-Market Architecture** (Orchestrator, Risk Management)
✅ **Backtesting Framework** (25 años de datos probado)

**LO QUE FALTA:** Integración real con brokers (6-8 semanas por mercado)

**RECOMENDACIÓN:** Empezar con **CRYPTO** por:
1. APIs más modernas y fáciles
2. 24/7 operation (perfecto para probar SRE)
3. FIFO obligatorio (excelente práctica tax)
4. Binance tiene mejor documentación

**Tu sistema es un "Ferrari con ruedas de bicicleta" que necesita neumáticos (broker APIs) para arrancar.**

---

**Fecha:** 2025-01-25
**Estado:** READY FOR DEVELOPMENT, NOT PRODUCTION
**Próximo Paso:** Elegir mercado e implementar broker API
