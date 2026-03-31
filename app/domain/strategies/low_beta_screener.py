"""
Low Beta Screener - Filtrado de Acciones por Volatilidad

Implementa screening de acciones basado en:
- Volatilidad histórica máxima
- Beta máximo
- Riesgo downside
- Sortino ratio mínimo
- Máximo drawdown tolerado
- Sectores defensivos
- Scores de baja volatilidad

SOLID Principles:
- Single Responsibility: Solo se encarga de screening
- Open/Closed: Extensible con nuevos filtros
- Dependency Inversion: Depende de abstracciones (models)
"""

from __future__ import annotations

import logging
import time
from decimal import Decimal
from typing import ClassVar, Optional

from .models import (
    LowVolatilityProfile,
    LowVolatilityScreeningCriteria,
    LowVolatilityScreeningResult,
    LowVolatilityStockResult,
    LowVolatilityStrategyConfig,
    SectorDefensiveLevel,
    VolatilityMetrics,
)

logger = logging.getLogger(__name__)


class LowBetaScreener:
    """
    Screener de acciones de baja volatilidad.

    Filtra universo de acciones basado en criterios de volatilidad
    y características defensivas para identificar candidatos de inversión.

    Attributes:
        config: Configuración de la estrategia de baja volatilidad
    """

    # Mapping de sectores a nivel defensivo
    SECTOR_DEFENSIVE_LEVELS: ClassVar[dict[str, SectorDefensiveLevel]] = {
        "Utilities": SectorDefensiveLevel.HIGHLY_DEFENSIVE,
        "Consumer Staples": SectorDefensiveLevel.HIGHLY_DEFENSIVE,
        "Healthcare": SectorDefensiveLevel.DEFENSIVE,
        "Real Estate": SectorDefensiveLevel.DEFENSIVE,
        "Telecommunication Services": SectorDefensiveLevel.DEFENSIVE,
        "Finance": SectorDefensiveLevel.NEUTRAL,
        "Industrials": SectorDefensiveLevel.NEUTRAL,
        "Consumer Discretionary": SectorDefensiveLevel.CYCLICAL,
        "Information Technology": SectorDefensiveLevel.CYCLICAL,
        "Technology": SectorDefensiveLevel.CYCLICAL,  # Added for compatibility
        "Materials": SectorDefensiveLevel.HIGHLY_CYCLICAL,
        "Energy": SectorDefensiveLevel.HIGHLY_CYCLICAL,
        "Biotechnology": SectorDefensiveLevel.CYCLICAL,  # Added for compatibility
    }

    def __init__(self, config: LowVolatilityStrategyConfig):
        """
        Inicializar screener.

        Args:
            config: Configuración de la estrategia
        """
        self.config = config
        self.criteria = self._create_screening_criteria()

    def _create_screening_criteria(self) -> LowVolatilityScreeningCriteria:
        """
        Crear criterios de screening desde config.

        Returns:
            Criterios de screening normalizados
        """
        return LowVolatilityScreeningCriteria(
            max_volatility=self.config.max_historical_volatility,
            max_beta=self.config.max_beta,
            min_beta=self.config.min_beta,
            max_downside_risk=self.config.max_downside_risk,
            min_sortino=self.config.min_sortino_ratio,
            max_drawdown=self.config.max_max_drawdown,
            min_low_vol_score=self.config.min_low_vol_score,
            min_defensive_score=self.config.min_defensive_score,
            min_stability_score=self.config.min_stability_score,
            preferred_sectors=self.config.preferred_sectors,
            avoid_sectors=self.config.avoid_sectors,
            require_defensive=self.config.require_defensive_sector,
            min_market_cap=self.config.min_market_cap,
        )

    def screen(
        self,
        profiles: list[LowVolatilityProfile],
    ) -> LowVolatilityScreeningResult:
        """
        Aplicar screening a lista de perfiles.

        Args:
            profiles: Lista de perfiles de acciones a evaluar

        Returns:
            Resultado del screening con acciones aprobadas y rechazadas
        """
        start_time = time.time()

        passed: list[LowVolatilityStockResult] = []
        failed: dict[str, list[str]] = {}
        total_evaluated = len(profiles)

        logger.info(
            f"Iniciando screening de baja volatilidad: {total_evaluated} acciones "
            f"con criterios: {self._get_criteria_description()}"
        )

        for profile in profiles:
            failure_reasons = self._evaluate_profile(profile)

            if not failure_reasons:
                # Crear LowVolatilityStockResult con score inicial
                stock = self._create_low_vol_stock(profile)
                passed.append(stock)
            else:
                failed[profile.symbol] = failure_reasons

        elapsed_ms = (time.time() - start_time) * 1000

        result = LowVolatilityScreeningResult(
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

    @staticmethod
    def _get_metrics(profile: LowVolatilityProfile) -> VolatilityMetrics:
        """
        Obtener las metricas de volatilidad de un perfil, garantizando que no sean None.

        Args:
            profile: Perfil de accion

        Returns:
            VolatilityMetrics del perfil (siempre inicializadas)
        """
        if profile.volatility_metrics is not None:
            return profile.volatility_metrics
        # Fallback: construir metricas desde campos del perfil
        return VolatilityMetrics(
            symbol=profile.symbol,
            average_volatility=profile.daily_volatility,
            annualized_volatility=profile.annualized_volatility,
            beta=profile.beta,
            downside_risk=profile.downside_deviation,
            max_drawdown=profile.max_drawdown,
            sortino_ratio=profile.sortino_ratio,
        )

    def _evaluate_profile(self, profile: LowVolatilityProfile) -> list[str]:
        """
        Evaluar si un perfil pasa todos los filtros.

        Args:
            profile: Perfil de acción a evaluar

        Returns:
            Lista de razones por las que falló (vacía si pasó)
        """
        failures: list[str] = []
        metrics = self._get_metrics(profile)

        # 1. Volatilidad histórica check
        avg_vol = metrics.average_volatility
        if avg_vol is not None and avg_vol > self.criteria.max_volatility:
            failures.append(
                f"Volatilidad muy alta: {avg_vol:.2f}% > {self.criteria.max_volatility}%"
            )

        # 2. Beta check
        beta = metrics.beta
        if beta is not None:
            if beta > self.criteria.max_beta:
                failures.append(f"Beta muy alto: {beta:.2f} > {self.criteria.max_beta}")
            if self.criteria.min_beta is not None and beta < self.criteria.min_beta:
                failures.append(f"Beta muy bajo: {beta:.2f} < {self.criteria.min_beta}")

        # 3. Downside risk check
        if self.criteria.max_downside_risk is not None:
            downside = metrics.downside_risk
            if downside is not None and downside > self.criteria.max_downside_risk:
                failures.append(
                    f"Riesgo downside alto: {downside:.2f}% > {self.criteria.max_downside_risk}%"
                )

        # 4. Sortino ratio check
        if self.criteria.min_sortino is not None:
            sortino = metrics.sortino_ratio
            if sortino is not None and sortino < self.criteria.min_sortino:
                failures.append(f"Sortino ratio bajo: {sortino:.2f} < {self.criteria.min_sortino}")

        # 5. Maximum drawdown check
        if self.criteria.max_drawdown is not None:
            max_dd = metrics.max_drawdown
            if max_dd is not None and max_dd < self.criteria.max_drawdown:
                failures.append(
                    f"Max drawdown excedido: {max_dd:.2f}% < {self.criteria.max_drawdown}%"
                )

        # 6. Low vol score check
        if (
            profile.low_vol_score is not None
            and profile.low_vol_score < self.criteria.min_low_vol_score
        ):
            failures.append(
                f"Low vol score bajo: {profile.low_vol_score:.1f} < {self.criteria.min_low_vol_score}"
            )

        # 7. Defensive score check
        if (
            profile.defensive_score is not None
            and profile.defensive_score < self.criteria.min_defensive_score
        ):
            failures.append(
                f"Defensive score bajo: {profile.defensive_score:.1f} < {self.criteria.min_defensive_score}"
            )

        # 8. Stability score check
        if (
            profile.stability_score is not None
            and profile.stability_score < self.criteria.min_stability_score
        ):
            failures.append(
                f"Stability score bajo: {profile.stability_score:.1f} < {self.criteria.min_stability_score}"
            )

        # 9. Sector checks
        sector = profile.sector
        if sector:
            # Verificar sectores evitados
            if sector in self.criteria.avoid_sectors:
                failures.append(f"Sector evitado: {sector}")

            # Verificar sector defensivo requerido
            if self.criteria.require_defensive:
                defensive_level = self.SECTOR_DEFENSIVE_LEVELS.get(
                    sector, SectorDefensiveLevel.NEUTRAL
                )
                if defensive_level not in [
                    SectorDefensiveLevel.DEFENSIVE,
                    SectorDefensiveLevel.HIGHLY_DEFENSIVE,
                ]:
                    failures.append(f"Sector no defensivo: {sector}")

        # 10. Market cap check
        if (
            self.criteria.min_market_cap is not None
            and profile.market_cap is not None
            and profile.market_cap < self.criteria.min_market_cap
        ):
            failures.append(
                f"Market cap muy bajo: ${profile.market_cap:.0f}M < ${self.criteria.min_market_cap:.0f}M"
            )

        # 11. Valuation checks (optional)
        if (
            self.config.max_pe_ratio is not None
            and profile.pe_ratio is not None
            and profile.pe_ratio > self.config.max_pe_ratio
        ):
            failures.append(f"P/E muy alto: {profile.pe_ratio:.1f} > {self.config.max_pe_ratio}")

        if (
            self.config.max_pb_ratio is not None
            and profile.pb_ratio is not None
            and profile.pb_ratio > self.config.max_pb_ratio
        ):
            failures.append(f"P/B muy alto: {profile.pb_ratio:.1f} > {self.config.max_pb_ratio}")

        if (
            self.config.max_debt_to_equity is not None
            and profile.debt_to_equity is not None
            and profile.debt_to_equity > self.config.max_debt_to_equity
        ):
            failures.append(
                f"D/E muy alto: {profile.debt_to_equity:.1f} > {self.config.max_debt_to_equity}"
            )

        return failures

    def _create_low_vol_stock(self, profile: LowVolatilityProfile) -> LowVolatilityStockResult:
        """
        Crear LowVolatilityStockResult desde profile.

        Args:
            profile: Perfil de acción

        Returns:
            LowVolatilityStockResult con score de decisión
        """
        # Calcular score de decisión
        decision_score = self._calculate_decision_score(profile)
        decision_reason = self._get_decision_reason(profile)
        recommendation = self._get_recommendation(decision_score)

        return LowVolatilityStockResult(
            profile=profile,
            decision_score=decision_score,
            decision_reason=decision_reason,
            recommendation=recommendation,
        )

    def _calculate_decision_score(self, profile: LowVolatilityProfile) -> Decimal:
        """
        Calcular score de decisión basado en pesos de configuración.

        Args:
            profile: Perfil de acción

        Returns:
            Score entre 0 y 100
        """
        scores = {
            "volatility": self._score_volatility(profile),
            "defensive": self._score_defensive(profile),
            "stability": self._score_stability(profile),
            "quality": self._score_quality(profile),
        }

        # Pesos desde config
        weights = {
            "volatility": float(self.config.volatility_weight),
            "defensive": float(self.config.defensive_weight),
            "stability": float(self.config.stability_weight),
            "quality": float(self.config.quality_weight),
        }

        weighted_score = sum(scores[k] * weights[k] for k in scores)

        return min(Decimal("100"), max(Decimal("0"), Decimal(str(weighted_score))))

    def _score_volatility(self, profile: LowVolatilityProfile) -> float:
        """
        Puntuar volatilidad (menor es mejor).

        Args:
            profile: Perfil de acción

        Returns:
            Score 0-100
        """
        metrics = self._get_metrics(profile)
        vol_score = float(metrics.volatility_score)

        # Ajustar por beta
        beta = float(metrics.beta or Decimal("1.0"))
        beta_adjustment = max(0, 100 - beta * 50)

        # Promedio
        return vol_score * 0.7 + beta_adjustment * 0.3

    def _score_defensive(self, profile: LowVolatilityProfile) -> float:
        """
        Puntuar característica defensiva.

        Args:
            profile: Perfil de acción

        Returns:
            Score 0-100
        """
        score = 50.0  # Base score
        metrics = self._get_metrics(profile)

        # Nivel defensivo del sector
        if profile.sector_defensive_level:
            level_scores = {
                SectorDefensiveLevel.HIGHLY_DEFENSIVE: 100,
                SectorDefensiveLevel.DEFENSIVE: 85,
                SectorDefensiveLevel.NEUTRAL: 50,
                SectorDefensiveLevel.CYCLICAL: 25,
                SectorDefensiveLevel.HIGHLY_CYCLICAL: 10,
            }
            score = level_scores.get(profile.sector_defensive_level, 50)

        # Ajustar por correlación con el mercado
        corr = metrics.correlation_to_market
        if corr is not None:
            corr_float = float(corr)
            # Menor correlación = más defensivo
            if corr_float < 0.5:
                score += 15
            elif corr_float < 0.7:
                score += 5
            elif corr_float > 0.9:
                score -= 10

        return max(0.0, min(100.0, score))

    def _score_stability(self, profile: LowVolatilityProfile) -> float:
        """
        Puntuar estabilidad.

        Args:
            profile: Perfil de acción

        Returns:
            Score 0-100
        """
        score = 50.0
        metrics = self._get_metrics(profile)

        # Máximo drawdown (menor es mejor)
        max_dd = metrics.max_drawdown
        if max_dd is not None:
            dd_float = float(max_dd)
            if dd_float > -10:
                score += 20
            elif dd_float > -20:
                score += 10
            elif dd_float < -40:
                score -= 20

        # Sharpe ratio (mayor es mejor)
        sharpe = metrics.sharpe_ratio
        if sharpe is not None:
            sharpe_float = float(sharpe)
            if sharpe_float > 1.5:
                score += 20
            elif sharpe_float > 1.0:
                score += 10
            elif sharpe_float < 0:
                score -= 20

        # Sortino ratio
        sortino = metrics.sortino_ratio
        if sortino is not None:
            sortino_float = float(sortino)
            if sortino_float > 2.0:
                score += 10
            elif sortino_float > 1.0:
                score += 5

        return max(0.0, min(100.0, score))

    def _score_quality(self, profile: LowVolatilityProfile) -> float:
        """
        Puntuar calidad fundamental.

        Args:
            profile: Perfil de acción

        Returns:
            Score 0-100
        """
        score = 50.0

        # ROE (mayor es mejor)
        if profile.roe is not None:
            roe_float = float(profile.roe)
            if roe_float >= 20:
                score += 20
            elif roe_float >= 15:
                score += 15
            elif roe_float >= 10:
                score += 10
            elif roe_float < 0:
                score -= 20

        # Debt to Equity (menor es mejor)
        if profile.debt_to_equity is not None:
            d_e_float = float(profile.debt_to_equity)
            if d_e_float < 50:
                score += 15
            elif d_e_float < 100:
                score += 5
            elif d_e_float > 200:
                score -= 20

        # P/E ratio
        if profile.pe_ratio is not None:
            pe_float = float(profile.pe_ratio)
            if 10 <= pe_float <= 20:
                score += 10
            elif pe_float < 10:
                score += 15
            elif pe_float > 30:
                score -= 10

        return max(0.0, min(100.0, score))

    def _get_decision_reason(self, profile: LowVolatilityProfile) -> str:
        """
        Obtener razón de la decisión.

        Args:
            profile: Perfil de acción

        Returns:
            Razón descriptiva
        """
        metrics = self._get_metrics(profile)
        vol = float(metrics.average_volatility)
        beta = float(metrics.beta)

        reason_parts = []

        if vol < 15:
            reason_parts.append("volatilidad muy baja")
        elif vol < 20:
            reason_parts.append("volatilidad baja")

        if beta < 0.5:
            reason_parts.append("beta muy bajo")
        elif beta < 0.7:
            reason_parts.append("beta bajo")

        if profile.sector_defensive_level in [
            SectorDefensiveLevel.DEFENSIVE,
            SectorDefensiveLevel.HIGHLY_DEFENSIVE,
        ]:
            reason_parts.append("sector defensivo")

        if reason_parts:
            return f"Paso screening: {', '.join(reason_parts)}"
        else:
            return "Paso screening de baja volatilidad"

    def _get_recommendation(self, score: Decimal) -> str:
        """
        Obtener recomendación basada en score.

        Args:
            score: Score de decisión

        Returns:
            Recomendación: buy/hold/avoid
        """
        if score >= 70:
            return "buy"
        elif score >= 50:
            return "hold"
        else:
            return "avoid"

    def _get_criteria_description(self) -> str:
        """Obtener descripción de criterios de screening."""
        return (
            f"Vol ≤{self.criteria.max_volatility}%, "
            f"Beta ≤{self.criteria.max_beta}, "
            f"Low Vol Score ≥{self.criteria.min_low_vol_score}"
        )

    def get_sector_defensive_level(self, sector: Optional[str]) -> SectorDefensiveLevel:
        """
        Obtener nivel defensivo de un sector.

        Args:
            sector: Nombre del sector

        Returns:
            Nivel defensivo del sector
        """
        if sector is None:
            return SectorDefensiveLevel.NEUTRAL

        return self.SECTOR_DEFENSIVE_LEVELS.get(sector, SectorDefensiveLevel.NEUTRAL)
