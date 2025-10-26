# TASK-AUDIT-12: Expandir cobertura de PortfolioRiskManager

## 📋 **Descripción**

Expandir la cobertura de `PortfolioRiskManager` del 82% actual a >95%, añadiendo tests para límites de correlación, exposición sectorial y otros casos de riesgo no cubiertos.

## 🎯 **Objetivo Técnico**

- Aumentar cobertura de PortfolioRiskManager a >95%
- Validar límites de correlación y exposición sectorial
- Garantizar detección de violaciones de riesgo

## 📁 **Módulos Afectados**

- `app/services/portfolio_risk_manager.py` - `PortfolioRiskManager`
- `app/models/portfolio.py` - `Portfolio`, `Position`
- `app/services/portfolio_analytics_service.py` - Análisis de portfolio

## 🔍 **Casos de Test Específicos**

### 1. **Límites de Correlación**

```python
def test_correlation_limit_validation():
    """Test que valida límites de correlación entre activos"""
    # Casos a probar:
    # - Correlación > max_correlation_limit (0.7)
    # - Correlación entre múltiples activos
    # - Correlación con datos históricos insuficientes
    # - Correlación con activos no correlacionados
```

### 2. **Exposición Sectorial**

```python
def test_sector_exposure_validation():
    """Test que valida límites de exposición sectorial"""
    # Casos a probar:
    # - Exposición > max_sector_exposure (0.3)
    # - Exposición con múltiples sectores
    # - Exposición con sectores no definidos
    # - Exposición con activos sin sector
```

### 3. **Límites de Concentración**

```python
def test_concentration_limit_validation():
    """Test que valida límites de concentración de activos"""
    # Casos a probar:
    # - Concentración > max_concentration_limit (0.2)
    # - Concentración con múltiples activos
    # - Concentración con activos de diferentes tipos
    # - Concentración con activos de diferentes monedas
```

### 4. **Validación de Límites de Riesgo**

```python
def test_risk_limit_validation():
    """Test que valida límites de riesgo del portfolio"""
    # Casos a probar:
    # - VaR > max_var_limit (0.05)
    # - CVaR > max_cvar_limit (0.07)
    # - Volatilidad > max_volatility_limit (0.2)
    # - Drawdown > max_drawdown_limit (0.15)
```

## ✅ **Criterios de Aceptación**

- [ ] Cobertura >95% en PortfolioRiskManager
- [ ] Todos los límites de riesgo validados
- [ ] Detección correcta de violaciones
- [ ] Logs detallados de violaciones
- [ ] Tests de integración con portfolio

## 🚨 **Impacto en el Sistema**

- **Riesgo:** Reduce riesgo de violaciones no detectadas
- **Confiabilidad:** Garantiza detección de límites de riesgo
- **Robustez:** Mejora resistencia a condiciones de mercado extremas

## 📊 **Métricas de Éxito**

- **Cobertura:** >95% en PortfolioRiskManager
- **Límites validados:** 100% de límites de riesgo
- **Violaciones detectadas:** 100% de casos de violación
- **Tiempo de validación:** <100ms por validación

## 🔧 **Implementación Sugerida**

1. Identificar métodos sin cobertura específicos
2. Crear tests para cada límite de riesgo
3. Implementar validaciones robustas
4. Añadir logging detallado
5. Documentar límites y comportamientos

## 📝 **Notas Técnicas**

- Usar `pytest.parametrize` para múltiples casos de límites
- Implementar `pytest.raises()` para casos de violación
- Usar `unittest.mock` para simular datos de mercado
- Validar con `pytest.mark.asyncio` para operaciones asíncronas
- Implementar fixtures para portfolios de prueba
