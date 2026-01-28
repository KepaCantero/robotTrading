"""
Crypto Portfolio Constructor

This module provides portfolio construction functionality for cryptocurrency
momentum strategies, with specific considerations for crypto markets:

- Bitcoin as core holding (40-60%)
- Altcoins for alpha (40-60%)
- Position sizing based on liquidity
- Volatility targeting
- Risk management for extreme moves
"""

import logging
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional

import numpy as np

from .models import (
    CryptoAsset,
    CryptoAssetType,
    CryptoMomentumConfig,
    CryptoMomentumScore,
    CryptoPortfolio,
    CryptoPosition,
)

logger = logging.getLogger(__name__)


class CryptoPortfolioConstructor:
    """
    Construct crypto momentum portfolio.

    Crypto-specific considerations:
    - BTC as core holding (40-60%)
    - Altcoins for alpha (40-60%)
    - Position sizing based on liquidity
    - Volatility targeting
    - 24/7 trading means continuous monitoring
    - Higher volatility requires smaller positions
    """

    def __init__(self, config: CryptoMomentumConfig):
        """
        Initialize portfolio constructor.

        Args:
            config: Strategy configuration
        """
        self.config = config
        self.rebalance_history: List[Dict] = []

    def construct_portfolio(
        self,
        ranked_assets: List[CryptoAsset],
        momentum_scores: Dict[str, CryptoMomentumScore],
        total_capital: Decimal,
    ) -> CryptoPortfolio:
        """
        Construct crypto momentum portfolio.

        Allocation:
        - BTC: Fixed weight (usually 40-60%)
        - Top altcoins: Remaining weight by momentum score
        - Position cap: Max 10% per position

        Args:
            ranked_assets: List of assets ranked by momentum
            momentum_scores: Dict of momentum scores by symbol
            total_capital: Total capital to invest

        Returns:
            Constructed portfolio
        """
        logger.info(f"Constructing portfolio with ${total_capital:,.0f}")

        positions: List[CryptoPosition] = []

        # Separate BTC and altcoins
        btc_asset = None
        altcoins = []

        for asset in ranked_assets:
            if asset.asset_type == CryptoAssetType.BITCOIN and asset.symbol == "BTC":
                btc_asset = asset
            else:
                altcoins.append(asset)

        # Allocate BTC position
        btc_weight = self.config.btc_weight
        btc_value = total_capital * btc_weight

        if btc_asset:
            btc_position = self._create_position(
                asset=btc_asset,
                value=btc_value,
                target_weight=btc_weight,
                momentum_score=momentum_scores.get("BTC"),
            )
            positions.append(btc_position)
            logger.info(f"BTC position: {btc_weight:.1%} = ${btc_value:,.0f}")

        # Allocate altcoins
        if altcoins:
            altcoin_weight = Decimal("1") - btc_weight
            altcoin_value = total_capital * altcoin_weight

            # Select top altcoins by momentum score
            max_altcoins = min(len(altcoins), self.config.portfolio_size - (1 if btc_asset else 0))
            top_altcoins = altcoins[:max_altcoins]

            # Calculate weights by momentum score
            altcoin_weights = self._calculate_altcoin_weights(
                top_altcoins, momentum_scores, altcoin_weight
            )

            for i, asset in enumerate(top_altcoins):
                weight = altcoin_weights[i]
                value = (
                    altcoin_value * (weight / altcoin_weight)
                    if altcoin_weight > 0
                    else Decimal("0")
                )

                position = self._create_position(
                    asset=asset,
                    value=value,
                    target_weight=weight,
                    momentum_score=momentum_scores.get(asset.symbol),
                )
                positions.append(position)

                logger.info(f"{asset.symbol} position: {weight:.1%} = ${value:,.0f}")

        # Calculate portfolio metrics
        invested_value = sum(pos.value for pos in positions)
        cash = total_capital - invested_value

        portfolio = CryptoPortfolio(
            positions=positions,
            total_value=total_capital,
            cash=cash,
            btc_weight=btc_weight if btc_asset else Decimal("0"),
            altcoin_weight=Decimal("1") - btc_weight,
            last_rebalance=date.today(),
            rebalance_threshold=self.config.rebalance_threshold,
        )

        # Calculate expected volatility
        portfolio.expected_volatility = self._calculate_portfolio_volatility(portfolio)

        logger.info(
            f"Portfolio constructed: {len(positions)} positions, "
            f"${invested_value:,.0f} invested, ${cash:,.0f} cash"
        )

        return portfolio

    def _create_position(
        self,
        asset: CryptoAsset,
        value: Decimal,
        target_weight: Decimal,
        momentum_score: Optional[CryptoMomentumScore],
    ) -> CryptoPosition:
        """Create a portfolio position."""
        quantity = value / asset.current_price if asset.current_price > 0 else Decimal("0")

        position = CryptoPosition(
            symbol=asset.symbol,
            quantity=quantity,
            entry_price=asset.current_price,
            current_price=asset.current_price,
            value=value,
            weight=target_weight,
        )

        return position

    def _calculate_altcoin_weights(
        self,
        altcoins: List[CryptoAsset],
        momentum_scores: Dict[str, CryptoMomentumScore],
        total_weight: Decimal,
    ) -> List[Decimal]:
        """
        Calculate altcoin weights based on momentum scores.

        Uses a softmax-like function to convert scores to weights.

        Args:
            altcoins: List of altcoin assets
            momentum_scores: Momentum scores by symbol
            total_weight: Total weight to allocate

        Returns:
            List of weights for each altcoin
        """
        if not altcoins:
            return []

        # Get momentum scores
        scores = []
        for asset in altcoins:
            score = momentum_scores.get(asset.symbol)
            if score:
                scores.append(float(score.final_score))
            else:
                scores.append(50.0)  # Default score

        # Apply softmax to get weights
        exp_scores = [np.exp(s / 25) for s in scores]  # Temperature = 25
        total_exp = sum(exp_scores)

        raw_weights = [e / total_exp for e in exp_scores]

        # Apply position size limits
        max_weight = self.config.max_position_size
        adjusted_weights = []

        for raw_w in raw_weights:
            adjusted_w = min(Decimal(str(raw_w)), max_weight)
            adjusted_weights.append(adjusted_w)

        # Normalize to total_weight
        total_adjusted = sum(adjusted_weights)
        if total_adjusted > 0:
            final_weights = [(w / total_adjusted) * total_weight for w in adjusted_weights]
        else:
            final_weights = [total_weight / len(altcoins)] * len(altcoins)

        # Further adjust for liquidity
        final_weights = self._adjust_for_liquidity(altcoins, final_weights)

        return final_weights

    def _adjust_for_liquidity(
        self, assets: List[CryptoAsset], weights: List[Decimal]
    ) -> List[Decimal]:
        """
        Adjust weights based on liquidity.

        Lower liquidity = smaller position to reduce slippage risk.

        Args:
            assets: List of assets
            weights: Original weights

        Returns:
            Adjusted weights
        """
        adjusted = []

        for asset, weight in zip(assets, weights):
            # Liquidity adjustment factor
            liq_factor = asset.liquidity_score / Decimal("100")

            # Reduce weight for low liquidity assets
            # Minimum weight is 50% of original
            adjusted_weight = weight * max(Decimal("0.5"), liq_factor)

            adjusted.append(adjusted_weight)

        # Renormalize
        total = sum(adjusted)
        if total > 0:
            adjusted = [(w / total) * sum(weights) for w in adjusted]

        return adjusted

    def calculate_position_size(
        self,
        asset: CryptoAsset,
        score: float,
        total_capital: Decimal,
    ) -> Decimal:
        """
        Calculate position size for crypto asset.

        Considerations:
        - Momentum score (higher = larger position)
        - Liquidity (lower = smaller position)
        - Volatility (higher = smaller position)
        - Max position limit

        Args:
            asset: Crypto asset
            score: Momentum score (0-100)
            total_capital: Total available capital

        Returns:
            Position value in USD
        """
        # Base allocation based on score
        base_allocation = Decimal(str(score / 100)) * self.config.max_position_size

        # Adjust for liquidity
        liq_adjustment = asset.liquidity_score / Decimal("100")
        adjusted_allocation = base_allocation * liq_adjustment

        # Adjust for volatility (higher vol = smaller position)
        vol_adjustment = max(
            Decimal("0.5"),
            min(Decimal("1.0"), Decimal("100") / asset.volatility_90d),
        )
        final_allocation = adjusted_allocation * vol_adjustment

        # Apply max position limit
        final_allocation = min(final_allocation, self.config.max_position_size)

        position_value = total_capital * final_allocation

        logger.debug(
            f"Position size for {asset.symbol}: "
            f"${position_value:,.0f} ({float(final_allocation):.1%})"
        )

        return position_value

    def rebalance_portfolio(
        self,
        current_portfolio: CryptoPortfolio,
        target_portfolio: CryptoPortfolio,
    ) -> Dict[str, Decimal]:
        """
        Calculate rebalance trades.

        Only trade if deviation > threshold (5% default).
        Minimizes trading fees in crypto.

        Args:
            current_portfolio: Current portfolio state
            target_portfolio: Target portfolio state

        Returns:
            Dict of trades by symbol (positive = buy, negative = sell)
        """
        threshold = self.config.rebalance_threshold
        trades: Dict[str, Decimal] = {}

        # Create current position map
        current_positions = {pos.symbol: pos for pos in current_portfolio.positions}

        # Calculate target weights
        target_weights = {}
        for pos in target_portfolio.positions:
            target_weights[pos.symbol] = pos.weight

        # Find trades needed
        all_symbols = set(current_positions.keys()) | set(target_weights.keys())

        for symbol in all_symbols:
            current_pos = current_positions.get(symbol)
            target_weight = target_weights.get(symbol, Decimal("0"))

            if current_pos is None:
                # New position
                target_value = target_portfolio.total_value * target_weight
                trades[symbol] = target_value
            elif target_weight == Decimal("0"):
                # Close position
                trades[symbol] = -current_pos.quantity
            else:
                # Check if rebalance needed
                weight_diff = abs(current_pos.weight - target_weight)

                if weight_diff > threshold:
                    # Calculate target quantity
                    target_value = target_portfolio.total_value * target_weight
                    target_quantity = target_value / current_pos.current_price

                    # Trade needed
                    trade_qty = target_quantity - current_pos.quantity
                    trades[symbol] = trade_qty

        # Record rebalance
        rebalance_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "trades": len(trades),
            "estimated_value": sum(abs(v) for v in trades.values()),
        }
        self.rebalance_history.append(rebalance_record)

        logger.info(
            f"Rebalance calculated: {len(trades)} trades, "
            f"est. value ${sum(abs(v) for v in trades.values()):,.0f}"
        )

        return trades

    def _calculate_portfolio_volatility(self, portfolio: CryptoPortfolio) -> Decimal:
        """
        Calculate expected portfolio volatility.

        Uses simplified covariance estimation based on:
        - Individual asset volatilities
        - BTC correlation (most assets correlate with BTC)

        Args:
            portfolio: Portfolio to analyze

        Returns:
            Expected annual volatility
        """
        if not portfolio.positions:
            return Decimal("0")

        # For simplicity, assume:
        # - BTC vol = 60%
        # - Avg altcoin vol = 100%
        # - Correlation matrix (simplified)

        btc_pos = portfolio.btc_position
        btc_vol = Decimal("60")  # 60% annual vol for BTC
        btc_weight = portfolio.btc_weight

        avg_altcoin_vol = Decimal("100")  # 100% annual vol for altcoins
        altcoin_weight = portfolio.altcoin_weight

        # Simplified portfolio vol (assuming 0.7 correlation)
        correlation = Decimal("0.7")

        portfolio_var = (
            (btc_weight**2) * (btc_vol**2)
            + (altcoin_weight**2) * (avg_altcoin_vol**2)
            + 2 * btc_weight * altcoin_weight * btc_vol * avg_altcoin_vol * correlation
        )

        portfolio_vol = Decimal(str(np.sqrt(float(portfolio_var)))).quantize(Decimal("0.01"))

        logger.debug(f"Expected portfolio volatility: {portfolio_vol:.1f}%")

        return portfolio_vol

    def get_portfolio_summary(self, portfolio: CryptoPortfolio) -> Dict:
        """
        Get portfolio summary statistics.

        Args:
            portfolio: Portfolio to summarize

        Returns:
            Summary statistics
        """
        if not portfolio.positions:
            return {
                "total_positions": 0,
                "invested_value": 0,
                "cash": float(portfolio.cash),
                "btc_weight": 0,
                "altcoin_weight": 0,
            }

        total_pnl = sum(pos.unrealized_pnl for pos in portfolio.positions)
        total_pnl_pct = (
            sum(pos.unrealized_pnl_pct * pos.weight for pos in portfolio.positions)
            if portfolio.positions
            else 0
        )

        return {
            "total_positions": len(portfolio.positions),
            "invested_value": float(portfolio.invested_value),
            "cash": float(portfolio.cash),
            "btc_weight": float(portfolio.btc_weight),
            "altcoin_weight": float(portfolio.altcoin_weight),
            "unrealized_pnl": float(total_pnl),
            "unrealized_pnl_pct": float(total_pnl_pct),
            "expected_volatility": (
                float(portfolio.expected_volatility) if portfolio.expected_volatility else None
            ),
            "last_rebalance": (
                portfolio.last_rebalance.isoformat() if portfolio.last_rebalance else None
            ),
        }
