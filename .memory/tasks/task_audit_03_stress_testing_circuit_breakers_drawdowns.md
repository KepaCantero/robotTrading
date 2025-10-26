# TASK-AUDIT-03: Stress Testing de Circuit Breakers y Drawdowns

## 📋 **Descripción**

Crear tests que simulen drawdowns extremos, límites diarios de pérdida y activación de kill-switches para garantizar que el sistema siempre corta operaciones al alcanzar umbrales críticos.

## 🎯 **Objetivo Técnico**

- Validar activación correcta de circuit breakers bajo condiciones extremas
- Garantizar que kill-switches funcionan en escenarios de drawdown extremo
- Implementar tests de estrés para condiciones de mercado adversas

## 📁 **Módulos Afectados**

- `app/services/circuit_breaker_manager.py` - `CircuitBreakerManager`
- `app/services/portfolio_risk_manager.py` - `PortfolioRiskManager`
- `app/services/portfolio_service.py` - `PortfolioService`
- `app/models/portfolio.py` - `CircuitBreaker`, `CircuitBreakerState`

## 🔍 **Casos de Test Específicos**

### 1. **Drawdown Extremo**

```python
def test_circuit_breaker_activation_on_extreme_drawdown():
    """Test que valida activación de circuit breaker por drawdown extremo"""
    # Casos a probar:
    # - Drawdown > max_drawdown_limit (15%)
    # - Drawdown rápido en <1 hora
    # - Drawdown gradual durante el día
    # - Drawdown con múltiples activos
```

### 2. **Límites Diarios de Pérdida**

```python
def test_daily_loss_limit_circuit_breaker():
    """Test que valida activación por límite diario de pérdida"""
    # Casos a probar:
    # - Pérdida diaria > daily_loss_limit (5%)
    # - Pérdida acumulada durante sesión
    # - Pérdida con trades múltiples
    # - Recuperación después de límite alcanzado
```

### 3. **Kill Switch Activation**

```python
def test_kill_switch_activation_scenarios():
    """Test que valida activación de kill switch en escenarios críticos"""
    # Casos a probar:
    # - Múltiples circuit breakers activados simultáneamente
    # - Error rate > threshold
    # - Latencia > max_latency_ms
    # - Volatilidad > volatility_threshold_extreme
```

### 4. **Recovery y Reset**

```python
def test_circuit_breaker_recovery_mechanisms():
    """Test que valida mecanismos de recuperación de circuit breakers"""
    # Casos a probar:
    # - Reset automático después de cooldown
    # - Reset manual por administrador
    # - Estado persistente entre reinicios
    # - Logging de eventos de activación/reset
```

## ✅ **Criterios de Aceptación**

- [ ] Circuit breakers se activan correctamente en todos los escenarios
- [ ] Kill switches cortan operaciones inmediatamente
- [ ] Sistema se recupera correctamente después de activación
- [ ] Logs detallados de todos los eventos de circuit breaker
- [ ] Cobertura >95% en métodos de circuit breaker

## 🚨 **Impacto en el Sistema**

- **Riesgo:** Garantiza seguridad operativa durante backtesting y entornos en vivo
- **Confiabilidad:** Protege contra pérdidas no controladas
- **Robustez:** Mejora resistencia a condiciones de mercado extremas

## 📊 **Métricas de Éxito**

- **Cobertura:** >95% en métodos de circuit breaker
- **Tiempo de activación:** <100ms para kill switches
- **Falsos positivos:** <1% en activación de circuit breakers
- **Recovery time:** <5 minutos para reset automático

## 🔧 **Implementación Sugerida**

1. Crear datos de prueba para escenarios extremos
2. Implementar tests de carga para circuit breakers
3. Validar timing de activación y reset
4. Añadir métricas de rendimiento
5. Documentar procedimientos de emergencia

## 📝 **Notas Técnicas**

- Usar `asyncio` para tests de concurrencia
- Implementar timeouts para tests de activación
- Validar estado persistente con base de datos
- Usar `pytest.mark.slow` para tests de estrés
- Implementar cleanup automático en teardown
- Considerar usar `pytest-xdist` para tests paralelos
