"""Bloque 2 — Dividend Safety Score: fórmula pública, PIT, validación empírica.

Validación (T2.4) dentro de la ventana del tier gratis (~2021+):
- LUMN recortó en 2022 por ESTRÉS (apalancamiento) → el score a fin-2021
  lo deja POR DEBAJO del umbral: discrimina el caso que un score de
  ratios puede discriminar.
- T (reset post-spin 2022) e INTC (recorte 2024 por capex, FFO cubría)
  NO son visibles para ratios por naturaleza — documentado como límite.
- La validación COVID-2020 del plan original es IMPOSIBLE sin
  fundamentales pre-2020 (limitación del tier gratis, declarada).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.backtesting.dividend_safety import DEFAULT_WEIGHTS, DividendSafetyScorer


@pytest.fixture(scope="module")
def scorer():
    s = DividendSafetyScorer()
    if not s.income.path.exists():
        pytest.skip("SimFin corpus not downloaded")
    return s


class TestEmpiricalValidation:
    def test_distress_cutter_lumn_below_threshold(self, scorer):
        """LUMN recortó 2022 por estrés; a fin-2021 el score lo excluye."""
        r = scorer.score("LUMN", date(2021, 12, 31))
        assert r.computable
        assert r.score < Decimal("60")

    def test_maintainers_above_threshold(self, scorer):
        for t in ("MSFT", "JNJ"):
            r = scorer.score(t, date(2023, 12, 31))
            assert r.computable, (t, r.gaps)
            assert r.score >= Decimal("60"), (t, r.score)

    def test_strategic_resets_are_a_documented_limit(self, scorer):
        """T/INTC recortaron por ESTRATEGIA (spin/capex) con FFO cubriendo
        el pago: un score de ratios no puede verlos — se fija el hecho
        para que nadie crea que el score los predice."""
        t_reset = scorer.score("T", date(2021, 12, 31))
        assert t_reset.score >= Decimal("60")  # no flag — y así se documenta
        intc = scorer.score("INTC", date(2023, 12, 31))
        assert intc.score >= Decimal("60")


class TestPitContract:
    def test_before_any_publication_is_zero_with_gaps(self, scorer):
        r = scorer.score("VZ", date(2020, 6, 1))  # free tier starts ~2021
        assert r.score == Decimal("0")
        assert r.gaps  # the WHY is in the report

    def test_weights_are_public_and_reproducible(self, scorer):
        r = scorer.score("MSFT", date(2023, 12, 31))
        assert r.weights == DEFAULT_WEIGHTS
        assert r.to_dict()["formula"]  # the formula ships with every report

    def test_custom_weights_change_the_result_deterministically(self):
        base = DividendSafetyScorer()
        heavy_solvency = DividendSafetyScorer(
            weights={**DEFAULT_WEIGHTS, "solvencia": 50, "cobertura": 10}
        )
        as_of = date(2021, 12, 31)
        s_base = base.score("LUMN", as_of).score
        s_heavy = heavy_solvency.score("LUMN", as_of).score
        assert s_base != s_heavy  # configurable and reproducible, not magic


class TestUniverseFilter:
    def test_filter_excludes_distress_and_non_computable(self, scorer):
        inside, outside, reports = scorer.universe_filter(
            ["MSFT", "LUMN", "VZ"], date(2021, 12, 31), min_score=Decimal("60")
        )
        assert "MSFT" in inside
        assert "LUMN" in outside
        assert "VZ" in outside  # non-computable NEVER passes silently
        by_ticker = {r.ticker: r for r in reports}
        assert by_ticker["VZ"].gaps

    def test_golden_scores_pinned(self, scorer):
        """Golden pins: same corpus + weights → same numbers. If the data
        or the formula change, these FAIL loudly instead of drifting."""
        pins = {
            ("MSFT", "2023-12-31"): "94.1",
            ("JNJ", "2023-12-31"): "89.2",
            ("INTC", "2023-12-31"): "86.9",
            ("LUMN", "2021-12-31"): "58.3",
        }
        for (ticker, as_of), expected in pins.items():
            got = scorer.score(ticker, date.fromisoformat(as_of)).score
            assert str(got) == expected, (
                f"{ticker}@{as_of}: {got} ≠ {expected} (¿corpus o fórmula cambiaron?)"
            )
