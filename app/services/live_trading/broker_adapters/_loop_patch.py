"""Opt-in ib_insync loop patching.

The three IB-related modules used to call ``util.patchAsyncio()`` at IMPORT
time — a global mutation of asyncio that crashes under uvloop (NiceGUI's
event loop: "Can't patch loop of type uvloop.Loop") and breaks any paper
trading in the dashboard. PLAN_PRODUCCION_PAPER_IBKR.md (Fase 3) orders the
global patch removed; this helper keeps it available for the IB adapters at
CONNECT time, where it is actually needed, and tolerates loops that
nest_asyncio cannot patch (uvloop): the adapter's own connection errors
surface whatever is really wrong instead of an import-time crash.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def patch_ib_eventloop() -> bool:
    """Patch the running loop for ib_insync's sync-style API. Returns True
    when patched; False (with a warning) when the loop type refuses it."""
    try:
        from ib_insync import util

        util.patchAsyncio()
        return True
    except ValueError as exc:  # uvloop and friends
        logger.warning(
            "ib_insync asyncio patch skipped (%s) — the IB adapters must use "
            "their async API on this loop",
            exc,
        )
        return False
