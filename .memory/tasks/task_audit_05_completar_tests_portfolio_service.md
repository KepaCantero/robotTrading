# TASK-AUDIT-05: Completar tests de PortfolioService

## 📋 **Descripción**

Cubrir las 19 líneas sin test de `PortfolioService`, incluyendo rutas de error en rebalanceo y cierre de posiciones por límites de pérdida para alcanzar cobertura 100%.

## 🎯 **Objetivo Técnico**

- Completar cobertura de código en PortfolioService
- Validar rutas de error en operaciones críticas
- Garantizar manejo seguro de límites de pérdida

## 📁 **Módulos Afectados**

- `app/services/portfolio_service.py` - `PortfolioService`
- `app/models/portfolio.py` - `Portfolio`, `Position`
- `app/services/portfolio_risk_manager.py` - Integración con gestión de riesgo

## 🔍 **Casos de Test Específicos**

### 1. **Rebalanceo con Errores**

```python
def test_portfolio_rebalancing_error_scenarios():
    """Test que valida rebalanceo con escenarios de error"""
    # Casos a probar:
    # - Rebalanceo con activos no disponibles
    # - Rebalanceo con límites de riesgo excedidos
    # - Rebalanceo con datos de mercado faltantes
    # - Rebalanceo con errores de ejecución
```

### 2. **Cierre de Posiciones por Límites**

```python
def test_position_closing_by_limits():
    """Test que valida cierre de posiciones por límites de pérdida"""
    # Casos a probar:
    # - Stop loss automático
    # - Take profit automático
    # - Cierre por límite diario de pérdida
    # - Cierre por drawdown máximo
```

### 3. **Gestión de Errores en Operaciones**

```python
def test_portfolio_service_error_handling():
    """Test que valida manejo de errores en PortfolioService"""
    # Casos a probar:
    # - Errores de conexión con proveedor
    # - Errores de validación de datos
    # - Errores de cálculo de riesgo
    # - Errores de persistencia de datos
```

### 4. **Integración con Circuit Breakers**

```python
def test_portfolio_circuit_breaker_integration():
    """Test que valida integración con circuit breakers"""
    # Casos a probar:
    # - Activación de circuit breaker durante operación
    # - Recuperación después de circuit breaker
    # - Estado de portfolio durante circuit breaker
    # - Logging de eventos de circuit breaker
```

## ✅ **Criterios de Aceptación**

- [ ] Cobertura 100% en PortfolioService
- [ ] Todos los casos de error están cubiertos
- [ ] Operaciones críticas tienen manejo de errores robusto
- [ ] Logs detallados para debugging
- [ ] Tests de integración con servicios relacionados

## 🚨 **Impacto en el Sistema**

- **Riesgo:** Reduce riesgo de pérdidas no controladas en ejecución real
- **Confiabilidad:** Garantiza estabilidad en operaciones de portfolio
- **Robustez:** Mejora resistencia a fallos en servicios externos

## 📊 **Métricas de Éxito**

- **Cobertura:** 100% en PortfolioService
- **Tests pasando:** 100% en todos los escenarios
- **Tiempo de respuesta:** <200ms para operaciones críticas
- **Errores manejados:** 100% de casos de error cubiertos

## 🔧 **Implementación Sugerida**

1. Identificar líneas sin cobertura específicas
2. Crear tests para cada ruta de código no cubierta
3. Implementar mocks para servicios externos
4. Validar comportamiento en casos de error
5. Documentar casos de uso y comportamientos esperados

## 📝 **Notas Técnicas**

- Usar `pytest.fixture` para setup de portfolio de prueba
- Implementar `pytest.raises()` para casos de error esperados
- Usar `unittest.mock` para simular servicios externos
- Validar con `pytest.mark.asyncio` para operaciones asíncronas
- Implementar cleanup automático en teardown
