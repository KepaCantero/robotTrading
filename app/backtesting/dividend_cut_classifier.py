"""Bloque 2 (T2.6) — dividend-cut classifier with CONFORMAL prediction.

A plain classifier says "cut 62%" and forces a decision. A conformal
classifier (MAPIE, split-conformal LAC) returns a 90% PREDICTION SET:
{cut}, {no-cut} or {both}. "Both" = the honest abstention — "no
clasificable con confianza" — which is exactly what a novice-facing
product should say instead of a coin flip dressed as a probability.

Dataset: snapshots at as_of dates; features = the five score factors'
points + the raw ratios; label = dividends paid fell ≥5% the NEXT fiscal
year (computed only from figures PUBLISHED after the fact — labels look
forward by construction, features never do).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

import numpy as np

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

#: abstención por defecto: conjuntos al 90% de confianza
DEFAULT_ALPHA = 0.10


@dataclass
class CutDataset:
    """Snapshot rows for the classifier (features NEVER look ahead)."""

    X: np.ndarray
    y: np.ndarray  # 1 = recorte, 0 = mantenido
    tickers: list[str]
    as_of: list[date] = field(default_factory=list)


def build_dataset(
    snapshot_dates: list[date],
    tickers: list[str] | None = None,
    data_dir: Path | None = None,
) -> CutDataset:
    """One row per (ticker, snapshot) with a KNOWN next-year outcome."""
    from app.backtesting.dividend_safety import DividendSafetyScorer

    scorer = DividendSafetyScorer(data_dir=data_dir)
    rows, labels, tk, dates = [], [], [], []
    universe = tickers or scorer.income.tickers()
    for as_of in snapshot_dates:
        for ticker in universe:
            report = scorer.score(ticker, as_of)
            if not report.computable:
                continue  # gaps never train the classifier
            paid = scorer._paid_dividends(ticker, as_of)  # noqa: SLF001
            by_year = {}
            for d, amount in paid:
                by_year[d.year] = amount
            this_year = by_year.get(as_of.year - 1) or (paid[-1][1] if paid else None)
            next_year = by_year.get(as_of.year)
            if this_year is None or next_year is None or this_year <= 0:
                continue  # outcome unknown → excluded, not invented
            cut = next_year < this_year * Decimal("0.95")
            rows.append([float(f.points) for f in report.factors])
            labels.append(1 if cut else 0)
            tk.append(ticker)
            dates.append(as_of)
    return CutDataset(
        X=np.array(rows, dtype=float).reshape(-1, 5),
        y=np.array(labels, dtype=int),
        tickers=tk,
        as_of=dates,
    )


class ConformalCutClassifier:
    """Logistic cut-classifier + MAPIE split-conformal sets at 1-α."""

    def __init__(self, alpha: float = DEFAULT_ALPHA, random_state: int = 77001):
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        self.alpha = alpha
        self.random_state = random_state
        self._scaler = StandardScaler()
        self._model = LogisticRegression(max_iter=1000, class_weight="balanced")
        self._mapie = None

    def fit(self, train: CutDataset, calibration: CutDataset) -> "ConformalCutClassifier":
        # mapie 1.6: SplitConformalClassifier, LAC conformity (least
        # ambiguous set-valued) at the constructor's confidence_level
        from mapie.classification import SplitConformalClassifier

        X_tr = self._scaler.fit_transform(train.X)
        self._model.fit(X_tr, train.y)
        self._mapie = SplitConformalClassifier(
            self._model, confidence_level=1 - self.alpha, conformity_score="lac", prefit=True
        )
        self._mapie.conformalize(self._scaler.transform(calibration.X), calibration.y)
        return self

    def predict_set(self, row: np.ndarray) -> set[int]:
        """90% prediction set: {0}, {1} or {0,1} (the abstention)."""
        if self._mapie is None:
            raise RuntimeError("fit first")
        # mapie 1.6: predict_set → (y_pred, sets[n, n_classes])
        _, sets = self._mapie.predict_set(self._scaler.transform(row.reshape(1, -1)))
        classes = self._model.classes_
        return {int(classes[i]) for i, flag in enumerate(sets[0]) if flag}

    def verdict(self, row: np.ndarray) -> dict:
        """Novice-facing verdict with the abstención state explicit."""
        pred_set = self.predict_set(row)
        if pred_set == {0, 1} or len(pred_set) != 1:
            state = "abstencion"
            label = None
        else:
            only = next(iter(pred_set))
            state = "decisivo"
            label = "recorte" if only == 1 else "mantenido"
        return {"estado": state, "prediccion": label, "confianza": f"{1 - self.alpha:.0%}"}


def walk_forward_coverage(
    snapshots: list[date],
    tickers: list[str] | None = None,
    alpha: float = DEFAULT_ALPHA,
    data_dir: Path | None = None,
) -> dict:
    """Train on earlier snapshots, evaluate the NEXT one; report coverage.

    Coverage = fraction of decisive+abstaining rows whose TRUE label is
    inside the predicted set (the conformal guarantee we measure, not
    assume). Abstention rate is reported alongside — published with the
    score per the plan.
    """
    datasets = {d: build_dataset([d], tickers, data_dir) for d in snapshots}
    results = {}
    for i, eval_date in enumerate(snapshots[1:], start=1):
        # all snapshots BEFORE the calibration one, concatenated; with
        # only two snapshots left of `eval` this may be empty → skipped
        if i - 1 == 0:
            results[eval_date.isoformat()] = {"estado": "sin snapshots previos suficientes"}
            continue
        train = _concat(datasets[snapshots[j]] for j in range(i - 1))
        calib = datasets[snapshots[i - 1]]
        test = datasets[eval_date]
        if len(set(train.y)) < 2 or len(set(calib.y)) < 2 or len(test.y) == 0:
            results[eval_date.isoformat()] = {"estado": "datos insuficientes"}
            continue
        clf = ConformalCutClassifier(alpha=alpha).fit(train, calib)
        covered = 0
        decisive = 0
        for row, y_true in zip(test.X, test.y):
            pred_set = clf.predict_set(row)
            if len(pred_set) == 1:
                decisive += 1
            if int(y_true) in pred_set:
                covered += 1
        n = len(test.y)
        results[eval_date.isoformat()] = {
            "n": n,
            "cobertura": round(covered / n, 4),
            "abstencion": round(1 - decisive / n, 4),
            "garantia": f"{1 - alpha:.0%}",
        }
    return results


def _concat(datasets) -> CutDataset:
    parts = list(datasets)
    return CutDataset(
        X=np.vstack([p.X for p in parts]),
        y=np.concatenate([p.y for p in parts]),
        tickers=[t for p in parts for t in p.tickers],
        as_of=[d for p in parts for d in p.as_of],
    )
