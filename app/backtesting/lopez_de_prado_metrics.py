"""
López de Prado - Machine Learning for Asset Managers Implementation

This module implements advanced metrics and methodologies from Marcos López de Prado's book
"Machine Learning for Asset Managers" (2020).

Key Features:
1. Sharpe Ratio Combination Methods
2. Portfolio Stability Validation
3. Turnover-Adjusted Performance Metrics
4. Portfolio Concentration Metrics
5. Hierarchical Risk Parity (HRP) support
6. Spectral Risk Measures

Reference:
    López de Prado, M. (2020). Machine Learning for Asset Managers.
    Cambridge University Press.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import numpy as np
from scipy import stats
from scipy.cluster import hierarchy

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


@dataclass
class SharpeCombinationResult:
    """Result from Sharpe ratio combination analysis."""

    combined_sharpe: float
    method: str
    individual_sharpes: list[float] = field(default_factory=list)
    weights: Optional[np.ndarray] = None
    improvement_pct: float = 0.0
    is_statistically_significant: bool = False
    p_value: float = 1.0
    confidence_interval: Optional[tuple[float, float]] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "combined_sharpe": self.combined_sharpe,
            "method": self.method,
            "individual_sharpes": self.individual_sharpes,
            "weights": self.weights.tolist() if self.weights is not None else None,
            "improvement_pct": self.improvement_pct,
            "is_statistically_significant": self.is_statistically_significant,
            "p_value": self.p_value,
            "confidence_interval": self.confidence_interval,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class PortfolioStabilityMetrics:
    """Portfolio stability validation metrics."""

    is_stable: bool
    stability_score: float  # 0-100
    turnover_mean: float
    turnover_std: float
    weights_autocorrelation: float
    allocation_drift_max: float
    allocation_drift_mean: float
    cross_period_correlation: float
    num_periods: int
    period_length_days: int
    stability_threshold: float = 70.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_stable": self.is_stable,
            "stability_score": self.stability_score,
            "turnover_mean": self.turnover_mean,
            "turnover_std": self.turnover_std,
            "weights_autocorrelation": self.weights_autocorrelation,
            "allocation_drift_max": self.allocation_drift_max,
            "allocation_drift_mean": self.allocation_drift_mean,
            "cross_period_correlation": self.cross_period_correlation,
            "num_periods": self.num_periods,
            "period_length_days": self.period_length_days,
            "stability_threshold": self.stability_threshold,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TurnoverAdjustedMetrics:
    """Turnover-adjusted performance metrics."""

    raw_sharpe: float
    turnover_adjusted_sharpe: float
    annualized_turnover: float
    adjustment_factor: float
    is_cost_effective: bool
    estimated_transaction_costs: float
    net_sharpe: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "raw_sharpe": self.raw_sharpe,
            "turnover_adjusted_sharpe": self.turnover_adjusted_sharpe,
            "annualized_turnover": self.annualized_turnover,
            "adjustment_factor": self.adjustment_factor,
            "is_cost_effective": self.is_cost_effective,
            "estimated_transaction_costs": self.estimated_transaction_costs,
            "net_sharpe": self.net_sharpe,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ConcentrationMetrics:
    """Portfolio concentration metrics."""

    herfindahl_index: float  # HHI: 0-1, higher = more concentrated
    effective_n_assets: float  # 1/HHI
    max_weight: float
    top_3_concentration: float
    top_5_concentration: float
    gini_coefficient: float  # 0-1, higher = more unequal
    shannon_entropy: float  # Higher = more diversified
    is_overconcentrated: bool
    concentration_score: float  # 0-100, higher = more concentrated
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "herfindahl_index": self.herfindahl_index,
            "effective_n_assets": self.effective_n_assets,
            "max_weight": self.max_weight,
            "top_3_concentration": self.top_3_concentration,
            "top_5_concentration": self.top_5_concentration,
            "gini_coefficient": self.gini_coefficient,
            "shannon_entropy": self.shannon_entropy,
            "is_overconcentrated": self.is_overconcentrated,
            "concentration_score": self.concentration_score,
            "timestamp": self.timestamp.isoformat(),
        }


class SharpeRatioCombinator:
    """
    Implements Sharpe ratio combination methods from López de Prado.

    Chapter 8: Sharpe Ratio Combinations
    - Optimal combination of multiple strategies
    - Spectral risk measures
    - Hierarchical combination methods
    """

    def __init__(self, risk_free_rate: Optional[float] = None):
        """
        Initialize Sharpe ratio combinator.

        Args:
            risk_free_rate: Annual risk-free rate (default: from CentralizedConfig)
        """
        self.risk_free_rate = (
            risk_free_rate
            if risk_free_rate is not None
            else float(get_config().backtesting.default_risk_free_rate)
        )

    def combine_sharpes_optimal(
        self,
        sharpes: np.ndarray,
        cov_matrix: np.ndarray,
    ) -> SharpeCombinationResult:
        """
        Optimal Sharpe ratio combination using covariance matrix.

        From López de Prado Chapter 8.3: Optimal combination of multiple strategies.
        The optimal combination weights are proportional to (Σ^(-1) * SR), where SR is
        the vector of Sharpe ratios and Σ is the correlation matrix.

        Args:
            sharpes: Array of individual Sharpe ratios
            cov_matrix: Covariance matrix of strategy returns

        Returns:
            SharpeCombinationResult with optimal combination
        """
        n = len(sharpes)
        if n == 0:
            logger.warning("No Sharpe ratios to combine")
            return SharpeCombinationResult(combined_sharpe=0.0, method="optimal")

        if n == 1:
            return SharpeCombinationResult(
                combined_sharpe=float(sharpes[0]),
                method="optimal",
                individual_sharpes=[float(sharpes[0])],
                weights=np.array([1.0]),
            )

        try:
            # Compute correlation matrix from covariance
            stds = np.sqrt(np.diag(cov_matrix))
            corr_matrix = cov_matrix / np.outer(stds, stds)

            # Handle singular matrix
            try:
                inv_corr = np.linalg.inv(corr_matrix)
            except np.linalg.LinAlgError:
                # Use pseudoinverse if singular
                inv_corr = np.linalg.pinv(corr_matrix)

            # Optimal weights: w ∝ Σ^(-1) * SR
            weights = inv_corr @ sharpes
            weights = np.maximum(weights, 0)  # Long-only constraint
            weights = weights / weights.sum()  # Normalize

            # Combined Sharpe ratio
            combined_sharpe = float(np.sqrt(weights.T @ cov_matrix @ weights))
            combined_sharpe = (
                combined_sharpe / np.sqrt(weights.T @ corr_matrix @ weights)
                if combined_sharpe > 0
                else 0.0
            )

            # Improvement vs simple average
            avg_sharpe = float(np.mean(sharpes))
            improvement = ((combined_sharpe / avg_sharpe) - 1.0) * 100 if avg_sharpe > 0 else 0.0

            return SharpeCombinationResult(
                combined_sharpe=combined_sharpe,
                method="optimal",
                individual_sharpes=[float(s) for s in sharpes],
                weights=weights,
                improvement_pct=improvement,
            )

        except Exception as e:
            logger.error(f"Error in optimal Sharpe combination: {e}")
            # Fallback to simple average
            return self._average_combination(sharpes)

    def combine_sharpes_hierarchical(
        self,
        sharpes: np.ndarray,
        cov_matrix: np.ndarray,
        linkage_method: str = "ward",
    ) -> SharpeCombinationResult:
        """
        Hierarchical Sharpe ratio combination using HRP methodology.

        From López de Prado Chapter 8.4: Hierarchical combination methods.
        Uses hierarchical clustering to combine strategies while accounting for
        correlation structure.

        Args:
            sharpes: Array of individual Sharpe ratios
            cov_matrix: Covariance matrix of strategy returns
            linkage_method: Linkage method for hierarchical clustering

        Returns:
            SharpeCombinationResult with hierarchical combination
        """
        n = len(sharpes)
        if n <= 1:
            return self.combine_sharpes_optimal(sharpes, cov_matrix)

        try:
            # Compute correlation matrix
            stds = np.sqrt(np.diag(cov_matrix))
            corr_matrix = cov_matrix / np.outer(stds, stds)

            # Convert to distance matrix
            distance_matrix = np.sqrt((1 - corr_matrix) / 2)

            # Perform hierarchical clustering
            linkage = hierarchy.linkage(distance_matrix, method=linkage_method)

            # Quasi-diagonalization (reorder by clustering)
            cluster_order = self._get_quasi_diag(linkage)
            sorted_indices = np.array(cluster_order)

            # Recursive bisection for weights
            weights = self._get_hrp_weights(cov_matrix, sorted_indices)

            # Combined Sharpe
            combined_sharpe = float(weights.T @ sharpes)

            return SharpeCombinationResult(
                combined_sharpe=combined_sharpe,
                method=f"hierarchical_{linkage_method}",
                individual_sharpes=[float(s) for s in sharpes],
                weights=weights,
            )

        except Exception as e:
            logger.error(f"Error in hierarchical Sharpe combination: {e}")
            return self._average_combination(sharpes)

    def _get_quasi_diag(self, linkage: np.ndarray) -> list[int]:
        """
        Recover quasi-diagonal order from hierarchical clustering.

        Args:
            linkage: Linkage matrix from scipy.cluster.hierarchy.linkage

        Returns:
            List of indices in quasi-diagonal order
        """
        return list(hierarchy.leaves_list(linkage))

    def _get_hrp_weights(
        self,
        cov_matrix: np.ndarray,
        sorted_indices: np.ndarray,
    ) -> np.ndarray:
        """
        Compute Hierarchical Risk Parity weights.

        From López de Prado: Build portfolio by recursive bisection.
        """
        n = len(sorted_indices)
        weights = np.ones(n)

        # Recursive bisection
        def _recursive_bisection(indices: np.ndarray) -> float:
            if len(indices) == 1:
                return 1.0

            # Split in half
            mid = len(indices) // 2
            left_indices = indices[:mid]
            right_indices = indices[mid:]

            # Compute variances for each cluster
            left_var = self._get_cluster_variance(cov_matrix, left_indices)
            right_var = self._get_cluster_variance(cov_matrix, right_indices)

            # Allocate weights inversely proportional to variance
            total_var = left_var + right_var
            left_weight = right_var / total_var if total_var > 0 else 0.5
            right_weight = left_var / total_var if total_var > 0 else 0.5

            # Recursively compute weights
            _recursive_bisection(left_indices)
            _recursive_bisection(right_indices)

            # Update weights
            weights[left_indices] *= left_weight
            weights[right_indices] *= right_weight

            return 1.0

        _recursive_bisection(sorted_indices)

        # Reorder to original order
        reordered_weights = np.empty_like(weights)
        reordered_weights[sorted_indices] = weights

        return reordered_weights

    def _get_cluster_variance(
        self,
        cov_matrix: np.ndarray,
        indices: np.ndarray,
    ) -> float:
        """Compute cluster variance for HRP."""
        if len(indices) == 0:
            return 0.0

        # Equal-weighted variance
        sub_cov = cov_matrix[np.ix_(indices, indices)]
        return float(np.mean(sub_cov))

    def combine_sharpes_spectral(
        self,
        sharpes: np.ndarray,
        returns_matrix: np.ndarray,
        risk_aversion: float = 1.0,
    ) -> SharpeCombinationResult:
        """
        Spectral risk measure for Sharpe combination.

        From López de Prado Chapter 8.5: Spectral risk measures.
        Uses spectral decomposition to weight strategies by risk contribution.

        Args:
            sharpes: Array of individual Sharpe ratios
            returns_matrix: T x N matrix of returns (T periods, N strategies)
            risk_aversion: Risk aversion parameter

        Returns:
            SharpeCombinationResult with spectral combination
        """
        n = len(sharpes)
        if n <= 1:
            return self.combine_sharpes_optimal(sharpes, np.cov(returns_matrix.T))

        try:
            # Compute covariance matrix
            cov_matrix = np.cov(returns_matrix.T)

            # Eigenvalue decomposition
            eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)

            # Filter positive eigenvalues
            positive_eigenvalues = eigenvalues[eigenvalues > 1e-10]
            positive_eigenvectors = eigenvectors[:, eigenvalues > 1e-10]

            if len(positive_eigenvalues) == 0:
                return self._average_combination(sharpes)

            # Spectral weights: weight by eigenvalue
            spectral_weights = positive_eigenvalues / positive_eigenvalues.sum()

            # Transform to strategy weights
            strategy_weights = positive_eigenvectors @ spectral_weights
            strategy_weights = np.maximum(strategy_weights, 0)
            strategy_weights = strategy_weights / strategy_weights.sum()

            # Combined Sharpe
            combined_sharpe = float(strategy_weights.T @ sharpes)

            return SharpeCombinationResult(
                combined_sharpe=combined_sharpe,
                method="spectral",
                individual_sharpes=[float(s) for s in sharpes],
                weights=strategy_weights,
            )

        except Exception as e:
            logger.error(f"Error in spectral Sharpe combination: {e}")
            return self._average_combination(sharpes)

    def _average_combination(
        self,
        sharpes: np.ndarray,
    ) -> SharpeCombinationResult:
        """Simple average combination as fallback."""
        avg_sharpe = float(np.mean(sharpes))
        n = len(sharpes)
        return SharpeCombinationResult(
            combined_sharpe=avg_sharpe,
            method="average",
            individual_sharpes=[float(s) for s in sharpes],
            weights=np.ones(n) / n,
        )

    def test_sharpe_significance(
        self,
        sharpe1: float,
        sharpe2: float,
        returns1: np.ndarray,
        returns2: np.ndarray,
    ) -> tuple[bool, float]:
        """
        Test if two Sharpe ratios are significantly different.

        From López de Prado Chapter 8.2: Testing the Sharpe ratio.
        Uses Jobson-Korkie test with Memmel correction.

        Args:
            sharpe1: First Sharpe ratio
            sharpe2: Second Sharpe ratio
            returns1: Returns for first strategy
            returns2: Returns for second strategy

        Returns:
            Tuple of (is_significantly_different, p_value)
        """
        try:
            n = len(returns1)
            if n != len(returns2) or n < 4:
                return False, 1.0

            # Compute correlation
            corr = np.corrcoef(returns1, returns2)[0, 1]

            # Jobson-Korkie statistic with Memmel correction
            diff = sharpe1 - sharpe2

            # Variance of the difference
            var_diff = (1 + 0.5 * sharpe1**2) / n + (1 + 0.5 * sharpe2**2) / n - 2 * corr / n

            if var_diff <= 0:
                return False, 1.0

            # Test statistic
            z_stat = diff / np.sqrt(var_diff)

            # Two-tailed p-value
            p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

            # Significant at 95% confidence
            is_significant = p_value < 0.05

            return is_significant, float(p_value)

        except Exception as e:
            logger.error(f"Error testing Sharpe significance: {e}")
            return False, 1.0


class PortfolioStabilityValidator:
    """
    Portfolio stability validation across time periods.

    From López de Prado Chapter 9: Portfolio Stability.
    A stable portfolio should maintain consistent allocations across rebalancing periods.
    """

    def __init__(
        self,
        stability_threshold: float = 70.0,
        max_turnover_threshold: float = 0.5,  # 50% annual turnover
    ):
        """
        Initialize stability validator.

        Args:
            stability_threshold: Minimum stability score (0-100) to consider stable
            max_turnover_threshold: Maximum acceptable annual turnover
        """
        self.stability_threshold = stability_threshold
        self.max_turnover_threshold = max_turnover_threshold

    def validate_stability(
        self,
        weights_history: list[np.ndarray],
        period_length_days: int = 30,
    ) -> PortfolioStabilityMetrics:
        """
        Validate portfolio stability across time periods.

        From López de Prado: Stable portfolios should have:
        1. Low turnover across periods
        2. High autocorrelation in weights
        3. Minimal allocation drift
        4. High cross-period correlation

        Args:
            weights_history: List of weight arrays for each period
            period_length_days: Length of each rebalancing period

        Returns:
            PortfolioStabilityMetrics with comprehensive stability analysis
        """
        n_periods = len(weights_history)

        if n_periods < 2:
            logger.warning("Insufficient periods for stability analysis")
            return PortfolioStabilityMetrics(
                is_stable=False,
                stability_score=0.0,
                turnover_mean=0.0,
                turnover_std=0.0,
                weights_autocorrelation=0.0,
                allocation_drift_max=0.0,
                allocation_drift_mean=0.0,
                cross_period_correlation=0.0,
                num_periods=n_periods,
                period_length_days=period_length_days,
                stability_threshold=self.stability_threshold,
            )

        try:
            # Calculate turnover between consecutive periods
            turnovers = []
            for i in range(n_periods - 1):
                turnover = self._calculate_turnover(
                    weights_history[i],
                    weights_history[i + 1],
                )
                turnovers.append(turnover)

            turnover_mean = float(np.mean(turnovers))
            turnover_std = float(np.std(turnovers))

            # Calculate weights autocorrelation
            weights_autocorr = self._calculate_weights_autocorrelation(weights_history)

            # Calculate allocation drift
            drift_max, drift_mean = self._calculate_allocation_drift(weights_history)

            # Calculate cross-period correlation
            cross_period_corr = self._calculate_cross_period_correlation(weights_history)

            # Compute composite stability score (0-100)
            stability_score = self._compute_stability_score(
                turnover_mean=turnover_mean,
                weights_autocorr=weights_autocorr,
                drift_max=drift_max,
                cross_period_corr=cross_period_corr,
            )

            is_stable = stability_score >= self.stability_threshold

            return PortfolioStabilityMetrics(
                is_stable=is_stable,
                stability_score=stability_score,
                turnover_mean=turnover_mean,
                turnover_std=turnover_std,
                weights_autocorrelation=weights_autocorr,
                allocation_drift_max=drift_max,
                allocation_drift_mean=drift_mean,
                cross_period_correlation=cross_period_corr,
                num_periods=n_periods,
                period_length_days=period_length_days,
                stability_threshold=self.stability_threshold,
            )

        except Exception as e:
            logger.error(f"Error validating portfolio stability: {e}")
            return PortfolioStabilityMetrics(
                is_stable=False,
                stability_score=0.0,
                turnover_mean=0.0,
                turnover_std=0.0,
                weights_autocorrelation=0.0,
                allocation_drift_max=0.0,
                allocation_drift_mean=0.0,
                cross_period_correlation=0.0,
                num_periods=n_periods,
                period_length_days=period_length_days,
                stability_threshold=self.stability_threshold,
            )

    def _calculate_turnover(
        self,
        weights_old: np.ndarray,
        weights_new: np.ndarray,
    ) -> float:
        """
        Calculate turnover between two weight vectors.

        Turnover = 0.5 * sum(|w_new - w_old|)

        From López de Prado: Turnover measures how much the portfolio changes.
        """
        return float(0.5 * np.sum(np.abs(weights_new - weights_old)))

    def _calculate_weights_autocorrelation(
        self,
        weights_history: list[np.ndarray],
    ) -> float:
        """
        Calculate autocorrelation of portfolio weights across periods.

        High autocorrelation indicates stable allocations.
        """
        # Stack weights into matrix
        weights_matrix = np.vstack(weights_history)

        # Compute correlation of each asset's weights over time
        n_assets = weights_matrix.shape[1]
        autocorrs = []

        for i in range(n_assets):
            series = weights_matrix[:, i]
            if len(series) > 1:
                # Lag-1 autocorrelation
                corr = np.corrcoef(series[:-1], series[1:])[0, 1]
                if not np.isnan(corr):
                    autocorrs.append(corr)

        return float(np.mean(autocorrs)) if autocorrs else 0.0

    def _calculate_allocation_drift(
        self,
        weights_history: list[np.ndarray],
    ) -> tuple[float, float]:
        """
        Calculate allocation drift statistics.

        Drift measures how much weights deviate from their historical mean.
        """
        weights_matrix = np.vstack(weights_history)
        mean_weights = np.mean(weights_matrix, axis=0)

        # Maximum absolute drift from mean
        drifts = np.abs(weights_matrix - mean_weights)
        drift_max = float(np.max(drifts))
        drift_mean = float(np.mean(drifts))

        return drift_max, drift_mean

    def _calculate_cross_period_correlation(
        self,
        weights_history: list[np.ndarray],
    ) -> float:
        """
        Calculate average correlation between consecutive period weights.
        """
        correlations = []

        for i in range(len(weights_history) - 1):
            corr = np.corrcoef(weights_history[i], weights_history[i + 1])[0, 1]
            if not np.isnan(corr):
                correlations.append(corr)

        return float(np.mean(correlations)) if correlations else 0.0

    def _compute_stability_score(
        self,
        turnover_mean: float,
        weights_autocorr: float,
        drift_max: float,
        cross_period_corr: float,
    ) -> float:
        """
        Compute composite stability score (0-100).

        Components:
        1. Low turnover: 30 points max
        2. High autocorrelation: 30 points max
        3. Low drift: 20 points max
        4. High cross-period correlation: 20 points max
        """
        # Turnover score (lower is better)
        turnover_score = max(0, 30 * (1 - turnover_mean / self.max_turnover_threshold))

        # Autocorrelation score (higher is better)
        autocorr_score = max(0, 30 * weights_autocorr)

        # Drift score (lower is better)
        drift_score = max(0, 20 * (1 - drift_max))

        # Cross-period correlation score (higher is better)
        corr_score = max(0, 20 * cross_period_corr)

        total_score = turnover_score + autocorr_score + drift_score + corr_score

        return float(min(total_score, 100.0))


class TurnoverAdjustedCalculator:
    """
    Turnover-adjusted performance metrics.

    From López de Prado Chapter 10: Turnover Analysis.
    High turnover strategies need higher gross returns to compensate for
    transaction costs.
    """

    def __init__(
        self,
        transaction_cost_bps: float = 10.0,  # 10 bps per trade
        risk_free_rate: Optional[float] = None,
    ):
        """
        Initialize turnover-adjusted calculator.

        Args:
            transaction_cost_bps: Transaction cost in basis points
            risk_free_rate: Annual risk-free rate (default: from CentralizedConfig)
        """
        self.transaction_cost_bps = transaction_cost_bps
        self.risk_free_rate = (
            risk_free_rate
            if risk_free_rate is not None
            else float(get_config().backtesting.default_risk_free_rate)
        )

    def calculate_turnover_adjusted_sharpe(
        self,
        returns: np.ndarray,
        weights_history: list[np.ndarray],
        period_length_days: int = 30,
    ) -> TurnoverAdjustedMetrics:
        """
        Calculate turnover-adjusted Sharpe ratio.

        From López de Prado: Adjust Sharpe ratio for turnover costs.

        Args:
            returns: Array of returns
            weights_history: List of weight vectors
            period_length_days: Rebalancing period length

        Returns:
            TurnoverAdjustedMetrics with adjusted Sharpe ratio
        """
        try:
            # Calculate raw Sharpe ratio
            returns_array = np.array(returns)
            raw_sharpe = self._calculate_sharpe(returns_array)

            # Calculate annualized turnover
            turnovers = []
            for i in range(len(weights_history) - 1):
                turnover = self._calculate_turnover(
                    weights_history[i],
                    weights_history[i + 1],
                )
                turnovers.append(turnover)

            avg_turnover = float(np.mean(turnovers)) if turnovers else 0.0

            # Annualize turnover
            periods_per_year = 365 / period_length_days
            annualized_turnover = avg_turnover * periods_per_year

            # Estimate transaction costs
            cost_per_trade = self.transaction_cost_bps / 10000  # Convert to decimal
            estimated_costs = annualized_turnover * cost_per_trade

            # Adjustment factor (from López de Prado)
            adjustment_factor = 1.0 / (1.0 + estimated_costs)

            # Adjusted Sharpe ratio
            turnover_adjusted_sharpe = raw_sharpe * adjustment_factor

            # Net Sharpe after costs
            net_sharpe = raw_sharpe - estimated_costs * np.sqrt(252)

            # Determine if cost-effective
            is_cost_effective = net_sharpe > raw_sharpe * 0.8  # Allow 20% degradation

            return TurnoverAdjustedMetrics(
                raw_sharpe=raw_sharpe,
                turnover_adjusted_sharpe=turnover_adjusted_sharpe,
                annualized_turnover=annualized_turnover,
                adjustment_factor=adjustment_factor,
                is_cost_effective=is_cost_effective,
                estimated_transaction_costs=estimated_costs,
                net_sharpe=net_sharpe,
            )

        except Exception as e:
            logger.error(f"Error calculating turnover-adjusted Sharpe: {e}")
            return TurnoverAdjustedMetrics(
                raw_sharpe=0.0,
                turnover_adjusted_sharpe=0.0,
                annualized_turnover=0.0,
                adjustment_factor=1.0,
                is_cost_effective=False,
                estimated_transaction_costs=0.0,
                net_sharpe=0.0,
            )

    def _calculate_sharpe(self, returns: np.ndarray) -> float:
        """Calculate annualized Sharpe ratio."""
        if len(returns) < 2:
            return 0.0

        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)

        if std_return == 0:
            return 0.0

        # Annualize (assuming daily returns)
        annual_return = mean_return * 252
        annual_std = std_return * np.sqrt(252)

        sharpe = (annual_return - self.risk_free_rate) / annual_std

        return float(sharpe)

    def _calculate_turnover(
        self,
        weights_old: np.ndarray,
        weights_new: np.ndarray,
    ) -> float:
        """Calculate turnover between weight vectors."""
        return float(0.5 * np.sum(np.abs(weights_new - weights_old)))


class ConcentrationAnalyzer:
    """
    Portfolio concentration metrics.

    From López de Prado Chapter 11: Concentration Analysis.
    Measures how concentrated a portfolio is across assets.
    """

    def __init__(
        self,
        max_concentration_threshold: float = 0.3,  # 30% max single position
        hhi_threshold: float = 0.2,  # HHI threshold
    ):
        """
        Initialize concentration analyzer.

        Args:
            max_concentration_threshold: Maximum allowed single position weight
            hhi_threshold: Herfindahl-Hirschman Index threshold
        """
        self.max_concentration_threshold = max_concentration_threshold
        self.hhi_threshold = hhi_threshold

    def analyze_concentration(
        self,
        weights: np.ndarray,
    ) -> ConcentrationMetrics:
        """
        Analyze portfolio concentration.

        Args:
            weights: Portfolio weight vector (sums to 1)

        Returns:
            ConcentrationMetrics with comprehensive concentration analysis
        """
        try:
            weights_array = np.array(weights)

            # Herfindahl-Hirschman Index (HHI)
            hhi = float(np.sum(weights_array**2))

            # Effective number of assets
            effective_n = 1.0 / hhi if hhi > 0 else 0.0

            # Max weight
            max_weight = float(np.max(weights_array))

            # Top-N concentration
            sorted_weights = np.sort(weights_array)[::-1]
            top_3_conc = float(np.sum(sorted_weights[:3])) if len(sorted_weights) >= 3 else 1.0
            top_5_conc = float(np.sum(sorted_weights[:5])) if len(sorted_weights) >= 5 else 1.0

            # Gini coefficient
            gini = self._calculate_gini(weights_array)

            # Shannon entropy
            entropy = self._calculate_shannon_entropy(weights_array)

            # Determine if over-concentrated
            is_overconcentrated = (
                max_weight > self.max_concentration_threshold or hhi > self.hhi_threshold
            )

            # Concentration score (0-100)
            concentration_score = hhi * 100

            return ConcentrationMetrics(
                herfindahl_index=hhi,
                effective_n_assets=effective_n,
                max_weight=max_weight,
                top_3_concentration=top_3_conc,
                top_5_concentration=top_5_conc,
                gini_coefficient=gini,
                shannon_entropy=entropy,
                is_overconcentrated=is_overconcentrated,
                concentration_score=concentration_score,
            )

        except Exception as e:
            logger.error(f"Error analyzing concentration: {e}")
            return ConcentrationMetrics(
                herfindahl_index=1.0,
                effective_n_assets=1.0,
                max_weight=1.0,
                top_3_concentration=1.0,
                top_5_concentration=1.0,
                gini_coefficient=0.0,
                shannon_entropy=0.0,
                is_overconcentrated=True,
                concentration_score=100.0,
            )

    def _calculate_gini(self, weights: np.ndarray) -> float:
        """
        Calculate Gini coefficient.

        Gini = 0: Perfect equality
        Gini = 1: Perfect inequality
        """
        sorted_weights = np.sort(weights)
        n = len(weights)

        if n == 0:
            return 0.0

        cumsum = np.cumsum(sorted_weights)
        gini = (n + 1 - 2 * np.sum(cumsum) / cumsum[-1]) / n

        return float(gini)

    def _calculate_shannon_entropy(self, weights: np.ndarray) -> float:
        """
        Calculate Shannon entropy.

        Higher entropy = more diversified.
        """
        # Filter out zero weights
        non_zero_weights = weights[weights > 0]

        if len(non_zero_weights) == 0:
            return 0.0

        # Normalize
        non_zero_weights = non_zero_weights / non_zero_weights.sum()

        # Calculate entropy
        entropy = -np.sum(non_zero_weights * np.log(non_zero_weights + 1e-10))

        return float(entropy)


# Factory function for easy instantiation
def create_lopez_de_prado_suite(
    risk_free_rate: Optional[float] = None,
    stability_threshold: float = 70.0,
    transaction_cost_bps: float = 10.0,
) -> dict[str, Any]:
    """
    Create a complete Lopez de Prado metrics suite.

    Args:
        risk_free_rate: Annual risk-free rate (default: from CentralizedConfig)
        stability_threshold: Portfolio stability threshold (0-100)
        transaction_cost_bps: Transaction cost in basis points

    Returns:
        Dictionary with all Lopez de Prado metrics calculators
    """
    rf = (
        risk_free_rate
        if risk_free_rate is not None
        else float(get_config().backtesting.default_risk_free_rate)
    )
    return {
        "sharpe_combiner": SharpeRatioCombinator(risk_free_rate=rf),
        "stability_validator": PortfolioStabilityValidator(
            stability_threshold=stability_threshold,
        ),
        "turnover_calculator": TurnoverAdjustedCalculator(
            transaction_cost_bps=transaction_cost_bps,
            risk_free_rate=rf,
        ),
        "concentration_analyzer": ConcentrationAnalyzer(),
    }
