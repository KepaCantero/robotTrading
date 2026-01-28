# Grinold & Kahn - Active Portfolio Management

## Reglas Clave

### 1. Fundamental Law of Active Management
**IR = IC × sqrt(BR)**
- Information Ratio = Information Coefficient × raíz(Breadth)
- IC: Skill (correlación predicción-realidad)
- BR: Breadth (número independiente de apuestas/año)
- Implicación: Más apuestas independientes → mejor IR (aunque IC sea bajo)

### 2. Transfer Coefficient (TC)
- Mide impacto de constraints en performance
- TC = 1.0: sin constraints, alpha completo capturado
- TC < 1.0: constraints reducen alpha
- Calcular: comparar portfolio óptimo vs restringido

### 3. Alpha Shrinkage
- Reducir predicciones de alpha por overconfidence
- Shrinkage = σ_cross / (σ_cross + σ_time)
- Aplicar antes de optimización de portfolio

### 4. Risk Decomposition
- Systematic risk (beta)
- Factor-specific risk (size, value, momentum)
- Idiosyncratic risk (stock-specific)
- Attribution por fuente de riesgo

### 5. Transaction Cost Model
- Costos proporcionales: commission + spread
- Costos cuadráticos: market impact ∝ sqrt(size)
- Incluir en optimización (no solo post-hoc)

### 6. Turnover Constraint
- Limitar turnover mensual (ej: <50%)
- Penalizar cambios frecuentes
- Balance entre alpha capture y costos

### 7. Neutralidad
- Dollar Neutral: suma pesos = 0
- Beta Neutral: beta_portfolio = 0
- Sector Neutral: suma pesos por sector = 0
- Elegir según objetivo

### 8. Maximum Holding Period
- Max 5% ADV por posición
- Evita iliquidez en salida
- Penalty si predicción requiere holding >5% ADV

### 9. Eigenfactor Risk
- Descomponer matriz de covarianza en eigenvectors
- Limitar exposición a primer eigenfactor (market)
- Diversificar entre eigenfactors restantes

### 10. Active Share
- Active Share = 0.5 × Σ|w_portfolio - w_benchmark|
- Target: Active Share > 60% (evitar closet indexing)
- <20%: demasiado parecido al benchmark
