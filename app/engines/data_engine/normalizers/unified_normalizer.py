"""
UnifiedNormalizer - Normalizador unificado que combina todos los normalizadores.
"""

import logging
from decimal import Decimal
from typing import Any, Optional

from .corporate_actions_handler import CorporateActionsHandler
from .price_normalizer import PriceNormalizer
from .symbol_normalizer import SymbolNormalizer
from .timestamp_normalizer import TimestampNormalizer

logger = logging.getLogger(__name__)


class UnifiedNormalizer:
    """
    Normalizador unificado que aplica todos los normalizadores.

    Combina:
    - Timestamp normalization
    - Symbol normalization
    - Price normalization (splits, dividendos)
    - Corporate actions handling
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Inicializar normalizador unificado.

        Args:
            config: Configuración
        """
        config = config or {}

        self.timestamp_normalizer = TimestampNormalizer(config.get("timestamp_config", {}))
        self.symbol_normalizer = SymbolNormalizer(config.get("symbol_config", {}))
        self.price_normalizer = PriceNormalizer(config.get("price_config", {}))
        self.corporate_actions_handler = CorporateActionsHandler(
            config.get("corporate_actions_config", {})
        )

        # Sincronizar corporate actions entre price_normalizer y handler
        self.price_normalizer.corporate_actions_db = self.corporate_actions_handler.actions_db

    def normalize_ohlcv_data(
        self, data: list[dict[str, Any]], symbol: str, source: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        Normalizar datos OHLCV completos.

        Args:
            data: Lista de diccionarios con datos OHLCV
            symbol: Símbolo normalizado
            source: Fuente de datos (opcional)

        Returns:
            Lista de datos normalizados
        """
        normalized_data = []

        # Normalizar símbolo
        normalized_symbol = self.symbol_normalizer.normalize(symbol, source)

        # Extraer timestamps y precios
        timestamps = []
        prices_dict = {"open": [], "high": [], "low": [], "close": []}

        for item in data:
            # Normalizar timestamp
            timestamp = self.timestamp_normalizer.normalize(
                item.get("timestamp"), source_timezone=item.get("timezone")
            )
            timestamps.append(timestamp)

            # Extraer precios
            for price_field in ["open", "high", "low", "close"]:
                prices_dict[price_field].append(item.get(price_field))

        # Aplicar ajustes de corporate actions
        if self.corporate_actions_handler.actions_db.get(normalized_symbol):
            # Aplicar ajustes a precios
            for price_field in ["open", "high", "low", "close"]:
                prices_dict[price_field] = (
                    self.corporate_actions_handler.apply_adjustments_to_prices(
                        normalized_symbol,
                        [
                            Decimal(str(p)) if not isinstance(p, Decimal) else p
                            for p in prices_dict[price_field]
                        ],
                        timestamps,
                    )
                )

        # Construir datos normalizados
        for i, item in enumerate(data):
            normalized_item = {
                "symbol": normalized_symbol,
                "timestamp": timestamps[i],
                "open": (
                    prices_dict["open"][i] if i < len(prices_dict["open"]) else item.get("open")
                ),
                "high": (
                    prices_dict["high"][i] if i < len(prices_dict["high"]) else item.get("high")
                ),
                "low": prices_dict["low"][i] if i < len(prices_dict["low"]) else item.get("low"),
                "close": (
                    prices_dict["close"][i] if i < len(prices_dict["close"]) else item.get("close")
                ),
                "volume": Decimal(str(item.get("volume", 0))),
                "source": source,
                "normalized": True,
            }

            # Mantener metadata adicional si existe
            if "metadata" in item:
                normalized_item["metadata"] = item["metadata"]

            normalized_data.append(normalized_item)

        return normalized_data

    def normalize_quote(
        self, quote_data: dict[str, Any], symbol: str, source: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Normalizar quote en tiempo real.

        Args:
            quote_data: Dict con datos del quote
            symbol: Símbolo
            source: Fuente de datos

        Returns:
            Quote normalizado
        """
        normalized_symbol = self.symbol_normalizer.normalize(symbol, source)
        normalized_timestamp = self.timestamp_normalizer.normalize(
            quote_data.get("timestamp"), source_timezone=quote_data.get("timezone")
        )

        normalized_quote = {
            "symbol": normalized_symbol,
            "timestamp": normalized_timestamp,
            "bid": Decimal(str(quote_data.get("bid", 0))),
            "ask": Decimal(str(quote_data.get("ask", 0))),
            "last": Decimal(str(quote_data.get("last", 0))),
            "open": Decimal(str(quote_data.get("open", 0))),
            "high": Decimal(str(quote_data.get("high", 0))),
            "low": Decimal(str(quote_data.get("low", 0))),
            "close": Decimal(str(quote_data.get("close", 0))),
            "volume": Decimal(str(quote_data.get("volume", 0))),
            "source": source,
            "normalized": True,
        }

        # Mantener metadata
        if "metadata" in quote_data:
            normalized_quote["metadata"] = quote_data["metadata"]

        return normalized_quote
