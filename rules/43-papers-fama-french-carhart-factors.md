# Papers Fundamentales - Fama-French-Carhart Factors

## Fama & French (1993) - Common Risk Factors

### Size Factor (SMB - Small Minus Big)
- Small cap stocks outperform large cap
- SMB = Return_small - Return_large
- Proxy: Russell 2000 vs S&P 500
- Aplicación: overweight small caps en portfolio

### Value Factor (HML - High Minus Low)
- High book-to-market (value) outperform low (growth)
- HML = Return_value - Return_growth
- Métricas: P/B ratio, P/E ratio, dividend yield
- Aplicación: screen por B/M ratio, overweight value

### Market Factor (MKT - Market Return)
- Beta exposure al mercado
- MKT = Return_market - Risk_free_rate
- Aplicación: market-neutral strategies (beta = 0)

### Three-Factor Model
Return = α + β_MKT × MKT + β_SMB × SMB + β_HML × HML + ε
- α (alpha): excess return after adjusting for factors
- Target: α > 0 y estadísticamente significativo

## Carhart (1997) - Momentum Factor

### Momentum Factor (UMD/WML - Up Minus Down)
- Winners continue winning, losers continue losing
- UMD = Return_winners - Return_losers
- Formation period: 12 months
- Skip month: evitar reversión a corto plazo (1 mes)
- Holding period: 1 mes

### Four-Factor Model (Carhart)
Return = α + β_MKT × MKT + β_SMB × SMB + β_HML × HML + β_UMD × UMD + ε
- Añade momentum al modelo Fama-French
- Explica ~95% de variación en returns

## Aplicación Práctica

### Factor Screening
1. Calcular exposición a cada factor
2. Target: exposición positiva a factors con premium
   - SMB: positivo (small caps)
   - HML: positivo (value)
   - UMD: positivo (momentum)
3. Neutralizar si no quieres exposición (ej: beta = 0)

### Factor Timing
- No todos los factores funcionan en todos los regímenes
- Bull market: momentum works, value struggles
- Bear market: value defensivo, momentum reverses
- Adaptar exposición según régimen

### Risk Attribution
- Descomponer retorno en factores
- Return = Factor Returns + Alpha
- Validar que alpha no sea "disfrazado" beta

### Rebalancing
- Rebalance mensual (momentum)
- Rebalance anual (value, size)
- Transaction costs vs factor drift
