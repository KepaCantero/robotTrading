"""
Triple Barrier Method for Financial ML Labeling.

Implementation based on Marcos López de Prado's "Advances in Financial Machine Learning", Chapter 3.

The Triple Barrier Method addresses the shortcomings of fixed-time horizon labeling by:
1. Using horizontal barriers (profit taking and stop loss)
2. Using a vertical barrier (time limit)
3. Labeling based on which barrier is hit first

This provides more meaningful labels for ML that account for:
- Volatility (wider stops for volatile assets)
- Risk-reward ratios
- Realistic trading scenarios
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

# Try to import numba for acceleration
try:
    from numba import jit
    HAS_NUMBA = True
except ImportError:
    # Fallback: use a dummy decorator that just returns the function
    def jit(*args, **kwargs):
        """Dummy jit decorator when numba is not available."""
        def decorator(func):
            return func
        return decorator
    HAS_NUMBA = False

# Try to import matplotlib, if not available make plotting optional
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    plt = None

# Try to import volatility, if not available use simple std dev
try:
    from arch import arch_model
    HAS_ARCH = True
except ImportError:
    HAS_ARCH = False


@dataclass
class TripleBarrierConfig:
    """
    Configuration for Triple Barrier labeling.

    Args:
        upper_barrier_pct: Profit target as percentage (e.g., 0.02 for 2%)
        lower_barrier_pct: Stop loss as percentage (e.g., -0.01 for -1%)
        vertical_barrier_days: Time horizon in days/bars
        min_return: Minimum return threshold for labeling
        vol_scale: Scaling factor for volatility-based barriers
        vol_window: Window for volatility calculation
        numba_enabled: Enable Numba acceleration
    """

    upper_barrier_pct: float = 0.02
    lower_barrier_pct: float = -0.01
    vertical_barrier_days: int = 5
    min_return: float = 0.0
    vol_scale: float = 1.5
    vol_window: int = 20
    numba_enabled: bool = True
    metadata: Dict[str, any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.upper_barrier_pct <= 0:
            raise ValueError("upper_barrier_pct must be positive")
        if self.lower_barrier_pct >= 0:
            raise ValueError("lower_barrier_pct must be negative")
        if self.vertical_barrier_days <= 0:
            raise ValueError("vertical_barrier_days must be positive")
        if abs(self.lower_barrier_pct) > self.upper_barrier_pct:
            import warnings

            warnings.warn(
                "Stop loss is larger than profit target. Consider adjusting for positive risk-reward.",
                UserWarning,
            stacklevel=2,
            )


@jit(nopython=True, cache=True)
def get_barrier_labels(
    prices: np.ndarray,
    events: np.ndarray,
    upper_barrier: float,
    lower_barrier: float,
    vertical_barrier: int,
) -> np.ndarray:
    """
    Generate triple barrier labels using Numba-accelerated core logic.

    This function determines which barrier is hit first for each event:
    - 1: Upper barrier hit (profit target reached)
    - -1: Lower barrier hit (stop loss triggered)
    - 0: Vertical barrier hit (time expired)

    Args:
        prices: Array of prices
        events: Array of event indices (entry points)
        upper_barrier: Upper barrier multiplier (e.g., 1.02 for 2% profit)
        lower_barrier: Lower barrier multiplier (e.g., 0.99 for 1% stop)
        vertical_barrier: Number of bars for vertical barrier

    Returns:
        Array of labels: 1 (upper), -1 (lower), 0 (vertical)

    Examples:
        >>> prices = np.array([100.0, 101.0, 102.0, 103.0, 101.5])
        >>> events = np.array([0])
        >>> labels = get_barrier_labels(prices, events, 1.02, 0.99, 3)
        # Returns [1] if price hits 102.0 before hitting 99.0 or 3 bars pass
    """
    n_events = len(events)
    labels = np.zeros(n_events, dtype=np.int64)

    for i in range(n_events):
        t0 = events[i]
        entry_price = prices[t0]

        # Calculate barrier levels
        upper_level = entry_price * upper_barrier
        lower_level = entry_price * lower_barrier

        # Search for first barrier hit
        end_idx = min(t0 + vertical_barrier, len(prices))

        for j in range(t0 + 1, end_idx):
            price = prices[j]

            # Check upper barrier first (profit taking)
            if price >= upper_level:
                labels[i] = 1
                break

            # Check lower barrier (stop loss)
            if price <= lower_level:
                labels[i] = -1
                break

        # If no barrier hit, label is 0 (vertical barrier hit)

    return labels


@jit(nopython=True, cache=True)
def get_barrier_labels_with_timing(
    prices: np.ndarray,
    events: np.ndarray,
    upper_barrier: float,
    lower_barrier: float,
    vertical_barrier: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate triple barrier labels with timing information.

    Returns both the label and the number of bars until barrier hit.

    Args:
        prices: Array of prices
        events: Array of event indices (entry points)
        upper_barrier: Upper barrier multiplier
        lower_barrier: Lower barrier multiplier
        vertical_barrier: Number of bars for vertical barrier

    Returns:
        Tuple of (labels array, bars_to_barrier array)
    """
    n_events = len(events)
    labels = np.zeros(n_events, dtype=np.int64)
    bars_to_barrier = np.zeros(n_events, dtype=np.int64)

    for i in range(n_events):
        t0 = events[i]
        entry_price = prices[t0]

        upper_level = entry_price * upper_barrier
        lower_level = entry_price * lower_barrier

        end_idx = min(t0 + vertical_barrier, len(prices))

        for j in range(t0 + 1, end_idx):
            price = prices[j]

            if price >= upper_level:
                labels[i] = 1
                bars_to_barrier[i] = j - t0
                break

            if price <= lower_level:
                labels[i] = -1
                bars_to_barrier[i] = j - t0
                break

        if labels[i] == 0:
            bars_to_barrier[i] = vertical_barrier

    return labels, bars_to_barrier


def calculate_dynamic_barriers(
    prices: pd.Series,
    events: pd.Series,
    config: TripleBarrierConfig,
    vol_scaling: bool = True,
) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate dynamic barriers adjusted for volatility.

    Uses volatility to adjust barrier widths:
    - High volatility → Wider barriers
    - Low volatility → Narrower barriers

    Args:
        prices: Series of prices
        events: Series of event timestamps (datetime index)
        config: Triple barrier configuration
        vol_scaling: Whether to apply volatility scaling

    Returns:
        Tuple of (upper_barriers, lower_barriers) as Series aligned with events

    Examples:
        >>> prices = pd.Series([100, 101, 102, 103, 104])
        >>> events = pd.Series([pd.Timestamp('2020-01-01')])
        >>> upper, lower = calculate_dynamic_barriers(prices, events, config)
    """
    if not vol_scaling:
        # Use fixed barriers from config
        n_events = len(events)
        upper_barriers = pd.Series(
            [config.upper_barrier_pct] * n_events, index=events.index
        )
        lower_barriers = pd.Series(
            [config.lower_barrier_pct] * n_events, index=events.index
        )
        return upper_barriers, lower_barriers

    # Calculate rolling volatility
    returns = prices.pct_change().dropna()
    vol = returns.rolling(window=config.vol_window).std()

    # Calculate volatility at each event
    event_volatilities = []
    for event_time in events:
        # Find closest volatility measurement
        if event_time in vol.index:
            event_vol = vol.loc[event_time]
        else:
            # Find closest preceding volatility
            valid_idx = vol.index[vol.index <= event_time]
            if len(valid_idx) > 0:
                event_vol = vol.loc[valid_idx[-1]]
            else:
                event_vol = vol.iloc[0] if len(vol) > 0 else 0.01

        event_volatilities.append(event_vol)

    event_volatilities = pd.Series(event_volatilities, index=events.index)

    # Scale barriers based on volatility
    # Higher volatility → wider barriers
    median_vol = event_volatilities.median()
    vol_multiplier = config.vol_scale * (event_volatilities / median_vol)

    upper_barriers = config.upper_barrier_pct * vol_multiplier
    lower_barriers = config.lower_barrier_pct * vol_multiplier

    return upper_barriers, lower_barriers


def get_vertical_barriers(
    events: pd.Series, prices: pd.Series, num_days: int
) -> pd.Series:
    """
    Calculate vertical barriers (time limits) for each event.

    The vertical barrier represents the maximum holding period.
    It prevents positions from being held indefinitely.

    Args:
        events: Series of event timestamps (datetime index)
        prices: Price series with datetime index
        num_days: Number of days for vertical barrier

    Returns:
        Series of vertical barrier timestamps aligned with events

    Examples:
        >>> events = pd.Series([pd.Timestamp('2020-01-01')])
        >>> prices = pd.Series([100, 101, 102], index=pd.date_range('2020-01-01', periods=3))
        >>> vertical = get_vertical_barriers(events, prices, 5)
    """
    vertical_barriers = []

    for event_time in events:
        # Calculate vertical barrier timestamp
        vertical_barrier = event_time + pd.Timedelta(days=num_days)

        # Ensure it's within the data range
        if vertical_barrier > prices.index[-1]:
            vertical_barrier = prices.index[-1]

        vertical_barriers.append(vertical_barrier)

    return pd.Series(vertical_barriers, index=events.index)


class TripleBarrierLabeler:
    """
    Triple Barrier Method labeler for financial ML.

    This class implements the complete triple barrier labeling methodology
    from López de Prado, including:
    - Dynamic barrier calculation
    - Volatility-adjusted barriers
    - Label generation with timing information
    - Visualization and analysis tools

    Attributes:
        config: Configuration for triple barrier labeling
        prices: Historical price data
        events: Entry events (signals)

    Examples:
        >>> config = TripleBarrierConfig(
        ...     upper_barrier_pct=0.02,
        ...     lower_barrier_pct=-0.01,
        ...     vertical_barrier_days=5
        ... )
        >>> labeler = TripleBarrierLabeler(config)
        >>> labels = labeler.fit_transform(prices, events)
        >>> print(labels['label'].value_counts())
    """

    def __init__(self, config: Optional[TripleBarrierConfig] = None):
        """
        Initialize the Triple Barrier labeler.

        Args:
            config: Configuration for labeling. If None, uses defaults.
        """
        self.config = config or TripleBarrierConfig()
        self.prices: Optional[pd.Series] = None
        self.events: Optional[pd.Series] = None
        self.labels_: Optional[pd.DataFrame] = None
        self.barrier_info_: Optional[Dict] = None

    def fit(
        self, prices: pd.Series, events: pd.Series, vol_scaling: bool = True
    ) -> "TripleBarrierLabeler":
        """
        Fit the labeler to price data and events.

        Calculates barriers and generates labels for all events.

        Args:
            prices: Series of prices with datetime index
            events: Series of event timestamps or indices
            vol_scaling: Whether to use volatility-adjusted barriers

        Returns:
            Self for method chaining

        Examples:
            >>> labeler = TripleBarrierLabeler()
            >>> labeler.fit(prices, events)
        """
        self.prices = prices
        self.events = events

        # Convert datetime events to indices if needed
        # Check if events contain datetime values (not just index type)
        if len(events) > 0 and isinstance(events.iloc[0], (pd.Timestamp, np.datetime64)):
            # Events contain datetime values, convert to positional indices
            event_indices = []
            for event_time in events:
                if event_time in prices.index:
                    idx = prices.index.get_loc(event_time)
                    event_indices.append(int(idx))
                else:
                    # Find closest
                    idx = prices.index.get_indexer([event_time], method="nearest")[0]
                    event_indices.append(int(idx))
            event_indices = np.array(event_indices, dtype=np.int64)
        else:
            # Events are already positional indices
            event_indices = np.array(events.values, dtype=np.int64)

        # Calculate dynamic barriers
        upper_barriers_pct, lower_barriers_pct = calculate_dynamic_barriers(
            prices, events, self.config, vol_scaling
        )

        # Convert percentages to multipliers
        upper_multipliers = 1.0 + upper_barriers_pct
        lower_multipliers = 1.0 + lower_barriers_pct

        # Generate labels for each event
        all_labels = []
        all_barriers = []
        all_timing = []

        for i, (event_idx, upper_mult, lower_mult) in enumerate(
            zip(event_indices, upper_multipliers, lower_multipliers)
        ):
            # event_idx should already be a positional integer at this point
            # But let's ensure it's the right type
            pos_idx = int(event_idx)

            # Validate index is within bounds
            if pos_idx < 0 or pos_idx >= len(prices):
                raise ValueError(f"event_idx {pos_idx} out of bounds for prices length {len(prices)}")

            # Get labels for this event
            labels, timing = get_barrier_labels_with_timing(
                prices.values,
                np.array([pos_idx]),
                upper_mult,
                lower_mult,
                self.config.vertical_barrier_days,
            )

            all_labels.append(labels[0])
            all_timing.append(timing[0])

            # Store barrier info
            entry_price = prices.iloc[event_idx]
            all_barriers.append(
                {
                    "entry_price": entry_price,
                    "upper_barrier": entry_price * upper_mult,
                    "lower_barrier": entry_price * lower_mult,
                    "upper_pct": upper_mult - 1.0,
                    "lower_pct": lower_mult - 1.0,
                }
            )

        # Create results DataFrame
        self.labels_ = pd.DataFrame(
            {
                "label": all_labels,
                "bars_to_barrier": all_timing,
                "upper_barrier_pct": [b["upper_pct"] for b in all_barriers],
                "lower_barrier_pct": [b["lower_pct"] for b in all_barriers],
                "entry_price": [b["entry_price"] for b in all_barriers],
            },
            index=events.index,
        )

        # Add barrier hit information
        self.labels_["barrier_hit"] = self.labels_["label"].map(
            {1: "upper", -1: "lower", 0: "vertical"}
        )

        # Store additional info
        self.barrier_info_ = {
            "upper_barriers": all_barriers,
            "event_indices": event_indices,
            "vol_scaling_used": vol_scaling,
        }

        return self

    def transform(self, prices: pd.Series, events: pd.Series) -> pd.DataFrame:
        """
        Transform new events using fitted labeler.

        Args:
            prices: Price series
            events: Event series

        Returns:
            DataFrame with labels
        """
        if self.prices is None or self.events is None:
            raise ValueError("Labeler must be fitted before transform")

        return self.fit(prices, events).labels_

    def fit_transform(
        self, prices: pd.Series, events: pd.Series, vol_scaling: bool = True
    ) -> pd.DataFrame:
        """
        Fit and transform in one step.

        Args:
            prices: Price series
            events: Event series
            vol_scaling: Whether to use volatility scaling

        Returns:
            DataFrame with labels and metadata
        """
        self.fit(prices, events, vol_scaling)
        return self.labels_

    def get_label_distribution(self) -> pd.Series:
        """
        Get the distribution of labels.

        Returns:
            Series with counts of each label type

        Examples:
            >>> labeler.fit(prices, events)
            >>> dist = labeler.get_label_distribution()
            >>> print(dist)
        """
        if self.labels_ is None:
            raise ValueError("Labeler must be fitted first")

        return self.labels_["label"].value_counts()

    def get_average_holding_period(self) -> Dict[int, float]:
        """
        Get average holding period for each label type.

        Returns:
            Dict mapping label to average holding period in bars

        Examples:
            >>> labeler.fit(prices, events)
            >>> avg_hold = labeler.get_average_holding_period()
            >>> print(f"Average hold for winners: {avg_hold[1]} bars")
        """
        if self.labels_ is None:
            raise ValueError("Labeler must be fitted first")

        return (
            self.labels_.groupby("label")["bars_to_barrier"].mean().to_dict()
        )

    def get_bin_labels(self, min_return: float = 0.0) -> np.ndarray:
        """
        Get binary labels for classification (1 for profit, 0 for loss).

        This converts the triple barrier labels to binary:
        - Label 1 (upper barrier) → 1 (profit)
        - Label -1 (lower barrier) → 0 (loss)
        - Label 0 (vertical barrier) → depends on min_return

        Args:
            min_return: Minimum return threshold for vertical barrier to be 1

        Returns:
            Binary labels array

        Examples:
            >>> bin_labels = labeler.get_bin_labels(min_return=0.01)
        """
        if self.labels_ is None:
            raise ValueError("Labeler must be fitted first")

        binary_labels = self.labels_["label"].copy()

        # Convert vertical barrier labels based on return
        vertical_mask = self.labels_["label"] == 0

        # For vertical barriers, we'd need to calculate actual returns
        # This is a simplified version
        binary_labels[vertical_mask] = 1  # Default to 1, can be refined

        # Convert -1 to 0
        binary_labels[binary_labels == -1] = 0

        return binary_labels.values


def plot_triple_barrier(
    prices: pd.Series,
    event_idx: int,
    upper_barrier: float,
    lower_barrier: float,
    vertical_barrier: int,
    label: int,
    ax: Optional["plt.Axes"] = None,  # type: ignore
) -> Optional["plt.Axes"]:  # type: ignore
    """
    Visualize a triple barrier labeling event.

    Creates a visualization showing:
    - Price path
    - Entry point
    - Upper and lower barriers
    - Vertical barrier
    - Which barrier was hit

    Args:
        prices: Price series
        event_idx: Index of the event
        upper_barrier: Upper barrier price level
        lower_barrier: Lower barrier price level
        vertical_barrier: Vertical barrier index
        label: The label that was assigned (1, -1, or 0)
        ax: Optional matplotlib axis

    Returns:
        Matplotlib axis with plot, or None if matplotlib not available

    Examples:
        >>> fig, ax = plt.subplots()
        >>> plot_triple_barrier(prices, event_idx, upper, lower, vertical, label, ax)
        >>> plt.show()
    """
    if not HAS_MATPLOTLIB:
        import warnings
        warnings.warn("Matplotlib not available, skipping visualization", UserWarning, stacklevel=2)
        return None

    if ax is None:
        _, ax = plt.subplots(figsize=(12, 6))  # type: ignore

    # Get price slice for visualization
    end_idx = min(event_idx + vertical_barrier + 5, len(prices))
    start_idx = max(0, event_idx - 5)
    price_slice = prices.iloc[start_idx:end_idx]

    # Plot price
    x_vals = range(len(price_slice))
    ax.plot(x_vals, price_slice.values, "b-", label="Price", linewidth=2)

    # Plot entry point
    entry_x = event_idx - start_idx
    ax.axvline(entry_x, color="green", linestyle="--", alpha=0.5, label="Entry")
    ax.plot(entry_x, prices.iloc[event_idx], "go", markersize=10)

    # Plot horizontal barriers
    ax.axhline(upper_barrier, color="g", linestyle="--", alpha=0.3, label="Upper Barrier")
    ax.axhline(lower_barrier, color="r", linestyle="--", alpha=0.3, label="Lower Barrier")

    # Plot vertical barrier
    vert_x = vertical_barrier - start_idx
    ax.axvline(vert_x, color="orange", linestyle="--", alpha=0.5, label="Vertical Barrier")

    # Highlight the barrier that was hit
    barrier_colors = {1: "green", -1: "red", 0: "orange"}
    barrier_names = {1: "Upper (Profit)", -1: "Lower (Stop)", 0: "Vertical (Time)"}
    color = barrier_colors[label]
    name = barrier_names[label]

    ax.set_title(f"Triple Barrier: {name} Hit", fontsize=12, fontweight="bold")
    ax.set_xlabel("Bars")
    ax.set_ylabel("Price")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    return ax


def meta_labeling(
    primary_labels: np.ndarray,
    features: np.ndarray,
    actual_returns: np.ndarray,
) -> np.ndarray:
    """
    Generate meta-labels for position sizing.

    Meta-labeling determines whether the primary signal was correct,
    which can be used for bet sizing rather than direction.

    Args:
        primary_labels: Primary model predictions (-1, 0, 1)
        features: Feature matrix for ML model
        actual_returns: Actual returns for each event

    Returns:
        Binary meta-labels (1 if primary signal was correct, 0 otherwise)

    Examples:
        >>> meta_labels = meta_labeling(primary_preds, features, actual_returns)
        >>> # Use meta_labels to train a classifier for bet sizing
    """
    meta_labels = np.zeros(len(primary_labels))

    for i, (label, ret) in enumerate(zip(primary_labels, actual_returns)):
        # Check if primary signal was correct
        if (label == 1 and ret > 0) or (label == -1 and ret < 0):
            meta_labels[i] = 1
        else:
            meta_labels[i] = 0

    return meta_labels


def calculate_sample_weights(
    events: pd.Series, labels: pd.DataFrame, max_holding_period: int
) -> pd.Series:
    """
    Calculate sample weights based on uniqueness and overlap.

    Samples with more overlap get lower weights to prevent
    over-representation in ML training.

    Args:
        events: Event timestamps
        labels: DataFrame with labels including 'bars_to_barrier'
        max_holding_period: Maximum holding period for overlap calculation

    Returns:
        Series of sample weights

    Examples:
        >>> weights = calculate_sample_weights(events, labels, max_holding_period=5)
        >>> model.fit(X, y, sample_weight=weights)
    """
    n_samples = len(events)
    weights = np.ones(n_samples)

    for i in range(n_samples):
        t_start = events.iloc[i]
        holding_period = labels["bars_to_barrier"].iloc[i]
        t_end = t_start + pd.Timedelta(days=holding_period)

        # Count overlaps
        overlaps = 0
        for j in range(n_samples):
            if i == j:
                continue

            other_start = events.iloc[j]
            other_holding = labels["bars_to_barrier"].iloc[j]
            other_end = other_start + pd.Timedelta(days=other_holding)

            # Check for overlap
            if not (t_end <= other_start or t_start >= other_end):
                overlaps += 1

        # Weight is inversely proportional to overlaps
        weights[i] = 1.0 / (1.0 + overlaps)

    # Normalize
    weights = weights / weights.sum()

    return pd.Series(weights, index=events.index)


def purged_cv_split(
    n_samples: int,
    n_folds: int = 5,
    embargo_pct: float = 0.01,
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    Generate purged cross-validation splits for time series.

    Prevents data leakage by removing samples near train/test boundaries.

    Args:
        n_samples: Total number of samples
        n_folds: Number of CV folds
        embargo_pct: Percentage of samples to embargo after each split

    Returns:
        List of (train_indices, test_indices) tuples

    Examples:
        >>> splits = purged_cv_split(1000, n_folds=5, embargo_pct=0.01)
        >>> for train_idx, test_idx in splits:
        ...     model.fit(X[train_idx], y[train_idx])
        ...     score = model.score(X[test_idx], y[test_idx])
    """
    from sklearn.model_selection import KFold

    kfold = KFold(n_splits=n_folds, shuffle=False)
    embargo = int(n_samples * embargo_pct)

    purged_splits = []

    for train_idx, test_idx in kfold.split(range(n_samples)):
        # Purge train samples that overlap with test
        train_idx = train_idx[train_idx < test_idx[0] - embargo]

        # Embargo test samples near train
        test_idx = test_idx[test_idx > train_idx[-1] + embargo] if len(train_idx) > 0 else test_idx

        purged_splits.append((train_idx, test_idx))

    return purged_splits


def triple_barrier_method(
    prices: pd.Series,
    events: pd.Series,
    upper_barrier_pct: float = 0.02,
    lower_barrier_pct: float = -0.01,
    vertical_barrier_days: int = 5,
    vol_scaling: bool = True,
    vol_window: int = 20,
    vol_scale: float = 1.5,
) -> pd.DataFrame:
    """
    Apply triple barrier labeling to price data (convenience function).

    This is a simplified interface to the TripleBarrierLabeler class
    for quick labeling without explicit configuration.

    Args:
        prices: Series of prices with datetime index
        events: Series of event timestamps
        upper_barrier_pct: Profit target percentage (default 2%)
        lower_barrier_pct: Stop loss percentage (default -1%)
        vertical_barrier_days: Time horizon in days (default 5)
        vol_scaling: Use volatility-adjusted barriers (default True)
        vol_window: Window for volatility calculation (default 20)
        vol_scale: Volatility scaling factor (default 1.5)

    Returns:
        DataFrame with columns:
        - label: The barrier that was hit (1, -1, or 0)
        - barrier_hit: Which barrier ('upper', 'lower', 'vertical')
        - days_to_barrier: Time until barrier hit
        - upper_barrier_pct: Upper barrier used
        - lower_barrier_pct: Lower barrier used

    Examples:
        >>> labels = triple_barrier_method(
        ...     prices=close_prices,
        ...     events=signal_dates,
        ...     upper_barrier_pct=0.02,
        ...     lower_barrier_pct=-0.01,
        ...     vertical_barrier_days=5
        ... )
        >>> print(labels['label'].value_counts())
    """
    config = TripleBarrierConfig(
        upper_barrier_pct=upper_barrier_pct,
        lower_barrier_pct=lower_barrier_pct,
        vertical_barrier_days=vertical_barrier_days,
        vol_window=vol_window,
        vol_scale=vol_scale,
    )

    labeler = TripleBarrierLabeler(config)
    labels = labeler.fit_transform(prices, events, vol_scaling=vol_scaling)

    return labels
