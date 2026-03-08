"""
IBEX35 Contract Helpers for Spanish Stocks

Provides contract creation utilities for trading Spanish stocks and indices
through Interactive Brokers.
"""

from typing import List

from ib_insync.contract import Contract as IBContract, Stock

# IBEX35 constituents (common Spanish stocks with exchange suffixes)
IBEX35_SYMBOLS = [
    "ACS.MC",  # ACS Group
    "AENA.MC",  # Aena
    "AMS.MC",  # Amadeus
    "ANA.MC",  # Acciona
    "ACX.MC",  # Acciona Energia
    "SAB.MC",  # Sabadell
    "BME.MC",  # Bolsas y Mercados
    "BKT.MC",  # Bankinter
    "SAN.MC",  # Banco Santander
    "CLNX.MC",  # Cellnex
    "CABK.MC",  # CaixaBank
    "ENG.MC",  # Enagas
    "ELE.MC",  # Endesa
    "FER.MC",  # Ferrovial
    "GRF.MC",  # Grifols
    "IAG.MC",  # IAG
    "IBE.MC",  # Iberdrola
    "ITX.MC",  # Inditex
    "COL.MC",  # Colonial
    "LOG.MC",  # Logista
    "MAP.MC",  # Mapfre
    "MEL.MC",  # Melia Hotels
    "MRL.MC",  # Merlin Properties
    "NTGY.MC",  # Naturgy
    "OHL.MC",  # OHLA
    "PHM.MC",  # PharmaMar
    "REE.MC",  # Red Electrica
    "REP.MC",  # Repsol
    "SAR.MC",  # Sacyr (temporarily in IBEX35)
    "SLR.MC",  # Solaria
    "TUB.MC",  # Tubacex
    "TEF.MC",  # Telefonica
    "VIS.MC",  # Viscofan
    "VWS.MC",  # VW Woks (temporarily in IBEX35)
    "BBVA.MC",  # BBVA (trades on NYSE but in IBEX35)
    "MTS.MC",  # ArcelorMittal (trades on multiple exchanges but in IBEX35)
]


def create_stock_contract(
    symbol: str, currency: str = "EUR", exchange: str = "SMART"
) -> IBContract:
    """
    Create an IB Contract for a Spanish stock.

    Args:
        symbol: Stock symbol (e.g., "SAN.MC" or "SAN")
        currency: Currency (default: "EUR")
        exchange: Exchange (default: "SMART" for smart routing)
                 Use "MADRID" for specific Spanish exchange

    Returns:
        IBContract object for the stock

    Examples:
        >>> create_stock_contract("SAN.MC")
        >>> create_stock_contract("TEF.MC", exchange="MADRID")
    """
    # Extract symbol without exchange suffix if provided
    base_symbol = symbol.split('.')[0]

    contract = Stock(symbol=base_symbol, exchange=exchange, currency=currency)

    return contract


def create_index_contract() -> IBContract:
    """
    Create an IB Contract for the IBEX35 index.

    Returns:
        IBContract object for IBEX35 index (for CFD/futures trading)

    Note:
        IBEX35 index trading typically requires CFDs or futures,
        not direct index trading.
    """
    from ib_insync.contract import Index

    contract = Index(symbol="IBEX", exchange="Meff", currency="EUR")  # Spanish derivatives exchange

    return contract


def get_ibex35_symbols() -> List[str]:
    """
    Get list of IBEX35 constituent symbols.

    Returns:
        List of stock symbols with Spanish exchange suffix (.MC)

    Note:
        This list may not be exhaustive as IBEX35 composition
        changes quarterly. Always verify with official sources.
    """
    return IBEX35_SYMBOLS.copy()


def is_ibex35_symbol(symbol: str) -> bool:
    """
    Check if a symbol is part of IBEX35.

    Args:
        symbol: Stock symbol to check

    Returns:
        True if symbol is in IBEX35, False otherwise
    """
    # Normalize symbol
    normalized = symbol.upper()
    if '.' not in normalized:
        normalized = f"{normalized}.MC"

    return normalized in IBEX35_SYMBOLS


def get_spanish_exchange_suffix() -> str:
    """
    Get the standard exchange suffix for Spanish stocks.

    Returns:
        ".MC" (Madrid, Spain / Bolsa de Madrid)
    """
    return ".MC"
