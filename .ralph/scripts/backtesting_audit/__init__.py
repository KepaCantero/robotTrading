"""
Backtesting Audit Module

Módulo para auditar tests de backtesting contra las reglas de trading.

Este módulo proporciona clases y funciones para:
1. Verificar que ComplianceEngine tiene las validaciones requeridas
2. Ejecutar backtests por profile_investor

Architecture:
    Todo debe pasar por ComplianceEngine.
    BacktestEngine → ComplianceEngine → Validaciones (R1, R2, R4, CHAN-002, RET-003)

Usage:
    from .ralph.scripts.backtesting_audit import ComplianceChecker, ProfileRunner

    # Verificar ComplianceEngine
    checker = ComplianceChecker(project_root)
    results = checker.check_all()

    # Ejecutar backtests por profile
    runner = ProfileRunner()
    results = runner.run_all_profiles()
"""

from .compliance_checker import ComplianceChecker, ComplianceValidationResult, ComplianceReport

__all__ = [
    "ComplianceChecker",
    "ComplianceValidationResult",
    "ComplianceReport",
]
