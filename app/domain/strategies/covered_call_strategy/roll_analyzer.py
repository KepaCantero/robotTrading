"""
Roll Analyzer - Análisis de Oportunidades de Rolling

Implementa análisis de oportunidades de rolling para posiciones covered call:
- Identificar cuándo hacer roll
- Calcular beneficio esperado del roll
- Comparar opciones de roll (up, down, out)
- Optimizar strike y expiry del roll

El rolling permite:
1. Extender la duración de la estrategia
2. Ajustarse a movimientos del mercado
3. Generar prima adicional
4. Gestionar riesgo de assignment

SOLID Principles:
- Single Responsibility: Solo análisis de rolling, no ejecución
- Open/Closed: Extensible con nuevas estrategias de roll
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from .greeks_calculator import GreeksCalculator
from .models import (
    AssignmentProbability,
    CallOption,
    CoveredCallPosition,
    RollOpportunity,
    RollType,
)

logger = logging.getLogger(__name__)


class RollAnalyzer:
    """
    Analizador de oportunidades de rolling.

    Evalúa si vale la pena hacer roll de una posición covered call
    y determina la mejor estrategia de rolling.

    Attributes:
        greeks_calculator: Calculador de Greeks
        min_premium_benefit: Beneficio mínimo de prima para justificar roll
    """

    def __init__(
        self,
        greeks_calculator: Optional[GreeksCalculator] = None,
        min_premium_benefit: Optional[Decimal] = None,  # 0.5% mínimo
    ):
        """
        Inicializar analizador de rolls.

        Args:
            greeks_calculator: Calculador de Greeks
            min_premium_benefit: Beneficio mínimo (% del subyacente)
        """
        if min_premium_benefit is None:
            min_premium_benefit = Decimal("0.005")
        self.greeks_calculator = greeks_calculator or GreeksCalculator()
        self.min_premium_benefit = min_premium_benefit

        logger.info(f"RollAnalyzer inicializado: " f"min_premium_benefit={min_premium_benefit:.2%}")

    def analyze_roll_opportunities(
        self,
        position: CoveredCallPosition,
        current_price: Decimal,
        available_options: List[CallOption],
    ) -> List[RollOpportunity]:
        """
        Analizar oportunidades de rolling para una posición.

        Args:
            position: Posición a analizar
            current_price: Precio actual del subyacente
            available_options: Opciones disponibles para roll

        Returns:
            Lista de oportunidades de rolling (ordenadas por beneficio)
        """
        opportunities = []

        # Actualizar precio en la posición
        position.current_price = current_price

        # Calcular moneyness actual
        otm_pct = (position.call_option.strike - current_price) / current_price

        # 1. Análisis de Roll Up (si el stock subió)
        if otm_pct < -0.02:  # Está ITM > 2%
            up_opportunities = self._analyze_roll_up(position, current_price, available_options)
            opportunities.extend(up_opportunities)

        # 2. Análisis de Roll Down (si el stock cayó mucho)
        elif otm_pct > 0.05:  # Está OTM > 5%
            down_opportunities = self._analyze_roll_down(position, current_price, available_options)
            opportunities.extend(down_opportunities)

        # 3. Análisis de Roll Out (extender tiempo)
        out_opportunities = self._analyze_roll_out(position, current_price, available_options)
        opportunities.extend(out_opportunities)

        # Ordenar por beneficio
        opportunities.sort(key=lambda x: x.additional_premium, reverse=True)

        logger.debug(
            f"Análisis de roll: {len(opportunities)} oportunidades "
            f"encontradas para {position.symbol}"
        )

        return opportunities

    def _analyze_roll_up(
        self,
        position: CoveredCallPosition,
        current_price: Decimal,
        available_options: List[CallOption],
    ) -> List[RollOpportunity]:
        """
        Analizar roll up (subir strike).

        Se usa cuando el stock subió y la opción está ITM.
        El objetivo es moverse a un strike más alto para:
        - Evitar assignment
        - Mantener exposición alcista
        - Recibir prima adicional

        Args:
            position: Posición actual
            current_price: Precio actual
            available_options: Opciones disponibles

        Returns:
            Lista de oportunidades de roll up
        """
        opportunities = []

        # Calcular strike objetivo (~3-5% OTM)
        target_strike_pct = Decimal("1.03")  # 3% OTM
        target_strike = current_price * target_strike_pct

        # Buscar opciones con strike >= target
        # y expiry >= expiry actual + 7 días
        min_expiry = position.call_option.expiry_date + timedelta(days=7)

        for option in available_options:
            if option.strike < target_strike:
                continue

            if option.expiry_date < min_expiry:
                continue

            # Calcular beneficio del roll
            current_option_value = position.current_option_price or position.call_option.mid_price
            new_option_bid = option.bid

            if current_option_value is None or new_option_bid is None:
                continue

            # Costo de cerrar posición actual
            close_cost = current_option_value * position.contracts_sold * 100

            # Prima de nueva posición
            new_premium = new_option_bid * position.contracts_sold * 100

            # Beneficio neto
            net_benefit = new_premium - close_cost
            net_benefit_pct = net_benefit / (current_price * position.shares_owned)

            # Solo considerar si el beneficio es positivo
            if net_benefit <= 0:
                continue

            # Crear oportunidad
            opportunity = RollOpportunity(
                position=position,
                new_option=option,
                roll_type=RollType.ROLL_UP_AND_OUT,
                additional_premium=net_benefit,
                days_to_expiry_new=option.days_to_expiry,
                reason=f"Subir strike de ${position.call_option.strike} a ${option.strike}",
                expected_benefit=f"Beneficio neto: ${net_benefit:.2f} ({net_benefit_pct:.2%})",
                probability_delta="Reducir riesgo de assignment",
            )

            opportunities.append(opportunity)

        return opportunities

    def _analyze_roll_down(
        self,
        position: CoveredCallPosition,
        current_price: Decimal,
        available_options: List[CallOption],
    ) -> List[RollOpportunity]:
        """
        Analizar roll down (bajar strike).

        Se usa cuando el stock cayó y la opción está muy OTM.
        El objetivo es bajar el strike para:
        - Recibir más prima
        - Reducir el "dinero muerto" en el strike alto
        - Aumentar probabilidad de assignment (no es malo si el stock está bajo)

        Args:
            position: Posición actual
            current_price: Precio actual
            available_options: Opciones disponibles

        Returns:
            Lista de oportunidades de roll down
        """
        opportunities = []

        # Strike objetivo (~2-3% OTM del precio actual)
        target_strike_pct = Decimal("1.02")  # 2% OTM
        target_strike = current_price * target_strike_pct

        # Buscar opciones con strike < strike actual
        # y >= target_strike
        # y expiry >= expiry actual + 7 días
        min_expiry = position.call_option.expiry_date + timedelta(days=7)

        for option in available_options:
            if option.strike >= position.call_option.strike:
                continue

            if option.strike < target_strike:
                continue

            if option.expiry_date < min_expiry:
                continue

            # Calcular beneficio del roll
            current_option_value = position.current_option_price or position.call_option.mid_price
            new_option_bid = option.bid

            if current_option_value is None or new_option_bid is None:
                continue

            # Costo de cerrar posición actual (pequeño si está muy OTM)
            close_cost = current_option_value * position.contracts_sold * 100

            # Prima de nueva posición (debe ser mayor)
            new_premium = new_option_bid * position.contracts_sold * 100

            # Beneficio neto
            net_benefit = new_premium - close_cost
            net_benefit_pct = net_benefit / (current_price * position.shares_owned)

            # Solo considerar si el beneficio es significativo
            if net_benefit_pct < self.min_premium_benefit:
                continue

            # Crear oportunidad
            opportunity = RollOpportunity(
                position=position,
                new_option=option,
                roll_type=RollType.ROLL_DOWN_AND_OUT,
                additional_premium=net_benefit,
                days_to_expiry_new=option.days_to_expiry,
                reason=f"Bajar strike de ${position.call_option.strike} a ${option.strike}",
                expected_benefit=f"Beneficio neto: ${net_benefit:.2f} ({net_benefit_pct:.2%})",
                probability_delta="Aumentar probabilidad de assignment",
            )

            opportunities.append(opportunity)

        return opportunities

    def _analyze_roll_out(
        self,
        position: CoveredCallPosition,
        current_price: Decimal,
        available_options: List[CallOption],
    ) -> List[RollOpportunity]:
        """
                Analizar roll out (extenderexpiry).

                Se usa cuando:
                - La opción está cerca de vencer (< 7-10 días)
        - Se quiere mantener la posición por más tiempo
        - La posición está cerca de ATM o ligeramente OTM

                El objetivo es extender el plazo para:
                - Recibir prima adicional
                - Mantener la posición activa
                - Beneficiarse de más theta decay

                Args:
                    position: Posición actual
                    current_price: Precio actual
                    available_options: Opciones disponibles

                Returns:
                    Lista de oportunidades de roll out
        """
        opportunities: List[RollOpportunity] = []

        # Días al vencimiento
        dte = position.call_option.days_to_expiry

        # Solo considerar si está cerca de vencer
        if dte > 14:
            return opportunities

        # Buscar opciones con mismo strike
        # y expiry >= 30 días en el futuro
        min_expiry = date.today() + timedelta(days=30)

        for option in available_options:
            # Buscar mismo strike (o muy cercano)
            if abs(option.strike - position.call_option.strike) > Decimal("0.50"):
                continue

            if option.expiry_date < min_expiry:
                continue

            # Calcular beneficio del roll
            current_option_value = position.current_option_price or position.call_option.mid_price
            new_option_bid = option.bid

            if current_option_value is None or new_option_bid is None:
                continue

            # Costo de cerrar posición actual
            close_cost = current_option_value * position.contracts_sold * 100

            # Prima de nueva posición
            new_premium = new_option_bid * position.contracts_sold * 100

            # Beneficio neto
            net_benefit = new_premium - close_cost
            net_benefit_pct = net_benefit / (current_price * position.shares_owned)

            # Crear oportunidad (incluso si beneficio es pequeño, extender tiempo tiene valor)
            opportunity = RollOpportunity(
                position=position,
                new_option=option,
                roll_type=RollType.ROLL_OUT,
                additional_premium=net_benefit,
                days_to_expiry_new=option.days_to_expiry,
                reason=f"Extender de {dte} a {option.days_to_expiry} días",
                expected_benefit=f"Prima adicional: ${net_benefit:.2f} ({net_benefit_pct:.2%})",
                probability_delta="Mantener gestión de posición",
            )

            opportunities.append(opportunity)

        return opportunities

    def should_roll(
        self,
        position: CoveredCallPosition,
        current_price: Decimal,
        opportunities: List[RollOpportunity],
    ) -> Tuple[bool, Optional[RollOpportunity]]:
        """
        Determinar si se debe hacer roll y cuál es la mejor oportunidad.

        Args:
            position: Posición a evaluar
            current_price: Precio actual
            opportunities: Oportunidades de rolling

        Returns:
            (should_roll, best_opportunity)
        """
        if not opportunities:
            return False, None

        # Obtener la mejor oportunidad (mayor beneficio neto)
        best = opportunities[0]

        # Criterios para justificar roll:
        # 1. Beneficio mínimo
        if best.additional_premium <= 0:
            return False, None

        benefit_pct = best.additional_premium / (current_price * position.shares_owned)

        # 2. El beneficio debe justificar el riesgo
        if benefit_pct < self.min_premium_benefit:
            # Excepción: si es roll out por DTE bajo
            if best.roll_type == RollType.ROLL_OUT:
                dte = position.call_option.days_to_expiry
                if dte <= 5:
                    return True, best
            return False, None

        # 3. Evaluar probabilidad de assignment
        current_prob = position.assignment_probability

        # Si la probabilidad actual es muy alta, justifica roll casi siempre
        if current_prob in [AssignmentProbability.VERY_HIGH]:
            return True, best

        # Si es alta y el roll reduce la probabilidad significativamente
        if current_prob == AssignmentProbability.HIGH:
            # Evaluar delta de probabilidad
            try:
                new_prob = self.greeks_calculator.estimate_probability(
                    best.new_option, current_price
                )

                # Si el roll reduce de HIGH/VERY_HIGH a LOW/MODERATE
                if new_prob in [
                    AssignmentProbability.LOW,
                    AssignmentProbability.MODERATE,
                    AssignmentProbability.VERY_LOW,
                ]:
                    return True, best
            except Exception:
                pass

        # Para otros casos, el beneficio debe ser mayor
        if benefit_pct >= self.min_premium_benefit * 2:
            return True, best

        return True, best

    def calculate_roll_metrics(
        self,
        position: CoveredCallPosition,
        opportunity: RollOpportunity,
    ) -> dict:
        """
        Calcular métricas detalladas de una oportunidad de roll.

        Args:
            position: Posición actual
            opportunity: Oportunidad de roll

        Returns:
            Dict con métricas
        """
        position.current_price or Decimal("100")

        # Métricas actuales
        current_return_if_called = position.return_if_called or Decimal("0")
        current_return_if_unchanged = position.return_if_unchanged or Decimal("0")
        current_break_even = position.break_even_price
        current_downside_prot = position.downside_protection or Decimal("0")

        # Métricas después del roll (estimadas)
        # Nuevos parámetros
        new_strike = opportunity.new_option.strike
        new_premium_total = position.total_premium + opportunity.additional_premium
        new_premium_per_share = new_premium_total / position.shares_owned

        # Nuevo break-even
        new_break_even = position.average_cost - new_premium_per_share

        # Nuevo retorno si se ejerce
        new_profit_per_share = new_strike - position.average_cost + new_premium_per_share
        new_return_if_called = (new_profit_per_share / position.average_cost) * 100

        # Nuevo retorno si sin cambios
        new_return_if_unchanged = (new_premium_total / position.total_cost) * 100

        # Nueva protección a la baja
        new_downside_prot = (new_premium_total / position.total_cost) * 100

        return {
            "current_metrics": {
                "strike": str(position.call_option.strike),
                "break_even": str(current_break_even),
                "return_if_called": str(current_return_if_called),
                "return_if_unchanged": str(current_return_if_unchanged),
                "downside_protection": str(current_downside_prot),
                "days_to_expiry": position.call_option.days_to_expiry,
            },
            "new_metrics": {
                "strike": str(new_strike),
                "break_even": str(new_break_even),
                "return_if_called": str(new_return_if_called),
                "return_if_unchanged": str(new_return_if_unchanged),
                "downside_protection": str(new_downside_prot),
                "days_to_expiry": opportunity.days_to_expiry_new,
            },
            "delta": {
                "additional_premium": str(opportunity.additional_premium),
                "break_even_change": str(new_break_even - current_break_even),
                "return_if_called_change": str(new_return_if_called - current_return_if_called),
                "return_if_unchanged_change": str(
                    new_return_if_unchanged - current_return_if_unchanged
                ),
            },
        }
