"""
Signals Service Package

Re-exports from app.services for backward compatibility.
Uses late import to avoid domain layer depending on services layer at module load time.
"""

from app.domain.services.signals.scoring import get_signal_scoring_engine

__all__ = ["get_signal_scoring_engine"]
