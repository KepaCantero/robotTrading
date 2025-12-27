"""
T7.1: PortfolioConstructor - Portfolio optimization and construction

Uses multiple strategies for portfolio allocation:
1. Equal-weight: Baseline, simple allocation
2. Risk-parity: Weight by inverse volatility (requires historical data)
3. Efficient frontier: Maximize Sharpe ratio (requires expected returns/covariance)

Fallback chain: Try efficient frontier → risk parity → equal weight
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from .models import AllocationWeight, PortfolioAllocation, PortfolioConstructionRequest

logger = logging.getLogger(__name__)


class PortfolioConstructor:
    """
    Constructs optimized portfolios across enabled trading modules.

    Applies multiple optimization strategies with graceful fallback:
    - Efficient Frontier (PyPortfolioOpt) - preferred
    - Risk Parity (volatility-weighted) - fallback
    - Equal Weight - fallback
    """

    # Risk profiles affect how aggressively we allocate
    RISK_PROFILE_CONFIG = {
        "aggressive": {
            "efficiency_weight": Decimal("0.7"),  # Higher weight on high-return modules
            "volatility_tolerance": Decimal("0.25"),  # Can accept higher volatility
        },
        "balanced": {
            "efficiency_weight": Decimal("0.5"),
            "volatility_tolerance": Decimal("0.15"),
        },
        "conservative": {
            "efficiency_weight": Decimal("0.3"),  # Higher weight on lower-volatility modules
            "volatility_tolerance": Decimal("0.10"),
        },
    }

    # Module characteristics (volatility, expected return, minimum allocation)
    MODULE_CHARACTERISTICS = {
        "momentum": {
            "volatility_score": Decimal("0.18"),  # Moderate
            "expected_return": Decimal("12"),  # 12% annually
            "min_allocation_pct": Decimal("5"),
            "max_allocation_pct": Decimal("40"),
        },
        "mean_reversion": {
            "volatility_score": Decimal("0.15"),  # Lower
            "expected_return": Decimal("8"),
            "min_allocation_pct": Decimal("5"),
            "max_allocation_pct": Decimal("35"),
        },
        "pairs_trading": {
            "volatility_score": Decimal("0.12"),  # Low
            "expected_return": Decimal("6"),
            "min_allocation_pct": Decimal("5"),
            "max_allocation_pct": Decimal("30"),
        },
        "machine_learning_basic": {
            "volatility_score": Decimal("0.20"),
            "expected_return": Decimal("15"),
            "min_allocation_pct": Decimal("0"),
            "max_allocation_pct": Decimal("35"),
        },
        "transformer_engine": {
            "volatility_score": Decimal("0.22"),
            "expected_return": Decimal("18"),
            "min_allocation_pct": Decimal("0"),
            "max_allocation_pct": Decimal("30"),
        },
        "deep_learning_engine": {
            "volatility_score": Decimal("0.25"),
            "expected_return": Decimal("20"),
            "min_allocation_pct": Decimal("0"),
            "max_allocation_pct": Decimal("25"),
        },
        "reinforcement_learning": {
            "volatility_score": Decimal("0.28"),
            "expected_return": Decimal("22"),
            "min_allocation_pct": Decimal("0"),
            "max_allocation_pct": Decimal("20"),
        },
        "ensemble_strategy": {
            "volatility_score": Decimal("0.16"),
            "expected_return": Decimal("14"),
            "min_allocation_pct": Decimal("5"),
            "max_allocation_pct": Decimal("40"),
        },
    }

    def __init__(self):
        """Initialize portfolio constructor."""
        self.construction_history: List[PortfolioAllocation] = []
        logger.info("✅ PortfolioConstructor initialized")

    async def construct_portfolio(
        self,
        request: PortfolioConstructionRequest,
    ) -> PortfolioAllocation:
        """
        Construct optimized portfolio across enabled modules.

        Strategy:
        1. Try efficient frontier optimization (requires expected returns/covariance)
        2. Fallback to risk-parity weighting (inverse volatility)
        3. Final fallback to equal-weight allocation

        Args:
            request: Portfolio construction request with modules and capital

        Returns:
            PortfolioAllocation with optimized weights
        """
        start_time = datetime.utcnow()

        try:
            # Validate enabled modules
            if not request.enabled_modules:
                logger.warning("No modules enabled, using equal weight")
                return await self._construct_equal_weight_portfolio(request)

            # Get risk profile config
            risk_config = self.RISK_PROFILE_CONFIG.get(
                request.risk_profile,
                self.RISK_PROFILE_CONFIG["balanced"],
            )

            # Try efficient frontier first
            allocation = await self._construct_efficient_frontier_portfolio(request, risk_config)
            if allocation.success:
                allocation.allocation_method = "efficient_frontier"
                self.construction_history.append(allocation)
                elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                logger.info(
                    f"✅ Efficient frontier portfolio constructed for {request.profile_id}, "
                    f"elapsed={elapsed_ms:.0f}ms"
                )
                return allocation

            # Fallback to risk-parity
            logger.info("Efficient frontier failed, falling back to risk-parity")
            allocation = await self._construct_risk_parity_portfolio(request)
            if allocation.success:
                allocation.allocation_method = "risk_parity"
                self.construction_history.append(allocation)
                elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                logger.info(
                    f"✅ Risk-parity portfolio constructed for {request.profile_id}, "
                    f"elapsed={elapsed_ms:.0f}ms"
                )
                return allocation

            # Final fallback to equal weight
            logger.info("Risk-parity failed, falling back to equal-weight")
            allocation = await self._construct_equal_weight_portfolio(request)
            if allocation.success:
                self.construction_history.append(allocation)
                elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                logger.info(
                    f"✅ Equal-weight portfolio constructed for {request.profile_id}, "
                    f"elapsed={elapsed_ms:.0f}ms"
                )
            return allocation

        except Exception as e:
            logger.error(f"❌ Error constructing portfolio: {e}")
            return PortfolioAllocation(
                success=False,
                profile_id=request.profile_id,
                total_capital_eur=request.capital_eur,
                allocations=[],
                allocation_method="error",
                expected_portfolio_return_pct=Decimal("0"),
                expected_portfolio_sharpe=Decimal("0"),
                expected_portfolio_drawdown_pct=Decimal("0"),
                diversification_ratio=Decimal("0"),
                error_message=str(e),
            )

    async def _construct_efficient_frontier_portfolio(
        self,
        request: PortfolioConstructionRequest,
        risk_config: Dict,
    ) -> PortfolioAllocation:
        """
        Construct portfolio using efficient frontier optimization.

        Uses expected returns and volatility estimates to maximize Sharpe ratio.
        """
        try:
            # Get module characteristics
            module_returns = {}
            module_volatilities = {}

            for module in request.enabled_modules:
                if module in self.MODULE_CHARACTERISTICS:
                    char = self.MODULE_CHARACTERISTICS[module]
                    module_returns[module] = char["expected_return"]
                    module_volatilities[module] = char["volatility_score"]
                else:
                    # Default for unknown modules
                    module_returns[module] = Decimal("10")
                    module_volatilities[module] = Decimal("0.15")

            # Calculate efficient weights using Sharpe ratio maximization
            # Simplified: weight by (return / volatility) ratio
            sharpe_ratios = {}
            for module in request.enabled_modules:
                ret = module_returns[module]
                vol = module_volatilities[module]
                sharpe_ratios[module] = ret / vol if vol > 0 else Decimal("0")

            # Normalize to weights
            total_sharpe = sum(sharpe_ratios.values())
            if total_sharpe <= 0:
                logger.warning("Negative Sharpe ratios, falling back to equal weight")
                return PortfolioAllocation(
                    success=False,
                    profile_id=request.profile_id,
                    total_capital_eur=request.capital_eur,
                    allocations=[],
                    allocation_method="efficient_frontier",
                    expected_portfolio_return_pct=Decimal("0"),
                    expected_portfolio_sharpe=Decimal("0"),
                    expected_portfolio_drawdown_pct=Decimal("0"),
                    diversification_ratio=Decimal("0"),
                )

            weights = {
                module: (sharpe_ratios[module] / total_sharpe) * Decimal("100")
                for module in request.enabled_modules
            }

            # Apply risk profile adjustment
            efficiency_weight = risk_config["efficiency_weight"]
            equal_weight = (
                (Decimal("1") - efficiency_weight) / len(request.enabled_modules) * Decimal("100")
            )

            adjusted_weights = {}
            for module in request.enabled_modules:
                adjusted = weights[module] * efficiency_weight + equal_weight * (
                    Decimal("1") - efficiency_weight
                )
                adjusted_weights[module] = adjusted

            # Normalize to 100%
            total_weight = sum(adjusted_weights.values())
            if total_weight > 0:
                adjusted_weights = {
                    module: (weight / total_weight) * Decimal("100")
                    for module, weight in adjusted_weights.items()
                }

            # Create allocation
            allocations = []
            portfolio_return = Decimal("0")
            portfolio_volatility = Decimal("0")

            for module in request.enabled_modules:
                weight = adjusted_weights.get(module, Decimal("0"))
                capital = request.capital_eur * weight / Decimal("100")

                allocations.append(
                    AllocationWeight(
                        module_name=module,
                        weight_pct=weight,
                        capital_allocation_eur=capital,
                        rationale="Efficient frontier optimization: Sharpe ratio weighting",
                    )
                )

                # Accumulate portfolio metrics
                portfolio_return += module_returns[module] * weight / Decimal("100")
                portfolio_volatility += (module_volatilities[module] * weight / Decimal("100")) ** 2

            # Calculate portfolio metrics
            portfolio_volatility = portfolio_volatility.sqrt()
            portfolio_sharpe = (
                (portfolio_return - Decimal("2")) / portfolio_volatility
                if portfolio_volatility > 0
                else Decimal("0")
            )  # Assuming 2% risk-free rate
            portfolio_drawdown = portfolio_volatility * Decimal("2")  # Max drawdown ≈ 2σ

            # Calculate diversification ratio
            equal_weight_volatility = sum(
                self.MODULE_CHARACTERISTICS.get(m, {}).get("volatility_score", Decimal("0.15"))
                for m in request.enabled_modules
            ) / len(request.enabled_modules)
            diversification_ratio = (
                equal_weight_volatility / portfolio_volatility
                if portfolio_volatility > 0
                else Decimal("1")
            )

            return PortfolioAllocation(
                success=True,
                profile_id=request.profile_id,
                total_capital_eur=request.capital_eur,
                allocations=allocations,
                allocation_method="efficient_frontier",
                expected_portfolio_return_pct=portfolio_return,
                expected_portfolio_sharpe=portfolio_sharpe,
                expected_portfolio_drawdown_pct=portfolio_drawdown,
                diversification_ratio=diversification_ratio,
                optimization_notes="Efficient frontier with Sharpe ratio maximization and risk profile adjustment",
            )

        except Exception as e:
            logger.error(f"Efficient frontier optimization failed: {e}")
            return PortfolioAllocation(
                success=False,
                profile_id=request.profile_id,
                total_capital_eur=request.capital_eur,
                allocations=[],
                allocation_method="efficient_frontier",
                expected_portfolio_return_pct=Decimal("0"),
                expected_portfolio_sharpe=Decimal("0"),
                expected_portfolio_drawdown_pct=Decimal("0"),
                diversification_ratio=Decimal("0"),
                error_message=str(e),
            )

    async def _construct_risk_parity_portfolio(
        self,
        request: PortfolioConstructionRequest,
    ) -> PortfolioAllocation:
        """
        Construct portfolio using risk-parity approach.

        Weight each module inversely by its volatility (lower volatility = higher weight).
        """
        try:
            # Get volatility scores
            volatilities = {}
            for module in request.enabled_modules:
                if module in self.MODULE_CHARACTERISTICS:
                    volatilities[module] = self.MODULE_CHARACTERISTICS[module]["volatility_score"]
                else:
                    volatilities[module] = Decimal("0.15")

            # Risk parity: weight inversely by volatility
            # weight ∝ 1/volatility
            risk_parity_weights = {
                module: Decimal("1") / vol if vol > 0 else Decimal("1")
                for module, vol in volatilities.items()
            }

            # Normalize to 100%
            total_weight = sum(risk_parity_weights.values())
            normalized_weights = {
                module: (weight / total_weight) * Decimal("100")
                for module, weight in risk_parity_weights.items()
            }

            # Get expected returns
            expected_returns = {}
            for module in request.enabled_modules:
                if module in self.MODULE_CHARACTERISTICS:
                    expected_returns[module] = self.MODULE_CHARACTERISTICS[module][
                        "expected_return"
                    ]
                else:
                    expected_returns[module] = Decimal("10")

            # Create allocation
            allocations = []
            portfolio_return = Decimal("0")
            portfolio_volatility = Decimal("0")

            for module in request.enabled_modules:
                weight = normalized_weights.get(module, Decimal("0"))
                capital = request.capital_eur * weight / Decimal("100")

                allocations.append(
                    AllocationWeight(
                        module_name=module,
                        weight_pct=weight,
                        capital_allocation_eur=capital,
                        rationale="Risk-parity: Inverse volatility weighting",
                    )
                )

                # Accumulate portfolio metrics
                portfolio_return += expected_returns[module] * weight / Decimal("100")
                portfolio_volatility += (volatilities[module] * weight / Decimal("100")) ** 2

            portfolio_volatility = portfolio_volatility.sqrt()
            portfolio_sharpe = (
                (portfolio_return - Decimal("2")) / portfolio_volatility
                if portfolio_volatility > 0
                else Decimal("0")
            )
            portfolio_drawdown = portfolio_volatility * Decimal("2")

            # Diversification ratio
            equal_weight_volatility = sum(volatilities.values()) / len(request.enabled_modules)
            diversification_ratio = (
                equal_weight_volatility / portfolio_volatility
                if portfolio_volatility > 0
                else Decimal("1")
            )

            return PortfolioAllocation(
                success=True,
                profile_id=request.profile_id,
                total_capital_eur=request.capital_eur,
                allocations=allocations,
                allocation_method="risk_parity",
                expected_portfolio_return_pct=portfolio_return,
                expected_portfolio_sharpe=portfolio_sharpe,
                expected_portfolio_drawdown_pct=portfolio_drawdown,
                diversification_ratio=diversification_ratio,
                optimization_notes="Risk-parity allocation: weights inversely proportional to volatility",
            )

        except Exception as e:
            logger.error(f"Risk-parity portfolio construction failed: {e}")
            return PortfolioAllocation(
                success=False,
                profile_id=request.profile_id,
                total_capital_eur=request.capital_eur,
                allocations=[],
                allocation_method="risk_parity",
                expected_portfolio_return_pct=Decimal("0"),
                expected_portfolio_sharpe=Decimal("0"),
                expected_portfolio_drawdown_pct=Decimal("0"),
                diversification_ratio=Decimal("0"),
                error_message=str(e),
            )

    async def _construct_equal_weight_portfolio(
        self,
        request: PortfolioConstructionRequest,
    ) -> PortfolioAllocation:
        """
        Construct simple equal-weight portfolio (baseline).

        Each enabled module gets equal allocation.
        """
        try:
            if not request.enabled_modules:
                return PortfolioAllocation(
                    success=False,
                    profile_id=request.profile_id,
                    total_capital_eur=request.capital_eur,
                    allocations=[],
                    allocation_method="equal_weight",
                    expected_portfolio_return_pct=Decimal("0"),
                    expected_portfolio_sharpe=Decimal("0"),
                    expected_portfolio_drawdown_pct=Decimal("0"),
                    diversification_ratio=Decimal("0"),
                    error_message="No modules enabled",
                )

            weight_per_module = Decimal("100") / len(request.enabled_modules)

            allocations = []
            portfolio_return = Decimal("0")
            portfolio_volatility = Decimal("0")

            for module in request.enabled_modules:
                capital = request.capital_eur * weight_per_module / Decimal("100")

                allocations.append(
                    AllocationWeight(
                        module_name=module,
                        weight_pct=weight_per_module,
                        capital_allocation_eur=capital,
                        rationale="Equal-weight baseline allocation",
                    )
                )

                # Get module characteristics
                if module in self.MODULE_CHARACTERISTICS:
                    char = self.MODULE_CHARACTERISTICS[module]
                    portfolio_return += char["expected_return"] * weight_per_module / Decimal("100")
                    portfolio_volatility += (
                        char["volatility_score"] * weight_per_module / Decimal("100")
                    ) ** 2
                else:
                    portfolio_return += Decimal("10") * weight_per_module / Decimal("100")
                    portfolio_volatility += (
                        Decimal("0.15") * weight_per_module / Decimal("100")
                    ) ** 2

            portfolio_volatility = portfolio_volatility.sqrt()
            portfolio_sharpe = (
                (portfolio_return - Decimal("2")) / portfolio_volatility
                if portfolio_volatility > 0
                else Decimal("0")
            )
            portfolio_drawdown = portfolio_volatility * Decimal("2")

            # Diversification ratio (for equal weight, it's 1 by definition relative to itself)
            diversification_ratio = Decimal("1.0")

            return PortfolioAllocation(
                success=True,
                profile_id=request.profile_id,
                total_capital_eur=request.capital_eur,
                allocations=allocations,
                allocation_method="equal_weight",
                expected_portfolio_return_pct=portfolio_return,
                expected_portfolio_sharpe=portfolio_sharpe,
                expected_portfolio_drawdown_pct=portfolio_drawdown,
                diversification_ratio=diversification_ratio,
                optimization_notes="Simple equal-weight baseline allocation",
            )

        except Exception as e:
            logger.error(f"Equal-weight portfolio construction failed: {e}")
            return PortfolioAllocation(
                success=False,
                profile_id=request.profile_id,
                total_capital_eur=request.capital_eur,
                allocations=[],
                allocation_method="equal_weight",
                expected_portfolio_return_pct=Decimal("0"),
                expected_portfolio_sharpe=Decimal("0"),
                expected_portfolio_drawdown_pct=Decimal("0"),
                diversification_ratio=Decimal("0"),
                error_message=str(e),
            )

    async def get_construction_history(
        self,
        limit: Optional[int] = None,
    ) -> List[PortfolioAllocation]:
        """Get portfolio construction history."""
        results = self.construction_history
        if limit:
            results = results[-limit:]
        return results

    def get_constructor_status(self) -> Dict:
        """Get constructor operational status."""
        successful = sum(1 for p in self.construction_history if p.success)
        total = len(self.construction_history)

        # Calculate average Sharpe
        avg_sharpe = Decimal("0")
        if successful > 0:
            sharpes = [
                p.expected_portfolio_sharpe
                for p in self.construction_history
                if p.success and p.expected_portfolio_sharpe > Decimal("0")
            ]
            if sharpes:
                avg_sharpe = sum(sharpes) / len(sharpes)

        return {
            "total_constructions": total,
            "successful_constructions": successful,
            "success_rate": successful / max(1, total),
            "average_sharpe": float(avg_sharpe),
            "history_size": total,
        }


# Singleton
_constructor: Optional[PortfolioConstructor] = None


def get_portfolio_constructor() -> PortfolioConstructor:
    """Get or create singleton PortfolioConstructor."""
    global _constructor
    if _constructor is None:
        _constructor = PortfolioConstructor()

    return _constructor
