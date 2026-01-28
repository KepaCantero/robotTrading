# Before/After Code Examples - Half-Implemented Features Fix
**Reference Guide for Implementation**

This document shows the exact code changes needed to fix each half-implemented feature.

---

## 1. NUMBA FALLBACK REMOVAL

### BEFORE (WRONG)
```python
# app/core/numba_accelerators.py

try:
    from numba import jit, njit, prange
    import numba

    NUMBA_AVAILABLE = True
    NUMBA_VERSION = numba.__version__
    logging.info(f"✅ Numba {NUMBA_VERSION} available - JIT compilation enabled")
except ImportError:
    # Fallback decorators if numba is not available
    NUMBA_AVAILABLE = False
    NUMBA_VERSION = None

    def jit(nopython=True, cache=True, parallel=False):
        """Fallback decorator that returns the function as-is."""
        def decorator(func):
            return func
        return decorator

    def njit(func=None, **kwargs):
        """Fallback decorator for njit."""
        if func is None:
            return lambda f: f
        return func

    def prange(iterable):
        """Fallback for prange - just use regular range."""
        return range(iterable)

    logging.warning("⚠️ Numba not available - using pure Python (install with: pip install numba)")
```

### AFTER (CORRECT)
```python
# app/core/numba_accelerators.py

try:
    from numba import jit, njit, prange
    import numba

    NUMBA_AVAILABLE = True
    NUMBA_VERSION = numba.__version__
    logger.info(f"✅ Numba {NUMBA_VERSION} available - JIT compilation enabled")
except ImportError:
    raise ImportError(
        "Numba is REQUIRED for performance. "
        "Without Numba, calculations will be 50-100x slower. "
        "Install with: pip install numba>=0.59.0,<1.0.0"
    )
```

---

## 2. EMAIL NOTIFICATION FALLBACK

### BEFORE (WRONG)
```python
# app/services/alerting_system/notification_channels.py

class EmailChannel(NotificationChannel):
    async def send(self, target: NotificationTarget, payload: NotificationPayload) -> bool:
        try:
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            import aiosmtplib
        except ImportError:
            logger.warning("aiosmtplib not installed. Run: pip install aiosmtplib")
            # Fallback: log the notification
            logger.info(
                f"[EMAIL SIMULATION] To: {target.endpoint}, "
                f"Subject: {payload.rule_name}, Message: {payload.message}"
            )
            return True  # Pretends success!
```

### AFTER (CORRECT)
```python
# app/services/alerting_system/notification_channels.py

class EmailChannel(NotificationChannel):
    async def send(self, target: NotificationTarget, payload: NotificationPayload) -> bool:
        try:
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            import aiosmtplib
        except ImportError:
            raise ImportError(
                "aiosmtplib is REQUIRED for email notifications. "
                "Install with: pip install aiosmtplib>=3.0.0"
            )

        # ... actual email sending implementation ...
```

**AND add to requirements.txt:**
```txt
aiosmtplib>=3.0.0  # REQUIRED: Async SMTP for email notifications
```

---

## 3. CRYPTO API SERVICE STUB

### BEFORE (WRONG)
```python
# app/services/crypto_data_service.py

def _fetch_price_from_api(self, pair: str) -> Optional[Decimal]:
    logger.debug(f"Attempting to fetch price from API for {pair}")
    # In a real implementation, this would:
    # 1. Connect to Binance/Coinbase/Kraken API
    # 2. Request current price
    # 3. Parse and return Decimal price
    raise NotImplementedError("API price fetching not yet implemented")

# But this is caught and returns hardcoded fallback prices!
def get_current_price(self, symbol: str) -> Decimal:
    try:
        price = asyncio.run(self.reconnection_manager.connect_with_backoff(
            lambda: self._fetch_price_from_api(pair)
        ))
    except NotImplementedError:
        # Fallback to hardcoded prices
        return self._get_fallback_price(symbol)  # FAKE PRICES!
```

### AFTER (Option A - IMPLEMENT)
```python
# app/services/crypto_data_service.py

def _fetch_price_from_api(self, pair: str) -> Decimal:
    """
    Fetch current price from exchange API.

    Args:
        pair: Crypto pair (e.g., "BTC/USD")

    Returns:
        Current price as Decimal

    Raises:
        ConnectionError: If API unavailable
    """
    import httpx

    symbol = self._pair_to_exchange_symbol(pair)

    async def _fetch():
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            )
            response.raise_for_status()
            data = response.json()
            return Decimal(str(data['price']))

    return asyncio.run(self.reconnection_manager.connect_with_backoff(_fetch))

def get_current_price(self, symbol: str) -> Decimal:
    """
    Get current price for crypto symbol.

    Args:
        symbol: Crypto symbol (e.g., "BTC")

    Returns:
        Current price in USD

    Raises:
        ConnectionError: If API unavailable
        ValueError: If invalid symbol
    """
    pair = f"{symbol}/USD"
    return self._fetch_price_from_api(pair)

# Remove _get_fallback_price() entirely
# Remove all hardcoded fallback prices
```

### AFTER (Option B - REMOVE)
```bash
# Delete the entire file
rm /app/services/crypto_data_service.py

# Remove all imports
grep -r "from app.services.crypto_data_service" app/ --delete
grep -r "CryptoDataService" app/ --delete

# Update documentation
# "Crypto trading is not currently supported"
```

---

## 4. MATPLOTLIB VISUALIZATION

### BEFORE (WRONG)
```python
# app/backtesting/labeling/triple_barrier.py

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    plt = None

def plot_triple_barrier(...) -> Optional["plt.Axes"]:
    if not HAS_MATPLOTLIB:
        import warnings
        warnings.warn("Matplotlib not available, skipping visualization", UserWarning)
        return None  # Silent failure

    # ... plotting code ...
```

### AFTER (CORRECT)
```python
# app/backtesting/labeling/triple_barrier.py

try:
    import matplotlib.pyplot as plt
except ImportError:
    raise ImportError(
        "matplotlib is REQUIRED for visualization. "
        "Install with: pip install matplotlib>=3.7.0"
    )

def plot_triple_barrier(...) -> "plt.Axes":
    """Plot triple barrier labeling visualization."""
    if ax is None:
        _, ax = plt.subplots(figsize=(12, 6))

    # ... plotting code (no HAS_MATPLOTLIB check) ...

    return ax
```

**AND add to requirements.txt:**
```txt
matplotlib>=3.7.0  # REQUIRED: Visualization and plotting
```

---

## 5. SCIPY FOR PAIRS TRADING

### BEFORE (WRONG)
```python
# app/strategies/pairs_trading.py

try:
    from scipy.stats import coint
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("scipy not available, cointegration tests will be limited")

# Then later...
if not SCIPY_AVAILABLE:
    # Use simplified (incorrect) cointegration test
    return self._simplified_cointegration_test(series1, series2)
```

### AFTER (CORRECT)
```python
# app/strategies/pairs_trading.py

try:
    from scipy.stats import coint
    from scipy import stats
except ImportError:
    raise ImportError(
        "scipy is REQUIRED for cointegration tests. "
        "Pairs trading cannot function without scipy. "
        "Install with: pip install scipy>=1.11.0,<2.0.0"
    )

# Always use scipy cointegration - no fallback
def test_cointegration(self, series1: pd.Series, series2: pd.Series) -> float:
    """Test cointegration using scipy."""
    score, pvalue, _ = coint(series1, series2)
    return pvalue
```

---

## 6. BACKTEST EXECUTOR

### BEFORE (WRONG)
```python
# app/backtesting/core/executor.py

class BacktestExecutor:
    """Backtest execution engine."""

    def execute(self, quotes: QuotesType, strategy: StrategyType, **kwargs) -> BacktestResult:
        """Execute backtest and return results."""
        raise NotImplementedError  # But this is a concrete class!

    def validate_inputs(self, quotes: QuotesType, strategy: StrategyType) -> None:
        """Validate inputs before execution."""
        if not quotes:
            raise ValueError("Quotes cannot be empty")
        # ... validation logic ...
```

### AFTER (CORRECT - Option A: Abstract)
```python
# app/backtesting/core/executor.py

from abc import ABC, abstractmethod

class BacktestExecutor(ABC):
    """
    Abstract base class for backtest execution.

    Subclasses MUST implement the execute() method.
    """

    @abstractmethod
    def execute(self, quotes: QuotesType, strategy: StrategyType, **kwargs) -> BacktestResult:
        """
        Execute backtest and return results.

        Note:
            This method MUST be implemented by subclasses.

        Raises:
            NotImplementedError: Always - subclass must implement
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement execute() method"
        )

    def validate_inputs(self, quotes: QuotesType, strategy: StrategyType) -> None:
        """Validate inputs before execution."""
        if not quotes:
            raise ValueError("Quotes cannot be empty")
        # ... validation logic ...
```

### AFTER (CORRECT - Option B: Implement)
```python
# app/backtesting/core/executor.py

class BacktestExecutor:
    """Backtest execution engine."""

    def execute(self, quotes: QuotesType, strategy: StrategyType, **kwargs) -> BacktestResult:
        """
        Execute backtest and return results.

        Args:
            quotes: Market data quotes
            strategy: Trading strategy
            **kwargs: Additional parameters

        Returns:
            BacktestResult with performance metrics
        """
        # Validate inputs
        self.validate_inputs(quotes, strategy)

        # Initialize results
        results = BacktestResult(
            initial_capital=self.config.initial_capital,
            start_date=quotes[0].timestamp,
            end_date=quotes[-1].timestamp,
        )

        # Execute backtest logic
        for quote in quotes:
            # Generate signal
            signal = strategy.generate_signal(quote)

            # Execute trade
            if signal:
                trade = self._execute_trade(signal, quote)
                results.add_trade(trade)

        # Calculate metrics
        results.calculate_metrics()

        return results
```

---

## 7. META-LABELING FUNCTION

### BEFORE (WRONG)
```python
# app/backtesting/labeling/triple_barrier.py

def meta_labeling(
    primary_labels: np.ndarray,
    features: np.ndarray,
    actual_returns: np.ndarray,
) -> np.ndarray:
    """
    Generate meta-labels for position sizing.

    THIS IS A SIMPLIFIED VERSION - FULL IMPLEMENTATION NEEDED:
    - Should train a classifier on features vs actual returns
    - Should use cross-validation to prevent overfitting
    - Should output probability scores, not binary
    """
    meta_labels = np.zeros(len(primary_labels))

    for i, (label, ret) in enumerate(zip(primary_labels, actual_returns)):
        # Simplified: just check if signal was correct
        if (label == 1 and ret > 0) or (label == -1 and ret < 0):
            meta_labels[i] = 1
        else:
            meta_labels[i] = 0

    return meta_labels  # Too simple!
```

### AFTER (Option A - IMPLEMENT FULL)
```python
# app/backtesting/labeling/triple_barrier.py

from sklearn.ensemble import RandomForestClassifier
from app.backtesting.validation.purged_kfold import PurgedKFold
from sklearn.calibration import CalibratedClassifierCV

def meta_labeling(
    primary_labels: np.ndarray,
    features: np.ndarray,
    actual_returns: np.ndarray,
    model_type: str = "random_forest",
    cv_folds: int = 5,
    embargo_pct: float = 0.01,
    calibrate: bool = True,
) -> np.ndarray:
    """
    Generate meta-labels for position sizing using ML.

    Follows López de Prado's methodology:
    1. Create binary target: was primary signal correct?
    2. Train classifier: features -> was_primary_correct
    3. Use purged k-fold CV to prevent data leakage
    4. Calibrate probabilities for proper bet sizing
    5. Output probability scores [0, 1]

    Args:
        primary_labels: Primary model predictions (-1, 0, 1)
        features: Feature matrix [n_samples, n_features]
        actual_returns: Actual returns for each event
        model_type: Type of classifier
        cv_folds: Number of CV folds
        embargo_pct: Embargo percentage after each fold
        calibrate: Whether to calibrate probabilities

    Returns:
        Probability scores [0, 1] for position sizing
        Higher values = higher confidence in primary signal
    """
    n_samples = len(primary_labels)

    # Create binary target
    meta_target = np.zeros(n_samples, dtype=np.int64)
    for i, (label, ret) in enumerate(zip(primary_labels, actual_returns)):
        if (label == 1 and ret > 0) or (label == -1 and ret < 0):
            meta_target[i] = 1
        else:
            meta_target[i] = 0

    # Initialize classifier
    if model_type == "random_forest":
        clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            min_samples_leaf=0.01,
            random_state=42,
            n_jobs=-1,
        )
    else:
        raise ValueError(f"Unknown model_type: {model_type}")

    # Use purged CV to prevent data leakage
    purged_cv = PurgedKFold(
        n_splits=cv_folds,
        embargo_pct=embargo_pct,
    )

    cv_splits = list(purged_cv.split(features, meta_target))

    # Cross-validated predictions
    meta_probs = np.zeros(n_samples)

    for train_idx, test_idx in cv_splits:
        X_train, X_test = features[train_idx], features[test_idx]
        y_train = meta_target[train_idx]

        # Train classifier
        clf.fit(X_train, y_train)

        # Predict probabilities for test set
        if hasattr(clf, "predict_proba"):
            probs = clf.predict_proba(X_test)[:, 1]
        else:
            probs = clf.predict(X_test).astype(float)

        meta_probs[test_idx] = probs

    # Optional: Calibrate probabilities
    if calibrate:
        calibrated_clf = CalibratedClassifierCV(
            clf,
            method='isotonic',
            cv='prefit',
        )
        calibrated_clf.fit(features, meta_target)
        meta_probs = calibrated_clf.predict_proba(features)[:, 1]

    return meta_probs
```

### AFTER (Option B - REMOVE)
```python
# app/backtesting/labeling/triple_barrier.py

# Remove the function entirely
# Add to module docstring:

"""
Triple Barrier Method for Financial ML Labeling.

Note: Meta-labeling is not currently implemented.
For position sizing using meta-labeling, see:
- López de Prado, "Advances in Financial Machine Learning", Chapter 3
- Meta-labeling involves training a secondary classifier to determine
  whether the primary signal is likely to be correct

This feature is planned for future implementation.
GitHub Issue: #XXX
"""
```

---

## 8. DATA SOURCE FALLBACK

### BEFORE (WRONG)
```python
# app/backtesting/data_loader.py

# Try multiple Yahoo Finance libraries as fallbacks
try:
    import yfinance as _yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

try:
    import yahoo_fin as _yahoo_fin
    HAS_YAHOO_FIN = True
except ImportError:
    HAS_YAHOO_FIN = False

# Then later...
def fetch_data(self, symbol: str) -> pd.DataFrame:
    if HAS_YFINANCE:
        return self._fetch_with_yfinance(symbol)
    elif HAS_YAHOO_FIN:
        return self._fetch_with_yahoo_fin(symbol)  # Different format!
    else:
        raise ValueError("No data source available")
```

### AFTER (CORRECT)
```python
# app/backtesting/data_loader.py

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    raise ImportError(
        "yfinance is REQUIRED for market data. "
        "Install with: pip install yfinance>=0.2.0"
    )

def fetch_data(self, symbol: str) -> pd.DataFrame:
    """
    Fetch market data for symbol.

    Args:
        symbol: Stock symbol (e.g., "AAPL")

    Returns:
        DataFrame with OHLCV data
    """
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="max")

    if data.empty:
        raise ValueError(f"No data found for symbol: {symbol}")

    return data
```

**AND add to requirements.txt:**
```txt
yfinance>=0.2.0  # REQUIRED: Yahoo Finance data
```

---

## 9. TODO COMMENTS

### BEFORE (WRONG)
```python
# app/backtesting/reports/baseline_optimization_reporter.py

def generate_report(self) -> str:
    """Generate HTML report."""
    html = self._generate_html()

    # TODO: Implement PDF generation using weasyprint or similar
    # pdf_path = self._generate_pdf_report()

    return html
```

### AFTER (Option A - IMPLEMENT)
```python
# app/backtesting/reports/baseline_optimization_reporter.py

from weasyprint import HTML, CSS

def generate_report(self, output_format: str = "html") -> str:
    """
    Generate report.

    Args:
        output_format: "html" or "pdf"

    Returns:
        Report file path
    """
    html = self._generate_html()

    if output_format == "pdf":
        output_path = self.output_path.replace(".html", ".pdf")
        HTML(string=html).write_pdf(output_path)
        return output_path
    else:
        output_path = self.output_path
        with open(output_path, "w") as f:
            f.write(html)
        return output_path
```

### AFTER (Option B - REMOVE TODO)
```python
# app/backtesting/reports/baseline_optimization_reporter.py

def generate_report(self) -> str:
    """
    Generate HTML report.

    Note:
        PDF export is not currently supported.
        Use your browser's print-to-PDF functionality instead.
    """
    html = self._generate_html()

    output_path = self.output_path
    with open(output_path, "w") as f:
        f.write(html)

    logger.info(f"Report saved to: {output_path}")
    logger.info("To save as PDF, open the HTML file and use Print > Save as PDF")

    return output_path
```

---

## TESTING EXAMPLES

### Test Numba Requirement
```python
# tests/unit/test_numba_accelerators.py

def test_numba_required():
    """Test that Numba is required."""
    # This test should fail without numba installed
    from app.core.numba_accelerators import calculate_rsi

    prices = [100, 101, 102, 103, 102, 101, 100, 99, 98, 99, 100, 101, 102, 103, 104]
    result = calculate_rsi(prices, period=14)

    assert result is not None
    assert 0 <= result <= 100

def test_numba_performance():
    """Test that Numba provides expected speedup."""
    import time
    from app.core.numba_accelerators import calculate_rsi

    prices = list(range(10000))  # 10K data points

    start = time.time()
    result = calculate_rsi(prices, period=14)
    elapsed = time.time() - start

    # Should be < 50ms with Numba
    assert elapsed < 0.05, f"Numba too slow: {elapsed:.3f}s"
```

### Test Email Requirement
```python
# tests/unit/test_notification_channels.py

def test_email_channel_requires_aiosmtplib():
    """Test that aiosmtplib is required for email."""
    # Mock aiosmtplib as unavailable
    import sys
    original_module = sys.modules.get('aiosmtplib')
    sys.modules['aiosmtplib'] = None

    # Should raise ImportError
    with pytest.raises(ImportError, match="aiosmtplib is REQUIRED"):
        from app.services.alerting_system.notification_channels import EmailChannel

    # Restore module
    if original_module:
        sys.modules['aiosmtplib'] = original_module
```

---

## MIGRATION GUIDE

### For Developers

1. **Update your local environment:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run tests to ensure dependencies:**
   ```bash
   pytest tests/unit/ -v
   ```

3. **Update imports in your code:**
   ```python
   # Before (with fallback)
   from app.core.numba_accelerators import calculate_rsi, NUMBA_AVAILABLE
   if NUMBA_AVAILABLE:
       rsi = calculate_rsi(prices)
   else:
       rsi = calculate_rsi_slow(prices)  # Fallback

   # After (no fallback)
   from app.core.numba_accelerators import calculate_rsi
   rsi = calculate_rsi(prices)  # Will raise ImportError if numba missing
   ```

4. **Handle ImportErrors in your application:**
   ```python
   # In your main.py or app/__init__.py
   try:
       from app.core.numba_accelerators import calculate_rsi
       from app.backtesting.labeling.triple_barrier import TripleBarrierLabeler
       # ... other imports ...
   except ImportError as e:
       logger.error(f"Missing required dependency: {e}")
       logger.error("Please install all required dependencies:")
       logger.error("  pip install -r requirements.txt")
       sys.exit(1)
   ```

### For DevOps

1. **Update CI/CD pipeline:**
   ```yaml
   # .github/workflows/test.yml
   jobs:
     test:
       steps:
         - name: Install dependencies
           run: pip install -r requirements.txt

         - name: Run tests
           run: pytest tests/ -v

         - name: Check for fallback logic
           run: |
             grep -r "HAS_" app/ && exit 1 || true
             grep -r "_AVAILABLE" app/ && exit 1 || true
             echo "No fallback flags found - OK"
   ```

2. **Update deployment documentation:**
   ```markdown
   ## Required Dependencies

   All dependencies are REQUIRED - no optional fallbacks.

   ```bash
   pip install -r requirements.txt
   ```

   ### Critical Dependencies
   - `numba>=0.59.0` - Required for performance
   - `scipy>=1.11.0` - Required for statistical functions
   - `matplotlib>=3.7.0` - Required for visualization
   ```

---

## SUMMARY

### Key Changes
1. **Remove all try/except ImportError with fallback**
2. **Raise ImportError immediately when dependency missing**
3. **Add all dependencies to requirements.txt**
4. **Remove all HAS_* flags**
5. **Remove all NotImplementedError stubs**
6. **Remove all TODO/FIXME comments**

### Benefits
- Explicit dependencies
- No silent degradation
- Clear error messages
- Easier debugging
- Better performance
- Cleaner code

### Files to Modify
1. `/app/core/numba_accelerators.py`
2. `/app/services/hurst_exponent_analyzer.py`
3. `/app/backtesting/labeling/triple_barrier.py`
4. `/app/services/momentum_analysis_optimized.py`
5. `/app/services/crypto_data_service.py` (or delete)
6. `/app/services/forex_data_service.py` (or delete)
7. `/app/services/alerting_system/notification_channels.py`
8. `/app/backtesting/data_loader.py`
9. `/app/strategies/pairs_trading.py`
10. `/requirements.txt`

### Estimated Time
- **Minimal fixes:** 15 hours (2 days)
- **Full implementation:** 59 hours (1.5 weeks)

---

**Remember:** "Either it's 100% implemented or it doesn't exist"
