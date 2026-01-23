"""
Value at Risk (VaR) Calculators

Implementa diferentes métodos para calcular VaR:
- Historical VaR
- Parametric VaR (Variance-Covariance)
- Monte Carlo VaR
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    pass

    ARCH_AVAILABLE = True
except ImportError:
    ARCH_AVAILABLE = False
    logger.warning("arch no disponible. Modelos GARCH limitados.")


class BaseVaRCalculator(ABC):
    """Clase base para calculadores de VaR."""

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar VaR calculator.

        Args:
            config: Configuración del calculator
        """
        self.config = config
        self.confidence_level = config.get('confidence_level', 0.95)  # 95% por defecto
        self.time_horizon = config.get('time_horizon', 1)  # días
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def calculate_var(
        self, returns: np.ndarray, portfolio_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calcular VaR.

        Args:
            returns: Serie de retornos históricos
            portfolio_value: Valor del portfolio (opcional)

        Returns:
            Dict con VaR y métricas relacionadas
        """


class HistoricalVaRCalculator(BaseVaRCalculator):
    """
    Historical VaR Calculator.

    Calcula VaR usando distribución empírica de retornos históricos.
    """

    def calculate_var(
        self, returns: np.ndarray, portfolio_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calcular VaR histórico.

        Args:
            returns: Serie de retornos históricos
            portfolio_value: Valor del portfolio

        Returns:
            Dict con VaR histórico
        """
        try:
            if len(returns) == 0:
                return {'error': 'No returns data provided'}

            # Convertir a numpy array si es necesario
            if isinstance(returns, (pd.Series, list)):
                returns = np.array(returns)

            # Calcular percentil correspondiente al confidence level
            percentile = (1 - self.confidence_level) * 100

            # VaR histórico (percentil de distribución empírica)
            var_historical = np.percentile(returns, percentile)

            # CVaR (Expected Shortfall) - promedio de pérdidas más allá del VaR
            losses_beyond_var = returns[returns <= var_historical]
            cvar = np.mean(losses_beyond_var) if len(losses_beyond_var) > 0 else var_historical

            # Convertir a valor absoluto si portfolio_value está disponible
            var_amount = None
            cvar_amount = None
            if portfolio_value is not None:
                var_amount = abs(var_historical * portfolio_value)
                cvar_amount = abs(cvar * portfolio_value)

            return {
                'var': float(var_historical),
                'var_amount': float(var_amount) if var_amount is not None else None,
                'cvar': float(cvar),
                'cvar_amount': float(cvar_amount) if cvar_amount is not None else None,
                'confidence_level': self.confidence_level,
                'time_horizon': self.time_horizon,
                'method': 'historical',
                'observations': len(returns),
            }
        except Exception as e:
            self.logger.error(f"Error calculando VaR histórico: {e}", exc_info=True)
            return {'error': str(e)}


class ParametricVaRCalculator(BaseVaRCalculator):
    """
    Parametric VaR Calculator (Variance-Covariance).

    Asume distribución normal de retornos.
    """

    def calculate_var(
        self, returns: np.ndarray, portfolio_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calcular VaR paramétrico.

        Args:
            returns: Serie de retornos históricos
            portfolio_value: Valor del portfolio

        Returns:
            Dict con VaR paramétrico
        """
        try:
            if len(returns) == 0:
                return {'error': 'No returns data provided'}

            # Convertir a numpy array
            if isinstance(returns, (pd.Series, list)):
                returns = np.array(returns)

            # Z-score para confidence level
            from scipy import stats

            # CRITICAL: Test for normality before using parametric VaR
            # Parametric VaR assumes normal distribution which often doesn't hold
            is_normal = True
            normality_warning = None

            if len(returns) >= 20:  # Need sufficient samples for test
                try:
                    # Jarque-Bera test for normality
                    jb_stat, jb_pvalue = stats.jarque_bera(returns)
                    if jb_pvalue < 0.05:  # Reject normality at 5% significance
                        is_normal = False
                        # Calculate excess kurtosis and skewness
                        kurt = stats.kurtosis(returns)
                        skew = stats.skew(returns)
                        normality_warning = (
                            f"Returns are NOT normally distributed (JB p-value={jb_pvalue:.4f}, "
                            f"skew={skew:.2f}, kurtosis={kurt:.2f}). "
                            f"Parametric VaR may UNDERESTIMATE risk by 15-30%."
                        )
                        logger.warning(f"VaR WARNING: {normality_warning}")
                except Exception as e:
                    logger.debug(f"Normality test failed: {e}")

            # Calcular media y desviación estándar
            mean_return = np.mean(returns)
            std_return = np.std(returns)

            z_score = stats.norm.ppf(1 - self.confidence_level)

            # VaR paramétrico: mean - z * std
            var_parametric = mean_return - z_score * std_return

            # CVaR bajo normalidad: mean - std * phi(z) / (1 - confidence_level)
            # donde phi es la densidad normal estándar
            phi_z = stats.norm.pdf(z_score)
            cvar_parametric = mean_return - std_return * phi_z / (1 - self.confidence_level)

            # Convertir a valor absoluto si portfolio_value está disponible
            var_amount = None
            cvar_amount = None
            if portfolio_value is not None:
                var_amount = abs(var_parametric * portfolio_value)
                cvar_amount = abs(cvar_parametric * portfolio_value)

            return {
                'var': float(var_parametric),
                'var_amount': float(var_amount) if var_amount is not None else None,
                'cvar': float(cvar_parametric),
                'cvar_amount': float(cvar_amount) if cvar_amount is not None else None,
                'confidence_level': self.confidence_level,
                'time_horizon': self.time_horizon,
                'method': 'parametric',
                'mean_return': float(mean_return),
                'std_return': float(std_return),
                'z_score': float(z_score),
                'is_normal_distribution': is_normal,
                'normality_warning': normality_warning,
            }
        except ImportError:
            self.logger.warning("scipy no disponible. Usando aproximación básica.")
            # Aproximación básica sin scipy
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            # Aproximación z-score para 95% = 1.645, 99% = 2.326
            z_scores = {0.95: 1.645, 0.99: 2.326, 0.90: 1.282}
            z_score = z_scores.get(self.confidence_level, 1.645)
            var_parametric = mean_return - z_score * std_return

            var_amount = None
            if portfolio_value is not None:
                var_amount = abs(var_parametric * portfolio_value)

            return {
                'var': float(var_parametric),
                'var_amount': float(var_amount) if var_amount is not None else None,
                'confidence_level': self.confidence_level,
                'time_horizon': self.time_horizon,
                'method': 'parametric_basic',
                'mean_return': float(mean_return),
                'std_return': float(std_return),
            }
        except Exception as e:
            self.logger.error(f"Error calculando VaR paramétrico: {e}", exc_info=True)
            return {'error': str(e)}


class MonteCarloVaRCalculator(BaseVaRCalculator):
    """
    Monte Carlo VaR Calculator.

    Simula retornos futuros usando Monte Carlo.
    """

    def __init__(self, config: Dict[str, Any]):
        """Inicializar Monte Carlo VaR calculator."""
        super().__init__(config)
        self.n_simulations = config.get('n_simulations', 10000)

    def calculate_var(
        self, returns: np.ndarray, portfolio_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calcular VaR usando Monte Carlo.

        Args:
            returns: Serie de retornos históricos
            portfolio_value: Valor del portfolio

        Returns:
            Dict con VaR Monte Carlo
        """
        try:
            if len(returns) == 0:
                return {'error': 'No returns data provided'}

            # Convertir a numpy array
            if isinstance(returns, (pd.Series, list)):
                returns = np.array(returns)

            # Calcular parámetros de distribución
            mean_return = np.mean(returns)
            std_return = np.std(returns)

            # Simular retornos futuros
            np.random.seed(42)  # Para reproducibilidad
            simulated_returns = np.random.normal(mean_return, std_return, self.n_simulations)

            # Calcular percentil de simulaciones
            percentile = (1 - self.confidence_level) * 100
            var_mc = np.percentile(simulated_returns, percentile)

            # CVaR de simulaciones
            losses_beyond_var = simulated_returns[simulated_returns <= var_mc]
            cvar_mc = np.mean(losses_beyond_var) if len(losses_beyond_var) > 0 else var_mc

            # Convertir a valor absoluto si portfolio_value está disponible
            var_amount = None
            cvar_amount = None
            if portfolio_value is not None:
                var_amount = abs(var_mc * portfolio_value)
                cvar_amount = abs(cvar_mc * portfolio_value)

            return {
                'var': float(var_mc),
                'var_amount': float(var_amount) if var_amount is not None else None,
                'cvar': float(cvar_mc),
                'cvar_amount': float(cvar_amount) if cvar_amount is not None else None,
                'confidence_level': self.confidence_level,
                'time_horizon': self.time_horizon,
                'method': 'monte_carlo',
                'n_simulations': self.n_simulations,
                'mean_return': float(mean_return),
                'std_return': float(std_return),
            }
        except Exception as e:
            self.logger.error(f"Error calculando VaR Monte Carlo: {e}", exc_info=True)
            return {'error': str(e)}


class GARCHVaRCalculator(BaseVaRCalculator):
    """
    GARCH VaR Calculator.

    Usa modelos GARCH para modelar volatilidad dinámica.
    """

    def calculate_var(
        self, returns: np.ndarray, portfolio_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calcular VaR usando modelo GARCH.

        Args:
            returns: Serie de retornos históricos
            portfolio_value: Valor del portfolio

        Returns:
            Dict con VaR GARCH
        """
        if not ARCH_AVAILABLE:
            self.logger.warning("arch no disponible. Usando método paramétrico como fallback.")
            calculator = ParametricVaRCalculator(self.config)
            return calculator.calculate_var(returns, portfolio_value)

        try:
            if len(returns) < 100:
                self.logger.warning("Pocos datos para GARCH. Usando método paramétrico.")
                calculator = ParametricVaRCalculator(self.config)
                return calculator.calculate_var(returns, portfolio_value)

            # Convertir a numpy array
            if isinstance(returns, (pd.Series, list)):
                returns = np.array(returns)

            # Ajustar modelo GARCH(1,1)
            from arch import arch_model

            model = arch_model(returns * 100, vol='Garch', p=1, q=1)
            fitted_model = model.fit(disp='of')

            # Obtener volatilidad condicional
            forecast = fitted_model.forecast(horizon=1)
            conditional_volatility = np.sqrt(forecast.variance.values[-1, 0]) / 100

            # Calcular VaR usando volatilidad condicional
            from scipy import stats

            z_score = stats.norm.ppf(1 - self.confidence_level)

            mean_return = np.mean(returns)
            var_garch = mean_return - z_score * conditional_volatility

            # CVaR
            phi_z = stats.norm.pdf(z_score)
            cvar_garch = mean_return - conditional_volatility * phi_z / (1 - self.confidence_level)

            # Convertir a valor absoluto
            var_amount = None
            cvar_amount = None
            if portfolio_value is not None:
                var_amount = abs(var_garch * portfolio_value)
                cvar_amount = abs(cvar_garch * portfolio_value)

            return {
                'var': float(var_garch),
                'var_amount': float(var_amount) if var_amount is not None else None,
                'cvar': float(cvar_garch),
                'cvar_amount': float(cvar_amount) if cvar_amount is not None else None,
                'confidence_level': self.confidence_level,
                'time_horizon': self.time_horizon,
                'method': 'garch',
                'conditional_volatility': float(conditional_volatility),
            }
        except ImportError:
            calculator = ParametricVaRCalculator(self.config)
            return calculator.calculate_var(returns, portfolio_value)
        except Exception as e:
            self.logger.error(f"Error calculando VaR GARCH: {e}", exc_info=True)
            calculator = ParametricVaRCalculator(self.config)
            return calculator.calculate_var(returns, portfolio_value)
