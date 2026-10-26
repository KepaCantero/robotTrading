"""Bloque 2 — Dividend Safety Score propio (score 0–100, PIT).

La fórmula es PÚBLICA y configurable (pesos abajo); se calcula solo con
información publicada hasta la fecha pedida (Bloque 1) y con los eventos
de dividendo ya cobrados del corpus propio. Cuando falta un factor, ese
símbolo queda `computable=False` para el factor y el hueco aparece en el
informe — el score degrada su cobertura, nunca inventa (patrón D04).

Factores (peso por defecto):
  1. cobertura    (35)  payout sobre net income; FFO (OCF) cuando existe
  2. solvencia    (25)  deuda/patrimonio y su tendencia 3 años
  3. persistencia (20)  años consecutivos sin recorte del pago
  4. crecimiento  (10)  CAGR 3 años del dividendo y del beneficio
  5. estabilidad  (10)  drawdown del pago y desviación del beneficio

Limitación del tier gratis declarada: fundamentales desde ~2021 → las
ventanas de 3 años solo computan desde ~2024, y la validación COVID-2020
original no es posible; la validación empírica usa el recorte de INTC
(feb-2024) dentro de la ventana disponible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.backtesting.fundamentals_source import FundamentalsSource

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

#: pesos configurables — se publican con cada informe
DEFAULT_WEIGHTS: dict[str, int] = {
    "cobertura": 35,
    "solvencia": 25,
    "persistencia": 20,
    "crecimiento": 10,
    "estabilidad": 10,
}

_ONE = Decimal("1")
_HUNDRED = Decimal("100")


@dataclass
class FactorResult:
    """Resultado de un factor: puntos conseguidos / posibles + el porqué."""

    name: str
    weight: int
    points: Decimal  # 0..1 normalizado (se multiplica por el peso)
    computable: bool = True
    detail: str = ""

    @property
    def earned(self) -> Decimal:
        return self.points * Decimal(self.weight)


@dataclass
class DividendSafetyReport:
    """Score por símbolo con sus factores y huecos, reproducible."""

    ticker: str
    as_of: date
    score: Decimal  # 0..100; None-safe: huecos reducen el denominador
    weights: dict[str, int]
    factors: list[FactorResult] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    @property
    def computable(self) -> bool:
        return any(f.computable for f in self.factors)

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "as_of": self.as_of.isoformat(),
            "score": str(self.score),
            "computable": self.computable,
            "formula": {f.name: f"{f.points}×{f.weight}" for f in self.factors},
            "gaps": self.gaps,
        }


def _safe_div(a: Decimal | None, b: Decimal | None) -> Decimal | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def _cagr(begin: Decimal, end: Decimal, years: int) -> Decimal | None:
    if begin is None or end is None or begin <= 0 or end <= 0 or years <= 0:
        return None
    return (float(end) / float(begin)) ** (1.0 / years) - 1.0  # noqa: COM818


class DividendSafetyScorer:
    """Motor del score sobre los corpus SimFin (anual) + dividendos."""

    def __init__(
        self,
        data_dir: Path | None = None,
        weights: dict[str, int] | None = None,
    ):
        base = data_dir or _DATA_DIR / "fundamentals"
        self.income = FundamentalsSource("us-income-annual", data_dir=base)
        self.balance = FundamentalsSource("us-balance-annual", data_dir=base)
        self.cashflow = FundamentalsSource("us-cashflow-annual", data_dir=base)
        self.weights = {**DEFAULT_WEIGHTS, **(weights or {})}

    # ------------------------------------------------------------------
    def _paid_dividends(self, ticker: str, as_of: date) -> list[tuple[date, Decimal]]:
        """Dividendos anuales pagados (positivos) publicados ≤ as_of."""
        out = []
        for f in self.cashflow.figure_history(ticker, "Dividends Paid", as_of):
            # SimFin reports cash OUTFLOW as negative; paid amount is |v|
            if f.value != 0:
                out.append((f.report_date, abs(f.value)))
        return sorted(out)

    # ------------------------------------------------------------------
    def _factor_cobertura(self, ticker: str, as_of: date) -> FactorResult:
        w = self.weights["cobertura"]
        net = self.income.figure(ticker, "Net Income", as_of)
        ocf = self.cashflow.figure(ticker, "Net Cash from Operating Activities", as_of)
        paid = self.cashflow.figure(ticker, "Dividends Paid", as_of)
        if net is None or paid is None or abs(paid.value) == 0:
            return FactorResult(
                "cobertura",
                w,
                Decimal("0"),
                computable=False,
                detail="sin beneficio o dividendo publicado",
            )
        payout = _safe_div(abs(paid.value), net.value if net.value > 0 else None)
        base = payout
        detail = f"payout NI {payout:.2f}" if payout is not None else "beneficio ≤0"
        # FFO view when available (OCF), harder to fake than net income
        ffo_payout = _safe_div(abs(paid.value), ocf.value if ocf and ocf.value > 0 else None)
        if ffo_payout is not None:
            base = min(payout or ffo_payout, ffo_payout)
            detail += f" · FFO {ffo_payout:.2f}"
        if base is None:
            return FactorResult(
                "cobertura",
                w,
                Decimal("0"),
                computable=False,
                detail=detail + " (sin cobertura computable)",
            )
        # ≤50% pago → 1.0; ≥100% → 0; lineal entre medias
        if base <= Decimal("0.5"):
            points = Decimal("1")
        elif base >= Decimal("1.0"):
            points = Decimal("0")
        else:
            points = (Decimal("1.0") - base) * 2
        return FactorResult("cobertura", w, points, True, detail)

    def _factor_solvencia(self, ticker: str, as_of: date) -> FactorResult:
        w = self.weights["solvencia"]
        eq = self.balance.figure(ticker, "Total Equity", as_of)
        hist_debt: list[Decimal] = []
        for f in self.balance.figure_history(ticker, "Long Term Debt", as_of):
            if f.report_date.year >= as_of.year - 3:
                hist_debt.append(f.value)
        if eq is None or eq.value <= 0 or not hist_debt:
            return FactorResult(
                "solvencia",
                w,
                Decimal("0"),
                computable=False,
                detail="sin patrimonio o deuda publicados",
            )
        debt_now = hist_debt[-1]
        ratio = debt_now / eq.value  # deuda/patrimonio
        trend = hist_debt[-1] - hist_debt[0]  # >0 = más deuda
        points = (
            Decimal("1")
            if ratio <= Decimal("0.5")
            else (
                Decimal("0.6")
                if ratio <= Decimal("1")
                else (Decimal("0.3") if ratio <= Decimal("2") else Decimal("0"))
            )
        )
        if trend < 0:  # desapalancando suma
            points = min(_ONE, points + Decimal("0.1"))
        elif trend > 0 and ratio > _ONE:
            points = max(Decimal("0"), points - Decimal("0.1"))
        return FactorResult(
            "solvencia",
            w,
            points,
            True,
            f"deuda/patrimonio {ratio:.2f}, deuda 3y {trend:+.0f}",
        )

    def _factor_persistencia(self, ticker: str, as_of: date) -> FactorResult:
        w = self.weights["persistencia"]
        pagos = self._paid_dividends(ticker, as_of)
        if len(pagos) < 2:
            return FactorResult(
                "persistencia",
                w,
                Decimal("0"),
                computable=False,
                detail=f"{len(pagos)} pagos publicados (mín. 2)",
            )
        anios = 0
        prev: Decimal | None = None
        for _, amount in pagos:
            if prev is not None and amount < prev * Decimal("0.95"):  # recorte >5%
                anios = 0
            anios += 1
            prev = amount
        # ventana máx computable con 4 años de tier gratis: 4
        points = min(Decimal(anios), Decimal("4")) / Decimal("4")
        return FactorResult("persistencia", w, points, True, f"{anios} años sin recorte ≥5%")

    def _factor_crecimiento(self, ticker: str, as_of: date) -> FactorResult:
        w = self.weights["crecimiento"]
        pagos = self._paid_dividends(ticker, as_of)
        ni = self.income.figure_history(ticker, "Net Income", as_of)
        div_cagr = None
        if len(pagos) >= 2:
            years = (pagos[-1][0].year - pagos[0][0].year) or 1
            div_cagr = _cagr(pagos[0][1], pagos[-1][1], years)
        ni_cagr = None
        if len(ni) >= 2:
            years = (ni[-1].report_date.year - ni[0].report_date.year) or 1
            ni_cagr = _cagr(ni[0].value, ni[-1].value, years)
        if div_cagr is None and ni_cagr is None:
            return FactorResult(
                "crecimiento", w, Decimal("0"), computable=False, detail="sin historia suficiente"
            )
        parts = []
        if div_cagr is not None:
            parts.append(max(Decimal("0"), min(_ONE, Decimal(str(div_cagr)) * 10)))
        if ni_cagr is not None:
            parts.append(max(Decimal("0"), min(_ONE, Decimal(str(ni_cagr)) * 10)))
        points = sum(parts) / Decimal(len(parts))
        return FactorResult(
            "crecimiento",
            w,
            points,
            True,
            f"div CAGR {div_cagr:+.1%}" if div_cagr is not None else "div CAGR n/d",
        )

    def _factor_estabilidad(self, ticker: str, as_of: date) -> FactorResult:
        w = self.weights["estabilidad"]
        pagos = self._paid_dividends(ticker, as_of)
        ni = [f.value for f in self.income.figure_history(ticker, "Net Income", as_of)]
        if len(pagos) < 2 or len(ni) < 2:
            return FactorResult(
                "estabilidad", w, Decimal("0"), computable=False, detail="sin historia suficiente"
            )
        amounts = [a for _, a in pagos]
        peak, dd = amounts[0], Decimal("0")
        for a in amounts:
            peak = max(peak, a)
            dd = max(dd, (peak - a) / peak if peak > 0 else dd)
        positives = [v for v in ni if v > 0]
        ni_stable = len(positives) == len(ni)
        points = _ONE - min(_ONE, dd * 2)  # dd 0 → 1.0; dd ≥50% → 0
        if not ni_stable:
            points = points * Decimal("0.5")  # beneficios negativos alguna vez
        return FactorResult("estabilidad", w, points, True, f"dd pago {dd:.0%}")

    # ------------------------------------------------------------------
    def score(self, ticker: str, as_of: date) -> DividendSafetyReport:
        """Score 0–100 del símbolo a la fecha (solo publicado ≤ as_of)."""
        factors = [
            self._factor_cobertura(ticker, as_of),
            self._factor_solvencia(ticker, as_of),
            self._factor_persistencia(ticker, as_of),
            self._factor_crecimiento(ticker, as_of),
            self._factor_estabilidad(ticker, as_of),
        ]
        earned = sum((f.earned for f in factors if f.computable), Decimal("0"))
        possible = sum((Decimal(f.weight) for f in factors if f.computable), Decimal("0"))
        total = Decimal("0") if possible == 0 else (earned / possible * _HUNDRED)
        gaps = [f"{f.name}: {f.detail}" for f in factors if not f.computable]
        return DividendSafetyReport(
            ticker=ticker.upper(),
            as_of=as_of,
            score=total.quantize(Decimal("0.1")),
            weights=self.weights,
            factors=factors,
            gaps=gaps,
        )

    def universe_filter(self, tickers: list[str], as_of: date, min_score: Decimal = Decimal("60")):
        """Filtra el universo por score delante del ranking (T2.2).

        Devuelve (dentro, fuera, informes): los que no computan quedan
        FUERA con su hueco documentado — nunca pasan de rositas.
        """
        inside, outside, reports = [], [], []
        for t in tickers:
            r = self.score(t, as_of)
            reports.append(r)
            if r.computable and r.score >= min_score:
                inside.append(t)
            else:
                outside.append(t)
        return inside, outside, reports
