"""Tests for scripts/import_news_archive.py (news archive → sentiment series)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "import_news_archive.py"

_spec = importlib.util.spec_from_file_location("import_news_archive", SCRIPT_PATH)
importer = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
sys.modules.setdefault("import_news_archive", importer)
assert _spec.loader is not None
_spec.loader.exec_module(importer)

NEWS_CSV = """title,date,stock
Apple surges to record high on blowout earnings,2020-06-01 10:00:00-04:00,AAPL
Apple misses estimates and plunges,2020-06-01 16:00:00-04:00,AAPL
Analysts upgrade Tesla sharply higher,2020-06-02 09:30:00-04:00,TSLA
Tesla not profitable this quarter,2020-06-03 09:30:00-04:00,TSLA
Weekly market wrap,2020-06-03 18:00:00-04:00,TSLA
GE wins major contract,2020-06-04 09:30:00-04:00,GE
"""


def test_score_headline_polarity_and_negation() -> None:
    assert importer.score_headline("Apple surges to record high on blowout earnings") > 0.5
    assert importer.score_headline("Apple misses estimates and plunges") < -0.5
    # negation flips the following scored word
    assert importer.score_headline("profit") > 0
    assert importer.score_headline("not profitable") < 0
    # intensifier amplifies
    assert importer.score_headline("sharply higher") > importer.score_headline("higher")
    # no lexicon words → exactly neutral
    assert importer.score_headline("Weekly market wrap") == 0.0
    # bounded to [-1, 1] however many hits
    score = importer.score_headline("surges soars rallies bullish beats upbeat")
    assert -1.0 <= score <= 1.0 and score > 0.9  # tanh saturates near 1


def test_pick_column_matches_both_archive_schemas() -> None:
    assert importer._pick_column(["title", "date", "stock"], importer.TEXT_COLUMNS) == "title"
    assert (
        importer._pick_column(
            ["", "headline", "url", "publisher", "date", "stock"], importer.TEXT_COLUMNS
        )
        == "headline"
    )
    with pytest.raises(ValueError):
        importer._pick_column(["a", "b"], importer.DATE_COLUMNS)


def test_import_aggregates_daily_per_symbol(tmp_path: Path) -> None:
    source = tmp_path / "news.csv"
    source.write_text(NEWS_CSV)
    out_dir = tmp_path / "sentiment"

    exit_code = importer.main(["--csv", str(source), "--out", str(out_dir)])

    assert exit_code == 0
    aapl = pd.read_csv(out_dir / "AAPL.csv")
    assert list(aapl.columns) == ["date", "news_count", "sentiment_mean", "sentiment_sum"]
    # both AAPL headlines land on 2020-06-01: count aggregates, mean averages them
    day = aapl[aapl["date"] == "2020-06-01"].iloc[0]
    assert day["news_count"] == 2
    assert day["sentiment_mean"] == pytest.approx(
        (
            importer.score_headline("Apple surges to record high on blowout earnings")
            + importer.score_headline("Apple misses estimates and plunges")
        )
        / 2,
        abs=1e-6,  # output is rounded to 6 decimals
    )
    tsla = pd.read_csv(out_dir / "TSLA.csv")
    assert len(tsla) == 2  # 06-02 and 06-03
    assert list(tsla["date"]) == sorted(tsla["date"])
    assert (out_dir / "GE.csv").exists()


def test_symbols_filter_and_skip_existing(tmp_path: Path) -> None:
    source = tmp_path / "news.csv"
    source.write_text(NEWS_CSV)
    out_dir = tmp_path / "sentiment"
    out_dir.mkdir()
    sentinel = out_dir / "AAPL.csv"
    sentinel.write_text("sentinel\n")

    assert (
        importer.main(["--csv", str(source), "--symbols", "AAPL", "GE", "--out", str(out_dir)]) == 0
    )
    assert sentinel.read_text() == "sentinel\n"  # kept without --overwrite
    assert not (out_dir / "TSLA.csv").exists()
    assert (out_dir / "GE.csv").exists()

    # a requested symbol absent from the archive exits non-zero
    assert importer.main(["--csv", str(source), "--symbols", "ZZZZ", "--out", str(out_dir)]) == 1
