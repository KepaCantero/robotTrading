"""
Volatility Calculator - Cálculo de Métricas de Volatilidad

Implementa cálculo de:
- Volatilidad histórica (20, 60, 252 días)
- Beta (respecto al mercado)
- Downside risk (semi-deviation)
- Maximum drawdown
- Sortino ratio
- Sharpe ratio
- Correlación con el mercado
- Volatilidad idiosincrática

SOLID Principles:
- Single Responsibility: Solo cálculo de métricas
- Open/Closed: Extensible con nuevas métricas
- Dependency Inversion: Depende de abstracciones (models)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np
from scipy import stats

from .models import VolatilityMetrics, VolatilityRegime

if TYPE_CHECKING:
    from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class ReturnSeries:
    """
    Serie de retornos para análisis.

    Attributes:
        symbol: Símbolo de la acción
        dates: Fechas de los retornos
        returns: Retornos diarios (como decimales)
        prices: Precios correspondientes
    """

    symbol: str
    dates: list[date]
    returns: np.ndarray
    prices: np.ndarray


class VolatilityCalculator:
    """
    Calculador de métricas de volatilidad.

    Calcula métricas de riesgo y volatilidad para acciones
    utilizando datos históricos de precios.

    Attributes:
        risk_free_rate: Tasa libre de riesgo anual (para Sharpe/Sortino)
        trading_days_per_year: Días de trading por año (default: 252)
    """

    def __init__(
        self,
        risk_free_rate: Decimal | None = None,
        trading_days_per_year: int = 252,
    ):
        """
        Inicializar calculador.

        Args:
            risk_free_rate: Tasa libre de riesgo anual (2% por defecto)
            trading_days_per_year: Días de trading por año
        """
        if risk_free_rate is None:
            risk_free_rate = Decimal("0.02")
        self.risk_free_rate = risk_free_rate
        self.trading_days_per_year = trading_days_per_year

    def calculate_all_metrics(
        self,
        price_series: list[tuple[date, Decimal]],
        market_series: list[tuple[date, Decimal]],
        symbol: str,
    ) -> VolatilityMetrics:
        """
        Calcular todas las métricas de volatilidad.

        Args:
            price_series: Serie de precios históricos (fecha, precio)
            market_series: Serie de precios del mercado (fecha, precio)
            symbol: Símbolo de la acción

        Returns:
            Métricas de volatilidad completas
        """
        if len(price_series) < 20:
            raise ValueError(f"Se necesitan al menos 20 datos de precio, got {len(price_series)}")

        # Preparar datos
        stock_returns = self._calculate_returns(price_series)
        market_returns = self._calculate_returns(market_series)

        # Alinear retornos
        aligned_returns = self._align_returns(stock_returns, market_returns)

        # Calcular métricas
        vol_20d = self.calculate_historical_volatility(price_series, window=20)
        vol_60d = self.calculate_historical_volatility(price_series, window=60)
        vol_252d = self.calculate_historical_volatility(price_series, window=252)

        beta = self.calculate_beta(aligned_returns[0], aligned_returns[1])
        downside_risk = self.calculate_downside_risk(stock_returns)
        max_drawdown = self.calculate_max_drawdown(price_series)

        sortino = self.calculate_sortino_ratio(stock_returns)
        sharpe = self.calculate_sharpe_ratio(stock_returns)
        correlation = self.calculate_correlation(aligned_returns[0], aligned_returns[1])

        idiosyncratic_vol = self.calculate_idiosyncratic_volatility(
            aligned_returns[0], aligned_returns[1], beta
        )

        skewness, kurtosis = self.calculate_moments(stock_returns)

        regime = self._determine_volatility_regime(
            vol_60d if vol_60d is not None else (vol_20d if vol_20d is not None else Decimal("0"))
        )

        return VolatilityMetrics(
            symbol=symbol,
            historical_volatility_20d=vol_20d,
            historical_volatility_60d=vol_60d,
            historical_volatility_252d=vol_252d,
            beta=beta,
            downside_risk=downside_risk,
            max_drawdown=max_drawdown,
            sortino_ratio=sortino,
            sharpe_ratio=sharpe,
            correlation_to_market=correlation,
            idiosyncratic_volatility=idiosyncratic_vol,
            skewness=skewness,
            kurtosis=kurtosis,
            volatility_regime=regime,
        )

    def calculate_historical_volatility(
        self,
        price_series: list[tuple[date, Decimal]],
        window: int = 20,
    ) -> Decimal | None:
        """
        Calcular volatilidad histórica.

        Usa desviación estándar de retornos logarítmicos
        anualizada por sqrt(252).

        Args:
            price_series: Serie de precios históricos (fecha, precio)
            window: Ventana en días (default: 20)

        Returns:
            Volatilidad anualizada (%) o None si no hay suficientes datos
        """
        if len(price_series) < window + 1:
            logger.warning(f"Insufficient data for {window}-day volatility")
            return None

        # Extraer precios
        prices = np.array([float(p[1]) for p in price_series[-window:]])

        # Calcular retornos logarítmicos
        log_returns = np.diff(np.log(prices))

        # Desviación estándar
        std_dev = np.std(log_returns, ddof=1)

        # Anualizar
        annualized_vol = std_dev * np.sqrt(self.trading_days_per_year)

        # Convertir a porcentaje
        return Decimal(str(annualized_vol * 100)).quantize(Decimal("0.01"))

    def calculate_beta(
        self,
        stock_returns: np.ndarray,
        market_returns: np.ndarray,
    ) -> Decimal | None:
        """
        Calcular beta respecto al mercado.

        Beta = Cov(stock, market) / Var(market)

        Args:
            stock_returns: Retornos de la acción
            market_returns: Retornos del mercado

        Returns:
            Beta o None si no se puede calcular
        """
        if len(stock_returns) != len(market_returns) or len(stock_returns) < 2:
            return None

        # Calcular covarianza y varianza
        covariance = np.cov(stock_returns, market_returns)[0, 1]
        market_variance = np.var(market_returns, ddof=1)

        if market_variance == 0:
            return None

        beta = covariance / market_variance

        return Decimal(str(beta)).quantize(Decimal("0.01"))

    def calculate_downside_risk(
        self,
        returns: np.ndarray,
        min_return: float = 0.0,
    ) -> Decimal | None:
        """
        Calcular riesgo downside (semi-deviation).

        Solo considera retornos por debajo del mínimo.

        Args:
            returns: Retornos diarios
            min_return: Retorno mínimo (default: 0)

        Returns:
            Downside risk anualizado (%) o None
        """
        if len(returns) < 2:
            return None

        # Filtrar retornos por debajo del mínimo
        downside_returns = returns[returns < min_return]

        if len(downside_returns) == 0:
            return Decimal("0")

        # Calcular semi-desviación
        downside_deviation = np.std(downside_returns, ddof=1)

        # Anualizar
        annualized = downside_deviation * np.sqrt(self.trading_days_per_year)

        return Decimal(str(annualized * 100)).quantize(Decimal("0.01"))

    def calculate_max_drawdown(
        self,
        price_series: list[tuple[date, Decimal]],
    ) -> Decimal | None:
        """
        Calcular máximo drawdown.

        Drawdown máximo desde el pico más alto.

        Args:
            price_series: Serie de precios históricos

        Returns:
            Máximo drawdown (%) o None
        """
        if len(price_series) < 2:
            return None

        prices = np.array([float(p[1]) for p in price_series])

        # Calcular peaks y drawdowns
        cummax = np.maximum.accumulate(prices)
        drawdowns = (prices - cummax) / cummax * 100

        max_dd: float = np.min(drawdowns)

        return Decimal(str(max_dd)).quantize(Decimal("0.01"))

    def calculate_sortino_ratio(
        self,
        returns: np.ndarray,
        target_return: float = 0.0,
    ) -> Decimal | None:
        """
        Calcular Sortino ratio.

        Sortino = (mean_return - target) / downside_deviation

        Args:
            returns: Retornos diarios
            target_return: Retorno objetivo (default: 0)

        Returns:
            Sortino ratio anualizado o None
        """
        if len(returns) < 2:
            return None

        # Retorno promedio anualizado
        mean_return = np.mean(returns) * self.trading_days_per_year

        # Downside deviation
        downside_dev = self.calculate_downside_risk(returns, target_return)
        if downside_dev is None or downside_dev == 0:
            return None

        sortino = (mean_return - target_return) / (float(downside_dev) / 100)

        return Decimal(str(sortino)).quantize(Decimal("0.01"))

    def calculate_sharpe_ratio(
        self,
        returns: np.ndarray,
    ) -> Decimal | None:
        """
        Calcular Sharpe ratio.

        Sharpe = (mean_return - rf) / std_dev

        Args:
            returns: Retornos diarios

        Returns:
            Sharpe ratio anualizado o None
        """
        if len(returns) < 2:
            return None

        # Retorno promedio anualizado
        mean_return = np.mean(returns) * self.trading_days_per_year

        # Desviación estándar anualizada
        std_dev = np.std(returns, ddof=1) * np.sqrt(self.trading_days_per_year)

        if std_dev == 0:
            return None

        # Sharpe ratio
        rf = float(self.risk_free_rate)
        sharpe = (mean_return - rf) / std_dev

        return Decimal(str(sharpe)).quantize(Decimal("0.01"))

    def calculate_correlation(
        self,
        stock_returns: np.ndarray,
        market_returns: np.ndarray,
    ) -> Decimal | None:
        """
        Calcular correlación con el mercado.

        Args:
            stock_returns: Retornos de la acción
            market_returns: Retornos del mercado

        Returns:
            Correlación (-1 a 1) o None
        """
        if len(stock_returns) != len(market_returns) or len(stock_returns) < 2:
            return None

        correlation = np.corrcoef(stock_returns, market_returns)[0, 1]

        if np.isnan(correlation):
            return None

        return Decimal(str(correlation)).quantize(Decimal("0.01"))

    def calculate_idiosyncratic_volatility(
        self,
        stock_returns: np.ndarray,
        market_returns: np.ndarray,
        beta: Decimal | None,
    ) -> Decimal | None:
        """
        Calcular volatilidad idiosincrática.

        Volatilidad no explicada por el mercado.
        IdioVol = sqrt(TotalVol² - (Beta * MarketVol)²)

        Args:
            stock_returns: Retornos de la acción
            market_returns: Retornos del mercado
            beta: Beta calculado

        Returns:
            Volatilidad idiosincrática anualizada (%) o None
        """
        if beta is None or len(stock_returns) < 2:
            return None

        # Volatilidad total
        total_vol = np.std(stock_returns, ddof=1)

        # Volatilidad del mercado
        market_vol = np.std(market_returns, ddof=1)

        # Volatilidad sistemática
        systematic_vol = float(beta) * market_vol

        # Volatilidad idiosincrática
        idio_vol_sq = total_vol**2 - systematic_vol**2

        if idio_vol_sq < 0:
            return Decimal("0")

        idio_vol = np.sqrt(max(0, idio_vol_sq))

        # Anualizar y convertir a porcentaje
        annualized = idio_vol * np.sqrt(self.trading_days_per_year) * 100

        return Decimal(str(annualized)).quantize(Decimal("0.01"))

    def calculate_moments(
        self,
        returns: np.ndarray,
    ) -> tuple[Decimal | None, Decimal | None]:
        """
        Calcular skewness y kurtosis de retornos.

        Args:
            returns: Retornos diarios

        Returns:
            (skewness, kurtosis) o (None, None)
        """
        if len(returns) < 3:
            return (None, None)

        try:
            skewness = stats.skew(returns)
            kurtosis = stats.kurtosis(returns)  # Excess kurtosis

            return (
                Decimal(str(skewness)).quantize(Decimal("0.01")),
                Decimal(str(kurtosis)).quantize(Decimal("0.01")),
            )
        except Exception as e:
            logger.warning(f"Error calculating moments: {e}")
            return (None, None)

    def _calculate_returns(
        self,
        price_series: list[tuple[date, Decimal]],
    ) -> np.ndarray:
        """
        Calcular retornos logarítmicos desde serie de precios.

        Args:
            price_series: Serie de precios (fecha, precio)

        Returns:
            Array de retornos
        """
        if len(price_series) < 2:
            return np.array([], dtype=np.float64)

        prices = np.array([float(p[1]) for p in price_series])

        # Retornos logaritmicos
        log_returns: np.ndarray = np.diff(np.log(prices))

        return log_returns

    def _align_returns(
        self,
        stock_returns: np.ndarray,
        market_returns: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Alinear retornos de acción y mercado por fecha.

        Args:
            stock_returns: Retornos de la acción
            market_returns: Retornos del mercado

        Returns:
            (stock_aligned, market_aligned)
        """
        min_len = min(len(stock_returns), len(market_returns))

        return (
            stock_returns[-min_len:],
            market_returns[-min_len:],
        )

    def _determine_volatility_regime(
        self,
        volatility: Decimal,
    ) -> VolatilityRegime:
        """
        Determinar régimen de volatilidad basado en VIX implícito.

        Args:
            volatility: Volatilidad actual

        Returns:
            Régimen de volatilidad
        """
        vol_float = float(volatility)

        if vol_float < 15:
            return VolatilityRegime.LOW
        elif vol_float < 25:
            return VolatilityRegime.NORMAL
        elif vol_float < 35:
            return VolatilityRegime.ELEVATED
        else:
            return VolatilityRegime.HIGH

    def calculate_portfolio_volatility(
        self,
        weights: list[float],
        returns_matrix: np.ndarray,
    ) -> Decimal:
        """
        Calcular volatilidad de portafolio.

        Args:
            weights: Pesos del portafolio
            returns_matrix: Matriz de retornos (filas=activos, columnas=días)

        Returns:
            Volatilidad del portafolio anualizada (%)
        """
        # Matriz de covarianza
        cov_matrix = np.cov(returns_matrix)

        # Volatilidad del portafolio
        weights_array = np.array(weights)
        portfolio_variance = np.dot(weights_array.T, np.dot(cov_matrix, weights_array))
        portfolio_vol = np.sqrt(portfolio_variance)

        # Anualizar
        annualized_vol = portfolio_vol * np.sqrt(self.trading_days_per_year)

        return Decimal(str(annualized_vol * 100)).quantize(Decimal("0.01"))

    def calculate_minimum_variance_weights(
        self,
        returns_matrix: np.ndarray,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
    ) -> list[float]:
        """
        Calcular pesos de varianza mínima.

        Resuelve: min w'Σw sujeto a sum(w)=1

        Args:
            returns_matrix: Matriz de retornos
            min_weight: Peso mínimo por activo
            max_weight: Peso máximo por activo

        Returns:
            Pesos óptimos
        """
        from scipy.optimize import minimize

        n_assets = returns_matrix.shape[0]

        # Matriz de covarianza
        cov_matrix = np.cov(returns_matrix)

        # Función objetivo: varianza del portafolio
        def portfolio_variance(weights):
            return np.dot(weights.T, np.dot(cov_matrix, weights))

        # Restricciones
        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1}  # Pesos suman 1

        # Límites
        bounds = [(min_weight, max_weight) for _ in range(n_assets)]

        # Peso inicial (equal weight)
        x0 = np.array([1.0 / n_assets] * n_assets)

        # Optimizar
        result = minimize(
            portfolio_variance,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if result.success:
            return list(result.x.tolist())
        else:
            logger.warning(f"Optimization failed: {result.message}")
            return [1.0 / n_assets] * n_assets
