"""
Corporate Actions Handler Package

This package handles corporate events that affect positions:
- Stock splits: Quantity and entry price adjustment
- Dividends: Cash received and baseline price adjustment
- Mergers: Position conversion to acquiring company
- Delistings: Position closure
- Spin-offs: New shares received
- Rights offerings: Rights issued to shareholders
- Symbol changes: Symbol updates

Phase 2.6: Corporate Actions Handler for multi-day position support.

Author: Algorithmic Trading System
Date: 2026-01-25
"""

from app.services.corporate_actions.handler import (
    CorporateAction,
    CorporateActionsHandler,
    CorporateActionType,
)

__all__ = [
    "CorporateAction",
    "CorporateActionType",
    "CorporateActionsHandler",
]
