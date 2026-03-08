"""
Subsystem Configuration Factory.

Provides default configurations for all subsystems used by ComplianceEngine.
Follows the Factory pattern to centralize config creation and ensure
consistent defaults across the application.

Usage:
    from app.shared.utils.subsystem_config_factory import SubsystemConfigFactory

    factory = SubsystemConfigFactory()
    backtest_config = factory.get_backtest_config()
    risk_config = factory.get_risk_engine_config()
"""

from decimal import Decimal
from typing import Any, Dict, Optional

from app.shared.config.centralized_config import get_config


class SubsystemConfigFactory:
    """
    Factory for creating default subsystem configurations.

    This factory provides sensible defaults for all subsystems that
    require configuration when instantiated by the ComplianceEngine.

    Benefits:
    - Centralized configuration management
    - Consistent defaults across the application
    - Easy to override for testing
    - Single source of truth for subsystem configs
    """

    _instance: Optional["SubsystemConfigFactory"] = None

    def __new__(cls) -> "SubsystemConfigFactory":
        """Singleton pattern for consistent config access."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize factory with default configurations."""
        if self._initialized:
            return
        self._initialized = True

    # ==========================================================================
    # BACKTESTING ENGINE CONFIG
    # ==========================================================================

    def get_backtest_config(self) -> "BacktestConfig":
        """
        Get default BacktestConfig for BacktestEngine.

        Returns:
            BacktestConfig with sensible defaults
        """
        from app.backtesting.models import BacktestConfig

        return BacktestConfig(
            strategy_name="compliance_default",
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            risk_free_rate=get_config().backtesting.default_risk_free_rate,
            max_position_size=Decimal("0.1"),
        )

    # ==========================================================================
    # RISK ENGINE CONFIG
    # ==========================================================================

    def get_risk_engine_config(self) -> Dict[str, Any]:
        """
        Get default configuration for RiskEngine.

        Returns:
            Dict with risk engine defaults
        """
        return {
            "max_portfolio_var": 0.15,
            "max_position_concentration": 0.20,
            "var_confidence_level": 0.95,
            "lookback_days": 252,
            "correlation_window": 60,
            "stress_test_scenarios": [
                "market_crash",
                "volatility_spike",
                "liquidity_crisis",
            ],
            "enable_dynamic_var": True,
            "alert_thresholds": {
                "var_breach": 0.8,
                "concentration_warning": 0.15,
            },
        }

    # ==========================================================================
    # PORTFOLIO ENGINE CONFIG
    # ==========================================================================

    def get_portfolio_engine_config(self) -> Dict[str, Any]:
        """
        Get default configuration for PortfolioEngine.

        Returns:
            Dict with portfolio engine defaults
        """
        return {
            "rebalance_threshold": 0.05,
            "max_positions": 50,
            "min_position_size": Decimal("0.01"),
            "optimization_method": "mean_variance",
            "risk_budget": {
                "equity": 0.60,
                "fixed_income": 0.30,
                "alternatives": 0.10,
            },
            "transaction_cost_model": {
                "fixed_cost": Decimal("1.0"),
                "variable_cost": Decimal("0.001"),
            },
            "constraints": {
                "min_diversification": 0.3,
                "max_single_asset": 0.10,
            },
        }

    # ==========================================================================
    # ALPHA MODEL CONFIG (for Narang subsystem)
    # ==========================================================================

    def get_alpha_model_config(self) -> Dict[str, Any]:
        """
        Get default configuration for alpha model.

        Note: Use 'multi_factor' (with underscore), not 'multifactor'.

        Returns:
            Dict with alpha model defaults
        """
        return {
            "model_type": "multi_factor",  # NOT 'multifactor'
            "lookback_period": 252,
            "factors": ["momentum", "value", "quality", "volatility"],
            "factor_weights": {
                "momentum": 0.25,
                "value": 0.25,
                "quality": 0.25,
                "volatility": 0.25,
            },
            "rebalance_frequency": "monthly",
        }

    # ==========================================================================
    # PORTFOLIO CONSTRUCTOR CONFIG (for Narang subsystem)
    # ==========================================================================

    def get_portfolio_constructor_config(self) -> Dict[str, Any]:
        """
        Get default configuration for portfolio constructor.

        Returns:
            Dict with portfolio constructor defaults
        """
        return {
            "optimization_method": "mean_variance",
            "risk_aversion": 2.5,
            "target_return": 0.10,
            "max_weight": 0.10,
            "min_weight": 0.01,
        }

    # ==========================================================================
    # REGIME DETECTOR CONFIG (for Ernest Chan subsystem)
    # ==========================================================================

    def get_regime_detector_config(self) -> Dict[str, Any]:
        """
        Get default configuration for regime detector.

        Returns:
            Dict with regime detector defaults
        """
        return {
            "n_regimes": 3,
            "lookback_window": 252,
            "smoothing_window": 20,
            "transition_threshold": 0.3,
        }

    # ==========================================================================
    # EXECUTION ALGORITHM CONFIG (for Ernest Chan subsystem)
    # ==========================================================================

    def get_execution_algorithm_config(self) -> Dict[str, Any]:
        """
        Get default configuration for execution algorithms.

        Returns:
            Dict with execution algorithm defaults
        """
        return {
            "vwap": {
                "participation_rate": 0.1,
                "time_window_minutes": 30,
            },
            "twap": {
                "slice_interval_seconds": 60,
                "randomize_timing": True,
            },
        }

    # ==========================================================================
    # LIVE TRADING CONFIG
    # ==========================================================================

    def get_live_trading_config(self) -> Dict[str, Any]:
        """
        Get default configuration for live trading.

        Returns:
            Dict with live trading defaults
        """
        return {
            "broker_type": "paper",
            "max_retry_attempts": 3,
            "order_timeout_seconds": 30,
            "enable_confirmations": True,
        }

    # ==========================================================================
    # GENERIC GETTER
    # ==========================================================================

    def get_config(self, subsystem_name: str) -> Optional[Any]:
        """
        Get configuration for a specific subsystem by name.

        Args:
            subsystem_name: Name of the subsystem

        Returns:
            Configuration object/dict or None if not found
        """
        config_map = {
            "backtesting_engine": self.get_backtest_config,
            "risk_engine": self.get_risk_engine_config,
            "portfolio_engine": self.get_portfolio_engine_config,
            "alpha_model": self.get_alpha_model_config,
            "portfolio_constructor": self.get_portfolio_constructor_config,
            "regime_detector": self.get_regime_detector_config,
            "execution_algorithm": self.get_execution_algorithm_config,
            "live_trading": self.get_live_trading_config,
            "ernest_chan": self.get_regime_detector_config,
            "narang": self.get_alpha_model_config,
        }

        getter = config_map.get(subsystem_name)
        if getter:
            return getter()
        return None


# Singleton instance for convenience
_factory: Optional[SubsystemConfigFactory] = None


def get_subsystem_config_factory() -> SubsystemConfigFactory:
    """
    Get the singleton SubsystemConfigFactory instance.

    Returns:
        SubsystemConfigFactory singleton
    """
    global _factory
    if _factory is None:
        _factory = SubsystemConfigFactory()
    return _factory
