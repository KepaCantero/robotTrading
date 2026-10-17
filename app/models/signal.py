"""Re-export de los modelos de señal canónicos (viven en la capa domain).

Históricamente aquí había una copia divergente; unificar evita que
isinstance(x, Signal) falle según qué gemelo importe cada módulo.
"""

from app.domain.models.signal import (
    MarketData,
    Signal,
    SignalPriorityQueue,
    SignalScorer,
    SignalSource,
    SignalStrength,
    SignalType,
)

__all__ = [
    "MarketData",
    "Signal",
    "SignalPriorityQueue",
    "SignalScorer",
    "SignalSource",
    "SignalStrength",
    "SignalType",
]
