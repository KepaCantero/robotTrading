"""
Protocol interfaces for SOLID architecture

This module contains all Protocol interfaces used throughout
the application for dependency inversion and interface segregation.
"""

from app.core.protocols.signal_scoring import SignalScoringEngineProtocol

__all__ = ["SignalScoringEngineProtocol"]
