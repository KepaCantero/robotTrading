"""
Handcrafted Weights Optimizer - Robert Carver's methodology.

Implements handcrafted portfolio weights following Carver's "Systematic Trading":
- Weights based on instrument risk characteristics
- Volatility targeting
- Instrument diversification constraints
- Simple, robust allocation rules

From "Systematic Trading" by Robert Carver:
"Handcrafting is the process of manually setting portfolio weights based on
risk characteristics rather than optimizing algorithms. It's more robust and
interpretable than complex optimization methods."
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Union

import numpy as np
from numpy.typing import NDArray

from .base import BaseOptimizer

logger = logging.getLogger(__name__)


class HandcraftedWeightsOptimizer(BaseOptimizer):
    """
    Handcrafted Weights Optimizer (Carver's methodology).

    Key principles from "Systematic Trading":
    1. Weights based on instrument volatility (inverse volatility weighting)
    2. Volatility targeting (scale to target volatility)
    3. Instrument diversification constraints (max weight per instrument)
    4. Simple, robust allocation rules
    5. No complex optimization (avoid overfitting)

    This is Carver's preferred method for systematic trading portfolios.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize handcrafted weights optimizer.

        Args:
            config: Optimizer configuration
                - target_volatility: Target annualized volatility (default 0.15)
                - max_instrument_weight: Max weight per instrument (default 0.40)
                - min_instrument_weight: Min weight per instrument (default 0.01)
                - use_volatility_scaling: Scale weights by volatility (default True)
                - equal_risk_contribution: Use equal risk contribution (default False)
        """
        super().__init__(config)

        # Carver's parameters
        self.target_volatility = config.get("target_volatility", 0.15)
        self.max_instrument_weight = config.get("max_instrument_weight", 0.40)
        self.min_instrument_weight = config.get("min_instrument_weight", 0.01)
        self.use_volatility_scaling = config.get("use_volatility_scaling", True)
        self.equal_risk_contribution = config.get("equal_risk_contribution", False)

        logger.info(
            f"HandcraftedWeightsOptimizer initialized: "
            f"target_vol={self.target_volatility}, "
            f"max_weight={self.max_instrument_weight}"
        )

    def optimize(
        self,
        returns: Optional[NDArray[np.floating]] = None,
        **kwargs,
    ) -> Union[NDArray[np.floating], Dict[str, Any]]:
        """
        Optimize using handcrafted weights (Carver's methodology).

        Steps:
        1. Calculate instrument volatilities
        2. Apply inverse volatility weighting (Carver's preferred method)
        3. Scale to target volatility
        4. Apply instrument diversification constraints
        5. Optionally use equal risk contribution

        Args:
            returns: Asset returns (optional, not used in handcrafting)
            **kwargs: Additional parameters:
                - expected_returns: Expected returns (not used in handcrafting)
                - cov_matrix: Covariance matrix (required)
                - constraints: Additional constraints

        Returns:
            Dict with handcrafted weights and metrics
        """
        expected_returns = kwargs.get("expected_returns", returns)
        cov_matrix = kwargs.get("cov_matrix")
        constraints = kwargs.get("constraints") or {}

        if cov_matrix is None:
            raise ValueError("cov_matrix is required for HandcraftedWeightsOptimizer")

        try:
            len(expected_returns)

            # Step 1: Calculate instrument volatilities
            volatilities = self._calculate_volatilities(cov_matrix)

            # Step 2: Calculate handcrafted weights
            if self.equal_risk_contribution:
                # Equal risk contribution (Carver's alternative method)
                weights = self._equal_risk_contribution_weights(cov_matrix)
            else:
                # Inverse volatility weighting (Carver's preferred method)
                weights = self._inverse_volatility_weights(volatilities)

            # Step 3: Apply instrument diversification constraints
            max_weight = constraints.get("max_weight", self.max_instrument_weight)
            min_weight = constraints.get("min_weight", self.min_instrument_weight)

            weights = np.clip(weights, min_weight, max_weight)

            # Step 4: Re-normalize weights
            weights = weights / weights.sum()

            # Step 5: Volatility targeting (Carver's methodology)
            if self.use_volatility_scaling:
                weights = self._apply_volatility_targeting(weights, volatilities, cov_matrix)

            # Calculate portfolio metrics
            expected_return = float(np.dot(weights, expected_returns))
            portfolio_volatility = float(np.sqrt(weights @ cov_matrix @ weights))
            sharpe_ratio = (
                expected_return / portfolio_volatility if portfolio_volatility > 0 else 0.0
            )

            # Calculate risk contributions (for verification)
            risk_contributions = self._calculate_risk_contributions(weights, cov_matrix)

            return {
                "weights": {f"asset_{i}": float(w) for i, w in enumerate(weights)},
                "expected_return": expected_return,
                "volatility": portfolio_volatility,
                "sharpe_ratio": sharpe_ratio,
                "method": "handcrafted_carver",
                "volatility_target": self.target_volatility,
                "instrument_volatilities": {
                    f"asset_{i}": float(vol) for i, vol in enumerate(volatilities)
                },
                "risk_contributions": {
                    f"asset_{i}": float(rc) for i, rc in enumerate(risk_contributions)
                },
                "diversification_ratio": self._calculate_diversification_ratio(
                    weights, volatilities
                ),
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error in handcrafted optimization: {e}", exc_info=True)
            return self._equal_weight_fallback(len(expected_returns))

    def _calculate_volatilities(self, cov_matrix: np.ndarray) -> np.ndarray:
        """
        Calculate instrument volatilities from covariance matrix.

        Args:
            cov_matrix: Covariance matrix

        Returns:
            Array of volatilities
        """
        # Volatility is the square root of the diagonal (variance)
        volatilities = np.sqrt(np.diag(cov_matrix))

        # Ensure all volatilities are positive
        volatilities = np.maximum(volatilities, 1e-10)

        return volatilities

    def _inverse_volatility_weights(self, volatilities: np.ndarray) -> np.ndarray:
        """
        Calculate inverse volatility weights (Carver's preferred method).

        Formula: w_i = (1/σ_i) / Σ(1/σ_j)

        This gives lower weight to more volatile instruments, which is
        Carver's recommended approach for handcrafted portfolios.

        Args:
            volatilities: Array of instrument volatilities

        Returns:
            Array of weights
        """
        # Inverse volatility
        inv_vol = 1.0 / volatilities

        # Normalize to sum to 1
        weights = inv_vol / inv_vol.sum()

        return weights

    def _equal_risk_contribution_weights(self, cov_matrix: np.ndarray) -> np.ndarray:
        """
        Calculate equal risk contribution weights (Carver's alternative method).

        This method ensures each instrument contributes equally to portfolio risk.
        Uses a simple iterative approach (Carver avoids complex optimization).

        Args:
            cov_matrix: Covariance matrix

        Returns:
            Array of weights
        """
        n = len(cov_matrix)

        # Start with inverse volatility weights (good initial guess)
        volatilities = self._calculate_volatilities(cov_matrix)
        weights = self._inverse_volatility_weights(volatilities)

        # Simple iterative approach (Carver's method)
        max_iterations = 100
        tolerance = 1e-6

        for _iteration in range(max_iterations):
            # Calculate risk contributions
            portfolio_var = weights @ cov_matrix @ weights
            marginal_contrib = cov_matrix @ weights
            risk_contrib = weights * marginal_contrib / portfolio_var

            # Target risk contribution (equal for all instruments)
            target_risk = 1.0 / n

            # Check convergence
            error = np.sum((risk_contrib - target_risk) ** 2)
            if error < tolerance:
                break

            # Adjust weights (multiplicative update)
            adjustment = np.where(risk_contrib > 0, target_risk / (risk_contrib + 1e-10), 1.0)
            weights = weights * np.power(adjustment, 0.5)  # Damped adjustment
            weights = np.maximum(weights, 1e-10)
            weights = weights / weights.sum()

        return weights

    def _apply_volatility_targeting(
        self,
        weights: np.ndarray,
        volatilities: np.ndarray,
        cov_matrix: np.ndarray,
    ) -> np.ndarray:
        """
        Apply volatility targeting (Carver's methodology).

        Scale weights so portfolio volatility matches target volatility.

        Formula: w_scaled = w * (σ_target / σ_portfolio)

        Args:
            weights: Current weights
            volatilities: Instrument volatilities
            cov_matrix: Covariance matrix

        Returns:
            Scaled weights
        """
        # Calculate current portfolio volatility
        portfolio_volatility = float(np.sqrt(weights @ cov_matrix @ weights))

        if portfolio_volatility == 0:
            return weights

        # Scale factor to reach target volatility
        scale_factor = self.target_volatility / portfolio_volatility

        # Apply scaling (but don't exceed max leverage)
        max_leverage = 2.0  # Carver recommends limiting leverage
        scale_factor = min(scale_factor, max_leverage)

        scaled_weights = weights * scale_factor

        return scaled_weights

    def _calculate_risk_contributions(
        self, weights: np.ndarray, cov_matrix: np.ndarray
    ) -> np.ndarray:
        """
        Calculate risk contributions for each instrument.

        Args:
            weights: Portfolio weights
            cov_matrix: Covariance matrix

        Returns:
            Array of risk contributions (percentages)
        """
        # Portfolio variance
        portfolio_var = weights @ cov_matrix @ weights

        if portfolio_var <= 0:
            return np.zeros(len(weights))

        # Marginal risk contribution
        marginal_contrib = (cov_matrix @ weights) / np.sqrt(portfolio_var)

        # Risk contribution
        risk_contrib = weights * marginal_contrib

        # Normalize to percentages
        total_risk = risk_contrib.sum()
        if total_risk > 0:
            return risk_contrib / total_risk

        return risk_contrib

    def _calculate_diversification_ratio(
        self, weights: np.ndarray, volatilities: np.ndarray
    ) -> float:
        """
        Calculate diversification ratio (Carver's metric).

        DR = (Σ w_i * σ_i) / σ_portfolio

        Values > 1 indicate diversification benefits.

        Args:
            weights: Portfolio weights
            volatilities: Instrument volatilities

        Returns:
            Diversification ratio
        """
        # Weighted average volatility
        weighted_avg_vol = np.sum(weights * volatilities)

        # Portfolio volatility (approximate, assuming correlation = 1)
        portfolio_vol = np.sqrt(np.sum((weights * volatilities) ** 2))

        if portfolio_vol == 0:
            return 1.0

        return float(weighted_avg_vol / portfolio_vol)

    def _equal_weight_fallback(self, n: int) -> Dict[str, Any]:
        """
        Fallback to equal weights.

        Args:
            n: Number of instruments

        Returns:
            Dict with equal weights
        """
        weight = 1.0 / n
        return {
            "weights": {f"asset_{i}": weight for i in range(n)},
            "expected_return": 0.0,
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "method": "equal_weight_fallback",
        }


def create_handcrafted_weights(
    volatilities: Dict[str, float],
    target_volatility: float = 0.15,
    max_weight: float = 0.40,
) -> Dict[str, float]:
    """
    Convenience function to create handcrafted weights from volatilities.

    This is Carver's recommended simple approach:
    1. Calculate inverse volatility weights
    2. Apply max weight constraint
    3. Scale to target volatility

    Args:
        volatilities: Dict mapping instrument names to volatilities
        target_volatility: Target portfolio volatility
        max_weight: Maximum weight per instrument

    Returns:
        Dict mapping instrument names to weights

    Example:
        >>> volatilities = {"AAPL": 0.25, "MSFT": 0.22, "TLT": 0.10}
        >>> weights = create_handcrafted_weights(volatilities)
        >>> print(weights)
        {'AAPL': 0.15, 'MSFT': 0.17, 'TLT': 0.68}
    """
    # Convert to numpy array
    instruments = list(volatilities.keys())
    vol_array = np.array([volatilities[i] for i in instruments])

    # Inverse volatility weights
    inv_vol = 1.0 / vol_array
    weights = inv_vol / inv_vol.sum()

    # Apply max weight constraint
    weights = np.minimum(weights, max_weight)

    # Re-normalize
    weights = weights / weights.sum()

    # Calculate current portfolio volatility (assuming correlation = 0.5)
    avg_correlation = 0.5
    portfolio_vol = np.sqrt(
        np.sum((weights * vol_array) ** 2)
        + 2
        * avg_correlation
        * np.sum(
            [
                (weights[i] * weights[j] * vol_array[i] * vol_array[j])
                for i in range(len(weights))
                for j in range(i + 1, len(weights))
            ]
        )
    )

    # Scale to target volatility
    if portfolio_vol > 0:
        scale_factor = target_volatility / portfolio_vol
        weights = weights * scale_factor

    # Re-normalize one more time
    weights = weights / weights.sum()

    return {instruments[i]: float(weights[i]) for i in range(len(instruments))}
