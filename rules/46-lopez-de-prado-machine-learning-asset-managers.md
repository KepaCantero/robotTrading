# Marcos López de Prado - Machine Learning for Asset Managers

## Reglas Clave (Complement to Advances in Financial ML)

### 1. De-Noising Correlation Matrix
**Random Matrix Theory (RMT)**:
- Eigenvalues de matriz aleatoria: λ_min a λ_max conocidos
- λ > λ_max: signal (mantener)
- λ < λ_max: noise (eliminar)
- Reconstruir matriz con solo eigenvalues "signal"

**Aplicación**:
- Mejora optimización de portfolio (Markowitz)
- Reduce overfitting en allocation
- Más estable out-of-sample

### 2. Hierarchical Risk Parity (HRP)
**Algoritmo**:
1. Cluster jerárquico de assets (correlación)
2. Quasi-diagonalization (reordenar matriz)
3. Recursive bisection (asignar pesos)
4. Risk parity dentro de cada cluster

**Ventajas vs Markowitz**:
- No requiere inversión de matriz (más robusto)
- No produce pesos extremos
- Más estable out-of-sample

### 3. Critical Line Algorithm (CLA)
- Efficient Frontier sin errores numéricos
- Más robusto que quadratic programming
- Garantiza pesos dentro de [0, 1]

### 4. Nested Clustered Optimization (NCO)
**Combina**:
- Clustering (reduce dimensionalidad)
- CLA (optimización robusta dentro de clusters)
- Inter-cluster allocation

**Ventajas**:
- Menos overfitting que Markowitz
- Más diversificado que Risk Parity
- Balanced entre ambos extremos

### 5. Maximum Sharpe Ratio Portfolio
**Con constraints**:
- Long-only: weights ≥ 0
- Fully invested: Σweights = 1
- Leverage constraint: ||weights||₁ ≤ leverage_max
- Position limits: weight_i ≤ max_weight

### 6. Minimum Variance Portfolio
- Minimize σ²_portfolio
- Sin considerar expected returns
- Más estable que max Sharpe
- Útil cuando expected returns inciertos

### 7. Black-Litterman Model
**Combina**:
- Market equilibrium (CAPM)
- Investor views (predicciones)
- Bayesian posterior

**Ventajas**:
- Evita pesos extremos
- Incorpora views sin abandonar equilibrium
- Más diversificado

### 8. Mean-Variance vs Risk Parity
**Mean-Variance** (Markowitz):
- Óptimo SI expected returns conocidos
- Pero: expected returns difíciles de estimar
- Overfitting alto

**Risk Parity**:
- Ignora expected returns
- Equal risk contribution por asset
- Menos overfitting
- Pero: puede ignorar alpha

**Recomendación**: NCO (combinación)

### 9. Covariance Matrix Estimation
**Métodos**:
- Sample covariance: simple, pero ruidosa
- Shrinkage (Ledoit-Wolf): reduce ruido
- De-noised (RMT): elimina eigenvalues noise
- Robust (Gerber): resistente a outliers

### 10. Portfolio Turnover Penalty
- High turnover → high transaction costs
- Penalizar cambios: cost = λ × ||w_new - w_old||₁
- λ: transaction cost factor
- Balance: alpha vs costs
