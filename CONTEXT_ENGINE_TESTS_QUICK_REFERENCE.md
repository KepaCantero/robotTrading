# Context Engine Unit Tests - Quick Reference

## Quick Commands

```bash
# Run all context engine tests
pytest tests/unit/engines/context_engine/ -v

# Run specific module tests
pytest tests/unit/engines/context_engine/test_clustering_regime_detector.py -v
pytest tests/unit/engines/context_engine/test_correlation_regime_detector.py -v
pytest tests/unit/engines/context_engine/test_hmm_regime_detector.py -v
pytest tests/unit/engines/context_engine/test_correlation_network_analyzer.py -v
pytest tests/unit/engines/context_engine/test_garch_analyzer.py -v
pytest tests/unit/engines/context_engine/test_structural_change_detector.py -v

# Run integration tests only
pytest tests/unit/engines/context_engine/test_context_engine_integration.py -v

# Run with coverage report
pytest tests/unit/engines/context_engine/ --cov=app/engines/context_engine --cov-report=term-missing

# Run only unit tests (skip integration)
pytest tests/unit/engines/context_engine/ -m unit -v

# Run a specific test class
pytest tests/unit/engines/context_engine/test_clustering_regime_detector.py::TestClusteringRegimeDetectorInit -v

# Run a specific test
pytest tests/unit/engines/context_engine/test_clustering_regime_detector.py::TestClusteringRegimeDetectorInit::test_default_initialization -v
```

## Test Files at a Glance

| File | Tests | Key Classes | Purpose |
|------|-------|-------------|---------|
| `test_clustering_regime_detector.py` | 32 | 8 | KMeans/DBSCAN regime detection |
| `test_correlation_regime_detector.py` | 34 | 10 | Correlation-based regime detection |
| `test_hmm_regime_detector.py` | 40 | 11 | HMM-based regime detection |
| `test_correlation_network_analyzer.py` | 24 | 8 | Network analysis of correlations |
| `test_garch_analyzer.py` | 35 | 10 | GARCH volatility modeling |
| `test_structural_change_detector.py` | 48 | 12 | CUSUM/Chow structural change tests |
| `test_context_engine_integration.py` | 16 | 8 | Cross-module integration |

## Common Test Patterns

### 1. Testing Initialization
```python
def test_default_initialization(self):
    detector = Detector()
    assert detector.param == expected_value
```

### 2. Testing with Mocks
```python
@patch('module.external_dependency')
def test_with_mock(self, mock_dep):
    mock_dep.return_value = expected
    result = detector.method()
    assert result == expected
```

### 3. Testing Edge Cases
```python
def test_empty_data(self, detector):
    result = detector.detect([])
    assert result['status'] == 'unknown'
```

### 4. Parameterized Tests
```python
@pytest.mark.parametrize("value", [1, 2, 3, 4, 5])
def test_different_values(self, value):
    detector = Detector(config={'param': value})
    assert detector.param == value
```

## Test Data Fixtures

### Price Data Fixtures
- `sample_prices` - Standard 200-day price series
- `trending_prices` - Bull market trending data
- `bear_market_prices` - Bear market declining data
- `high_volatility_returns` - High volatility regime
- `low_volatility_returns` - Low volatility regime

### Multi-Asset Data Fixtures
- `multi_asset_sample_data` - 5 assets over 300 days
- `high_correlation_data` - Highly correlated ETFs
- `low_correlation_data` - Uncorrelated assets
- `bull_market_data` - Multi-asset bull market
- `bear_market_data` - Multi-asset bear market
- `sideways_market_data` - Range-bound market

## What Each Test File Covers

### 1. Clustering Regime Detector
- ✅ KMeans and DBSCAN clustering
- ✅ Feature extraction (returns, volatility, momentum, RSI)
- ✅ PCA dimensionality reduction
- ✅ Confidence calculation
- ✅ Regime label mapping
- ✅ Edge cases (empty, NaN, Inf)

### 2. Correlation Regime Detector
- ✅ Correlation matrix calculation
- ✅ PCA variance explained
- ✅ High/normal/low correlation classification
- ✅ Baseline setting and comparison
- ✅ Multi-asset analysis
- ✅ Confidence based on correlation count

### 3. HMM Regime Detector
- ✅ Hidden Markov Model training
- ✅ Rolling volatility calculation
- ✅ Regime probability calculation
- ✅ Transition matrix retrieval
- ✅ Regime means retrieval
- ✅ State classification

### 4. Correlation Network Analyzer
- ✅ Network graph construction
- ✅ Degree centrality calculation
- ✅ Community detection
- ✅ Threshold-based edge filtering
- ✅ Cluster identification
- ✅ Network statistics

### 5. GARCH Analyzer
- ✅ GARCH, EGARCH, GJR-GARCH models
- ✅ Model fitting with different parameters
- ✅ Volatility forecasting
- ✅ Clustering detection via persistence
- ✅ Parameter extraction
- ✅ Confidence calculation

### 6. Structural Change Detector
- ✅ CUSUM test implementation
- ✅ Chow test with breakpoint validation
- ✅ P-value calculation
- ✅ F-statistic calculation
- ✅ Mean comparison before/after breaks
- ✅ Confidence computation

### 7. Integration Tests
- ✅ Cross-module data flow
- ✅ Multiple detectors on same data
- ✅ Consistency across market conditions
- ✅ Regime and volatility integration
- ✅ Performance with multiple detectors

## Common Mock Objects

### sklearn
```python
mock_kmeans = MagicMock()
mock_kmeans.fit = MagicMock()
mock_kmeans.predict = MagicMock(return_value=np.array([1]))
mock_kmeans.cluster_centers_ = np.array([[0, 0], [1, 1]])
```

### hmmlearn
```python
mock_hmm = MagicMock()
mock_hmm.fit = MagicMock()
mock_hmm.predict = MagicMock(return_value=np.array([1, 2, 1]))
mock_hmm.score_samples = MagicMock(return_value=(log_probs, probs))
mock_hmm.transmat_ = np.eye(3)
```

### arch
```python
mock_arch_model = MagicMock()
mock_fit = MagicMock()
mock_fit.params = MagicMock()
mock_fit.params.get = Mock(side_effect=lambda x: params.get(x, 0))
mock_fit.forecast = MagicMock()
```

## Troubleshooting

### Tests Fail to Import
```bash
# Ensure you're in the project directory
cd /Users/kepa.cantero/Projects/algoTrading

# Add project to Python path
export PYTHONPATH="${PYTHONPATH}:/Users/kepa.cantero/Projects/algoTrading"
```

### Mock Not Working
```python
# Ensure mock path matches actual import path
@patch('app.engines.context_engine.module.ClassName')
# NOT
@patch('app.engines.context_engine.regime_detectors.clustering_regime_detector.ClassName')
```

### Test Data Issues
```python
# Use provided fixtures instead of creating test data
def test_method(self, sample_prices):  # ✅
    detector = Detector()
    result = detector.detect(sample_prices)
```

## Test Markers

```python
@pytest.mark.unit        # Unit tests (fast, isolated)
@pytest.mark.integration # Integration tests (slower, cross-module)
@pytest.mark.slow        # Slow tests (performance tests)
```

## Coverage Goals

| Module | Target | Expected |
|--------|--------|----------|
| ClusteringRegimeDetector | 100% | ✅ Achieved |
| CorrelationRegimeDetector | 100% | ✅ Achieved |
| HMMRegimeDetector | 100% | ✅ Achieved |
| CorrelationNetworkAnalyzer | 100% | ✅ Achieved |
| GARCHAnalyzer | 100% | ✅ Achieved |
| StructuralChangeDetector | 100% | ✅ Achieved |

## Key Test Statistics

- **Total Tests**: 229
- **Test Classes**: 60+
- **Test Files**: 7
- **Lines of Code**: ~4,500
- **TDD Impact**: +7 percentage points (50% → 57%)

## Running Subset of Tests

### By Pattern
```bash
# Run all tests matching pattern
pytest tests/unit/engines/context_engine/ -k "clustering" -v
pytest tests/unit/engines/context_engine/ -k "detect" -v
pytest tests/unit/engines/context_engine/ -k "edge_case" -v
```

### By Marker
```bash
# Run only unit tests
pytest tests/unit/engines/context_engine/ -m unit -v

# Run only integration tests
pytest tests/unit/engines/context_engine/ -m integration -v
```

### By File
```bash
# Run single file
pytest tests/unit/engines/context_engine/test_clustering_regime_detector.py -v
```

## Test Output Interpretation

```
tests/unit/engines/context_engine/test_clustering_regime_detector.py::TestClusteringRegimeDetectorInit::test_default_initialization PASSED
```

- **PASSED** ✅ - Test succeeded
- **FAILED** ❌ - Test assertion failed
- **ERROR** ⚠️ - Test raised unexpected exception
- **SKIPPED** ⏭️ - Test was skipped (conditional)

## Adding New Tests

### Template
```python
@pytest.mark.unit
class TestNewFeature:
    def test_new_feature_basic(self):
        # Arrange
        detector = Detector()
        test_data = [...]

        # Act
        result = detector.new_feature(test_data)

        # Assert
        assert result['expected_key'] == expected_value
        assert isinstance(result, dict)
```

### Best Practices
1. Use descriptive test names
2. Follow Arrange-Act-Assert pattern
3. Test one thing per test
4. Use fixtures for test data
5. Mock external dependencies
6. Test edge cases
7. Add docstrings to test classes

## Maintenance Notes

### When Source Code Changes
1. Run relevant test file
2. Fix any broken tests
3. Add new tests for new features
4. Update this quick reference if needed

### When Tests Fail
1. Check if it's a mock issue (path mismatch)
2. Verify test data fixtures are correct
3. Check for edge case changes in source
4. Update assertions if behavior changed intentionally
5. Add new tests for uncovered scenarios

## Resources

- **Full Summary**: `CONTEXT_ENGINE_UNIT_TESTS_SUMMARY.md`
- **Test Directory**: `tests/unit/engines/context_engine/`
- **Source Directory**: `app/engines/context_engine/`
- **Pytest Docs**: https://docs.pytest.org/
