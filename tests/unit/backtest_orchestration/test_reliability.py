"""Fiabilidad (30-10): abanico bootstrap, retiradas, estrés y el
portfolio real en buy&hold — la matemática, determinista y honesta."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.backtesting.acceptance.monte_carlo_validator import MonteCarloValidator
from app.services.backtest_orchestration.reliability import (
    bootstrap_portfolio,
    daily_returns,
    portfolio_buyhold,
    stress_windows,
    withdrawal_sequences,
)


def _write_csv(folder, symbol: str, dates, closes) -> None:
    pd.DataFrame({"date": dates, "Close": closes}).to_csv(folder / f"{symbol}.csv", index=False)


class TestBootstrap:
    def test_constant_returns_collapse_all_percentiles(self):
        boot = bootstrap_portfolio(np.full(300, 0.01), n_paths=50)
        assert abs(boot["final_p05"] - 1.01**300) < 0.01
        assert boot["final_p95"] == boot["final_p05"]
        assert boot["prob_loss"] == 0.0
        assert boot["max_dd_p05"] == 0.0

    def test_deterministic_with_fixed_seed(self):
        rng = np.random.default_rng(7)
        rets = rng.normal(0.0004, 0.012, 800)
        assert bootstrap_portfolio(rets, n_paths=100) == bootstrap_portfolio(rets, n_paths=100)

    def test_bands_shape_and_p5_feeds_validator(self):
        rng = np.random.default_rng(3)
        boot = bootstrap_portfolio(rng.normal(0.0003, 0.01, 1000), n_paths=200)
        assert len(boot["bands"]) == 5
        assert all(len(band) == len(boot["bands"][0]) for band in boot["bands"])
        # el abanico es a través de CAMINOS: P5 ≤ P25 ≤ mediana ≤ P75 ≤ P95
        # en cada instante (axis equivocado = cuantiles por camino, no abanico)
        for t in range(len(boot["bands"][0])):
            assert (
                boot["bands"][0][t]
                <= boot["bands"][1][t]
                <= boot["bands"][2][t]
                <= boot["bands"][3][t]
                <= boot["bands"][4][t] + 1e-6
            )
        criterion = MonteCarloValidator().validate(boot["p5_return"])
        assert criterion.passed == (boot["p5_return"] >= -0.20)

    def test_too_few_returns_returns_none(self):
        assert bootstrap_portfolio(np.full(30, 0.01)) is None


class TestWithdrawal:
    def test_zero_returns_huge_withdrawal_exhausts(self):
        res = withdrawal_sequences(np.zeros(300), withdrawal_rate_annual=2.0, n_paths=20)
        assert res["prob_exhausted"] == 1.0

    def test_zero_returns_small_withdrawal_survives(self):
        res = withdrawal_sequences(np.zeros(300), withdrawal_rate_annual=0.02, n_paths=20)
        assert res["prob_exhausted"] == 0.0
        assert abs(res["final_p50"] - (1 - 0.02 / 12 * 14)) < 0.01


class TestStressAndBuyHold:
    def test_stress_windows_ew_drawdown(self, tmp_path):
        dates = pd.date_range("2020-01-01", "2020-04-30", freq="B")
        labels = [d.strftime("%Y-%m-%d") for d in dates]
        # el crash ocurre DENTRO de la ventana COVID (feb 19 → mar 23):
        # plano 100 → -50% lineal dentro de la ventana → plano
        crash = []
        for d in dates:
            if d < pd.Timestamp("2020-02-19"):
                crash.append(100.0)
            elif d <= pd.Timestamp("2020-03-23"):
                span = (d - pd.Timestamp("2020-02-19")).days
                total = (pd.Timestamp("2020-03-23") - pd.Timestamp("2020-02-19")).days
                crash.append(100.0 - 50.0 * span / total)
            else:
                crash.append(50.0)
        _write_csv(tmp_path, "FLAT", labels, np.full(len(dates), 100.0))
        _write_csv(tmp_path, "CRASH", labels, crash)

        stress = stress_windows(["FLAT", "CRASH", "MISSING"], tmp_path)
        covid = stress["COVID crash (Feb–Mar 2020)"]
        # equiponderado: mitad plana, mitad -50% dentro de la ventana → dd ≈ -25%
        assert covid["symbols_used"] == 2
        assert -0.30 < covid["max_drawdown"] < -0.20

    def test_portfolio_buyhold_weights_and_coverage(self, tmp_path):
        dates = pd.date_range("2020-01-01", "2020-12-31", freq="B")
        labels = [d.strftime("%Y-%m-%d") for d in dates]
        _write_csv(tmp_path, "AAA", labels, np.linspace(100, 200, len(dates)))  # +100%
        _write_csv(tmp_path, "BBB", labels, np.full(len(dates), 100.0))  # 0%

        sim = portfolio_buyhold(
            {"AAA": 0.75, "BBB": 0.25, "NOCSV": 0.10}, "2020-01-01", "2020-12-31", tmp_path
        )
        # pesos renormalizados sobre los que cubren: 75/100 AAA → +75%
        assert sim["symbols_used"] == ["AAA", "BBB"]
        assert "NOCSV" in sim["symbols_missing"]
        assert abs(sim["total_return"] - 0.75) < 0.01
        assert sim["weight_covered"] == 1.0

    def test_daily_returns_from_equity(self):
        rets = daily_returns([("2026-01-01", "100"), ("2026-01-02", "110"), ("2026-01-03", "99")])
        assert np.allclose(rets, [0.10, -0.10])
