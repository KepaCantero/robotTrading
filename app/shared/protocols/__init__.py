"""
Protocol interfaces for SOLID architecture

This module contains all Protocol interfaces used throughout
the application for dependency inversion and interface segregation.
"""

from app.shared.protocols.i_alert_processor import IAlertProcessor
from app.shared.protocols.i_broker_adapter import IBrokerAdapter
from app.shared.protocols.i_data_feed import IDataFeed
from app.shared.protocols.i_kill_switch_monitor import IKillSwitchMonitor
from app.shared.protocols.i_post_trade_analyzer import IPostTradeAnalyzer
from app.shared.protocols.i_pre_trade_validator import IPreTradeValidator
from app.shared.protocols.i_spain_tax_engine import ISpainTaxEngine
from app.shared.protocols.i_strategy_cycle_runner import IStrategyCycleRunner
from app.shared.protocols.i_trade_executor import ITradeExecutor
from app.shared.protocols.i_trading_decision_logger import ITradingDecisionLogger

__all__ = [
    "IAlertProcessor",
    "IBrokerAdapter",
    "IDataFeed",
    "IKillSwitchMonitor",
    "IPostTradeAnalyzer",
    "IPreTradeValidator",
    "ISpainTaxEngine",
    "IStrategyCycleRunner",
    "ITradeExecutor",
    "ITradingDecisionLogger",
]
