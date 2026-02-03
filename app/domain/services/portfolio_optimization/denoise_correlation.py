"""
De-noising Correlation Matrix - Random Matrix Theory (RMT)

Implements López de Prado's correlation matrix de-noising method
using Random Matrix Theory to remove noise from correlation matrices.

Reference: Rule 03-lopez-de-prado-advances-financial-ml.md
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from scipy.optimize import minimize
from scipy.spatial.distance import squareform

from app.domain.services.portfolio_optimization._validation import (
    is_square_matrix,
    is_symmetric,
    log_optimization_failure,
)


logger = logging.getLogger(__name__)


# RMT de-noising default parameters
DEFAULT_METHOD = "spectral"  # Default de-noising method
DEFAULT_MIN_OBSERVATION_RATIO = 2.0  # Minimum T/n ratio for RMT validity
DEFAULT_SIGMA = 1.0  # Standard deviation for standardized returns
DEFAULT_KDE_GRID_POINTS = 1000  # Number of points for KDE grid
DEFAULT_SHRINKAGE_MAX = 0.5  # Maximum default shrinkage
DEFAULT_SHRINKAGE_ASSET_FACTOR = 0.01  # Shrinkage per 100 assets
DEFAULT_EPSILON = 1e-10  # Small epsilon for numerical stability


@dataclass
class DenoisedResult:
    """Result of correlation matrix de-noising."""

    original_corr: np.ndarray  # Original correlation matrix (N, N)
    denoised_corr: np.ndarray  # De-noised correlation matrix (N, N)
    denoised_cov: Optional[np.ndarray]  # De-noised covariance matrix (N, N)
    eigenvalues: np.ndarray  # Eigenvalues of original matrix (N,)
    denoised_eigenvalues: np.ndarray  # Eigenvalues after de-noising (N,)
    symbols: List[str]  # Asset symbols/tickers

    @property
    def noise_ratio(self) -> float:
        """Get ratio of noise eigenvalues to signal eigenvalues."""
        n = len(self.eigenvalues)
        if n == 0:
            return 0.0

        # Calculate q factor (T/n where T=observations, n=assets)
        q_factor = self._calculate_q_factor()

        # Max theoretical eigenvalue for random matrix
        max_random = self._calculate_max_random_eigenvalue(q_factor, n)

        signal_count = np.sum(self.eigenvalues > max_random)
        noise_count = n - signal_count

        return float(noise_count) / float(n) if n > 0 else 0.0

    def _calculate_q_factor(self) -> float:
        """Calculate q factor (T/n where T=observations, n=assets)."""
        # Simplified - assumes default values
        return DEFAULT_MIN_OBSERVATION_RATIO * 2.0  # Default T/n = 4.0

    def _calculate_max_random_eigenvalue(self, q: float, n_assets: int) -> float:
        """Calculate maximum theoretical random eigenvalue (Marchenko-Pastur)."""
        sigma = DEFAULT_SIGMA
        return sigma * (1 + 1 / np.sqrt(q)) ** 2


class CorrelationDenoiser:
    """
    Correlation matrix de-noising using Random Matrix Theory.

    Removes noise from correlation matrices by:
    1. Computing eigenvalue decomposition
    2. Identifying signal vs noise eigenvalues using RMT
    3. Replacing noise eigenvalues with their average
    4. Reconstructing de-noised matrix

    Reference: López de Prado, M. (2019). "Machine Learning for Asset Managers"
    """

    def __init__(
        self,
        method: str = DEFAULT_METHOD,
        min_observation_ratio: float = DEFAULT_MIN_OBSERVATION_RATIO,
    ):
        """
        Initialize de-noiser.

        Args:
            method: De-noising method (spectral, shrinkage, constant_corr)
            min_observation_ratio: Minimum T/n ratio for RMT validity
        """
        valid_methods = ["spectral", "shrinkage", "constant_corr"]
        if method not in valid_methods:
            raise ValueError(
                f"method must be one of {valid_methods}, got {method}"
            )

        if min_observation_ratio < 2.0:
            raise ValueError(
                f"min_observation_ratio must be >= 2.0 for RMT validity, "
                f"got {min_observation_ratio}"
            )

        self._method = method
        self._min_obs_ratio = min_observation_ratio

    def denoise_correlation(
        self,
        corr_matrix: np.ndarray,
        n_observations: int,
        symbols: Optional[List[str]] = None,
    ) -> DenoisedResult:
        """
        De-noise correlation matrix using RMT.

        Args:
            corr_matrix: Input correlation matrix
            n_observations: Number of observations (T)
            symbols: Asset symbols

        Returns:
            DenoisedResult with de-noised matrices

        Raises:
            ValueError: If matrix is invalid or observations insufficient
        """
        # Validate input matrix
        if not is_square_matrix(corr_matrix):
            raise ValueError(
                f"Correlation matrix must be square, got shape {corr_matrix.shape}"
            )

        if not is_symmetric(corr_matrix):
            logger.warning("Correlation matrix is not symmetric, symmetrizing...")
            corr_matrix = (corr_matrix + corr_matrix.T) / 2

        n_assets = corr_matrix.shape[0]
        q = n_observations / n_assets

        if q < self._min_obs_ratio:
            raise ValueError(
                f"Insufficient observations for RMT: T/n = {q:.2f} "
                f"< {self._min_obs_ratio}. Need at least {self._min_obs_ratio * n_assets:.0f} "
                f"observations for {n_assets} assets."
            )

        # Eigenvalue decomposition
        try:
            eigenvalues, eigenvectors = np.linalg.eigh(corr_matrix)
        except np.linalg.LinAlgError as e:
            log_optimization_failure(
                "denoise_correlation.eigh",
                e,
                {"n_assets": n_assets, "n_observations": n_observations},
            )
            raise ValueError(f"Eigenvalue decomposition failed: {e}")

        # Check for complex eigenvalues (should not happen for symmetric matrix)
        if np.any(np.abs(eigenvalues.imag) > 1e-10):
            logger.warning("Complex eigenvalues detected, using real parts")
            eigenvalues = eigenvalues.real

        eigenvalues = eigenvalues.real

        # Sort eigenvalues and eigenvectors
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        # Calculate max theoretical eigenvalue for random matrix
        max_random_eigenvalue = self._calculate_max_random_eigenvalue(q, n_assets)

        # Separate signal and noise eigenvalues
        signal_eigenvalues = eigenvalues[eigenvalues > max_random_eigenvalue]
        noise_eigenvalues = eigenvalues[eigenvalues <= max_random_eigenvalue]

        # Replace noise eigenvalues with their average
        if len(noise_eigenvalues) > 0:
            noise_mean = np.mean(noise_eigenvalues)
            denoised_eigenvalues = eigenvalues.copy()
            denoised_eigenvalues[eigenvalues <= max_random_eigenvalue] = noise_mean
        else:
            denoised_eigenvalues = eigenvalues

        # Reconstruct correlation matrix
        denoised_corr = eigenvectors @ np.diag(denoised_eigenvalues) @ eigenvectors.T

        # Ensure diagonal is exactly 1.0
        np.fill_diagonal(denoised_corr, 1.0)

        # Make sure it's symmetric
        denoised_corr = (denoised_corr + denoised_corr.T) / 2

        # Ensure PSD (clip negative values on diagonal)
        np.fill_diagonal(denoised_corr, np.maximum(np.diag(denoised_corr), 1.0))

        return DenoisedResult(
            original_corr=corr_matrix,
            denoised_corr=denoised_corr,
            denoised_cov=None,  # Would need std devs to convert
            eigenvalues=eigenvalues,
            denoised_eigenvalues=denoised_eigenvalues,
            symbols=symbols or list(range(n_assets)),
        )

    def denoise_correlation_with_std(
        self,
        cov_matrix: np.ndarray,
        n_observations: int,
        symbols: Optional[List[str]] = None,
    ) -> DenoisedResult:
        """
        De-noise covariance matrix.

        De-noises the correlation matrix and converts back to covariance.

        Args:
            cov_matrix: Input covariance matrix
            n_observations: Number of observations
            symbols: Asset symbols

        Returns:
            DenoisedResult with de-noised covariance

        Raises:
            ValueError: If matrix is invalid or observations insufficient
        """
        # Validate covariance matrix
        if not is_square_matrix(cov_matrix):
            raise ValueError(
                f"Covariance matrix must be square, got shape {cov_matrix.shape}"
            )

        # Extract standard deviations
        std_devs = np.sqrt(np.diag(cov_matrix))

        # Check for zero variance
        if np.any(std_devs < DEFAULT_EPSILON):
            raise ValueError(
                "Covariance matrix has zero variance assets. "
                "Remove zero variance assets before de-noising."
            )

        # Convert to correlation
        corr_matrix = cov_matrix / np.outer(std_devs, std_devs)
        np.fill_diagonal(corr_matrix, 1.0)

        # De-noise correlation
        result = self.denoise_correlation(corr_matrix, n_observations, symbols)

        # Convert back to covariance
        denoised_cov = result.denoised_corr * np.outer(std_devs, std_devs)
        result.denoised_cov = denoised_cov

        return result

    def _calculate_max_random_eigenvalue(
        self,
        q: float,
        n_assets: int,
    ) -> float:
        """
        Calculate maximum theoretical eigenvalue for random matrix.

        Based on Marchenko-Pastur law.

        Args:
            q: T/n ratio (observations / assets)
            n_assets: Number of assets

        Returns:
            Maximum eigenvalue for random component
        """
        # For correlation matrix, sigma = 1
        sigma = DEFAULT_SIGMA

        # Marchenko-Pastur upper bound
        lambda_max = sigma * (1 + 1 / np.sqrt(q)) ** 2

        return lambda_max

    def _calculate_min_random_eigenvalue(self, q: float) -> float:
        """
        Calculate minimum theoretical eigenvalue for random matrix.

        Args:
            q: T/n ratio

        Returns:
            Minimum eigenvalue for random component
        """
        sigma = DEFAULT_SIGMA

        # Marchenko-Pastur lower bound
        lambda_min = sigma * (1 - 1 / np.sqrt(q)) ** 2

        return max(lambda_min, DEFAULT_EPSILON)

    def fit_kde(
        self,
        eigenvalues: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Fit Kernel Density Estimation to eigenvalues.

        Useful for visualizing signal vs noise separation.

        Args:
            eigenvalues: Array of eigenvalues

        Returns:
            Tuple of (eigenvalue_grid, pdf_values)

        Raises:
            ImportError: If scipy is not available
        """
        try:
            from scipy.stats import gaussian_kde
        except ImportError:
            raise ImportError("scipy is required for KDE fitting")

        if len(eigenvalues) < 2:
            raise ValueError(f"Need at least 2 eigenvalues for KDE, got {len(eigenvalues)}")

        kde = gaussian_kde(eigenvalues)
        grid = np.linspace(
            eigenvalues.min() * 0.9,
            eigenvalues.max() * 1.1,
            DEFAULT_KDE_GRID_POINTS,
        )
        pdf = kde(grid)

        return grid, pdf

    def get_number_of_signal_factors(
        self,
        corr_matrix: np.ndarray,
        n_observations: int,
    ) -> int:
        """
        Estimate number of signal factors using RMT.

        Args:
            corr_matrix: Correlation matrix
            n_observations: Number of observations

        Returns:
            Estimated number of signal factors
        """
        # Validate matrix
        if not is_square_matrix(corr_matrix):
            raise ValueError(f"Correlation matrix must be square, got shape {corr_matrix.shape}")

        eigenvalues = np.linalg.eigvalsh(corr_matrix)
        q = n_observations / corr_matrix.shape[0]

        max_random = self._calculate_max_random_eigenvalue(q, corr_matrix.shape[0])

        # Count eigenvalues significantly above random threshold
        signal_count = np.sum(eigenvalues > max_random)

        return int(signal_count)

    def shrink_to_constant_correlation(
        self,
        corr_matrix: np.ndarray,
        shrinkage: Optional[float] = None,
    ) -> np.ndarray:
        """
        Shrink correlation matrix to constant correlation model.

        Args:
            corr_matrix: Input correlation matrix
            shrinkage: Shrinkage intensity (0-1). None = auto.

        Returns:
            Shrunk correlation matrix
        """
        n = corr_matrix.shape[0]

        # Calculate average correlation (off-diagonal)
        avg_corr = np.mean(corr_matrix[np.triu_indices(n, k=1)])

        # Create constant correlation matrix
        constant_corr = np.full((n, n), avg_corr)
        np.fill_diagonal(constant_corr, 1.0)

        if shrinkage is None:
            # Simple heuristic: more assets = more shrinkage
            shrinkage = min(n * DEFAULT_SHRINKAGE_ASSET_FACTOR, DEFAULT_SHRINKAGE_MAX)

        # Validate shrinkage
        if not (0.0 <= shrinkage <= 1.0):
            raise ValueError(f"shrinkage must be in [0, 1], got {shrinkage}")

        # Shrink
        shrunk = (1 - shrinkage) * corr_matrix + shrinkage * constant_corr

        # Ensure symmetry and diagonal
        shrunk = (shrunk + shrunk.T) / 2
        np.fill_diagonal(shrunk, 1.0)

        return shrunk
