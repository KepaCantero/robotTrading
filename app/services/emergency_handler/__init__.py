"""
Emergency Handler - Closes all positions on critical system failures.

This is a CRITICAL component for production trading that protects against
catastrophic losses when the system fails unexpectedly.
"""

from .emergency_closer import EmergencyCloser, EmergencyCloseResult, EmergencyTrigger

__all__ = [
    "EmergencyCloseResult",
    "EmergencyCloser",
    "EmergencyTrigger",
]
