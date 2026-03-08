"""
Signal Scoring Module

Re-exports from app.services for backward compatibility.
"""

from app.services.signal_scoring_engine import get_signal_scoring_engine

__all__ = ["get_signal_scoring_engine"]
