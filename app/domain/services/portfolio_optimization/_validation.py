# mypy: ignore-errors
"""
Shared validation utilities for portfolio optimization.

Provides common validation functions for covariance matrices,
input sanitization, and logging across all optimization modules.
"""

from __future__ import annotations

import logging
import traceback
from typing import Optional, Tuple

import numpy as np

# Trading convention constants
TRADING_DAYS = 252  # Trading days per year

# Numerical tolerances
PSD_TOLERANCE = 1e-10  # Tolerance for PSD check
SYMMETRY_TOLERANCE = 1e-10  # Tolerance for symmetry check
WEIGHT_SUM_TOLERANCE = 1e-6  # Tolerance for weight sum check
MIN_VARIANCE_THRESHOLD = 1e-10  # Minimum variance threshold


logger = logging.getLogger(__name__)


def is_square_matrix(matrix: np.ndarray) -> bool:
    """
    Check if matrix is square.

    Args:
        matrix: Input matrix

    Returns:
        True if matrix is square
    """
    return matrix.ndim == 2 and matrix.shape[0] == matrix.shape[1]


def is_symmetric(matrix: np.ndarray, tolerance: float = SYMMETRY_TOLERANCE) -> bool:
    """
    Check if matrix is symmetric within tolerance.

    Args:
        matrix: Input matrix
        tolerance: Numerical tolerance for comparison

    Returns:
        True if matrix is symmetric
    """
    if not is_square_matrix(matrix):
        return False
    return np.allclose(matrix, matrix.T, atol=tolerance)


def is_positive_semidefinite(
    matrix: np.ndarray,
    tolerance: float = PSD_TOLERANCE,
    check_symmetry: bool = True,
) -> bool:
    """
    Check if matrix is positive semidefinite.

    A matrix is PSD if all eigenvalues are >= 0.

    Args:
        matrix: Input matrix
        tolerance: Tolerance for negative eigenvalues
        check_symmetry: Whether to verify symmetry first

    Returns:
        True if matrix is PSD

    Raises:
        ValueError: If matrix is not square
    """
    if not is_square_matrix(matrix):
        raise ValueError(f"Matrix must be square, got shape {matrix.shape}")

    if check_symmetry and not is_symmetric(matrix):
        return False

    try:
        eigenvalues = np.linalg.eigvalsh(matrix)
        return np.all(eigenvalues >= -tolerance)
    except np.linalg.LinAlgError:
        return False


def validate_covariance_matrix(
    cov_matrix: np.ndarray,
    check_psd: bool = True,
    check_symmetry: bool = True,
    enforce_psd: bool = False,
) -> Tuple[bool, np.ndarray, Optional[str]]:
    """
    Validate and optionally fix covariance matrix.

    Args:
        cov_matrix: Covariance matrix to validate
        check_psd: Whether to check positive semidefinite
        check_symmetry: Whether to check symmetry
        enforce_psd: Whether to enforce PSD (clip negative eigenvalues)

    Returns:
        Tuple of (is_valid, processed_matrix, error_message)
        - is_valid: True if validation passed
        - processed_matrix: Original or fixed matrix
        - error_message: None if valid, error description if invalid
    """
    error_msg = None
    processed = cov_matrix.copy()

    # Check square
    if not is_square_matrix(cov_matrix):
        error_msg = f"Covariance matrix must be square, got shape {cov_matrix.shape}"
        logger.error(error_msg)
        return False, processed, error_msg

    # Check symmetry
    if check_symmetry and not is_symmetric(cov_matrix):
        error_msg = "Covariance matrix is not symmetric"
        logger.warning(f"{error_msg}, symmetrizing...")
        # Symmetrize: (M + M.T) / 2
        processed = (processed + processed.T) / 2

    # Check PSD
    if check_psd and not is_positive_semidefinite(processed):
        error_msg = "Covariance matrix is not positive semidefinite"
        if enforce_psd:
            logger.warning(f"{error_msg}, enforcing PSD via eigenvalue clipping...")
            processed = enforce_positive_semidefinite(processed)
        else:
            logger.error(error_msg)
            return False, processed, error_msg

    return True, processed, None


def enforce_positive_semidefinite(
    cov_matrix: np.ndarray,
    tolerance: float = PSD_TOLERANCE,
) -> np.ndarray:
    """
    Enforce positive semidefiniteness via eigenvalue decomposition.

    Args:
        cov_matrix: Input covariance matrix
        tolerance: Small tolerance for eigenvalue clipping

    Returns:
        PSD covariance matrix
    """
    # Eigenvalue decomposition
    eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)

    # Clip negative eigenvalues
    eigenvalues_clipped = np.maximum(eigenvalues, tolerance)

    # Reconstruct matrix
    psd_matrix = eigenvectors @ np.diag(eigenvalues_clipped) @ eigenvectors.T

    # Ensure symmetry
    psd_matrix = (psd_matrix + psd_matrix.T) / 2

    return psd_matrix


def sanitize_input_returns(
    returns: dict[str, list[float]] | np.ndarray,
    min_variance_threshold: float = MIN_VARIANCE_THRESHOLD,
) -> Tuple[np.ndarray, list[str], list[int]]:
    """
    Sanitize input returns by removing NaN and zero-variance assets.

    Args:
        returns: Dictionary of symbol -> returns or 2D array
        min_variance_threshold: Minimum variance threshold

    Returns:
        Tuple of (cleaned_returns, valid_symbols, valid_indices)
    """
    if isinstance(returns, dict):
        symbols = list(returns.keys())
        # Convert to array
        max_len = max(len(v) for v in returns.values())
        data = np.full((max_len, len(symbols)), np.nan)
        for i, sym in enumerate(symbols):
            series = returns[sym]
            data[: len(series), i] = series
    else:
        data = np.asarray(returns)
        symbols = [f"Asset_{i}" for i in range(data.shape[1]) if data.shape[1] > 0]

    # Find valid assets (no NaN, positive variance)
    valid_indices = []
    for i in range(data.shape[1]):
        col = data[:, i]
        # Check for NaN
        if np.any(np.isnan(col)):
            logger.warning(f"Asset {symbols[i] if i < len(symbols) else i} contains NaN, skipping")
            continue
        # Check variance
        if np.var(col) < min_variance_threshold:
            logger.warning(
                f"Asset {symbols[i] if i < len(symbols) else i} has zero variance, skipping"
            )
            continue
        valid_indices.append(i)

    if len(valid_indices) == 0:
        raise ValueError("No valid assets found after sanitization")

    valid_symbols = [symbols[i] for i in valid_indices]
    cleaned_data = data[:, valid_indices]

    return cleaned_data, valid_symbols, valid_indices


def validate_weights_sum_to_one(
    weights: np.ndarray,
    tolerance: float = WEIGHT_SUM_TOLERANCE,
) -> Tuple[bool, float]:
    """
    Validate that weights sum to 1.0.

    Args:
        weights: Portfolio weights
        tolerance: Numerical tolerance

    Returns:
        Tuple of (is_valid, actual_sum)
    """
    weight_sum = float(np.sum(weights))
    is_valid = abs(weight_sum - 1.0) < tolerance
    return is_valid, weight_sum


def log_optimization_failure(
    method_name: str,
    exception: Exception,
    context: Optional[dict] = None,
) -> None:
    """
    Log optimization failure with stack trace and context.

    Args:
        method_name: Name of the optimization method
        exception: The exception that occurred
        context: Optional dictionary with context information
    """
    logger.error(
        f"Optimization failed in {method_name}: {str(exception)}",
        extra={
            "method": method_name,
            "exception_type": type(exception).__name__,
            "context": context or {},
        },
        exc_info=True,
    )

    # Also log the stack trace separately
    stack_trace = "".join(
        traceback.format_exception(type(exception), exception, exception.__traceback__)
    )
    logger.debug(f"Stack trace for {method_name} failure:\n{stack_trace}")


def sanitize_covariance_matrix(
    cov_matrix: np.ndarray,
    min_variance_threshold: float = MIN_VARIANCE_THRESHOLD,
    enforce_psd: bool = True,
) -> Tuple[np.ndarray, list[int]]:
    """
    Sanitize covariance matrix by removing zero-variance assets.

    Args:
        cov_matrix: Input covariance matrix
        min_variance_threshold: Minimum variance threshold
        enforce_psd: Whether to enforce PSD

    Returns:
        Tuple of (cleaned_cov_matrix, valid_indices)
    """
    # Find assets with positive variance
    variances = np.diag(cov_matrix)
    valid_indices = np.where(variances >= min_variance_threshold)[0].tolist()

    if len(valid_indices) == 0:
        raise ValueError("No assets with positive variance found")

    if len(valid_indices) < cov_matrix.shape[0]:
        logger.warning(
            f"Removed {cov_matrix.shape[0] - len(valid_indices)} " "assets with zero variance"
        )

    # Extract submatrix
    cleaned = cov_matrix[np.ix_(valid_indices, valid_indices)]

    # Enforce PSD if requested
    if enforce_psd:
        cleaned = enforce_positive_semidefinite(cleaned)

    return cleaned, valid_indices


def get_condition_number(matrix: np.ndarray) -> float:
    """
    Get condition number of a matrix.

    Args:
        matrix: Input matrix

    Returns:
        Condition number (ratio of largest to smallest singular value)
    """
    return float(np.linalg.cond(matrix))
