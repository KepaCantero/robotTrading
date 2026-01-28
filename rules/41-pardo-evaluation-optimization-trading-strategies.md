# Robert Pardo - Evaluation and Optimization of Trading Strategies

## Reglas Clave

### 1. Walk-Forward Optimization
- In-Sample (IS): 70% datos para optimización
- Out-of-Sample (OOS): 30% datos para validación
- Rolling windows: Re-optimizar cada N meses
- Degradation IS/OOS: Máximo 30% aceptable

### 2. Robustness Testing
- Parameter sensitivity: variar ±20% cada parámetro
- Sharpe debe ser estable (variación <30%)
- Evitar "cliff edges" (caída abrupta con cambio pequeño)

### 3. Monte Carlo Simulation
- Shuffle de trades (preservar distribución)
- 1000+ iteraciones
- Confidence intervals: p5, p50, p95
- Worst-case DD debe ser aceptable (p95 DD < 30%)

### 4. Statistical Significance
- Minimum 30 trades para significancia
- T-test: Sharpe vs 0 (p-value < 0.05)
- Bootstrap confidence intervals
- No confiar en <100 trades para estrategias diarias

### 5. Overfitting Detection
- Complexity penalty: más parámetros → mayor IS/OOS gap requerido
- Regla: 1 parámetro libre por 50 trades
- Reject si >5 parámetros libres con <250 trades

### 6. Transaction Cost Realism
- Commission: datos reales del broker
- Slippage: modelar según spread y order size
- Market impact: √(size / ADV) × volatility
- Recalcular todos los backtests con costos completos

### 7. Data Quality
- Survivorship bias: incluir delisted stocks
- Point-in-time data: corporate actions correctos
- Adjusted prices: splits y dividendos
- Data snooping: no re-usar símbolos de optimization

### 8. Strategy Correlation
- Correlación entre estrategias < 0.7
- Combinar estrategias decorrelacionadas
- Penalizar combinaciones altamente correlacionadas

### 9. Regime Awareness
- Bull market: momentum works
- Bear market: mean reversion works
- Sideways: pairs trading works
- Adaptar según régimen detectado

### 10. Maximum Favorable Excursion (MFE) / Maximum Adverse Excursion (MAE)
- MFE: máximo profit alcanzado durante trade
- MAE: máxima pérdida durante trade
- Usar para optimizar TP/SL
- Target: MFE/MAE ratio > 2.0
