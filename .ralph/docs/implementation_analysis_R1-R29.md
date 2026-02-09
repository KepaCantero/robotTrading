# Análisis de Implementación - Reglas R1-R29
## Realistic Retail Trading Rules

**Fecha:** 2026-02-08
**Objetivo:** Analizar qué reglas R1-R29 ya están implementadas en el código

---

## RESUMEN EJECUTIVO

| Categoría | Reglas | Implementadas | Parcialmente | No Implementadas |
|-----------|--------|---------------|--------------|------------------|
| Gestión de Capital | R1-R4 | 3 | 1 | 0 |
| Backtesting | R5-R7 | 1 | 1 | 1 |
| Ejecución | R8-R10 | 0 | 1 | 2 |
| Posiciones | R11-R13 | 0 | 0 | 3 |
| Data | R14-R16 | 1 | 0 | 2 |
| Psicología | R17-R18 | 0 | 0 | 2 |
| Análisis | R19-R21 | 1 | 1 | 1 |
| Adaptación | R22-R24 | 1 | 0 | 2 |
| Escalado | R25-R27 | 0 | 1 | 2 |
| Compliance | R28-R29 | 0 | 1 | 1 |
| **TOTAL** | **29** | **7 (24%)** | **7 (24%)** | **15 (52%)** |

---

## ANÁLISIS DETALLADO POR REGLA

### ✅ COMPLETAMENTE IMPLEMENTADAS (7)

#### R1. Kelly Criterion + Tamaño Máximo
**Status:** ✅ IMPLEMENTADO
**Ubicación:**
- `app/services/position_sizing_engine.py` - PositionSizingEngine
- `app/backtesting/labeling/bet_sizing.py` - Kelly sizing
- `app/domain/configurators/risk_configurator.py` - Risk parameters

**Evidencia:**
```python
# En position_sizing_engine.py
class PositionSizingEngine:
    def calculate_position_size(self, capital, win_rate, avg_win, avg_loss):
        kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        return kelly * 0.5  # Half-Kelly
```

---

#### R2. Drawdown Máximo
**Status:** ✅ IMPLEMENTADO
**Ubicación:**
- `app/services/risk_scaling/drawdown_monitor.py`
- `app/services/risk_scaling/risk_scaling_monitor.py`
- `app/engines/risk_engine/drawdown_controllers/`
- `app/services/alerting_system/rule_templates.py` - portfolio_drawdown_halt()

**Evidencia:**
```python
# En rule_templates.py
def portfolio_drawdown_halt() -> AlertRule:
    return AlertRule(
        threshold=Decimal("15.0"),  # 15% circuit breaker
        tags={"action": "halt_trading"}
    )
```

---

#### R3. Correlación y Concentración
**Status:** ✅ IMPLEMENTADO
**Ubicación:**
- `app/services/correlation/example_usage.py`
- `app/portfolio/multi_asset/allocation.py`
- `app/domain/services/portfolio_optimization/`

---

#### R4. Ratio Riesgo/Beneficio Mínimo 2:1
**Status:** ⚠️ PARCIALMENTE IMPLEMENTADO
**Ubicación:**
- `app/services/risk_management_chan.py` - Risk/reward analysis
- `config/strategy_defaults.yaml` - risk_management.stop_loss_pct

**Falta:** Validación automática en señal de entrada

---

#### R14. Calidad de Datos
**Status:** ✅ IMPLEMENTADO
**Ubicación:**
- `app/sre/data_integrity/sanity_layer.py`
- `app/backtesting/services/database_service.py`
- `app/database/repositories.py`

---

#### R19. Identificación de Régimen de Mercado
**Status:** ✅ IMPLEMENTADO
**Ubicación:**
- `app/services/regime_detection_chan.py`
- `app/backtesting/validation/regime_detector.py`

---

#### R22. Revisión Mensual
**Status:** ✅ IMPLEMENTADO
**Ubicación:**
- `app/services/portfolio_analytics_service.py`
- `app/backtesting/report_generator.py`

---

### ⚠️ PARCIALMENTE IMPLEMENTADAS (7)

#### R5. Walk-Forward Analysis
**Status:** ⚠️ PARCIAL
**Ubicación:**
- `app/backtesting/walk_forward_validator.py`
- `app/backtesting/walk_forward_validator_enhanced.py`
- `app/backtesting/validation/walk_forward.py`

**Falta:** Validación de degradación OOS 30% automática

---

#### R8. Gestión de Spread Bid-Ask
**Status:** ⚠️ PARCIAL
**Ubicación:**
- `app/microstructure/liquidity.py` - Spread analysis
- `app/simulation/trading_costs.py` - Trading costs

**Falta:** Lógica automática de limit vs market orders

---

#### R10. Slippage Máximo
**Status:** ⚠️ PARCIAL
**Ubicación:**
- `app/simulation/trading_costs.py` - Slippage simulation
- `app/backtesting/execution_engine.py`

**Falta:** Validación en ejecución live con alertas

---

#### R20. Confirmación Múltiple
**Status:** ⚠️ PARCIAL
**Ubicación:**
- `app/domain/entities/pre_trade_analysis.py` - Pre-trade checks
- `app/services/signal_scorer.py` - Signal scoring

**Falta:** Validador de 2+ confirmaciones automático

---

#### R21. Volumen como Filtro
**Status:** ⚠️ PARCIAL
**Ubicación:**
- `app/microstructure/liquidity.py` - Volume analysis
- `app/services/value_signal_enhancer.py`

**Falta:** Filtro de volumen en señal de entrada

---

#### R25-R27. Fases de Capital
**Status:** ⚠️ PARCIAL
**Ubicación:**
- `app/services/capital_tier_strategy_selector.py`
- `config/capital_tiers.yaml`
- `config/rollout/` - Stage configs

**Falta:** Sistema completo de CapitalPhaseManager con parámetros por fase

---

#### R28. Registro de Operaciones
**Status:** ⚠️ PARCIAL
**Ubicación:**
- `app/database/models.py` - Trade models
- `app/sre/reconciliation/boot_reconciler.py`

**Falta:** Formato específico para Hacienda con retención 5 años

---

### ❌ NO IMPLEMENTADAS (15)

#### R6. Prevención de Overfitting
**Falta:**
- Validador de ratio parámetros/datos < 1:30
- Purged cross-validation con embargo temporal

**Archivos a crear:**
- `app/backtesting/validation/overfitting_guard.py`

---

#### R7. Monte Carlo para Riesgo
**Falta:**
- Simulaciones Monte Carlo de backtest
- Validación de resultado real vs percentiles 5-95%

**Archivos a crear:**
- `app/services/risk/monte_carlo_analyzer.py`

---

#### R9. Timing de Ejecución
**Falta:**
- Evitar primeros/últimos 15 min del mercado
- Evitar anuncios macro (FED, CPI, NFP)

**Archivos a crear:**
- `app/services/execution_timing.py`

---

#### R11. Trailing Stop Dinámico
**Falta:**
- Trailing stop que se ajusta con beneficio (2R, 3R, etc.)

**Archivos a crear:**
- `app/services/position_management/trailing_stop_manager.py`

---

#### R12. Take Profit Parcial
**Falta:**
- Cierre parcial en hitos (2R: 50%, 3R: 25%)

**Archivos a crear:**
- `app/services/position_management/partial_take_profit.py`

---

#### R13. Pyramiding
**Falta:**
- Añadir posiciones solo a ganadores

**Archivos a crear:**
- `app/services/position_management/pyramiding_manager.py`

---

#### R15. Logging Completo
**Falta:**
- Logger de decisiones con timestamp completo

**Archivos a crear:**
- `app/services/logging/trading_decision_logger.py`

---

#### R16. Reconciliación Diaria
**Falta:**
- Reconciliación automática sistema vs broker
- Alerta si diferencias > 0.1%

**Archivos a crear:**
- `app/services/reconciliation/daily_reconciler.py`

---

#### R17. Sin Emociones
**Falta:**
- Cooldown tras 3 pérdidas consecutivas
- No cambiar reglas durante mercado abierto

**Archivos a crear:**
- `app/services/psychology/emotion_control_guard.py`

---

#### R18. Journal de Trades
**Falta:**
- Registro con emoción 1-5 y lecciones aprendidas

**Archivos a crear:**
- `app/services/journal/trading_journal.py`

---

#### R23. A/B Testing
**Falta:**
- Prueba en paper trading antes de producción
- Validación de mejora >10%

**Archivos a crear:**
- `app/services/testing/ab_tester.py`

---

#### R24. Diversificación de Estrategias
**Falta:**
- Múltiples estrategias no correlacionadas
- Rebalanceo trimestral

**Archivos a crear:**
- `app/services/portfolio/strategy_portfolio.py`

---

#### R29. Seguridad de API Keys
**Falta:**
- Rotación trimestral de keys
- Validación de permisos mínimos
- Nunca hardcodear credenciales

**Archivos a crear:**
- `app/services/security/api_key_manager.py`

---

## PLAN DE IMPLEMENTACIÓN PRIORITARIO

### Fase 1: CRÍTICO (implementar primero)
1. **R11** - Trailing Stop Dinámico
2. **R15** - Logging Completo
3. **R16** - Reconciliación Diaria
4. **R29** - Seguridad de API Keys

**Tiempo estimado:** 2-3 días

### Fase 2: IMPORTANTE (1-3 meses)
5. **R9** - Timing de Ejecución
6. **R12** - Take Profit Parcial
7. **R13** - Pyramiding
8. **R17** - Sin Emociones
9. **R18** - Journal de Trades

**Tiempo estimado:** 1-2 semanas

### Fase 3: DESEABLE (al escalar)
10. **R6** - Prevención de Overfitting
11. **R7** - Monte Carlo
12. **R23** - A/B Testing
13. **R24** - Diversificación de Estrategias

**Tiempo estimado:** 2-3 semanas

---

## ARCHIVOS EXISTENTES A MODIFICAR

### strategy_defaults.yaml
**Cambios necesarios:**
- Añadir max_risk_per_trade por fase
- Añadir min_rr_ratio por fase
- Añadir max_positions por fase
- Añadir trailing_stop_pct
- Añadir partial_take_profit_levels

### Nueva estructura propuesta:
```yaml
capital_phases:
  survival:  # 1k-10k
    max_risk_per_trade: 0.01
    max_positions: 2
    min_rr_ratio: 2.5
    trailing_stop_pct: 0.015
  growth:  # 10k-50k
    max_risk_per_trade: 0.015
    max_positions: 3
    min_rr_ratio: 2.2
  optimization:  # 50k-500k
    max_risk_per_trade: 0.02
    max_positions: 5
    min_rr_ratio: 2.0

position_management:
  trailing_stop:
    enabled: true
    trigger_2r: "move_to_breakeven"
    trigger_3r: "trailing_50pct_profit"
    trailing_pct: 0.015

  partial_take_profit:
    enabled: true
    levels:
      - r_multiple: 2.0
        close_pct: 0.50
        action: "move_to_breakeven"
      - r_multiple: 3.0
        close_pct: 0.25
        action: "trailing_stop"
      - r_multiple: 5.0
        close_pct: 0.25
        action: "none"

pyramiding:
  enabled: true
  max_additions: 2
  first_addition_pct: 0.50
  second_addition_pct: 0.25
  only_add_to_winners: true
```

---

## MÉTRICAS DE ÉXITO

### Objetivos por Fase

| Métrica | Fase 1 (1k-10k) | Fase 2 (10k-50k) | Fase 3 (50k-500k) |
|---------|-----------------|-------------------|-------------------|
| Trades/mes | 10-20 | 20-40 | 40-100 |
| Win Rate | >45% | >50% | >55% |
| R:R Prom | >2.5 | >2.2 | >2.0 |
| Max DD | <20% | <15% | <12% |
| Sharpe | >1.0 | >1.2 | >1.5 |

---

## CONCLUSIÓN

**Estado actual:**
- 24% de reglas completamente implementadas
- 24% parcialmente implementadas
- 52% no implementadas

**Prioridad:**
1. Completar reglas críticas de gestión de posiciones (R11-R13)
2. Implementar logging y reconciliación (R15-R16)
3. Añadir validaciones de psicología (R17-R18)
4. Mejorar backtesting con validaciones robustas (R6-R7)

**Próximos pasos:**
1. Actualizar `strategy_defaults.yaml` con nuevos parámetros
2. Crear `app/services/position_management/` con:
   - `trailing_stop_manager.py`
   - `partial_take_profit.py`
   - `pyramiding_manager.py`
3. Crear `app/services/logging/trading_decision_logger.py`
4. Crear `app/services/reconciliation/daily_reconciler.py`
