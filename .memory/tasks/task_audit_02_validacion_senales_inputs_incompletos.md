# TASK-AUDIT-02: Validar coherencia de señales con inputs incompletos

## 📋 **Descripción**

Implementar tests que simulen escenarios con datos de mercado incompletos o parciales, garantizando que el sistema responde de manera predecible y segura sin generar señales erróneas.

## 🎯 **Objetivo Técnico**

- Validar comportamiento del sistema con datos incompletos
- Garantizar que no se generan señales erróneas o inconsistentes
- Implementar manejo seguro de datos faltantes

## 📁 **Módulos Afectados**

- `app/services/signal_scorer.py` - `SignalScorerService`
- `app/services/signal_evaluation_engine.py` - `SignalEvaluationEngine`
- `app/services/position_sizing_engine.py` - `PositionSizingEngine`
- `app/models/signal.py` - Validación de señales

## 🔍 **Casos de Test Específicos**

### 1. **Datos de Mercado Incompletos**

```python
def test_signal_generation_with_incomplete_market_data():
    """Test que valida generación de señales con datos incompletos"""
    # Casos a probar:
    # - Quote con bid/ask faltantes
    # - HistoricalData con gaps temporales
    # - TechnicalIndicators con valores None
    # - MarketData con campos obligatorios faltantes
```

### 2. **Validación de Señales con Datos Parciales**

```python
def test_signal_validation_with_partial_data():
    """Test que valida validación de señales con datos parciales"""
    # Casos a probar:
    # - Signal con metadata incompleta
    # - SignalType sin datos de soporte
    # - SignalStrength con valores extremos
    # - Timestamp fuera de rango válido
```

### 3. **Manejo de Errores en Evaluación**

```python
def test_signal_evaluation_error_handling():
    """Test que valida manejo de errores en evaluación de señales"""
    # Casos a probar:
    # - Excepción en cálculo de scores
    # - Timeout en evaluación de señales
    # - Datos corruptos o malformados
    # - Recursos insuficientes para procesamiento
```

## ✅ **Criterios de Aceptación**

- [ ] Sistema rechaza señales con datos incompletos críticos
- [ ] Señales válidas se procesan correctamente con datos parciales
- [ ] Errores se manejan de forma consistente y predecible
- [ ] Logs detallados para debugging de problemas de datos
- [ ] Cobertura >95% en métodos de validación de señales

## 🚨 **Impacto en el Sistema**

- **Riesgo:** Protege de decisiones defectuosas por datos faltantes
- **Confiabilidad:** Garantiza coherencia en generación de señales
- **Robustez:** Mejora resistencia a datos de mercado imperfectos

## 📊 **Métricas de Éxito**

- **Cobertura:** >95% en métodos de validación de señales
- **Señales erróneas:** 0 con datos incompletos críticos
- **Tiempo de respuesta:** <100ms para validación de señales

## 🔧 **Implementación Sugerida**

1. Identificar campos críticos vs opcionales en datos de mercado
2. Crear tests para cada tipo de dato incompleto
3. Implementar validaciones robustas en entrada de datos
4. Añadir logging detallado para debugging
5. Documentar política de manejo de datos faltantes

## 📝 **Notas Técnicas**

- Usar `pytest.parametrize` para múltiples casos de datos incompletos
- Implementar validaciones con `pydantic` para datos estructurados
- Considerar usar `Optional` types para campos no críticos
- Validar comportamiento con `pytest.raises()` para casos de error
- Implementar timeouts para operaciones de evaluación
