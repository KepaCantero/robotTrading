"""
Domain Layer - Clean Architecture

This layer contains the core business logic and enterprise rules.
It has NO dependencies on external frameworks, databases, or UI.

Layers:
- Entities: Core business objects with identity
- Value Objects: Immutable values without identity
- Repository Interfaces: Contracts for data access (abstract)
- Domain Services: Business logic that doesn't fit in entities
"""
