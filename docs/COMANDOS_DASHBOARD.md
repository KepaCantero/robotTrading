# Comandos para Ejecutar el Dashboard

## Comando Principal

Para ejecutar el dashboard de AlgoTrading:

```bash
python run_dashboard.py
```

O directamente con Streamlit:

```bash
streamlit run app/dashboard/main.py
```

## Requisitos Previos

### 1. Instalar Streamlit (si no está instalado)

```bash
pip install streamlit
```

O instalar todas las dependencias:

```bash
pip install -r requirements.txt
```

### 2. Verificar que Streamlit está disponible

```bash
streamlit --version
```

## Opciones de Ejecución

### Ejecutar con puerto personalizado

```bash
streamlit run app/dashboard/main.py --server.port 8502
```

### Ejecutar en modo headless (sin abrir navegador automáticamente)

```bash
streamlit run app/dashboard/main.py --server.headless true
```

### Ejecutar con configuración personalizada

```bash
streamlit run app/dashboard/main.py \
  --server.port 8501 \
  --server.headless false \
  --browser.gatherUsageStats false
```

## Acceso al Dashboard

Una vez ejecutado, el dashboard estará disponible en:

- **URL Local:** http://localhost:8501
- **URL Red:** http://[tu-ip]:8501

El navegador se abrirá automáticamente (a menos que uses `--server.headless true`).

## Detener el Dashboard

Presiona `Ctrl+C` en la terminal donde se está ejecutando el dashboard.

## Características del Dashboard

El dashboard incluye:

1. **Vista Principal** (`app/dashboard/main.py`)

   - Resumen de backtests ejecutados
   - Métricas de rendimiento
   - Visualizaciones de equity curves

2. **Meta Dashboard** (`app/dashboard/meta_dashboard_page.py`)

   - Análisis metacognitivo
   - Correlaciones entre estrategias
   - Clustering de resultados
   - Performance Matrix
   - Alert Engine

3. **Carga de Datos**
   - Carga automática de resultados de comprehensive backtests
   - Soporte para múltiples formatos (CSV, JSON)

## Solución de Problemas

### Error: "streamlit: command not found"

```bash
# Instalar streamlit
pip install streamlit

# O usar python -m
python -m streamlit run app/dashboard/main.py
```

### Error: "Port 8501 already in use"

```bash
# Usar otro puerto
streamlit run app/dashboard/main.py --server.port 8502
```

### El dashboard no muestra datos

1. Verificar que hay resultados de backtest en `reports/comprehensive_backtest/`
2. Verificar los logs en la terminal para errores de carga
3. Asegurarse de que los archivos CSV/JSON tienen el formato correcto

## Comandos Rápidos

```bash
# Ejecutar dashboard
python run_dashboard.py

# Ejecutar dashboard en puerto específico
streamlit run app/dashboard/main.py --server.port 8502

# Ejecutar dashboard y ver logs detallados
streamlit run app/dashboard/main.py --logger.level=debug
```

## Notas

- El dashboard se actualiza automáticamente cuando cambias el código (modo desarrollo)
- Los datos se cargan desde `reports/comprehensive_backtest/` por defecto
- Para ver cambios en los datos, recarga la página del navegador
