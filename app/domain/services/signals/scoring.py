"""
Signal Scoring Module

Re-exports from app.services for backward compatibility.
Uses late import to avoid domain layer depending on services layer at module load time.
"""

from app.core.protocols.signal_scoring import SignalScoringEngineProtocol


def get_signal_scoring_engine() -> SignalScoringEngineProtocol:
    """
    Get signal scoring engine instance.

    Late import to avoid domain layer depending on services layer.
    """
    # Late import to avoid architecture violation at module load time
    from app.services.signal_scoring_engine import get_signal_scoring_engine as _get_engine

    return _get_engine()


__all__ = ["get_signal_scoring_engine", "SignalScoringEngineProtocol"]
