"""
Bet Sizing with Meta-Labeling Integration for Financial ML

Based on Marcos López de Prado's "Advances in Financial Machine Learning", Chapters 3 & 10.

This module implements the complete bet sizing pipeline using meta-labeling:
1. Primary Model: Predicts direction (buy/sell)
2. Meta-Model: Predicts probability of primary model being correct
3. Bet Sizing: Uses meta-model probabilities to size positions

Key Innovation:
The primary model determines DIRECTION, while the meta-model determines SIZE.
This separation allows for:
- Better risk management
- Reduced false positives
- Improved risk-adjusted returns
- Dynamic position sizing based on confidence

Bet Sizing Methods with Meta-Labeling:
1. Kelly Criterion with Meta-Probabilities: f* = 2p - 1
2. Expected Value with Meta-Probabilities: EV = p * win - (1-p) * loss
3. Confidence-Based Sizing: Size proportional to meta-model confidence
4. Discrete Allocation: Allocate to top N opportunities
5. Risk Parity with Meta-Weights: Equalize risk contribution

Example Workflow:
    >>> # Step 1: Train primary model
    >>> primary_model = RandomForestClassifier()
    >>> primary_model.fit(X_train, y_train)
    >>>
    >>> # Step 2: Generate meta-labels
    >>> primary_pred = primary_model.predict(X_train)
    >>> meta_labels = (primary_pred == y_train).astype(int)
    >>>
    >>> # Step 3: Train meta-model
    >>> X_meta = np.column_stack([X_train, primary_pred])
    >>> meta_model = RandomForestClassifier()
    >>> meta_model.fit(X_meta, meta_labels)
    >>>
    >>> # Step 4: Calculate bet sizes for new data
    >>> bet_sizes = calculate_bet_sizes_with_meta_labeling(
    ...     primary_model, meta_model, X_test, expected_returns
    ... )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class MetaBetSizingConfig:
    """Configuration for meta-labeling bet sizing."""

    # Bet sizing method
    method: str = "meta_kelly"  # meta_kelly, meta_expected_value, meta_confidence, discrete

    # Confidence thresholds
    confidence_threshold: float = 0.5  # Minimum meta-probability to take trade
    high_confidence_threshold: float = 0.7  # Threshold for "high confidence" sizing

    # Position limits
    max_bet_size: float = 1.0  # Maximum position size
    min_bet_size: float = 0.0  # Minimum position size
    max_total_exposure: float = 1.0  # Maximum total exposure

    # Method-specific parameters
    kelly_fraction: float = 0.25  # Fraction of full Kelly (for safety)

    # Discrete allocation parameters
    n_bets: int = 10  # Number of top bets to make (for discrete method)

    # Risk adjustment
    adjust_for_volatility: bool = True
    adjust_for_correlation: bool = False

    # Expected value parameters
    default_win_amount: float = 0.02  # Default expected win (2%)
    default_loss_amount: float = 0.01  # Default expected loss (1%)

    def __post_init__(self):
        """Validate configuration."""
        valid_methods = [
            "meta_kelly",
            "meta_expected_value",
            "meta_confidence",
            "discrete",
            "risk_parity",
        ]
        if self.method not in valid_methods:
            raise ValueError(f"method must be one of {valid_methods}")

        if self.confidence_threshold < 0 or self.confidence_threshold > 1:
            raise ValueError("confidence_threshold must be between 0 and 1")

        if self.high_confidence_threshold <= self.confidence_threshold:
            raise ValueError("high_confidence_threshold must be > confidence_threshold")

        if self.max_bet_size < 0 or self.max_bet_size > 1:
            raise ValueError("max_bet_size must be between 0 and 1")


@dataclass
class MetaBetSizingResult:
    """Result of meta-labeling bet sizing."""

    bet_sizes: np.ndarray
    """Position sizes for each signal"""

    primary_predictions: np.ndarray
    """Primary model predictions"""

    meta_probabilities: np.ndarray
    """Meta-model probabilities"""

    expected_returns: np.ndarray
    """Expected returns for each signal"""

    confidence_levels: np.ndarray
    """Confidence levels (low, medium, high)"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata"""

    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "bet_sizes": self.bet_sizes.tolist(),
            "primary_predictions": self.primary_predictions.tolist(),
            "meta_probabilities": self.meta_probabilities.tolist(),
            "expected_returns": self.expected_returns.tolist(),
            "confidence_levels": self.confidence_levels.tolist(),
            "avg_bet_size": float(np.mean(self.bet_sizes)),
            "total_exposure": float(np.abs(self.bet_sizes).sum()),
            "n_trades": int((self.bet_sizes > 0).sum()),
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class MetaLabelingBetSizing:
    """
    Bet sizing using meta-labeling probabilities.

    This class implements the complete bet sizing pipeline using
    meta-model probabilities to determine position sizes.

    Example:
        >>> bet_sizing = MetaLabelingBetSizing(method="meta_kelly")
        >>> result = bet_sizing.calculate_sizes(
        ...     primary_model, meta_model, X, expected_returns
        ... )
        >>> print(f"Average bet size: {result.bet_sizes.mean():.2%}")
    """

    def __init__(self, config: Optional[MetaBetSizingConfig] = None):
        """
        Initialize meta-labeling bet sizing.

        Args:
            config: Configuration for bet sizing
        """
        self.config = config or MetaBetSizingConfig()

    def calculate_sizes(
        self,
        primary_model: Any,
        meta_model: Any,
        X: Union[pd.DataFrame, np.ndarray],
        expected_returns: Optional[np.ndarray] = None,
        volatilities: Optional[np.ndarray] = None,
        correlation_matrix: Optional[np.ndarray] = None,
    ) -> MetaBetSizingResult:
        """
        Calculate bet sizes using meta-labeling.

        Args:
            primary_model: Trained primary model (direction)
            meta_model: Trained meta-model (sizing)
            X: Feature matrix
            expected_returns: Optional expected returns for each prediction
            volatilities: Optional volatilities for risk adjustment
            correlation_matrix: Optional correlation matrix

        Returns:
            MetaBetSizingResult with position sizes and metadata

        Example:
            >>> result = bet_sizing.calculate_sizes(
            ...     primary_model, meta_model, X_test, expected_returns
            ... )
            >>> positions = result.bet_sizes * capital
        """
        # Convert to numpy array
        if isinstance(X, pd.DataFrame):
            X = X.values

        # Step 1: Get primary model predictions
        primary_predictions = primary_model.predict(X)

        # Step 2: Get primary model probabilities
        if hasattr(primary_model, "predict_proba"):
            primary_proba = primary_model.predict_proba(X)
            if primary_proba.shape[1] == 2:
                primary_proba = primary_proba[:, 1]
            else:
                primary_proba = primary_proba.max(axis=1)
        else:
            primary_proba = np.ones(len(X)) * 0.5

        # Step 3: Prepare meta features
        X_meta = np.column_stack([X, primary_predictions, primary_proba])

        # Step 4: Get meta-model probabilities
        if hasattr(meta_model, "predict_proba"):
            meta_proba_raw = meta_model.predict_proba(X_meta)
            if meta_proba_raw.shape[1] == 2:
                meta_probabilities = meta_proba_raw[:, 1]
            else:
                meta_probabilities = meta_proba_raw.max(axis=1)
        else:
            meta_predictions = meta_model.predict(X_meta)
            meta_probabilities = meta_predictions.astype(float)

        # Step 5: Calculate bet sizes based on method
        if self.config.method == "meta_kelly":
            bet_sizes = self._meta_kelly_sizing(primary_predictions, meta_probabilities)
        elif self.config.method == "meta_expected_value":
            bet_sizes = self._meta_expected_value_sizing(
                primary_predictions, meta_probabilities, expected_returns
            )
        elif self.config.method == "meta_confidence":
            bet_sizes = self._meta_confidence_sizing(primary_predictions, meta_probabilities)
        elif self.config.method == "discrete":
            bet_sizes = self._discrete_allocation(primary_predictions, meta_probabilities)
        elif self.config.method == "risk_parity":
            bet_sizes = self._risk_parity_sizing(
                primary_predictions, meta_probabilities, volatilities
            )
        else:
            raise ValueError(f"Unknown method: {self.config.method}")

        # Step 6: Apply volatility adjustment
        if self.config.adjust_for_volatility and volatilities is not None:
            bet_sizes = self._adjust_for_volatility(bet_sizes, volatilities)

        # Step 7: Apply correlation adjustment
        if self.config.adjust_for_correlation and correlation_matrix is not None:
            bet_sizes = self._adjust_for_correlation(
                bet_sizes, correlation_matrix, primary_predictions
            )

        # Step 8: Apply position size limits
        bet_sizes = np.clip(bet_sizes, 0, self.config.max_bet_size)

        # Step 9: Apply exposure limit
        bet_sizes = self._apply_exposure_limit(bet_sizes)

        # Step 10: Calculate confidence levels
        confidence_levels = self._calculate_confidence_levels(meta_probabilities)

        # Default expected returns if not provided
        if expected_returns is None:
            expected_returns = np.full(
                len(X),
                self.config.default_win_amount,
            )

        return MetaBetSizingResult(
            bet_sizes=bet_sizes,
            primary_predictions=primary_predictions,
            meta_probabilities=meta_probabilities,
            expected_returns=expected_returns,
            confidence_levels=confidence_levels,
            metadata={
                "method": self.config.method,
                "n_signals": len(X),
                "avg_meta_probability": float(np.mean(meta_probabilities)),
                "avg_bet_size": float(np.mean(bet_sizes)),
                "total_exposure": float(np.abs(bet_sizes).sum()),
            },
        )

    def _meta_kelly_sizing(
        self,
        primary_predictions: np.ndarray,
        meta_probabilities: np.ndarray,
    ) -> np.ndarray:
        """
        Calculate bet sizes using Kelly criterion with meta-probabilities.

        Kelly formula: f* = 2p - 1 (for even odds)
        where p is the meta-model probability.

        Args:
            primary_predictions: Primary model predictions
            meta_probabilities: Meta-model probabilities

        Returns:
            Kelly bet sizes
        """
        bet_sizes = np.zeros(len(meta_probabilities))

        for i, (pred, meta_prob) in enumerate(zip(primary_predictions, meta_probabilities)):
            # Only size positions when primary model has a signal
            if pred == 0:
                continue

            # Only take trades where meta-model has sufficient confidence
            if meta_prob < self.config.confidence_threshold:
                continue

            # Kelly criterion with even odds: f = 2p - 1
            kelly = 2 * meta_prob - 1

            # Only bet if positive expected value
            if kelly > 0:
                # Apply fractional Kelly for safety
                kelly = kelly * self.config.kelly_fraction

                bet_sizes[i] = max(0, kelly)

        return bet_sizes

    def _meta_expected_value_sizing(
        self,
        primary_predictions: np.ndarray,
        meta_probabilities: np.ndarray,
        expected_returns: Optional[np.ndarray],
    ) -> np.ndarray:
        """
        Calculate bet sizes using expected value with meta-probabilities.

        EV = p * win_amount + (1-p) * loss_amount

        Args:
            primary_predictions: Primary model predictions
            meta_probabilities: Meta-model probabilities
            expected_returns: Expected returns for each prediction

        Returns:
            Expected value bet sizes
        """
        bet_sizes = np.zeros(len(meta_probabilities))

        for i, (pred, meta_prob) in enumerate(zip(primary_predictions, meta_probabilities)):
            if pred == 0:
                continue

            if meta_prob < self.config.confidence_threshold:
                continue

            # Get expected return
            if expected_returns is not None and i < len(expected_returns):
                exp_ret = expected_returns[i]
            else:
                exp_ret = self.config.default_win_amount

            # Assume loss is half of expected return
            win_amount = abs(exp_ret)
            loss_amount = abs(exp_ret) * 0.5

            # Calculate expected value
            p = meta_prob
            q = 1 - p
            ev = p * win_amount - q * loss_amount

            # Normalize to [0, 1]
            if win_amount + loss_amount > 0:
                normalized_ev = max(0, ev / (win_amount + loss_amount))
                bet_sizes[i] = normalized_ev

        return bet_sizes

    def _meta_confidence_sizing(
        self,
        primary_predictions: np.ndarray,
        meta_probabilities: np.ndarray,
    ) -> np.ndarray:
        """
        Calculate bet sizes based on confidence levels.

        - Low confidence (p < 0.5): No trade
        - Medium confidence (0.5 <= p < 0.7): Small position
        - High confidence (p >= 0.7): Full position

        Args:
            primary_predictions: Primary model predictions
            meta_probabilities: Meta-model probabilities

        Returns:
            Confidence-based bet sizes
        """
        bet_sizes = np.zeros(len(meta_probabilities))

        for i, (pred, meta_prob) in enumerate(zip(primary_predictions, meta_probabilities)):
            if pred == 0:
                continue

            # Low confidence: no trade
            if meta_prob < self.config.confidence_threshold:
                bet_sizes[i] = 0.0

            # Medium confidence: linear scaling
            elif meta_prob < self.config.high_confidence_threshold:
                # Scale from 0 to 0.5
                norm_prob = (meta_prob - self.config.confidence_threshold) / (
                    self.config.high_confidence_threshold - self.config.confidence_threshold
                )
                bet_sizes[i] = norm_prob * 0.5

            # High confidence: scale from 0.5 to max_bet_size
            else:
                norm_prob = (meta_prob - self.config.high_confidence_threshold) / (
                    1.0 - self.config.high_confidence_threshold
                )
                bet_sizes[i] = 0.5 + norm_prob * (self.config.max_bet_size - 0.5)

        return bet_sizes

    def _discrete_allocation(
        self,
        primary_predictions: np.ndarray,
        meta_probabilities: np.ndarray,
    ) -> np.ndarray:
        """
        Calculate bet sizes using discrete allocation.

        Allocate equal size to top N opportunities by meta-probability.

        Args:
            primary_predictions: Primary model predictions
            meta_probabilities: Meta-model probabilities

        Returns:
            Discrete allocation bet sizes
        """
        n_samples = len(meta_probabilities)
        bet_sizes = np.zeros(n_samples)

        # Filter to active signals with sufficient confidence
        active_mask = (primary_predictions != 0) & (
            meta_probabilities >= self.config.confidence_threshold
        )
        active_indices = np.where(active_mask)[0]

        if len(active_indices) == 0:
            return bet_sizes

        # Get top N bets
        n_bets = min(self.config.n_bets, len(active_indices))
        top_k_idx = np.argsort(meta_probabilities[active_indices])[-n_bets:]
        selected_indices = active_indices[top_k_idx]

        # Equal allocation to selected bets
        if n_bets > 0:
            bet_sizes[selected_indices] = 1.0 / n_bets

        return bet_sizes

    def _risk_parity_sizing(
        self,
        primary_predictions: np.ndarray,
        meta_probabilities: np.ndarray,
        volatilities: Optional[np.ndarray],
    ) -> np.ndarray:
        """
        Calculate bet sizes using risk parity with meta-weights.

        Combine risk parity (inverse volatility) with meta-model confidence.

        Args:
            primary_predictions: Primary model predictions
            meta_probabilities: Meta-model probabilities
            volatilities: Volatility for each asset

        Returns:
            Risk parity bet sizes with meta-weighting
        """
        bet_sizes = np.zeros(len(meta_probabilities))

        # Filter to active signals
        active_mask = (primary_predictions != 0) & (
            meta_probabilities >= self.config.confidence_threshold
        )
        active_indices = np.where(active_mask)[0]

        if len(active_indices) == 0:
            return bet_sizes

        # Default volatilities if not provided
        if volatilities is None:
            active_vols = np.ones(len(active_indices))
        else:
            active_vols = volatilities[active_indices]

        # Risk parity: weight proportional to 1/volatility
        inv_vols = 1.0 / (active_vols + 1e-10)
        base_weights = inv_vols / inv_vols.sum()

        # Adjust by meta-model probability (confidence)
        active_proba = meta_probabilities[active_indices]
        adjusted_weights = base_weights * active_proba

        # Normalize
        adjusted_weights = adjusted_weights / adjusted_weights.sum()

        bet_sizes[active_indices] = adjusted_weights

        return bet_sizes

    def _adjust_for_volatility(
        self,
        bet_sizes: np.ndarray,
        volatilities: np.ndarray,
    ) -> np.ndarray:
        """Adjust bet sizes for volatility."""
        # Normalize volatilities
        norm_vol = volatilities / volatilities.mean()

        # Inverse volatility scaling
        vol_adjustment = 1.0 / (norm_vol + 1e-10)

        return bet_sizes * vol_adjustment

    def _adjust_for_correlation(
        self,
        bet_sizes: np.ndarray,
        correlation_matrix: np.ndarray,
        primary_predictions: np.ndarray,
    ) -> np.ndarray:
        """Adjust bet sizes for correlation."""
        # Get active positions
        active_mask = (bet_sizes > 0) & (primary_predictions != 0)
        active_indices = np.where(active_mask)[0]

        if len(active_indices) < 2:
            return bet_sizes

        # Calculate average correlation for each position
        avg_correlations = np.zeros(len(active_indices))

        for i, idx in enumerate(active_indices):
            corrs = correlation_matrix[idx, active_indices]
            corrs = np.delete(corrs, i)  # Remove self-correlation
            avg_correlations[i] = np.abs(corrs).mean()

        # Adjust bet sizes: higher correlation → smaller size
        correlation_adjustment = 1.0 / (1.0 + avg_correlations)
        bet_sizes[active_indices] = bet_sizes[active_indices] * correlation_adjustment

        return bet_sizes

    def _apply_exposure_limit(self, bet_sizes: np.ndarray) -> np.ndarray:
        """Apply portfolio exposure limit."""
        total_exposure = bet_sizes.sum()

        if total_exposure > self.config.max_total_exposure:
            scale_factor = self.config.max_total_exposure / total_exposure
            bet_sizes = bet_sizes * scale_factor

        return bet_sizes

    def _calculate_confidence_levels(
        self,
        meta_probabilities: np.ndarray,
    ) -> np.ndarray:
        """
        Calculate confidence levels for each prediction.

        Returns:
            Array of confidence levels: 0 (low), 1 (medium), 2 (high)
        """
        confidence_levels = np.zeros(len(meta_probabilities), dtype=int)

        for i, prob in enumerate(meta_probabilities):
            if prob < self.config.confidence_threshold:
                confidence_levels[i] = 0  # Low
            elif prob < self.config.high_confidence_threshold:
                confidence_levels[i] = 1  # Medium
            else:
                confidence_levels[i] = 2  # High

        return confidence_levels


def calculate_bet_sizes_with_meta_labeling(
    primary_model: Any,
    meta_model: Any,
    X: Union[pd.DataFrame, np.ndarray],
    expected_returns: Optional[np.ndarray] = None,
    method: str = "meta_kelly",
    confidence_threshold: float = 0.5,
    max_bet_size: float = 1.0,
    **kwargs,
) -> np.ndarray:
    """
    Calculate bet sizes using meta-labeling models.

    Convenience function for quick bet sizing with meta-labeling.

    Args:
        primary_model: Trained primary model
        meta_model: Trained meta-model
        X: Feature matrix
        expected_returns: Optional expected returns
        method: Bet sizing method
        confidence_threshold: Minimum confidence for trading
        max_bet_size: Maximum position size
        **kwargs: Additional arguments for MetaBetSizingConfig

    Returns:
        Bet sizes array

    Example:
        >>> bet_sizes = calculate_bet_sizes_with_meta_labeling(
        ...     primary_model, meta_model, X_test,
        ...     method="meta_kelly", confidence_threshold=0.6
        ... )
        >>> print(f"Average bet size: {bet_sizes.mean():.2%}")
    """
    config = MetaBetSizingConfig(
        method=method,
        confidence_threshold=confidence_threshold,
        max_bet_size=max_bet_size,
        **kwargs,
    )

    bet_sizing = MetaLabelingBetSizing(config)
    result = bet_sizing.calculate_sizes(primary_model, meta_model, X, expected_returns)

    return result.bet_sizes


def calculate_expected_value_with_meta_probabilities(
    meta_probabilities: np.ndarray,
    primary_predictions: np.ndarray,
    win_amounts: Optional[np.ndarray] = None,
    loss_amounts: Optional[np.ndarray] = None,
    default_win: float = 0.02,
    default_loss: float = 0.01,
) -> np.ndarray:
    """
    Calculate expected value using meta-model probabilities.

    EV = p * win + (1-p) * loss

    Args:
        meta_probabilities: Meta-model probabilities
        primary_predictions: Primary model predictions
        win_amounts: Expected win amounts
        loss_amounts: Expected loss amounts
        default_win: Default win amount
        default_loss: Default loss amount

    Returns:
        Expected value array

    Example:
        >>> ev = calculate_expected_value_with_meta_probabilities(
        ...     meta_proba, primary_preds, win_amounts, loss_amounts
        ... )
        >>> print(f"Average EV: {ev.mean():.4f}")
    """
    n_samples = len(meta_probabilities)
    expected_values = np.zeros(n_samples)

    # Default values
    if win_amounts is None:
        win_amounts = np.full(n_samples, default_win)
    if loss_amounts is None:
        loss_amounts = np.full(n_samples, default_loss)

    for i, (meta_prob, pred) in enumerate(zip(meta_probabilities, primary_predictions)):
        if pred == 0:
            continue

        p = meta_prob
        q = 1 - p
        win = win_amounts[i] if i < len(win_amounts) else default_win
        loss = loss_amounts[i] if i < len(loss_amounts) else default_loss

        ev = p * win - q * loss
        expected_values[i] = ev

    return expected_values


def calculate_kelly_with_meta_probabilities(
    meta_probabilities: np.ndarray,
    primary_predictions: np.ndarray,
    win_amounts: Optional[np.ndarray] = None,
    loss_amounts: Optional[np.ndarray] = None,
    kelly_fraction: float = 0.25,
) -> np.ndarray:
    """
    Calculate Kelly criterion using meta-model probabilities.

    Kelly: f* = p/d - q/v where:
    - p = probability of winning (meta-probability)
    - q = 1-p (probability of losing)
    - d = loss amount per unit bet
    - v = win amount per unit bet

    Args:
        meta_probabilities: Meta-model probabilities
        primary_predictions: Primary model predictions
        win_amounts: Expected win amounts
        loss_amounts: Expected loss amounts
        kelly_fraction: Fraction of full Kelly to use

    Returns:
        Kelly fractions array

    Example:
        >>> kelly = calculate_kelly_with_meta_probabilities(
        ...     meta_proba, primary_preds, win_amounts, loss_amounts
        ... )
        >>> print(f"Average Kelly: {kelly.mean():.4f}")
    """
    n_samples = len(meta_probabilities)
    kelly_fractions = np.zeros(n_samples)

    # Default values
    if win_amounts is None:
        win_amounts = np.full(n_samples, 0.02)
    if loss_amounts is None:
        loss_amounts = np.full(n_samples, 0.01)

    for i, (meta_prob, pred) in enumerate(zip(meta_probabilities, primary_predictions)):
        if pred == 0:
            continue

        p = meta_prob
        q = 1 - p
        v = win_amounts[i] if i < len(win_amounts) else 0.02
        d = loss_amounts[i] if i < len(loss_amounts) else 0.01

        if d > 0 and v > 0:
            kelly = (p / d) - (q / v)

            # Only bet if positive EV
            if kelly > 0:
                kelly_fractions[i] = kelly * kelly_fraction

    return kelly_fractions
