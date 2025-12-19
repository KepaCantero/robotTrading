"""
Exposure Managers

Implementa gestión de exposición:
- Exposure limits por activo, sector, estrategia
- Leverage monitoring
- Concentration risk (Herfindahl index)
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np

from app.models.portfolio import Portfolio, Position

logger = logging.getLogger(__name__)


class BaseExposureManager(ABC):
    """Clase base para exposure managers."""

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar exposure manager.

        Args:
            config: Configuración del manager
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def analyze_exposure(self, portfolio: Portfolio, **kwargs) -> Dict[str, Any]:
        """
        Analizar exposición del portfolio.

        Args:
            portfolio: Portfolio a analizar
            **kwargs: Argumentos adicionales

        Returns:
            Análisis de exposición
        """
        pass


class ExposureManager(BaseExposureManager):
    """
    Exposure Manager principal.

    Gestiona exposición del portfolio por múltiples dimensiones.
    """

    def __init__(self, config: Dict[str, Any]):
        """Inicializar exposure manager."""
        super().__init__(config)

        # Límites de exposición
        self.max_asset_exposure = config.get('max_asset_exposure', 0.20)  # 20% por activo
        self.max_sector_exposure = config.get('max_sector_exposure', 0.30)  # 30% por sector
        self.max_strategy_exposure = config.get('max_strategy_exposure', 0.40)  # 40% por estrategia
        self.max_total_exposure = config.get('max_total_exposure', 0.95)  # 95% total

        # Leverage
        self.max_leverage = config.get('max_leverage', 1.0)  # Sin leverage por defecto
        self.warn_leverage = config.get('warn_leverage', 0.8)  # Warning a 80%

        # Historial de violaciones
        self.exposure_violations: List[Dict[str, Any]] = []
        self.max_violation_history = 1000

    def analyze_exposure(
        self,
        portfolio: Portfolio,
        strategy_allocations: Optional[Dict[str, List[str]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Analizar exposición completa del portfolio.

        Args:
            portfolio: Portfolio a analizar
            strategy_allocations: Asignación de símbolos por estrategia (opcional)
            **kwargs: Argumentos adicionales

        Returns:
            Análisis completo de exposición
        """
        try:
            # Análisis por activo
            asset_exposure = self._analyze_asset_exposure(portfolio)

            # Análisis por sector (si está disponible)
            sector_exposure = self._analyze_sector_exposure(portfolio)

            # Análisis por estrategia
            strategy_exposure = {}
            if strategy_allocations:
                strategy_exposure = self._analyze_strategy_exposure(portfolio, strategy_allocations)

            # Leverage
            leverage_analysis = self._analyze_leverage(portfolio)

            # Concentración
            concentration_analysis = self._analyze_concentration(portfolio)

            # Detectar violaciones
            violations = self._detect_violations(
                asset_exposure, sector_exposure, strategy_exposure, leverage_analysis
            )

            return {
                'asset_exposure': asset_exposure,
                'sector_exposure': sector_exposure,
                'strategy_exposure': strategy_exposure,
                'leverage': leverage_analysis,
                'concentration': concentration_analysis,
                'violations': violations,
                'total_exposure': float(
                    sum(pos.market_value for pos in portfolio.positions) / portfolio.total_equity
                )
                if portfolio.total_equity > 0
                else 0.0,
                'timestamp': datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Error analizando exposición: {e}", exc_info=True)
            return {'error': str(e)}

    def _analyze_asset_exposure(self, portfolio: Portfolio) -> Dict[str, Any]:
        """Analizar exposición por activo."""
        if portfolio.total_equity == 0:
            return {'exposures': {}, 'max_exposure': 0.0, 'violations': []}

        exposures = {}
        violations = []

        for position in portfolio.positions:
            exposure = float(position.market_value / portfolio.total_equity)
            exposures[position.symbol] = {
                'exposure': exposure,
                'value': float(position.market_value),
                'quantity': float(position.quantity),
                'limit': self.max_asset_exposure,
                'violation': exposure > self.max_asset_exposure,
            }

            if exposure > self.max_asset_exposure:
                violations.append(
                    {
                        'type': 'asset_exposure',
                        'symbol': position.symbol,
                        'exposure': exposure,
                        'limit': self.max_asset_exposure,
                        'severity': 'high'
                        if exposure > self.max_asset_exposure * 1.5
                        else 'medium',
                    }
                )

        max_exposure = (
            max(exposures.values(), key=lambda x: x['exposure'])['exposure'] if exposures else 0.0
        )

        return {
            'exposures': exposures,
            'max_exposure': max_exposure,
            'violations': violations,
            'limit': self.max_asset_exposure,
        }

    def _analyze_sector_exposure(self, portfolio: Portfolio) -> Dict[str, Any]:
        """Analizar exposición por sector."""
        if portfolio.total_equity == 0:
            return {'exposures': {}, 'max_exposure': 0.0, 'violations': []}

        # Agrupar por asset class (usando como proxy de sector)
        sector_exposures = {}

        for position in portfolio.positions:
            sector = (
                position.asset_class.value
                if hasattr(position.asset_class, 'value')
                else str(position.asset_class)
            )

            if sector not in sector_exposures:
                sector_exposures[sector] = Decimal("0")

            sector_exposures[sector] += position.market_value

        # Convertir a porcentajes
        exposures = {}
        violations = []

        for sector, value in sector_exposures.items():
            exposure = float(value / portfolio.total_equity)
            exposures[sector] = {
                'exposure': exposure,
                'value': float(value),
                'limit': self.max_sector_exposure,
                'violation': exposure > self.max_sector_exposure,
            }

            if exposure > self.max_sector_exposure:
                violations.append(
                    {
                        'type': 'sector_exposure',
                        'sector': sector,
                        'exposure': exposure,
                        'limit': self.max_sector_exposure,
                        'severity': 'high'
                        if exposure > self.max_sector_exposure * 1.5
                        else 'medium',
                    }
                )

        max_exposure = (
            max(exposures.values(), key=lambda x: x['exposure'])['exposure'] if exposures else 0.0
        )

        return {
            'exposures': exposures,
            'max_exposure': max_exposure,
            'violations': violations,
            'limit': self.max_sector_exposure,
        }

    def _analyze_strategy_exposure(
        self, portfolio: Portfolio, strategy_allocations: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Analizar exposición por estrategia."""
        if portfolio.total_equity == 0:
            return {'exposures': {}, 'max_exposure': 0.0, 'violations': []}

        # Crear mapa símbolo -> estrategia
        symbol_to_strategy = {}
        for strategy, symbols in strategy_allocations.items():
            for symbol in symbols:
                symbol_to_strategy[symbol] = strategy

        # Agrupar por estrategia
        strategy_exposures = {}

        for position in portfolio.positions:
            strategy = symbol_to_strategy.get(position.symbol, 'unknown')

            if strategy not in strategy_exposures:
                strategy_exposures[strategy] = Decimal("0")

            strategy_exposures[strategy] += position.market_value

        # Convertir a porcentajes
        exposures = {}
        violations = []

        for strategy, value in strategy_exposures.items():
            exposure = float(value / portfolio.total_equity)
            exposures[strategy] = {
                'exposure': exposure,
                'value': float(value),
                'limit': self.max_strategy_exposure,
                'violation': exposure > self.max_strategy_exposure,
            }

            if exposure > self.max_strategy_exposure:
                violations.append(
                    {
                        'type': 'strategy_exposure',
                        'strategy': strategy,
                        'exposure': exposure,
                        'limit': self.max_strategy_exposure,
                        'severity': 'high'
                        if exposure > self.max_strategy_exposure * 1.5
                        else 'medium',
                    }
                )

        max_exposure = (
            max(exposures.values(), key=lambda x: x['exposure'])['exposure'] if exposures else 0.0
        )

        return {
            'exposures': exposures,
            'max_exposure': max_exposure,
            'violations': violations,
            'limit': self.max_strategy_exposure,
        }

    def _analyze_leverage(self, portfolio: Portfolio) -> Dict[str, Any]:
        """Analizar leverage del portfolio."""
        if portfolio.total_equity == 0:
            return {'leverage': 0.0, 'warnings': [], 'violations': []}

        # Leverage = exposición total / equity
        total_exposure = sum(pos.market_value for pos in portfolio.positions)
        leverage = float(total_exposure / portfolio.total_equity)

        warnings = []
        violations = []

        if leverage > self.max_leverage:
            violations.append(
                {
                    'type': 'leverage',
                    'leverage': leverage,
                    'limit': self.max_leverage,
                    'severity': 'critical',
                }
            )
        elif leverage > self.warn_leverage:
            warnings.append(
                {
                    'type': 'leverage_warning',
                    'leverage': leverage,
                    'warning_threshold': self.warn_leverage,
                    'severity': 'medium',
                }
            )

        return {
            'leverage': leverage,
            'total_exposure': float(total_exposure),
            'equity': float(portfolio.total_equity),
            'warnings': warnings,
            'violations': violations,
            'max_leverage': self.max_leverage,
            'warn_leverage': self.warn_leverage,
        }

    def _analyze_concentration(self, portfolio: Portfolio) -> Dict[str, Any]:
        """Analizar concentración del portfolio usando Herfindahl index."""
        if portfolio.total_equity == 0:
            return {'herfindahl_index': 0.0, 'effective_n': 0, 'concentration_level': 'low'}

        # Calcular pesos de cada posición
        weights = [float(pos.market_value / portfolio.total_equity) for pos in portfolio.positions]

        if not weights:
            return {'herfindahl_index': 0.0, 'effective_n': 0, 'concentration_level': 'low'}

        # Herfindahl index: suma de cuadrados de pesos
        herfindahl_index = sum(w**2 for w in weights)

        # Effective number of positions: 1 / HHI
        effective_n = 1.0 / herfindahl_index if herfindahl_index > 0 else len(weights)

        # Nivel de concentración
        if herfindahl_index > 0.5:
            concentration_level = 'very_high'
        elif herfindahl_index > 0.3:
            concentration_level = 'high'
        elif herfindahl_index > 0.15:
            concentration_level = 'medium'
        else:
            concentration_level = 'low'

        return {
            'herfindahl_index': float(herfindahl_index),
            'effective_n': float(effective_n),
            'concentration_level': concentration_level,
            'n_positions': len(weights),
            'top_5_weight': sum(sorted(weights, reverse=True)[:5])
            if len(weights) >= 5
            else sum(weights),
            'top_10_weight': sum(sorted(weights, reverse=True)[:10])
            if len(weights) >= 10
            else sum(weights),
        }

    def _detect_violations(
        self,
        asset_exposure: Dict[str, Any],
        sector_exposure: Dict[str, Any],
        strategy_exposure: Dict[str, Any],
        leverage_analysis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Detectar todas las violaciones de exposición."""
        violations = []

        # Violaciones de activos
        violations.extend(asset_exposure.get('violations', []))

        # Violaciones de sectores
        violations.extend(sector_exposure.get('violations', []))

        # Violaciones de estrategias
        violations.extend(strategy_exposure.get('violations', []))

        # Violaciones de leverage
        violations.extend(leverage_analysis.get('violations', []))

        # Guardar en historial
        for violation in violations:
            violation['timestamp'] = datetime.utcnow().isoformat()
            self.exposure_violations.append(violation)

        # Mantener historial limitado
        if len(self.exposure_violations) > self.max_violation_history:
            self.exposure_violations = self.exposure_violations[-self.max_violation_history :]

        return violations

    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del manager."""
        return {
            'max_asset_exposure': self.max_asset_exposure,
            'max_sector_exposure': self.max_sector_exposure,
            'max_strategy_exposure': self.max_strategy_exposure,
            'max_total_exposure': self.max_total_exposure,
            'max_leverage': self.max_leverage,
            'violations_count': len(self.exposure_violations),
        }
