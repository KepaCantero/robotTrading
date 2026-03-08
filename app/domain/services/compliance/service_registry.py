"""
Compliance Service Registry
============================

Central registration point for all 12 compliance services.
Implements lazy initialization and thread-safe singleton pattern.

Services Registered:
1.  Ernest Chan (Rule 1)      - Regime Detection, Execution, Optimization
2.  Narang (Rule 2)           - Alpha Models, Risk Models, Transaction Costs
3.  López de Prado (Rule 3)   - Meta-Labeling, Purged CV
4.  Harris (Rule 6)           - Microstructure, Order Book Analysis
5.  O'Hara (Rule 7)           - Order Flow, Liquidity, Price Discovery
6.  Hull (Rule 13)            - Greeks, VaR, Stress Testing
7.  Google SRE (Rule 20)      - Golden Signals, Trading Metrics

Author: Compliance Integration System
Date: 2026-02-03
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# SERVICE FACTORY TYPE
# =============================================================================


ServiceFactory = Callable[[], Any]


# =============================================================================
# SERVICE REGISTRY
# =============================================================================


class ComplianceServiceRegistry:
    """
    Central registry for all compliance services.

    Features:
        - Lazy initialization: Services created only when first accessed
        - Thread-safe: Uses locks for concurrent access
        - Singleton pattern: Single instance across application
        - Service factories: Deferred instantiation

    Example:
        registry = ComplianceServiceRegistry.getInstance()

        # Get service (lazy initialization)
        harris = registry.get_service("harris_integrator")

        # Check availability
        if registry.is_available("alpha_model"):
            alpha = registry.get_service("alpha_model")
    """

    _instance: Optional["ComplianceServiceRegistry"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        """Private constructor - use getInstance() instead."""
        if ComplianceServiceRegistry._instance is not None:
            raise RuntimeError("Use getInstance() to get the singleton instance")

        self._factories: Dict[str, ServiceFactory] = {}
        self._services: Dict[str, Any] = {}
        self._availability: Dict[str, bool] = {}
        self._service_lock = threading.RLock()

        # Register all service factories
        self._register_factories()

    @classmethod
    def getInstance(cls) -> "ComplianceServiceRegistry":
        """
        Get the singleton instance.

        Returns:
            ComplianceServiceRegistry singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def resetInstance(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        with cls._lock:
            cls._instance = None

    # =========================================================================
    # PICKLE SUPPORT (for multiprocessing)
    # =========================================================================

    def __getstate__(self) -> Dict[str, Any]:
        """
        Get state for pickling (excludes unpicklable locks).

        Thread locks cannot be pickled, so we exclude them and recreate
        them in __setstate__. This is required for multiprocessing support.
        """
        state = self.__dict__.copy()
        # Remove unpicklable locks - they will be recreated in __setstate__
        state.pop('_service_lock', None)
        # Clear cached services as they won't be valid in the new process
        state['_services'] = {}
        state['_availability'] = {}
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        """
        Restore state from pickling (recreates locks).

        Thread locks are recreated here after unpickling.
        """
        self.__dict__.update(state)
        # Recreate the unpicklable lock
        self._service_lock = threading.RLock()

    # =========================================================================
    # REGISTRATION
    # =========================================================================

    def _register_factories(self) -> None:
        """Register all service factories."""

        # -------------------------------------------------------------------------
        # Rule 1: Ernest Chan - Quantitative Trading
        # -------------------------------------------------------------------------
        self._factories["regime_detector"] = self._create_regime_detector
        self._factories["vwap_executor"] = self._create_vwap_executor
        self._factories["twap_executor"] = self._create_twap_executor
        self._factories["is_executor"] = self._create_is_executor
        self._factories["pov_executor"] = self._create_pov_executor
        self._factories["portfolio_optimizer"] = self._create_portfolio_optimizer

        # -------------------------------------------------------------------------
        # Rule 2: Narang - Inside the Black Box
        # -------------------------------------------------------------------------
        self._factories["alpha_model"] = self._create_alpha_model
        self._factories["risk_model"] = self._create_risk_model
        self._factories["cost_model"] = self._create_cost_model
        self._factories["portfolio_constructor"] = self._create_portfolio_constructor
        self._factories["execution_engine_narang"] = self._create_execution_engine_narang

        # -------------------------------------------------------------------------
        # Rule 3: López de Prado - Financial Machine Learning
        # -------------------------------------------------------------------------
        self._factories["meta_labeling"] = self._create_meta_labeling
        self._factories["purged_cv"] = self._create_purged_cv

        # -------------------------------------------------------------------------
        # Rule 6: Harris - Trading and Exchanges
        # -------------------------------------------------------------------------
        self._factories["harris_integrator"] = self._create_harris_integrator
        self._factories["order_book_analyzer"] = self._create_order_book_analyzer
        self._factories["dark_pool_router"] = self._create_dark_pool_router

        # -------------------------------------------------------------------------
        # Rule 7: O'Hara - Market Microstructure Theory
        # -------------------------------------------------------------------------
        self._factories["order_flow_analyzer"] = self._create_order_flow_analyzer
        self._factories["liquidity_analyzer"] = self._create_liquidity_analyzer
        self._factories["price_discovery_analyzer"] = self._create_price_discovery_analyzer
        self._factories["call_auction"] = self._create_call_auction

        # -------------------------------------------------------------------------
        # Rule 13: Hull - Risk Management
        # -------------------------------------------------------------------------
        self._factories["var_calculator"] = self._create_var_calculator
        self._factories["greeks_calculator"] = self._create_greeks_calculator
        self._factories["stress_tester"] = self._create_stress_tester

        # -------------------------------------------------------------------------
        # Rule 20: Google SRE
        # -------------------------------------------------------------------------
        self._factories["golden_signals"] = self._create_golden_signals
        self._factories["trading_metrics"] = self._create_trading_metrics
        self._factories["toil_tracker"] = self._create_toil_tracker

    def register_service(
        self,
        service_name: str,
        factory: ServiceFactory,
    ) -> None:
        """
        Register a new service factory.

        Args:
            service_name: Name of the service
            factory: Factory function that creates the service
        """
        with self._service_lock:
            self._factories[service_name] = factory
            # Clear cached service if exists
            if service_name in self._services:
                del self._services[service_name]
        logger.info("Registered service factory", service_name=service_name)

    # =========================================================================
    # SERVICE ACCESS
    # =========================================================================

    def get_service(self, service_name: str) -> Optional[Any]:
        """
        Get a service by name (lazy initialization).

        Args:
            service_name: Name of the service

        Returns:
            Service instance or None if not available
        """
        with self._service_lock:
            # Return cached service if available
            if service_name in self._services:
                return self._services[service_name]

            # Check if factory exists
            if service_name not in self._factories:
                logger.warning("Service factory not found", service_name=service_name)
                return None

            # Create service using factory
            try:
                factory = self._factories[service_name]
                service = factory()
                self._services[service_name] = service
                self._availability[service_name] = service is not None
                logger.debug("Created service", service_name=service_name)
                return service
            except Exception as e:
                logger.warning("Failed to create service", service_name=service_name, error=str(e))
                self._availability[service_name] = False
                return None

    def is_available(self, service_name: str) -> bool:
        """
        Check if a service is available.

        Args:
            service_name: Name of the service

        Returns:
            True if service is available
        """
        with self._service_lock:
            if service_name in self._availability:
                return self._availability[service_name]

            # Try to get the service to check availability
            service = self.get_service(service_name)
            return service is not None

    def get_all_services(self) -> Dict[str, Any]:
        """
        Get all registered services.

        Returns:
            Dict mapping service names to service instances
        """
        with self._service_lock:
            services = {}
            for service_name in self._factories.keys():
                service = self.get_service(service_name)
                if service is not None:
                    services[service_name] = service
            return services

    def get_availability_report(self) -> Dict[str, bool]:
        """
        Get availability status of all services.

        Returns:
            Dict mapping service names to availability status
        """
        with self._service_lock:
            availability = {}
            for service_name in self._factories.keys():
                availability[service_name] = self.is_available(service_name)
            return availability

    # =========================================================================
    # SERVICE FACTORIES (Lazy Initialization)
    # =========================================================================

    # -------------------------------------------------------------------------
    # Rule 1: Ernest Chan Factories
    # -------------------------------------------------------------------------

    def _create_regime_detector(self) -> Optional[Any]:
        try:
            from app.services.regime_detection_chan import get_regime_detector

            return get_regime_detector(method="hmm", n_regimes=4)
        except ImportError:
            return None

    def _create_vwap_executor(self) -> Optional[Any]:
        try:
            from app.domain.services.execution.algorithms import get_execution_algorithm

            return get_execution_algorithm("vwap")
        except ImportError:
            return None

    def _create_twap_executor(self) -> Optional[Any]:
        try:
            from app.domain.services.execution.algorithms import get_execution_algorithm

            return get_execution_algorithm("twap")
        except ImportError:
            return None

    def _create_is_executor(self) -> Optional[Any]:
        try:
            from app.domain.services.execution.algorithms import get_execution_algorithm

            return get_execution_algorithm("implementation_shortfall")
        except ImportError:
            return None

    def _create_pov_executor(self) -> Optional[Any]:
        try:
            from app.domain.services.execution.algorithms import get_execution_algorithm

            return get_execution_algorithm("pov")
        except ImportError:
            return None

    def _create_portfolio_optimizer(self) -> Optional[Any]:
        try:
            from app.services.optimization_chan import get_portfolio_optimizer

            return get_portfolio_optimizer(method="mean_variance")
        except ImportError:
            return None

    # -------------------------------------------------------------------------
    # Rule 2: Narang Factories
    # -------------------------------------------------------------------------

    def _create_alpha_model(self) -> Optional[Any]:
        try:
            from app.domain.strategies.alpha_models import get_alpha_model

            return get_alpha_model(
                {
                    "model_type": "multifactor",
                    "factors": ["momentum", "mean_reversion"],
                }
            )
        except ImportError:
            return None

    def _create_risk_model(self) -> Optional[Any]:
        try:
            from app.services.risk_models_narang import get_risk_model

            return get_risk_model(
                {
                    "model_type": "factor",
                    "max_factor_exposure": 0.15,
                }
            )
        except ImportError:
            return None

    def _create_cost_model(self) -> Optional[Any]:
        try:
            from app.services.transaction_costs import get_transaction_cost_model

            return get_transaction_cost_model({"model_type": "almgren_chriss"})
        except ImportError:
            return None

    def _create_portfolio_constructor(self) -> Optional[Any]:
        try:
            from app.services.portfolio_construction_narang import get_portfolio_constructor

            return get_portfolio_constructor(
                {
                    "optimization_method": "mean_variance",
                }
            )
        except ImportError:
            return None

    def _create_execution_engine_narang(self) -> Optional[Any]:
        try:
            from app.services.execution_narang import get_execution_engine

            return get_execution_engine({})
        except ImportError:
            return None

    # -------------------------------------------------------------------------
    # Rule 3: López de Prado Factories
    # -------------------------------------------------------------------------

    def _create_meta_labeling(self) -> Optional[Any]:
        try:
            from app.backtesting.labeling.meta_labeling import get_meta_labeling

            return get_meta_labeling()
        except ImportError:
            return None

    def _create_purged_cv(self) -> Optional[Any]:
        try:
            from app.backtesting.validation.cross_validation import PurgedKFold

            return PurgedKFold(n_splits=5, embargo_pct=0.01)
        except ImportError:
            return None

    # -------------------------------------------------------------------------
    # Rule 6: Harris Factories
    # -------------------------------------------------------------------------

    def _create_harris_integrator(self) -> Optional[Any]:
        try:
            from app.engines.execution_engine.microstructure.harris_integration import (
                get_harris_integrator,
            )

            return get_harris_integrator(
                asset_class="equity",
                enable_all_rules=True,
            )
        except ImportError:
            return None

    def _create_order_book_analyzer(self) -> Optional[Any]:
        try:
            from app.engines.execution_engine.microstructure.order_book_analyzer import (
                get_order_book_analyzer,
            )

            return get_order_book_analyzer()
        except ImportError:
            return None

    def _create_dark_pool_router(self) -> Optional[Any]:
        try:
            from app.engines.execution_engine.microstructure.dark_pool_router import (
                get_dark_pool_router,
            )

            return get_dark_pool_router()
        except ImportError:
            return None

    # -------------------------------------------------------------------------
    # Rule 7: O'Hara Factories
    # -------------------------------------------------------------------------

    def _create_order_flow_analyzer(self) -> Optional[Any]:
        try:
            from app.domain.market_analysis.microstructure.order_flow import get_order_flow_analyzer

            return get_order_flow_analyzer()
        except ImportError:
            return None

    def _create_liquidity_analyzer(self) -> Optional[Any]:
        try:
            from app.domain.market_analysis.microstructure.liquidity import get_liquidity_analyzer

            return get_liquidity_analyzer()
        except ImportError:
            return None

    def _create_price_discovery_analyzer(self) -> Optional[Any]:
        try:
            from app.domain.market_analysis.microstructure.price_discovery import (
                get_price_discovery_analyzer,
            )

            return get_price_discovery_analyzer()
        except ImportError:
            return None

    def _create_call_auction(self) -> Optional[Any]:
        try:
            from app.domain.market_analysis.microstructure.trading_mechanisms import (
                get_call_auction,
            )

            return get_call_auction()
        except ImportError:
            return None

    # -------------------------------------------------------------------------
    # Rule 13: Hull Factories
    # -------------------------------------------------------------------------

    def _create_var_calculator(self) -> Optional[Any]:
        try:
            from app.engines.risk_engine.var_calculators.var_calculators import (
                HistoricalVaRCalculator,
            )

            config = {'confidence_level': 0.95, 'time_horizon': 1}
            return HistoricalVaRCalculator(config)
        except ImportError:
            return None

    def _create_greeks_calculator(self) -> Optional[Any]:
        try:
            from app.engines.risk_engine.greeks_calculator import get_greeks_calculator

            return get_greeks_calculator()
        except ImportError:
            return None

    def _create_stress_tester(self) -> Optional[Any]:
        try:
            from app.engines.risk_engine.stress_testers.advanced_stress_scenarios import (
                get_advanced_stress_tester,
            )

            return get_advanced_stress_tester()
        except ImportError:
            return None

    # -------------------------------------------------------------------------
    # Rule 20: Google SRE Factories
    # -------------------------------------------------------------------------

    def _create_golden_signals(self) -> Optional[Any]:
        try:
            from app.sre.monitoring.golden_signals import get_golden_signals_monitor

            return get_golden_signals_monitor(service_name="compliance_registry")
        except ImportError:
            return None

    def _create_trading_metrics(self) -> Optional[Any]:
        try:
            from app.sre.monitoring.trading_metrics import get_trading_metrics_monitor

            return get_trading_metrics_monitor()
        except ImportError:
            return None

    def _create_toil_tracker(self) -> Optional[Any]:
        try:
            from app.sre.automation.toil_tracker import get_toil_tracker

            return get_toil_tracker(service_name="compliance_registry")
        except ImportError:
            return None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def get_service_registry() -> ComplianceServiceRegistry:
    """
    Get the global service registry instance.

    Returns:
        ComplianceServiceRegistry singleton
    """
    return ComplianceServiceRegistry.getInstance()


def get_service(service_name: str) -> Optional[Any]:
    """
    Get a service from the global registry.

    Args:
        service_name: Name of the service

    Returns:
        Service instance or None if not available
    """
    registry = get_service_registry()
    return registry.get_service(service_name)
