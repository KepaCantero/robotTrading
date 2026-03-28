"""
Portfolio Risk Manager - TASK-15: Refactorización de Servicios

Este módulo implementa el gestor de riesgos del portafolio, separando la lógica
de gestión de riesgo de los servicios de portafolio.
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from app.domain.models.portfolio import Portfolio, Position
from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Niveles de riesgo."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskViolation(str, Enum):
    """Tipos de violaciones de riesgo."""

    POSITION_SIZE = "position_size"
    TOTAL_EXPOSURE = "total_exposure"
    SECTOR_EXPOSURE = "sector_exposure"
    SECTOR_CONCENTRATION = "sector_concentration"  # [TASK-5.6]
    COUNTRY_EXPOSURE = "country_exposure"  # [TASK-5.6]
    COUNTRY_CONCENTRATION = "country_concentration"  # [TASK-5.6]
    CORRELATION = "correlation"
    DAILY_LOSS = "daily_loss"
    DRAWDOWN = "drawdown"
    VOLATILITY = "volatility"
    UNHEDGED_FX_EXPOSURE = "unhedged_fx_exposure"  # [TASK-5.5]
    EXCESSIVE_FX_CONCENTRATION = "excessive_fx_concentration"  # [TASK-5.5]


class PortfolioRiskManager:
    """
    Gestor de riesgos del portafolio.

    Responsabilidades:
    - Monitorear límites de riesgo
    - Detectar violaciones
    - Calcular métricas de riesgo
    - Proporcionar alertas
    """

    def __init__(self, correlation_analyzer=None):
        """
        Inicializar gestor de riesgos.

        Args:
            correlation_analyzer: Optional CorrelationAnalyzer instance for real correlation
        """
        self.config = get_config().trading

        # Límites de riesgo
        self.max_position_size = self.config.max_position_size
        self.max_total_exposure = self.config.max_total_exposure
        self.max_sector_exposure = self.config.max_sector_exposure
        self.max_correlation = self.config.max_correlation
        self.daily_loss_limit = self.config.daily_loss_limit
        self.max_drawdown_limit = self.config.max_drawdown_limit

        # Circuit breaker thresholds
        self.circuit_breaker_daily_loss = self.config.circuit_breaker_daily_loss
        self.circuit_breaker_drawdown = self.config.circuit_breaker_drawdown
        self.circuit_breaker_volatility = self.config.circuit_breaker_volatility

        # Métricas de riesgo
        self.risk_checks_performed = 0
        self.risk_violations_detected = 0
        self.risk_alerts_sent = 0

        # Historial de violaciones
        self.violation_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000

        # Estado actual de riesgo
        self.current_risk_level = RiskLevel.LOW
        self.last_risk_assessment = datetime.utcnow()

        # Real-time correlation analyzer (Phase 2.4)
        self.correlation_analyzer = correlation_analyzer
        self._correlation_cache: Optional[Any] = None
        self._correlation_cache_time: Optional[datetime] = None
        self._correlation_cache_ttl = 3600  # 1 hour cache

    def assess_portfolio_risk(
        self, portfolio: Portfolio, new_position: Optional[Position] = None
    ) -> Dict[str, Any]:
        """
        Evaluar riesgo del portafolio.

        Args:
            portfolio: Portafolio a evaluar
            new_position: Nueva posición a considerar

        Returns:
            Evaluación completa de riesgo
        """
        self.risk_checks_performed += 1

        # Try to use async correlation if available and not in async context
        try:
            asyncio.get_running_loop()
            # We're in an async context, use synchronous fallback
            risk_metrics = self._calculate_risk_metrics(portfolio, new_position)
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            try:
                risk_metrics = asyncio.run(
                    self._calculate_risk_metrics_async(portfolio, new_position)
                )
            except RuntimeError:
                # Fallback to sync if async fails
                risk_metrics = self._calculate_risk_metrics(portfolio, new_position)

        # Detectar violaciones
        violations = self._detect_risk_violations(risk_metrics)

        # Determinar nivel de riesgo
        risk_level = self._determine_risk_level(violations, risk_metrics)

        # Generar recomendaciones
        recommendations = self._generate_recommendations(violations, risk_metrics)

        # Crear evaluación
        risk_assessment = {
            "portfolio_id": portfolio.portfolio_id,
            "risk_level": risk_level,
            "risk_metrics": risk_metrics,
            "violations": violations,
            "recommendations": recommendations,
            "assessment_time": datetime.utcnow(),
            "new_position": new_position.symbol if new_position else None,
        }

        # Actualizar estado
        self.current_risk_level = risk_level
        self.last_risk_assessment = datetime.utcnow()

        # Registrar violaciones
        if violations:
            self._record_violations(violations, risk_assessment)

        logger.debug(f"Portfolio risk assessment: {risk_assessment}")
        return risk_assessment

    async def _calculate_risk_metrics_async(
        self, portfolio: Portfolio, new_position: Optional[Position]
    ) -> Dict[str, Any]:
        """Calcular métricas de riesgo (async version for correlation)."""
        # Calcular exposición total
        total_exposure = self._calculate_total_exposure(portfolio, new_position)

        # Calcular exposición por sector
        sector_exposures = self._calculate_sector_exposures(portfolio, new_position)

        # Calcular correlaciones (async - uses real correlation matrix)
        correlations = await self._calculate_correlations_async(portfolio, new_position)

        # Calcular pérdidas diarias
        daily_loss = self._calculate_daily_loss(portfolio)

        # Calcular drawdown
        drawdown = self._calculate_drawdown(portfolio)

        # Calcular volatilidad del portafolio
        portfolio_volatility = self._calculate_portfolio_volatility(portfolio)

        # Calcular exposición de moneda extranjera [TASK-5.5]
        currency_exposures = self._calculate_currency_exposure(portfolio, new_position)

        return {
            "total_exposure": total_exposure,
            "sector_exposures": sector_exposures,
            "correlations": correlations,
            "daily_loss": daily_loss,
            "drawdown": drawdown,
            "portfolio_volatility": portfolio_volatility,
            "currency_exposures": currency_exposures,
            "position_count": len(portfolio.positions) + (1 if new_position else 0),
        }

    def _calculate_risk_metrics(
        self, portfolio: Portfolio, new_position: Optional[Position]
    ) -> Dict[str, Any]:
        """Calcular métricas de riesgo (synchronous fallback)."""
        # Calcular exposición total
        total_exposure = self._calculate_total_exposure(portfolio, new_position)

        # Calcular exposición por sector
        sector_exposures = self._calculate_sector_exposures(portfolio, new_position)

        # Calcular correlaciones (synchronous fallback)
        correlations = self._calculate_correlations(portfolio, new_position)

        # Calcular pérdidas diarias
        daily_loss = self._calculate_daily_loss(portfolio)

        # Calcular drawdown
        drawdown = self._calculate_drawdown(portfolio)

        # Calcular volatilidad del portafolio
        portfolio_volatility = self._calculate_portfolio_volatility(portfolio)

        # Calcular exposición de moneda extranjera [TASK-5.5]
        currency_exposures = self._calculate_currency_exposure(portfolio, new_position)

        return {
            "total_exposure": total_exposure,
            "sector_exposures": sector_exposures,
            "correlations": correlations,
            "daily_loss": daily_loss,
            "drawdown": drawdown,
            "portfolio_volatility": portfolio_volatility,
            "currency_exposures": currency_exposures,
            "position_count": len(portfolio.positions) + (1 if new_position else 0),
        }

    def _detect_risk_violations(self, risk_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detectar violaciones de riesgo."""
        violations = []

        # Verificar exposición total
        if risk_metrics["total_exposure"] > self.max_total_exposure:
            violations.append(
                {
                    "type": RiskViolation.TOTAL_EXPOSURE,
                    "current_value": risk_metrics["total_exposure"],
                    "limit": self.max_total_exposure,
                    "severity": "high",
                }
            )

        # Verificar exposición por sector
        for sector, exposure in risk_metrics["sector_exposures"].items():
            if exposure > self.max_sector_exposure:
                violations.append(
                    {
                        "type": RiskViolation.SECTOR_EXPOSURE,
                        "sector": sector,
                        "current_value": exposure,
                        "limit": self.max_sector_exposure,
                        "severity": "medium",
                    }
                )

        # Verificar correlaciones altas
        for pair, correlation in risk_metrics["correlations"].items():
            if abs(correlation) > self.max_correlation:
                violations.append(
                    {
                        "type": RiskViolation.CORRELATION,
                        "pair": pair,
                        "current_value": abs(correlation),
                        "limit": self.max_correlation,
                        "severity": "medium",
                    }
                )

        # Verificar pérdida diaria
        if risk_metrics["daily_loss"] > self.daily_loss_limit:
            violations.append(
                {
                    "type": RiskViolation.DAILY_LOSS,
                    "current_value": risk_metrics["daily_loss"],
                    "limit": self.daily_loss_limit,
                    "severity": "critical",
                }
            )

        # Verificar drawdown
        if risk_metrics["drawdown"] > self.max_drawdown_limit:
            violations.append(
                {
                    "type": RiskViolation.DRAWDOWN,
                    "current_value": risk_metrics["drawdown"],
                    "limit": self.max_drawdown_limit,
                    "severity": "critical",
                }
            )

        # Verificar exposición de moneda extranjera [TASK-5.5]
        if "currency_exposures" in risk_metrics:
            fx_violations = self._detect_fx_violations(risk_metrics["currency_exposures"])
            violations.extend(fx_violations)

        return violations

    def _determine_risk_level(
        self, violations: List[Dict[str, Any]], risk_metrics: Dict[str, Any]
    ) -> RiskLevel:
        """Determinar nivel de riesgo."""
        if not violations:
            return RiskLevel.LOW

        # Contar violaciones por severidad
        critical_violations = sum(1 for v in violations if v["severity"] == "critical")
        high_violations = sum(1 for v in violations if v["severity"] == "high")
        medium_violations = sum(1 for v in violations if v["severity"] == "medium")

        if critical_violations > 0:
            return RiskLevel.CRITICAL
        elif high_violations > 0 or medium_violations > 2:
            return RiskLevel.HIGH
        elif medium_violations > 0:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _generate_recommendations(
        self, violations: List[Dict[str, Any]], risk_metrics: Dict[str, Any]
    ) -> List[str]:
        """Generar recomendaciones de riesgo."""
        recommendations = []

        for violation in violations:
            if violation["type"] == RiskViolation.TOTAL_EXPOSURE:
                recommendations.append(
                    f"Reduce total exposure from {violation['current_value']:.2%} "
                    f"to below {violation['limit']:.2%}"
                )
            elif violation["type"] == RiskViolation.SECTOR_EXPOSURE:
                recommendations.append(
                    f"Reduce {violation['sector']} sector exposure from "
                    f"{violation['current_value']:.2%} to below {violation['limit']:.2%}"
                )
            elif violation["type"] == RiskViolation.CORRELATION:
                recommendations.append(
                    f"Reduce correlation between {violation['pair']} from "
                    f"{violation['current_value']:.2f} to below {violation['limit']:.2f}"
                )
            elif violation["type"] == RiskViolation.DAILY_LOSS:
                recommendations.append(
                    f"Stop trading - daily loss {violation['current_value']:.2%} "
                    f"exceeds limit {violation['limit']:.2%}"
                )
            elif violation["type"] == RiskViolation.DRAWDOWN:
                recommendations.append(
                    f"Reduce positions - drawdown {violation['current_value']:.2%} "
                    f"exceeds limit {violation['limit']:.2%}"
                )

        return recommendations

    def _calculate_total_exposure(
        self, portfolio: Portfolio, new_position: Optional[Position]
    ) -> Decimal:
        """Calcular exposición total."""
        total_exposure = Decimal("0")

        for position in portfolio.positions:
            total_exposure += position.market_value

        if new_position:
            total_exposure += new_position.market_value

        # Normalizar por capital total
        total_capital = portfolio.total_value
        return total_exposure / total_capital if total_capital > 0 else Decimal("0")

    def _calculate_sector_exposures(
        self, portfolio: Portfolio, new_position: Optional[Position]
    ) -> Dict[str, Decimal]:
        """Calcular exposición por sector."""
        sector_exposures = {}

        for position in portfolio.positions:
            sector = getattr(position, "sector", "unknown")
            if sector not in sector_exposures:
                sector_exposures[sector] = Decimal("0")
            sector_exposures[sector] += position.market_value

        if new_position:
            sector = getattr(new_position, "sector", "unknown")
            if sector not in sector_exposures:
                sector_exposures[sector] = Decimal("0")
            sector_exposures[sector] += new_position.market_value

        # Normalizar por capital total
        total_capital = portfolio.total_value
        if total_capital > 0:
            for sector in sector_exposures:
                sector_exposures[sector] = sector_exposures[sector] / total_capital

        return sector_exposures

    async def _calculate_correlations_async(
        self, portfolio: Portfolio, new_position: Optional[Position]
    ) -> Dict[str, float]:
        """
        Calcular correlaciones entre posiciones usando real-time correlation matrix.

        Phase 2.4: Uses CorrelationAnalyzer for real correlation from historical prices.
        Falls back to simulated correlation if analyzer not available or data unavailable.
        """
        correlations = {}

        positions = list(portfolio.positions)
        if new_position:
            positions.append(new_position)

        if not positions:
            return correlations

        # Try to use real-time correlation analyzer
        if self.correlation_analyzer:
            try:
                # Check if we have a valid cache
                cache_valid = (
                    self._correlation_cache is not None
                    and self._correlation_cache_time is not None
                    and (datetime.utcnow() - self._correlation_cache_time).total_seconds()
                    < self._correlation_cache_ttl
                )

                if not cache_valid:
                    # Get list of symbols
                    symbols = [pos.symbol for pos in positions]

                    # Calculate correlation matrix
                    correlation_matrix = (
                        await self.correlation_analyzer.calculate_correlation_matrix(symbols)
                    )

                    # Update cache
                    self._correlation_cache = correlation_matrix
                    self._correlation_cache_time = datetime.utcnow()

                # Extract pairwise correlations from cached matrix
                if self._correlation_cache is not None:
                    for i, pos1 in enumerate(positions):
                        for _j, pos2 in enumerate(positions[i + 1 :], i + 1):
                            pair = f"{pos1.symbol}-{pos2.symbol}"
                            try:
                                # Get correlation from matrix
                                correlation = float(
                                    self._correlation_cache.loc[pos1.symbol, pos2.symbol]
                                )
                                correlations[pair] = correlation
                            except (KeyError, ValueError):
                                # Fallback to simulated correlation if not found
                                correlations[pair] = self._get_fallback_correlation(pos1, pos2)

                    logger.debug(f"Calculated {len(correlations)} real correlations")
                    return correlations

            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.warning(f"Error using correlation analyzer: {e}, falling back")

        # Fallback to simulated correlation
        for i, pos1 in enumerate(positions):
            for _j, pos2 in enumerate(positions[i + 1 :], i + 1):
                pair = f"{pos1.symbol}-{pos2.symbol}"
                correlations[pair] = self._get_fallback_correlation(pos1, pos2)

        return correlations

    def _get_fallback_correlation(self, pos1: Position, pos2: Position) -> float:
        """
        Get fallback correlation based on sector.

        Args:
            pos1: First position
            pos2: Second position

        Returns:
            Simulated correlation value
        """
        sector1 = getattr(pos1, "sector", "")
        sector2 = getattr(pos2, "sector", "")

        # Same sector: higher correlation
        if sector1 and sector2 and sector1 == sector2:
            return 0.5

        # Same market (US): moderate correlation
        market1 = getattr(pos1, "market", "US")
        market2 = getattr(pos2, "market", "US")
        if market1 == market2:
            return 0.3

        # Different: low correlation
        return 0.1

    def _calculate_correlations(
        self, portfolio: Portfolio, new_position: Optional[Position]
    ) -> Dict[str, float]:
        """Calcular correlaciones entre posiciones (synchronous fallback)."""
        correlations = {}

        positions = list(portfolio.positions)
        if new_position:
            positions.append(new_position)

        # Calcular correlaciones por pares
        for i, pos1 in enumerate(positions):
            for _j, pos2 in enumerate(positions[i + 1 :], i + 1):
                pair = f"{pos1.symbol}-{pos2.symbol}"
                # Use fallback correlation
                correlations[pair] = self._get_fallback_correlation(pos1, pos2)

        return correlations

    def _calculate_daily_loss(self, portfolio: Portfolio) -> Decimal:
        """Calcular pérdida diaria."""
        # Implementación simplificada
        return Decimal("0.02")  # 2% de pérdida diaria simulada

    def _calculate_drawdown(self, portfolio: Portfolio) -> Decimal:
        """Calcular drawdown."""
        # Implementación simplificada
        return Decimal("0.05")  # 5% de drawdown simulado

    def _calculate_portfolio_volatility(self, portfolio: Portfolio) -> Decimal:
        """Calcular volatilidad del portafolio."""
        # Implementación simplificada
        return Decimal("0.15")  # 15% de volatilidad simulada

    def _record_violations(
        self, violations: List[Dict[str, Any]], risk_assessment: Dict[str, Any]
    ) -> None:
        """Registrar violaciones en historial."""
        self.risk_violations_detected += len(violations)

        violation_record = {
            "violations": violations,
            "risk_level": risk_assessment["risk_level"],
            "timestamp": datetime.utcnow(),
            "portfolio_id": risk_assessment["portfolio_id"],
        }

        self.violation_history.append(violation_record)

        # Mantener tamaño máximo del historial
        if len(self.violation_history) > self.max_history_size:
            self.violation_history = self.violation_history[-self.max_history_size :]

    def get_risk_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de riesgo."""
        return {
            "risk_checks_performed": self.risk_checks_performed,
            "risk_violations_detected": self.risk_violations_detected,
            "risk_alerts_sent": self.risk_alerts_sent,
            "current_risk_level": self.current_risk_level.value,
            "last_risk_assessment": self.last_risk_assessment,
            "violation_history_size": len(self.violation_history),
            "max_position_size": self.max_position_size,
            "max_total_exposure": self.max_total_exposure,
            "max_sector_exposure": self.max_sector_exposure,
            "max_correlation": self.max_correlation,
            "daily_loss_limit": self.daily_loss_limit,
            "max_drawdown_limit": self.max_drawdown_limit,
        }

    def _calculate_currency_exposure(
        self, portfolio: Portfolio, new_position: Optional[Position]
    ) -> Dict[str, Any]:
        """
        Calcular exposición de moneda extranjera [TASK-5.5].

        Returns:
            Dict with currency exposures and totals
        """
        base_currency = portfolio.currency or "USD"
        exposure_by_currency: Dict[str, Decimal] = {}
        total_unhedged = Decimal("0")
        total_portfolio_value = portfolio.total_equity

        # Aggregate positions by currency
        positions_to_check = portfolio.positions.copy()
        if new_position:
            positions_to_check.append(new_position)

        for position in positions_to_check:
            # Skip base currency and hedge positions
            if position.currency == base_currency or position.hedging.is_hedge:
                continue

            position_value = position.market_value
            if position.currency not in exposure_by_currency:
                exposure_by_currency[position.currency] = Decimal("0")

            exposure_by_currency[position.currency] += position_value
            total_unhedged += position_value

        # Calculate percentages
        portfolio_pct = (
            (total_unhedged / total_portfolio_value * 100)
            if total_portfolio_value > 0
            else Decimal("0")
        )

        return {
            "by_currency": exposure_by_currency,
            "total_unhedged": total_unhedged,
            "total_portfolio_pct": portfolio_pct,
        }

    def _detect_fx_violations(self, currency_exposures: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detectar violaciones de exposición a moneda extranjera [TASK-5.5].

        Args:
            currency_exposures: Currency exposure metrics from _calculate_currency_exposure

        Returns:
            List of FX-related violations
        """
        violations = []

        # Get thresholds from config
        try:
            hedging_config = self.config.currency_hedging
            hedging_config.single_currency_max
            total_fx_max = hedging_config.total_fx_max
        except (AttributeError, KeyError):
            # Fallback defaults
            total_fx_max = 0.50

        by_currency = currency_exposures.get("by_currency", {})
        total_unhedged_pct = currency_exposures.get("total_portfolio_pct", Decimal("0"))

        # Check total unhedged FX exposure
        if total_unhedged_pct > Decimal(str(total_fx_max * 100)):
            violations.append(
                {
                    "type": RiskViolation.EXCESSIVE_FX_CONCENTRATION,
                    "current_value": float(total_unhedged_pct),
                    "limit": float(Decimal(str(total_fx_max)) * 100),
                    "severity": "high",
                    "description": f"Total unhedged FX exposure {total_unhedged_pct:.1f}% exceeds limit",
                }
            )

        # Check individual currency exposures
        for currency, amount in by_currency.items():
            # This would need portfolio total value for percentage calculation
            # For now, log at medium severity if above threshold
            violations.append(
                {
                    "type": RiskViolation.UNHEDGED_FX_EXPOSURE,
                    "currency": currency,
                    "current_value": float(amount),
                    "severity": "medium",
                    "description": f"Unhedged {currency} exposure of {amount:,.0f}",
                }
            )

        return violations

    def get_recent_violations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener violaciones recientes."""
        return self.violation_history[-limit:] if self.violation_history else []

    def clear_history(self) -> None:
        """Limpiar historial de violaciones."""
        self.violation_history.clear()
        logger.info("Cleared risk violation history")

    def reset_statistics(self) -> None:
        """Resetear estadísticas de riesgo."""
        self.risk_checks_performed = 0
        self.risk_violations_detected = 0
        self.risk_alerts_sent = 0
        self.current_risk_level = RiskLevel.LOW
        logger.info("Reset risk statistics")
