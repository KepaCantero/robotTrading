"""Bloque 2 (T2.6) — conformal cut classifier: sets, abstention, measured coverage."""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from app.backtesting.dividend_cut_classifier import (
    ConformalCutClassifier,
    CutDataset,
    walk_forward_coverage,
)


def _blobs(rng, n, sep):
    X = rng.normal(size=(n, 5))
    X[: n // 2, 0] -= sep
    X[n // 2 :, 0] += sep
    y = np.array([0] * (n // 2) + [1] * (n // 2))
    idx = rng.permutation(n)  # interleave classes so every split is 2-class
    return X[idx], y[idx]


class TestSyntheticConformal:
    def test_separable_is_decisive_and_covers(self):
        rng = np.random.default_rng(0)
        X, y = _blobs(rng, 600, 3.0)
        train = CutDataset(X[:200], y[:200], ["t"] * 200)
        calib = CutDataset(X[200:400], y[200:400], ["t"] * 200)
        clf = ConformalCutClassifier().fit(train, calib)
        covered = decisive = 0
        for row, yy in zip(X[400:], y[400:]):
            s = clf.predict_set(row)
            decisive += len(s) == 1
            covered += int(yy) in s
        assert decisive >= 170  # claramente separable → casi todo decisivo
        assert covered / 200 >= 0.85  # la garantía 90% se CUMPLE empíricamente

    def test_overlapping_produces_abstentions(self):
        rng = np.random.default_rng(1)
        X, y = _blobs(rng, 600, 0.15)  # casi indistinguibles
        train = CutDataset(X[:200], y[:200], ["t"] * 200)
        calib = CutDataset(X[200:400], y[200:400], ["t"] * 200)
        clf = ConformalCutClassifier().fit(train, calib)
        abstentions = sum(len(clf.predict_set(r)) != 1 for r in X[400:])
        assert abstentions > 0  # la honestidad existe: sets {0,1}

    def test_verdict_states_abstencion(self):
        rng = np.random.default_rng(2)
        X, y = _blobs(rng, 600, 0.1)
        train = CutDataset(X[:200], y[:200], ["t"] * 200)
        calib = CutDataset(X[200:400], y[200:400], ["t"] * 200)
        clf = ConformalCutClassifier().fit(train, calib)
        states = {clf.verdict(r)["estado"] for r in X[400:]}
        assert states <= {"decisivo", "abstencion"}
        v = clf.verdict(X[0])
        assert v["confianza"] == "90%"


class TestRealWalkForward:
    def test_measured_coverage_meets_the_guarantee(self):
        """Sobre el corpus SimFin real: cobertura medida ≥ 0.85 con
        garantía del 90% y abstención declarada — publicado con el score."""
        cov = walk_forward_coverage([date(2022, 12, 31), date(2023, 12, 31), date(2024, 12, 31)])
        last = cov["2024-12-31"]
        if last.get("estado") == "datos insuficientes":
            pytest.skip("corpus sin snapshots suficientes")
        assert last["n"] > 100
        assert last["cobertura"] >= 0.85
        assert 0.0 < last["abstencion"] < 0.5
        assert last["garantia"] == "90%"
