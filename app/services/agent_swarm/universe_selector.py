"""Automatic run-universe derivation from the local CSV corpus.

When a swarm request carries no explicit symbols the universe is derived
from the CSVs in ``data/historical``: a deterministic quality screen
(minimum history, freshness, liquidity floor) followed by a top-K ranking
by average dollar volume. With a recognised investment goal the screen is
first restricted to that goal's curated set (dividend ETFs, defensive
names); the generic ranking caps symbols per structural family so a
liquidity top doesn't collapse into the same mega-caps and three copies
of the S&P 500. Every decision the screen makes is reported
(scanned / kept / dropped per reason) so logs and the UI can show exactly
what was picked and why.

``DEFAULT_UNIVERSE`` (the historical 10-symbol showcase list) lives here as
the last-resort fallback when the corpus is empty or unreadable.

Caveat: dollar volume is measured in each symbol's native currency, so the
ranking compares nominal traded value across currencies (a ¥-quoted share
out-ranks an economically similar €-quoted one). For a top-K liquidity
screen that distortion is acceptable; the goal is to surface investable,
liquid names, not to price anything.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

#: default corpus location — the same relative path DataLoader uses
DEFAULT_DATA_DIR = Path("data/historical")

#: last-resort universe when the corpus is empty or unreadable
DEFAULT_UNIVERSE = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "SAN",
    "ITX.MC",
    "MC.PA",
    "SAP.DE",
    "6758.T",
    "SPY",
    "IBEX",
]

#: how many symbols an auto-picked universe contains
AUTO_UNIVERSE_SIZE = 30
#: minimum bar count to trade a symbol automatically (~2 years daily)
MIN_BARS = 500
#: a CSV whose last bar is older than this is stale and never auto-traded
MAX_STALE_DAYS = 120
#: liquidity floor: average daily traded value (close × volume) of the
#: recent window, in the symbol's native currency
MIN_DOLLAR_VOLUME = 1_000_000.0
#: trailing window (bars) used to measure recent liquidity (~1 year daily)
LIQUIDITY_WINDOW = 252

#: columns read from each CSV — nothing else enters memory
_USECOLS = ["date", "Close", "Volume"]

#: objective-aware candidate sets (intersected with the corpus; symbols
#: without a local CSV simply never surface). Curated, well-known tickers —
#: the corpus holds hundreds of them but carries no category metadata.
DIVIDEND_ETFS = {
    # SOLO ETFs de dividendo: VT (acciones globales totales, sin filtro de
    # dividendo) diluye el factor con ~22% del capital — el vehículo
    # internacional coherente es VYMI. BND tampoco: el refugio-a-BND a
    # cadencia de rebalance vendió en el suelo de 2022 y re-entró tras el
    # rebote (77% vs 127% del mismo run sin él).
    "SCHD",
    "QDIV",  # Global X S&P 500 Quality Dividend (US, distribuye MENSUAL,
    # ~2.6% — verificado 30-10: el QDIV "bare" de Yahoo es este, NO el
    # iShares World Quality Dividend Acc; inception 2018-07-13 casa con
    # el CSV. No-UCITS: solo simulación/paper, no comprable en la UE)
    "VHYL",  # Vanguard FTSE All-World High Dividend Yield UCITS: reparte
    # trimestral (~3.4% yield, 13.4 años de historial, 2013+) — la clase
    # ACC es otro ISIN; este VHYL distribuye y tributa cada año
    "IDVY",  # iShares Euro Dividend UCITS ~4.2% yield, 18.8 años (2008+)
    "VIG",
    "VYM",
    "DGRO",
    "DGRW",
    "DVY",
    "HDV",
    "SDY",
    "NOBL",
    "PEY",
    "SPHD",
    "FDL",
    "DLN",
    "DVYE",
    "VIGI",
    "RDVI",
    "FDVV",
    "DTD",
    "DON",
    "IDV",
    "DWX",
    "SDIV",
    "SPYD",
    "SCHY",
    "DTN",
    "OEDV",
    "EMD",
    "HIY",
    "FVD",
    "DGRS",
    "TDVD",
    "VYMI",
    "FGD",
    "PID",
    "IHDG",
    "DES",
}
DEFENSIVE_SYMBOLS = {
    "BND",
    "AGG",
    "IEF",
    "TLT",
    "LQD",
    "SCHZ",
    "BIV",
    "VGIT",
    "VCSH",
    "MUB",
    "GLD",
    "IAU",
    "XLV",
    "XLP",
    "XLU",
    "VPU",
    "VDC",
    "VHT",
    "JNJ",
    "PG",
    "KO",
    "WMT",
    "MCD",
}

#: UCITS total-return set (EUR-listed, Irish/Luxembourg funds): the
#: Spain-appropriate answer for "live off your portfolio" — accumulation
#: (no yearly dividend tax drag) for the core, one high-dividend engine
#: with deep history, and a euro-sovereign cushion. Suffix symbols match
#: their corpus CSVs (EUNL.DE.csv / IBGS.AS.csv — Yahoo tickers).
UCITS_TOTAL_RETURN = {
    "EUNL.DE",  # iShares Core MSCI World Acc, 2009-09+ — the accumulator core
    "VHYL",  # Vanguard All-World High Dividend (reparte trimestral), 2013-05+
    "IDVY",  # iShares Euro Dividend (reparte anual), 2008-01+
    "IBGS.AS",  # iShares € Govt Bond 1-3yr (verificado 30-10), 2008-10+ — cushion
}

#: ACUMULAR (owner 31-10, FIX 2): el objetivo son SIEMPRE dos fondos —
#: equity global + bono aggregate. El PAR OBJETIVO es VWCE + AGGH.AS
#: (la cartera real del usuario); ambos nacen tarde (2019-07 / 2021-05),
#: así que en ventanas que no cubren se sustituyen por DOCUMENTADOS con
#: historia: IUSQ.DE (iShares MSCI ACWI Acc, 2011-10+ — el VWCE con
#: historia) por equity, y AGG (iShares Core US Aggregate, el hermano
#: US del Global Aggregate EUR-hedged) por bono. EUNL/EIMI/IBGS SALEN
#: del objetivo: eran relleno del arnés de simulación y un run ACUMULAR
#: de 10 años desplegaba 4 mangas (29/29/21/20) en lugar del par
#: objetivo — el objetivo de producto es 2 fondos, no un harness.
ACUMULAR_EQUITY = ("VWCE", "IUSQ.DE")  # (target, sustituto con historia)
ACUMULAR_BOND = ("AGGH.AS", "AGG")

#: goal (as the UI sends it) → corpus filter
GOAL_FILTERS: dict[str, set[str]] = {
    "MAXIMIZAR_DIVIDENDOS": DIVIDEND_ETFS,
    "CAPITAL_PRESERVATION": DEFENSIVE_SYMBOLS,
    "VIVIR_DE_LA_CARTERA": UCITS_TOTAL_RETURN,
    # ACUMULAR no vive aquí: es una selección por VENTANA (par objetivo
    # vs sustitutos documentados) — ver _acumular_universe
}

#: overlap families inside the goal sets: funds that hold essentially the
#: same basket (DGRO/VIG share ~80-95% of holdings by weight; NOBL/SDY are
#: both dividend-aristocrat strategies; BND/AGG/SCHZ track the same US
#: aggregate bond index). Holding two of them is paying twice for one
#: exposure, so the goal screen keeps ONE per family — the most liquid.
#: Symbols in no family are kept as themselves.
_OVERLAP_FAMILIES: dict[str, frozenset[str]] = {
    "us-dividend-growth": frozenset({"DGRO", "VIG", "DGRW", "RDVI", "DGRS"}),
    "us-quality-yield": frozenset({"SCHD", "VYM", "HDV", "FDVV", "DTD", "DLN", "DTN", "FVD"}),
    "us-aristocrats": frozenset({"NOBL", "SDY"}),
    "us-high-yield": frozenset({"DVY", "PEY", "SPHD", "FDL", "SPYD", "SDIV", "HIY"}),
    "intl-dividend": frozenset(
        {"VYMI", "FGD", "PID", "IHDG", "IDV", "DWX", "VIGI", "SCHY", "DVYE", "EMD"}
    ),
    "mid-small-dividend": frozenset({"DON", "DES", "OEDV", "TDVD"}),
    "us-aggregate-bond": frozenset({"BND", "AGG", "SCHZ", "BIV"}),
    "us-treasuries": frozenset({"TLT", "IEF", "VGIT"}),
    "us-corporate-bond": frozenset({"LQD", "VCSH"}),
    "gold": frozenset({"GLD", "IAU"}),
    "healthcare-sector": frozenset({"XLV", "VHT"}),
    "staples-sector": frozenset({"XLP", "VDC"}),
    "utilities-sector": frozenset({"XLU", "VPU"}),
}
_OVERLAP_BY_SYMBOL = {sym: fam for fam, syms in _OVERLAP_FAMILIES.items() for sym in syms}


def overlap_family_of(symbol: str) -> str | None:
    """Overlap family of a symbol inside the goal sets, if any."""
    return _OVERLAP_BY_SYMBOL.get(symbol)


#: minimum goal-filtered survivors before falling back to the generic screen
GOAL_FILTER_MIN = 8

#: structural families for the generic screen: a raw liquidity ranking
#: always surfaces the same mega-caps and three copies of the S&P 500
#: (SPY/IVV/VOO). Capping per family forces diversity without abandoning
#: the liquidity-first ordering. Symbols in no family are never capped.
_FAMILIES: dict[str, frozenset[str]] = {
    frozenset({"SPY", "IVV", "VOO", "QQQ", "DIA", "IWM", "RSP", "VTI", "EFA", "EEM"}): "us-index",
    frozenset(
        {"AAPL", "MSFT", "GOOGL", "META", "AMZN", "NVDA", "TSLA", "AVGO", "ORCL", "CRM"}
    ): "mega-tech",
    frozenset({"SMH", "SOXX", "AMD", "INTC", "TSM", "MU"}): "semiconductors",
    frozenset({"TLT", "LQD", "BND", "AGG", "IEF", "BIV", "SHY", "VGIT", "VCSH"}): "bonds",
    frozenset({"GLD", "SLV", "USO", "DBC", "GSG"}): "commodities",
    frozenset(
        {
            "XLF",
            "XLE",
            "XLK",
            "XLV",
            "XLI",
            "XLP",
            "XLU",
            "XLY",
            "XLB",
            "XLC",
            "VDC",
            "VCR",
            "VDE",
            "VFH",
            "VHT",
            "VIS",
            "VGT",
            "VAW",
            "VNQ",
            "VPU",
            "VOX",
        }
    ): "sector-etfs",
    frozenset({"IBEX", "SAN", "BBVA"}): "spain",
}
_FAMILY_BY_SYMBOL = {sym: fam for syms, fam in _FAMILIES.items() for sym in syms}
#: max symbols kept per family in the generic screen
FAMILY_CAP = 3


def family_of(symbol: str) -> str:
    """Structural family of a symbol (own name = uncapped singleton)."""
    if symbol in _FAMILY_BY_SYMBOL:
        return _FAMILY_BY_SYMBOL[symbol]
    if symbol.endswith(".T"):
        return "japan"
    if "." in symbol:  # .MC .DE .PA .AS … European exchanges
        return "europe"
    return symbol


@dataclass(frozen=True)
class CorpusSymbol:
    """Quality metrics of one CSV in the corpus."""

    symbol: str
    first_date: date
    last_date: date
    bars: int
    avg_dollar_volume: float


@dataclass(frozen=True)
class CorpusScan:
    """Full scan of one corpus folder (cached per process)."""

    symbols: tuple[CorpusSymbol, ...]
    unreadable: tuple[str, ...]

    @property
    def symbol_names(self) -> list[str]:
        return [s.symbol for s in self.symbols]


@dataclass(frozen=True)
class AutoUniverseResult:
    """Outcome of the automatic universe screen, diagnostics included."""

    symbols: list[str]
    scanned: int
    kept: int
    dropped: dict[str, int]
    fallback_used: bool
    goal_filter: str = ""
    diversified: bool = False
    overlap_dropped: int = 0
    #: limitaciones declaradas del objetivo (sustitutos por ventana) —
    #: la UI las muestra: el usuario debe SABER que su 10y ACUMULAR
    #: simula IUSQ.DE+AGG porque VWCE/AGGH nacen tarde
    notes: tuple[str, ...] = ()

    def summary(self) -> str:
        one_liner = "auto universe"
        if self.goal_filter:
            one_liner += f" ({self.goal_filter} goal filter)"
        one_liner += ": "
        if self.fallback_used:
            return one_liner + f"corpus unusable ({self.scanned} CSVs) -> fallback DEFAULT_UNIVERSE"
        dropped = ", ".join(
            f"{count} {reason}" for reason, count in sorted(self.dropped.items()) if count
        )
        return (
            one_liner
            + f"{self.scanned} CSVs scanned -> {self.kept} valid"
            + (f" (dropped: {dropped})" if dropped else "")
            + f" -> top {len(self.symbols)}"
            + (" by liquidity" if not self.goal_filter else " by liquidity in-goal")
            + (" with family cap" if self.diversified else "")
            + (f" ({self.overlap_dropped} overlapping dropped)" if self.overlap_dropped else "")
            + (f" — {'; '.join(self.notes)}" if self.notes else "")
        )


def corpus_symbol_names(data_dir: Path | str = DEFAULT_DATA_DIR) -> list[str]:
    """Symbol names of every CSV in the corpus (glob only, no reading)."""
    folder = Path(data_dir)
    if not folder.is_dir():
        return []
    return sorted(path.stem.upper() for path in folder.glob("*.csv"))


@lru_cache(maxsize=4)
def scan_corpus(data_dir: Path) -> CorpusScan:
    """Scan every CSV in ``data_dir`` and compute per-symbol metrics.

    Expensive (~seconds over the full corpus): read once per process and
    reuse through the cache. Files that are not readable OHLCV CSVs are
    reported in ``unreadable`` instead of failing the scan.
    """
    symbols: list[CorpusSymbol] = []
    unreadable: list[str] = []
    if not data_dir.is_dir():
        logger.warning("Corpus folder %s does not exist", data_dir)
        return CorpusScan(symbols=(), unreadable=())

    for csv_path in sorted(data_dir.glob("*.csv")):
        try:
            frame = pd.read_csv(csv_path, usecols=_USECOLS)
            dates = pd.to_datetime(frame["date"])
            window = frame.tail(LIQUIDITY_WINDOW)
            avg_volume = float((window["Close"] * window["Volume"]).mean())
        except (ValueError, KeyError, pd.errors.ParserError):
            unreadable.append(csv_path.stem.upper())
            continue
        if frame.empty or math.isnan(avg_volume):
            unreadable.append(csv_path.stem.upper())
            continue
        symbols.append(
            CorpusSymbol(
                symbol=csv_path.stem.upper(),
                first_date=dates.min().date(),
                last_date=dates.max().date(),
                bars=len(frame),
                avg_dollar_volume=avg_volume,
            )
        )
    logger.info(
        "Corpus scan of %s: %d readable, %d unreadable",
        data_dir,
        len(symbols),
        len(unreadable),
    )
    return CorpusScan(symbols=tuple(symbols), unreadable=tuple(unreadable))


def _acumular_universe(
    scan: CorpusScan,
    today: date,
    window_start: date | None,
) -> AutoUniverseResult:
    """The ACUMULAR two-fund universe, resolved per window (FIX 2, 31-10).

    ``VWCE + AGGH.AS`` (the target pair) whenever the window fits both
    funds' history; otherwise each seat falls to its DOCUMENTED
    substitute with history — ``IUSQ.DE`` (ACWI Acc, 2011-10+) for
    equity, ``AGG`` (US aggregate) for the bond — and the substitution
    is DECLARED in ``notes`` so logs and UI say it out loud. Never a
    4-fund simulation harness: the product objective is two funds.
    """
    by_name = {sym.symbol: sym for sym in scan.symbols}
    dropped: dict[str, int] = {
        "unreadable": len(scan.unreadable),
        "out-of-goal": max(0, len(scan.symbols) - 4),
        "short-history": 0,
        "stale": 0,
        "illiquid": 0,
        "uncovered-window": 0,
    }
    notes: list[str] = []
    picked: list[str] = []
    for role, (target, substitute) in (
        ("equity", ACUMULAR_EQUITY),
        ("bond", ACUMULAR_BOND),
    ):
        chosen: str | None = None
        for candidate in (target, substitute):
            sym = by_name.get(candidate)
            if sym is None:
                continue
            if sym.bars < MIN_BARS:
                dropped["short-history"] += 1
            elif (today - sym.last_date).days > MAX_STALE_DAYS:
                dropped["stale"] += 1
            elif window_start is not None and sym.first_date > window_start:
                dropped["uncovered-window"] += 1
            else:
                chosen = candidate
                break
        if chosen is None:
            raise ValueError(
                "Auto universe: ACUMULAR no tiene un fondo viable que cubra la "
                f"ventana {window_start or '(sin fecha)'} para el asiento {role} "
                f"(probados {target} y {substitute}) — recorta la ventana o "
                "descarga su histórico primero."
            )
        if chosen != target:
            notes.append(f"{role}: {chosen} sustituye a {target} (no cubre la ventana)")
        picked.append(chosen)
    return AutoUniverseResult(
        symbols=picked,
        scanned=len(scan.symbols) + len(scan.unreadable),
        kept=len(picked),
        dropped=dropped,
        fallback_used=False,
        goal_filter="ACUMULAR",
        notes=tuple(notes),
    )


def auto_universe(
    data_dir: Path | str = DEFAULT_DATA_DIR,
    k: int = AUTO_UNIVERSE_SIZE,
    today: date | None = None,
    goal: str | None = None,
    window_start: date | None = None,
    exhaustive: bool = False,
) -> AutoUniverseResult:
    """Derive the run universe from the corpus (deterministic).

    Filters: enough history (``MIN_BARS``), fresh data (``MAX_STALE_DAYS``),
    enough liquidity (``MIN_DOLLAR_VOLUME``). With a recognised ``goal`` the
    candidates are first restricted to that goal's curated set (dividend
    ETFs / defensive names); too few survivors falls back to the generic
    screen. The generic ranking caps ``FAMILY_CAP`` symbols per structural
    family (a raw liquidity top always surfaces the same mega-caps and
    three copies of the S&P 500). Falls back to ``DEFAULT_UNIVERSE`` —
    loudly — when nothing survives the screen.

    ``exhaustive=True`` (user 2026-10-27: "automatic y todos los
    símbolos"): NO curated goal filter, NO family caps, NO top-k — every
    symbol that survives the basic screen enters the universe. The passive
    default (static_ew) is a whole-market portfolio, not a hand-picked
    shortlist; the coverage gate still rules on window fit.
    """
    effective_today = today or date.today()
    scan = scan_corpus(Path(data_dir))
    goal_key = (goal or "").upper().strip()
    if goal_key == "ACUMULAR" and not exhaustive:
        # FIX 2 (31-10): el objetivo de acumulación es DOS fondos por
        # diseño — par objetivo si la ventana lo cubre, sustitutos
        # documentados si no, limitación declarada. Nunca un conjunto
        # de relleno de 4+ mangas.
        return _acumular_universe(scan, effective_today, window_start)
    goal_filter = None if exhaustive else GOAL_FILTERS.get(goal_key)
    goal_label = (goal_key if goal_filter else "") or ("exhaustive" if exhaustive else "")
    k = len(scan.symbols) if exhaustive else k
    dropped: dict[str, int] = {
        "unreadable": len(scan.unreadable),
        "out-of-goal": 0,
        "short-history": 0,
        "stale": 0,
        "illiquid": 0,
        "uncovered-window": 0,
    }
    candidates: list[CorpusSymbol] = []
    for sym in scan.symbols:
        if goal_filter and sym.symbol not in goal_filter:
            dropped["out-of-goal"] += 1
        elif sym.bars < MIN_BARS:
            dropped["short-history"] += 1
        elif (effective_today - sym.last_date).days > MAX_STALE_DAYS:
            dropped["stale"] += 1
        elif sym.avg_dollar_volume < MIN_DOLLAR_VOLUME:
            dropped["illiquid"] += 1
        elif window_start is not None and sym.first_date > window_start:
            # un símbolo que no cubre la ventana solo puede hacer FALLAR la
            # run entera si llega al motor: fuera del universo aquí, con
            # su contador en el resumen que la UI muestra como aviso.
            dropped["uncovered-window"] += 1
        else:
            candidates.append(sym)

    if goal_filter and len(candidates) < GOAL_FILTER_MIN:
        # Los objetivos CURADOS nunca caen en silencio a la pantalla
        # genérica (30-10: una petición ACUMULAR testeó IBEX/Toyota/SPY
        # porque Yahoo subestima el volumen de los ETF listados en EUR y
        # el floor de liquidez dejó el conjunto bajo el mínimo). Segundo
        # intento SIN el floor: son nombres curados, no micro-caps — el
        # floor protege la pantalla genérica, no las listas del objetivo.
        relaxed = [
            sym
            for sym in scan.symbols
            if sym.symbol in goal_filter
            and sym.bars >= MIN_BARS
            and (effective_today - sym.last_date).days <= MAX_STALE_DAYS
            and (window_start is None or sym.first_date <= window_start)
        ]
        if not relaxed:
            raise ValueError(
                f"Auto universe: objective {goal_key} has no viable candidates "
                "in the corpus (history/freshness/window) — pick the universe "
                "manually or download its data first."
            )
        dropped["illiquid"] += len(relaxed) - len(candidates)
        logger.warning(
            "Auto universe: only %d/%d %s candidates pass the liquidity floor "
            "-> using the curated set without it (Yahoo understates EUR volume)",
            len(candidates),
            len(relaxed),
            goal_key,
        )
        candidates = relaxed

    scanned = len(scan.symbols) + len(scan.unreadable)
    if not candidates:
        logger.warning(
            "Auto universe: no valid symbols among %d CSVs in %s -> DEFAULT_UNIVERSE",
            scanned,
            data_dir,
        )
        return AutoUniverseResult(
            symbols=list(DEFAULT_UNIVERSE),
            scanned=scanned,
            kept=0,
            dropped=dropped,
            fallback_used=True,
        )

    ranked = sorted(candidates, key=lambda s: (-s.avg_dollar_volume, s.symbol))
    if exhaustive:
        picked, overlap_dropped = [s.symbol for s in ranked], 0  # todos, sin caps
    elif goal_filter:
        picked, overlap_dropped = _one_per_overlap_family(ranked, k, window_start)
    else:
        picked = _diversify(ranked, k)
        overlap_dropped = 0
    return AutoUniverseResult(
        symbols=picked,
        scanned=scanned,
        kept=len(candidates),
        dropped=dropped,
        fallback_used=False,
        goal_filter=goal_label,
        diversified=not goal_filter,
        overlap_dropped=overlap_dropped,
    )


def _one_per_overlap_family(
    ranked: list[CorpusSymbol], k: int, window_start: date | None = None
) -> tuple[list[str], int]:
    """Keep ONE symbol of each overlap family (one exposure, one fee);
    unaffiliated symbols pass through. Returns (picked, dropped).

    With ``window_start`` (the run's first day) the family representative
    must COVER the window when any member does: for a 2008-2026 run the
    intl-dividend seat goes to PID (history from 2005), not to the more
    liquid VYMI (history from 2016). Liquidity only breaks ties between
    members that equally cover — or when none does.
    """
    tolerance = timedelta(days=90)
    picked: list[str] = []
    seen_families: set[str] = set()
    dropped = 0
    for sym in ranked:
        family = overlap_family_of(sym.symbol)
        if family is None:
            picked.append(sym.symbol)
            if len(picked) == k:
                break
            continue
        if family in seen_families:
            dropped += 1
            continue
        if window_start is not None:
            covers = sym.first_date <= window_start + tolerance
            if not covers:
                covering = [
                    m
                    for m in ranked
                    if overlap_family_of(m.symbol) == family
                    and m.first_date <= window_start + tolerance
                ]
                if covering:
                    # este run es largo: la familia la cubre otro miembro
                    winner = min(covering, key=lambda m: (-m.avg_dollar_volume, m.symbol))
                    picked.append(winner.symbol)
                    seen_families.add(family)
                    dropped += 1
                    if len(picked) == k:
                        break
                    continue
        seen_families.add(family)
        picked.append(sym.symbol)
        if len(picked) == k:
            break
    return picked, dropped


def _diversify(ranked: list[CorpusSymbol], k: int) -> list[str]:
    """Top-k by liquidity with at most ``FAMILY_CAP`` per structural family.

    Deferred (over-cap) symbols fill the remaining slots in rank order so
    the result still has ``k`` names when the corpus allows it.
    """
    picked: list[str] = []
    deferred: list[str] = []
    counts: dict[str, int] = {}
    for sym in ranked:
        family = family_of(sym.symbol)
        if counts.get(family, 0) >= FAMILY_CAP:
            deferred.append(sym.symbol)
            continue
        counts[family] = counts.get(family, 0) + 1
        picked.append(sym.symbol)
        if len(picked) == k:
            return picked
    return [*picked, *deferred][:k]
