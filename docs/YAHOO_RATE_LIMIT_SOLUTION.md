# 🔴 Solución para Rate Limits de Yahoo Finance

## Situación Actual

Tanto `yfinance` como `yahoo_fin` están siendo bloqueados por rate limits estrictos de Yahoo Finance.

**Error**: "Rate limited" o "Expecting value: line 1 column 1"

## ✅ Solución Inmediata: Trabajar con Datos Disponibles

### Símbolos que Ya Tienes Descargados

Verifica con:

```bash
ls data/historical/*.csv
```

**Símbolos típicamente disponibles**:

- AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA (Technology)
- Otros que hayas descargado previamente

### Configurar Portfolio con Datos Disponibles

1. **Ver qué símbolos tienes**:

```bash
ls data/historical/*.csv | sed 's|data/historical/||g' | sed 's|.csv||g'
```

2. **Ajustar `config/portfolio.yaml`** para usar solo esos símbolos:

```yaml
strategy_allocations:
  momentum:
    sectors:
      - technology # ✅ Ya tienes: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA

  mean_reversion:
    sectors:
      - technology # ✅ Temporal - usa los mismos símbolos

  pairs_trading:
    sectors:
      - technology # ✅ AAPL + MSFT par completo disponible
```

3. **Ejecutar backtest** - funcionará con los CSVs locales sin rate limits.

## 🔄 Estrategias para Descargar Más Datos

### Opción 1: Esperar y Reintentar Más Tarde (Gratis)

Yahoo Finance resetea rate limits después de varias horas:

```bash
# Esperar 2-4 horas y luego:
python scripts/download_with_yahoo_fin.py AEP BAC KO
```

### Opción 2: Descargar Manualmente desde Yahoo Finance

1. Ir a: https://finance.yahoo.com/quote/SYMBOL/history
2. Seleccionar período
3. Click "Download" (botón debajo del gráfico)
4. Guardar como `data/historical/SYMBOL.csv`

### Opción 3: Usar Alpha Vantage (Alternativa Gratuita)

Alpha Vantage ofrece 500 requests/día gratis:

1. Obtener API key: https://www.alphavantage.co/support/#api-key
2. Usar su API en vez de Yahoo Finance
3. Más estable y sin rate limits tan estrictos

### Opción 4: Usar VPN o Cambiar IP

Si estás bloqueado por IP, cambiar tu IP puede ayudar.

## 🎯 Recomendación para Ahora

**Trabaja con los datos que tienes**:

1. El portfolio puede funcionar perfectamente con solo Technology sector
2. Momentum: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA ✅
3. Mean Reversion: Usar temporalmente technology ✅
4. Pairs Trading: AAPL + MSFT par completo ✅

**Una vez funcionando el sistema**, descarga más datos gradualmente durante varios días.

---

_Última actualización: 2025-10-29_
