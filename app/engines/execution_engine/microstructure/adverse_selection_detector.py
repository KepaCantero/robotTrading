"""
Adverse Selection Detection

Implements O'Hara Rule 7.2: Detect adverse selection in trading.

Adverse selection occurs when you consistently trade against better-informed
counterparties, leading to losses.

This module implements:
1. VPIN (Volume-Synchronized PIN) - Probability of Informed Trading
2. Order Flow Toxicity - Easley et al. model
3. Post-trade price movement analysis
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class VPINResult:
    """VPIN (Volume-Synchronized Probability of Informed Trading) result."""

    symbol: str
    vpin: float  # 0-1, higher = more informed trading
    bucket_count: int
    is_high: bool  # VPIN > threshold

    # Components
    buy_volume: float
    sell_volume: float
    imbalance: float


@dataclass
class OrderToxicityResult:
    """Order flow toxicity result."""

    symbol: str
    toxicity_score: float  # Higher = more toxic
    is_toxic: bool

    # Components
    buy_pressure: float
    sell_pressure: float
    order_flow_imbalance: float


@dataclass
class AdverseSelectionResult:
    """Adverse selection detection result."""

    symbol: str
    detected: bool
    confidence: float  # 0-1

    # Metrics
    adverse_move_rate: float  # % of moves against you
    avg_adverse_cost_bps: float
    vpin: Optional[float]
    toxicity: Optional[float]

    # Recommendation
    should_reduce_trading: bool
    recommended_action: str


class VPINCalculator:
    """
    Volume-Synchronized PIN Calculator (O'Hara Rule 7.2).

    VPIN measures the probability of informed trading based on
    order flow imbalance over fixed volume buckets.

    High VPIN = High information asymmetry = Be careful
    """

    def __init__(
        self,
        bucket_size: float = 10000,  # Volume per bucket
        n_buckets: int = 50,  # Number of buckets for rolling average
        threshold: float = 0.4,  # VPIN threshold for "high"
    ):
        """
        Initialize VPIN calculator.

        Args:
            bucket_size: Volume per bucket (shares)
            n_buckets: Number of buckets for moving average
            threshold: VPIN threshold for high information risk
        """
        self.bucket_size = bucket_size
        self.n_buckets = n_buckets
        self.threshold = threshold

        logger.info(
            f"VPINCalculator initialized: bucket_size={bucket_size}, "
            f"n_buckets={n_buckets}, threshold={threshold}"
        )

    def calculate_vpin(
        self,
        df: pd.DataFrame,
        price_col: str = "price",
        volume_col: str = "volume",
        buy_col: Optional[str] = None,  # If available, buy volume
    ) -> VPINResult:
        """
        Calculate VPIN from trade data.

        Args:
            df: DataFrame with trades
            price_col: Price column name
            volume_col: Volume column name
            buy_col: Buy volume column (if available, otherwise infer)

        Returns:
            VPINResult with VPIN and components
        """
        if buy_col is None or buy_col not in df.columns:
            # Infer buy/sell from price changes (tick rule)
            df = self._classify_trades(df, price_col, volume_col)
            buy_col = "buy_volume"
            sell_col = "sell_volume"
        else:
            sell_col = "sell_volume"
            if sell_col not in df.columns:
                df[sell_col] = df[volume_col] - df[buy_col]

        # Create volume buckets
        df["bucket"] = df[volume_col].cumsum() // self.bucket_size

        # Aggregate by bucket
        bucketed = df.groupby("bucket").agg({buy_col: "sum", sell_col: "sum"}).reset_index()

        if len(bucketed) < self.n_buckets:
            logger.warning(
                f"Insufficient data for VPIN: {len(bucketed)} buckets, " f"need {self.n_buckets}"
            )
            return VPINResult(
                symbol="unknown",
                vpin=0.0,
                bucket_count=len(bucketed),
                is_high=False,
                buy_volume=0.0,
                sell_volume=0.0,
                imbalance=0.0,
            )

        # Calculate absolute imbalance per bucket
        bucketed["total_volume"] = bucketed[buy_col] + bucketed[sell_col]
        bucketed["imbalance"] = np.abs(bucketed[buy_col] - bucketed[sell_col])

        # Rolling VPIN
        bucketed["vpin"] = (
            bucketed["imbalance"].rolling(window=self.n_buckets).mean()
            / bucketed["total_volume"].rolling(window=self.n_buckets).mean()
        )

        # Latest VPIN
        latest_vpin = bucketed["vpin"].iloc[-1]

        return VPINResult(
            symbol="unknown",
            vpin=latest_vpin,
            bucket_count=len(bucketed),
            is_high=latest_vpin > self.threshold,
            buy_volume=bucketed[buy_col].sum(),
            sell_volume=bucketed[sell_col].sum(),
            imbalance=np.abs(bucketed[buy_col].sum() - bucketed[sell_col].sum())
            / (bucketed[buy_col].sum() + bucketed[sell_col].sum()),
        )

    def _classify_trades(
        self,
        df: pd.DataFrame,
        price_col: str,
        volume_col: str,
    ) -> pd.DataFrame:
        """
        Classify trades as buys or sells using tick rule.

        Trade at/above previous tick = Buy
        Trade below previous tick = Sell
        """
        df = df.copy()
        df["price_change"] = df[price_col].diff()

        # Classify
        df["is_buy"] = df["price_change"] >= 0

        # Assign volume
        df["buy_volume"] = np.where(df["is_buy"], df[volume_col], 0)
        df["sell_volume"] = np.where(~df["is_buy"], df[volume_col], 0)

        return df

    def calculate_vpin_history(
        self,
        df: pd.DataFrame,
        price_col: str = "price",
        volume_col: str = "volume",
    ) -> pd.Series:
        """
        Calculate VPIN time series.

        Returns VPIN for each bucket (after warmup period).
        """
        self.calculate_vpin(df, price_col, volume_col)

        # Re-calculate with full history
        df = self._classify_trades(df, price_col, volume_col)
        df["bucket"] = df[volume_col].cumsum() // self.bucket_size

        bucketed = (
            df.groupby("bucket").agg({"buy_volume": "sum", "sell_volume": "sum"}).reset_index()
        )

        bucketed["total_volume"] = bucketed["buy_volume"] + bucketed["sell_volume"]
        bucketed["imbalance"] = np.abs(bucketed["buy_volume"] - bucketed["sell_volume"])

        bucketed["vpin"] = bucketed["imbalance"] / bucketed["total_volume"]
        bucketed["vpin_ma"] = bucketed["vpin"].rolling(window=self.n_buckets).mean()

        return bucketed["vpin_ma"].dropna()


class OrderFlowToxicity:
    """
    Order Flow Toxicity Calculator (Easley et al. model).

    Measures how "toxic" the order flow is - i.e., how much
    it indicates informed trading.

    Based on: Easley, López de Prado, O'Hara (2012)
    "Flow Toxicity and Liquidity in a High-Frequency World"
    """

    def __init__(
        self,
        window: int = 100,
        toxicity_threshold: float = 0.5,
    ):
        """
        Initialize toxicity calculator.

        Args:
            window: Rolling window for calculations
            toxicity_threshold: Threshold for "toxic" flow
        """
        self.window = window
        self.toxicity_threshold = toxicity_threshold

        logger.info(
            f"OrderFlowToxicity initialized: window={window}, " f"threshold={toxicity_threshold}"
        )

    def calculate_toxicity(
        self,
        df: pd.DataFrame,
        price_col: str = "price",
        volume_col: str = "volume",
        bid_col: Optional[str] = None,
        ask_col: Optional[str] = None,
    ) -> OrderToxicityResult:
        """
        Calculate order flow toxicity.

        Args:
            df: DataFrame with trades
            price_col: Price column
            volume_col: Volume column
            bid_col: Bid price column (optional)
            ask_col: Ask price column (optional)

        Returns:
            OrderToxicityResult with toxicity metrics
        """
        # Calculate price changes
        df = df.copy()
        df["returns"] = df[price_col].pct_change()

        # If bid/ask available, measure crossing behavior
        if bid_col and ask_col and bid_col in df.columns and ask_col in df.columns:
            df["mid"] = (df[bid_col] + df[ask_col]) / 2

            # Toxicity: Buying above mid or selling below mid
            df["buy_toxic"] = np.where(
                (df[price_col] > df["mid"]) & (df[volume_col] > 0),
                df[volume_col],
                0,
            )
            df["sell_toxic"] = np.where(
                (df[price_col] < df["mid"]) & (df[volume_col] > 0),
                df[volume_col],
                0,
            )

            total_toxic = df["buy_toxic"].sum() + df["sell_toxic"].sum()
            total_volume = df[volume_col].sum()

            toxicity_score = (total_toxic / total_volume) if total_volume > 0 else 0

        else:
            # Fallback: Use price movement toxicity
            # Large price moves = likely informed trading
            df["abs_returns"] = df["returns"].abs()
            df["toxic_volume"] = df[volume_col] * df["abs_returns"]

            toxicity_score = (
                df["toxic_volume"].sum() / df[volume_col].sum() if df[volume_col].sum() > 0 else 0
            )

        # Order flow imbalance
        df["is_buy"] = df["returns"] >= 0
        buy_volume = df.loc[df["is_buy"], volume_col].sum()
        sell_volume = df.loc[~df["is_buy"], volume_col].sum()

        total_flow = buy_volume + sell_volume
        if total_flow > 0:
            ofi = (buy_volume - sell_volume) / total_flow
        else:
            ofi = 0.0

        return OrderToxicityResult(
            symbol="unknown",
            toxicity_score=toxicity_score,
            is_toxic=toxicity_score > self.toxicity_threshold,
            buy_pressure=buy_volume / total_flow if total_flow > 0 else 0,
            sell_pressure=sell_volume / total_flow if total_flow > 0 else 0,
            order_flow_imbalance=ofi,
        )

    def detect_toxic_periods(
        self,
        df: pd.DataFrame,
        price_col: str = "price",
        volume_col: str = "volume",
    ) -> pd.DataFrame:
        """
        Detect periods of high toxicity.

        Returns DataFrame with toxicity flag for each time window.
        """
        df = df.copy()
        df["returns"] = df[price_col].pct_change()
        df["abs_returns"] = df["returns"].abs()

        # Rolling toxicity
        df["toxic_volume"] = df[volume_col] * df["abs_returns"]
        df["rolling_toxicity"] = (
            df["toxic_volume"].rolling(window=self.window).sum()
            / df[volume_col].rolling(window=self.window).sum()
        )

        df["is_toxic_period"] = df["rolling_toxicity"] > self.toxicity_threshold

        return df[["is_toxic_period", "rolling_toxicity"]].fillna(False)


class AdverseSelectionDetector:
    """
    Adverse Selection Detector (O'Hara Rule 7.2).

    Combines multiple signals to detect if you're being adversely selected:
    1. Post-trade price movement analysis
    2. VPIN
    3. Order flow toxicity
    """

    def __init__(
        self,
        lookforward_minutes: int = 30,
        adverse_threshold: float = 0.6,  # 60% adverse moves = bad
    ):
        """
        Initialize detector.

        Args:
            lookforward_minutes: Minutes to look ahead for adverse moves
            adverse_threshold: Threshold for adverse selection detection
        """
        self.lookforward_minutes = lookforward_minutes
        self.adverse_threshold = adverse_threshold

        self.vpin_calc = VPINCalculator()
        self.toxicity_calc = OrderFlowToxicity()

        logger.info(
            f"AdverseSelectionDetector initialized: "
            f"lookforward={lookforward_minutes}m, threshold={adverse_threshold}"
        )

    def detect_adverse_selection(
        self,
        executions: pd.DataFrame,
        price_history: pd.DataFrame,
        exec_time_col: str = "timestamp",
        exec_side_col: str = "side",
        exec_price_col: str = "price",
        price_time_col: str = "timestamp",
        price_col: str = "close",
    ) -> AdverseSelectionResult:
        """
        Detect adverse selection in executions.

        Args:
            executions: DataFrame with executed trades
            price_history: DataFrame with historical prices
            exec_time_col: Execution timestamp column
            exec_side_col: Execution side (BUY/SELL)
            exec_price_col: Execution price column
            price_time_col: Price history timestamp column
            price_col: Price column

        Returns:
            AdverseSelectionResult with detection status
        """
        if len(executions) < 10:
            return AdverseSelectionResult(
                symbol="unknown",
                detected=False,
                confidence=0.0,
                adverse_move_rate=0.0,
                avg_adverse_cost_bps=0.0,
                vpin=None,
                toxicity=None,
                should_reduce_trading=False,
                recommended_action="Insufficient data",
            )

        # Analyze post-trade movements
        adverse_moves = 0
        adverse_costs = []

        for _, exec in executions.iterrows():
            exec_time = exec[exec_time_col]
            exec_side = exec[exec_side_col]
            exec_price = float(exec[exec_price_col])

            # Get future price
            future_time = exec_time + pd.Timedelta(minutes=self.lookforward_minutes)
            future_prices = price_history[
                (price_history[price_time_col] >= exec_time)
                & (price_history[price_time_col] <= future_time)
            ]

            if len(future_prices) == 0:
                continue

            # Use last price in window
            future_price = float(future_prices[price_col].iloc[-1])

            # Check if move was adverse
            if exec_side.upper() == "BUY":
                # Bought, price went down
                is_adverse = future_price < exec_price
                cost_bps = ((exec_price - future_price) / exec_price) * 10000
            else:
                # Sold, price went up
                is_adverse = future_price > exec_price
                cost_bps = ((future_price - exec_price) / exec_price) * 10000

            if is_adverse:
                adverse_moves += 1
                adverse_costs.append(max(0, cost_bps))

        # Calculate metrics
        total_executions = len(executions)
        adverse_rate = adverse_moves / total_executions if total_executions > 0 else 0

        avg_adverse_cost = np.mean(adverse_costs) if adverse_costs else 0

        # Calculate VPIN
        vpin_result = self.vpin_calc.calculate_vpin(
            price_history,
            price_col=price_col,
            volume_col="volume",
        )

        # Calculate toxicity
        toxicity_result = self.toxicity_calc.calculate_toxicity(
            price_history,
            price_col=price_col,
            volume_col="volume",
        )

        # Determine if adverse selection detected
        detected = adverse_rate > self.adverse_threshold

        # Confidence based on multiple signals
        if detected:
            confidence = min(1.0, adverse_rate + (vpin_result.vpin * 0.3))
        else:
            confidence = 0.0

        # Recommendation
        if detected and confidence > 0.7:
            should_reduce = True
            action = "REDUCE_TRADING_FREQUENCY"
        elif detected and confidence > 0.5:
            should_reduce = True
            action = "USE_LIMIT_ORDERS_ONLY"
        else:
            should_reduce = False
            action = "NORMAL_TRADING"

        return AdverseSelectionResult(
            symbol=(
                executions.get("symbol", ["unknown"])[0]
                if "symbol" in executions.columns
                else "unknown"
            ),
            detected=detected,
            confidence=confidence,
            adverse_move_rate=adverse_rate,
            avg_adverse_cost_bps=avg_adverse_cost,
            vpin=vpin_result.vpin,
            toxicity=toxicity_result.toxicity_score,
            should_reduce_trading=should_reduce,
            recommended_action=action,
        )


# Global singletons
_vpin_calculator: VPINCalculator = None
_order_flow_toxicity: OrderFlowToxicity = None
_adverse_selection_detector: AdverseSelectionDetector = None


def get_vpin_calculator(
    bucket_size: float = 10000,
    n_buckets: int = 50,
    threshold: float = 0.4,
) -> VPINCalculator:
    """Get or create global VPINCalculator instance."""
    global _vpin_calculator
    if _vpin_calculator is None:
        _vpin_calculator = VPINCalculator(
            bucket_size=bucket_size,
            n_buckets=n_buckets,
            threshold=threshold,
        )

    return _vpin_calculator


def get_order_flow_toxicity(
    window: int = 100,
    toxicity_threshold: float = 0.5,
) -> OrderFlowToxicity:
    """Get or create global OrderFlowToxicity instance."""
    global _order_flow_toxicity
    if _order_flow_toxicity is None:
        _order_flow_toxicity = OrderFlowToxicity(
            window=window,
            toxicity_threshold=toxicity_threshold,
        )

    return _order_flow_toxicity


def get_adverse_selection_detector(
    lookforward_minutes: int = 30,
    adverse_threshold: float = 0.6,
) -> AdverseSelectionDetector:
    """Get or create global AdverseSelectionDetector instance."""
    global _adverse_selection_detector
    if _adverse_selection_detector is None:
        _adverse_selection_detector = AdverseSelectionDetector(
            lookforward_minutes=lookforward_minutes,
            adverse_threshold=adverse_threshold,
        )

    return _adverse_selection_detector
