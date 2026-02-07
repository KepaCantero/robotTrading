"""
Dividend Analyzer - Análisis de Sostenibilidad y Calidad de Dividendos

Implementa análisis profundo de:
- Calidad del dividendo (combinación de múltiple factores)
- Sostenibilidad (capacidad de mantener/incrementar dividendo)
- Payout ratio analysis
- Dividend growth rate calculation
- Dividend safety scoring

SOLID Principles:
- Single Responsibility: Solo análisis, no screening ni construcción
- Open/Closed: Extensible con nuevas métricas
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from .models import DividendProfile, DividendSafety

logger = logging.getLogger(__name__)


@dataclass
class DividendQualityScore:
    """
    Score de calidad de dividendo (0-100).

    Combina múltiples factores:
    - Yield ajustado por riesgo
    - Crecimiento de dividendos
    - Años de aumentos consecutivos
    - Payout ratio saludable
    - Cobertura de flujo de caja
    """

    total: Decimal
    yield_score: Decimal
    growth_score: Decimal
    consistency_score: Decimal
    safety_score: Decimal
    coverage_score: Decimal

    def __post_init__(self):
        """Validar que el score total sea consistente."""
        if self.total < 0 or self.total > 100:
            raise ValueError(f"Total score debe estar entre 0-100: {self.total}")


@dataclass
class DividendSustainabilityMetrics:
    """
    Métricas de sostenibilidad de dividendos.

    Evalúa la capacidad de la empresa para:
    - Mantener el dividendo actual
    - Crecer el dividendo en el futuro
    - Resistir recesiones
    """

    sustainable: bool
    sustainability_score: Decimal  # 0-100
    risk_factors: List[str]
    strength_factors: List[str]
    payout_trend: str  # "improving", "stable", "declining"
    fcf_trend: str  # "improving", "stable", "declining"
    earnings_stability: Decimal  # 0-100
    dividend_buffer: Optional[Decimal] = None  # FCF / dividendos - 1


class DividendAnalyzer:
    """
    Analizador de calidad y sostenibilidad de dividendos.

    Proporciona análisis detallado para evaluar la calidad de
    acciones de dividendos más allá del screening básico.

    Attributes:
        lookback_years: Años de histórico para análisis
    """

    def __init__(self, lookback_years: int = 10):
        """
        Inicializar analizador.

        Args:
            lookback_years: Años de histórico para análisis
        """
        self.lookback_years = lookback_years

    def analyze_quality(self, profile: DividendProfile) -> DividendQualityScore:
        """
        Analizar calidad del dividendo.

        Args:
            profile: Perfil de acción a analizar

        Returns:
            Score de calidad con componentes desglosados
        """
        logger.debug(f"Analizando calidad de dividendo para {profile.symbol}")

        yield_score = self._calculate_yield_score(profile)
        growth_score = self._calculate_growth_score(profile)
        consistency_score = self._calculate_consistency_score(profile)
        safety_score = self._calculate_safety_score(profile)
        coverage_score = self._calculate_coverage_score(profile)

        # Calcular total como promedio ponderado
        total = (
            yield_score * Decimal("0.25")
            + growth_score * Decimal("0.25")
            + consistency_score * Decimal("0.20")
            + safety_score * Decimal("0.20")
            + coverage_score * Decimal("0.10")
        )

        quality = DividendQualityScore(
            total=total.quantize(Decimal("0.01")),
            yield_score=yield_score,
            growth_score=growth_score,
            consistency_score=consistency_score,
            safety_score=safety_score,
            coverage_score=coverage_score,
        )

        logger.debug(
            f"Calidad de {profile.symbol}: {quality.total}/100 "
            f"(Y:{yield_score} G:{growth_score} C:{consistency_score} "
            f"S:{safety_score} Cov:{coverage_score})"
        )

        return quality

    def analyze_sustainability(
        self,
        profile: DividendProfile,
        historical_data: Optional[Dict[str, List[Decimal]]] = None,
    ) -> DividendSustainabilityMetrics:
        """
        Analizar sostenibilidad del dividendo.

        Args:
            profile: Perfil de acción
            historical_data: Datos históricos opcionales para análisis de tendencias

        Returns:
            Métricas de sostenibilidad
        """
        logger.debug(f"Analizando sostenibilidad para {profile.symbol}")

        risk_factors = self._identify_risk_factors(profile)
        strength_factors = self._identify_strength_factors(profile)

        # Calcular score de sostenibilidad
        sustainability_score = self._calculate_sustainability_score(
            profile, risk_factors, strength_factors
        )

        # Determinar si es sostenible
        sustainable = sustainability_score >= 60

        # Analizar tendencias
        payout_trend = self._analyze_payout_trend(historical_data)
        fcf_trend = self._analyze_fcf_trend(historical_data)

        # Calcular estabilidad de earnings
        earnings_stability = self._calculate_earnings_stability(historical_data)

        # Calcular buffer de dividendos
        dividend_buffer = self._calculate_dividend_buffer(profile)

        metrics = DividendSustainabilityMetrics(
            sustainable=sustainable,
            sustainability_score=sustainability_score.quantize(Decimal("0.01")),
            risk_factors=risk_factors,
            strength_factors=strength_factors,
            payout_trend=payout_trend,
            fcf_trend=fcf_trend,
            earnings_stability=earnings_stability,
            dividend_buffer=dividend_buffer,
        )

        logger.debug(
            f"Sostenibilidad de {profile.symbol}: "
            f"{metrics.sustainability_score}/100 ({'Sí' if sustainable else 'No'})"
        )

        return metrics

    def _calculate_yield_score(self, profile: DividendProfile) -> Decimal:
        """
        Calcular score basado en yield.

        Yield óptimo: 4-6%. Mucho más alto puede ser trap.
        """
        yield_pct = profile.dividend_data.dividend_yield

        if Decimal("4.0") <= yield_pct <= Decimal("6.0"):
            return Decimal("100")
        elif Decimal("3.0") <= yield_pct < Decimal("4.0"):
            # 70-100 escalado
            return Decimal("70") + (yield_pct - Decimal("3.0")) * Decimal("15")
        elif Decimal("6.0") < yield_pct <= Decimal("8.0"):
            # 80-100 descendiente
            return Decimal("100") - (yield_pct - Decimal("6.0")) * Decimal("10")
        elif yield_pct < Decimal("3.0"):
            # 0-70 escalado
            return yield_pct * Decimal("23.33")
        else:  # > 8%
            return max(Decimal("0"), Decimal("80") - (yield_pct - Decimal("8.0")) * Decimal("20"))

    def _calculate_growth_score(self, profile: DividendProfile) -> Decimal:
        """
        Calcular score basado en crecimiento de dividendos.
        """
        growth_3y = profile.dividend_data.dividend_growth_rate_3y or Decimal("0")
        growth_5y = profile.dividend_data.dividend_growth_rate_5y or Decimal("0")
        years = profile.dividend_data.years_consecutive_increases

        score = Decimal("0")

        # Score por tasa de crecimiento (promedio 3y y 5y)
        avg_growth = (growth_3y + growth_5y) / 2

        if avg_growth >= 10:
            score += 50
        elif avg_growth >= 5:
            score += 40
        elif avg_growth >= 2:
            score += 30
        elif avg_growth >= 0:
            score += 20
        else:
            # Penalizar crecimiento negativo
            score += max(Decimal("-20"), avg_growth * 2)

        # Score por años consecutivos
        if years >= 25:
            score += 50
        elif years >= 10:
            score += 40
        elif years >= 5:
            score += 30
        elif years >= 3:
            score += 20
        else:
            score += years * 5

        return min(Decimal("100"), max(Decimal("0"), score))

    def _calculate_consistency_score(self, profile: DividendProfile) -> Decimal:
        """
        Calcular score de consistencia de pagos.
        """
        years = profile.dividend_data.years_consecutive_increases

        # Años de aumentos consecutivos es el mejor indicador
        if years >= 25:
            return Decimal("100")
        elif years >= 15:
            return Decimal("90")
        elif years >= 10:
            return Decimal("80")
        elif years >= 5:
            return Decimal("65")
        elif years >= 3:
            return Decimal("50")
        elif years >= 1:
            return Decimal("30")
        else:
            return Decimal("10")

    def _calculate_safety_score(self, profile: DividendProfile) -> Decimal:
        """
        Calcular score basado en seguridad del dividendo.
        """
        safety = profile.dividend_data.safety

        safety_scores = {
            DividendSafety.VERY_SAFE: Decimal("100"),
            DividendSafety.SAFE: Decimal("85"),
            DividendSafety.MODERATE: Decimal("60"),
            DividendSafety.RISKY: Decimal("30"),
            DividendSafety.DANGEROUS: Decimal("0"),
        }

        return safety_scores.get(safety, Decimal("50"))

    def _calculate_coverage_score(self, profile: DividendProfile) -> Decimal:
        """
        Calcular score basado en cobertura de dividendos.
        """
        coverage = profile.dividend_data.dividend_coverage_ratio

        if coverage is None:
            # Fallback a payout ratio invertido
            payout = profile.dividend_data.payout_ratio
            if payout is None:
                return Decimal("50")  # Sin datos

            # Payout 50% = coverage 2x
            coverage = 100 / payout if payout > 0 else Decimal("0")

        if coverage >= 2.0:
            return Decimal("100")
        elif coverage >= 1.5:
            return Decimal("85")
        elif coverage >= 1.2:
            return Decimal("70")
        elif coverage >= 1.0:
            return Decimal("50")
        else:
            return Decimal("0")

    def _get_sector_for_symbol(self, symbol: str) -> Optional[str]:
        """
        Obtener sector para un símbolo.

        Args:
            symbol: Símbolo de acción

        Returns:
            Sector o None
        """
        return None  # Implementado en estrategia principal

    def _identify_risk_factors(self, profile: DividendProfile) -> List[str]:
        """Identificar factores de riesgo."""
        risks = []

        if profile.is_dividend_trap:
            risks.append("Posible dividend trap detectado")

        if profile.dividend_data.payout_ratio is not None:
            if profile.dividend_data.payout_ratio > 90:
                risks.append("Payout ratio muy alto (>90%)")
            elif profile.dividend_data.payout_ratio > 70:
                risks.append("Payout ratio elevado (>70%)")

        if profile.dividend_data.dividend_growth_rate_3y is not None:
            if profile.dividend_data.dividend_growth_rate_3y < 0:
                risks.append("Dividendos decreciendo")
            elif profile.dividend_data.dividend_growth_rate_3y < 2:
                risks.append("Crecimiento mínimo de dividendos")

        if profile.dividend_data.dividend_coverage_ratio is not None:
            if profile.dividend_data.dividend_coverage_ratio < 1.0:
                risks.append("Cobertura de FCF insuficiente")

        if profile.debt_to_equity is not None and profile.debt_to_equity > 200:
            risks.append("Apalancamiento elevado (D/E > 200%)")

        if profile.beta is not None and profile.beta > 1.5:
            risks.append("Beta elevado (>1.5), alta volatilidad")

        return risks

    def _identify_strength_factors(self, profile: DividendProfile) -> List[str]:
        """Identificar factores de fortaleza."""
        strengths = []

        if profile.dividend_data.years_consecutive_increases >= 25:
            strengths.append("Dividend Aristocrat (25+ años)")
        elif profile.dividend_data.years_consecutive_increases >= 10:
            strengths.append(
                f"{profile.dividend_data.years_consecutive_increases} años de aumentos"
            )

        if profile.dividend_data.safety == DividendSafety.VERY_SAFE:
            strengths.append("Dividend muy seguro (payout < 40%)")

        if profile.dividend_data.dividend_growth_rate_5y is not None:
            if profile.dividend_data.dividend_growth_rate_5y >= 10:
                strengths.append(
                    f"Crecimiento alto 5A: {profile.dividend_data.dividend_growth_rate_5y}%"
                )

        if profile.dividend_data.dividend_coverage_ratio is not None:
            if profile.dividend_data.dividend_coverage_ratio >= 2.0:
                strengths.append("Cobertura sólida (FCF >= 2x dividendos)")

        if profile.roe is not None and profile.roe >= 15:
            strengths.append(f"ROE excelente: {profile.roe}%")

        return strengths

    def _calculate_sustainability_score(
        self,
        profile: DividendProfile,
        risk_factors: List[str],
        strength_factors: List[str],
    ) -> Decimal:
        """
        Calcular score de sostenibilidad (0-100).
        """
        # Score base por payout
        payout = profile.dividend_data.payout_ratio or 100
        if payout <= 50:
            base = Decimal("80")
        elif payout <= 70:
            base = Decimal("60")
        elif payout <= 90:
            base = Decimal("40")
        else:
            base = Decimal("20")

        # Ajustar por factores de riesgo
        base -= len(risk_factors) * 10

        # Ajustar por factores de fortaleza
        base += len(strength_factors) * 5

        # Bonus por años consecutivos
        years = profile.dividend_data.years_consecutive_increases
        if years >= 10:
            base += 10
        elif years >= 5:
            base += 5

        return min(Decimal("100"), max(Decimal("0"), base))

    def _analyze_payout_trend(self, historical_data: Optional[Dict[str, List[Decimal]]]) -> str:
        """Analizar tendencia de payout ratio."""
        if historical_data is None or "payout_ratio" not in historical_data:
            return "stable"

        payouts = historical_data["payout_ratio"]
        if len(payouts) < 3:
            return "stable"

        # Comparar promedio reciente vs histórico
        recent_avg = sum(payouts[-3:]) / 3
        historical_avg = sum(payouts[:-3]) / max(1, len(payouts) - 3)

        if recent_avg < historical_avg * 0.9:
            return "improving"
        elif recent_avg > historical_avg * 1.1:
            return "declining"
        else:
            return "stable"

    def _analyze_fcf_trend(self, historical_data: Optional[Dict[str, List[Decimal]]]) -> str:
        """Analizar tendencia de FCF."""
        if historical_data is None or "fcf" not in historical_data:
            return "stable"

        fcfs = historical_data["fcf"]
        if len(fcfs) < 3:
            return "stable"

        # Calcular regresión lineal simple
        n = len(fcfs)
        x = list(range(n))

        # y = mx + b
        sum_x = sum(x)
        sum_y = float(sum(fcfs))
        sum_xy = sum(x[i] * float(fcfs[i]) for i in range(n))
        sum_x2 = sum(xi * xi for xi in x)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

        if slope > 0.01:  # Crecimiento > 1%
            return "improving"
        elif slope < -0.01:  # Declinación > 1%
            return "declining"
        else:
            return "stable"

    def _calculate_earnings_stability(
        self, historical_data: Optional[Dict[str, List[Decimal]]]
    ) -> Decimal:
        """
        Calcular estabilidad de earnings (0-100).

        Menor volatilidad = mayor estabilidad.
        """
        if historical_data is None or "eps" not in historical_data:
            return Decimal("50")  # Sin datos

        eps_values = [float(e) for e in historical_data["eps"]]
        if len(eps_values) < 2:
            return Decimal("50")

        avg = sum(eps_values) / len(eps_values)
        if avg == 0:
            return Decimal("0")

        # Coeficiente de variación
        variance = sum((e - avg) ** 2 for e in eps_values) / len(eps_values)
        std_dev = variance**0.5
        cv = std_dev / abs(avg) if avg != 0 else 1

        # Convertir a score (CV bajo = score alto)
        # CV 0 = 100, CV 0.5+ = 0
        score = max(0, 100 - cv * 200)

        return Decimal(str(min(100, max(0, score))))

    def _calculate_dividend_buffer(self, profile: DividendProfile) -> Optional[Decimal]:
        """
        Calcular buffer de dividendos.

        Buffer = (FCF / Dividendos) - 1
        Representa qué porcentaje podrían crecer los dividendos con FCF actual.
        """
        coverage = profile.dividend_data.dividend_coverage_ratio
        if coverage is None:
            return None

        return coverage - Decimal("1")

    def analyze_yield_on_cost(
        self,
        profile: DividendProfile,
        purchase_price: Decimal,
        years_held: int,
    ) -> Decimal:
        """
        Calcular Yield on Cost.

        Yield on Cost = Dividendo Anual Actual / Precio de Compra

        Muestra cómo ha crecido el dividendo sobre el costo base.

        Args:
            profile: Perfil actual
            purchase_price: Precio de compra
            years_held: Años que se ha mantenido

        Returns:
            Yield on Cost (%)
        """
        annual_dividend = profile.dividend_data.annual_dividend
        yield_on_cost = (annual_dividend / purchase_price) * 100

        return yield_on_cost.quantize(Decimal("0.01"))

    def project_dividend_income(
        self,
        profile: DividendProfile,
        investment_amount: Decimal,
        years: int = 10,
        growth_rate: Optional[Decimal] = None,
    ) -> List[Tuple[int, Decimal, Decimal]]:
        """
        Proyectar ingreso por dividendos futuro.

        Args:
            profile: Perfil de acción
            investment_amount: Monto a invertir
            years: Años a proyectar
            growth_rate: Tasa de crecimiento anual (usa histórica si es None)

        Returns:
            Lista de (año, dividendo_anual, ingreso_total)
        """
        if growth_rate is None:
            growth_rate = profile.dividend_data.dividend_growth_rate_5y or Decimal("0")

        # Calcular número de acciones
        shares = investment_amount / profile.current_price

        projections = []
        current_dividend = profile.dividend_data.annual_dividend

        for year in range(1, years + 1):
            # Aplicar crecimiento
            current_dividend = current_dividend * (1 + growth_rate / 100)

            # Calcular ingreso
            annual_income = current_dividend * shares

            projections.append((year, current_dividend, annual_income))

        return projections
