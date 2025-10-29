# ✅ Integración de Yahoo Finance v8 API

## Estado Actual

El sistema ahora usa **Yahoo Finance v8 API directamente** como método principal para descargar datos. Esto evita los rate limits de `yfinance` y `yahoo_fin`.

## Métodos de Descarga (En Orden de Prioridad)

1. **CSV local** (`data/historical/*.csv`) - Más rápido
2. **Yahoo Finance v8 API directa** - Más confiable y evita rate limits
3. `yfinance` - Fallback secundario
4. `yahoo_fin` - Fallback final

## Script de Descarga: `download_yahoo_v8.py`

Nuevo script optimizado que usa la API v8 directamente:

```bash
python scripts/download_yahoo_v8.py AEP BAC KO
```

**Características**:

- ✅ Usa la API v8 oficial de Yahoo Finance
- ✅ Manejo robusto de rate limits (429) con exponential backoff
- ✅ Rotación de User-Agents para evitar detección
- ✅ Retry automático con hasta 5 intentos
- ✅ Delay configurable entre descargas (default: 6 segundos)

## Integración Automática en `DataLoader`

El `DataLoader` ahora usa automáticamente la API v8 cuando:

1. No hay CSV local disponible
2. Necesita descargar datos en tiempo real para el backtest

**Código**: `app/backtesting/data_loader.py::_load_from_yahoo_v8_api()`

## Ventajas de Yahoo Finance v8 API

- ✅ **API oficial** - Menos bloqueos que librerías no oficiales
- ✅ **Más estable** - Endpoint mantenido por Yahoo
- ✅ **Mejor estructura** - JSON limpio y bien formateado
- ✅ **Sin dependencias extra** - Solo requiere `requests`

## Uso

### Descargar Un Símbolo

```bash
python scripts/download_yahoo_v8.py AAPL
```

### Descargar Múltiples Símbolos

```bash
python scripts/download_yahoo_v8.py AEP BAC KO JPM
```

### En el Backtest

El sistema automáticamente usa la API v8 si no hay CSV local:

```python
from app.backtesting.data_loader import DataLoader

loader = DataLoader()
quotes = loader.load_historical_data('AEP', start_date, end_date)
# Automáticamente usa Yahoo Finance v8 API si no hay CSV
```

## Manejo de Rate Limits

Si recibes HTTP 429 (Too Many Requests):

1. **Espera 10-15 minutos** antes de reintentar
2. **Reduce el número de símbolos** por lote
3. **Aumenta el delay** en el script:
   ```python
   downloader = YahooFinanceV8Downloader(delay=10.0)  # 10 segundos entre descargas
   ```

## Comparación con Otros Métodos

| Método           | Ventajas                         | Desventajas                              |
| ---------------- | -------------------------------- | ---------------------------------------- |
| **Yahoo v8 API** | ✅ Más confiable, menos bloqueos | ⚠️ Requiere manejo manual de rate limits |
| `yfinance`       | ✅ API simple                    | ❌ Rate limits muy estrictos             |
| `yahoo_fin`      | ✅ Alternativa a yfinance        | ❌ También bloqueado frecuentemente      |
| **CSV local**    | ✅ Sin rate limits, muy rápido   | ⚠️ Requiere descarga previa              |

## Recomendación

**Usa la combinación**:

1. Descarga inicial con `download_yahoo_v8.py` para todos los símbolos del portfolio
2. Guarda en CSV local (`data/historical/`)
3. El backtest usa CSV automáticamente (sin rate limits)
4. Actualiza periódicamente (semanales/mensuales) con el script

---

_Última actualización: 2025-10-29_
