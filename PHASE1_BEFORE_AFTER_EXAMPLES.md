# Phase 1: Fallback Removal - Before/After Examples

This document shows concrete examples of how fallbacks were removed from each file.

---

## 1. secure_serialization.py

### Before
```python
try:
    import msgpack
    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False
    msgpack = None

def _convert_for_msgpack(obj: Any) -> Any:
    # Handle numpy arrays
    if HAS_NUMPY and isinstance(obj, np.ndarray):
        return { '__type__': 'numpy.ndarray', ... }

    # Handle pandas DataFrames
    if HAS_PANDAS and isinstance(obj, pd.DataFrame):
        return { '__type__': 'pandas.DataFrame', ... }

def sign_and_dump(data: Any, secret_key: Union[str, bytes] = None) -> str:
    if not HAS_MSGPACK:
        raise ValueError("msgpack not installed")
    converted_data = _convert_for_msgpack(data)
    serialized = msgpack.packb(converted_data, use_bin_type=True)
```

### After
```python
# REQUIRED: No fallbacks - fail fast if dependencies are missing
import msgpack  # noqa: F401
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401

def _convert_for_msgpack(obj: Any) -> Any:
    # Handle numpy arrays (REQUIRED - no fallback)
    if isinstance(obj, np.ndarray):
        return { '__type__': 'numpy.ndarray', ... }

    # Handle pandas DataFrames (REQUIRED - no fallback)
    if isinstance(obj, pd.DataFrame):
        return { '__type__': 'pandas.DataFrame', ... }

def sign_and_dump(data: Any, secret_key: Union[str, bytes] = None) -> str:
    # Use msgpack (REQUIRED - no fallback)
    converted_data = _convert_for_msgpack(data)
    serialized = msgpack.packb(converted_data, use_bin_type=True)
```

---

## 2. tier_mapper.py

### Before
```python
try:
    from app.core.config.strategy_config_loader import get_strategy_config
    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False

@classmethod
def _load_thresholds_from_config(cls) -> None:
    if HAS_CONFIG_LOADER and cls.THRESHOLDS.get("loaded", False) is False:
        try:
            config = get_strategy_config()
            thresholds = config.get_tier_thresholds()
            # ... load thresholds
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.warning(f"Could not load tier thresholds from config: {e}")
```

### After
```python
# Import centralized configuration (REQUIRED - no fallbacks)
from app.core.config.strategy_config_loader import get_strategy_config  # noqa: F401

@classmethod
def _load_thresholds_from_config(cls) -> None:
    """Load thresholds from centralized config (REQUIRED)."""
    if cls.THRESHOLDS.get("loaded", False) is False:
        try:
            config = get_strategy_config()
            thresholds = config.get_tier_thresholds()
            # ... load thresholds
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Failed to load tier thresholds from config: {e}")
            raise  # Fail fast instead of warning
```

---

## 3. messaging.py

### Before
```python
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

try:
    import zmq
    HAS_ZMQ = True
except ImportError:
    HAS_ZMQ = False

def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
    self.use_zmq = use_zmq and HAS_ZMQ

    if HAS_REDIS:
        try:
            self.redis_client = redis.Redis(host=redis_host, port=redis_port)
            self.redis_client.ping()
            logger.info("✅ Redis connected for messaging")
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"⚠️ Redis connection failed: {e}, falling back to in-memory")
            self.redis_client = None
```

### After
```python
# REQUIRED: No fallbacks - fail fast if dependencies are missing
import redis  # noqa: F401
import zmq  # noqa: F401

def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
    self.use_zmq = use_zmq

    # REQUIRED: Redis connection (no fallbacks)
    try:
        self.redis_client = redis.Redis(host=redis_host, port=redis_port)
        self.redis_client.ping()
        logger.info("✅ Redis connected for messaging")
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"❌ Redis connection failed: {e}")
        raise  # Fail fast instead of falling back to in-memory
```

---

## 4. data_loader.py

### Before
```python
try:
    import yfinance as yf_module
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

try:
    from yahoo_fin.stock_info import get_data as yahoo_fin_get_data
    HAS_YAHOO_FIN = True
except ImportError:
    HAS_YAHOO_FIN = False

def _load_from_csv(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Quote]:
    file_path = self.base_path / f"{symbol}.csv"

    if not file_path.exists():
        logger.warning(f"CSV file not found: {file_path}. Trying yfinance...")
        return self._load_from_yfinance(symbol, start_date, end_date)

    try:
        df = pd.read_csv(file_path)
        # ... process data
    except (ValueError, KeyError) as e:
        logger.error(f"Error loading CSV for {symbol}: {e}")
        logger.warning("Falling back to yfinance...")
        return self._load_from_yfinance(symbol, start_date, end_date)

def _load_from_yfinance(self, symbol: str, ...) -> List[Quote]:
    # Try yfinance
    yf_module = _ensure_yfinance()
    if yf_module is not None:
        try:
            # ... use yfinance
            return quotes
        except Exception as e:
            logger.debug(f"yfinance failed for {symbol}: {e}, trying yahoo_fin...")

    # Fallback to yahoo_fin
    if HAS_YAHOO_FIN:
        try:
            # ... use yahoo_fin
            return quotes
        except Exception as e:
            logger.debug(f"yahoo_fin failed for {symbol}: {e}")

    logger.warning(f"No data available from Yahoo Finance for {symbol}")
    return []  # Empty list as fallback
```

### After
```python
# REQUIRED: Yahoo Finance libraries (no fallbacks)
import yfinance as yf  # noqa: F401
from yahoo_fin.stock_info import get_data as yahoo_fin_get_data  # noqa: F401

def _load_from_csv(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Quote]:
    file_path = self.base_path / f"{symbol}.csv"

    if not file_path.exists():
        logger.error(f"CSV file not found: {file_path}")
        raise FileNotFoundError(f"CSV file not found: {file_path}")  # Fail fast

    try:
        df = pd.read_csv(file_path)
        # ... process data
        return quotes
    except (ValueError, KeyError) as e:
        logger.error(f"Error loading CSV for {symbol}: {e}")
        raise  # Fail fast - no fallback to yfinance

def _load_from_yfinance(self, symbol: str, ...) -> List[Quote]:
    """Load data from Yahoo Finance using multiple methods (REQUIRED)."""
    # Try Yahoo Finance v8 API directly first (most reliable)
    quotes = self._load_from_yahoo_v8_api(symbol, start_date, end_date, timeframe)
    if quotes:
        return quotes

    # Try yfinance second
    try:
        ticker = yf.Ticker(symbol)
        # ... use yfinance
        return quotes
    except Exception as e:
        logger.debug(f"yfinance failed for {symbol}: {e}, trying yahoo_fin...")

    # Use yahoo_fin as last resort
    try:
        # ... use yahoo_fin
        return quotes
    except Exception as e:
        logger.debug(f"yahoo_fin failed for {symbol}: {e}")

    # All methods failed - raise error instead of returning empty list
    raise RuntimeError(f"No data available from Yahoo Finance for {symbol}")  # Fail fast
```

---

## 5. learning_storage.py

### Before
```python
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

def save_weights(self, engine_name: str, weights: Any, ...):
    if format == 'joblib':
        if not JOBLIB_AVAILABLE:
            raise ImportError("joblib no disponible para guardar .joblib")
        joblib.dump(data, file_path)
    elif format == 'msgpack':
        if not MSGPACK_AVAILABLE:
            raise ImportError("msgpack no disponible para guardar .msgpack")
        self._save_msgpack(file_path, data)

async def save_weights_async(self, ...):
    if format == 'joblib':
        if not JOBLIB_AVAILABLE:
            raise ImportError("joblib no disponible")
        # ... serialize

        # Escribir de forma asíncrona
        if AIOFILES_AVAILABLE:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(buffer.read())
        else:
            # Fallback síncrono
            with open(file_path, 'wb') as f:
                f.write(buffer.read())

def _detect_format(self, weights: Any) -> str:
    if TORCH_AVAILABLE and isinstance(weights, (torch.nn.Module, torch.Tensor)):
        return 'pt'
    elif JOBLIB_AVAILABLE:
        return 'joblib'
    elif MSGPACK_AVAILABLE:
        return 'msgpack'
    else:
        # Fallback - no hay formato seguro disponible
        raise ImportError("No hay formato de serialización seguro disponible")
```

### After
```python
# SECURITY: Using joblib and msgpack instead of pickle for secure serialization (REQUIRED)
import joblib  # noqa: F401
import msgpack  # noqa: F401
import aiofiles  # noqa: F401
import torch  # noqa: F401

def save_weights(self, engine_name: str, weights: Any, ...):
    if format == 'joblib':
        joblib.dump(data, file_path)  # REQUIRED - no availability check
    elif format == 'msgpack':
        self._save_msgpack(file_path, data)  # REQUIRED - no availability check

async def save_weights_async(self, ...):
    if format == 'joblib':
        # ... serialize

        # Escribir de forma asíncrona (REQUIRED - aiofiles must be available)
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(buffer.read())

def _detect_format(self, weights: Any) -> str:
    """Detectar formato óptimo y seguro según tipo de pesos (REQUIRED)."""
    if isinstance(weights, (torch.nn.Module, torch.Tensor)):
        return 'pt'
    else:
        return 'joblib'  # REQUIRED - joblib must be available
```

---

## 6. meta_analyzer.py

### Before
```python
try:
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn no disponible. Clustering deshabilitado.")

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("matplotlib no disponible. Visualizaciones deshabilitadas.")

def analyze_clusters(self):
    if not SKLEARN_AVAILABLE:
        logger.warning("Clustering no disponible - scikit-learn no instalado")
        return None

    kmeans = KMeans(n_clusters=self.n_clusters)
    # ... perform clustering

def plot_clusters(self):
    if not MATPLOTLIB_AVAILABLE:
        logger.warning("Visualización no disponible - matplotlib no instalado")
        return

    plt.figure(figsize=(10, 6))
    # ... create plot
```

### After
```python
# REQUIRED - no fallbacks
from sklearn.cluster import KMeans  # noqa: F401
import matplotlib.pyplot as plt  # noqa: F401
import seaborn as sns  # noqa: F401

def analyze_clusters(self):
    # Clustering always available - no availability check needed
    kmeans = KMeans(n_clusters=self.n_clusters)
    # ... perform clustering

def plot_clusters(self):
    # Visualization always available - no availability check needed
    plt.figure(figsize=(10, 6))
    # ... create plot
```

---

## 7. ohlcv_sources.py

### Before
```python
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp no disponible. Fuentes OHLCV asíncronas no funcionarán.")

class BinanceSource(BaseDataSource):
    async def connect(self) -> bool:
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp no disponible. BinanceSource no puede conectarse.")
            self.last_error = "aiohttp no disponible"
            return False  # Fallback - return False

        try:
            self.session = aiohttp.ClientSession()
            self.is_connected = True
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Error conectando a Binance: {e}")
            self.last_error = str(e)
            return False  # Fallback - return False

class AlpacaSource(BaseDataSource):
    async def connect(self) -> bool:
        if not self.api_key or not self.api_secret:
            logger.error("Alpaca API key y secret requeridos")
            self.last_error = "API credentials missing"
            return False  # Fallback - return False

        try:
            self.session = aiohttp.ClientSession(headers={...})
            self.is_connected = True
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Error conectando a Alpaca: {e}")
            self.last_error = str(e)
            return False  # Fallback - return False
```

### After
```python
# REQUIRED: No fallbacks - aiohttp is required for async HTTP requests
import aiohttp  # noqa: F401

class BinanceSource(BaseDataSource):
    async def connect(self) -> bool:
        try:
            self.session = aiohttp.ClientSession()
            self.is_connected = True
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Error conectando a Binance: {e}")
            self.last_error = str(e)
            raise  # Fail fast - don't return False

class AlpacaSource(BaseDataSource):
    async def connect(self) -> bool:
        if not self.api_key or not self.api_secret:
            logger.error("Alpaca API key y secret requeridos")
            self.last_error = "API credentials missing"
            raise ValueError("Alpaca API key y secret requeridos")  # Fail fast

        try:
            self.session = aiohttp.ClientSession(headers={...})
            self.is_connected = True
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Error conectando a Alpaca: {e}")
            self.last_error = str(e)
            raise  # Fail fast - don't return False
```

---

## 8. options_sources.py, sentiment_sources.py, fundamental_sources.py

### Before
```python
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

class OptionsVolatilitySource(BaseDataSource):
    async def connect(self) -> bool:
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp no disponible. OptionsSource no puede conectarse.")
            self.last_error = "aiohttp no disponible"
            return False  # Fallback

        try:
            self.session = aiohttp.ClientSession()
            self.is_connected = True
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Error conectando a Options Source: {e}")
            self.last_error = str(e)
            return False  # Fallback
```

### After
```python
# REQUIRED: No fallbacks - aiohttp is required for async HTTP requests
import aiohttp  # noqa: F401

class OptionsVolatilitySource(BaseDataSource):
    async def connect(self) -> bool:
        try:
            self.session = aiohttp.ClientSession()
            self.is_connected = True
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Error conectando a Options Source: {e}")
            self.last_error = str(e)
            raise  # Fail fast - don't return False
```

---

## 9. quantstats_integration.py

### Before
```python
# Try to import QuantStats, fall back gracefully if not available
try:
    pass  # Actual import was missing!
    QUANTSTATS_AVAILABLE = True
except ImportError:
    QUANTSTATS_AVAILABLE = False
    logger.warning("⚠️ QuantStats not available - using fallback metrics")

class QuantStatsIntegration:
    def __init__(self):
        self.available = QUANTSTATS_AVAILABLE

    def calculate_advanced_metrics(self, returns: pd.Series, ...) -> Dict[str, float]:
        if not self.available or len(returns) < 2:
            return self._fallback_metrics(returns, periods_per_year)  # Fallback

        try:
            # Calculate using QuantStats
            metrics["sharpe_ratio"] = ...
            metrics["sortino_ratio"] = ...
            # ... more metrics
        except (ValueError, TypeError) as e:
            logger.warning(f"Error calculating QuantStats metrics: {e}, using fallback")
            return self._fallback_metrics(returns, periods_per_year)  # Fallback

    def _fallback_metrics(self, returns: pd.Series, ...) -> Dict[str, float]:
        """Calculate basic metrics when QuantStats not available."""
        metrics = {}
        # ... 50+ lines of fallback metrics
        return metrics
```

### After
```python
# REQUIRED: No fallbacks - QuantStats is required for advanced metrics
try:
    import quantstats  # noqa: F401
    QUANTSTATS_AVAILABLE = True
except ImportError:
    QUANTSTATS_AVAILABLE = False
    raise ImportError(
        "QuantStats is required for advanced metrics. Install: pip install quantstats"
    )

class QuantStatsIntegration:
    def __init__(self):
        self.available = QUANTSTATS_AVAILABLE

    def calculate_advanced_metrics(self, returns: pd.Series, ...) -> Dict[str, float]:
        """Calculate advanced performance metrics using QuantStats (REQUIRED)."""
        if not isinstance(returns, pd.Series):
            raise ValueError(f"Cannot convert returns to Series")

        if len(returns) < 2:
            raise ValueError("Returns series must have at least 2 data points")

        try:
            # Calculate using QuantStats (REQUIRED - no fallback)
            metrics["sharpe_ratio"] = ...
            metrics["sortino_ratio"] = ...
            # ... more metrics
        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating QuantStats metrics: {e}")
            raise  # Fail fast - no fallback

    # _fallback_metrics() method removed entirely (50+ lines deleted)
```

---

## Summary of Changes

| Pattern | Before | After |
|---------|--------|-------|
| **Import check** | `try/except ImportError` with flag | Direct import (fail at load time) |
| **Feature check** | `if HAS_<LIBRARY>` | No check (lib required) |
| **Connection fail** | `return False` | `raise Exception` |
| **Missing config** | `logger.warning()` + default | `raise ValueError/ConfigError` |
| **Data unavailable** | `return []` | `raise RuntimeError` |
| **Fallback method** | Call alternate method | Raise exception |
| **Logging** | `logger.warning()` on fail | `logger.error()` + raise |

---

## Key Takeaways

1. **Explicit is better than implicit**: All dependencies are now explicit in imports
2. **Fail fast**: Errors occur at import/startup, not during execution
3. **No silent failures**: All errors are logged and raised
4. **Simpler code**: Removed ~280 lines of fallback code
5. **Easier testing**: No need to test fallback paths
6. **Better security**: No fallback to insecure methods (e.g., pickle)

---

**Result**: The codebase now follows the principle "100% implementation or nothing - no half measures"
