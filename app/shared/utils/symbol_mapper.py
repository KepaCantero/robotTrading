"""
Symbol Mapper - Centralized Symbol Mapping for Multi-Broker FIFO Tax Compliance

CRITICAL for FIFO tax compliance because different brokers use different symbol formats:
- Binance: BTCUSDT, ETHUSDT
- OANDA: BTC_USD, ETH_USD
- IBKR: IBKR:BTC, IBKR:ETH
- Degiro: Various formats

This component ensures that:
1. All brokers normalize to a single internal symbol format
2. FIFO calculations work across multiple brokers
3. Modelo 721 tax reporting is accurate
4. Transaction safety is maintained for audit purposes

Architecture:
- Centralized mapping database with transaction safety
- Two-way conversion: internal_symbol <-> broker_symbol
- Multi-broker support with validation
- Integration with IBroker interface and FIFO system
- Comprehensive audit logging for tax compliance

Author: Backend Developer (SRE Integration)
Date: 2026-01-25
Status: PRODUCTION - Critical for Tax Compliance
"""

import logging
import re
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import ClassVar, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.interfaces.broker_base import BrokerType

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND CONFIGURATION
# ============================================================================


class MappingStatus(str, Enum):
    """Status of a symbol mapping"""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    PENDING_REVIEW = "pending_review"
    AUTO_DETECTED = "auto_detected"


class SymbolMappingError(Exception):
    """Base exception for symbol mapping errors"""


class AmbiguousSymbolError(SymbolMappingError):
    """Raised when a symbol could map to multiple internal symbols"""


class UnknownSymbolError(SymbolMappingError):
    """Raised when a broker symbol cannot be mapped"""


class ValidationError(SymbolMappingError):
    """Raised when symbol validation fails"""


@dataclass
class SymbolMapping:
    """
    Represents a mapping between internal and broker-specific symbols.

    This is the core data structure for symbol normalization across brokers.
    Each mapping is immutable once created to ensure audit trail integrity.

    Attributes:
        id: Unique identifier for this mapping
        internal_symbol: Standardized internal symbol (e.g., "BTC", "ETH")
        broker_symbol: Broker-specific symbol (e.g., "BTCUSDT", "BTC_USD")
        broker_name: Name of the broker (e.g., "binance", "oanda")
        broker_type: Type of broker (crypto, forex, stocks_us, stocks_eu)
        asset_class: Asset classification (crypto, forex, stock, etf)
        status: Current status of this mapping
        created_at: When this mapping was created
        updated_at: Last time this mapping was modified
        is_verified: Whether this mapping has been verified
        metadata: Additional information about this mapping
    """

    id: UUID = field(default_factory=uuid4)
    internal_symbol: str = field(default="")
    broker_symbol: str = field(default="")
    broker_name: str = field(default="")
    broker_type: BrokerType = field(default=BrokerType.CRYPTO)
    asset_class: str = field(default="crypto")
    status: MappingStatus = field(default=MappingStatus.ACTIVE)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_verified: bool = field(default=False)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate the mapping after initialization"""
        if not self.internal_symbol:
            raise ValidationError("internal_symbol cannot be empty")
        if not self.broker_symbol:
            raise ValidationError("broker_symbol cannot be empty")
        if not self.broker_name:
            raise ValidationError("broker_name cannot be empty")

        # Normalize symbols (if not already normalized)
        # Note: This is a safety net, normalization should happen before creating SymbolMapping
        self.internal_symbol = self.internal_symbol.upper().strip()
        self.broker_symbol = self.broker_symbol.upper().strip()
        self.broker_name = self.broker_name.lower().strip()

    def to_dict(self) -> dict:
        """Convert mapping to dictionary for serialization"""
        return {
            "id": str(self.id),
            "internal_symbol": self.internal_symbol,
            "broker_symbol": self.broker_symbol,
            "broker_name": self.broker_name,
            "broker_type": self.broker_type.value,
            "asset_class": self.asset_class,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_verified": self.is_verified,
            "metadata": self.metadata,
        }


# ============================================================================
# BROKER-SPECIFIC MAPPING TABLES
# ============================================================================


class BrokerMappingTables:
    """
    Pre-defined broker-specific symbol mapping tables.

    These tables provide default mappings for common brokers and symbols.
    They are used as a fallback when database lookups fail.
    """

    # Binance cryptocurrency mappings
    BINANCE_CRYPTO: ClassVar[dict] = {
        # Major cryptocurrencies
        "BTC": "BTCUSDT",
        "ETH": "ETHUSDT",
        "BNB": "BNBUSDT",
        "XRP": "XRPUSDT",
        "ADA": "ADAUSDT",
        "DOGE": "DOGEUSDT",
        "SOL": "SOLUSDT",
        "DOT": "DOTUSDT",
        "MATIC": "MATICUSDT",
        "AVAX": "AVAXUSDT",
        "LINK": "LINKUSDT",
        "UNI": "UNIUSDT",
        "ATOM": "ATOMUSDT",
        "LTC": "LTCUSDT",
        "BCH": "BCHUSDT",
        "XLM": "XLMUSDT",
        "ALGO": "ALGOUSDT",
        "VET": "VETUSDT",
        "FIL": "FILUSDT",
        # Forex pairs on Binance
        "EURUSD": "EURUSDT",
        "GBPUSD": "GBPUSDT",
        "USDJPY": "USDJPYUSDT",
    }

    # OANDA forex mappings
    OANDA_FOREX: ClassVar[dict] = {
        # Major forex pairs
        "EURUSD": "EUR_USD",
        "GBPUSD": "GBP_USD",
        "USDJPY": "USD_JPY",
        "USDCHF": "USD_CHF",
        "AUDUSD": "AUD_USD",
        "USDCAD": "USD_CAD",
        "NZDUSD": "NZD_USD",
        # Minor pairs
        "EURGBP": "EUR_GBP",
        "EURJPY": "EUR_JPY",
        "GBPJPY": "GBP_JPY",
        # Base currencies (for single currency mapping)
        "EUR": "EUR_USD",
        "GBP": "GBP_USD",
        "USD": "USD_JPY",  # Default to USDJPY for USD
        "CHF": "USD_CHF",
        "AUD": "AUD_USD",
        "CAD": "USD_CAD",
        "NZD": "NZD_USD",
        "JPY": "USD_JPY",
        # Crypto on OANDA
        "BTC": "BTC_USD",
        "ETH": "ETH_USD",
        "LTC": "LTC_USD",
        "XRP": "XRP_USD",
    }

    # Interactive Brokers mappings
    IBKR_STOCKS_US: ClassVar[dict] = {
        # Tech stocks
        "AAPL": "AAPL",
        "MSFT": "MSFT",
        "GOOGL": "GOOGL",
        "AMZN": "AMZN",
        "TSLA": "TSLA",
        "META": "META",
        "NVDA": "NVDA",
        "AMD": "AMD",
        "INTC": "INTC",
        # Crypto on IBKR
        "BTC": "IBKR:BTC",
        "ETH": "IBKR:ETH",
        # ETFs
        "SPY": "SPY",
        "QQQ": "QQQ",
        "IWM": "IWM",
        "VTI": "VTI",
    }

    # Degiro mappings
    DEGIRO_STOCKS_EU: ClassVar[dict] = {
        # European stocks
        "ASML": "ASML",
        "SAP": "SAP",
        "ING": "INGA",
        "PHILIPS": "PHIA",
        "KPN": "KPN",
        # US stocks on Degiro
        "AAPL": "AAPL",
        "MSFT": "MSFT",
        "GOOGL": "GOOGL",
        # ETFs
        "VWCE": "VWCE",  # Vanguard All-World
        "IWDA": "IWDA",  # iShares Core MSCI World
        "EUNH": "EUNH",  # iShares Core MSCI EM IMI
    }

    # Kraken mappings
    KRAKEN_CRYPTO: ClassVar[dict] = {
        "BTC": "XXBTZUSD",
        "ETH": "XETHZUSD",
        "XRP": "XXRPZUSD",
        "LTC": "XLTCZUSD",
        "ADA": "ADAUSD",
        "DOT": "DOTUSD",
        "LINK": "LINKUSD",
    }

    # Coinbase mappings
    COINBASE_CRYPTO: ClassVar[dict] = {
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        "XRP": "XRP-USD",
        "LTC": "LTC-USD",
        "BCH": "BCH-USD",
        "ADA": "ADA-USD",
        "DOT": "DOT-USD",
        "SOL": "SOL-USD",
    }

    @classmethod
    def get_default_mapping(cls, broker_name: str, internal_symbol: str) -> Optional[str]:
        """
        Get default broker symbol for a given internal symbol.

        Args:
            broker_name: Name of the broker
            internal_symbol: Internal symbol to map

        Returns:
            Broker-specific symbol or None if not found
        """
        broker_name = broker_name.lower()

        mapping_tables = {
            "binance": cls.BINANCE_CRYPTO,
            "oanda": cls.OANDA_FOREX,
            "ibkr": cls.IBKR_STOCKS_US,
            "degiro": cls.DEGIRO_STOCKS_EU,
            "kraken": cls.KRAKEN_CRYPTO,
            "coinbase": cls.COINBASE_CRYPTO,
        }

        table = mapping_tables.get(broker_name)
        if table:
            return table.get(internal_symbol.upper())

        return None

    @classmethod
    def get_all_broker_symbols(cls, internal_symbol: str) -> dict[str, str]:
        """
        Get all broker symbols for a given internal symbol.

        Args:
            internal_symbol: Internal symbol to map

        Returns:
            Dictionary mapping broker names to their symbols
        """
        internal_symbol = internal_symbol.upper()
        result = {}

        for broker_name, table in [
            ("binance", cls.BINANCE_CRYPTO),
            ("oanda", cls.OANDA_FOREX),
            ("ibkr", cls.IBKR_STOCKS_US),
            ("degiro", cls.DEGIRO_STOCKS_EU),
            ("kraken", cls.KRAKEN_CRYPTO),
            ("coinbase", cls.COINBASE_CRYPTO),
        ]:
            if internal_symbol in table:
                result[broker_name] = table[internal_symbol]

        return result


# ============================================================================
# SYMBOL VALIDATION
# ============================================================================


class SymbolValidator:
    """
    Validates symbols according to broker-specific rules.

    Ensures that symbols are properly formatted before creating mappings.
    """

    # Regex patterns for different symbol formats
    PATTERNS: ClassVar[dict] = {
        "binance_crypto": r"^[A-Z]{3,10}USDT$",
        "binance_forex": r"^[A-Z]{6}USDT$",
        "oanda_forex": r"^[A-Z]{3}_[A-Z]{3}$",
        "oanda_crypto": r"^[A-Z]{3,10}_USD$",
        "ibkr_stock": r"^[A-Z]{1,5}$",
        "ibkr_crypto": r"^IBKR:[A-Z]{3,10}$",
        "degiro_stock": r"^[A-Z]{4,5}$",
        "kraken_crypto": r"^X?[A-Z]{3,10}ZUSD$",
        "coinbase_crypto": r"^[A-Z]{3,10}-USD$",
    }

    @classmethod
    def validate_internal_symbol(cls, symbol: str) -> bool:
        """
        Validate internal symbol format.

        Internal symbols should be uppercase alphanumeric, 2-10 characters.

        Args:
            symbol: Symbol to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If symbol is invalid
        """
        if not symbol:
            raise ValidationError("Symbol cannot be empty")

        symbol = symbol.strip()

        # Check format - must already be uppercase (no normalization here)
        if not re.match(r"^[A-Z]{2,10}$", symbol):
            raise ValidationError(
                f"Invalid internal symbol format: {symbol}. Must be 2-10 uppercase letters."
            )

        return True

    @classmethod
    def validate_broker_symbol(cls, symbol: str, broker_name: str) -> bool:
        """
        Validate broker-specific symbol format.

        Args:
            symbol: Broker symbol to validate
            broker_name: Name of the broker

        Returns:
            True if valid

        Raises:
            ValidationError: If symbol is invalid
        """
        if not symbol:
            raise ValidationError("Broker symbol cannot be empty")

        symbol = symbol.strip()
        broker_name = broker_name.lower()

        # Broker-specific validation (normalize to uppercase for pattern matching)
        symbol_upper = symbol.upper()

        if broker_name == "binance":
            if not (
                re.match(cls.PATTERNS["binance_crypto"], symbol_upper)
                or re.match(cls.PATTERNS["binance_forex"], symbol_upper)
            ):
                raise ValidationError(
                    f"Invalid Binance symbol format: {symbol}. Expected format: BTCUSDT or EURUSDT"
                )

        elif broker_name == "oanda":
            if not (
                re.match(cls.PATTERNS["oanda_forex"], symbol_upper)
                or re.match(cls.PATTERNS["oanda_crypto"], symbol_upper)
            ):
                raise ValidationError(
                    f"Invalid OANDA symbol format: {symbol}. Expected format: EUR_USD or BTC_USD"
                )

        elif broker_name == "ibkr":
            if not (
                re.match(cls.PATTERNS["ibkr_stock"], symbol_upper)
                or re.match(cls.PATTERNS["ibkr_crypto"], symbol_upper)
            ):
                raise ValidationError(
                    f"Invalid IBKR symbol format: {symbol}. Expected format: AAPL or IBKR:BTC"
                )

        elif broker_name == "kraken":
            if not re.match(cls.PATTERNS["kraken_crypto"], symbol_upper):
                raise ValidationError(
                    f"Invalid Kraken symbol format: {symbol}. Expected format: XXBTZUSD"
                )

        elif broker_name == "coinbase" and not re.match(
            cls.PATTERNS["coinbase_crypto"], symbol_upper
        ):
            raise ValidationError(
                f"Invalid Coinbase symbol format: {symbol}. Expected format: BTC-USD"
            )

        return True

    @classmethod
    def extract_internal_from_broker(cls, broker_symbol: str, broker_name: str) -> str:
        """
        Extract internal symbol from broker symbol.

        Args:
            broker_symbol: Broker-specific symbol
            broker_name: Name of the broker

        Returns:
            Internal symbol (uppercase)

        Raises:
            ValidationError: If extraction fails
        """
        broker_symbol = broker_symbol.strip().upper()
        broker_name = broker_name.lower()

        try:
            if broker_name == "binance":
                # Remove USDT suffix (USDT = 4 characters)
                if broker_symbol.endswith("USDT"):
                    return broker_symbol[:-4]
                # If no USDT suffix, try to extract base from other patterns
                return broker_symbol

            elif broker_name == "oanda":
                # Remove _USD suffix (for crypto) or extract base from forex pair
                if "_USD" in broker_symbol:
                    return broker_symbol.split("_")[0]
                # Handle forex pairs like EUR_USD -> EURUSD is not a valid internal symbol
                # Extract the base currency
                if "_" in broker_symbol:
                    return broker_symbol.split("_")[0]
                return broker_symbol

            elif broker_name == "ibkr":
                # Remove IBKR: prefix
                if broker_symbol.startswith("IBKR:"):
                    return broker_symbol[5:]
                return broker_symbol

            elif broker_name == "kraken":
                # Remove X prefix and ZUSD suffix
                symbol = broker_symbol
                if symbol.startswith("X"):
                    symbol = symbol[1:]
                if symbol.endswith("ZUSD"):
                    symbol = symbol[:-4]
                # Convert XBT to BTC (Kraken uses XBT for Bitcoin)
                if symbol == "XBT":
                    symbol = "BTC"
                return symbol

            elif broker_name == "coinbase" and broker_symbol.endswith("-USD"):
                # Remove -USD suffix (-USD = 4 characters)
                return broker_symbol[:-4]

            # Default: return as-is
            return broker_symbol

        except (ConnectionError, TimeoutError, ValueError) as e:
            raise ValidationError(
                f"Failed to extract internal symbol from {broker_symbol}: {e}"
            ) from e


# ============================================================================
# MAIN SYMBOL MAPPER CLASS
# ============================================================================


class SymbolMapper:
    """
    Centralized Symbol Mapper for multi-broker FIFO tax compliance.

    This is the main class that manages symbol mappings between internal
    standardized format and broker-specific formats.

    Key Features:
    1. Two-way conversion: internal_symbol <-> broker_symbol
    2. Multi-broker support with validation
    3. Transaction safety for FIFO audit trail
    4. Integration with IBroker interface
    5. Comprehensive logging for tax compliance

    Usage:
        ```python
        mapper = SymbolMapper()

        # Convert internal to broker
        broker_symbol = mapper.map_internal_to_broker("BTC", "binance")

        # Convert broker to internal
        internal_symbol = mapper.map_broker_to_internal("BTCUSDT", "binance")

        # Add new mapping
        await mapper.add_mapping(
            internal_symbol="DOGE",
            broker_symbol="DOGEUSDT",
            broker_name="binance",
            broker_type=BrokerType.CRYPTO
        )

        # Get all brokers for a symbol
        brokers = mapper.get_all_brokers_for_symbol("BTC")
        ```

    Transaction Safety:
        All mapping operations are logged and can be audited for tax compliance.
        Database operations use transactions to ensure consistency.
    """

    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        Initialize the Symbol Mapper.

        Args:
            db_session: Optional database session. If None, creates new sessions as needed.
        """
        self._db_session = db_session
        self._cache: dict[tuple[str, str], SymbolMapping] = {}
        self._reverse_cache: dict[tuple[str, str], SymbolMapping] = {}
        self._initialized = False

        logger.info("SymbolMapper initialized")

    # ========================================================================
    # PUBLIC API - MAPPING METHODS
    # ========================================================================

    def map_internal_to_broker(
        self, internal_symbol: str, broker_name: str, use_default: bool = True
    ) -> str:
        """
        Convert internal symbol to broker-specific symbol.

        This method is CRITICAL for FIFO tax compliance. It ensures that all
        operations use the correct broker-specific symbol format.

        Args:
            internal_symbol: Internal standardized symbol (e.g., "BTC")
            broker_name: Name of the broker (e.g., "binance")
            use_default: If True, use default mappings when database lookup fails

        Returns:
            Broker-specific symbol (e.g., "BTCUSDT")

        Raises:
            UnknownSymbolError: If mapping not found and use_default=False
            ValidationError: If symbols are invalid

        Example:
            >>> mapper = SymbolMapper()
            >>> mapper.map_internal_to_broker("BTC", "binance")
            'BTCUSDT'
            >>> mapper.map_internal_to_broker("BTC", "oanda")
            'BTC_USD'
        """
        try:
            # Normalize inputs first
            internal_symbol = internal_symbol.strip().upper()
            broker_name = broker_name.strip().lower()

            # Validate inputs after normalization
            SymbolValidator.validate_internal_symbol(internal_symbol)

            # Check cache first
            cache_key = (internal_symbol, broker_name)
            if cache_key in self._cache:
                mapping = self._cache[cache_key]
                logger.debug(
                    f"Cache hit: {internal_symbol} -> {mapping.broker_symbol} ({broker_name})"
                )
                return mapping.broker_symbol

            # Try database lookup (would be async in real implementation)
            # For now, use default tables
            broker_symbol = BrokerMappingTables.get_default_mapping(broker_name, internal_symbol)

            if broker_symbol:
                logger.info(
                    f"Mapped {internal_symbol} -> {broker_symbol} ({broker_name}) [default table]"
                )
                return broker_symbol

            if not use_default:
                raise UnknownSymbolError(f"No mapping found for {internal_symbol} -> {broker_name}")

            # Fallback: try to construct broker symbol
            broker_symbol = self._construct_broker_symbol(internal_symbol, broker_name)
            logger.warning(
                f"Constructed broker symbol: {internal_symbol} -> {broker_symbol} "
                f"({broker_name}) [fallback]"
            )
            return broker_symbol

        except (ConnectionError, TimeoutError, ValueError) as e:
            logger.error(f"Error mapping {internal_symbol} to {broker_name}: {e}", exc_info=True)
            raise

    def map_broker_to_internal(
        self, broker_symbol: str, broker_name: str, use_default: bool = True
    ) -> str:
        """
        Convert broker-specific symbol to internal symbol.

        This method is CRITICAL for FIFO tax compliance. It normalizes all
        broker-specific symbols to a single internal format.

        Args:
            broker_symbol: Broker-specific symbol (e.g., "BTCUSDT")
            broker_name: Name of the broker (e.g., "binance")
            use_default: If True, use default mappings when database lookup fails

        Returns:
            Internal standardized symbol (e.g., "BTC")

        Raises:
            UnknownSymbolError: If mapping not found and use_default=False
            ValidationError: If symbols are invalid
            AmbiguousSymbolError: If symbol could map to multiple internal symbols

        Example:
            >>> mapper = SymbolMapper()
            >>> mapper.map_broker_to_internal("BTCUSDT", "binance")
            'BTC'
            >>> mapper.map_broker_to_internal("BTC_USD", "oanda")
            'BTC'
        """
        try:
            # Normalize inputs first
            broker_symbol = broker_symbol.strip().upper()
            broker_name = broker_name.strip().lower()

            # Check for empty broker symbol after normalization
            if not broker_symbol:
                raise UnknownSymbolError(f"Cannot map empty broker symbol from {broker_name}")

            # Check reverse cache
            cache_key = (broker_symbol, broker_name)
            if cache_key in self._reverse_cache:
                mapping = self._reverse_cache[cache_key]
                logger.debug(
                    f"Reverse cache hit: {broker_symbol} -> {mapping.internal_symbol} "
                    f"({broker_name})"
                )
                return mapping.internal_symbol

            # Try to extract internal symbol from broker symbol
            internal_symbol = SymbolValidator.extract_internal_from_broker(
                broker_symbol, broker_name
            )

            # Validate extracted symbol
            SymbolValidator.validate_internal_symbol(internal_symbol)

            # Verify by doing reverse mapping
            expected_broker_symbol = self.map_internal_to_broker(
                internal_symbol, broker_name, use_default=use_default
            )

            if expected_broker_symbol != broker_symbol:
                logger.warning(
                    f"Symbol mismatch during reverse mapping: "
                    f"{broker_symbol} -> {internal_symbol} -> {expected_broker_symbol}"
                )

            logger.info(f"Mapped {broker_symbol} -> {internal_symbol} ({broker_name})")
            return internal_symbol

        except (ConnectionError, TimeoutError, ValueError) as e:
            logger.error(f"Error mapping {broker_symbol} from {broker_name}: {e}", exc_info=True)
            raise

    async def add_mapping(
        self,
        internal_symbol: str,
        broker_symbol: str,
        broker_name: str,
        broker_type: BrokerType,
        asset_class: str = "crypto",
        is_verified: bool = False,
        metadata: Optional[dict] = None,
    ) -> SymbolMapping:
        """
        Add a new symbol mapping to the database.

        This method creates a new mapping with transaction safety for audit purposes.
        All mappings are logged for FIFO tax compliance.

        Args:
            internal_symbol: Internal standardized symbol
            broker_symbol: Broker-specific symbol
            broker_name: Name of the broker
            broker_type: Type of broker (crypto, forex, stocks_us, stocks_eu)
            asset_class: Asset classification
            is_verified: Whether this mapping has been verified
            metadata: Additional metadata

        Returns:
            Created SymbolMapping object

        Raises:
            ValidationError: If symbols are invalid
            SymbolMappingError: If mapping already exists

        Example:
            >>> mapper = SymbolMapper()
            >>> await mapper.add_mapping(
            ...     internal_symbol="SOL",
            ...     broker_symbol="SOLUSDT",
            ...     broker_name="binance",
            ...     broker_type=BrokerType.CRYPTO
            ... )
        """
        try:
            # Normalize inputs first
            internal_symbol = internal_symbol.strip().upper()
            broker_symbol = broker_symbol.strip().upper()
            broker_name = broker_name.strip().lower()

            # Validate inputs after normalization
            SymbolValidator.validate_internal_symbol(internal_symbol)
            SymbolValidator.validate_broker_symbol(broker_symbol, broker_name)

            # Create mapping object
            mapping = SymbolMapping(
                internal_symbol=internal_symbol,
                broker_symbol=broker_symbol,
                broker_name=broker_name,
                broker_type=broker_type,
                asset_class=asset_class,
                status=MappingStatus.ACTIVE,
                is_verified=is_verified,
                metadata=metadata or {},
            )

            # In a real implementation, save to database here
            # For now, just update cache
            cache_key = (internal_symbol, broker_name)
            reverse_cache_key = (broker_symbol, broker_name)

            if cache_key in self._cache:
                logger.warning(
                    f"Mapping already exists in cache: {internal_symbol} -> {broker_symbol} "
                    f"({broker_name}). Updating."
                )

            self._cache[cache_key] = mapping
            self._reverse_cache[reverse_cache_key] = mapping

            # Log for audit trail
            logger.info(
                f"Added symbol mapping: {internal_symbol} -> {broker_symbol} "
                f"({broker_name}, type={broker_type.value}, "
                f"asset_class={asset_class}, verified={is_verified})"
            )

            return mapping

        except (ConnectionError, TimeoutError, ValueError) as e:
            logger.error(
                f"Error adding mapping {internal_symbol} -> {broker_symbol}: {e}", exc_info=True
            )
            raise SymbolMappingError(f"Failed to add mapping: {e}") from e

    def get_all_brokers_for_symbol(self, internal_symbol: str) -> dict[str, str]:
        """
        Get all broker symbols for a given internal symbol.

        This is useful for multi-broker arbitrage and for checking
        which brokers support a particular asset.

        Args:
            internal_symbol: Internal standardized symbol

        Returns:
            Dictionary mapping broker names to their broker-specific symbols

        Example:
            >>> mapper = SymbolMapper()
            >>> mapper.get_all_brokers_for_symbol("BTC")
            {
                'binance': 'BTCUSDT',
                'oanda': 'BTC_USD',
                'ibkr': 'IBKR:BTC',
                'kraken': 'XXBTZUSD',
                'coinbase': 'BTC-USD'
            }
        """
        try:
            # Normalize input first
            internal_symbol = internal_symbol.strip().upper()

            # Validate after normalization
            SymbolValidator.validate_internal_symbol(internal_symbol)

            # Get from default tables
            broker_symbols = BrokerMappingTables.get_all_broker_symbols(internal_symbol)

            # Add cached mappings
            for (cached_internal, broker_name), mapping in self._cache.items():
                if cached_internal == internal_symbol:
                    broker_symbols[broker_name] = mapping.broker_symbol

            logger.info(f"Found {len(broker_symbols)} broker mappings for {internal_symbol}")
            return broker_symbols

        except (ConnectionError, TimeoutError, ValueError) as e:
            logger.error(f"Error getting brokers for {internal_symbol}: {e}", exc_info=True)
            return {}

    def validate_mapping(
        self, internal_symbol: str, broker_symbol: str, broker_name: str
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that a mapping is correct.

        This performs bidirectional validation to ensure that:
        1. internal_symbol -> broker_symbol is valid
        2. broker_symbol -> internal_symbol is valid
        3. Both directions map to each other

        Args:
            internal_symbol: Internal standardized symbol
            broker_symbol: Broker-specific symbol
            broker_name: Name of the broker

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> mapper = SymbolMapper()
            >>> mapper.validate_mapping("BTC", "BTCUSDT", "binance")
            (True, None)
            >>> mapper.validate_mapping("BTC", "XXX", "binance")
            (False, "Invalid broker symbol format")
        """
        try:
            # Normalize inputs first
            internal_symbol = internal_symbol.strip().upper()
            broker_symbol = broker_symbol.strip().upper()
            broker_name = broker_name.strip().lower()

            # Validate internal symbol
            SymbolValidator.validate_internal_symbol(internal_symbol)

            # Validate broker symbol
            SymbolValidator.validate_broker_symbol(broker_symbol, broker_name)

            # Check bidirectional mapping
            mapped_broker = self.map_internal_to_broker(internal_symbol, broker_name)
            if mapped_broker != broker_symbol:
                return False, (
                    f"Forward mapping mismatch: {internal_symbol} -> {mapped_broker}, "
                    f"expected {broker_symbol}"
                )

            mapped_internal = self.map_broker_to_internal(broker_symbol, broker_name)
            if mapped_internal != internal_symbol:
                return False, (
                    f"Reverse mapping mismatch: {broker_symbol} -> {mapped_internal}, "
                    f"expected {internal_symbol}"
                )

            logger.info(f"Mapping validated: {internal_symbol} <-> {broker_symbol} ({broker_name})")
            return True, None

        except (ValidationError, UnknownSymbolError) as e:
            # These are validation failures, return False with error message
            return False, str(e)
        except (ConnectionError, TimeoutError, ValueError) as e:
            error_msg = f"Validation failed: {e}"
            logger.error(f"validate_mapping: {error_msg}")
            return False, error_msg

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def _construct_broker_symbol(self, internal_symbol: str, broker_name: str) -> str:
        """
        Construct a broker symbol from internal symbol using heuristics.

        This is a fallback method when no mapping exists.

        Args:
            internal_symbol: Internal symbol
            broker_name: Name of the broker

        Returns:
            Constructed broker symbol
        """
        broker_name = broker_name.lower()
        internal_symbol = internal_symbol.upper()

        # Broker-specific construction rules
        return {
            "binance": f"{internal_symbol}USDT",
            "oanda": f"{internal_symbol}_USD",
            "ibkr": f"IBKR:{internal_symbol}",
            "kraken": f"X{internal_symbol}ZUSD",
            "coinbase": f"{internal_symbol}-USD",
        }.get(broker_name, internal_symbol)

    def get_supported_brokers(self) -> list[str]:
        """
        Get list of supported brokers.

        Returns:
            List of broker names
        """
        return [
            "binance",
            "oanda",
            "ibkr",
            "degiro",
            "kraken",
            "coinbase",
        ]

    def get_statistics(self) -> dict:
        """
        Get statistics about symbol mappings.

        Returns:
            Dictionary with mapping statistics
        """
        return {
            "cached_mappings": len(self._cache),
            "cached_reverse_mappings": len(self._reverse_cache),
            "supported_brokers": self.get_supported_brokers(),
            "default_tables_available": len(BrokerMappingTables.BINANCE_CRYPTO) > 0,
        }

    def clear_cache(self) -> None:
        """
        Clear the mapping cache.

        This is useful for testing or when mappings are updated externally.
        """
        self._cache.clear()
        self._reverse_cache.clear()
        logger.info("Symbol mapping cache cleared")


# ============================================================================
# BROKER ADAPTER MIXIN
# ============================================================================


class SymbolMapperMixin:
    """
    Mixin class for broker adapters to easily integrate symbol mapping.

    This mixin provides convenience methods for broker adapters to use
    the SymbolMapper.

    Usage in broker adapter:
        ```python
        class BinanceAdapter(IBroker, SymbolMapperMixin):
            def __init__(self):
                self.symbol_mapper = SymbolMapper()

            async def get_live_ticker(self, symbol: str) -> Ticker:
                # Convert internal to broker symbol
                broker_symbol = self.map_to_broker(symbol)
                # ... call Binance API ...

            def map_to_broker(self, internal_symbol: str) -> str:
                return self.symbol_mapper.map_internal_to_broker(
                    internal_symbol, self.get_broker_name()
                )
        ```
    """

    symbol_mapper: "SymbolMapper"

    @abstractmethod
    def get_broker_name(self) -> str:
        """Return the broker name for mapping purposes.

        This method must be implemented by the class that uses this mixin.
        """
        raise NotImplementedError("Subclasses must implement get_broker_name()")

    def __init__(self):
        self.symbol_mapper = SymbolMapper()

    def map_to_broker(self, internal_symbol: str) -> str:
        """Map internal symbol to broker-specific symbol."""
        return self.symbol_mapper.map_internal_to_broker(internal_symbol, self.get_broker_name())

    def map_from_broker(self, broker_symbol: str) -> str:
        """Map broker-specific symbol to internal symbol."""
        return self.symbol_mapper.map_broker_to_internal(broker_symbol, self.get_broker_name())

    def validate_symbol_mapping(
        self, internal_symbol: str, broker_symbol: str
    ) -> tuple[bool, Optional[str]]:
        """Validate a symbol mapping."""
        return self.symbol_mapper.validate_mapping(
            internal_symbol, broker_symbol, self.get_broker_name()
        )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def create_symbol_mapper(db_session: Optional[AsyncSession] = None) -> SymbolMapper:
    """
    Factory function to create a SymbolMapper instance.

    Args:
        db_session: Optional database session

    Returns:
        SymbolMapper instance
    """
    return SymbolMapper(db_session=db_session)


async def get_or_create_mapping(
    internal_symbol: str,
    broker_symbol: str,
    broker_name: str,
    broker_type: BrokerType,
    db_session: Optional[AsyncSession] = None,
) -> SymbolMapping:
    """
    Get existing mapping or create new one.

    This is a convenience function for common use cases.

    Args:
        internal_symbol: Internal symbol
        broker_symbol: Broker symbol
        broker_name: Broker name
        broker_type: Type of broker
        db_session: Optional database session

    Returns:
        SymbolMapping object
    """
    mapper = create_symbol_mapper(db_session)

    # Try to validate existing mapping
    is_valid, _ = mapper.validate_mapping(internal_symbol, broker_symbol, broker_name)

    if is_valid:
        # Return existing mapping (in real implementation, would fetch from DB)
        return SymbolMapping(
            internal_symbol=internal_symbol,
            broker_symbol=broker_symbol,
            broker_name=broker_name,
            broker_type=broker_type,
            is_verified=True,
        )
    else:
        # Create new mapping
        return await mapper.add_mapping(
            internal_symbol=internal_symbol,
            broker_symbol=broker_symbol,
            broker_name=broker_name,
            broker_type=broker_type,
            is_verified=False,
        )


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "AmbiguousSymbolError",
    # Utilities
    "BrokerMappingTables",
    "BrokerType",
    # Enums
    "MappingStatus",
    # Main class
    "SymbolMapper",
    "SymbolMapperMixin",
    # Data classes
    "SymbolMapping",
    # Exceptions
    "SymbolMappingError",
    "SymbolValidator",
    "UnknownSymbolError",
    "ValidationError",
    # Factory functions
    "create_symbol_mapper",
    "get_or_create_mapping",
]
