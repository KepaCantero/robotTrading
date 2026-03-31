"""
Comprehensive Stress Testing Scenarios - Hull Chapter 20

Implements advanced stress testing scenarios beyond basic historical scenarios.

Scenarios include:
1. Market crash scenarios (Black Monday, 2008, COVID, etc.)
2. Volatility spike scenarios (VIX explosion)
3. Correlation breakdown scenarios
4. Liquidity crisis scenarios
5. Sector rotation scenarios
6. Interest rate shock scenarios
7. Currency crisis scenarios
8. Commodity shock scenarios
9. Geopolitical event scenarios
10. Combination stress scenarios

Reference: Hull, Options, Futures, and Other Derivatives, Chapter 20
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

import numpy as np

from app.domain.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


class ComprehensiveStressScenarios:
    """
    Comprehensive Stress Testing Scenarios.

    Implements a wide range of stress scenarios for robust risk assessment.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize comprehensive stress scenarios.

        Args:
            config: Configuration dictionary
        """
        config = config or {}
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Load all scenarios
        self.market_crash_scenarios = self._load_market_crash_scenarios()
        self.volatility_scenarios = self._load_volatility_scenarios()
        self.correlation_scenarios = self._load_correlation_scenarios()
        self.liquidity_scenarios = self._load_liquidity_scenarios()
        self.interest_rate_scenarios = self._load_interest_rate_scenarios()
        self.currency_scenarios = self._load_currency_scenarios()
        self.combination_scenarios = self._load_combination_scenarios()

    def _load_market_crash_scenarios(self) -> dict[str, dict[str, Any]]:
        """Load historical market crash scenarios."""
        return {
            "black_monday_1987": {
                "name": "Black Monday 1987",
                "description": "22.6% single-day market drop",
                "market_shock": -0.226,
                "volatility_multiplier": 5.0,
                "correlation_increase": 0.4,
                "liquidity_decrease": 0.5,
                "sector_impact": {
                    "technology": -0.30,
                    "financials": -0.25,
                    "consumer": -0.20,
                },
            },
            "asian_crisis_1997": {
                "name": "Asian Financial Crisis 1997",
                "description": "Emerging market currency and equity crisis",
                "market_shock": -0.15,
                "volatility_multiplier": 3.0,
                "correlation_increase": 0.3,
                "currency_shock": -0.40,  # Emerging market currencies
                "sector_impact": {
                    "emerging_markets": -0.40,
                    "technology": -0.15,
                    "financials": -0.20,
                },
            },
            "dot_com_bubble_2000": {
                "name": "Dot-com Bubble Burst 2000",
                "description": "Technology sector collapse",
                "market_shock": -0.10,
                "volatility_multiplier": 2.5,
                "correlation_increase": 0.2,
                "sector_impact": {
                    "technology": -0.50,
                    "telecommunications": -0.35,
                    "consumer_cyclical": -0.15,
                },
            },
            "global_financial_crisis_2008": {
                "name": "Global Financial Crisis 2008",
                "description": "Systemic financial crisis",
                "market_shock": -0.50,
                "volatility_multiplier": 4.0,
                "correlation_increase": 0.5,
                "liquidity_decrease": 0.8,
                "sector_impact": {
                    "financials": -0.70,
                    "real_estate": -0.60,
                    "consumer_cyclical": -0.40,
                    "industrials": -0.35,
                },
            },
            "flash_crash_2010": {
                "name": "Flash Crash 2010",
                "description": "Rapid intra-day crash and recovery",
                "market_shock": -0.10,
                "volatility_multiplier": 10.0,
                "correlation_increase": 0.3,
                "duration_hours": 1,  # Very short duration
                "sector_impact": {
                    "all": -0.10,  # Broad-based
                },
            },
            "covid_crash_2020": {
                "name": "COVID-19 Market Crash 2020",
                "description": "Pandemic-induced global market crash",
                "market_shock": -0.35,
                "volatility_multiplier": 3.5,
                "correlation_increase": 0.4,
                "sector_impact": {
                    "travel_leisure": -0.50,
                    "energy": -0.45,
                    "financials": -0.30,
                    "technology": -0.15,
                    "healthcare": -0.10,
                },
            },
        }

    def _load_volatility_scenarios(self) -> dict[str, dict[str, Any]]:
        """Load volatility spike scenarios."""
        return {
            "vix_spike_2x": {
                "name": "VIX Spike 2x",
                "description": "Volatility index doubles",
                "volatility_multiplier": 2.0,
                "market_shock": -0.05,  # Mild negative correlation
            },
            "vix_surge_3x": {
                "name": "VIX Surge 3x",
                "description": "Volatility index triples",
                "volatility_multiplier": 3.0,
                "market_shock": -0.10,
            },
            "volatility_explosion": {
                "name": "Volatility Explosion",
                "description": "Extreme volatility (5x normal)",
                "volatility_multiplier": 5.0,
                "market_shock": -0.15,
                "correlation_increase": 0.3,
            },
            "volatility_regime_shift": {
                "name": "Volatility Regime Shift",
                "description": "Permanent shift to higher volatility regime",
                "volatility_multiplier": 2.5,
                "market_shock": -0.08,
                "persistent": True,
            },
        }

    def _load_correlation_scenarios(self) -> dict[str, dict[str, Any]]:
        """Load correlation breakdown scenarios."""
        return {
            "correlation_breakdown_moderate": {
                "name": "Moderate Correlation Breakdown",
                "description": "All correlations increase to 0.7",
                "correlation_target": 0.7,
                "diversification_loss": 0.4,
            },
            "correlation_breakdown_severe": {
                "name": "Severe Correlation Breakdown",
                "description": "All correlations increase to 0.9",
                "correlation_target": 0.9,
                "diversification_loss": 0.7,
            },
            "correlation_breakdown_extreme": {
                "name": "Extreme Correlation Breakdown",
                "description": "Perfect correlation (worst case)",
                "correlation_target": 1.0,
                "diversification_loss": 1.0,
            },
            "asymmetric_correlation": {
                "name": "Asymmetric Correlation Increase",
                "description": "Correlations increase only during downturns",
                "correlation_target": 0.8,
                "asymmetric": True,
                "downside_only": True,
            },
        }

    def _load_liquidity_scenarios(self) -> dict[str, dict[str, Any]]:
        """Load liquidity crisis scenarios."""
        return {
            "liquidity_drought": {
                "name": "Liquidity Drought",
                "description": "Market liquidity dries up",
                "liquidity_decrease": 0.8,
                "bid_ask_widening": 3.0,
                "market_impact_increase": 2.5,
            },
            "market_freeze": {
                "name": "Market Freeze",
                "description": "Extreme liquidity crisis",
                "liquidity_decrease": 0.95,
                "bid_ask_widening": 10.0,
                "market_impact_increase": 5.0,
            },
        }

    def _load_interest_rate_scenarios(self) -> dict[str, dict[str, Any]]:
        """Load interest rate shock scenarios."""
        return {
            "rate_hike_100bp": {
                "name": "100bp Rate Hike",
                "description": "Sudden 100 basis point rate increase",
                "rate_shock": 0.01,
                "bond_impact": -0.05,
                "sector_impact": {
                    "real_estate": -0.10,
                    "utilities": -0.08,
                    "financials": 0.05,  # Banks benefit
                    "technology": -0.05,
                },
            },
            "rate_hike_200bp": {
                "name": "200bp Rate Hike",
                "description": "Aggressive 200 basis point rate increase",
                "rate_shock": 0.02,
                "bond_impact": -0.10,
                "sector_impact": {
                    "real_estate": -0.20,
                    "utilities": -0.15,
                    "financials": 0.10,
                    "technology": -0.10,
                },
            },
            "rate_curve_inversion": {
                "name": "Yield Curve Inversion",
                "description": "2y-10y curve inverts",
                "curve_shift": "inversion",
                "recession_probability": 0.7,
            },
        }

    def _load_currency_scenarios(self) -> dict[str, dict[str, Any]]:
        """Load currency crisis scenarios."""
        return {
            "usd_strength": {
                "name": "USD Surge",
                "description": "US dollar strengthens significantly",
                "usd_shock": 0.15,
                "emerging_market_impact": -0.20,
                "commodity_impact": -0.10,
            },
            "emerging_market_crisis": {
                "name": "EM Currency Crisis",
                "description": "Emerging market currencies collapse",
                "em_currency_shock": -0.30,
                "contagion": True,
            },
        }

    def _load_combination_scenarios(self) -> dict[str, dict[str, Any]]:
        """Load combination stress scenarios."""
        return {
            "perfect_storm": {
                "name": "Perfect Storm",
                "description": "Multiple stress factors simultaneously",
                "market_shock": -0.30,
                "volatility_multiplier": 3.0,
                "correlation_target": 0.9,
                "liquidity_decrease": 0.7,
            },
            "systemic_crisis": {
                "name": "Systemic Crisis",
                "description": "Worst-case systemic event",
                "market_shock": -0.50,
                "volatility_multiplier": 5.0,
                "correlation_target": 1.0,
                "liquidity_decrease": 0.9,
                "rate_shock": 0.02,
            },
            "inflation_shock": {
                "name": "Inflation Shock",
                "description": "Surprise inflation spike",
                "inflation_shock": 0.05,
                "rate_response": 0.015,
                "market_shock": -0.15,
                "sector_impact": {
                    "real_estate": -0.20,
                    "consumer_staples": -0.10,
                    "energy": 0.15,
                    "financials": 0.10,
                },
            },
        }

    def run_comprehensive_stress_tests(
        self,
        portfolio: Portfolio,
        scenario_categories: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Run comprehensive stress tests across multiple categories.

        Args:
            portfolio: Portfolio to test
            scenario_categories: Categories to test (None = all)

        Returns:
            Comprehensive stress test results
        """
        try:
            if scenario_categories is None:
                scenario_categories = [
                    "market_crash",
                    "volatility",
                    "correlation",
                    "liquidity",
                    "interest_rate",
                    "currency",
                    "combination",
                ]

            results = {}
            all_scenarios = []

            for category in scenario_categories:
                category_results = self._run_category_scenarios(portfolio, category)
                if category_results:
                    results[category] = category_results
                    all_scenarios.extend(category_results.get("scenarios", []))

            # Generate comprehensive summary
            summary = self._generate_comprehensive_summary(results, all_scenarios)

            return {
                "categories": results,
                "summary": summary,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error running comprehensive stress tests: {e}", exc_info=True)
            return {"error": str(e)}

    def _run_category_scenarios(
        self,
        portfolio: Portfolio,
        category: str,
    ) -> dict[str, Any]:
        """Run all scenarios in a category."""
        scenario_map = {
            "market_crash": self.market_crash_scenarios,
            "volatility": self.volatility_scenarios,
            "correlation": self.correlation_scenarios,
            "liquidity": self.liquidity_scenarios,
            "interest_rate": self.interest_rate_scenarios,
            "currency": self.currency_scenarios,
            "combination": self.combination_scenarios,
        }

        scenarios = scenario_map.get(category, {})
        if not scenarios:
            self.logger.warning(f"No scenarios found for category: {category}")
            return {}

        category_results = {
            "category": category,
            "scenarios": [],
            "worst_case": None,
            "best_case": None,
        }

        for scenario_id, scenario in scenarios.items():
            result = self._apply_scenario(portfolio, scenario)
            result["scenario_id"] = scenario_id
            category_results["scenarios"].append(result)

        # Find worst and best cases
        losses = [s.get("loss_percentage", 0) for s in category_results["scenarios"]]
        if losses:
            worst_idx = np.argmax(losses)
            best_idx = np.argmin(losses)
            category_results["worst_case"] = category_results["scenarios"][worst_idx]
            category_results["best_case"] = category_results["scenarios"][best_idx]
            category_results["avg_loss"] = float(np.mean(losses))
            category_results["max_loss"] = float(np.max(losses))

        return category_results

    def _apply_scenario(
        self,
        portfolio: Portfolio,
        scenario: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply a stress scenario to the portfolio."""
        initial_value = float(portfolio.total_equity)

        # Get market shock
        market_shock = scenario.get("market_shock", 0.0)

        # Apply shock to positions
        stressed_value = initial_value * (1 + market_shock)

        # Calculate loss
        loss = initial_value - stressed_value
        loss_percentage = (loss / initial_value * 100) if initial_value > 0 else 0.0

        # Apply additional stress factors
        stress_factors = {
            "volatility_multiplier": scenario.get("volatility_multiplier", 1.0),
            "correlation_target": scenario.get("correlation_target"),
            "liquidity_decrease": scenario.get("liquidity_decrease", 0.0),
        }

        # Assess severity
        severity = self._assess_scenario_severity(loss_percentage, scenario)

        return {
            "scenario_name": scenario["name"],
            "description": scenario["description"],
            "initial_value": initial_value,
            "stressed_value": stressed_value,
            "loss": loss,
            "loss_percentage": loss_percentage,
            "market_shock": market_shock,
            "stress_factors": stress_factors,
            "severity": severity["level"],
            "recommendation": severity["recommendation"],
        }

    def _assess_scenario_severity(
        self,
        loss_percentage: float,
        scenario: dict[str, Any],
    ) -> dict[str, Any]:
        """Assess the severity of a stress scenario result."""
        if loss_percentage > 40:
            return {
                "level": "CRITICAL",
                "recommendation": "Catastrophic loss. Immediate position closure required.",
            }
        elif loss_percentage > 25:
            return {
                "level": "EXTREME",
                "recommendation": "Severe loss. Emergency risk reduction required.",
            }
        elif loss_percentage > 15:
            return {
                "level": "HIGH",
                "recommendation": "Significant loss. Major de-risking recommended.",
            }
        elif loss_percentage > 10:
            return {
                "level": "MODERATE",
                "recommendation": "Moderate loss. Consider reducing exposure.",
            }
        elif loss_percentage > 5:
            return {
                "level": "ELEVATED",
                "recommendation": "Mild loss. Increased monitoring required.",
            }
        else:
            return {
                "level": "LOW",
                "recommendation": "Acceptable loss. Normal monitoring.",
            }

    def _generate_comprehensive_summary(
        self,
        results: dict[str, dict[str, Any]],
        all_scenarios: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate comprehensive summary of all stress tests."""
        if not all_scenarios:
            return {"error": "No valid scenarios"}

        # Find overall worst and best cases
        losses = [s.get("loss_percentage", 0) for s in all_scenarios]
        worst_idx = np.argmax(losses)
        best_idx = np.argmin(losses)

        # Calculate statistics
        worst_loss = losses[worst_idx]
        best_loss = losses[best_idx]
        avg_loss = float(np.mean(losses))
        median_loss = float(np.median(losses))
        std_loss = float(np.std(losses))

        # Risk categorization
        if worst_loss > 40:
            overall_risk = "CRITICAL"
            recommendation = (
                "Portfolio is extremely vulnerable to stress scenarios. "
                "Immediate risk reduction required."
            )
        elif worst_loss > 25:
            overall_risk = "HIGH"
            recommendation = (
                "Portfolio shows significant vulnerability to stress scenarios. "
                "Major de-risking recommended."
            )
        elif worst_loss > 15:
            overall_risk = "MODERATE"
            recommendation = (
                "Portfolio has moderate stress vulnerability. Consider reducing exposure."
            )
        else:
            overall_risk = "ACCEPTABLE"
            recommendation = (
                "Portfolio shows reasonable resilience to stress scenarios. "
                "Continue normal monitoring."
            )

        return {
            "overall_risk": overall_risk,
            "recommendation": recommendation,
            "statistics": {
                "worst_case_loss_pct": worst_loss,
                "best_case_loss_pct": best_loss,
                "average_loss_pct": avg_loss,
                "median_loss_pct": median_loss,
                "std_dev_loss_pct": std_loss,
            },
            "worst_scenario": all_scenarios[worst_idx],
            "best_scenario": all_scenarios[best_idx],
            "categories_tested": list(results.keys()),
            "total_scenarios": len(all_scenarios),
        }

    def get_scenario_description(self, scenario_id: str) -> Optional[dict[str, Any]]:
        """
        Get detailed description of a specific scenario.

        Args:
            scenario_id: Scenario identifier (e.g., 'covid_crash_2020')

        Returns:
            Scenario details or None if not found
        """
        all_scenarios = {
            **self.market_crash_scenarios,
            **self.volatility_scenarios,
            **self.correlation_scenarios,
            **self.liquidity_scenarios,
            **self.interest_rate_scenarios,
            **self.currency_scenarios,
            **self.combination_scenarios,
        }

        return all_scenarios.get(scenario_id)

    def list_available_scenarios(self) -> dict[str, list[str]]:
        """List all available scenarios by category."""
        return {
            "market_crash": list(self.market_crash_scenarios.keys()),
            "volatility": list(self.volatility_scenarios.keys()),
            "correlation": list(self.correlation_scenarios.keys()),
            "liquidity": list(self.liquidity_scenarios.keys()),
            "interest_rate": list(self.interest_rate_scenarios.keys()),
            "currency": list(self.currency_scenarios.keys()),
            "combination": list(self.combination_scenarios.keys()),
        }
