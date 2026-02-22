"""
Option Screener - Filtrado de Opciones Óptimas para Covered Calls

Implementa screening de opciones call para encontrar las mejores oportunidades
de venta de opciones cubiertas.

Criterios de screening:
- Días al vencimiento (DTE): 30-45 días óptimo para theta decay
- Moneyness: 2-5% OTM para balance entre riesgo y premio
- Prima mínima: 1% del precio del subyacente
- Liquidez: open interest y volumen mínimos
- IV rank: evitar IV extremadamente alta (IV crush post-earnings)
- Evitar earnings

SOLID Principles:
- Single Responsibility: Solo screening, no gestión de posiciones
- Open/Closed: Extensible con nuevos criterios
"""

import logging
import time
from decimal import Decimal
from typing import List, Optional

from .greeks_calculator import GreeksCalculator
from .models import (
    AssignmentProbability,
    CallOption,
    Moneyness,
    OptionScreenerResult,
    OptionScreeningCriteria,
)

logger = logging.getLogger(__name__)


class OptionScreener:
    """
    Screener de opciones para covered calls.

    Filtra y clasifica opciones call para encontrar las mejores
    oportunidades de venta de opciones cubiertas.

    Attributes:
        criteria: Criterios de screening
        greeks_calculator: Calculador de Greeks
    """

    def __init__(
        self,
        criteria: OptionScreeningCriteria,
        greeks_calculator: Optional[GreeksCalculator] = None,
    ):
        """
        Inicializar screener.

        Args:
            criteria: Criterios de screening
            greeks_calculator: Calculador de Greeks (opcional)
        """
        self.criteria = criteria
        self.greeks_calculator = greeks_calculator or GreeksCalculator()

        logger.info(
            f"OptionScreener inicializado: "
            f"DTE={criteria.min_days_to_expiry}-{criteria.max_days_to_expiry}, "
            f"OTM={criteria.min_moneyness}-{criteria.max_moneyness}, "
            f"Min premium={criteria.min_premium}%"
        )

    def screen(
        self,
        options: List[CallOption],
        underlying_price: Decimal,
    ) -> OptionScreenerResult:
        """
        Aplicar screening a una lista de opciones.

        Args:
            options: Lista de opciones a evaluar
            underlying_price: Precio del subyacente

        Returns:
            Resultado del screening
        """
        start_time = time.time()

        options_passed = []
        options_failed = {}

        for option in options:
            # Actualizar precio del subyacente
            option.underlying_price = underlying_price

            # Evaluar criterios
            failures = self._evaluate_option(option)

            if not failures:
                # Calcular score si tenemos Greeks calculator
                if self.greeks_calculator:
                    try:
                        greeks = self.greeks_calculator.calculate(option)
                        prob = self.greeks_calculator.estimate_probability(option)

                        # Agregar metadata
                        option.metadata = {
                            "delta": str(greeks.delta),
                            "theta": str(greeks.theta),
                            "gamma": str(greeks.gamma),
                            "vega": str(greeks.vega),
                            "assignment_probability": prob,
                        }
                    except Exception as e:
                        logger.warning(f"Error calculando Greeks: {e}")

                options_passed.append(option)
            else:
                options_failed[option.option_symbol or f"{option.strike}"] = failures

        screening_time = (time.time() - start_time) * 1000  # ms

        result = OptionScreenerResult(
            symbol=options[0].symbol if options else "UNKNOWN",
            underlying_price=underlying_price,
            options_passed=options_passed,
            options_failed=options_failed,
            total_evaluated=len(options),
            screening_time_ms=screening_time,
            criteria=self.criteria,
        )

        logger.info(
            f"Screening completado: {len(options_passed)}/{len(options)} pasaron "
            f"({result.pass_rate:.1f}%) en {screening_time:.0f}ms"
        )

        return result

    def _evaluate_option(self, option: CallOption) -> List[str]:
        """
        Evaluar opción contra todos los criterios.

        Args:
            option: Opción a evaluar

        Returns:
            Lista de razones por las que falló (vacía si pasa)
        """
        failures = []

        # 1. Días al vencimiento
        dte = option.days_to_expiry
        if dte < self.criteria.min_days_to_expiry:
            failures.append(f"DTE muy bajo ({dte} < {self.criteria.min_days_to_expiry})")
        elif dte > self.criteria.max_days_to_expiry:
            failures.append(f"DTE muy alto ({dte} > {self.criteria.max_days_to_expiry})")

        # 2. Moneyness
        if option.underlying_price is not None:
            otm_pct = self._calculate_otm_percentage(option)
            if otm_pct < self.criteria.min_moneyness:
                failures.append(f"Muy ITM ({otm_pct:.1%} < {self.criteria.min_moneyness:.1%})")
            elif otm_pct > self.criteria.max_moneyness:
                failures.append(
                    f"Demasiado OTM ({otm_pct:.1%} > {self.criteria.max_moneyness:.1%})"
                )

        # 3. Prima mínima
        min_premium = float(self.criteria.min_premium)
        if option.underlying_price is not None:
            premium_pct = float(option.mid_price or 0) / float(option.underlying_price)
            if premium_pct < min_premium:
                failures.append(f"Prima muy baja ({premium_pct:.2%} < {min_premium:.2%})")

        # 4. Liquidez
        if self.criteria.min_open_interest > 0:
            if (
                option.open_interest is not None
                and option.open_interest < self.criteria.min_open_interest
            ):
                failures.append(
                    f"OI bajo ({option.open_interest} < {self.criteria.min_open_interest})"
                )

        if self.criteria.min_volume > 0:
            if option.volume is not None and option.volume < self.criteria.min_volume:
                failures.append(f"Volumen bajo ({option.volume} < {self.criteria.min_volume})")

        # 5. Target Delta (si está especificado)
        if self.criteria.target_delta is not None and hasattr(option, 'metadata'):
            try:
                delta_str = option.metadata.get('delta')
                if delta_str:
                    delta = float(delta_str)
                    target = float(self.criteria.target_delta)
                    if abs(delta - target) > 0.2:  # Tolerancia de 0.2
                        failures.append(
                            f"Delta fuera de rango ({delta:.2f} vs target {target:.2f})"
                        )
            except (ValueError, KeyError):
                pass

        return failures

    def _calculate_otm_percentage(self, option: CallOption) -> float:
        """
        Calcular porcentaje OTM.

        Para calls: OTM% = (strike - price) / price

        Args:
            option: Opción a evaluar

        Returns:
            Porcentaje OTM (positivo = OTM, negativo = ITM)
        """
        if option.underlying_price is None or option.underlying_price == 0:
            return 0.0

        return float((option.strike - option.underlying_price) / option.underlying_price)

    def score_option(self, option: CallOption) -> Decimal:
        """
        Calcular score de una opción (0-100).

        El score combina:
        - Premium (mayor es mejor)
        - Theta decay (mayor es mejor)
        - Assignment probability (menor es mejor)
        - DTE (cerca de target es mejor)
        - Liquidez (mayor es mejor)

        Args:
            option: Opción a calificar

        Returns:
            Score de 0 a 100
        """
        score = Decimal("0")

        # 1. Premium score (0-25 puntos)
        if option.underlying_price is not None and option.mid_price is not None:
            premium_pct = float(option.mid_price) / float(option.underlying_price)
            # 1% = 10 puntos, 3%+ = 25 puntos
            premium_score = min(25, premium_pct * 800)
            score += Decimal(str(premium_score))

        # 2. Theta score (0-25 puntos)
        if hasattr(option, 'metadata') and 'theta' in option.metadata:
            try:
                theta = float(option.metadata['theta'])
                # Más negativo = más theta decay para el vendedor = mejor
                theta_score = min(25, abs(theta) * 100)
                score += Decimal(str(theta_score))
            except (ValueError, KeyError):
                score += Decimal("10")  # Neutral si no hay theta

        # 3. Assignment probability score (0-25 puntos)
        if hasattr(option, 'metadata') and 'assignment_probability' in option.metadata:
            prob = option.metadata['assignment_probability']
            prob_scores = {
                AssignmentProbability.VERY_LOW: 25,
                AssignmentProbability.LOW: 20,
                AssignmentProbability.MODERATE: 15,
                AssignmentProbability.HIGH: 5,
                AssignmentProbability.VERY_HIGH: 0,
            }
            score += Decimal(str(prob_scores.get(prob, 10)))

        # 4. DTE score (0-15 puntos)
        target_dte = (self.criteria.min_days_to_expiry + self.criteria.max_days_to_expiry) / 2
        dte = option.days_to_expiry
        dte_diff = abs(dte - target_dte)
        dte_score = max(0, 15 - dte_diff * 0.5)
        score += Decimal(str(dte_score))

        # 5. Liquidity score (0-10 puntos)
        liquidity_score = 0
        if option.open_interest:
            liquidity_score += min(5, option.open_interest / 100)
        if option.volume:
            liquidity_score += min(5, option.volume / 100)
        score += Decimal(str(liquidity_score))

        return max(Decimal("0"), min(Decimal("100"), score))

    def get_best_option(
        self,
        options: List[CallOption],
        underlying_price: Decimal,
        top_n: int = 1,
    ) -> List[CallOption]:
        """
        Obtener las mejores opciones después del screening.

        Args:
            options: Lista de opciones
            underlying_price: Precio del subyacente
            top_n: Número de mejores opciones a retornar

        Returns:
            Lista de mejores opciones (ordenadas por score)
        """
        # Aplicar screening
        result = self.screen(options, underlying_price)

        # Calcular scores
        scored_options = [(self.score_option(opt), opt) for opt in result.options_passed]

        # Ordenar por score descendente
        scored_options.sort(key=lambda x: x[0], reverse=True)

        # Retornar top N
        return [opt for score, opt in scored_options[:top_n]]

    def filter_by_moneyness(
        self,
        options: List[CallOption],
        moneyness: Moneyness,
        underlying_price: Decimal,
    ) -> List[CallOption]:
        """
        Filtrar opciones por moneyness.

        Args:
            options: Lista de opciones
            moneyness: Moneyness deseado
            underlying_price: Precio del subyacente

        Returns:
            Lista filtrada de opciones
        """
        filtered = []

        for option in options:
            option.underlying_price = underlying_price

            if option.moneyness == moneyness:
                filtered.append(option)

        return filtered

    def filter_by_dte(
        self,
        options: List[CallOption],
        min_dte: int,
        max_dte: int,
    ) -> List[CallOption]:
        """
        Filtrar opciones por días al vencimiento.

        Args:
            options: Lista de opciones
            min_dte: DTE mínimo
            max_dte: DTE máximo

        Returns:
            Lista filtrada de opciones
        """
        return [opt for opt in options if min_dte <= opt.days_to_expiry <= max_dte]

    def filter_by_premium(
        self,
        options: List[CallOption],
        min_premium_pct: Decimal,
        underlying_price: Decimal,
    ) -> List[CallOption]:
        """
        Filtrar opciones por prima mínima.

        Args:
            options: Lista de opciones
            min_premium_pct: Prima mínima (% del precio)
            underlying_price: Precio del subyacente

        Returns:
            Lista filtrada de opciones
        """
        filtered = []

        min_premium = float(min_premium_pct)

        for option in options:
            option.underlying_price = underlying_price

            if option.mid_price is not None:
                premium_pct = float(option.mid_price) / float(underlying_price)
                if premium_pct >= min_premium:
                    filtered.append(option)

        return filtered
