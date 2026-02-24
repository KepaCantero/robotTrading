"""
Risk Engine - Base Engine (Hull Chapters 18-20)

Engine principal para gestion de riesgos que extiende PortfolioRiskManager.
Implementa recomendaciones de Hull para gestion de riesgos avanzada:

Value at Risk (VaR) Methods:
- Historical VaR: Non-parametric using empirical distribution
- Parametric VaR: Assumes normal distribution with variance-covariance
- Monte Carlo VaR: Simulated scenarios
- Conditional VaR (Expected Shortfall): Average loss beyond VaR
- Component VaR: Risk contribution by position (NEW)
- EWMA VaR: Exponentially weighted moving average (NEW)

Options Greeks (Chapters 17-19):
- Delta, Gamma, Theta, Vega, Rho
- Higher-order Greeks: Vanna, Vomma, Charm, Veta
- Portfolio-level Greeks aggregation
- Delta hedging calculations

Stress Testing (Chapter 20):
- Historical scenarios (2008, COVID, etc.)
- Monte Carlo stress scenarios
- Correlation breakdown scenarios (NEW)
- Correlation stress testing (NEW)

Risk Limits Enforcement:
- Automatic position reduction when VaR exceeded
- Portfolio heatmaps by risk factor
- Risk attribution by asset class
- Dynamic position sizing

GARCH Volatility Modeling:
- GARCH(1,1) for conditional volatility
- EWMA volatility estimation
- Volatility forecasting

Reference:
- Hull, Options, Futures, and Other Derivatives, Chapters 17-20

REFACTORED: Uses TYPE_CHECKING and lazy imports to avoid circular dependencies.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, runtime_checkable

# Use TYPE_CHECKING for type hints only - no runtime import
if TYPE_CHECKING:
    from app.domain.models.portfolio import Portfolio
    from app.domain.services.risk.portfolio import PortfolioRiskManager


# Define a Protocol for Portfolio to use at runtime instead of placeholder
@runtime_checkable
class PortfolioProtocol(Protocol):
    """Protocol for Portfolio to avoid circular imports at runtime."""

    @property
    def portfolio_id(self) -> str:
        """Portfolio identifier."""
        ...

    @property
    def capital(self) -> Any:
        """Current capital."""
        ...


def _get_portfolio_class():
    """
    Lazily import Portfolio class to avoid circular dependencies.

    Returns:
        Portfolio class or a minimal placeholder if import fails
    """
    try:
        from app.domain.models.portfolio import Portfolio
        return Portfolio
    except ImportError:
        # Return a minimal placeholder class if the real one can't be imported
        # This allows the risk_engine to be imported even when pydantic is missing
        class _PortfolioPlaceholder:
            """Placeholder Portfolio class when pydantic is not available."""
            pass
        return _PortfolioPlaceholder


def _get_portfolio_risk_manager():
    """
    Lazily import PortfolioRiskManager to avoid circular dependencies.

    Returns:
        PortfolioRiskManager class or a minimal placeholder if import fails
    """
    try:
        from app.domain.services.risk.portfolio import PortfolioRiskManager
        return PortfolioRiskManager
    except ImportError:
        # Create a minimal placeholder
        class _PortfolioRiskManagerPlaceholder:
            """Placeholder when services can't be imported."""

            def assess_portfolio_risk(self, portfolio):
                return {'risk_level': 'unknown'}
        return _PortfolioRiskManagerPlaceholder


from .alert_system import AlertSystem
from .correlation_analyzers import CorrelationAnalyzer
from .drawdown_controllers import DrawdownController
from .exposure_managers import ExposureManager
from .greeks_calculator import GreeksCalculator
from .risk_attribution import RiskAttributor
from .risk_limits_enforcer import RiskLimitsEnforcer
from .stress_testers import StressTester
from .stress_testers.comprehensive_scenarios import ComprehensiveStressScenarios
from .stress_testers.correlation_stress import CorrelationStressTester
from .stress_testers.portfolio_variance_stress import PortfolioVarianceStressTester

# New Hull-compliant components
from .var_calculators.component_var import ComponentVaRCalculator
from .var_calculators.ewma_var import EWMAVaRCalculator

logger = logging.getLogger(__name__)

__all__ = [
    "RiskEngine",
    "BaseRiskEngine",
    "PortfolioProtocol",  # Protocol for dependency injection
    "AlertSystem",
    "DrawdownController",
    "CorrelationAnalyzer",
    "ExposureManager",
    "RiskAttributor",
    "StressTester",
    # New Hull-compliant components
    "ComponentVaRCalculator",
    "EWMAVaRCalculator",
    "GreeksCalculator",
    "CorrelationStressTester",
    "PortfolioVarianceStressTester",
    "ComprehensiveStressScenarios",
    "RiskLimitsEnforcer",
]

# Required dependencies - with proper import handling
try:
    pass

    ARCH_AVAILABLE = True
except ImportError:
    ARCH_AVAILABLE = False
    logger.warning("arch package not available. GARCH models will be limited.")

try:
    pass

    STATSMODELS_AVAILABLE = True
except ImportError:
    pass

    STATSMODELS_AVAILABLE = False
    logger.warning(
        "statsmodels package not available. Using fallback implementations from scipy/numpy. Some statistical features will be limited."
    )


class BaseRiskEngine(ABC):
    """Clase base para Risk Engine."""

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar Risk Engine.

        Args:
            config: Configuracion del engine
        """
        self.config = config
        self.enabled = config.get('enabled', True)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialized = False

    @abstractmethod
    def initialize(self) -> None:
        """Inicializar el engine."""

    @abstractmethod
    def assess_risk(self, portfolio: "Portfolio", **kwargs) -> Dict[str, Any]:
        """
        Evaluar riesgo del portfolio.

        Args:
            portfolio: Portfolio a evaluar
            **kwargs: Argumentos adicionales

        Returns:
            Dict con evaluacion de riesgo
        """


class RiskEngine(BaseRiskEngine):
    """
    Risk Engine principal.

    Expande PortfolioRiskManager con capacidades avanzadas.
    """

    def __init__(self, config: Dict[str, Any]):
        """Inicializar Risk Engine."""
        super().__init__(config)

        # PortfolioRiskManager base - lazy load to avoid circular dependencies
        self._risk_manager = None

        # Componentes del engine
        self.var_calculator = None
        self.stress_tester = None
        self.exposure_manager = None
        self.drawdown_controller = None
        self.correlation_analyzer = None
        self.risk_attributor = None
        self.alert_system = None

        # Estado del engine
        self.risk_history: List[Dict[str, Any]] = []
        self.alert_history: List[Dict[str, Any]] = []

        # Metricas
        self.risk_assessments_performed = 0
        self.alerts_triggered = 0

    @property
    def risk_manager(self):
        """Lazy load PortfolioRiskManager to avoid circular dependencies."""
        if self._risk_manager is None:
            PortfolioRiskManager = _get_portfolio_risk_manager()
            self._risk_manager = PortfolioRiskManager()
        return self._risk_manager

    def initialize(self) -> None:
        """Inicializar Risk Engine."""
        try:
            self.logger.info("RiskEngine inicializado")
            self._initialized = True
        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            self.logger.error(f"Error inicializando RiskEngine: {e}", exc_info=True)
            self._initialized = False

    def assess_risk(self, portfolio: "Portfolio", **kwargs) -> Dict[str, Any]:
        """
        Evaluar riesgo completo del portfolio.

        Args:
            portfolio: Portfolio a evaluar
            **kwargs: Argumentos adicionales (returns_history, prices, etc.)

        Returns:
            Dict con evaluacion completa de riesgo
        """
        if not self._initialized:
            self.initialize()

        if not self.enabled:
            return {'status': 'disabled'}

        try:
            self.risk_assessments_performed += 1

            # Evaluación básica usando PortfolioRiskManager
            basic_assessment = self.risk_manager.assess_portfolio_risk(portfolio)

            # Evaluación avanzada
            advanced_assessment = self._assess_advanced_risk(portfolio, **kwargs)

            # Combinar evaluaciones
            full_assessment = {
                **basic_assessment,
                **advanced_assessment,
                'timestamp': datetime.utcnow().isoformat(),
                'assessment_id': self.risk_assessments_performed,
            }

            # Guardar en historial
            self.risk_history.append(full_assessment)

            # Verificar alertas
            self._check_alerts(full_assessment, portfolio)

            return full_assessment

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            self.logger.error(f"Error evaluando riesgo: {e}", exc_info=True)
            return {'error': str(e), 'status': 'error'}

    def _assess_advanced_risk(self, portfolio: "Portfolio", **kwargs) -> Dict[str, Any]:
        """Evaluar riesgos avanzados."""
        assessment = {}

        # VaR si está disponible
        if self.var_calculator:
            try:
                returns_history = kwargs.get('returns_history')
                if returns_history is not None:
                    var_result = self.var_calculator.calculate_var(returns_history)
                    assessment['var'] = var_result
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                self.logger.warning(f"Error calculando VaR: {e}")

        # Stress testing si está disponible
        if self.stress_tester:
            try:
                stress_result = self.stress_tester.run_stress_tests(portfolio)
                assessment['stress_tests'] = stress_result
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                self.logger.warning(f"Error en stress testing: {e}")

        # Exposición si está disponible
        if self.exposure_manager:
            try:
                exposure_result = self.exposure_manager.analyze_exposure(portfolio)
                assessment['exposure'] = exposure_result
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                self.logger.warning(f"Error analizando exposición: {e}")

        # Drawdown control si está disponible
        if self.drawdown_controller:
            try:
                drawdown_result = self.drawdown_controller.assess_drawdown(portfolio)
                assessment['drawdown'] = drawdown_result
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                self.logger.warning(f"Error evaluando drawdown: {e}")

        # Correlaciones si está disponible
        if self.correlation_analyzer:
            try:
                prices_history = kwargs.get('prices_history')
                if prices_history is not None:
                    correlation_result = self.correlation_analyzer.analyze_correlations(
                        portfolio, prices_history
                    )
                    assessment['correlations'] = correlation_result
            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                self.logger.warning(f"Error analizando correlaciones: {e}")

        # Risk attribution si está disponible
        if self.risk_attributor:
            try:
                attribution_result = self.risk_attributor.attribute_risk(portfolio, **kwargs)
                assessment['risk_attribution'] = attribution_result
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                self.logger.warning(f"Error en risk attribution: {e}")

        return assessment

    def _check_alerts(self, assessment: Dict[str, Any], portfolio: "Portfolio") -> None:
        """Verificar y generar alertas."""
        if not self.alert_system:
            return

        try:
            alerts = self.alert_system.check_thresholds(assessment, portfolio)
            if alerts:
                self.alerts_triggered += len(alerts)
                self.alert_history.extend(alerts)
                self.alert_system.send_alerts(alerts)
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            self.logger.warning(f"Error verificando alertas: {e}")

    def set_var_calculator(self, var_calculator: Any) -> None:
        """Establecer calculador de VaR."""
        self.var_calculator = var_calculator
        self.logger.info(f"VaR calculator configurado: {type(var_calculator).__name__}")

    def set_stress_tester(self, stress_tester: Any) -> None:
        """Establecer stress tester."""
        self.stress_tester = stress_tester
        self.logger.info(f"Stress tester configurado: {type(stress_tester).__name__}")

    def set_exposure_manager(self, exposure_manager: Any) -> None:
        """Establecer exposure manager."""
        self.exposure_manager = exposure_manager
        self.logger.info(f"Exposure manager configurado: {type(exposure_manager).__name__}")

    def set_drawdown_controller(self, drawdown_controller: Any) -> None:
        """Establecer drawdown controller."""
        self.drawdown_controller = drawdown_controller
        self.logger.info(f"Drawdown controller configurado: {type(drawdown_controller).__name__}")

    def set_correlation_analyzer(self, correlation_analyzer: Any) -> None:
        """Establecer correlation analyzer."""
        self.correlation_analyzer = correlation_analyzer
        self.logger.info(f"Correlation analyzer configurado: {type(correlation_analyzer).__name__}")

    def set_risk_attributor(self, risk_attributor: Any) -> None:
        """Establecer risk attributor."""
        self.risk_attributor = risk_attributor
        self.logger.info(f"Risk attributor configurado: {type(risk_attributor).__name__}")

    def set_alert_system(self, alert_system: Any) -> None:
        """Establecer sistema de alertas."""
        self.alert_system = alert_system
        self.logger.info(f"Alert system configurado: {type(alert_system).__name__}")

    def get_status(self) -> Dict[str, Any]:
        """
        Obtener estado del engine.

        Returns:
            Dict con estado del engine
        """
        return {
            'enabled': self.enabled,
            'initialized': self._initialized,
            'has_var_calculator': self.var_calculator is not None,
            'has_stress_tester': self.stress_tester is not None,
            'has_exposure_manager': self.exposure_manager is not None,
            'has_drawdown_controller': self.drawdown_controller is not None,
            'has_correlation_analyzer': self.correlation_analyzer is not None,
            'has_risk_attributor': self.risk_attributor is not None,
            'has_alert_system': self.alert_system is not None,
            'risk_assessments_performed': self.risk_assessments_performed,
            'alerts_triggered': self.alerts_triggered,
            'risk_history_size': len(self.risk_history),
            'alert_history_size': len(self.alert_history),
            'timestamp': datetime.utcnow().isoformat(),
        }
