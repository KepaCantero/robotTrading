"""
Logging protocols (R15, R28)
"""
from typing import Protocol


class ITradingDecisionLogger(Protocol):
    """Logger append-only con correlation ID - Máximo 5 métodos"""

    def log_signal(self, signal: "TradeSignal", metadata: dict) -> str:
        """Log signal con correlation ID"""
        ...

    def log_execution(self, correlation_id: str, result: "TradeResult") -> None:
        """Log execution result"""
        ...

    def log_validation_result(self, correlation_id: str, validator: str, passed: bool) -> None:
        """Log validation result"""
        ...

    def get_logs_by_correlation_id(self, correlation_id: str) -> list:
        """Obtener logs por correlation ID"""
        ...

    def export_for_hacienda(self, year: int) -> list:
        """R28: Exportar logs para Hacienda (5 años)"""
        ...
