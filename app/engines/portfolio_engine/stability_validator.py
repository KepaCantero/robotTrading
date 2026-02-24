"""
Portfolio Stability Validation Module

Implements López de Prado's portfolio stability validation methodologies
for the portfolio engine. Provides comprehensive stability analysis across
time periods, market regimes, and rebalancing events.

Key Features:
- Time-period stability validation
- Cross-regime stability analysis
- Turnover optimization
- Allocation drift monitoring
- Stability-based portfolio selection

Reference:
    López de Prado, M. (2020). Machine Learning for Asset Managers.
    Chapters 9-11: Portfolio Stability, Turnover, Concentration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import numpy as np

from app.shared.config.centralized_config import get_config

if TYPE_CHECKING:
    from app.backtesting.lopez_de_prado_metrics import PortfolioStabilityMetrics

from app.backtesting.lopez_de_prado_metrics import (
    ConcentrationAnalyzer,
    PortfolioStabilityValidator as LopeDePradoStabilityValidator,
    SharpeRatioCombinator,
    TurnoverAdjustedCalculator,
)

logger = logging.getLogger(__name__)


@dataclass
class StabilityValidationConfig:
    """Configuration for stability validation."""

    # Stability thresholds
    min_stability_score: float = 70.0  # Minimum stability score (0-100)
    max_turnover_annual: float = 0.5  # Maximum annual turnover (50%)
    max_allocation_drift: float = 0.2  # Maximum allocation drift (20%)

    # Time periods
    rebalancing_frequency_days: int = 30  # Rebalancing frequency
    min_historical_periods: int = 6  # Minimum periods for validation

    # Concentration limits
    max_single_position_weight: float = 0.3  # 30% max single position
    max_hhi: float = 0.2  # Herfindahl-Hirschman Index threshold

    # Cost parameters
    transaction_cost_bps: float = 10.0  # 10 bps per trade
    risk_free_rate: float = float(get_config().backtesting.default_risk_free_rate)  # Annual risk-free rate from config

    # Validation flags
    require_stable_for_production: bool = True
    log_warnings: bool = True


@dataclass
class PortfolioValidationResult:
    """Result of portfolio stability validation."""

    is_valid: bool
    is_stable: bool
    is_cost_effective: bool
    is_properly_diversified: bool

    stability_score: float
    stability_metrics: Optional[PortfolioStabilityMetrics] = None

    sharpe_adjusted: Optional[float] = None
    sharpe_raw: Optional[float] = None

    concentration_score: float = 0.0
    concentration_risk: str = "UNKNOWN"  # LOW, MEDIUM, HIGH, CRITICAL

    annual_turnover: float = 0.0
    estimated_costs: float = 0.0

    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    validation_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_valid": self.is_valid,
            "is_stable": self.is_stable,
            "is_cost_effective": self.is_cost_effective,
            "is_properly_diversified": self.is_properly_diversified,
            "stability_score": self.stability_score,
            "stability_metrics": (
                self.stability_metrics.to_dict() if self.stability_metrics else None
            ),
            "sharpe_adjusted": self.sharpe_adjusted,
            "sharpe_raw": self.sharpe_raw,
            "concentration_score": self.concentration_score,
            "concentration_risk": self.concentration_risk,
            "annual_turnover": self.annual_turnover,
            "estimated_costs": self.estimated_costs,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "validation_timestamp": self.validation_timestamp.isoformat(),
        }


class PortfolioStabilityValidator:
    """
    Comprehensive portfolio stability validation engine.

    Implements López de Prado's stability validation methodologies:
    - Cross-period stability analysis
    - Turnover-adjusted performance metrics
    - Concentration risk assessment
    - Sharpe ratio combination validation
    """

    def __init__(
        self,
        config: Optional[StabilityValidationConfig] = None,
    ):
        """
        Initialize portfolio stability validator.

        Args:
            config: Validation configuration
        """
        self.config = config or StabilityValidationConfig()

        # Initialize López de Prado metrics components
        self.sharpe_combiner = SharpeRatioCombinator(
            risk_free_rate=self.config.risk_free_rate,
        )
        self.stability_validator = LopeDePradoStabilityValidator(
            stability_threshold=self.config.min_stability_score,
            max_turnover_threshold=self.config.max_turnover_annual,
        )
        self.turnover_calculator = TurnoverAdjustedCalculator(
            transaction_cost_bps=self.config.transaction_cost_bps,
            risk_free_rate=self.config.risk_free_rate,
        )
        self.concentration_analyzer = ConcentrationAnalyzer(
            max_concentration_threshold=self.config.max_single_position_weight,
            hhi_threshold=self.config.max_hhi,
        )

        # Historical tracking
        self.validation_history: List[PortfolioValidationResult] = []

        logger.info("PortfolioStabilityValidator initialized")

    def validate_portfolio_allocation(
        self,
        weights: np.ndarray,
        weights_history: List[np.ndarray],
        returns_history: Optional[np.ndarray] = None,
        expected_returns: Optional[np.ndarray] = None,
    ) -> PortfolioValidationResult:
        """
        Validate a portfolio allocation for stability and cost-effectiveness.

        Args:
            weights: Current portfolio weights
            weights_history: Historical weights for stability analysis
            returns_history: Historical returns for Sharpe calculation
            expected_returns: Expected returns for forward-looking analysis

        Returns:
            PortfolioValidationResult with comprehensive validation
        """
        warnings = []
        recommendations = []

        # Initialize result
        result = PortfolioValidationResult(
            is_valid=False,
            is_stable=False,
            is_cost_effective=False,
            is_properly_diversified=False,
            stability_score=0.0,
            concentration_score=0.0,
            annual_turnover=0.0,
            estimated_costs=0.0,
            warnings=warnings,
            recommendations=recommendations,
        )

        try:
            # Step 1: Validate stability across time periods
            if len(weights_history) >= self.config.min_historical_periods:
                stability_metrics = self.stability_validator.validate_stability(
                    weights_history=weights_history,
                    period_length_days=self.config.rebalancing_frequency_days,
                )
                result.stability_metrics = stability_metrics
                result.stability_score = stability_metrics.stability_score
                result.is_stable = stability_metrics.is_stable

                if not stability_metrics.is_stable:
                    warnings.append(
                        f"Portfolio stability score ({stability_metrics.stability_score:.1f}) "
                        f"below threshold ({self.config.min_stability_score})"
                    )
                    recommendations.append(
                        "Reduce parameter complexity or increase rebalancing frequency"
                    )
            else:
                warnings.append(
                    f"Insufficient historical periods ({len(weights_history)}) "
                    f"for stability validation (minimum: {self.config.min_historical_periods})"
                )
                result.is_stable = None  # Unknown

            # Step 2: Validate cost-effectiveness
            if returns_history is not None and len(returns_history) > 0:
                turnover_metrics = self.turnover_calculator.calculate_turnover_adjusted_sharpe(
                    returns=returns_history,
                    weights_history=weights_history,
                    period_length_days=self.config.rebalancing_frequency_days,
                )

                result.sharpe_raw = turnover_metrics.raw_sharpe
                result.sharpe_adjusted = turnover_metrics.turnover_adjusted_sharpe
                result.annual_turnover = turnover_metrics.annualized_turnover
                result.estimated_costs = turnover_metrics.estimated_transaction_costs
                result.is_cost_effective = turnover_metrics.is_cost_effective

                if not turnover_metrics.is_cost_effective:
                    warnings.append(
                        f"Portfolio not cost-effective: "
                        f"Sharpe degrades from {turnover_metrics.raw_sharpe:.2f} to "
                        f"{turnover_metrics.net_sharpe:.2f} after transaction costs"
                    )
                    recommendations.append("Reduce turnover frequency or increase position sizes")

            # Step 3: Validate concentration
            concentration_metrics = self.concentration_analyzer.analyze_concentration(
                weights=weights,
            )

            result.concentration_score = concentration_metrics.concentration_score
            result.is_properly_diversified = not concentration_metrics.is_overconcentrated

            if concentration_metrics.is_overconcentrated:
                # Determine risk level
                if concentration_metrics.max_weight > 0.5:
                    result.concentration_risk = "CRITICAL"
                    warnings.append(
                        f"CRITICAL: Single position weight ({concentration_metrics.max_weight:.1%}) "
                        "exceeds 50% threshold"
                    )
                elif concentration_metrics.max_weight > self.config.max_single_position_weight:
                    result.concentration_risk = "HIGH"
                    warnings.append(
                        f"HIGH: Single position weight ({concentration_metrics.max_weight:.1%}) "
                        f"exceeds threshold ({self.config.max_single_position_weight:.1%})"
                    )
                else:
                    result.concentration_risk = "MEDIUM"

                recommendations.append(
                    f"Reduce concentration: Effective N assets = {concentration_metrics.effective_n_assets:.1f}. "
                    f"Aim for at least {10 - int(concentration_metrics.effective_n_assets)} more assets."
                )
            else:
                result.concentration_risk = "LOW"

            # Step 4: Combine into overall validation
            result.is_valid = self._determine_validity(result)

            # Log warnings if configured
            if self.config.log_warnings and warnings:
                for warning in warnings:
                    logger.warning(f"Portfolio validation warning: {warning}")

            # Store in history
            self.validation_history.append(result)

            return result

        except Exception as e:
            logger.error(f"Error validating portfolio allocation: {e}", exc_info=True)
            warnings.append(f"Validation error: {str(e)}")
            result.warnings = warnings
            return result

    def _determine_validity(self, result: PortfolioValidationResult) -> bool:
        """
        Determine overall portfolio validity.

        A portfolio is valid if it meets all required criteria.
        """
        # If we couldn't assess stability, be conservative
        if result.is_stable is False:
            return False

        # Must be cost-effective
        if result.is_cost_effective is False:
            return False

        # Must be properly diversified
        if result.is_properly_diversified is False:
            return False

        # If production deployment required, stability must be confirmed
        if self.config.require_stable_for_production and result.is_stable is not True:
            return False

        return True

    def compare_portfolio_stabilities(
        self,
        portfolios: Dict[str, List[np.ndarray]],
        returns: Optional[Dict[str, np.ndarray]] = None,
    ) -> Dict[str, PortfolioValidationResult]:
        """
        Compare stability of multiple portfolios.

        Args:
            portfolios: Dictionary mapping portfolio names to weight histories
            returns: Optional dictionary of returns for each portfolio

        Returns:
            Dictionary mapping names to validation results
        """
        results = {}

        for name, weights_history in portfolios.items():
            current_weights = weights_history[-1]
            portfolio_returns = returns.get(name) if returns else None

            results[name] = self.validate_portfolio_allocation(
                weights=current_weights,
                weights_history=weights_history,
                returns_history=portfolio_returns,
            )

        # Rank by stability score
        ranked = sorted(
            results.items(),
            key=lambda x: x[1].stability_score,
            reverse=True,
        )

        logger.info("Portfolio stability ranking:")
        for rank, (name, result) in enumerate(ranked, 1):
            logger.info(
                f"{rank}. {name}: "
                f"Stability={result.stability_score:.1f}, "
                f"Valid={result.is_valid}, "
                f"Cost-Effective={result.is_cost_effective}"
            )

        return results

    def get_stability_recommendations(
        self,
        result: PortfolioValidationResult,
    ) -> List[str]:
        """
        Get actionable recommendations to improve portfolio stability.

        Args:
            result: Validation result

        Returns:
            List of recommendations
        """
        recommendations = []

        # Stability recommendations
        if result.stability_metrics:
            sm = result.stability_metrics

            if sm.turnover_mean > self.config.max_turnover_annual:
                recommendations.append(
                    f"Reduce turnover: Current {sm.turnover_mean:.1%} annual turnover "
                    f"exceeds threshold {self.config.max_turnover_annual:.1%}. "
                    "Consider longer holding periods or fewer rebalances."
                )

            if sm.weights_autocorrelation < 0.5:
                recommendations.append(
                    f"Low weight autocorrelation ({sm.weights_autocorrelation:.2f}) "
                    "suggests inconsistent allocations. Review strategy logic."
                )

            if sm.allocation_drift_max > self.config.max_allocation_drift:
                recommendations.append(
                    f"High allocation drift ({sm.allocation_drift_max:.1%}) detected. "
                    "Implement drift control or more frequent rebalancing."
                )

        # Concentration recommendations
        if result.concentration_score > 30:
            recommendations.append(
                f"High concentration score ({result.concentration_score:.1f}). "
                "Add more uncorrelated assets to improve diversification."
            )

        # Cost recommendations
        if result.estimated_costs > 0.02:  # 2% annual cost
            recommendations.append(
                f"High transaction costs ({result.estimated_costs:.1%} annually). "
                "Reduce turnover or negotiate lower commission rates."
            )

        # Sharpe degradation recommendations
        if result.sharpe_adjusted and result.sharpe_raw:
            degradation = (result.sharpe_raw - result.sharpe_adjusted) / result.sharpe_raw
            if degradation > 0.2:  # More than 20% degradation
                recommendations.append(
                    f"Sharpe ratio degrades {degradation:.1%} after turnover adjustment. "
                    "Optimize execution to reduce market impact."
                )

        return recommendations

    def save_validation_report(
        self,
        filepath: Path,
        result: PortfolioValidationResult,
    ) -> None:
        """
        Save validation report to file.

        Args:
            filepath: Path to save report
            result: Validation result to save
        """
        import json

        filepath.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "validation_config": {
                "min_stability_score": self.config.min_stability_score,
                "max_turnover_annual": self.config.max_turnover_annual,
                "max_allocation_drift": self.config.max_allocation_drift,
                "rebalancing_frequency_days": self.config.rebalancing_frequency_days,
                "transaction_cost_bps": self.config.transaction_cost_bps,
            },
            "validation_result": result.to_dict(),
            "recommendations": self.get_stability_recommendations(result),
        }

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Validation report saved to {filepath}")


class StabilityBasedPortfolioSelector:
    """
    Selects the most stable portfolio from multiple candidates.

    From López de Prado: When multiple strategies exist, prefer the most stable
    one over the highest return, as stability indicates robustness and lower
    overfitting risk.
    """

    def __init__(
        self,
        validator: PortfolioStabilityValidator,
        min_stability_score: float = 70.0,
    ):
        """
        Initialize stability-based selector.

        Args:
            validator: Portfolio stability validator
            min_stability_score: Minimum stability score for consideration
        """
        self.validator = validator
        self.min_stability_score = min_stability_score

    def select_most_stable_portfolio(
        self,
        portfolios: Dict[str, List[np.ndarray]],
        returns: Optional[Dict[str, np.ndarray]] = None,
        require_cost_effective: bool = True,
    ) -> Tuple[str, PortfolioValidationResult]:
        """
        Select the most stable portfolio from candidates.

        Args:
            portfolios: Dictionary mapping names to weight histories
            returns: Optional returns for each portfolio
            require_cost_effective: Whether to require cost-effectiveness

        Returns:
            Tuple of (selected_portfolio_name, validation_result)
        """
        # Validate all portfolios
        validation_results = self.validator.compare_portfolio_stabilities(
            portfolios=portfolios,
            returns=returns,
        )

        # Filter by minimum stability
        candidates = {
            name: result
            for name, result in validation_results.items()
            if result.stability_score >= self.min_stability_score
        }

        if not candidates:
            logger.warning(
                f"No portfolios meet minimum stability score {self.min_stability_score}. "
                "Returning highest-scoring portfolio."
            )
            candidates = validation_results

        # Filter by cost-effectiveness if required
        if require_cost_effective:
            cost_effective = {
                name: result
                for name, result in candidates.items()
                if result.is_cost_effective is not False
            }

            if cost_effective:
                candidates = cost_effective

        # Select highest stability score
        selected = max(
            candidates.items(),
            key=lambda x: x[1].stability_score,
        )

        name, result = selected

        logger.info(
            f"Selected portfolio '{name}' with stability score {result.stability_score:.1f}"
        )

        return name, result

    def rank_portfolios_by_stability(
        self,
        portfolios: Dict[str, List[np.ndarray]],
        returns: Optional[Dict[str, np.ndarray]] = None,
    ) -> List[Tuple[str, PortfolioValidationResult]]:
        """
        Rank portfolios by stability score.

        Args:
            portfolios: Dictionary mapping names to weight histories
            returns: Optional returns for each portfolio

        Returns:
            List of (name, result) tuples sorted by stability (highest first)
        """
        validation_results = self.validator.compare_portfolio_stabilities(
            portfolios=portfolios,
            returns=returns,
        )

        ranked = sorted(
            validation_results.items(),
            key=lambda x: x[1].stability_score,
            reverse=True,
        )

        return ranked


# Convenience functions
def create_portfolio_stability_validator(
    min_stability_score: float = 70.0,
    transaction_cost_bps: float = 10.0,
    risk_free_rate: float = None,
) -> PortfolioStabilityValidator:
    """
    Create a portfolio stability validator with default configuration.

    Args:
        min_stability_score: Minimum stability score (0-100)
        transaction_cost_bps: Transaction cost in basis points
        risk_free_rate: Annual risk-free rate (default: from CentralizedConfig)

    Returns:
        Configured PortfolioStabilityValidator
    """
    rf = risk_free_rate if risk_free_rate is not None else float(get_config().backtesting.default_risk_free_rate)
    config = StabilityValidationConfig(
        min_stability_score=min_stability_score,
        transaction_cost_bps=transaction_cost_bps,
        risk_free_rate=rf,
    )

    return PortfolioStabilityValidator(config=config)


def validate_single_portfolio(
    weights: np.ndarray,
    weights_history: List[np.ndarray],
    returns: Optional[np.ndarray] = None,
    **kwargs,
) -> PortfolioValidationResult:
    """
    Validate a single portfolio for stability.

    Convenience function for quick validation.

    Args:
        weights: Current portfolio weights
        weights_history: Historical weights
        returns: Historical returns (optional)
        **kwargs: Additional configuration parameters

    Returns:
        PortfolioValidationResult
    """
    validator = create_portfolio_stability_validator(**kwargs)

    return validator.validate_portfolio_allocation(
        weights=weights,
        weights_history=weights_history,
        returns_history=returns,
    )
