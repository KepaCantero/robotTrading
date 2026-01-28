"""
Greeks Calculator - Black-Scholes Option Pricing and Greeks

Implementa cálculo de Greeks usando el modelo Black-Scholes-Merton:
- Delta: Sensibilidad del precio de la opción al precio del subyacente
- Gamma: Sensibilidad de delta al precio del subyacente (convexidad)
- Theta: Sensibilidad del precio de la opción al paso del tiempo
- Vega: Sensibilidad del precio de la opción a la volatilidad
- Rho: Sensibilidad del precio de la opción a la tasa de interés

SOLID Principles:
- Single Responsibility: Solo cálculo de Greeks, no gestión de posiciones
- Open/Closed: Extensible con nuevos modelos de pricing
"""

import logging
import math
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from .models import CallOption, OptionGreeks

logger = logging.getLogger(__name__)


class BlackScholesGreeks:
    """
    Calculador de Greeks usando el modelo Black-Scholes-Merton.

    El modelo Black-Scholes asume:
    - No hay arbitraje
    - Posibilidad de comprar y vender cualquier cantidad del activo
    - No hay costos de transacción ni impuestos
    - Trading continuo
    - Activos fraccionarios
    - Tasa de interés constante y sin riesgo
    - Volatilidad constante
    - No hay dividendos (o se pueden modelar)

    Referencia:
    Black, F., & Scholes, M. (1973). The pricing of options and corporate liabilities.
    Journal of Political Economy, 81(3), 637-654.
    """

    # Constantes matemáticas
    SQRT_2_PI = math.sqrt(2 * math.pi)
    SQRT_2 = math.sqrt(2)

    def __init__(
        self,
        risk_free_rate: float = 0.05,  # 5% anual
        dividend_yield: float = 0.0,
    ):
        """
        Inicializar calculador de Greeks.

        Args:
            risk_free_rate: Tasa de interés libre de riesgo (anual)
            dividend_yield: Yield de dividendos del activo (anual)
        """
        self.risk_free_rate = risk_free_rate
        self.dividend_yield = dividend_yield

    def calculate_greeks(
        self,
        option: CallOption,
        underlying_price: Optional[Decimal] = None,
        volatility: Optional[float] = None,
    ) -> OptionGreeks:
        """
        Calcular Greeks para una opción call.

        Args:
            option: Opción a calcular
            underlying_price: Precio del subyacente (usa option.underlying_price si es None)
            volatility: Volatilidad (usa option.implied_volatility si es None)

        Returns:
            Greeks de la opción

        Raises:
            ValueError: Si faltan parámetros requeridos
        """
        # Obtener parámetros
        S = float(underlying_price or option.underlying_price)
        K = float(option.strike)
        T = option.days_to_expiry / 365.0  # Convertir a años

        if S is None or S <= 0:
            raise ValueError(f"Precio del subyacente inválido: {S}")

        if K <= 0:
            raise ValueError(f"Strike inválido: {K}")

        if T <= 0:
            # Opción vencida o venciendo hoy
            if S > K:
                return OptionGreeks(
                    delta=Decimal("1.0"),
                    gamma=Decimal("0.0"),
                    theta=Decimal("0.0"),
                    vega=Decimal("0.0"),
                    rho=Decimal("0.0"),
                )
            else:
                return OptionGreeks(
                    delta=Decimal("0.0"),
                    gamma=Decimal("0.0"),
                    theta=Decimal("0.0"),
                    vega=Decimal("0.0"),
                    rho=Decimal("0.0"),
                )

        # Obtener volatilidad
        if volatility is None:
            if option.implied_volatility is None:
                raise ValueError("Se requiere volatilidad implícita")
            sigma = float(option.implied_volatility) / 100.0  # Convertir % a decimal
        else:
            sigma = volatility

        if sigma <= 0:
            raise ValueError(f"Volatilidad inválida: {sigma}")

        # Calcular Greeks usando Black-Scholes
        greeks = self._calculate_black_scholes_greeks(S, K, T, sigma)

        logger.debug(
            f"Greeks calculados para {option.symbol} {K} strike: "
            f"Delta={greeks.delta}, Gamma={greeks.gamma}, "
            f"Theta={greeks.theta}, Vega={greeks.vega}"
        )

        return greeks

    def _calculate_black_scholes_greeks(
        self, S: float, K: float, T: float, sigma: float
    ) -> OptionGreeks:
        """
        Calcular Greeks usando fórmulas Black-Scholes.

        Para una opción call europea:
        - d1 = (ln(S/K) + (r + σ²/2)T) / (σ√T)
        - d2 = d1 - σ√T

        - Delta = N(d1)
        - Gamma = N'(d1) / (Sσ√T)
        - Theta = -(SN'(d1)σ) / (2√T) - rKe^(-rT)N(d2)
        - Vega = SN'(d1)√T
        - Rho = KTe^(-rT)N(d2)

        Donde:
        - N(x) = Función de distribución normal acumulativa
        - N'(x) = Función de densidad normal (PDF)

        Args:
            S: Precio del subyacente
            K: Strike
            T: Tiempo al vencimiento (años)
            sigma: Volatilidad

        Returns:
            Greeks calculados
        """
        r = self.risk_free_rate
        q = self.dividend_yield

        # Calcular d1 y d2
        d1 = self._calculate_d1(S, K, T, r, q, sigma)
        d2 = d1 - sigma * math.sqrt(T)

        # Calcular N(d1), N(d2), N'(d1)
        N_d1 = self._cumulative_normal(d1)
        N_d2 = self._cumulative_normal(d2)
        N_prime_d1 = self._normal_pdf(d1)

        # Calcular Greeks
        delta = math.exp(-q * T) * N_d1

        if T > 0 and sigma > 0 and S > 0:
            gamma = (math.exp(-q * T) * N_prime_d1) / (S * sigma * math.sqrt(T))
            vega = (
                S * math.exp(-q * T) * N_prime_d1 * math.sqrt(T)
            ) / 100.0  # Por 1% cambio en vol

            # Theta (por día)
            theta_numerator = -(S * math.exp(-q * T) * N_prime_d1 * sigma) / (2 * math.sqrt(T))
            theta_second_term = -r * K * math.exp(-r * T) * N_d2
            theta = (theta_numerator + theta_second_term) / 365.0  # Por día

            # Rho (por 1% cambio en tasa)
            rho = (K * T * math.exp(-r * T) * N_d2) / 100.0
        else:
            gamma = 0.0
            vega = 0.0
            theta = 0.0
            rho = 0.0

        return OptionGreeks(
            delta=Decimal(str(round(delta, 6))),
            gamma=Decimal(str(round(gamma, 6))),
            theta=Decimal(str(round(theta, 6))),
            vega=Decimal(str(round(vega, 6))),
            rho=Decimal(str(round(rho, 6))),
        )

    def _calculate_d1(
        self, S: float, K: float, T: float, r: float, q: float, sigma: float
    ) -> float:
        """
        Calcular d1 del modelo Black-Scholes.

        d1 = [ln(S/K) + (r - q + σ²/2)T] / (σ√T)
        """
        if T == 0 or sigma == 0:
            return 0.0

        numerator = math.log(S / K) + (r - q + (sigma**2) / 2) * T
        denominator = sigma * math.sqrt(T)

        return numerator / denominator

    def _cumulative_normal(self, x: float) -> float:
        """
        Función de distribución normal acumulativa N(x).

        Usa la aproximación de Abramowitz y Stegun (1964).

        Para x >= 0: N(x) = 1 - φ(x) * (a1*t + a2*t² + a3*t³ + a4*t⁴ + a5*t⁵)
        Para x < 0: N(x) = 1 - N(-x)  (por simetría)

        donde:
        - φ(x) = PDF de la normal
        - t = 1 / (1 + p*x)
        - p, a1, a2, ... son constantes

        Args:
            x: Valor

        Returns:
            N(x) = P(Z <= x) para Z ~ N(0,1)
        """
        if x == 0:
            return 0.5

        # Constantes de la aproximación
        a1 = 0.254829592
        a2 = -0.284496736
        a3 = 1.421413741
        a4 = -1.453152027
        a5 = 1.061405429
        p = 0.3275911

        # Para valores negativos, usar simetría: N(-x) = 1 - N(x)
        if x < 0:
            return 1.0 - self._cumulative_normal(-x)

        # Para valores positivos
        # Calcular t
        t = 1.0 / (1.0 + p * x)

        # Calcular la serie
        y = t * (a1 + t * (a2 + t * (a3 + t * (a4 + t * a5))))

        # Resultado para x >= 0
        return 1.0 - self._normal_pdf(x) * y

    def _normal_pdf(self, x: float) -> float:
        """
        Función de densidad de probabilidad normal (PDF).

        φ(x) = (1 / √(2π)) * e^(-x²/2)

        Args:
            x: Valor

        Returns:
            φ(x) = PDF de N(0,1) en x
        """
        return math.exp(-0.5 * x * x) / self.SQRT_2_PI

    def calculate_implied_volatility(
        self,
        option: CallOption,
        market_price: float,
        underlying_price: Optional[Decimal] = None,
        max_iterations: int = 100,
        tolerance: float = 1e-6,
    ) -> float:
        """
        Calcular volatilidad implícita usando el método de Newton-Raphson.

        La IV es la volatilidad que hace que el precio del modelo sea igual
        al precio de mercado.

        Args:
            option: Opción a calcular
            market_price: Precio de mercado de la opción
            underlying_price: Precio del subyacente
            max_iterations: Iteraciones máximas
            tolerance: Tolerancia para convergencia

        Returns:
            Volatilidad implícita (en porcentaje)

        Raises:
            ValueError: Si no converge
        """
        S = float(underlying_price or option.underlying_price)
        K = float(option.strike)
        T = option.days_to_expiry / 365.0

        if T <= 0 or S <= 0 or K <= 0:
            raise ValueError("Parámetros inválidos para IV")

        # Valor inicial: 30%
        sigma = 0.3

        for iteration in range(max_iterations):
            # Calcular precio del modelo y vega
            try:
                price = self._calculate_call_price(S, K, T, sigma)
                greeks = self._calculate_black_scholes_greeks(S, K, T, sigma)
                vega = float(greeks.vega) * 100.0  # Convertir de por 1% a valor absoluto

                # Verificar convergencia
                diff = price - market_price
                if abs(diff) < tolerance:
                    return sigma * 100.0  # Retornar en porcentaje

                # Newton-Raphson: sigma_new = sigma - diff / vega
                if vega < tolerance:
                    break

                sigma = sigma - diff / vega

                # Evitar valores negativos
                if sigma < 0.001:
                    sigma = 0.001

            except (ZeroDivisionError, ValueError):
                break

        raise ValueError(f"No convergió IV después de {max_iterations} iteraciones")

    def _calculate_call_price(self, S: float, K: float, T: float, sigma: float) -> float:
        """
        Calcular precio de una call usando Black-Scholes.

        C = S*N(d1) - K*e^(-rT)*N(d2)

        Args:
            S: Precio del subyacente
            K: Strike
            T: Tiempo al vencimiento (años)
            sigma: Volatilidad

        Returns:
            Precio de la call
        """
        r = self.risk_free_rate
        q = self.dividend_yield

        d1 = self._calculate_d1(S, K, T, r, q, sigma)
        d2 = d1 - sigma * math.sqrt(T)

        N_d1 = self._cumulative_normal(d1)
        N_d2 = self._cumulative_normal(d2)

        call_price = S * math.exp(-q * T) * N_d1 - K * math.exp(-r * T) * N_d2

        return call_price

    def estimate_assignment_probability(
        self,
        option: CallOption,
        current_price: Optional[Decimal] = None,
    ) -> str:
        """
        Estimar probabilidad de assignment.

        Basado en:
        - Moneyness (ITM程度)
        - Delta del option
        - Días al vencimiento

        Args:
            option: Opción a evaluar
            current_price: Precio actual del subyacente

        Returns:
            Probabilidad de assignment (AssignmentProbability)
        """
        from .models import AssignmentProbability

        S = float(current_price or option.underlying_price)
        K = float(option.strike)

        if S is None:
            return AssignmentProbability.MODERATE

        # Calcular ITM %
        itm_pct = (S - K) / S if S > K else 0

        # Días al vencimiento
        dte = option.days_to_expiry

        # Calcular delta aproximado
        try:
            greeks = self.calculate_greeks(option, current_price)
            delta = float(greeks.delta)
        except Exception:
            delta = 0.5

        # Lógica de probabilidad
        if dte <= 1:
            # Vencimiento muy cerca
            if itm_pct > 0.01:  # > 1% ITM
                return AssignmentProbability.VERY_HIGH
            elif itm_pct > 0:
                return AssignmentProbability.HIGH
            else:
                return AssignmentProbability.MODERATE

        elif dte <= 7:
            # Una semana
            if itm_pct > 0.02 or delta > 0.8:
                return AssignmentProbability.VERY_HIGH
            elif itm_pct > 0.01 or delta > 0.7:
                return AssignmentProbability.HIGH
            elif itm_pct > 0 or delta > 0.6:
                return AssignmentProbability.MODERATE
            else:
                return AssignmentProbability.LOW

        else:
            # Más de una semana
            if itm_pct > 0.05 or delta > 0.9:
                return AssignmentProbability.HIGH
            elif itm_pct > 0.02 or delta > 0.8:
                return AssignmentProbability.MODERATE
            elif itm_pct > 0 or delta > 0.7:
                return AssignmentProbability.LOW
            else:
                return AssignmentProbability.VERY_LOW


class GreeksCalculator:
    """
    Facade para cálculo de Greeks.

    Proporciona una interfaz simplificada para calcular Greeks
    usando diferentes modelos de pricing.
    """

    def __init__(
        self,
        model: str = "black_scholes",
        risk_free_rate: float = 0.05,
    ):
        """
        Inicializar calculador.

        Args:
            model: Modelo de pricing ("black_scholes", etc.)
            risk_free_rate: Tasa libre de riesgo
        """
        self.model = model
        self.risk_free_rate = risk_free_rate

        if model == "black_scholes":
            self.calculator = BlackScholesGreeks(risk_free_rate=risk_free_rate)
        else:
            raise ValueError(f"Modelo no soportado: {model}")

    def calculate(
        self,
        option: CallOption,
        underlying_price: Optional[Decimal] = None,
        volatility: Optional[float] = None,
    ) -> OptionGreeks:
        """
        Calcular Greeks.

        Args:
            option: Opción a calcular
            underlying_price: Precio del subyacente
            volatility: Volatilidad

        Returns:
            Greeks de la opción
        """
        return self.calculator.calculate_greeks(option, underlying_price, volatility)

    def estimate_probability(
        self,
        option: CallOption,
        current_price: Optional[Decimal] = None,
    ) -> str:
        """
        Estimar probabilidad de assignment.

        Args:
            option: Opción a evaluar
            current_price: Precio actual

        Returns:
            Probabilidad de assignment
        """
        if isinstance(self.calculator, BlackScholesGreeks):
            return self.calculator.estimate_assignment_probability(option, current_price)
        else:
            from .models import AssignmentProbability

            return AssignmentProbability.MODERATE
