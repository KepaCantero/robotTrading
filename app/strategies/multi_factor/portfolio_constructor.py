"""
Factor Portfolio Constructor - Build Factor-Tilted Portfolios

This module implements portfolio construction using factor tilt optimization.
The goal is to build a diversified portfolio with targeted factor exposures
while controlling risk and turnover.

Key features:
- Factor tilt optimization (target specific factor exposures)
- Sector neutrality constraints
- Position size limits and diversification
- Risk-aware optimization

SOLID Principles:
- Single Responsibility: Only portfolio construction, not factor calculation
- Open/Closed: Extensible with new optimization objectives
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List

import numpy as np
from scipy.optimize import Bounds, minimize

from .factor_calculator import get_default_factor_premiums
from .factor_models import FactorModelManager
from .models import (
    FactorOptimizationResult,
    FactorPortfolio,
    FactorPosition,
    FactorProfile,
    FactorRebalanceRecommendation,
    FactorStrategyConfig,
)

logger = logging.getLogger(__name__)


class FactorPortfolioConstructor:
    """
    Construct factor-tilted portfolios using optimization.

    The optimizer aims to:
    1. Achieve target factor tilts
    2. Minimize tracking error to market (optional)
    3. Maximize diversification
    4. Respect position and sector constraints
    """

    def __init__(self, config: FactorStrategyConfig):
        """
        Initialize portfolio constructor.

        Args:
            config: Strategy configuration
        """
        self.config = config
        self.factor_manager = FactorModelManager()
        self.factor_premiums = get_default_factor_premiums()

        logger.info(
            f"FactorPortfolioConstructor initialized: "
            f"portfolio_size={config.portfolio_size}, "
            f"value_tilt={config.value_tilt}, "
            f"profitability_tilt={config.profitability_tilt}"
        )

    def construct_portfolio(
        self,
        profiles: List[FactorProfile],
        factor_scores_dict: Dict[str, Any],
        total_capital: Decimal,
    ) -> FactorPortfolio:
        """
        Construct a factor-tilted portfolio.

        Args:
            profiles: List of factor profiles (universe)
            factor_scores_dict: Factor scores for all stocks
            total_capital: Total capital to invest

        Returns:
            Constructed FactorPortfolio
        """
        logger.info(f"Constructing portfolio from {len(profiles)} stocks")

        # Filter to top stocks based on composite score
        top_stocks = self._select_top_stocks(profiles, factor_scores_dict)

        if len(top_stocks) < self.config.portfolio_size:
            logger.warning(
                f"Insufficient stocks after filtering: "
                f"{len(top_stocks)} < {self.config.portfolio_size}"
            )
            # Use what we have
            selected_stocks = top_stocks
        else:
            selected_stocks = top_stocks[: self.config.portfolio_size]

        # Calculate optimal weights
        optimization_result = self._optimize_weights(selected_stocks, factor_scores_dict)

        # Create positions
        positions = self._create_positions(
            selected_stocks, optimization_result.weights, factor_scores_dict
        )

        # Calculate portfolio metrics
        factor_exposures = self._calculate_portfolio_factor_exposures(positions, factor_scores_dict)
        sector_weights = self._calculate_sector_weights(positions)

        portfolio = FactorPortfolio(
            positions=positions,
            total_value=total_capital,
            cash=Decimal("0"),
            factor_exposures=factor_exposures,
            sector_weights=sector_weights,
            created_at=datetime.utcnow(),
        )

        # Set next rebalance date
        portfolio.rebalance_at = self._calculate_next_rebalance_date()

        logger.info(
            f"Portfolio constructed: {len(positions)} positions, "
            f"factor_exposures={factor_exposures}"
        )

        return portfolio

    def _select_top_stocks(
        self,
        profiles: List[FactorProfile],
        factor_scores_dict: Dict[str, Any],
    ) -> List[FactorProfile]:
        """
        Select top stocks based on composite factor score with sector diversification.

        Args:
            profiles: All factor profiles
            factor_scores_dict: Factor scores

        Returns:
            Sorted list of top profiles with sector diversification
        """
        scored_profiles = []

        for profile in profiles:
            if profile.symbol not in factor_scores_dict:
                continue

            factor_scores = factor_scores_dict[profile.symbol]

            # Skip if below minimum scores
            if profile.quality_score and profile.quality_score < self.config.min_quality_score:
                continue
            if (
                profile.overall_factor_score
                and profile.overall_factor_score < self.config.min_factor_score
            ):
                continue

            # Calculate weighted composite score based on tilts
            composite_score = self._calculate_composite_score(factor_scores, profile)
            scored_profiles.append((composite_score, profile))

        # Sort by composite score (descending)
        scored_profiles.sort(key=lambda x: x[0], reverse=True)

        # Select top N stocks with sector diversification
        selected_profiles = []
        sector_counts = {}  # Track stocks per sector

        # Target max stocks per sector (based on max_sector_weight)
        # If max_sector_weight is 0.25 and portfolio_size is 20, max 5 stocks per sector
        # Use * 1.5 instead of * 2 to be more conservative in stock selection
        max_stocks_per_sector = max(
            2, int(self.config.portfolio_size * float(self.config.max_sector_weight) * 1.5)
        )

        for score, profile in scored_profiles:
            sector = profile.sector or "Unknown"

            # Check if we've hit the limit for this sector
            if sector_counts.get(sector, 0) >= max_stocks_per_sector:
                continue

            selected_profiles.append(profile)
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

            # Stop when we have enough stocks
            if len(selected_profiles) >= self.config.portfolio_size * 2:
                break

        # If we don't have enough stocks, fill from remaining
        if len(selected_profiles) < self.config.portfolio_size:
            for score, profile in scored_profiles:
                if profile not in selected_profiles:
                    selected_profiles.append(profile)
                    if len(selected_profiles) >= self.config.portfolio_size * 2:
                        break

        return selected_profiles

    def _calculate_composite_score(
        self,
        factor_scores: Any,
        profile: FactorProfile,
    ) -> float:
        """
        Calculate composite score based on factor tilts.

        Args:
            factor_scores: Factor scores
            profile: Factor profile

        Returns:
            Composite score (higher is better)
        """
        score = 0.0

        # Factor tilts determine weights
        if factor_scores.value_score is not None:
            score += float(factor_scores.value_score) * float(self.config.value_tilt) * 100

        if factor_scores.profitability_score is not None:
            score += (
                float(factor_scores.profitability_score)
                * float(self.config.profitability_tilt)
                * 100
            )

        if factor_scores.momentum_score is not None:
            score += float(factor_scores.momentum_score) * float(self.config.momentum_tilt) * 100

        if factor_scores.size_score is not None:
            score += float(factor_scores.size_score) * float(self.config.size_tilt) * 100

        if factor_scores.investment_score is not None:
            score += (
                float(factor_scores.investment_score) * float(self.config.investment_tilt) * 100
            )

        # Add base quality score
        if profile.quality_score is not None:
            score += float(profile.quality_score) * 0.3

        # Add momentum score
        if factor_scores.factor_momentum_score is not None:
            score += float(factor_scores.factor_momentum_score) * 0.2

        return score

    def _optimize_weights(
        self,
        profiles: List[FactorProfile],
        factor_scores_dict: Dict[str, Any],
    ) -> FactorOptimizationResult:
        """
        Optimize portfolio weights using factor tilt optimization.

        Objective:
        - Maximize portfolio factor score
        - Minimize concentration (Herfindahl index)

        Constraints:
        - Sum of weights = 1
        - Min/max position sizes
        - Max sector weight
        - Max factor exposure

        Args:
            profiles: Selected stocks
            factor_scores_dict: Factor scores

        Returns:
            Optimization result
        """
        n = len(profiles)
        symbols = [p.symbol for p in profiles]

        # Initial weights (equal weight)
        w0 = np.ones(n) / n

        # Calculate expected returns and factor exposures
        expected_returns = np.zeros(n)
        factor_exposures_matrix = np.zeros((n, 5))  # 5 factors

        for i, profile in enumerate(profiles):
            if profile.symbol in factor_scores_dict:
                scores = factor_scores_dict[profile.symbol]

                # Expected return from factor premiums
                exp_return = 0.02  # Risk-free rate

                if scores.value_score is not None:
                    exp_return += float(scores.value_score) * self.factor_premiums["value"]
                if scores.profitability_score is not None:
                    exp_return += (
                        float(scores.profitability_score) * self.factor_premiums["profitability"]
                    )
                if scores.momentum_score is not None:
                    exp_return += float(scores.momentum_score) * self.factor_premiums["momentum"]

                expected_returns[i] = exp_return

                # Factor exposures
                factor_exposures_matrix[i, 0] = float(scores.value_score or 0)
                factor_exposures_matrix[i, 1] = float(scores.size_score or 0)
                factor_exposures_matrix[i, 2] = float(scores.profitability_score or 0)
                factor_exposures_matrix[i, 3] = float(scores.investment_score or 0)
                factor_exposures_matrix[i, 4] = float(scores.momentum_score or 0)

        # Objective function: maximize return - lambda * concentration
        def objective(w):
            # Expected return
            portfolio_return = w @ expected_returns

            # Concentration penalty (Herfindahl index)
            concentration = np.sum(w**2)

            return -(portfolio_return - 0.5 * concentration)

        # Constraints
        constraints = []

        # Sum of weights = 1
        constraints.append(
            {
                "type": "eq",
                "fun": lambda w: np.sum(w) - 1.0,
            }
        )

        # Max sector weight (soft constraint via penalty)
        sectors = [p.sector or "Unknown" for p in profiles]
        unique_sectors = list(set(sectors))

        def sector_constraint(w, sector):
            sector_mask = np.array([s == sector for s in sectors])
            return np.sum(w[sector_mask]) - float(self.config.max_sector_weight)

        for sector in unique_sectors:
            constraints.append(
                {
                    "type": "ineq",
                    "fun": lambda w, s=sector: -sector_constraint(w, s),
                }
            )

        # Bounds for each weight
        bounds = Bounds(
            lb=float(self.config.min_position),
            ub=float(self.config.max_single_position),
        )

        # Optimize
        result = minimize(
            objective,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-9},
        )

        if not result.success:
            logger.warning(f"Optimization failed: {result.message}")
            # Fall back to equal weight with sector constraints
            weights = self._apply_sector_constraints(w0, sectors)
            status = "suboptimal"
        else:
            weights = result.x
            # Ensure weights respect sector constraints even after optimization
            weights = self._apply_sector_constraints(weights, sectors)
            status = "optimal"

        # Ensure weights are non-negative and sum to 1
        # Note: _apply_sector_constraints already normalizes, so just ensure non-negative
        weights = np.maximum(weights, 0)
        total_weight = np.sum(weights)
        if total_weight > 0:
            weights = weights / total_weight

        # Final check: re-apply sector constraints after normalization to ensure they're still respected
        weights = self._apply_sector_constraints(weights, sectors)

        # Enforce both sector and position constraints iteratively
        max_iterations = 50
        max_single_pos = float(self.config.max_single_position)

        for iteration in range(max_iterations):
            max_violation = 0.0
            adjusted = False

            # Check position size constraints
            for i in range(len(weights)):
                if weights[i] > max_single_pos:
                    violation = weights[i] - max_single_pos
                    max_violation = max(max_violation, violation)

                    # Cap this position
                    excess = weights[i] - max_single_pos
                    weights[i] = max_single_pos

                    # Redistribute excess to other stocks
                    other_mask = np.ones(len(weights), dtype=bool)
                    other_mask[i] = False
                    other_weights = weights[other_mask]
                    other_total = np.sum(other_weights)

                    if other_total > 0:
                        # Redistribute proportionally
                        weights[other_mask] += other_weights * (excess / other_total)

                    adjusted = True

            # Re-apply sector constraints after position adjustments
            if adjusted:
                weights = self._apply_sector_constraints(weights, sectors)

            # Normalize
            weights = np.maximum(weights, 0)
            total_weight = np.sum(weights)
            if total_weight > 0:
                weights = weights / total_weight

            # Check if converged
            if max_violation < 1e-6:
                break

        # If still violating position constraints, apply hard cap
        # This may result in weights summing to less than 1.0, which is acceptable
        max_weight = np.max(weights)
        if max_weight > max_single_pos:
            logger.warning(
                f"Could not satisfy both position and sector constraints. "
                f"Applying hard cap on positions: max_weight={max_weight:.4f} > {max_single_pos}"
            )
            for i in range(len(weights)):
                if weights[i] > max_single_pos:
                    weights[i] = max_single_pos

            # Do NOT renormalize - accept that weights may sum to less than 1.0
            # The remaining cash will be held as cash
            weights = np.maximum(weights, 0)

        # Calculate portfolio metrics
        portfolio_return = weights @ expected_returns

        # Calculate portfolio risk (simplified - use weighted average of factor exposures)
        # For proper risk, would need covariance matrix of factor returns
        portfolio_risk = np.sqrt(np.sum(weights**2)) * 0.15  # Assume 15% vol

        # Calculate factor exposures
        portfolio_factor_exposures = {
            "value": float(weights @ factor_exposures_matrix[:, 0]),
            "size": float(weights @ factor_exposures_matrix[:, 1]),
            "profitability": float(weights @ factor_exposures_matrix[:, 2]),
            "investment": float(weights @ factor_exposures_matrix[:, 3]),
            "momentum": float(weights @ factor_exposures_matrix[:, 4]),
        }

        # Create weights dictionary
        weights_dict = {
            symbol: Decimal(str(round(w, 4)))
            for symbol, w in zip(symbols, weights)
            if w > 0.001  # Only include meaningful positions
        }

        return FactorOptimizationResult(
            weights=weights_dict,
            expected_return=Decimal(str(portfolio_return)),
            expected_risk=Decimal(str(portfolio_risk)),
            factor_exposures=portfolio_factor_exposures,
            optimization_status=status,
            iterations=result.nit if hasattr(result, "nit") else 0,
            objective_value=Decimal(str(-result.fun)),
        )

    def _create_positions(
        self,
        profiles: List[FactorProfile],
        weights: Dict[str, Decimal],
        factor_scores_dict: Dict[str, Any],
    ) -> List[FactorPosition]:
        """Create portfolio positions from weights."""
        positions = []

        for profile in profiles:
            if profile.symbol not in weights:
                continue

            weight = weights[profile.symbol]

            # Calculate factor exposures for this position
            if profile.symbol in factor_scores_dict:
                scores = factor_scores_dict[profile.symbol]
                factor_exposure = {
                    "value": float(scores.value_score or 0),
                    "size": float(scores.size_score or 0),
                    "profitability": float(scores.profitability_score or 0),
                    "investment": float(scores.investment_score or 0),
                    "momentum": float(scores.momentum_score or 0),
                }

                # Calculate expected return
                exp_return = 0.02  # Risk-free
                exp_return += factor_exposure["value"] * self.factor_premiums["value"]
                exp_return += (
                    factor_exposure["profitability"] * self.factor_premiums["profitability"]
                )
                exp_return += factor_exposure["momentum"] * self.factor_premiums["momentum"]
            else:
                factor_exposure = {}
                exp_return = None

            position = FactorPosition(
                symbol=profile.symbol,
                weight=weight,
                factor_exposure=factor_exposure,
                expected_return=Decimal(str(exp_return)) if exp_return else None,
                sector=profile.sector,
            )

            positions.append(position)

        return positions

    def _calculate_portfolio_factor_exposures(
        self,
        positions: List[FactorPosition],
        factor_scores_dict: Dict[str, Any],
    ) -> Dict[str, Decimal]:
        """Calculate portfolio-level factor exposures."""
        portfolio_exposures = {
            "value": Decimal("0"),
            "size": Decimal("0"),
            "profitability": Decimal("0"),
            "investment": Decimal("0"),
            "momentum": Decimal("0"),
        }

        total_weight = sum(pos.weight for pos in positions)

        if total_weight == 0:
            return portfolio_exposures

        for pos in positions:
            for factor in portfolio_exposures:
                exposure = pos.factor_exposure.get(factor, 0)
                weighted_exposure = Decimal(str(exposure)) * pos.weight / total_weight
                portfolio_exposures[factor] += weighted_exposure

        return portfolio_exposures

    def _calculate_sector_weights(self, positions: List[FactorPosition]) -> Dict[str, Decimal]:
        """
        Calculate sector weights as percentage of total portfolio weight.

        Sector weights are normalized to sum to 1.0 for reporting purposes.
        """
        sector_weights = {}
        total_weight = sum(pos.weight for pos in positions)

        for pos in positions:
            sector = pos.sector or "Unknown"
            if sector not in sector_weights:
                sector_weights[sector] = Decimal("0")
            sector_weights[sector] += (
                pos.weight / total_weight if total_weight > 0 else Decimal("0")
            )

        return sector_weights

    def _calculate_next_rebalance_date(self) -> datetime:
        """Calculate next rebalance date based on frequency."""
        now = datetime.utcnow()

        if self.config.rebalance_frequency == "monthly":
            next_date = now + timedelta(days=30)
        elif self.config.rebalance_frequency == "quarterly":
            next_date = now + timedelta(days=90)
        elif self.config.rebalance_frequency == "semi_annual":
            next_date = now + timedelta(days=180)
        else:  # annual
            next_date = now + timedelta(days=365)

        return next_date

    def _apply_sector_constraints(
        self,
        weights: np.ndarray,
        sectors: List[str],
    ) -> np.ndarray:
        """
        Apply sector weight constraints to portfolio weights.

        This ensures no single sector exceeds the maximum sector weight
        by redistributing excess weight proportionally to other sectors.

        Args:
            weights: Current portfolio weights
            sectors: List of sectors for each stock

        Returns:
            Adjusted weights attempting to respect sector constraints
        """
        adjusted_weights = weights.copy()
        unique_sectors = list(set(sectors))
        max_sector_weight = float(self.config.max_sector_weight)

        # Check if it's mathematically possible to satisfy all constraints
        # If n_sectors * max_sector_weight < 1.0, we must allow some overage
        min_max_sector = 1.0 / len(unique_sectors)
        effective_max = max(max_sector_weight, min_max_sector)

        if effective_max > max_sector_weight:
            logger.debug(
                f"Cannot satisfy all sector constraints: {len(unique_sectors)} sectors * {max_sector_weight} < 1.0. "
                f"Using effective max_sector_weight={effective_max:.4f}"
            )

        # Iterate to satisfy sector constraints
        max_iterations = 100
        for iteration in range(max_iterations):
            max_violation = 0.0

            # Check each sector and cap if needed
            for sector in unique_sectors:
                sector_mask = np.array([s == sector for s in sectors])
                sector_total = np.sum(adjusted_weights[sector_mask])

                if sector_total > effective_max:
                    violation = sector_total - effective_max
                    max_violation = max(max_violation, violation)

                    # Calculate excess weight
                    excess = sector_total - effective_max

                    # Scale down this sector to effective max
                    if sector_total > 0:
                        scale_factor = effective_max / sector_total
                        adjusted_weights[sector_mask] *= scale_factor

                    # Redistribute excess to stocks in other sectors
                    other_sectors_info = []
                    for other_sector in unique_sectors:
                        if other_sector == sector:
                            continue
                        other_sector_mask = np.array([s == other_sector for s in sectors])
                        other_sector_total = np.sum(adjusted_weights[other_sector_mask])
                        other_sectors_info.append(
                            (other_sector, other_sector_mask, other_sector_total)
                        )

                    if other_sectors_info:
                        # Count total stocks in other sectors
                        total_other_stocks = sum(np.sum(mask) for _, mask, _ in other_sectors_info)

                        if total_other_stocks > 0:
                            # Distribute excess equally to all stocks in other sectors
                            per_stock_allocation = excess / total_other_stocks
                            for (
                                other_sector,
                                other_sector_mask,
                                other_sector_total,
                            ) in other_sectors_info:
                                adjusted_weights[other_sector_mask] += per_stock_allocation

            # Ensure all weights are non-negative
            adjusted_weights = np.maximum(adjusted_weights, 0)

            # Renormalize to maintain sum = 1
            total_weight = np.sum(adjusted_weights)
            if total_weight > 0:
                adjusted_weights = adjusted_weights / total_weight

            # Check if all constraints are satisfied
            if max_violation < 1e-6:
                break

        return adjusted_weights

    def rebalance(
        self,
        current_portfolio: FactorPortfolio,
        profiles: List[FactorProfile],
        factor_scores_dict: Dict[str, Any],
        total_capital: Decimal,
    ) -> FactorPortfolio:
        """
        Rebalance existing portfolio.

        Args:
            current_portfolio: Current portfolio
            profiles: Updated universe
            factor_scores_dict: Updated factor scores
            total_capital: Current total capital

        Returns:
            Rebalanced portfolio
        """
        logger.info("Rebalancing portfolio")

        # Check if rebalance is needed
        recommendation = self.analyze_drift(current_portfolio, factor_scores_dict)

        if not recommendation.needs_rebalance:
            logger.info("No rebalance needed")
            return current_portfolio

        # Construct new portfolio
        new_portfolio = self.construct_portfolio(profiles, factor_scores_dict, total_capital)

        logger.info(
            f"Portfolio rebalanced: {len(new_portfolio.positions)} positions, "
            f"expected_cost={recommendation.estimated_cost}"
        )

        return new_portfolio

    def analyze_drift(
        self,
        portfolio: FactorPortfolio,
        factor_scores_dict: Dict[str, Any],
    ) -> FactorRebalanceRecommendation:
        """
        Analyze portfolio drift and recommend rebalancing.

        Args:
            portfolio: Current portfolio
            factor_scores_dict: Current factor scores

        Returns:
            Rebalancing recommendation
        """
        needs_rebalance = False
        reasons = []

        # Check if rebalance date has passed
        if portfolio.rebalance_at and datetime.utcnow() >= portfolio.rebalance_at:
            needs_rebalance = True
            reasons.append("Scheduled rebalance date reached")

        # Check position drift
        current_weights = {pos.symbol: pos.weight for pos in portfolio.positions}

        # Calculate target weights (re-optimize)
        # This is simplified - in practice would re-run optimization
        target_weights = current_weights.copy()  # Placeholder

        # Check if any position deviated significantly
        for symbol, current_weight in current_weights.items():
            target_weight = target_weights.get(symbol, current_weight)
            if abs(current_weight - target_weight) > self.config.rebalance_threshold:
                needs_rebalance = True
                reasons.append(
                    f"Position drift: {symbol} deviated by {abs(current_weight - target_weight):.1%}"
                )

        # Check factor drift
        target_exposures = portfolio.factor_exposures
        for factor, target_exp in target_exposures.items():
            # Simplified: assume target hasn't changed
            if abs(float(target_exp)) > float(self.config.max_factor_exposure):
                needs_rebalance = True
                reasons.append(f"Factor exposure exceeded: {factor}")

        # Calculate trades
        trades_required = []
        for symbol in set(list(current_weights.keys()) + list(target_weights.keys())):
            current = current_weights.get(symbol, Decimal("0"))
            target = target_weights.get(symbol, Decimal("0"))
            if current != target:
                trades_required.append((symbol, current, target))

        # Estimate cost (simplified: 10 bps per trade)
        estimated_cost = Decimal(str(len(trades_required) * 0.001))

        # Estimate benefit (simplified: potential return improvement)
        estimated_benefit = Decimal("0.01")  # 1% annual improvement

        recommendation = FactorRebalanceRecommendation(
            needs_rebalance=needs_rebalance,
            reason="; ".join(reasons) if reasons else "No rebalance needed",
            current_weights=current_weights,
            target_weights=target_weights,
            trades_required=trades_required,
            estimated_cost=estimated_cost,
            expected_benefit=estimated_benefit,
        )

        return recommendation

    def get_portfolio_metrics(
        self,
        portfolio: FactorPortfolio,
    ) -> Dict[str, Any]:
        """
        Get comprehensive portfolio metrics.

        Args:
            portfolio: Factor portfolio

        Returns:
            Dictionary of metrics
        """
        metrics = {
            "total_value": float(portfolio.total_value),
            "cash": float(portfolio.cash),
            "invested_capital": float(portfolio.invested_capital),
            "positions_count": portfolio.positions_count,
            "is_diversified": portfolio.is_diversified,
            "max_position_weight": float(portfolio.max_position_weight),
            "herfindahl_index": float(portfolio.herfindahl_index),
            "factor_exposures": {k: float(v) for k, v in portfolio.factor_exposures.items()},
            "sector_weights": {k: float(v) for k, v in portfolio.sector_weights.items()},
            "created_at": portfolio.created_at.isoformat(),
            "rebalance_at": portfolio.rebalance_at.isoformat() if portfolio.rebalance_at else None,
        }

        # Calculate expected return
        if portfolio.positions:
            weighted_return = Decimal("0")
            total_weight = Decimal("0")

            for pos in portfolio.positions:
                if pos.expected_return is not None:
                    weighted_return += pos.expected_return * pos.weight
                    total_weight += pos.weight

            if total_weight > 0:
                metrics["expected_annual_return"] = float(weighted_return / total_weight)

        return metrics
