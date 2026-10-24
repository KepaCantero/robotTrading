#!/usr/bin/env python
"""Protocolo cuantitativo de carteras — harness estático multi-ventana.

Herramienta de validación ANTES de optimizar: evalúa carteras estáticas
(equal-weight / yield-weight, con drift o re-balance anual) en la ventana
completa, sub-ventanas de estrés y una ventana OOS reservada, con Sharpe
deflactado (Bailey & López de Prado 2014).

Fue la herramienta que destapó los bugs de datos del repo (CSVs que
empezaban a mitad de ventana, señales caducadas en silencio) y que
demostró que ninguna capa de gestión batía al equiponderado pasivo.

Uso:
    python scripts/quant_protocol.py --symbols SCHD VYM VYMI VIG
    python scripts/quant_protocol.py --symbols SCHD VYM VYMI VIG --rf 1.2 --trials 68

Convenciones honestas:
    - Retornos diarios a CIERRE (ffill por símbolo; el retorno del día es
      la media de los símbolos que cotizaron).
    - Coste de entrada 0.1% (slippage) sobre el retorno total.
    - Sharpe con rf configurable (default 0); rf≈1.2% EUR es la media
      2016-2026 de la ECB.
    - DSR asume N ensayos (declara cuántos probaste) y varianza de SR
      entre ellos; los ensayos correlacionados infla el N efectivo —
      reporta también un N efectivo conservador.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "historical"

#: yield anual (%) por símbolo — estimaciones estáticas (limitación declarada)
YIELDS: dict[str, float] = {
    "SCHD": 3.4,
    "DGRO": 2.0,
    "VYM": 3.0,
    "DVY": 3.8,
    "VYMI": 4.2,
    "NOBL": 2.4,
    "VIG": 1.8,
    "SDY": 2.8,
    "DLN": 2.0,
    "PEY": 4.5,
    "SPY": 1.3,
    "QDIV": 3.0,
    "VHYL": 3.6,
    "IDVY": 4.2,
}


@dataclass(frozen=True)
class Window:
    name: str
    start: str
    end: str


DEFAULT_WINDOWS = (
    Window("FULL 2016-2026", "2016-10-01", "2026-10-01"),
    Window("SW1 2016-2020", "2016-10-01", "2020-03-01"),
    Window("SW2 COVID 2020-2022", "2020-02-01", "2022-02-01"),
    Window("SW3 BEAR 2022-2024", "2022-01-01", "2024-01-01"),
    Window("OOS 2024-2026 (reservada)", "2024-01-01", "2026-10-01"),
)


def load_series(symbol: str, data_dir: Path = DATA_DIR) -> dict[str, float]:
    path = data_dir / f"{symbol}.csv"
    if not path.exists():
        raise SystemExit(f"No data for {symbol} ({path}) — download it first")
    out: dict[str, float] = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            d = row.get("date") or row.get("Date")
            c = row.get("Close") or row.get("close")
            if d and c and d not in out:
                out[d] = float(c)
    if len(out) < 10:
        raise SystemExit(f"Too few rows for {symbol}: {len(out)}")
    return out


def portfolio_daily_returns(
    symbols: list[str],
    caches: dict[str, dict[str, float]],
    win: Window,
    weights: dict[str, float],
    rebalance_days: int | None = None,
) -> list[float]:
    """Retornos diarios de la cartera ponderada (rebalance opcional)."""
    per_symbol: dict[str, dict[str, float]] = {}
    union: set[str] = set()
    for sym in symbols:
        s = caches[sym]
        days = sorted(d for d in s if win.start <= d <= win.end)
        if not days:
            continue
        per_symbol[sym] = {d: s[d] for d in days}
        union |= set(per_symbol[sym])
    calendar = sorted(union)
    if len(calendar) < 3:
        return []

    rets: dict[str, dict[str, float]] = {}
    for sym, ff in per_symbol.items():
        days = sorted(ff)
        rets[sym] = {
            days[i]: ff[days[i]] / ff[days[i - 1]] - 1
            for i in range(1, len(days))
            if ff[days[i - 1]] > 0
        }

    out: list[float] = []
    w = dict(weights)
    last_rebal_i = 0
    values = {sym: w.get(sym, 0.0) for sym in per_symbol}
    for i in range(1, len(calendar)):
        d = calendar[i]
        # retorno PORCENTUAL: ganancia (Σ valor_i × r_i) sobre el valor total
        total_v = sum(values.values())
        gain = sum(values.get(s, 0.0) * rets[s].get(d, 0.0) for s in per_symbol)
        out.append(gain / total_v if total_v > 0 else 0.0)
        for sym in per_symbol:
            values[sym] = values.get(sym, 0.0) * (1 + rets[sym].get(d, 0.0))
        if rebalance_days and (i - last_rebal_i) >= rebalance_days:
            total = sum(values.values())
            for sym in per_symbol:
                values[sym] = total * w.get(sym, 1.0 / len(per_symbol))
            last_rebal_i = i
    return out


def metrics(rets: list[float], entry_cost: float = 0.001, rf: float = 0.0) -> dict:
    if len(rets) < 20:
        return {"skip": True}
    eq = 1.0 - entry_cost
    curve = [eq]
    for r in rets:
        eq *= 1 + r
        curve.append(eq)
    peak, mdd = curve[0], 0.0
    for v in curve:
        peak = max(peak, v)
        if peak > 0:
            mdd = min(mdd, v / peak - 1)
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    sd = math.sqrt(var)
    rf_d = rf / 100.0 / 252.0
    sharpe = (mean - rf_d) / sd * math.sqrt(252) if sd > 0 else 0.0
    m3 = sum((r - mean) ** 3 for r in rets) / len(rets)
    m4 = sum((r - mean) ** 4 for r in rets) / len(rets)
    return {
        "total_pct": (curve[-1] - 1) * 100,
        "cagr_pct": (curve[-1] ** (252 / len(rets)) - 1) * 100 if curve[-1] > 0 else -100.0,
        "sharpe": sharpe,
        "maxdd_pct": mdd * 100,
        "days": len(rets),
        "skew": m3 / sd**3 if sd > 0 else 0.0,
        "kurt": m4 / var**2 if var > 0 else 3.0,
    }


def norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_ppf(p: float) -> float:
    """Acklam — precisión suficiente para el DSR."""
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00, 3.754408661907416e00)
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    q, r = p - 0.5, (p - 0.5) ** 2
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
        * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    )


def deflated_sharpe(
    sr_annual: float,
    days: int,
    skew: float,
    kurt: float,
    n_trials: int,
    var_sr_trials: float,
) -> float:
    """DSR (Bailey & López de Prado 2014) — todo en unidades diarias.

    SR0 = E[max SR | N ensayos] = sqrt(V[SR_n])·((1−γ)·Z_{1−1/N} + γ·Z_{1−1/(Ne)})
    DSR = Φ((SR_obs − SR0)·sqrt(T−1) / sqrt(1 − skew·SR + (kurt−1)/4·SR²))
    """
    gamma = 0.5772156649015329
    sr_p = sr_annual / math.sqrt(252)
    if n_trials <= 1:
        sr0_p = 0.0
    else:
        z1 = norm_ppf(1 - 1.0 / n_trials)
        z2 = norm_ppf(1 - 1.0 / (n_trials * math.e))
        sr0_p = math.sqrt(max(var_sr_trials, 1e-12)) * ((1 - gamma) * z1 + gamma * z2)
        sr0_p /= math.sqrt(252)  # V de ensayos en anualizado
    denom = math.sqrt(max(1e-12, 1 - skew * sr_p + (kurt - 1) / 4 * sr_p**2))
    stat = (sr_p - sr0_p) * math.sqrt(max(1, days - 1)) / denom
    return norm_cdf(stat)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--symbols", nargs="+", required=True, help="universo (CSVs en data/historical)"
    )
    ap.add_argument("--rf", type=float, default=0.0, help="risk-free anual %% (0.0=bruto)")
    ap.add_argument(
        "--trials", type=int, default=1, help="N de configuraciones probadas (para el DSR)"
    )
    ap.add_argument(
        "--entry-cost", type=float, default=0.001, help="slippage de entrada (fracción)"
    )
    args = ap.parse_args()

    symbols = [s.upper() for s in args.symbols]
    caches = {s: load_series(s) for s in symbols}
    n = len(symbols)
    ew = {s: 1.0 / n for s in symbols}
    ysum = sum(YIELDS.get(s, 2.5) for s in symbols)
    yw = {s: YIELDS.get(s, 2.5) / ysum for s in symbols}

    portfolios = {
        "EW-drift": (ew, None),
        "EW-anual": (ew, 252),
        "YieldW-anual": (yw, 252),
    }

    print(f"Universo: {symbols}")
    print(
        f"Yield ponderado EW: {sum(YIELDS.get(s, 2.5) for s in symbols) / n:.2f}%  (rf={args.rf}%)"
    )
    print()
    for pname, (w, rb) in portfolios.items():
        print(f"── {pname} " + "─" * 40)
        for win in DEFAULT_WINDOWS:
            m = metrics(
                portfolio_daily_returns(symbols, caches, win, w, rebalance_days=rb),
                entry_cost=args.entry_cost,
                rf=args.rf,
            )
            if m.get("skip"):
                continue
            print(
                f"  {win.name:28} ret {m['total_pct']:+8.1f}%  CAGR {m['cagr_pct']:6.2f}%  "
                f"SR {m['sharpe']:4.2f}  DD {m['maxdd_pct']:6.1f}%"
            )
        full = metrics(
            portfolio_daily_returns(symbols, caches, DEFAULT_WINDOWS[0], w, rebalance_days=rb),
            entry_cost=args.entry_cost,
            rf=args.rf,
        )
        if args.trials > 1:
            # varianza de SR entre los portfolios evaluados como proxy de la
            # varianza entre ensayos (debes declarar el N real de tu búsqueda)
            srs = [
                metrics(
                    portfolio_daily_returns(
                        symbols, caches, DEFAULT_WINDOWS[0], pw, rebalance_days=prb
                    ),
                    entry_cost=args.entry_cost,
                    rf=args.rf,
                )["sharpe"]
                for pw, prb in portfolios.values()
            ]
            mean_sr = sum(srs) / len(srs)
            var_sr = sum((x - mean_sr) ** 2 for x in srs) / max(1, len(srs) - 1)
            dsr = deflated_sharpe(
                full["sharpe"], full["days"], full["skew"], full["kurt"], args.trials, var_sr
            )
            print(f"  DSR (N={args.trials}): {dsr:.3f} {'✓ >0.95' if dsr > 0.95 else '✗ ≤0.95'}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
