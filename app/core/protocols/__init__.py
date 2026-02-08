"""
Protocol interfaces for SOLID architecture

This module contains all Protocol interfaces used throughout
the application for dependency inversion and interface segregation.
"""

from app.core.protocols.i_pre_trade_validator import IPreTradeValidator
from app.core.protocols.i_trade_executor import ITradeExecutor
from app.core.protocols.i_post_trade_analyzer import IPostTradeAnalyzer
from app.core.protocols.i_broker_adapter import IBrokerAdapter
from app.core.protocols.i_spain_tax_engine import ISpainTaxEngine
from app.core.protocols.i_trading_decision_logger import ITradingDecisionLogger
from app.core.protocols.i_kill_switch_monitor import IKillSwitchMonitor
from app.core.protocols.i_alert_processor import IAlertProcessor
from app.core.protocols.i_strategy_cycle_runner import IStrategyCycleRunner

__all__ = [
    "IPreTradeValidator",
    "ITradeExecutor",
    "IPostTradeAnalyzer",
    "IBrokerAdapter",
    "ISpainTaxEngine",
    "ITradingDecisionLogger",
    "IKillSwitchMonitor",
    "IAlertProcessor",
    "IStrategyCycleRunner",
]
