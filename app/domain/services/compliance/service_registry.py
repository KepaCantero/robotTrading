"""Backward-compatibility re-export. Canonical module: app.services.compliance.service_registry."""

from app.services.compliance.service_registry import (
    ComplianceServiceRegistry,
    get_service,
    get_service_registry,
)

__all__ = ["ComplianceServiceRegistry", "get_service", "get_service_registry"]
