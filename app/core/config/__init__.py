"""
Core Configuration Package

Re-exports from app.shared.config for backward compatibility.
"""

from app.shared.config.centralized_config import get_config

__all__ = ["get_config"]
