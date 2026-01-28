# Robert Kissell - Algorithmic Trading and Portfolio Management

## Reglas Clave

### 1. Pre-Trade Analysis
- Estimate market impact ANTES de ejecutar
- Model: Impact = α × (size/ADV)^β × volatility
- Typical β: 0.5-0.6 (raíz cuadrada)
- Decision: ejecutar si impact < 50 bps

### 2. Transaction Cost Analysis (TCA)
**Componentes del costo total**:
- Commission: fijo por acción/trade
- Spread: (ask - bid) / 2
- Market impact: función de size/ADV
- Timing cost: precio realizado vs precio decisión
- Opportunity cost: no ejecutar cuando debías

### 3. Implementation Shortfall
IS = (Decision Price - Execution Price) / Decision Price
- Positivo: peor ejecución que decisión
- Target: IS < 20 bps para órdenes líquidas
- Benchmark para evaluar execution quality

### 4. VWAP Benchmark
- Compare precio realizado vs VWAP del día
- VWAP = Σ(Price × Volume) / Σ(Volume)
- Target: estar dentro de ±10 bps de VWAP

### 5. Arrival Price vs VWAP Strategy
- **Arrival Price**: Ejecutar rápido (minimizar timing risk)
  - Usar cuando: alta urgencia, alpha decay rápido
- **VWAP**: Ejecutar pasivo (minimizar market impact)
  - Usar cuando: baja urgencia, órdenes grandes

### 6. Smart Order Routing (SOR)
- Route orders al mejor venue (price, liquidity, fees)
- Considerar: maker-taker fees, rebates, hidden liquidity
- Re-route dinámicamente si condiciones cambian

### 7. Participation Rate
- Target: 10-20% de ADV por día
- >20%: alto market impact
- <5%: timing risk alto (demasiado lento)

### 8. Order Slicing
- Dividir órdenes grandes en child orders
- Schedule: uniforme (TWAP) o volume-weighted (VWAP)
- Adaptar según order book depth

### 9. Post-Trade Analysis
- Comparar execution vs benchmarks
- Analizar: impact, timing, opportunity costs
- Feedback loop: mejorar modelo pre-trade

### 10. Execution Venue Selection
- Lit markets: transparencia, mejor precio
- Dark pools: menos impact, pero adverse selection
- Internalizers: mejor spread, pero routing conflict
- Balance según order size y urgencia
