"""Inventory Manager for Avellaneda-Stoikov Market Making.

This module manages inventory risk and provides controls for position management
in market making strategies.

Key Features:
- Calculate inventory risk metrics
- Determine when to reduce positions
- Calculate dynamic target inventory
- Adjust quotes to manage inventory
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.domain.trading.market_making.avellaneda_stoikov.as_model import calculate_inventory_risk
from app.domain.trading.market_making.avellaneda_stoikov.models import (
    ASConfig,
    ASQuote,
    InventoryConfig,
    InventoryState,
)
from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


@dataclass
class InventoryThresholds:
    """Threshold levels for inventory management."""

    safe_level: float = 0.5  # Below 50% utilization
    warning_level: float = 0.7  # 70% utilization - start reducing
    critical_level: float = 0.9  # 90% utilization - force reduction


class InventoryManager:
    """
    Manage inventory for market making strategies.

    The inventory manager controls position risk by:
    1. Monitoring inventory levels and risk metrics
    2. Determining when to reduce positions
    3. Calculating dynamic target inventory
    4. Adjusting quotes to encourage closing positions

    Example:
        >>> config = InventoryConfig(max_inventory=100)
        >>> manager = InventoryManager(config)
        >>> state = manager.get_inventory_state(
        ...     symbol="BTC-USD",
        ...     inventory=50,
        ...     price=50000.0,
        ...     volatility=0.3,
        ... )
        >>> manager.should_reduce_inventory(state)
        False
    """

    def __init__(
        self,
        config: InventoryConfig,
        as_config: Optional[ASConfig] = None,
    ) -> None:
        """
        Initialize the inventory manager.

        Args:
            config: Inventory management configuration.
            as_config: Optional AS config for volatility parameter.
        """
        self.config = config
        self.as_config = as_config
        self.thresholds = InventoryThresholds(
            warning_level=config.warning_threshold,
            critical_level=config.liquidation_threshold,
        )

        logger.info(
            f"Initialized InventoryManager: max={config.max_inventory}, "
            f"min={config.min_inventory}, target={config.target_inventory}, "
            f"warning={config.warning_threshold}, liquidation={config.liquidation_threshold}"
        )

    def get_inventory_state(
        self,
        symbol: str,
        inventory: int,
        price: float | Decimal,
        volatility: float | Decimal,
        current_timestamp: Optional[datetime] = None,
    ) -> InventoryState:
        """
        Get current inventory state with risk metrics.

        Args:
            symbol: Trading symbol.
            inventory: Current inventory position.
            price: Current price.
            volatility: Current volatility (annualized).
            current_timestamp: Current timestamp.

        Returns:
            Current inventory state.
        """
        if current_timestamp is None:
            current_timestamp = datetime.now()

        # Calculate inventory value
        inv_value = Decimal(str(price)) * Decimal(str(inventory))

        # Calculate inventory risk
        time_horizon_years = float(self.as_config.T) / 31536000 if self.as_config else 0.003169
        inv_risk = calculate_inventory_risk(
            inventory=inventory,
            price=float(price),
            volatility=float(volatility),
            time_horizon=time_horizon_years,
            risk_multiplier=self.config.risk_multiplier,
        )

        # Calculate liquidation horizon (time to flatten at current rate)
        liquidation_horizon = self._calculate_liquidation_horizon(inventory)

        # Check threshold levels
        utilization = self._calculate_inventory_utilization(inventory)
        is_warning = utilization >= self.thresholds.warning_level
        is_liquidation = utilization >= self.thresholds.critical_level

        return InventoryState(
            symbol=symbol,
            current_inventory=inventory,
            target_inventory=self.config.target_inventory,
            inventory_value=inv_value,
            inventory_risk=Decimal(str(inv_risk)),
            liquidation_horizon=Decimal(str(liquidation_horizon)),
            max_inventory=self.config.max_inventory,
            min_inventory=self.config.min_inventory,
            is_at_warning_level=is_warning,
            is_at_liquidation_level=is_liquidation,
            timestamp=current_timestamp,
        )

    def should_reduce_inventory(
        self,
        state: InventoryState,
    ) -> bool:
        """
        Check if inventory should be reduced.

        Reduction is triggered when:
        1. At or above warning threshold
        2. At or above liquidation threshold
        3. Inventory risk is too high

        Args:
            state: Current inventory state.

        Returns:
            True if inventory should be reduced.
        """
        # Check liquidation threshold first (highest priority)
        if state.is_at_liquidation_level:
            logger.warning(
                f"Inventory at liquidation level for {state.symbol}: "
                f"{state.current_inventory}/{state.max_inventory}"
            )
            return True

        # Check warning threshold
        if state.is_at_warning_level:
            logger.info(
                f"Inventory at warning level for {state.symbol}: "
                f"{state.current_inventory}/{state.max_inventory}"
            )
            return True

        return False

    def calculate_target_inventory(
        self,
        current_inventory: int,
        time_remaining: float | Decimal,
        total_horizon: float | Decimal,
    ) -> int:
        """
        Calculate dynamic target inventory.

        The target gradually moves toward the desired target (usually 0)
        as time approaches the end of the trading window.

        Formula:
        q_target(t) = q_target_final + (q_current - q_target_final) * (T - t) / T

        This creates a gradual liquidation path.

        Args:
            current_inventory: Current inventory position.
            time_remaining: Time remaining in trading window.
            total_horizon: Total time horizon.

        Returns:
            Target inventory level.

        Examples:
            >>> manager = InventoryManager(InventoryConfig(target_inventory=0))
            >>> # At start: maintain current inventory
            >>> manager.calculate_target_inventory(100, 3600, 3600)
            100
            >>> # Halfway: reduce toward target
            >>> manager.calculate_target_inventory(100, 1800, 3600)
            50
            >>> # Near end: close to target
            >>> manager.calculate_target_inventory(100, 300, 3600)
            8
        """
        t_rem = float(time_remaining)
        T = float(total_horizon)

        if T <= 0:
            return self.config.target_inventory

        # Calculate decay factor
        decay_factor = t_rem / T

        # Calculate target
        inventory_diff = current_inventory - self.config.target_inventory
        target = self.config.target_inventory + int(inventory_diff * decay_factor)

        # Round toward target
        if inventory_diff > 0:
            target = math.ceil(target)
        else:
            target = math.floor(target)

        return target

    def adjust_quotes_for_inventory(
        self,
        quote: ASQuote,
        inventory_state: InventoryState,
    ) -> ASQuote:
        """
        Adjust quotes to manage inventory.

        Adjustment logic:
        - If long inventory: lower bid (less aggressive buying), lower ask (more aggressive selling)
        - If short inventory: raise bid (more aggressive buying), raise ask (less aggressive selling)

        The adjustment is proportional to how far we are from target.

        Args:
            quote: Base quote from AS model.
            inventory_state: Current inventory state.

        Returns:
            Adjusted quote with inventory management.

        Examples:
            >>> manager = InventoryManager(InventoryConfig())
            >>> from decimal import Decimal
            >>> from datetime import datetime
            >>> quote = ASQuote(
            ...     symbol="BTC-USD",
            ...     timestamp=datetime.now(),
            ...     mid_price=Decimal("50000"),
            ...     reservation_price=Decimal("50000"),
            ...     optimal_bid=Decimal("49990"),
            ...     optimal_ask=Decimal("50010"),
            ...     optimal_spread_bps=Decimal("2"),
            ...     inventory=50,
            ...     inventory_skew=Decimal("0"),
            ...     time_to_expiry=Decimal("1800"),
            ... )
            >>> state = manager.get_inventory_state("BTC-USD", 50, 50000, 0.3)
            >>> adjusted = manager.adjust_quotes_for_inventory(quote, state)
            >>> adjusted.optimal_bid < quote.optimal_bid  # Lower bid when long
            True
        """
        inventory_diff = inventory_state.current_inventory - inventory_state.target_inventory

        if abs(inventory_diff) == 0:
            # At target: no adjustment needed
            return quote

        # Calculate adjustment magnitude based on distance from target
        max_inventory = max(
            abs(inventory_state.max_inventory),
            abs(inventory_state.min_inventory),
        )
        inventory_ratio = abs(inventory_diff) / max_inventory if max_inventory > 0 else 0

        # Base adjustment: proportional to inventory ratio and spread
        base_adjustment = (
            quote.optimal_spread_bps
            * Decimal(str(inventory_ratio))
            / Decimal("10000")
            * quote.mid_price
        )

        if inventory_diff > 0:
            # Long inventory: encourage selling
            # Lower ask (more aggressive) and lower/widen bid (less aggressive)
            ask_adjustment = base_adjustment * Decimal("0.5")  # More aggressive selling
            bid_adjustment = base_adjustment  # Less aggressive buying
            quote.optimal_ask -= ask_adjustment
            quote.optimal_bid -= bid_adjustment
            logger.debug(
                f"Adjusted quotes for long inventory ({inventory_diff}): "
                f"bid -={float(bid_adjustment):.4f}, ask -={float(ask_adjustment):.4f}"
            )
        else:
            # Short inventory: encourage buying
            # Raise bid (more aggressive) and raise/widen ask (less aggressive)
            bid_adjustment = base_adjustment * Decimal("0.5")  # More aggressive buying
            ask_adjustment = base_adjustment  # Less aggressive selling
            quote.optimal_bid += bid_adjustment
            quote.optimal_ask += ask_adjustment
            logger.debug(
                f"Adjusted quotes for short inventory ({inventory_diff}): "
                f"bid +={float(bid_adjustment):.4f}, ask +={float(ask_adjustment):.4f}"
            )

        # Ensure quotes remain valid
        if quote.optimal_bid <= 0:
            quote.optimal_bid = quote.mid_price * Decimal("0.999")
        if quote.optimal_ask <= 0:
            quote.optimal_ask = quote.mid_price * Decimal("1.001")

        return quote

    def _calculate_inventory_utilization(self, inventory: int) -> float:
        """Calculate inventory utilization ratio (0-1)."""
        max_abs = max(
            abs(self.config.max_inventory),
            abs(self.config.min_inventory),
        )
        if max_abs == 0:
            return 0.0
        return abs(inventory) / max_abs

    def _calculate_liquidation_horizon(
        self,
        inventory: int,
        default_horizon: float = 3600.0,
    ) -> float:
        """
        Estimate time to liquidate position at current rate.

        Args:
            inventory: Current inventory.
            default_horizon: Default horizon if no AS config.

        Returns:
            Estimated liquidation time in seconds.
        """
        if self.as_config is not None:
            return float(self.as_config.T)
        return default_horizon

    def get_inventory_action(
        self,
        state: InventoryState,
    ) -> str:
        """
        Get recommended action for inventory management.

        Args:
            state: Current inventory state.

        Returns:
            Action string: 'hold', 'reduce', 'liquidate', 'close'
        """
        if state.is_at_liquidation_level:
            return "liquidate"
        if state.is_at_warning_level:
            return "reduce"
        if abs(state.current_inventory - state.target_inventory) < 5:
            return "hold"
        return "close"

    def calculate_position_size(
        self,
        current_inventory: int,
        price: float | Decimal,
        volatility: float | Decimal,
        capital: float | Decimal,
    ) -> int:
        """
        Calculate recommended position size based on risk parameters.

        Uses Kelly criterion-inspired sizing with risk limits.

        Args:
            current_inventory: Current position.
            price: Current price.
            volatility: Current volatility.
            capital: Available capital.

        Returns:
            Recommended position size (can be negative for short).
        """
        # Base position size from capital
        config = get_config()
        risk_amount = getattr(config.trading, 'max_risk_per_trade', 0.02)  # 2% risk per trade
        price_f = float(price)
        vol_f = float(volatility)

        # Size based on volatility (higher vol = smaller size)
        base_size = int(risk_amount / (price_f * vol_f))

        # Limit by max inventory
        max_size = min(base_size, self.config.max_inventory)

        # If already positioned, limit additional size
        if current_inventory > 0:
            # Long: can only add up to max
            return max(0, self.config.max_inventory - current_inventory)
        elif current_inventory < 0:
            # Short: can only add up to min
            return min(0, self.config.min_inventory - current_inventory)
        else:
            return max_size
