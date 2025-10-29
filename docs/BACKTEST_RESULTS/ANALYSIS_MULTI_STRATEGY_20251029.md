# 🔍 Análisis Detallado: Multi-Strategy Backtest Results

**Fecha**: 2025-10-29  
**Backtest**: all_strategies - Conservative  
**Período**: 2015-11-01 to 2025-10-28 (10 años)

---

## 📊 Resumen Ejecutivo

### Resultados Generales

- **Capital Inicial**: $100,000
- **Capital Final**: $92,778.89
- **Retorno Total**: **-7.22%** ❌
- **Total Trades**: 381
- **Sharpe Ratio**: -0.026 (negativo = riesgo sin recompensa)
- **Max Drawdown**: -9.86%

### Distribución de Trades por Estrategia

| Estrategia         | Capital       | Trades | % del Total | Retorno | Estado           |
| ------------------ | ------------- | ------ | ----------- | ------- | ---------------- |
| **Momentum**       | $50,000 (50%) | 0      | 0%          | 0.00%   | ⚠️ **INACTIVA**  |
| **Mean Reversion** | $25,000 (25%) | 381    | 100%        | -28.88% | ❌ **PERDIENDO** |
| **Pairs Trading**  | $25,000 (25%) | 0      | 0%          | 0.00%   | ⚠️ **INACTIVA**  |

**⚠️ PROBLEMA CRÍTICO**: Solo 1 de 3 estrategias está activa, y esa está perdiendo dinero significativamente.

---

## 🔴 Análisis de Problemas

### 1. MOMENTUM: 0 Trades (50% del capital inactivo)

#### Síntomas

- **Capital asignado**: $50,000 (50% del total)
- **Trades ejecutados**: 0
- **Capital final**: $50,000 (sin cambios)

#### Causas Probables

**A) Filtros de Indicadores Muy Restrictivos**

```python
# Momentum requiere múltiples condiciones simultáneas:
- RSI < 40 (oversold)
- Precio > EMA (tendencia alcista)
- Volumen > 1.5x promedio
- ATR > 1.5% (volatilidad mínima)
- Stochastic RSI favorable
- Cooldown entre señales
```

**B) Histórico Insuficiente**

- Momentum necesita al menos 14-50 barras de histórico
- Si los datos empiezan cerca del inicio del backtest, puede no haber suficiente histórico inicial

**C) Símbolos No Cumplen Condiciones**

- Los símbolos de Technology (AAPL, MSFT, etc.) pueden no cumplir todas las condiciones de momentum simultáneamente
- Mercados laterales o bajistas no generan señales de momentum

#### Recomendación

1. **Reducir umbrales** de RSI, ATR, y volumen
2. **Aumentar lookback period** si hay suficiente histórico
3. **Verificar logs** de por qué no se generan señales
4. **Simplificar filtros** temporalmente para diagnóstico

---

### 2. PAIRS TRADING: 0 Trades (25% del capital inactivo)

#### Síntomas

- **Capital asignado**: $25,000 (25% del total)
- **Trades ejecutados**: 0
- **Capital final**: $25,000 (sin cambios)

#### Causas Probables

**A) pair_symbols No Configurado Correctamente**

```python
# Pairs Trading requiere:
if market_data.symbol not in self.pair_symbols:
    return signals  # Sin señales si símbolo no está en par
```

**B) Condiciones de Spread No Cumplidas**

```python
# Requiere todas estas condiciones:
- spread_threshold: 0.3 (muy bajo)
- cointegration_threshold: 0.01
- min_correlation: 0.4
- _is_spread_signal() debe retornar True
```

**C) No Hay Pares Válidos en Portfolio**

- Los sectores configurados (banks, energy, technology) pueden no tener pares correlacionados
- Pairs Trading necesita SÍMBOLOS ESPECÍFICOS como par, no solo sectores

#### Recomendación

1. **Configurar pair_symbols explícitos**:

   ```yaml
   # Ejemplo en portfolio.yaml
   pairs_trading:
     pair_symbols:
       - ["AAPL", "MSFT"] # Par de tecnología
       - ["JPM", "BAC"] # Par de bancos
       - ["XOM", "CVX"] # Par de energía
   ```

2. **Verificar correlación histórica** entre símbolos propuestos
3. **Bajar thresholds temporalmente** para diagnóstico:
   - spread_threshold: 0.1
   - cointegration_threshold: 0.005
   - min_correlation: 0.3

---

### 3. MEAN REVERSION: 381 Trades, -28.88% Retorno

#### Síntomas

- **Capital asignado**: $25,000 (25% del total)
- **Trades ejecutados**: 381 (100% de todos los trades)
- **Retorno**: -28.88% ❌
- **Win Rate**: 42.0% (aceptable pero insuficiente)
- **Sharpe Ratio**: -0.106 (negativo)
- **Max Drawdown**: -39.44% (muy alto)

#### Análisis del Problema

**A) Win Rate vs Retorno**

- Win Rate del 42% debería generar retorno positivo si:
  - Los trades ganadores compensan los perdedores
  - El stop loss no es demasiado estrecho
  - El take profit es adecuado

**B) Problemas Identificados**

1. **Stop Loss Muy Estrecho**: 3% (mean_reversion.yaml)

   - En mercados volátiles, 3% se activa muy rápido
   - 381 trades sugieren muchas entradas y salidas rápidas

2. **Take Profit Pequeño**: 6%

   - Ratio stop_loss:take_profit = 1:2
   - Si solo ganas el 42% de las veces, necesitas al menos 1:2.5 para ser rentable

3. **Z-Score Threshold Muy Bajo**: 0.5

   - Con z-score de 0.5, estás entrando en desviaciones pequeñas
   - Mayor probabilidad de falsas señales
   - Mayor número de trades que no se revierten

4. **Exposición Máxima**: 60%
   - Puede estar sobre-apalancado en posiciones perdedoras

#### Cálculo Teórico

Con win rate del 42%:

- 381 trades × 42% = 160 trades ganadores
- 381 trades × 58% = 221 trades perdedores
- Si stop loss = -3% y take profit = +6%:
  - Pérdidas promedio: -3% × 221 = -663 puntos
  - Ganancias promedio: +6% × 160 = +960 puntos
  - Net: +297 puntos teóricos

**Pero el retorno es -28.88%**, lo que sugiere:

- Stop loss se activa más frecuentemente que el take profit
- Costos de transacción (commission + slippage) están erosionando ganancias
- Posibles gaps que saltan el stop loss

#### Recomendación

1. **Ajustar ratio stop_loss:take_profit** a 1:3 o 1:4
2. **Aumentar z_score_threshold** a 1.0 o 1.5 (menos trades, mayor calidad)
3. **Revisar comisiones y slippage** - pueden estar muy altas
4. **Añadir filtro de volumen** para evitar gaps
5. **Considerar trailing stop** en vez de stop loss fijo

---

## 📈 Impacto en Portfolio Total

### Análisis de Capital

- **Momentum ($50,000)**: Sin actividad → $50,000 (0% retorno)
- **Mean Reversion ($25,000)**: -28.88% → $17,779 (-$7,221 pérdida)
- **Pairs Trading ($25,000)**: Sin actividad → $25,000 (0% retorno)
- **Total**: $92,779 (-$7,221 / -7.22%)

### Observaciones

1. **50% del capital está completamente inactivo** (Momentum + Pairs Trading)
2. **El 100% de las pérdidas vienen de Mean Reversion** (la única estrategia activa)
3. **Sin Momentum, el portfolio no tiene estrategias alcistas** para aprovechar tendencias
4. **Sin Pairs Trading, no hay diversificación** de estilos de trading

---

## ✅ Plan de Acción Recomendado

### Fase 1: Diagnóstico (Inmediato)

1. **Verificar logs de generación de señales**:

   - ¿Por qué Momentum no genera señales?
   - ¿Por qué Pairs Trading no genera señales?
   - ¿Qué símbolos están siendo evaluados?

2. **Revisar configuración de portfolio.yaml**:
   - Símbolos disponibles vs símbolos requeridos
   - pair_symbols configurado correctamente
   - Sectores correctamente asignados

### Fase 2: Ajustes de Parámetros (Corto Plazo)

1. **Momentum**:

   - Reducir `rsi_threshold` a 35
   - Reducir `momentum_threshold` a 0.015
   - Reducir `volume_threshold` a 1.2
   - Deshabilitar temporalmente ATR filter para diagnóstico

2. **Pairs Trading**:

   - Configurar `pair_symbols` explícitos en configuración
   - Reducir `spread_threshold` a 0.1
   - Reducir `min_correlation` a 0.3

3. **Mean Reversion**:
   - Aumentar `z_score_threshold` a 1.0
   - Ajustar `stop_loss_pct` a 0.04 (4%)
   - Aumentar `take_profit_pct` a 0.12 (12%)
   - Ratio 1:3 más apropiado

### Fase 3: Validación (Mediano Plazo)

1. Ejecutar backtest con nuevos parámetros
2. Comparar resultados:
   - Trades por estrategia
   - Win rate por estrategia
   - Sharpe ratio por estrategia
3. Iterar hasta que todas las estrategias generen trades

### Fase 4: Optimización (Largo Plazo)

1. Usar Optuna para optimizar parámetros simultáneamente
2. Ajustar asignación de capital basada en performance histórica
3. Implementar rotación de estrategias según condiciones de mercado

---

## 📝 Notas Técnicas

### Archivos Relevantes

- `app/backtesting/multi_strategy_engine.py` - Motor de backtest multi-estrategia
- `app/strategies/momentum.py` - Lógica de generación de señales Momentum
- `app/strategies/mean_reversion.py` - Lógica de generación de señales Mean Reversion
- `app/strategies/pairs_trading.py` - Lógica de generación de señales Pairs Trading
- `config/portfolio.yaml` - Configuración de sectores y asignaciones
- `config/strategies/*.yaml` - Parámetros de estrategias

### Métricas Clave a Monitorear

- **Señales generadas** vs **Trades ejecutados** (para identificar filtros restrictivos)
- **Win rate** por estrategia
- **Sharpe ratio** por estrategia
- **Max drawdown** por estrategia
- **Capital allocation efficiency** (% de capital que genera trades)

---

## 🎯 Conclusión

El backtest multi-estrategia actual muestra:

**✅ Funciona**:

- La infraestructura multi-estrategia funciona correctamente
- Mean Reversion genera señales y ejecuta trades
- La asignación de capital se respeta

**❌ Problemas Críticos**:

1. **Momentum inactivo** - 50% del capital sin uso
2. **Pairs Trading inactivo** - 25% del capital sin uso
3. **Mean Reversion perdiendo** - La única estrategia activa tiene retorno negativo significativo

**🔧 Acciones Inmediatas**:

1. Diagnosticar por qué Momentum y Pairs Trading no generan señales
2. Ajustar parámetros de Mean Reversion para mejorar ratio riesgo/retorno
3. Configurar correctamente pair_symbols para Pairs Trading
4. Validar que todos los símbolos necesarios estén disponibles en CSV

---

_Análisis generado: 2025-10-29_
