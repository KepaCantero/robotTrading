"""
Portfolio Optimizers

Implementa diferentes métodos de optimización de portfolio:
- Mean-variance optimization (Markowitz)
- Risk parity allocation
- Black-Litterman model
- Kelly Criterion adaptativo
"""

import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    import cvxpy as cp

    CVXPY_AVAILABLE = True
except ImportError:
    CVXPY_AVAILABLE = False
    logger.warning("cvxpy no disponible. Optimización avanzada limitada.")

try:
    from pypfopt import EfficientFrontier, expected_returns as pypfopt_expected_returns, risk_models

    PYPORTFOLIO_AVAILABLE = True
except ImportError:
    PYPORTFOLIO_AVAILABLE = False
    logger.warning("PyPortfolioOpt no disponible. Usando implementación básica.")


class BaseOptimizer(ABC):
    """Clase base para optimizadores de portfolio."""

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar optimizer.

        Args:
            config: Configuración del optimizer
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def optimize(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Optimizar asignación de capital.

        Args:
            expected_returns: Retornos esperados (array 1D)
            cov_matrix: Matriz de covarianza (array 2D)
            constraints: Restricciones adicionales

        Returns:
            Dict con pesos optimizados y métricas
        """
        pass


class MarkowitzOptimizer(BaseOptimizer):
    """
    Mean-Variance Optimizer (Markowitz).

    Maximiza Sharpe ratio sujeto a restricciones.
    """

    def optimize(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Optimizar usando teoría de Markowitz.

        Args:
            expected_returns: Retornos esperados
            cov_matrix: Matriz de covarianza
            constraints: Restricciones (max_weight, min_weight, etc.)

        Returns:
            Dict con pesos optimizados
        """
        constraints = constraints or {}

        try:
            if PYPORTFOLIO_AVAILABLE:
                return self._optimize_pypfopt(expected_returns, cov_matrix, constraints)
            elif CVXPY_AVAILABLE:
                return self._optimize_cvxpy(expected_returns, cov_matrix, constraints)
            else:
                return self._optimize_basic(expected_returns, cov_matrix, constraints)
        except Exception as e:
            self.logger.error(f"Error en optimización Markowitz: {e}", exc_info=True)
            return self._equal_weight_fallback(len(expected_returns))

    def _optimize_pypfopt(
        self, expected_returns: np.ndarray, cov_matrix: np.ndarray, constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimizar usando PyPortfolioOpt."""
        try:
            # Crear EfficientFrontier
            ef = EfficientFrontier(expected_returns, cov_matrix)

            # Aplicar restricciones
            max_weight = constraints.get('max_weight', 1.0)
            min_weight = constraints.get('min_weight', 0.0)

            # Maximizar Sharpe ratio
            weights = ef.max_sharpe()

            # Normalizar si es necesario
            cleaned_weights = ef.clean_weights()

            # Convertir a dict
            weights_dict = {k: float(v) for k, v in cleaned_weights.items()}

            # Calcular métricas
            performance = ef.portfolio_performance(verbose=False)

            return {
                'weights': weights_dict,
                'expected_return': float(performance[0]),
                'volatility': float(performance[1]),
                'sharpe_ratio': float(performance[2]),
                'method': 'markowitz_pypfopt',
            }
        except Exception as e:
            self.logger.warning(f"PyPortfolioOpt falló: {e}. Usando método básico.")
            return self._optimize_basic(expected_returns, cov_matrix, constraints)

    def _optimize_cvxpy(
        self, expected_returns: np.ndarray, cov_matrix: np.ndarray, constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimizar usando cvxpy."""
        n = len(expected_returns)

        # Variables de decisión (pesos)
        w = cp.Variable(n)

        # Parámetros
        mu = cp.Parameter(n)
        mu.value = expected_returns
        Sigma = cp.Parameter((n, n), PSD=True)
        Sigma.value = cov_matrix

        # Objetivo: Maximizar retorno esperado - riesgo (penalizado)
        risk_aversion = self.config.get('risk_aversion', 0.5)
        portfolio_return = mu.T @ w
        portfolio_risk = cp.quad_form(w, Sigma)
        objective = cp.Maximize(portfolio_return - risk_aversion * portfolio_risk)

        # Restricciones
        constraint_list = [cp.sum(w) == 1, w >= 0]  # Long only

        # Restricciones adicionales
        max_weight = constraints.get('max_weight', 1.0)
        min_weight = constraints.get('min_weight', 0.0)
        constraint_list.append(w <= max_weight)
        constraint_list.append(w >= min_weight)

        # Resolver
        problem = cp.Problem(objective, constraint_list)
        problem.solve()

        if problem.status == 'optimal':
            weights = w.value
            weights = np.maximum(weights, 0)  # Asegurar no negativos
            weights = weights / weights.sum()  # Normalizar

            # Calcular métricas
            expected_return = float(np.dot(weights, expected_returns))
            volatility = float(np.sqrt(np.dot(weights, np.dot(cov_matrix, weights))))
            sharpe_ratio = expected_return / volatility if volatility > 0 else 0.0

            return {
                'weights': {f'asset_{i}': float(w) for i, w in enumerate(weights)},
                'expected_return': expected_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'method': 'markowitz_cvxpy',
            }
        else:
            self.logger.warning(f"Optimización cvxpy no convergió: {problem.status}")
            return self._equal_weight_fallback(n)

    def _optimize_basic(
        self, expected_returns: np.ndarray, cov_matrix: np.ndarray, constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimización básica sin dependencias externas."""
        n = len(expected_returns)

        # Método simple: inverso de varianza (inverse volatility weighting)
        variances = np.diag(cov_matrix)
        inv_vol = 1.0 / np.sqrt(variances)
        weights = inv_vol / inv_vol.sum()

        # Aplicar restricciones
        max_weight = constraints.get('max_weight', 1.0)
        min_weight = constraints.get('min_weight', 0.0)
        weights = np.clip(weights, min_weight, max_weight)
        weights = weights / weights.sum()  # Re-normalizar

        # Calcular métricas
        expected_return = float(np.dot(weights, expected_returns))
        volatility = float(np.sqrt(np.dot(weights, np.dot(cov_matrix, weights))))
        sharpe_ratio = expected_return / volatility if volatility > 0 else 0.0

        return {
            'weights': {f'asset_{i}': float(w) for i, w in enumerate(weights)},
            'expected_return': expected_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'method': 'markowitz_basic',
        }

    def _equal_weight_fallback(self, n: int) -> Dict[str, Any]:
        """Fallback a pesos iguales."""
        weight = 1.0 / n
        return {
            'weights': {f'asset_{i}': weight for i in range(n)},
            'expected_return': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'method': 'equal_weight_fallback',
        }


class RiskParityOptimizer(BaseOptimizer):
    """
    Risk Parity Optimizer.

    Asigna pesos para que cada activo contribuya igualmente al riesgo total.
    """

    def optimize(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Optimizar usando Risk Parity.

        Args:
            expected_returns: Retornos esperados (no usado en Risk Parity)
            cov_matrix: Matriz de covarianza
            constraints: Restricciones adicionales

        Returns:
            Dict con pesos optimizados
        """
        constraints = constraints or {}

        try:
            n = len(cov_matrix)

            # Método básico: Inverse volatility weighting
            # (aproximación simple de Risk Parity)
            variances = np.diag(cov_matrix)
            inv_vol = 1.0 / np.sqrt(variances)
            weights = inv_vol / inv_vol.sum()

            # Método avanzado: Optimización iterativa para igualar contribución de riesgo
            if CVXPY_AVAILABLE:
                weights = self._optimize_risk_parity_cvxpy(cov_matrix, constraints)

            # Aplicar restricciones
            max_weight = constraints.get('max_weight', 1.0)
            min_weight = constraints.get('min_weight', 0.0)
            weights = np.clip(weights, min_weight, max_weight)
            weights = weights / weights.sum()

            # Calcular métricas
            expected_return = float(np.dot(weights, expected_returns))
            volatility = float(np.sqrt(np.dot(weights, np.dot(cov_matrix, weights))))
            sharpe_ratio = expected_return / volatility if volatility > 0 else 0.0

            return {
                'weights': {f'asset_{i}': float(w) for i, w in enumerate(weights)},
                'expected_return': expected_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'method': 'risk_parity',
            }
        except Exception as e:
            self.logger.error(f"Error en optimización Risk Parity: {e}", exc_info=True)
            return self._equal_weight_fallback(len(cov_matrix))

    def _optimize_risk_parity_cvxpy(
        self, cov_matrix: np.ndarray, constraints: Dict[str, Any]
    ) -> np.ndarray:
        """Optimización Risk Parity usando cvxpy."""
        n = len(cov_matrix)
        w = cp.Variable(n)

        # Objetivo: Minimizar diferencia en contribución de riesgo
        portfolio_risk = cp.quad_form(w, cov_matrix)
        risk_contributions = cp.multiply(w, cp.quad_form(w, cov_matrix) / w)

        # Minimizar varianza de contribuciones de riesgo
        objective = cp.Minimize(cp.sum_squares(risk_contributions - portfolio_risk / n))

        # Restricciones
        constraint_list = [cp.sum(w) == 1, w >= 0]

        # Resolver
        problem = cp.Problem(objective, constraint_list)
        problem.solve()

        if problem.status == 'optimal':
            weights = w.value
            weights = np.maximum(weights, 0)
            weights = weights / weights.sum()
            return weights
        else:
            # Fallback a inverse volatility
            variances = np.diag(cov_matrix)
            inv_vol = 1.0 / np.sqrt(variances)
            return inv_vol / inv_vol.sum()

    def _equal_weight_fallback(self, n: int) -> Dict[str, Any]:
        """Fallback a pesos iguales."""
        weight = 1.0 / n
        return {
            'weights': {f'asset_{i}': weight for i in range(n)},
            'expected_return': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'method': 'equal_weight_fallback',
        }


class BlackLittermanOptimizer(BaseOptimizer):
    """
    Black-Litterman Optimizer.

    Combina vistas del mercado con equilibrio del mercado.
    """

    def optimize(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Optimizar usando modelo Black-Litterman.

        Args:
            expected_returns: Retornos de equilibrio del mercado
            cov_matrix: Matriz de covarianza
            constraints: Restricciones y vistas

        Returns:
            Dict con pesos optimizados
        """
        constraints = constraints or {}

        try:
            n = len(expected_returns)

            # Obtener vistas del usuario (si están disponibles)
            views = constraints.get('views', {})
            view_confidences = constraints.get('view_confidences', {})

            # Si no hay vistas, usar retornos de equilibrio directamente
            if not views:
                # Usar Markowitz con retornos de equilibrio
                markowitz = MarkowitzOptimizer(self.config)
                return markowitz.optimize(expected_returns, cov_matrix, constraints)

            # Implementación simplificada de Black-Litterman
            # Tau (escala de incertidumbre)
            tau = constraints.get('tau', 0.05)

            # Construir matriz de vistas P y vector de vistas Q
            P = self._build_views_matrix(n, views)
            Q = self._build_views_vector(views)
            Omega = self._build_uncertainty_matrix(n, views, view_confidences)

            # Retornos de equilibrio (PI)
            PI = expected_returns

            # Retornos ajustados por Black-Litterman
            # BL_return = [(tau*Sigma)^-1 + P'*Omega^-1*P]^-1 * [(tau*Sigma)^-1*PI + P'*Omega^-1*Q]
            tau_Sigma_inv = np.linalg.inv(tau * cov_matrix)
            Omega_inv = np.linalg.inv(Omega) if Omega.shape[0] > 0 else np.array([])

            if Omega_inv.shape[0] > 0:
                # Con vistas
                A = tau_Sigma_inv + P.T @ Omega_inv @ P
                b = tau_Sigma_inv @ PI + P.T @ Omega_inv @ Q
                bl_returns = np.linalg.solve(A, b)
            else:
                # Sin vistas, usar equilibrio
                bl_returns = PI

            # Usar Markowitz con retornos BL
            markowitz = MarkowitzOptimizer(self.config)
            return markowitz.optimize(bl_returns, cov_matrix, constraints)

        except Exception as e:
            self.logger.error(f"Error en optimización Black-Litterman: {e}", exc_info=True)
            return self._equal_weight_fallback(len(expected_returns))

    def _build_views_matrix(self, n: int, views: Dict[str, Any]) -> np.ndarray:
        """Construir matriz de vistas P."""
        # Implementación simplificada
        # En producción, esto debería ser más sofisticado
        P = np.eye(n)  # Por defecto, vista por cada activo
        return P

    def _build_views_vector(self, views: Dict[str, Any]) -> np.ndarray:
        """Construir vector de vistas Q."""
        # Implementación simplificada
        n = len(views) if views else 1
        Q = np.zeros(n)
        return Q

    def _build_uncertainty_matrix(
        self, n: int, views: Dict[str, Any], view_confidences: Dict[str, Any]
    ) -> np.ndarray:
        """Construir matriz de incertidumbre Omega."""
        # Implementación simplificada
        n_views = len(views) if views else n
        Omega = np.eye(n_views) * 0.1  # Diagonal con incertidumbre constante
        return Omega

    def _equal_weight_fallback(self, n: int) -> Dict[str, Any]:
        """Fallback a pesos iguales."""
        weight = 1.0 / n
        return {
            'weights': {f'asset_{i}': weight for i in range(n)},
            'expected_return': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'method': 'equal_weight_fallback',
        }


class KellyCriterionOptimizer(BaseOptimizer):
    """
    Kelly Criterion Optimizer adaptativo.

    Optimiza tamaño de posición basado en probabilidades de éxito.
    """

    def optimize(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Optimizar usando Kelly Criterion adaptativo.

        Args:
            expected_returns: Retornos esperados
            cov_matrix: Matriz de covarianza (no usado directamente en Kelly)
            constraints: Restricciones y probabilidades de éxito

        Returns:
            Dict con pesos optimizados
        """
        constraints = constraints or {}

        try:
            n = len(expected_returns)

            # Obtener probabilidades de éxito y retornos por trade
            win_probabilities = constraints.get('win_probabilities', np.ones(n) * 0.5)
            win_returns = constraints.get('win_returns', expected_returns)
            loss_returns = constraints.get('loss_returns', -expected_returns * 0.5)

            # Kelly fraction para cada activo: f = (p*b - q) / b
            # donde p=probabilidad ganar, q=probabilidad perder, b=ratio ganancia/pérdida
            kelly_fractions = []

            for i in range(n):
                p = float(win_probabilities[i])
                q = 1 - p
                win_return = float(win_returns[i])
                loss_return = abs(float(loss_returns[i]))

                if loss_return > 0:
                    b = win_return / loss_return  # Ratio ganancia/pérdida
                    kelly_f = (p * b - q) / b if b > 0 else 0
                    # Asegurar que Kelly fraction esté en [0, 1]
                    kelly_f = max(0, min(1, kelly_f))
                else:
                    kelly_f = 0

                kelly_fractions.append(kelly_f)

            # Normalizar para que sumen 1 (asignación de capital)
            kelly_fractions = np.array(kelly_fractions)
            if kelly_fractions.sum() > 0:
                weights = kelly_fractions / kelly_fractions.sum()
            else:
                weights = np.ones(n) / n  # Fallback a pesos iguales

            # Aplicar restricciones
            max_weight = constraints.get('max_weight', 1.0)
            min_weight = constraints.get('min_weight', 0.0)
            weights = np.clip(weights, min_weight, max_weight)
            weights = weights / weights.sum()

            # Calcular métricas
            expected_return = float(np.dot(weights, expected_returns))
            volatility = float(np.sqrt(np.dot(weights, np.dot(cov_matrix, weights))))
            sharpe_ratio = expected_return / volatility if volatility > 0 else 0.0

            return {
                'weights': {f'asset_{i}': float(w) for i, w in enumerate(weights)},
                'expected_return': expected_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'method': 'kelly_criterion',
                'kelly_fractions': {
                    f'asset_{i}': float(kf) for i, kf in enumerate(kelly_fractions)
                },
            }
        except Exception as e:
            self.logger.error(f"Error en optimización Kelly Criterion: {e}", exc_info=True)
            return self._equal_weight_fallback(len(expected_returns))

    def _equal_weight_fallback(self, n: int) -> Dict[str, Any]:
        """Fallback a pesos iguales."""
        weight = 1.0 / n
        return {
            'weights': {f'asset_{i}': weight for i in range(n)},
            'expected_return': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'method': 'equal_weight_fallback',
        }
