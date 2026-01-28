"""
SRE Automation Package.

Provides tools for reducing toil and automating repetitive operational tasks:
- ToilTracker: Track and reduce manual operational work
- Automation pipelines for common SRE tasks
"""

from .toil_tracker import (
    AutomationOpportunity,
    AutomationPotential,
    ToilCategory,
    ToilConfig,
    ToilEntry,
    ToilMetrics,
    ToilReport,
    ToilTracker,
    get_toil_tracker,
)

__all__ = [
    "ToilEntry",
    "ToilTracker",
    "ToilCategory",
    "ToilReport",
    "AutomationOpportunity",
    "AutomationPotential",
    "ToilMetrics",
    "ToilConfig",
    "get_toil_tracker",
]
