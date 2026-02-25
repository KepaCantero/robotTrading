"""
Monte Carlo Simulator Module

Extracted from comprehensive_backtest_runner.py for SRP compliance.

Provides Monte Carlo simulation functionality for backtesting:
- Realistic data generation with GARCH and regime switching
- Volatility-adjusted quote generation
- Scenario simulation for stress testing
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class MonteCarloSimulator:
    """
    Monte Carlo simulation for backtesting stress tests.

    Provides methods for:
    - Generating realistic synthetic data
    - Creating volatility-adjusted scenarios
    - Running multiple simulation iterations
    """

    # Default simulation parameters
    DEFAULT_N_SIMULATIONS = 100
    DEFAULT_N_DAYS = 252

    def __init__(
        self,
        random_state: int = 42,
        base_price: float = 100.0,
        base_volume: int = 50_000_000,
    ):
        """
        Initialize Monte Carlo simulator.

        Args:
            random_state: Random seed for reproducibility
            base_price: Base price for synthetic data
            base_volume: Base volume for synthetic data
        """
        self.random_state = random_state
        self.base_price = base_price
        self.base_volume = base_volume
        np.random.seed(random_state)

    def create_monte_carlo_quotes(
        self,
        base_quotes: Optional[List],
        volatility_multiplier: float = 1.0,
        use_regime_switching: bool = True,
    ) -> List:
        """
        Crear quotes modificados con volatilidad realista para Monte Carlo.

        Uses RealisticDataGenerator with GARCH and regime switching
        instead of simple random shocks.

        Args:
            base_quotes: Base quotes to modify (optional)
            volatility_multiplier: Multiplicador de volatilidad
            use_regime_switching: Whether to use regime switching

        Returns:
            Lista de quotes modificados con datos realistas
        """
        from app.backtesting.realistic_data_generator import RealisticDataGenerator

        # Si no hay quotes base, crear datos nuevos
        if not base_quotes:
            logger.warning("No base quotes available, generating new realistic data")
            gen = RealisticDataGenerator(
                seed=self.random_state,
                base_price=self.base_price,
                base_volume=self.base_volume,
            )

            start_date = datetime.now()
            return gen.generate_realistic_quotes(
                symbol='SYNTH',
                n_days=self.DEFAULT_N_DAYS,
                start_date=start_date,
                use_regime_switching=use_regime_switching,
            )

        # Usar generador realista para crear simulaciones Monte Carlo realistas
        gen = RealisticDataGenerator(
            seed=self.random_state,
            base_price=float(base_quotes[0].close),
            base_volume=int(base_quotes[0].volume) if base_quotes[0].volume else self.base_volume,
        )

        start_date = base_quotes[0].timestamp if base_quotes else datetime.now()

        modified_quotes = gen.generate_realistic_quotes(
            symbol=base_quotes[0].symbol if base_quotes else 'SYNTH',
            n_days=len(base_quotes),
            start_date=start_date,
            use_regime_switching=use_regime_switching,
            initial_regime='volatile',  # Usa régimen volátil para Monte Carlo
        )

        logger.info(
            f"Generated {len(modified_quotes)} realistic Monte Carlo quotes "
            f"(replacing simplistic random shocks)"
        )

        return modified_quotes

    def generate_volatility_scenarios(
        self,
        base_quotes: List,
        n_scenarios: int = 5,
        volatility_range: tuple = (0.5, 2.0),
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple volatility scenarios for stress testing.

        Args:
            base_quotes: Base quotes to modify
            n_scenarios: Number of scenarios to generate
            volatility_range: Range of volatility multipliers (min, max)

        Returns:
            List of scenario dictionaries with quotes and metadata
        """
        scenarios = []
        vol_multipliers = np.linspace(
            volatility_range[0],
            volatility_range[1],
            n_scenarios,
        )

        for i, vol_mult in enumerate(vol_multipliers):
            quotes = self.create_monte_carlo_quotes(
                base_quotes=base_quotes,
                volatility_multiplier=vol_mult,
            )

            scenarios.append({
                'scenario_id': i,
                'volatility_multiplier': vol_mult,
                'quotes': quotes,
                'description': f"Volatility {vol_mult:.1f}x baseline",
            })

        return scenarios

    def calculate_monte_carlo_statistics(
        self,
        simulation_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate aggregated statistics across Monte Carlo simulations.

        Args:
            simulation_results: List of results from each simulation

        Returns:
            Dictionary with aggregated statistics
        """
        if not simulation_results:
            return {}

        # Extract key metrics from all simulations
        returns = []
        sharpe_ratios = []
        max_drawdowns = []
        win_rates = []

        for result in simulation_results:
            metrics = result.get('metrics', {})
            if 'total_return' in metrics:
                returns.append(metrics['total_return'])
            if 'sharpe_ratio' in metrics:
                sharpe_ratios.append(metrics['sharpe_ratio'])
            if 'max_drawdown' in metrics:
                max_drawdowns.append(metrics['max_drawdown'])
            if 'win_rate' in metrics:
                win_rates.append(metrics['win_rate'])

        stats = {
            'n_simulations': len(simulation_results),
        }

        if returns:
            stats['return'] = {
                'mean': float(np.mean(returns)),
                'std': float(np.std(returns)),
                'min': float(np.min(returns)),
                'max': float(np.max(returns)),
                'percentile_5': float(np.percentile(returns, 5)),
                'percentile_95': float(np.percentile(returns, 95)),
            }

        if sharpe_ratios:
            stats['sharpe'] = {
                'mean': float(np.mean(sharpe_ratios)),
                'std': float(np.std(sharpe_ratios)),
                'min': float(np.min(sharpe_ratios)),
                'max': float(np.max(sharpe_ratios)),
            }

        if max_drawdowns:
            stats['drawdown'] = {
                'mean': float(np.mean(max_drawdowns)),
                'max': float(np.max(max_drawdowns)),
                'min': float(np.min(max_drawdowns)),
            }

        if win_rates:
            stats['win_rate'] = {
                'mean': float(np.mean(win_rates)),
                'std': float(np.std(win_rates)),
            }

        return stats


# Module-level convenience functions
def generate_monte_carlo_quotes(
    base_quotes: Optional[List],
    volatility_multiplier: float = 1.0,
    random_state: int = 42,
) -> List:
    """Convenience function for Monte Carlo quote generation."""
    simulator = MonteCarloSimulator(random_state=random_state)
    return simulator.create_monte_carlo_quotes(
        base_quotes=base_quotes,
        volatility_multiplier=volatility_multiplier,
    )
