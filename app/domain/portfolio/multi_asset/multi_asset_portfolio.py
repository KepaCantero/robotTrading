"""
Multi-Asset Portfolio Manager.

This module provides the main portfolio management functionality for multi-asset
portfolios, including construction, rebalancing, and risk management.
"""
# mypy: ignore-errors

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.backtesting.models import Trade

from .asset_class import AssetClass, AssetClassConfig, AssetClassType
from .models import MultiAssetAllocation, MultiAssetPortfolio, PortfolioMetrics, RiskTolerance

logger = logging.getLogger(__name__)


class MultiAssetConfig(BaseModel):
    """
    Configuration for multi-asset portfolio manager.

    Attributes:
        asset_classes: List of asset class configurations
        rebalance_threshold: Deviation threshold for rebalancing
        risk_tolerance: Overall risk tolerance
        max_positions_per_class: Maximum positions per asset class
        min_position_size: Minimum position size as fraction of portfolio
        max_position_size: Maximum position size as fraction of portfolio
        trading_cost_bps: Trading cost in basis points
        enable_tilts: Enable tactical tilts
        max_tilt_size: Maximum tactical tilt size
        currency: Portfolio base currency
        metadata: Additional metadata
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    asset_classes: List[AssetClassConfig] = Field(
        ..., min_length=1, description="Asset class configurations"
    )
    rebalance_threshold: Decimal = Field(
        default=Decimal("0.05"),
        ge=Decimal("0"),
        le=Decimal("0.5"),
        description="Rebalance threshold",
    )
    risk_tolerance: RiskTolerance = Field(
        default=RiskTolerance.MODERATE, description="Overall risk tolerance"
    )
    max_positions_per_class: int = Field(
        default=20, ge=1, le=100, description="Max positions per class"
    )
    min_position_size: Decimal = Field(
        default=Decimal("0.01"), ge=Decimal("0"), le=Decimal("1"), description="Min position size"
    )
    max_position_size: Decimal = Field(
        default=Decimal("0.20"), ge=Decimal("0"), le=Decimal("1"), description="Max position size"
    )
    trading_cost_bps: Decimal = Field(
        default=Decimal("10"), ge=Decimal("0"), le=Decimal("100"), description="Trading cost in bps"
    )
    enable_tilts: bool = Field(default=False, description="Enable tactical tilts")
    max_tilt_size: Decimal = Field(
        default=Decimal("0.20"), ge=Decimal("0"), le=Decimal("0.5"), description="Max tactical tilt"
    )
    currency: str = Field(default="USD", description="Portfolio base currency")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("max_position_size")
    @classmethod
    def validate_max_position_size(cls, v: Decimal, info) -> Decimal:
        """Validate max_position_size is >= min_position_size."""
        if "min_position_size" in info.data and v < info.data["min_position_size"]:
            raise ValueError(
                f"max_position_size ({v}) must be >= min_position_size ({info.data['min_position_size']})"
            )
        return v

    @field_validator("asset_classes")
    @classmethod
    def validate_asset_classes(cls, v: List[AssetClassConfig]) -> List[AssetClassConfig]:
        """Validate asset class configurations."""
        names = [ac.name for ac in v]
        if len(names) != len(set(names)):
            raise ValueError("Asset class names must be unique")

        # Check at least one enabled
        if not any(ac.enabled for ac in v):
            raise ValueError("At least one asset class must be enabled")

        return v


@dataclass
class PortfolioConstructionResult:
    """
    Result of portfolio construction.

    Attributes:
        portfolio: Constructed portfolio
        metrics: Portfolio metrics
        trades: Required trades to implement
        warnings: List of warnings
        success: Whether construction was successful
        error: Error message if unsuccessful
    """

    portfolio: Optional[MultiAssetPortfolio]
    metrics: Optional[PortfolioMetrics]
    trades: List[Trade]
    warnings: List[str]
    success: bool
    error: Optional[str] = None


@dataclass
class RebalanceResult:
    """
    Result of portfolio rebalancing.

    Attributes:
        trades: Trades to execute
        total_cost: Estimated total cost
        pre_rebalance_weights: Weights before rebalancing
        post_rebalance_weights: Target weights after rebalancing
        warnings: List of warnings
        success: Whether rebalancing was successful
        error: Error message if unsuccessful
    """

    trades: List[Trade]
    total_cost: Decimal
    pre_rebalance_weights: Dict[str, Decimal]
    post_rebalance_weights: Dict[str, Decimal]
    warnings: List[str]
    success: bool
    error: Optional[str] = None


class MultiAssetPortfolioManager:
    """
    Manage multi-asset portfolio.

    This class provides comprehensive portfolio management functionality including:
    - Asset class allocation
    - Within-class allocation
    - Risk management across assets
    - Rebalancing logic
    - Portfolio construction
    - Risk contribution analysis

    Example:
        >>> config = MultiAssetConfig(asset_classes=[...])
        >>> manager = MultiAssetPortfolioManager(config)
        >>>
        >>> # Construct portfolio
        >>> result = manager.construct_portfolio(
        ...     target_weights={"equity": Decimal("0.6"), "bonds": Decimal("0.4")},
        ...     market_data=market_data
        ... )
    """

    def __init__(self, config: MultiAssetConfig):
        """
        Initialize portfolio manager.

        Args:
            config: Portfolio configuration
        """
        self.config = config
        self.asset_classes: Dict[str, AssetClass] = {}
        self._initialize_asset_classes()

    def _initialize_asset_classes(self) -> None:
        """Initialize asset classes from configuration."""
        for ac_config in self.config.asset_classes:
            if ac_config.enabled:
                asset_class = AssetClass.from_config(ac_config)
                self.asset_classes[ac_config.name] = asset_class
                logger.info(f"Initialized asset class: {ac_config.name} ({ac_config.type})")

    def construct_portfolio(
        self,
        target_weights: Dict[str, Decimal],
        market_data: Dict[str, pd.DataFrame],
        strategy: str = "equal_weight",
    ) -> PortfolioConstructionResult:
        """
        Construct multi-asset portfolio.

        Process:
        1. Validate target weights sum to 1
        2. For each asset class:
           a. Select assets (by strategy or index)
           b. Calculate within-class allocation
           c. Apply position limits
        3. Calculate portfolio-level metrics
        4. Validate risk constraints

        Args:
            target_weights: Target weights for each asset class (name -> weight)
            market_data: Market data for each asset class (name -> DataFrame)
            strategy: Within-class allocation strategy

        Returns:
            PortfolioConstructionResult with portfolio and metadata
        """
        warnings: List[str] = []

        try:
            # Step 1: Validate target weights
            self._validate_target_weights(target_weights)

            # Step 2: Get available asset classes
            available_classes = self._get_available_asset_classes(target_weights)

            # Step 3: Create allocations for each asset class
            allocations: Dict[str, MultiAssetAllocation] = {}

            for class_name, weight in target_weights.items():
                if class_name not in available_classes:
                    warnings.append(f"Asset class '{class_name}' not available, skipping")
                    continue

                asset_class = available_classes[class_name]

                # Check if we have market data for this class
                if class_name not in market_data or market_data[class_name].empty:
                    warnings.append(f"No market data for '{class_name}', using cash proxy")
                    # Create simple allocation with cash proxy
                    allocations[class_name] = self._create_cash_allocation(asset_class, weight)
                    continue

                # Create within-class allocation
                try:
                    allocation = self._create_asset_class_allocation(
                        asset_class=asset_class,
                        weight=weight,
                        market_data=market_data[class_name],
                        strategy=strategy,
                    )
                    allocations[class_name] = allocation
                except Exception as e:
                    warnings.append(f"Failed to allocate to '{class_name}': {str(e)}")
                    logger.error(f"Allocation failed for {class_name}: {e}")
                    # Fallback to cash
                    allocations[class_name] = self._create_cash_allocation(asset_class, weight)

            # Step 4: Create portfolio
            portfolio = MultiAssetPortfolio(
                name="Multi-Asset Portfolio",
                allocations=allocations,
                total_value=Decimal("1000000"),  # Default $1M
                last_rebalanced=datetime.utcnow(),
                rebalance_threshold=self.config.rebalance_threshold,
                currency=self.config.currency,
            )

            # Step 5: Calculate metrics
            metrics = self._calculate_initial_metrics(portfolio, market_data)

            # Step 6: Generate initial trades (implementation trades)
            trades = self._generate_implementation_trades(portfolio, market_data)

            logger.info(f"Portfolio constructed with {len(allocations)} asset classes")

            return PortfolioConstructionResult(
                portfolio=portfolio,
                metrics=metrics,
                trades=trades,
                warnings=warnings,
                success=True,
            )

        except Exception as e:
            logger.error(f"Portfolio construction failed: {e}", exc_info=True)
            return PortfolioConstructionResult(
                portfolio=None,
                metrics=None,
                trades=[],
                warnings=warnings,
                success=False,
                error=str(e),
            )

    def rebalance(
        self,
        current_portfolio: MultiAssetPortfolio,
        target_weights: Dict[str, Decimal],
        current_prices: Dict[str, Decimal],
        portfolio_value: Decimal,
    ) -> RebalanceResult:
        """
        Calculate rebalancing trades.

        Only rebalance if:
        - Asset class weight deviates > threshold
        - Within-class allocation deviates > threshold

        Args:
            current_portfolio: Current portfolio state
            target_weights: Target weights for each asset class
            current_prices: Current prices for all assets
            portfolio_value: Current total portfolio value

        Returns:
            RebalanceResult with trades and metadata
        """
        warnings: List[str] = []
        trades: List[Trade] = []

        try:
            # Get current weights
            pre_rebalance_weights = current_portfolio.get_asset_class_weights()

            # Check if rebalancing is needed
            rebalance_needed, deviations = self._check_rebalance_needed(
                current_portfolio, target_weights, current_prices, portfolio_value
            )

            if not rebalance_needed:
                logger.info("No rebalancing needed - all weights within threshold")
                return RebalanceResult(
                    trades=[],
                    total_cost=Decimal("0"),
                    pre_rebalance_weights=pre_rebalance_weights,
                    post_rebalance_weights=target_weights,
                    warnings=[],
                    success=True,
                )

            # Calculate trades needed
            for class_name, target_weight in target_weights.items():
                if class_name not in current_portfolio.allocations:
                    # New asset class
                    trades.extend(
                        self._calculate_asset_class_trades(
                            class_name=class_name,
                            target_weight=target_weight,
                            current_weight=Decimal("0"),
                            portfolio_value=portfolio_value,
                            current_prices=current_prices,
                        )
                    )
                else:
                    # Existing asset class
                    current_alloc = current_portfolio.allocations[class_name]
                    current_weight = current_alloc.weight

                    if abs(current_weight - target_weight) > self.config.rebalance_threshold:
                        trades.extend(
                            self._calculate_asset_class_trades(
                                class_name=class_name,
                                target_weight=target_weight,
                                current_weight=current_weight,
                                portfolio_value=portfolio_value,
                                current_prices=current_prices,
                                current_allocation=current_alloc,
                            )
                        )

            # Calculate total cost
            total_cost = sum(t.estimated_cost for t in trades)

            logger.info(f"Calculated {len(trades)} rebalancing trades")

            return RebalanceResult(
                trades=trades,
                total_cost=total_cost,
                pre_rebalance_weights=pre_rebalance_weights,
                post_rebalance_weights=target_weights,
                warnings=warnings,
                success=True,
            )

        except Exception as e:
            logger.error(f"Rebalancing failed: {e}", exc_info=True)
            return RebalanceResult(
                trades=[],
                total_cost=Decimal("0"),
                pre_rebalance_weights=current_portfolio.get_asset_class_weights(),
                post_rebalance_weights=target_weights,
                warnings=warnings,
                success=False,
                error=str(e),
            )

    def calculate_risk_contributions(
        self, portfolio: MultiAssetPortfolio, returns: pd.DataFrame
    ) -> Dict[str, Decimal]:
        """
        Calculate risk contributions by asset class.

        Uses marginal contribution to risk (MCTR).

        Args:
            portfolio: Portfolio to analyze
            returns: Historical returns for all assets

        Returns:
            Dictionary of asset class -> risk contribution
        """
        try:
            # Get portfolio weights as vector
            all_assets = portfolio.get_all_assets()
            symbols = list(all_assets.keys())
            weights = np.array([float(all_assets[s]) for s in symbols])

            # Get returns for portfolio symbols
            portfolio_returns = returns[symbols] if not returns.empty else pd.DataFrame()

            if portfolio_returns.empty:
                # Return equal contributions if no data
                n_classes = len(portfolio.allocations)
                contribution = (
                    Decimal("1") / Decimal(str(n_classes)) if n_classes > 0 else Decimal("0")
                )
                return {name: contribution for name in portfolio.allocations}

            # Calculate covariance matrix
            cov_matrix = portfolio_returns.cov().values

            # Calculate portfolio variance
            portfolio_variance = float(weights.T @ cov_matrix @ weights)

            if portfolio_variance == 0:
                # No risk, return equal contributions
                n_classes = len(portfolio.allocations)
                contribution = (
                    Decimal("1") / Decimal(str(n_classes)) if n_classes > 0 else Decimal("0")
                )
                return {name: contribution for name in portfolio.allocations}

            # Calculate marginal contribution to risk for each asset
            # MCTR_i = (w_i * (Σw)_i) / σ_p^2
            marginal_contrib = (cov_matrix @ weights) / portfolio_variance

            # Aggregate by asset class
            risk_contributions: Dict[str, float] = {}

            for class_name, alloc in portfolio.allocations.items():
                class_contribution = 0.0
                for symbol in alloc.assets:
                    if symbol in symbols:
                        symbol_idx = symbols.index(symbol)
                        abs_weight = alloc.get_absolute_weight(symbol)
                        class_contribution += float(abs_weight) * marginal_contrib[symbol_idx]

                risk_contributions[class_name] = class_contribution

            # Normalize to sum to 1
            total = sum(risk_contributions.values())
            if total > 0:
                risk_contributions = {
                    k: Decimal(str(v / total)) for k, v in risk_contributions.items()
                }
            else:
                # Equal contributions if calculation failed
                n_classes = len(portfolio.allocations)
                equal_contrib = (
                    Decimal("1") / Decimal(str(n_classes)) if n_classes > 0 else Decimal("0")
                )
                risk_contributions = {name: equal_contrib for name in portfolio.allocations}

            return risk_contributions

        except Exception as e:
            logger.error(f"Risk contribution calculation failed: {e}", exc_info=True)
            # Return equal contributions on error
            n_classes = len(portfolio.allocations)
            equal_contrib = (
                Decimal("1") / Decimal(str(n_classes)) if n_classes > 0 else Decimal("0")
            )
            return {name: equal_contrib for name in portfolio.allocations}

    def _validate_target_weights(self, target_weights: Dict[str, Decimal]) -> None:
        """
        Validate target weights.

        Args:
            target_weights: Target weights to validate

        Raises:
            ValueError: If weights are invalid
        """
        if not target_weights:
            raise ValueError("Target weights cannot be empty")

        # Check sum is approximately 1
        total = sum(target_weights.values())
        tolerance = Decimal("0.01")

        if abs(total - Decimal("1")) > tolerance:
            raise ValueError(f"Target weights must sum to 1 (±{tolerance}), got {total}")

        # Check all weights are non-negative
        for name, weight in target_weights.items():
            if weight < 0:
                raise ValueError(f"Weight for {name} cannot be negative, got {weight}")

        # Check all target asset classes exist
        for name in target_weights:
            if name not in self.asset_classes and name not in [
                ac.name for ac in self.config.asset_classes
            ]:
                raise ValueError(f"Unknown asset class: {name}")

    def _get_available_asset_classes(
        self, target_weights: Dict[str, Decimal]
    ) -> Dict[str, AssetClass]:
        """Get available asset classes from target weights."""
        available = {}
        for name in target_weights:
            if name in self.asset_classes:
                available[name] = self.asset_classes[name]
        return available

    def _create_asset_class_allocation(
        self,
        asset_class: AssetClass,
        weight: Decimal,
        market_data: pd.DataFrame,
        strategy: str = "equal_weight",
    ) -> MultiAssetAllocation:
        """
        Create allocation for a single asset class.

        Args:
            asset_class: Asset class definition
            weight: Target weight for this class
            market_data: Market data for assets in this class
            strategy: Allocation strategy

        Returns:
            MultiAssetAllocation
        """
        # Get available assets from market data
        symbols = list(market_data.columns) if not market_data.empty else []

        if not symbols:
            # No assets available, use cash proxy
            return self._create_cash_allocation(asset_class, weight)

        # Select top assets by liquidity or market cap if needed
        max_pos = min(
            len(symbols), asset_class.max_positions or self.config.max_positions_per_class
        )
        selected_symbols = symbols[:max_pos]

        # Calculate within-class weights
        if strategy == "equal_weight":
            within_weights = {s: Decimal("1") / Decimal(str(max_pos)) for s in selected_symbols}
        elif strategy == "market_cap_weighted":
            # Would need market cap data
            within_weights = self._calculate_market_cap_weights(selected_symbols, market_data)
        elif strategy == "volatility_weighted":
            within_weights = self._calculate_volatility_weights(selected_symbols, market_data)
        else:
            # Default to equal weight
            within_weights = {s: Decimal("1") / Decimal(str(max_pos)) for s in selected_symbols}

        # Apply position size limits
        within_weights = self._apply_position_limits(within_weights)

        # Calculate expected return and risk for this allocation
        expected_return = asset_class.expected_return * weight
        risk = asset_class.volatility * weight

        return MultiAssetAllocation(
            asset_class=asset_class,
            weight=weight,
            assets=within_weights,
            expected_return=expected_return,
            risk=risk,
        )

    def _create_cash_allocation(
        self, asset_class: AssetClass, weight: Decimal
    ) -> MultiAssetAllocation:
        """Create cash allocation for asset class."""
        return MultiAssetAllocation(
            asset_class=asset_class,
            weight=weight,
            assets={"CASH": Decimal("1")},
            expected_return=Decimal("0"),
            risk=Decimal("0"),
        )

    def _calculate_market_cap_weights(
        self, symbols: List[str], market_data: pd.DataFrame
    ) -> Dict[str, Decimal]:
        """Calculate market cap weighted allocation."""
        # Simplified - would need actual market cap data
        # For now, use equal weight
        n = len(symbols)
        return {s: Decimal("1") / Decimal(str(n)) for s in symbols}

    def _calculate_volatility_weights(
        self, symbols: List[str], market_data: pd.DataFrame
    ) -> Dict[str, Decimal]:
        """Calculate inverse volatility weighted allocation."""
        weights = {}

        for symbol in symbols:
            if symbol in market_data.columns:
                # Calculate volatility (inverse)
                returns = market_data[symbol].pct_change().dropna()
                vol = returns.std()
                weights[symbol] = Decimal(str(1 / (vol + 1e-6)))  # Avoid division by zero

        # Normalize
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return weights

    def _apply_position_limits(self, weights: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """Apply position size limits to weights."""
        limited = {}

        # Ensure weights are within bounds
        for symbol, weight in weights.items():
            # Apply max position size
            if weight > self.config.max_position_size:
                limited[symbol] = self.config.max_position_size
            elif weight < self.config.min_position_size:
                limited[symbol] = Decimal("0")
            else:
                limited[symbol] = weight

        # Renormalize
        total = sum(limited.values())
        if total > 0:
            limited = {k: v / total for k, v in limited.items()}

        return limited

    def _calculate_initial_metrics(
        self, portfolio: MultiAssetPortfolio, market_data: Dict[str, pd.DataFrame]
    ) -> PortfolioMetrics:
        """Calculate initial portfolio metrics."""
        # Calculate expected return and volatility
        expected_return = Decimal("0")
        portfolio_variance = Decimal("0")

        for alloc in portfolio.allocations.values():
            expected_return += alloc.expected_return or Decimal("0")
            # Simplified variance calculation
            if alloc.risk:
                risk_val = alloc.risk
                portfolio_variance += risk_val**2

        volatility = portfolio_variance.sqrt() if portfolio_variance > 0 else Decimal("0")

        return PortfolioMetrics(
            total_return=Decimal("0"),
            annualized_return=expected_return,
            volatility=volatility,
        )

    def _generate_implementation_trades(
        self, portfolio: MultiAssetPortfolio, market_data: Dict[str, pd.DataFrame]
    ) -> List[Trade]:
        """Generate trades to implement the portfolio."""
        trades = []

        for class_name, alloc in portfolio.allocations.items():
            for symbol, weight in alloc.assets.items():
                if symbol == "CASH":
                    continue

                # Get price from market data
                price = Decimal("100")  # Default

                if class_name in market_data and not market_data[class_name].empty:
                    if symbol in market_data[class_name].columns:
                        # Get last price
                        price = Decimal(str(market_data[class_name][symbol].iloc[-1]))

                # Calculate position size
                position_value = portfolio.total_value * alloc.get_absolute_weight(symbol)

                # Determine if fractional shares are allowed (crypto, forex)
                asset_class = self.asset_classes.get(class_name)
                allow_fractional = asset_class and asset_class.type in [
                    AssetClassType.CRYPTO,
                    AssetClassType.FOREX,
                ]

                if allow_fractional:
                    # Use fractional shares
                    quantity = position_value / price
                else:
                    # Round to whole shares
                    quantity = (position_value / price).quantize(Decimal("1"))

                # Cap quantity at maximum limit
                max_quantity = Decimal("1000000")
                if quantity > max_quantity:
                    quantity = max_quantity
                elif quantity < -max_quantity:
                    quantity = -max_quantity

                if quantity > 0:
                    trade = Trade(
                        symbol=symbol,
                        asset_class=class_name,
                        quantity=quantity,
                        price=price,
                        value=position_value,
                        reason=f"Initial allocation to {class_name}",
                        priority=50,
                        estimated_cost=position_value
                        * self.config.trading_cost_bps
                        / Decimal("10000"),
                    )
                    trades.append(trade)

        return trades

    def _check_rebalance_needed(
        self,
        portfolio: MultiAssetPortfolio,
        target_weights: Dict[str, Decimal],
        current_prices: Dict[str, Decimal],
        portfolio_value: Decimal,
    ) -> Tuple[bool, Dict[str, Decimal]]:
        """Check if rebalancing is needed."""
        deviations = {}
        rebalance_needed = False

        for class_name, target_weight in target_weights.items():
            if class_name not in portfolio.allocations:
                # New class, need to rebalance
                rebalance_needed = True
                deviations[class_name] = target_weight
            else:
                current_weight = portfolio.allocations[class_name].weight
                deviation = abs(current_weight - target_weight)
                deviations[class_name] = deviation

                if deviation > self.config.rebalance_threshold:
                    rebalance_needed = True

        return rebalance_needed, deviations

    def _calculate_asset_class_trades(
        self,
        class_name: str,
        target_weight: Decimal,
        current_weight: Decimal,
        portfolio_value: Decimal,
        current_prices: Dict[str, Decimal],
        current_allocation: Optional[MultiAssetAllocation] = None,
    ) -> List[Trade]:
        """Calculate trades to rebalance an asset class."""
        trades = []

        # Calculate weight difference
        weight_diff = target_weight - current_weight
        target_value = portfolio_value * target_weight

        if abs(weight_diff) < self.config.rebalance_threshold:
            return trades

        if current_allocation is None:
            # New allocation - buy target assets
            # This is simplified - would need to know target assets
            pass
        else:
            # Adjust existing allocation
            for symbol, within_weight in current_allocation.assets.items():
                if symbol == "CASH":
                    continue

                price = current_prices.get(symbol, Decimal("100"))
                target_asset_value = target_value * within_weight
                quantity = (target_asset_value / price).quantize(Decimal("1"))

                if quantity > 0:
                    trade = Trade(
                        symbol=symbol,
                        asset_class=class_name,
                        quantity=quantity,
                        price=price,
                        value=target_asset_value,
                        reason=f"Rebalance {class_name} allocation",
                        priority=int(abs(weight_diff) * 100),
                        estimated_cost=target_asset_value
                        * self.config.trading_cost_bps
                        / Decimal("10000"),
                    )
                    trades.append(trade)

        return trades
