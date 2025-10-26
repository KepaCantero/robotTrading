# TASK-AUDIT-07: Mejorar tests de CircuitBreakerManager

## 📋 **Descripción**

Mejorar la cobertura de `CircuitBreakerManager` del 68% actual a >95%, añadiendo tests de activación/desactivación, timeouts, y condiciones extremas para garantizar activación correcta de kill switches.

## 🎯 **Objetivo Técnico**

- Aumentar cobertura de CircuitBreakerManager a >95%
- Validar activación y desactivación de circuit breakers
- Garantizar funcionamiento correcto de kill switches

## 📁 **Módulos Afectados**

- `app/services/circuit_breaker_manager.py` - `CircuitBreakerManager`
- `app/models/portfolio.py` - `CircuitBreaker`, `CircuitBreakerState`
- `app/services/portfolio_service.py` - Integración con portfolio

## 🔍 **Casos de Test Específicos**

### 1. **Activación de Circuit Breakers**

```python
def test_circuit_breaker_activation():
    """Test que valida activación de circuit breakers"""
    # Casos a probar:
    # - Activación por error rate threshold
    # - Activación por tiempo de respuesta
    # - Activación por múltiples errores consecutivos
    # - Activación manual por administrador
```

### 2. **Desactivación y Reset**

```python
def test_circuit_breaker_deactivation_and_reset():
    """Test que valida desactivación y reset de circuit breakers"""
    # Casos a probar:
    # - Reset automático después de cooldown
    # - Reset manual por administrador
    # - Reset parcial vs completo
    # - Estado persistente entre reinicios
```

### 3. **Timeouts y Cooldowns**

```python
def test_circuit_breaker_timeouts():
    """Test que valida timeouts y cooldowns"""
    # Casos a probar:
    # - Cooldown period correcto
    # - Timeout de operaciones
    # - Timeout de reset
    # - Timeout de activación
```

### 4. **Condiciones Extremas**

```python
def test_circuit_breaker_extreme_conditions():
    """Test que valida circuit breakers en condiciones extremas"""
    # Casos a probar:
    # - Múltiples circuit breakers activados simultáneamente
    # - Circuit breaker durante alta carga
    # - Circuit breaker con recursos limitados
    # - Circuit breaker con datos corruptos
```

## ✅ **Criterios de Aceptación**

- [ ] Cobertura >95% en CircuitBreakerManager
- [ ] Activación correcta en todos los escenarios
- [ ] Desactivación y reset funcionan correctamente
- [ ] Timeouts y cooldowns respetados
- [ ] Logs detallados de todos los eventos

## 🚨 **Impacto en el Sistema**

- **Riesgo:** Garantiza activación correcta de kill switches
- **Confiabilidad:** Protege contra fallos en cascada
- **Robustez:** Mejora resistencia a condiciones extremas

## 📊 **Métricas de Éxito**

- **Cobertura:** >95% en CircuitBreakerManager
- **Tiempo de activación:** <50ms para circuit breakers
- **Falsos positivos:** <1% en activación
- **Recovery time:** <5 minutos para reset automático

## 🔧 **Implementación Sugerida**

1. Identificar métodos sin cobertura específicos
2. Crear tests para cada estado de circuit breaker
3. Implementar tests de concurrencia
4. Validar timing de activación/desactivación
5. Documentar comportamientos esperados

## 📝 **Notas Técnicas**

- Usar `asyncio` para tests de concurrencia
- Implementar `pytest.mark.slow` para tests de timing
- Usar `unittest.mock` para simular servicios externos
- Validar con `pytest.raises()` para casos de error
- Implementar cleanup automático en teardown
