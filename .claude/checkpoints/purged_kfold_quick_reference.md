# Purged K-Fold with Embargo - Quick Reference Guide

**Reference:** López de Prado, "Advances in Financial Machine Learning", Chapter 3.6

---

## 🚀 Quick Start

### Installation
Already included in `app/backtesting/validation/purged_kfold.py`

### Basic Usage
```python
from app.backtesting.validation.purged_kfold import PurgedKFold

# Create cross-validator
purged_cv = PurgedKFold(
    n_splits=5,
    purge_pct=0.05,   # 5% purge
    embargo_pct=0.02,  # 2% embargo
)

# Generate splits
splits = purged_cv.split(X, y)

# Use splits
for train_idx, test_idx in splits:
    X_train, X_test = X[train_idx], X[test_idx]
    # Train and evaluate model...
```

---

## 📖 Key Concepts

### Purge (5% default)
Removes training samples that overlap with test period.

**Why?** Prevents look-ahead bias from samples containing information about test period.

### Embargo (2% default)
Adds buffer zone after test set.

**Why?** Prevents information leakage from adjacent samples.

### K-Fold (5 splits default)
Splits data into K folds for robust validation.

**Why?** Provides reliable performance estimates across multiple splits.

---

## 🔧 Configuration

### PurgedKFold Parameters
```python
PurgedKFold(
    n_splits=5,           # Number of folds
    purge_pct=0.05,       # Purge % (0-0.5)
    embargo_pct=0.02,     # Embargo % (0-0.5)
    min_train_samples=252,# Min training samples
    min_test_samples=20,  # Min test samples
    shuffle=False,        # Don't shuffle time series
    random_state=None,    # Random seed
)
```

### Recommended Settings

| Scenario | n_splits | purge_pct | embargo_pct |
|----------|----------|-----------|-------------|
| Daily Data | 5 | 0.05 | 0.02 |
| Intraday | 10 | 0.03 | 0.01 |
| Weekly | 3 | 0.10 | 0.05 |

---

## 📊 API Reference

### Main Classes

#### PurgedKFold
```python
split(X, y=None, groups=None)
    # Returns: List of (train_indices, test_indices)

validate_no_leakage(X)
    # Returns: True if no leakage detected

get_n_splits()
    # Returns: Number of splits

get_split_summary()
    # Returns: DataFrame with split statistics
```

#### PurgedTimeSeriesSplit
```python
PurgedTimeSeriesSplit(
    n_splits=5,
    purge_pct=0.05,
    embargo_pct=0.02,
    max_train_size=None,  # Fixed window size
    test_size=None,       # Fixed test size
)

split(X, y=None, groups=None)
    # Returns: List of (train_indices, test_indices)
```

### Convenience Functions

#### purged_kfold_splits()
```python
splits = purged_kfold_splits(
    X,
    n_splits=5,
    purge_pct=0.05,
    embargo_pct=0.02,
)
```

#### cross_validate_with_purging()
```python
results = cross_validate_with_purging(
    estimator,  # sklearn-like estimator
    X, y,
    n_splits=5,
    purge_pct=0.05,
    embargo_pct=0.02,
    scoring=None,  # Custom scoring function
    fit_params=None,
)
# Returns: {'test_score': [scores...]}
```

---

## 🧪 Testing

### Validate No Leakage
```python
purged_cv = PurgedKFold(n_splits=5)
splits = purged_cv.split(X, y)

# Check for leakage
is_safe = purged_cv.validate_no_leakage(X)
print(f"No leakage: {is_safe}")
```

### View Split Details
```python
summary = purged_cv.get_split_summary()
print(summary)
# Output:
#    fold  train_size  test_size  purged_count  embargo_size  purge_pct
# 0     0         780        200             0            20       0.00
# 1     1         730        200            50            20       6.25
```

---

## 💡 Examples

### Example 1: Classification
```python
from sklearn.ensemble import RandomForestClassifier
from app.backtesting.validation.purged_kfold import cross_validate_with_purging

clf = RandomForestClassifier()
results = cross_validate_with_purging(clf, X, y, n_splits=5)
print(f"Mean accuracy: {np.mean(results['test_score']):.4f}")
```

### Example 2: Regression
```python
from sklearn.linear_model import LinearRegression

reg = LinearRegression()
results = cross_validate_with_purging(reg, X, y_continuous, n_splits=5)
print(f"Mean R²: {np.mean(results['test_score']):.4f}")
```

### Example 3: Custom Scoring
```python
from sklearn.metrics import f1_score

results = cross_validate_with_purging(
    clf, X, y, n_splits=5,
    scoring=lambda y_true, y_pred: f1_score(y_true, y_pred, average='weighted')
)
```

### Example 4: Time Series Split
```python
from app.backtesting.validation.purged_kfold import PurgedTimeSeriesSplit

tscv = PurgedTimeSeriesSplit(n_splits=5, test_size=50)
splits = tscv.split(X, y)

for train_idx, test_idx in splits:
    # Expanding window for time series
    X_train, X_test = X[train_idx], X[test_idx]
    # ...
```

---

## ⚠️ Common Pitfalls

### Don't Use Standard K-Fold
```python
# ❌ WRONG - Causes look-ahead bias
from sklearn.model_selection import KFold
kf = KFold(n_splits=5, shuffle=True)

# ✅ CORRECT - Use PurgedKFold
from app.backtesting.validation.purged_kfold import PurgedKFold
purged_cv = PurgedKFold(n_splits=5, shuffle=False)
```

### Don't Shuffle Time Series
```python
# ❌ WRONG - Breaks temporal order
purged_cv = PurgedKFold(n_splits=5, shuffle=True)

# ✅ CORRECT - Preserve temporal order
purged_cv = PurgedKFold(n_splits=5, shuffle=False)
```

### Always Validate Leakage
```python
# ✅ Always check for leakage
purged_cv = PurgedKFold(n_splits=5)
splits = purged_cv.split(X, y)
assert purged_cv.validate_no_leakage(X), "Leakage detected!"
```

---

## 📚 Resources

### Main Implementation
- `app/backtesting/validation/purged_kfold.py` - Core implementation
- `tests/backtesting/validation/test_purged_kfold.py` - Unit tests
- `examples/purged_kfold_example.py` - Usage examples

### Integration
- `app/backtesting/data_split.py` - DataSplit with Purged K-Fold support
- `app/backtesting/walk_forward_validator.py` - Walk-forward validation

### Documentation
- `.claude/checkpoints/phase3_purged_kfold_checkpoint.md` - Full checkpoint report
- `.claude/rules/03-lopez-de-prado-advances-financial-ml.md` - López de Prado rules

---

## 🎓 Theory

### Why Purge?
Financial time series have serial correlation. Samples close in time share information. Standard K-Fold includes these samples in training, causing look-ahead bias.

**Solution:** Purge removes training samples within `purge_pct` of test set.

### Why Embargo?
Samples immediately after test set may still share information due to:
- Overnight gaps
- Market microstructure effects
- Order flow persistence

**Solution:** Embargo adds buffer zone after test set.

### Mathematical Formulation

Given:
- n_samples: Total samples
- purge_pct: Purge percentage
- embargo_pct: Embargo percentage

Purge zone:
```
purge_size = max(1, int(n_samples * purge_pct))
purge_start = test_start - purge_size
purge_end = test_start
```

Embargo zone:
```
embargo_size = max(1, int(n_samples * embargo_pct))
embargo_start = test_end
embargo_end = test_end + embargo_size
```

---

## ✅ Best Practices

1. **Always use PurgedKFold for financial time series**
2. **Set shuffle=False to preserve temporal order**
3. **Validate no leakage after generating splits**
4. **Use PurgedTimeSeriesSplit for pure time series**
5. **Adjust purge_pct/embargo_pct based on data frequency**
6. **Use cross_validate_with_purging for sklearn-like API**
7. **Review split summary to understand purge/embargo effects**

---

## 🚀 Advanced Usage

### Custom Purge/Embargo Calculation
```python
from app.backtesting.validation.purged_kfold import get_purge_indices, get_embargo_indices

# Calculate purged indices
purged = get_purge_indices(train_idx, test_idx, purge_pct=0.05, n_samples=1000)

# Calculate embargo indices
embargo = get_embargo_indices(test_idx, embargo_pct=0.02, n_samples=1000)

# Apply embargo to training set
train_after_embargo, embargo_idx = apply_embargo(
    train_idx, test_idx, embargo_pct=0.02, n_samples=1000
)
```

### Integration with Backtesting
```python
from app.backtesting.data_split import DataSplit, TrainValTestSplitter

# Configure with Purged K-Fold
split_config = DataSplit(
    use_purged_kfold=True,
    n_splits=5,
    purge_pct=0.05,
    embargo_pct=0.02,
)

splitter = TrainValTestSplitter(split_config)
splits = splitter.purged_kfold_split(market_data)

# Use splits in backtesting
for train_data, test_data in splits:
    # Run backtest...
```

---

**Last Updated:** 2025-01-28
**Version:** 1.0.0
