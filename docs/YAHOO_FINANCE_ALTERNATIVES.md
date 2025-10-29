# 🔄 Alternativas a yfinance - Yahoo Finance

## Problema Actual

`yfinance` está siendo bloqueado por rate limits muy estrictos de Yahoo Finance.

## ✅ Solución: Usar `yahoo_fin` como Alternativa

### Instalación

```bash
pip install yahoo_fin
```

### Ventajas de `yahoo_fin`

- ✅ **Diferente implementación**: Usa métodos distintos que pueden evitar rate limits
- ✅ **Mismo resultado**: Misma data de Yahoo Finance
- ✅ **Fácil de usar**: API similar pero con diferentes llamadas internas
- ✅ **Ya integrado**: El sistema ahora lo usa automáticamente como fallback

### El Sistema Ahora Usa Automáticamente

1. **Primero intenta `yfinance`**
2. **Si falla, usa `yahoo_fin` automáticamente**
3. **Si ambos fallan, usa CSV local**

No necesitas cambiar nada - el sistema detecta automáticamente qué librerías están disponibles.

## 📥 Instalar Yahoo_fin

```bash
pip install yahoo_fin
```

También necesitas `requests_html` (opcional pero recomendado):

```bash
pip install requests_html
```

## 🔧 Uso Manual (si quieres probar)

```python
from yahoo_fin.stock_info import get_data

# Formato de fecha: mm/dd/yyyy
df = get_data("AAPL", start_date="01/01/2015", end_date="10/29/2025", interval="1d")
print(df.head())
```

## 🎯 Recomendación

1. **Instalar `yahoo_fin`**:
   ```bash
   pip install yahoo_fin requests_html
   ```

2. **Reintentar descarga**:
   ```bash
   # yahoo_fin se usará automáticamente como fallback
   python scripts/download_portfolio_data.py --symbols AEP BAC --delay 3.0
   ```

3. El sistema probará ambas librerías y usará la que funcione.

## 📚 Otras Alternativas (Futuro)

Si `yahoo_fin` también tiene problemas:

1. **Alpha Vantage** (500 requests/día gratis)
2. **IEX Cloud** (API oficial, más estable)
3. **Polygon.io** (Pago pero muy rápido)

---

*Última actualización: 2025-10-29*

