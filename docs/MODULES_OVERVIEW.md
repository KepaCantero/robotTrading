# Modules Overview - AlgoTrading System

## System Modules

| Módulo | Función principal | Entradas | Salidas | Estrategias aplicadas | Parámetros clave | Dependencias |
|--------|-------------------|----------|---------|----------------------|------------------|--------------|
| TechnicalAnalyst | Genera señales de compra/venta con indicadores técnicos | Quote (OHLCV) | Signal(type, confidence, reason) | Momentum + Mean Reversion | RSI(14), EMA(12,26) | numpy, pandas, Decimal |
| RiskManager | Dimensiona posiciones y valida señales | Signal, Portfolio | Validated Signal | Risk-based sizing | stop_loss, take_profit, max_position_size | Portfolio models |
| ExecutionEngine | Ejecuta señales con slippage/commission | Signal, Market | Executed Trade | FIFO matching | slippage_percentage, commission | Trade models |
| BacktestingEngine | Simula estrategias históricamente | Quote[], Signal[] | BacktestResult | Virtual execution | initial_capital, commission, slippage | SimpleBacktester |
| Dashboard | Visualiza resultados y ejecuta backtests | BacktestResult | Visual charts, exports | Interactive analysis | Streamlit, plotly | streamlit, plotly, pandas |

## Module Details

### Module: TechnicalAnalyst (MomentumStrategy)

**Función:** Genera señales de compra/venta a partir de indicadores técnicos (RSI, MACD, ATR, ADX, EMA).

**Entradas:** 
```python
Quote {
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
}
```

**Salidas:** 
```python
Signal {
    type: BUY/SELL/HOLD
    confidence: float (0-100%)
    reason: str (e.g., "RSI < 30, EMA trend positive")
    metadata: dict
}
```

**Estrategia:** Momentum + Mean Reversion combinada
- RSI para detectar sobrecompra/sobreventa
- EMA Trend para confirmar dirección
- Volume Ratio para validar momentum

**Parámetros clave:** 
- `rsi_threshold`: 40 (default)
- `ema_fast`: 12, `ema_slow`: 26
- `momentum_threshold`: 0.005
- `stop_loss`: 3.0%
- `take_profit`: 7.0%

**Dependencias:** numpy, pandas, ta-lib (via custom implementation)

### Module: RiskManager

**Función:** Validates signals and manages position sizing based on risk criteria

**Entradas:**
- Signal from TechnicalAnalyst
- Current Portfolio state
- Market conditions

**Salidas:**
- Validated Signal (approved/rejected)
- Position size recommendation
- Risk metrics

**Decisions:**
- Calculates position size based on signal confidence
- Checks stop loss and take profit levels
- Validates capital availability
- Enforces maximum position size limits

**Criteria:**
```python
position_size = capital * max_position_size * confidence_factor
if position_size * price > capital:
    reject_signal()
if pnl_risk > daily_loss_limit:
    reduce_position_size()
```

### Module: ExecutionEngine

**Función:** Executes validated signals with realistic market conditions

**Entradas:**
- Validated Signal
- Current market price
- Execution settings

**Salidas:**
- Executed Trade (with execution price, slippage, commission)
- Updated Portfolio

**Implementation:**
```python
execution_price = market_price * (1 + slippage_factor)
commission = fixed_commission
total_cost = position_size * execution_price + commission
pnl = (exit_price - entry_price) * quantity - commission
```

**Dependencies:** Trade models, MarketData models

### Module: BacktestingEngine

**Función:** Simula estrategias históricamente con datos reales

**Entradas:**
- Historical Quotes array
- Signals array
- Configuration (capital, commission, slippage)

**Salidas:**
- BacktestResult {
    trades: List[Trade]
    performance: PerformanceMetrics
    equity_curve: List[datetime, Decimal]
    total_return: Decimal
}

**Process:**
1. Initialize capital
2. For each quote in chronological order:
   - Update equity curve
   - Check for signals
   - Execute buy/sell signals
   - Check exit conditions (stop loss, take profit)
3. Close all positions at end
4. Calculate metrics
5. Return results

### Module: Dashboard

**Función:** Interfaz visual para ejecutar backtests y analizar resultados

**Entradas:**
- Module selection
- Configuration presets
- Symbol, dates, capital

**Salidas:**
- Interactive charts (equity curve)
- Metrics table
- Trade log with reasons
- Export files (JSON/CSV)

**Features:**
- Select module (Momentum, Mean Reversion, TechnicalAnalyst)
- Select configuration (Conservative, Moderate, Aggressive)
- Execute backtest
- View metrics, equity curve, trade log
- Compare multiple configurations
- Export results

## Decision Examples

### Example 1: Momentum BUY Signal

**Input:**
```python
Quote {
    symbol: "AAPL"
    timestamp: "2024-01-15 10:30:00"
    close: 150.00
    volume: 10000000
}
```

**Process:**
1. Calculate RSI(14) = 28.5 < 30 ✅
2. Calculate EMA(12) = 149.8, EMA(26) = 148.5
3. EMA Trend = 149.8 - 148.5 = +1.3 ✅
4. Volume Ratio = 10M / 8M = 1.25 > 1.0 ✅

**Output:**
```python
Signal {
    type: BUY
    confidence: 85%
    reason: "RSI=28.5 < 30 (oversold), EMA trend positive (+1.3), Volume 1.25x average"
    metadata: {
        "rsi": 28.5,
        "ema_trend": 1.3,
        "volume_ratio": 1.25
    }
}
```

### Example 2: Mean Reversion SELL Signal

**Input:**
```python
Quote {
    symbol: "TSLA"
    timestamp: "2024-01-15 14:00:00"
    close: 250.00
    z_score: +2.5
}
```

**Process:**
1. Calculate Z-score = +2.5 > threshold ✅
2. Check volatility = high
3. Check momentum = negative

**Output:**
```python
Signal {
    type: SELL
    confidence: 75%
    reason: "Z-score +2.5 indicates overextension, expect mean reversion"
    metadata: {
        "z_score": 2.5,
        "volatility": "high"
    }
}
```

## Module Interactions

```
┌─────────────────┐
│  Data Loader    │ → Quotes
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ TechnicalAnalyst│ → Signals
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Risk Manager   │ → Validated Signals
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ExecutionEngine │ → Trades
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ BacktestingEng.│ → Results
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Dashboard      │ → Visualizations
└─────────────────┘
```

## Testing & Validation

**Unit Tests:**
- `tests/strategies/test_momentum.py` - Momentum strategy tests
- `tests/strategies/test_mean_reversion.py` - Mean reversion tests
- `tests/backtesting/test_backtesting.py` - Backtest engine tests

**Integration Tests:**
- End-to-end backtest execution
- Signal generation → Trade execution
- PnL calculation accuracy
- Metric computation verification

**Performance Benchmarks:**
- Signal generation: <5ms per quote
- Backtest execution: <2s for 1000 quotes
- Dashboard rendering: <1s for 100 trades

