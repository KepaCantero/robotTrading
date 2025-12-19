"""
PriceNormalizer - Normalización de precios.

Maneja ajustes por splits, dividendos y corporate actions.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PriceNormalizer:
    """
    Normalizador de precios.

    Ajusta precios históricos por splits, dividendos y otras corporate actions.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar normalizador.

        Args:
            config: Configuración
        """
        config = config or {}
        self.apply_splits = config.get('apply_splits', True)
        self.apply_dividends = config.get('apply_dividends', True)
        self.corporate_actions_db: Dict[str, List[Dict[str, Any]]] = {}

    def normalize(
        self,
        price: Any,
        symbol: str,
        timestamp: datetime,
        adjust_for_splits: bool = True,
        adjust_for_dividends: bool = True,
    ) -> Decimal:
        """
        Normalizar precio.

        Args:
            price: Precio a normalizar
            symbol: Símbolo del instrumento
            timestamp: Timestamp del precio
            adjust_for_splits: Aplicar ajustes por splits
            adjust_for_dividends: Aplicar ajustes por dividendos

        Returns:
            Precio normalizado
        """
        try:
            # Convertir a Decimal
            if isinstance(price, Decimal):
                normalized_price = price
            elif isinstance(price, (int, float)):
                normalized_price = Decimal(str(price))
            else:
                normalized_price = Decimal(str(price))

            # Aplicar ajustes
            if adjust_for_splits and self.apply_splits:
                normalized_price = self._apply_splits(normalized_price, symbol, timestamp)

            if adjust_for_dividends and self.apply_dividends:
                normalized_price = self._apply_dividends(normalized_price, symbol, timestamp)

            return normalized_price

        except Exception as e:
            logger.error(f"Error normalizando precio {price}: {e}")
            return Decimal(str(price))

    def _apply_splits(self, price: Decimal, symbol: str, timestamp: datetime) -> Decimal:
        """
        Aplicar ajustes por stock splits.

        Args:
            price: Precio original
            symbol: Símbolo
            timestamp: Timestamp

        Returns:
            Precio ajustado
        """
        # Buscar splits en el futuro (precios históricos se ajustan hacia atrás)
        if symbol not in self.corporate_actions_db:
            return price

        actions = self.corporate_actions_db[symbol]
        # Filtrar con validación explícita de tipo
        splits = [
            a
            for a in actions
            if a.get('type') == 'split'
            and isinstance(a.get('date'), datetime)
            and a.get('date') > timestamp
        ]

        # Función auxiliar para obtener fecha con tipo correcto
        def get_split_date(action: dict) -> datetime:
            date = action.get('date')
            return date if isinstance(date, datetime) else datetime.min

        # Aplicar splits en orden cronológico
        for split in sorted(splits, key=get_split_date):
            ratio = split.get('ratio', 1.0)
            if ratio > 0:
                price = price * Decimal(str(ratio))

        return price

    def _apply_dividends(self, price: Decimal, symbol: str, timestamp: datetime) -> Decimal:
        """
        Aplicar ajustes por dividendos.

        Args:
            price: Precio original
            symbol: Símbolo
            timestamp: Timestamp

        Returns:
            Precio ajustado
        """
        # Buscar dividendos en el futuro
        if symbol not in self.corporate_actions_db:
            return price

        actions = self.corporate_actions_db[symbol]
        # Filtrar con validación explícita de tipo
        dividends = [
            a
            for a in actions
            if a.get('type') == 'dividend'
            and isinstance(a.get('date'), datetime)
            and a.get('date') > timestamp
        ]

        # Función auxiliar para obtener fecha con tipo correcto
        def get_dividend_date(action: dict) -> datetime:
            date = action.get('date')
            return date if isinstance(date, datetime) else datetime.min

        # Aplicar ajustes por dividendos (restar del precio)
        for dividend in sorted(dividends, key=get_dividend_date):
            amount = Decimal(str(dividend.get('amount', 0)))
            price = price - amount

        return price

    def register_corporate_action(
        self, symbol: str, action_type: str, date: datetime, **kwargs
    ) -> None:
        """
        Registrar una corporate action.

        Args:
            symbol: Símbolo
            action_type: Tipo (split, dividend, etc.)
            date: Fecha de la acción
            **kwargs: Datos adicionales (ratio, amount, etc.)
        """
        if symbol not in self.corporate_actions_db:
            self.corporate_actions_db[symbol] = []

        action = {'type': action_type, 'date': date, **kwargs}

        self.corporate_actions_db[symbol].append(action)
        logger.debug(f"Corporate action registrada: {symbol} {action_type} en {date}")

    def normalize_batch(
        self,
        prices: List[Any],
        symbol: str,
        timestamps: List[datetime],
        adjust_for_splits: bool = True,
        adjust_for_dividends: bool = True,
    ) -> List[Decimal]:
        """
        Normalizar múltiples precios.

        Args:
            prices: Lista de precios
            symbol: Símbolo
            timestamps: Lista de timestamps correspondientes
            adjust_for_splits: Aplicar splits
            adjust_for_dividends: Aplicar dividendos

        Returns:
            Lista de precios normalizados
        """
        if len(prices) != len(timestamps):
            raise ValueError("prices y timestamps deben tener la misma longitud")

        return [
            self.normalize(price, symbol, ts, adjust_for_splits, adjust_for_dividends)
            for price, ts in zip(prices, timestamps)
        ]
