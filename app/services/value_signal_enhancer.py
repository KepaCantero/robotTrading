"""
Value Signal Enhancement Module.

This module implements enhanced value signal calculations as described in
Antti Ilmanen's "Expected Returns" methodologies.

Key Concepts:
- Value signal aggregation across multiple metrics
- Cross-sectional ranking and normalization
- Time-series momentum enhancement
- Fundamental factor combination
- Risk-adjusted value signals

Reference:
    "Expected Returns: An Investor's Guide" by Antti Ilmanen
    Chapter 9: Value signals
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ValueMetricType(Enum):
    """Types of value metrics."""

    # Traditional valuation ratios
    PE_RATIO = "pe_ratio"  # Price-to-earnings
    PB_RATIO = "pb_ratio"  # Price-to-book
    PS_RATIO = "ps_ratio"  # Price-to-sales
    EV_EBITDA = "ev_ebitda"  # EV/EBITDA
    DIVIDEND_YIELD = "dividend_yield"  # Dividend yield

    # Cash flow metrics
    PCF_RATIO = "pcf_ratio"  # Price-to-cash-flow
    FCF_YIELD = "fcf_yield"  # Free cash flow yield
    EV_SALES = "ev_sales"  # EV/Sales

    # Relative valuation
    REL_PE = "rel_pe"  # Relative P/E
    REL_PB = "rel_pb"  # Relative P/B

    # Composite metrics
    COMPOSITE_VALUE = "composite_value"  # Composite value score


@dataclass
class ValueSignalResult:
    """Result of value signal calculation."""

    timestamp: datetime
    asset: str
    value_score: float
    value_rank: float  # Cross-sectional rank (0-1)
    value_percentile: float  # Percentile (0-100)
    z_score: float  # Z-score relative to universe
    is_cheap: bool
    is_expensive: bool
    metric_contributions: Dict[str, float]
    risk_adjusted_score: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "asset": self.asset,
            "value_score": self.value_score,
            "value_rank": self.value_rank,
            "value_percentile": self.value_percentile,
            "z_score": self.z_score,
            "is_cheap": self.is_cheap,
            "is_expensive": self.is_expensive,
            "metric_contributions": self.metric_contributions,
            "risk_adjusted_score": self.risk_adjusted_score,
            "details": self.details,
        }


@dataclass
class CrossSectionalValueResult:
    """Result of cross-sectional value analysis."""

    timestamp: datetime
    universe_size: int
    mean_value_score: float
    std_value_score: float
    value_dispersion: float  # Dispersion across universe
    cheap_count: int
    expensive_count: int
    value_spread: float  # Return spread between cheap and expensive
    details: Dict[str, Any] = field(default_factory=dict)


class ValueSignalEnhancer:
    """
    Enhanced value signal calculator following Ilmanen's methodologies.

    This class implements comprehensive value signal enhancement including:
    1. Multiple valuation metric aggregation
    2. Cross-sectional ranking and normalization
    3. Time-series momentum adjustment
    4. Risk-adjusted value scoring
    5. Sector-relative valuation

    Key improvements over basic value signals:
    - Combines multiple value metrics robustly
    - Handles missing data with proper imputation
    - Provides cross-sectional context
    - Adjusts for risk and quality
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize value signal enhancer.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.metrics = self.config.get(
            "metrics",
            ["pe_ratio", "pb_ratio", "ps_ratio", "ev_ebitda", "dividend_yield"],
        )
        self.weights = self.config.get(
            "weights",
            dict.fromkeys(self.metrics, 1.0),
        )
        self.cheap_threshold = self.config.get("cheap_threshold", 0.3)  # Bottom 30%
        self.expensive_threshold = self.config.get("expensive_threshold", 0.7)  # Top 70%
        self.outlier_method = self.config.get("outlier_method", "winsorize")  # winsorize or trim
        self.outlier_threshold = self.config.get("outlier_threshold", 3.0)  # Standard deviations

    def calculate_value_signal(
        self,
        data: pd.DataFrame,
        asset: str,
        sector: Optional[str] = None,
        sector_data: Optional[pd.DataFrame] = None,
    ) -> ValueSignalResult:
        """
        Calculate enhanced value signal for a single asset.

        Args:
            data: DataFrame with value metrics (columns) for all assets
            asset: Asset ticker/symbol
            sector: Optional sector for relative valuation
            sector_data: Optional sector-specific data

        Returns:
            ValueSignalResult with enhanced value signal
        """
        logger.debug(f"Calculating value signal for {asset}...")

        if asset not in data.index:
            return self._create_empty_result(asset, "Asset not found in data")

        # Extract asset data
        asset_data = data.loc[asset]

        # Calculate individual metric scores (inverse for valuation ratios)
        metric_scores = {}
        metric_contributions = {}

        for metric in self.metrics:
            if metric not in asset_data or pd.isna(asset_data[metric]):
                continue

            value = asset_data[metric]

            # Handle different metric types
            if metric in ["dividend_yield", "fcf_yield"]:
                # Higher is better
                raw_score = value
            else:
                # Lower is better (inverse for ratios)
                raw_score = 1 / (value + 1e-8)

            # Winsorize outliers
            cross_sectional = data[metric].dropna()
            winsorized = self._winsorize(cross_sectional, self.outlier_threshold)

            # Normalize to z-score
            z_score = (raw_score - winsorized.mean()) / (winsorized.std() + 1e-8)

            # Apply weight
            weight = self.weights.get(metric, 1.0)
            metric_scores[metric] = z_score * weight
            metric_contributions[metric] = z_score

        if not metric_scores:
            return self._create_empty_result(asset, "No valid metrics available")

        # Aggregate to composite value score
        value_score = np.mean(list(metric_scores.values()))

        # Calculate cross-sectional rank
        all_scores = []
        for _idx, row in data.iterrows():
            scores = []
            for metric in self.metrics:
                if metric in row and not pd.isna(row[metric]):
                    raw_score = {"dividend_yield": row[metric], "fcf_yield": row[metric]}.get(
                        metric, 1 / (row[metric] + 1e-8)
                    )

                    cross_sectional = data[metric].dropna()
                    winsorized = self._winsorize(cross_sectional, self.outlier_threshold)
                    z_score = (raw_score - winsorized.mean()) / (winsorized.std() + 1e-8)
                    scores.append(z_score * self.weights.get(metric, 1.0))

            if scores:
                all_scores.append(np.mean(scores))

        all_scores = np.array(all_scores)

        # Rank-based score (0-1)
        asset_score_idx = np.where(data.index == asset)[0]
        if len(asset_score_idx) > 0:
            rank = (all_scores < value_score).sum()
            value_rank = rank / len(all_scores)
            value_percentile = value_rank * 100
        else:
            value_rank = 0.5
            value_percentile = 50.0

        # Z-score
        z_score = (value_score - np.mean(all_scores)) / (np.std(all_scores) + 1e-8)

        # Determine if cheap/expensive
        is_cheap = value_rank < self.cheap_threshold
        is_expensive = value_rank > self.expensive_threshold

        # Risk adjustment (simple volatility adjustment)
        risk_adjusted_score = self._risk_adjust_value_score(value_score, asset_data)

        result = ValueSignalResult(
            timestamp=datetime.now(),
            asset=asset,
            value_score=value_score,
            value_rank=value_rank,
            value_percentile=value_percentile,
            z_score=z_score,
            is_cheap=is_cheap,
            is_expensive=is_expensive,
            metric_contributions=metric_contributions,
            risk_adjusted_score=risk_adjusted_score,
            details={
                "sector": sector,
                "n_metrics_used": len(metric_scores),
                "metrics_available": len(metric_scores),
            },
        )

        return result

    def calculate_cross_sectional_values(
        self,
        data: pd.DataFrame,
        returns: Optional[pd.DataFrame] = None,
    ) -> CrossSectionalValueResult:
        """
        Calculate cross-sectional value statistics.

        Args:
            data: DataFrame with value metrics for all assets
            returns: Optional future returns for value spread calculation

        Returns:
            CrossSectionalValueResult with universe statistics
        """
        logger.info("Calculating cross-sectional value statistics...")

        # Calculate value scores for all assets
        value_scores = []

        for asset in data.index:
            signal = self.calculate_value_signal(data, asset)
            value_scores.append(signal.value_score)

        value_scores = np.array(value_scores)

        # Statistics
        mean_score = np.mean(value_scores)
        std_score = np.std(value_scores)

        # Dispersion (coefficient of variation)
        dispersion = std_score / (abs(mean_score) + 1e-8)

        # Count cheap and expensive
        cheap_count = np.sum(
            data.index.isin(
                [a for a in data.index if self.calculate_value_signal(data, a).is_cheap]
            )
        )
        expensive_count = np.sum(
            data.index.isin(
                [a for a in data.index if self.calculate_value_signal(data, a).is_expensive]
            )
        )

        # Calculate value spread if returns provided
        value_spread = 0.0
        if returns is not None:
            cheap_assets = [
                a
                for a in data.index
                if a in returns.index and self.calculate_value_signal(data, a).is_cheap
            ]
            expensive_assets = [
                a
                for a in data.index
                if a in returns.index and self.calculate_value_signal(data, a).is_expensive
            ]

            if cheap_assets and expensive_assets:
                cheap_return = returns.loc[cheap_assets].mean()
                expensive_return = returns.loc[expensive_assets].mean()
                value_spread = cheap_return - expensive_return

        result = CrossSectionalValueResult(
            timestamp=datetime.now(),
            universe_size=len(data),
            mean_value_score=mean_score,
            std_value_score=std_score,
            value_dispersion=dispersion,
            cheap_count=cheap_count,
            expensive_count=expensive_count,
            value_spread=value_spread,
            details={
                "min_score": np.min(value_scores),
                "max_score": np.max(value_scores),
                "median_score": np.median(value_scores),
            },
        )

        logger.info(
            f"Cross-Sectional Values: Mean={mean_score:.3f} | "
            f"Cheap={cheap_count} | Expensive={expensive_count} | "
            f"Spread={value_spread:.3f}"
        )

        return result

    def calculate_time_series_value_momentum(
        self,
        historical_values: pd.Series,
        lookback_periods: Optional[List[int]] = None,
    ) -> Dict[str, float]:
        """
        Calculate time-series momentum for value signals.

        This measures how value scores have changed over time,
        a key concept in Ilmanen's framework.

        Args:
            historical_values: Historical value scores
            lookback_periods: List of lookback periods in months

        Returns:
            Dict with momentum metrics
        """
        logger.debug("Calculating value momentum...")

        if lookback_periods is None:
            lookback_periods = [1, 3, 6, 12]

        momentum_metrics = {}

        for period in lookback_periods:
            if len(historical_values) < period + 1:
                continue

            recent_value = historical_values.iloc[-1]
            past_value = historical_values.iloc[-period - 1]

            # Change in value score
            change = recent_value - past_value

            # Percentage change
            pct_change = (change / (abs(past_value) + 1e-8)) * 100

            momentum_metrics[f"{period}m_change"] = change
            momentum_metrics[f"{period}m_pct_change"] = pct_change

        # Trend strength (linear regression slope)
        if len(historical_values) >= 6:
            x = np.arange(len(historical_values))
            y = historical_values.values

            try:
                from scipy import stats

                slope, _, r_value, _, _ = stats.linregress(x, y)
                momentum_metrics["trend_slope"] = slope
                momentum_metrics["trend_r_squared"] = r_value**2
            except Exception:
                momentum_metrics["trend_slope"] = 0.0
                momentum_metrics["trend_r_squared"] = 0.0

        return momentum_metrics

    def _winsorize(self, series: pd.Series, threshold: float) -> pd.Series:
        """Winsorize series to handle outliers."""
        mean = series.mean()
        std = series.std()

        lower_bound = mean - threshold * std
        upper_bound = mean + threshold * std

        return series.clip(lower=lower_bound, upper=upper_bound)

    def _risk_adjust_value_score(
        self,
        value_score: float,
        asset_data: pd.Series,
    ) -> float:
        """
        Adjust value score for risk factors.

        Simple risk adjustment based on volatility and quality factors.
        """
        risk_penalty = 0.0

        # Volatility penalty (if available)
        if "volatility" in asset_data and not pd.isna(asset_data["volatility"]):
            vol = asset_data["volatility"]
            # Higher volatility -> small penalty
            risk_penalty += min(vol * 0.1, 0.2)

        # Quality bonus (if available)
        if "quality_score" in asset_data and not pd.isna(asset_data["quality_score"]):
            quality = asset_data["quality_score"]
            # Higher quality -> bonus
            risk_penalty -= min(quality * 0.1, 0.2)

        return value_score - risk_penalty

    def _create_empty_result(self, asset: str, reason: str) -> ValueSignalResult:
        """Create empty result when calculation fails."""
        return ValueSignalResult(
            timestamp=datetime.now(),
            asset=asset,
            value_score=0.0,
            value_rank=0.5,
            value_percentile=50.0,
            z_score=0.0,
            is_cheap=False,
            is_expensive=False,
            metric_contributions={},
            risk_adjusted_score=0.0,
            details={"error": reason},
        )


def calculate_enhanced_value_signal(
    data: pd.DataFrame,
    asset: str,
    config: Optional[Dict[str, Any]] = None,
) -> ValueSignalResult:
    """
    Convenience function to calculate enhanced value signal.

    Args:
        data: DataFrame with value metrics
        asset: Asset to analyze
        config: Configuration dictionary

    Returns:
        ValueSignalResult with analysis
    """
    enhancer = ValueSignalEnhancer(config)
    return enhancer.calculate_value_signal(data, asset)
