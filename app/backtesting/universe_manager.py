"""
Backtesting Universe with Survivorship Bias Adjustment

Includes delisted, bankrupt, and failed companies to prevent
survivorship bias in backtesting results.

Survivorship bias occurs when backtesting only includes currently active
companies, ignoring those that failed. This inflates performance metrics
because failed companies are systematically excluded from historical data.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Comprehensive backtesting universe with historical failures
BACKTEST_UNIVERSE = {
    "survivors": [
        # Tech survivors (companies that survived through all market cycles)
        "AAPL",  # Apple
        "MSFT",  # Microsoft
        "GOOGL",  # Google/Alphabet
        "AMZN",  # Amazon
        "JPM",  # JPMorgan Chase
        "BAC",  # Bank of America
        "WMT",  # Walmart
        "PG",  # Procter & Gamble
        "JNJ",  # Johnson & Johnson
        "XOM",  # ExxonMobil
        "BRK-B",  # Berkshire Hathaway
    ],
    "delisted": [
        # Major bankruptcies and failures (these should be included!)
        ("ENRN", "Enron Corporation", "2001-12-02", "bankruptcy"),
        ("LEH", "Lehman Brothers", "2008-09-15", "bankruptcy"),
        ("WCOM", "WorldCom", "2002-07-21", "bankruptcy"),
        ("KM", "Kmart", "2002-03-07", "bankruptcy"),
        ("TWXQ", "Toys R Us", "2017-09-18", "bankruptcy"),
        ("THMRQ", "Theranos", "2018-09-04", "dissolution"),
        ("PNCL", "Pinnacle Airlines", "2012-04-20", "bankruptcy"),
        ("MIR", "Mirant Corporation", "2007-01-09", "bankruptcy"),
        ("CAL", "Calpine Corporation", "2005-12-20", "bankruptcy"),
        ("FAIRX", "Fair Financial", "2008-11-14", "fraud"),
    ],
    "spun_off": [
        # Companies that were acquired (not bankrupt, but no longer trade independently)
        ("YHOO", "Yahoo", "2017-06-13", "acquired_by_verizon"),
        ("MW", "Monsanto", "2018-06-07", "acquired_by_bayer"),
        ("FT", "First Republic Bank", "2023-05-01", "seized_by_fdic"),
        ("TMUS", "T-Mobile US", "2020-04-01", "acquired_by_sprint"),
        ("CTX", "CenturyLink", "2023-09-01", "renamed_to_lumen"),
    ],
    "penny_stocks": [
        # Companies that fell to penny stock status during crisis periods
        ("GE", "General Electric", "2008-01-01", "2009-12-31", "fell_to_$6"),
        ("F", "Ford", "2008-01-01", "2009-12-31", "fell_to_$1"),
        ("C", "Citigroup", "2008-01-01", "2009-12-31", "fell_to_$1"),
        ("AIG", "AIG", "2008-01-01", "2009-12-31", "fell_to_$1"),
        ("BSC", "Bear Stearns", "2008-01-01", "2008-03-17", "acquired_at_$2"),
    ],
}


class UniverseManager:
    """
    Manages backtesting universe with survivorship bias adjustment.

    By including failed companies, we get a more realistic picture of
    strategy performance that would have been achievable in real-time.
    """

    def __init__(self, universe_config: Optional[Dict] = None):
        """
        Initialize universe manager.

        Args:
            universe_config: Custom universe config (uses default if None)
        """
        self.universe = universe_config or BACKTEST_UNIVERSE
        logger.info("UniverseManager initialized with survivorship bias adjustment")

    def get_universe(
        self,
        start_date: datetime,
        end_date: datetime,
        include_delisted: bool = True,
        include_spun_off: bool = True,
        include_penny_stocks: bool = False,
    ) -> List[str]:
        """
        Get list of symbols that were active during backtesting period.

        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            include_delisted: Include companies that went bankrupt
            include_spun_off: Include companies that were acquired
            include_penny_stocks: Include penny stock periods

        Returns:
            List of symbols that were active during the period
        """
        symbols = []

        # Always include survivors
        symbols.extend(self.universe["survivors"])

        # Add delisted if active during period
        if include_delisted:
            for entry in self.universe["delisted"]:
                symbol, name, delist_date, reason = entry
                delist_dt = datetime.strptime(delist_date, "%Y-%m-%d")
                if start_date < delist_dt < end_date:
                    symbols.append(symbol)
                    logger.debug(
                        f"Including delisted {symbol} ({name}) - "
                        f"delisted {delist_date} due to {reason}"
                    )

        # Add spun off if active during period
        if include_spun_off:
            for entry in self.universe["spun_off"]:
                symbol, name, acquire_date, acquirer = entry
                acquire_dt = datetime.strptime(acquire_date, "%Y-%m-%d")
                if start_date < acquire_dt < end_date:
                    symbols.append(symbol)
                    logger.debug(
                        f"Including acquired {symbol} ({name}) - "
                        f"acquired {acquire_date} by {acquirer}"
                    )

        # Add penny stocks if requested
        if include_penny_stocks:
            for entry in self.universe["penny_stocks"]:
                symbol = entry[0]
                period_start = datetime.strptime(entry[2], "%Y-%m-%d")
                period_end = datetime.strptime(entry[3], "%Y-%m-%d")

                # Check if penny stock period overlaps with backtest period
                if period_start <= end_date and period_end >= start_date:
                    if symbol not in symbols:  # Avoid duplicates
                        symbols.append(symbol)
                        logger.debug(
                            f"Including penny stock period for {symbol} "
                            f"({entry[4]}: {period_start.date()} to {period_end.date()})"
                        )

        logger.info(
            f"Universe includes {len(symbols)} symbols for period "
            f"{start_date.date()} to {end_date.date()}"
        )

        return symbols

    def filter_by_market_cap(
        self,
        symbols: List[str],
        min_market_cap: Optional[Decimal] = None,
        max_market_cap: Optional[Decimal] = None,
        historical_date: Optional[datetime] = None,
    ) -> List[str]:
        """
        Filter symbols by market cap.

        Args:
            symbols: List of symbols to filter
            min_market_cap: Minimum market cap (in billions)
            max_market_cap: Maximum market cap (in billions)
            historical_date: Date for historical market cap (uses current if None)

        Returns:
            Filtered list of symbols
        """
        # Simplified market cap data (in billions of USD)
        # In production, this would load from a data provider
        market_caps = {
            # Large caps
            "AAPL": 3000,
            "MSFT": 2500,
            "GOOGL": 2000,
            "AMZN": 1800,
            "JPM": 400,
            "BAC": 200,
            "XOM": 400,
            "JNJ": 400,
            "WMT": 400,
            "BRK-B": 600,
            # Mid/small caps
            "GE": 100,  # Pre-2017
            "F": 50,
            "C": 100,
            "AIG": 50,
            # Failed companies (at peak before failure)
            "ENRN": 70,  # At peak in 2000
            "LEH": 40,  # At peak in 2007
            "WCOM": 120,  # At peak in 1999
            "KM": 10,  # At peak in 2000
        }

        filtered = []
        for symbol in symbols:
            if symbol in market_caps:
                cap = Decimal(str(market_caps[symbol]))

                if min_market_cap and cap < min_market_cap:
                    continue
                if max_market_cap and cap > max_market_cap:
                    continue

                filtered.append(symbol)

        logger.info(
            f"Filtered to {len(filtered)} symbols by market cap "
            f"(min={min_market_cap}, max={max_market_cap})"
        )

        return filtered

    def calculate_survivorship_bias(
        self,
        survivor_returns: List[float],
        full_universe_returns: List[float],
    ) -> Dict[str, float]:
        """
        Quantify the impact of survivorship bias.

        Args:
            survivor_returns: Returns using only surviving companies
            full_universe_returns: Returns including failed companies

        Returns:
            Dictionary with bias metrics
        """
        if not survivor_returns or not full_universe_returns:
            return {"bias_detected": False}

        import numpy as np

        survivor_cagr = self._calculate_cagr_from_returns(survivor_returns)
        full_cagr = self._calculate_cagr_from_returns(full_universe_returns)

        bias_pct = (
            ((survivor_cagr - full_cagr) / abs(full_cagr) * 100)
            if full_cagr != 0
            else 0
        )

        result = {
            "survivor_cagr": survivor_cagr,
            "full_universe_cagr": full_cagr,
            "bias_percentage": bias_pct,
            "bias_detected": bias_pct > 10.0,  # More than 10% difference
        }

        if result["bias_detected"]:
            logger.warning(
                f"Survivorship bias detected: {bias_pct:.1f}% overestimation "
                f"(survivors: {survivor_cagr:.1%}, full: {full_cagr:.1%})"
            )

        return result

    def _calculate_cagr_from_returns(self, returns: List[float]) -> float:
        """
        Calculate CAGR from a list of returns.

        Args:
            returns: List of periodic returns

        Returns:
            CAGR as a decimal
        """
        if not returns:
            return 0.0

        import numpy as np

        # Convert returns to cumulative growth
        cumulative = (1.0 + np.array(returns)).prod()
        n_periods = len(returns)

        # CAGR = (cumulative_growth)^(1/n) - 1
        cagr = cumulative ** (1.0 / n_periods) - 1.0

        return cagr

    def get_sector_diversification(
        self, symbols: List[str]
    ) -> Dict[str, List[str]]:
        """
        Get sector breakdown for a list of symbols.

        Args:
            symbols: List of symbols

        Returns:
            Dictionary mapping sectors to symbol lists
        """
        # Simplified sector mapping
        sector_map = {
            "Technology": ["AAPL", "MSFT", "GOOGL", "CSCO", "INTC"],
            "Financials": ["JPM", "BAC", "C", "WFC", "GS"],
            "Healthcare": ["JNJ", "PFE", "UNH", "ABT"],
            "Consumer": ["WMT", "PG", "KO", "NKE"],
            "Energy": ["XOM", "CVX", "COP"],
            "Industrial": ["GE", "HON", "UNP"],
            "Failed": ["ENRN", "LEH", "WCOM", "KM"],
        }

        # Reverse map: symbol -> sector
        symbol_to_sector = {}
        for sector, tickers in sector_map.items():
            for ticker in tickers:
                symbol_to_sector[ticker] = sector

        # Group symbols by sector
        sectors = {}
        for symbol in symbols:
            sector = symbol_to_sector.get(symbol, "Unknown")
            if sector not in sectors:
                sectors[sector] = []
            sectors[sector].append(symbol)

        return sectors

    def get_universe_statistics(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, any]:
        """
        Get statistics about the backtesting universe.

        Args:
            start_date: Backtest start date
            end_date: Backtest end date

        Returns:
            Dictionary with universe statistics
        """
        symbols = self.get_universe(
            start_date=start_date,
            end_date=end_date,
            include_delisted=True,
            include_spun_off=True,
        )

        sectors = self.get_sector_diversification(symbols)

        return {
            "total_symbols": len(symbols),
            "sectors": {k: len(v) for k, v in sectors.items()},
            "delisted_included": sum(
                1
                for s in symbols
                for entry in self.universe["delisted"]
                if s == entry[0]
            ),
            "acquired_included": sum(
                1
                for s in symbols
                for entry in self.universe["spun_off"]
                if s == entry[0]
            ),
        }
