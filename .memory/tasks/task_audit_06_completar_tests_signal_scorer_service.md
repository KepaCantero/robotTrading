# TASK-AUDIT-06: Completar tests de SignalScorerService

## 📋 **Descripción**

Añadir tests que cubran los 39 caminos no probados en `SignalScorerService`, incluyendo validación de puntuaciones nulas, valores extremos y casos donde no hay suficientes datos de entrada.

## 🎯 **Objetivo Técnico**

- Completar cobertura de código en SignalScorerService
- Validar cálculo de scores de señales en casos extremos
- Garantizar comportamiento determinista del sistema de señales

## 📁 **Módulos Afectados**

- `app/services/signal_scorer.py` - `SignalScorerService`
- `app/services/signal_evaluation_engine.py` - `SignalEvaluationEngine`
- `app/services/position_sizing_engine.py` - `PositionSizingEngine`
- `app/services/signal_execution_engine.py` - `SignalExecutionEngine`

## 🔍 **Casos de Test Específicos**

### 1. **Puntuaciones Nulas y Extremas**

```python
def test_signal_scoring_with_null_and_extreme_values():
    """Test que valida scoring con valores nulos y extremos"""
    # Casos a probar:
    # - Signal con strength_score = None
    # - Signal con confidence_score = 0
    # - Signal con liquidity_score = 1.0
    # - Signal con combined_score fuera de rango
```

### 2. **Datos Insuficientes**

```python
def test_signal_scoring_with_insufficient_data():
    """Test que valida scoring con datos insuficientes"""
    # Casos a probar:
    # - MarketData con campos faltantes
    # - Metadata vacío o None
    # - Datos históricos insuficientes
    # - Indicadores técnicos incompletos
```

### 3. **Casos de Error en Evaluación**

```python
def test_signal_evaluation_error_cases():
    """Test que valida casos de error en evaluación de señales"""
    # Casos a probar:
    # - Error en cálculo de strength_score
    # - Error en cálculo de confidence_score
    # - Error en cálculo de liquidity_score
    # - Timeout en evaluación
```

### 4. **Integración con Motores Especializados**

```python
def test_signal_scorer_engine_integration():
    """Test que valida integración con motores especializados"""
    # Casos a probar:
    # - Evaluación con SignalEvaluationEngine
    # - Sizing con PositionSizingEngine
    # - Ejecución con SignalExecutionEngine
    # - Fallos en cualquier motor
```

## ✅ **Criterios de Aceptación**

- [ ] Cobertura >95% en SignalScorerService
- [ ] Scores de señales calculados dentro de límites seguros
- [ ] Comportamiento determinista en todos los casos
- [ ] Manejo robusto de errores en evaluación
- [ ] Logs detallados para debugging

## 🚨 **Impacto en el Sistema**

- **Riesgo:** Aumenta coherencia y reproducibilidad del sistema de señales
- **Confiabilidad:** Garantiza estabilidad en evaluación de señales
- **Robustez:** Mejora resistencia a datos de entrada imperfectos

## 📊 **Métricas de Éxito**

- **Cobertura:** >95% en SignalScorerService
- **Tests pasando:** 100% en todos los escenarios
- **Tiempo de evaluación:** <100ms por señal
- **Scores válidos:** 100% dentro de rangos esperados

## 🔧 **Implementación Sugerida**

1. Identificar métodos sin cobertura específicos
2. Crear tests para cada caso de uso no cubierto
3. Implementar validaciones de entrada robustas
4. Añadir logging detallado para debugging
5. Documentar comportamientos esperados

## 📝 **Notas Técnicas**

- Usar `pytest.parametrize` para múltiples casos de entrada
- Implementar `pytest.raises()` para casos de error esperados
- Usar `unittest.mock` para simular motores especializados
- Validar con `pytest.mark.asyncio` para operaciones asíncronas
- Implementar fixtures para datos de prueba consistentes
