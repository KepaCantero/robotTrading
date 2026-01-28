"""
Correlation Stress Testing - Hull Chapter 20

Implements correlation breakdown scenarios and stress testing.

Correlation risk is critical because:
1. Correlations tend toward 1.0 during market crises (contagion)
2. Diversification benefits disappear when needed most
3. Portfolio VaR can be severely underestimated in stress scenarios

Scenarios implemented:
- Correlation breakdown: All correlations → 1.0
- Sector contagion: Within-sector correlations spike
- Flight to quality: Risk assets correlate, safe havens decorrelate
- Asymmetric stress: Correlations increase only for negative returns

Reference: Hull, Options, Futures, and Other Derivatives, Chapter 20
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from app.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


class CorrelationStressTester:
    """
    Correlation Stress Tester.

    Tests portfolio resilience under correlation breakdown scenarios.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize correlation stress tester.

        Args:
            config: Configuration dictionary
        """
        config = config or {}
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Predefined stress scenarios
        self.scenarios = self._initialize_scenarios()

    def _initialize_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Initialize predefined correlation stress scenarios."""
        return {
            'correlation_breakdown': {
                'name': 'Perfect Correlation Breakdown',
                'description': 'All correlations move to 1.0 (worst-case contagion)',
                'correlation_target': 1.0,
                'apply_to_all': True,
            },
            'high_correlation': {
                'name': 'Elevated Correlations',
                'description': 'All correlations increase to 0.8 (elevated systemic risk)',
                'correlation_target': 0.8,
                'apply_to_all': True,
            },
            'sector_contagion': {
                'name': 'Sector Contagion',
                'description': 'Within-sector correlations spike to 0.9',
                'correlation_target': 0.9,
                'apply_to_sectors': True,
            },
            'asymmetric_stress': {
                'name': 'Asymmetric Downside Stress',
                'description': 'Correlations increase only during negative returns',
                'stress_negative_only': True,
            },
            'flight_to_quality': {
                'name': 'Flight to Quality',
                'description': 'Risk assets correlate (0.9), safe havens decorrelate',
                'risk_correlation': 0.9,
                'safe_haven_correlation': 0.0,
            },
        }

    def run_correlation_stress_tests(
        self,
        portfolio: Portfolio,
        current_correlation_matrix: Dict[str, Dict[str, float]],
        returns_history: Dict[str, List[float]],
        volatilities: Dict[str, float],
        scenario_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run correlation stress tests on portfolio.

        Args:
            portfolio: Portfolio to test
            current_correlation_matrix: Current correlation matrix
            returns_history: Historical returns by symbol
            volatilities: Current volatilities by symbol
            scenario_names: Scenarios to run (None = all)

        Returns:
            Stress test results
        """
        try:
            if scenario_names is None:
                scenario_names = list(self.scenarios.keys())

            results = {}
            portfolio_symbols = [pos.symbol for pos in portfolio.positions]

            for scenario_name in scenario_names:
                if scenario_name not in self.scenarios:
                    self.logger.warning(f'Unknown scenario: {scenario_name}')
                    continue

                scenario = self.scenarios[scenario_name]
                scenario_result = self._apply_correlation_scenario(
                    portfolio,
                    current_correlation_matrix,
                    returns_history,
                    volatilities,
                    scenario,
                )

                results[scenario_name] = scenario_result

            # Generate summary
            summary = self._generate_stress_summary(results, portfolio)

            return {
                'scenarios': results,
                'summary': summary,
                'portfolio_symbols': portfolio_symbols,
                'timestamp': self._get_timestamp(),
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f'Error running correlation stress tests: {e}', exc_info=True)
            return {'error': str(e)}

    def _apply_correlation_scenario(
        self,
        portfolio: Portfolio,
        current_correlation_matrix: Dict[str, Dict[str, float]],
        returns_history: Dict[str, List[float]],
        volatilities: Dict[str, float],
        scenario: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply a single correlation stress scenario."""
        # Create stressed correlation matrix
        stressed_matrix = self._create_stressed_correlation_matrix(
            current_correlation_matrix,
            portfolio,
            scenario,
        )

        # Calculate portfolio variance under stressed correlations
        stressed_variance = self._calculate_portfolio_variance(
            portfolio,
            stressed_matrix,
            volatilities,
        )

        # Calculate current portfolio variance
        current_variance = self._calculate_portfolio_variance(
            portfolio,
            current_correlation_matrix,
            volatilities,
        )

        # Calculate stress impact
        variance_increase = stressed_variance - current_variance
        variance_increase_pct = (
            (variance_increase / current_variance * 100) if current_variance > 0 else 0
        )

        # VaR impact (assuming normal distribution)
        from scipy import stats

        z_score = stats.norm.ppf(0.95)
        var_increase = z_score * (np.sqrt(stressed_variance) - np.sqrt(current_variance))

        return {
            'scenario_name': scenario['name'],
            'description': scenario['description'],
            'current_variance': current_variance,
            'stressed_variance': stressed_variance,
            'variance_increase': variance_increase,
            'variance_increase_pct': variance_increase_pct,
            'var_impact': var_increase,
            'stressed_correlation_matrix': stressed_matrix,
            'risk_assessment': self._assess_stress_impact(variance_increase_pct),
        }

    def _create_stressed_correlation_matrix(
        self,
        current_matrix: Dict[str, Dict[str, float]],
        portfolio: Portfolio,
        scenario: Dict[str, Any],
    ) -> Dict[str, Dict[str, float]]:
        """Create stressed correlation matrix based on scenario."""
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

        # Apply scenario rules
        if scenario.get('apply_to_all', False):
            target_corr = scenario['correlation_target']
            for symbol1 in portfolio_symbols:
                for symbol2 in portfolio_symbols:
                    if symbol1 != symbol2:
                        stressed_matrix[symbol1][symbol2] = target_corr

        elif scenario.get('apply_to_sectors', False):
            # Apply within sectors (simplified: all same sector for now)
            target_corr = scenario['correlation_target']
            for symbol1 in portfolio_symbols:
                for symbol2 in portfolio_symbols:
                    if symbol1 != symbol2:
                        stressed_matrix[symbol1][symbol2] = target_corr

        elif scenario.get('stress_negative_only', False):
            # Asymmetric: increase correlations only for downside
            # Use current correlations but note they'd be higher in stress
            for symbol1 in portfolio_symbols:
                for symbol2 in portfolio_symbols:
                    if symbol1 != symbol2:
                        current_corr = current_matrix.get(symbol1, {}).get(symbol2, 0.5)
                        # Increase by 50% but cap at 1.0
                        stressed_corr = min(1.0, current_corr * 1.5)
                        stressed_matrix[symbol1][symbol2] = stressed_corr

        elif 'risk_correlation' in scenario:
            # Flight to quality: differentiate risk vs safe haven
            # Simplified: treat all as risk assets
            target_corr = scenario['risk_correlation']
            for symbol1 in portfolio_symbols:
                for symbol2 in portfolio_symbols:
                    if symbol1 != symbol2:
                        stressed_matrix[symbol1][symbol2] = target_corr

        return stressed_matrix

    def _calculate_portfolio_variance(
        self,
        portfolio: Portfolio,
        correlation_matrix: Dict[str, Dict[str, float]],
        volatilities: Dict[str, float],
    ) -> float:
        """
        Calculate portfolio variance given correlations and volatilities.

        Formula:
        σ²_p = Σᵢ Σⱼ wᵢ wⱼ σᵢ σⱼ ρᵢⱼ

        Where:
        - wᵢ = weight of asset i
        - σᵢ = volatility of asset i
        - ρᵢⱼ = correlation between i and j
        """
        if portfolio.total_equity == 0:
            return 0.0

        weights = {}
        for position in portfolio.positions:
            weights[position.symbol] = float(position.market_value / portfolio.total_equity)

        variance = 0.0
        symbols = list(weights.keys())

        for symbol1 in symbols:
            for symbol2 in symbols:
                w1 = weights[symbol1]
                w2 = weights[symbol2]
                sigma1 = volatilities.get(symbol1, 0.2)
                sigma2 = volatilities.get(symbol2, 0.2)

                # Get correlation
                if symbol1 == symbol2:
                    correlation = 1.0
                else:
                    correlation = correlation_matrix.get(symbol1, {}).get(symbol2, 0.0)
                    if correlation is None:
                        correlation = 0.0  # Default to uncorrelated if missing

                variance += w1 * w2 * sigma1 * sigma2 * correlation

        return variance

    def _assess_stress_impact(self, variance_increase_pct: float) -> Dict[str, Any]:
        """Assess the severity of stress impact."""
        if variance_increase_pct > 100:
            severity = 'CRITICAL'
            action = 'IMMEDIATE position reduction required'
        elif variance_increase_pct > 50:
            severity = 'HIGH'
            action = 'Significant de-risking recommended'
        elif variance_increase_pct > 25:
            severity = 'MODERATE'
            action = 'Monitor and consider reducing exposure'
        elif variance_increase_pct > 10:
            severity = 'ELEVATED'
            action = 'Increased vigilance required'
        else:
            severity = 'LOW'
            action = 'Normal monitoring sufficient'

        return {
            'severity': severity,
            'recommended_action': action,
            'variance_increase_pct': variance_increase_pct,
        }

    def _generate_stress_summary(
        self,
        results: Dict[str, Dict[str, Any]],
        portfolio: Portfolio,
    ) -> Dict[str, Any]:
        """Generate summary of stress test results."""
        summary = {
            'worst_scenario': None,
            'best_scenario': None,
            'average_variance_increase': 0.0,
            'max_variance_increase': 0.0,
            'scenario_count': len(results),
        }

        if not results:
            return summary

        variance_increases = []

        for scenario_name, result in results.items():
            if 'variance_increase_pct' in result:
                variance_increases.append(
                    {
                        'scenario': scenario_name,
                        'increase_pct': result['variance_increase_pct'],
                        'severity': result.get('risk_assessment', {}).get('severity', 'UNKNOWN'),
                    }
                )

        if variance_increases:
            # Find worst and best
            worst = max(variance_increases, key=lambda x: x['increase_pct'])
            best = min(variance_increases, key=lambda x: x['increase_pct'])

            summary['worst_scenario'] = worst
            summary['best_scenario'] = best
            summary['max_variance_increase'] = worst['increase_pct']
            summary['average_variance_increase'] = np.mean(
                [v['increase_pct'] for v in variance_increases]
            )

        # Overall assessment
        max_increase = summary['max_variance_increase']
        if max_increase > 100:
            summary['overall_risk'] = 'CRITICAL'
            summary['recommendation'] = 'Portfolio highly vulnerable to correlation breakdown'
        elif max_increase > 50:
            summary['overall_risk'] = 'HIGH'
            summary['recommendation'] = 'Significant correlation risk present'
        elif max_increase > 25:
            summary['overall_risk'] = 'MODERATE'
            summary['recommendation'] = 'Moderate correlation vulnerability'
        else:
            summary['overall_risk'] = 'LOW'
            summary['recommendation'] = 'Correlation risk within acceptable bounds'

        return summary

    def calculate_correlation_breakdown_var(
        self,
        portfolio: Portfolio,
        volatilities: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Calculate VaR under perfect correlation breakdown (worst case).

        This represents the maximum possible portfolio VaR if all correlations go to 1.0.

        Args:
            portfolio: Portfolio to analyze
            volatilities: Asset volatilities

        Returns:
            Breakdown VaR analysis
        """
        if portfolio.total_equity == 0:
            return {'error': 'Portfolio value is zero'}

        # Create perfect correlation matrix
        symbols = [pos.symbol for pos in portfolio.positions]
        perfect_correlation = {}

        for symbol1 in symbols:
            perfect_correlation[symbol1] = {}
            for symbol2 in symbols:
                perfect_correlation[symbol1][symbol2] = 1.0

        # Calculate portfolio variance under perfect correlation
        breakdown_variance = self._calculate_portfolio_variance(
            portfolio, perfect_correlation, volatilities
        )

        # Calculate VaR (95% confidence)
        from scipy import stats

        z_score = stats.norm.ppf(0.95)
        breakdown_volatility = np.sqrt(breakdown_variance)
        breakdown_var = z_score * breakdown_volatility

        # Calculate current (uncorrelated) variance for comparison
        uncorrelated_matrix = {}
        for symbol1 in symbols:
            uncorrelated_matrix[symbol1] = {}
            for symbol2 in symbols:
                if symbol1 == symbol2:
                    uncorrelated_matrix[symbol1][symbol2] = 1.0
                else:
                    uncorrelated_matrix[symbol1][symbol2] = 0.0

        uncorrelated_variance = self._calculate_portfolio_variance(
            portfolio, uncorrelated_matrix, volatilities
        )
        uncorrelated_volatility = np.sqrt(uncorrelated_variance)
        uncorrelated_var = z_score * uncorrelated_volatility

        # VaR increase due to correlation breakdown
        var_increase = breakdown_var - uncorrelated_var
        var_increase_pct = (var_increase / uncorrelated_var * 100) if uncorrelated_var > 0 else 0

        return {
            'breakdown_var': breakdown_var,
            'uncorrelated_var': uncorrelated_var,
            'var_increase': var_increase,
            'var_increase_pct': var_increase_pct,
            'breakdown_volatility': breakdown_volatility,
            'uncorrelated_volatility': uncorrelated_volatility,
            'interpretation': self._interpret_breakdown_risk(var_increase_pct),
        }

    def _interpret_breakdown_risk(self, var_increase_pct: float) -> str:
        """Interpret correlation breakdown risk."""
        if var_increase_pct > 200:
            return (
                f'CRITICAL: VaR would increase by {var_increase_pct:.1f}% under '
                f'correlation breakdown. Portfolio lacks true diversification.'
            )
        elif var_increase_pct > 100:
            return (
                f'HIGH: VaR would increase by {var_increase_pct:.1f}% under '
                f'correlation breakdown. Significant diversification erosion risk.'
            )
        elif var_increase_pct > 50:
            return (
                f'MODERATE: VaR would increase by {var_increase_pct:.1f}% under '
                f'correlation breakdown. Monitor correlation exposure.'
            )
        else:
            return (
                f'LOW: VaR would increase by only {var_increase_pct:.1f}% under '
                f'correlation breakdown. Good diversification resilience.'
            )

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.utcnow().isoformat()
