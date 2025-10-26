# Dashboard de Estrategias - Plan de Implementación

## 📊 Tareas Críticas - Dashboard Completo

### TAREA-1: ESTRUCTURA AVANZADA DEL DASHBOARD ✅ PARCIAL

**Estado**: Estructura básica creada
**Archivos Creados**:
- ✅ `app/dashboard/__init__.py`
- ✅ `app/dashboard/data_loader.py`
- ⏳ `app/dashboard/main.py` - Streamlit app principal
- ⏳ `app/dashboard/components/` - Componentes modulares

**Subtareas Restantes**:
- [ ] Crear main.py con tabs (Overview, Estrategias, Parámetros, Live, Insights)
- [ ] Implementar componentes básicos (metrics_panel, charts, tables, controls)
- [ ] Integrar Streamlit con st.session_state
- [ ] Añadir visualización con Plotly/Altair

### TAREA-2: GESTOR DE ESTRATEGIAS ⏳ PENDIENTE

**Archivo**: `app/dashboard/strategy_manager.py`
**Objetivo**: Detectar y gestionar estrategias automáticamente

**Implementación Requerida**:
```python
def list_strategies():
    # Escanear app/strategies/
    # Cargar metadata
    # Retornar lista de estrategias con estado
    pass
```

### TAREA-3: AJUSTE DE PARÁMETROS ⏳ PENDIENTE

**Archivo**: `app/dashboard/parameter_tuner.py`
**Objetivo**: Permitir ajustar parámetros sin editar código

**Funcionalidades**:
- [ ] Leer config desde YAML
- [ ] Crear sliders/interactivos en Streamlit
- [ ] Guardar cambios automáticamente
- [ ] Opción "Recalcular backtest"

### TAREA-4: VISUALIZACIÓN AVANZADA ⏳ PENDIENTE

**Archivos**: `app/dashboard/components/charts.py`, `metrics_panel.py`

**Gráficos Requeridos**:
- [ ] Equity curve
- [ ] Drawdown curve
- [ ] Heatmap de correlación
- [ ] Histograma de retornos
- [ ] KPIs panel

### TAREA-5: MONITOR EN TIEMPO REAL ⏳ PENDIENTE

**Archivo**: `app/dashboard/live_monitor.py`
**Objetivo**: Feed en vivo de paper trading

**Funcionalidades**:
- [ ] Conectar a logs de paper trading
- [ ] Mostrar últimas operaciones
- [ ] PnL intradía
- [ ] Posiciones abiertas
- [ ] Auto-refresh cada 15-30s

### TAREA-6: INSIGHTS AUTOMÁTICOS ⏳ PENDIENTE

**Objetivo**: Sugerir mejoras basadas en performance
**Funcionalidades**:
- [ ] Analizar histórico
- [ ] Detectar correlaciones
- [ ] Alertar sobre drawdowns altos
- [ ] Sugerir ajustes

### TAREA-7: VALIDACIÓN Y TESTS ⏳ PENDIENTE

**Objetivo**: Tests para cada módulo
**Tests Requeridos**:
- [ ] test_data_loader.py
- [ ] test_strategy_manager.py
- [ ] test_parameter_tuner.py
- [ ] test_charts.py

### TAREA-8: CONFIGURACIÓN ⏳ PENDIENTE

**Dependencias a Añadir**:
```python
streamlit
plotly
seaborn
altair
watchdog
rich
```

**Scripts**:
- [ ] `scripts/run_dashboard.sh`
- [ ] Comando `make dashboard` en Makefile

## 🎯 Estado Actual

**Progreso**: 1/8 tareas iniciadas
**Archivos Creados**: 2
**Archivos Pendientes**: 6+ componentes

## ⚠️ NOTA IMPORTANTE

Esta implementación requiere:
1. **Instalación de Streamlit** y dependencias de visualización
2. **Integración con datos existentes** (backtesting, paper trading)
3. **Múltiples módulos** de visualización y gestión
4. **Testing exhaustivo** de cada componente

**Estimación**: Tarea COMPLEJA que requiere varias horas de desarrollo

## 💡 Recomendación

Dado que esta es una tarea extensa y el usuario necesita ejecutar backtests AHORA, sugeriría:
1. Completar primero los componentes básicos del dashboard (main.py básico)
2. Implementar paso a paso, empezando por el Strategy Manager
3. Priorizar funcionalidad antes que complejidad visual

¿Procedo con la implementación completa o te muestro cómo ejecutar el backtest que ya tienes?

