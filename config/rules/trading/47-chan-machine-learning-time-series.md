# Nicholas Chan - Machine Learning for Time Series

## Reglas Clave

### 1. Stationarity Enforcement
**Tests**:
- ADF (Augmented Dickey-Fuller)
- KPSS (Kwiatkowski-Phillips-Schmidt-Shin)
- PP (Phillips-Perron)

**Transformations**:
- Returns vs prices (casi siempre usar returns)
- Log returns para simetría
- Fractional differentiation (López de Prado)
- Differencing: Δx_t = x_t - x_t-1

### 2. Autocorrelation Detection
- ACF (AutoCorrelation Function)
- PACF (Partial AutoCorrelation Function)
- Ljung-Box test (p-value < 0.05 → autocorrelation)
- Implicación: Sharpe ratio inflado si ignoras

### 3. Feature Engineering para Time Series
**Lag features**:
- return_t-1, return_t-2, ..., return_t-n
- Evitar leakage: solo usar t-1 en features para predecir t

**Rolling statistics**:
- rolling_mean(window=20)
- rolling_std(window=20)
- rolling_max, rolling_min

**Technical indicators**:
- RSI, MACD, Bollinger Bands
- Momentum, ROC
- Volume-based: OBV, VWAP

### 4. Train-Test Split Temporal
**NUNCA random split**:
- Train: primeros 70% cronológicamente
- Test: últimos 30% cronológicamente
- Walk-forward: re-train cada N días

**TimeSeriesSplit** (sklearn):
- K folds cronológicos
- Train size crece, test size fijo
- Simula producción

### 5. Seasonal Decomposition
- Trend: long-term movement
- Seasonal: periodic patterns
- Residual: random noise
- STL decomposition (Seasonal-Trend-Loess)

### 6. ARIMA/GARCH Models
**ARIMA** (AutoRegressive Integrated Moving Average):
- AR(p): autorregresión
- I(d): integración (differencing)
- MA(q): moving average
- Selección: AIC/BIC mínimo

**GARCH** (Generalized AutoRegressive Conditional Heteroskedasticity):
- Modela volatility clustering
- σ²_t = α₀ + α₁×ε²_t-1 + β₁×σ²_t-1
- Útil para risk management

### 7. Cointegration (Pairs Trading)
**Engle-Granger test**:
1. Regress Y on X: Y = α + β×X + ε
2. Test stationarity de ε (ADF)
3. p-value < 0.05 → cointegrated

**Johansen test**:
- Multivariate cointegration
- Más robusto que Engle-Granger
- Identifica múltiples relaciones

### 8. Regime Detection
**Hidden Markov Models (HMM)**:
- States: bull, bear, sideways
- Transition probabilities
- Emission probabilities (observables)

**Change Point Detection**:
- CUSUM (Cumulative Sum)
- Bayesian change point
- Detección de structural breaks

### 9. Cross-Validation para Time Series
**Blocked Cross-Validation**:
- Block size > autocorrelation length
- Gap between train/test (embargo period)
- Preserva temporal structure

**Combinatorial Purged CV** (López de Prado):
- Purge overlapping samples
- Embargo period para evitar leakage
- Más realista que K-Fold estándar

### 10. Feature Selection
**Methods**:
- Recursive Feature Elimination (RFE)
- LASSO (L1 regularization)
- Tree-based importance (MDI, MDA)
- Correlation filtering

**Criteria**:
- Remove alta correlación (>0.95)
- Remove baja varianza
- Keep top N por importance score
