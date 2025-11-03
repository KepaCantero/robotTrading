# 🎯 Dashboard Avanzado - Guía de Uso

## 🚀 Inicio Rápido

Para ejecutar el nuevo dashboard visual:

```bash
python run_dashboard.py --advanced
```

O directamente:

```bash
streamlit run app/dashboard/advanced_dashboard.py
```

## ✨ Características Principales

### 1. **Diseño Visual Atractivo**

- 🎨 Cards de métricas con colores dinámicos (Verde/Amarillo/Naranja/Rojo)
- 📊 Gráficos interactivos con Plotly
- 🎯 Layout profesional con tabs y columnas
- 💫 Animaciones y transiciones suaves

### 2. **Indicadores de Color Inteligentes**

Los indicadores cambian de color según los umbrales configurados:

- 🟢 **Verde (Excellent)**: Métricas excelentes (por encima de "good")
- 🟡 **Amarillo (Good)**: Métricas buenas (entre "warn" y "good")
- 🟠 **Naranja (Warning)**: Métricas aceptables (entre "bad" y "warn")
- 🔴 **Rojo (Bad)**: Métricas pobres (por debajo de "bad")

**Métricas con indicadores:**

- Sharpe Ratio
- Return %
- Win Rate %
- Max Drawdown %

### 3. **Selector Visual de Tests**

En el sidebar puedes seleccionar qué tests ejecutar:

- ✅ Baseline
- ✅ Learning Engines
- ✅ Multi-Strategy
- ✅ Monte Carlo
- ✅ Grid Search
- ✅ Ablation Study
- ✅ Walk Forward
- ✅ Out of Sample
- ✅ Regime Test
- ✅ Transformer Optimization

### 4. **Configuración de Condiciones**

Fácil configuración de parámetros de ejecución:

- **Symbol**: Símbolo a analizar
- **Start/End Date**: Rango de fechas
- **Initial Capital**: Capital inicial
- **Advanced Settings**:
  - Paralelización
  - Meta Analysis
  - Incremental Learning

### 5. **Configuración de Umbrales de Color**

Puedes ajustar los umbrales que determinan los colores:

- **Sharpe Ratio**: bad, warn, good
- **Max Drawdown**: bad, warn, good
- **Win Rate**: bad, warn, good
- **Return %**: bad, warn, good

### 6. **Vistas Organizadas en Tabs**

#### 📊 **Dashboard Tab**

- KPIs principales con indicadores de color
- Top 5 performers
- Distribución de rendimiento
- Vista general rápida

#### 📈 **Individual Results Tab**

- Detalles de cada test individual
- Métricas expandibles
- Gráficos de comparación por test
- Filtros por tipo de test

#### 🔍 **Comparison Tab**

- Comparación visual entre múltiples tests
- Gráficos interactivos
- Tabla detallada de comparación
- Selección múltiple de tests

#### 📁 **Load Results Tab**

- Cargar resultados existentes
- Navegador de archivos
- Visualización de resultados guardados

## 🎨 Ejemplos de Uso

### Ejemplo 1: Ejecutar Solo Multi-Strategy

1. Abre el dashboard: `python run_dashboard.py --advanced`
2. En el sidebar, marca solo "✅ Multi-Strategy"
3. Configura símbolo y fechas
4. Click en "🚀 EXECUTE SELECTED TESTS"
5. Ve a la pestaña "Dashboard" para ver resultados

### Ejemplo 2: Comparar Baseline vs Learning Engines

1. Ejecuta ambos tests (marca ambos checkboxes)
2. Espera a que terminen
3. Ve a la pestaña "🔍 Comparison"
4. Selecciona ambos tests en el multiselect
5. Compara métricas visualmente

### Ejemplo 3: Ajustar Umbrales de Color

1. En el sidebar, expande "🎨 Color Thresholds"
2. Ajusta los valores de "Bad", "Warn", "Good"
3. Los colores se actualizan automáticamente en todas las vistas

## 📊 Métricas Mostradas

### Métricas Principales (con colores)

- **Sharpe Ratio**: Rendimiento ajustado por riesgo
- **Return %**: Retorno total porcentual
- **Win Rate %**: Porcentaje de trades ganadores
- **Max Drawdown %**: Máxima caída del capital

### Métricas Adicionales

- Total PnL
- Total Trades
- Avg Trade PnL
- Sortino Ratio
- Calmar Ratio
- Profit Factor

## 🎯 Mejores Prácticas

1. **Empieza con Dashboard Tab**: Obtén una vista general rápida
2. **Usa Filtros**: Filtra por tipo de test para análisis específicos
3. **Compara Top Performers**: Ve siempre a "Individual Results" para detalles
4. **Ajusta Umbrales**: Personaliza los umbrales según tus expectativas
5. **Guarda Configuraciones**: Los parámetros se mantienen durante la sesión

## 🚨 Solución de Problemas

### El dashboard no muestra colores

- Verifica que los umbrales estén configurados correctamente
- Asegúrate de que los datos tengan las columnas esperadas

### No se pueden ejecutar tests desde el dashboard

- Actualmente la ejecución requiere el comando línea:
  ```bash
  python scripts/run_comprehensive_backtest.py <test_name>
  ```
- El botón de ejecución muestra un mensaje informativo

### Los resultados no se cargan

- Verifica que la ruta en "Load Results" sea correcta
- Asegúrate de que existan archivos CSV/JSON en el directorio
- Revisa los logs en la terminal para errores

## 🔄 Próximas Mejoras

- [ ] Ejecución de tests directamente desde el dashboard
- [ ] Guardado de configuraciones personalizadas
- [ ] Exportación de reportes PDF/HTML
- [ ] Notificaciones cuando los tests terminen
- [ ] Integración con Meta-Analyzer en tiempo real
- [ ] Más tipos de gráficos (equity curves, drawdown charts)

## 📝 Notas

- El dashboard es completamente interactivo y se actualiza en tiempo real
- Los datos se cargan automáticamente si existen resultados previos
- Los colores se basan en los umbrales configurados en el sidebar
- Todas las vistas son responsive y se adaptan al tamaño de pantalla
