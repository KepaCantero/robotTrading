"""
Asset Class Definitions and Configuration.

This module defines the asset class types, their characteristics, and the data structures
used to represent and analyze different asset classes in a multi-asset portfolio.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


def _get_asset_config(attr_name: str, default_value: float) -> float:
    """
    Get asset class configuration value with fallback default.

    Args:
        attr_name: Config attribute name
        default_value: Default value if config attribute not found

    Returns:
        Float value from config or default
    """
    try:
        config = get_config()
        return float(getattr(config.trading, attr_name, default_value))
    except (AttributeError, ValueError, TypeError) as e:
        logger.debug(
            "Config attribute not found, using default",
            extra={"attr_name": attr_name, "default_value": default_value, "error": str(e)},
        )
        return default_value


# Risk-free rate default - now loaded from config (for backward compatibility reference)
# Use config.trading.portfolio_risk_free_rate instead


class RebalanceFrequency(str, Enum):
    """Rebalancing frequency options."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUALLY = "semi_annually"
    ANNUALLY = "annually"


class AssetClassType(str, Enum):
    """
    Asset class types supported in the multi-asset portfolio system.

    Each asset class has distinct characteristics:
    - EQUITY: Stocks, ETFs, ownership in companies
    - FIXED_INCOME: Bonds, treasuries, debt instruments
    - CRYPTO: Cryptocurrencies, digital assets
    - FOREX: Currency pairs, foreign exchange
    - COMMODITY: Physical goods (gold, oil, agriculture)
    - REAL_ESTATE: Property, REITs
    - CASH: Cash equivalents, money market
    """

    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"
    REAL_ESTATE = "real_estate"
    CASH = "cash"

    @classmethod
    def get_trading_hours(cls, asset_type: str) -> Dict[str, str]:
        """
        Get typical trading hours for an asset class.

        Args:
            asset_type: Asset class type

        Returns:
            Dictionary with 'open' and 'close' times in UTC
        """
        hours_map = {
            cls.EQUITY: {"open": "14:30", "close": "21:00"},  # NYSE hours in UTC
            cls.CRYPTO: {"open": "00:00", "close": "23:59"},  # 24/7
            cls.FOREX: {"open": "00:00", "close": "23:59"},  # 24/5
            cls.FIXED_INCOME: {"open": "13:00", "close": "20:00"},  # Bond hours
            cls.COMMODITY: {"open": "14:00", "close": "21:00"},  # CME hours
            cls.REAL_ESTATE: {"open": "14:30", "close": "21:00"},  # REITs trade like stocks
            cls.CASH: {"open": "00:00", "close": "23:59"},  # Always available
        }
        return hours_map.get(asset_type, {"open": "00:00", "close": "23:59"})  # type: ignore

    @classmethod
    def get_settlement_period(cls, asset_type: str) -> timedelta:
        """
        Get typical settlement period for an asset class.

        Args:
            asset_type: Asset class type

        Returns:
            Settlement period as timedelta
        """
        settlement_map = {
            cls.EQUITY: timedelta(days=2),  # T+2
            cls.CRYPTO: timedelta(seconds=0),  # Instant
            cls.FOREX: timedelta(days=2),  # T+2
            cls.FIXED_INCOME: timedelta(days=1),  # T+1
            cls.COMMODITY: timedelta(days=1),  # T+1
            cls.REAL_ESTATE: timedelta(days=2),  # T+2 like equities
            cls.CASH: timedelta(seconds=0),  # Instant
        }
        return settlement_map.get(asset_type, timedelta(days=2))  # type: ignore

    @classmethod
    def get_typical_volatility(cls, asset_type: str) -> Tuple[Decimal, Decimal]:
        """
        Get typical volatility range for an asset class.

        Args:
            asset_type: Asset class type

        Returns:
            Tuple of (min_volatility, max_volatility) as annualized decimals
        """
        asset_type_lower = asset_type.lower() if isinstance(asset_type, str) else str(asset_type)

        # Get volatility ranges from config with fallback defaults
        if "equity" in asset_type_lower:
            vol_min = _get_asset_config("asset_class_equity_vol_min", 0.10)
            vol_max = _get_asset_config("asset_class_equity_vol_max", 0.30)
        elif "crypto" in asset_type_lower:
            vol_min = _get_asset_config("asset_class_crypto_vol_min", 0.40)
            vol_max = _get_asset_config("asset_class_crypto_vol_max", 1.20)
        elif "forex" in asset_type_lower:
            vol_min = _get_asset_config("asset_class_forex_vol_min", 0.05)
            vol_max = _get_asset_config("asset_class_forex_vol_max", 0.15)
        elif "fixed_income" in asset_type_lower or "fixedincome" in asset_type_lower:
            vol_min = _get_asset_config("asset_class_fixed_income_vol_min", 0.02)
            vol_max = _get_asset_config("asset_class_fixed_income_vol_max", 0.10)
        elif "commodity" in asset_type_lower:
            vol_min = _get_asset_config("asset_class_commodity_vol_min", 0.15)
            vol_max = _get_asset_config("asset_class_commodity_vol_max", 0.40)
        elif "real_estate" in asset_type_lower or "realestate" in asset_type_lower:
            vol_min = _get_asset_config("asset_class_real_estate_vol_min", 0.10)
            vol_max = _get_asset_config("asset_class_real_estate_vol_max", 0.25)
        elif "cash" in asset_type_lower:
            vol_min = _get_asset_config("asset_class_cash_vol_min", 0.00)
            vol_max = _get_asset_config("asset_class_cash_vol_max", 0.02)
        else:
            # Default fallback
            vol_min = _get_asset_config("asset_class_default_vol_min", 0.05)
            vol_max = _get_asset_config("asset_class_default_vol_max", 0.20)

        return (Decimal(str(vol_min)), Decimal(str(vol_max)))

    @classmethod
    def get_typical_return(cls, asset_type: str) -> Tuple[Decimal, Decimal]:
        """
        Get typical expected return range for an asset class.

        Args:
            asset_type: Asset class type

        Returns:
            Tuple of (min_return, max_return) as annualized decimals
        """
        asset_type_lower = asset_type.lower() if isinstance(asset_type, str) else str(asset_type)

        # Get return ranges from config with fallback defaults
        if "equity" in asset_type_lower:
            ret_min = _get_asset_config("asset_class_equity_return_min", 0.05)
            ret_max = _get_asset_config("asset_class_equity_return_max", 0.12)
        elif "crypto" in asset_type_lower:
            ret_min = _get_asset_config("asset_class_crypto_return_min", -0.20)
            ret_max = _get_asset_config("asset_class_crypto_return_max", 0.50)
        elif "forex" in asset_type_lower:
            ret_min = _get_asset_config("asset_class_forex_return_min", -0.05)
            ret_max = _get_asset_config("asset_class_forex_return_max", 0.10)
        elif "fixed_income" in asset_type_lower or "fixedincome" in asset_type_lower:
            ret_min = _get_asset_config("asset_class_fixed_income_return_min", 0.01)
            ret_max = _get_asset_config("asset_class_fixed_income_return_max", 0.06)
        elif "commodity" in asset_type_lower:
            ret_min = _get_asset_config("asset_class_commodity_return_min", -0.10)
            ret_max = _get_asset_config("asset_class_commodity_return_max", 0.20)
        elif "real_estate" in asset_type_lower or "realestate" in asset_type_lower:
            ret_min = _get_asset_config("asset_class_real_estate_return_min", 0.03)
            ret_max = _get_asset_config("asset_class_real_estate_return_max", 0.10)
        elif "cash" in asset_type_lower:
            ret_min = _get_asset_config("asset_class_cash_return_min", 0.00)
            ret_max = _get_asset_config("asset_class_cash_return_max", 0.03)
        else:
            # Default fallback
            ret_min = _get_asset_config("asset_class_default_return_min", 0.00)
            ret_max = _get_asset_config("asset_class_default_return_max", 0.10)

        return (Decimal(str(ret_min)), Decimal(str(ret_max)))


@dataclass
class AssetClassReturns:
    """
    Historical returns data for an asset class.

    Attributes:
        asset_class_type: Type of asset class
        returns: Series of historical returns
        start_date: Start date of returns data
        end_date: End date of returns data
        frequency: Data frequency (daily, weekly, monthly)
    """

    asset_class_type: AssetClassType
    returns: pd.Series
    start_date: datetime
    end_date: datetime
    frequency: str = "daily"

    def __post_init__(self):
        """Validate returns data after initialization."""
        if self.returns.empty:
            raise ValueError("Returns data cannot be empty")

        if not isinstance(self.returns.index, pd.DatetimeIndex):
            raise ValueError("Returns index must be a DatetimeIndex")

        if self.returns.isnull().any():
            raise ValueError("Returns data contains NaN values")

    @property
    def n_observations(self) -> int:
        """Number of return observations."""
        return len(self.returns)

    @property
    def annualized_return(self) -> Decimal:
        """Calculate annualized mean return."""
        mean_return = self.returns.mean()

        # Adjust for frequency
        periods_per_year = {"daily": 252, "weekly": 52, "monthly": 12}
        n_periods = periods_per_year.get(self.frequency, 252)

        annualized = (1 + mean_return) ** n_periods - 1
        return Decimal(str(annualized))

    @property
    def annualized_volatility(self) -> Decimal:
        """Calculate annualized volatility."""
        vol = self.returns.std()

        # Adjust for frequency
        periods_per_year = {"daily": 252, "weekly": 52, "monthly": 12}
        n_periods = periods_per_year.get(self.frequency, 252)

        annualized = vol * np.sqrt(n_periods)
        return Decimal(str(annualized))

    def sharpe_ratio(self, risk_free_rate: Optional[float] = None) -> float:
        """
        Calculate Sharpe ratio.

        Args:
            risk_free_rate: Risk-free rate for Sharpe ratio calculation.
                If None, uses config value or default.

        Returns:
            Sharpe ratio value
        """
        if risk_free_rate is None:
            risk_free_rate = _get_asset_config("portfolio_risk_free_rate", 0.02)

        excess_return = self.annualized_return - Decimal(str(risk_free_rate))
        vol = self.annualized_volatility

        if vol == 0:
            return 0.0

        return float(excess_return / vol)

    @property
    def skewness(self) -> float:
        """Calculate return skewness."""
        return float(self.returns.skew())

    @property
    def kurtosis(self) -> float:
        """Calculate return kurtosis."""
        return float(self.returns.kurtosis())

    def get_percentile_return(self, percentile: float) -> Decimal:
        """
        Get return at a given percentile.

        Args:
            percentile: Percentile to compute (0-100)

        Returns:
            Return at the specified percentile
        """
        return_val = self.returns.quantile(percentile / 100)
        return Decimal(str(return_val))

    def get_var(self, confidence: float = 0.95) -> Decimal:
        """
        Calculate Value at Risk (VaR).

        Args:
            confidence: Confidence level (e.g., 0.95 for 95% VaR)

        Returns:
            VaR at the specified confidence level
        """
        percentile = (1 - confidence) * 100
        return self.get_percentile_return(percentile)

    def get_cvar(self, confidence: float = 0.95) -> Decimal:
        """
        Calculate Conditional VaR (Expected Shortfall).

        Args:
            confidence: Confidence level

        Returns:
            CVaR at the specified confidence level
        """
        var = float(self.get_var(confidence))
        tail_returns = self.returns[self.returns <= var]
        cvar = tail_returns.mean()
        return Decimal(str(cvar))


@dataclass
class AssetClassMetrics:
    """
    Risk and return metrics for an asset class.

    Attributes:
        expected_return: Expected annual return
        volatility: Annualized volatility
        sharpe_ratio: Sharpe ratio
        sortino_ratio: Sortino ratio
        max_drawdown: Maximum historical drawdown
        var_95: Value at Risk at 95% confidence
        cvar_95: Conditional VaR at 95%
        beta: Beta relative to market
        correlation_to_equities: Correlation to equities
        correlation_to_bonds: Correlation to bonds
        skewness: Return distribution skewness
        kurtosis: Return distribution kurtosis
    """

    expected_return: Decimal
    volatility: Decimal
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    var_95: Optional[Decimal] = None
    cvar_95: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    correlation_to_equities: Optional[Decimal] = None
    correlation_to_bonds: Optional[Decimal] = None
    skewness: Optional[Decimal] = None
    kurtosis: Optional[Decimal] = None

    def validate(self) -> bool:
        """
        Validate metrics are reasonable.

        Returns:
            True if metrics are valid

        Raises:
            ValueError: If metrics are invalid
        """
        if self.volatility < 0:
            raise ValueError(f"Volatility must be non-negative, got {self.volatility}")

        max_vol = _get_asset_config("asset_class_max_volatility", 2.0)
        if self.volatility > Decimal(str(max_vol)):
            raise ValueError(
                f"Volatility exceeds reasonable maximum ({max_vol}), got {self.volatility}"
            )

        min_return = _get_asset_config("asset_class_min_expected_return", -1.0)
        if self.expected_return < Decimal(str(min_return)):
            raise ValueError(
                f"Expected return cannot be less than {min_return*100}%, got {self.expected_return}"
            )

        max_return = _get_asset_config("asset_class_max_expected_return", 2.0)
        if self.expected_return > Decimal(str(max_return)):
            raise ValueError(
                f"Expected return exceeds reasonable maximum ({max_return}), got {self.expected_return}"
            )

        return True

    @property
    def risk_return_ratio(self) -> Decimal:
        """Calculate return per unit of risk (return/volatility)."""
        if self.volatility == 0:
            return Decimal("0")
        return self.expected_return / self.volatility

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "expected_return": float(self.expected_return),
            "volatility": float(self.volatility),
            "sharpe_ratio": float(self.sharpe_ratio) if self.sharpe_ratio else None,
            "sortino_ratio": float(self.sortino_ratio) if self.sortino_ratio else None,
            "max_drawdown": float(self.max_drawdown) if self.max_drawdown else None,
            "var_95": float(self.var_95) if self.var_95 else None,
            "cvar_95": float(self.cvar_95) if self.cvar_95 else None,
            "beta": float(self.beta) if self.beta else None,
            "correlation_to_equities": (
                float(self.correlation_to_equities) if self.correlation_to_equities else None
            ),
            "correlation_to_bonds": (
                float(self.correlation_to_bonds) if self.correlation_to_bonds else None
            ),
            "skewness": float(self.skewness) if self.skewness else None,
            "kurtosis": float(self.kurtosis) if self.kurtosis else None,
        }


class AssetClassConfig(BaseModel):
    """
    Configuration for a single asset class.

    This defines the constraints and characteristics of an asset class
    in the multi-asset portfolio.

    Attributes:
        name: Unique name for this asset class
        type: Asset class type
        expected_return: Expected annual return
        volatility: Expected annual volatility
        min_weight: Minimum allocation weight
        max_weight: Maximum allocation weight
        rebalance_frequency: How often to rebalance this class
        symbols: List of symbols in this asset class (optional)
        max_positions: Maximum number of positions within this class
        correlation_matrix: Correlation matrix with other asset classes
        metadata: Additional metadata
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        str_strip_whitespace=True,
        use_enum_values=True,
    )

    name: str = Field(..., description="Unique name for this asset class")
    type: AssetClassType = Field(..., description="Asset class type")
    expected_return: Decimal = Field(
        ..., ge=Decimal("-1"), le=Decimal("2"), description="Expected annual return"
    )
    volatility: Decimal = Field(
        ..., ge=Decimal("0"), le=Decimal("2"), description="Expected annual volatility"
    )
    min_weight: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Minimum allocation weight",
    )
    max_weight: Decimal = Field(
        default=Decimal("1"),
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Maximum allocation weight",
    )
    rebalance_frequency: RebalanceFrequency = Field(
        default=RebalanceFrequency.MONTHLY, description="Rebalancing frequency"
    )
    symbols: Optional[List[str]] = Field(default=None, description="List of symbols in this class")
    max_positions: int = Field(
        default=50, ge=1, le=500, description="Maximum positions within class"
    )
    correlation_matrix: Optional[Dict[str, float]] = Field(
        default=None, description="Correlations with other asset classes"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    enabled: bool = Field(default=True, description="Whether this asset class is enabled")

    @field_validator("max_weight")
    @classmethod
    def validate_max_weight(cls, v: Decimal, info) -> Decimal:
        """Validate max_weight is >= min_weight."""
        if "min_weight" in info.data and v < info.data["min_weight"]:
            raise ValueError(f"max_weight ({v}) must be >= min_weight ({info.data['min_weight']})")
        return v

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate symbols list."""
        if v is not None:
            if len(v) == 0:
                raise ValueError("Symbols list cannot be empty if provided")

            # Check for duplicates
            if len(set(v)) != len(v):
                raise ValueError("Symbols list contains duplicates")

            # Check symbol formats
            for symbol in v:
                if not symbol or len(symbol.strip()) == 0:
                    raise ValueError("Symbol cannot be empty")

        return v

    @field_validator("correlation_matrix")
    @classmethod
    def validate_correlations(cls, v: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        """Validate correlation values are in valid range."""
        if v is not None:
            for key, corr in v.items():
                if not -1 <= corr <= 1:
                    raise ValueError(f"Correlation with {key} must be between -1 and 1, got {corr}")
        return v


@dataclass
class AssetClass:
    """
    Asset class definition for multi-asset portfolio.

    This class represents an asset class with its characteristics,
    constraints, and historical data for portfolio optimization.

    Attributes:
        name: Unique name/identifier
        type: Asset class type
        expected_return: Expected annual return
        volatility: Expected annual volatility
        min_weight: Minimum portfolio weight
        max_weight: Maximum portfolio weight
        rebalance_frequency: How often to rebalance
        correlation_matrix: Correlation matrix with other classes
        symbols: Available symbols in this class
        metrics: Historical metrics
        config: Configuration object
        enabled: Whether this class is available for allocation
    """

    name: str
    type: AssetClassType
    expected_return: Decimal
    volatility: Decimal
    min_weight: Decimal = Decimal("0")
    max_weight: Decimal = Decimal("1")
    rebalance_frequency: str = "monthly"
    correlation_matrix: Optional[pd.DataFrame] = None
    symbols: Optional[List[str]] = None
    metrics: Optional[AssetClassMetrics] = None
    config: Optional[AssetClassConfig] = None
    enabled: bool = True
    max_positions: int = 50
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate asset class after initialization."""
        # Convert types if needed
        if isinstance(self.expected_return, (int, float)):
            self.expected_return = Decimal(str(self.expected_return))
        if isinstance(self.volatility, (int, float)):
            self.volatility = Decimal(str(self.volatility))
        if isinstance(self.min_weight, (int, float)):
            self.min_weight = Decimal(str(self.min_weight))
        if isinstance(self.max_weight, (int, float)):
            self.max_weight = Decimal(str(self.max_weight))

        # Validate
        self.validate()

    def validate(self) -> bool:
        """
        Validate asset class configuration.

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        logger.debug("Validating asset class", extra={"name": self.name, "type": self.type.value})
        # Check name
        if not self.name or len(self.name.strip()) == 0:
            raise ValueError("Asset class name cannot be empty")

        # Check weights
        if self.min_weight < 0 or self.min_weight > 1:
            raise ValueError(f"min_weight must be between 0 and 1, got {self.min_weight}")

        if self.max_weight < 0 or self.max_weight > 1:
            raise ValueError(f"max_weight must be between 0 and 1, got {self.max_weight}")

        if self.min_weight > self.max_weight:
            raise ValueError(
                f"min_weight ({self.min_weight}) cannot exceed max_weight ({self.max_weight})"
            )

        # Check volatility
        if self.volatility < 0:
            raise ValueError(f"Volatility must be non-negative, got {self.volatility}")

        max_vol = _get_asset_config("asset_class_max_volatility", 2.0)
        if self.volatility > Decimal(str(max_vol)):
            raise ValueError(
                f"Volatility exceeds reasonable maximum ({max_vol}), got {self.volatility}"
            )

        # Check expected return
        min_return = _get_asset_config("asset_class_min_expected_return", -1.0)
        if self.expected_return < Decimal(str(min_return)):
            raise ValueError(
                f"Expected return cannot be less than {min_return*100}%, got {self.expected_return}"
            )

        # Validate rebalance frequency
        valid_frequencies = ["daily", "weekly", "monthly", "quarterly", "semi_annually", "annually"]
        if self.rebalance_frequency not in valid_frequencies:
            raise ValueError(
                f"Invalid rebalance frequency: {self.rebalance_frequency}. "
                f"Must be one of {valid_frequencies}"
            )

        # Validate metrics if provided
        if self.metrics:
            self.metrics.validate()

        logger.debug("Asset class validation passed", extra={"name": self.name})
        return True

    @property
    def risk_return_ratio(self) -> Decimal:
        """Calculate return per unit of risk."""
        if self.volatility == 0:
            return Decimal("0")
        return self.expected_return / self.volatility

    def calculate_sharpe_ratio(self, risk_free_rate: Optional[float] = None) -> float:
        """
        Calculate Sharpe ratio.

        Args:
            risk_free_rate: Risk-free rate for Sharpe ratio calculation.
                If None, uses config value or default.

        Returns:
            Sharpe ratio value
        """
        if risk_free_rate is None:
            risk_free_rate = _get_asset_config("portfolio_risk_free_rate", 0.02)

        logger.debug(
            "Calculating Sharpe ratio",
            extra={
                "name": self.name,
                "expected_return": float(self.expected_return),
                "volatility": float(self.volatility),
                "risk_free_rate": risk_free_rate,
            },
        )

        rf = Decimal(str(risk_free_rate))
        if self.volatility == 0:
            return 0.0
        return float((self.expected_return - rf) / self.volatility)

    @property
    def sharpe_ratio(self) -> float:
        """
        Calculate Sharpe ratio with default risk-free rate.

        Returns:
            Sharpe ratio using config-based risk-free rate
        """
        return self.calculate_sharpe_ratio()

    def to_config(self) -> AssetClassConfig:
        """Convert to AssetClassConfig object."""
        correlation_dict = None
        if self.correlation_matrix is not None:
            correlation_dict = {
                col: float(self.correlation_matrix.loc[row, col])
                for col in self.correlation_matrix.columns
                for row in self.correlation_matrix.index
                if row != col
            }

        return AssetClassConfig(
            name=self.name,
            type=self.type,
            expected_return=self.expected_return,
            volatility=self.volatility,
            min_weight=self.min_weight,
            max_weight=self.max_weight,
            rebalance_frequency=RebalanceFrequency(self.rebalance_frequency),
            symbols=self.symbols,
            max_positions=self.max_positions,
            correlation_matrix=correlation_dict,
            metadata=self.metadata,
            enabled=self.enabled,
        )

    @classmethod
    def from_config(cls, config: AssetClassConfig) -> AssetClass:
        """
        Create AssetClass from AssetClassConfig.

        Args:
            config: AssetClassConfig object

        Returns:
            AssetClass instance
        """
        # Handle rebalance_frequency - it might be string or enum
        if isinstance(config.rebalance_frequency, str):
            rebalance_freq = config.rebalance_frequency
        else:
            rebalance_freq = config.rebalance_frequency.value

        return cls(
            name=config.name,
            type=config.type,
            expected_return=config.expected_return,
            volatility=config.volatility,
            min_weight=config.min_weight,
            max_weight=config.max_weight,
            rebalance_frequency=rebalance_freq,
            symbols=config.symbols,
            max_positions=config.max_positions,
            metadata=config.metadata,
            enabled=config.enabled,
        )

    def get_correlation_with(self, other_name: str) -> Optional[float]:
        """
        Get correlation with another asset class.

        Args:
            other_name: Name of other asset class

        Returns:
            Correlation value or None if not available
        """
        if self.correlation_matrix is None:
            return None

        if other_name not in self.correlation_matrix.index:
            return None

        if self.name not in self.correlation_matrix.columns:
            return None

        return float(self.correlation_matrix.loc[other_name, self.name])

    def is_within_weight_bounds(self, weight: Decimal) -> bool:
        """
        Check if a weight is within bounds for this asset class.

        Args:
            weight: Weight to check

        Returns:
            True if weight is within bounds
        """
        return self.min_weight <= weight <= self.max_weight

    def calculate_position_size(self, portfolio_value: Decimal, target_weight: Decimal) -> Decimal:
        """
        Calculate position size for this asset class.

        Args:
            portfolio_value: Total portfolio value
            target_weight: Target weight for this asset class

        Returns:
            Position size in currency units
        """
        # Ensure weight is within bounds
        weight = max(self.min_weight, min(self.max_weight, target_weight))
        return portfolio_value * weight

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "type": self.type.value,
            "expected_return": float(self.expected_return),
            "volatility": float(self.volatility),
            "min_weight": float(self.min_weight),
            "max_weight": float(self.max_weight),
            "rebalance_frequency": self.rebalance_frequency,
            "symbols": self.symbols,
            "max_positions": self.max_positions,
            "enabled": self.enabled,
            "sharpe_ratio": self.sharpe_ratio,
            "risk_return_ratio": float(self.risk_return_ratio),
            "metadata": self.metadata,
        }
