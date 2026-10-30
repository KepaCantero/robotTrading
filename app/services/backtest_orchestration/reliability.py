"""Fiabilidad de la cartera examinada (30-10): el abanico, no solo el camino.

Tres análisis sobre los retornos DIARIOS de la cartera REAL que el run
ejecutó (correlaciones y costes ya embebidos en la serie — remuestrear
por activo suelto inventaría diversificación falsa):

1. ``bootstrap_portfolio`` — bootstrap circular por bloques de la serie
   de retornos → distribución de riqueza futura para un horizonte igual
   al testado. P5/mediana/P95, probabilidad de pérdida, drawdown P5 y
   las bandas temporales del gráfico de abanico. El ``p5_return``
   alimenta el ``MonteCarloValidator`` (P5 ≥ −20%), que por fin juzga
   datos reales.
2. ``withdrawal_sequences`` — secuencias de rendimientos (sequence
   risk): retirada fija anual (4%, cobro mensual) sobre riqueza inicial
   → probabilidad de agotar y P5 de riqueza final. La pregunta de
   VIVIR_DE_LA_CARTERA.
3. ``stress_windows`` — replay del equiponderado del universo sobre dos
   ventanas reales de estrés (COVID 2020, subida de tipos 2022) con los
   CSV locales.
4. ``portfolio_buyhold`` — cómo se habría comportado un portfolio REAL
   (p.ej. la cuenta importada live-ibkr) en la misma ventana, buy&hold
   con sus pesos reales.

Todo determinista (seed fija): el mismo run da el mismo abanico.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

#: bloque ≈ 1 mes de calendario: preserva la autocorrelación corta
BLOCK_DAYS = 21
N_PATHS = 1000
#: menos de ~3 meses de retornos no estiman ninguna distribución
MIN_RETURNS = 60
SEED = 20261030

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "historical"

#: ventanas de estrés reales (pico→valle del propio episodio)
STRESS_WINDOWS: dict[str, tuple[str, str]] = {
    "COVID crash (Feb–Mar 2020)": ("2020-02-19", "2020-03-23"),
    "Rate shock (2022)": ("2021-12-31", "2022-10-12"),
}


def daily_returns(equity: list) -> np.ndarray:
    """Retornos diarios desde la curva de equity FULL-resolution."""
    values = np.array([float(v) for _, v in equity], dtype=float)
    if len(values) < 2:
        return np.array([])
    return values[1:] / values[:-1] - 1.0


def _circular_block_paths(
    returns: np.ndarray, horizon: int, n_paths: int, rng: np.random.Generator
) -> np.ndarray:
    """Bootstrap circular por bloques (mantiene la autocorrelación corta)."""
    n = len(returns)
    blocks = int(np.ceil(horizon / BLOCK_DAYS))
    starts = rng.integers(0, n, size=(n_paths, blocks))
    idx = (starts[:, :, None] + np.arange(BLOCK_DAYS)[None, None, :]) % n
    return returns[idx].reshape(n_paths, -1)[:, :horizon]


def bootstrap_portfolio(
    returns: np.ndarray,
    horizon_days: int | None = None,
    n_paths: int = N_PATHS,
    seed: int = SEED,
) -> dict | None:
    """Abanico P5–P95 de la riqueza futura (multiplicadores: 1.0 = inicio)."""
    returns = np.asarray(returns, dtype=float)
    if len(returns) < MIN_RETURNS:
        return None
    horizon = horizon_days or len(returns)
    rng = np.random.default_rng(seed)
    paths = _circular_block_paths(returns, horizon, n_paths, rng)
    wealth = np.cumprod(1.0 + paths, axis=1)

    final = wealth[:, -1]
    peak = np.maximum.accumulate(wealth, axis=1)
    max_dd = ((wealth - peak) / peak).min(axis=1)

    step = max(1, horizon // 60)
    band_wealth = np.column_stack([np.ones(wealth.shape[0]), wealth[:, ::step]])
    # percentile ACROSS PATHS at each time step (axis=0 → five time series);
    # axis=1 would give per-path time-quantiles — 5 numbers per path, not a fan
    bands = np.percentile(band_wealth, [5, 25, 50, 75, 95], axis=0)

    years = horizon / 252.0

    def _cagr(mult: float) -> float:
        return float(mult ** (1.0 / years) - 1.0) if mult > 0 else -1.0

    return {
        "n_paths": n_paths,
        "block_days": BLOCK_DAYS,
        "horizon_days": horizon,
        "horizon_years": round(years, 1),
        "final_p05": round(float(np.percentile(final, 5)), 4),
        "final_p25": round(float(np.percentile(final, 25)), 4),
        "final_p50": round(float(np.percentile(final, 50)), 4),
        "final_p75": round(float(np.percentile(final, 75)), 4),
        "final_p95": round(float(np.percentile(final, 95)), 4),
        "cagr_p05": round(_cagr(float(np.percentile(final, 5))), 4),
        "cagr_p50": round(_cagr(float(np.percentile(final, 50))), 4),
        "max_dd_p05": round(float(np.percentile(max_dd, 5)), 4),
        "prob_loss": round(float((final < 1.0).mean()), 4),
        "p5_return": round(float(np.percentile(final, 5) - 1.0), 4),
        "bands": bands.round(4).tolist(),
    }


def withdrawal_sequences(
    returns: np.ndarray,
    withdrawal_rate_annual: float = 0.04,
    horizon_days: int | None = None,
    n_paths: int = N_PATHS,
    seed: int = SEED,
) -> dict | None:
    """Sequence-of-returns: retirada fija anual (cobro mensual ≈ 21 días)
    sobre riqueza inicial 1 — ¿cuánto dura el dinero?"""
    returns = np.asarray(returns, dtype=float)
    if len(returns) < MIN_RETURNS:
        return None
    horizon = horizon_days or len(returns)
    rng = np.random.default_rng(seed + 1)
    paths = _circular_block_paths(returns, horizon, n_paths, rng)

    monthly = withdrawal_rate_annual / 12.0
    wealth = np.ones(n_paths)
    exhausted = np.zeros(n_paths, dtype=bool)
    for t in range(horizon):
        wealth = wealth * (1.0 + paths[:, t])
        if (t + 1) % BLOCK_DAYS == 0:
            wealth = wealth - monthly
        newly_broke = (wealth <= 0) & ~exhausted
        if newly_broke.any():
            exhausted |= newly_broke
        wealth = np.maximum(wealth, 0.0)

    return {
        "withdrawal_rate_annual": withdrawal_rate_annual,
        "horizon_years": round(horizon / 252.0, 1),
        "prob_exhausted": round(float(exhausted.mean()), 4),
        "final_p05": round(float(np.percentile(wealth, 5)), 4),
        "final_p50": round(float(np.percentile(wealth, 50)), 4),
        "final_p95": round(float(np.percentile(wealth, 95)), 4),
    }


def _read_window(csv: Path, start: str, end: str):
    """Serie Close de una ventana, o None si el CSV no la cubre."""
    import pandas as pd

    try:
        frame = pd.read_csv(csv, usecols=["date", "Close"], parse_dates=["date"], index_col="date")
        window = frame.loc[start:end, "Close"].dropna()
    except Exception:  # noqa: BLE001 - un CSV corrupto no rompe la tarjeta
        return None
    return window if len(window) >= 5 else None


def stress_windows(symbols: list[str], data_dir: Path | str = DEFAULT_DATA_DIR) -> dict | None:
    """Drawdown pico→valle del equiponderado del universo (buy&hold,
    base 1 al inicio de cada ventana) en los episodios reales de estrés.
    Quien no cubre una ventana con datos locales queda fuera (contado);
    menos de 2 nombres → ventana sin veredicto."""
    folder = Path(data_dir)
    if not folder.exists():
        return None
    out: dict[str, dict | None] = {}
    for label, (start, end) in STRESS_WINDOWS.items():
        normalized = []
        for sym in symbols:
            window = _read_window(folder / f"{sym}.csv", start, end)
            if window is not None:
                normalized.append(window / float(window.iloc[0]))
        if len(normalized) < 2:
            out[label] = None
            continue
        ew = (sum(normalized) / len(normalized)).dropna()
        dd = float((ew / ew.cummax() - 1.0).min())
        out[label] = {
            "symbols_used": len(normalized),
            "total_return": round(float(ew.iloc[-1] - 1.0), 4),
            "max_drawdown": round(dd, 4),
        }
    return out or None


def portfolio_buyhold(
    weights: dict[str, float],
    start: str,
    end: str,
    data_dir: Path | str = DEFAULT_DATA_DIR,
) -> dict | None:
    """Cómo se habría comportado un portfolio REAL (símbolo → peso) en la
    ventana: buy&hold ponderado con sus propios pesos. Quien no tiene
    datos que cubran la ventana queda fuera (listado) y el peso se
    renormaliza sobre los que quedan — dicho honestamente en el resultado."""
    folder = Path(data_dir)
    if not folder.exists() or not weights:
        return None
    used: list[str] = []
    missing: list[str] = []
    series = []
    for sym, weight in weights.items():
        window = _read_window(folder / f"{sym}.csv", start, end)
        if window is None:
            missing.append(sym)
            continue
        series.append(float(weight) * (window / float(window.iloc[0])))
        used.append(sym)
    if not series:
        return None
    covered_weight = sum(float(weights[s]) for s in used)
    port = (sum(series) / covered_weight).dropna()
    if len(port) < 5:
        return None
    dd = float((port / port.cummax() - 1.0).min())
    days = max((port.index[-1] - port.index[0]).days, 1)
    years = days / 365.25
    total = float(port.iloc[-1] - 1.0)
    return {
        "symbols_used": used,
        "symbols_missing": missing,
        "weight_covered": round(covered_weight, 4),
        "total_return": round(total, 4),
        "cagr": round((1.0 + total) ** (1.0 / years) - 1.0 if total > -1 else -1.0, 4),
        "max_drawdown": round(dd, 4),
        "years": round(years, 1),
    }
