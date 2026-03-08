"""
System Availability Checks
Extracted from compliance_engine.py for SRP compliance.
TASK-24: SRP Refactoring
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SystemAvailability:
    """Track availability of all 17 systems (8 main + 12 compliance, with overlap)."""

    def __init__(self, enable_logging: bool = False):
        """
        Initialize SystemAvailability.

        Args:
            enable_logging: Enable detailed logging for system checks
        """
        # First: Set simple attributes before any operations that might use them
        self.enable_logging = enable_logging

        # Second: Initialize tracking dictionary
        self._systems: Dict[str, bool] = {}

        # Third: Check all systems (may use enable_logging)
        self._check_all_systems()

    def _check_all_systems(self):
        """Check availability of all systems."""
        systems_to_check = {
            # Existing systems
            "backtesting_engine": self._check_backtesting,
            "live_trading": self._check_live_trading,
            "paper_trading": self._check_paper_trading,
            "strategies": self._check_strategies,
            "risk_engine": self._check_risk_engine,
            "portfolio_engine": self._check_portfolio_engine,
            "data_engine": self._check_data_engine,
            "context_engine": self._check_context_engine,
            "execution_engine": self._check_execution_engine,
            # Compliance systems (12 rules)
            "ernest_chan": self._check_chan,
            "narang": self._check_narang,
            "lopez_de_prado": self._check_lopez_de_prado,
            "tomasini": self._check_tomasini,
            "hastie": self._check_hastie,
            "harris": self._check_harris,
            "ohara": self._check_ohara,
            "percival": self._check_percival,
            "hull": self._check_hull,
            "google_sre": self._check_sre,
            "beck_tdd": self._check_beck,
            "martin_arch": self._check_martin,
        }

        for name, check_func in systems_to_check.items():
            try:
                self._systems[name] = check_func()
            except Exception:
                self._systems[name] = False

    def _check_backtesting(self) -> bool:
        try:
            from importlib.util import find_spec

            return find_spec("app.backtesting") is not None
        except ImportError:
            return False

    def _check_live_trading(self) -> bool:
        try:
            from importlib.util import find_spec

            return find_spec("app.providers.live_trading") is not None
        except ImportError:
            return False

    def _check_paper_trading(self) -> bool:
        try:
            from importlib.util import find_spec

            return find_spec("app.providers.paper_trading") is not None
        except ImportError:
            return False

    def _check_strategies(self) -> bool:
        try:
            from importlib.util import find_spec

            return find_spec("app.strategies") is not None
        except ImportError:
            return False

    def _check_risk_engine(self) -> bool:
        try:
            from importlib.util import find_spec

            return find_spec("app.engines.risk_engine") is not None
        except ImportError:
            return False

    def _check_portfolio_engine(self) -> bool:
        try:
            from importlib.util import find_spec

            return find_spec("app.engines.portfolio_engine") is not None
        except ImportError:
            return False

    def _check_data_engine(self) -> bool:
        try:
            from importlib.util import find_spec

            return find_spec("app.services.data_service") is not None
        except ImportError:
            return False

    def _check_context_engine(self) -> bool:
        try:
            from importlib.util import find_spec

            return find_spec("app.maestro") is not None
        except ImportError:
            return False

    def _check_execution_engine(self) -> bool:
        """
        Check if execution engine (microstructure) is available.

        The execution engine is implemented as MarketMicrostructureEngine
        in the microstructure subdirectory.
        """
        try:
            from importlib.util import find_spec

            return find_spec("app.microstructure") is not None
        except ImportError as e:
            if self.enable_logging:
                logger.debug(f"Execution engine not available: {e}")
            return False

    def _check_chan(self) -> bool:
        try:
            from importlib.util import find_spec

            return find_spec("app.services.momentum_analysis_chan") is not None
        except ImportError:
            return False

    def _check_narang(self) -> bool:
        try:
            from importlib.util import find_spec

            return find_spec("app.services") is not None
        except ImportError:
            return False

    def _check_lopez_de_prado(self) -> bool:
        try:
            from importlib.util import find_spec

            return find_spec("app.services.optimization_chan") is not None
        except ImportError:
            return False

    def _check_tomasini(self) -> bool:
        try:
            # Tomasini is about architecture patterns
            return True  # Always available
        except ImportError:
            return False

    def _check_hastie(self) -> bool:
        try:
            from importlib.util import find_spec

            return find_spec("app.ensemble") is not None
        except ImportError:
            return False

    def _check_harris(self) -> bool:
        try:
            from importlib.util import find_spec

            return (
                find_spec("app.engines.execution_engine.microstructure.harris_integration")
                is not None
            )
        except ImportError:
            return False

    def _check_ohara(self) -> bool:
        try:
            from importlib.util import find_spec

            return find_spec("app.microstructure") is not None
        except ImportError:
            return False

    def _check_percival(self) -> bool:
        try:
            # Percival is about architecture patterns
            return True  # Always available
        except ImportError:
            return False

    def _check_hull(self) -> bool:
        try:
            from importlib.util import find_spec

            return find_spec("app.services.risk_management_chan") is not None
        except ImportError:
            return False

    def _check_sre(self) -> bool:
        try:
            from importlib.util import find_spec

            return find_spec("app.sre") is not None
        except ImportError:
            return False

    def _check_beck(self) -> bool:
        try:
            # Beck is about TDD patterns
            return True  # Always available
        except ImportError:
            return False

    def _check_martin(self) -> bool:
        try:
            # Martin is about clean architecture
            return True  # Always available
        except ImportError:
            return False

    def get_availability(self) -> Dict[str, bool]:
        """Get availability of all systems."""
        return self._systems.copy()

    def is_available(self, system_name: str) -> bool:
        """Check if a specific system is available."""
        return self._systems.get(system_name, False)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of system availability."""
        available = sum(1 for v in self._systems.values() if v)
        total = len(self._systems)
        return {
            "total_systems": total,
            "available_systems": available,
            "availability_percentage": (available / total * 100) if total > 0 else 0,
            "systems": self._systems,
        }


# =============================================================================
# SYSTEM BUS - Orchestrates All 17 Systems
# =============================================================================
