"""
Backtesting Compliance Module - Reglas R5, R6, R7, DATA-001

Este módulo implementa las validaciones específicas de backtesting según
las reglas definidas en .ralph/rules/rules_mapping.yml:

- R5: Walk-Forward Analysis - Validación con ventanas temporales
- R6: Overfitting Prevention - Ratio parámetros/observaciones < 1:30
- R7: Monte Carlo Simulation - Stress testing con simulaciones
- DATA-001: Purged Cross-Validation - CV sin data leakage

Uso:
    from app.backtesting.backtesting_compliance import BacktestingCompliance

    compliance = BacktestingCompliance()
    result = compliance.validate_backtest(
        backtest_results=results,
        n_parameters=10,
        n_observations=500
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES DE COMPLIANCE (según rules_mapping.yml)
# =============================================================================

# R6: Overfitting Prevention - Ratio máximo parámetros/observaciones
MAX_PARAM_OBSERVATION_RATIO = 1 / 30  # < 1:30

# R5: Walk-Forward Analysis - Configuración mínima
MIN_WALK_FORWARD_WINDOWS = 3
MIN_TRADES_PER_WINDOW = 10
MIN_CONSISTENCY_RATIO = 0.7  # 70% de ventanas deben ser rentables
MAX_IS_OOS_DEGRADATION = 0.30  # Máximo 30% degradación IS->OOS

# R7: Monte Carlo Simulation
MIN_MONTE_CARLO_SIMULATIONS = 1000
CONFIDENCE_LEVELS = [0.95, 0.99]

# DATA-001: Purged Cross-Validation
MIN_PURGE_DAYS = 5  # Días a purgar entre train/test
EMBARGO_DAYS = 10  # Días de embargo después del test


# =============================================================================
# RESULTADOS DE COMPLIANCE
# =============================================================================


@dataclass
class ComplianceViolation:
    """Representa una violación de compliance."""

    rule_id: str
    rule_name: str
    severity: str  # 'ERROR', 'WARNING', 'INFO'
    message: str
    value: float | None = None
    threshold: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestingComplianceResult:
    """Resultado completo de validación de compliance."""

    is_compliant: bool
    violations: list[ComplianceViolation] = field(default_factory=list)

    # R5: Walk-Forward
    walk_forward_passed: bool = False
    walk_forward_consistency: float = 0.0
    walk_forward_is_oos_ratio: float = 0.0

    # R6: Overfitting
    overfitting_check_passed: bool = False
    param_observation_ratio: float = 0.0

    # R7: Monte Carlo
    monte_carlo_passed: bool = False
    monte_carlo_var_95: float = 0.0
    monte_carlo_var_99: float = 0.0

    # DATA-001: Purged CV
    purged_cv_passed: bool = False
    purge_days_used: int = 0

    def add_violation(self, violation: ComplianceViolation) -> None:
        """Añadir una violación y actualizar estado."""
        self.violations.append(violation)
        if violation.severity == "ERROR":
            self.is_compliant = False

    def get_summary(self) -> dict[str, Any]:
        """Obtener resumen del resultado."""
        return {
            "is_compliant": self.is_compliant,
            "total_violations": len(self.violations),
            "errors": sum(1 for v in self.violations if v.severity == "ERROR"),
            "warnings": sum(1 for v in self.violations if v.severity == "WARNING"),
            "walk_forward_passed": self.walk_forward_passed,
            "overfitting_check_passed": self.overfitting_check_passed,
            "monte_carlo_passed": self.monte_carlo_passed,
            "purged_cv_passed": self.purged_cv_passed,
        }


# =============================================================================
# VALIDADOR PRINCIPAL
# =============================================================================


class BacktestingCompliance:
    """
    Validador de compliance para backtesting.

    Implementa las reglas R5, R6, R7 y DATA-001 definidas en rules_mapping.yml.

    Ejemplo de uso:
        compliance = BacktestingCompliance()

        # Validar overfitting (R6)
        result = compliance.check_overfitting(n_parameters=15, n_observations=600)

        # Validar walk-forward (R5)
        result = compliance.check_walk_forward(windows_results=[...])

        # Validación completa
        result = compliance.validate_backtest(...)
    """

    def __init__(
        self,
        max_param_ratio: float = MAX_PARAM_OBSERVATION_RATIO,
        min_walk_forward_windows: int = MIN_WALK_FORWARD_WINDOWS,
        min_consistency_ratio: float = MIN_CONSISTENCY_RATIO,
        max_is_oos_degradation: float = MAX_IS_OOS_DEGRADATION,
        min_monte_carlo_sims: int = MIN_MONTE_CARLO_SIMULATIONS,
        min_purge_days: int = MIN_PURGE_DAYS,
    ):
        """
        Inicializar validador con configuración.

        Args:
            max_param_ratio: Ratio máximo parámetros/observaciones (R6)
            min_walk_forward_windows: Mínimo de ventanas WF (R5)
            min_consistency_ratio: Mínimo ratio de consistencia (R5)
            max_is_oos_degradation: Máxima degradación IS->OOS (R5)
            min_monte_carlo_sims: Mínimo de simulaciones MC (R7)
            min_purge_days: Mínimo días de purge (DATA-001)
        """
        self.max_param_ratio = max_param_ratio
        self.min_walk_forward_windows = min_walk_forward_windows
        self.min_consistency_ratio = min_consistency_ratio
        self.max_is_oos_degradation = max_is_oos_degradation
        self.min_monte_carlo_sims = min_monte_carlo_sims
        self.min_purge_days = min_purge_days

        logger.info(
            f"BacktestingCompliance initialized: "
            f"max_param_ratio={max_param_ratio:.4f}, "
            f"min_wf_windows={min_walk_forward_windows}, "
            f"min_consistency={min_consistency_ratio:.2f}"
        )

    # =========================================================================
    # R6: Overfitting Prevention
    # =========================================================================

    def check_overfitting(
        self,
        n_parameters: int,
        n_observations: int,
        result: BacktestingComplianceResult | None = None,
    ) -> BacktestingComplianceResult:
        """
        Validar R6: Overfitting Prevention.

        Regla: El ratio parámetros/observaciones debe ser < 1:30
        Esto previene el sobreajuste del modelo.

        Args:
            n_parameters: Número de parámetros optimizables
            n_observations: Número de observaciones en el dataset
            result: Resultado existente para actualizar (opcional)

        Returns:
            BacktestingComplianceResult con el resultado de la validación
        """
        if result is None:
            result = BacktestingComplianceResult(is_compliant=True)

        if n_observations <= 0:
            result.add_violation(
                ComplianceViolation(
                    rule_id="R6",
                    rule_name="Overfitting Prevention",
                    severity="ERROR",
                    message="n_observations debe ser > 0",
                    value=n_observations,
                    threshold=1,
                )
            )
            result.overfitting_check_passed = False
            return result

        ratio = n_parameters / n_observations
        result.param_observation_ratio = ratio

        if ratio >= self.max_param_ratio:
            result.add_violation(
                ComplianceViolation(
                    rule_id="R6",
                    rule_name="Overfitting Prevention",
                    severity="ERROR",
                    message=f"Ratio parametros/observaciones ({ratio:.4f}) >= max permitido ({self.max_param_ratio:.4f})",
                    value=ratio,
                    threshold=self.max_param_ratio,
                    details={
                        "n_parameters": n_parameters,
                        "n_observations": n_observations,
                        "min_observations_needed": int(n_parameters / self.max_param_ratio),
                    },
                )
            )
            result.overfitting_check_passed = False
        else:
            logger.info(
                f"R6 PASSED: param/obs ratio={ratio:.4f} < {self.max_param_ratio:.4f} "
                f"({n_parameters} params, {n_observations} obs)"
            )
            result.overfitting_check_passed = True

        return result

    # =========================================================================
    # R5: Walk-Forward Analysis
    # =========================================================================

    def check_walk_forward(
        self,
        windows_results: list[dict[str, Any]],
        result: BacktestingComplianceResult | None = None,
    ) -> BacktestingComplianceResult:
        """
        Validar R5: Walk-Forward Analysis.

        Criterios:
        - Mínimo 3 ventanas completas
        - 70%+ de ventanas deben ser rentables (OOS)
        - Degradación IS->OOS < 30%

        Args:
            windows_results: Lista de resultados por ventana, cada uno con:
                - is_return: Return in-sample
                - oos_return: Return out-of-sample
                - is_sharpe: Sharpe in-sample
                - oos_sharpe: Sharpe out-of-sample
                - trades: Número de trades
            result: Resultado existente para actualizar (opcional)

        Returns:
            BacktestingComplianceResult con el resultado de la validación
        """
        if result is None:
            result = BacktestingComplianceResult(is_compliant=True)

        # Validar número mínimo de ventanas
        if len(windows_results) < self.min_walk_forward_windows:
            result.add_violation(
                ComplianceViolation(
                    rule_id="R5",
                    rule_name="Walk-Forward Analysis",
                    severity="ERROR",
                    message=f"Insuficientes ventanas WF: {len(windows_results)} < {self.min_walk_forward_windows}",
                    value=len(windows_results),
                    threshold=self.min_walk_forward_windows,
                )
            )
            result.walk_forward_passed = False
            return result

        # Calcular métricas de consistencia
        profitable_windows = sum(1 for w in windows_results if w.get("oos_return", 0) > 0)
        consistency = profitable_windows / len(windows_results)
        result.walk_forward_consistency = consistency

        # Calcular ratio IS/OOS
        is_sharpes = [w.get("is_sharpe", 0) for w in windows_results]
        oos_sharpes = [w.get("oos_sharpe", 0) for w in windows_results]
        avg_is_sharpe = np.mean(is_sharpes) if is_sharpes else 0
        avg_oos_sharpe = np.mean(oos_sharpes) if oos_sharpes else 0

        is_oos_ratio = avg_oos_sharpe / avg_is_sharpe if avg_is_sharpe != 0 else 0.0
        result.walk_forward_is_oos_ratio = is_oos_ratio

        # Validar consistencia
        if consistency < self.min_consistency_ratio:
            result.add_violation(
                ComplianceViolation(
                    rule_id="R5",
                    rule_name="Walk-Forward Analysis",
                    severity="ERROR",
                    message=f"Consistencia WF ({consistency:.2%}) < mínimo ({self.min_consistency_ratio:.2%})",
                    value=consistency,
                    threshold=self.min_consistency_ratio,
                    details={
                        "profitable_windows": profitable_windows,
                        "total_windows": len(windows_results),
                    },
                )
            )

        # Validar degradación IS->OOS
        degradation = 1 - is_oos_ratio if is_oos_ratio > 0 else 1.0
        if degradation > self.max_is_oos_degradation:
            result.add_violation(
                ComplianceViolation(
                    rule_id="R5",
                    rule_name="Walk-Forward Analysis",
                    severity="WARNING",
                    message=f"Degradación IS->OOS ({degradation:.2%}) > máximo ({self.max_is_oos_degradation:.2%})",
                    value=degradation,
                    threshold=self.max_is_oos_degradation,
                    details={
                        "avg_is_sharpe": avg_is_sharpe,
                        "avg_oos_sharpe": avg_oos_sharpe,
                        "is_oos_ratio": is_oos_ratio,
                    },
                )
            )

        # Determinar si pasó
        result.walk_forward_passed = (
            consistency >= self.min_consistency_ratio and degradation <= self.max_is_oos_degradation
        )

        if result.walk_forward_passed:
            logger.info(
                f"R5 PASSED: consistencia={consistency:.2%}, "
                f"IS/OOS ratio={is_oos_ratio:.2f}, "
                f"degradación={degradation:.2%}"
            )

        return result

    # =========================================================================
    # R7: Monte Carlo Simulation
    # =========================================================================

    def check_monte_carlo(
        self,
        var_95: float,
        var_99: float,
        n_simulations: int = 1000,
        result: BacktestingComplianceResult | None = None,
    ) -> BacktestingComplianceResult:
        """
        Validar R7: Monte Carlo Simulation.

        Criterios:
        - Mínimo 1000 simulaciones
        - VaR 95% y 99% calculados

        Args:
            var_95: Value at Risk al 95% de confianza
            var_99: Value at Risk al 99% de confianza
            n_simulations: Número de simulaciones realizadas
            result: Resultado existente para actualizar (opcional)

        Returns:
            BacktestingComplianceResult con el resultado de la validación
        """
        if result is None:
            result = BacktestingComplianceResult(is_compliant=True)

        result.monte_carlo_var_95 = var_95
        result.monte_carlo_var_99 = var_99

        # Validar número de simulaciones
        if n_simulations < self.min_monte_carlo_sims:
            result.add_violation(
                ComplianceViolation(
                    rule_id="R7",
                    rule_name="Monte Carlo Simulation",
                    severity="WARNING",
                    message=f"Pocas simulaciones MC: {n_simulations} < {self.min_monte_carlo_sims}",
                    value=n_simulations,
                    threshold=self.min_monte_carlo_sims,
                )
            )

        # Validar que VaR está en rango esperado (-1 a 0 típicamente)
        if var_95 > 0 or var_99 > 0:
            result.add_violation(
                ComplianceViolation(
                    rule_id="R7",
                    rule_name="Monte Carlo Simulation",
                    severity="WARNING",
                    message="VaR positivo detectado - posible error en cálculo",
                    details={
                        "var_95": var_95,
                        "var_99": var_99,
                    },
                )
            )

        # Monte Carlo pasa si se ejecutó con suficientes simulaciones
        result.monte_carlo_passed = n_simulations >= self.min_monte_carlo_sims

        if result.monte_carlo_passed:
            logger.info(
                f"R7 PASSED: {n_simulations} simulaciones, "
                f"VaR 95%={var_95:.4f}, VaR 99%={var_99:.4f}"
            )

        return result

    # =========================================================================
    # DATA-001: Purged Cross-Validation
    # =========================================================================

    def check_purged_cv(
        self,
        purge_days: int,
        embargo_days: int = 0,
        has_overlap: bool = False,
        result: BacktestingComplianceResult | None = None,
    ) -> BacktestingComplianceResult:
        """
        Validar DATA-001: Purged Cross-Validation.

        Criterios:
        - Mínimo 5 días de purge entre train/test
        - Embargo days recomendados (10)
        - Sin overlap entre folds

        Args:
            purge_days: Días purgados entre train y test
            embargo_days: Días de embargo después del test
            has_overlap: Si hay overlap entre folds (debe ser False)
            result: Resultado existente para actualizar (opcional)

        Returns:
            BacktestingComplianceResult con el resultado de la validación
        """
        if result is None:
            result = BacktestingComplianceResult(is_compliant=True)

        result.purge_days_used = purge_days

        # Validar purge days
        if purge_days < self.min_purge_days:
            result.add_violation(
                ComplianceViolation(
                    rule_id="DATA-001",
                    rule_name="Purged Cross-Validation",
                    severity="ERROR",
                    message=f"Purge days ({purge_days}) < mínimo ({self.min_purge_days})",
                    value=purge_days,
                    threshold=self.min_purge_days,
                )
            )

        # Validar embargo
        if embargo_days < EMBARGO_DAYS:
            result.add_violation(
                ComplianceViolation(
                    rule_id="DATA-001",
                    rule_name="Purged Cross-Validation",
                    severity="WARNING",
                    message=f"Embargo days ({embargo_days}) < recomendado ({EMBARGO_DAYS})",
                    value=embargo_days,
                    threshold=EMBARGO_DAYS,
                )
            )

        # Validar overlap
        if has_overlap:
            result.add_violation(
                ComplianceViolation(
                    rule_id="DATA-001",
                    rule_name="Purged Cross-Validation",
                    severity="ERROR",
                    message="Overlap detectado entre folds - data leakage risk",
                    details={
                        "has_overlap": has_overlap,
                    },
                )
            )

        result.purged_cv_passed = purge_days >= self.min_purge_days and not has_overlap

        if result.purged_cv_passed:
            logger.info(
                f"DATA-001 PASSED: purge={purge_days} días, "
                f"embargo={embargo_days} días, sin overlap"
            )

        return result

    # =========================================================================
    # VALIDACIÓN COMPLETA
    # =========================================================================

    def validate_backtest(
        self,
        backtest_results: dict[str, Any] | None = None,
        n_parameters: int = 0,
        n_observations: int = 0,
        walk_forward_windows: list[dict[str, Any]] | None = None,
        monte_carlo_var_95: float = 0.0,
        monte_carlo_var_99: float = 0.0,
        monte_carlo_simulations: int = 0,
        purge_days: int = 0,
        embargo_days: int = 0,
        has_cv_overlap: bool = False,
    ) -> BacktestingComplianceResult:
        """
        Ejecutar validación completa de compliance de backtesting.

        Args:
            backtest_results: Resultados del backtest (opcional, para extensión)
            n_parameters: Número de parámetros optimizables
            n_observations: Número de observaciones
            walk_forward_windows: Resultados de ventanas walk-forward
            monte_carlo_var_95: VaR 95% de Monte Carlo
            monte_carlo_var_99: VaR 99% de Monte Carlo
            monte_carlo_simulations: Número de simulaciones MC
            purge_days: Días de purge en CV
            embargo_days: Días de embargo en CV
            has_cv_overlap: Si hay overlap en CV

        Returns:
            BacktestingComplianceResult con validación completa
        """
        result = BacktestingComplianceResult(is_compliant=True)

        # R6: Overfitting Prevention
        if n_parameters > 0 and n_observations > 0:
            result = self.check_overfitting(
                n_parameters=n_parameters,
                n_observations=n_observations,
                result=result,
            )

        # R5: Walk-Forward Analysis
        if walk_forward_windows:
            result = self.check_walk_forward(
                windows_results=walk_forward_windows,
                result=result,
            )

        # R7: Monte Carlo
        if monte_carlo_simulations > 0:
            result = self.check_monte_carlo(
                var_95=monte_carlo_var_95,
                var_99=monte_carlo_var_99,
                n_simulations=monte_carlo_simulations,
                result=result,
            )

        # DATA-001: Purged CV
        if purge_days > 0:
            result = self.check_purged_cv(
                purge_days=purge_days,
                embargo_days=embargo_days,
                has_overlap=has_cv_overlap,
                result=result,
            )

        # Log resumen
        summary = result.get_summary()
        if result.is_compliant:
            logger.info(f"Backtesting compliance PASSED: {summary}")
        else:
            logger.warning(f"Backtesting compliance FAILED: {summary}")
            for v in result.violations:
                logger.warning(f"  [{v.severity}] {v.rule_id}: {v.message}")

        return result


# =============================================================================
# FUNCIÓN DE CONVENIENCIA
# =============================================================================


def create_backtesting_compliance() -> BacktestingCompliance:
    """
    Crear instancia de BacktestingCompliance con configuración por defecto.

    Returns:
        BacktestingCompliance configurado
    """
    return BacktestingCompliance()


def validate_backtest_quick(
    n_parameters: int,
    n_observations: int,
) -> BacktestingComplianceResult:
    """
    Validación rápida de overfitting (R6).

    Args:
        n_parameters: Número de parámetros
        n_observations: Número de observaciones

    Returns:
        BacktestingComplianceResult
    """
    compliance = BacktestingCompliance()
    return compliance.check_overfitting(n_parameters, n_observations)
