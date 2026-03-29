"""
Portfolio Variance Stress Testing - Hull Chapter 20

Implements comprehensive portfolio variance stress testing to understand
how portfolio risk changes under extreme market conditions.

Key features:
1. Variance decomposition by risk factor
2. Stress scenarios for correlation breakdown
3. Volatility spike scenarios
4. Concentration stress testing
5. Leverage stress scenarios
6. Multi-dimensional stress analysis

Reference: Hull, Options, Futures, and Other Derivatives, Chapter 20
"""

import logging
from typing import Any, Optional

import numpy as np

from app.domain.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


class PortfolioVarianceStressTester:
    """
    Portfolio Variance Stress Tester.

    Tests how portfolio variance changes under various stress scenarios.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize portfolio variance stress tester.

        Args:
            config: Configuration dictionary
        """
        config = config or {}
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Stress scenarios
        self.scenarios = self._initialize_scenarios()

    def _initialize_scenarios(self) -> dict[str, dict[str, Any]]:
        """Initialize comprehensive stress scenarios."""
        return {
            "baseline": {
                "name": "Baseline (Current Market)",
                "description": "Current market conditions",
                "volatility_multiplier": 1.0,
                "correlation_multiplier": 1.0,
                "volatility_floor": 0.0,
                "correlation_target": None,
            },
            "volatility_spike_2x": {
                "name": "Volatility Spike (2x)",
                "description": "All volatilities double",
                "volatility_multiplier": 2.0,
                "correlation_multiplier": 1.0,
                "volatility_floor": 0.0,
                "correlation_target": None,
            },
            "volatility_spike_3x": {
                "name": "Volatility Spike (3x)",
                "description": "All volatilities triple",
                "volatility_multiplier": 3.0,
                "correlation_multiplier": 1.0,
                "volatility_floor": 0.0,
                "correlation_target": None,
            },
            "correlation_breakdown_80": {
                "name": "Correlation Breakdown to 0.8",
                "description": "All correlations move to 0.8",
                "volatility_multiplier": 1.0,
                "correlation_multiplier": 0.0,  # Not used
                "volatility_floor": 0.0,
                "correlation_target": 0.8,
            },
            "correlation_breakdown_90": {
                "name": "Correlation Breakdown to 0.9",
                "description": "All correlations move to 0.9",
                "volatility_multiplier": 1.0,
                "correlation_multiplier": 0.0,
                "volatility_floor": 0.0,
                "correlation_target": 0.9,
            },
            "correlation_breakdown_perfect": {
                "name": "Perfect Correlation (1.0)",
                "description": "All correlations move to 1.0 (worst case)",
                "volatility_multiplier": 1.0,
                "correlation_multiplier": 0.0,
                "volatility_floor": 0.0,
                "correlation_target": 1.0,
            },
            "volatility_correlation_combo": {
                "name": "Volatility + Correlation Stress",
                "description": "2x volatility + 0.9 correlation",
                "volatility_multiplier": 2.0,
                "correlation_multiplier": 0.0,
                "volatility_floor": 0.0,
                "correlation_target": 0.9,
            },
            "extreme_stress": {
                "name": "Extreme Stress (3x vol + perfect corr)",
                "description": "Worst case: 3x volatility + perfect correlation",
                "volatility_multiplier": 3.0,
                "correlation_multiplier": 0.0,
                "volatility_floor": 0.0,
                "correlation_target": 1.0,
            },
            "asymmetric_volatility": {
                "name": "Asymmetric Volatility Spike",
                "description": "Volatility increases only for losing positions",
                "volatility_multiplier": 2.5,
                "correlation_multiplier": 1.0,
                "volatility_floor": 0.0,
                "correlation_target": None,
                "asymmetric": True,
            },
        }

    def run_variance_stress_tests(
        self,
        portfolio: Portfolio,
        current_correlations: dict[str, dict[str, float]],
        current_volatilities: dict[str, float],
        scenario_names: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Run comprehensive variance stress tests.

        Args:
            portfolio: Portfolio to test
            current_correlations: Current correlation matrix
            current_volatilities: Current volatilities by symbol
            scenario_names: Scenarios to run (None = all)

        Returns:
            Stress test results
        """
        try:
            if scenario_names is None:
                scenario_names = list(self.scenarios.keys())

            # Calculate baseline variance
            baseline_variance = self._calculate_portfolio_variance(
                portfolio, current_correlations, current_volatilities
            )

            results = {}
            variance_increases = []

            for scenario_name in scenario_names:
                if scenario_name not in self.scenarios:
                    self.logger.warning(f"Unknown scenario: {scenario_name}")
                    continue

                scenario = self.scenarios[scenario_name]

                # Apply stress scenario
                stressed_variance = self._apply_stress_scenario(
                    portfolio,
                    current_correlations,
                    current_volatilities,
                    scenario,
                )

                variance_increase = stressed_variance - baseline_variance
                variance_increase_pct = (
                    variance_increase / baseline_variance * 100 if baseline_variance > 0 else 0
                )

                results[scenario_name] = {
                    "scenario": scenario["name"],
                    "description": scenario["description"],
                    "baseline_variance": baseline_variance,
                    "stressed_variance": stressed_variance,
                    "variance_increase": variance_increase,
                    "variance_increase_pct": variance_increase_pct,
                    "volatility_multiplier": scenario["volatility_multiplier"],
                    "correlation_target": scenario.get("correlation_target"),
                    "risk_assessment": self._assess_variance_increase(variance_increase_pct),
                }

                variance_increases.append(
                    {
                        "scenario": scenario_name,
                        "increase_pct": variance_increase_pct,
                    }
                )

            # Generate summary
            summary = self._generate_variance_stress_summary(results, variance_increases)

            return {
                "scenarios": results,
                "summary": summary,
                "baseline_variance": baseline_variance,
                "timestamp": self._get_timestamp(),
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error running variance stress tests: {e}", exc_info=True)
            return {"error": str(e)}

    def _calculate_portfolio_variance(
        self,
        portfolio: Portfolio,
        correlations: dict[str, dict[str, float]],
        volatilities: dict[str, float],
    ) -> float:
        """
        Calculate portfolio variance.

        Formula: σ²_p = Σᵢ Σⱼ wᵢ wⱼ σᵢ σⱼ ρᵢⱼ
        """
        if portfolio.total_equity == 0:
            return 0.0

        # Calculate weights
        weights = {}
        for position in portfolio.positions:
            weights[position.symbol] = float(position.market_value / portfolio.total_equity)

        # Calculate variance
        variance = 0.0
        symbols = list(weights.keys())

        for symbol1 in symbols:
            for symbol2 in symbols:
                w1 = weights[symbol1]
                w2 = weights[symbol2]
                sigma1 = volatilities.get(symbol1, 0.2)
                sigma2 = volatilities.get(symbol2, 0.2)

                if symbol1 == symbol2:
                    correlation = 1.0
                else:
                    correlation = correlations.get(symbol1, {}).get(symbol2, 0.0)
                    if correlation is None:
                        correlation = 0.0

                variance += w1 * w2 * sigma1 * sigma2 * correlation

        return variance

    def _apply_stress_scenario(
        self,
        portfolio: Portfolio,
        current_correlations: dict[str, dict[str, float]],
        current_volatilities: dict[str, float],
        scenario: dict[str, Any],
    ) -> float:
        """Apply a stress scenario to calculate stressed variance."""
        # Stress volatilities
        stressed_volatilities = {}
        for symbol, vol in current_volatilities.items():
            stressed_vol = vol * scenario["volatility_multiplier"]

            # Apply volatility floor
            if "volatility_floor" in scenario:
                stressed_vol = max(stressed_vol, scenario["volatility_floor"])

            stressed_volatilities[symbol] = stressed_vol

        # Stress correlations
        stressed_correlations = self._stress_correlations(
            current_correlations,
            portfolio,
            scenario,
        )

        # Calculate stressed variance
        return self._calculate_portfolio_variance(
            portfolio, stressed_correlations, stressed_volatilities
        )

    def _stress_correlations(
        self,
        current_correlations: dict[str, dict[str, float]],
        portfolio: Portfolio,
        scenario: dict[str, Any],
    ) -> dict[str, dict[str, float]]:
        """Apply correlation stress to correlation matrix."""
        portfolio_symbols = [pos.symbol for pos in portfolio.positions]
        stressed_matrix = {}

        # Initialize matrix
        for symbol1 in portfolio_symbols:
            stressed_matrix[symbol1] = {}
            for symbol2 in portfolio_symbols:
                if symbol1 == symbol2:
                    stressed_matrix[symbol1][symbol2] = 1.0
                else:
                    stressed_matrix[symbol1][symbol2] = None

        # Apply correlation target if specified
        correlation_target = scenario.get("correlation_target")
        if correlation_target is not None:
            for symbol1 in portfolio_symbols:
                for symbol2 in portfolio_symbols:
                    if symbol1 != symbol2:
                        stressed_matrix[symbol1][symbol2] = correlation_target
        else:
            # Use current correlations
            for symbol1 in portfolio_symbols:
                for symbol2 in portfolio_symbols:
                    if symbol1 != symbol2:
                        current_corr = current_correlations.get(symbol1, {}).get(symbol2, 0.0)
                        stressed_matrix[symbol1][symbol2] = (
                            current_corr if current_corr is not None else 0.0
                        )

        return stressed_matrix

    def _assess_variance_increase(self, variance_increase_pct: float) -> dict[str, Any]:
        """Assess the severity of variance increase."""
        if variance_increase_pct > 200:
            return {
                "severity": "CRITICAL",
                "action": "IMMEDIATE position reduction required",
                "variance_increase_pct": variance_increase_pct,
            }
        elif variance_increase_pct > 100:
            return {
                "severity": "HIGH",
                "action": "Significant de-risking recommended",
                "variance_increase_pct": variance_increase_pct,
            }
        elif variance_increase_pct > 50:
            return {
                "severity": "MODERATE",
                "action": "Consider reducing exposure",
                "variance_increase_pct": variance_increase_pct,
            }
        elif variance_increase_pct > 20:
            return {
                "severity": "ELEVATED",
                "action": "Increased monitoring required",
                "variance_increase_pct": variance_increase_pct,
            }
        else:
            return {
                "severity": "LOW",
                "action": "Normal monitoring sufficient",
                "variance_increase_pct": variance_increase_pct,
            }

    def _generate_variance_stress_summary(
        self,
        results: dict[str, dict[str, Any]],
        variance_increases: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate summary of variance stress test results."""
        if not variance_increases:
            return {"error": "No valid results"}

        # Find worst and best scenarios
        worst = max(variance_increases, key=lambda x: x["increase_pct"])
        best = min(variance_increases, key=lambda x: x["increase_pct"])

        # Calculate statistics
        increase_values = [v["increase_pct"] for v in variance_increases]

        summary = {
            "worst_scenario": {
                "name": worst["scenario"],
                "variance_increase_pct": worst["increase_pct"],
                "details": results.get(worst["scenario"], {}),
            },
            "best_scenario": {
                "name": best["scenario"],
                "variance_increase_pct": best["increase_pct"],
                "details": results.get(best["scenario"], {}),
            },
            "statistics": {
                "mean_increase_pct": float(np.mean(increase_values)),
                "median_increase_pct": float(np.median(increase_values)),
                "max_increase_pct": float(np.max(increase_values)),
                "min_increase_pct": float(np.min(increase_values)),
                "std_increase_pct": float(np.std(increase_values)),
            },
            "overall_assessment": self._generate_overall_assessment(increase_values),
        }

        return summary

    def _generate_overall_assessment(self, increase_values: list[float]) -> dict[str, Any]:
        """Generate overall risk assessment based on all scenarios."""
        max_increase = max(increase_values)
        mean_increase = np.mean(increase_values)

        if max_increase > 200:
            risk_level = "CRITICAL"
            recommendation = (
                "Portfolio is highly vulnerable to stress scenarios. "
                "Significant de-risking required immediately."
            )
        elif max_increase > 100:
            risk_level = "HIGH"
            recommendation = (
                "Portfolio shows significant stress vulnerability. "
                "Consider reducing exposure and improving diversification."
            )
        elif max_increase > 50:
            risk_level = "MODERATE"
            recommendation = (
                "Portfolio has moderate stress vulnerability. "
                "Monitor closely and consider selective de-risking."
            )
        else:
            risk_level = "ACCEPTABLE"
            recommendation = (
                "Portfolio shows reasonable resilience to stress scenarios. "
                "Continue normal monitoring."
            )

        return {
            "risk_level": risk_level,
            "recommendation": recommendation,
            "max_variance_increase_pct": max_increase,
            "mean_variance_increase_pct": mean_increase,
        }

    def decompose_portfolio_variance(
        self,
        portfolio: Portfolio,
        correlations: dict[str, dict[str, float]],
        volatilities: dict[str, float],
    ) -> dict[str, Any]:
        """
        Decompose portfolio variance into components.

        Shows:
        1. Diagonal variance (individual position risk)
        2. Off-diagonal covariance (diversification effect)
        3. Risk contribution by position

        Args:
            portfolio: Portfolio to analyze
            correlations: Correlation matrix
            volatilities: Volatilities by symbol

        Returns:
            Variance decomposition
        """
        try:
            if portfolio.total_equity == 0:
                return {"error": "Portfolio value is zero"}

            # Calculate weights
            weights = {}
            for position in portfolio.positions:
                weights[position.symbol] = float(position.market_value / portfolio.total_equity)

            # Calculate variance components
            diagonal_variance = 0.0  # Σ wᵢ² σᵢ²
            off_diagonal_covariance = 0.0  # Σᵢ≠ⱼ wᵢ wⱼ σᵢ σⱼ ρᵢⱼ
            position_contributions = {}

            symbols = list(weights.keys())

            for symbol in symbols:
                w = weights[symbol]
                sigma = volatilities.get(symbol, 0.2)

                # Diagonal component
                diagonal = w * w * sigma * sigma
                diagonal_variance += diagonal

                # Off-diagonal component
                off_diag = 0.0
                for other_symbol in symbols:
                    if other_symbol != symbol:
                        w_other = weights[other_symbol]
                        sigma_other = volatilities.get(other_symbol, 0.2)
                        correlation = correlations.get(symbol, {}).get(other_symbol, 0.0)
                        if correlation is None:
                            correlation = 0.0

                        off_diag += w * w_other * sigma * sigma_other * correlation

                off_diagonal_covariance += off_diag / 2  # Divide by 2 to avoid double counting

                # Position contribution (simplified)
                position_contributions[symbol] = {
                    "weight": w,
                    "volatility": sigma,
                    "diagonal_risk": diagonal,
                    "covariance_risk": off_diag,
                    "total_contribution": diagonal + off_diag,
                }

            total_variance = diagonal_variance + off_diagonal_covariance

            # Calculate percentages
            for symbol in position_contributions:
                contrib = position_contributions[symbol]
                if total_variance > 0:
                    contrib["contribution_pct"] = (
                        contrib["total_contribution"] / total_variance * 100
                    )

            # Diversification ratio
            # = weighted avg volatility / portfolio volatility
            weighted_avg_vol = sum(abs(weights[s]) * volatilities.get(s, 0.2) for s in symbols)
            portfolio_vol = np.sqrt(total_variance) if total_variance > 0 else 0
            diversification_ratio = weighted_avg_vol / portfolio_vol if portfolio_vol > 0 else 1.0

            return {
                "total_variance": total_variance,
                "portfolio_volatility": portfolio_vol,
                "diagonal_variance": diagonal_variance,
                "off_diagonal_covariance": off_diagonal_covariance,
                "diagonal_pct": (
                    diagonal_variance / total_variance * 100 if total_variance > 0 else 0
                ),
                "off_diagonal_pct": (
                    off_diagonal_covariance / total_variance * 100 if total_variance > 0 else 0
                ),
                "position_contributions": position_contributions,
                "diversification_ratio": diversification_ratio,
                "diversification_benefit": diversification_ratio - 1.0,
                "interpretation": self._interpret_variance_decomposition(
                    diagonal_variance, off_diagonal_covariance, total_variance
                ),
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error decomposing variance: {e}", exc_info=True)
            return {"error": str(e)}

    def _interpret_variance_decomposition(
        self,
        diagonal_variance: float,
        off_diagonal_covariance: float,
        total_variance: float,
    ) -> str:
        """Interpret variance decomposition."""
        if total_variance == 0:
            return "No variance to decompose"

        diag_pct = diagonal_variance / total_variance * 100

        if diag_pct > 80:
            return (
                f"High idiosyncratic risk ({diag_pct:.1f}% from diagonal). "
                f"Limited diversification benefits. Consider adding uncorrelated assets."
            )
        elif diag_pct > 60:
            return (
                f"Moderate idiosyncratic risk ({diag_pct:.1f}% from diagonal). "
                f"Some diversification benefits present."
            )
        else:
            return (
                f"Good diversification ({diag_pct:.1f}% from diagonal). "
                f"Portfolio benefits from correlation structure."
            )

    def calculate_concentration_stress(
        self,
        portfolio: Portfolio,
        volatilities: dict[str, float],
        concentration_threshold: float = 0.30,
    ) -> dict[str, Any]:
        """
        Calculate variance stress from concentration risk.

        Tests what happens if the largest position experiences adverse moves.

        Args:
            portfolio: Portfolio to test
            volatilities: Volatilities by symbol
            concentration_threshold: Threshold for concentrated position

        Returns:
            Concentration stress analysis
        """
        try:
            if portfolio.total_equity == 0:
                return {"error": "Portfolio value is zero"}

            # Find largest position
            positions_by_value = sorted(
                portfolio.positions,
                key=lambda p: p.market_value,
                reverse=True,
            )

            if not positions_by_value:
                return {"error": "No positions in portfolio"}

            largest_position = positions_by_value[0]
            largest_weight = float(largest_position.market_value / portfolio.total_equity)

            # Calculate portfolio variance excluding largest position
            remaining_positions = [p for p in portfolio.positions if p != largest_position]

            if not remaining_positions:
                return {
                    "error": "Portfolio has only one position",
                    "largest_weight": largest_weight,
                }

            # Simulate stress: largest position drops by 3 sigma
            largest_vol = volatilities.get(largest_position.symbol, 0.2)
            stress_return = -3 * largest_vol  # 3-sigma adverse move

            # Calculate portfolio loss
            portfolio_loss = largest_weight * stress_return

            # Calculate variance contribution
            variance_contribution = largest_weight**2 * largest_vol**2

            # Assessment
            is_concentrated = largest_weight > concentration_threshold

            if is_concentrated:
                severity = "HIGH" if largest_weight > 0.50 else "MODERATE"
                recommendation = (
                    f"Position {largest_position.symbol} is {largest_weight:.1%} of portfolio. "
                    f"Consider reducing concentration or implementing hedging."
                )
            else:
                severity = "LOW"
                recommendation = "Concentration within acceptable limits"

            return {
                "largest_position": largest_position.symbol,
                "largest_weight": largest_weight,
                "largest_volatility": largest_vol,
                "is_concentrated": is_concentrated,
                "concentration_threshold": concentration_threshold,
                "stress_scenario": {
                    "shock": "3-sigma adverse move",
                    "expected_return": stress_return,
                    "portfolio_loss": portfolio_loss,
                    "loss_pct": portfolio_loss * 100,
                },
                "variance_contribution": variance_contribution,
                "severity": severity,
                "recommendation": recommendation,
            }

        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error(f"Error calculating concentration stress: {e}", exc_info=True)
            return {"error": str(e)}

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.utcnow().isoformat()
