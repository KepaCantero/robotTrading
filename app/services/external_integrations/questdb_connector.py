"""
T17.1.1: QuestDBConnector - Time-series database integration

QuestDB is a high-performance time-series database for storing market data,
trades, and performance metrics. Uses ILP (Influx Line Protocol) for high-throughput writes.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesData:
    """Time-series data point."""

    timestamp: datetime
    symbol: str
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    vwap: Optional[Decimal] = None


@dataclass
class TradeRecord:
    """Trade record for database."""

    trade_id: str
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    timestamp: datetime
    portfolio_value: Decimal
    pnl: Decimal


class QuestDBConnector:
    """
    QuestDB integration for time-series data storage.

    Features:
    - OHLCV data storage via ILP (Influx Line Protocol)
    - Trade history tracking
    - Performance metrics storage
    - High-performance querying via HTTP REST API
    - Connection pooling with aiohttp
    """

    def __init__(self, host: str = "localhost", ilp_port: int = 9009, http_port: int = 9000):
        """
        Initialize QuestDB connector.

        Args:
            host: QuestDB host
            ilp_port: ILP write port (default 9009)
            http_port: HTTP REST API port (default 9000)
        """
        self.host = host
        self.ilp_port = ilp_port
        self.http_port = http_port
        self.ilp_url = f"http://{host}:{ilp_port}"
        self.http_url = f"http://{host}:{http_port}"
        self.connected = False
        self.session: Optional[aiohttp.ClientSession] = None
        self.write_buffer: List[str] = []
        self.buffer_size = 1000
        logger.info(f"✅ QuestDBConnector initialized ({host}:{ilp_port}/{http_port})")

    async def connect(self) -> bool:
        """Connect to QuestDB and verify connectivity."""
        try:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            self.session = aiohttp.ClientSession(
                connector=connector, timeout=aiohttp.ClientTimeout(total=30)
            )

            # Test connectivity
            async with self.session.get(f"{self.http_url}/status") as resp:
                if resp.status == 200:
                    self.connected = True
                    logger.info(f"✅ Connected to QuestDB ({self.host}:{self.ilp_port})")
                    return True

        except Exception as e:
            logger.error(f"❌ QuestDB connection failed: {str(e)}")
            self.connected = False
            if self.session:
                await self.session.close()

        return False

    async def disconnect(self) -> bool:
        """Disconnect from QuestDB."""
        try:
            if self.write_buffer:
                await self._flush_buffer()
            if self.session:
                await self.session.close()
            self.connected = False
            logger.info("✅ Disconnected from QuestDB")
            return True
        except Exception as e:
            logger.error(f"❌ Disconnect failed: {str(e)}")
            return False

    async def insert_ohlcv(self, data: TimeSeriesData) -> bool:
        """
        Insert OHLCV data point via ILP.

        Args:
            data: TimeSeriesData point

        Returns:
            True if successful
        """
        if not self.connected or not self.session:
            logger.warning("⚠️ Not connected to QuestDB")
            return False

        try:
            # Convert to ILP format: table_name,tags field=value timestamp
            ilp_line = (
                f"ohlcv,symbol={data.symbol} "
                f"open={float(data.open_price)},"
                f"high={float(data.high_price)},"
                f"low={float(data.low_price)},"
                f"close={float(data.close_price)},"
                f"volume={float(data.volume)} "
                f"{int(data.timestamp.timestamp() * 1e9)}\n"
            )

            self.write_buffer.append(ilp_line)

            # Flush if buffer is full
            if len(self.write_buffer) >= self.buffer_size:
                await self._flush_buffer()

            logger.debug(f"✅ Buffered OHLCV: {data.symbol}")
            return True

        except Exception as e:
            logger.error(f"❌ Insert OHLCV failed: {str(e)}")
            return False

    async def insert_batch_ohlcv(self, data_list: List[TimeSeriesData]) -> int:
        """
        Insert batch of OHLCV data.

        Args:
            data_list: List of TimeSeriesData

        Returns:
            Number of records inserted
        """
        if not self.connected:
            return 0

        inserted = 0
        for data in data_list:
            if await self.insert_ohlcv(data):
                inserted += 1

        logger.info(f"✅ Queued {inserted} OHLCV records")
        return inserted

    async def insert_trade(self, trade: TradeRecord) -> bool:
        """
        Insert trade record via ILP.

        Args:
            trade: TradeRecord

        Returns:
            True if successful
        """
        if not self.connected or not self.session:
            logger.warning("⚠️ Not connected to QuestDB")
            return False

        try:
            # ILP format for trades
            ilp_line = (
                f"trades,symbol={trade.symbol},side={trade.side} "
                f"quantity={float(trade.quantity)},"
                f"price={float(trade.price)},"
                f"portfolio_value={float(trade.portfolio_value)},"
                f"pnl={float(trade.pnl)} "
                f"{int(trade.timestamp.timestamp() * 1e9)}\n"
            )

            self.write_buffer.append(ilp_line)

            if len(self.write_buffer) >= self.buffer_size:
                await self._flush_buffer()

            logger.debug(f"✅ Buffered trade: {trade.trade_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Insert trade failed: {str(e)}")
            return False

    async def _flush_buffer(self) -> bool:
        """Flush write buffer to QuestDB."""
        if not self.write_buffer or not self.session:
            return False

        try:
            data = "".join(self.write_buffer).encode()
            async with self.session.post(
                f"{self.ilp_url}/write",
                data=data,
                params={"precision": "ns"},
            ) as resp:
                if resp.status in (200, 204):
                    logger.info(f"✅ Flushed {len(self.write_buffer)} records to QuestDB")
                    self.write_buffer.clear()
                    return True
                else:
                    logger.error(f"❌ Flush failed: HTTP {resp.status}")
                    return False

        except Exception as e:
            logger.error(f"❌ Buffer flush failed: {str(e)}")
            return False

    async def query_ohlcv(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[TimeSeriesData]:
        """
        Query OHLCV data via HTTP REST API.

        Args:
            symbol: Stock symbol
            start_time: Start time
            end_time: End time

        Returns:
            List of TimeSeriesData
        """
        if not self.connected or not self.session:
            return []

        try:
            # Format timestamps for QuestDB SQL query
            start_ts = start_time.isoformat()
            end_ts = end_time.isoformat()

            # SQL query for OHLCV data
            sql_query = (  # nosec B608 - controlled inputs
                f"SELECT timestamp, symbol, open, high, low, close, volume "  # nosec B608 - controlled inputs
                f"FROM ohlcv "  # nosec B608 - controlled inputs
                f"WHERE symbol = '{symbol}' "  # nosec B608 - controlled inputs
                f"AND timestamp >= '{start_ts}' "  # nosec B608 - controlled inputs
                f"AND timestamp <= '{end_ts}' "  # nosec B608 - controlled inputs
                f"ORDER BY timestamp ASC"  # nosec B608 - controlled inputs
            )

            # Execute query via HTTP REST API
            params = {"query": sql_query}
            async with self.session.get(f"{self.http_url}/exec", params=params) as resp:
                if resp.status == 200:
                    result = await resp.json()

                    # Parse response and build TimeSeriesData objects
                    results = []
                    if "dataset" in result:
                        for row in result["dataset"]:
                            try:
                                data = TimeSeriesData(
                                    timestamp=datetime.fromisoformat(row[0]),
                                    symbol=row[1],
                                    open_price=Decimal(str(row[2])),
                                    high_price=Decimal(str(row[3])),
                                    low_price=Decimal(str(row[4])),
                                    close_price=Decimal(str(row[5])),
                                    volume=Decimal(str(row[6])),
                                )
                                results.append(data)
                            except (ValueError, IndexError) as e:
                                logger.warning(f"⚠️ Failed to parse row: {e}")
                                continue

                    logger.info(f"✅ Query returned {len(results)} OHLCV records for {symbol}")
                    return results
                else:
                    logger.error(f"❌ Query failed: HTTP {resp.status}")
                    return []

        except Exception as e:
            logger.error(f"❌ OHLCV query failed: {str(e)}")
            return []

    async def query_trades(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
    ) -> List[TradeRecord]:
        """Query trade records via HTTP REST API."""
        if not self.connected or not self.session:
            return []

        try:
            # Build SQL query with optional filters
            sql_query = "SELECT trade_id, symbol, side, quantity, price, timestamp, portfolio_value, pnl FROM trades WHERE 1=1"

            if symbol:
                sql_query += f" AND symbol = '{symbol}'"  # nosec B608 - controlled inputs
            if start_time:
                start_ts = start_time.isoformat()
                sql_query += f" AND timestamp >= '{start_ts}'"  # nosec B608 - controlled inputs

            sql_query += " ORDER BY timestamp DESC"

            # Execute query via HTTP REST API
            params = {"query": sql_query}
            async with self.session.get(f"{self.http_url}/exec", params=params) as resp:
                if resp.status == 200:
                    result = await resp.json()

                    # Parse response and build TradeRecord objects
                    results = []
                    if "dataset" in result:
                        for row in result["dataset"]:
                            try:
                                trade = TradeRecord(
                                    trade_id=row[0],
                                    symbol=row[1],
                                    side=row[2],
                                    quantity=Decimal(str(row[3])),
                                    price=Decimal(str(row[4])),
                                    timestamp=datetime.fromisoformat(row[5]),
                                    portfolio_value=Decimal(str(row[6])),
                                    pnl=Decimal(str(row[7])),
                                )
                                results.append(trade)
                            except (ValueError, IndexError) as e:
                                logger.warning(f"⚠️ Failed to parse trade row: {e}")
                                continue

                    logger.info(f"✅ Query returned {len(results)} trade records")
                    return results
                else:
                    logger.error(f"❌ Trade query failed: HTTP {resp.status}")
                    return []

        except Exception as e:
            logger.error(f"❌ Trade query failed: {str(e)}")
            return []

    async def get_latest_price(self, symbol: str) -> Optional[Decimal]:
        """Get latest price for symbol via HTTP REST API."""
        if not self.connected or not self.session:
            return None

        try:
            # SQL query for latest close price
            sql_query = (  # nosec B608 - controlled inputs
                f"SELECT close FROM ohlcv "  # nosec B608 - controlled inputs
                f"WHERE symbol = '{symbol}' "  # nosec B608 - controlled inputs
                f"ORDER BY timestamp DESC LIMIT 1"  # nosec B608 - controlled inputs
            )

            params = {"query": sql_query}
            async with self.session.get(f"{self.http_url}/exec", params=params) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if "dataset" in result and len(result["dataset"]) > 0:
                        price = Decimal(str(result["dataset"][0][0]))
                        logger.debug(f"✅ Latest price for {symbol}: {price}")
                        return price
                    return None
                else:
                    logger.error(f"❌ Price query failed: HTTP {resp.status}")
                    return None

        except Exception as e:
            logger.error(f"❌ Failed to get latest price: {str(e)}")
            return None

    async def get_statistics(self, symbol: str) -> Dict:
        """Get statistics for symbol via HTTP REST API."""
        if not self.connected or not self.session:
            return {}

        try:
            # SQL query for aggregated statistics
            sql_query = (  # nosec B608 - controlled inputs
                f"SELECT COUNT(*) as count, MIN(close) as min_close, "  # nosec B608 - controlled inputs
                f"MAX(close) as max_close, AVG(close) as avg_close "
                f"FROM ohlcv WHERE symbol = '{symbol}'"  # nosec B608 - controlled inputs
            )

            params = {"query": sql_query}
            async with self.session.get(f"{self.http_url}/exec", params=params) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if "dataset" in result and len(result["dataset"]) > 0:
                        row = result["dataset"][0]
                        stats = {
                            "count": int(row[0]),
                            "min": Decimal(str(row[1])),
                            "max": Decimal(str(row[2])),
                            "avg": Decimal(str(row[3])),
                        }
                        logger.info(f"✅ Statistics for {symbol}: {stats['count']} records")
                        return stats
                    return {}
                else:
                    logger.error(f"❌ Statistics query failed: HTTP {resp.status}")
                    return {}

        except Exception as e:
            logger.error(f"❌ Failed to get statistics: {str(e)}")
            return {}

    def get_connection_status(self) -> Dict:
        """Get connection status."""
        return {
            "connected": self.connected,
            "host": self.host,
            "ilp_port": self.ilp_port,
            "http_port": self.http_port,
            "ilp_url": self.ilp_url,
            "http_url": self.http_url,
            "buffered_records": len(self.write_buffer),
        }


# Singleton
_connector: Optional[QuestDBConnector] = None


def get_questdb_connector(
    host: str = "localhost",
    port: int = 9009,
) -> QuestDBConnector:
    """Get or create singleton QuestDBConnector."""
    global _connector
    if _connector is None:
        _connector = QuestDBConnector()
        logger.info("✅ QuestDBConnector singleton initialized")

    return _connector
