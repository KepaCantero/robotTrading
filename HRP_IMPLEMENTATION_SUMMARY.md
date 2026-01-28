# Hierarchical Risk Parity (HRP) Implementation Summary

## Overview

This document summarizes the implementation of **Hierarchical Risk Parity (HRP)** following Marcos López de Prado's specifications from "Machine Learning for Asset Managers" (2016) and "Advances in Financial Machine Learning".

## Files Created

### 1. Main Implementation
**File:** `/Users/kepa.cantero/Projects/algoTrading/app/engines/portfolio_engine/optimizers/hierarchical_risk_parity.py`

**Classes:**
- `HierarchicalRiskParity` - Core HRP implementation
- `HRPOptimizer` - Wrapper class matching optimizer interface

**Key Functions:**
- `compute_hrp_weights()` - Convenience function for computing HRP weights
- `plot_hrp_dendrogram()` - Visualization function for dendrograms

### 2. Tests
**File:** `/Users/kepa.cantero/Projects/algoTrading/tests/unit/engines/portfolio_engine/optimizers/test_hierarchical_risk_parity.py`

**Test Coverage:**
- 33 comprehensive tests covering all HRP functionality
- Tests for all linkage methods (single, average, complete, ward)
- Edge cases (single asset, empty matrices, etc.)
- Property tests (diversification, stability, no negative weights)

### 3. Updated Module Export
**File:** `/Users/kepa.cantero/Projects/algoTrading/app/engines/portfolio_engine/optimizers/__init__.py`

Added HRP exports:
- `HierarchicalRiskParity`
- `HRPOptimizer`
- `compute_hrp_weights`
- `plot_hrp_dendrogram`
- `HRP_AVAILABLE`

## HRP Algorithm Implementation

### Step 1: Correlation-Based Distance
```python
distance = sqrt((1 - correlation) / 2)
```
This ensures:
- correlation = 1 → distance = 0 (identical assets)
- correlation = 0 → distance = sqrt(0.5) (uncorrelated)
- correlation = -1 → distance = 1 (opposite behavior)

### Step 2: Hierarchical Clustering
Supports 4 linkage methods from scipy.cluster.hierarchy:
1. **Single** - Minimum distance between clusters
2. **Average** - Average distance (UPGMA)
3. **Complete** - Maximum distance
4. **Ward** - Minimize within-cluster variance

### Step 3: Quasi-Diagonalization
Reorders the covariance matrix so that similar investments are placed together using the dendrogram structure.

### Step 4: Recursive Bisection
Allocates capital by:
1. Recursively splitting clusters into sub-clusters
2. Allocating weight between sub-clusters based on inverse variance
3. Continuing until individual assets are reached

## Key Advantages over Markowitz

| Feature | Markowitz | HRP |
|---------|-----------|-----|
| Matrix inversion required | Yes | No |
| Extreme weights | Yes | No |
| Out-of-sample stability | Poor | Good |
| Expected returns needed | Yes | No |
| Overfitting risk | High | Low |

## Usage Examples

### Basic Usage
```python
from app.engines.portfolio_engine.optimizers.hierarchical_risk_parity import compute_hrp_weights
import numpy as np

# Create covariance matrix
cov_matrix = np.cov(returns.T)

# Compute HRP weights
weights = compute_hrp_weights(cov_matrix, linkage_method='single')
```

### Using HRPOptimizer
```python
from app.engines.portfolio_engine.optimizers.hierarchical_risk_parity import HRPOptimizer

optimizer = HRPOptimizer(config={'linkage_method': 'single'})
result = optimizer.optimize(expected_returns, cov_matrix)

print(result['weights'])      # Portfolio weights
print(result['volatility'])    # Portfolio volatility
print(result['effective_n_assets'])  # Diversification metric
```

### Visualizing Dendrogram
```python
from app.engines.portfolio_engine.optimizers.hierarchical_risk_parity import plot_hrp_dendrogram

plot_hrp_dendrogram(cov_matrix, linkage_method='single', labels=asset_names)
```

## Metrics Provided

1. **Portfolio Variance/Volatility** - Risk measures
2. **Effective N Assets** - Diversification metric (1 / Herfindahl index)
3. **Max Weight** - Concentration measure
4. **Cophenetic Correlation** - Quality of clustering (higher is better)

## Test Results

All 33 tests pass successfully:
- ✅ HRP weight calculation
- ✅ All linkage methods (single, average, complete, ward)
- ✅ Quasi-diagonalization
- ✅ Recursive bisection
- ✅ Edge cases (single asset, empty matrices, etc.)
- ✅ Dendrogram generation
- ✅ Property tests (no negative weights, diversification, stability)

## Compliance with López de Prado's Rules

From `rules/trading/46-lopez-de-prado-machine-learning-asset-managers.md`:

### ✅ HRP Algorithm (Rule #2)
- [x] Hierarchical clustering of assets (correlation)
- [x] Quasi-diagonalization (reorder matrix)
- [x] Recursive bisection (allocate weights)
- [x] Risk parity within each cluster

### ✅ Linkage Methods (Rule #2)
- [x] Single linkage
- [x] Average linkage
- [x] Complete linkage
- [x] Ward linkage

### ✅ Key Advantages (Rule #2)
- [x] No matrix inversion required
- [x] No extreme weights produced
- [x] More stable out-of-sample

## Next Steps

1. **Integration with Portfolio Engine** - Connect HRP to the main portfolio optimization pipeline

2. **NCO (Nested Clustered Optimization)** - Implement the advanced method that combines HRP clustering with Markowitz optimization within clusters

3. **De-noising** - Implement Random Matrix Theory (RMT) based correlation matrix de-noising to further improve robustness

4. **Performance Comparison** - Add backtesting to compare HRP vs Markowitz vs Risk Parity

## References

- López de Prado, M. (2016). "Machine Learning for Asset Managers"
- López de Prado, M. (2018). "Advances in Financial Machine Learning"
- Paper: "Building Diversified Portfolios that Outperform Out of Sample"

---

**Implementation Date:** 2025-01-30
**Status:** ✅ Complete and tested
**Test Coverage:** 33/33 tests passing
