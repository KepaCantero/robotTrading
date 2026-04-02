"""
Component VaR Calculator - Hull Chapter 18

Implements Component VaR (CVaR) which measures the contribution of each
position to total portfolio VaR. This is critical for:

1. Risk budgeting - allocating risk across positions
2. Position limits - setting VaR-based limits
3. Performance attribution - risk-adjusted returns by position
4. Concentration limits - identifying over-concentrated risks

Formula:
Component VaR_i = VaR_portfolio * Beta_i * w_i

Where:
- Beta_i = Covariance(r_i, r_p) / Variance(r_p)
- w_i = weight of position i in portfolio
- Sum of all Component VaRs = Portfolio VaR

Reference: Hull, Options, Futures, and Other Derivatives, Chapter 18
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from app.domain.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


class ComponentVaRCalculator:
    """
    Component VaR Calculator.

    Calculates risk contribution by position to enable risk budgeting
    and position-level risk management.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize Component VaR calculator.

        Args:
            config: Configuration dictionary
        """
        config = config or {}
        self.confidence_level = config.get("confidence_level", 0.95)
        self.logger = logging.getLogger(self.__class__.__name__)

    def calculate_component_var(
        self,
        portfolio: Portfolio,
        returns_history: dict[str, list[float]],
        portfolio_var: float,
        method: str = "parametric",
    ) -> dict[str, Any]:
        """
        Calculate Component VaR for all positions.

        Args:
            portfolio: Portfolio to analyze
            returns_history: Historical returns by symbol
            portfolio_var: Total portfolio VaR
            method: Method for beta calculation ('parametric' or 'historical')

        Returns:
            Dict with component VaR analysis
        """
        try:
            if portfolio.total_equity == 0:
                return {"error": "Portfolio value is zero"}

            # Calculate portfolio returns
            portfolio_returns = self._calculate_portfolio_returns(portfolio, returns_history)

            if len(portfolio_returns) < 30:
                return {
                    "error": f"Insufficient data: {len(portfolio_returns)} observations, need 30+"
                }

            # Calculate component VaR for each position
            components = {}
            total_component_var = 0.0

            for position in portfolio.positions:
                symbol = position.symbol

                if symbol not in returns_history:
                    continue

                # Get position returns
                position_returns = np.array(returns_history[symbol])

                # Align lengths
                min_len = min(len(portfolio_returns), len(position_returns))
                if min_len < 30:
                    continue

                portfolio_ret = portfolio_returns[:min_len]
                position_ret = position_returns[:min_len]

                # Calculate weight
                weight = float(position.market_value / portfolio.total_equity)

                # Calculate beta (systematic risk)
                beta = self._calculate_beta(position_ret, portfolio_ret)

                # Component VaR
                component_var = portfolio_var * beta * weight

                components[symbol] = {
                    "weight": weight,
                    "beta": beta,
                    "component_var": component_var,
                    "component_var_pct": 0.0,  # Will be calculated
                    "marginal_var": component_var / weight if weight > 0 else 0.0,
                    "position_value": float(position.market_value),
                }

                total_component_var += component_var

            # Calculate percentages
            if total_component_var > 0:
                for symbol in components:
                    components[symbol]["component_var_pct"] = (
                        components[symbol]["component_var"] / total_component_var * 100
                    )

            # Validation check: sum of components should equal portfolio VaR
            sum_check = total_component_var / portfolio_var if portfolio_var != 0 else 0

            return {
                "components": components,
                "total_component_var": total_component_var,
                "portfolio_var": portfolio_var,
                "sum_check": sum_check,  # Should be ~1.0
                "sum_check_pass": 0.95 <= sum_check <= 1.05,
                "method": method,
                "n_positions": len(components),
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error calculating component VaR: {e}", exc_info=True)
            return {"error": str(e)}

    def _calculate_portfolio_returns(
        self,
        portfolio: Portfolio,
        returns_history: dict[str, list[float]],
    ) -> np.ndarray:
        """Calculate portfolio returns from position returns."""
        portfolio_symbols = [pos.symbol for pos in portfolio.positions]
        available_symbols = [s for s in portfolio_symbols if s in returns_history]

        if not available_symbols:
            return np.array([])

        # Calculate weights
        weights = {}
        for position in portfolio.positions:
            if position.symbol in available_symbols:
                weights[position.symbol] = float(position.market_value / portfolio.total_equity)

        # Find minimum length
        min_len = min(len(returns_history[s]) for s in available_symbols)

        # Calculate weighted returns
        portfolio_returns = []
        for i in range(min_len):
            daily_return = sum(
                weights.get(symbol, 0) * returns_history[symbol][i] for symbol in available_symbols
            )
            portfolio_returns.append(daily_return)

        return np.array(portfolio_returns)

    def _calculate_beta(
        self,
        asset_returns: np.ndarray,
        portfolio_returns: np.ndarray,
    ) -> float:
        """
        Calculate beta (systematic risk).

        Beta = Covariance(asset, portfolio) / Variance(portfolio)

        Args:
            asset_returns: Asset returns
            portfolio_returns: Portfolio returns

        Returns:
            Beta value
        """
        try:
            # Calculate covariance and variance
            covariance = np.cov(asset_returns, portfolio_returns)[0, 1]
            variance = np.var(portfolio_returns)

            if variance == 0:
                return 0.0

            beta = covariance / variance
            return float(beta)

        except (ValueError, ZeroDivisionError):
            return 0.0

    def calculate_incremental_var(
        self,
        portfolio: Portfolio,
        returns_history: dict[str, list[float]],
        symbol_to_add: str,
        weight_to_add: float,
    ) -> dict[str, Any]:
        """
        Calculate Incremental VaR - change in portfolio VaR if we add a position.

        This helps evaluate whether a new position increases risk proportionately
        to its expected return.

        Args:
            portfolio: Current portfolio
            returns_history: Historical returns
            symbol_to_add: Symbol to add to portfolio
            weight_to_add: Weight of new position (as decimal)

        Returns:
            Dict with incremental VaR analysis
        """
        try:
            # Calculate current portfolio returns
            current_returns = self._calculate_portfolio_returns(portfolio, returns_history)

            if len(current_returns) < 30:
                return {"error": "Insufficient data for incremental VaR"}

            # Calculate current VaR (95%)
            var_current = np.percentile(current_returns, 5)

            # Calculate new portfolio returns with added position
            if symbol_to_add not in returns_history:
                return {"error": f"Symbol {symbol_to_add} not in returns history"}

            new_returns = returns_history[symbol_to_add]
            min_len = min(len(current_returns), len(new_returns))

            # New portfolio returns = current + new_position_weight * new_returns
            new_portfolio_returns = current_returns[:min_len] + weight_to_add * np.array(
                new_returns[:min_len]
            )

            # Calculate new VaR
            var_new = np.percentile(new_portfolio_returns, 5)

            # Incremental VaR
            incremental_var = var_new - var_current

            return {
                "current_var": var_current,
                "new_var": var_new,
                "incremental_var": incremental_var,
                "var_change_pct": (
                    (incremental_var / abs(var_current) * 100) if var_current != 0 else 0
                ),
                "symbol": symbol_to_add,
                "weight": weight_to_add,
                "recommendation": self._evaluate_incremental_var(incremental_var, var_current),
            }

        except (ValueError, TypeError, KeyError) as e:
            self.logger.error(f"Error calculating incremental VaR: {e}", exc_info=True)
            return {"error": str(e)}

    def _evaluate_incremental_var(
        self,
        incremental_var: float,
        current_var: float,
    ) -> str:
        """Evaluate if incremental VaR is acceptable."""
        if incremental_var > 0:
            # VaR becomes more negative (increases risk)
            increase_pct = abs(incremental_var / current_var) if current_var != 0 else 0

            if increase_pct > 0.5:  # More than 50% increase
                return "REJECT - Risk increase exceeds 50%"
            elif increase_pct > 0.2:  # More than 20% increase
                return "CAUTION - Significant risk increase"
            else:
                return "ACCEPT - Moderate risk increase"
        else:
            # VaR becomes less negative (decreases risk) - beneficial
            return "ACCEPT - Reduces portfolio risk"

    def generate_risk_budget_report(
        self,
        component_var_result: dict[str, Any],
        risk_budget: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """
        Generate risk budget report comparing actual vs target risk contributions.

        Args:
            component_var_result: Result from calculate_component_var
            risk_budget: Target risk contribution by symbol (as percentages)

        Returns:
            Risk budget analysis
        """
        if "components" not in component_var_result:
            return {"error": "Invalid component VaR result"}

        components = component_var_result["components"]

        report = {
            "positions": [],
            "budget_compliance": True,
            "total_over_budget": 0.0,
        }

        for symbol, data in components.items():
            target_pct = risk_budget.get(symbol, 0) if risk_budget else 0
            actual_pct = data["component_var_pct"]

            deviation = actual_pct - target_pct

            position_report = {
                "symbol": symbol,
                "actual_risk_pct": actual_pct,
                "target_risk_pct": target_pct,
                "deviation_pct": deviation,
                "status": "within_budget" if abs(deviation) <= 5.0 else "over_budget",
                "component_var": data["component_var"],
                "position_value": data["position_value"],
            }

            report["positions"].append(position_report)

            if abs(deviation) > 5.0:
                report["budget_compliance"] = False
                report["total_over_budget"] += abs(deviation)

        return report
