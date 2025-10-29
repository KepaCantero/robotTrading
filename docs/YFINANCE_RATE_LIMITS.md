# ⚠️ YFinance Rate Limits - Soluciones

## 🔴 Problema Actual

YFinance tiene rate limits muy estrictos (típicamente ~5 requests/minuto) que están bloqueando todas las descargas.

## ✅ Soluciones Alternativas

### Opción 1: Usar Datos Existentes (Recomendado Inmediato)

Ya tienes estos símbolos descargados:

- ✅ AAPL, AMZN, GOOGL, META, MSFT, NVDA, TSLA (Technology/Growth)
- ✅ XOM, CVX (Energy - algunos)

**Solución**: Ajustar `portfolio.yaml` temporalmente para usar solo símbolos disponibles:

```yaml
strategy_allocations:
  momentum:
    sectors:
      - technology # ✅ AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA disponibles
      - growth # ✅ TSLA, AMZN, META disponibles
      # - energy     # ❌ Comentar temporalmente

  mean_reversion:
    sectors:
      # Temporalmente usar technology hasta descargar utilities
      - technology # Usar AAPL temporalmente para testing
      # - utilities     # ❌ Comentar hasta descargar
      # - consumer_staples
      # - reits

  pairs_trading:
    sectors:
      - technology # ✅ AAPL, MSFT disponibles (par completo)
```

### Opción 2: Esperar y Descargar en Horas (Muy Lento)

```bash
# Esperar 15-30 minutos entre cada símbolo
python scripts/download_portfolio_data.py --symbols AEP --delay 1800  # 30 min delay
```

### Opción 3: Usar Alpha Vantage API (Alternativa)

1. Obtener API key gratis: https://www.alphavantage.co/support/#api-key
2. Modificar `DataLoader` para usar Alpha Vantage
3. 5 requests/minuto gratis, 500/día

### Opción 4: Descargar Manualmente desde Yahoo Finance

1. Ir a https://finance.yahoo.com/quote/SYMBOL/history
2. Seleccionar período
3. Descargar CSV
4. Guardar como `data/historical/SYMBOL.csv`

### Opción 5: Trabajar con Portfolio Reducido

Crear un portfolio más pequeño solo con símbolos disponibles:

```yaml
# Portfolio mínimo funcional
strategy_allocations:
  momentum:
    sectors: [technology, growth] # ✅ Símbolos disponibles

  mean_reversion:
    sectors: [technology] # Temporal para testing

  pairs_trading:
    sectors: [technology] # AAPL+MSFT par completo ✅
```

## 🎯 Recomendación Inmediata

**Usa los datos que ya tienes** y ajusta el portfolio temporalmente:

1. Modificar `portfolio.yaml` para usar solo `technology` sector
2. Ejecutar backtest con los 7 símbolos disponibles
3. Una vez funcionando, descargar el resto gradualmente

---

_Última actualización: 2025-10-29_
