"""
ContextEngine - Engine principal de análisis de contexto de mercado.

Proporciona API unificada para:
- Detección de régimen (HMM, clustering, correlaciones)
- Análisis de volatilidad (GARCH, regímenes)
- Correlaciones dinámicas
- Indicadores macro
- Cache de resultados
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np

from .correlation_analyzers.correlation_network_analyzer import CorrelationNetworkAnalyzer
from .correlation_analyzers.dcc_garch_analyzer import DCCGARCHAnalyzer
from .correlation_analyzers.rolling_correlation_analyzer import RollingCorrelationAnalyzer
from .macro_indicators.market_breadth_analyzer import MarketBreadthAnalyzer
from .macro_indicators.sector_rotation_detector import SectorRotationDetector
from .macro_indicators.vix_analyzer import VIXAnalyzer
from .macro_indicators.yield_curve_analyzer import YieldCurveAnalyzer
from .regime_detectors.clustering_regime_detector import ClusteringRegimeDetector
from .regime_detectors.correlation_regime_detector import CorrelationRegimeDetector
from .regime_detectors.hmm_regime_detector import HMMRegimeDetector
from .volatility_analyzers.garch_analyzer import GARCHAnalyzer
from .volatility_analyzers.structural_change_detector import StructuralChangeDetector
from .volatility_analyzers.volatility_regime_detector import VolatilityRegimeDetector

logger = logging.getLogger(__name__)


class ContextEngine:
    """
    Engine principal de análisis de contexto.

    Coordina todos los detectores y analizadores para proporcionar
    una visión completa del contexto de mercado.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar Context Engine.

        Args:
            config: Configuración completa
        """
        config = config or {}
        self.config = config

        # Inicializar detectores de régimen
        self.hmm_detector = HMMRegimeDetector(config.get('hmm_config', {}))
        self.clustering_detector = ClusteringRegimeDetector(config.get('clustering_config', {}))
        self.correlation_regime_detector = CorrelationRegimeDetector(
            config.get('correlation_regime_config', {})
        )

        # Inicializar analizadores de volatilidad
        self.structural_change_detector = StructuralChangeDetector(
            config.get('structural_change_config', {})
        )
        self.volatility_regime_detector = VolatilityRegimeDetector(
            config.get('volatility_regime_config', {})
        )
        self.garch_analyzer = GARCHAnalyzer(config.get('garch_config', {}))

        # Inicializar analizadores de correlación
        self.rolling_correlation = RollingCorrelationAnalyzer(
            config.get('rolling_correlation_config', {})
        )
        self.dcc_garch = DCCGARCHAnalyzer(config.get('dcc_garch_config', {}))
        self.network_analyzer = CorrelationNetworkAnalyzer(config.get('network_config', {}))

        # Inicializar indicadores macro
        self.vix_analyzer = VIXAnalyzer()
        self.yield_curve_analyzer = YieldCurveAnalyzer()
        self.sector_rotation = SectorRotationDetector()
        self.market_breadth = MarketBreadthAnalyzer()

        # Cache
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = config.get('cache_ttl', 3600)  # 1 hora

        logger.info("ContextEngine inicializado")

    def get_current_regime(
        self,
        prices: List[float],
        method: str = 'ensemble',  # hmm, clustering, correlation, ensemble
    ) -> Dict[str, Any]:
        """
        Obtener régimen actual de mercado.

        Args:
            prices: Lista de precios históricos
            method: Método a usar (o 'ensemble' para combinar todos)

        Returns:
            Dict con régimen detectado y confianza
        """
        # Verificar cache
        cache_key = f"regime_{method}_{len(prices)}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.now() - cached.get('timestamp', datetime.min) < timedelta(
                seconds=self.cache_ttl
            ):
                return cached.get('data', {})

        results = {}

        if method == 'hmm' or method == 'ensemble':
            hmm_result = self.hmm_detector.detect(prices)
            results['hmm'] = hmm_result

        if method == 'clustering' or method == 'ensemble':
            clustering_result = self.clustering_detector.detect(prices)
            results['clustering'] = clustering_result

        if method == 'ensemble':
            # Combinar resultados
            regime = self._combine_regime_results(results)
            result = {
                'regime': regime['regime'],
                'confidence': regime['confidence'],
                'methods': results,
            }
        else:
            # Usar resultado del método específico
            result = results.get(method, {})

        # Cachear resultado
        self.cache[cache_key] = {'data': result, 'timestamp': datetime.now()}

        return result

    def get_volatility_regime(
        self, prices: List[float], volatility_history: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Obtener régimen de volatilidad.

        Args:
            prices: Lista de precios
            volatility_history: Historial de volatilidad (opcional)

        Returns:
            Dict con régimen de volatilidad
        """
        cache_key = f"volatility_{len(prices)}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.now() - cached.get('timestamp', datetime.min) < timedelta(
                seconds=self.cache_ttl
            ):
                return cached.get('data', {})

        # Detectar régimen de volatilidad
        vol_regime = self.volatility_regime_detector.detect(prices, volatility_history)

        # Detectar cambios estructurales
        structural_change = self.structural_change_detector.detect(prices)

        # GARCH analysis
        returns = [prices[i + 1] / prices[i] - 1 for i in range(len(prices) - 1)]
        garch_result = self.garch_analyzer.detect_clustering(returns)

        result = {
            'regime': vol_regime.get('regime', 'unknown'),
            'volatility': vol_regime.get('volatility', 0.0),
            'percentile': vol_regime.get('percentile', 50),
            'structural_change': structural_change,
            'garch_clustering': garch_result,
        }

        # Cachear
        self.cache[cache_key] = {'data': result, 'timestamp': datetime.now()}

        return result

    def get_correlation_matrix(
        self,
        price_data: Dict[str, List[float]],
        method: str = 'rolling',  # rolling, dcc_garch, network
    ) -> Dict[str, Any]:
        """
        Obtener matriz de correlación.

        Args:
            price_data: Dict con símbolos y precios
            method: Método a usar

        Returns:
            Dict con matriz de correlación y análisis
        """
        cache_key = f"correlation_{method}_{len(price_data)}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.now() - cached.get('timestamp', datetime.min) < timedelta(
                seconds=self.cache_ttl
            ):
                return cached.get('data', {})

        # Convertir a returns
        returns_data = {}
        for symbol, prices in price_data.items():
            if len(prices) > 1:
                returns = [prices[i + 1] / prices[i] - 1 for i in range(len(prices) - 1)]
                returns_data[symbol] = returns

        if method == 'rolling':
            result = self.rolling_correlation.calculate_rolling_correlation(returns_data)
        elif method == 'dcc_garch':
            result = self.dcc_garch.analyze(returns_data)
        elif method == 'network':
            # Calcular matriz primero
            rolling_result = self.rolling_correlation.calculate_rolling_correlation(returns_data)
            corr_matrix = np.array(rolling_result.get('correlation_matrix', []))
            if len(corr_matrix) > 0:
                network_result = self.network_analyzer.analyze_network(
                    corr_matrix, list(returns_data.keys())
                )
                result = {
                    'correlation_matrix': rolling_result.get('correlation_matrix'),
                    'network_analysis': network_result,
                }
            else:
                result = {'correlation_matrix': None}
        else:
            result = {'error': f'Método desconocido: {method}'}

        # Cachear
        self.cache[cache_key] = {'data': result, 'timestamp': datetime.now()}

        return result

    def _combine_regime_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Combinar resultados de múltiples métodos."""
        regimes = []
        confidences = []

        for method, result in results.items():
            if 'regime' in result:
                regimes.append(result['regime'])
            if 'confidence' in result:
                confidences.append(result['confidence'])

        # Régimen más común
        if regimes:
            regime = max(set(regimes), key=regimes.count)
        else:
            regime = 'unknown'

        # Confianza promedio
        confidence = np.mean(confidences) if confidences else 0.0

        return {'regime': regime, 'confidence': confidence}

    def get_context_summary(
        self, prices: List[float], price_data: Optional[Dict[str, List[float]]] = None
    ) -> Dict[str, Any]:
        """
        Obtener resumen completo de contexto.

        Args:
            prices: Precios del activo principal
            price_data: Precios de múltiples activos (opcional)

        Returns:
            Dict con resumen completo
        """
        summary = {
            'regime': self.get_current_regime(prices, method='ensemble'),
            'volatility_regime': self.get_volatility_regime(prices),
            'timestamp': datetime.now().isoformat(),
        }

        if price_data:
            summary['correlation'] = self.get_correlation_matrix(price_data, method='rolling')

        return summary
