"""Application routers module.

Routers are application-level services that map domain inputs to
configuration outputs. They follow SOLID principles and Clean Architecture.

Available routers:
- InputProfileRouter: Maps InputProfile to SystemConfiguration
"""

from app.application.routers.input_profile_router import InputProfileRouter

__all__ = [
    "InputProfileRouter",
]
