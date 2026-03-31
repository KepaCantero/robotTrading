"""
Portfolio Optimizers

Implementa diferentes métodos de optimización de portfolio:
- Mean-variance optimization (Markowitz)
- Risk parity allocation
- Black-Litterman model
- Kelly Criterion adaptativo
- Handcrafted Weights (Carver's methodology)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional, Union, cast

import numpy as np

logger = logging.getLogger(__name__)

# Import handcrafted optimizer from separate file
try:
    from .handcrafted_optimizer import HandcraftedWeightsOptimizer, create_handcrafted_weights

    HANDCRAFTED_AVAILABLE = True
except ImportError:
    HANDCRAFTED_AVAILABLE = False
    HandcraftedWeightsOptimizer = None
    create_handcrafted_weights = None

# Import HRP optimizer from separate file
try:
    from .hierarchical_risk_parity import (
        HierarchicalRiskParity,
        HRPOptimizer,
        compute_hrp_weights,
        plot_hrp_dendrogram,
    )

    HRP_AVAILABLE = True
    logger.info("Hierarchical Risk Parity (HRP) optimizer is available")
except ImportError:
    HRP_AVAILABLE = False
    HierarchicalRiskParity = None
    HRPOptimizer = None
    compute_hrp_weights = None
    plot_hrp_dendrogram = None
    logger.warning(
        "Hierarchical Risk Parity (HRP) optimizer could not be imported. Check scipy installation."
    )

# cvxpy import with fallback - provides convex optimization
try:
    import cvxpy as cp

    CVXPY_AVAILABLE = True
    logger.info("cvxpy is available for convex optimization")
except ImportError:
    cp = None
    CVXPY_AVAILABLE = False
    logger.warning(
        "cvxpy is not installed. Portfolio optimization will use scipy-based fallbacks. "
        "For full convex optimization capabilities, install cvxpy: pip install cvxpy"
    )

# PyPortfolioOpt import with fallback - provides efficient frontier optimization
try:
    from pyportfolioopt import EfficientFrontier

    PYPFOPT_AVAILABLE = True
    logger.info("PyPortfolioOpt is available for efficient frontier optimization")
except ImportError:
    EfficientFrontier = None
    PYPFOPT_AVAILABLE = False
    logger.warning(
        "PyPortfolioOpt is not installed. Portfolio optimization will use basic methods. "
        "For advanced optimization features, install PyPortfolioOpt: pip install pyportfolioopt"
    )

# scipy is REQUIRED - provides core optimization capabilities
try:
    from scipy.optimize import minimize

    SCIPY_AVAILABLE = True
    logger.info("scipy.optimize is available")
except ImportError:
    minimize = None
    SCIPY_AVAILABLE = False
    logger.error(
        "scipy is not installed and is REQUIRED for optimization. "
        "Please install scipy: pip install scipy"
    )


class BaseOptimizer(ABC):
    """Clase base para optimizadores de portfolio."""

    def __init__(self, config: dict[str, Any]):
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
        constraints: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Optimizar asignación de capital.

        Args:
            expected_returns: Retornos esperados (array 1D)
            cov_matrix: Matriz de covarianza (array 2D)
            constraints: Restricciones adicionales

        Returns:
            Dict con pesos optimizados y métricas
        """


class MarkowitzOptimizer(BaseOptimizer):
    """
    Mean-Variance Optimizer (Markowitz).

    Maximiza Sharpe ratio sujeto a restricciones.
    """

    def optimize(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
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
            # Try PyPortfolioOpt first (most robust)
            if PYPFOPT_AVAILABLE:
                return self._optimize_pypfopt(expected_returns, cov_matrix, constraints)
            # Fall back to cvxpy if available
            elif CVXPY_AVAILABLE:
                return self._optimize_cvxpy(expected_returns, cov_matrix, constraints)
            # Fall back to scipy-based optimization
            elif SCIPY_AVAILABLE:
                self.logger.info(
                    "Using scipy-based optimization (cvxpy and PyPortfolioOpt not available)"
                )
                return self._optimize_scipy(expected_returns, cov_matrix, constraints)
            # Final fallback to basic analytical methods
            else:
                self.logger.warning(
                    "No optimization libraries available, using basic analytical method"
                )
                return self._optimize_basic(expected_returns, cov_matrix, constraints)
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            self.logger.error(f"Error en optimización Markowitz: {e}", exc_info=True)
            return self._equal_weight_fallback(len(expected_returns))

    def _optimize_pypfopt(
        self, expected_returns: np.ndarray, cov_matrix: np.ndarray, constraints: dict[str, Any]
    ) -> dict[str, Any]:
        """Optimizar usando PyPortfolioOpt."""
        try:
            # Crear EfficientFrontier
            ef = EfficientFrontier(expected_returns, cov_matrix)

            # Aplicar restricciones
            constraints.get("max_weight", 1.0)
            constraints.get("min_weight", 0.0)

            # Maximizar Sharpe ratio
            ef.max_sharpe()

            # Normalizar si es necesario
            cleaned_weights = ef.clean_weights()

            # Convertir a dict
            weights_dict = {k: float(v) for k, v in cleaned_weights.items()}

            # Calcular métricas
            performance = ef.portfolio_performance(verbose=False)

            return {
                "weights": weights_dict,
                "expected_return": float(performance[0]),
                "volatility": float(performance[1]),
                "sharpe_ratio": float(performance[2]),
                "method": "markowitz_pypfopt",
            }
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.warning(f"PyPortfolioOpt falló: {e}. Usando método básico.")
            return self._optimize_basic(expected_returns, cov_matrix, constraints)

    def _optimize_cvxpy(
        self, expected_returns: np.ndarray, cov_matrix: np.ndarray, constraints: dict[str, Any]
    ) -> dict[str, Any]:
        """Optimizar usando cvxpy."""
        if not CVXPY_AVAILABLE or cp is None:
            raise ImportError("cvxpy is not available")

        n = len(expected_returns)

        # Variables de decisión (pesos)
        w = cp.Variable(n)

        # Parámetros
        mu = cp.Parameter(n)
        mu.value = expected_returns
        Sigma = cp.Parameter((n, n), PSD=True)
        Sigma.value = cov_matrix

        # Objetivo: Maximizar retorno esperado - riesgo (penalizado)
        risk_aversion = self.config.get("risk_aversion", 0.5)
        portfolio_return = mu.T @ w
        portfolio_risk = cp.quad_form(w, Sigma)
        objective = cp.Maximize(portfolio_return - risk_aversion * portfolio_risk)

        # Restricciones
        constraint_list = [cp.sum(w) == 1, w >= 0]  # Long only

        # Restricciones adicionales
        max_weight = constraints.get("max_weight", 1.0)
        min_weight = constraints.get("min_weight", 0.0)
        constraint_list.append(w <= max_weight)
        constraint_list.append(w >= min_weight)

        # Resolver
        problem = cp.Problem(objective, constraint_list)
        problem.solve()

        if problem.status == "optimal":
            weights = w.value
            weights = np.maximum(weights, 0)  # Asegurar no negativos
            weights = weights / weights.sum()  # Normalizar

            # Calcular métricas
            expected_return = float(np.dot(weights, expected_returns))
            volatility = float(np.sqrt(np.dot(weights, np.dot(cov_matrix, weights))))
            sharpe_ratio = expected_return / volatility if volatility > 0 else 0.0

            return {
                "weights": {f"asset_{i}": float(w) for i, w in enumerate(weights)},
                "expected_return": expected_return,
                "volatility": volatility,
                "sharpe_ratio": sharpe_ratio,
                "method": "markowitz_cvxpy",
            }
        else:
            self.logger.warning(f"Optimización cvxpy no convergió: {problem.status}")
            return self._equal_weight_fallback(n)

    def _optimize_scipy(
        self, expected_returns: np.ndarray, cov_matrix: np.ndarray, constraints: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Optimización usando scipy.optimize.minimize.

        Maximiza el Sharpe ratio usando optimización numérica.
        Funciona como fallback cuando cvxpy no está disponible.
        """
        if not SCIPY_AVAILABLE or minimize is None:
            raise ImportError("scipy is not available")

        n = len(expected_returns)

        # Obtener restricciones
        max_weight = constraints.get("max_weight", 1.0)
        min_weight = constraints.get("min_weight", 0.0)

        # Punto inicial: pesos inversos a volatilidad
        variances = np.diag(cov_matrix)
        variances = np.maximum(variances, 1e-10)
        inv_vol = 1.0 / np.sqrt(variances)
        x0 = inv_vol / inv_vol.sum()

        # Función objetivo: negativo del Sharpe ratio (para minimizar)
        def _negative_sharpe(weights: np.ndarray) -> float:
            """Calcula el negativo del Sharpe ratio."""
            portfolio_return = np.dot(weights, expected_returns)
            portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
            portfolio_volatility = np.sqrt(portfolio_variance)

            if portfolio_volatility < 1e-10:
                return -1e10  # Penalizar portfolios con muy baja volatilidad

            sharpe_ratio = portfolio_return / portfolio_volatility
            return float(-sharpe_ratio)

        # Gradiente del negativo del Sharpe ratio
        def _negative_sharpe_gradient(weights: np.ndarray) -> np.ndarray:
            """Calcula el gradiente del negativo del Sharpe ratio."""
            portfolio_return = np.dot(weights, expected_returns)
            portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
            portfolio_volatility = np.sqrt(portfolio_variance)

            if portfolio_volatility < 1e-10:
                return cast("np.ndarray", np.zeros(n))

            # Gradiente de Sharpe ratio:
            # dSR/dw = (mu * sigma_p - r_p * (1/sigma_p) * Sigma * w) / sigma_p^2
            #       = (mu * sigma_p^2 - r_p * Sigma * w) / sigma_p^3

            sigma_w = np.dot(cov_matrix, weights)
            grad_sharpe = (
                expected_returns * portfolio_volatility
                - portfolio_return * sigma_w / portfolio_volatility
            ) / (portfolio_volatility**2)

            return cast("np.ndarray", np.array(-grad_sharpe))

        # Restricciones
        bounds = [(min_weight, max_weight) for _ in range(n)]
        constraints_dict = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

        # Optimizar usando SLSQP (método robusto para problemas con restricciones)
        result = minimize(
            _negative_sharpe,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints_dict,
            jac=_negative_sharpe_gradient,
            options={
                "ftol": 1e-12,
                "maxiter": 1000,
                "disp": False,
            },
        )

        if result.success or (result.x is not None and np.all(np.isfinite(result.x))):
            weights = result.x
            weights = np.maximum(weights, 0)  # Asegurar no negativos
            weights = weights / weights.sum()  # Normalizar

            # Calcular métricas
            expected_return = float(np.dot(weights, expected_returns))
            volatility = float(np.sqrt(np.dot(weights, np.dot(cov_matrix, weights))))
            sharpe_ratio = expected_return / volatility if volatility > 0 else 0.0

            return {
                "weights": {f"asset_{i}": float(w) for i, w in enumerate(weights)},
                "expected_return": expected_return,
                "volatility": volatility,
                "sharpe_ratio": sharpe_ratio,
                "method": "markowitz_scipy",
            }
        else:
            self.logger.warning(f"Optimización scipy no convergió: {result.message}")
            return self._optimize_basic(expected_returns, cov_matrix, constraints)

    def _optimize_basic(
        self, expected_returns: np.ndarray, cov_matrix: np.ndarray, constraints: dict[str, Any]
    ) -> dict[str, Any]:
        """Optimización básica sin dependencias externas."""
        len(expected_returns)

        # Método simple: inverso de varianza (inverse volatility weighting)
        variances = np.diag(cov_matrix)
        inv_vol = 1.0 / np.sqrt(variances)
        weights = inv_vol / inv_vol.sum()

        # Aplicar restricciones
        max_weight = constraints.get("max_weight", 1.0)
        min_weight = constraints.get("min_weight", 0.0)
        weights = np.clip(weights, min_weight, max_weight)
        weights = weights / weights.sum()  # Re-normalizar

        # Calcular métricas
        expected_return = float(np.dot(weights, expected_returns))
        volatility = float(np.sqrt(np.dot(weights, np.dot(cov_matrix, weights))))
        sharpe_ratio = expected_return / volatility if volatility > 0 else 0.0

        return {
            "weights": {f"asset_{i}": float(w) for i, w in enumerate(weights)},
            "expected_return": expected_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "method": "markowitz_basic",
        }

    def _equal_weight_fallback(self, n: int) -> dict[str, Any]:
        """Fallback a pesos iguales."""
        weight = 1.0 / n
        return {
            "weights": {f"asset_{i}": weight for i in range(n)},
            "expected_return": 0.0,
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "method": "equal_weight_fallback",
        }


class RiskParityOptimizer(BaseOptimizer):
    """
    Risk Parity Optimizer.

    Asigna pesos para que cada activo contribuya igualmente al riesgo total.
    Uses Newton-Raphson iterative method for true risk parity.
    """

    def optimize(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
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
            len(cov_matrix)

            # Use iterative algorithm for true risk parity
            weights = self._optimize_risk_parity_iterative(cov_matrix, constraints)

            # Aplicar restricciones
            max_weight = constraints.get("max_weight", 1.0)
            min_weight = constraints.get("min_weight", 0.0)
            weights = np.clip(weights, min_weight, max_weight)
            weights = weights / weights.sum()

            # Calcular métricas
            expected_return = float(np.dot(weights, expected_returns))
            volatility = float(np.sqrt(np.dot(weights, np.dot(cov_matrix, weights))))
            sharpe_ratio = expected_return / volatility if volatility > 0 else 0.0

            # Calculate risk contributions for verification
            risk_contributions = self._calculate_risk_contributions(weights, cov_matrix)

            return {
                "weights": {f"asset_{i}": float(w) for i, w in enumerate(weights)},
                "expected_return": expected_return,
                "volatility": volatility,
                "sharpe_ratio": sharpe_ratio,
                "risk_contributions": {
                    f"asset_{i}": float(rc) for i, rc in enumerate(risk_contributions)
                },
                "method": "risk_parity_iterative",
            }
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error en optimización Risk Parity: {e}", exc_info=True)
            return self._equal_weight_fallback(len(cov_matrix))

    def _optimize_risk_parity_iterative(
        self, cov_matrix: np.ndarray, constraints: dict[str, Any]
    ) -> np.ndarray:
        """
        Optimización Risk Parity usando scipy.optimize.minimize.

        Minimiza: sum((RC_i - 1/n)^2)
        where RC_i = w_i * (Sigma @ w)_i / sigma_p^2

        This ensures each asset contributes equally to portfolio risk.
        Uses SLSQP optimizer with guaranteed convergence.
        """
        if not SCIPY_AVAILABLE or minimize is None:
            # Fallback to iterative method if scipy is not available
            self.logger.warning("scipy not available, using iterative risk parity method")
            weights = self._get_inverse_volatility_weights(cov_matrix)
            return self._risk_parity_fallback(
                cov_matrix, weights, 1.0 / len(cov_matrix), constraints
            )

        n = len(cov_matrix)

        # Initial guess: inverse volatility weights (good starting point)
        variances = np.diag(cov_matrix)
        variances = np.maximum(variances, 1e-10)
        inv_vol = 1.0 / np.sqrt(variances)
        x0 = inv_vol / inv_vol.sum()

        target_risk = 1.0 / n  # Target: equal risk contribution

        def _risk_parity_objective(weights: np.ndarray) -> float:
            """Objective: minimize sum of squared differences from target risk."""
            portfolio_var = weights @ cov_matrix @ weights
            if portfolio_var <= 0:
                return 1e10  # Penalty for invalid portfolio

            # Risk contributions: RC_i = w_i * (Sigma @ w)_i / sigma_p^2
            marginal_contrib = cov_matrix @ weights
            risk_contrib = weights * marginal_contrib / portfolio_var

            # Sum of squared deviations from target
            return float(np.sum((risk_contrib - target_risk) ** 2))

        def _risk_parity_gradient(weights: np.ndarray) -> np.ndarray:
            """Analytical gradient for faster convergence."""
            portfolio_var = weights @ cov_matrix @ weights
            if portfolio_var <= 0:
                return cast("np.ndarray", np.array([0.0] * n))

            sigma_w = cov_matrix @ weights
            rc = weights * sigma_w / portfolio_var
            diff = rc - target_risk

            # Gradient of RC_i w.r.t. w_j
            grad = np.zeros(n)
            for i in range(n):
                for j in range(n):
                    if i == j:
                        drc_dw = (sigma_w[i] + weights[i] * cov_matrix[i, i]) / portfolio_var
                        drc_dw -= rc[i] * 2 * sigma_w[j] / portfolio_var
                    else:
                        drc_dw = weights[i] * cov_matrix[i, j] / portfolio_var
                        drc_dw -= rc[i] * 2 * sigma_w[j] / portfolio_var
                    grad[j] += 2 * diff[i] * drc_dw

            return cast("np.ndarray", np.array(grad))

        # Use scipy.optimize.minimize with SLSQP
        try:
            result = minimize(
                _risk_parity_objective,
                x0,
                method="SLSQP",
                jac=_risk_parity_gradient,
                bounds=[(1e-10, 1.0) for _ in range(n)],
                constraints={"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
                options={
                    "ftol": 1e-12,
                    "maxiter": constraints.get("max_iterations", 500),
                    "disp": False,
                },
            )

            if result.success:
                self.logger.debug(f"Risk parity converged: {result.message}")
                return cast("np.ndarray", result.x)
            else:
                self.logger.warning(f"Scipy optimization warning: {result.message}")
                # Still use result if it's reasonable
                if result.fun < 1e-4:
                    return cast("np.ndarray", result.x)
                # Otherwise fall back to iterative method
                weights = self._get_inverse_volatility_weights(cov_matrix)
                return self._risk_parity_fallback(cov_matrix, weights, target_risk, constraints)

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            self.logger.warning(f"Scipy optimization failed: {e}, using fallback")
            # Fallback to iterative method
            weights = self._get_inverse_volatility_weights(cov_matrix)
            return self._risk_parity_fallback(cov_matrix, weights, target_risk, constraints)

    def _get_inverse_volatility_weights(self, cov_matrix: np.ndarray) -> np.ndarray:
        """Get initial weights using inverse volatility weighting."""
        variances = np.diag(cov_matrix)
        variances = np.maximum(variances, 1e-10)
        inv_vol = 1.0 / np.sqrt(variances)
        result = inv_vol / inv_vol.sum()
        return cast("np.ndarray", result)

    def _risk_parity_fallback(
        self,
        cov_matrix: np.ndarray,
        weights: np.ndarray,
        target_risk: float,
        constraints: dict[str, Any],
    ) -> np.ndarray:
        """Fallback iterative method when scipy is not available."""
        max_iter = constraints.get("max_iterations", 100)
        tolerance = constraints.get("tolerance", 1e-8)

        for iteration in range(max_iter):
            portfolio_var = weights @ cov_matrix @ weights
            if portfolio_var <= 0:
                break

            marginal_risk = cov_matrix @ weights
            risk_contributions = weights * marginal_risk / portfolio_var
            error: float = float(np.sum((risk_contributions - target_risk) ** 2))

            if error < tolerance:
                self.logger.debug(f"Risk parity fallback converged: iter={iteration + 1}")
                break

            # Multiplicative update
            adjustment = np.where(
                risk_contributions > 0, target_risk / (risk_contributions + 1e-10), 1.0
            )
            weights = weights * np.power(adjustment, 0.3)  # Damped
            weights = np.maximum(weights, 1e-10)
            weights = weights / weights.sum()

        return weights

    def _calculate_risk_contributions(
        self, weights: np.ndarray, cov_matrix: np.ndarray
    ) -> np.ndarray:
        """Calculate risk contributions for each asset."""
        portfolio_var = weights @ cov_matrix @ weights
        if portfolio_var <= 0:
            return cast("np.ndarray", np.zeros(len(weights)))

        portfolio_vol = np.sqrt(portfolio_var)
        marginal_risk = (cov_matrix @ weights) / portfolio_vol
        risk_contributions = weights * marginal_risk

        # Normalize to percentage
        total = risk_contributions.sum()
        if total > 0:
            return cast("np.ndarray", risk_contributions / total)
        return cast("np.ndarray", risk_contributions)

    def _equal_weight_fallback(self, n: int) -> dict[str, Any]:
        """Fallback a pesos iguales."""
        weight = 1.0 / n
        return {
            "weights": {f"asset_{i}": weight for i in range(n)},
            "expected_return": 0.0,
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "method": "equal_weight_fallback",
        }


class BlackLittermanOptimizer(BaseOptimizer):
    """
    Black-Litterman Optimizer.

    Combina vistas del mercado con equilibrio del mercado usando
    el modelo bayesiano de Black-Litterman.

    Views format:
    - Absolute views: {'asset_0': 0.05} means asset 0 will return 5%
    - Relative views: {'asset_0 - asset_1': 0.02} means asset 0 outperforms asset 1 by 2%
    """

    def optimize(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Optimizar usando modelo Black-Litterman.

        Args:
            expected_returns: Retornos de equilibrio del mercado (implied returns)
            cov_matrix: Matriz de covarianza
            constraints: Restricciones y vistas:
                - views: Dict mapping view description to expected return
                - view_confidences: Dict mapping view to confidence (0-1)
                - tau: Uncertainty scaling (default 0.05)
                - market_caps: Market capitalizations for equilibrium weights

        Returns:
            Dict con pesos optimizados
        """
        constraints = constraints or {}

        try:
            n = len(expected_returns)

            # Get views configuration
            views = constraints.get("views", {})
            view_confidences = constraints.get("view_confidences", {})
            tau = 0.05  # Black-Litterman tau parameter, typically 0.025 to 0.05

            # If no views, use implied equilibrium returns with Markowitz
            if not views:
                markowitz = MarkowitzOptimizer(self.config)
                result = markowitz.optimize(expected_returns, cov_matrix, constraints)
                result["method"] = "black_litterman_equilibrium"
                return result

            # Build views matrices
            P, Q, Omega = self._build_views_system(n, views, view_confidences, cov_matrix, tau)

            if P is None or len(P) == 0:
                # No valid views, use equilibrium
                markowitz = MarkowitzOptimizer(self.config)
                result = markowitz.optimize(expected_returns, cov_matrix, constraints)
                result["method"] = "black_litterman_equilibrium"
                return result

            # Prior: equilibrium returns (PI)
            PI = expected_returns

            # Posterior Black-Litterman returns
            # BL = [(tau*Sigma)^-1 + P'*Omega^-1*P]^-1 * [(tau*Sigma)^-1*PI + P'*Omega^-1*Q]
            try:
                tau_Sigma = tau * cov_matrix
                tau_Sigma_inv = np.linalg.inv(tau_Sigma)

                # Use pseudo-inverse for numerical stability
                Omega_inv = np.linalg.pinv(Omega)

                # Posterior precision and mean
                posterior_precision = tau_Sigma_inv + P.T @ Omega_inv @ P
                posterior_precision_inv = np.linalg.inv(posterior_precision)

                posterior_mean = posterior_precision_inv @ (
                    tau_Sigma_inv @ PI + P.T @ Omega_inv @ Q
                )

                bl_returns = posterior_mean

            except np.linalg.LinAlgError as e:
                self.logger.warning(f"Matrix inversion failed: {e}, using equilibrium")
                bl_returns = PI

            # Optimize with BL returns
            markowitz = MarkowitzOptimizer(self.config)
            result = markowitz.optimize(bl_returns, cov_matrix, constraints)
            result["method"] = "black_litterman"
            result["bl_returns"] = {f"asset_{i}": float(r) for i, r in enumerate(bl_returns)}
            result["equilibrium_returns"] = {f"asset_{i}": float(r) for i, r in enumerate(PI)}
            result["views_applied"] = len(views)

            return result

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error en optimización Black-Litterman: {e}", exc_info=True)
            return self._equal_weight_fallback(len(expected_returns))

    def _build_views_system(
        self,
        n: int,
        views: dict[str, Any],
        view_confidences: dict[str, float],
        cov_matrix: np.ndarray,
        tau: float,
    ) -> tuple:
        """
        Build the views system (P, Q, Omega) for Black-Litterman.

        Args:
            n: Number of assets
            views: Dict of views (asset_index or 'asset_i - asset_j' -> return)
            view_confidences: Dict of confidences (0-1)
            cov_matrix: Covariance matrix
            tau: Uncertainty parameter

        Returns:
            (P, Q, Omega) matrices
        """
        view_list = []
        P_rows = []
        Q_values = []
        confidences = []

        for view_key, expected_return in views.items():
            try:
                row = np.zeros(n)

                # Parse view key
                if " - " in str(view_key):
                    # Relative view: 'asset_i - asset_j'
                    parts = str(view_key).split(" - ")
                    idx1 = self._parse_asset_index(parts[0], n)
                    idx2 = self._parse_asset_index(parts[1], n)
                    if idx1 is not None and idx2 is not None:
                        row[idx1] = 1.0
                        row[idx2] = -1.0
                        view_list.append(view_key)
                else:
                    # Absolute view: 'asset_i' or just index
                    idx = self._parse_asset_index(view_key, n)
                    if idx is not None:
                        row[idx] = 1.0
                        view_list.append(view_key)

                if np.any(row != 0):
                    P_rows.append(row)
                    Q_values.append(float(expected_return))
                    conf = view_confidences.get(view_key, 0.5)
                    confidences.append(max(0.01, min(1.0, float(conf))))

            except (ValueError, KeyError, TypeError) as e:
                self.logger.warning(f"Invalid view {view_key}: {e}")
                continue

        if not P_rows:
            return None, None, None

        P = np.array(P_rows)
        Q = np.array(Q_values)

        # Build Omega: uncertainty matrix for views
        # Omega = diag(P * tau * Sigma * P') / confidence
        # Higher confidence = lower uncertainty
        k = len(view_list)
        Omega = np.zeros((k, k))

        for i in range(k):
            # View uncertainty proportional to view variance
            view_var = P[i] @ (tau * cov_matrix) @ P[i].T
            # Scale by inverse confidence (lower confidence = higher uncertainty)
            Omega[i, i] = view_var / confidences[i]

        return P, Q, Omega

    def _parse_asset_index(self, key: Union[str, int], n: int) -> Optional[int]:
        """Parse asset key to index."""
        try:
            if isinstance(key, int):
                return key if 0 <= key < n else None

            key_str = str(key).strip()
            if key_str.startswith("asset_"):
                idx = int(key_str.replace("asset_", ""))
                return idx if 0 <= idx < n else None

            # Try direct integer parsing
            idx = int(key_str)
            return idx if 0 <= idx < n else None

        except (ValueError, TypeError):
            return None

    def _equal_weight_fallback(self, n: int) -> dict[str, Any]:
        """Fallback a pesos iguales."""
        weight = 1.0 / n
        return {
            "weights": {f"asset_{i}": weight for i in range(n)},
            "expected_return": 0.0,
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "method": "equal_weight_fallback",
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
        constraints: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
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
            win_probabilities = constraints.get("win_probabilities", np.ones(n) * 0.5)
            win_returns = constraints.get("win_returns", expected_returns)
            loss_returns = constraints.get("loss_returns", -expected_returns * 0.5)

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
            max_weight = constraints.get("max_weight", 1.0)
            min_weight = constraints.get("min_weight", 0.0)
            weights = np.clip(weights, min_weight, max_weight)
            weights = weights / weights.sum()

            # Calcular métricas
            expected_return = float(np.dot(weights, expected_returns))
            volatility = float(np.sqrt(np.dot(weights, np.dot(cov_matrix, weights))))
            sharpe_ratio = expected_return / volatility if volatility > 0 else 0.0

            return {
                "weights": {f"asset_{i}": float(w) for i, w in enumerate(weights)},
                "expected_return": expected_return,
                "volatility": volatility,
                "sharpe_ratio": sharpe_ratio,
                "method": "kelly_criterion",
                "kelly_fractions": {
                    f"asset_{i}": float(kf) for i, kf in enumerate(kelly_fractions)
                },
            }
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error en optimización Kelly Criterion: {e}", exc_info=True)
            return self._equal_weight_fallback(len(expected_returns))

    def _equal_weight_fallback(self, n: int) -> dict[str, Any]:
        """Fallback a pesos iguales."""
        weight = 1.0 / n
        return {
            "weights": {f"asset_{i}": weight for i in range(n)},
            "expected_return": 0.0,
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "method": "equal_weight_fallback",
        }


def get_optimization_capabilities() -> dict[str, bool]:
    """
    Get available optimization capabilities.

    Returns a dictionary indicating which optimization libraries are available.

    Returns:
        Dict with keys:
        - cvxpy: True if cvxpy is available for convex optimization
        - pypfopt: True if PyPortfolioOpt is available for efficient frontier
        - scipy: True if scipy.optimize is available for numerical optimization
        - handcrafted: True if handcrafted optimizer is available
        - hrp: True if HRP optimizer is available
    """
    return {
        "cvxpy": CVXPY_AVAILABLE,
        "pypfopt": PYPFOPT_AVAILABLE,
        "scipy": SCIPY_AVAILABLE,
        "handcrafted": HANDCRAFTED_AVAILABLE,
        "hrp": HRP_AVAILABLE,
    }


def get_optimization_method() -> str:
    """
    Get the recommended optimization method based on available libraries.

    Returns:
        str: The recommended optimization method
    """
    if PYPFOPT_AVAILABLE:
        return "pypfopt"
    elif CVXPY_AVAILABLE:
        return "cvxpy"
    elif SCIPY_AVAILABLE:
        return "scipy"
    else:
        return "basic"


__all__ = [
    "CVXPY_AVAILABLE",
    "HANDCRAFTED_AVAILABLE",
    "HRP_AVAILABLE",
    "PYPFOPT_AVAILABLE",
    "SCIPY_AVAILABLE",
    "BaseOptimizer",
    "BlackLittermanOptimizer",
    "HRPOptimizer",
    "HandcraftedWeightsOptimizer",
    "HierarchicalRiskParity",
    "KellyCriterionOptimizer",
    "MarkowitzOptimizer",
    "RiskParityOptimizer",
    "compute_hrp_weights",
    "create_handcrafted_weights",
    "get_optimization_capabilities",
    "get_optimization_method",
    "plot_hrp_dendrogram",
]
