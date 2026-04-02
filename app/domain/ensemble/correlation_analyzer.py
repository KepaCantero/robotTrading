"""
Correlation Analyzer for Strategy Relationship Analysis.

This module provides tools for analyzing correlations between trading
strategies to identify redundancy and improve diversification.
"""

from __future__ import annotations

# mypy: ignore-errors
import logging
from decimal import Decimal
from typing import Any

import numpy as np

from app.domain.ensemble.models import CorrelationMetrics

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """Analyze correlations between trading strategies.

    This class provides methods for:
    - Calculating correlation matrices
    - Detecting redundant strategies (high correlation)
    - Computing effective number of independent bets
    - Analyzing diversification quality

    Example:
        >>> analyzer = CorrelationAnalyzer(
        ...     strategies=['momentum', 'mean_reversion', 'trend']
        ... )
        >>> metrics = analyzer.analyze_correlations(returns_data)
    """

    def __init__(
        self,
        strategies: list[str],
        correlation_threshold: float = 0.9,
        method: str = "pearson",
    ):
        """Initialize correlation analyzer.

        Args:
            strategies: List of strategy names
            correlation_threshold: Threshold for detecting redundancy
            method: Correlation method ('pearson', 'spearman', 'kendall')

        Raises:
            ValueError: If parameters are invalid
        """
        try:
            if not strategies or len(strategies) < 2:
                raise ValueError("At least 2 strategies required")

            if method not in ["pearson", "spearman", "kendall"]:
                raise ValueError(f"Invalid correlation method: {method}")

            if not (0 <= correlation_threshold <= 1):
                raise ValueError(
                    f"Correlation threshold must be between 0 and 1, got {correlation_threshold}"
                )

            self.strategies = strategies
            self.correlation_threshold = correlation_threshold
            self.method = method

        except (TypeError, AttributeError) as e:
            logger.error("CorrelationAnalyzer initialization failed", exc_info=True)
            raise ValueError(f"Invalid parameters: {e}") from e

    def analyze_correlations(self, returns_data: dict[str, np.ndarray]) -> CorrelationMetrics:
        """Analyze correlations between strategies.

        Args:
            returns_data: Historical returns for each strategy

        Returns:
            Correlation metrics

        Raises:
            ValueError: If data is invalid
        """
        try:
            # Validate input
            self._validate_returns_data(returns_data)

            # Calculate correlation matrix
            corr_matrix = self._calculate_correlation_matrix(returns_data)

            # Calculate statistics
            mean_corr, median_corr, max_corr, min_corr = self._calculate_correlation_stats(
                corr_matrix
            )

            # Detect redundant pairs
            redundant_pairs = self._detect_redundant_pairs(corr_matrix)

            # Calculate effective number of bets
            effective_n_bets = self._calculate_effective_number_bets(corr_matrix)

            # Calculate eigenvalues and condition number
            eigenvalues = self._calculate_eigenvalues(corr_matrix)
            condition_number = self._calculate_condition_number(eigenvalues)

            # Convert correlation matrix to dict format
            corr_matrix_dict = self._matrix_to_dict(corr_matrix)

            return CorrelationMetrics(
                correlation_matrix=corr_matrix_dict,
                mean_correlation=Decimal(str(mean_corr)),
                median_correlation=Decimal(str(median_corr)),
                max_correlation=Decimal(str(max_corr)),
                min_correlation=Decimal(str(min_corr)),
                redundant_pairs=redundant_pairs,
                effective_number_bets=effective_n_bets,
                eigenvalues=eigenvalues,
                condition_number=condition_number,
            )

        except Exception as e:
            logger.error("Correlation analysis failed", exc_info=True)
            raise RuntimeError(f"Correlation analysis failed: {e}") from e

    def _validate_returns_data(self, returns_data: dict[str, np.ndarray]) -> None:
        """Validate returns data.

        Args:
            returns_data: Returns data to validate

        Raises:
            ValueError: If data is invalid
        """
        if not returns_data:
            raise ValueError("Returns data cannot be empty")

        for strategy in self.strategies:
            if strategy not in returns_data:
                raise ValueError(f"Missing returns data for strategy: {strategy}")

            if not isinstance(returns_data[strategy], np.ndarray):
                raise ValueError(f"Returns for {strategy} must be numpy array")

            if len(returns_data[strategy]) < 2:
                raise ValueError(f"Insufficient data for {strategy}")

    def _calculate_correlation_matrix(self, returns_data: dict[str, np.ndarray]) -> np.ndarray:
        """Calculate correlation matrix.

        Args:
            returns_data: Historical returns for each strategy

        Returns:
            Correlation matrix as numpy array
        """
        try:
            # Stack returns
            returns_matrix = np.column_stack([returns_data[s] for s in self.strategies])

            # Calculate correlation based on method
            if self.method == "pearson":
                corr_matrix = np.corrcoef(returns_matrix, rowvar=False)
            elif self.method == "spearman":
                from scipy.stats import spearmanr

                corr_matrix, _ = spearmanr(returns_matrix, axis=0)
            elif self.method == "kendall":
                from scipy.stats import kendalltau

                n = len(self.strategies)
                corr_matrix = np.eye(n)

                for i in range(n):
                    for j in range(i + 1, n):
                        corr, _ = kendalltau(returns_matrix[:, i], returns_matrix[:, j])
                        corr_matrix[i, j] = corr
                        corr_matrix[j, i] = corr

            # Handle NaN values
            corr_matrix = np.nan_to_num(corr_matrix, nan=0.0)

            # Ensure diagonal is 1.0
            np.fill_diagonal(corr_matrix, 1.0)

            return corr_matrix

        except Exception:
            logger.error("Correlation matrix calculation failed", exc_info=True)
            # Fallback to identity matrix on error
            return np.eye(len(self.strategies))

    def _calculate_correlation_stats(
        self, corr_matrix: np.ndarray
    ) -> tuple[float, float, float, float]:
        """Calculate correlation statistics.

        Args:
            corr_matrix: Correlation matrix

        Returns:
            Tuple of (mean, median, max, min) correlations
        """
        try:
            # Extract upper triangular (excluding diagonal)
            n = len(self.strategies)
            upper_triangular = []

            for i in range(n):
                for j in range(i + 1, n):
                    upper_triangular.append(corr_matrix[i, j])

            if not upper_triangular:
                return 0.0, 0.0, 0.0, 0.0

            mean_corr = float(np.mean(upper_triangular))
            median_corr = float(np.median(upper_triangular))
            max_corr = float(np.max(upper_triangular))
            min_corr = float(np.min(upper_triangular))

            return mean_corr, median_corr, max_corr, min_corr

        except Exception:
            logger.error("Correlation stats calculation failed", exc_info=True)
            return 0.0, 0.0, 0.0, 0.0

    def _detect_redundant_pairs(self, corr_matrix: np.ndarray) -> list[tuple[str, str, float]]:
        """Detect redundant strategy pairs.

        Args:
            corr_matrix: Correlation matrix

        Returns:
            List of tuples (strategy1, strategy2, correlation)
        """
        try:
            redundant = []
            n = len(self.strategies)

            for i in range(n):
                for j in range(i + 1, n):
                    corr = abs(corr_matrix[i, j])

                    if corr >= self.correlation_threshold:
                        redundant.append((self.strategies[i], self.strategies[j], float(corr)))

            # Sort by correlation (descending)
            redundant.sort(key=lambda x: x[2], reverse=True)

            return redundant

        except Exception:
            logger.error("Redundant pair detection failed", exc_info=True)
            return []

    def _calculate_effective_number_bets(self, corr_matrix: np.ndarray) -> float:
        """Calculate effective number of independent bets.

        Effective N = n / (1 + (n-1) * average_correlation)

        Args:
            corr_matrix: Correlation matrix

        Returns:
            Effective number of independent bets
        """
        try:
            n = len(self.strategies)

            # Calculate average correlation
            upper_triangular = []
            for i in range(n):
                for j in range(i + 1, n):
                    upper_triangular.append(abs(corr_matrix[i, j]))

            if not upper_triangular:
                return float(n)

            avg_corr = np.mean(upper_triangular)

            # Calculate effective number
            effective_n = n / (1 + (n - 1) * avg_corr)

            return float(effective_n)

        except Exception:
            logger.error("Effective number of bets calculation failed", exc_info=True)
            return float(len(self.strategies))

    def _calculate_eigenvalues(self, corr_matrix: np.ndarray) -> list[float]:
        """Calculate eigenvalues of correlation matrix.

        Args:
            corr_matrix: Correlation matrix

        Returns:
            List of eigenvalues sorted in descending order
        """
        try:
            eigenvalues = np.linalg.eigvalsh(corr_matrix)
            eigenvalues = sorted(eigenvalues, reverse=True)
            return [float(ev) for ev in eigenvalues]

        except Exception:
            logger.error("Eigenvalue calculation failed", exc_info=True)
            return [1.0] * len(self.strategies)

    def _calculate_condition_number(self, eigenvalues: list[float]) -> float:
        """Calculate condition number of correlation matrix.

        Condition number = max(eigenvalue) / min(eigenvalue)
        High condition number indicates numerical instability.

        Args:
            eigenvalues: List of eigenvalues

        Returns:
            Condition number
        """
        try:
            if not eigenvalues or eigenvalues[-1] == 0:
                return float("inf")

            return eigenvalues[0] / eigenvalues[-1]

        except Exception:
            logger.error("Condition number calculation failed", exc_info=True)
            return 1.0

    def _matrix_to_dict(self, matrix: np.ndarray) -> dict[str, dict[str, Decimal]]:
        """Convert correlation matrix to nested dictionary.

        Args:
            matrix: Correlation matrix

        Returns:
            Nested dictionary of correlations
        """
        result = {}

        for i, strategy_i in enumerate(self.strategies):
            result[strategy_i] = {}

            for j, strategy_j in enumerate(self.strategies):
                result[strategy_i][strategy_j] = Decimal(str(matrix[i, j]))

        return result

    def get_most_correlated_pair(
        self, metrics: CorrelationMetrics
    ) -> tuple[str, str, float] | None:
        """Get the most correlated strategy pair.

        Args:
            metrics: Correlation metrics

        Returns:
            Tuple of (strategy1, strategy2, correlation) or None
        """
        if not metrics.redundant_pairs:
            return None

        return metrics.redundant_pairs[0]

    def get_least_correlated_pair(
        self, metrics: CorrelationMetrics
    ) -> tuple[str, str, float] | None:
        """Get the least correlated strategy pair.

        Args:
            metrics: Correlation metrics

        Returns:
            Tuple of (strategy1, strategy2, correlation) or None
        """
        try:
            corr_matrix = metrics.correlation_matrix
            min_corr = float(metrics.min_correlation)

            # Find pair with minimum correlation
            for i, strategy_i in enumerate(self.strategies):
                for j in range(i + 1, len(self.strategies)):
                    strategy_j = self.strategies[j]
                    corr = float(corr_matrix[strategy_i][strategy_j])

                    if abs(corr - min_corr) < 1e-6:
                        return (strategy_i, strategy_j, corr)

            return None

        except Exception:
            logger.error("Least correlated pair lookup failed", exc_info=True)
            return None

    def suggest_strategy_removal(
        self, metrics: CorrelationMetrics, max_to_remove: int = 1
    ) -> list[str]:
        """Suggest strategies to remove based on redundancy.

        Args:
            metrics: Correlation metrics
            max_to_remove: Maximum number of strategies to suggest removing

        Returns:
            List of strategy names to remove
        """
        try:
            if not metrics.redundant_pairs:
                return []

            # Count how many times each strategy appears in redundant pairs
            removal_scores = dict.fromkeys(self.strategies, 0)

            for s1, s2, corr in metrics.redundant_pairs:
                # Weight by correlation strength
                weight = corr
                removal_scores[s1] += weight
                removal_scores[s2] += weight

            # Sort by removal score
            sorted_strategies = sorted(removal_scores.items(), key=lambda x: x[1], reverse=True)

            # Return top N strategies to remove
            return [s[0] for s in sorted_strategies[:max_to_remove]]

        except Exception:
            logger.error("Redundant pair detection failed", exc_info=True)
            return []

    def calculate_portfolio_correlation(
        self,
        returns_data: dict[str, np.ndarray],
        weights: dict[str, float],
    ) -> float:
        """Calculate average portfolio correlation (weighted).

        Args:
            returns_data: Historical returns for each strategy
            weights: Strategy weights

        Returns:
            Weighted average correlation
        """
        try:
            # Calculate correlation matrix
            corr_matrix = self._calculate_correlation_matrix(returns_data)

            n = len(self.strategies)
            weighted_sum = 0.0
            weight_sum = 0.0

            for i in range(n):
                for j in range(i + 1, n):
                    weight = weights.get(self.strategies[i], 0) * weights.get(self.strategies[j], 0)
                    weighted_sum += weight * abs(corr_matrix[i, j])
                    weight_sum += weight

            if weight_sum == 0:
                return 0.0

            return weighted_sum / weight_sum

        except Exception:
            logger.error("Portfolio correlation calculation failed", exc_info=True)
            return 0.0

    def calculate_partial_correlation(
        self,
        returns_data: dict[str, np.ndarray],
        strategy1: str,
        strategy2: str,
    ) -> float:
        """Calculate partial correlation between two strategies.

        Partial correlation measures the relationship between two variables
        while controlling for the effects of all other variables.

        Args:
            returns_data: Historical returns
            strategy1: First strategy
            strategy2: Second strategy

        Returns:
            Partial correlation coefficient
        """
        try:
            if strategy1 not in self.strategies or strategy2 not in self.strategies:
                raise ValueError("Invalid strategy names")

            # Stack returns
            returns_matrix = np.column_stack([returns_data[s] for s in self.strategies])

            # Get indices
            idx1 = self.strategies.index(strategy1)
            idx2 = self.strategies.index(strategy2)

            # Calculate precision matrix (inverse of covariance)
            cov_matrix = np.cov(returns_matrix, rowvar=False)
            precision_matrix = np.linalg.inv(cov_matrix)

            # Partial correlation formula
            partial_corr = -precision_matrix[idx1, idx2] / np.sqrt(
                precision_matrix[idx1, idx1] * precision_matrix[idx2, idx2]
            )

            return float(partial_corr)

        except Exception:
            logger.error("Portfolio correlation calculation failed", exc_info=True)
            return 0.0

    def calculate_rolling_correlation(
        self,
        returns_data: dict[str, np.ndarray],
        window: int = 60,
    ) -> dict[str, dict[str, list[float]]]:
        """Calculate rolling correlations over time.

        Args:
            returns_data: Historical returns
            window: Rolling window size

        Returns:
            Dictionary of rolling correlations for each pair
        """
        try:
            if window < 2:
                raise ValueError("Window must be at least 2")

            # Stack returns
            returns_matrix = np.column_stack([returns_data[s] for s in self.strategies])

            n_strategies = len(self.strategies)
            n_periods = returns_matrix.shape[0]

            if n_periods < window:
                raise ValueError(
                    f"Insufficient data for rolling window. Need {window}, got {n_periods}"
                )

            rolling_correlations = {}

            for i in range(n_strategies):
                for j in range(i + 1, n_strategies):
                    s1 = self.strategies[i]
                    s2 = self.strategies[j]

                    corr_list = []

                    for t in range(window, n_periods):
                        window_returns = returns_matrix[t - window : t, :]
                        corr = np.corrcoef(window_returns[:, i], window_returns[:, j])[0, 1]

                        if not np.isnan(corr):
                            corr_list.append(float(corr))

                    key = f"{s1}_{s2}"
                    rolling_correlations[key] = corr_list

            return rolling_correlations

        except Exception:
            logger.error("Rolling correlation calculation failed", exc_info=True)
            return {}

    def get_correlation_summary(self, metrics: CorrelationMetrics) -> dict[str, Any]:
        """Get summary of correlation analysis.

        Args:
            metrics: Correlation metrics

        Returns:
            Summary dictionary
        """
        try:
            most_correlated = self.get_most_correlated_pair(metrics)
            least_correlated = self.get_least_correlated_pair(metrics)

            return {
                "num_strategies": len(self.strategies),
                "mean_correlation": float(metrics.mean_correlation),
                "median_correlation": float(metrics.median_correlation),
                "max_correlation": float(metrics.max_correlation),
                "min_correlation": float(metrics.min_correlation),
                "most_correlated_pair": most_correlated,
                "least_correlated_pair": least_correlated,
                "num_redundant_pairs": len(metrics.redundant_pairs),
                "effective_number_bets": metrics.effective_number_bets,
                "condition_number": metrics.condition_number,
                "diversification_quality": metrics.diversification_quality,
                "has_redundancy": metrics.has_redundancy,
                "is_well_conditioned": metrics.is_well_conditioned,
            }

        except Exception:
            logger.error("Rolling correlation calculation failed", exc_info=True)
            return {}

    def test_stability(
        self,
        returns_data: dict[str, np.ndarray],
        n_splits: int = 5,
    ) -> dict[str, float]:
        """Test stability of correlations over time.

        Splits data into n periods and calculates correlation in each period
        to measure stability.

        Args:
            returns_data: Historical returns
            n_splits: Number of time periods to test

        Returns:
            Dictionary with stability metrics
        """
        try:
            if n_splits < 2:
                raise ValueError("Need at least 2 splits for stability test")

            # Get minimum length
            min_length = min(len(returns_data[s]) for s in self.strategies)

            split_size = min_length // n_splits

            if split_size < 10:
                raise ValueError("Insufficient data for stability test")

            correlations_by_split = []

            for i in range(n_splits):
                start_idx = i * split_size
                end_idx = start_idx + split_size if i < n_splits - 1 else min_length

                # Get subset of data
                subset_data = {s: returns_data[s][start_idx:end_idx] for s in self.strategies}

                # Calculate correlation matrix
                corr_matrix = self._calculate_correlation_matrix(subset_data)

                # Get mean correlation
                n = len(self.strategies)
                corrs = [corr_matrix[i, j] for i in range(n) for j in range(i + 1, n)]
                correlations_by_split.append(np.mean(corrs))

            # Calculate stability metrics
            mean_corr = np.mean(correlations_by_split)
            std_corr = np.std(correlations_by_split)
            cv_corr = std_corr / mean_corr if mean_corr != 0 else float("inf")

            # Handle case where CV could be negative or mean is near zero
            stability_score = 1.0 / (1.0 + abs(cv_corr)) if mean_corr != 0 else 0.0

            return {
                "mean_correlation": float(mean_corr),
                "std_correlation": float(std_corr),
                "cv_correlation": float(abs(cv_corr)) if cv_corr >= 0 else 0.0,
                "min_correlation": float(min(correlations_by_split)),
                "max_correlation": float(max(correlations_by_split)),
                "stability_score": float(stability_score),  # Higher = more stable
            }

        except Exception:
            logger.error("Correlation stability analysis failed", exc_info=True)
            return {
                "mean_correlation": 0.0,
                "std_correlation": 0.0,
                "cv_correlation": 0.0,
                "stability_score": 0.0,
            }
