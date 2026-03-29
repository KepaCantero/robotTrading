"""
Broker Failover Manager - Manage multiple broker connections with failover.

This package provides automatic failover capabilities for multi-broker trading systems.
It monitors broker health and automatically switches to backup brokers when the primary fails.

Features:
- Automatic failover to secondary broker
- Health checks every minute
- Position sync across brokers
- Configurable failover triggers
- Alert on failover

Example:
    from app.services.broker_failover import BrokerFailoverManager, BrokerConfig
    from app.services.live_trading.broker_adapters import AlpacaAdapter, PaperAdapter

    # Configure brokers
    brokers = [
        BrokerConfig(
            name="alpaca",
            broker=AlpacaAdapter(),
            priority=1,
        ),
        BrokerConfig(
            name="paper",
            broker=PaperAdapter(),
            priority=2,
        ),
    ]

    # Create manager
    async def on_failover(from_broker: str, to_broker: str):
        logger.debug(f"Failed over from {from_broker} to {to_broker}")

    manager = BrokerFailoverManager(
        brokers=brokers,
        on_failover=on_failover,
        health_check_interval=60.0,
    )

    # Start monitoring
    await manager.start()

    # Execute order with automatic failover
    result = await manager.execute_order_with_failover(
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("100"),
    )
"""

from .manager import BrokerConfig, BrokerFailoverManager, BrokerHealth, BrokerState

__all__ = [
    "BrokerConfig",
    "BrokerFailoverManager",
    "BrokerHealth",
    "BrokerState",
]
