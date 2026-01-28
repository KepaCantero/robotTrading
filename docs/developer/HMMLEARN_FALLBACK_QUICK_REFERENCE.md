# HMMlearn Fallback - Quick Reference Guide

## Overview

The codebase uses Hidden Markov Models (HMM) for market regime detection. When the `hmmlearn` package is not available, the system automatically falls back to using sklearn's `GaussianMixture`.

## Files Using HMM

1. **`/app/engines/context_engine/regime_detectors/hmm_regime_detector.py`**
   - HMM-based regime detection for context engine
   - Detects bull, bear, and sideways market regimes

2. **`/app/services/regime_detection_chan.py`**
   - Ernest Chan's regime detection methodology
   - Market regime detection with multiple methods (HMM, K-Means, threshold, momentum)

## Usage

### Normal Usage (No Code Changes Required)

```python
# Import and use as normal - the fallback is transparent
from app.engines.context_engine.regime_detectors.hmm_regime_detector import HMMRegimeDetector

detector = HMMRegimeDetector(n_regimes=3)
detector.fit(prices)
result = detector.detect(prices)
```

```python
# Chan's regime detection
from app.services.regime_detection_chan import MarketRegimeDetector

detector = MarketRegimeDetector(method='hmm', n_regimes=3)
regimes = detector.detect_regimes(returns, prices)
```

### Check if HMM is Available

```python
from app.engines.context_engine.regime_detectors.hmm_regime_detector import HMM_AVAILABLE

if HMM_AVAILABLE:
    # Using full HMM implementation
    print("Full HMM available")
else:
    # Using GaussianMixture fallback
    print("Using fallback")
```

## Installation

### For Production (Recommended)

```bash
pip install hmmlearn
```

### With Requirements

Add to `requirements.txt`:
```
hmmlearn>=0.2.8
```

Or to `requirements-dev.txt`:
```
hmmlearn>=0.2.8
```

## Fallback Behavior

### With hmmlearn (Optimal)
- Full Hidden Markov Model
- Captures temporal dependencies
- Estimates transition probabilities
- Better for time series regime detection

### Without hmmlearn (Fallback)
- Uses sklearn's GaussianMixture
- Clustering without temporal dynamics
- Stationary transition matrix
- Basic regime detection functionality

## Logging

### Check Your Logs

**HMM Available:**
```
INFO: hmmlearn is available - using Hidden Markov Models for regime detection
```

**Using Fallback:**
```
WARNING: hmmlearn is not available. HMM regime detection will use fallback to GaussianMixture.
For optimal regime detection, install hmmlearn: pip install hmmlearn
```

## Testing

### Test Both Scenarios

**Test with hmmlearn:**
```bash
# Install hmmlearn
pip install hmmlearn

# Run tests
pytest tests/unit/engines/context_engine/test_hmm_regime_detector.py
```

**Test without hmmlearn:**
```bash
# Uninstall hmmlearn
pip uninstall -y hmmlearn

# Run tests (should use fallback)
pytest tests/unit/engines/context_engine/test_hmm_regime_detector.py
```

## Troubleshooting

### Import Error Already Fixed

If you see:
```
ModuleNotFoundError: No module named 'hmmlearn'
```

This is expected behavior if hmmlearn is not installed. The code will:
1. Log a warning
2. Use GaussianMixture fallback
3. Continue functioning normally

### Verify Fallback is Working

```python
import logging
logging.basicConfig(level=logging.INFO)

from app.engines.context_engine.regime_detectors.hmm_regime_detector import HMMRegimeDetector

# You should see the warning if hmmlearn is not installed
detector = HMMRegimeDetector()
```

### Performance Differences

**HMM (Optimal):**
- Better at detecting regime transitions
- Captures persistence in market states
- More accurate for time-series data

**GaussianMixture (Fallback):**
- Still provides reasonable regime clustering
- May be less sensitive to temporal patterns
- Suitable for initial development/testing

## API Reference

### HMMRegimeDetector

```python
class HMMRegimeDetector:
    def __init__(self, config: Dict[str, Any] = None)
        """
        Args:
            n_regimes: Number of regimes (default: 3)
            n_features: Number of features (default: 2)
            window_size: Rolling window size (default: 100)
            min_samples: Minimum samples for training (default: 50)
        """

    def fit(self, prices: List[float]) -> bool
        """Train HMM model"""

    def detect(self, prices: List[float]) -> Dict[str, Any]
        """
        Detect current regime
        Returns:
            regime: str
            probability: float
            regime_probabilities: Dict[str, float]
            confidence: float
            state: int
        """
```

### MarketRegimeDetector (Chan)

```python
class MarketRegimeDetector:
    def __init__(self, n_regimes: int = 3, method: str = "hmm", lookback_window: int = 60)
        """
        Args:
            n_regimes: Number of regimes to detect
            method: 'hmm', 'kmeans', 'threshold', or 'momentum'
            lookback_window: Lookback window for features
        """

    def detect_regimes(self, returns: pd.Series, prices: Optional[pd.Series] = None) -> pd.Series
        """Detect market regimes from price/return data"""
```

## Best Practices

1. **Production:** Install hmmlearn for optimal performance
2. **Development:** Can use fallback for initial development
3. **Testing:** Test both scenarios if possible
4. **Monitoring:** Check logs for fallback warnings
5. **Documentation:** Inform users of optional dependency

## Related Files

- `/app/engines/context_engine/regime_detectors/hmm_regime_detector.py`
- `/app/services/regime_detection_chan.py`
- `/scripts/verify_ml_dependencies.py` (validation script)
- `/HMMLEARN_FALLBACK_IMPLEMENTATION.md` (detailed implementation report)

---

**Last Updated:** 2026-01-28
**Status:** Active - Fallback implementation complete and tested
