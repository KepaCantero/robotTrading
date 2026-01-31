"""
Covariance Calculator Domain Service - Covariance and correlation matrices

CovarianceCalculator provides domain logic for calculating covariance
and correlation matrices for portfolio optimization.

Reference: Rule 48-papers-markowitz (Markowitz Portfolio Selection)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class CovarianceResult:
    """Result of covariance calculation."""

    covariance_matrix: np.ndarray  # Covariance matrix
    correlation_matrix: np.ndarray  # Correlation matrix
    std_devs: np.ndarray  # Standard deviations
    means: np.ndarray  # Mean returns
    symbols: List[str]  # Asset symbols

    def get_covariance(self, symbol1: str, symbol2: str) -> Decimal:
        """Get covariance between two symbols."""
        try:
            idx1 = self.symbols.index(symbol1)
            idx2 = self.symbols.index(symbol2)
            return Decimal(str(self.covariance_matrix[idx1, idx2]))
        except ValueError:
            raise ValueError(f"Symbol not found in result")

    def get_correlation(self, symbol1: str, symbol2: str) -> Decimal:
        """Get correlation between two symbols."""
        try:
            idx1 = self.symbols.index(symbol1)
            idx2 = self.symbols.index(symbol2)
            return Decimal(str(self.correlation_matrix[idx1, idx2]))
        except ValueError:
            raise ValueError(f"Symbol not found in result")

    def get_std_dev(self, symbol: str) -> Decimal:
        """Get standard deviation for a symbol."""
        try:
            idx = self.symbols.index(symbol)
            return Decimal(str(self.std_devs[idx]))
        except ValueError:
            raise ValueError(f"Symbol not found in result")


class CovarianceCalculator:
    """
    Domain service for calculating covariance and correlation matrices.

    Provides pure domain logic for:
    - Sample covariance estimation
    - Shrinkage estimators
    - Exponential weighted covariance
    - Correlation matrix calculation

    Reference: Markowitz Portfolio Selection (paper 48)
    """

    # Default minimum observation period (252 trading days = 1 year)
    MIN_OBSERVATIONS = 252

    def __init__(
        self,
        min_observations: int = MIN_OBSERVATIONS,
        shrinkage: Optional[float] = None,
    ):
        """
        Initialize covariance calculator.

        Args:
            min_observations: Minimum number of observations required
            shrinkage: Shrinkage intensity (0-1). None = no shrinkage.
                        Recommended: 0.1 for Ledoit-Wolf
        """
        self._min_observations = min_observations
        self._shrinkage = shrinkage

    def calculate_sample_covariance(
        self,
        returns: Dict[str, List[Decimal]],
    ) -> CovarianceResult:
        """
        Calculate sample covariance matrix.

        Args:
            returns: Dictionary of symbol -> return series

        Returns:
            CovarianceResult with matrices and statistics

        Raises:
            ValueError: If insufficient data
        """
        # Validate input
        symbols = list(returns.keys())
        n_assets = len(symbols)

        if n_assets < 2:
            raise ValueError("Need at least 2 assets for covariance calculation")

        # Convert to numpy array
        returns_array = self._dict_to_array(returns, symbols)

        n_obs = returns_array.shape[0]
        if n_obs < self._min_observations:
            raise ValueError(f"Insufficient observations: {n_obs} < {self._min_observations}")

        # Calculate means
        means = np.mean(returns_array, axis=0)

        # Calculate covariance matrix (sample covariance)
        cov_matrix = np.cov(returns_array, rowvar=False, ddof=1)

        # Calculate correlation matrix
        std_devs = np.sqrt(np.diag(cov_matrix))
        corr_matrix = self._covariance_to_correlation(cov_matrix)

        return CovarianceResult(
            covariance_matrix=cov_matrix,
            correlation_matrix=corr_matrix,
            std_devs=std_devs,
            means=means,
            symbols=symbols,
        )

    def calculate_shrinkage_covariance(
        self,
        returns: Dict[str, List[Decimal]],
        shrinkage: Optional[float] = None,
    ) -> CovarianceResult:
        """
        Calculate shrinkage covariance matrix (Ledoit-Wolf).

        Shrinkage reduces estimation error by combining sample covariance
        with a structured estimator (constant correlation).

        Args:
            returns: Dictionary of symbol -> return series
            shrinkage: Shrinkage intensity (0-1). None = auto-calculate.

        Returns:
            CovarianceResult with shrunk covariance matrix
        """
        # Get sample covariance
        result = self.calculate_sample_covariance(returns)

        # Calculate shrinkage if not provided
        if shrinkage is None:
            shrinkage = self._ledoit_wolf_shrinkage(
                result.correlation_matrix,
                len(returns[result.symbols[0]]),
            )

        # Calculate structured estimator (constant correlation)
        n_assets = len(result.symbols)
        mean_corr = np.mean(result.correlation_matrix[np.triu_indices(n_assets, k=1)])

        # Create constant correlation matrix
        constant_corr = np.full((n_assets, n_assets), mean_corr)
        np.fill_diagonal(constant_corr, 1.0)

        # Convert back to covariance
        std_matrix = np.outer(result.std_devs, result.std_devs)
        structured_cov = constant_corr * std_matrix

        # Shrink: combine sample and structured
        shrunk_cov = (1 - shrinkage) * result.covariance_matrix + shrinkage * structured_cov

        # Update correlation matrix
        shrunk_corr = self._covariance_to_correlation(shrunk_cov)

        return CovarianceResult(
            covariance_matrix=shrunk_cov,
            correlation_matrix=shrunk_corr,
            std_devs=result.std_devs,
            means=result.means,
            symbols=result.symbols,
        )

    def calculate_exponential_covariance(
        self,
        returns: Dict[str, List[Decimal]],
        span: int = 60,
    ) -> CovarianceResult:
        """
        Calculate exponential-weighted covariance matrix.

        Gives more weight to recent observations, which is useful
        for adaptive portfolios.

        Args:
            returns: Dictionary of symbol -> return series
            span: Span for exponential decay (default ~60 trading days)

        Returns:
            CovarianceResult with EWMA covariance matrix
        """
        symbols = list(returns.keys())
        returns_array = self._dict_to_array(returns, symbols)

        # Calculate exponential weights
        n_obs = returns_array.shape[0]
        alpha = 2 / (span + 1)
        weights = np.array([(1 - alpha) ** (n_obs - 1 - i) for i in range(n_obs)])
        weights = weights / weights.sum()  # Normalize

        # Calculate weighted means
        weighted_means = np.average(returns_array, axis=0, weights=weights)

        # Calculate weighted covariance
        centered = returns_array - weighted_means
        weighted_cov = np.zeros((len(symbols), len(symbols)))

        for i in range(len(symbols)):
            for j in range(i, len(symbols)):
                cov = np.average(
                    centered[:, i] * centered[:, j],
                    weights=weights,
                )
                weighted_cov[i, j] = cov
                weighted_cov[j, i] = cov

        # Calculate correlation
        std_devs = np.sqrt(np.diag(weighted_cov))
        corr_matrix = self._covariance_to_correlation(weighted_cov)

        return CovarianceResult(
            covariance_matrix=weighted_cov,
            correlation_matrix=corr_matrix,
            std_devs=std_devs,
            means=weighted_means,
            symbols=symbols,
        )

    def get_positive_semidefinite_covariance(
        self,
        cov_matrix: np.ndarray,
    ) -> np.ndarray:
        """
        Ensure covariance matrix is positive semi-definite.

        Uses eigenvalue decomposition to remove negative eigenvalues.

        Args:
            cov_matrix: Input covariance matrix

        Returns:
            PSD covariance matrix
        """
        # Eigenvalue decomposition
        eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)

        # Clip negative eigenvalues
        eigenvalues = np.maximum(eigenvalues, 0)

        # Reconstruct matrix
        psd_matrix = eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T

        return psd_matrix

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    def _dict_to_array(
        self,
        returns: Dict[str, List[Decimal]],
        symbols: List[str],
    ) -> np.ndarray:
        """Convert returns dictionary to numpy array."""
        # Find minimum length
        min_len = min(len(returns[s]) for s in symbols)

        # Build array
        arrays = []
        for symbol in symbols:
            series = returns[symbol][-min_len:]  # Take most recent
            # Convert to float
            float_series = [float(r) for r in series]
            arrays.append(float_series)

        return np.column_stack(arrays)

    def _covariance_to_correlation(self, cov_matrix: np.ndarray) -> np.ndarray:
        """Convert covariance matrix to correlation matrix."""
        std_devs = np.sqrt(np.diag(cov_matrix))
        corr_matrix = cov_matrix / np.outer(std_devs, std_devs)
        # Ensure diagonal is exactly 1.0
        np.fill_diagonal(corr_matrix, 1.0)
        return corr_matrix

    def _correlation_to_covariance(
        self,
        corr_matrix: np.ndarray,
        std_devs: np.ndarray,
    ) -> np.ndarray:
        """Convert correlation matrix to covariance matrix."""
        return corr_matrix * np.outer(std_devs, std_devs)

    def _ledoit_wolf_shrinkage(
        self,
        corr_matrix: np.ndarray,
        n_obs: int,
    ) -> float:
        """
        Calculate optimal Ledoit-Wolf shrinkage intensity.

        Simplified calculation based on:
        Ledoit, O., & Wolf, M. (2004). "A well-conditioned estimator
        for large-dimensional covariance matrices."

        Args:
            corr_matrix: Sample correlation matrix
            n_obs: Number of observations

        Returns:
            Shrinkage intensity (0-1)
        """
        n_assets = corr_matrix.shape[0]

        # Calculate average correlation
        mean_corr = np.mean(corr_matrix[np.triu_indices(n_assets, k=1)])

        # Simplified shrinkage formula
        # Shrinkage decreases with more observations and more assets
        pi_term = n_assets / n_obs
        shrinkage = min(pi_term, 1.0)

        return float(shrinkage)

    def get_risk_contribution(
        self,
        weights: np.ndarray,
        cov_matrix: np.ndarray,
    ) -> np.ndarray:
        """
        Calculate risk contribution of each asset.

        Component contribution to portfolio volatility:
        RC_i = w_i * (Σw)_i / σ_p

        Args:
            weights: Portfolio weights
            cov_matrix: Covariance matrix

        Returns:
            Risk contribution for each asset
        """
        # Calculate marginal contribution to risk
        portfolio_var = weights @ cov_matrix @ weights
        portfolio_std = np.sqrt(portfolio_var)

        marginal_contrib = cov_matrix @ weights
        contrib = weights * marginal_contrib / portfolio_std

        return contrib

    def get_effective_number_bets(
        self,
        weights: np.ndarray,
        cov_matrix: np.ndarray,
    ) -> float:
        """
        Calculate effective number of uncorrelated bets.

        Measures diversification: how many independent positions
        the portfolio effectively holds.

        Args:
            weights: Portfolio weights
            cov_matrix: Covariance matrix

        Returns:
            Effective number of bets
        """
        # Calculate portfolio variance
        portfolio_var = weights @ cov_matrix @ weights

        # Calculate average variance
        avg_var = np.mean(np.diag(cov_matrix))

        # Effective number of bets
        # N* = (w'Σw) / (σ²_avg)
        enb = portfolio_var / avg_var if avg_var > 0 else 0

        return float(enb)
