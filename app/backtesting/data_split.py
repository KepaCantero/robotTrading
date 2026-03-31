"""
Train/Validation/Test Split for Backtesting

Prevents overfitting and data snooping by properly splitting time-series data.

Now includes Purged K-Fold with Embargo cross-validation as described in:
"Advances in Financial Machine Learning" by Marcos López de Prado
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class DataSplit:
    """Configuration for data split."""

    def __init__(
        self,
        train_pct: float = 0.70,
        val_pct: float = 0.15,
        test_pct: float = 0.15,
        min_train_days: int = 252,  # 1 year of trading data
        # Purged K-Fold settings
        use_purged_kfold: bool = False,
        n_splits: int = 5,
        purge_pct: float = 0.05,
        embargo_pct: float = 0.02,
    ):
        """
        Initialize data split configuration.

        Args:
            train_pct: Percentage for training (default 70%)
            val_pct: Percentage for validation (default 15%)
            test_pct: Percentage for testing (default 15%)
            min_train_days: Minimum days for training set
            use_purged_kfold: Use Purged K-Fold cross-validation (López de Prado)
            n_splits: Number of folds for Purged K-Fold
            purge_pct: Percentage to purge before test set (default 5%)
            embargo_pct: Percentage to embargo after test set (default 2%)
        """
        if abs(train_pct + val_pct + test_pct - 1.0) > 0.01:
            raise ValueError("Split percentages must sum to 1.0")

        self.train_pct = train_pct
        self.val_pct = val_pct
        self.test_pct = test_pct
        self.min_train_days = min_train_days

        # Purged K-Fold settings
        self.use_purged_kfold = use_purged_kfold
        self.n_splits = n_splits
        self.purge_pct = purge_pct
        self.embargo_pct = embargo_pct


class TrainValTestSplitter:
    """
    Splits time-series data into train/validation/test sets.

    Uses time-based splitting (not random) to preserve temporal order
    and prevent look-ahead bias.
    """

    def __init__(self, split_config: Optional[DataSplit] = None):
        """
        Initialize train/validation/test splitter.

        Args:
            split_config: DataSplit configuration (uses defaults if None)
        """
        self.config = split_config or DataSplit()

    def split_data(
        self,
        market_data: list,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> tuple[list, list, list]:
        """
        Split market data into train/validation/test sets.

        Args:
            market_data: List of market data bars
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Tuple of (train_data, val_data, test_data)
        """
        if not market_data:
            raise ValueError("Market data is empty")

        # Sort by timestamp
        sorted_data = sorted(market_data, key=lambda x: x.timestamp)

        # Apply date filters if specified
        if start_date:
            sorted_data = [x for x in sorted_data if x.timestamp >= start_date]
        if end_date:
            sorted_data = [x for x in sorted_data if x.timestamp <= end_date]

        if not sorted_data:
            raise ValueError("No data after applying date filters")

        total_bars = len(sorted_data)

        # Check minimum requirements
        if total_bars < self.config.min_train_days:
            logger.warning(
                f"Insufficient data for training: {total_bars} bars < "
                f"{self.config.min_train_days} minimum"
            )

        # Calculate split indices (time-based, preserves temporal order)
        train_end_idx = int(total_bars * self.config.train_pct)
        val_end_idx = int(total_bars * (self.config.train_pct + self.config.val_pct))

        train_data = sorted_data[:train_end_idx]
        val_data = sorted_data[train_end_idx:val_end_idx]
        test_data = sorted_data[val_end_idx:]

        logger.info(
            f"Data split: Train={len(train_data)} bars ({len(train_data) / total_bars:.1%}), "
            f"Val={len(val_data)} bars ({len(val_data) / total_bars:.1%}), "
            f"Test={len(test_data)} bars ({len(test_data) / total_bars:.1%})"
        )

        return train_data, val_data, test_data

    def walk_forward_split(
        self,
        market_data: list,
        window_size: int = 252,  # 1 year
        step_size: int = 63,  # 3 months
    ) -> list[tuple[list, list, list]]:
        """
        Create multiple train/val/test splits for walk-forward validation.

        This creates rolling windows for more robust validation.

        Args:
            market_data: List of market data bars
            window_size: Size of each window (default 252 trading days)
            step_size: Step size for rolling (default 63 trading days = 3 months)

        Returns:
            List of (train_data, val_data, test_data) tuples
        """
        sorted_data = sorted(market_data, key=lambda x: x.timestamp)
        total_bars = len(sorted_data)

        if total_bars < window_size * 3:
            logger.warning(
                f"Insufficient data for walk-forward: {total_bars} bars < {window_size * 3} minimum"
            )
            return []

        splits = []

        for start_idx in range(0, total_bars - window_size * 3, step_size):
            end_idx = start_idx + window_size

            if end_idx > total_bars:
                break

            # Split window: 70% train, 15% val, 15% test
            window_data = sorted_data[start_idx:end_idx]
            train_end = int(window_size * self.config.train_pct)
            val_end = int(window_size * (self.config.train_pct + self.config.val_pct))

            train = window_data[:train_end]
            val = window_data[train_end:val_end]
            test = window_data[val_end:]

            splits.append((train, val, test))

        logger.info(f"Created {len(splits)} walk-forward windows")
        return splits

    def purged_kfold_split(
        self,
        market_data: list,
    ) -> list[tuple[list, list]]:
        """
        Create purged K-Fold splits for cross-validation.

        This implements López de Prado's method to prevent look-ahead bias
        in financial ML backtesting.

        Args:
            market_data: List of market data bars

        Returns:
            List of (train_data, test_data) tuples with purged splits
        """
        from app.backtesting.validation.purged_kfold import PurgedKFold

        # Convert market data to array for indexing
        sorted_data = sorted(market_data, key=lambda x: x.timestamp)
        n_samples = len(sorted_data)

        # Create PurgedKFold splitter
        purged_cv = PurgedKFold(
            n_splits=self.config.n_splits,
            purge_pct=self.config.purge_pct,
            embargo_pct=self.config.embargo_pct,
            min_train_samples=self.config.min_train_days,
            min_test_samples=20,
        )

        # Generate splits
        splits = purged_cv.split(np.arange(n_samples))

        # Convert indices back to market data
        purged_splits = []
        for train_idx, test_idx in splits:
            train_data = [sorted_data[i] for i in train_idx]
            test_data = [sorted_data[i] for i in test_idx]
            purged_splits.append((train_data, test_data))

        logger.info(
            f"Created {len(purged_splits)} purged K-Fold splits "
            f"(purge={self.config.purge_pct:.1%}, embargo={self.config.embargo_pct:.1%})"
        )

        return purged_splits

    def purged_kfold_split_with_validation(
        self,
        market_data: list,
    ) -> list[tuple[list, list, list]]:
        """
        Create purged K-Fold splits with train/validation/test sets.

        This extends purged K-Fold to include a validation set by
        splitting the training set further.

        Args:
            market_data: List of market data bars

        Returns:
            List of (train_data, val_data, test_data) tuples
        """
        from app.backtesting.validation.purged_kfold import PurgedKFold

        sorted_data = sorted(market_data, key=lambda x: x.timestamp)
        n_samples = len(sorted_data)

        purged_cv = PurgedKFold(
            n_splits=self.config.n_splits,
            purge_pct=self.config.purge_pct,
            embargo_pct=self.config.embargo_pct,
            min_train_samples=self.config.min_train_days,
            min_test_samples=20,
        )

        splits = purged_cv.split(np.arange(n_samples))

        purged_splits = []
        for train_idx, test_idx in splits:
            # Further split training data into train/validation
            n_train = len(train_idx)
            val_start_idx = int(
                n_train * (1 - self.config.val_pct / (self.config.train_pct + self.config.val_pct))
            )

            train_indices = train_idx[:val_start_idx]
            val_indices = train_idx[val_start_idx:]

            train_data = [sorted_data[i] for i in train_indices]
            val_data = [sorted_data[i] for i in val_indices]
            test_data = [sorted_data[i] for i in test_idx]

            purged_splits.append((train_data, val_data, test_data))

        logger.info(
            f"Created {len(purged_splits)} purged K-Fold splits with validation "
            f"(purge={self.config.purge_pct:.1%}, embargo={self.config.embargo_pct:.1%})"
        )

        return purged_splits


class MultipleTestingCorrector:
    """
    Applies statistical corrections for multiple testing.

    Prevents data snooping by adjusting confidence intervals
    when testing multiple parameter combinations.
    """

    def __init__(self, num_tests: int, base_confidence: float = 0.95):
        """
        Initialize multiple testing corrector.

        Args:
            num_tests: Number of tests performed
            base_confidence: Base confidence level (default 95%)
        """
        self.num_tests = num_tests
        self.base_confidence = base_confidence

    def bonferroni_correction(self) -> float:
        """
        Apply Bonferroni correction for multiple testing.

        More conservative, controls family-wise error rate.

        Returns:
            Adjusted confidence level
        """
        adjusted = self.base_confidence / self.num_tests
        logger.info(
            f"Bonferroni correction: {self.base_confidence:.2%} → {adjusted:.4%} "
            f"({self.num_tests} tests)"
        )
        return adjusted

    def benjamini_hochberg_correction(self, p_values: list[float]) -> list[bool]:
        """
        Apply Benjamini-Hochberg procedure for false discovery rate.

        Less conservative than Bonferroni, controls false discovery rate.

        Args:
            p_values: List of p-values from tests

        Returns:
            List of booleans indicating which tests are significant
        """
        if not p_values:
            return []

        # Sort p-values
        sorted_indices = sorted(range(len(p_values)), key=lambda i: p_values[i])
        sorted_p_values = [p_values[i] for i in sorted_indices]

        # Calculate BH critical values
        significant = [False] * len(p_values)

        for rank, p_value in enumerate(sorted_p_values, 1):
            critical_value = (rank / len(p_values)) * 0.05  # 5% FDR
            if p_value <= critical_value:
                significant[sorted_indices[rank - 1]] = True
            else:
                # Stop at first non-significant
                break

        num_significant = sum(significant)
        logger.info(
            f"Benjamini-Hochberg: {num_significant}/{len(p_values)} tests significant "
            f"at 5% FDR level"
        )

        return significant

    def holm_bonferroni_correction(self, p_values: list[float]) -> list[bool]:
        """
        Apply Holm-Bonferroni step-down procedure.

        Less conservative than Bonferroni, more powerful than Bonferroni.

        Args:
            p_values: List of p-values from tests

        Returns:
            List of booleans indicating which tests are significant
        """
        if not p_values:
            return []

        # Sort p-values
        sorted_indices = sorted(range(len(p_values)), key=lambda i: p_values[i])
        sorted_p_values = [p_values[i] for i in sorted_indices]

        # Step-down procedure
        significant = [False] * len(p_values)

        for rank, p_value in enumerate(sorted_p_values, 1):
            critical_value = 0.05 / (len(p_values) - rank + 1)
            if p_value <= critical_value:
                significant[sorted_indices[rank - 1]] = True
            else:
                # Stop at first non-significant
                break

        num_significant = sum(significant)
        logger.info(
            f"Holm-Bonferroni: {num_significant}/{len(p_values)} tests significant at 5% level"
        )

        return significant


def validate_out_of_sample_performance(
    train_sharpe: float, val_sharpe: float, test_sharpe: float, min_performance_ratio: float = 0.7
) -> bool:
    """
    Validate that out-of-sample performance is acceptable.

    Helps detect overfitting by ensuring test performance isn't
    significantly worse than validation performance.

    Args:
        train_sharpe: Sharpe ratio on training set
        val_sharpe: Sharpe ratio on validation set
        test_sharpe: Sharpe ratio on test set
        min_performance_ratio: Minimum acceptable ratio (default 0.7)

    Returns:
        True if performance is acceptable, False otherwise
    """
    # Check that test Sharpe >= min_ratio * val Sharpe
    if test_sharpe < val_sharpe * min_performance_ratio:
        logger.warning(
            f"⚠️ OOS degradation: Test Sharpe ({test_sharpe:.2f}) is "
            f"less than {min_performance_ratio:.0%} of Val Sharpe ({val_sharpe:.2f})"
        )
        return False

    # Also check that test Sharpe is positive if val Sharpe is positive
    if val_sharpe > 0 and test_sharpe < 0:
        logger.warning(
            f"⚠️ Sign flip: Val Sharpe ({val_sharpe:.2f}) is positive "
            f"but Test Sharpe ({test_sharpe:.2f}) is negative"
        )
        return False

    logger.info(
        f"✅ OOS validation passed: Train={train_sharpe:.2f}, "
        f"Val={val_sharpe:.2f}, Test={test_sharpe:.2f}"
    )
    return True
