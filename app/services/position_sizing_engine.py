import logging
from decimal import Decimal
from typing import Dict, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)

"""
Position Sizing Engine with ATR-Based Dynamic Stop Loss and Kelly Criterion.

TASK-IND-2: Implements dynamic stop loss based on ATR (Average True Range).
Uses ATR * 2 as default multiplier for adaptive stop loss that adjusts to volatility.

RULE-01-1.9: Implements Kelly Criterion position sizing (Half-Kelly conservative approach).
Kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
Capped at 25% of capital with Half-Kelly safety multiplier.

Configuration:
This module now uses centralized configuration from config/risk_management.yaml:
- ATR multipliers (1.0, 2.0, 3.0) are loaded from config
- Position sizing percentages are loaded from config
- Risk per trade percentages are loaded from config
"""

# Import centralized configuration
try:
    from app.core.config.strategy_config_loader import get_strategy_config

    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False


class PositionSizingEngine:
    """
    TASK-IND-2, IND-4: Calculates dynamic stop loss and position sizing based on ATR.

    Stop Loss Formula: stop_loss_distance = ATR * multiplier
    Default multiplier: 2.0 (2x ATR) - loaded from config
    Position Sizing: risk_per_trade = 2% capital / (ATR * 2)
    """

    def __init__(self, atr_multiplier: Optional[float] = None):
        """
        Initialize calculator.

        Args:
            atr_multiplier: Multiplier for ATR (default loaded from config, typically 2.0)
        """
        if atr_multiplier is None and HAS_CONFIG_LOADER:
            strategy_config = get_strategy_config()
            atr_multiplier = strategy_config.get_atr_multiplier('default_stop')
        elif atr_multiplier is None:
            atr_multiplier = 2.0

        self.atr_multiplier = Decimal(str(atr_multiplier))

    def calculate_stop_loss_price(
        self,
        entry_price: Decimal,
        direction: str,
        atr: Optional[float] = None,
        stop_loss_pct: Optional[float] = None,
    ) -> Optional[Decimal]:
        """
        TASK-IND-2: Calculate dynamic stop loss price.

        Priority:
        1. If ATR available: use ATR * multiplier (adaptive to volatility)
        2. If stop_loss_pct provided: use percentage-based stop
        3. Return None if neither available

        Args:
            entry_price: Entry price of the trade
            direction: 'buy' or 'sell' (case-insensitive)
            atr: Average True Range value
            stop_loss_pct: Stop loss percentage (fallback)

        Returns:
            Stop loss price or None
        """
        if not entry_price or entry_price <= 0:
            return None

        # Normalize direction to lowercase for case-insensitive comparison
        direction_normalized = direction.lower() if isinstance(direction, str) else direction

        # Validate direction
        if direction_normalized not in ["buy", "sell"]:
            return None

        # TASK-IND-2: Use ATR-based dynamic stop if available
        if atr is not None:
            atr_value = Decimal(str(atr))
            stop_distance = atr_value * self.atr_multiplier

            if direction_normalized == "buy":
                return entry_price - stop_distance
            elif direction_normalized == "sell":
                return entry_price + stop_distance

        # Fallback: Use percentage-based stop loss
        if stop_loss_pct is not None:
            stop_pct = Decimal(str(stop_loss_pct))

            if direction_normalized == "buy":
                return entry_price * (Decimal("1") - stop_pct)
            elif direction_normalized == "sell":
                return entry_price * (Decimal("1") + stop_pct)

        return None

    def calculate_position_size_from_atr(
        self,
        capital: Decimal,
        risk_per_trade_pct: Optional[float] = None,
        entry_price: Decimal = None,
        atr: Optional[float] = None,
    ) -> Optional[Decimal]:
        """
        TASK-IND-4: Calculate position size based on ATR.

        Formula: risk_per_trade = 2% capital / (ATR * 2)
        This ensures consistent risk across different volatility levels.

        Args:
            capital: Total capital available
            risk_per_trade_pct: Risk per trade as percentage (loaded from config if None)
            entry_price: Entry price for the position
            atr: Average True Range

        Returns:
            Position size in shares or None
        """
        if not capital or capital <= 0 or not entry_price or entry_price <= 0:
            return None

        # Load default risk per trade from config if not provided
        if risk_per_trade_pct is None:
            if HAS_CONFIG_LOADER:
                strategy_config = get_strategy_config()
                risk_config = strategy_config.get_risk_config()
                risk_per_trade_pct = float(
                    risk_config.get('risk_per_trade', {}).get('default', 0.02)
                )
            else:
                risk_per_trade_pct = 0.02  # Default 2% risk per trade

        # Calculate risk amount in dollars
        risk_amount = capital * Decimal(str(risk_per_trade_pct)) / Decimal("100")

        # TASK-IND-4: Use ATR-based stop distance if available
        if atr is not None and atr > 0:
            stop_distance = Decimal(str(atr)) * self.atr_multiplier

            # CRITICAL VALIDATION: Ensure stop distance is reasonable vs entry price
            # Stop distance should not exceed 20% of entry price (sanity check)
            max_stop_pct = Decimal("0.20")
            max_stop_distance = entry_price * max_stop_pct

            if stop_distance > max_stop_distance:
                logger.warning(
                    f"ATR stop distance {stop_distance} exceeds 20% of price {entry_price}, "
                    f"capping at {max_stop_distance}"
                )
                stop_distance = max_stop_distance

            if stop_distance > 0:
                # Calculate shares: risk_amount / stop_distance_per_share
                # This gives us how many shares we can buy where losing stop_distance per share
                # equals our total risk amount
                shares = risk_amount / stop_distance

                # Verify result makes sense
                position_value = shares * entry_price
                if position_value > capital:
                    # Cap at available capital
                    shares = capital / entry_price
                    logger.debug(f"Position size capped at available capital: {shares} shares")

                return shares

        # Fallback: Use fixed percentage stop (e.g., 5%)
        default_stop_pct = Decimal("0.05")
        stop_distance = entry_price * default_stop_pct

        if stop_distance > 0:
            shares = risk_amount / stop_distance
            return shares

        return None

    def calculate_kelly_position_size(
        self,
        win_rate: Union[float, Decimal],
        avg_win: Union[float, Decimal],
        avg_loss: Union[float, Decimal],
        capital: Optional[Decimal] = None,
    ) -> Dict[str, Union[Decimal, float]]:
        """
        RULE-01-1.9: Calculate Kelly Criterion position size with Half-Kelly safety.

        Kelly Formula: (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

        Conservative constraints (Ernest Chan recommendations):
        - Half-Kelly: Reduces volatility and drawdown while maintaining most growth
        - Max position: 25% of capital (prevents overconcentration)
        - Min position: 0% (negative Kelly means don't trade)

        Args:
            win_rate: Win rate as decimal (0.0 to 1.0), NOT percentage
            avg_win: Average winning trade profit (positive value)
            avg_loss: Average losing trade loss (negative value, typically expressed as positive)
            capital: Total available capital (optional, for position value calculation)

        Returns:
            Dictionary with:
                - kelly_fraction: Raw Kelly fraction (can be negative)
                - half_kelly_fraction: Half-Kelly with 25% cap (0.0 to 0.25)
                - position_percentage: Recommended position as % of capital (0-100)
                - position_value: Dollar amount of position (if capital provided)
                - recommendation: 'BUY', 'REDUCE', or 'AVOID'

        Raises:
            ValueError: If avg_win <= 0 or inputs are invalid

        Example:
            >>> engine = PositionSizingEngine()
            >>> result = engine.calculate_kelly_position_size(
            ...     win_rate=0.55,
            ...     avg_win=100.0,
            ...     avg_loss=75.0,
            ...     capital=Decimal("10000")
            ... )
            >>> print(result['position_value'])  # e.g., Decimal("1500.00")
        """
        # Input validation
        if not isinstance(win_rate, (int, float, Decimal)):
            raise ValueError(f"win_rate must be numeric, got {type(win_rate)}")

        if not isinstance(avg_win, (int, float, Decimal)):
            raise ValueError(f"avg_win must be numeric, got {type(avg_win)}")

        if not isinstance(avg_loss, (int, float, Decimal)):
            raise ValueError(f"avg_loss must be numeric, got {type(avg_loss)}")

        # Convert to float for calculation
        win_rate_float = float(win_rate)
        avg_win_float = float(avg_win)
        avg_loss_float = float(abs(avg_loss))  # Use absolute value for calculation

        # Check for NaN values
        import math

        if math.isnan(win_rate_float):
            raise ValueError("win_rate cannot be NaN")
        if math.isnan(avg_win_float):
            raise ValueError("avg_win cannot be NaN")
        if math.isnan(avg_loss_float):
            raise ValueError("avg_loss cannot be NaN")

        # Check for infinity
        if math.isinf(win_rate_float):
            raise ValueError("win_rate cannot be infinite")
        if math.isinf(avg_win_float):
            raise ValueError("avg_win cannot be infinite")
        if math.isinf(avg_loss_float):
            raise ValueError("avg_loss cannot be infinite")

        # Validate ranges
        if not 0.0 <= win_rate_float <= 1.0:
            raise ValueError(f"win_rate must be between 0 and 1, got {win_rate_float}")

        if avg_win_float <= 0:
            raise ValueError(f"avg_win must be positive, got {avg_win_float}")

        if avg_loss_float <= 0:
            raise ValueError(
                f"avg_loss must be positive (absolute loss value), got {avg_loss_float}"
            )

        # Calculate raw Kelly fraction
        # Kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        # This represents the optimal fraction of capital to wager
        kelly_numerator = (win_rate_float * avg_win_float) - ((1 - win_rate_float) * avg_loss_float)
        raw_kelly = kelly_numerator / avg_win_float

        # Apply Half-Kelly (conservative approach per Ernest Chan)
        half_kelly = raw_kelly * 0.5

        # Cap at 25% maximum position size (risk management constraint)
        capped_kelly = max(0.0, min(half_kelly, 0.25))

        # Generate recommendation based on raw Kelly
        if raw_kelly <= 0:
            recommendation = "AVOID"
            logger.warning(
                f"Kelly Criterion indicates negative expectancy: {raw_kelly:.4f}. "
                f"Recommendation: AVOID trade. win_rate={win_rate_float:.2f}, "
                f"avg_win=${avg_win_float:.2f}, avg_loss=${avg_loss_float:.2f}"
            )
        elif raw_kelly < 0.02:
            recommendation = "REDUCE"
            logger.info(
                f"Kelly Criterion indicates marginal edge: {raw_kelly:.4f}. "
                f"Recommendation: REDUCE position size. win_rate={win_rate_float:.2f}"
            )
        else:
            recommendation = "BUY"
            logger.debug(
                f"Kelly Criterion favorable: {raw_kelly:.4f}. "
                f"Half-Kelly (capped): {capped_kelly:.4f}"
            )

        # Calculate position details
        result = {
            "kelly_fraction": Decimal(str(raw_kelly)),
            "half_kelly_fraction": Decimal(str(capped_kelly)),
            "position_percentage": Decimal(str(capped_kelly * 100)),
            "recommendation": recommendation,
        }

        # Add position value if capital provided
        if capital is not None:
            if capital <= 0:
                raise ValueError(f"capital must be positive, got {capital}")

            position_value = capital * Decimal(str(capped_kelly))
            result["position_value"] = position_value

            # Validate position value is reasonable
            max_position_value = capital * Decimal("0.25")
            if position_value > max_position_value:
                logger.warning(
                    f"Calculated position value ${position_value:.2f} exceeds "
                    f"25% cap of ${max_position_value:.2f}. Capping at 25%."
                )
                result["position_value"] = max_position_value

        return result

    def calculate_kelly_from_backtest(
        self,
        performance_metrics: Dict[str, Union[Decimal, float, int]],
        capital: Optional[Decimal] = None,
    ) -> Dict[str, Union[Decimal, float, str]]:
        """
        Calculate Kelly position size from backtest performance metrics.

        Convenience method that extracts win_rate, avg_win, and avg_loss
        from a PerformanceMetrics object or dictionary and applies Kelly Criterion.

        Args:
            performance_metrics: Dictionary with keys:
                - win_rate: Win rate percentage (0-100) or decimal (0-1)
                - avg_win: Average winning trade profit
                - avg_loss: Average losing trade loss
                Alternatively, can extract from PerformanceMetrics object
            capital: Total available capital (optional)

        Returns:
            Dictionary with Kelly recommendations (see calculate_kelly_position_size)

        Example:
            >>> from app.backtesting.metrics import MetricsCalculator
            >>> metrics = calculator.calculate_all_metrics(...)
            >>> engine = PositionSizingEngine()
            >>> kelly_result = engine.calculate_kelly_from_backtest(
            ...     metrics.model_dump(),
            ...     capital=Decimal("10000")
            ... )
        """
        # Extract metrics with fallback handling
        win_rate = performance_metrics.get("win_rate", 0)
        avg_win = performance_metrics.get("avg_win", 0)
        avg_loss = performance_metrics.get("avg_loss", 0)

        # Handle win_rate in percentage form (common in backtesting output)
        # Convert to decimal if > 1.0
        if isinstance(win_rate, (int, float, Decimal)) and win_rate > 1.0:
            win_rate_decimal = Decimal(str(win_rate)) / Decimal("100")
        else:
            win_rate_decimal = Decimal(str(win_rate))

        # Validate we have meaningful metrics
        if float(avg_win) <= 0 or float(abs(avg_loss)) <= 0:
            logger.warning(
                f"Insufficient backtest data for Kelly calculation. "
                f"avg_win={avg_win}, avg_loss={avg_loss}. Using fallback 2% rule."
            )
            # Fallback to 2% rule when Kelly metrics unavailable
            fallback_result = {
                "kelly_fraction": Decimal("0.02"),
                "half_kelly_fraction": Decimal("0.02"),
                "position_percentage": Decimal("2.0"),
                "recommendation": "FALLBACK_2PCT",
                "fallback_reason": "Insufficient backtest data",
            }

            if capital is not None:
                fallback_result["position_value"] = capital * Decimal("0.02")

            return fallback_result

        # Calculate Kelly using the extracted metrics
        return self.calculate_kelly_position_size(
            win_rate=win_rate_decimal,
            avg_win=Decimal(str(avg_win)),
            avg_loss=Decimal(str(abs(avg_loss))),  # Use absolute value
            capital=capital,
        )


# ============================================================================
# META-LABELING POSITION SIZING (López de Prado Chapter 3 & 10)
# ============================================================================


class MetaLabelingPositionSizer:
    """
    Use meta-labeling probabilities for position sizing.

    This class integrates López de Prado's meta-labeling framework (Chapter 3)
    with the position sizing engine, enabling ML-based bet sizing (Chapter 10).

    Key Concepts:
    - Primary Model: Predicts signal direction (buy/sell/hold)
    - Meta Model: Predicts whether primary model will be correct
    - Bet Sizing: Position size based on meta-model confidence

    The meta-labeling approach separates signal direction from position sizing:
    1. Primary model determines DIRECTION (when to buy/sell)
    2. Meta model determines SIZE (how much to bet)

    Example:
        >>> sizer = MetaLabelingPositionSizer()
        >>> position_sizes = sizer.calculate_position_size(
        ...     signals=np.array([1, -1, 1, 0]),
        ...     meta_proba=np.array([0.7, 0.6, 0.8, 0.4]),
        ...     expected_returns=np.array([0.02, -0.015, 0.025, 0.0])
        ... )
        >>> print(f"Position sizes: {position_sizes}")
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize meta-labeling position sizer.

        Args:
            config: Optional configuration dictionary with keys:
                - bet_sizing_method: 'meta_kelly', 'meta_probability', 'meta_expected_value'
                - confidence_threshold: Minimum confidence to take trade (default: 0.5)
                - max_bet_size: Maximum position size (default: 1.0)
                - min_bet_size: Minimum position size (default: 0.0)
        """
        self.config = config or {}

        # Lazy import to avoid circular dependencies
        try:
            from app.backtesting.labeling.bet_sizing import BetSizing
            from app.backtesting.labeling.meta_labeling import MetaLabeling

            self.meta_labeler = MetaLabeling()
            self.bet_sizing = BetSizing()
            self._has_ml_modules = True
        except ImportError as e:
            logger.warning(f"ML modules not available: {e}")
            self._has_ml_modules = False

        # Configuration with defaults
        self.bet_sizing_method = self.config.get("bet_sizing_method", "meta_kelly")
        self.confidence_threshold = self.config.get("confidence_threshold", 0.5)
        self.max_bet_size = self.config.get("max_bet_size", 1.0)
        self.min_bet_size = self.config.get("min_bet_size", 0.0)

    def calculate_position_size(
        self,
        signals: np.ndarray,
        meta_proba: np.ndarray,
        expected_returns: Optional[np.ndarray] = None,
        capital: Optional[Union[Decimal, float]] = None,
    ) -> np.ndarray:
        """
        Calculate position size using meta-labeling probabilities.

        Uses the meta-model's confidence to size positions according to
        López de Prado's methodology:

        - High meta-model confidence → larger position
        - Low meta-model confidence → smaller position or no trade
        - Kelly criterion adaptation for optimal sizing

        Args:
            signals: Primary model predictions (-1, 0, 1)
            meta_proba: Meta-model probabilities (confidence in primary prediction)
            expected_returns: Optional expected returns for each prediction
            capital: Optional total capital for position value calculation

        Returns:
            Position sizes array (as fractions of capital)

        Raises:
            ValueError: If signals and meta_proba have different lengths

        Example:
            >>> sizer = MetaLabelingPositionSizer()
            >>> position_sizes = sizer.calculate_position_size(
            ...     signals=np.array([1, -1, 1, 0]),
            ...     meta_proba=np.array([0.7, 0.6, 0.8, 0.4]),
            ...     expected_returns=np.array([0.02, -0.015, 0.025, 0.0]),
            ...     capital=Decimal("10000")
            ... )
            >>> print(f"Position sizes: {position_sizes}")
        """
        # Validate inputs
        if len(signals) != len(meta_proba):
            raise ValueError(
                f"signals and meta_proba must have same length: "
                f"{len(signals)} != {len(meta_proba)}"
            )

        if expected_returns is not None and len(expected_returns) != len(signals):
            raise ValueError(
                f"signals and expected_returns must have same length: "
                f"{len(signals)} != {len(expected_returns)}"
            )

        if not self._has_ml_modules:
            logger.warning("ML modules not available, using fallback sizing")
            return self._fallback_sizing(signals, meta_proba)

        # Import bet sizing function
        from app.backtesting.labeling.bet_sizing import calculate_bet_sizes_ml

        # Calculate bet sizes using ML-based approach
        bet_sizes = calculate_bet_sizes_ml(
            meta_proba=meta_proba,
            primary_predictions=signals,
            expected_returns=expected_returns,
            method=self.bet_sizing_method,
            confidence_threshold=self.confidence_threshold,
            max_bet_size=self.max_bet_size,
            min_bet_size=self.min_bet_size,
        )

        # Apply signal direction to bet sizes
        # Positive signals → positive position, negative signals → negative position
        position_sizes = bet_sizes * np.sign(signals)

        # Log summary statistics
        n_trades = (position_sizes != 0).sum()
        avg_size = np.abs(position_sizes[position_sizes != 0]).mean() if n_trades > 0 else 0
        total_exposure = np.abs(position_sizes).sum()

        logger.info(
            f"Meta-labeling position sizing: {n_trades} trades, "
            f"avg size: {avg_size:.2%}, total exposure: {total_exposure:.2%}"
        )

        return position_sizes

    def calculate_position_size_with_meta_model(
        self,
        X: np.ndarray,
        primary_predictions: np.ndarray,
        meta_model=None,
        expected_returns: Optional[np.ndarray] = None,
        capital: Optional[Union[Decimal, float]] = None,
    ) -> np.ndarray:
        """
        Calculate position sizes using a trained meta-model.

        This is the complete end-to-end function that:
        1. Gets meta-model probabilities for new data
        2. Converts probabilities to position sizes
        3. Applies risk management constraints

        Args:
            X: Feature matrix for meta-model prediction
            primary_predictions: Primary model predictions (-1, 0, 1)
            meta_model: Trained meta-model (must have predict_proba method)
            expected_returns: Optional expected returns
            capital: Optional total capital

        Returns:
            Position sizes array

        Example:
            >>> sizer = MetaLabelingPositionSizer()
            >>> position_sizes = sizer.calculate_position_size_with_meta_model(
            ...     X=X_test,
            ...     primary_predictions=primary_preds,
            ...     meta_model=trained_meta_model
            ... )
        """
        if meta_model is None:
            logger.warning("No meta-model provided, using fallback")
            return self._fallback_sizing(
                primary_predictions, np.ones(len(primary_predictions)) * 0.5
            )

        if not self._has_ml_modules:
            return self._fallback_sizing(
                primary_predictions, np.ones(len(primary_predictions)) * 0.5
            )

        # Import bet sizing function
        from app.backtesting.labeling.bet_sizing import calculate_bet_sizes_with_meta_model

        # Calculate bet sizes using meta-model
        bet_sizes = calculate_bet_sizes_with_meta_model(
            meta_model=meta_model,
            X=X,
            primary_predictions=primary_predictions,
            expected_returns=expected_returns,
            method=self.bet_sizing_method,
            confidence_threshold=self.confidence_threshold,
        )

        # Apply signal direction
        position_sizes = bet_sizes * np.sign(primary_predictions)

        return position_sizes

    def fit_meta_model(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: Optional[np.ndarray] = None,
        y_test: Optional[np.ndarray] = None,
    ) -> Dict:
        """
        Fit meta-labeling model on training data.

        This trains both the primary and meta models according to
        López de Prado's meta-labeling framework.

        Args:
            X_train: Training features
            y_train: Training labels (original trading signals)
            X_test: Optional test features for evaluation
            y_test: Optional test labels

        Returns:
            Dictionary with training results:
                - meta_model: Fitted meta-model
                - meta_proba: Meta-model probabilities for test set
                - bet_sizes: Recommended bet sizes
                - metrics: Performance metrics

        Example:
            >>> sizer = MetaLabelingPositionSizer()
            >>> result = sizer.fit_meta_model(X_train, y_train, X_test, y_test)
            >>> print(f"Meta-model accuracy: {result['metrics']['meta_accuracy']}")
        """
        if not self._has_ml_modules:
            raise RuntimeError("ML modules not available for meta-model training")

        from app.backtesting.labeling.meta_labeling import apply_meta_labeling

        # Fit meta-labeling model
        result = apply_meta_labeling(
            X_train=X_train,
            y_train=y_train,
            X_test=X_test if X_test is not None else X_train,
            y_test=y_test,
        )

        logger.info(
            f"Meta-model trained: primary accuracy={result.primary_accuracy:.4f}, "
            f"meta accuracy={result.meta_accuracy:.4f}, "
            f"combined accuracy={result.combined_accuracy:.4f}"
        )

        return {
            "meta_model": self.meta_labeler.meta_model,
            "meta_proba": result.meta_proba,
            "bet_sizes": result.bet_sizes,
            "metrics": {
                "primary_accuracy": result.primary_accuracy,
                "meta_accuracy": result.meta_accuracy,
                "combined_accuracy": result.combined_accuracy,
            },
        }

    def _fallback_sizing(self, signals: np.ndarray, meta_proba: np.ndarray) -> np.ndarray:
        """
        Fallback sizing when ML modules are not available.

        Uses simple confidence-based sizing.

        Args:
            signals: Trading signals
            meta_proba: Meta-model probabilities

        Returns:
            Position sizes
        """
        position_sizes = np.zeros(len(signals))

        for i, (signal, prob) in enumerate(zip(signals, meta_proba)):
            if signal == 0 or prob < self.confidence_threshold:
                position_sizes[i] = 0.0
            else:
                # Simple linear scaling
                size = (prob - self.confidence_threshold) / (1.0 - self.confidence_threshold)
                position_sizes[i] = np.sign(signal) * size

        return np.clip(position_sizes, self.min_bet_size, self.max_bet_size)


class PositionSizingEngineWithMetaLabeling(PositionSizingEngine):
    """
    Extended position sizing engine with meta-labeling support.

    This class combines the traditional position sizing methods (ATR, Kelly)
    with López de Prado's meta-labeling framework for ML-based position sizing.

    Features:
    - Traditional position sizing (ATR-based, Kelly criterion)
    - Meta-labeling position sizing (ML-based)
    - Hybrid approach (meta-labeling with Kelly adjustment)
    - Automatic fallback when ML modules unavailable

    Example:
        >>> engine = PositionSizingEngineWithMetaLabeling()
        >>> # Use meta-labeling for position sizing
        >>> sizes = engine.calculate_meta_labeling_sizes(
        ...     signals=np.array([1, -1, 1]),
        ...     meta_proba=np.array([0.7, 0.6, 0.8])
        ... )
        >>> # Or use traditional sizing
        >>> kelly_result = engine.calculate_kelly_position_size(
        ...     win_rate=0.55,
        ...     avg_win=100.0,
        ...     avg_loss=75.0,
        ...     capital=Decimal("10000")
        ... )
    """

    def __init__(self, atr_multiplier: Optional[float] = None):
        """Initialize extended position sizing engine."""
        super().__init__(atr_multiplier)
        self.meta_sizer = MetaLabelingPositionSizer()

    def calculate_meta_labeling_sizes(
        self,
        signals: np.ndarray,
        meta_proba: np.ndarray,
        expected_returns: Optional[np.ndarray] = None,
        capital: Optional[Union[Decimal, float]] = None,
    ) -> np.ndarray:
        """
        Calculate position sizes using meta-labeling.

        Args:
            signals: Primary model predictions
            meta_proba: Meta-model probabilities
            expected_returns: Optional expected returns
            capital: Optional total capital

        Returns:
            Position sizes as fractions of capital

        Example:
            >>> engine = PositionSizingEngineWithMetaLabeling()
            >>> sizes = engine.calculate_meta_labeling_sizes(
            ...     signals=np.array([1, -1, 1]),
            ...     meta_proba=np.array([0.7, 0.6, 0.8]),
            ...     capital=Decimal("10000")
            ... )
        """
        return self.meta_sizer.calculate_position_size(
            signals=signals,
            meta_proba=meta_proba,
            expected_returns=expected_returns,
            capital=capital,
        )

    def calculate_hybrid_sizes(
        self,
        signals: np.ndarray,
        meta_proba: np.ndarray,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        capital: Union[Decimal, float],
        expected_returns: Optional[np.ndarray] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Calculate position sizes using hybrid meta-labeling + Kelly approach.

        This combines:
        1. Meta-labeling for filtering (only trade when meta-model confident)
        2. Kelly criterion for sizing (optimal position size)

        Args:
            signals: Primary model predictions
            meta_proba: Meta-model probabilities
            win_rate: Historical win rate for Kelly calculation
            avg_win: Average win for Kelly calculation
            avg_loss: Average loss for Kelly calculation
            capital: Total capital
            expected_returns: Optional expected returns

        Returns:
            Dictionary with:
                - position_sizes: Final position sizes
                - meta_sizes: Meta-labeling based sizes
                - kelly_fraction: Kelly fraction applied
                - filter_mask: Which signals passed meta-model filter

        Example:
            >>> engine = PositionSizingEngineWithMetaLabeling()
            >>> result = engine.calculate_hybrid_sizes(
            ...     signals=np.array([1, -1, 1]),
            ...     meta_proba=np.array([0.7, 0.6, 0.8]),
            ...     win_rate=0.55,
            ...     avg_win=100.0,
            ...     avg_loss=75.0,
            ...     capital=Decimal("10000")
            ... )
            >>> print(f"Position sizes: {result['position_sizes']}")
        """
        # Calculate Kelly fraction
        kelly_result = self.calculate_kelly_position_size(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            capital=Decimal(str(capital)) if isinstance(capital, float) else capital,
        )

        kelly_fraction = float(kelly_result["half_kelly_fraction"])

        # Get meta-labeling sizes
        meta_sizes = self.meta_sizer.calculate_position_size(
            signals=signals,
            meta_proba=meta_proba,
            expected_returns=expected_returns,
        )

        # Apply Kelly fraction as a cap on meta-labeling sizes
        # Meta-labeling provides the base size, Kelly provides the cap
        filter_mask = meta_proba >= self.meta_sizer.confidence_threshold
        position_sizes = np.zeros(len(signals))

        for i in range(len(signals)):
            if filter_mask[i] and signals[i] != 0:
                # Use meta-labeling size but cap at Kelly fraction
                base_size = abs(meta_sizes[i])
                capped_size = min(base_size, kelly_fraction)
                position_sizes[i] = np.sign(signals[i]) * capped_size

        return {
            "position_sizes": position_sizes,
            "meta_sizes": meta_sizes,
            "kelly_fraction": kelly_fraction,
            "filter_mask": filter_mask,
        }
