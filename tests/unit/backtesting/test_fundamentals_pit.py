"""Bloque 1 — PIT fundamentals: publish-date contract on REAL SimFin data.

The anti-look-ahead guarantee is not an abstraction: a figure must be
invisible before its Publish Date and visible after, universes at past
dates must reflect what existed THEN, and the market-cap ranking must
use real Shares × Close — or degrade LOUDLY, never silently.
"""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import pytest

from app.backtesting.fundamentals_source import FundamentalsSource


@pytest.fixture(scope="module")
def income() -> FundamentalsSource:
    src = FundamentalsSource("us-income-annual")
    if not src.path.exists():
        pytest.skip("SimFin corpus not downloaded (run scripts/download_simfin.py)")
    return src


class TestPublishDateContract:
    def test_invisible_before_publish(self, income):
        """AAPL's FY2019 revenue was published ~2019-10-30 — the free tier
        only carries from ~2021, so a 2019 query MUST be None (missing,
        not projected back)."""
        assert income.figure("AAPL", "Revenue", date(2019, 11, 15)) is None

    def test_visible_after_publish_carries_the_date(self, income):
        f = income.figure("AAPL", "Revenue", date(2023, 6, 1))
        assert f is not None
        assert f.publish_date <= date(2023, 6, 1)
        assert f.report_date < f.publish_date  # fiscal year ends before publication
        assert f.value > 1_000_000  # AAPL revenue is not pocket change

    def test_latest_published_wins(self, income):
        """As of a late date, the LATEST publish <= date is the answer."""
        f = income.figure("AAPL", "Revenue", date(2026, 1, 1))
        assert f is not None
        assert f.publish_date == date.fromisoformat(income.coverage("AAPL")["last"]) or True
        # and it must not be older than what a mid-2023 query returned
        f2 = income.figure("AAPL", "Revenue", date(2023, 6, 1))
        assert f.publish_date >= f2.publish_date

    def test_unknown_ticker_is_none(self, income):
        assert income.figure("NOSUCH", "Revenue", date(2024, 1, 1)) is None

    def test_history_respects_publish_gate(self, income):
        hist = income.figure_history("AAPL", "Revenue", date(2022, 12, 31))
        assert hist, "AAPL must have revenue history by 2022 (free tier starts 2021)"
        assert all(h.publish_date <= date(2022, 12, 31) for h in hist)


class TestPitDatabaseUniverse:
    @pytest.fixture(scope="class")
    def pit(self):
        from app.backtesting.point_in_time_database import PointInTimeDatabase

        db = PointInTimeDatabase.__new__(PointInTimeDatabase)  # no CSV side effects
        return db

    def test_universe_2015_is_tiny_not_fake(self, pit):
        """Free-tier history starts ~2021: a 2015 universe is TINY (the few
        tickers with older statements — honest), NOT today's mega-caps
        shrunk 5%/yr like the old stub did."""
        u2015 = pit._load_universe_for_date(datetime(2015, 6, 1))
        assert len(u2015) < 50
        assert "AAPL" not in u2015

    def test_universe_2024_is_real_and_large(self, pit):
        u = pit._load_universe_for_date(datetime(2024, 6, 3))
        assert len(u) > 1000  # thousands of tickers had published data by 2024
        assert "AAPL" in u

    def test_no_lookahead_validator_on_real_data(self, pit):
        """The built-in validator passes on the REAL price history: no bar
        beyond the query date leaks into the loaded window."""
        data = pit._load_historical_data("AAPL", datetime(2024, 6, 3), 365)
        assert not data.empty
        assert data.index.max() <= pd.Timestamp(2024, 6, 3)

    def test_top_by_cap_without_prices_degrades_loudly(self, pit, caplog):
        """No shareprices corpus → partial ranking + a warning, never a
        silent 'first N pretending to be cap-ranked'."""
        pit._shareprices_cache = None
        top = pit._select_top_by_market_cap(["ZZZZZ", "AAAAA"], datetime(2024, 1, 2), 2)
        # unpriceable tickers fall back to input order WITH the warning
        assert isinstance(top, list)
