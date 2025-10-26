"""
Portfolio Risk Manager - TASK-15: Refactorización de Servicios

Este módulo implementa el gestor de riesgos del portafolio, separando la lógica
de gestión de riesgo de los servicios de portafolio.
"""

import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.centralized_config import get_config
from app.models.portfolio import Portfolio, Position

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
    CORRELATION = "correlation"
    DAILY_LOSS = "daily_loss"
    DRAWDOWN = "drawdown"
    VOLATILITY = "volatility"


class PortfolioRiskManager:
    """
    Gestor de riesgos del portafolio.

    Responsabilidades:
    - Monitorear límites de riesgo
    - Detectar violaciones
    - Calcular métricas de riesgo
    - Proporcionar alertas
    """

    def __init__(self):
        """Inicializar gestor de riesgos."""
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

        # Calcular métricas de riesgo
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

    def _calculate_risk_metrics(
        self, portfolio: Portfolio, new_position: Optional[Position]
    ) -> Dict[str, Any]:
        """Calcular métricas de riesgo."""
        # Calcular exposición total
        total_exposure = self._calculate_total_exposure(portfolio, new_position)

        # Calcular exposición por sector
        sector_exposures = self._calculate_sector_exposures(portfolio, new_position)

        # Calcular correlaciones
        correlations = self._calculate_correlations(portfolio, new_position)

        # Calcular pérdidas diarias
        daily_loss = self._calculate_daily_loss(portfolio)

        # Calcular drawdown
        drawdown = self._calculate_drawdown(portfolio)

        # Calcular volatilidad del portafolio
        portfolio_volatility = self._calculate_portfolio_volatility(portfolio)

        return {
            "total_exposure": total_exposure,
            "sector_exposures": sector_exposures,
            "correlations": correlations,
            "daily_loss": daily_loss,
            "drawdown": drawdown,
            "portfolio_volatility": portfolio_volatility,
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

    def _calculate_correlations(
        self, portfolio: Portfolio, new_position: Optional[Position]
    ) -> Dict[str, float]:
        """Calcular correlaciones entre posiciones."""
        # Implementación simplificada
        correlations = {}

        positions = list(portfolio.positions)
        if new_position:
            positions.append(new_position)

        # Calcular correlaciones por pares
        for i, pos1 in enumerate(positions):
            for j, pos2 in enumerate(positions[i + 1 :], i + 1):
                pair = f"{pos1.symbol}-{pos2.symbol}"
                # Correlación simulada basada en sector
                correlation = (
                    0.3 if getattr(pos1, "sector", "") == getattr(pos2, "sector", "") else 0.1
                )
                correlations[pair] = correlation

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
