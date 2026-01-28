# Papers Fundamentales - Almgren-Chriss & Avellaneda-Stoikov

## Almgren & Chriss (2001) - Optimal Execution

### Market Impact Model
**Permanent Impact** (información revelada):
- g(v) = γ × v
- v = participation rate (order size / volume)
- γ: permanent impact coefficient

**Temporary Impact** (liquidez consumida):
- h(v) = ε × sign(v) + η × v
- ε: fixed spread cost
- η: temporary impact coefficient

**Total Cost**:
Cost = ∫[g(v) + h(v)]dv = γ×V + ε×sign(V) + η×(V²/T)
- V: order size
- T: execution horizon

### Optimal Execution Strategy
**Trade-off**:
- Ejecutar rápido: más market impact, menos timing risk
- Ejecutar lento: menos market impact, más timing risk

**Solución óptima**:
- Trajectory: exponencial o lineal según risk aversion
- Risk-neutral: uniform (VWAP)
- Risk-averse: front-loaded (más al inicio)

### Implementation Shortfall
IS = (Execution Price - Decision Price) / Decision Price
- Incluye: impact + timing + opportunity cost
- Benchmark para evaluar execution

## Avellaneda & Stoikov (2008) - Market Making

### Optimal Bid-Ask Spread
**Spread óptimo**:
δ_bid = δ_ask = γ × σ² × (T - t) + (1/γ) × ln(1 + γ/κ)
- γ: risk aversion
- σ: volatility
- T-t: time to end
- κ: order arrival rate

**Implicaciones**:
- Mayor volatility → wider spread
- Menos tiempo restante → tighter spread
- Mayor risk aversion → wider spread

### Inventory Management
**Optimal quotes con inventario**:
- Bid = mid - δ + q×γ×σ²×(T-t)
- Ask = mid + δ + q×γ×σ²×(T-t)
- q: inventory (positivo = long, negativo = short)

**Skewing**:
- Long inventory → bid más bajo, ask más bajo (quieres vender)
- Short inventory → bid más alto, ask más alto (quieres comprar)
- Objetivo: cerrar inventory a cero al final del día

### Risk Control
- Position limits por inventory
- Stop-loss si inventory × price > límite
- Forced liquidation si cerca de cierre

## Aplicación Práctica

### Execution Algorithm (Almgren-Chriss)
1. Estimar market impact parameters (γ, η)
2. Calcular trajectory óptimo
3. Ejecutar según schedule
4. Adaptar si condiciones cambian

### Market Making (Avellaneda-Stoikov)
1. Calcular spread óptimo según volatility
2. Ajustar quotes por inventory
3. Monitorear P&L vs modelo
4. Close inventory antes del cierre

### Pre-Trade Cost Estimation
Impact_estimate = γ × (size/ADV) + η × (size/ADV)²
- Si impact > threshold: slice order o usar dark pool
- Si impact < threshold: ejecutar directamente
