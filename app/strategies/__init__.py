"""
Sistema de Estrategias Múltiples - TASK-31

Este módulo implementa un framework modular para ejecutar múltiples estrategias
de trading sin modificar código, basado en el principio:
"Don't build a strategy. Build a machine that can build, test, and run any strategy."
"""

from .base import BaseStrategy
from .config_loader import StrategyConfigLoader
from .execution_engine import ExecutionEngine
from .factory import StrategyFactory
from .registry import StrategyRegistry
from .strategy_logger import StrategyLogger

__all__ = [
    "BaseStrategy",
    "StrategyFactory",
    "StrategyRegistry",
    "StrategyConfigLoader",
    "ExecutionEngine",
    "StrategyLogger",
]
