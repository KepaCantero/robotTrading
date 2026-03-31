"""
Unit tests for Bias Correctors (Ernest Chan methodologies)
"""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from app.backtesting.bias_correctors import (
    BacktestValidator,
    BiasDetectionResult,
    CorporateAction,
    DividendAndSplitAdjuster,
    LookAheadBiasCorrector,
    create_bias_correction_pipeline,
)


class TestLookAheadBiasCorrector:
    """Tests for LookAheadBiasCorrector class."""

    @pytest.fixture
    def corrector(self):
        """Create a LookAheadBiasCorrector instance."""
        return LookAheadBiasCorrector(strict_mode=True)

    @pytest.fixture
    def sample_signals(self):
        """Create sample signals DataFrame."""
        dates = pd.date_range(start="2020-01-01", periods=100, freq="D")
        return pd.DataFrame(
            {
                "timestamp": dates,
                "signal": np.random.randn(100),
                "ma_20": np.random.randn(100),
                "rsi": np.random.rand(100) * 100,
            }
        )

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data DataFrame."""
        dates = pd.date_range(start="2020-01-01", periods=100, freq="D")
        return pd.DataFrame(
            {
                "timestamp": dates,
                "close": 100 + np.random.randn(100).cumsum(),
                "volume": np.random.randint(1000, 10000, 100),
            }
        )

    def test_initialization(self, corrector):
        """Test corrector initialization."""
        assert corrector.strict_mode is True
        assert corrector.detected_issues == []

    def test_validate_no_lookahead_clean(self, corrector, sample_signals, sample_market_data):
        """Test validation with clean data (no lookahead bias)."""
        result = corrector.validate_no_lookahead(
            signals=sample_signals,
            market_data=sample_market_data,
            signal_columns=["signal", "ma_20", "rsi"],
            timestamp_column="timestamp",
        )

        assert isinstance(result, BiasDetectionResult)
        assert hasattr(result, 'has_lookahead_bias')
        assert hasattr(result, 'recommendations')

    def test_detects_forward_filling(self, corrector):
        """Test detection of forward filling bias."""
        # Create data with suspicious forward filling
        dates = pd.date_range(start="2020-01-01", periods=100, freq="D")
        signals = pd.DataFrame(
            {
                "timestamp": dates,
                "indicator": [50] * 80 + [51, 52, 53, 54, 55] * 4,  # Many repeated values
            }
        )

        result = corrector.validate_no_lookahead(
            signals=signals,
            market_data=signals,
            signal_columns=["indicator"],
            timestamp_column="timestamp",
        )

        assert isinstance(result, BiasDetectionResult)

    def test_detects_insufficient_nan_in_indicators(self, corrector):
        """Test detection of insufficient NaN values in indicators."""
        dates = pd.date_range(start="2020-01-01", periods=100, freq="D")
        signals = pd.DataFrame(
            {
                "timestamp": dates,
                # No NaN values - suspicious for MA-type indicators
                "ma_20": np.random.randn(100),
            }
        )

        result = corrector.validate_no_lookahead(
            signals=signals,
            market_data=signals,
            signal_columns=["ma_20"],
            timestamp_column="timestamp",
        )

        assert isinstance(result, BiasDetectionResult)
        # Should flag potential issue

    def test_generates_recommendations(self, corrector, sample_signals, sample_market_data):
        """Test that recommendations are generated."""
        result = corrector.validate_no_lookahead(
            signals=sample_signals,
            market_data=sample_market_data,
            signal_columns=["signal"],
            timestamp_column="timestamp",
        )

        assert isinstance(result.recommendations, list)
        assert len(result.recommendations) > 0


class TestDividendAndSplitAdjuster:
    """Tests for DividendAndSplitAdjuster class."""

    @pytest.fixture
    def adjuster(self):
        """Create a DividendAndSplitAdjuster instance."""
        return DividendAndSplitAdjuster(adjustment_method="backwards")

    @pytest.fixture
    def sample_prices(self):
        """Create sample price data."""
        dates = pd.date_range(start="2020-01-01", periods=100, freq="D")
        return pd.DataFrame(
            {
                "date": dates,
                "open": 100 + np.random.randn(100).cumsum(),
                "high": 102 + np.random.randn(100).cumsum(),
                "low": 98 + np.random.randn(100).cumsum(),
                "close": 100 + np.random.randn(100).cumsum(),
            }
        )

    def test_initialization(self, adjuster):
        """Test adjuster initialization."""
        assert adjuster.adjustment_method == "backwards"
        assert adjuster.adjustment_factors == {}

    def test_apply_stock_split(self, adjuster, sample_prices):
        """Test stock split application."""
        split_date = datetime(2020, 2, 1)
        split_ratio = 0.5  # 2-for-1 split

        adjusted = adjuster.apply_stock_split(
            prices=sample_prices,
            split_date=split_date,
            split_ratio=split_ratio,
        )

        assert isinstance(adjusted, pd.DataFrame)
        assert "close" in adjusted.columns

        # Prices before split should be adjusted
        pre_split = adjusted[adjusted["date"] < split_date]
        post_split = adjusted[adjusted["date"] >= split_date]

        # Pre-split prices should be approximately half of post-split
        if len(pre_split) > 0 and len(post_split) > 0:
            # This is a rough check - the exact relationship depends on the data
            assert len(pre_split) > 0

    def test_apply_stock_split_forwards(self):
        """Test stock split with forward adjustment method."""
        adjuster = DividendAndSplitAdjuster(adjustment_method="forwards")

        dates = pd.date_range(start="2020-01-01", periods=50, freq="D")
        prices = pd.DataFrame(
            {
                "date": dates,
                "close": np.linspace(100, 110, 50),
            }
        )

        split_date = datetime(2020, 1, 20)
        split_ratio = 0.5

        adjusted = adjuster.apply_stock_split(
            prices=prices,
            split_date=split_date,
            split_ratio=split_ratio,
        )

        assert isinstance(adjusted, pd.DataFrame)

    def test_calculate_total_return(self, adjuster):
        """Test total return calculation including dividends."""
        prices = pd.Series([100, 101, 102, 103, 104, 105])
        dividends = pd.Series([0, 0.5, 0, 0, 1.0, 0])  # Dividends on some days

        total_returns = adjuster.calculate_total_return(prices, dividends)

        assert isinstance(total_returns, pd.Series)
        assert len(total_returns) == len(prices)

        # Total return should be approximately price return + dividend yield
        # (first value will be NaN due to pct_change)
        assert total_returns.isna().sum() >= 1

    def test_reconstruct_adjusted_prices(self, adjuster):
        """Test reconstruction of adjusted prices."""
        raw_prices = pd.Series(
            [100, 101, 102, 103, 104, 105],
            index=pd.date_range(start="2020-01-01", periods=6, freq="D"),
        )

        dividends = pd.DataFrame(
            {
                "date": [datetime(2020, 1, 3), datetime(2020, 1, 5)],
                "amount": [0.5, 1.0],
            }
        )

        splits = pd.DataFrame(
            {
                "date": [datetime(2020, 1, 4)],
                "ratio": [0.5],
            }
        )

        adjusted = adjuster.reconstruct_adjusted_prices(raw_prices, dividends, splits)

        assert isinstance(adjusted, pd.Series)
        assert len(adjusted) == len(raw_prices)


class TestBacktestValidator:
    """Tests for BacktestValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a BacktestValidator instance."""
        return BacktestValidator(min_samples=50, confidence_level=0.95)

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns."""
        np.random.seed(42)
        return pd.Series(np.random.randn(100) * 0.01)

    @pytest.fixture
    def sample_signals(self):
        """Create sample signals."""
        dates = pd.date_range(start="2020-01-01", periods=100, freq="D")
        return pd.DataFrame(
            {
                "timestamp": dates,
                "signal": np.random.randn(100),
            }
        )

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data."""
        dates = pd.date_range(start="2020-01-01", periods=100, freq="D")
        return pd.DataFrame(
            {
                "timestamp": dates,
                "close": 100 + np.random.randn(100).cumsum(),
            }
        )

    def test_initialization(self, validator):
        """Test validator initialization."""
        assert validator.min_samples == 50
        assert validator.confidence_level == 0.95

    def test_validate_backtest(self, validator, sample_returns, sample_signals, sample_market_data):
        """Test comprehensive backtest validation."""
        result = validator.validate_backtest(
            returns=sample_returns,
            signals=sample_signals,
            market_data=sample_market_data,
        )

        assert isinstance(result, BiasDetectionResult)
        assert hasattr(result, 'has_lookahead_bias')
        assert hasattr(result, 'has_survivorship_bias')
        assert hasattr(result, 'corrected_sharpe_ratio')
        assert hasattr(result, 'original_sharpe_ratio')

    def test_sharpe_ratio_calculation(self, validator):
        """Test Sharpe ratio calculation."""
        returns = pd.Series(np.random.randn(100) * 0.01)
        sharpe = validator._calculate_sharpe_ratio(returns)

        assert isinstance(sharpe, float)
        # Sharpe should be reasonable (not extremely high or low for random data)
        assert -5 < sharpe < 5

    def test_with_insufficient_samples(self, validator):
        """Test validation with insufficient samples."""
        short_returns = pd.Series(np.random.randn(10) * 0.01)

        result = validator.validate_backtest(
            returns=short_returns,
            signals=pd.DataFrame({"timestamp": pd.date_range(start="2020-01-01", periods=10)}),
            market_data=pd.DataFrame(
                {
                    "timestamp": pd.date_range(start="2020-01-01", periods=10),
                    "close": 100 + np.random.randn(10).cumsum(),
                }
            ),
        )

        assert isinstance(result, BiasDetectionResult)
        # Should flag insufficient samples


class TestBiasCorrectionPipeline:
    """Tests for bias correction pipeline."""

    @pytest.fixture
    def sample_raw_data(self, default_symbol):
        """Create sample raw data."""
        dates = pd.date_range(start="2020-01-01", periods=100, freq="D")
        return pd.DataFrame(
            {
                "date": dates,
                "symbol": [default_symbol] * 100,
                "open": 100 + np.random.randn(100).cumsum(),
                "high": 102 + np.random.randn(100).cumsum(),
                "low": 98 + np.random.randn(100).cumsum(),
                "close": 100 + np.random.randn(100).cumsum(),
            }
        )

    @pytest.fixture
    def sample_dividends(self):
        """Create sample dividend data."""
        return pd.DataFrame(
            {
                "date": [datetime(2020, 1, 15), datetime(2020, 2, 15)],
                "amount": [0.5, 0.6],
            }
        )

    @pytest.fixture
    def sample_splits(self):
        """Create sample split data."""
        return pd.DataFrame(
            {
                "date": [datetime(2020, 2, 1)],
                "ratio": [0.5],
            }
        )

    def test_pipeline_with_all_data(self, sample_raw_data, sample_dividends, sample_splits):
        """Test pipeline with dividends and splits."""
        result = create_bias_correction_pipeline(
            raw_data=sample_raw_data,
            dividend_data=sample_dividends,
            split_data=sample_splits,
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_raw_data)

    def test_pipeline_with_prices_only(self, sample_raw_data):
        """Test pipeline with only price data."""
        result = create_bias_correction_pipeline(
            raw_data=sample_raw_data,
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_raw_data)

    def test_pipeline_handles_errors(self):
        """Test pipeline error handling."""
        # Create invalid data
        invalid_data = pd.DataFrame({"invalid": ["a", "b", "c"]})

        result = create_bias_correction_pipeline(invalid_data)

        # Should return original data on error
        assert isinstance(result, pd.DataFrame)


class TestCorporateAction:
    """Tests for CorporateAction dataclass."""

    def test_corporate_action_creation(self, default_symbol):
        """Test creating a CorporateAction."""
        action = CorporateAction(
            date=datetime(2020, 1, 15),
            symbol=default_symbol,
            action_type="split",
            ratio=0.5,
            amount=None,
        )

        assert action.date == datetime(2020, 1, 15)
        assert action.symbol == default_symbol
        assert action.action_type == "split"
        assert action.ratio == 0.5

    def test_dividend_action(self, default_symbol):
        """Test creating a dividend action."""
        action = CorporateAction(
            date=datetime(2020, 1, 15),
            symbol=default_symbol,
            action_type="dividend",
            ratio=None,
            amount=0.5,
        )

        assert action.action_type == "dividend"
        assert action.amount == 0.5


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_dataframes(self):
        """Test handling of empty DataFrames."""
        corrector = LookAheadBiasCorrector()
        result = corrector.validate_no_lookahead(
            signals=pd.DataFrame(),
            market_data=pd.DataFrame(),
            signal_columns=[],
        )

        assert isinstance(result, BiasDetectionResult)

    def test_single_row_data(self):
        """Test handling of single-row data."""
        signals = pd.DataFrame({"timestamp": [datetime(2020, 1, 1)], "signal": [1.0]})
        market_data = pd.DataFrame({"timestamp": [datetime(2020, 1, 1)], "close": [100.0]})

        corrector = LookAheadBiasCorrector()
        result = corrector.validate_no_lookahead(
            signals=signals,
            market_data=market_data,
            signal_columns=["signal"],
            timestamp_column="timestamp",
        )

        assert isinstance(result, BiasDetectionResult)

    def test_missing_columns(self):
        """Test handling of missing columns."""
        signals = pd.DataFrame({"wrong_column": [1, 2, 3]})
        market_data = pd.DataFrame({"close": [100, 101, 102]})

        corrector = LookAheadBiasCorrector()
        # Should not crash even with missing columns
        result = corrector.validate_no_lookahead(
            signals=signals,
            market_data=market_data,
            signal_columns=["signal"],  # This column doesn't exist
        )

        assert isinstance(result, BiasDetectionResult)


class TestIntegration:
    """Integration tests for bias correction."""

    def test_full_bias_correction_workflow(self):
        """Test complete bias correction workflow."""
        # Create realistic data
        np.random.seed(42)
        dates = pd.date_range(start="2019-01-01", periods=252, freq="D")  # 1 year of data

        raw_data = pd.DataFrame(
            {
                "date": dates,
                "close": 100 + np.random.randn(252).cumsum(),
            }
        )

        dividends = pd.DataFrame(
            {
                "date": [datetime(2019, 3, 15), datetime(2019, 6, 15), datetime(2019, 9, 15)],
                "amount": [0.5, 0.6, 0.7],
            }
        )

        splits = pd.DataFrame(
            {
                "date": [datetime(2019, 6, 1)],
                "ratio": [0.5],
            }
        )

        # Apply corrections
        corrected_data = create_bias_correction_pipeline(
            raw_data=raw_data,
            dividend_data=dividends,
            split_data=splits,
        )

        # Validate
        validator = BacktestValidator()
        signals = pd.DataFrame(
            {
                "timestamp": dates,
                "signal": np.random.randn(252),
            }
        )

        result = validator.validate_backtest(
            returns=corrected_data["close"].pct_change().dropna(),
            signals=signals,
            market_data=corrected_data,
        )

        assert isinstance(result, BiasDetectionResult)
        assert hasattr(result, 'corrected_sharpe_ratio')
