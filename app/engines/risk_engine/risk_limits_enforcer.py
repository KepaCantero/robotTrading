"""
Risk Limits Enforcer - Hull Chapter 18

Implements automatic risk limit enforcement based on VaR thresholds.

Enforcement actions:
1. Position reduction when VaR exceeds limits
2. Trading halt when VaR breaches critical threshold
3. Dynamic position sizing based on VaR utilization
4. Portfolio heatmaps by risk factor
5. Risk attribution by asset class

This module implements the risk management controls recommended in Hull:
- Stop-loss limits
- VaR-based position limits
- Concentration limits
- Leverage limits

Reference: Hull, Options, Futures, and Other Derivatives, Chapter 18
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np

from app.core.centralized_config import get_config
from app.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


def _get_risk_config(attr_name: str, default_value: float) -> Decimal:
    """
    Get risk management configuration value with fallback default.

    Args:
        attr_name: Config attribute name
        default_value: Default value if config attribute not found

    Returns:
        Decimal value from config or default
    """
    try:
        config = get_config()
        value = float(getattr(config.trading, attr_name, default_value))
        return Decimal(str(value))
    except (AttributeError, ValueError, TypeError) as e:
        logger.warning(f"Error getting risk config '{attr_name}': {e}, using default {default_value}")
        return Decimal(str(default_value))


class RiskLimitsEnforcer:
    """
    Risk Limits Enforcer.

    Monitors portfolio risk and automatically enforces limits.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize risk limits enforcer.

        Args:
            config: Configuration dictionary (deprecated, uses centralized config instead)
        """
        # Use centralized config system with fallbacks
        # VaR limits (as percentages of portfolio value)
        self.var_warning_limit = _get_risk_config("var_enforcer_warning_limit", 0.02)
        self.var_critical_limit = _get_risk_config("var_enforcer_critical_limit", 0.03)
        self.var_halt_limit = _get_risk_config("var_enforcer_halt_limit", 0.05)

        # Position limits
        self.max_position_pct = _get_risk_config("risk_enforcer_max_position_pct", 0.20)
        self.max_concentration_pct = _get_risk_config("risk_enforcer_max_concentration_pct", 0.40)

        # Leverage limits
        self.max_leverage = _get_risk_config("risk_enforcer_max_leverage", 2.0)

        # Drawdown limits
        self.max_drawdown_pct = _get_risk_config("max_drawdown_limit", 0.15)

        # Enforcement state
        self.trading_halted = False
        self.halt_reason = None
        self.enforcement_history: List[Dict[str, Any]] = []

        self.logger = logging.getLogger(self.__class__.__name__)

    def check_var_limits(
        self,
        portfolio: Portfolio,
        current_var: float,
        portfolio_value: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Check if portfolio VaR exceeds limits and recommend actions.

        Args:
            portfolio: Portfolio to check
            current_var: Current VaR (as decimal, e.g., 0.02 for 2%)
            portfolio_value: Total portfolio value

        Returns:
            Enforcement recommendation
        """
        try:
            if portfolio_value is None:
                portfolio_value = float(portfolio.total_equity)

            var_amount = current_var * portfolio_value
            var_pct = current_var * 100

            # Determine action
            action = None
            severity = 'NORMAL'
            messages = []

            if current_var >= self.var_halt_limit:
                action = 'HALT_TRADING'
                severity = 'CRITICAL'
                messages.append(
                    f'VaR {var_pct:.2f}% exceeds halt limit {self.var_halt_limit*100:.2f}%'
                )
                self.trading_halted = True
                self.halt_reason = f'VaR limit breach: {var_pct:.2f}%'

            elif current_var >= self.var_critical_limit:
                action = 'REDUCE_POSITIONS'
                severity = 'CRITICAL'
                reduction_needed = self._calculate_required_reduction(
                    current_var, self.var_warning_limit
                )
                messages.append(
                    f'VaR {var_pct:.2f}% exceeds critical limit '
                    f'{self.var_critical_limit*100:.2f}%'
                )
                messages.append(f'Reduce positions by {reduction_needed:.1f}%')

            elif current_var >= self.var_warning_limit:
                action = 'MONITOR'
                severity = 'WARNING'
                messages.append(
                    f'VaR {var_pct:.2f}% exceeds warning limit '
                    f'{self.var_warning_limit*100:.2f}%'
                )

            else:
                messages.append(f'VaR {var_pct:.2f}% within acceptable limits')

            # Calculate VaR utilization
            utilization = current_var / self.var_critical_limit

            result = {
                'current_var': current_var,
                'var_amount': var_amount,
                'var_pct': var_pct,
                'var_utilization': utilization,
                'severity': severity,
                'action': action,
                'messages': messages,
                'limits': {
                    'warning': self.var_warning_limit * 100,
                    'critical': self.var_critical_limit * 100,
                    'halt': self.var_halt_limit * 100,
                },
                'trading_halted': self.trading_halted,
            }

            # Log enforcement action
            if action and action != 'MONITOR':
                self._log_enforcement('var_limit', result)

            return result

        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error(f'Error checking VaR limits: {e}', exc_info=True)
            return {'error': str(e)}

    def _calculate_required_reduction(
        self,
        current_var: float,
        target_var: float,
    ) -> float:
        """
        Calculate required position reduction to meet target VaR.

        Assumes VaR scales with square root of position size.
        """
        if target_var >= current_var:
            return 0.0

        # To reduce VaR from current to target:
        # new_var = current_var * sqrt(reduction_ratio)
        # reduction_ratio = (target_var / current_var)^2

        reduction_ratio = (target_var / current_var) ** 2
        required_reduction = (1 - reduction_ratio) * 100

        return required_reduction

    def enforce_position_limits(
        self,
        portfolio: Portfolio,
    ) -> Dict[str, Any]:
        """
        Enforce position size and concentration limits.

        Args:
            portfolio: Portfolio to check

        Returns:
            Enforcement actions
        """
        try:
            if portfolio.total_equity == 0:
                return {'error': 'Portfolio value is zero'}

            violations = []
            position_limits = {}

            for position in portfolio.positions:
                # Calculate position weight
                weight = float(position.market_value / portfolio.total_equity)

                # Check position limit
                if weight > self.max_position_pct:
                    violations.append(
                        {
                            'type': 'position_size',
                            'symbol': position.symbol,
                            'current_weight': weight,
                            'limit': self.max_position_pct,
                            'excess': weight - self.max_position_pct,
                            'action': 'REDUCE',
                            'required_reduction': (weight - self.max_position_pct)
                            * portfolio.total_equity,
                        }
                    )

                position_limits[position.symbol] = {
                    'current_weight': weight,
                    'limit': self.max_position_pct,
                    'utilization': weight / self.max_position_pct,
                    'status': 'OK' if weight <= self.max_position_pct else 'EXCEEDED',
                }

            # Check concentration (top N positions)
            sorted_positions = sorted(
                portfolio.positions,
                key=lambda p: p.market_value,
                reverse=True,
            )

            top_concentration = sum(
                float(pos.market_value / portfolio.total_equity)
                for pos in sorted_positions[:3]  # Top 3 positions
            )

            if top_concentration > self.max_concentration_pct:
                violations.append(
                    {
                        'type': 'concentration',
                        'description': 'Top 3 positions',
                        'current_concentration': top_concentration,
                        'limit': self.max_concentration_pct,
                        'excess': top_concentration - self.max_concentration_pct,
                        'action': 'DIVERSIFY',
                    }
                )

            result = {
                'violations': violations,
                'position_limits': position_limits,
                'top_concentration': top_concentration,
                'concentration_limit': self.max_concentration_pct,
                'compliance': len(violations) == 0,
            }

            if violations:
                self._log_enforcement('position_limits', result)

            return result

        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error(f'Error enforcing position limits: {e}', exc_info=True)
            return {'error': str(e)}

    def generate_risk_heatmap(
        self,
        portfolio: Portfolio,
        risk_contributions: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Generate portfolio risk heatmap by position.

        Args:
            portfolio: Portfolio to analyze
            risk_contributions: Risk contribution by position (Component VaR)

        Returns:
            Risk heatmap data
        """
        try:
            if portfolio.total_equity == 0:
                return {'error': 'Portfolio value is zero'}

            heatmap_data = []
            total_risk = 0.0

            for position in portfolio.positions:
                weight = float(position.market_value / portfolio.total_equity)

                # Risk level based on weight
                # Get risk heatmap thresholds from config
                try:
                    config = get_config()
                    high_risk_threshold = float(getattr(
                        config.trading, 'risk_heatmap_high_threshold', 0.15
                    ))
                    medium_risk_threshold = float(getattr(
                        config.trading, 'risk_heatmap_medium_threshold', 0.10
                    ))
                except (AttributeError, ValueError, TypeError) as e:
                    self.logger.warning(f"Error getting risk heatmap thresholds: {e}, using defaults")
                    high_risk_threshold = 0.15
                    medium_risk_threshold = 0.10

                if weight > high_risk_threshold:
                    risk_level = 'HIGH'
                    risk_color = 'red'
                elif weight > medium_risk_threshold:
                    risk_level = 'MEDIUM'
                    risk_color = 'yellow'
                else:
                    risk_level = 'LOW'
                    risk_color = 'green'

                # Risk contribution
                risk_contribution = (
                    risk_contributions.get(position.symbol, 0.0) if risk_contributions else weight
                )
                total_risk += abs(risk_contribution)

                heatmap_data.append(
                    {
                        'symbol': position.symbol,
                        'weight': weight,
                        'value': float(position.market_value),
                        'risk_level': risk_level,
                        'risk_color': risk_color,
                        'risk_contribution': risk_contribution,
                    }
                )

            # Sort by risk contribution
            heatmap_data.sort(key=lambda x: abs(x['risk_contribution']), reverse=True)

            # Calculate percentages
            if total_risk > 0:
                for item in heatmap_data:
                    item['risk_pct'] = abs(item['risk_contribution']) / total_risk * 100

            return {
                'heatmap': heatmap_data,
                'total_risk': total_risk,
                'highest_risk': heatmap_data[0] if heatmap_data else None,
                'risk_distribution': self._analyze_risk_distribution(heatmap_data),
            }

        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error(f'Error generating risk heatmap: {e}', exc_info=True)
            return {'error': str(e)}

    def _analyze_risk_distribution(
        self,
        heatmap_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Analyze risk distribution across positions.

        Args:
            heatmap_data: List of heatmap data items with risk contributions

        Returns:
            Risk distribution metrics
        """
        if not heatmap_data:
            return {}

        # Concentration metrics
        top_3_risk = sum(item.get('risk_pct', 0) for item in heatmap_data[:3])
        top_5_risk = sum(item.get('risk_pct', 0) for item in heatmap_data[:5])

        # Risk concentration assessment using config
        try:
            config = get_config()
            high_threshold = float(getattr(
                config.trading, 'risk_concentration_high_threshold', 60.0
            ))
            medium_threshold = float(getattr(
                config.trading, 'risk_concentration_medium_threshold', 40.0
            ))
        except (AttributeError, ValueError, TypeError) as e:
            self.logger.warning(f"Error getting risk concentration thresholds: {e}, using defaults")
            high_threshold = 60.0
            medium_threshold = 40.0

        if top_3_risk > high_threshold:
            concentration = 'HIGH'
        elif top_3_risk > medium_threshold:
            concentration = 'MEDIUM'
        else:
            concentration = 'LOW'

        return {
            'top_3_concentration': top_3_risk,
            'top_5_concentration': top_5_risk,
            'concentration_level': concentration,
            'n_positions': len(heatmap_data),
        }

    def attribute_risk_by_asset_class(
        self,
        portfolio: Portfolio,
        returns_history: Dict[str, List[float]],
        asset_class_mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Attribute risk by asset class.

        Args:
            portfolio: Portfolio to analyze
            returns_history: Historical returns by symbol
            asset_class_mapping: Symbol to asset class mapping

        Returns:
            Risk attribution by asset class
        """
        try:
            if portfolio.total_equity == 0:
                return {'error': 'Portfolio value is zero'}

            # Default asset class mapping (simplified)
            if asset_class_mapping is None:
                asset_class_mapping = {}
                for position in portfolio.positions:
                    # Simple heuristic based on symbol
                    if position.symbol.endswith('-USD'):
                        asset_class_mapping[position.symbol] = 'crypto'
                    else:
                        asset_class_mapping[position.symbol] = 'equities'

            # Group by asset class
            class_exposures = {}
            class_volatilities = {}

            for position in portfolio.positions:
                asset_class = asset_class_mapping.get(position.symbol, 'unknown')
                exposure = float(position.market_value)

                if asset_class not in class_exposures:
                    class_exposures[asset_class] = 0.0
                    class_volatilities[asset_class] = []

                class_exposures[asset_class] += exposure

                # Get volatility
                if position.symbol in returns_history:
                    returns = returns_history[position.symbol]
                    if len(returns) > 1:
                        class_volatilities[asset_class].append(np.std(returns))

            # Calculate risk contributions
            total_exposure = sum(class_exposures.values())
            risk_attributions = {}

            # Get default volatility from config
            try:
                config = get_config()
                default_vol = float(getattr(
                    config.trading, 'risk_enforcer_default_volatility', 0.2
                ))
            except (AttributeError, ValueError, TypeError) as e:
                self.logger.warning(f"Error getting default volatility: {e}, using default 0.2")
                default_vol = 0.2

            for asset_class, exposure in class_exposures.items():
                weight = exposure / total_exposure if total_exposure > 0 else 0

                # Average volatility for asset class
                vols = class_volatilities.get(asset_class, [default_vol])
                avg_vol = np.mean(vols) if vols else default_vol

                # Risk contribution (simplified)
                risk_contribution = weight * avg_vol

                risk_attributions[asset_class] = {
                    'exposure': exposure,
                    'weight': weight,
                    'avg_volatility': avg_vol,
                    'risk_contribution': risk_contribution,
                    'n_positions': len(
                        [
                            p
                            for p in portfolio.positions
                            if asset_class_mapping.get(p.symbol) == asset_class
                        ]
                    ),
                }

            # Calculate percentages
            total_risk = sum(attr['risk_contribution'] for attr in risk_attributions.values())

            for asset_class in risk_attributions:
                if total_risk > 0:
                    risk_attributions[asset_class]['risk_pct'] = (
                        risk_attributions[asset_class]['risk_contribution'] / total_risk * 100
                    )

            return {
                'by_asset_class': risk_attributions,
                'total_exposure': total_exposure,
                'total_risk': total_risk,
                'dominant_risk': (
                    max(risk_attributions.items(), key=lambda x: x[1]['risk_contribution'])[0]
                    if risk_attributions
                    else None
                ),
            }

        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error(f'Error attributing risk: {e}', exc_info=True)
            return {'error': str(e)}

    def calculate_dynamic_position_size(
        self,
        base_position_value: float,
        current_var_utilization: float,
        max_utilization: Optional[float] = None,
    ) -> float:
        """
        Calculate dynamically adjusted position size based on VaR utilization.

        Reduces position size as portfolio approaches VaR limits.

        Args:
            base_position_value: Original position value
            current_var_utilization: Current VaR / limit
            max_utilization: Maximum utilization before scaling (uses config if not provided)

        Returns:
            Adjusted position value
        """
        # Get max utilization from config if not provided
        if max_utilization is None:
            max_utilization = float(_get_risk_config("dynamic_position_max_utilization", 0.8))

        if current_var_utilization >= max_utilization:
            return 0.0  # No new positions

        # Scale factor decreases as utilization increases
        scale_factor = 1.0 - (current_var_utilization / max_utilization)
        scale_factor = max(0.0, scale_factor)

        adjusted_value = base_position_value * scale_factor

        self.logger.debug(
            f'Dynamic position sizing: base={base_position_value:.2f}, '
            f'utilization={current_var_utilization:.2%}, scale={scale_factor:.2%}, '
            f'adjusted={adjusted_value:.2f}'
        )

        return adjusted_value

    def _log_enforcement(
        self,
        enforcement_type: str,
        result: Dict[str, Any],
    ) -> None:
        """Log enforcement action to history."""
        log_entry = {
            'type': enforcement_type,
            'timestamp': datetime.utcnow().isoformat(),
            'result': result,
        }

        self.enforcement_history.append(log_entry)

        self.logger.warning(f'Risk enforcement action: {enforcement_type} - {result}')

    def reset_trading_halt(self) -> None:
        """Reset trading halt flag (use after manual review)."""
        self.trading_halted = False
        self.halt_reason = None
        self.logger.info('Trading halt flag reset')

    def get_enforcement_status(self) -> Dict[str, Any]:
        """Get current enforcement status."""
        return {
            'trading_halted': self.trading_halted,
            'halt_reason': self.halt_reason,
            'enforcement_count': len(self.enforcement_history),
            'limits': {
                'var_warning': self.var_warning_limit * 100,
                'var_critical': self.var_critical_limit * 100,
                'var_halt': self.var_halt_limit * 100,
                'max_position': self.max_position_pct * 100,
                'max_concentration': self.max_concentration_pct * 100,
                'max_leverage': self.max_leverage,
                'max_drawdown': self.max_drawdown_pct * 100,
            },
        }
