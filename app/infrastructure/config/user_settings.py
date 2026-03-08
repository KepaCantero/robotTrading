"""
User Settings Model

Defines the user-specific configuration model.
"""
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class BrokerType(str, Enum):
    """Available broker types."""

    ALPACA = "alpaca"
    IBKR = "ibkr"
    PAPER = "paper"


class OrderTypePreference(str, Enum):
    """Default order type preferences."""

    MARKET = "market"
    LIMIT = "limit"
    STOP_LIMIT = "stop_limit"


class TradingProfile(BaseModel):
    """User's trading profile and preferences."""

    profile_name: str = Field(default="default", description="Profile name")
    risk_tolerance: str = Field(
        default="moderate",
        description="Risk tolerance level: conservative, moderate, aggressive",
    )
    max_positions: int = Field(default=5, description="Maximum concurrent positions")
    max_capital_per_trade: Decimal = Field(
        default=Decimal("0.2"), description="Max capital per trade (0-1)"
    )
    default_stop_loss_pct: Decimal = Field(
        default=Decimal("0.05"), description="Default stop loss percentage"
    )
    default_take_profit_pct: Decimal = Field(
        default=Decimal("0.15"), description="Default take profit percentage"
    )


class NotificationSettings(BaseModel):
    """User notification preferences."""

    enable_telegram: bool = Field(default=False, description="Enable Telegram alerts")
    telegram_chat_id: Optional[str] = Field(default=None, description="Telegram chat ID")
    enable_email: bool = Field(default=False, description="Enable email alerts")
    email_address: Optional[str] = Field(default=None, description="Email address")
    alert_on_entry: bool = Field(default=True, description="Alert on entry orders")
    alert_on_exit: bool = Field(default=True, description="Alert on exit orders")
    alert_on_risk: bool = Field(default=True, description="Alert on risk events")
    daily_summary: bool = Field(default=True, description="Send daily summary")


class BrokerSettings(BaseModel):
    """Broker connection settings."""

    broker_type: BrokerType = Field(default=BrokerType.PAPER, description="Primary broker")
    paper_trading: bool = Field(default=True, description="Use paper trading mode")
    alpaca_api_key: Optional[str] = Field(default=None, description="Alpaca API key")
    alpaca_api_secret: Optional[str] = Field(default=None, description="Alpaca API secret")
    alpaca_base_url: Optional[str] = Field(
        default="https://paper-api.alpaca.markets",
        description="Alpaca base URL",
    )
    ibkr_host: str = Field(default="127.0.0.1", description="IBKR gateway host")
    ibkr_port: int = Field(default=4001, description="IBKR gateway port")
    ibkr_client_id: int = Field(default=1, description="IBKR client ID")


class OrderPreferences(BaseModel):
    """User order execution preferences."""

    default_order_type: OrderTypePreference = Field(
        default=OrderTypePreference.LIMIT, description="Default order type"
    )
    limit_price_offset_pct: Decimal = Field(
        default=Decimal("0.001"), description="Limit price offset from mid (0.1%)"
    )
    allow_amex_orders: bool = Field(default=True, description="Allow AMEX orders")
    allow_arca_orders: bool = Field(default=True, description="Allow ARCA orders")
    allow_nyse_orders: bool = Field(default=True, description="Allow NYSE orders")
    allow_nasdaq_orders: bool = Field(default=True, description="Allow NASDAQ orders")
    min_order_size: int = Field(default=1, description="Minimum order size (shares)")
    max_order_size: int = Field(default=10000, description="Maximum order size (shares)")


class TradingHours(BaseModel):
    """Trading hours and session preferences."""

    auto_start_market: bool = Field(default=False, description="Auto-start at market open")
    auto_stop_market: bool = Field(default=False, description="Auto-stop at market close")
    pre_market_trading: bool = Field(default=False, description="Allow pre-market trading")
    after_hours_trading: bool = Field(default=False, description="Allow after-hours trading")
    timezone: str = Field(default="America/New_York", description="Trading timezone")


class RiskLimits(BaseModel):
    """User-specific risk limits."""

    max_daily_loss: Decimal = Field(default=Decimal("0.05"), description="Max daily loss (5%)")
    max_drawdown: Decimal = Field(default=Decimal("0.15"), description="Max drawdown (15%)")
    kill_switch_enabled: bool = Field(default=True, description="Enable kill switch")
    max_position_size: Decimal = Field(
        default=Decimal("0.2"), description="Max single position (20%)"
    )
    max_total_exposure: Decimal = Field(
        default=Decimal("0.8"), description="Max total exposure (80%)"
    )


class SymbolUniverse(BaseModel):
    """User's tradable symbol universe."""

    allowed_symbols: List[str] = Field(
        default_factory=lambda: ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
        description="Allowed trading symbols",
    )
    min_price: Decimal = Field(default=Decimal("10"), description="Min stock price")
    max_price: Decimal = Field(default=Decimal("1000"), description="Max stock price")
    min_volume: int = Field(default=100000, description="Min daily volume")
    exclude_otc: bool = Field(default=True, description="Exclude OTC stocks")


class UserSettings(BaseModel):
    """Complete user settings model."""

    # User identification
    user_id: str = Field(default="single_user", description="User identifier")
    user_name: str = Field(default="Trader", description="User display name")

    # Trading settings
    trading_profile: TradingProfile = Field(
        default_factory=TradingProfile, description="Trading profile"
    )
    broker_settings: BrokerSettings = Field(
        default_factory=BrokerSettings, description="Broker settings"
    )
    order_preferences: OrderPreferences = Field(
        default_factory=OrderPreferences, description="Order preferences"
    )
    trading_hours: TradingHours = Field(default_factory=TradingHours, description="Trading hours")
    risk_limits: RiskLimits = Field(default_factory=RiskLimits, description="Risk limits")
    symbol_universe: SymbolUniverse = Field(
        default_factory=SymbolUniverse, description="Symbol universe"
    )

    # Notifications
    notifications: NotificationSettings = Field(
        default_factory=NotificationSettings, description="Notification settings"
    )

    # System preferences
    log_level: str = Field(default="INFO", description="Logging level")
    data_retention_days: int = Field(default=30, description="Data retention days")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

    def get_allowed_symbols(self) -> List[str]:
        """Get list of allowed trading symbols."""
        return self.symbol_universe.allowed_symbols

    def is_symbol_allowed(self, symbol: str) -> bool:
        """Check if symbol is allowed for trading."""
        return symbol.upper() in self.symbol_universe.allowed_symbols

    def is_paper_trading(self) -> bool:
        """Check if running in paper trading mode."""
        return self.broker_settings.paper_trading
