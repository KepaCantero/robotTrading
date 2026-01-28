# Implementation Tasks for Half-Implemented Features
**Generated:** 2026-01-28
**Priority Order:** Critical → High → Medium → Low

---

## TASK 1: Remove Numba Fallback Logic (CRITICAL)
**Priority:** 🔴 HIGHEST
**Estimated Time:** 2 hours
**Agent:** Performance Optimization Specialist

### Files to Modify
1. `/app/core/numba_accelerators.py` (Lines 26-55)
2. `/app/services/hurst_exponent_analyzer.py` (Lines 44-72)
3. `/app/backtesting/labeling/triple_barrier.py` (Lines 24-34)
4. `/app/services/momentum_analysis_optimized.py` (Lines 25-45)

### Changes Required

**Before:**
```python
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

**After:**
```python
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

### Acceptance Criteria
- [ ] All files raise ImportError if numba is not installed
- [ ] No fallback decorator definitions exist
- [ ] No logging.warning() for missing numba
- [ ] All unit tests pass with numba installed
- [ ] ImportError raised without numba
- [ ] Documentation updated to reflect numba requirement

### Testing
```bash
# Test 1: Verify numba is required
python -c "from app.core.numba_accelerators import calculate_rsi"  # Should fail without numba

# Test 2: Verify numba works when installed
pip install numba>=0.59.0
python -c "from app.core.numba_accelerators import calculate_rsi; print('✅ Success')"

# Test 3: Run all tests
pytest tests/unit/test_numba_accelerators.py -v
```

### Installation Instructions
Add to documentation:
```markdown
## Required Dependencies

This system REQUIRES Numba for performance. Without Numba, calculations will be 50-100x slower.

```bash
pip install numba>=0.59.0,<1.0.0
```

If you cannot install Numba (e.g., on Windows without Visual Studio), consider using Docker instead.
```

---

## TASK 2: Resolve Crypto/Forex API Stubs (CRITICAL)
**Priority:** 🔴 HIGH
**Estimated Time:** 16 hours (if implementing) or 2 hours (if removing)
**Agent:** Integration Specialist

### Option A: Implement Full API Integration

#### Files to Modify
1. `/app/services/crypto_data_service.py` (Lines 365-386)
2. `/app/services/forex_data_service.py` (Lines 269-288)

#### Changes Required

**Implement `_fetch_price_from_api()` for Crypto:**
```python
def _fetch_price_from_api(self, pair: str) -> Optional[Decimal]:
    """
    Fetch current price from exchange API.

    Args:
        pair: Crypto pair (e.g., "BTC/USD")

    Returns:
        Current price as Decimal

    Raises:
        ConnectionError: If API unavailable
        ValueError: If invalid response
    """
    import httpx

    # Map pair to exchange symbol
    symbol = self._pair_to_exchange_symbol(pair)

    try:
        async def _fetch():
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Example: Binance API
                response = await client.get(
                    f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
                )
                response.raise_for_status()
                data = response.json()
                return Decimal(str(data['price']))

        return asyncio.run(self.reconnection_manager.connect_with_backoff(_fetch))

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching price for {pair}: {e}")
        raise
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Connection error fetching price for {pair}: {e}")
        raise

def _pair_to_exchange_symbol(self, pair: str) -> str:
    """Convert pair format to exchange symbol."""
    # BTC/USD -> BTCUSDT
    base, quote = pair.split('/')
    return f"{base.upper()}{quote.upper()}T"
```

**Implement `_fetch_rate_from_api()` for Forex:**
```python
def _fetch_rate_from_api(self, pair: str) -> Optional[Decimal]:
    """
    Fetch current exchange rate from API.

    Args:
        pair: Forex pair (e.g., "EUR/USD")

    Returns:
        Current exchange rate as Decimal

    Raises:
        ConnectionError: If API unavailable
        ValueError: If invalid response
    """
    import httpx

    try:
        async def _fetch():
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Example: exchangerate-api.io
                response = await client.get(
                    f"https://api.exchangerate-api.com/v4/latest/{pair.replace('/', '')}"
                )
                response.raise_for_status()
                data = response.json()
                return Decimal(str(data['rates'][pair.split('/')[1]]))

        return asyncio.run(self.reconnection_manager.connect_with_backoff(_fetch))

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching rate for {pair}: {e}")
        raise
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Connection error fetching rate for {pair}: {e}")
        raise
```

**Add to requirements.txt:**
```txt
# API Clients
httpx>=0.25.0  # Required: Async HTTP client for APIs
```

**Acceptance Criteria (Option A):**
- [ ] All `_fetch_*_from_api()` methods implemented
- [ ] No NotImplementedError stubs remain
- [ ] No hardcoded fallback prices
- [ ] Proper error handling (raise, don't return None)
- [ ] Rate limiting implemented
- [ ] Authentication configured (if needed)
- [ ] Integration tests pass with real APIs
- [ ] API keys documented in .env.example

### Option B: Remove Services Entirely

**Files to Delete:**
1. `/app/services/crypto_data_service.py`
2. `/app/services/forex_data_service.py`

**Files to Update:**
```bash
# Find all imports
grep -r "from app.services.crypto_data_service" /app/
grep -r "from app.services.forex_data_service" /app/
grep -r "CryptoDataService" /app/
grep -r "ForexDataService" /app/
```

**Acceptance Criteria (Option B):**
- [ ] Both service files deleted
- [ ] All imports removed from other files
- [ ] Documentation updated to reflect removal
- [ ] No broken imports in tests
- [ ] CI/CD passes

---

## TASK 3: Fix Email Notification Fallback (HIGH)
**Priority:** 🟠 HIGH
**Estimated Time:** 3 hours
**Agent:** Notification Specialist

### Files to Modify
1. `/app/services/alerting_system/notification_channels.py` (Lines 114-121)
2. `/requirements.txt`

### Changes Required

**Add to requirements.txt:**
```txt
# Email Notifications
aiosmtplib>=3.0.0  # REQUIRED: Async SMTP for email notifications
```

**Update EmailChannel.send():**
```python
# BEFORE
try:
    import aiosmtplib
except ImportError:
    logger.warning("aiosmtplib not installed. Run: pip install aiosmtplib")
    # Fallback: log the notification
    logger.info(f"[EMAIL SIMULATION] To: {target.endpoint}, ...")
    return True  # Pretends success

# AFTER
try:
    import aiosmtplib
except ImportError:
    raise ImportError(
        "aiosmtplib is REQUIRED for email notifications. "
        "Install with: pip install aiosmtplib>=3.0.0"
    )
```

**Acceptance Criteria:**
- [ ] aiosmtplib in requirements.txt
- [ ] ImportError raised if aiosmtplib missing
- [ ] No "EMAIL SIMULATION" fallback
- [ ] EmailChannel returns False on failure (not True)
- [ ] Integration tests verify email sending
- [ ] SMTP configuration documented

### Testing
```bash
# Test 1: Verify aiosmtplib is required
python -c "from app.services.alerting_system.notification_channels import EmailChannel" \
  # Should fail without aiosmtplib

# Test 2: Test email sending
pytest tests/unit/services/test_notification_channels.py -v -k email
```

---

## TASK 4: Resolve Visualization Dependencies (MEDIUM)
**Priority:** 🟡 MEDIUM
**Estimated Time:** 2 hours
**Agent:** Visualization Specialist

### Files to Modify
1. `/app/backtesting/labeling/triple_barrier.py` (Lines 36-42)
2. `/requirements.txt`

### Changes Required

**Add to requirements.txt:**
```txt
# Visualization
matplotlib>=3.7.0  # REQUIRED: Visualization and plotting
```

**Update import:**
```python
# BEFORE
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    plt = None

# AFTER
try:
    import matplotlib.pyplot as plt
except ImportError:
    raise ImportError(
        "matplotlib is REQUIRED for visualization. "
        "Install with: pip install matplotlib>=3.7.0"
    )
```

**Update plot_triple_barrier():**
```python
def plot_triple_barrier(...) -> Optional["plt.Axes"]:
    if not HAS_MATPLOTLIB:  # Remove this check
        import warnings
        warnings.warn("Matplotlib not available, skipping visualization", UserWarning)
        return None

    # Direct implementation - no HAS_MATPLOTLIB check
    if ax is None:
        _, ax = plt.subplots(figsize=(12, 6))
    # ... rest of implementation
```

**Acceptance Criteria:**
- [ ] matplotlib in requirements.txt
- [ ] ImportError raised when importing visualization functions
- [ ] No HAS_MATPLOTLIB flags
- [ ] Clear documentation of visualization features
- [ ] Visualization tests pass

---

## TASK 5: Implement or Remove Meta-Labeling (MEDIUM)
**Priority:** 🟡 MEDIUM
**Estimated Time:** 12 hours (if implementing) or 1 hour (if removing)
**Agent:** ML Specialist

### Option A: Implement Full Meta-Labeling

**File to Modify:** `/app/backtesting/labeling/triple_barrier.py` (Lines 663-695)

**Full Implementation:**
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import PurgedKFold
from sklearn.calibration import CalibratedClassifierCV
import numpy as np

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
    1. Train classifier: features -> was_primary_correct
    2. Use purged k-fold CV to prevent data leakage
    3. Calibrate probabilities for proper bet sizing
    4. Output probability scores [0, 1]

    Args:
        primary_labels: Primary model predictions (-1, 0, 1)
        features: Feature matrix [n_samples, n_features]
        actual_returns: Actual returns for each event
        model_type: Type of classifier ('random_forest', 'logistic', etc.)
        cv_folds: Number of CV folds
        embargo_pct: Embargo percentage after each fold
        calibrate: Whether to calibrate probabilities

    Returns:
        Probability scores [0, 1] for position sizing
        Higher values = higher confidence in primary signal

    Example:
        >>> meta_probs = meta_labeling(primary_preds, X, actual_returns)
        >>> # Use meta_probs for bet sizing
        >>> position_size = base_size * (meta_probs - 0.5) * 2
    """
    n_samples = len(primary_labels)

    # Create binary target: was primary signal correct?
    meta_target = np.zeros(n_samples, dtype=np.int64)
    for i, (label, ret) in enumerate(zip(primary_labels, actual_returns)):
        if (label == 1 and ret > 0) or (label == -1 and ret < 0):
            meta_target[i] = 1  # Primary was correct
        else:
            meta_target[i] = 0  # Primary was wrong

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
    # Import existing PurgedKFold implementation
    from app.backtesting.validation.purged_kfold import PurgedKFold

    purged_cv = PurgedKFold(
        n_splits=cv_folds,
        embargo_pct=embargo_pct,
    )

    # Get CV splits (assuming sequential data)
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
            # Fallback for classifiers without predict_proba
            probs = clf.predict(X_test).astype(float)

        meta_probs[test_idx] = probs

    # Optional: Calibrate probabilities
    if calibrate:
        from sklearn.calibration import CalibratedClassifierCV

        calibrated_clf = CalibratedClassifierCV(
            clf,
            method='isotonic',
            cv='prefit',
        )
        # Refit on full data with calibration
        calibrated_clf.fit(features, meta_target)
        meta_probs = calibrated_clf.predict_proba(features)[:, 1]

    return meta_probs
```

**Acceptance Criteria (Option A):**
- [ ] Full ML pipeline implemented
- [ ] PurgedKFold CV prevents data leakage
- [ ] Probability scores calibrated
- [ ] Feature importance analysis added
- [ ] Unit tests validate probabilities
- [ ] Documentation updated
- [ ] Performance benchmarks

### Option B: Remove Function

**Changes:**
```python
# Remove the function entirely
# Add docstring to module:
"""
Triple Barrier Method for Financial ML Labeling.

Note: Meta-labeling is not currently implemented.
For position sizing using meta-labeling, see López de Prado (2018).
This feature is planned for future implementation.
"""
```

**Acceptance Criteria (Option B):**
- [ ] Function removed
- [ ] Module docstring updated
- [ ] No broken imports
- [ ] Documentation updated

---

## TASK 6: Implement or Remove BacktestExecutor (HIGH)
**Priority:** 🟠 HIGH
**Estimated Time:** 8 hours (if implementing) or 1 hour (if making abstract)
**Agent:** Backtesting Specialist

### Option A: Make Class Abstract

**File to Modify:** `/app/backtesting/core/executor.py`

**Changes:**
```python
from abc import ABC, abstractmethod

class BacktestExecutor(ABC):
    """
    Abstract base class for backtest execution.

    Subclasses must implement the execute() method with specific
    backtest execution logic.
    """

    @abstractmethod
    def execute(
        self,
        quotes: QuotesType,
        strategy: StrategyType,
        **kwargs
    ) -> BacktestResult:
        """
        Execute backtest and return results.

        Args:
            quotes: List of market data quotes
            strategy: Trading strategy instance
            **kwargs: Additional execution parameters

        Returns:
            BacktestResult with performance metrics

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If execution fails

        Note:
            This method MUST be implemented by subclasses.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement execute() method"
        )
```

**Acceptance Criteria (Option A):**
- [ ] Class marked as abstract (inherits from ABC)
- [ ] execute() marked as @abstractmethod
- [ ] Docstring updated to reflect abstract nature
- [ ] All subclasses properly implement execute()
- [ ] Unit tests validate abstract behavior
- [ ] ImportError if trying to instantiate base class

### Option B: Implement execute()

This is more complex and requires full backtest execution logic. Consider making it abstract instead.

---

## TASK 7: Standardize Data Source Libraries (LOW)
**Priority:** 🟢 LOW
**Estimated Time:** 2 hours
**Agent:** Data Engineering Specialist

### Files to Modify
1. `/app/backtesting/data_loader.py` (Lines 20-49)

### Changes Required

**Remove yahoo_fin fallback:**
```python
# BEFORE
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

# AFTER
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    raise ImportError(
        "yfinance is REQUIRED for market data. "
        "Install with: pip install yfinance>=0.2.0"
    )
```

**Update all references:**
- Replace `HAS_YAHOO_FIN` with `YFINANCE_AVAILABLE`
- Remove yahoo_fin imports
- Use only yfinance

**Acceptance Criteria:**
- [ ] Only yfinance used
- [ ] No yahoo_fin references
- [ ] yfinance in requirements.txt
- [ ] No HAS_YAHOO_FIN flags
- [ ] All tests pass with yfinance only

---

## TASK 8: Implement or Remove PDF Report Generation (LOW)
**Priority:** 🟢 LOW
**Estimated Time:** 6 hours (if implementing) or 0.5 hours (if removing TODO)

### Option A: Implement PDF Export

**Add to requirements.txt:**
```txt
# PDF Generation
weasyprint>=60.0  # HTML to PDF conversion
```

**Implement in `/app/backtesting/reports/baseline_optimization_reporter.py`:**
```python
def generate_pdf_report(
    self,
    output_path: str,
    include_charts: bool = True,
) -> None:
    """
    Generate PDF report from backtest results.

    Args:
        output_path: Path to save PDF file
        include_charts: Whether to include performance charts

    Raises:
        ImportError: If weasyprint not available
        ValueError: If no results to export
    """
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        raise ImportError(
            "weasyprint is REQUIRED for PDF generation. "
            "Install with: pip install weasyprint>=60.0"
        )

    if not self.results:
        raise ValueError("No backtest results to export")

    # Generate HTML report first
    html_content = self._generate_html_report()

    # Convert to PDF
    HTML(string=html_content).write_pdf(
        output_path,
        stylesheets=[CSS(string=self._get_pdf_styles())]
    )

    logger.info(f"✅ PDF report saved to: {output_path}")
```

**Acceptance Criteria (Option A):**
- [ ] weasyprint in requirements.txt
- [ ] generate_pdf_report() implemented
- [ ] PDF styling added
- [ ] Unit tests validate PDF generation
- [ ] Charts embedded in PDF

### Option B: Remove TODO

**Changes:**
```python
# Remove line 261:
# TODO: Implement PDF generation using weasyprint or similar

# Add to documentation:
"""
Report Generation
-----------------
Supported formats:
- HTML (default): Interactive HTML reports with charts
- JSON: Machine-readable data export
- CSV: Spreadsheet-compatible results

Note: PDF export is not currently supported.
Use HTML export and print-to-PDF as a workaround.
"""
```

---

## TASK 9: Address All TODO/FIXME Comments (MEDIUM)
**Priority:** 🟡 MEDIUM
**Estimated Time:** 8 hours
**Agent:** Code Quality Specialist

### Files to Address

#### 1. `/app/tax/exporters/modelo_721_exporter.py`
**Lines 356, 382:** Incomplete tax export implementation

**Action:**
```python
# Option A: Implement
def _calculate_fallback_tax_rate(self, asset_type: str) -> Decimal:
    """Calculate fallback tax rate when specific rate not available."""
    # Implement proper tax rate calculation
    tax_rates = {
        "stocks": Decimal("0.19"),
        "etf": Decimal("0.19"),
        "bonds": Decimal("0.19"),
        "crypto": Decimal("0.19"),
    }
    return tax_rates.get(asset_type.lower(), Decimal("0.19"))

def _parse_ecb_xml(self, xml_content: str) -> Dict:
    """Parse ECB XML reference rates."""
    from xml.etree import ElementTree as ET

    root = ET.fromstring(xml_content)
    # Parse and return exchange rates
    # ...
```

**Option B:** Remove incomplete implementation and mark as unsupported

#### 2. `/app/models/deployment.py`
**Line 7:** "TODO: Complete implementation in PHASE 4"

**Action:**
- Convert to GitHub issue
- Add link in docstring
- Or implement now if critical

#### 3. `/app/dashboard/data_loader.py`
**Lines 74, 79:** Status check and PnL retrieval not implemented

**Action:**
```python
# Implement actual status check
def get_trading_status(self) -> Dict[str, Any]:
    """Get current trading status."""
    # Query database or API for actual status
    return {
        "is_trading": True,
        "active_positions": len(self.position_manager.get_all_positions()),
        "last_signal_time": self.signal_manager.get_last_signal_time(),
    }
```

#### 4. `/app/services/live_trading/broker_adapters/ib_adapter.py`
**Lines 49-50:** Position model not implemented

**Action:**
- Implement position model or
- Import from existing position module

#### 5. `/app/services/corporate_actions/handler.py`
**Line 818:** No persistence

**Action:**
```python
def persist_to_database(self, event: CorporateActionEvent) -> None:
    """Persist corporate action to database."""
    from app.database.models import CorporateAction

    db_event = CorporateAction(
        symbol=event.symbol,
        action_type=event.action_type,
        declaration_date=event.declaration_date,
        ex_date=event.ex_date,
        record_date=event.record_date,
        pay_date=event.pay_date,
        value=event.value,
    )
    self.db_session.add(db_event)
    self.db_session.commit()
```

#### 6. `/app/strategies/momentum_modular/learning/deep_learning_engine.py`
**Line 737:** Weight loading not implemented

**Action:**
```python
def load_pretrained_weights(self, model_path: str) -> None:
    """Load pretrained model weights."""
    import torch

    checkpoint = torch.load(model_path)
    self.model.load_state_dict(checkpoint['model_state_dict'])
    self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    logger.info(f"✅ Loaded pretrained weights from: {model_path}")
```

**Acceptance Criteria:**
- [ ] All TODO/FIXME comments resolved
- [ ] Either implemented or removed
- [ ] GitHub issues created for future work
- [ ] No placeholder comments in code
- [ ] Documentation updated

---

## TESTING STRATEGY

### Unit Tests
For each task, create unit tests:

```python
# Example: Test Numba requirement
def test_numba_required():
    """Test that Numba is required for accelerators."""
    # This should fail without numba
    with pytest.raises(ImportError):
        # Mock numba as unavailable
        import sys
        sys.modules['numba'] = None

        # Try to import accelerators
        from app.core.numba_accelerators import calculate_rsi
```

### Integration Tests
```python
# Example: Test email notification
def test_email_notification_sending():
    """Test that email notifications are sent."""
    # Configure test SMTP server
    # Send test email
    # Verify email received
    pass
```

### Performance Tests
```python
# Example: Verify Numba speedup
def test_numba_performance():
    """Test that Numba provides expected speedup."""
    import time

    # Test with Numba
    start = time.time()
    result = calculate_rsi(prices, period=14)
    numba_time = time.time() - start

    # Should be < 50ms for 10K data points
    assert numba_time < 0.05, f"Numba too slow: {numba_time}s"
```

---

## DEPLOYMENT CHECKLIST

### Pre-Deployment
- [ ] All tasks completed
- [ ] All tests passing
- [ ] Documentation updated
- [ ] requirements.txt updated
- [ ] CI/CD pipeline updated
- [ ] Migration guide created

### Deployment
- [ ] Create feature branch
- [ ] Merge to main
- [ ] Tag release
- [ ] Update CHANGELOG.md
- [ ] Deploy to staging
- [ ] Run smoke tests
- [ ] Deploy to production

### Post-Deployment
- [ ] Monitor error logs
- [ ] Verify performance metrics
- [ ] Check user feedback
- [ ] Update documentation as needed

---

## SUMMARY

### Total Estimated Time
- Task 1 (Numba): 2 hours
- Task 2 (Crypto/Forex): 16 hours (implement) or 2 hours (remove)
- Task 3 (Email): 3 hours
- Task 4 (Visualization): 2 hours
- Task 5 (Meta-labeling): 12 hours (implement) or 1 hour (remove)
- Task 6 (BacktestExecutor): 8 hours (implement) or 1 hour (abstract)
- Task 7 (Data sources): 2 hours
- Task 8 (PDF): 6 hours (implement) or 0.5 hours (remove)
- Task 9 (TODOs): 8 hours

**If implementing everything:** ~59 hours (~1.5 weeks)
**If making minimal changes:** ~15.5 hours (~2 days)

### Recommended Approach
1. **Phase 1 (Critical):** Tasks 1, 2 (remove), 3 - 1 week
2. **Phase 2 (High):** Tasks 4, 6 (abstract), 7 - 1 week
3. **Phase 3 (Medium):** Task 9 - 1 week
4. **Phase 4 (Future):** Tasks 5, 8 - As needed

### Success Metrics
- Zero fallback logic in production code
- All required dependencies enforced
- No NotImplementedError in core features
- Clear error messages for missing dependencies
- Documentation matches implementation
