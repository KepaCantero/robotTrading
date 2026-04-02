"""
SymbolNormalizer - Normalización de símbolos.

Normaliza símbolos de diferentes formatos a formato estándar.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


class SymbolNormalizer:
    """
    Normalizador de símbolos de trading.

    Convierte símbolos a formato estándar y maneja variaciones.
    """

    def __init__(self, config: dict[str, str | int | float | bool] | None = None):
        """
        Inicializar normalizador.

        Args:
            config: Configuración
        """
        config = config or {}
        self.uppercase = config.get("uppercase", True)
        self.remove_suffixes = config.get("remove_suffixes", True)
        self.suffix_mappings: dict[str, str] = config.get(
            "suffix_mappings",
            {
                ".US": "",  # Polygon format
                ".TO": "",  # Toronto
                ".L": "",  # London
                ".T": "",  # Tokyo
                ".HK": "",  # Hong Kong
            },
        )
        self.exchange_mappings: dict[str, dict[str, str]] = config.get("exchange_mappings", {})

    def normalize(self, symbol: str | int | float, source: str | None = None) -> str:
        """
        Normalizar símbolo a formato estándar.

        Args:
            symbol: Símbolo en cualquier formato
            source: Fuente de datos (opcional, para mapeos específicos)

        Returns:
            Símbolo normalizado
        """
        try:
            # Convertir a string
            symbol_str = str(symbol).strip()

            if not symbol_str:
                raise ValueError("Símbolo vacío")

            # Aplicar uppercase si está configurado
            if self.uppercase:
                symbol_str = symbol_str.upper()

            # Remover sufijos de exchange
            if self.remove_suffixes:
                for suffix, replacement in self.suffix_mappings.items():
                    if symbol_str.endswith(suffix):
                        symbol_str = symbol_str[: -len(suffix)] + replacement

            # Aplicar mapeos específicos de exchange
            if source:
                mapping = self.exchange_mappings.get(source)
                if mapping:
                    symbol_str = mapping.get(symbol_str, symbol_str)

            # Limpiar caracteres especiales (mantener letras, números, puntos, guiones)
            symbol_str = re.sub(r"[^A-Z0-9.\-]", "", symbol_str)

            return symbol_str

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error normalizando símbolo {symbol}: {e}")
            return str(symbol).strip().upper()

    def normalize_batch(self, symbols: list, source: str | None = None) -> list:
        """
        Normalizar múltiples símbolos.

        Args:
            symbols: Lista de símbolos
            source: Fuente de datos (opcional)

        Returns:
            Lista de símbolos normalizados
        """
        return [self.normalize(sym, source) for sym in symbols]

    def get_variations(self, symbol: str) -> list:
        """
        Obtener variaciones posibles de un símbolo.

        Útil para búsqueda flexible.

        Args:
            symbol: Símbolo base

        Returns:
            Lista de variaciones posibles
        """
        variations = [symbol]

        # Agregar sufijos comunes
        for suffix in [".US", ".TO", ".L", ".T", ".HK"]:
            variations.append(f"{symbol}{suffix}")

        return variations
