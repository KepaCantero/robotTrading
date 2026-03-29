"""
Advanced Stress Testing Scenarios - Hull Chapter 20

Implements specialized stress testing scenarios for:
1. Liquidity Risk Scenarios
2. Counterparty Risk Scenarios
3. Operational Risk Scenarios
4. Systemic Risk Scenarios
5. Contagion Risk Scenarios

Reference: Hull, Risk Management and Financial Institutions, Chapter 20
"""

import logging
from datetime import datetime
from typing import Any, Optional

import numpy as np

from app.domain.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


class LiquidityRiskStressTester:
    """
    Liquidity Risk Stress Tester.

    Tests portfolio resilience under various liquidity crisis scenarios.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize liquidity risk stress tester.

        Args:
            config: Configuration dictionary
        """
        config = config or {}
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Liquidity stress scenarios
        self.scenarios = self._initialize_liquidity_scenarios()

    def _initialize_liquidity_scenarios(self) -> dict[str, dict[str, Any]]:
        """Initialize liquidity stress scenarios."""
        return {
            "baseline": {
                "name": "Baseline Liquidity",
                "description": "Normal market conditions",
                "bid_ask_spread_multiplier": 1.0,
                "market_impact_multiplier": 1.0,
                "volume_multiplier": 1.0,
                "liquidity_score": 1.0,
            },
            "mild_liquidity_drought": {
                "name": "Mild Liquidity Drought",
                "description": "Reduced market depth and wider spreads",
                "bid_ask_spread_multiplier": 2.0,
                "market_impact_multiplier": 1.5,
                "volume_multiplier": 0.7,
                "liquidity_score": 0.7,
            },
            "moderate_liquidity_crisis": {
                "name": "Moderate Liquidity Crisis",
                "description": "Significant liquidity reduction",
                "bid_ask_spread_multiplier": 4.0,
                "market_impact_multiplier": 2.5,
                "volume_multiplier": 0.4,
                "liquidity_score": 0.4,
            },
            "severe_liquidity_crisis": {
                "name": "Severe Liquidity Crisis",
                "description": "Market freeze conditions",
                "bid_ask_spread_multiplier": 10.0,
                "market_impact_multiplier": 5.0,
                "volume_multiplier": 0.1,
                "liquidity_score": 0.1,
            },
            "flash_crash_liquidity": {
                "name": "Flash Crash Liquidity Evaporation",
                "description": "Rapid intra-day liquidity disappearance",
                "bid_ask_spread_multiplier": 20.0,
                "market_impact_multiplier": 15.0,
                "volume_multiplier": 0.05,
                "liquidity_score": 0.05,
                "duration_minutes": 30,
            },
            "asset_specific_liquidity": {
                "name": "Asset-Specific Liquidity Crisis",
                "description": "Liquidity dries up for specific assets",
                "affected_assets": ["small_cap", "emerging_markets", "high_yield"],
                "bid_ask_spread_multiplier": 8.0,
                "market_impact_multiplier": 4.0,
                "volume_multiplier": 0.2,
            },
        }

    def calculate_liquidity_adjusted_var(
        self,
        portfolio: Portfolio,
        base_var: float,
        scenario_name: str = "moderate_liquidity_crisis",
    ) -> dict[str, Any]:
        """
        Calculate liquidity-adjusted VaR.

        Adjusts standard VaR for liquidity risk during stress scenarios.

        Formula: L-VaR = VaR + Liquidity Cost

        Liquidity Cost = 0.5 * Spread * Position Size + Market Impact

        Args:
            portfolio: Portfolio to analyze
            base_var: Base VaR calculation
            scenario_name: Liquidity scenario to apply

        Returns:
            Liquidity-adjusted VaR
        """
        try:
            if scenario_name not in self.scenarios:
                return {"error": f"Unknown scenario: {scenario_name}"}

            scenario = self.scenarios[scenario_name]

            # Calculate liquidity cost for each position
            total_liquidity_cost = 0.0
            position_liquidity_costs = []

            for position in portfolio.positions:
                position_value = float(position.market_value)

                # Estimate bid-ask spread under stress
                # Assume 0.1% normal spread for liquid assets
                base_spread = 0.001
                stressed_spread = base_spread * scenario["bid_ask_spread_multiplier"]

                # Spread cost (half spread = cost to exit)
                spread_cost = 0.5 * stressed_spread * position_value

                # Market impact cost
                # Assume 1% market impact per 10% of daily volume traded
                base_impact = 0.01
                stressed_impact = base_impact * scenario["market_impact_multiplier"]

                # Estimate position size relative to volume
                volume_factor = 0.1 / scenario.get("volume_multiplier", 1.0)
                market_impact_cost = stressed_impact * volume_factor * position_value

                total_position_cost = spread_cost + market_impact_cost
                total_liquidity_cost += total_position_cost

                position_liquidity_costs.append(
                    {
                        "symbol": position.symbol,
                        "position_value": position_value,
                        "spread_cost": spread_cost,
                        "market_impact_cost": market_impact_cost,
                        "total_liquidity_cost": total_position_cost,
                    }
                )

            # Liquidity-adjusted VaR
            liquidity_adjusted_var = base_var + total_liquidity_cost

            # Calculate liquidity adjustment percentage
            liquidity_adjustment_pct = (
                (total_liquidity_cost / abs(base_var)) * 100 if base_var != 0 else 0
            )

            return {
                "base_var": base_var,
                "liquidity_cost": total_liquidity_cost,
                "liquidity_adjusted_var": liquidity_adjusted_var,
                "liquidity_adjustment_pct": liquidity_adjustment_pct,
                "scenario": scenario["name"],
                "position_costs": position_liquidity_costs,
                "interpretation": self._interpret_lvar(liquidity_adjustment_pct),
            }

        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error(f"Error calculating L-VaR: {e}", exc_info=True)
            return {"error": str(e)}

    def _interpret_lvar(self, adjustment_pct: float) -> str:
        """Interpret liquidity adjustment."""
        if adjustment_pct > 50:
            return (
                f"CRITICAL: Liquidity risk increases VaR by {adjustment_pct:.1f}%. "
                f"Portfolio highly vulnerable to liquidity crises."
            )
        elif adjustment_pct > 20:
            return (
                f"HIGH: Liquidity risk increases VaR by {adjustment_pct:.1f}%. "
                f"Significant liquidity exposure."
            )
        elif adjustment_pct > 10:
            return (
                f"MODERATE: Liquidity risk increases VaR by {adjustment_pct:.1f}%. "
                f"Manageable liquidity exposure."
            )
        else:
            return (
                f"LOW: Liquidity risk increases VaR by {adjustment_pct:.1f}%. "
                f"Portfolio has good liquidity profile."
            )

    def run_liquidity_stress_tests(
        self,
        portfolio: Portfolio,
        base_var: float,
        scenario_names: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Run comprehensive liquidity stress tests.

        Args:
            portfolio: Portfolio to test
            base_var: Base VaR calculation
            scenario_names: Scenarios to run (None = all)

        Returns:
            Liquidity stress test results
        """
        try:
            if scenario_names is None:
                scenario_names = list(self.scenarios.keys())

            results = {}

            for scenario_name in scenario_names:
                if scenario_name not in self.scenarios:
                    continue

                result = self.calculate_liquidity_adjusted_var(portfolio, base_var, scenario_name)

                if "error" not in result:
                    results[scenario_name] = result

            # Generate summary
            summary = self._generate_liquidity_summary(results)

            return {
                "scenarios": results,
                "summary": summary,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error(f"Error running liquidity stress tests: {e}", exc_info=True)
            return {"error": str(e)}

    def _generate_liquidity_summary(self, results: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Generate summary of liquidity stress tests."""
        if not results:
            return {"error": "No valid results"}

        adjustments = [r.get("liquidity_adjustment_pct", 0) for r in results.values()]

        return {
            "worst_scenario": max(
                results.items(), key=lambda x: x[1].get("liquidity_adjustment_pct", 0)
            ),
            "best_scenario": min(
                results.items(), key=lambda x: x[1].get("liquidity_adjustment_pct", 0)
            ),
            "avg_adjustment_pct": float(np.mean(adjustments)),
            "max_adjustment_pct": float(np.max(adjustments)),
            "risk_assessment": self._assess_liquidity_risk(adjustments),
        }

    def _assess_liquidity_risk(self, adjustments: list[float]) -> dict[str, Any]:
        """Assess overall liquidity risk."""
        max_adjustment = max(adjustments)

        if max_adjustment > 50:
            return {
                "level": "CRITICAL",
                "action": "Immediate liquidity risk reduction required",
            }
        elif max_adjustment > 20:
            return {
                "level": "HIGH",
                "action": "Significant de-risking recommended",
            }
        elif max_adjustment > 10:
            return {
                "level": "MODERATE",
                "action": "Monitor and selectively reduce exposure",
            }
        else:
            return {
                "level": "LOW",
                "action": "Normal monitoring sufficient",
            }


class CounterpartyRiskStressTester:
    """
    Counterparty Risk Stress Tester.

    Tests portfolio exposure to counterparty defaults.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize counterparty risk stress tester."""
        config = config or {}
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Counterparty scenarios
        self.scenarios = self._initialize_counterparty_scenarios()

    def _initialize_counterparty_scenarios(self) -> dict[str, dict[str, Any]]:
        """Initialize counterparty default scenarios."""
        return {
            "single_minor_default": {
                "name": "Single Minor Counterparty Default",
                "description": "Small counterparty defaults",
                "num_defaults": 1,
                "default_size": "minor",
                "correlation_increase": 0.0,
            },
            "single_major_default": {
                "name": "Single Major Counterparty Default",
                "description": "Large counterparty defaults",
                "num_defaults": 1,
                "default_size": "major",
                "correlation_increase": 0.2,
            },
            "multiple_defaults": {
                "name": "Multiple Counterparty Defaults",
                "description": "Several counterparties default simultaneously",
                "num_defaults": 3,
                "default_size": "moderate",
                "correlation_increase": 0.4,
            },
            "systemic_default_contagion": {
                "name": "Systemic Default Contagion",
                "description": "Widespread counterparty defaults",
                "num_defaults": 10,
                "default_size": "mixed",
                "correlation_increase": 0.8,
                "recovery_rate": 0.4,  # Lower recovery in systemic crises
            },
        }

    def calculate_counterparty_exposure(
        self,
        portfolio: Portfolio,
        counterparty_data: dict[str, dict[str, Any]],
        scenario_name: str = "single_major_default",
    ) -> dict[str, Any]:
        """
        Calculate counterparty credit risk exposure.

        Args:
            portfolio: Portfolio to analyze
            counterparty_data: Counterparty information
                - exposure: Current exposure to counterparty
                - credit_quality: Credit rating (AAA to C)
                - recovery_rate: Expected recovery rate (0-1)
            scenario_name: Default scenario to apply

        Returns:
            Counterparty risk metrics
        """
        try:
            if scenario_name not in self.scenarios:
                return {"error": f"Unknown scenario: {scenario_name}"}

            scenario = self.scenarios[scenario_name]

            # Calculate potential losses from defaults
            total_exposure_at_default = 0.0
            counterparty_losses = []

            for counterparty, data in counterparty_data.items():
                exposure = data.get("exposure", 0)
                base_recovery_rate = data.get("recovery_rate", 0.4)

                # Adjust recovery rate for scenario
                scenario_recovery = base_recovery_rate * scenario.get("recovery_rate", 1.0)

                # Loss given default
                lgd = exposure * (1 - scenario_recovery)

                total_exposure_at_default += lgd

                counterparty_losses.append(
                    {
                        "counterparty": counterparty,
                        "exposure": exposure,
                        "recovery_rate": scenario_recovery,
                        "loss_given_default": lgd,
                    }
                )

            # Calculate CVA (Credit Value Adjustment) approximation
            # CVA = LGD * PD * EAD
            # Simplified: Use stress probabilities
            stress_default_prob = {
                "minor": 0.05,
                "moderate": 0.20,
                "major": 0.50,
            }.get(scenario["default_size"], 0.20)

            expected_loss = total_exposure_at_default * stress_default_prob

            # Correlation adjustment (correlated defaults)
            correlation_multiplier = 1 + scenario.get("correlation_increase", 0)
            adjusted_expected_loss = expected_loss * correlation_multiplier

            return {
                "scenario": scenario["name"],
                "total_exposure_at_default": total_exposure_at_default,
                "expected_loss": adjusted_expected_loss,
                "stress_default_probability": stress_default_prob,
                "correlation_multiplier": correlation_multiplier,
                "counterparty_losses": counterparty_losses,
                "risk_assessment": self._assess_counterparty_risk(
                    adjusted_expected_loss, portfolio.total_equity
                ),
            }

        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error(f"Error calculating counterparty exposure: {e}", exc_info=True)
            return {"error": str(e)}

    def _assess_counterparty_risk(
        self, expected_loss: float, portfolio_value: float
    ) -> dict[str, Any]:
        """Assess counterparty risk level."""
        loss_pct = (expected_loss / portfolio_value * 100) if portfolio_value > 0 else 0

        if loss_pct > 10:
            return {
                "level": "CRITICAL",
                "loss_percentage": loss_pct,
                "action": "Immediate counterparty diversification required",
            }
        elif loss_pct > 5:
            return {
                "level": "HIGH",
                "loss_percentage": loss_pct,
                "action": "Significant counterparty risk reduction needed",
            }
        elif loss_pct > 2:
            return {
                "level": "MODERATE",
                "loss_percentage": loss_pct,
                "action": "Monitor counterparty concentrations",
            }
        else:
            return {
                "level": "LOW",
                "loss_percentage": loss_pct,
                "action": "Normal monitoring sufficient",
            }


class OperationalRiskStressTester:
    """
    Operational Risk Stress Tester.

    Tests portfolio resilience to operational failures.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize operational risk stress tester."""
        config = config or {}
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Operational risk scenarios
        self.scenarios = self._initialize_operational_scenarios()

    def _initialize_operational_scenarios(self) -> dict[str, dict[str, Any]]:
        """Initialize operational failure scenarios."""
        return {
            "system_outage": {
                "name": "Trading System Outage",
                "description": "Unable to trade for extended period",
                "duration_hours": 4,
                "impact_type": "trading_halt",
                "market_moving": True,
            },
            "data_feed_failure": {
                "name": "Critical Data Feed Failure",
                "description": "Loss of market data",
                "duration_hours": 2,
                "impact_type": "information_loss",
                "market_moving": True,
            },
            "settlement_failure": {
                "name": "Settlement System Failure",
                "description": "Unable to settle trades",
                "duration_hours": 24,
                "impact_type": "settlement_delay",
                "penalty_multiplier": 1.5,
            },
            "human_error": {
                "name": "Operational Human Error",
                "description": "Fat finger or other trading error",
                "impact_type": "adverse_trade",
                "error_size_pct": 0.05,  # 5% of position
            },
            "cyber_incident": {
                "name": "Cybersecurity Incident",
                "description": "Security breach affecting operations",
                "duration_hours": 48,
                "impact_type": "system_compromise",
                "reputation_loss": True,
            },
            "vendor_failure": {
                "name": "Critical Vendor Failure",
                "description": "Third-party service provider fails",
                "duration_hours": 12,
                "impact_type": "service_disruption",
            },
        }

    def calculate_operational_risk_impact(
        self,
        portfolio: Portfolio,
        portfolio_volatility: float,
        scenario_name: str = "system_outage",
    ) -> dict[str, Any]:
        """
        Calculate operational risk impact on portfolio.

        Args:
            portfolio: Portfolio to analyze
            portfolio_volatility: Daily portfolio volatility
            scenario_name: Operational failure scenario

        Returns:
            Operational risk impact assessment
        """
        try:
            if scenario_name not in self.scenarios:
                return {"error": f"Unknown scenario: {scenario_name}"}

            scenario = self.scenarios[scenario_name]

            impact_type = scenario["impact_type"]
            estimated_loss = 0.0
            impact_details = {}

            if impact_type == "trading_halt":
                # Cannot hedge or rebalance during market move
                duration_hours = scenario["duration_hours"]
                if scenario.get("market_moving", False):
                    # Assume market moves 1 sigma against us
                    adverse_move = portfolio_volatility * np.sqrt(duration_hours / 24)
                    estimated_loss = abs(float(portfolio.total_equity) * adverse_move)
                    impact_details = {
                        "duration_hours": duration_hours,
                        "adverse_move_sigma": 1.0,
                        "unhedged_exposure": float(portfolio.total_equity),
                    }

            elif impact_type == "information_loss":
                # Trading blind - potential for adverse trades
                duration_hours = scenario["duration_hours"]
                # Assume making suboptimal decisions
                decision_cost = portfolio_volatility * 0.5 * np.sqrt(duration_hours / 24)
                estimated_loss = abs(float(portfolio.total_equity) * decision_cost)
                impact_details = {
                    "duration_hours": duration_hours,
                    "decision_quality_degradation": 0.5,
                }

            elif impact_type == "settlement_delay":
                # Penalties and financing costs
                duration_hours = scenario["duration_hours"]
                penalty_multiplier = scenario.get("penalty_multiplier", 1.0)
                # Assume 0.1% per day penalty
                daily_penalty_rate = 0.001 * penalty_multiplier
                penalty = float(portfolio.total_equity) * daily_penalty_rate * (duration_hours / 24)
                estimated_loss = penalty
                impact_details = {
                    "duration_hours": duration_hours,
                    "penalty_rate": daily_penalty_rate,
                }

            elif impact_type == "adverse_trade":
                # Human error in trade execution
                error_size_pct = scenario.get("error_size_pct", 0.05)
                estimated_loss = abs(float(portfolio.total_equity) * error_size_pct)
                impact_details = {
                    "error_size_pct": error_size_pct,
                    "correctable": False,  # Assume error cannot be corrected
                }

            elif impact_type == "system_compromise":
                # System compromise - potential for losses
                duration_hours = scenario["hours"]
                # Combine trading halt + reputation loss
                trading_loss = (
                    float(portfolio.total_equity)
                    * portfolio_volatility
                    * np.sqrt(duration_hours / 24)
                )

                reputation_loss = 0.0
                if scenario.get("reputation_loss", False):
                    # Assume 2% reputation hit
                    reputation_loss = float(portfolio.total_equity) * 0.02

                estimated_loss = trading_loss + reputation_loss
                impact_details = {
                    "duration_hours": duration_hours,
                    "trading_loss": trading_loss,
                    "reputation_loss": reputation_loss,
                }

            elif impact_type == "service_disruption":
                # Third-party service disruption
                duration_hours = scenario["duration_hours"]
                # Reduced functionality
                disruption_cost = (
                    float(portfolio.total_equity)
                    * portfolio_volatility
                    * 0.3
                    * np.sqrt(duration_hours / 24)
                )
                estimated_loss = disruption_cost
                impact_details = {
                    "duration_hours": duration_hours,
                    "functionality_reduction": 0.7,
                }

            # Calculate loss percentage
            loss_pct = (
                (estimated_loss / float(portfolio.total_equity) * 100)
                if portfolio.total_equity > 0
                else 0
            )

            return {
                "scenario": scenario["name"],
                "description": scenario["description"],
                "impact_type": impact_type,
                "estimated_loss": estimated_loss,
                "loss_percentage": loss_pct,
                "impact_details": impact_details,
                "risk_assessment": self._assess_operational_risk(loss_pct),
            }

        except (ValueError, TypeError, AttributeError, ZeroDivisionError) as e:
            self.logger.error(f"Error calculating operational risk: {e}", exc_info=True)
            return {"error": str(e)}

    def _assess_operational_risk(self, loss_pct: float) -> dict[str, Any]:
        """Assess operational risk level."""
        if loss_pct > 5:
            return {
                "level": "CRITICAL",
                "action": "Immediate operational controls required",
            }
        elif loss_pct > 2:
            return {
                "level": "HIGH",
                "action": "Strengthen operational resilience",
            }
        elif loss_pct > 1:
            return {
                "level": "MODERATE",
                "action": "Review operational procedures",
            }
        else:
            return {
                "level": "LOW",
                "action": "Normal monitoring",
            }


class AdvancedStressTestOrchestrator:
    """
    Orchestrates all advanced stress testing scenarios.

    Combines liquidity, counterparty, and operational risk stress tests.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize advanced stress test orchestrator."""
        config = config or {}
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        self.liquidity_tester = LiquidityRiskStressTester(config)
        self.counterparty_tester = CounterpartyRiskStressTester(config)
        self.operational_tester = OperationalRiskStressTester(config)

    def run_comprehensive_advanced_stress_tests(
        self,
        portfolio: Portfolio,
        base_var: float,
        portfolio_volatility: float,
        counterparty_data: Optional[dict[str, dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """
        Run all advanced stress tests.

        Args:
            portfolio: Portfolio to test
            base_var: Base VaR calculation
            portfolio_volatility: Daily portfolio volatility
            counterparty_data: Counterparty exposure data

        Returns:
            Comprehensive advanced stress test results
        """
        try:
            results = {}

            # 1. Liquidity stress tests
            liquidity_results = self.liquidity_tester.run_liquidity_stress_tests(
                portfolio, base_var
            )
            results["liquidity_risk"] = liquidity_results

            # 2. Counterparty stress tests (if data provided)
            if counterparty_data:
                counterparty_results = {}
                for scenario_name in self.counterparty_tester.scenarios:
                    result = self.counterparty_tester.calculate_counterparty_exposure(
                        portfolio, counterparty_data, scenario_name
                    )
                    if "error" not in result:
                        counterparty_results[scenario_name] = result
                results["counterparty_risk"] = counterparty_results
            else:
                results["counterparty_risk"] = {"note": "No counterparty data provided"}

            # 3. Operational stress tests
            operational_results = {}
            for scenario_name in self.operational_tester.scenarios:
                result = self.operational_tester.calculate_operational_risk_impact(
                    portfolio, portfolio_volatility, scenario_name
                )
                if "error" not in result:
                    operational_results[scenario_name] = result
            results["operational_risk"] = operational_results

            # Generate overall assessment
            overall_assessment = self._generate_overall_assessment(results, portfolio)

            return {
                "results": results,
                "overall_assessment": overall_assessment,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error(f"Error running advanced stress tests: {e}", exc_info=True)
            return {"error": str(e)}

    def _generate_overall_assessment(
        self,
        results: dict[str, Any],
        portfolio: Portfolio,
    ) -> dict[str, Any]:
        """Generate overall risk assessment."""
        risk_scores = []

        # Assess liquidity risk
        liquidity_summary = results.get("liquidity_risk", {}).get("summary", {})
        liquidity_risk_level = liquidity_summary.get("risk_assessment", {}).get("level", "LOW")
        risk_scores.append(self._risk_level_to_score(liquidity_risk_level))

        # Assess counterparty risk
        counterparty_results = results.get("counterparty_risk", {})
        if counterparty_results and "note" not in counterparty_results:
            worst_counterparty = max(
                counterparty_results.values(),
                key=lambda x: x.get("risk_assessment", {}).get("loss_percentage", 0),
            )
            counterparty_risk_level = worst_counterparty.get("risk_assessment", {}).get(
                "level", "LOW"
            )
            risk_scores.append(self._risk_level_to_score(counterparty_risk_level))

        # Assess operational risk
        operational_results = results.get("operational_risk", {})
        if operational_results:
            worst_operational = max(
                operational_results.values(),
                key=lambda x: x.get("loss_percentage", 0),
            )
            operational_risk_level = worst_operational.get("risk_assessment", {}).get(
                "level", "LOW"
            )
            risk_scores.append(self._risk_level_to_score(operational_risk_level))

        # Calculate overall risk
        avg_risk_score = np.mean(risk_scores) if risk_scores else 0

        if avg_risk_score >= 4:
            overall_level = "CRITICAL"
            recommendation = (
                "Immediate and comprehensive risk reduction required across all dimensions"
            )
        elif avg_risk_score >= 3:
            overall_level = "HIGH"
            recommendation = "Significant de-risking required. Review all risk categories"
        elif avg_risk_score >= 2:
            overall_level = "MODERATE"
            recommendation = "Moderate risk exposure. Continue monitoring and selective reduction"
        else:
            overall_level = "LOW"
            recommendation = "Risk levels within acceptable bounds"

        return {
            "overall_risk_level": overall_level,
            "risk_score": avg_risk_score,
            "recommendation": recommendation,
            "risk_categories": {
                "liquidity": liquidity_risk_level,
                "counterparty": (
                    counterparty_results.get("note", "N/A")
                    if "note" in counterparty_results
                    else counterparty_risk_level
                ),
                "operational": (
                    operational_results.get("risk_assessment", {}).get("level", "N/A")
                    if operational_results
                    else "N/A"
                ),
            },
        }

    def _risk_level_to_score(self, level: str) -> float:
        """Convert risk level to numeric score."""
        scores = {
            "LOW": 1,
            "MODERATE": 2,
            "HIGH": 3,
            "CRITICAL": 4,
        }
        return scores.get(level, 1)


# Alias for backward compatibility with compliance engine
# AdvancedStressTester is the main class users should interact with for Hull's stress testing
AdvancedStressTester = AdvancedStressTestOrchestrator


def get_advanced_stress_tester(config: Optional[dict[str, Any]] = None) -> AdvancedStressTester:
    """
    Get an AdvancedStressTester instance for Hull's advanced stress testing.

    This is a convenience function for the compliance engine to check if
    Hull systems are available.

    Args:
        config: Optional configuration dictionary

    Returns:
        AdvancedStressTester instance (aliased to AdvancedStressTestOrchestrator)

    Example:
        >>> stress_tester = get_advanced_stress_tester()
        >>> results = stress_tester.run_comprehensive_stress_test(portfolio_data)
    """
    return AdvancedStressTester(config=config)
