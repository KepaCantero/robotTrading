"""
Output generation module.

Generates consolidated output DataFrames with allocation results
and metrics for reporting and analysis.
"""

from __future__ import annotations

import logging

import pandas as pd
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# Data models for type checking
class StockMetrics(BaseModel):
    """Metrics for a single stock."""

    ticker: str
    strategy: str | None = None
    weight: float = 0.0
    capital: float = 0.0
    sps_score: float = 0.0
    sortino_ratio: float | None = None
    h_long: float | None = None
    h_short: float | None = None
    half_life_tau: float | None = None
    garch_volatility: float | None = None
    decision_log: str = ""


class PairMetrics(BaseModel):
    """Metrics for a trading pair."""

    ticker1: str
    ticker2: str
    cointegration_score: float
    correlation: float
    half_life_tau: float | None = None
    decision_log: str = ""


class OutputGenerator:
    """
    Generates consolidated output from allocation results.

    Creates DataFrames with all metrics and decision logs for
    reporting and analysis.
    """

    def __init__(self) -> None:
        """Initialize output generator."""

    def generate(
        self,
        allocations: dict[str, StockMetrics],
        pairs: list[PairMetrics],
    ) -> pd.DataFrame:
        """
        Generate consolidated output DataFrame.

        Columns: Ticker, Estrategia, Peso, Capital, SPS, Sortino, H_long, H_short, τ, σ_GARCH, Decision_Log.

        Args:
            allocations: Dictionary of allocations
            pairs: List of pair metrics

        Returns:
            DataFrame with all metrics and decision logs
        """
        rows = []

        for ticker, alloc in allocations.items():
            row = {
                "Ticker": alloc.ticker,
                "Estrategia": alloc.strategy or "unassigned",
                "Peso": f"{alloc.weight:.4f}",
                "Capital": f"${alloc.capital:,.2f}",
                "SPS": f"{alloc.sps_score:.4f}",
                "Sortino": (
                    f"{alloc.sortino_ratio:.4f}" if alloc.sortino_ratio is not None else "N/A"
                ),
                "H_long": f"{alloc.h_long:.4f}" if alloc.h_long is not None else "N/A",
                "H_short": f"{alloc.h_short:.4f}" if alloc.h_short is not None else "N/A",
                "τ": f"{alloc.half_life_tau:.2f}" if alloc.half_life_tau is not None else "N/A",
                "σ_GARCH": (
                    f"{alloc.garch_volatility:.4f}" if alloc.garch_volatility is not None else "N/A"
                ),
                "Decision_Log": alloc.decision_log,
            }
            rows.append(row)

        # Add pairs
        for pair in pairs:
            row = {
                "Ticker": f"{pair.ticker1}-{pair.ticker2}",
                "Estrategia": "pairs_trading",
                "Peso": "N/A",
                "Capital": "N/A",
                "SPS": f"{pair.cointegration_score:.4f}",
                "Sortino": "N/A",
                "H_long": "N/A",
                "H_short": "N/A",
                "τ": f"{pair.half_life_tau:.2f}" if pair.half_life_tau is not None else "N/A",
                "σ_GARCH": "N/A",
                "Decision_Log": pair.decision_log,
            }
            rows.append(row)

        df = pd.DataFrame(rows)
        logger.info(f"Generated output DataFrame: {len(df)} rows")
        return df
