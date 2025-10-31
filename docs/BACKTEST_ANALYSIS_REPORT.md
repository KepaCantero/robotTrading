# Análisis de Resultados del Comprehensive Backtest

## 📊 Resumen Ejecutivo

**Fecha:** 2025-10-31  
**Símbolo:** SNOW  
**Periodo:** 2023-01-01 a 2024-01-01 (1 año)  
**Capital Inicial:** $100,000.00  
**Total de Backtests:** 232

## ⚠️ PROBLEMAS DETECTADOS

### 1. **Win Rate > 100%** (CRÍTICO)

- **Valores observados:** 2578.95%, 3450.70%, etc.
- **Causa probable:** Error en cálculo o extracción de win_rate
- **Impacto:** Métricas no confiables

### 2. **Return % Contradictorio con PnL**

- **Ejemplo:** Return: 366.24% pero PnL: -$14,292.68
- **Causa probable:** `total_return` se multiplica por 100 dos veces
- **Impacto:** Métricas de retorno incorrectas

### 3. **Sharpe Ratio Negativo o Casi Cero**

- Todos los resultados muestran Sharpe negativo o muy bajo
- Indica bajo rendimiento ajustado por riesgo
- Puede ser real si no hay trades o todos son perdedores

### 4. **Max Drawdown Negativo**

- El signo negativo puede ser correcto (drawdown es negativo por definición)
- Pero la presentación debería ser positiva con signo "-" explícito

## 🔍 ANÁLISIS DETALLADO

### Problema 1: Win Rate

El cálculo de `win_rate` en `engine.py` línea 1163:

```python
win_rate = (winning_count / total_trades * 100) if total_trades > 0 else Decimal("0")
```

Esto debería dar un valor entre 0-100. Sin embargo, en el reporte se muestra >100%.

**Posibles causas:**

1. El valor se está multiplicando dos veces
2. Hay un error en cómo se cuenta `winning_trades` vs `total_trades`
3. El `win_rate` almacenado ya está en formato decimal (0.2578) en lugar de porcentaje (25.78)

### Problema 2: Total Return

El cálculo de `total_return` en `engine.py` línea 267:

```python
total_return = (
    ((self.capital - self.config.initial_capital) / self.config.initial_capital) * Decimal("100")
    if self.config.initial_capital > 0
    else Decimal("0")
)
```

Luego en `comprehensive_backtest_runner.py` línea 173:

```python
'return_pct': float(result.total_return * 100),
```

**Problema:** Si `total_return` ya está en porcentaje (multiplicado por 100), entonces se está multiplicando por 100 OTRA VEZ.

**Ejemplo:**

- Si capital final = $85,707.32, inicial = $100,000
- Return real = (85,707.32 - 100,000) / 100,000 = -0.1429 = -14.29%
- `total_return` debería ser -14.29 (como porcentaje)
- Pero si se multiplica por 100 otra vez: -1429%

Esto explicaría los valores altos e inconsistentes.

### Problema 3: PnL vs Return

Si PnL = -$14,292.68 y capital inicial = $100,000:

- Return real = -14.29%
- Pero el reporte muestra 366.24%

Esto confirma que hay una doble multiplicación o error en el cálculo.

## 🔧 CORRECCIONES NECESARIAS

### Corrección 1: Verificar formato de total_return

`total_return` debe ser:

- **Opción A:** Decimal entre 0-100 (14.29 para 14.29%) - NO multiplicar por 100 en el reporte
- **Opción B:** Decimal entre 0-1 (0.1429 para 14.29%) - Multiplicar por 100 en el reporte

### Corrección 2: Verificar win_rate

`win_rate` debe estar entre 0-100. Si está almacenado como decimal (0.2578), debe multiplicarse por 100.

### Corrección 3: Max Drawdown

El drawdown debe mostrarse como valor positivo con signo "-" explícito:

- En lugar de: -2.84%
- Mostrar: -2.84% (ya está bien) o 2.84% (drawdown)

## 📈 INTERPRETACIÓN DE RESULTADOS

### Mejores Resultados (por Sharpe Ratio)

1. **Ablation - Without rsi_filter:**

   - Sharpe: -0.00 (mejor, aunque negativo)
   - PnL: -$14,292.68
   - **Conclusión:** Eliminar rsi_filter reduce pérdidas

2. **Monte Carlo - Simulation 89:**
   - Sharpe: -0.08
   - PnL: -$8,022.73
   - **Conclusión:** Esta simulación fue menos perjudicial

### Observaciones

- **Todos los resultados tienen PnL negativo:** La estrategia está perdiendo dinero en todos los backtests
- **Sharpe negativo:** Rendimiento ajustado por riesgo es malo
- **Win Rate inconsistente:** No se puede confiar en estos valores hasta corregir el error

## ✅ ACCIONES RECOMENDADAS

1. **Inmediato:**

   - Corregir cálculo de `total_return` (no multiplicar dos veces)
   - Verificar y corregir `win_rate`
   - Re-ejecutar backtests después de correcciones

2. **Análisis:**

   - Verificar por qué no se generan señales (0 signals en logs)
   - Revisar configuración de filtros (0 filtros activos en logs)
   - Analizar por qué todos los trades son perdedores

3. **Mejoras:**
   - Ajustar thresholds de filtros
   - Revisar lógica de señalización
   - Validar que los módulos se carguen correctamente

## 📝 NOTAS TÉCNICAS

- Los backtests se ejecutaron correctamente (232 tests completados)
- El sistema de reporte funciona pero tiene errores en formato de métricas
- Los logs muestran "0 filtros activos" - esto debe investigarse
