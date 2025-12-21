"""
Tests for RegimeAnalyzer - regime detection and analysis.

Tests all 4 main methods with various market scenarios:
- Regime detection (Bull/Neutral/Bear)
- Performance analysis by regime
- Transition analysis
- Walk-forward robustness
"""

import numpy as np
import pandas as pd
import pytest

from app.backtesting.regime_analyzer import RegimeAnalyzer


class TestRegimeAnalyzer:
    """Tests for RegimeAnalyzer class."""

    @pytest.fixture
    def analyzer(self) -> RegimeAnalyzer:
        """Create RegimeAnalyzer instance."""
        return RegimeAnalyzer(n_regimes=3, window=20, random_state=42)

    @pytest.fixture
    def sample_returns(self) -> pd.Series:
        """Create sample returns series with datetime index."""
        np.random.seed(42)
        dates = pd.date_range(start="2023-01-01", periods=252, freq="B")  # 1 year
        returns = np.random.normal(0.001, 0.02, 252)
        return pd.Series(returns, index=dates, name="returns")

    @pytest.fixture
    def bull_market_returns(self) -> pd.Series:
        """Create synthetic bull market returns."""
        dates = pd.date_range(start="2023-01-01", periods=252, freq="B")
        # Bull market: positive drift, low volatility
        returns = np.random.normal(0.002, 0.01, 252)
        return pd.Series(returns, index=dates, name="returns")

    @pytest.fixture
    def bear_market_returns(self) -> pd.Series:
        """Create synthetic bear market returns."""
        dates = pd.date_range(start="2023-01-01", periods=252, freq="B")
        # Bear market: negative drift, high volatility
        returns = np.random.normal(-0.001, 0.025, 252)
        return pd.Series(returns, index=dates, name="returns")

    @pytest.fixture
    def mixed_market_returns(self) -> pd.Series:
        """Create returns with mixed market regimes."""
        dates = pd.date_range(start="2023-01-01", periods=756, freq="B")  # 3 years
        # 1 year bull, 1 year sideways, 1 year bear
        bull = np.random.normal(0.002, 0.01, 252)
        neutral = np.random.normal(0.0001, 0.015, 252)
        bear = np.random.normal(-0.001, 0.025, 252)
        returns = np.concatenate([bull, neutral, bear])
        return pd.Series(returns, index=dates, name="returns")

    # Tests for detect_regimes
    def test_detect_regimes_basic(self, analyzer: RegimeAnalyzer, sample_returns: pd.Series):
        """Test basic regime detection."""
        regimes = analyzer.detect_regimes(sample_returns)

        assert regimes is not None
        assert len(regimes) == len(sample_returns)
        assert regimes.index.equals(sample_returns.index)
        assert regimes.min() >= 0
        assert regimes.max() < analyzer.n_regimes

    def test_detect_regimes_output_series(self, analyzer: RegimeAnalyzer, sample_returns: pd.Series):
        """Test regime detection returns Series."""
        regimes = analyzer.detect_regimes(sample_returns)

        assert isinstance(regimes, pd.Series)
        assert regimes.name == "regime"
        assert len(regimes) == len(sample_returns)

    def test_detect_regimes_stores_labels(self, analyzer: RegimeAnalyzer, sample_returns: pd.Series):
        """Test that detected regimes are stored internally."""
        regimes = analyzer.detect_regimes(sample_returns)

        stored_labels = analyzer.get_regime_labels()
        assert stored_labels is not None
        assert stored_labels.equals(regimes)

    def test_detect_regimes_insufficient_data(self, analyzer: RegimeAnalyzer):
        """Test regime detection with insufficient data."""
        short_returns = pd.Series(np.random.normal(0, 0.02, 10))
        regimes = analyzer.detect_regimes(short_returns)

        assert regimes is not None
        assert len(regimes) == 10

    def test_detect_regimes_bull_market(self, analyzer: RegimeAnalyzer, bull_market_returns: pd.Series):
        """Test regime detection on bull market data."""
        regimes = analyzer.detect_regimes(bull_market_returns)

        assert regimes is not None
        # Should detect regimes (mix of states)
        unique_regimes = len(regimes.unique())
        assert 1 <= unique_regimes <= analyzer.n_regimes

    def test_detect_regimes_bear_market(self, analyzer: RegimeAnalyzer, bear_market_returns: pd.Series):
        """Test regime detection on bear market data."""
        regimes = analyzer.detect_regimes(bear_market_returns)

        assert regimes is not None
        # Should detect regimes (mix of states)
        unique_regimes = len(regimes.unique())
        assert 1 <= unique_regimes <= analyzer.n_regimes

    def test_detect_regimes_reproducibility(
        self, analyzer: RegimeAnalyzer, sample_returns: pd.Series
    ):
        """Test that regime detection is reproducible with same random_state."""
        regimes1 = analyzer.detect_regimes(sample_returns)

        # Create new analyzer with same random_state
        analyzer2 = RegimeAnalyzer(n_regimes=3, window=20, random_state=42)
        regimes2 = analyzer2.detect_regimes(sample_returns)

        assert regimes1.equals(regimes2)

    def test_detect_regimes_different_window(self, analyzer: RegimeAnalyzer, sample_returns: pd.Series):
        """Test regime detection with different window size."""
        analyzer_large_window = RegimeAnalyzer(n_regimes=3, window=50, random_state=42)
        regimes = analyzer_large_window.detect_regimes(sample_returns)

        assert regimes is not None
        assert len(regimes) == len(sample_returns)

    # Tests for analyze_regime_performance
    def test_analyze_regime_performance_basic(
        self, analyzer: RegimeAnalyzer, sample_returns: pd.Series
    ):
        """Test basic regime performance analysis."""
        regimes = analyzer.detect_regimes(sample_returns)
        analysis = analyzer.analyze_regime_performance(sample_returns, regimes)

        assert isinstance(analysis, dict)
        assert len(analysis) > 0
        # Should have multiple regimes
        assert len(analysis) <= analyzer.n_regimes

    def test_analyze_regime_performance_metrics(
        self, analyzer: RegimeAnalyzer, sample_returns: pd.Series
    ):
        """Test that regime analysis includes all metrics."""
        regimes = analyzer.detect_regimes(sample_returns)
        analysis = analyzer.analyze_regime_performance(sample_returns, regimes)

        for regime_name, metrics in analysis.items():
            assert "periods" in metrics
            assert "pct_time" in metrics
            assert "total_return" in metrics
            assert "annualized_return" in metrics
            assert "volatility" in metrics
            assert "sharpe_ratio" in metrics
            assert "max_drawdown" in metrics
            assert "win_rate" in metrics

    def test_analyze_regime_performance_values(
        self, analyzer: RegimeAnalyzer, sample_returns: pd.Series
    ):
        """Test that regime metrics have reasonable values."""
        regimes = analyzer.detect_regimes(sample_returns)
        analysis = analyzer.analyze_regime_performance(sample_returns, regimes)

        for regime_name, metrics in analysis.items():
            assert 0 <= metrics["win_rate"] <= 1
            assert metrics["periods"] > 0
            assert 0 <= metrics["pct_time"] <= 100
            assert metrics["volatility"] >= 0

    def test_analyze_regime_performance_bull_better_sharpe(
        self, analyzer: RegimeAnalyzer, mixed_market_returns: pd.Series
    ):
        """Test that Bull regime has better Sharpe ratio than Bear."""
        regimes = analyzer.detect_regimes(mixed_market_returns)
        analysis = analyzer.analyze_regime_performance(mixed_market_returns, regimes)

        bull_sharpe = analysis.get("Bull", {}).get("sharpe_ratio", -999)
        bear_sharpe = analysis.get("Bear", {}).get("sharpe_ratio", 999)

        # Bull should have better (higher) Sharpe than Bear
        assert bull_sharpe > bear_sharpe

    def test_analyze_regime_performance_default_labels(self, analyzer: RegimeAnalyzer, sample_returns: pd.Series):
        """Test regime analysis uses stored labels by default."""
        analyzer.detect_regimes(sample_returns)
        analysis = analyzer.analyze_regime_performance(sample_returns)

        assert isinstance(analysis, dict)
        assert len(analysis) > 0

    def test_analyze_regime_performance_mismatched_lengths(
        self, analyzer: RegimeAnalyzer, sample_returns: pd.Series
    ):
        """Test regime analysis with mismatched lengths."""
        wrong_regimes = pd.Series([0, 1, 2] * 50)  # Only 150 elements
        analysis = analyzer.analyze_regime_performance(sample_returns, wrong_regimes)

        assert analysis == {}

    # Tests for regime_transition_analysis
    def test_regime_transition_analysis_basic(
        self, analyzer: RegimeAnalyzer, sample_returns: pd.Series
    ):
        """Test basic regime transition analysis."""
        regimes = analyzer.detect_regimes(sample_returns)
        transitions = analyzer.regime_transition_analysis(regimes)

        assert isinstance(transitions, dict)
        assert "transition_matrix" in transitions
        assert "transition_probabilities" in transitions
        assert "regime_names" in transitions
        assert "duration_statistics" in transitions

    def test_regime_transition_matrix_properties(
        self, analyzer: RegimeAnalyzer, sample_returns: pd.Series
    ):
        """Test transition matrix has correct properties."""
        regimes = analyzer.detect_regimes(sample_returns)
        transitions = analyzer.regime_transition_analysis(regimes)

        trans_matrix = np.array(transitions["transition_matrix"])
        trans_probs = np.array(transitions["transition_probabilities"])

        # Check dimensions
        assert trans_matrix.shape == (analyzer.n_regimes, analyzer.n_regimes)
        assert trans_probs.shape == (analyzer.n_regimes, analyzer.n_regimes)

        # Check probabilities sum to 1 (except for regimes with 0 transitions)
        for row in trans_probs:
            row_sum = row.sum()
            if row_sum > 0:
                assert np.isclose(row_sum, 1.0, atol=1e-6)

    def test_regime_transition_duration_statistics(
        self, analyzer: RegimeAnalyzer, sample_returns: pd.Series
    ):
        """Test transition analysis includes duration statistics."""
        regimes = analyzer.detect_regimes(sample_returns)
        transitions = analyzer.regime_transition_analysis(regimes)

        duration_stats = transitions.get("duration_statistics", {})
        assert len(duration_stats) > 0

        for regime_name, stats in duration_stats.items():
            assert "mean_duration" in stats
            assert "median_duration" in stats
            assert "min_duration" in stats
            assert "max_duration" in stats
            assert "transitions" in stats
            assert stats["max_duration"] >= stats["min_duration"]

    def test_regime_transition_insufficient_data(self, analyzer: RegimeAnalyzer):
        """Test regime transition analysis with insufficient data."""
        short_regimes = pd.Series([0, 1])
        transitions = analyzer.regime_transition_analysis(short_regimes)

        # Should return either empty dict or handle gracefully
        assert isinstance(transitions, dict)
        # If not empty, should have required keys or be minimal
        if transitions:
            assert "transition_matrix" in transitions or len(transitions) < 3

    def test_regime_transition_regime_names(
        self, analyzer: RegimeAnalyzer, sample_returns: pd.Series
    ):
        """Test that regime names are correct."""
        regimes = analyzer.detect_regimes(sample_returns)
        transitions = analyzer.regime_transition_analysis(regimes)

        regime_names = transitions.get("regime_names", [])
        assert len(regime_names) <= analyzer.n_regimes
        assert all(isinstance(name, (str, int)) for name in regime_names)

    # Tests for out_of_sample_regime_robustness
    def test_out_of_sample_robustness_basic(
        self, analyzer: RegimeAnalyzer, mixed_market_returns: pd.Series
    ):
        """Test basic out-of-sample robustness analysis."""
        robustness = analyzer.out_of_sample_regime_robustness(
            mixed_market_returns, test_periods=3, train_window=252
        )

        assert isinstance(robustness, dict)
        assert "test_periods" in robustness
        assert "train_window" in robustness
        assert "period_results" in robustness

    def test_out_of_sample_robustness_metrics(
        self, analyzer: RegimeAnalyzer, mixed_market_returns: pd.Series
    ):
        """Test robustness analysis includes all metrics."""
        robustness = analyzer.out_of_sample_regime_robustness(
            mixed_market_returns, test_periods=3, train_window=252
        )

        if robustness and robustness["period_results"]:
            assert "avg_return" in robustness
            assert "std_return" in robustness
            assert "consistency" in robustness

    def test_out_of_sample_robustness_period_results(
        self, analyzer: RegimeAnalyzer, mixed_market_returns: pd.Series
    ):
        """Test that period results have required fields."""
        robustness = analyzer.out_of_sample_regime_robustness(
            mixed_market_returns, test_periods=3, train_window=252
        )

        for period_result in robustness.get("period_results", []):
            assert "period" in period_result
            assert "test_return" in period_result
            assert "test_volatility" in period_result
            assert "test_sharpe" in period_result

    def test_out_of_sample_robustness_insufficient_data(self, analyzer: RegimeAnalyzer):
        """Test robustness with insufficient data."""
        short_returns = pd.Series(np.random.normal(0, 0.02, 100))
        robustness = analyzer.out_of_sample_regime_robustness(short_returns, test_periods=5, train_window=252)

        assert robustness == {}

    def test_out_of_sample_robustness_different_periods(
        self, analyzer: RegimeAnalyzer, mixed_market_returns: pd.Series
    ):
        """Test robustness with different number of periods."""
        robustness_2 = analyzer.out_of_sample_regime_robustness(
            mixed_market_returns, test_periods=2, train_window=252
        )
        robustness_5 = analyzer.out_of_sample_regime_robustness(
            mixed_market_returns, test_periods=5, train_window=252
        )

        assert robustness_2["test_periods"] == 2
        assert robustness_5["test_periods"] <= 5  # May be adjusted based on data

    # Integration tests
    def test_full_workflow(self, analyzer: RegimeAnalyzer, mixed_market_returns: pd.Series):
        """Test complete workflow from detection to analysis."""
        # Detect regimes
        regimes = analyzer.detect_regimes(mixed_market_returns)
        assert regimes is not None

        # Analyze performance
        performance = analyzer.analyze_regime_performance(mixed_market_returns, regimes)
        assert len(performance) > 0

        # Analyze transitions
        transitions = analyzer.regime_transition_analysis(regimes)
        assert "transition_matrix" in transitions

        # Robustness test
        robustness = analyzer.out_of_sample_regime_robustness(mixed_market_returns, test_periods=2, train_window=252)
        assert isinstance(robustness, dict)

    def test_get_regime_names(self, analyzer: RegimeAnalyzer):
        """Test regime name mapping."""
        names = analyzer.get_regime_names()

        assert isinstance(names, dict)
        assert 0 in names
        assert 1 in names
        assert 2 in names
        assert names[0] == "Bear Market"
        assert names[1] == "Neutral Market"
        assert names[2] == "Bull Market"

    def test_analyzer_attributes(self, analyzer: RegimeAnalyzer):
        """Test analyzer has correct attributes."""
        assert analyzer.n_regimes == 3
        assert analyzer.window == 20
        assert analyzer.random_state == 42

    def test_multiple_detections(self, analyzer: RegimeAnalyzer, sample_returns: pd.Series):
        """Test multiple regime detections overwrite previous."""
        # First detection
        regimes1 = analyzer.detect_regimes(sample_returns)
        assert analyzer.get_regime_labels() is not None

        # Second detection (different data)
        returns2 = sample_returns * 2
        regimes2 = analyzer.detect_regimes(returns2)

        # Should have stored the second detection
        stored = analyzer.get_regime_labels()
        assert stored.equals(regimes2)

    def test_regime_consistency_across_calls(
        self, analyzer: RegimeAnalyzer, sample_returns: pd.Series
    ):
        """Test regime detection consistency."""
        regimes1 = analyzer.detect_regimes(sample_returns)

        # Analysis should work with same regimes
        analysis1 = analyzer.analyze_regime_performance(sample_returns, regimes1)
        analysis2 = analyzer.analyze_regime_performance(sample_returns, regimes1)

        assert analysis1 == analysis2

    def test_regime_edge_case_constant_returns(self, analyzer: RegimeAnalyzer):
        """Test regime detection with constant returns."""
        constant_returns = pd.Series([0.001] * 252)
        regimes = analyzer.detect_regimes(constant_returns)

        assert regimes is not None
        assert len(regimes) == 252

    def test_regime_edge_case_extreme_volatility(self, analyzer: RegimeAnalyzer):
        """Test regime detection with extreme volatility."""
        extreme_returns = pd.Series(np.random.normal(0, 0.1, 252))  # 10% daily std
        regimes = analyzer.detect_regimes(extreme_returns)

        assert regimes is not None
        assert len(regimes) == 252

    def test_large_dataset_handling(self, analyzer: RegimeAnalyzer):
        """Test handling of large dataset."""
        large_returns = pd.Series(np.random.normal(0.001, 0.02, 5000))  # 20 years of data
        regimes = analyzer.detect_regimes(large_returns)

        assert regimes is not None
        assert len(regimes) == 5000

    def test_regime_numeric_consistency(self, analyzer: RegimeAnalyzer, sample_returns: pd.Series):
        """Test regime labels are properly numeric."""
        regimes = analyzer.detect_regimes(sample_returns)

        assert regimes.dtype in [np.int32, np.int64, int]
        for regime in regimes.unique():
            assert isinstance(int(regime), int)
            assert 0 <= regime < analyzer.n_regimes
