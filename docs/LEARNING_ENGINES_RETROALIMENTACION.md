# 📊 Retroalimentación de Learning Engines en Backtesting

## ✅ CONFIRMACIÓN: Los Learning Engines SÍ Retroalimentan al Backtest

Los learning engines están **activos y retroalimentando** durante el backtest. Este documento explica exactamente qué hacen y cómo funcionan.

---

## 🔄 Flujo de Retroalimentación

### 1️⃣ **Durante la Generación de Señales** (Cada Quote)

**Archivo:** `app/strategies/momentum_modular/strategy.py` (líneas 179-226)

```python
def generate_signals(self, market_data: Quote) -> List[Signal]:
    # ...
    # 6. SI learning engine está activo, obtener predicción
    if self.learning_engine and self.learning_engine.enabled:
        # Extraer features completas
        features = {
            'indicators': indicators,
            'filter_results': filter_results,
            'market_context': market_context,
            'metadata': {...}
        }

        # Obtener predicción del learning engine
        learning_prediction = self.learning_engine.predict(features)

        # ✅ FILTRAR SEÑAL si probabilidad es baja
        if success_prob < self.min_success_probability:
            return []  # Rechaza la señal

        # ✅ AJUSTAR THRESHOLDS dinámicamente
        self._apply_learning_adjustments(learning_prediction)
```

**Lo que hace:**

- ✅ **Filtra señales** con baja probabilidad de éxito
- ✅ **Ajusta thresholds** de filtros dinámicamente
- ✅ **Influencia en confidence** de la señal (60% filtros, 40% learning)

---

### 2️⃣ **Registro de Market Data** (Cada Timestamp)

**Archivo:** `app/backtesting/engine.py` (líneas 156-181)

```python
# Durante run_backtest(), para cada market_data:
if self.strategy and hasattr(self.strategy, 'learning_engine'):
    # Agregar market data al historial
    self.strategy._learning_updater.add_market_data(
        market_data={
            'price': price,
            'volume': float(getattr(md, 'volume', 0)),
            'symbol': md.symbol
        },
        timestamp=md.timestamp
    )

    # Intentar reentrenar si es necesario (cada 7 días por defecto)
    self.strategy._learning_updater.retrain_if_needed(
        current_date=md.timestamp,
        quotes=market_data[:market_data.index(md)+1]
    )
```

**Lo que hace:**

- ✅ **Acumula datos de mercado** para reentrenamiento futuro
- ✅ **Verifica si debe reentrenar** (cada 7 días por defecto)
- ✅ **Reentrena automáticamente** si hay suficientes trades (>20)

---

### 3️⃣ **Registro de Trades Abiertos** (Al Ejecutar Buy/Sell)

**Archivo:** `app/backtesting/engine.py` (líneas 635-655 y 793-809)

```python
# Al ejecutar un buy/sell:
if self.strategy and hasattr(self.strategy, 'learning_engine'):
    # Registrar trade abierto
    self.strategy._learning_updater.add_trade_result(
        trade={
            'symbol': signal.symbol,
            'entry_time': trade.entry_time,
            'entry_price': float(trade.entry_price),
            'quantity': float(trade.quantity),
            'side': 'buy'  # o 'sell'
        },
        timestamp=market_data.timestamp
    )
```

**Lo que hace:**

- ✅ **Registra trades abiertos** en el historial del learning engine
- ✅ **Prepara datos** para reentrenamiento futuro

---

### 4️⃣ **Registro de Trades Cerrados con P&L** (Al Cerrar Posición)

**Archivo:** `app/backtesting/engine.py` (líneas 790-820)

```python
# Al cerrar un trade (con P&L final):
if self.strategy and hasattr(self.strategy, 'learning_engine'):
    # Registrar trade cerrado CON P&L
    self.strategy._learning_updater.add_trade_result(
        trade={
            'symbol': trade.symbol,
            'entry_time': trade.entry_time,
            'exit_time': trade.exit_time,
            'entry_price': float(trade.entry_price),
            'exit_price': float(trade.exit_price),
            'quantity': float(trade.quantity),
            'pnl': float(trade.pnl),  # ← P&L REAL
            'side': trade.side
        },
        timestamp=exit_time
    )
```

**Lo que hace:**

- ✅ **Registra trades cerrados** con P&L real
- ✅ **Alimenta el historial** para reentrenamiento
- ✅ **Conecta predicciones con resultados reales**

---

## 📈 Qué Hacen los Learning Engines

### **Durante Backtest:**

1. **Filtrado de Señales:**

   - Evalúa cada señal generada
   - Si `success_probability < min_success_probability` → **RECHAZA la señal**
   - Evita trades con baja probabilidad de éxito

2. **Ajuste Dinámico de Thresholds:**

   - Ajusta `min_success_probability` según confianza del modelo
   - Modifica thresholds de filtros si el modelo lo sugiere
   - Se adapta a condiciones de mercado cambiantes

3. **Mejora de Confidence:**

   - Combina confidence de filtros (60%) con predicción de learning (40%)
   - Señales más precisas y mejor calibradas

4. **Reentrenamiento Automático:**
   - Cada 7 días (configurable) verifica si debe reentrenar
   - Si hay >20 trades nuevos, reentrena con datos actualizados
   - **El modelo mejora durante el backtest**

---

## 🔍 Verificación de Activación

Para verificar que los learning engines están activos, revisa los logs:

```
✅ Learning engine activado: supervised
✅ Filtro activado: ema_filter
...
🚫 Señal rechazada por learning engine: prob=0.45 < 0.60
🔄 Iniciando reentrenamiento de SupervisedLearningEngine (25 trades, último reentrenamiento: None)
✅ Reentrenamiento completado: {'train_loss': 0.32, 'val_loss': 0.35}
```

---

## ⚠️ Puntos Importantes

1. **Reentrenamiento no bloqueante:**

   - Si falla el reentrenamiento, el backtest continúa
   - No interrumpe la ejecución

2. **Lookahead bias prevenido:**

   - Solo usa datos hasta el momento actual
   - Labels se generan con delay apropiado (10 días por defecto)

3. **Training/Test separation:**
   - Reentrenamiento usa solo trades anteriores
   - No usa información del futuro

---

## 📊 Resumen

| Componente                     | Estado    | Retroalimentación                       |
| ------------------------------ | --------- | --------------------------------------- |
| **Filtrado de señales**        | ✅ Activo | Rechaza señales con baja probabilidad   |
| **Ajuste de thresholds**       | ✅ Activo | Modifica parámetros dinámicamente       |
| **Registro de market data**    | ✅ Activo | Acumula datos para reentrenamiento      |
| **Registro de trades**         | ✅ Activo | Registra entrada y salida con P&L       |
| **Reentrenamiento automático** | ✅ Activo | Reentrena cada 7 días si hay >20 trades |

---

## 🎯 Conclusión

**SÍ, los learning engines están retroalimentando activamente durante el backtest.**

- **Filtran señales** antes de ejecutarse
- **Ajustan parámetros** dinámicamente
- **Reentrenan** periódicamente con nuevos datos
- **Mejoran** las decisiones de trading durante el backtest

El sistema está diseñado para que los learning engines aprendan y se adapten durante el backtest, mejorando continuamente su capacidad de predicción.
