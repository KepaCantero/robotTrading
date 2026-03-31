from __future__ import annotations

"""Quote Generator for Avellaneda-Stoikov Market Making.

This module provides the quote generator that combines the AS model with
practical constraints like inventory limits, spread limits, and quote enabling/disabling.
"""


import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from app.domain.trading.market_making.avellaneda_stoikov.as_model import AvellanedaStoikovModel

if TYPE_CHECKING:
    from app.domain.trading.market_making.avellaneda_stoikov.models import (
        ASConfig,
        ASQuote,
        ASQuoteParams,
    )

logger = logging.getLogger(__name__)


class ASQuoteGenerator:
    """
    Generate market making quotes using Avellaneda-Stoikov model.

    This generator wraps the core AS model and adds practical constraints:
    - Spread limits (min/max)
    - Inventory limits (disable quotes when at max position)
    - Price sanity checks
    - Volatility estimation

    Example:
        >>> config = ASConfig()
        >>> generator = ASQuoteGenerator(config)
        >>> quote = generator.generate_quotes(
        ...     symbol="BTC-USD",
        ...     mid_price=Decimal("50000.0"),
        ...     inventory=10,
        ... )
    """

    def __init__(
        self,
        config: ASConfig,
    ) -> None:
        """
        Initialize the quote generator.

        Args:
            config: AS model configuration.
        """
        self.config = config
        self.as_model = AvellanedaStoikovModel(config)

        logger.info(
            f"Initialized ASQuoteGenerator: gamma={config.gamma}, "
            f"sigma={config.sigma}, k={config.k}, T={config.T}, "
            f"max_inventory={config.max_inventory}"
        )

    def generate_quotes(
        self,
        symbol: str,
        mid_price: float | Decimal | str,
        inventory: int,
        current_timestamp,
        volatility_override: float | Decimal | str | None = None,
        time_remaining: float | Decimal | str | None = None,
    ) -> ASQuote:
        """
        Generate real-time market making quotes.

        Process:
        1. Validate inputs
        2. Update volatility if override provided
        3. Calculate time remaining if not provided
        4. Generate base quotes using AS model
        5. Apply inventory limits
        6. Apply spread limits
        7. Return final quotes

        Args:
            symbol: Trading symbol.
            mid_price: Current mid price.
            inventory: Current inventory position.
            current_timestamp: Current time for quote generation.
            volatility_override: Optional volatility override for this quote.
            time_remaining: Optional time remaining (defaults to T from config).

        Returns:
            Complete quote with bid, ask, and metadata.

        Raises:
            ValueError: If inputs are invalid.

        Examples:
            >>> from datetime import datetime
            >>> config = ASConfig()
            >>> gen = ASQuoteGenerator(config)
            >>> quote = gen.generate_quotes(
            ...     symbol="AAPL",
            ...     mid_price=Decimal("150.0"),
            ...     inventory=5,
            ...     current_timestamp=datetime.now(),
            ... )
            >>> quote.optimal_bid < quote.optimal_ask
            True
        """
        # Validate and convert inputs
        mid = Decimal(str(mid_price))
        if mid <= 0:
            raise ValueError(f"Mid price must be positive, got {mid}")

        # Handle volatility override
        if volatility_override is not None:
            vol_override = Decimal(str(volatility_override))
            if vol_override <= 0:
                raise ValueError(f"Volatility override must be positive, got {vol_override}")
            self.as_model.update_volatility(vol_override)

        # Calculate time remaining
        if time_remaining is None:
            t_rem = self.config.T
        else:
            t_rem = Decimal(str(time_remaining))
            if t_rem < 0:
                raise ValueError(f"Time remaining must be non-negative, got {t_rem}")
            if t_rem > self.config.T:
                logger.warning(
                    f"Time remaining ({t_rem}) exceeds horizon ({self.config.T}), "
                    "using horizon instead"
                )
                t_rem = self.config.T

        # Generate base quotes
        quote = self.as_model.calculate_quotes(mid, inventory, t_rem)
        quote.symbol = symbol
        quote.timestamp = current_timestamp

        # Apply constraints
        quote = self._apply_inventory_limits(quote, inventory)
        quote = self._apply_spread_limits(quote)
        quote = self._apply_price_sanity_checks(quote)

        logger.debug(
            f"Generated quote for {symbol}: mid={mid:.4f}, "
            f"bid={quote.optimal_bid:.4f}, ask={quote.optimal_ask:.4f}, "
            f"spread_bps={quote.optimal_spread_bps:.2f}, "
            f"inventory={inventory}"
        )

        return quote

    def _apply_inventory_limits(
        self,
        quote: ASQuote,
        current_inventory: int,
    ) -> ASQuote:
        """
        Apply inventory limits to quotes.

        Rules:
        - If at max long (inventory >= max_inventory): disable or widen bid
        - If at max short (inventory <= min_inventory): disable or widen ask
        - Adjust spread to encourage closing positions

        Args:
            quote: Base quote from AS model.
            current_inventory: Current inventory position.

        Returns:
            Quote with inventory limits applied.
        """
        max_inv = self.config.max_inventory
        min_inv = -self.config.max_inventory  # Symmetric limits

        # Check if at limits
        is_max_long = current_inventory >= max_inv
        is_max_short = current_inventory <= min_inv

        # Disable or widen quotes at limits
        if is_max_long:
            # At max long: discourage buying more
            quote.is_bid_enabled = False
            # Widen ask to encourage selling
            quote.optimal_ask = quote.reservation_price
            logger.debug(f"At max long inventory ({current_inventory}), disabled bid quote")

        if is_max_short:
            # At max short: discourage selling more
            quote.is_ask_enabled = False
            # Widen bid to encourage buying
            quote.optimal_bid = quote.reservation_price
            logger.debug(f"At max short inventory ({current_inventory}), disabled ask quote")

        # Near limits: adjust quotes to encourage closing
        inventory_utilization = abs(current_inventory) / max_inv if max_inv > 0 else 0

        if inventory_utilization > 0.8:
            # Near limit: skew quotes to close position
            skew_factor = Decimal(str(0.5 * (inventory_utilization - 0.8) / 0.2))
            spread_adjustment = (
                skew_factor * quote.optimal_spread_bps / Decimal("10000") * quote.mid_price
            )

            if current_inventory > 0:
                # Long: lower bid, lower ask (encourage selling)
                quote.optimal_bid -= spread_adjustment
                quote.optimal_ask -= spread_adjustment
            else:
                # Short: raise bid, raise ask (encourage buying)
                quote.optimal_bid += spread_adjustment
                quote.optimal_ask += spread_adjustment

        return quote

    def _apply_spread_limits(self, quote: ASQuote) -> ASQuote:
        """
        Apply minimum and maximum spread limits.

        Ensures:
        - Spread is at least min_spread_bps (profitability)
        - Spread is at most max_spread_bps (competitiveness)

        Args:
            quote: Base quote from AS model.

        Returns:
            Quote with spread limits applied.
        """
        current_spread_bps = quote.optimal_spread_bps
        min_spread = self.config.min_spread_bps
        max_spread = self.config.max_spread_bps

        # Check minimum spread
        if current_spread_bps < min_spread:
            # Widen spread to minimum
            spread_adjustment = min_spread - current_spread_bps
            half_adjustment = spread_adjustment / Decimal("2")

            quote.optimal_bid -= half_adjustment / 10000 * quote.mid_price
            quote.optimal_ask += half_adjustment / 10000 * quote.mid_price
            quote.optimal_spread_bps = min_spread
            quote.spread_adjustment += spread_adjustment

            logger.debug(
                f"Spread ({current_spread_bps:.2f} bps) below minimum ({min_spread:.2f} bps), "
                "widened to minimum"
            )

        # Check maximum spread
        elif current_spread_bps > max_spread:
            # Tighten spread to maximum by moving bid/ask toward midpoint
            midpoint = (quote.optimal_bid + quote.optimal_ask) / Decimal("2")
            target_half_spread_price = (
                max_spread / Decimal("10000") * quote.mid_price / Decimal("2")
            )

            quote.optimal_bid = midpoint - target_half_spread_price
            quote.optimal_ask = midpoint + target_half_spread_price
            quote.optimal_spread_bps = max_spread
            quote.spread_adjustment -= current_spread_bps - max_spread

            logger.debug(
                f"Spread ({float(current_spread_bps):.2f} bps) exceeds maximum ({float(max_spread):.2f} bps), "
                "tightened to maximum"
            )

        return quote

    def _apply_price_sanity_checks(self, quote: ASQuote) -> ASQuote:
        """
        Apply sanity checks to generated prices.

        Ensures:
        - Bid is positive
        - Ask is positive
        - Ask > bid (valid spread)
        - Prices are within reasonable bounds

        Args:
            quote: Quote to validate.

        Returns:
            Sanitized quote.

        Raises:
            ValueError: If quotes are fundamentally invalid.
        """
        # Ensure positive prices
        if quote.optimal_bid <= 0:
            logger.warning(f"Generated non-positive bid {quote.optimal_bid}, setting to minimum")
            quote.optimal_bid = Decimal("0.0001")

        if quote.optimal_ask <= 0:
            logger.warning(f"Generated non-positive ask {quote.optimal_ask}, setting to minimum")
            quote.optimal_ask = Decimal("0.0001")

        # Ensure valid spread
        if quote.optimal_ask <= quote.optimal_bid:
            logger.warning(
                f"Generated invalid spread (ask={quote.optimal_ask} <= bid={quote.optimal_bid}), "
                "adjusting"
            )
            # Set minimum spread
            midpoint = (quote.optimal_bid + quote.optimal_ask) / 2
            min_spread_price = self.config.min_spread_bps / 10000 * midpoint
            quote.optimal_bid = midpoint - min_spread_price / 2
            quote.optimal_ask = midpoint + min_spread_price / 2

        # Ensure prices aren't too far from mid price (sanity check)
        max_deviation = Decimal("0.5")  # 50% maximum deviation
        if quote.optimal_bid > quote.mid_price * (1 + max_deviation):
            logger.warning("Bid price too far above mid, adjusting")
            quote.optimal_bid = quote.mid_price * (1 - self.config.min_spread_bps / 10000)

        if quote.optimal_ask < quote.mid_price * (1 - max_deviation):
            logger.warning("Ask price too far below mid, adjusting")
            quote.optimal_ask = quote.mid_price * (1 + self.config.min_spread_bps / 10000)

        return quote

    def generate_quotes_batch(
        self,
        quotes_params: list[ASQuoteParams],
    ) -> list[ASQuote]:
        """
        Generate multiple quotes efficiently.

        Args:
            quotes_params: List of quote parameters.

        Returns:
            List of generated quotes.
        """
        quotes = []
        for params in quotes_params:
            quote = self.generate_quotes(
                symbol=params.symbol,
                mid_price=params.mid_price,
                inventory=params.inventory,
                current_timestamp=params.current_timestamp,
                volatility_override=params.volatility_override,
                time_remaining=params.time_remaining,
            )
            quotes.append(quote)
        return quotes

    def update_config(self, new_config: ASConfig) -> None:
        """
        Update the generator configuration.

        Args:
            new_config: New configuration to use.
        """
        self.config = new_config
        self.as_model = AvellanedaStoikovModel(new_config)
        logger.info("Updated ASQuoteGenerator configuration")
