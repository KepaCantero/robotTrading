# TASK-AUDIT-01: Añadir tests para divisiones por cero en RiskCalculator

## 📋 **Descripción**

Crear unit tests que validen que las funciones de cálculo de riesgo manejan divisiones por cero de forma segura, lanzando `ZeroDivisionError` o devolviendo `0` según política de riesgo.

## 🎯 **Objetivo Técnico**

- Validar manejo seguro de divisiones por cero en cálculos críticos
- Implementar tests para edge cases matemáticos
- Garantizar que los cálculos no interrumpen el flujo del sistema

## 📁 **Módulos Afectados**

- `app/services/portfolio_risk_manager.py` - `assess_portfolio_risk()`
- `app/services/momentum_analysis.py` - `TechnicalIndicatorCalculator.calculate_rsi()`
- `app/services/portfolio_analytics_service.py` - Métodos de cálculo de riesgo

## 🔍 **Casos de Test Específicos**

### 1. **PortfolioRiskManager.assess_portfolio_risk()**

```python
def test_division_by_zero_in_exposure_calculation():
    """Test que valida manejo de división por cero en cálculo de exposición"""
    # Casos a probar:
    # - Portfolio con valor total = 0
    # - Position con cantidad = 0
    # - Precio de activo = 0
    # - Correlación = 0
```

### 2. **TechnicalIndicatorCalculator.calculate_rsi()**

```python
def test_rsi_division_by_zero():
    """Test que valida manejo de avg_loss = 0 en RSI"""
    # Casos a probar:
    # - avg_loss = 0 (debería devolver 100.0)
    # - avg_gain = 0 (debería devolver 0.0)
    # - Ambos = 0 (caso extremo)
```

### 3. **Cálculos de Volatilidad y Sharpe Ratio**

```python
def test_volatility_calculation_edge_cases():
    """Test que valida cálculos de volatilidad con datos extremos"""
    # Casos a probar:
    # - Desviación estándar = 0
    # - Returns vacíos
    # - Returns con valores NaN
```

## ✅ **Criterios de Aceptación**

- [ ] Tests cubren todos los casos de división por cero identificados
- [ ] Funciones devuelven valores seguros (0, NaN, o excepción controlada)
- [ ] No se generan `ZeroDivisionError` no controlados
- [ ] Cobertura de código >95% en métodos de cálculo de riesgo
- [ ] Tests pasan en condiciones extremas de mercado

## 🚨 **Impacto en el Sistema**

- **Riesgo:** Evita fallos matemáticos que afectarían decisiones de trading
- **Confiabilidad:** Garantiza estabilidad en cálculos críticos
- **Robustez:** Mejora resistencia a condiciones extremas de mercado

## 📊 **Métricas de Éxito**

- **Cobertura:** >95% en métodos de cálculo de riesgo
- **Tests pasando:** 100% en condiciones extremas
- **Errores controlados:** 0 divisiones por cero no manejadas

## 🔧 **Implementación Sugerida**

1. Identificar todas las divisiones en métodos de riesgo
2. Crear tests para cada caso de división por cero
3. Implementar manejo seguro (try/catch o validaciones previas)
4. Validar comportamiento con datos extremos
5. Documentar política de manejo de errores matemáticos

## 📝 **Notas Técnicas**

- Usar `pytest.raises()` para validar excepciones esperadas
- Implementar tolerancias numéricas con `assertAlmostEqual()`
- Considerar usar `Decimal` para cálculos financieros críticos
- Validar comportamiento con `math.isnan()` y `math.isinf()`
