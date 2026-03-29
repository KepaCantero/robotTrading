"""
Correlation Analyzer for FX Intermarket Strategy.

This module provides statistical correlation analysis capabilities for
identifying and measuring relationships between FX pairs and external assets.

Uses scipy.stats for correlation calculations and statistical testing.

Key features:
- Pearson correlation with p-value calculation
- Rolling correlation analysis
- Correlation regime change detection
- Significance testing
- Correlation matrix generation

References:
    scipy.stats.pearsonr: Pearson correlation coefficient and p-value
"""

from __future__ import annotations

import logging
from decimal import Decimal

import numpy as np
import pandas as pd
from scipy import stats

from app.domain.strategies.fx_intermarket.models import (
    AssetClass,
    FXCorrelationPair,
    IntermarketRelationship,
    RelationshipType,
)

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """
    Statistical correlation analyzer for intermarket relationships.

    Provides methods for calculating correlations between FX pairs and
    external assets, detecting significant relationships, and identifying
    regime changes in correlation patterns.

    Attributes:
        lookback_days: Default lookback period for calculations
        min_correlation: Minimum correlation threshold
        min_significance: Minimum significance threshold (0-100)

    Examples:
        >>> analyzer = CorrelationAnalyzer(
        ...     lookback_days=60,
        ...     min_correlation=Decimal("0.7"),
        ...     min_significance=Decimal("80")
        ... )
        >>> relationship = analyzer.calculate_intermarket_correlation(
        ...     fx_pair="USD/JPY",
        ...     external_asset="SPX",
        ...     asset_class=AssetClass.EQUITY,
        ...     fx_returns=fx_data,
        ...     asset_returns=spy_data,
        ...     relationship_type=RelationshipType.SAFE_HAVEN
        ... )
    """

    def __init__(
        self,
        lookback_days: int = 60,
        min_correlation: Decimal | None = None,
        min_significance: Decimal | None = None,
    ):
        """
        Initialize the correlation analyzer.

        Args:
            lookback_days: Lookback period for correlation calculations
            min_correlation: Minimum absolute correlation to consider significant
            min_significance: Minimum significance score (0-100)

        Raises:
            ValueError: If parameters are invalid
        """
        if min_correlation is None:
            min_correlation = Decimal("0.6")
        if min_significance is None:
            min_significance = Decimal("70")
        if lookback_days <= 0:
            raise ValueError(f"lookback_days must be positive, got {lookback_days}")

        if not Decimal("0") <= min_correlation <= Decimal("1"):
            raise ValueError(f"min_correlation must be between 0 and 1, got {min_correlation}")

        if not Decimal("0") <= min_significance <= Decimal("100"):
            raise ValueError(f"min_significance must be between 0 and 100, got {min_significance}")

        self.lookback_days = lookback_days
        self.min_correlation = min_correlation
        self.min_significance = min_significance

        logger.info(
            f"CorrelationAnalyzer initialized: lookback={lookback_days}, "
            f"min_corr={min_correlation}, min_sig={min_significance}"
        )

    def calculate_correlation(
        self, series1: pd.Series | np.ndarray, series2: pd.Series | np.ndarray
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate Pearson correlation and p-value between two series.

        Uses scipy.stats.pearsonr for correlation calculation and
        statistical significance testing.

        Args:
            series1: First time series
            series2: Second time series

        Returns:
            Tuple of (correlation, p_value) as Decimals

        Raises:
            ValueError: If series have different lengths or insufficient data

        Examples:
            >>> corr, pval = analyzer.calculate_correlation(
            ...     fx_returns,
            ...     asset_returns
            ... )
            >>> print(f"Correlation: {corr}, P-value: {pval}")
        """
        # Convert to numpy arrays if needed
        if isinstance(series1, pd.Series):
            series1 = series1.values
        if isinstance(series2, pd.Series):
            series2 = series2.values

        # Validate inputs
        if len(series1) != len(series2):
            raise ValueError(f"Series must have same length: got {len(series1)} and {len(series2)}")

        if len(series1) < 2:
            raise ValueError(f"Series must have at least 2 observations, got {len(series1)}")

        # Remove NaN values
        mask = ~(np.isnan(series1) | np.isnan(series2))
        clean_series1 = series1[mask]
        clean_series2 = series2[mask]

        if len(clean_series1) < 2:
            raise ValueError(
                f"Insufficient valid data points after removing NaN: got {len(clean_series1)}"
            )

        try:
            # Calculate correlation and p-value using scipy
            correlation, p_value = stats.pearsonr(clean_series1, clean_series2)

            # Validate correlation is in valid range
            if not -1 <= correlation <= 1:
                raise ValueError(f"Invalid correlation value: {correlation}")

            return Decimal(str(correlation)), Decimal(str(p_value))

        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            raise

    def calculate_fx_pair_correlation(
        self,
        pair1: str,
        pair2: str,
        returns_data: dict[str, pd.Series],
    ) -> FXCorrelationPair:
        """
        Calculate correlation between two FX pairs.

        Args:
            pair1: First currency pair symbol
            pair2: Second currency pair symbol
            returns_data: Dictionary mapping symbols to return series

        Returns:
            FXCorrelationPair with correlation metrics

        Raises:
            ValueError: If pairs not found in returns_data or calculation fails

        Examples:
            >>> corr_pair = analyzer.calculate_fx_pair_correlation(
            ...     "EUR/USD",
            ...     "GBP/USD",
            ...     returns_data
            ... )
        """
        if pair1 not in returns_data:
            raise ValueError(f"Pair {pair1} not found in returns_data")

        if pair2 not in returns_data:
            raise ValueError(f"Pair {pair2} not found in returns_data")

        series1 = returns_data[pair1]
        series2 = returns_data[pair2]

        # Limit to lookback period
        if len(series1) > self.lookback_days:
            series1 = series1.tail(self.lookback_days)
        if len(series2) > self.lookback_days:
            series2 = series2.tail(self.lookback_days)

        # Calculate correlation
        correlation, p_value = self.calculate_correlation(series1, series2)

        return FXCorrelationPair(
            pair1=pair1,
            pair2=pair2,
            correlation=correlation,
            p_value=p_value,
            lookback_days=min(len(series1), len(series2)),
        )

    def calculate_intermarket_correlation(
        self,
        fx_pair: str,
        external_asset: str,
        asset_class: AssetClass,
        fx_returns: pd.Series,
        asset_returns: pd.Series,
        relationship_type: RelationshipType,
    ) -> IntermarketRelationship:
        """
        Calculate correlation between an FX pair and external asset.

        Computes the correlation, beta (sensitivity), and significance
        of the relationship between a currency pair and an external asset.

        Args:
            fx_pair: FX pair symbol
            external_asset: External asset symbol
            asset_class: Class of external asset
            fx_returns: FX pair return series
            asset_returns: External asset return series
            relationship_type: Type of relationship

        Returns:
            IntermarketRelationship with correlation metrics

        Raises:
            ValueError: If inputs are invalid or calculation fails

        Examples:
            >>> relationship = analyzer.calculate_intermarket_correlation(
            ...     fx_pair="USD/JPY",
            ...     external_asset="SPX",
            ...     asset_class=AssetClass.EQUITY,
            ...     fx_returns=fx_data,
            ...     asset_returns=spy_data,
            ...     relationship_type=RelationshipType.SAFE_HAVEN
            ... )
        """
        # Validate inputs
        if not isinstance(fx_pair, str) or not fx_pair:
            raise ValueError("fx_pair must be a non-empty string")

        if not isinstance(external_asset, str) or not external_asset:
            raise ValueError("external_asset must be a non-empty string")

        # Align series to lookback period
        if len(fx_returns) > self.lookback_days:
            fx_returns = fx_returns.tail(self.lookback_days)
        if len(asset_returns) > self.lookback_days:
            asset_returns = asset_returns.tail(self.lookback_days)

        # Ensure series are aligned
        if (
            len(fx_returns) != len(asset_returns)
            and isinstance(fx_returns, pd.Series)
            and isinstance(asset_returns, pd.Series)
        ):
            # Align by index if both are Series with datetime index
            aligned = pd.concat([fx_returns, asset_returns], axis=1, join="inner")
            fx_returns = aligned.iloc[:, 0]
            asset_returns = aligned.iloc[:, 1]

        # Calculate correlation
        correlation, p_value = self.calculate_correlation(fx_returns, asset_returns)

        # Calculate beta (covariance / variance)
        beta = self._calculate_beta(fx_returns, asset_returns)

        # Calculate significance score
        significance = (Decimal("1") - p_value) * Decimal("100")

        return IntermarketRelationship(
            fx_pair=fx_pair,
            external_asset=external_asset,
            asset_class=asset_class,
            relationship_type=relationship_type,
            correlation=correlation,
            beta=beta,
            significance=significance,
            lookback_days=min(len(fx_returns), len(asset_returns)),
        )

    def _calculate_beta(
        self, fx_returns: pd.Series | np.ndarray, asset_returns: pd.Series | np.ndarray
    ) -> Decimal:
        """
        Calculate beta coefficient (sensitivity of FX to external asset).

        Beta = Covariance(FX, Asset) / Variance(Asset)

        Args:
            fx_returns: FX return series
            asset_returns: Asset return series

        Returns:
            Beta coefficient as Decimal
        """
        # Convert to numpy arrays
        if isinstance(fx_returns, pd.Series):
            fx_returns = fx_returns.values
        if isinstance(asset_returns, pd.Series):
            asset_returns = asset_returns.values

        # Remove NaN
        mask = ~(np.isnan(fx_returns) | np.isnan(asset_returns))
        fx_clean = fx_returns[mask]
        asset_clean = asset_returns[mask]

        if len(fx_clean) < 2:
            return Decimal("0")

        try:
            # Calculate covariance and variance
            covariance = np.cov(fx_clean, asset_clean)[0, 1]
            variance = np.var(asset_clean, ddof=1)

            if variance == 0:
                return Decimal("0")

            beta = covariance / variance
            return Decimal(str(beta))

        except Exception as e:
            logger.warning(f"Error calculating beta: {e}")
            return Decimal("0")

    def detect_correlation_regime_change(
        self,
        historical_correlations: list[float] | pd.Series,
        window: int = 20,
        threshold: float = 2.0,
    ) -> bool:
        """
        Detect if correlation has undergone a regime change.

        Uses z-score analysis on rolling correlations to detect
        significant shifts in correlation patterns.

        Args:
            historical_correlations: Time series of historical correlations
            window: Rolling window for statistics
            threshold: Z-score threshold for regime change detection

        Returns:
            True if regime change detected, False otherwise

        Examples:
            >>> is_regime_change = analyzer.detect_correlation_regime_change(
            ...     correlations,
            ...     window=20,
            ...     threshold=2.0
            ... )
        """
        # Convert to pandas Series if needed
        if isinstance(historical_correlations, list):
            correlations = pd.Series(historical_correlations)
        else:
            correlations = historical_correlations.copy()

        if len(correlations) < window:
            return False

        # Calculate rolling statistics
        rolling_mean = correlations.rolling(window=window).mean()
        rolling_std = correlations.rolling(window=window).std()

        # Get latest values
        latest_corr = correlations.iloc[-1]
        latest_mean = rolling_mean.iloc[-1]
        latest_std = rolling_std.iloc[-1]

        if latest_std == 0 or pd.isna(latest_std):
            return False

        # Calculate z-score
        z_score = abs((latest_corr - latest_mean) / latest_std)

        # Check if z-score exceeds threshold
        return z_score > threshold

    def calculate_rolling_correlation(
        self,
        series1: pd.Series,
        series2: pd.Series,
        window: int = 20,
    ) -> pd.Series:
        """
        Calculate rolling correlation between two series.

        Args:
            series1: First time series
            series2: Second time series
            window: Rolling window size

        Returns:
            Series of rolling correlations

        Raises:
            ValueError: If window is invalid or series are incompatible

        Examples:
            >>> rolling_corr = analyzer.calculate_rolling_correlation(
            ...     fx_returns,
            ...     asset_returns,
            ...     window=30
            ... )
        """
        if window <= 1:
            raise ValueError(f"Window must be > 1, got {window}")

        if len(series1) != len(series2):
            raise ValueError(f"Series must have same length: got {len(series1)} and {len(series2)}")

        # Align series
        if isinstance(series1, pd.Series) and isinstance(series2, pd.Series):
            aligned = pd.concat([series1, series2], axis=1, join="inner")
            series1 = aligned.iloc[:, 0]
            series2 = aligned.iloc[:, 1]

        # Calculate rolling correlation
        rolling_corr = series1.rolling(window=window).corr(series2)

        return rolling_corr

    def identify_significant_relationships(
        self,
        fx_pairs: list[str],
        external_assets: dict[str, AssetClass],
        returns_data: dict[str, pd.Series],
        relationship_types: dict[str, RelationshipType] | None = None,
    ) -> list[IntermarketRelationship]:
        """
        Identify all significant intermarket relationships.

        Tests all combinations of FX pairs and external assets for
        significant correlations based on configured thresholds.

        Args:
            fx_pairs: List of FX pair symbols
            external_assets: Dict mapping asset symbols to asset classes
            returns_data: Dict mapping symbols to return series
            relationship_types: Optional dict of specific relationship types

        Returns:
            List of significant IntermarketRelationship objects

        Examples:
            >>> relationships = analyzer.identify_significant_relationships(
            ...     fx_pairs=["EUR/USD", "USD/JPY"],
            ...     external_assets={"SPX": AssetClass.EQUITY},
            ...     returns_data=all_returns,
            ...     relationship_types={"USD/JPY_SPX": RelationshipType.SAFE_HAVEN}
            ... )
        """
        significant_relationships = []

        # Default relationship types if not provided
        if relationship_types is None:
            relationship_types = {}

        for fx_pair in fx_pairs:
            if fx_pair not in returns_data:
                logger.warning(f"FX pair {fx_pair} not found in returns_data")
                continue

            for asset_symbol, asset_class in external_assets.items():
                if asset_symbol not in returns_data:
                    logger.warning(f"Asset {asset_symbol} not found in returns_data")
                    continue

                try:
                    # Determine relationship type
                    key = f"{fx_pair}_{asset_symbol}"
                    relationship_type = relationship_types.get(
                        key, self._infer_relationship_type(fx_pair, asset_class)
                    )

                    # Calculate correlation
                    relationship = self.calculate_intermarket_correlation(
                        fx_pair=fx_pair,
                        external_asset=asset_symbol,
                        asset_class=asset_class,
                        fx_returns=returns_data[fx_pair],
                        asset_returns=returns_data[asset_symbol],
                        relationship_type=relationship_type,
                    )

                    # Check if meets significance thresholds
                    abs_correlation = abs(relationship.correlation)
                    if (
                        abs_correlation >= self.min_correlation
                        and relationship.significance >= self.min_significance
                    ):
                        significant_relationships.append(relationship)
                        logger.info(
                            f"Found significant relationship: "
                            f"{fx_pair} - {asset_symbol} "
                            f"(corr={relationship.correlation:.2f}, "
                            f"sig={relationship.significance:.0f})"
                        )

                except Exception as e:
                    logger.warning(
                        f"Error calculating correlation for {fx_pair} - {asset_symbol}: {e}"
                    )
                    continue

        return significant_relationships

    def _infer_relationship_type(self, fx_pair: str, asset_class: AssetClass) -> RelationshipType:
        """
        Infer relationship type based on FX pair and asset class.

        Args:
            fx_pair: Currency pair symbol
            asset_class: Asset class of external asset

        Returns:
            Inferred RelationshipType
        """
        # Safe haven: JPY and CHF with equities
        if asset_class == AssetClass.EQUITY:
            if "JPY" in fx_pair or "CHF" in fx_pair:
                return RelationshipType.SAFE_HAVEN
            else:
                return RelationshipType.CARRY_TRADE

        # Commodity link: AUD, CAD, NZD with commodities
        if asset_class == AssetClass.COMMODITY and any(
            curr in fx_pair for curr in ["AUD", "CAD", "NZD"]
        ):
            return RelationshipType.COMMODITY_LINK

        # Default to positive/negative correlation based on pair
        return RelationshipType.POSITIVE_CORRELATION

    def get_correlation_matrix(
        self,
        symbols: list[str],
        returns_data: dict[str, pd.Series],
    ) -> pd.DataFrame:
        """
        Generate correlation matrix for multiple symbols.

        Args:
            symbols: List of symbol names
            returns_data: Dictionary mapping symbols to return series

        Returns:
            DataFrame correlation matrix

        Raises:
            ValueError: If symbols not found in returns_data

        Examples:
            >>> corr_matrix = analyzer.get_correlation_matrix(
            ...     ["EUR/USD", "GBP/USD", "USD/JPY"],
            ...     returns_data
            ... )
        """
        # Collect series for all symbols
        series_dict = {}
        for symbol in symbols:
            if symbol not in returns_data:
                raise ValueError(f"Symbol {symbol} not found in returns_data")
            series = returns_data[symbol]
            if len(series) > self.lookback_days:
                series = series.tail(self.lookback_days)
            series_dict[symbol] = series

        # Create DataFrame
        df = pd.DataFrame(series_dict)

        # Calculate correlation matrix
        corr_matrix = df.corr(method="pearson")

        return corr_matrix

    def __str__(self) -> str:
        """Return string representation of analyzer."""
        return (
            f"CorrelationAnalyzer("
            f"lookback={self.lookback_days}, "
            f"min_corr={self.min_correlation}, "
            f"min_sig={self.min_significance})"
        )

    def __repr__(self) -> str:
        """Return detailed representation of analyzer."""
        return (
            f"CorrelationAnalyzer("
            f"lookback_days={self.lookback_days}, "
            f"min_correlation={self.min_correlation}, "
            f"min_significance={self.min_significance})"
        )
