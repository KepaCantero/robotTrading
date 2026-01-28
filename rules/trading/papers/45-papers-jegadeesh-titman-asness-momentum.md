# Papers Fundamentales - Momentum (Jegadeesh-Titman & Asness)

## Jegadeesh & Titman (1993) - Returns to Buying Winners and Selling Losers

### Momentum Effect
- Winners últimos 3-12 meses → continúan ganando
- Losers últimos 3-12 meses → continúan perdiendo
- Effect persiste 3-12 meses después de formation

### Optimal Parameters (Original Paper)
- **Formation period**: 12 meses
- **Skip period**: 1 mes (evitar bid-ask bounce y reversión corto plazo)
- **Holding period**: 3-12 meses
- **Rebalance**: mensual

### Implementation
1. Rankear stocks por return últimos 12 meses (skip último mes)
2. Long: top 30% (winners)
3. Short: bottom 30% (losers)
4. Equal weight o weight por momentum magnitude
5. Rebalance mensual

### Risk Management
- Momentum crashes: severos en market reversals
- Hedge: stop-loss, position limits
- Diversification: cross-asset momentum

## Asness, Moskowitz & Pedersen (2013) - Value and Momentum Everywhere

### Cross-Asset Momentum
**Assets cubiertos**:
- Equities: individual stocks
- Equity indices: S&P 500, FTSE, Nikkei
- Currencies: FX pairs
- Commodities: energy, metals, agriculture
- Fixed income: bonds, rates

### Time-Series Momentum (TSMOM)
- Signal: sign(Return_t-1 a t-12)
- Long si positivo, short si negativo
- Más robusto que cross-sectional (no requiere universo)

### Combination Strategy
**Value + Momentum**:
- Low correlation entre factors (~0.2)
- Combinar: 50% value + 50% momentum
- Sharpe improvement: √2 (aprox)
- Diversification benefit

### Risk-Adjusted Momentum
- Scale position size por volatility
- Target volatility: 10-15% anual
- Position = (Target Vol / Realized Vol) × base_size

### Regime Detection
- Momentum works en trending markets
- Momentum fails en mean-reverting markets
- Use ADX, Hurst exponent para detectar régimen
- Reduce exposure si Hurst < 0.5 (mean-reverting)

## Aplicación Práctica

### Multi-Asset Momentum Strategy
1. Universo: stocks, ETFs, FX, commodities
2. Señal: return últimos 12 meses (skip 1 mes)
3. Rank cross-sectional
4. Long top 20%, short bottom 20%
5. Volatility targeting por asset
6. Rebalance mensual

### Momentum + Quality Screen
1. Calculate momentum score
2. Filter: solo quality stocks (ROE > 15%, Debt/Equity < 0.5)
3. Reduce momentum crashes
4. Improve Sharpe ratio

### Stop-Loss for Momentum
- Momentum crash detection: mercado down >10% en mes
- Stop-loss: exit all si detección de crash
- Re-entry: cuando market stabilizes
