# Reglas Realistas de Algo Trading
## Para: 1000€ → 500k (Objetivo: vivir del trading)

**Extracto y filtrado de gemini_rules.txt**
**Fecha:** 2026-02-08

---

## METODOLOGÍA DE FILTRADO

Se han filtrado las 827 reglas originales según:
- **Aplicabilidad real** para capital retail (1k-500k)
- **Accionabilidad** (no conceptos abstractos)
- **Eliminación de redundancias**
- **Referencias comprobadas**

Se han conservado **~40 reglas** (5% del total).

---

## BLOQUE 1: GESTIÓN DE CAPITAL Y RIESGO

### R1. Gestión de posición (Kelly Criterion)
**ID original:** Múltiples referencias a Ralph Vince
**Servicio:** Risk

**Regla:**
- Calcular tamaño de posición usando Kelly Fraction = (Win% * AvgWin - Loss% * AvgLoss) / AvgWin
- Usar **Fraccional Kelly** (25-50% del Kelly óptimo) para reducir volatilidad
- Máximo **2% del capital** por trade individual
- **Stop loss** máximo del 3% del capital por trade

**Implementación:**
```python
kelly_fraction = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
position_size = capital * kelly_fraction * 0.5  # 50% de Kelly fraccional
```

**Referencias:**
- *The Mathematics of Money Management* - Ralph Vince
- *Fortune's Formula* - William Poundstone

---

### R2. Drawdown máximo
**ID original:** 557 (Hull - Risk Management)
**Servicio:** Risk

**Regla:**
- **Drawdown máximo del 15%** antes de detener trading
- Si se alcanza el 15% DD: revisar estrategia, reducir tamaño 50%
- Si se alcanza el 25% DD: parar completamente, hacer post-mortem

**Implementación:**
```python
if current_drawdown >= 0.15:
    reduce_positions(0.5)
    log_alert("Drawdown warning")
elif current_drawdown >= 0.25:
    stop_trading()
    log_critical("Trading halted")
```

---

### R3. Correlación y concentración
**ID original:** 631 (Danielsson - Financial Risk Forecasting)
**Servicio:** Risk

**Regla:**
- Máximo **3 posiciones abiertas** simultáneamente (capital < 10k)
- Correlación máxima entre activos: **0.7**
- No más del **20% del capital** en un solo activo
- No más del **40% del capital** en un mismo sector

---

### R4. Ratio Riesgo/Beneficio
**ID original:** 651 (Kissell - Algorithmic Trading)
**Servicio:** Execution

**Regla:**
- **Ratio mínimo R:R de 2:1** para abrir cualquier posición
- Para setups de alta probabilidad: aceptar 1.5:1
- Calcular R:R como: (Target Price - Entry) / (Entry - Stop Loss)

**Implementación:**
```python
rr_ratio = (target_price - entry_price) / (entry_price - stop_loss)
if rr_ratio < 2.0:
    reject_trade("R:R ratio below threshold")
```

---

## BLOQUE 2: BACKTESTING Y VALIDACIÓN

### R5. Walk-Forward Analysis
**ID original:** Referencias a López de Prado (múltiples reglas)
**Servicio:** Data

**Regla:**
- **Mínimo 6 meses** de datos para backtesting inicial
- Usar **Walk-Forward Analysis** con ventanas móviles:
  - Training: 70% de datos
  - Test: 30% de datos
  - Rolling window de mínimo 3 meses
- **IS vs OOS performance**: Máxima degradación del 30% en OOS

**Referencia:** *Advances in Financial Machine Learning* - Marcos López de Prado

---

### R6. Overfitting prevention
**ID original:** 653 (López de Prado)
**Servicio:** Data

**Regla:**
- Ratio parámetros/datos < 1:30
- Mínimo **50 trades** en backtesting para validación
- Usar **purged cross-validation** (eliminar datos entre train y test)
- Aplicar **embargo temporal** (eliminar t±N días alrededor de cada sample)

---

### R7. Monte Carlo para riesgo
**ID original:** 613 (Glasserman - Monte Carlo Methods)
**Servicio:** Risk

**Regla:**
- Ejecutar **1000 simulaciones Monte Carlo** del backtest
- Percentil 5% como estimador de drawdown máximo esperado
- Si el resultado real está fuera del rango 5-95%: revisar modelo

---

## BLOQUE 3: EJECUCIÓN Y MICROESTRUCTURA

### R8. Spread Bid-Ask
**ID original:** 636 (O'Hara - Market Microstructure)
**Servicio:** Execution

**Regla:**
- Para **spreads < 0.1%**: usar limit orders
- Para **spreads > 0.2%**: usar market orders solo en señales fuertes
- No operar si spread > 0.5% del precio (excepto crypto emergente)

---

### R9. Timing de ejecución
**ID original:** 672 (Donadio - Advanced Strategies)
**Servicio:** Execution

**Regla:**
- Evitar **primeros 15 min** y últimos 15 min del mercado (alta volatilidad)
- No operar durante **anuncios macro** (FED, CPI, NFP)
- Horas óptimas: 10:00-15:00 hora local del mercado

---

### R10. Slippage máximo
**ID original:** 636 (O'Hara)
**Servicio:** Execution

**Regla:**
- Slippage máximo aceptable: **0.1%** del precio esperado
- Si slippage > 0.2%: cancelar orden y reevaluar
- Registrar slippage real vs esperado en cada trade

---

## BLOQUE 4: GESTIÓN DE POSICIONES

### R11. Trailing Stop
**ID original:** 618 (Chan - Algorithmic Trading)
**Servicio:** Execution

**Regla:**
- Implementar trailing stop del **1.5%** desde el máximo del trade
- Cuando beneficio > 2R: mover stop a break-even
- Cuando beneficio > 3R: trailing stop al 50% del beneficio

**Implementación:**
```python
if unrealized_pnl > 2 * risk_amount:
    stop_loss = entry_price  # Break-even
elif unrealized_pnl > 3 * risk_amount:
    stop_loss = current_price - (unrealized_pnl * 0.5)
```

---

### R12. Take Profit parcial
**ID original:** 654 (Schwager - Market Wizards)
**Servicio:** Execution

**Regla:**
- Al alcanzar +2R: cerrar **50%** de posición, mover resto a break-even
- Al alcanzar +3R: cerrar otro 25%
- Dejar 25% correr con trailing stop

---

### R13. Pyramiding (adicionar posiciones)
**ID original:** 651 (Kissell)
**Servicio:** Execution

**Regla:**
- Solo agregar a ganadores (nunca promediar pérdidas)
- Segunda entrada: 50% del tamaño inicial
- Tercera entrada: 25% del tamaño inicial
- Máximo 3 entradas por dirección

---

## BLOQUE 5: DATA E INFRAESTRUCTURA

### R14. Calidad de datos
**ID original:** 732 (Ilyas - Data Cleaning)
**Servicio:** Data

**Regla:**
- Validar datos: missing values, outliers, duplicados
- Para missing: usar forward fill (máximo 3 gaps consecutivos)
- Para outliers (>3 desviaciones estándar): marcar para revisión manual
- Guardar **todos los raw data** (nunca sobreescribir)

---

### R15. Logs completos
**ID original:** 640 (Compliance - audit trails)
**Servicio:** Data

**Regla:**
- Registrar **cada decisión** del sistema con timestamp
- Campos requeridos: señal, tamaño, precio, razón, P&L
- Logs inmutables (append-only)
- Backup diario de logs

---

### R16. Reconciliación diaria
**ID original:** 750 (Data monitoring)
**Servicio:** Data

**Regla:**
- Al cierre de mercado: reconciliar posición del sistema vs broker
- Diferencias > 0.1%: alerta inmediata
- Generar reporte P&L diario
- Verificar: trades abiertos, pendientes, cash disponible

---

## BLOQUE 6: PSICOLOGÍA Y DISCIPLINA

### R17. Sin emociones
**ID original:** 676 (Emotion AI - evitar decisiones emocionales)
**Servicio:** Compliance (self)

**Regla:**
- **Nunca** cambiar reglas durante mercado abierto
- **Nunca** hacer revenge trading después de pérdidas
- Periodo de cooldown: 1 hora sin trading tras 3 pérdidas consecutivas
- Revisar decisiones solo fuera de horario de mercado

---

### R18. Journal de trades
**ID original:** 608 (Harris - post-execution analysis)
**Servicio:** Execution

**Regla:**
- Registrar: razón de entrada, salida, emociones (1-5), lecciones
- Revisar semanalmente: errores recurrentes, setups ganadores
- Categorizar trades: ganador planificado, ganador suerte, perdedor error, perdedor planificado

---

## BLOQUE 7: ANÁLISIS TÉCNICO Y SEÑALES

### R19. Tendencia vs Rango
**ID original:** 663 (Peters - Fractal Market Analysis)
**Servicio:** Execution

**Regla:**
- Identificar régimen del mercado (ADX > 25 = tendencia)
- En tendencia: usar seguimientos de tendencia (breakouts, moving averages)
- En rango: usar mean reversion (RSI, bandas Bollinger)
- No operar cuando ADX < 15 (sin dirección clara)

---

### R20. Confirmación múltiple
**ID original:** 618 (Chan)
**Servicio:** Execution

**Regla:**
- Mínimo **2 confirmaciones** antes de entrada:
  1. Señal primaria (setup)
  2. Confirmación de volumen
  3. Confirmación de mercado general (índice)
- Si confirmaciones < 2: reducir tamaño 50%

---

### R21. Volumen como filtro
**ID original:** 618 (Chan)
**Servicio:** Execution

**Regla:**
- Volumen mínimo: media de 20 períodos
- Breakouts sin volumen: considerar falso
- Divergencias precio-volumen: señal de alerta

---

## BLOQUE 8: ADAPTACIÓN Y MEJORA

### R22. Revisión mensual
**ID original:** 648 (Chincarini - performance monitoring)
**Servicio:** Execution

**Regla:**
- Análisis mensual: Sharpe ratio, Sortino, max DD, win rate
- Comparar vs benchmarks (SPY, BTC según activo)
- Si Sharpe < 1 o Sortino < 1.5: revisar estrategia
- Documentar cambios y rationale

---

### R23. A/B testing
**ID original:** 627 (Jansen - Machine Learning)
**Servicio:** Execution

**Regla:**
- Antes de cambiar parámetros: probar en paper trading 2 semanas
- Mínimo 20 trades en paper para validar
- Solo implementar si mejora >10% en métricas clave

---

### R24. Diversificación de estrategias
**ID original:** 642 (Chan - Quantitative Trading)
**Servicio:** Risk

**Regla:**
- Mínimo **2 estrategias no correlacionadas** (capital > 10k)
- Asignación: 60-40 o 50-50 según performance
- Rebalanceo trimestral de estrategias

---

## BLOQUE 9: ESCALADO (Fases de Capital)

### R25. Fase 1: 1k-10k (Supervivencia)
**ID original:** Práctica de traders profesionales
**Servicio:** Risk

**Regla:**
- Objetivo: **sobrevivir y aprender**, no enriquecer
- 1% máximo por trade (conservador)
- Máximo 2 posiciones simultáneas
- Focus en 1-2 activos máximo
- Documentar TODO

---

### R26. Fase 2: 10k-50k (Crecimiento)
**ID original:** 651 (Kissell)
**Servicio:** Execution

**Regla:**
- Subir a 1.5-2% por trade
- Añadir segunda estrategia
- Expandir a 3-5 activos correlacionados
- Empezar optimización de parámetros

---

### R27. Fase 3: 50k-500k (Optimización)
**ID original:** 655 (Hull - Risk Management)
**Servicio:** Risk

**Regla:**
- Portfolio de 3+ estrategias
- Diversificación por mercados (acciones, crypto, forex)
- Gestión de portafolio moderna (Markowitz, Black-Litterman)
- Considerar derivados para cobertura

---

## BLOQUE 10: COMPLIANCE (Retail Trader)

### R28. Registro de operaciones
**ID original:** 628 (Callioni - Compliance)
**Servicio:** Compliance

**Regla:**
- Mantener registro de todas las operaciones (Hacienda requirement)
- Guardar confirms de broker/exchange
- Registrar P&L mensual para impuestos
- Retener datos mínimo 5 años

---

### R29. Seguridad
**ID original:** 752 (Identity and Access Management)
**Servicio:** Compliance

**Regla:**
- 2FA obligatorio en todas las cuentas
- API keys con permisos mínimos (no withdrawal)
- Rotar keys cada 3 meses
- Never hardcodear credenciales en código

---

## RESUMEN EJECUTIVO

### Niveles de Prioridad

**CRÍTICO (implementar primero):**
- R1: Kelly + 2% max por trade
- R2: Drawdown 15% stop
- R4: R:R 2:1 mínimo
- R15: Logs completos
- R16: Reconciliación diaria

**IMPORTANTE (implementar en 1-3 meses):**
- R5: Walk-forward analysis
- R8: Gestión de spread
- R11: Trailing stop
- R14: Calidad de datos

**DESEABLE (implementar al escalar):**
- R12: Take profit parcial
- R24: Diversificación de estrategias
- R27: Gestión de portafolio

### Métricas Objetivo

| Fase | Capital | Trades/mes | Win Rate | R:R Prom | Max DD |
|------|---------|------------|----------|----------|--------|
| 1    | 1k-10k  | 10-20      | >45%     | >2.5     | <20%   |
| 2    | 10k-50k | 20-40      | >50%     | >2.2     | <15%   |
| 3    | 50k-500k| 40-100     | >55%     | >2.0     | <12%   |

---

## REFERENCIAS PRINCIPALES

1. **López de Prado, Marcos** - *Advances in Financial Machine Learning*
2. **Chan, Ernie** - *Algorithmic Trading: Winning Strategies and Their Rationale*
3. **Vince, Ralph** - *The Mathematics of Money Management*
4. **O'Hara, Maureen** - *Market Microstructure Theory*
5. **Hull, John** - *Risk Management and Financial Institutions*
6. **Kissell, Robert** - *The Science of Algorithmic Trading and Portfolio Management*
7. **Cartea, Álvaro** - *Algorithmic and High-Frequency Trading*
8. **Jansen, Stefan** - *Machine Learning for Algorithmic Trading*

---

## NOTA FINAL

Este documento extrae solo lo **realista y aplicable** para un trader retail.
Las reglas originales de gemini_rules.txt contenían mucho contenido sobre:
- Dark pools, HFT institucional, compliance bancario
- Infraestructura de baja latencia (colocation)
- Regulación MiFID/SEC para instituciones

Estos temas **NO aplican** a tu caso de 1000€ → 500k y han sido eliminados.

**El foco está en:** sobrevivir, aprender, y escalar gradualmente.
