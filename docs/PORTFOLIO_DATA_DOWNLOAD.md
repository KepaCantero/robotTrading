# 📥 Portfolio Data Download Guide

Script para descargar automáticamente datos históricos de todos los símbolos del portfolio configurado.

## 🚀 Uso Rápido

### Descargar todos los símbolos del portfolio

```bash
# Descargar 10 años de datos para todos los símbolos en portfolio.yaml
python scripts/download_portfolio_data.py

# Descargar solo 5 años
python scripts/download_portfolio_data.py --years 5

# Limitar a 10 símbolos (para evitar rate limits)
python scripts/download_portfolio_data.py --max-symbols 10
```

### Descargar símbolos específicos

```bash
# Descargar solo símbolos específicos
python scripts/download_portfolio_data.py --symbols AAPL MSFT GOOGL NEE PG KO

# Con delay más largo para evitar rate limits
python scripts/download_portfolio_data.py --symbols AAPL MSFT --delay 1.0
```

## ⚙️ Opciones

- `--years N`: Número de años de datos históricos (default: 10)
- `--output-dir PATH`: Directorio de salida (default: `data/historical`)
- `--delay SECONDS`: Delay entre descargas (default: 0.5s)
- `--max-symbols N`: Máximo número de símbolos (default: todos)
- `--symbols SYM1 SYM2 ...`: Símbolos específicos a descargar

## 📊 Ejemplo Completo

```bash
# Paso 1: Descargar todos los símbolos del portfolio (puede tardar)
python scripts/download_portfolio_data.py --years 10 --delay 1.0

# Si hay rate limits, esperar y retry solo los fallidos:
python scripts/download_portfolio_data.py --symbols AAPL MSFT GOOGL
```

## 🔄 Manejo de Rate Limits

El script incluye:
- **Retry automático**: 3 intentos con delays progresivos
- **Detección de rate limits**: Pausa automática si detecta límites
- **Skip de archivos existentes**: No descarga si el CSV ya existe

Si encuentras rate limits frecuentes:
1. Aumenta el delay: `--delay 2.0`
2. Descarga en lotes pequeños
3. Espera entre ejecuciones

## 📁 Formato de Archivos

Los CSVs se guardan en `data/historical/SYMBOL.csv` con formato:

```csv
date,timestamp,open,high,low,close,volume
2015-01-01,2015-01-01,100.0,102.5,99.5,101.2,1000000
...
```

## ✅ Ventajas de CSV Local

- ✅ **Sin rate limits**: No depende de yfinance en cada backtest
- ✅ **Más rápido**: Carga local instantánea
- ✅ **Offline**: Funciona sin conexión
- ✅ **Reproducibilidad**: Mismos datos en cada ejecución

## 🔧 Integración con Backtest

Una vez descargados los CSVs, el `PortfolioBuilder` los usará automáticamente:

1. Intenta cargar desde CSV primero
2. Si no existe, usa yfinance como fallback
3. Guarda en cache para futuros backtests

---

*Última actualización: 2025-10-29*

