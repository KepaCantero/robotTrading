"""
Database models for position monitoring and other features.

This module re-exports all models from the parent models.py module
to maintain backward compatibility with existing imports.
"""

# Import directly from the models.py file to avoid circular import
# We need to import the module first, then extract all models
import sys
from pathlib import Path

# Add the parent directory to sys.modules if not already present
models_file = Path(__file__).parent.parent / "models.py"

# Import the module using importlib to avoid circular reference
spec = __import__("importlib.util").util.spec_from_file_location(
    "app.database.models_module",
    models_file
)
models_module = __import__("importlib.util").util.module_from_spec(spec)
sys.modules["app.database.models_module"] = models_module
spec.loader.exec_module(models_module)

# Extract all models from the loaded module
User = models_module.User
APIKey = models_module.APIKey
Portfolio = models_module.Portfolio
Asset = models_module.Asset
Position = models_module.Position
Trade = models_module.Trade
MarketData = models_module.MarketData
Signal = models_module.Signal
Backtest = models_module.Backtest
RiskMetrics = models_module.RiskMetrics
SystemLog = models_module.SystemLog
PositionState = models_module.PositionState

__all__ = [
    "User",
    "APIKey",
    "Portfolio",
    "Asset",
    "Position",
    "Trade",
    "MarketData",
    "Signal",
    "Backtest",
    "RiskMetrics",
    "SystemLog",
    "PositionState",
]
