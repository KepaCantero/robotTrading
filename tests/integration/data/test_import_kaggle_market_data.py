"""Integration tests for scripts/import_kaggle_market_data.py.

Builds a synthetic archive mixing both Kaggle layouts — Stooq
(Data/Stocks/*.us.txt, "Huge Stock Market Dataset") and folder
(stocks/*.csv with Adj Close, "Stock Market Dataset") — and checks the
converter output against the real backtesting DataLoader.
"""

from __future__ import annotations

import importlib.util
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from app.backtesting.data_loader import DataLoader

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "import_kaggle_market_data.py"

_spec = importlib.util.spec_from_file_location("import_kaggle_market_data", SCRIPT_PATH)
importer = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
sys.modules.setdefault("import_kaggle_market_data", importer)
assert _spec.loader is not None
_spec.loader.exec_module(importer)

AAPL_TXT = """Date,Open,High,Low,Close,Volume
2000-01-03,104.87,112.50,101.69,111.94,4783900
2000-01-04,108.25,110.62,101.19,102.50,4574800
2000-01-05,103.75,110.62,99.50,104.00,6897600
2000-01-05,103.75,110.62,99.50,104.00,6897600
2000-01-06,200.00,90.00,89.00,95.00,1000
2000-01-07,0,0,0,0,1000
"""

GE_TXT = """Date,Open,High,Low,Close,Volume
2010-01-04,15.10,15.40,15.00,15.30,100000
2010-01-05,15.30,15.80,15.20,15.70,120000
2010-01-06,15.70,16.00,15.50,15.90,90000
2010-01-07,0,16.10,15.60,16.00,80000
"""

SPY_TXT = """Date,Open,High,Low,Close,Volume
2010-01-04,113.00,113.50,112.60,113.20,900000
2010-01-05,113.20,114.00,113.00,113.80,850000
2010-01-06,113.80,114.20,113.10,113.90,700000
"""

ADJ_TXT = """Date,Open,High,Low,Close,Volume,Adjusted Close
2010-01-04,20.00,21.00,19.50,20.50,1000,10.25
2010-01-05,20.50,22.00,20.00,21.00,1100,10.50
"""

ZZZ_TXT = """Date,Open,High,Low,Close,Volume
2010-01-04,5.00,5.20,4.90,5.10,1000
2010-01-05,5.10,5.30,5.00,5.20,1100
"""

# jacksoncrow "Stock Market Dataset" layout: stocks/<TICKER>.csv, Yahoo
# columns with Adj Close (frozen ~2020).
INTC_CSV = """Date,Open,High,Low,Close,Adj Close,Volume
2010-01-04,20.80,21.00,20.40,20.90,17.72,55000000
2010-01-05,20.90,21.30,20.60,21.10,17.89,44000000
2010-01-06,21.10,21.80,21.00,21.60,18.36,47000000
"""

META_CSV = """symbol,name
A,Agilent Technologies
AAPL,Apple Inc.
"""


def _make_archive(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Data/Stocks/aapl.us.txt", AAPL_TXT)
        archive.writestr("Data/Stocks/ge.us.txt", GE_TXT)
        archive.writestr("Data/Stocks/adj.us.txt", ADJ_TXT)
        archive.writestr("Data/Stocks/zzz.us.txt", ZZZ_TXT)
        archive.writestr("Data/ETFs/spy.us.txt", SPY_TXT)
        archive.writestr("stocks/intc.csv", INTC_CSV)
        archive.writestr("symbols_valid_meta.csv", META_CSV)
    return path


def test_kaggle_stem_strips_us_suffix_and_uppercases() -> None:
    assert importer.kaggle_stem("aapl.us.txt") == "AAPL"
    assert importer.kaggle_stem("Data/Stocks/ge.us.txt") == "GE"
    assert importer.kaggle_stem("brk-b.us.txt") == "BRK-B"


def test_source_stem_recognizes_both_layouts_and_ignores_metadata() -> None:
    assert importer.source_stem("Data/Stocks/aapl.us.txt") == "AAPL"
    assert importer.source_stem("stocks/intc.csv") == "INTC"
    assert importer.source_stem("etfs/schx.csv") == "SCHX"
    assert importer.source_stem("symbols_valid_meta.csv") is None
    assert importer.source_stem("Data/Stocks/notes.txt") is None


def test_import_converts_zip_to_loader_schema(tmp_path: Path) -> None:
    archive = _make_archive(tmp_path / "dataset.zip")
    out_dir = tmp_path / "historical"

    exit_code = importer.main(
        ["--zip", str(archive), "--tickers", "AAPL", "GE", "--out", str(out_dir)]
    )

    assert exit_code == 0
    header = (out_dir / "AAPL.csv").read_text().splitlines()[0]
    assert header == "date,Open,High,Low,Close,Volume"
    frame = pd.read_csv(out_dir / "AAPL.csv", index_col="date")
    # 6 rows in: one duplicate date, one OHLC-incoherent, one all-zero → 3 survive
    assert len(frame) == 3
    assert list(frame.index) == sorted(frame.index)
    assert "2000-01-06" not in frame.index
    assert (out_dir / "GE.csv").exists()


def test_existing_csvs_are_kept_without_overwrite(tmp_path: Path) -> None:
    archive = _make_archive(tmp_path / "dataset.zip")
    out_dir = tmp_path / "historical"
    out_dir.mkdir()
    sentinel = out_dir / "AAPL.csv"
    sentinel.write_text("sentinel\n")

    assert importer.main(["--zip", str(archive), "--out", str(out_dir)]) == 0
    assert sentinel.read_text() == "sentinel\n"

    assert importer.main(["--zip", str(archive), "--out", str(out_dir), "--overwrite"]) == 0
    assert sentinel.read_text().startswith("date,Open")


def test_etfs_are_opt_in(tmp_path: Path) -> None:
    archive = _make_archive(tmp_path / "dataset.zip")
    out_dir = tmp_path / "historical"

    importer.main(["--zip", str(archive), "--out", str(out_dir)])
    assert not (out_dir / "SPY.csv").exists()

    importer.main(["--zip", str(archive), "--out", str(out_dir), "--etfs"])
    assert (out_dir / "SPY.csv").exists()


def test_min_rows_skips_tiny_files_and_requested_missing_fail(tmp_path: Path) -> None:
    archive = _make_archive(tmp_path / "dataset.zip")
    out_dir = tmp_path / "historical"

    exit_code = importer.main(
        ["--zip", str(archive), "--tickers", "ZZZ", "--min-rows", "3", "--out", str(out_dir)]
    )

    assert exit_code == 1
    assert not (out_dir / "ZZZ.csv").exists()


def test_adjusted_close_column_rescales_ohlc(tmp_path: Path) -> None:
    archive = _make_archive(tmp_path / "dataset.zip")
    out_dir = tmp_path / "historical"

    importer.main(["--zip", str(archive), "--tickers", "ADJ", "--out", str(out_dir)])

    frame = pd.read_csv(out_dir / "ADJ.csv", index_col="date")
    assert frame.loc["2010-01-04", "Close"] == 10.25
    assert frame.loc["2010-01-04", "Open"] == 10.0
    assert frame.loc["2010-01-05", "High"] == 11.0


def test_roundtrip_through_backtesting_data_loader(tmp_path: Path) -> None:
    archive = _make_archive(tmp_path / "dataset.zip")
    out_dir = tmp_path / "historical"

    importer.main(["--zip", str(archive), "--tickers", "GE", "--out", str(out_dir)])

    loader = DataLoader(base_path=out_dir)
    quotes = loader.load_market_data("GE", datetime(2010, 1, 1), datetime(2010, 2, 1))
    assert len(quotes) == 4
    assert float(quotes[0].close) == 15.30
    assert float(quotes[0].high) == 15.40
    assert [quote.timestamp.day for quote in quotes] == [4, 5, 6, 7]
    # the Open=0 row is repaired open→close, not dropped
    assert float(quotes[-1].open) == 16.00


def test_folder_layout_csv_rescales_and_meta_stays_out(tmp_path: Path) -> None:
    archive = _make_archive(tmp_path / "dataset.zip")
    out_dir = tmp_path / "historical"

    exit_code = importer.main(["--zip", str(archive), "--tickers", "INTC", "--out", str(out_dir)])

    assert exit_code == 0
    frame = pd.read_csv(out_dir / "INTC.csv", index_col="date")
    # OHLC rescaled by adj/close (17.72/20.90 ≈ 0.84785…): Close == Adj Close
    assert frame.loc["2010-01-04", "Close"] == 17.72
    assert frame.loc["2010-01-04", "Open"] == pytest.approx(20.80 * 17.72 / 20.90)
    assert frame.loc["2010-01-06", "High"] == pytest.approx(21.80 * 18.36 / 21.60)
    assert not (out_dir / "SYMBOLS_VALID_META.csv").exists()


def test_dir_mode_walks_extracted_tree(tmp_path: Path) -> None:
    archive = _make_archive(tmp_path / "dataset.zip")
    extracted = tmp_path / "extracted"
    with zipfile.ZipFile(archive) as handle:
        handle.extractall(extracted)
    out_dir = tmp_path / "historical"

    exit_code = importer.main(["--dir", str(extracted), "--out", str(out_dir)])

    assert exit_code == 0
    assert (out_dir / "AAPL.csv").exists()
    assert (out_dir / "INTC.csv").exists()
    assert not (out_dir / "SPY.csv").exists()  # etfs still opt-in in dir mode
