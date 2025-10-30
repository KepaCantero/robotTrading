# Plan de Mejoras Estructurales del Sistema Multi-Strategy

## 📋 Resumen Ejecutivo

Basado en el análisis profundo de los resultados del backtest, se han identificado 8 problemas estructurales críticos y se están implementando mejoras para resolverlos.

## 🔍 Problemas Identificados

### 1. Distribución de Capital Estática ⚠️ CRÍTICO
**Problema**: Capital asignado estáticamente sin adaptarse al rendimiento real.
**Solución**: ✅ **DynamicCapitalReallocationEngine** implementado
- Recalcula pesos cada 30 días basado en rolling Sharpe (30 días)
- Considera ratio Return/Drawdown
- Ajusta por volatilidad (volatility targeting)
- Penaliza estrategias con < 5 trades en ventana de 30 días

### 2. Momentum: Solo 1 Trade ⚠️ CRÍTICO
**Problema**: Señales demasiado restrictivas o filtros que nunca se cumplen.
**Acción Requerida**: 
- ✅ Mejorar logging de señales (ver punto 7)
- ⏳ Ajustar thresholds dinámicamente basado en percentiles
- ⏳ Analizar condiciones previas para identificar filtros bloqueados

### 3. Mean Reversion: Win Rate 15.9% ⚠️ CRÍTICO
**Problema**: Opera contra tendencia sin validación de régimen.
**Acción Requerida**:
- ⏳ Añadir filtro de régimen: operar solo si ATR/volatilidad < percentil 30
- ⏳ Verificar que RSI está en rango neutral (no trending)
- ⏳ Agregar stop-loss dinámico basado en ATR

### 4. Pairs Trading: Inconsistencia P&L ⚠️ CRÍTICO
**Problema**: +0.14% retorno nominal pero -$40K P&L → bug en position sizing o exposición.
**Solución**: ✅ **RiskEnvelopeValidator** implementado
- Valida exposición por símbolo (max 20%)
- Valida exposición por estrategia (max 70%)
- Valida exposición total portfolio (max 95%)
- Bloquea trades que violen límites

**Acción Requerida**:
- ⏳ Integrar RiskEnvelopeValidator en SimpleBacktester
- ⏳ Verificar cálculo de position sizing en Pairs Trading

### 5. Sharpe Negativo en Todas las Estrategias
**Problema**: Exceso de volatilidad sin compensación.
**Acción Requerida**:
- ✅ Volatility targeting incluido en DynamicCapitalReallocationEngine
- ⏳ Implementar ajuste de tamaño de posición para σ ≈ 10% anualizada

### 6. Falta de Diversificación Temporal
**Problema**: Estrategias no operan en timeframes complementarios.
**Acción Requerida**:
- ⏳ Desacoplar horizontes temporales por estrategia
- ⏳ Momentum: 1 día - 1 semana
- ⏳ Mean Reversion: 1 hora - 1 día  
- ⏳ Pairs Trading: multi-día

### 7. Ausencia de Auditoría Granular ⚠️ IMPORTANTE
**Problema**: No hay logs de señales rechazadas ni razones de rechazo.
**Acción Requerida**:
- ✅ SignalDiagnosticLogger existe, pero necesita mejor integración
- ⏳ Registrar TODAS las condiciones previas para Momentum
- ⏳ Log de razones de rechazo para cada trade candidate
- ⏳ Reporte de spreads y fees estimados

### 8. Exceso de Trades Inútiles (Pairs: 215 trades)
**Problema**: No hay validación de cointegración continua.
**Acción Requerida**:
- ⏳ Implementar rolling Engle-Granger test cada 30 días
- ⏳ Eliminar pares con correlación < 0.7
- ⏳ Validar estabilidad de spread antes de entrar

## ✅ Implementaciones Completadas

1. **DynamicCapitalReallocationEngine** (`app/services/dynamic_capital_reallocation.py`)
   - Reasignación automática basada en performance
   - Composite score: Sharpe + Return/Drawdown + Win Rate
   - Volatility targeting integrado
   - Penalización por inactividad

2. **RiskEnvelopeValidator** (`app/services/risk_envelope_validator.py`)
   - Validación de exposición por símbolo (20% max)
   - Validación de exposición por estrategia (70% max)
   - Validación de exposición portfolio (95% max)

## ⏳ Próximos Pasos (Prioridad Alta)

### Integración Inmediata:
1. **Integrar RiskEnvelopeValidator en SimpleBacktester**
   - Validar cada trade antes de ejecutar
   - Bloquear trades que excedan límites

2. **Integrar DynamicCapitalReallocationEngine en MultiStrategyBacktester**
   - Ejecutar rebalanceo cada 30 días durante backtest
   - Registrar performance metrics continuamente
   - Aplicar nuevas asignaciones dinámicamente

3. **Mejorar Lombardía de Señales**
   - Extender SignalDiagnosticLogger para registrar condiciones previas
   - Log detallado de filtros activados/desactivados
   - Reporte de señales rechazadas con razones

### Mejoras de Estrategias:
4. **Mean Reversion: Filtro de Régimen**
   - Detectar régimen trending vs. ranging
   - Operar solo en ranging markets
   - Añadir stop-loss dinámico (ATR × k)

5. **Pairs Trading: Validación de Cointegración**
   - Rolling Engle-Granger test
   - Validación de correlación
   - Eliminación automática de pares inestables

6. **Momentum: Diagnóstico de Condiciones**
   - Log de todas las condiciones previas
   - Identificar filtros bloqueados
   - Ajustar thresholds dinámicamente

## 📊 Métricas de Éxito

Para medir la efectividad de las mejoras:

1. **Win Rate**: > 40% promedio (actualmente 15.9% en Mean Reversion)
2. **Sharpe Ratio**: > 1.0 combinado (actualmente -0.52)
3. **Total Return**: > 0% (actualmente -2.8%)
4. **Momentum Activity**: > 10 trades en periodo de prueba (actualmente 1)
5. **Exposición Controlada**: Ningún símbolo > 20% del capital
6. **Reallocation**: Disminución de capital a estrategias underperforming

## 🔧 Configuración

### DynamicCapitalReallocationEngine
```python
engine = DynamicCapitalReallocationEngine(
    rebalance_frequency_days=30,  # Rebalance cada 30 días
    rolling_window_days=30,        # Ventana de 30 días para métricas
    min_weight=Decimal("0.05"),    # Mínimo 5% por estrategia
    max_weight=Decimal("0.70"),    # Máximo 70% por estrategia
    volatility_target=0.10,        # 10% volatilidad anualizada objetivo
    min_trades_threshold=5,        # Mínimo 5 trades para ser considerada activa
)
```

### RiskEnvelopeValidator
```python
validator = RiskEnvelopeValidator(
    max_total_exposure_pct=Decimal("0.20"),      # 20% max por símbolo
    max_strategy_exposure_pct=Decimal("0.70"),   # 70% max por estrategia
    max_portfolio_exposure_pct=Decimal("0.95"),  # 95% max portfolio total
)
```

## 📝 Notas de Implementación

- Las mejoras están diseñadas para ser no-intrusivas y activarse progresivamente
- Se mantiene compatibilidad con backtests existentes
- Logging extendido para facilitar diagnóstico futuro
- Configuración centralizada para fácil ajuste de parámetros

