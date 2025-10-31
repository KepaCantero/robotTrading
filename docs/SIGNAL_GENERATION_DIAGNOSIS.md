# Diagnóstico: Problemas de Generación de Señales

## 📋 Resumen Ejecutivo

**Fecha:** 2025-10-31  
**Problema:** No se generan señales / Todos los trades son perdedores  
**Estado:** En Investigación / Corregido parcialmente

## 🔍 Problemas Identificados

### 1. **Error en Conteo de Filtros (CORREGIDO)**

**Problema:**
El método `_determine_signal_type` estaba contando incorrectamente los filtros que pasaban.

**Causa:**

- `_evaluate_filters` crea 3 entradas por cada filtro: `name`, `name_buy`, `name_sell`
- `_determine_signal_type` contaba TODAS las entradas de `filter_results`
- Si hay 6 filtros, `filter_results` tiene 18 entradas, no 6
- La comparación `len(passed_filters) >= total_filters / 2` nunca se cumplía correctamente

**Solución:**
Corregido para contar solo los resultados principales de cada filtro (sin `_buy`/`_sell`):

```python
filter_names = [f.name for f in self.filters]
passed_filters = [
    filter_name for filter_name in filter_names
    if filter_name in filter_results and filter_results[filter_name].get('passed', False)
]
```

**Estado:** ✅ CORREGIDO

---

### 2. **Falta de Señales de Venta**

**Problema:**
La estrategia solo genera señales `BUY`, nunca `SELL`. Esto significa que:

- Se abren posiciones pero nunca se cierran
- Las posiciones solo se cierran al final del backtest
- No hay gestión activa de salidas

**Causa:**

```python
# Revisar condiciones de venta (oversold/sobrecomprado)
market_type = market_context.get('type', 'unknown')
if market_type == 'trend_down':
    # Considerar venta si hay posición
    return None  # Por ahora solo compras

return None
```

**Impacto:**

- Las posiciones pueden mantenerse abiertas indefinidamente
- No se capturan ganancias cuando deberían
- No se cortan pérdidas activamente
- Los resultados del backtest no reflejan la estrategia completa

**Solución Requerida:**
Implementar lógica de SELL que:

1. Verifique si hay posición abierta para el símbolo
2. Genere señal SELL cuando:
   - Los filtros indiquen sobrecompra (RSI alto, momentum negativo, etc.)
   - El contexto de mercado cambie a tendencia bajista
   - Se alcance take-profit o stop-loss

**Estado:** ⚠️ PENDIENTE

---

### 3. **Configuración de Módulos**

**Verificación:**
Los módulos se cargan correctamente según la configuración YAML:

- ✅ `ema_filter`: enabled=True
- ✅ `rsi_filter`: enabled=True
- ✅ `stoch_rsi_filter`: enabled=True
- ✅ `momentum_filter`: enabled=True
- ✅ `volume_filter`: enabled=True
- ✅ `atr_filter`: enabled=True

**Conclusión:** Los módulos se cargan correctamente, no es un problema de configuración.

**Estado:** ✅ VERIFICADO

---

### 4. **Modo de Combinación de Filtros**

**Configuración Actual:**

- `balanced` preset: `combination_mode: "MAJORITY"`
- Con 6 filtros, requiere que al menos 4 pasen (mayoría = >50%)

**Problema Potencial:**
Si los thresholds son muy estrictos, puede ser difícil que 4+ filtros pasen simultáneamente.

**Ejemplo:**

- EMA Filter: requiere tendencia clara (EMA fast > EMA slow)
- RSI Filter: requiere RSI en rango específico según contexto
- Momentum Filter: requiere momentum positivo
- Volume Filter: requiere volumen > 110% del promedio
- ATR Filter: requiere volatilidad suficiente
- StochRSI Filter: requiere StochRSI en rango

**Si todos son estrictos:**

- Es raro que 4+ pasen al mismo tiempo
- Resultado: muy pocas señales generadas

**Recomendaciones:**

1. Cambiar a `combination_mode: "ANY"` para pruebas (más permisivo)
2. Relajar thresholds en preset `balanced`
3. Verificar que los filtros se adapten correctamente al contexto de mercado

**Estado:** ⚠️ REQUIERE AJUSTES

---

### 5. **Contextos de Activación de Filtros**

**Problema Potencial:**
Algunos filtros tienen restricciones de activación según el contexto:

**EMA Filter:**

```yaml
active_in_contexts:
  - "trend_up"
  - "trend_down"
  - "high_vol"
inactive_in_contexts:
  - "low_vol" # Desactivado en baja volatilidad
```

**Impacto:**
Si el mercado está en `low_vol` o `range`, el EMA Filter se desactiva. Esto reduce el número de filtros activos, haciendo más difícil alcanzar la mayoría.

**Recomendaciones:**

1. Revisar si las restricciones de activación son demasiado estrictas
2. Permitir activación en más contextos para pruebas
3. Loggear qué filtros están activos en cada momento

**Estado:** ⚠️ REQUIERE REVISIÓN

---

### 6. **Thresholds Adaptativos de RSI**

**Configuración:**
El RSI Filter usa thresholds adaptativos según el contexto:

- `trend_up`: buy_min=45, buy_max=70
- `trend_down`: buy_min=30, buy_max=50
- `range`: buy_min=30, buy_max=50
- `high_vol`: buy_min=35, buy_max=65

**Problema Potencial:**
Si el RSI está fuera de estos rangos, el filtro no pasa, reduciendo las señales.

**Verificación Necesaria:**

1. ¿Cuál es el rango típico de RSI en los datos históricos?
2. ¿Los thresholds adaptativos son apropiados?
3. ¿El contexto de mercado se detecta correctamente?

**Estado:** ⚠️ REQUIERE VERIFICACIÓN

---

### 7. **Problema de Trades Perdedores**

**Hipótesis 1: Timing de Entrada/Salida**

- Las señales se generan en momentos subóptimos
- No hay señales de salida, las posiciones se mantienen hasta el final
- Si el precio baja después de entrar, todas las posiciones resultan perdedoras

**Hipótesis 2: Stop-Loss Muy Ajustado**

- Si el stop-loss es muy cercano (ej. 2.5%), puede activarse frecuentemente en volatilidad normal
- Esto convertiría trades potencialmente ganadores en perdedores

**Hipótesis 3: Trading Contra la Tendencia**

- Si la estrategia compra en momentos de sobrecompra o en tendencias bajistas
- Las posiciones están condenadas a perder desde el inicio

**Verificación Requerida:**

1. Revisar timing de señales vs. precio
2. Analizar distribución de PnL por trade
3. Verificar si hay correlación entre contexto de mercado y resultado del trade

**Estado:** ⚠️ REQUIERE ANÁLISIS DETALLADO

---

## ✅ Correcciones Implementadas

### 1. Corregido `_determine_signal_type`

- Ahora cuenta correctamente los filtros que pasan
- Agregado logging detallado para debugging
- Lógica de mayoría corregida: `required = max(1, (total_filters + 1) // 2)`

### 2. Agregado Logging

- Logs de debug para ver qué filtros pasan
- Logs de qué modo de combinación se usa
- Logs cuando no se genera señal (razón)

---

## 🔧 Acciones Recomendadas

### Inmediatas (Alta Prioridad)

1. **Implementar Señales SELL**

   - Modificar `_determine_signal_type` para generar SELL cuando:
     - Hay posición abierta
     - Filtros indican sobrecompra
     - Contexto cambia a tendencia bajista
     - Se alcanza take-profit/stop-loss

2. **Relajar Thresholds para Pruebas**

   - Cambiar preset a `aggressive` o `ANY` mode
   - Reducir `min_volume_ratio` (ej. 1.05 en lugar de 1.1)
   - Aumentar rango de RSI para buy (ej. 40-80 en lugar de 45-70)

3. **Revisar Contextos de Activación**
   - Permitir más contextos para EMA Filter
   - Verificar que todos los filtros se activen en condiciones normales

### Mediano Plazo

4. **Análisis de Timing**

   - Comparar señales generadas vs. precio
   - Identificar si las entradas son en momentos apropiados
   - Verificar si el contexto de mercado se detecta correctamente

5. **Mejora de Stop-Loss/Take-Profit**

   - Usar stop-loss dinámico basado en ATR
   - Ajustar según volatilidad actual
   - Revisar si los valores actuales son apropiados

6. **Implementar Salidas Parciales**
   - Vender 50% en take-profit
   - Dejar 50% para seguir la tendencia
   - Trailing stop para la porción restante

---

## 📊 Métricas para Monitorear

Una vez implementadas las correcciones, monitorear:

1. **Generación de Señales**

   - Número de señales BUY generadas por día/semana
   - Número de señales SELL generadas por día/semana
   - Ratio BUY/SELL esperado

2. **Filtros**

   - % de veces que cada filtro pasa
   - Filtros más restrictivos (causan más rechazos)
   - Filtros más permisivos (siempre pasan)

3. **Contexto de Mercado**

   - Distribución de contextos detectados
   - Correlación entre contexto y resultado del trade
   - Exactitud de la detección de contexto

4. **Performance de Trades**
   - Win rate por contexto de mercado
   - Win rate por combinación de filtros que pasaron
   - Distribución de PnL (gains vs. losses)
   - Duración promedio de trades

---

## 🔗 Referencias

- `app/strategies/momentum_modular/strategy.py` - Lógica de generación de señales
- `app/strategies/momentum_modular/modules/filters/` - Implementación de filtros
- `config/strategies/momentum_modular.yaml` - Configuración de módulos y thresholds
- `docs/BACKTEST_ANALYSIS_REPORT.md` - Análisis de resultados de backtest

---

## 📝 Notas Finales

**Estado Actual:**

- ✅ Corrección de conteo de filtros implementada
- ⚠️ Señales SELL pendientes de implementación
- ⚠️ Thresholds y contextos requieren ajuste
- ⚠️ Problema de trades perdedores requiere análisis más profundo

**Próximos Pasos:**

1. Implementar señales SELL
2. Relajar configuración para pruebas
3. Ejecutar backtest de prueba con logging detallado
4. Analizar resultados y ajustar iterativamente
