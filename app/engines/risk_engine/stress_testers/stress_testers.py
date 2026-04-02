"""
Stress Testers

Implementa diferentes tipos de stress testing:
- Historical scenarios
- Monte Carlo scenarios
- Custom scenarios
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Union

import numpy as np

if TYPE_CHECKING:
    from app.domain.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


class BaseStressTester(ABC):
    """Clase base para stress testers."""

    def __init__(self, config: dict[str, int | float | str | bool]) -> None:
        """
        Inicializar stress tester.

        Args:
            config: Configuración del tester
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def run_stress_test(
        self, portfolio: Portfolio, scenario: dict[str, int | float | str]
    ) -> dict[str, int | float | str | bool | None]:
        """
        Ejecutar stress test.

        Args:
            portfolio: Portfolio a testear
            scenario: Escenario de stress

        Returns:
            Resultados del stress test
        """


class StressTester:
    """
    Stress Tester principal.

    Ejecuta múltiples tipos de stress tests.
    """

    def __init__(self, config: dict[str, int | float | str | bool]) -> None:
        """Inicializar stress tester."""
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Escenarios históricos predefinidos
        self.historical_scenarios = self._load_historical_scenarios()

        # Configuración
        n_scenarios = config.get("n_monte_carlo_scenarios", 1000)
        self.n_monte_carlo_scenarios: int = (
            n_scenarios if isinstance(n_scenarios, int) else int(n_scenarios)
        )

    def _load_historical_scenarios(self) -> dict[str, dict[str, int | float | str]]:
        """Cargar escenarios históricos predefinidos."""
        return {
            "2008_crisis": {
                "name": "2008 Financial Crisis",
                "market_shock": -0.50,  # -50% en mercado
                "volatility_multiplier": 3.0,
                "correlation_increase": 0.3,
                "description": "Simula crisis financiera de 2008",
            },
            "covid_19": {
                "name": "COVID-19 Pandemic",
                "market_shock": -0.35,  # -35% en mercado
                "volatility_multiplier": 2.5,
                "correlation_increase": 0.2,
                "description": "Simula impacto inicial de COVID-19",
            },
            "flash_crash": {
                "name": "Flash Crash (2010)",
                "market_shock": -0.10,  # -10% rápido
                "volatility_multiplier": 5.0,
                "correlation_increase": 0.1,
                "description": "Simula flash crash de 2010",
            },
            "black_monday": {
                "name": "Black Monday (1987)",
                "market_shock": -0.22,  # -22% en un día
                "volatility_multiplier": 4.0,
                "correlation_increase": 0.25,
                "description": "Simula Black Monday de 1987",
            },
        }

    def run_stress_tests(
        self, portfolio: Portfolio, scenario_types: list[str] | None = None
    ) -> dict[str, int | float | str | bool | None | list | dict]:
        """
        Ejecutar múltiples stress tests.

        Args:
            portfolio: Portfolio a testear
            scenario_types: Tipos de escenarios a ejecutar (None = todos)

        Returns:
            Resultados de todos los stress tests
        """
        if scenario_types is None:
            scenario_types = ["historical", "monte_carlo"]

        results: dict[str, int | float | str | bool | None | list | dict] = {}

        # Stress tests históricos
        if "historical" in scenario_types:
            results["historical"] = self._run_historical_stress_tests(portfolio)

        # Stress tests Monte Carlo
        if "monte_carlo" in scenario_types:
            results["monte_carlo"] = self._run_monte_carlo_stress_tests(portfolio)

        # Resumen
        results["summary"] = self._generate_summary(results, portfolio)

        return results

    def _run_historical_stress_tests(
        self, portfolio: Portfolio
    ) -> dict[str, int | float | str | bool | None | list | dict]:
        """Ejecutar stress tests históricos."""
        results: dict[str, int | float | str | bool | None | list | dict] = {}

        for scenario_id, scenario in self.historical_scenarios.items():
            try:
                result = self._apply_stress_scenario(portfolio, scenario)
                results[scenario_id] = {
                    **result,
                    "scenario_name": scenario["name"],
                    "description": scenario.get("description", ""),
                }
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                self.logger.error(f"Error ejecutando escenario {scenario_id}: {e}")
                results[scenario_id] = {"error": str(e)}

        return results

    def _run_monte_carlo_stress_tests(
        self, portfolio: Portfolio
    ) -> dict[str, int | float | str | bool | None | list | dict]:
        """Ejecutar stress tests Monte Carlo."""
        try:
            # Simular múltiples escenarios aleatorios
            mc_scenario_type = dict[str, Union[int, float, str]]
            stress_result_type = dict[str, Union[int, float, str, None, list, dict]]
            scenario_entry_type = dict[str, Union[mc_scenario_type, stress_result_type]]

            scenarios: list[scenario_entry_type] = []

            rng = np.random.default_rng(seed=42)

            for i in range(self.n_monte_carlo_scenarios):
                # Generar shock aleatorio
                market_shock = rng.normal(-0.1, 0.15)  # Distribución de shocks
                volatility_multiplier = rng.uniform(1.5, 4.0)

                scenario: mc_scenario_type = {
                    "name": f"Monte Carlo Scenario {i + 1}",
                    "market_shock": float(market_shock),
                    "volatility_multiplier": float(volatility_multiplier),
                    "correlation_increase": float(rng.uniform(0.1, 0.3)),
                }

                result = self._apply_stress_scenario(portfolio, scenario)
                entry: scenario_entry_type = {"scenario": scenario, "result": result}
                scenarios.append(entry)

            # Estadísticas de los escenarios
            portfolio_values: list[float] = []
            for s in scenarios:
                res = s["result"]
                if isinstance(res, dict):
                    val = res.get("stressed_portfolio_value")
                    if isinstance(val, (int, float)):
                        portfolio_values.append(float(val))

            return {
                "scenarios": scenarios[:10],  # Primeros 10 como ejemplo
                "statistics": {
                    "mean_portfolio_value": float(np.mean(portfolio_values)),
                    "std_portfolio_value": float(np.std(portfolio_values)),
                    "min_portfolio_value": float(np.min(portfolio_values)),
                    "max_portfolio_value": float(np.max(portfolio_values)),
                    "percentile_5": float(np.percentile(portfolio_values, 5)),
                    "percentile_95": float(np.percentile(portfolio_values, 95)),
                },
                "n_scenarios": self.n_monte_carlo_scenarios,
            }
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error en Monte Carlo stress tests: {e}", exc_info=True)
            return {"error": str(e)}

    def _apply_stress_scenario(
        self, portfolio: Portfolio, scenario: dict[str, int | float | str]
    ) -> dict[str, int | float | str | None | list | dict]:
        """
        Aplicar escenario de stress al portfolio.

        Args:
            portfolio: Portfolio original
            scenario: Escenario de stress

        Returns:
            Resultados del stress test
        """
        # Calcular valor inicial
        initial_value = float(portfolio.total_equity)

        # Aplicar shocks a posiciones
        stressed_positions: list[dict[str, float | str]] = []
        total_stressed_value = Decimal("0")

        raw_market_shock = scenario.get("market_shock", 0.0)
        market_shock: float = (
            raw_market_shock if isinstance(raw_market_shock, (int, float)) else 0.0
        )

        raw_vol_mult = scenario.get("volatility_multiplier", 1.0)
        volatility_multiplier: float = (
            raw_vol_mult if isinstance(raw_vol_mult, (int, float)) else 1.0
        )

        for position in portfolio.positions:
            # Aplicar shock de mercado
            stressed_price = position.market_price * Decimal(str(1 + market_shock))

            # Crear posición estresada
            stressed_position: dict[str, float | str] = {
                "symbol": position.symbol,
                "original_price": float(position.market_price),
                "stressed_price": float(stressed_price),
                "quantity": float(position.quantity),
                "original_value": float(position.market_value),
                "stressed_value": float(position.quantity * stressed_price),
            }

            stressed_positions.append(stressed_position)
            total_stressed_value += Decimal(str(stressed_position["stressed_value"]))

        # Calcular pérdida
        stressed_portfolio_value = float(portfolio.cash + total_stressed_value)
        loss = initial_value - stressed_portfolio_value
        loss_percentage = (loss / initial_value * 100) if initial_value > 0 else 0.0

        return {
            "initial_portfolio_value": initial_value,
            "stressed_portfolio_value": stressed_portfolio_value,
            "loss": loss,
            "loss_percentage": loss_percentage,
            "market_shock": market_shock,
            "volatility_multiplier": volatility_multiplier,
            "positions": stressed_positions,
        }

    def _generate_summary(
        self,
        results: dict[str, int | float | str | bool | None | list | dict],
        portfolio: Portfolio,
    ) -> dict[str, int | float | str | bool | None | dict]:
        """Generar resumen de resultados."""
        summary: dict[str, int | float | str | bool | None | dict] = {
            "initial_portfolio_value": float(portfolio.total_equity),
            "worst_case_scenario": None,
            "best_case_scenario": None,
            "average_loss": None,
            "max_loss": None,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Analizar resultados históricos
        if "historical" in results:
            historical = results["historical"]
            if isinstance(historical, dict):
                losses: list[dict[str, int | float | str]] = []

                for scenario_id, result in historical.items():
                    if isinstance(result, dict) and "loss_percentage" in result:
                        raw_lp = result["loss_percentage"]
                        lp_value: float = raw_lp if isinstance(raw_lp, (int, float)) else 0.0
                        raw_loss = result.get("loss", 0)
                        loss_value: float = raw_loss if isinstance(raw_loss, (int, float)) else 0.0

                        losses.append(
                            {
                                "scenario": scenario_id,
                                "loss_percentage": lp_value,
                                "loss": loss_value,
                            }
                        )

                if losses:
                    worst = max(losses, key=lambda x: x["loss_percentage"])
                    summary["worst_case_scenario"] = worst["scenario"]
                    summary["max_loss"] = worst["loss_percentage"]
                    summary["average_loss"] = float(
                        np.mean([var_l["loss_percentage"] for var_l in losses])
                    )

        # Analizar resultados Monte Carlo
        if "monte_carlo" in results:
            monte_carlo = results["monte_carlo"]
            if isinstance(monte_carlo, dict) and "statistics" in monte_carlo:
                mc_stats = monte_carlo["statistics"]
                if isinstance(mc_stats, dict):
                    raw_initial = summary["initial_portfolio_value"]
                    initial_value: float = (
                        raw_initial if isinstance(raw_initial, (int, float)) else 0.0
                    )
                    raw_mean = mc_stats["mean_portfolio_value"]
                    mean_val: float = raw_mean if isinstance(raw_mean, (int, float)) else 0.0
                    raw_p5 = mc_stats["percentile_5"]
                    p5_val: float = raw_p5 if isinstance(raw_p5, (int, float)) else 0.0
                    raw_p95 = mc_stats["percentile_95"]
                    p95_val: float = raw_p95 if isinstance(raw_p95, (int, float)) else 0.0

                    summary["monte_carlo"] = {
                        "expected_loss": initial_value - mean_val,
                        "worst_case_5pct": initial_value - p5_val,
                        "best_case_95pct": initial_value - p95_val,
                    }

        return summary
