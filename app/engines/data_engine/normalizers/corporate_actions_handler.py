"""
CorporateActionsHandler - Manejo de corporate actions.

Detecta y aplica splits, dividendos, y otras corporate actions.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CorporateActionsHandler:
    """
    Handler para corporate actions.

    Detecta, almacena y aplica corporate actions (splits, dividendos, etc.)
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar handler.

        Args:
            config: Configuración
        """
        config = config or {}
        self.actions_db: Dict[str, List[Dict[str, Any]]] = {}
        self.auto_detect = config.get('auto_detect', False)

    def register_split(
        self, symbol: str, date: datetime, ratio: float, description: Optional[str] = None
    ) -> None:
        """
        Registrar un stock split.

        Args:
            symbol: Símbolo
            date: Fecha del split
            ratio: Ratio del split (ej: 2.0 para 2:1 split)
            description: Descripción opcional
        """
        if symbol not in self.actions_db:
            self.actions_db[symbol] = []

        action = {
            'type': 'split',
            'date': date,
            'ratio': ratio,
            'description': description or f"{ratio}:1 split",
        }

        self.actions_db[symbol].append(action)
        logger.info(f"Split registrado: {symbol} {ratio}:1 en {date}")

    def register_dividend(
        self, symbol: str, date: datetime, amount: Decimal, description: Optional[str] = None
    ) -> None:
        """
        Registrar un dividendo.

        Args:
            symbol: Símbolo
            date: Fecha ex-dividend
            amount: Monto del dividendo
            description: Descripción opcional
        """
        if symbol not in self.actions_db:
            self.actions_db[symbol] = []

        action = {
            'type': 'dividend',
            'date': date,
            'amount': float(amount),
            'description': description or f"Dividend ${amount}",
        }

        self.actions_db[symbol].append(action)
        logger.info(f"Dividendo registrado: {symbol} ${amount} en {date}")

    def get_actions(
        self,
        symbol: str,
        action_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Obtener corporate actions para un símbolo.

        Args:
            symbol: Símbolo
            action_type: Tipo de acción (opcional)
            start_date: Fecha de inicio (opcional)
            end_date: Fecha de fin (opcional)

        Returns:
            Lista de acciones
        """
        if symbol not in self.actions_db:
            return []

        actions = self.actions_db[symbol]

        # Filtrar por tipo
        if action_type:
            actions = [a for a in actions if a.get('type') == action_type]

        # Filtrar por fecha
        if start_date:
            actions = [a for a in actions if a.get('date') >= start_date]

        if end_date:
            actions = [a for a in actions if a.get('date') <= end_date]

        return sorted(actions, key=lambda x: x.get('date'))

    def detect_split_from_price_jump(
        self,
        symbol: str,
        prices: List[Decimal],
        timestamps: List[datetime],
        threshold: float = 0.4,  # 40% jump indica posible split
    ) -> List[Dict[str, Any]]:
        """
        Detectar splits automáticamente basado en saltos de precio.

        Args:
            symbol: Símbolo
            prices: Lista de precios históricos
            timestamps: Lista de timestamps
            threshold: Threshold para detectar split (ratio de cambio)

        Returns:
            Lista de splits detectados
        """
        if len(prices) < 2:
            return []

        detected_splits = []

        for i in range(1, len(prices)):
            prev_price = float(prices[i - 1])
            curr_price = float(prices[i])

            if prev_price > 0:
                change_ratio = abs(curr_price / prev_price - 1)

                # Si el cambio es muy grande, podría ser un split
                if change_ratio > threshold and curr_price < prev_price:
                    # Calcular ratio del split (aproximado)
                    # Split hacia abajo (ej: 2:1)
                    ratio = prev_price / curr_price
                    if 1.5 <= ratio <= 10:  # Ratios razonables
                        detected_splits.append(
                            {
                                'type': 'split',
                                'date': timestamps[i],
                                'ratio': ratio,
                                'description': f"Auto-detectado: {ratio:.2f}:1 split",
                            }
                        )

        # Registrar splits detectados
        for split in detected_splits:
            self.register_split(symbol, split['date'], split['ratio'], split['description'])

        return detected_splits

    def apply_adjustments_to_prices(
        self,
        symbol: str,
        prices: List[Decimal],
        timestamps: List[datetime],
        adjust_splits: bool = True,
        adjust_dividends: bool = True,
    ) -> List[Decimal]:
        """
        Aplicar ajustes de corporate actions a precios históricos.

        Args:
            symbol: Símbolo
            prices: Lista de precios
            timestamps: Lista de timestamps
            adjust_splits: Aplicar ajustes por splits
            adjust_dividends: Aplicar ajustes por dividendos

        Returns:
            Lista de precios ajustados
        """
        if symbol not in self.actions_db:
            return prices

        adjusted_prices = prices.copy()
        actions = self.get_actions(symbol)

        # Ordenar acciones por fecha (más reciente primero)
        actions = sorted(actions, key=lambda x: x.get('date'), reverse=True)

        for action in actions:
            action_date = action.get('date')
            action_type = action.get('type')

            # Aplicar ajustes a precios antes de la fecha de la acción
            for i, (price, ts) in enumerate(zip(adjusted_prices, timestamps)):
                if ts < action_date:
                    if action_type == 'split' and adjust_splits:
                        ratio = action.get('ratio', 1.0)
                        if ratio > 0:
                            adjusted_prices[i] = price * Decimal(str(ratio))

                    elif action_type == 'dividend' and adjust_dividends:
                        amount = Decimal(str(action.get('amount', 0)))
                        adjusted_prices[i] = price - amount

        return adjusted_prices
