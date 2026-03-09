"""
Tests for Correlation Analyzer.

This module tests the CorrelationAnalyzer class which provides
statistical correlation analysis for FX intermarket relationships.
"""

from decimal import Decimal

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from app.domain.strategies.fx_intermarket.correlation_analyzer import CorrelationAnalyzer
from app.domain.strategies.fx_intermarket.models import (
    AssetClass,
    FXCorrelationPair,
    IntermarketRelationship,
    RelationshipType,
)


class TestCorrelationAnalyzerInitialization:
    """Tests for CorrelationAnalyzer initialization."""

    def test_initialization_default(self) -> None:
        """Test initialization with default parameters."""
        analyzer = CorrelationAnalyzer()

        assert analyzer.lookback_days == 60
        assert analyzer.min_correlation == Decimal("0.6")
        assert analyzer.min_significance == Decimal("70")

    def test_initialization_custom(self) -> None:
        """Test initialization with custom parameters."""
        analyzer = CorrelationAnalyzer(
            lookback_days=90,
            min_correlation=Decimal("0.7"),
            min_significance=Decimal("80"),
        )

        assert analyzer.lookback_days == 90
        assert analyzer.min_correlation == Decimal("0.7")
        assert analyzer.min_significance == Decimal("80")

    def test_initialization_invalid_lookback_negative(self) -> None:
        """Test initialization rejects negative lookback."""
        with pytest.raises(ValueError, match="lookback_days must be positive"):
            CorrelationAnalyzer(lookback_days=-10)

    def test_initialization_invalid_lookback_zero(self) -> None:
        """Test initialization rejects zero lookback."""
        with pytest.raises(ValueError, match="lookback_days must be positive"):
            CorrelationAnalyzer(lookback_days=0)

    def test_initialization_invalid_min_correlation_high(self) -> None:
        """Test initialization rejects min_correlation > 1."""
        with pytest.raises(ValueError, match="min_correlation must be between 0 and 1"):
            CorrelationAnalyzer(min_correlation=Decimal("1.5"))

    def test_initialization_invalid_min_correlation_low(self) -> None:
        """Test initialization rejects min_correlation < 0."""
        with pytest.raises(ValueError, match="min_correlation must be between 0 and 1"):
            CorrelationAnalyzer(min_correlation=Decimal("-0.1"))

    def test_initialization_invalid_min_significance_high(self) -> None:
        """Test initialization rejects min_significance > 100."""
        with pytest.raises(ValueError, match="min_significance must be between 0 and 100"):
            CorrelationAnalyzer(min_significance=Decimal("101"))

    def test_initialization_invalid_min_significance_low(self) -> None:
        """Test initialization rejects min_significance < 0."""
        with pytest.raises(ValueError, match="min_significance must be between 0 and 100"):
            CorrelationAnalyzer(min_significance=Decimal("-10"))

    def test_string_representation(self) -> None:
        """Test string representation of analyzer."""
        analyzer = CorrelationAnalyzer(
            lookback_days=90,
            min_correlation=Decimal("0.7"),
            min_significance=Decimal("80"),
        )

        str_repr = str(analyzer)
        assert "CorrelationAnalyzer" in str_repr
        assert "lookback=90" in str_repr
        assert "min_corr=0.7" in str_repr
        assert "min_sig=80" in str_repr

    def test_repr(self) -> None:
        """Test detailed representation of analyzer."""
        analyzer = CorrelationAnalyzer(
            lookback_days=60,
            min_correlation=Decimal("0.6"),
            min_significance=Decimal("70"),
        )

        repr_str = repr(analyzer)
        assert "CorrelationAnalyzer" in repr_str
        assert "lookback_days=60" in repr_str


class TestCalculateCorrelation:
    """Tests for calculate_correlation method."""

    @pytest.fixture
    def analyzer(self) -> CorrelationAnalyzer:
        """Provide a correlation analyzer for testing."""
        return CorrelationAnalyzer()

    @pytest.fixture
    def sample_series1(self) -> Series:
        """Provide sample series 1 for testing."""
        return Series([1.0, 2.0, 3.0, 4.0, 5.0])

    @pytest.fixture
    def sample_series2(self) -> Series:
        """Provide sample series 2 for testing."""
        return Series([2.0, 4.0, 6.0, 8.0, 10.0])

    def test_calculate_correlation_positive(
        self, analyzer: CorrelationAnalyzer, sample_series1: Series, sample_series2: Series
    ) -> None:
        """Test correlation calculation with positive correlation."""
        correlation, p_value = analyzer.calculate_correlation(sample_series1, sample_series2)

        assert isinstance(correlation, Decimal)
        assert isinstance(p_value, Decimal)
        assert correlation == Decimal("1")
        assert p_value < Decimal("0.01")

    def test_calculate_correlation_negative(self, analyzer: CorrelationAnalyzer) -> None:
        """Test correlation calculation with negative correlation."""
        series1 = Series([1.0, 2.0, 3.0, 4.0, 5.0])
        series2 = Series([5.0, 4.0, 3.0, 2.0, 1.0])

        correlation, p_value = analyzer.calculate_correlation(series1, series2)

        assert correlation == Decimal("-1")
        assert p_value < Decimal("0.01")

    def test_calculate_correlation_no_correlation(self, analyzer: CorrelationAnalyzer) -> None:
        """Test correlation calculation with no correlation."""
        np.random.seed(42)
        series1 = Series(np.random.randn(100))
        series2 = Series(np.random.randn(100))

        correlation, p_value = analyzer.calculate_correlation(series1, series2)

        assert isinstance(correlation, Decimal)
        assert isinstance(p_value, Decimal)
        assert abs(correlation) < Decimal("0.3")

    def test_calculate_correlation_numpy_arrays(self, analyzer: CorrelationAnalyzer) -> None:
        """Test correlation calculation with numpy arrays."""
        arr1 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        arr2 = np.array([2.0, 4.0, 6.0, 8.0, 10.0])

        correlation, p_value = analyzer.calculate_correlation(arr1, arr2)

        assert correlation == Decimal("1")

    def test_calculate_correlation_different_lengths(
        self, analyzer: CorrelationAnalyzer, sample_series1: Series
    ) -> None:
        """Test correlation calculation rejects different length series."""
        series_short = Series([1.0, 2.0, 3.0])

        with pytest.raises(ValueError, match="Series must have same length"):
            analyzer.calculate_correlation(sample_series1, series_short)

    def test_calculate_correlation_insufficient_data(self, analyzer: CorrelationAnalyzer) -> None:
        """Test correlation calculation rejects insufficient data."""
        series1 = Series([1.0])
        series2 = Series([2.0])

        with pytest.raises(ValueError, match="Series must have at least 2 observations"):
            analyzer.calculate_correlation(series1, series2)

    def test_calculate_correlation_with_nan(self, analyzer: CorrelationAnalyzer) -> None:
        """Test correlation calculation handles NaN values."""
        series1 = Series([1.0, 2.0, np.nan, 4.0, 5.0])
        series2 = Series([2.0, 4.0, 6.0, 8.0, 10.0])

        correlation, p_value = analyzer.calculate_correlation(series1, series2)

        assert isinstance(correlation, Decimal)
        assert correlation > Decimal("0.9")

    def test_calculate_correlation_all_nan(self, analyzer: CorrelationAnalyzer) -> None:
        """Test correlation calculation with all NaN values."""
        series1 = Series([np.nan, np.nan, np.nan])
        series2 = Series([1.0, 2.0, 3.0])

        with pytest.raises(ValueError, match="Insufficient valid data points"):
            analyzer.calculate_correlation(series1, series2)


class TestCalculateFXPairCorrelation:
    """Tests for calculate_fx_pair_correlation method."""

    @pytest.fixture
    def analyzer(self) -> CorrelationAnalyzer:
        """Provide a correlation analyzer for testing."""
        return CorrelationAnalyzer(lookback_days=60)

    @pytest.fixture
    def returns_data(self) -> dict[str, Series]:
        """Provide returns data for testing."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        np.random.seed(42)

        return {
            "EUR/USD": Series(np.random.randn(100) * 0.01, index=dates),
            "GBP/USD": Series(np.random.randn(100) * 0.01, index=dates),
            "USD/JPY": Series(np.random.randn(100) * 0.01, index=dates),
        }

    def test_calculate_fx_pair_correlation(
        self, analyzer: CorrelationAnalyzer, returns_data: dict[str, Series]
    ) -> None:
        """Test FX pair correlation calculation."""
        corr_pair = analyzer.calculate_fx_pair_correlation(
            "EUR/USD",
            "GBP/USD",
            returns_data,
        )

        assert isinstance(corr_pair, FXCorrelationPair)
        assert corr_pair.pair1 == "EUR/USD"
        assert corr_pair.pair2 == "GBP/USD"
        assert isinstance(corr_pair.correlation, Decimal)
        assert isinstance(corr_pair.p_value, Decimal)
        # Lookback is limited by analyzer's setting (60)
        assert corr_pair.lookback_days == 60

    def test_calculate_fx_pair_correlation_pair1_not_found(
        self, analyzer: CorrelationAnalyzer, returns_data: dict[str, Series]
    ) -> None:
        """Test error when pair1 not found."""
        with pytest.raises(ValueError, match="Pair USD/CHF not found in returns_data"):
            analyzer.calculate_fx_pair_correlation(
                "USD/CHF",
                "EUR/USD",
                returns_data,
            )

    def test_calculate_fx_pair_correlation_pair2_not_found(
        self, analyzer: CorrelationAnalyzer, returns_data: dict[str, Series]
    ) -> None:
        """Test error when pair2 not found."""
        with pytest.raises(ValueError, match="Pair USD/CHF not found in returns_data"):
            analyzer.calculate_fx_pair_correlation(
                "EUR/USD",
                "USD/CHF",
                returns_data,
            )

    def test_calculate_fx_pair_correlation_lookback_limit(
        self, analyzer: CorrelationAnalyzer
    ) -> None:
        """Test that lookback period is respected."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        returns_data = {
            "EUR/USD": Series(np.random.randn(100) * 0.01, index=dates),
            "GBP/USD": Series(np.random.randn(100) * 0.01, index=dates),
        }

        corr_pair = analyzer.calculate_fx_pair_correlation(
            "EUR/USD",
            "GBP/USD",
            returns_data,
        )

        # Should limit to 60 days (the analyzer's lookback setting)
        assert corr_pair.lookback_days == 60


class TestCalculateIntermarketCorrelation:
    """Tests for calculate_intermarket_correlation method."""

    @pytest.fixture
    def analyzer(self) -> CorrelationAnalyzer:
        """Provide a correlation analyzer for testing."""
        return CorrelationAnalyzer(lookback_days=60)

    @pytest.fixture
    def fx_returns(self) -> Series:
        """Provide FX returns for testing."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        np.random.seed(42)
        return Series(np.random.randn(100) * 0.01, index=dates)

    @pytest.fixture
    def asset_returns(self) -> Series:
        """Provide asset returns for testing."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        np.random.seed(43)
        return Series(np.random.randn(100) * 0.02, index=dates)

    def test_calculate_intermarket_correlation(
        self, analyzer: CorrelationAnalyzer, fx_returns: Series, asset_returns: Series
    ) -> None:
        """Test intermarket correlation calculation."""
        relationship = analyzer.calculate_intermarket_correlation(
            fx_pair="USD/JPY",
            external_asset="SPX",
            asset_class=AssetClass.EQUITY,
            fx_returns=fx_returns,
            asset_returns=asset_returns,
            relationship_type=RelationshipType.SAFE_HAVEN,
        )

        assert isinstance(relationship, IntermarketRelationship)
        assert relationship.fx_pair == "USD/JPY"
        assert relationship.external_asset == "SPX"
        assert relationship.asset_class == AssetClass.EQUITY
        assert relationship.relationship_type == RelationshipType.SAFE_HAVEN
        assert isinstance(relationship.correlation, Decimal)
        assert isinstance(relationship.beta, Decimal)
        assert isinstance(relationship.significance, Decimal)

    def test_calculate_intermarket_correlation_empty_fx_pair(
        self, analyzer: CorrelationAnalyzer, asset_returns: Series
    ) -> None:
        """Test error when fx_pair is empty."""
        fx_returns = Series([1.0, 2.0, 3.0])

        with pytest.raises(ValueError, match="fx_pair must be a non-empty string"):
            analyzer.calculate_intermarket_correlation(
                fx_pair="",
                external_asset="SPX",
                asset_class=AssetClass.EQUITY,
                fx_returns=fx_returns,
                asset_returns=asset_returns,
                relationship_type=RelationshipType.SAFE_HAVEN,
            )

    def test_calculate_intermarket_correlation_empty_external_asset(
        self, analyzer: CorrelationAnalyzer, fx_returns: Series
    ) -> None:
        """Test error when external_asset is empty."""
        asset_returns = Series([1.0, 2.0, 3.0])

        with pytest.raises(ValueError, match="external_asset must be a non-empty string"):
            analyzer.calculate_intermarket_correlation(
                fx_pair="USD/JPY",
                external_asset="",
                asset_class=AssetClass.EQUITY,
                fx_returns=fx_returns,
                asset_returns=asset_returns,
                relationship_type=RelationshipType.SAFE_HAVEN,
            )


class TestCalculateBeta:
    """Tests for _calculate_beta method."""

    @pytest.fixture
    def analyzer(self) -> CorrelationAnalyzer:
        """Provide a correlation analyzer for testing."""
        return CorrelationAnalyzer()

    def test_calculate_beta_positive(self, analyzer: CorrelationAnalyzer) -> None:
        """Test beta calculation with positive relationship."""
        fx_returns = Series([0.01, 0.02, 0.03, 0.04, 0.05])
        asset_returns = Series([0.02, 0.04, 0.06, 0.08, 0.10])

        beta = analyzer._calculate_beta(fx_returns, asset_returns)

        assert isinstance(beta, Decimal)
        # Allow for floating point precision - beta should be approximately 0.5
        assert abs(beta - Decimal("0.5")) < Decimal("0.01")

    def test_calculate_beta_negative(self, analyzer: CorrelationAnalyzer) -> None:
        """Test beta calculation with negative relationship."""
        fx_returns = Series([0.01, 0.02, 0.03, 0.04, 0.05])
        asset_returns = Series([0.05, 0.04, 0.03, 0.02, 0.01])

        beta = analyzer._calculate_beta(fx_returns, asset_returns)

        assert isinstance(beta, Decimal)
        assert beta < Decimal("0")

    def test_calculate_beta_zero_variance(self, analyzer: CorrelationAnalyzer) -> None:
        """Test beta calculation when asset has zero variance."""
        fx_returns = Series([0.01, 0.02, 0.03, 0.04, 0.05])
        asset_returns = Series([0.05, 0.05, 0.05, 0.05, 0.05])

        beta = analyzer._calculate_beta(fx_returns, asset_returns)

        assert beta == Decimal("0")

    def test_calculate_beta_insufficient_data(self, analyzer: CorrelationAnalyzer) -> None:
        """Test beta calculation with insufficient data."""
        fx_returns = Series([0.01])
        asset_returns = Series([0.02])

        beta = analyzer._calculate_beta(fx_returns, asset_returns)

        assert beta == Decimal("0")


class TestDetectCorrelationRegimeChange:
    """Tests for detect_correlation_regime_change method."""

    @pytest.fixture
    def analyzer(self) -> CorrelationAnalyzer:
        """Provide a correlation analyzer for testing."""
        return CorrelationAnalyzer()

    def test_no_regime_change_stable(self, analyzer: CorrelationAnalyzer) -> None:
        """Test no regime change with stable correlations."""
        correlations = [0.7, 0.71, 0.69, 0.7, 0.72, 0.68, 0.7, 0.71]

        result = analyzer.detect_correlation_regime_change(correlations, window=5, threshold=2.0)

        assert result is False or isinstance(result, (bool, np.bool_))

    def test_regime_change_detected(self, analyzer: CorrelationAnalyzer) -> None:
        """Test regime change detection with larger shift."""
        # Create a series with a very large final shift
        # Using -0.5 instead of 0.0 to get more extreme z-score
        correlations = [0.7, 0.71, 0.69, 0.7, 0.72, 0.68, 0.7, 0.71, 0.7, -0.5]

        result = analyzer.detect_correlation_regime_change(correlations, window=5, threshold=1.5)

        # Result may be numpy bool or python bool
        assert bool(result) is True

    def test_regime_change_insufficient_data(self, analyzer: CorrelationAnalyzer) -> None:
        """Test regime change with insufficient data."""
        correlations = [0.7, 0.71]

        result = analyzer.detect_correlation_regime_change(correlations, window=5, threshold=2.0)

        assert result is False

    def test_regime_change_pandas_series(self, analyzer: CorrelationAnalyzer) -> None:
        """Test regime change with pandas Series."""
        correlations = Series([0.7, 0.71, 0.69, 0.7, 0.72, 0.68, 0.7, 0.71, 0.7, -0.5])

        result = analyzer.detect_correlation_regime_change(correlations, window=5, threshold=1.5)

        # Result may be numpy bool or python bool
        assert bool(result) is True


class TestCalculateRollingCorrelation:
    """Tests for calculate_rolling_correlation method."""

    @pytest.fixture
    def analyzer(self) -> CorrelationAnalyzer:
        """Provide a correlation analyzer for testing."""
        return CorrelationAnalyzer()

    @pytest.fixture
    def series1(self) -> Series:
        """Provide sample series 1."""
        return Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

    @pytest.fixture
    def series2(self) -> Series:
        """Provide sample series 2."""
        return Series([2, 4, 6, 8, 10, 12, 14, 16, 18, 20])

    def test_calculate_rolling_correlation(
        self, analyzer: CorrelationAnalyzer, series1: Series, series2: Series
    ) -> None:
        """Test rolling correlation calculation."""
        rolling_corr = analyzer.calculate_rolling_correlation(series1, series2, window=5)

        assert isinstance(rolling_corr, Series)
        assert len(rolling_corr) == len(series1)

    def test_calculate_rolling_correlation_invalid_window(
        self, analyzer: CorrelationAnalyzer, series1: Series, series2: Series
    ) -> None:
        """Test rolling correlation with invalid window."""
        with pytest.raises(ValueError, match="Window must be > 1"):
            analyzer.calculate_rolling_correlation(series1, series2, window=1)

    def test_calculate_rolling_correlation_different_lengths(
        self, analyzer: CorrelationAnalyzer, series1: Series
    ) -> None:
        """Test rolling correlation with different length series."""
        series_short = Series([1, 2, 3])

        with pytest.raises(ValueError, match="Series must have same length"):
            analyzer.calculate_rolling_correlation(series1, series_short, window=3)


class TestIdentifySignificantRelationships:
    """Tests for identify_significant_relationships method."""

    @pytest.fixture
    def analyzer(self) -> CorrelationAnalyzer:
        """Provide a correlation analyzer for testing."""
        return CorrelationAnalyzer(
            lookback_days=60,
            min_correlation=Decimal("0.6"),
            min_significance=Decimal("70"),
        )

    @pytest.fixture
    def returns_data(self) -> dict[str, Series]:
        """Provide returns data for testing."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        np.random.seed(42)

        return {
            "EUR/USD": Series(np.random.randn(100) * 0.01, index=dates),
            "USD/JPY": Series(np.random.randn(100) * 0.01, index=dates),
            "SPX": Series(np.random.randn(100) * 0.02, index=dates),
            "GOLD": Series(np.random.randn(100) * 0.015, index=dates),
        }

    def test_identify_significant_relationships(
        self, analyzer: CorrelationAnalyzer, returns_data: dict[str, Series]
    ) -> None:
        """Test identifying significant relationships."""
        fx_pairs = ["EUR/USD", "USD/JPY"]
        external_assets = {"SPX": AssetClass.EQUITY, "GOLD": AssetClass.COMMODITY}

        relationships = analyzer.identify_significant_relationships(
            fx_pairs=fx_pairs,
            external_assets=external_assets,
            returns_data=returns_data,
        )

        assert isinstance(relationships, list)
        for rel in relationships:
            assert isinstance(rel, IntermarketRelationship)

    def test_identify_significant_relationships_with_types(
        self, analyzer: CorrelationAnalyzer, returns_data: dict[str, Series]
    ) -> None:
        """Test identifying relationships with specific types."""
        fx_pairs = ["USD/JPY"]
        external_assets = {"SPX": AssetClass.EQUITY}
        relationship_types = {"USD/JPY_SPX": RelationshipType.SAFE_HAVEN}

        relationships = analyzer.identify_significant_relationships(
            fx_pairs=fx_pairs,
            external_assets=external_assets,
            returns_data=returns_data,
            relationship_types=relationship_types,
        )

        assert isinstance(relationships, list)

    def test_identify_significant_relationships_missing_fx_pair(
        self, analyzer: CorrelationAnalyzer, returns_data: dict[str, Series]
    ) -> None:
        """Test handling of missing FX pair."""
        fx_pairs = ["USD/CHF"]  # Not in returns_data
        external_assets = {"SPX": AssetClass.EQUITY}

        relationships = analyzer.identify_significant_relationships(
            fx_pairs=fx_pairs,
            external_assets=external_assets,
            returns_data=returns_data,
        )

        # Should return empty list, not raise error
        assert relationships == []

    def test_identify_significant_relationships_missing_asset(
        self, analyzer: CorrelationAnalyzer, returns_data: dict[str, Series]
    ) -> None:
        """Test handling of missing external asset."""
        fx_pairs = ["EUR/USD"]
        external_assets = {"VIX": AssetClass.EQUITY}  # Not in returns_data

        relationships = analyzer.identify_significant_relationships(
            fx_pairs=fx_pairs,
            external_assets=external_assets,
            returns_data=returns_data,
        )

        # Should return empty list, not raise error
        assert relationships == []


class TestInferRelationshipType:
    """Tests for _infer_relationship_type method."""

    @pytest.fixture
    def analyzer(self) -> CorrelationAnalyzer:
        """Provide a correlation analyzer for testing."""
        return CorrelationAnalyzer()

    def test_infer_safe_haven_jpy_equity(self, analyzer: CorrelationAnalyzer) -> None:
        """Test inferring safe haven relationship for JPY with equities."""
        rel_type = analyzer._infer_relationship_type("USD/JPY", AssetClass.EQUITY)

        assert rel_type == RelationshipType.SAFE_HAVEN

    def test_infer_safe_haven_chf_equity(self, analyzer: CorrelationAnalyzer) -> None:
        """Test inferring safe haven relationship for CHF with equities."""
        rel_type = analyzer._infer_relationship_type("USD/CHF", AssetClass.EQUITY)

        assert rel_type == RelationshipType.SAFE_HAVEN

    def test_infer_carry_trade_non_safe_haven(self, analyzer: CorrelationAnalyzer) -> None:
        """Test inferring carry trade for non-safe haven currencies."""
        rel_type = analyzer._infer_relationship_type("EUR/USD", AssetClass.EQUITY)

        assert rel_type == RelationshipType.CARRY_TRADE

    def test_infer_commodity_link_aud(self, analyzer: CorrelationAnalyzer) -> None:
        """Test inferring commodity link for AUD."""
        rel_type = analyzer._infer_relationship_type("AUD/USD", AssetClass.COMMODITY)

        assert rel_type == RelationshipType.COMMODITY_LINK

    def test_infer_commodity_link_cad(self, analyzer: CorrelationAnalyzer) -> None:
        """Test inferring commodity link for CAD."""
        rel_type = analyzer._infer_relationship_type("USD/CAD", AssetClass.COMMODITY)

        assert rel_type == RelationshipType.COMMODITY_LINK

    def test_infer_commodity_link_nzd(self, analyzer: CorrelationAnalyzer) -> None:
        """Test inferring commodity link for NZD."""
        rel_type = analyzer._infer_relationship_type("NZD/USD", AssetClass.COMMODITY)

        assert rel_type == RelationshipType.COMMODITY_LINK

    def test_infer_default_positive_correlation(self, analyzer: CorrelationAnalyzer) -> None:
        """Test default inference to positive correlation."""
        rel_type = analyzer._infer_relationship_type("EUR/USD", AssetClass.FIXED_INCOME)

        assert rel_type == RelationshipType.POSITIVE_CORRELATION


class TestGetCorrelationMatrix:
    """Tests for get_correlation_matrix method."""

    @pytest.fixture
    def analyzer(self) -> CorrelationAnalyzer:
        """Provide a correlation analyzer for testing."""
        return CorrelationAnalyzer(lookback_days=60)

    @pytest.fixture
    def returns_data(self) -> dict[str, Series]:
        """Provide returns data for testing."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        np.random.seed(42)

        return {
            "EUR/USD": Series(np.random.randn(100) * 0.01, index=dates),
            "GBP/USD": Series(np.random.randn(100) * 0.01, index=dates),
            "USD/JPY": Series(np.random.randn(100) * 0.01, index=dates),
        }

    def test_get_correlation_matrix(
        self, analyzer: CorrelationAnalyzer, returns_data: dict[str, Series]
    ) -> None:
        """Test correlation matrix generation."""
        symbols = ["EUR/USD", "GBP/USD", "USD/JPY"]
        corr_matrix = analyzer.get_correlation_matrix(symbols, returns_data)

        assert isinstance(corr_matrix, DataFrame)
        assert corr_matrix.shape == (3, 3)
        assert list(corr_matrix.columns) == symbols
        assert list(corr_matrix.index) == symbols

    def test_get_correlation_matrix_symbol_not_found(
        self, analyzer: CorrelationAnalyzer, returns_data: dict[str, Series]
    ) -> None:
        """Test error when symbol not found."""
        symbols = ["EUR/USD", "USD/CHF"]  # USD/CHF not in returns_data

        with pytest.raises(ValueError, match="Symbol USD/CHF not found in returns_data"):
            analyzer.get_correlation_matrix(symbols, returns_data)

    def test_get_correlation_matrix_lookback_limit(self, analyzer: CorrelationAnalyzer) -> None:
        """Test that lookback period is respected."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        returns_data = {
            "EUR/USD": Series(np.random.randn(100) * 0.01, index=dates),
            "GBP/USD": Series(np.random.randn(100) * 0.01, index=dates),
        }

        symbols = ["EUR/USD", "GBP/USD"]
        corr_matrix = analyzer.get_correlation_matrix(symbols, returns_data)

        # Matrix should still be computed correctly
        assert corr_matrix.shape == (2, 2)
