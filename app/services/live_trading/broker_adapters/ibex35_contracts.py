"""
IBEX35 Contract Helpers for Spanish Stocks

Provides contract creation utilities for trading Spanish stocks and indices
through Interactive Brokers.
"""

import logging

from ib_insync.contract import Contract as IBContract
from ib_insync.contract import Stock

logger = logging.getLogger(__name__)

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
    base_symbol = symbol.split(".")[0]

    logger.debug(
        "Creating stock contract",
        extra={
            "component": "ibex35_contracts",
            "operation": "create_stock_contract",
            "symbol": symbol,
            "base_symbol": base_symbol,
            "currency": currency,
            "exchange": exchange,
        },
    )

    contract = Stock(symbol=base_symbol, exchange=exchange, currency=currency)

    logger.info(
        "Stock contract created",
        extra={
            "component": "ibex35_contracts",
            "operation": "create_stock_contract",
            "symbol": base_symbol,
            "currency": currency,
            "exchange": exchange,
        },
    )

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

    logger.debug(
        "Creating IBEX35 index contract",
        extra={
            "component": "ibex35_contracts",
            "operation": "create_index_contract",
            "index": "IBEX",
            "exchange": "Meff",
            "currency": "EUR",
        },
    )

    contract = Index(symbol="IBEX", exchange="Meff", currency="EUR")  # Spanish derivatives exchange

    logger.info(
        "IBEX35 index contract created",
        extra={
            "component": "ibex35_contracts",
            "operation": "create_index_contract",
            "contract_symbol": "IBEX",
        },
    )

    return contract


def get_ibex35_symbols() -> list[str]:
    """
    Get list of IBEX35 constituent symbols.

    Returns:
        List of stock symbols with Spanish exchange suffix (.MC)

    Note:
        This list may not be exhaustive as IBEX35 composition
        changes quarterly. Always verify with official sources.
    """
    logger.debug(
        "Retrieving IBEX35 symbols list",
        extra={
            "component": "ibex35_contracts",
            "operation": "get_ibex35_symbols",
            "symbols_count": len(IBEX35_SYMBOLS),
        },
    )

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
    if "." not in normalized:
        normalized = f"{normalized}.MC"

    result = normalized in IBEX35_SYMBOLS

    logger.debug(
        "Checking if symbol is IBEX35 constituent",
        extra={
            "component": "ibex35_contracts",
            "operation": "is_ibex35_symbol",
            "input_symbol": symbol,
            "normalized_symbol": normalized,
            "is_ibex35": result,
        },
    )

    return result


def get_spanish_exchange_suffix() -> str:
    """
    Get the standard exchange suffix for Spanish stocks.

    Returns:
        ".MC" (Madrid, Spain / Bolsa de Madrid)
    """
    logger.debug(
        "Retrieving Spanish exchange suffix",
        extra={
            "component": "ibex35_contracts",
            "operation": "get_spanish_exchange_suffix",
            "suffix": ".MC",
        },
    )

    return ".MC"
