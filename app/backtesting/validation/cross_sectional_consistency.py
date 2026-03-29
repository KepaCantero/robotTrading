"""
Cross-Sectional Consistency Validation for Financial ML Models.

This module implements cross-sectional consistency checks as described in
Antti Ilmanen's "Expected Returns" methodologies.

Key Concepts:
- Cross-sectional signal consistency across assets
- Rank correlation validation
- Sector/regional consistency checks
- Time-stability of cross-sectional relationships
- Decile analysis for signal validation

Reference:
    "Expected Returns: An Investor's Guide" by Antti Ilmanen
    Chapter 4-5: Cross-sectional return predictors
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ConsistencyLevel(Enum):
    """Consistency assessment levels."""

    EXCELLENT = "excellent"  # IC > 0.1 or p-value < 0.01
    GOOD = "good"  # IC > 0.05 or p-value < 0.05
    MODERATE = "moderate"  # IC > 0.02 or p-value < 0.1
    WEAK = "weak"  # IC > 0 or p-value < 0.2
    POOR = "poor"  # IC <= 0 or p-value >= 0.2


@dataclass
class CrossSectionalResult:
    """Result of cross-sectional consistency analysis."""

    timestamp: datetime
    test_name: str
    consistency_level: ConsistencyLevel
    information_coefficient: float
    p_value: float
    rank_ic: float
    sample_size: int
    assets_tested: int
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "test_name": self.test_name,
            "consistency_level": self.consistency_level.value,
            "information_coefficient": self.information_coefficient,
            "p_value": self.p_value,
            "rank_ic": self.rank_ic,
            "sample_size": self.sample_size,
            "assets_tested": self.assets_tested,
            "details": self.details,
        }


@dataclass
class DecileAnalysisResult:
    """Result of decile analysis for signal validation."""

    timestamp: datetime
    signal_name: str
    decile_returns: dict[int, float]
    long_short_return: float
    monotonicity_score: float
    sharpe_ratio: float
    max_drawdown: float
    hit_rate: float
    is_monotonic: bool
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "signal_name": self.signal_name,
            "decile_returns": self.decile_returns,
            "long_short_return": self.long_short_return,
            "monotonicity_score": self.monotonicity_score,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "hit_rate": self.hit_rate,
            "is_monotonic": self.is_monotonic,
            "details": self.details,
        }


class CrossSectionalConsistencyChecker:
    """
    Cross-sectional consistency checker for financial signals.

    This class implements various tests to validate that signals are
    consistent across the cross-section of assets, as recommended by
    Antti Ilmanen's methodologies.

    Key validations:
    1. Information Coefficient (IC) analysis
    2. Rank correlation tests
    3. Decile analysis for monotonicity
    4. Sector/regional consistency
    5. Time-stability of cross-sectional relationships
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize cross-sectional consistency checker.

        Args:
            config: Configuration dictionary with parameters
        """
        self.config = config or {}
        self.ic_threshold_good = self.config.get("ic_threshold_good", 0.05)
        self.ic_threshold_excellent = self.config.get("ic_threshold_excellent", 0.10)
        self.p_value_threshold = self.config.get("p_value_threshold", 0.05)
        self.min_sample_size = self.config.get("min_sample_size", 50)
        self.n_deciles = self.config.get("n_deciles", 10)

        # History storage
        self._history: list[CrossSectionalResult] = []

    def validate_ic_consistency(
        self,
        signals: pd.DataFrame,
        returns: pd.DataFrame,
        periods: list[str] | None = None,
    ) -> CrossSectionalResult:
        """
        Validate Information Coefficient (IC) consistency.

        The IC measures the Spearman rank correlation between signals
        and subsequent returns. A key metric in Ilmanen's framework.

        Args:
            signals: DataFrame of signals (assets x time)
            returns: DataFrame of forward returns (assets x time)
            periods: List of time periods to test (default: all)

        Returns:
            CrossSectionalResult with IC analysis
        """
        logger.info("Validating IC consistency...")

        # Align data
        aligned_signals, aligned_returns = self._align_data(signals, returns)

        if periods is None:
            periods = aligned_signals.columns.tolist()

        ic_values = []
        rank_ic_values = []

        for period in periods:
            if period not in aligned_signals.columns or period not in aligned_returns.columns:
                continue

            signal_vals = aligned_signals[period].dropna()
            return_vals = aligned_returns[period].dropna()

            # Find common assets
            common_assets = signal_vals.index.intersection(return_vals.index)
            if len(common_assets) < self.min_sample_size:
                logger.warning(f"Insufficient samples for period {period}: {len(common_assets)}")
                continue

            # Calculate IC (Spearman correlation)
            ic = signal_vals[common_assets].corr(return_vals[common_assets], method="spearman")
            ic_values.append(ic)

            # Calculate Rank IC (Pearson on ranks)
            signal_ranks = signal_vals[common_assets].rank()
            return_ranks = return_vals[common_assets].rank()
            rank_ic = signal_ranks.corr(return_ranks, method="pearson")
            rank_ic_values.append(rank_ic)

        if not ic_values:
            return CrossSectionalResult(
                timestamp=datetime.now(),
                test_name="IC Consistency",
                consistency_level=ConsistencyLevel.POOR,
                information_coefficient=0.0,
                p_value=1.0,
                rank_ic=0.0,
                sample_size=0,
                assets_tested=0,
                details={"error": "No valid periods found"},
            )

        # Aggregate IC
        mean_ic = np.mean(ic_values)
        std_ic = np.std(ic_values)
        mean_rank_ic = np.mean(rank_ic_values)

        # Calculate t-statistic and p-value
        n = len(ic_values)
        t_stat = mean_ic / (std_ic / np.sqrt(n)) if std_ic > 0 else 0

        try:
            from scipy import stats

            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=n - 1))
        except Exception:
            p_value = 1.0

        # Determine consistency level
        if abs(mean_ic) >= self.ic_threshold_excellent and p_value < 0.01:
            consistency = ConsistencyLevel.EXCELLENT
        elif abs(mean_ic) >= self.ic_threshold_good and p_value < 0.05:
            consistency = ConsistencyLevel.GOOD
        elif abs(mean_ic) > 0.02 and p_value < 0.1:
            consistency = ConsistencyLevel.MODERATE
        elif abs(mean_ic) > 0 and p_value < 0.2:
            consistency = ConsistencyLevel.WEAK
        else:
            consistency = ConsistencyLevel.POOR

        result = CrossSectionalResult(
            timestamp=datetime.now(),
            test_name="IC Consistency",
            consistency_level=consistency,
            information_coefficient=mean_ic,
            p_value=p_value,
            rank_ic=mean_rank_ic,
            sample_size=n,
            assets_tested=len(common_assets),
            details={
                "ic_std": std_ic,
                "ic_values": ic_values,
                "t_statistic": t_stat,
                "ir": mean_ic / std_ic if std_ic > 0 else 0,  # Information Ratio
            },
        )

        self._history.append(result)

        logger.info(
            f"IC Consistency: {consistency.value} | IC={mean_ic:.4f} | p-value={p_value:.4f}"
        )

        return result

    def validate_decile_monotonicity(
        self,
        signals: pd.Series,
        returns: pd.Series,
        n_deciles: int | None = None,
    ) -> DecileAnalysisResult:
        """
        Validate signal monotonicity across deciles.

        This tests whether the signal exhibits monotonic return patterns
        across deciles, a key validation in Ilmanen's framework.

        Args:
            signals: Series of signal values by asset
            returns: Series of forward returns by asset
            n_deciles: Number of deciles to form (default: from config)

        Returns:
            DecileAnalysisResult with monotonicity analysis
        """
        n_deciles = n_deciles or self.n_deciles

        logger.info(f"Validating decile monotonicity ({n_deciles} deciles)...")

        # Align data
        common_assets = signals.index.intersection(returns.index)
        signals_aligned = signals[common_assets]
        returns_aligned = returns[common_assets]

        # Form deciles based on signal
        decile_labels = pd.qcut(
            signals_aligned,
            q=n_deciles,
            labels=False,
            duplicates="drop",
        )

        # Calculate returns by decile
        decile_returns = {}
        for decile in range(n_deciles):
            mask = decile_labels == decile
            if mask.sum() > 0:
                decile_return = returns_aligned[mask].mean()
                decile_returns[decile + 1] = decile_return  # 1-indexed

        # Calculate long-short return (top - bottom decile)
        long_short = decile_returns.get(n_deciles, 0) - decile_returns.get(1, 0)

        # Calculate monotonicity score
        monotonicity_score = self._calculate_monotonicity_score(list(decile_returns.values()))
        is_monotonic = monotonicity_score > 0.7

        # Calculate Sharpe ratio for long-short
        decile_df = pd.DataFrame({"decile": decile_labels, "return": returns_aligned})
        top_returns = decile_df[decile_df["decile"] == n_deciles - 1]["return"]
        bottom_returns = decile_df[decile_df["decile"] == 0]["return"]
        ls_returns = top_returns.values - bottom_returns.values

        sharpe = (
            np.mean(ls_returns) / np.std(ls_returns)
            if len(ls_returns) > 1 and np.std(ls_returns) > 0
            else 0
        )

        # Calculate max drawdown
        cumulative_returns = np.cumprod(1 + ls_returns) - 1
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / (running_max + 1e-8)
        max_drawdown = np.min(drawdown)

        # Calculate hit rate
        hit_rate = (ls_returns > 0).mean() if len(ls_returns) > 0 else 0

        result = DecileAnalysisResult(
            timestamp=datetime.now(),
            signal_name="decile_analysis",
            decile_returns=decile_returns,
            long_short_return=long_short,
            monotonicity_score=monotonicity_score,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            hit_rate=hit_rate,
            is_monotonic=is_monotonic,
            details={
                "n_deciles": n_deciles,
                "n_assets": len(common_assets),
                "assets_per_decile": len(common_assets) // n_deciles,
            },
        )

        logger.info(
            f"Decile Analysis: Long-Short={long_short:.4f} | "
            f"Monotonicity={monotonicity_score:.2f} | Sharpe={sharpe:.2f}"
        )

        return result

    def validate_sector_consistency(
        self,
        signals: pd.Series,
        returns: pd.Series,
        sectors: pd.Series,
        min_sectors: int = 3,
    ) -> dict[str, CrossSectionalResult]:
        """
        Validate signal consistency across sectors.

        Tests whether the signal performs consistently across different
        sectors, an important validation in Ilmanen's framework.

        Args:
            signals: Series of signal values by asset
            returns: Series of forward returns by asset
            sectors: Series of sector labels by asset
            min_sectors: Minimum number of sectors required

        Returns:
            Dict of CrossSectionalResult by sector
        """
        logger.info("Validating sector consistency...")

        results = {}

        # Get unique sectors
        unique_sectors = sectors.dropna().unique()

        if len(unique_sectors) < min_sectors:
            logger.warning(f"Insufficient sectors: {len(unique_sectors)} < {min_sectors}")
            return results

        for sector in unique_sectors:
            sector_mask = sectors == sector
            sector_signals = signals[sector_mask]
            sector_returns = returns[sector_mask]

            # Remove NaN values
            common_assets = sector_signals.dropna().index.intersection(
                sector_returns.dropna().index
            )

            if len(common_assets) < self.min_sample_size:
                logger.warning(f"Insufficient samples for sector {sector}: {len(common_assets)}")
                continue

            sector_signals_clean = sector_signals[common_assets]
            sector_returns_clean = sector_returns[common_assets]

            # Calculate IC for this sector
            ic = sector_signals_clean.corr(sector_returns_clean, method="spearman")

            # Calculate t-statistic
            n = len(common_assets)
            try:
                from scipy import stats

                # Fisher's z-transformation
                z = np.arctanh(ic)  # Fisher transformation
                se = 1 / np.sqrt(n - 3)
                t_stat = z / se
                p_value = 2 * (1 - stats.norm.cdf(abs(t_stat)))
            except Exception:
                p_value = 1.0

            # Determine consistency level
            if abs(ic) >= self.ic_threshold_excellent and p_value < 0.01:
                consistency = ConsistencyLevel.EXCELLENT
            elif abs(ic) >= self.ic_threshold_good and p_value < 0.05:
                consistency = ConsistencyLevel.GOOD
            elif abs(ic) > 0.02 and p_value < 0.1:
                consistency = ConsistencyLevel.MODERATE
            elif abs(ic) > 0 and p_value < 0.2:
                consistency = ConsistencyLevel.WEAK
            else:
                consistency = ConsistencyLevel.POOR

            results[sector] = CrossSectionalResult(
                timestamp=datetime.now(),
                test_name=f"Sector Consistency - {sector}",
                consistency_level=consistency,
                information_coefficient=ic,
                p_value=p_value,
                rank_ic=0.0,  # Not calculated for sector-level
                sample_size=n,
                assets_tested=len(common_assets),
                details={
                    "sector": sector,
                    "n_assets_in_sector": sector_mask.sum(),
                },
            )

        logger.info(f"Sector consistency validated for {len(results)} sectors")

        return results

    def validate_time_stability(
        self,
        signals: pd.DataFrame,
        returns: pd.DataFrame,
        window: int = 252,  # 1 year of daily data
        min_periods: int = 20,
    ) -> dict[str, Any]:
        """
        Validate time stability of cross-sectional relationships.

        Tests whether IC remains stable over time, crucial for
        signal reliability in Ilmanen's framework.

        Args:
            signals: DataFrame of signals (assets x time)
            returns: DataFrame of forward returns (assets x time)
            window: Rolling window size
            min_periods: Minimum periods for rolling calculation

        Returns:
            Dict with time stability analysis
        """
        logger.info("Validating time stability of IC...")

        # Align data
        aligned_signals, aligned_returns = self._align_data(signals, returns)

        # Calculate rolling IC
        rolling_ic = {}
        rolling_ic_values = []

        for col in aligned_signals.columns:
            if col not in aligned_returns.columns:
                continue

            signal_series = aligned_signals[col].dropna()
            return_series = aligned_returns[col].dropna()

            # Find common assets
            common_assets = signal_series.index.intersection(return_series.index)

            if len(common_assets) < self.min_sample_size:
                continue

            # Calculate IC for this period
            ic = signal_series[common_assets].corr(return_series[common_assets], method="spearman")
            rolling_ic[col] = ic
            rolling_ic_values.append(ic)

        if not rolling_ic_values:
            return {
                "mean_ic": 0.0,
                "std_ic": 0.0,
                "min_ic": 0.0,
                "max_ic": 0.0,
                "n_periods": 0,
                "is_stable": False,
                "details": {"error": "No valid periods found"},
            }

        ic_array = np.array(rolling_ic_values)

        # Calculate statistics
        mean_ic = np.mean(ic_array)
        std_ic = np.std(ic_array)
        min_ic = np.min(ic_array)
        max_ic = np.max(ic_array)

        # Stability test: IC should not change sign too frequently
        sign_changes = np.sum(np.diff(np.sign(ic_array)) != 0)
        sign_change_ratio = sign_changes / len(ic_array) if len(ic_array) > 1 else 0

        # Stability criterion: low std IC and low sign change ratio
        is_stable = std_ic < abs(mean_ic) * 2 and sign_change_ratio < 0.3

        result = {
            "mean_ic": mean_ic,
            "std_ic": std_ic,
            "min_ic": min_ic,
            "max_ic": max_ic,
            "n_periods": len(rolling_ic_values),
            "is_stable": is_stable,
            "sign_change_ratio": sign_change_ratio,
            "rolling_ic_by_period": rolling_ic,
            "details": {
                "window": window,
                "min_periods": min_periods,
                "stability_criteria": {
                    "std_ic_threshold": abs(mean_ic) * 2,
                    "sign_change_threshold": 0.3,
                },
            },
        }

        logger.info(
            f"Time Stability: Mean IC={mean_ic:.4f} | Std IC={std_ic:.4f} | Stable={is_stable}"
        )

        return result

    def _align_data(
        self,
        signals: pd.DataFrame | pd.Series,
        returns: pd.DataFrame | pd.Series,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Align signals and returns data."""
        if isinstance(signals, pd.Series):
            signals = signals.to_frame()
        if isinstance(returns, pd.Series):
            returns = returns.to_frame()

        # Align on index (assets)
        common_assets = signals.index.intersection(returns.index)
        signals_aligned = signals.loc[common_assets]
        returns_aligned = returns.loc[common_assets]

        return signals_aligned, returns_aligned

    def _calculate_monotonicity_score(self, returns: list[float]) -> float:
        """
        Calculate monotonicity score for decile returns.

        Args:
            returns: List of returns by decile (ordered)

        Returns:
            Monotonicity score (0-1, higher is more monotonic)
        """
        if len(returns) < 2:
            return 0.0

        # Count number of directional changes
        directional_changes = 0
        for i in range(len(returns) - 1):
            if (returns[i + 1] - returns[i]) * (returns[1] - returns[0]) < 0:
                directional_changes += 1

        # Max possible changes is n-1
        max_changes = len(returns) - 1

        # Monotonicity: 1 - (changes / max_changes)
        monotonicity = 1 - (directional_changes / max_changes)

        return monotonicity

    def get_history(self) -> list[CrossSectionalResult]:
        """Get analysis history."""
        return self._history.copy()

    def clear_history(self) -> None:
        """Clear analysis history."""
        self._history.clear()


def validate_cross_sectional_consistency(
    signals: pd.DataFrame | pd.Series,
    returns: pd.DataFrame | pd.Series,
    sectors: pd.Series | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Convenience function for comprehensive cross-sectional validation.

    Args:
        signals: Signal values (assets x time or Series for single period)
        returns: Forward returns (assets x time or Series for single period)
        sectors: Optional sector classifications
        config: Configuration dictionary

    Returns:
        Dict with all validation results
    """
    checker = CrossSectionalConsistencyChecker(config)

    results = {
        "ic_consistency": None,
        "decile_analysis": None,
        "sector_consistency": {},
        "time_stability": None,
    }

    # IC consistency
    if isinstance(signals, pd.DataFrame) and isinstance(returns, pd.DataFrame):
        results["ic_consistency"] = checker.validate_ic_consistency(signals, returns)
        results["time_stability"] = checker.validate_time_stability(signals, returns)

    # Decile analysis (for single period)
    if isinstance(signals, pd.Series) and isinstance(returns, pd.Series):
        results["decile_analysis"] = checker.validate_decile_monotonicity(signals, returns)

    # Sector consistency
    if sectors is not None and isinstance(signals, pd.Series):
        results["sector_consistency"] = checker.validate_sector_consistency(
            signals, returns, sectors
        )

    return results
