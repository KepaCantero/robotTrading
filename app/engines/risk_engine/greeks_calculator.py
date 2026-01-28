"""
Options Greeks Calculator - Hull Chapters 17 and 19

Implements comprehensive Greeks calculation for options risk management.

Greeks measure the sensitivity of option prices to various factors:
- Delta (Δ): Price sensitivity to underlying price changes
- Gamma (Γ): Delta sensitivity to underlying price changes (convexity)
- Theta (Θ): Time sensitivity (time decay)
- Vega (ν): Volatility sensitivity
- Rho (ρ): Interest rate sensitivity

Higher-order Greeks:
- Vanna: Delta sensitivity to volatility
- Vomma: Vega sensitivity to volatility (volga)
- Charm: Delta sensitivity to time
- Veta: Vega sensitivity to time

Reference:
- Hull, Options, Futures, and Other Derivatives, Chapters 17-19
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
from scipy.stats import norm

logger = logging.getLogger(__name__)


class GreeksCalculator:
    """
    Options Greeks Calculator.

    Calculates all major Greeks for European options using Black-Scholes-Merton.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Greeks calculator.

        Args:
            config: Configuration dictionary
        """
        config = config or {}
        self.risk_free_rate = config.get('risk_free_rate', 0.05)
        self.dividend_yield = config.get('dividend_yield', 0.0)
        self.logger = logging.getLogger(self.__class__.__name__)

    def calculate_all_greeks(
        self,
        option_type: str,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,  # In years
        volatility: float,  # Annualized
        risk_free_rate: Optional[float] = None,
        dividend_yield: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate all Greeks for an option.

        Args:
            option_type: 'call' or 'put'
            spot_price: Current underlying price
            strike_price: Option strike price
            time_to_expiry: Time to expiration (years)
            volatility: Implied volatility (decimal)
            risk_free_rate: Risk-free rate (optional, uses default if None)
            dividend_yield: Dividend yield (optional, uses default if None)

        Returns:
            Dict with all Greeks values
        """
        try:
            r = risk_free_rate if risk_free_rate is not None else self.risk_free_rate
            q = dividend_yield if dividend_yield is not None else self.dividend_yield

            S = spot_price
            K = strike_price
            T = time_to_expiry
            sigma = volatility

            if T <= 0:
                return {'error': 'Option must have positive time to expiry'}

            if sigma <= 0:
                return {'error': 'Volatility must be positive'}

            # Calculate d1 and d2 (Black-Scholes parameters)
            d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)

            # Calculate primary Greeks
            delta = self._calculate_delta(option_type, d1, q, T)
            gamma = self._calculate_gamma(d1, S, sigma, T)
            theta = self._calculate_theta(option_type, S, K, r, q, sigma, T, d1, d2)
            vega = self._calculate_vega(S, d1, T)
            rho = self._calculate_rho(option_type, K, r, T, d2)

            # Calculate higher-order Greeks
            vanna = self._calculate_vanna(d1, d2, sigma)
            vomma = self._calculate_vomma(d1, d2, sigma)
            charm = self._calculate_charm(option_type, d1, d2, sigma, T, r, q)
            veta = self._calculate_veta(d1, sigma, T, r, q)

            # Calculate option price (for context)
            option_price = self._calculate_option_price(option_type, S, K, T, r, q, sigma, d1, d2)

            return {
                'option_type': option_type,
                'spot_price': S,
                'strike_price': K,
                'time_to_expiry': T,
                'volatility': sigma,
                'option_price': option_price,
                'primary_greeks': {
                    'delta': delta,
                    'gamma': gamma,
                    'theta': theta,  # Per day
                    'theta_annual': theta * 365,  # Per year
                    'vega': vega,  # Per 1% volatility change
                    'rho': rho,  # Per 1% rate change
                },
                'higher_order_greeks': {
                    'vanna': vanna,
                    'vomma': vomma,
                    'charm': charm,
                    'veta': veta,
                },
                'risk_metrics': self._calculate_risk_metrics(delta, gamma, vega, S),
                'timestamp': datetime.utcnow().isoformat(),
            }

        except (ValueError, TypeError, ZeroDivisionError) as e:
            self.logger.error(f'Error calculating Greeks: {e}', exc_info=True)
            return {'error': str(e)}

    def _calculate_delta(
        self,
        option_type: str,
        d1: float,
        q: float,
        T: float,
    ) -> float:
        """Calculate Delta."""
        if option_type == 'call':
            return np.exp(-q * T) * norm.cdf(d1)
        elif option_type == 'put':
            return np.exp(-q * T) * (norm.cdf(d1) - 1)
        else:
            raise ValueError(f'Unknown option type: {option_type}')

    def _calculate_gamma(
        self,
        d1: float,
        S: float,
        sigma: float,
        T: float,
    ) -> float:
        """Calculate Gamma (same for calls and puts)."""
        return norm.pdf(d1) / (S * sigma * np.sqrt(T))

    def _calculate_theta(
        self,
        option_type: str,
        S: float,
        K: float,
        r: float,
        q: float,
        sigma: float,
        T: float,
        d1: float,
        d2: float,
    ) -> float:
        """
        Calculate Theta (per day).

        Returns negative value representing time decay.
        """
        term1 = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))

        if option_type == 'call':
            term2 = -r * K * np.exp(-r * T) * norm.cdf(d2)
            term3 = q * S * np.exp(-q * T) * norm.cdf(d1)
            theta = (term1 + term2 - term3) / 365  # Per day
        elif option_type == 'put':
            term2 = -r * K * np.exp(-r * T) * norm.cdf(-d2)
            term3 = q * S * np.exp(-q * T) * norm.cdf(-d1)
            theta = (term1 + term2 + term3) / 365  # Per day
        else:
            raise ValueError(f'Unknown option type: {option_type}')

        return theta

    def _calculate_vega(
        self,
        S: float,
        d1: float,
        T: float,
    ) -> float:
        """
        Calculate Vega.

        Represents change in option price for 1% (0.01) change in volatility.
        """
        return S * norm.pdf(d1) * np.sqrt(T) / 100  # Per 1% change

    def _calculate_rho(
        self,
        option_type: str,
        K: float,
        r: float,
        T: float,
        d2: float,
    ) -> float:
        """
        Calculate Rho.

        Represents change in option price for 1% (0.01) change in interest rate.
        """
        if option_type == 'call':
            rho = K * T * np.exp(-r * T) * norm.cdf(d2)
        elif option_type == 'put':
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2)
        else:
            raise ValueError(f'Unknown option type: {option_type}')

        return rho / 100  # Per 1% change

    def _calculate_vanna(self, d1: float, d2: float, sigma: float) -> float:
        """
        Calculate Vanna.

        Vanna = Delta sensitivity to volatility = Vega sensitivity to spot price.
        """
        return -norm.pdf(d1) * d2 / sigma

    def _calculate_vomma(self, d1: float, d2: float, sigma: float) -> float:
        """
        Calculate Vomma (Volga).

        Vomma = Vega sensitivity to volatility (volatility convexity).
        """
        return norm.pdf(d1) * d1 * d2 / sigma

    def _calculate_charm(
        self,
        option_type: str,
        d1: float,
        d2: float,
        sigma: float,
        T: float,
        r: float,
        q: float,
    ) -> float:
        """
        Calculate Charm.

        Charm = Delta sensitivity to time passage.
        """
        term1 = norm.pdf(d1) * (2 * r * T - d2 * sigma * np.sqrt(T)) / (2 * T * sigma * np.sqrt(T))

        if option_type == 'call':
            charm = q * np.exp(-q * T) * norm.cdf(d1) - term1
        elif option_type == 'put':
            charm = -q * np.exp(-q * T) * norm.cdf(-d1) - term1
        else:
            raise ValueError(f'Unknown option type: {option_type}')

        return charm / 365  # Per day

    def _calculate_veta(
        self,
        d1: float,
        sigma: float,
        T: float,
        r: float,
        q: float,
    ) -> float:
        """
        Calculate Veta.

        Veta = Vega sensitivity to time.
        """
        term = norm.pdf(d1) * (r - q + (d1 / (2 * T)) * sigma**2) / (sigma * T)
        return term / 365  # Per day

    def _calculate_option_price(
        self,
        option_type: str,
        S: float,
        K: float,
        T: float,
        r: float,
        q: float,
        sigma: float,
        d1: float,
        d2: float,
    ) -> float:
        """Calculate Black-Scholes option price."""
        if option_type == 'call':
            price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        elif option_type == 'put':
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
        else:
            raise ValueError(f'Unknown option type: {option_type}')

        return price

    def _calculate_risk_metrics(
        self,
        delta: float,
        gamma: float,
        vega: float,
        spot_price: float,
    ) -> Dict[str, Any]:
        """Calculate portfolio risk metrics from Greeks."""
        # Delta-adjusted exposure
        delta_exposure = delta * spot_price

        # Gamma risk (convexity)
        # Gamma > 0: benefits from large moves (long calls/puts)
        # Gamma < 0: hurt by large moves (short options)
        gamma_profile = 'long_gamma' if gamma > 0 else 'short_gamma'

        # Vega exposure
        # Vega > 0: benefits from volatility increase
        # Vega < 0: hurt by volatility increase
        vega_profile = 'long_vega' if vega > 0 else 'short_vega'

        return {
            'delta_exposure': delta_exposure,
            'gamma_profile': gamma_profile,
            'vega_profile': vega_profile,
            'risk_interpretation': self._interpret_greeks(delta, gamma, vega),
        }

    def _interpret_greeks(
        self,
        delta: float,
        gamma: float,
        vega: float,
    ) -> str:
        """Generate human-readable interpretation of Greeks profile."""
        interpretations = []

        # Delta interpretation
        if abs(delta) < 0.3:
            interpretations.append('Low directional exposure (at-the-money)')
        elif abs(delta) > 0.7:
            interpretations.append('High directional exposure (deep in-the-money)')
        else:
            interpretations.append('Moderate directional exposure')

        # Gamma interpretation
        if gamma > 0.01:
            interpretations.append('Positive gamma - benefits from volatility')
        elif gamma < -0.01:
            interpretations.append('Negative gamma - vulnerable to large moves')
        else:
            interpretations.append('Low gamma risk')

        # Vega interpretation
        if vega > 0.1:
            interpretations.append('Long volatility - profits from vol increase')
        elif vega < -0.1:
            interpretations.append('Short volatility - exposed to vol spikes')
        else:
            interpretations.append('Low volatility exposure')

        return '. '.join(interpretations)

    def calculate_portfolio_greeks(
        self,
        positions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate aggregate Greeks for an options portfolio.

        Args:
            positions: List of position dicts with:
                - option_type, spot_price, strike_price, time_to_expiry,
                  volatility, quantity, etc.

        Returns:
            Portfolio-level Greeks
        """
        try:
            portfolio_greeks = {
                'total_delta': 0.0,
                'total_gamma': 0.0,
                'total_theta': 0.0,
                'total_vega': 0.0,
                'total_rho': 0.0,
                'positions': [],
            }

            for position in positions:
                # Calculate Greeks for this position
                greeks = self.calculate_all_greeks(
                    option_type=position['option_type'],
                    spot_price=position['spot_price'],
                    strike_price=position['strike_price'],
                    time_to_expiry=position['time_to_expiry'],
                    volatility=position['volatility'],
                    risk_free_rate=position.get('risk_free_rate'),
                    dividend_yield=position.get('dividend_yield'),
                )

                if 'error' in greeks:
                    continue

                quantity = position.get('quantity', 1)

                # Add to portfolio totals (multiply by quantity)
                portfolio_greeks['total_delta'] += greeks['primary_greeks']['delta'] * quantity
                portfolio_greeks['total_gamma'] += greeks['primary_greeks']['gamma'] * quantity
                portfolio_greeks['total_theta'] += greeks['primary_greeks']['theta'] * quantity
                portfolio_greeks['total_vega'] += greeks['primary_greeks']['vega'] * quantity
                portfolio_greeks['total_rho'] += greeks['primary_greeks']['rho'] * quantity

                portfolio_greeks['positions'].append(
                    {
                        'symbol': position.get('symbol', 'UNKNOWN'),
                        'quantity': quantity,
                        'greeks': greeks['primary_greeks'],
                    }
                )

            # Generate portfolio-level interpretation
            portfolio_greeks['analysis'] = self._analyze_portfolio_greeks(portfolio_greeks)

            return portfolio_greeks

        except (ValueError, TypeError, KeyError) as e:
            self.logger.error(f'Error calculating portfolio Greeks: {e}', exc_info=True)
            return {'error': str(e)}

    def _analyze_portfolio_greeks(self, portfolio_greeks: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze portfolio Greeks profile."""
        analysis = {
            'delta_neutral': abs(portfolio_greeks['total_delta']) < 0.1,
            'gamma_exposure': (
                'long_gamma' if portfolio_greeks['total_gamma'] > 0 else 'short_gamma'
            ),
            'theta_profile': 'positive' if portfolio_greeks['total_theta'] > 0 else 'negative',
            'vega_exposure': 'long_vega' if portfolio_greeks['total_vega'] > 0 else 'short_vega',
            'daily_theta_decay': portfolio_greeks['total_theta'],
        }

        # Risk assessment
        risks = []
        if abs(portfolio_greeks['total_delta']) > 10:
            risks.append(f'High directional exposure: delta={portfolio_greeks["total_delta"]:.2f}')

        if portfolio_greeks['total_gamma'] < -1:
            risks.append(f'Short gamma exposure: gamma={portfolio_greeks["total_gamma"]:.4f}')

        if portfolio_greeks['total_theta'] < -100:
            risks.append(f'High time decay: theta={portfolio_greeks["total_theta"]:.2f}/day')

        if portfolio_greeks['total_vega'] < -50:
            risks.append(f'Short volatility exposure: vega={portfolio_greeks["total_vega"]:.2f}')

        analysis['risk_warnings'] = risks
        analysis['overall_risk'] = (
            'HIGH' if len(risks) > 2 else ('MODERATE' if len(risks) > 0 else 'LOW')
        )

        return analysis

    def calculate_delta_hedge_ratio(
        self,
        option_position: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate delta hedge ratio for neutralizing directional risk.

        Determines how many shares of underlying to buy/sell to hedge an option position.

        Args:
            option_position: Option position details

        Returns:
            Hedge ratio and recommendations
        """
        try:
            greeks = self.calculate_all_greeks(**option_position)

            if 'error' in greeks:
                return greeks

            delta = greeks['primary_greeks']['delta']
            quantity = option_position.get('quantity', 1)

            # Hedge ratio: shares needed to hedge
            hedge_ratio = -delta * quantity

            return {
                'option_delta': delta,
                'option_quantity': quantity,
                'hedge_ratio': hedge_ratio,
                'shares_to_trade': abs(hedge_ratio),
                'action': 'BUY' if hedge_ratio > 0 else 'SELL_SHORT',
                'hedge_effectiveness': self._evaluate_hedge_effectiveness(greeks),
            }

        except (ValueError, TypeError, KeyError) as e:
            self.logger.error(f'Error calculating hedge ratio: {e}', exc_info=True)
            return {'error': str(e)}

    def _evaluate_hedge_effectiveness(self, greeks: Dict[str, Any]) -> str:
        """Evaluate delta hedge effectiveness considering gamma."""
        gamma = greeks['primary_greeks']['gamma']

        if abs(gamma) < 0.001:
            return 'EXCELLENT - Low gamma, hedge remains effective'
        elif abs(gamma) < 0.01:
            return 'GOOD - Moderate gamma, hedge needs periodic adjustment'
        else:
            return 'POOR - High gamma, hedge requires frequent rebalancing'

    def validate_greeks_consistency(
        self,
        greeks_result: Dict[str, Any],
        tolerance: float = 0.01,
    ) -> Dict[str, Any]:
        """
        Validate Greeks calculations for consistency and correctness.

        Performs several validation checks:
        1. Put-call parity for matching options
        2. Gamma positivity (should always be positive)
        3. Vega positivity (should always be positive)
        4. Reasonable Greeks ranges
        5. Cross-Greek relationships

        Args:
            greeks_result: Result from calculate_all_greeks
            tolerance: Tolerance for numerical comparisons

        Returns:
            Validation results with any issues found
        """
        if 'error' in greeks_result:
            return {'valid': False, 'error': greeks_result['error']}

        validation_issues = []
        warnings = []

        primary_greeks = greeks_result.get('primary_greeks', {})
        higher_order = greeks_result.get('higher_order_greeks', {})

        # Extract Greeks
        delta = primary_greeks.get('delta')
        gamma = primary_greeks.get('gamma')
        theta = primary_greeks.get('theta')
        vega = primary_greeks.get('vega')
        rho = primary_greeks.get('rho')

        option_type = greeks_result.get('option_type')

        # 1. Gamma should always be positive
        if gamma is not None and gamma <= 0:
            validation_issues.append(f'Gamma must be positive, got {gamma}')

        # 2. Vega should always be positive
        if vega is not None and vega <= 0:
            validation_issues.append(f'Vega must be positive, got {vega}')

        # 3. Delta range validation
        if delta is not None:
            if option_type == 'call':
                if not (0 <= delta <= 1):
                    warnings.append(f'Call delta should be in [0,1], got {delta}')
            elif option_type == 'put':
                if not (-1 <= delta <= 0):
                    warnings.append(f'Put delta should be in [-1,0], got {delta}')

        # 4. Theta should be negative (long options lose value with time)
        if theta is not None and theta > 0:
            warnings.append(f'Theta typically negative for long options, got {theta}')

        # 5. Reasonable ranges check
        if gamma is not None and gamma > 1.0:
            warnings.append(f'Gamma unusually high: {gamma}')

        if vega is not None and abs(vega) > 10.0:
            warnings.append(f'Vega unusually high: {vega}')

        # 6. Cross-Greek relationships
        # High gamma should correlate with high vega near ATM
        time_to_expiry = greeks_result.get('time_to_expiry')
        spot_price = greeks_result.get('spot_price')
        strike_price = greeks_result.get('strike_price')

        if time_to_expiry and spot_price and strike_price:
            moneyness = spot_price / strike_price

            # Near ATM options should have higher gamma
            if 0.9 <= moneyness <= 1.1 and time_to_expiry < 0.25:
                if gamma is not None and gamma < 0.05:
                    warnings.append(f'Low gamma {gamma} for near-term ATM option - expected higher')

        # 7. Higher-order Greeks validation
        vomma = higher_order.get('vomma')
        if vomma is not None:
            # Vomma can be positive or negative, but extreme values warrant warning
            if abs(vomma) > 1.0:
                warnings.append(f'Extreme vomma value: {vomma}')

        return {
            'valid': len(validation_issues) == 0,
            'validation_issues': validation_issues,
            'warnings': warnings,
            'greeks_checked': {
                'delta': delta,
                'gamma': gamma,
                'theta': theta,
                'vega': vega,
                'rho': rho,
            },
            'validation_timestamp': greeks_result.get('timestamp'),
        }

    def validate_greeks_risk_limits(
        self,
        portfolio_greeks: Dict[str, Any],
        limits: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Validate portfolio Greeks against risk limits.

        Args:
            portfolio_greeks: Result from calculate_portfolio_greeks
            limits: Risk limits for each Greek

        Returns:
            Risk limit validation results
        """
        if 'error' in portfolio_greeks:
            return {'valid': False, 'error': portfolio_greeks['error']}

        # Default risk limits
        if limits is None:
            limits = {
                'max_delta': 100,  # Max net delta exposure
                'max_gamma': 5,  # Max gamma exposure
                'max_theta': -1000,  # Max daily theta decay (negative)
                'max_vega': 500,  # Max vega exposure
                'max_rho': 200,  # Max rho exposure
            }

        violations = []
        warnings = []

        total_delta = portfolio_greeks.get('total_delta', 0)
        total_gamma = portfolio_greeks.get('total_gamma', 0)
        total_theta = portfolio_greeks.get('total_theta', 0)
        total_vega = portfolio_greeks.get('total_vega', 0)
        total_rho = portfolio_greeks.get('total_rho', 0)

        # Check Delta
        max_delta = limits.get('max_delta', 100)
        if abs(total_delta) > max_delta:
            violations.append(
                {
                    'greek': 'delta',
                    'value': total_delta,
                    'limit': max_delta,
                    'excess': abs(total_delta) - max_delta,
                    'severity': 'HIGH' if abs(total_delta) > max_delta * 1.5 else 'MEDIUM',
                }
            )

        # Check Gamma
        max_gamma = limits.get('max_gamma', 5)
        if abs(total_gamma) > max_gamma:
            severity = 'CRITICAL' if total_gamma < -max_gamma * 1.5 else 'HIGH'
            violations.append(
                {
                    'greek': 'gamma',
                    'value': total_gamma,
                    'limit': max_gamma,
                    'excess': abs(total_gamma) - max_gamma,
                    'severity': severity,
                    'note': 'Short gamma exposure is particularly dangerous',
                }
            )

        # Check Theta
        max_theta = limits.get('max_theta', -1000)
        if total_theta < max_theta:
            violations.append(
                {
                    'greek': 'theta',
                    'value': total_theta,
                    'limit': max_theta,
                    'excess': max_theta - total_theta,
                    'severity': 'MEDIUM',
                    'note': 'Excessive time decay',
                }
            )

        # Check Vega
        max_vega = limits.get('max_vega', 500)
        if abs(total_vega) > max_vega:
            vega_severity = 'HIGH' if abs(total_vega) > max_vega * 1.5 else 'MEDIUM'
            violations.append(
                {
                    'greek': 'vega',
                    'value': total_vega,
                    'limit': max_vega,
                    'excess': abs(total_vega) - max_vega,
                    'severity': vega_severity,
                    'note': 'Short vega' if total_vega < 0 else 'Long vega',
                }
            )

        # Check Rho
        max_rho = limits.get('max_rho', 200)
        if abs(total_rho) > max_rho:
            warnings.append(
                {
                    'greek': 'rho',
                    'value': total_rho,
                    'limit': max_rho,
                    'excess': abs(total_rho) - max_rho,
                    'note': 'Interest rate exposure',
                }
            )

        # Calculate risk score
        risk_score = 0
        for v in violations:
            if v.get('severity') == 'CRITICAL':
                risk_score += 10
            elif v.get('severity') == 'HIGH':
                risk_score += 5
            else:
                risk_score += 2

        risk_level = (
            'CRITICAL'
            if risk_score > 20
            else ('HIGH' if risk_score > 10 else 'MEDIUM' if risk_score > 0 else 'LOW')
        )

        return {
            'within_limits': len(violations) == 0,
            'violations': violations,
            'warnings': warnings,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'portfolio_greeks': {
                'total_delta': total_delta,
                'total_gamma': total_gamma,
                'total_theta': total_theta,
                'total_vega': total_vega,
                'total_rho': total_rho,
            },
            'limits_applied': limits,
            'recommendation': self._generate_limit_recommendation(violations, risk_level),
        }

    def _generate_limit_recommendation(
        self, violations: List[Dict[str, Any]], risk_level: str
    ) -> str:
        """Generate recommendation based on limit violations."""
        if not violations:
            return 'Portfolio Greeks within acceptable limits'

        critical_violations = [v for v in violations if v.get('severity') == 'CRITICAL']
        high_violations = [v for v in violations if v.get('severity') == 'HIGH']

        if critical_violations:
            return (
                f'CRITICAL: {len(critical_violations)} critical violations. '
                f'Immediate position reduction required. Focus on reducing '
                f'{", ".join(set(v["greek"] for v in critical_violations))} exposure.'
            )
        elif high_violations:
            return (
                f'HIGH: {len(high_violations)} high-severity violations. '
                f'Significant de-risking recommended. Consider hedging '
                f'{", ".join(set(v["greek"] for v in high_violations))}.'
            )
        else:
            return (
                f'MODERATE: {len(violations)} violations detected. '
                f'Monitor closely and consider reducing exposure.'
            )

    def calculate_greeks_sensitivity_analysis(
        self,
        option_params: Dict[str, Any],
        shock_scenarios: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Perform sensitivity analysis on Greeks by shocking underlying parameters.

        This helps understand how Greeks change with market conditions,
        which is critical for dynamic hedging strategies.

        Args:
            option_params: Option parameters for calculate_all_greeks
            shock_scenarios: Custom shock scenarios (defaults provided)

        Returns:
            Sensitivity analysis results
        """
        default_scenarios = {
            'spot_shock_pct': 0.05,  # 5% spot price change
            'vol_shock_pct': 0.10,  # 10% volatility change
            'time_decay_days': 1,  # 1 day time decay
            'rate_shock_pct': 0.01,  # 1% rate change
        }

        if shock_scenarios:
            default_scenarios.update(shock_scenarios)

        try:
            # Calculate base Greeks
            base_greeks = self.calculate_all_greeks(**option_params)

            if 'error' in base_greeks:
                return {'error': 'Base Greeks calculation failed', 'details': base_greeks}

            sensitivity_results = {}
            base_params = option_params.copy()

            # 1. Spot price sensitivity (how Delta changes)
            spot_shock = default_scenarios['spot_shock_pct']
            spot_up_params = base_params.copy()
            spot_up_params['spot_price'] *= 1 + spot_shock
            greeks_spot_up = self.calculate_all_greeks(**spot_up_params)

            spot_down_params = base_params.copy()
            spot_down_params['spot_price'] *= 1 - spot_shock
            greeks_spot_down = self.calculate_all_greeks(**spot_down_params)

            if 'error' not in greeks_spot_up and 'error' not in greeks_spot_down:
                delta_change_up = (
                    greeks_spot_up['primary_greeks']['delta']
                    - base_greeks['primary_greeks']['delta']
                )
                delta_change_down = (
                    greeks_spot_down['primary_greeks']['delta']
                    - base_greeks['primary_greeks']['delta']
                )

                sensitivity_results['spot_sensitivity'] = {
                    'shock_pct': spot_shock,
                    'delta_change_up': delta_change_up,
                    'delta_change_down': delta_change_down,
                    'delta_stability': abs(delta_change_up - delta_change_down) < 0.1,
                    'gamma_validation': (abs(delta_change_up) - abs(delta_change_down))
                    / (2 * spot_shock * base_params['spot_price']),
                }

            # 2. Volatility sensitivity (how Vega changes)
            vol_shock = default_scenarios['vol_shock_pct']
            vol_up_params = base_params.copy()
            vol_up_params['volatility'] *= 1 + vol_shock
            greeks_vol_up = self.calculate_all_greeks(**vol_up_params)

            vol_down_params = base_params.copy()
            vol_down_params['volatility'] *= max(0.01, 1 - vol_shock)
            greeks_vol_down = self.calculate_all_greeks(**vol_down_params)

            if 'error' not in greeks_vol_up and 'error' not in greeks_vol_down:
                vega_change_up = (
                    greeks_vol_up['primary_greeks']['vega'] - base_greeks['primary_greeks']['vega']
                )
                vega_change_down = (
                    greeks_vol_down['primary_greeks']['vega']
                    - base_greeks['primary_greeks']['vega']
                )

                sensitivity_results['volatility_sensitivity'] = {
                    'shock_pct': vol_shock,
                    'vega_change_up': vega_change_up,
                    'vega_change_down': vega_change_down,
                    'vomma_validation': (vega_change_up - vega_change_down) / (2 * vol_shock),
                }

            # 3. Time decay sensitivity (how Theta accelerates)
            time_decay = default_scenarios['time_decay_days'] / 365
            time_forward_params = base_params.copy()
            time_forward_params['time_to_expiry'] = max(
                0.001, base_params['time_to_expiry'] - time_decay
            )
            greeks_time_forward = self.calculate_all_greeks(**time_forward_params)

            if 'error' not in greeks_time_forward:
                theta_acceleration = (
                    greeks_time_forward['primary_greeks']['theta']
                    - base_greeks['primary_greeks']['theta']
                )

                sensitivity_results['time_decay_sensitivity'] = {
                    'days_decay': default_scenarios['time_decay_days'],
                    'theta_acceleration': theta_acceleration,
                    'theta_warning': abs(theta_acceleration)
                    > abs(base_greeks['primary_greeks']['theta']) * 0.1,
                }

            # 4. Rate sensitivity (how Rho changes)
            rate_shock = default_scenarios['rate_shock_pct']
            rate_up_params = base_params.copy()
            rate_up_params['risk_free_rate'] = base_params.get('risk_free_rate', 0.05) + rate_shock
            greeks_rate_up = self.calculate_all_greeks(**rate_up_params)

            if 'error' not in greeks_rate_up:
                rho_change = (
                    greeks_rate_up['primary_greeks']['rho'] - base_greeks['primary_greeks']['rho']
                )

                sensitivity_results['rate_sensitivity'] = {
                    'rate_shock': rate_shock,
                    'rho_change': rho_change,
                    'rate_significance': abs(rho_change) > 0.01,
                }

            # Overall assessment
            sensitivity_results['assessment'] = self._assess_sensitivity(sensitivity_results)

            return {
                'base_greeks': base_greeks['primary_greeks'],
                'sensitivity_analysis': sensitivity_results,
                'scenarios_applied': default_scenarios,
            }

        except (ValueError, TypeError, KeyError) as e:
            self.logger.error(f'Error in sensitivity analysis: {e}', exc_info=True)
            return {'error': str(e)}

    def _assess_sensitivity(self, sensitivity_results: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall sensitivity profile."""
        risk_factors = []
        stability_score = 100

        # Spot sensitivity
        if 'spot_sensitivity' in sensitivity_results:
            spot = sensitivity_results['spot_sensitivity']
            if not spot.get('delta_stability', True):
                risk_factors.append('High gamma risk - Delta changes rapidly')
                stability_score -= 20

        # Volatility sensitivity
        if 'volatility_sensitivity' in sensitivity_results:
            vol = sensitivity_results['volatility_sensitivity']
            vomma = vol.get('vomma_validation', 0)
            if abs(vomma) > 0.5:
                risk_factors.append('High vomma - Vega changes rapidly with volatility')
                stability_score -= 15

        # Time decay
        if 'time_decay_sensitivity' in sensitivity_results:
            time = sensitivity_results['time_decay_sensitivity']
            if time.get('theta_warning', False):
                risk_factors.append('Accelerating time decay near expiration')
                stability_score -= 10

        if stability_score >= 80:
            stability_level = 'HIGH'
        elif stability_score >= 60:
            stability_level = 'MODERATE'
        else:
            stability_level = 'LOW'

        return {
            'stability_score': stability_score,
            'stability_level': stability_level,
            'risk_factors': risk_factors,
            'recommendation': self._get_sensitivity_recommendation(stability_level),
        }

    def _get_sensitivity_recommendation(self, stability_level: str) -> str:
        """Get recommendation based on stability level."""
        if stability_level == 'HIGH':
            return 'Greeks stable - normal monitoring sufficient'
        elif stability_level == 'MODERATE':
            return 'Greeks moderately sensitive - increase hedging frequency'
        else:
            return 'Greeks highly sensitive - frequent rebalancing required, consider reducing option exposure'

    def validate_put_call_parity(
        self,
        call_greeks: Dict[str, Any],
        put_greeks: Dict[str, Any],
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        risk_free_rate: float,
        tolerance: float = 0.01,
    ) -> Dict[str, Any]:
        """
        Validate put-call parity relationship.

        Put-call parity: C - P = S - K * e^(-rT)

        This is a fundamental no-arbitrage relationship that must hold.

        Args:
            call_greeks: Call option Greeks result
            put_greeks: Put option Greeks result
            spot_price: Current underlying price
            strike_price: Strike price
            time_to_expiry: Time to expiration
            risk_free_rate: Risk-free rate
            tolerance: Acceptable deviation from parity

        Returns:
            Validation results
        """
        try:
            if 'error' in call_greeks or 'error' in put_greeks:
                return {'valid': False, 'error': 'Invalid Greeks provided'}

            call_price = call_greeks.get('option_price')
            put_price = put_greeks.get('option_price')

            if call_price is None or put_price is None:
                return {'valid': False, 'error': 'Option prices not available'}

            # Calculate put-call parity
            lhs = call_price - put_price
            rhs = spot_price - strike_price * np.exp(-risk_free_rate * time_to_expiry)

            difference = abs(lhs - rhs)
            relative_diff = difference / spot_price if spot_price > 0 else 0

            # Check parity
            valid = difference < tolerance

            return {
                'valid': valid,
                'call_price': call_price,
                'put_price': put_price,
                'lhs': lhs,  # C - P
                'rhs': rhs,  # S - K*e^(-rT)
                'difference': difference,
                'relative_difference': relative_diff,
                'tolerance': tolerance,
                'arbitrage_opportunity': not valid and difference > tolerance,
                'potential_arbitrage_profit': difference if not valid else 0,
            }

        except (ValueError, TypeError, KeyError) as e:
            self.logger.error(f'Error validating put-call parity: {e}', exc_info=True)
            return {'valid': False, 'error': str(e)}

    def calculate_greeks_implied_values(
        self,
        option_price: float,
        option_type: str,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        risk_free_rate: float,
        dividend_yield: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Calculate implied volatility from option price using Newton-Raphson.

        This is the inverse problem to the Black-Scholes formula.

        Args:
            option_price: Observed market price
            option_type: 'call' or 'put'
            spot_price: Current underlying price
            strike_price: Strike price
            time_to_expiry: Time to expiration
            risk_free_rate: Risk-free rate
            dividend_yield: Dividend yield

        Returns:
            Implied volatility and related metrics
        """
        try:
            # Initial guess
            sigma = 0.2
            max_iterations = 100
            tolerance = 1e-6

            for i in range(max_iterations):
                # Calculate price with current volatility guess
                greeks = self.calculate_all_greeks(
                    option_type=option_type,
                    spot_price=spot_price,
                    strike_price=strike_price,
                    time_to_expiry=time_to_expiry,
                    volatility=sigma,
                    risk_free_rate=risk_free_rate,
                    dividend_yield=dividend_yield,
                )

                if 'error' in greeks:
                    return {'error': f'Failed to converge at iteration {i}'}

                model_price = greeks.get('option_price')
                vega = greeks['primary_greeks']['vega'] * 100  # Convert back from per-1% basis

                # Check convergence
                price_diff = model_price - option_price
                if abs(price_diff) < tolerance:
                    break

                # Newton-Raphson update
                if vega < 1e-6:
                    return {'error': 'Vega too small for convergence'}

                sigma = sigma - price_diff / vega

                # Ensure positivity
                sigma = max(0.001, sigma)

            else:
                return {'error': 'Failed to converge after maximum iterations'}

            # Return final result with Greeks
            final_greeks = self.calculate_all_greeks(
                option_type=option_type,
                spot_price=spot_price,
                strike_price=strike_price,
                time_to_expiry=time_to_expiry,
                volatility=sigma,
                risk_free_rate=risk_free_rate,
                dividend_yield=dividend_yield,
            )

            return {
                'implied_volatility': sigma,
                'market_price': option_price,
                'model_price': final_greeks.get('option_price'),
                'price_error': abs(final_greeks.get('option_price', 0) - option_price),
                'iterations': i + 1,
                'converged': True,
                'greeks_at_iv': final_greeks,
            }

        except (ValueError, TypeError, ZeroDivisionError) as e:
            self.logger.error(f'Error calculating implied volatility: {e}', exc_info=True)
            return {'error': str(e)}

    def validate_greeks_market_prices(
        self,
        market_prices: Dict[str, float],
        option_params: Dict[str, Any],
        price_tolerance: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Validate Greeks calculations against market prices.

        This helps detect model misspecification or market anomalies.

        Args:
            market_prices: Dict of option_type -> market_price
            option_params: Option parameters for calculate_all_greeks
            price_tolerance: Acceptable price deviation (e.g., 5%)

        Returns:
            Validation results comparing model to market
        """
        try:
            validation_results = {
                'options_validated': [],
                'total_options': len(market_prices),
                'within_tolerance': 0,
                'outside_tolerance': 0,
                'avg_price_error': 0.0,
                'max_price_error': 0.0,
            }

            price_errors = []

            for option_type, market_price in market_prices.items():
                # Calculate model price
                greeks = self.calculate_all_greeks(option_type=option_type, **option_params)

                if 'error' in greeks:
                    validation_results['options_validated'].append(
                        {
                            'option_type': option_type,
                            'error': greeks['error'],
                        }
                    )
                    continue

                model_price = greeks.get('option_price')
                price_error = abs(model_price - market_price)
                relative_error = price_error / market_price if market_price > 0 else 0

                price_errors.append(relative_error)

                is_valid = relative_error <= price_tolerance

                if is_valid:
                    validation_results['within_tolerance'] += 1
                else:
                    validation_results['outside_tolerance'] += 1

                validation_results['options_validated'].append(
                    {
                        'option_type': option_type,
                        'market_price': market_price,
                        'model_price': model_price,
                        'price_error': price_error,
                        'relative_error': relative_error,
                        'within_tolerance': is_valid,
                        'tolerance': price_tolerance,
                    }
                )

            # Calculate statistics
            if price_errors:
                validation_results['avg_price_error'] = float(np.mean(price_errors))
                validation_results['max_price_error'] = float(np.max(price_errors))
                validation_results['std_price_error'] = float(np.std(price_errors))

            validation_results['overall_valid'] = validation_results['outside_tolerance'] == 0

            return validation_results

        except (ValueError, TypeError, KeyError) as e:
            self.logger.error(f'Error validating Greeks against market: {e}', exc_info=True)
            return {'error': str(e)}


def get_greeks_calculator(config: Optional[Dict[str, Any]] = None) -> GreeksCalculator:
    """
    Get a GreeksCalculator instance for Hull's options risk management.

    This is a convenience function for the compliance engine to check if
    Hull systems are available.

    Args:
        config: Optional configuration for the Greeks calculator

    Returns:
        GreeksCalculator instance

    Example:
        >>> calculator = get_greeks_calculator()
        >>> greeks = calculator.calculate_all_greeks('call', 100, 95, 0.25, 0.2)
    """
    return GreeksCalculator(config=config)
