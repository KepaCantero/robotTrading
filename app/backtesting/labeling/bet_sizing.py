"""
Bet Sizing Implementation for Financial ML

Based on Marcos López de Prado's "Advances in Financial Machine Learning", Chapter 10.

Bet sizing determines how much to invest in each trading opportunity.
This is critical for risk management and maximizing risk-adjusted returns.

Key Concepts:
- Kelly Criterion: Optimal bet size for maximizing long-term growth
- Meta-labeling: Use ML predictions to size bets
- Risk Parity: Size bets based on risk contribution
- Drawdown Constraints: Limit position sizes based on drawdown
- Expected Value: Size based on the expected value of each trade
- Bet Sizing with ML: Use meta-model probabilities for position sizing

Methods:
1. Kelly Criterion: f* = (bp - q) / b
2. Probability Scaling: Size based on prediction probability
3. Risk Parity: Equalize risk contribution across positions
4. Concentration Limit: Cap maximum exposure
5. ML-based Sizing: Use meta-labeling model output for bet sizing
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BetSizingConfig:
    """Configuration for bet sizing."""

    # Bet sizing method
    method: str = "kelly"  # kelly, probability, risk_parity, fixed

    # Kelly criterion parameters
    kelly_fraction: float = 0.25  # Fraction of full Kelly (for safety)
    min_kelly: float = 0.01  # Minimum bet size
    max_kelly: float = 0.25  # Maximum bet size

    # Probability scaling parameters
    prob_threshold: float = 0.5  # Minimum probability to take trade
    prob_scaling: str = "linear"  # linear, sigmoid, softmax

    # Risk parity parameters
    risk_target: float = 0.15  # Target annualized risk (15%)
    risk_window: int = 20  # Window for volatility calculation

    # Position limits
    max_position_size: float = 1.0  # Maximum position size
    max_portfolio_exposure: float = 1.0  # Maximum total exposure
    concentration_limit: float = 0.3  # Max exposure per signal/asset

    # Drawdown constraints
    max_drawdown: float = 0.2  # Maximum drawdown (20%)
    drawdown_lookback: int = 252  # Lookback for drawdown calculation

    # Bet sizing adjustment
    adjust_for_volatility: bool = True
    adjust_for_correlation: bool = True
    adjust_for_regime: bool = False

    def __post_init__(self):
        """Validate configuration."""
        valid_methods = ["kelly", "probability", "risk_parity", "fixed"]
        if self.method not in valid_methods:
            raise ValueError(f"method must be one of {valid_methods}")

        if self.kelly_fraction <= 0 or self.kelly_fraction > 1:
            raise ValueError("kelly_fraction must be between 0 and 1")

        if self.prob_threshold < 0 or self.prob_threshold > 1:
            raise ValueError("prob_threshold must be between 0 and 1")

        if self.max_position_size < 0 or self.max_position_size > 1:
            raise ValueError("max_position_size must be between 0 and 1")


@dataclass
class BetSizingResult:
    """Result of bet sizing calculation."""

    bet_sizes: np.ndarray
    """Position sizes for each signal"""

    expected_returns: np.ndarray
    """Expected returns for each signal"""

    risk_contribution: np.ndarray
    """Risk contribution of each position"""

    kelly_fractions: np.ndarray
    """Kelly criterion fractions"""

    metadata: Dict = field(default_factory=dict)
    """Additional metadata"""

    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "bet_sizes": self.bet_sizes.tolist(),
            "expected_returns": self.expected_returns.tolist(),
            "risk_contribution": self.risk_contribution.tolist(),
            "kelly_fractions": self.kelly_fractions.tolist(),
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class BetSizing:
    """
    Bet sizing implementation for financial ML.

    This class implements various bet sizing methods:

    1. Kelly Criterion: Optimal bet size for maximizing growth
    2. Probability Scaling: Size based on prediction confidence
    3. Risk Parity: Equalize risk contribution across positions
    4. Fixed Sizing: Simple fixed position sizes

    Example:
        >>> bet_sizing = BetSizing(method="kelly")
        >>> result = bet_sizing.calculate_sizes(predictions, probabilities, returns)
        >>> print(f"Average bet size: {result.bet_sizes.mean():.2%}")
    """

    def __init__(self, config: Optional[BetSizingConfig] = None):
        """
        Initialize bet sizing calculator.

        Args:
            config: Configuration for bet sizing
        """
        self.config = config or BetSizingConfig()

    def calculate_sizes(
        self,
        predictions: np.ndarray,
        probabilities: Optional[np.ndarray] = None,
        expected_returns: Optional[np.ndarray] = None,
        volatilities: Optional[np.ndarray] = None,
        correlation_matrix: Optional[np.ndarray] = None,
        current_capital: float = 1_000_000.0,
        current_drawdown: float = 0.0,
    ) -> BetSizingResult:
        """
        Calculate bet sizes for given signals.

        Args:
            predictions: Trading signals (-1, 0, 1)
            probabilities: Prediction probabilities (confidence)
            expected_returns: Expected returns for each signal
            volatilities: Volatility for each asset
            correlation_matrix: Correlation matrix for assets
            current_capital: Current portfolio capital
            current_drawdown: Current portfolio drawdown

        Returns:
            BetSizingResult with position sizes and metadata

        Example:
            >>> result = bet_sizing.calculate_sizes(
            ...     predictions=predictions,
            ...     probabilities=probs,
            ...     expected_returns=rets,
            ... )
            >>> positions = result.bet_sizes * current_capital
        """
        n_signals = len(predictions)

        # Initialize with default values
        if probabilities is None:
            probabilities = np.ones(n_signals) * 0.5

        if expected_returns is None:
            expected_returns = np.zeros(n_signals)

        # Calculate bet sizes based on method
        if self.config.method == "kelly":
            bet_sizes = self._kelly_sizing(predictions, probabilities, expected_returns)
        elif self.config.method == "probability":
            bet_sizes = self._probability_sizing(predictions, probabilities)
        elif self.config.method == "risk_parity":
            bet_sizes = self._risk_parity_sizing(predictions, volatilities, correlation_matrix)
        elif self.config.method == "fixed":
            bet_sizes = self._fixed_sizing(predictions)
        else:
            raise ValueError(f"Unknown method: {self.config.method}")

        # Apply volatility adjustment
        if self.config.adjust_for_volatility and volatilities is not None:
            bet_sizes = self._adjust_for_volatility(bet_sizes, volatilities)

        # Apply correlation adjustment
        if self.config.adjust_for_correlation and correlation_matrix is not None:
            bet_sizes = self._adjust_for_correlation(bet_sizes, correlation_matrix)

        # Apply concentration limits
        bet_sizes = self._apply_concentration_limit(bet_sizes)

        # Apply position size limits
        bet_sizes = np.clip(bet_sizes, 0, self.config.max_position_size)

        # Apply portfolio exposure limit
        bet_sizes = self._apply_exposure_limit(bet_sizes)

        # Apply drawdown constraint
        if current_drawdown > self.config.max_drawdown:
            scale_factor = (self.config.max_drawdown - current_drawdown) / (1 - current_drawdown)
            scale_factor = max(0.0, scale_factor)
            bet_sizes = bet_sizes * scale_factor
            logger.warning(
                f"Drawdown constraint active: {current_drawdown:.2%} > {self.config.max_drawdown:.2%}. "
                f"Scaling positions by {scale_factor:.2%}"
            )

        # Calculate risk contribution
        risk_contribution = self._calculate_risk_contribution(
            bet_sizes, volatilities, correlation_matrix
        )

        # Calculate Kelly fractions (for reference)
        kelly_fractions = self._calculate_kelly_fractions(
            predictions, probabilities, expected_returns
        )

        return BetSizingResult(
            bet_sizes=bet_sizes,
            expected_returns=expected_returns,
            risk_contribution=risk_contribution,
            kelly_fractions=kelly_fractions,
            metadata={
                "method": self.config.method,
                "n_signals": n_signals,
                "avg_bet_size": float(np.mean(bet_sizes)),
                "total_exposure": float(np.abs(bet_sizes).sum()),
                "max_exposure": float(np.abs(bet_sizes).max()),
            },
        )

    def _kelly_sizing(
        self,
        predictions: np.ndarray,
        probabilities: np.ndarray,
        expected_returns: np.ndarray,
    ) -> np.ndarray:
        """
        Calculate bet sizes using Kelly criterion.

        Kelly formula: f* = (bp - q) / b
        where:
        - b = odds (win/loss ratio)
        - p = probability of winning
        - q = 1 - p

        Args:
            predictions: Trading signals
            probabilities: Prediction probabilities
            expected_returns: Expected returns

        Returns:
            Kelly bet sizes
        """
        bet_sizes = np.zeros(len(predictions))

        for i, (pred, prob, exp_ret) in enumerate(
            zip(predictions, probabilities, expected_returns)
        ):
            if pred == 0:
                continue

            # Use expected return as odds
            if exp_ret != 0:
                # b = expected_return / expected_loss
                if exp_ret > 0:
                    b = exp_ret / abs(exp_ret * 0.5)  # Assume 50% loss if wrong
                else:
                    b = abs(exp_ret * 0.5) / exp_ret  # Assume 50% gain if wrong
            else:
                b = 1.0  # Even odds

            p = prob
            q = 1 - p

            # Kelly criterion
            kelly = (b * p - q) / b

            # Only bet if positive expected value
            if kelly > 0:
                # Apply fractional Kelly for safety
                kelly = kelly * self.config.kelly_fraction

                # Clip to bounds
                kelly = np.clip(kelly, self.config.min_kelly, self.config.max_kelly)

                bet_sizes[i] = abs(kelly)

        return bet_sizes

    def _probability_sizing(
        self,
        predictions: np.ndarray,
        probabilities: np.ndarray,
    ) -> np.ndarray:
        """
        Calculate bet sizes based on prediction probability.

        Args:
            predictions: Trading signals
            probabilities: Prediction probabilities

        Returns:
            Probability-scaled bet sizes
        """
        bet_sizes = np.zeros(len(predictions))

        for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
            if pred == 0:
                continue

            # Only trade if probability exceeds threshold
            if prob < self.config.prob_threshold:
                continue

            if self.config.prob_scaling == "linear":
                # Linear scaling from threshold to 1
                size = (prob - self.config.prob_threshold) / (1 - self.config.prob_threshold)

            elif self.config.prob_scaling == "sigmoid":
                # Sigmoid scaling
                import math

                x = (prob - self.config.prob_threshold) / (1 - self.config.prob_threshold)
                size = 1 / (1 + math.exp(-5 * (x - 0.5)))

            elif self.config.prob_scaling == "softmax":
                # Softmax-like scaling
                import math

                size = math.exp(prob - 1) / (1 + math.exp(prob - 1))

            else:
                size = prob

            bet_sizes[i] = size

        return bet_sizes

    def _risk_parity_sizing(
        self,
        predictions: np.ndarray,
        volatilities: Optional[np.ndarray],
        correlation_matrix: Optional[np.ndarray],
    ) -> np.ndarray:
        """
        Calculate bet sizes using risk parity.

        Risk parity equalizes the risk contribution of each position.

        Args:
            predictions: Trading signals
            volatilities: Volatility for each asset
            correlation_matrix: Correlation matrix

        Returns:
            Risk parity bet sizes
        """
        bet_sizes = np.zeros(len(predictions))

        # Get active signals
        active_mask = predictions != 0
        n_active = active_mask.sum()

        if n_active == 0:
            return bet_sizes

        # Default volatilities if not provided
        if volatilities is None:
            volatilities = np.ones(n_active)
        else:
            volatilities = volatilities[active_mask]

        # Risk parity: weight proportional to 1/volatility
        inv_vol = 1.0 / (volatilities + 1e-10)
        weights = inv_vol / inv_vol.sum()

        # Set bet sizes
        bet_sizes[active_mask] = weights

        return bet_sizes

    def _fixed_sizing(self, predictions: np.ndarray) -> np.ndarray:
        """
        Calculate fixed bet sizes.

        Args:
            predictions: Trading signals

        Returns:
            Fixed bet sizes
        """
        bet_sizes = np.zeros(len(predictions))

        # Equal size for all active signals
        active_mask = predictions != 0
        n_active = active_mask.sum()

        if n_active > 0:
            size = 1.0 / n_active
            bet_sizes[active_mask] = size

        return bet_sizes

    def _adjust_for_volatility(
        self,
        bet_sizes: np.ndarray,
        volatilities: np.ndarray,
    ) -> np.ndarray:
        """
        Adjust bet sizes for volatility.

        Higher volatility → smaller position size.

        Args:
            bet_sizes: Original bet sizes
            volatilities: Asset volatilities

        Returns:
            Volatility-adjusted bet sizes
        """
        # Normalize volatilities
        norm_vol = volatilities / volatilities.mean()

        # Inverse volatility scaling
        vol_adjustment = 1.0 / (norm_vol + 1e-10)

        # Apply adjustment
        return bet_sizes * vol_adjustment

    def _adjust_for_correlation(
        self,
        bet_sizes: np.ndarray,
        correlation_matrix: np.ndarray,
    ) -> np.ndarray:
        """
        Adjust bet sizes for correlation.

        Reduce sizes for highly correlated positions.

        Args:
            bet_sizes: Original bet sizes
            correlation_matrix: Correlation matrix

        Returns:
            Correlation-adjusted bet sizes
        """
        # Get active positions
        active_mask = bet_sizes > 0
        active_indices = np.where(active_mask)[0]

        if len(active_indices) < 2:
            return bet_sizes

        # Calculate average correlation for each position
        avg_correlations = np.zeros(len(active_indices))

        for i, idx in enumerate(active_indices):
            # Get correlations with other active positions
            corrs = correlation_matrix[idx, active_indices]
            # Exclude self-correlation
            corrs = np.delete(corrs, i)
            avg_correlations[i] = np.abs(corrs).mean()

        # Adjust bet sizes: higher correlation → smaller size
        correlation_adjustment = 1.0 / (1.0 + avg_correlations)
        bet_sizes[active_indices] = bet_sizes[active_indices] * correlation_adjustment

        return bet_sizes

    def _apply_concentration_limit(self, bet_sizes: np.ndarray) -> np.ndarray:
        """
        Apply concentration limit.

        Cap individual position sizes.

        Args:
            bet_sizes: Original bet sizes

        Returns:
            Concentration-limited bet sizes
        """
        # Cap each position
        bet_sizes = np.minimum(bet_sizes, self.config.concentration_limit)

        return bet_sizes

    def _apply_exposure_limit(self, bet_sizes: np.ndarray) -> np.ndarray:
        """
        Apply portfolio exposure limit.

        Scale down if total exposure exceeds limit.

        Args:
            bet_sizes: Original bet sizes

        Returns:
            Exposure-limited bet sizes
        """
        total_exposure = bet_sizes.sum()

        if total_exposure > self.config.max_portfolio_exposure:
            scale_factor = self.config.max_portfolio_exposure / total_exposure
            bet_sizes = bet_sizes * scale_factor

        return bet_sizes

    def _calculate_risk_contribution(
        self,
        bet_sizes: np.ndarray,
        volatilities: Optional[np.ndarray],
        correlation_matrix: Optional[np.ndarray],
    ) -> np.ndarray:
        """
        Calculate risk contribution of each position.

        Args:
            bet_sizes: Position sizes
            volatilities: Asset volatilities
            correlation_matrix: Correlation matrix

        Returns:
            Risk contribution array
        """
        risk_contrib = np.zeros(len(bet_sizes))

        if volatilities is None:
            return risk_contrib

        # Calculate portfolio volatility
        active_mask = bet_sizes > 0

        if not active_mask.any():
            return risk_contrib

        # Simplified risk contribution: weight * volatility
        weighted_vol = bet_sizes * volatilities

        # Normalize to sum to 1
        total_risk = weighted_vol.sum()

        if total_risk > 0:
            risk_contrib = weighted_vol / total_risk

        return risk_contrib

    def _calculate_kelly_fractions(
        self,
        predictions: np.ndarray,
        probabilities: np.ndarray,
        expected_returns: np.ndarray,
    ) -> np.ndarray:
        """
        Calculate Kelly fractions for reference.

        Args:
            predictions: Trading signals
            probabilities: Prediction probabilities
            expected_returns: Expected returns

        Returns:
            Kelly fractions
        """
        kelly_fractions = np.zeros(len(predictions))

        for i, (pred, prob, exp_ret) in enumerate(
            zip(predictions, probabilities, expected_returns)
        ):
            if pred == 0 or exp_ret == 0:
                continue

            # Calculate Kelly fraction
            b = abs(exp_ret) / abs(exp_ret * 0.5)  # Win/loss ratio
            p = prob
            q = 1 - p

            kelly = (b * p - q) / b
            kelly_fractions[i] = kelly if kelly > 0 else 0.0

        return kelly_fractions


def calculate_bet_sizes(
    predictions: np.ndarray,
    probabilities: Optional[np.ndarray] = None,
    method: str = "kelly",
    **kwargs,
) -> np.ndarray:
    """
    Convenience function to calculate bet sizes.

    Args:
        predictions: Trading signals (-1, 0, 1)
        probabilities: Prediction probabilities
        method: Bet sizing method ('kelly', 'probability', 'risk_parity', 'fixed')
        **kwargs: Additional arguments for BetSizing

    Returns:
        Bet sizes array

    Example:
        >>> bet_sizes = calculate_bet_sizes(predictions, probabilities, method="kelly")
        >>> print(f"Average bet size: {bet_sizes.mean():.2%}")
    """
    config = BetSizingConfig(method=method)
    bet_sizing = BetSizing(config)

    result = bet_sizing.calculate_sizes(
        predictions=predictions,
        probabilities=probabilities,
        **kwargs,
    )

    return result.bet_sizes


# ============================================================================
# ML-BASED BET SIZING (López de Prado Chapter 10)
# ============================================================================


def calculate_bet_sizes_ml(
    meta_proba: np.ndarray,
    primary_predictions: np.ndarray,
    expected_returns: Optional[np.ndarray] = None,
    method: str = "meta_kelly",
    confidence_threshold: float = 0.5,
    max_bet_size: float = 1.0,
    min_bet_size: float = 0.0,
) -> np.ndarray:
    """
    Calculate bet sizes using ML-based meta-labeling approach.

    This implements the bet sizing methodology from López de Prado Chapter 10:
    "Bet Sizing" using the meta-model probabilities to size positions.

    The key insight is that the primary model determines the DIRECTION (buy/sell),
    while the meta-model determines the SIZE (how much to bet).

    Args:
        meta_proba: Meta-model probabilities (probability that primary prediction is correct)
        primary_predictions: Primary model predictions (-1, 0, 1)
        expected_returns: Optional expected returns for each prediction
        method: Bet sizing method:
                - 'meta_kelly': Kelly criterion based on meta-model probabilities
                - 'meta_probability': Direct probability scaling
                - 'meta_expected_value': Size based on expected value
                - 'meta_confidence': Confidence-based sizing with threshold
        confidence_threshold: Minimum confidence to take a trade (default: 0.5)
        max_bet_size: Maximum position size (default: 1.0)
        min_bet_size: Minimum position size (default: 0.0)

    Returns:
        Bet sizes array (same shape as meta_proba)

    Examples:
        >>> meta_proba = np.array([0.6, 0.8, 0.3, 0.9])
        >>> primary_preds = np.array([1, 1, -1, 1])
        >>> bet_sizes = calculate_bet_sizes_ml(meta_proba, primary_preds, method='meta_kelly')
        >>> print(f"Bet sizes: {bet_sizes}")
        [0.2, 0.6, 0.0, 0.8]

    References:
        López de Prado, "Advances in Financial Machine Learning", Chapter 10.
        "The meta-model's output should be used to size bets, not to determine direction."
    """
    bet_sizes = np.zeros(len(meta_proba))

    for i, (prob, pred) in enumerate(zip(meta_proba, primary_predictions)):
        # Only size positions when primary model has a signal
        if pred == 0:
            bet_sizes[i] = 0.0
            continue

        # Only take trades where meta-model has sufficient confidence
        if prob < confidence_threshold:
            bet_sizes[i] = 0.0
            continue

        if method == "meta_kelly":
            # Kelly criterion using meta-model probability
            # f = 2p - 1 (for even odds)
            # This assumes even odds (win amount equals loss amount)
            kelly = 2 * prob - 1
            bet_sizes[i] = max(0, kelly)

        elif method == "meta_probability":
            # Direct probability scaling
            # Size proportional to probability
            bet_sizes[i] = prob

        elif method == "meta_expected_value":
            # Size based on expected value
            if expected_returns is not None and i < len(expected_returns):
                exp_ret = expected_returns[i]
                # Expected value = prob * gain + (1-prob) * loss
                # Assuming gain = abs(exp_ret), loss = -abs(exp_ret)
                ev = prob * abs(exp_ret) - (1 - prob) * abs(exp_ret)
                # Normalize to [0, 1]
                if exp_ret != 0:
                    bet_sizes[i] = max(0, ev / abs(exp_ret))
            else:
                bet_sizes[i] = prob

        elif method == "meta_confidence":
            # Confidence-based sizing with step function
            # Below threshold: 0, at threshold: min_bet_size, at 1.0: max_bet_size
            if prob < confidence_threshold:
                bet_sizes[i] = 0.0
            else:
                # Linear scaling from threshold to 1.0
                normalized_confidence = (prob - confidence_threshold) / (1.0 - confidence_threshold)
                bet_sizes[i] = min_bet_size + normalized_confidence * (max_bet_size - min_bet_size)

        else:
            raise ValueError(f"Unknown bet sizing method: {method}")

    # Clip to bounds
    bet_sizes = np.clip(bet_sizes, min_bet_size, max_bet_size)

    return bet_sizes


def calculate_bet_sizes_with_discrete_allocation(
    meta_proba: np.ndarray,
    primary_predictions: np.ndarray,
    n_bets: int = 10,
    method: str = "top_k",
) -> np.ndarray:
    """
    Calculate bet sizes using discrete allocation strategy.

    Instead of continuous bet sizing, this approach allocates to a fixed number
    of best opportunities. This follows the "concentrated portfolio" approach
    from López de Prado.

    Args:
        meta_proba: Meta-model probabilities
        primary_predictions: Primary model predictions
        n_bets: Number of top bets to make (default: 10)
        method: Selection method:
                - 'top_k': Allocate equal size to top k bets by probability
                - 'threshold': Allocate to all bets above probability threshold
                - 'optimal_f': Use optimal f allocation (Kelly)

    Returns:
        Bet sizes array (0 or 1/n_bets for selected bets)

    Examples:
        >>> meta_proba = np.array([0.6, 0.8, 0.3, 0.9, 0.7])
        >>> primary_preds = np.array([1, 1, -1, 1, -1])
        >>> bet_sizes = calculate_bet_sizes_with_discrete_allocation(meta_proba, primary_preds, n_bets=2)
        >>> print(f"Selected bets: {bet_sizes.nonzero()[0]}")
    """
    n_samples = len(meta_proba)
    bet_sizes = np.zeros(n_samples)

    # Filter to only active signals
    active_mask = primary_predictions != 0
    active_indices = np.where(active_mask)[0]
    active_proba = meta_proba[active_indices]

    if len(active_indices) == 0:
        return bet_sizes

    if method == "top_k":
        # Select top k bets by probability
        k = min(n_bets, len(active_indices))
        top_k_idx = np.argsort(active_proba)[-k:]
        selected_indices = active_indices[top_k_idx]

        # Equal allocation to selected bets
        if k > 0:
            bet_sizes[selected_indices] = 1.0 / k

    elif method == "threshold":
        # Select all bets above threshold
        threshold = np.percentile(active_proba, 100 - (n_bets / len(active_proba) * 100))
        selected_mask = active_proba >= threshold
        selected_indices = active_indices[selected_mask]

        # Equal allocation
        if len(selected_indices) > 0:
            bet_sizes[selected_indices] = 1.0 / len(selected_indices)

    elif method == "optimal_f":
        # Use Kelly optimal f allocation
        # Sort by probability and allocate proportionally
        sorted_idx = np.argsort(active_proba)[::-1]

        # Allocate using diminishing weights
        for rank, idx in enumerate(sorted_idx):
            original_idx = active_indices[idx]
            # Weight decreases with rank: 1/rank
            if rank == 0:
                bet_sizes[original_idx] = 0.5  # 50% to best bet
            else:
                bet_sizes[original_idx] = 0.5 / (rank + 1)

        # Normalize to sum to 1
        total = bet_sizes.sum()
        if total > 0:
            bet_sizes = bet_sizes / total

    return bet_sizes


def calculate_bet_sizes_with_risk_target(
    meta_proba: np.ndarray,
    primary_predictions: np.ndarray,
    volatilities: np.ndarray,
    risk_target: float = 0.15,
    max_position_size: float = 1.0,
) -> np.ndarray:
    """
    Calculate bet sizes targeting a specific portfolio risk level.

    This implements the risk parity approach from López de Prado, where
    positions are sized to equalize risk contribution across all bets.

    Args:
        meta_proba: Meta-model probabilities (confidence in each signal)
        primary_predictions: Primary model predictions
        volatilities: Volatility for each asset
        risk_target: Target annualized portfolio risk (default: 15%)
        max_position_size: Maximum position size (default: 1.0)

    Returns:
        Bet sizes array

    Examples:
        >>> meta_proba = np.array([0.6, 0.8, 0.3, 0.9])
        >>> vols = np.array([0.2, 0.15, 0.25, 0.18])
        >>> bet_sizes = calculate_bet_sizes_with_risk_target(meta_proba, preds, vols)
    """
    n_samples = len(meta_proba)
    bet_sizes = np.zeros(n_samples)

    # Filter to active signals
    active_mask = (primary_predictions != 0) & (meta_proba >= 0.5)
    active_indices = np.where(active_mask)[0]

    if len(active_indices) == 0:
        return bet_sizes

    # Extract active values
    active_proba = meta_proba[active_indices]
    active_vols = volatilities[active_indices]

    # Calculate risk parity weights
    # Weight is inversely proportional to volatility
    inv_vols = 1.0 / (active_vols + 1e-10)
    weights = inv_vols / inv_vols.sum()

    # Adjust by meta-model probability (confidence)
    # Higher confidence -> larger position
    weights = weights * active_proba
    weights = weights / weights.sum()

    # Scale to meet risk target
    # Portfolio volatility = sqrt(sum(w_i^2 * vol_i^2))
    # For simplicity, assume uncorrelated
    portfolio_vol = np.sqrt(np.sum((weights * active_vols) ** 2))

    if portfolio_vol > 0:
        scaling_factor = risk_target / portfolio_vol
        weights = weights * scaling_factor

    # Apply position size limits
    weights = np.clip(weights, 0, max_position_size)

    # Rescale if needed
    if weights.sum() > 1.0:
        weights = weights / weights.sum()

    bet_sizes[active_indices] = weights

    return bet_sizes


def calculate_bet_sizes_expected_value(
    predictions: np.ndarray,
    probabilities: np.ndarray,
    win_amount: np.ndarray,
    loss_amount: np.ndarray,
    kelly_fraction: float = 0.25,
) -> np.ndarray:
    """
    Calculate bet sizes using the Expected Value and Kelly Criterion.

    This is the most sophisticated bet sizing method that combines:
    1. Expected value calculation
    2. Kelly criterion for optimal sizing
    3. Risk management through fractional Kelly

    Args:
        predictions: Trading signals (-1, 0, 1)
        probabilities: Probability of each prediction being correct
        win_amount: Expected profit if correct (as fraction, e.g., 0.02 for 2%)
        loss_amount: Expected loss if wrong (as fraction, e.g., 0.01 for 1%)
        kelly_fraction: Fraction of full Kelly to use (default: 0.25 for safety)

    Returns:
        Bet sizes array

    Examples:
        >>> preds = np.array([1, 1, -1, 1])
        >>> probs = np.array([0.6, 0.7, 0.55, 0.8])
        >>> wins = np.array([0.02, 0.02, 0.015, 0.025])
        >>> losses = np.array([0.01, 0.01, 0.01, 0.012])
        >>> bet_sizes = calculate_bet_sizes_expected_value(preds, probs, wins, losses)

    References:
        López de Prado, "Advances in Financial Machine Learning", Chapter 10.
        Kelly Criterion: f* = p/v - q/d where:
        - p = probability of winning
        - q = 1-p (probability of losing)
        - v = amount won per unit bet
        - d = amount lost per unit bet
    """
    n_samples = len(predictions)
    bet_sizes = np.zeros(n_samples)

    for i, (pred, prob, win, loss) in enumerate(
        zip(predictions, probabilities, win_amount, loss_amount)
    ):
        if pred == 0 or prob <= 0.5:
            continue

        # Calculate odds
        # v = win amount per unit bet
        # d = loss amount per unit bet
        v = win
        d = loss

        if d <= 0 or v <= 0:
            continue

        # Kelly criterion: f* = p/d - q/v
        # where p is win probability, q = 1-p is loss probability
        p = prob
        q = 1 - p

        kelly = (p / d) - (q / v)

        # Only bet if positive expected value
        if kelly > 0:
            # Apply fractional Kelly for safety
            kelly = kelly * kelly_fraction

            # Cap at reasonable maximum (typically 0.25 or less)
            bet_sizes[i] = min(kelly, 0.25)

    return bet_sizes


def calculate_kelly_criterion(
    win_probability: float,
    win_amount: float = 1.0,
    loss_amount: float = 1.0,
    fraction: float = 1.0,
) -> float:
    """
    Calculate Kelly criterion bet size.

    The Kelly criterion determines the optimal bet size to maximize long-term growth:
    f* = (bp - q) / b

    where:
    - b = win_amount / loss_amount (odds)
    - p = probability of winning
    - q = 1 - p (probability of losing)

    Args:
        win_probability: Probability of winning (0-1)
        win_amount: Amount won per unit bet (default: 1.0)
        loss_amount: Amount lost per unit bet (default: 1.0)
        fraction: Fraction of full Kelly to use (default: 1.0)

    Returns:
        Optimal bet size as fraction of capital

    Examples:
        >>> calculate_kelly_criterion(0.6, 1.0, 1.0)
        0.2  # Bet 20% of capital

        >>> calculate_kelly_criterion(0.55, 2.0, 1.0)
        0.1  # Bet 10% with 2:1 odds
    """
    if win_probability <= 0 or win_probability >= 1:
        return 0.0

    if loss_amount <= 0 or win_amount <= 0:
        return 0.0

    p = win_probability
    q = 1 - p
    b = win_amount / loss_amount

    # Kelly criterion: f* = (bp - q) / b
    kelly = (b * p - q) / b

    # Only bet if positive expected value
    if kelly <= 0:
        return 0.0

    # Apply fractional Kelly for safety
    kelly = kelly * fraction

    return max(0.0, min(kelly, 1.0))


def calculate_bet_sizes_with_meta_model(
    meta_model: object,
    X: np.ndarray,
    primary_predictions: np.ndarray,
    expected_returns: Optional[np.ndarray] = None,
    method: str = "kelly",
    confidence_threshold: float = 0.5,
) -> np.ndarray:
    """
    Calculate bet sizes using a trained meta-model.

    This is the complete end-to-end bet sizing function that:
    1. Gets meta-model probabilities for new data
    2. Converts probabilities to bet sizes
    3. Applies risk management constraints

    Args:
        meta_model: Trained meta-model (must have predict_proba method)
        X: Feature matrix for prediction
        primary_predictions: Primary model predictions
        expected_returns: Optional expected returns
        method: Bet sizing method ('kelly', 'probability', 'expected_value')
        confidence_threshold: Minimum confidence for trading

    Returns:
        Bet sizes array

    Examples:
        >>> from sklearn.ensemble import RandomForestClassifier
        >>> meta_model = RandomForestClassifier().fit(X_train, meta_labels_train)
        >>> bet_sizes = calculate_bet_sizes_with_meta_model(
        ...     meta_model, X_test, primary_preds, method='kelly'
        ... )
    """
    # Get meta-model predictions
    if hasattr(meta_model, "predict_proba"):
        meta_proba_raw = meta_model.predict_proba(X)

        # Extract probability of positive class (meta-label = 1)
        if meta_proba_raw.shape[1] == 2:
            meta_proba = meta_proba_raw[:, 1]
        else:
            # Multi-class: use max probability
            meta_proba = meta_proba_raw.max(axis=1)
    else:
        # No probabilities available, use binary predictions
        meta_pred = meta_model.predict(X)
        meta_proba = meta_pred.astype(float)

    # Calculate bet sizes
    bet_sizes = calculate_bet_sizes_ml(
        meta_proba=meta_proba,
        primary_predictions=primary_predictions,
        expected_returns=expected_returns,
        method=method,
        confidence_threshold=confidence_threshold,
    )

    return bet_sizes
