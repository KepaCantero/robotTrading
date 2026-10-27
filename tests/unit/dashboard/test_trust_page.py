"""UI-4 — the trust layer: real worst-year math, honest live door."""

from __future__ import annotations

import csv
from pathlib import Path

from app.presentation.dashboard.nicegui_app.pages.trust import _narration, worst_12_months


def _write(path: Path, symbol: str, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path / f"{symbol}.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "Open", "High", "Low", "Close", "Volume"])
        w.writerows(rows)


class TestWorst12Months:
    def test_known_crash_measured_exactly(self, tmp_path):
        from datetime import date, timedelta

        d0 = date(2020, 1, 1)
        rows = []
        # −40% crash held LONG enough to sit alone inside a 252-day window
        for i in range(560):
            px = 100.0 if i < 100 else (60.0 if i < 400 else 100.0)
            day = (d0 + timedelta(days=i)).isoformat()
            rows.append([day, px, px, px, px, 1000])
        _write(tmp_path, "AAA", rows)
        _write(tmp_path, "BBB", rows)

        result = worst_12_months(["AAA", "BBB"], data_dir=tmp_path)
        assert result is not None
        pct, _day = result
        assert -45 < pct < -35  # the −40% stretch, measured not asserted

    def test_insufficient_history_is_none(self, tmp_path):
        _write(tmp_path, "AAA", [[f"2024-01-{d:02d}", 100, 100, 100, 100, 1] for d in range(1, 11)])
        assert worst_12_months(["AAA", "BBB"], data_dir=tmp_path) is None

    def test_real_corpus_answers(self):
        pct, day = worst_12_months(["SCHD", "VYM", "VIG", "DVY", "BND"])
        assert pct < -10  # 2022 hit dividend mixes hard — the number must show it
        assert day[:2] == "20"


class TestNarration:
    def test_event_types_get_plain_lines(self):
        assert "started" in _narration("run_started").lower()
        assert "failed" in _narration("run_failed").lower()
