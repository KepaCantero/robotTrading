"""
Dividend Screener - Filtrado de Acciones por Métricas de Dividendos

Implementa screening de acciones basado en:
- Dividend yield mínimo y máximo
- Payout ratio
- Dividend growth rate
- Years of consecutive increases
- Market cap
- Quality scores

SOLID Principles:
- Single Responsibility: Solo se encarga de screening
- Open/Closed: Extensible con nuevos filtros
- Dependency Inversion: Depende de abstracciones (models)
"""

import logging
import time
from decimal import Decimal
from typing import Dict, List

from app.shared.config.centralized_config import get_config

from .models import (
    DividendProfile,
    DividendSafety,
    DividendScreeningCriteria,
    DividendScreeningResult,
    DividendStockResult,
    DividendStrategyConfig,
)

logger = logging.getLogger(__name__)


class DividendScreener:
    """
    Screener de acciones de dividendos.

    Filtra universo de acciones basado en criterios de dividendos
    y calidad fundamental para identificar candidatos de inversión.

    Attributes:
        config: Configuración de la estrategia de dividendos
    """

    def __init__(self, config: DividendStrategyConfig):
        """
        Inicializar screener.

        Args:
            config: Configuración de la estrategia
        """
        self.config = config
        self.criteria = self._create_screening_criteria()

        # Load fundamental analysis thresholds from config
        tt = get_config().trading_thresholds
        self.fa = tt  # Fundamental analysis thresholds

    def _create_screening_criteria(self) -> DividendScreeningCriteria:
        """
        Crear criterios de screening desde config.

        Returns:
            Criterios de screening normalizados
        """
        return DividendScreeningCriteria(
            min_yield=self.config.min_dividend_yield,
            max_yield=self.config.max_dividend_yield,
            max_payout=self.config.max_payout_ratio,
            min_growth=self.config.min_dividend_growth,
            min_years=self.config.min_years_consecutive,
            min_market_cap=self.config.min_market_cap,
            min_quality=self.config.min_quality_score,
            min_sustainability=self.config.min_sustainability_score,
            require_profitable=self.config.require_profitable,
            require_positive_fcf=self.config.require_positive_fcf,
            min_safety=self.config.min_dividend_safety,
            excluded_sectors=self.config.excluded_sectors,
        )

    def screen(
        self,
        profiles: List[DividendProfile],
    ) -> DividendScreeningResult:
        """
        Aplicar screening a lista de perfiles.

        Args:
            profiles: Lista de perfiles de acciones a evaluar

        Returns:
            Resultado del screening con acciones aprobadas y rechazadas
        """
        start_time = time.time()

        passed: List[DividendStockResult] = []
        failed: Dict[str, List[str]] = {}
        total_evaluated = len(profiles)

        logger.info(
            f"Iniciando screening de {total_evaluated} acciones "
            f"con criterios: {self._get_criteria_description()}"
        )

        for profile in profiles:
            failure_reasons = self._evaluate_profile(profile)

            if not failure_reasons:
                # Crear DividendStockResult con score inicial
                stock = self._create_dividend_stock(profile)
                passed.append(stock)
            else:
                failed[profile.symbol] = failure_reasons

        elapsed_ms = (time.time() - start_time) * 1000

        result = DividendScreeningResult(
            passed_stocks=passed,
            failed_stocks=failed,
            total_evaluated=total_evaluated,
            screening_time_ms=elapsed_ms,
            criteria=self.criteria,
        )

        logger.info(
            f"Screening completado: {len(passed)}/{total_evaluated} acciones pasaron "
            f"({result.pass_rate:.1f}%) en {elapsed_ms:.1f}ms"
        )

        return result

    def _evaluate_profile(self, profile: DividendProfile) -> List[str]:
        """
        Evaluar si un perfil pasa todos los filtros.

        Args:
            profile: Perfil de acción a evaluar

        Returns:
            Lista de razones por las que falló (vacía si pasó)
        """
        failures: List[str] = []

        # 0. Dividend trap check (más importante - va primero)
        if profile.is_dividend_trap:
            failures.append("Dividend trap detectado")
            # Si es trap, no seguir evaluando
            return failures

        # 1. Yield checks
        dividend_yield = profile.dividend_data.dividend_yield
        if dividend_yield < self.criteria.min_yield:
            failures.append(f"Yield muy bajo: {dividend_yield:.2f}% < {self.criteria.min_yield}%")
        if dividend_yield > self.criteria.max_yield:
            failures.append(f"Yield muy alto: {dividend_yield:.2f}% > {self.criteria.max_yield}%")

        # 2. Payout ratio check
        if profile.dividend_data.payout_ratio is not None and profile.dividend_data.payout_ratio > self.criteria.max_payout:
            failures.append(
                f"Payout ratio excedido: "
                f"{profile.dividend_data.payout_ratio:.1f}% > {self.criteria.max_payout}%"
            )

        # 3. Dividend growth check
        if self.criteria.min_growth is not None:
            growth_3y = profile.dividend_data.dividend_growth_rate_3y
            if growth_3y is not None and growth_3y < self.criteria.min_growth:
                failures.append(
                    f"Crecimiento insuficiente: " f"{growth_3y:.1f}% < {self.criteria.min_growth}%"
                )

        # 4. Consecutive years check
        if profile.dividend_data.years_consecutive_increases < self.criteria.min_years:
            failures.append(
                f"Años consecutivos insuficientes: "
                f"{profile.dividend_data.years_consecutive_increases} < {self.criteria.min_years}"
            )

        # 5. Market cap check
        if self.criteria.min_market_cap is not None and profile.market_cap is not None and profile.market_cap < self.criteria.min_market_cap:
            failures.append(
                f"Market cap muy bajo: "
                f"${profile.market_cap:.0f}M < ${self.criteria.min_market_cap:.0f}M"
            )

        # 6. Quality score check
        if profile.quality_score is not None and profile.quality_score < self.criteria.min_quality:
            failures.append(
                f"Quality score bajo: "
                f"{profile.quality_score:.1f} < {self.criteria.min_quality}"
            )

        # 7. Sustainability score check
        if profile.sustainability_score is not None and profile.sustainability_score < self.criteria.min_sustainability:
            failures.append(
                f"Sustainability score bajo: "
                f"{profile.sustainability_score:.1f} < {self.criteria.min_sustainability}"
            )

        # 8. Profitability check
        if self.criteria.require_profitable:
            eps = profile.dividend_data.earnings_per_share
            if eps is None or eps <= 0:
                failures.append(f"EPS no positivo: {eps}")

        # 9. FCF check
        if self.criteria.require_positive_fcf:
            fcf = profile.dividend_data.free_cash_flow_per_share
            if fcf is None or fcf <= 0:
                failures.append(f"FCF no positivo: {fcf}")

        # 10. Dividend safety check
        safety = profile.dividend_data.safety
        safety_order = {
            DividendSafety.VERY_SAFE: 5,
            DividendSafety.SAFE: 4,
            DividendSafety.MODERATE: 3,
            DividendSafety.RISKY: 2,
            DividendSafety.DANGEROUS: 1,
        }
        if safety_order[safety] < safety_order[self.criteria.min_safety]:
            failures.append(f"Seguridad de dividendo baja: {safety}")

        # 11. Sector exclusion check
        if profile.sector in self.criteria.excluded_sectors:
            failures.append(f"Sector excluido: {profile.sector}")

        # 12. Valuation checks (optional)
        if self.config.max_pe_ratio is not None and profile.pe_ratio is not None and profile.pe_ratio > self.config.max_pe_ratio:
            failures.append(
                f"P/E muy alto: {profile.pe_ratio:.1f} > {self.config.max_pe_ratio}"
            )

        if self.config.max_pb_ratio is not None and profile.pb_ratio is not None and profile.pb_ratio > self.config.max_pb_ratio:
            failures.append(
                f"P/B muy alto: {profile.pb_ratio:.1f} > {self.config.max_pb_ratio}"
            )

        # 13. Risk check (beta)
        if self.config.max_beta is not None and profile.beta is not None and profile.beta > self.config.max_beta:
            failures.append(f"Beta muy alto: {profile.beta:.2f} > {self.config.max_beta}")

        return failures

    def _create_dividend_stock(self, profile: DividendProfile) -> DividendStockResult:
        """
        Crear DividendStockResult desde profile.

        Args:
            profile: Perfil de acción

        Returns:
            DividendStockResult con score de decisión
        """
        # Calcular score de decisión preliminar (se refinará en analyzer)
        decision_score = self._calculate_preliminary_score(profile)
        decision_reason = f"Paso screening con yield {profile.dividend_data.dividend_yield:.2f}%"
        recommendation = self._get_recommendation(decision_score)

        return DividendStockResult(
            profile=profile,
            decision_score=Decimal(str(round(decision_score, 2))),
            decision_reason=decision_reason,
            recommendation=recommendation,
        )

    def _calculate_preliminary_score(self, profile: DividendProfile) -> float:
        """
        Calcular score preliminar basado en pesos de configuración.

        Args:
            profile: Perfil de acción

        Returns:
            Score entre 0 y 100
        """
        scores = {
            "yield": self._score_yield(profile),
            "growth": self._score_growth(profile),
            "sustainability": self._score_sustainability(profile),
            "value": self._score_value(profile),
        }

        # Pesos desde config
        weights = {
            "yield": float(self.config.yield_weight),
            "growth": float(self.config.growth_weight),
            "sustainability": float(self.config.sustainability_weight),
            "value": float(self.config.value_weight),
        }

        weighted_score = sum(scores[k] * weights[k] for k in scores.keys())

        return min(100.0, max(0.0, weighted_score))

    def _score_yield(self, profile: DividendProfile) -> float:
        """
        Puntuar yield (más alto es mejor hasta cierto punto).

        Args:
            profile: Perfil de acción

        Returns:
            Score 0-100
        """
        yield_pct = float(profile.dividend_data.dividend_yield)

        # Yield ideal: 4-6%
        if 4.0 <= yield_pct <= 6.0:
            return 100.0
        elif 3.0 <= yield_pct < 4.0:
            return 70.0 + (yield_pct - 3.0) * 15  # 70-85
        elif 6.0 < yield_pct <= 8.0:
            return 100.0 - (yield_pct - 6.0) * 10  # 80-100
        elif yield_pct < 3.0:
            return max(0.0, yield_pct * 20)  # 0-60
        else:  # yield_pct > 8.0
            return max(0.0, 80.0 - (yield_pct - 8.0) * 20)  # 60-80

    def _score_growth(self, profile: DividendProfile) -> float:
        """
        Puntuar crecimiento de dividendos.

        Args:
            profile: Perfil de acción

        Returns:
            Score 0-100
        """
        growth = profile.dividend_data.dividend_growth_rate_3y
        years = profile.dividend_data.years_consecutive_increases

        if growth is None:
            growth = 0.0

        growth_score = 0.0

        # Score por tasa de crecimiento
        if growth >= 10:
            growth_score += 50
        elif growth >= 5:
            growth_score += 40
        elif growth >= 2:
            growth_score += 30
        elif growth >= 0:
            growth_score += 20
        else:
            growth_score += max(0, 20 + growth * 2)  # Penalizar crecimiento negativo

        # Score por años consecutivos
        if years >= 25:
            growth_score += 50
        elif years >= 10:
            growth_score += 40
        elif years >= 5:
            growth_score += 30
        elif years >= 3:
            growth_score += 20
        else:
            growth_score += years * 5

        return min(100.0, growth_score)

    def _score_sustainability(self, profile: DividendProfile) -> float:
        """
        Puntuar sostenibilidad del dividendo.

        Args:
            profile: Perfil de acción

        Returns:
            Score 0-100
        """
        safety = profile.dividend_data.safety
        payout = profile.dividend_data.payout_ratio or 100

        safety_scores = {
            "very_safe": 100,
            "safe": 85,
            "moderate": 60,
            "risky": 30,
            "dangerous": 0,
        }

        base_score = safety_scores.get(safety, 50)

        # Penalizar payout ratio alto
        if payout > 80:
            base_score -= 20
        elif payout > 60:
            base_score -= 10

        # Bonus por dividend coverage ratio - use config values
        if profile.dividend_data.dividend_coverage_ratio:
            coverage = float(profile.dividend_data.dividend_coverage_ratio)
            if coverage >= self.fa.dividend_coverage_excellent:
                base_score = min(100, base_score + 10)
            elif coverage >= self.fa.dividend_coverage_good:
                base_score = min(100, base_score + 5)

        return max(0.0, min(100.0, base_score))

    def _score_value(self, profile: DividendProfile) -> float:
        """
        Puntuar valoración de la acción.

        Args:
            profile: Perfil de acción

        Returns:
            Score 0-100
        """
        score = 50.0  # Base score

        # P/E ratio (ideal range) - use config values
        if profile.pe_ratio is not None:
            pe = float(profile.pe_ratio)
            if self.fa.pe_ideal_min <= pe <= self.fa.pe_ideal_max:
                score += 20
            elif self.fa.pe_problematic_max <= pe < self.fa.pe_very_cheap_max:
                score += 30  # Muy barato
            elif self.fa.pe_ideal_max < pe <= self.fa.pe_acceptable_max:
                score += 10
            elif pe > self.fa.pe_too_expensive_min or pe < self.fa.pe_problematic_max:
                score -= 20  # Muy caro o problema

        # P/B ratio (ideal range) - use config values
        if profile.pb_ratio is not None:
            pb = float(profile.pb_ratio)
            if self.fa.pb_ideal_min <= pb <= self.fa.pb_ideal_max:
                score += 15
            elif self.fa.pb_very_cheap_max <= pb < self.fa.pb_ideal_min:
                score += 25  # Muy barato
            elif pb > self.fa.pb_too_expensive:
                score -= 15

        # ROE (ideal thresholds) - use config values
        if profile.roe is not None:
            roe = float(profile.roe)
            if roe >= self.fa.roe_excellent:
                score += 15
            elif roe >= self.fa.roe_good:
                score += 10
            elif roe < 0:
                score -= 20

        return max(0.0, min(100.0, score))

    def _get_recommendation(self, score: float) -> str:
        """
        Obtener recomendación basada en score - use config thresholds.

        Args:
            score: Score de decisión

        Returns:
            Recomendación: buy/hold/avoid
        """
        if score >= self.fa.dividend_buy_score:
            return "buy"
        elif score >= self.fa.dividend_hold_score:
            return "hold"
        else:
            return "avoid"

    def _get_criteria_description(self) -> str:
        """Obtener descripción de criterios de screening."""
        return (
            f"Yield: {self.criteria.min_yield}-{self.criteria.max_yield}%, "
            f"Payout ≤{self.criteria.max_payout}%, "
            f"Años ≥{self.criteria.min_years}, "
            f"Quality ≥{self.criteria.min_quality}"
        )
