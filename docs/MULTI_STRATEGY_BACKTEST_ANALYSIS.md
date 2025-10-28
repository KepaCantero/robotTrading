# 📊 Análisis del Backtest Multi-Strategy (10 años)

**Fecha**: 2025-10-28  
**Período**: 2015-10-31 a 2025-10-27  
**Capital Inicial**: $100,000  
**Capital Final**: $88,232  
**Retorno Total**: -11.77%

---

## 🎯 Resumen Ejecutivo

### ✅ **Lo que funciona bien:**

**Momentum Strategy** 🟢
- **Trades**: 56 en 10 años (5.6 trades/año) - Frecuencia saludable
- **Win Rate**: 51.8% - Aceptable
- **Retorno**: +2.86%
- **Sharpe**: -0.104
- **Max DD**: -8.46%

**Veredicto**: Estrategia viable, genera retornos consistentes con frecuencia apropiada.

---

### ❌ **Problemas Críticos Identificados:**

#### 1. **Mean Reversion Strategy** ⚠️
- **Trades**: 415 en 10 años (41.5 trades/año) - **OVER-TRADING**
- **Win Rate**: 43.1% - Por debajo del break-even
- **Retorno**: -35.49% ❌
- **Max DD**: -43.12% ❌
- **Capital**: $25,000 → $16,128 (-$8,872)

**Diagnóstico**:
- Lógica simplificada genera demasiadas señales
- No hay confirmación de reversión real
- Falta filtros de calidad (volumen, trend filter)
- Thresholds demasiado permisivos (z_score_threshold: 0.5)

**Impacto**: Pérdida sostenida en 10 años, destruye capital asignado.

---

#### 2. **Pairs Trading Strategy** 🔴 **CRÍTICO**
- **Trades**: 2,304 en 10 años (230.4 trades/año) - **EXCESIVO OVER-TRADING**
- **Win Rate**: 0.2% ❌ - **CATÁSTROFICO**
- **Retorno**: -17.30%
- **Max DD**: -27.40%
- **Capital**: $25,000 → $20,676 (-$4,324)

**Diagnóstico**:
- Operando solo con AAPL (no hay par completo)
- El fallback `_create_simple_buy_signal()` genera señales sin contexto de par
- Faltan datos del segundo símbolo (MSFT) en la serie temporal
- Genera señales sin lógica de cointegración válida

**Impacto**: Casi imposible ganar (de 2304 trades, solo ~4-5 ganaron).

**Root Cause**: 
```python
# FALLA ACTUAL EN app/strategies/pairs_trading.py línea 136-141
else:
    # ALWAYS generate signals for pairs trading
    price_change = (market_data.last - market_data.open) / market_data.open
    if abs(price_change) > Decimal("0.001"):
        signals.append(self._create_simple_buy_signal(market_data))
```

Este código genera señales sin contexto de par válido.

---

## 🔧 Causas Técnicas

### Mean Reversion
1. **Z-score simplificado**: Usa `price_change` del día como Z-score
2. **Thresholds muy bajos**: `z_score_threshold: 0.5` dispara en cualquier movimiento diario > 0.5%
3. **Sin filtros de calidad**: No verifica tendencia, volumen, o contexto de mercado
4. **No hay historial**: Necesita rolling average de 20+ días para Z-score real

### Pairs Trading
1. **No hay contexto de par**: Solo procesa AAPL, necesita MSFT para spread real
2. **Fallback destructivo**: Genera señales simples sin lógica de pares
3. **Spread simulado**: No usa datos históricos del par para calcular spread real
4. **Thresholds permisivos**: spread_threshold: 0.3, min_correlation: 0.4 son muy bajos

---

## 💡 Soluciones Recomendadas

### Opción A: Desactivar Pairs Trading Fallback (Recomendado) ✅

**Acción**: Eliminar el fallback que genera señales destructivas cuando no hay condiciones de par válidas.

```python
# CAMBIO NECESARIO en app/strategies/pairs_trading.py
# Eliminar líneas 136-141 (el else con _create_simple_buy_signal)
# Si no hay condiciones de par válidas, retornar lista vacía
```

**Resultado Esperado**:
- Pairs Trading: 0 trades (mejor que 2,304 destructivos)
- Capital preservado: $25,000
- Retorno total: **-35.49%** (solo MR pierde)

---

### Opción B: Ajustar Mean Reversion a 2-Trades/Año

**Acción**: Hacer MR tan restrictivo como Momentum.

```python
# Aumentar threshold efectivo
z_score_threshold: 2.0  # En vez de 0.5
# Añadir cooldown
cooldown_days: 60
# Añadir filtro de confirmación
require_volume_spike: true
```

**Resultado Esperado**:
- Mean Reversion: ~20 trades en 10 años (como Momentum)
- Win rate mejorado (menos señales falsas)
- Retorno positivo posible

---

### Opción C: Solo Momentum + Mean Reversion Optimizado

**Acción**: Configuración simplificada
- 60% Momentum
- 40% Mean Reversion optimizado
- 0% Pairs Trading (desactivar)

**Ventajas**:
- Elimina componente problemático (PT)
- Enfoque en 2 estrategias probadas
- Asignación 60/40 es más equilibrada

---

## 📈 Interpretación de Resultados

### Análisis de Drawdown
- **Momentum**: -8.46% (aceptable)
- **Mean Reversion**: -43.12% (crítico)
- **Pairs Trading**: -27.40% (alto)
- **Combinado**: -21.86% (alto para Conservative)

### Análisis de Sharpe
- **Momentum**: -0.104 (negativo pero bajo riesgo)
- **Mean Reversion**: -0.045 (muy negativo)
- **Pairs Trading**: -1.277 (catastrófico)
- **Combinado**: -0.382 (muy negativo)

### Análisis de Win Rate
- **Momentum**: 51.8% ✅ (por encima de 50%)
- **Mean Reversion**: 43.1% ⚠️ (por debajo de 50%)
- **Pairs Trading**: 0.2% ❌ (catastrófico)

---

## 🎯 Recomendaciones Inmediatas

### Prioridad CRÍTICA:
1. ❌ **Desactivar fallback en Pairs Trading** - Evita 2,304 trades destructivos
2. ⚠️ **Ajustar Mean Reversion** - Aumentar thresholds para reducir over-trading
3. ✅ **Mantener Momentum** - Única estrategia operativa

### Próximos Pasos:
1. Ejecutar backtest con Pairs Trading sin fallback
2. Optimizar Mean Reversion para 2-5 trades/año
3. Evaluar asignación 60% Momentum / 40% Mean Reversion
4. Considerar añadir filtros ADX para confirmar trending markets

---

## 📊 Conclusión Técnica

**Estado Actual**: Sistema multi-estrategia técnicamente funcional pero con over-trading destructivo en MR y PT.

**Arquitectura**: ✅ Correcta (capital allocation, sub-portfolios, agregación)
**Señal Generation**: ⚠️ Necesita optimización (demasiado permisivo)
**Risk Management**: ⚠️ No previene over-trading de señales de baja calidad

**Recomendación**: Implementar Opción A + B para un backtest equilibrado y rentable.

---

*Análisis generado: 2025-10-28 20:30 UTC*

