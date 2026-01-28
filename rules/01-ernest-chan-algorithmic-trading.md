# 📘 1. "Algorithmic Trading" - Ernest P. Chan

## REGLAS DE IMPLEMENTACIÓN PARA CLAUDE CODE

### A. BACKTESTING FUNDAMENTALS

**NUNCA uses datos futuros en decisiones presentes (look-ahead bias)**

```python
# ❌ MAL
if today_close > tomorrow_close:  # Esto es look-ahead bias
    signal = "SELL"

# ✅ BIEN
if today_close > yesterday_close:  # Solo datos históricos
    signal = "SELL"
```

**Implementa point-in-time database** - Solo usa datos disponibles en ese momento

```python
def get_data_at_timestamp(self, symbol: str, timestamp: datetime) -> Quote:
    """NUNCA retornar datos posteriores a timestamp."""
    return self.db.query(
        "SELECT * FROM quotes WHERE symbol=? AND timestamp <= ? ORDER BY timestamp DESC LIMIT 1",
        (symbol, timestamp)
    )
```

**SIEMPRE aplica slippage realista** - Usa bid/ask spread COMPLETO

```python
# ❌ MAL
execution_price = market_price

# ✅ BIEN
if side == "BUY":
    execution_price = ask_price * (1 + slippage_bps / 10000)  # Peor precio
else:
    execution_price = bid_price * (1 - slippage_bps / 10000)
```

**SIEMPRE incluye comisiones COMPLETAS** - No solo comisión del broker

```python
total_commission = (
    broker_commission +  # €1-5
    exchange_fee +       # €0.10-0.50
    regulatory_fee +     # €0.01-0.10
    data_feed_cost       # Prorratear €50-200/mes
)
```

**Implementa survivorship bias correction** - Incluye empresas que quebraron

```python
# ✅ BIEN
def get_universe(self, date: datetime) -> List[str]:
    """Retornar símbolos VIVOS en esa fecha (incluye delistings futuros)."""
    return self.db.query(
        "SELECT symbol FROM listings WHERE list_date <= ? AND (delist_date IS NULL OR delist_date > ?)",
        (date, date)
    )
```

**NUNCA optimices en TODO el dataset** - Divide train/test

```python
# ✅ BIEN
train_data = quotes[:int(len(quotes) * 0.7)]  # 70% train
test_data = quotes[int(len(quotes) * 0.7):]   # 30% test

# Optimizar SOLO en train
best_params = optimize(train_data)

# Validar en test (UNA SOLA VEZ)
final_result = backtest(test_data, best_params)
```

**Calcula Sharpe ratio CORRECTAMENTE** - Anualizado con 252 días

```python
def sharpe_ratio(returns: np.array, risk_free_rate: float = 0.02) -> float:
    excess_returns = returns - risk_free_rate / 252
    return np.sqrt(252) * np.mean(excess_returns) / np.std(excess_returns)
```

**SIEMPRE verifica que Sharpe > 1.0** - Minimum viable threshold

```python
if backtest_result.sharpe_ratio < 1.0:
    logger.warning("⚠️ Sharpe < 1.0 - Strategy likely not viable")
    return StrategyStatus.REJECTED
```

**Calcula Maximum Drawdown correctamente**

```python
def max_drawdown(equity_curve: List[float]) -> float:
    """Max drawdown desde peak hasta trough."""
    peak = equity_curve[0]
    max_dd = 0.0

    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak
        max_dd = max(max_dd, dd)

    return max_dd
```

**Rechaza estrategias con Max DD > 25%**

```python
if backtest_result.max_drawdown > 0.25:
    logger.error("❌ Max Drawdown > 25% - Too risky")
    return StrategyStatus.REJECTED
```

### B. POSITION SIZING & RISK MANAGEMENT

**NUNCA arriesgues más del 2% por trade**

```python
def calculate_position_size(
    self,
    account_value: Decimal,
    stop_loss_pct: Decimal
) -> Decimal:
    """Kelly Criterion simplificado: no arriesgar >2% por trade."""
    max_risk = account_value * Decimal("0.02")
    position_size = max_risk / stop_loss_pct
    return min(position_size, account_value * Decimal("0.20"))  # Max 20% por posición
```

**Implementa Kelly Criterion (versión conservadora)**

```python
def kelly_position_size(
    self,
    win_rate: float,
    avg_win: float,
    avg_loss: float
) -> float:
    """Kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win."""
    kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    return max(0, min(kelly * 0.5, 0.25))  # Half-Kelly, max 25%
```

**SIEMPRE usa stop-loss** - NUNCA confíes en mean reversion sin límite

```python
def enter_position(self, signal: Signal):
    entry_price = signal.price
    stop_loss = entry_price * (1 - self.max_loss_pct)  # e.g., 5% stop

    self.active_positions[signal.symbol] = Position(
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=entry_price * (1 + self.take_profit_pct)  # e.g., 10% target
    )
```

**Limita correlación entre posiciones** - Diversificación real

```python
def check_correlation_limit(self, new_symbol: str) -> bool:
    """No abrir posición si correlación con portfolio > 0.7."""
    portfolio_returns = self.get_portfolio_returns()
    new_returns = self.get_returns(new_symbol)

    correlation = np.corrcoef(portfolio_returns, new_returns)[0, 1]

    return abs(correlation) < 0.7
```

**Implementa circuit breaker** - Para si pierdes X% en un día

```python
def check_daily_loss_limit(self) -> bool:
    """Detener trading si pérdida diaria > 5%."""
    daily_pnl = self.calculate_daily_pnl()
    daily_loss_pct = daily_pnl / self.start_of_day_capital

    if daily_loss_pct < -0.05:
        logger.critical("🛑 CIRCUIT BREAKER: Daily loss > 5%")
        self.halt_trading()
        return False

    return True
```

### C. TRANSACTION COSTS

**Modela slippage como función de volatilidad**

```python
def calculate_slippage(self, symbol: str, order_size: Decimal) -> Decimal:
    """Slippage aumenta con volatilidad y tamaño de orden."""
    volatility = self.get_recent_volatility(symbol, days=20)
    adv = self.get_average_daily_volume(symbol)

    # Slippage base: 5 bps
    base_slippage = Decimal("0.0005")

    # Ajuste por volatilidad (VIX > 30 = 2x slippage)
    vol_multiplier = Decimal("1.0") + (volatility / Decimal("0.20"))

    # Ajuste por tamaño de orden (% del ADV)
    size_pct = order_size / adv
    size_multiplier = Decimal("1.0") + size_pct * Decimal("10")

    return base_slippage * vol_multiplier * size_multiplier
```

**NUNCA ignores el bid-ask spread**

```python
def get_effective_price(self, quote: Quote, side: str) -> Decimal:
    """Precio efectivo incluyendo spread."""
    spread = quote.ask - quote.bid

    if side == "BUY":
        # Pagar el ask + la mitad del spread (market impact)
        return quote.ask + spread * Decimal("0.5")
    else:
        # Recibir el bid - la mitad del spread
        return quote.bid - spread * Decimal("0.5")
```

**Calcula commission impact ratio** - Debe ser < 15%

```python
def calculate_commission_impact(self) -> float:
    """Commission impact = total commissions / gross return."""
    total_commissions = sum(t.commission for t in self.trades)
    gross_return = sum(abs(t.pnl) for t in self.trades)

    if gross_return == 0:
        return float('inf')

    impact = total_commissions / gross_return

    if impact > 0.15:
        logger.warning(f"⚠️ Commission impact {impact:.1%} > 15% threshold")

    return impact
```

### D. ESTRATEGIAS ESPECÍFICAS

**Mean Reversion: Usa Bollinger Bands correctamente**

```python
def bollinger_signal(self, prices: List[float], window: int = 20) -> str:
    """Señal cuando precio sale de 2 std deviations."""
    sma = np.mean(prices[-window:])
    std = np.std(prices[-window:])

    upper_band = sma + 2 * std
    lower_band = sma - 2 * std

    current_price = prices[-1]

    if current_price < lower_band:
        return "BUY"  # Oversold
    elif current_price > upper_band:
        return "SELL"  # Overbought
    else:
        return "HOLD"
```

**Momentum: Requiere > 12 meses de lookback**

```python
def momentum_signal(self, prices: List[float], lookback_days: int = 252) -> str:
    """Momentum = return over last 12 months (excluding last month)."""
    if len(prices) < lookback_days + 20:
        return "HOLD"

    # Excluir último mes para evitar reversión a corto plazo
    price_12m_ago = prices[-(lookback_days + 20)]
    price_1m_ago = prices[-20]

    momentum = (price_1m_ago - price_12m_ago) / price_12m_ago

    if momentum > 0.10:  # >10% return
        return "BUY"
    elif momentum < -0.10:
        return "SELL"
    else:
        return "HOLD"
```

**Pairs Trading: Cointegración es REQUERIDA**

```python
from statsmodels.tsa.stattools import coint

def check_cointegration(self, prices_a: np.array, prices_b: np.array) -> bool:
    """Verificar cointegración antes de hacer pairs trading."""
    score, pvalue, _ = coint(prices_a, prices_b)

    # p-value < 0.05 indica cointegración
    if pvalue < 0.05:
        logger.info(f"✅ Cointegration confirmed (p-value: {pvalue:.4f})")
        return True
    else:
        logger.warning(f"⚠️ No cointegration (p-value: {pvalue:.4f})")
        return False
```

**NUNCA uses estrategias de alta frecuencia sin co-location**

```python
def validate_latency_requirements(self) -> bool:
    """Estrategias <1 segundo REQUIEREN co-location."""
    if self.strategy_frequency < timedelta(seconds=1):
        if not self.is_colocated:
            logger.error("❌ HFT strategy without co-location - REJECTED")
            return False

    return True
```
