# TASK-AUDIT-10: Añadir tolerancias numéricas a tests de riesgo

## 📋 **Descripción**

Incorporar `assertAlmostEqual` con tolerancias definidas (relativas y absolutas) en los tests de riesgo financiero para validaciones estables ante pequeñas variaciones flotantes.

## 🎯 **Objetivo Técnico**

- Implementar tolerancias numéricas en tests de riesgo
- Garantizar validaciones estables ante variaciones flotantes
- Prevenir falsos negativos en tests de precisión

## 📁 **Módulos Afectados**

- `tests/test_portfolio_risk_manager.py` - Tests de gestión de riesgo
- `tests/test_momentum_analysis.py` - Tests de indicadores técnicos
- `tests/test_portfolio_analytics_service.py` - Tests de análisis de portfolio
- `tests/test_signal_scorer.py` - Tests de scoring de señales

## 🔍 **Casos de Test Específicos**

### 1. **Tolerancias para Cálculos de Riesgo**

```python
def test_risk_calculations_with_tolerances():
    """Test que valida cálculos de riesgo con tolerancias"""
    # Casos a probar:
    # - Exposición con tolerancia relativa 1e-6
    # - Correlación con tolerancia absoluta 1e-8
    # - Volatilidad con tolerancia relativa 1e-4
    # - Sharpe ratio con tolerancia absoluta 1e-6
```

### 2. **Tolerancias para Indicadores Técnicos**

```python
def test_technical_indicators_with_tolerances():
    """Test que valida indicadores técnicos con tolerancias"""
    # Casos a probar:
    # - RSI con tolerancia absoluta 1e-6
    # - EMA con tolerancia relativa 1e-8
    # - MACD con tolerancia absoluta 1e-6
    # - ATR con tolerancia relativa 1e-4
```

### 3. **Tolerancias para Cálculos de Portfolio**

```python
def test_portfolio_calculations_with_tolerances():
    """Test que valida cálculos de portfolio con tolerancias"""
    # Casos a probar:
    # - Valor total con tolerancia relativa 1e-6
    # - P&L con tolerancia absoluta 1e-8
    # - Retorno con tolerancia relativa 1e-6
    # - Drawdown con tolerancia absoluta 1e-6
```

### 4. **Tolerancias para Scoring de Señales**

```python
def test_signal_scoring_with_tolerances():
    """Test que valida scoring de señales con tolerancias"""
    # Casos a probar:
    # - Strength score con tolerancia absoluta 1e-6
    # - Confidence score con tolerancia relativa 1e-8
    # - Liquidity score con tolerancia absoluta 1e-6
    # - Combined score con tolerancia relativa 1e-6
```

## ✅ **Criterios de Aceptación**

- [ ] Tolerancias implementadas en todos los tests de riesgo
- [ ] Validaciones estables ante variaciones flotantes
- [ ] Falsos negativos eliminados
- [ ] Tolerancias documentadas y justificadas
- [ ] Tests pasando consistentemente

## 🚨 **Impacto en el Sistema**

- **Riesgo:** Previene falsos negativos y mantiene consistencia de cálculos
- **Confiabilidad:** Garantiza estabilidad en validaciones numéricas
- **Robustez:** Mejora resistencia a variaciones de precisión

## 📊 **Métricas de Éxito**

- **Falsos negativos:** 0 en tests de riesgo
- **Estabilidad:** 100% en validaciones numéricas
- **Tolerancias definidas:** >20 para diferentes tipos de cálculo
- **Tests pasando:** 100% consistentemente

## 🔧 **Implementación Sugerida**

1. Identificar tests que usan comparaciones numéricas exactas
2. Definir tolerancias apropiadas para cada tipo de cálculo
3. Reemplazar `assert` con `assertAlmostEqual`
4. Documentar justificación de tolerancias
5. Validar estabilidad en diferentes plataformas

## 📝 **Notas Técnicas**

- Usar `pytest.approx()` para comparaciones aproximadas
- Implementar tolerancias relativas y absolutas
- Considerar usar `Decimal` para cálculos financieros críticos
- Validar con `math.isclose()` para comparaciones flotantes
- Documentar tolerancias en docstrings de tests
