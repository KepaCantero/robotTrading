"""
BacktestConfig Value Object - Configuration for backtesting operations

This value object encapsulates all configuration parameters for a backtest.
It's immutable and validates all parameters upon creation.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from .backtest_type import BacktestType


@dataclass(frozen=True)
class BacktestConfigValue:
    """
    Backtest configuration value object.

    All configuration parameters are validated and immutable.
    """

    # Strategy configuration
    strategy_name: str
    strategy_params: dict[str, Any] = field(default_factory=dict)

    # Data configuration
    symbols: list[str] = field(default_factory=list)
    start_date: datetime = None
    end_date: datetime = None
    initial_capital: Decimal = Decimal("100000")

    # Backtest type
    backtest_type: BacktestType = BacktestType.BASELINE

    # Risk parameters
    max_position_size: Decimal = Decimal("0.10")
    stop_loss: Decimal = Decimal("0.03")
    take_profit: Decimal = Decimal("0.06")

    # Execution parameters
    commission: Decimal = Decimal("0.001")
    slippage: Decimal = Decimal("0.0001")

    # Output configuration
    output_dir: Path | None = None
    save_results: bool = True

    # Advanced parameters
    enable_regime_detection: bool = False
    enable_meta_learning: bool = False
    parallel_workers: int | None = None

    def __post_init__(self):
        """Validate configuration invariants."""
        if not self.strategy_name:
            raise ValueError("Strategy name cannot be empty")

        if self.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")

        if self.max_position_size <= 0 or self.max_position_size > 1:
            raise ValueError("Max position size must be between 0 and 1")

        if self.stop_loss <= 0 or self.stop_loss > 1:
            raise ValueError("Stop loss must be between 0 and 1")

        if self.take_profit <= 0 or self.take_profit > 1:
            raise ValueError("Take profit must be between 0 and 1")

        if self.commission < 0:
            raise ValueError("Commission cannot be negative")

        if self.slippage < 0:
            raise ValueError("Slippage cannot be negative")

        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValueError("Start date must be before end date")

        if self.parallel_workers is not None and self.parallel_workers <= 0:
            raise ValueError("Parallel workers must be positive")

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> BacktestConfigValue:
        """
        Create configuration from dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            BacktestConfigValue instance
        """
        # Parse dates
        start_date = None
        end_date = None
        if "start_date" in config_dict:
            start_date = datetime.fromisoformat(config_dict["start_date"])
        if "end_date" in config_dict:
            end_date = datetime.fromisoformat(config_dict["end_date"])

        # Parse backtest type
        backtest_type = BacktestType.BASELINE
        if "backtest_type" in config_dict:
            with contextlib.suppress(ValueError):
                backtest_type = BacktestType(config_dict["backtest_type"])

        # Parse output directory
        output_dir = None
        if "output_directory" in config_dict:
            output_dir = Path(config_dict["output_directory"])

        return cls(
            strategy_name=config_dict.get("strategy_name", ""),
            strategy_params=config_dict.get("strategy_params", {}),
            symbols=config_dict.get("symbols", []),
            start_date=start_date,
            end_date=end_date,
            initial_capital=Decimal(str(config_dict.get("initial_capital", "100000"))),
            backtest_type=backtest_type,
            max_position_size=Decimal(str(config_dict.get("max_position_size", "0.10"))),
            stop_loss=Decimal(str(config_dict.get("stop_loss", "0.03"))),
            take_profit=Decimal(str(config_dict.get("take_profit", "0.06"))),
            commission=Decimal(str(config_dict.get("commission", "0.001"))),
            slippage=Decimal(str(config_dict.get("slippage", "0.0001"))),
            output_dir=output_dir,
            save_results=config_dict.get("save_results", True),
            enable_regime_detection=config_dict.get("enable_regime_detection", False),
            enable_meta_learning=config_dict.get("enable_meta_learning", False),
            parallel_workers=config_dict.get("parallel_workers"),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Configuration dictionary
        """
        return {
            "strategy_name": self.strategy_name,
            "strategy_params": self.strategy_params,
            "symbols": self.symbols,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "initial_capital": str(self.initial_capital),
            "backtest_type": self.backtest_type.value,
            "max_position_size": str(self.max_position_size),
            "stop_loss": str(self.stop_loss),
            "take_profit": str(self.take_profit),
            "commission": str(self.commission),
            "slippage": str(self.slippage),
            "output_directory": str(self.output_dir) if self.output_dir else None,
            "save_results": self.save_results,
            "enable_regime_detection": self.enable_regime_detection,
            "enable_meta_learning": self.enable_meta_learning,
            "parallel_workers": self.parallel_workers,
        }
