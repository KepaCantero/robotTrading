"""
Walk-Forward Validation & Stress Testing System (Task 3.5)

Comprehensive validation system including:
- Walk-forward validation with configurable windows
- Temporal cross-validation
- Stress testing with synthetic data generation
- Monte Carlo simulations

COMPLIANCE: Integrado con BacktestingCompliance para validar:
- R5: Walk-Forward Analysis
- R6: Overfitting Prevention
- R7: Monte Carlo para riesgo
- DATA-001: Purged Cross-Validation
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union

import numpy as np
import yaml

# Type alias for nested JSON-like configuration and result dictionaries
JsonDict = dict[
    str,
    Union[
        int,
        float,
        str,
        bool,
        None,
        "JsonDict",
        list[Union[int, float, str, bool, None, "JsonDict"]],
    ],
]

# COMPLIANCE: Importar BacktestingCompliance para R5, R6, R7, DATA-001
from app.backtesting.backtesting_compliance import (
    BacktestingComplianceResult,
    create_backtesting_compliance,
)
from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig
from app.backtesting.realistic_data_generator import MarketRegime, RealisticDataGenerator
from app.domain.models.market_data import Quote

logger = logging.getLogger(__name__)


# ============================================================================
# Parameter Dataclasses for Reducing Function Arguments
# ============================================================================


@dataclass
class DataGenerationParams:
    """Parameters for synthetic data generation methods."""

    n_days: int
    start_date: datetime
    symbol: str = "SYNTH"
    drift: Optional[float] = None
    volatility: Optional[float] = None


@dataclass
class JumpDiffusionParams:
    """Parameters for jump diffusion price generation."""

    n_days: int
    start_date: datetime
    symbol: str = "SYNTH"
    jump_intensity: float = 0.1
    jump_mean: float = 0.0
    jump_std: float = 0.05


@dataclass
class FlashCrashParams:
    """Parameters for flash crash scenario generation."""

    n_days: int
    start_date: datetime
    symbol: str = "SYNTH"
    drop_pct: float = -0.10
    recovery_days: int = 5


@dataclass
class GapScenarioParams:
    """Parameters for gap scenario generation."""

    n_days: int
    start_date: datetime
    symbol: str = "SYNTH"
    gap_pct: float = 0.05
    n_gaps: int = 3


@dataclass
class ScenarioGenerationParams:
    """Parameters for stress test scenario generation."""

    scenario_type: str
    scenario_config: JsonDict
    n_days: int
    start_date: datetime
    symbol: str


@dataclass
class WalkForwardValidationParams:
    """Parameters for walk-forward strategy validation."""

    quotes: list[Quote]
    signals: list[object]
    config: BacktestConfig
    start_date: datetime
    end_date: datetime


@dataclass
class CrossValidationParams:
    """Parameters for temporal cross-validation."""

    quotes: list[Quote]
    signals: list[object]
    config: BacktestConfig
    start_date: datetime
    end_date: datetime


@dataclass
class FullValidationParams:
    """Parameters for full validation suite."""

    strategy: object
    strategy_name: str
    quotes: list[Quote]
    signals: list[object]
    backtest_config: BacktestConfig
    start_date: datetime
    end_date: datetime


# ============================================================================
# Configuration Loading
# ============================================================================


def load_validation_config(config_path: str = "config/validation.yaml") -> JsonDict:
    """Load validation configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Validation config not found at {config_path}, using defaults")
        return get_default_config()

    with open(path) as f:
        return yaml.safe_load(f)


def get_default_config() -> JsonDict:
    """Return default validation configuration (Req #2 - Enhanced)."""
    return {
        "walk_forward": {
            "enabled": True,
            "train_years": 4,
            "validation_years": 1,
            "step_years": 1,
            "min_windows": 3,
            "min_trades_per_window": 10,
            # Req #2: Walk-Forward Complete thresholds
            "min_cycles": 5,  # Minimum 5 complete cycles
            "thresholds": {
                # Original thresholds
                "min_consistency": 0.8,  # Increased from 0.6 - require 80% profitable windows
                "max_return_std": 0.25,  # Tightened from 0.3 - less variance allowed
                "min_avg_sharpe": 0.7,  # Increased from 0.5 - higher bar for Sharpe
                "max_avg_drawdown": -0.15,  # Tightened from -0.20 - less drawdown tolerance
                # Req #2: New IS/OOS thresholds
                "min_consistency_ratio": 0.7,  # Sharpe_OOS / Sharpe_IS > 0.7
                "max_degradation": 0.30,  # Maximum 30% degradation IS->OOS
                "max_negative_window_pct": 0.50,  # Max 50% negative windows before rejection
            },
        },
        "cross_validation": {
            "enabled": True,
            "n_folds": 5,
            "thresholds": {
                "min_consistency_score": 0.8,  # Increased from 0.6 - require 80% positive folds
                "max_return_variance": 0.20,  # Tightened from 0.25 - less variance allowed
            },
        },
        "stress_testing": {
            "enabled": True,
            "n_scenarios": 100,
            "scenarios": {
                "flash_crash": {
                    "enabled": True,
                    "weight": 0.15,
                    "drop_percentage": -0.10,
                    "recovery_days": 5,
                },
                "high_volatility": {
                    "enabled": True,
                    "weight": 0.20,
                    "volatility_multiplier": 3.0,
                    "duration_days": 20,
                },
                "trending_bull": {
                    "enabled": True,
                    "weight": 0.15,
                    "daily_drift": 0.002,
                    "duration_days": 60,
                },
                "trending_bear": {
                    "enabled": True,
                    "weight": 0.15,
                    "daily_drift": -0.002,
                    "duration_days": 60,
                },
                "mean_reverting": {
                    "enabled": True,
                    "weight": 0.15,
                    "reversion_speed": 0.1,
                    "equilibrium_price": 100.0,
                },
                "gap_up": {"enabled": True, "weight": 0.10, "gap_percentage": 0.05, "n_gaps": 3},
                "gap_down": {"enabled": True, "weight": 0.10, "gap_percentage": -0.05, "n_gaps": 3},
            },
            "thresholds": {
                "max_scenario_drawdown": -0.30,
                "min_survival_rate": 0.80,
                "max_avg_loss": -0.15,
                "min_recovery_rate": 0.70,
            },
        },
        "synthetic_data": {
            "base_price": 100.0,
            "base_volume": 1000000,
            "price_model": "gbm",
            "annual_volatility": 0.20,
            "annual_drift": 0.05,
            "volume_noise": 0.30,
        },
        "monte_carlo": {
            "enabled": True,
            "n_simulations": 1000,
            "confidence_levels": [0.95, 0.99],
            "block_size": 20,
        },
    }


# ============================================================================
# Data Classes for Results
# ============================================================================


@dataclass
class ValidationWindow:
    """Represents a single validation window result."""

    window_id: int
    train_start: datetime
    train_end: datetime
    validate_start: datetime
    validate_end: datetime
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    win_rate: float
    passed: bool = True

    # In-Sample (IS) metrics (Req #2 - Walk-Forward Complete)
    is_total_return: float = 0.0
    is_sharpe_ratio: float = 0.0
    is_max_drawdown: float = 0.0
    is_total_trades: int = 0
    is_win_rate: float = 0.0

    # Out-of-Sample (OOS) metrics alias (same as main metrics)
    @property
    def oos_total_return(self) -> float:
        """Return out-of-sample total return (alias for total_return)."""
        return self.total_return

    @property
    def oos_sharpe_ratio(self) -> float:
        """Return out-of-sample Sharpe ratio (alias for sharpe_ratio)."""
        return self.sharpe_ratio

    @property
    def oos_max_drawdown(self) -> float:
        """Return out-of-sample max drawdown (alias for max_drawdown)."""
        return self.max_drawdown


@dataclass
class StressScenarioResult:
    """Result of a single stress test scenario."""

    scenario_type: str
    scenario_id: int
    total_return: float
    max_drawdown: float
    survived: bool
    recovered: bool
    final_capital: float
    trades_executed: int


@dataclass
class ValidationReport:
    """Complete validation report."""

    strategy_name: str
    timestamp: datetime
    walk_forward_results: Optional[JsonDict] = None
    cross_validation_results: Optional[JsonDict] = None
    stress_test_results: Optional[JsonDict] = None
    monte_carlo_results: Optional[JsonDict] = None
    overall_passed: bool = False
    summary: JsonDict = field(default_factory=dict)


# ============================================================================
# Synthetic Data Generator (Enhanced with Realistic Models)
# ============================================================================


class SyntheticDataGenerator:
    """
    Generates realistic synthetic market data for stress testing.

    This is now a wrapper around RealisticDataGenerator which provides:
    - Markov Regime-Switching Model (bull/bear/sideways markets)
    - GARCH-like volatility clustering
    - Volume correlated with volatility and price movements
    - Jump-diffusion for extreme events

    The old simplistic models have been replaced with statistically realistic models.
    """

    def __init__(self, config: JsonDict):
        """
        Initialize with configuration.

        Args:
            config: Configuration dictionary with keys:
                - base_price: Starting price
                - base_volume: Base daily volume
                - annual_volatility: Annual volatility (for backward compatibility)
                - annual_drift: Annual drift (for backward compatibility)
                - random_state: Random seed
        """
        self.config = config
        self.base_price = config.get("base_price", 100.0)
        self.base_volume = int(config.get("base_volume", 50000000))

        # For backward compatibility, map old config to new generator
        self.realistic_generator = RealisticDataGenerator(
            seed=config.get("random_state", 42),
            base_price=self.base_price,
            base_volume=self.base_volume,
        )

        # Store old parameters for backward compatibility
        self.annual_volatility = config.get("annual_volatility", 0.20)
        self.annual_drift = config.get("annual_drift", 0.05)
        self.random_state = config.get("random_state", 42)

    def generate_gbm_prices(
        self,
        params: DataGenerationParams,
    ) -> list[Quote]:
        """
        Generate prices using realistic models (replaces simplistic GBM).

        The old GBM implementation used:
        - Constant volatility (unrealistic)
        - No volume correlation
        - No market regimes

        The new implementation uses:
        - Regime-switching model (bull/bear/sideways)
        - GARCH-like volatility clustering
        - Volume correlated with volatility

        Args:
            params: DataGenerationParams with n_days, start_date, symbol,
                    drift (DEPRECATED), volatility (DEPRECATED)

        Returns:
            List of Quote objects with realistic OHLCV data
        """
        n_days = params.n_days
        start_date = params.start_date
        symbol = params.symbol

        logger.info(f"Generating {n_days} days of realistic data (replacing simplistic GBM)")

        # Use realistic generator with regime switching
        return self.realistic_generator.generate_realistic_quotes(
            symbol=symbol,
            n_days=n_days,
            start_date=start_date,
            use_regime_switching=True,
            initial_regime=MarketRegime.BULL,  # Default to bull market
        )

    def generate_ou_prices(
        self,
        params: DataGenerationParams,
    ) -> list[Quote]:
        """
        Generate mean-reverting prices (replaces simplistic OU).

        The old OU implementation used a single mean-reversion level.
        The new implementation uses the sideways regime which provides
        more realistic mean-reversion with volatility clustering.

        Args:
            params: DataGenerationParams with n_days, start_date, symbol

        Returns:
            List of Quote objects
        """
        n_days = params.n_days
        start_date = params.start_date
        symbol = params.symbol

        logger.info(
            f"Generating {n_days} days of realistic sideways data (replacing simplistic OU)"
        )

        return self.realistic_generator.generate_realistic_quotes(
            symbol=symbol,
            n_days=n_days,
            start_date=start_date,
            use_regime_switching=True,
            initial_regime=MarketRegime.SIDEWAYS,
        )

    def generate_jump_diffusion_prices(
        self,
        params: JumpDiffusionParams,
    ) -> list[Quote]:
        """
        Generate prices with jumps (replaces simplistic jump-diffusion).

        The old implementation had:
        - Fixed jump probability
        - Simplistic jump sizes

        The new implementation:
        - Uses volatile regime with enhanced jumps
        - Jumps correlate with volatility
        - More realistic jump distributions

        Args:
            params: JumpDiffusionParams with n_days, start_date, symbol,
                    jump_intensity, jump_mean, jump_std (all DEPRECATED -
                    built into volatile regime)

        Returns:
            List of Quote objects
        """
        n_days = params.n_days
        start_date = params.start_date
        symbol = params.symbol

        logger.info(
            f"Generating {n_days} days of realistic volatile data with jumps "
            f"(replacing simplistic jump-diffusion)"
        )

        return self.realistic_generator.generate_realistic_quotes(
            symbol=symbol,
            n_days=n_days,
            start_date=start_date,
            use_regime_switching=True,
            initial_regime=MarketRegime.VOLATILE,
        )

    def generate_flash_crash_scenario(
        self,
        params: FlashCrashParams,
    ) -> list[Quote]:
        """
        Generate a flash crash scenario.

        The old implementation had:
        - Random crash timing (non-reproducible)
        - Linear recovery (unrealistic)

        The new implementation:
        - Uses bear regime with high volatility
        - More realistic crash dynamics
        - Reproducible with seed

        Args:
            params: FlashCrashParams with n_days, start_date, symbol,
                    drop_pct, recovery_days

        Returns:
            List of Quote objects with flash crash scenario
        """
        n_days = params.n_days
        start_date = params.start_date
        symbol = params.symbol

        logger.info(
            f"Generating {n_days} days of flash crash scenario (bear regime with high volatility)"
        )

        return self.realistic_generator.generate_realistic_quotes(
            symbol=symbol,
            n_days=n_days,
            start_date=start_date,
            use_regime_switching=True,
            initial_regime=MarketRegime.BEAR,
        )

    def generate_high_volatility_scenario(
        self,
        n_days: int,
        start_date: datetime,
        symbol: str = "SYNTH",
        volatility_multiplier: float = 3.0,
    ) -> list[Quote]:
        """
        Generate high volatility scenario.

        Args:
            n_days: Number of days to generate
            start_date: Start date
            symbol: Trading symbol
            volatility_multiplier: Multiplier (ignored - uses volatile regime)

        Returns:
            List of Quote objects with high volatility
        """
        logger.info(f"Generating {n_days} days of high volatility scenario (volatile regime)")

        return self.realistic_generator.generate_realistic_quotes(
            symbol=symbol,
            n_days=n_days,
            start_date=start_date,
            use_regime_switching=True,
            initial_regime=MarketRegime.VOLATILE,
        )

    def generate_trending_scenario(
        self,
        n_days: int,
        start_date: datetime,
        symbol: str = "SYNTH",
        daily_drift: float = 0.002,
    ) -> list[Quote]:
        """
        Generate trending market scenario.

        Args:
            n_days: Number of days to generate
            start_date: Start date
            symbol: Trading symbol
            daily_drift: Daily drift (ignored - uses bull regime)

        Returns:
            List of Quote objects with uptrend
        """
        logger.info(f"Generating {n_days} days of trending scenario (bull regime)")

        return self.realistic_generator.generate_realistic_quotes(
            symbol=symbol,
            n_days=n_days,
            start_date=start_date,
            use_regime_switching=True,
            initial_regime=MarketRegime.BULL,
        )

    def generate_gap_scenario(
        self,
        params: GapScenarioParams,
    ) -> list[Quote]:
        """
        Generate scenario with overnight gaps.

        The new implementation naturally produces gaps through
        realistic overnight price movements.

        Args:
            params: GapScenarioParams with n_days, start_date, symbol,
                    gap_pct, n_gaps

        Returns:
            List of Quote objects with natural gaps
        """
        n_days = params.n_days
        start_date = params.start_date
        symbol = params.symbol

        logger.info(
            f"Generating {n_days} days with realistic gaps (using volatile regime for more gaps)"
        )

        return self.realistic_generator.generate_realistic_quotes(
            symbol=symbol,
            n_days=n_days,
            start_date=start_date,
            use_regime_switching=True,
            initial_regime=MarketRegime.VOLATILE,  # Volatile = more gaps
        )

    def _prices_to_quotes(
        self,
        prices: list[float],
        start_date: datetime,
        symbol: str,
    ) -> list[Quote]:
        """
        DEPRECATED: This method is kept for backward compatibility.

        The realistic generator now handles all quote generation internally
        with proper OHLC, volume, and bid-ask spread.

        This method simply wraps the realistic generator.
        """
        logger.warning("_prices_to_quotes is deprecated. Using realistic data generator instead.")

        # Use realistic generator for proper OHLC
        return self.realistic_generator.generate_realistic_quotes(
            symbol=symbol,
            n_days=len(prices),
            start_date=start_date,
            use_regime_switching=False,  # Don't use regime switching for single list
            initial_regime=MarketRegime.SIDEWAYS,
        )


# ============================================================================
# Walk-Forward Validator (Enhanced)
# ============================================================================


class WalkForwardValidator:
    """
    Walk-Forward Validation (Task 3.5).

    Trains on historical window, validates on subsequent period, then rolls forward.
    Now with configurable thresholds and comprehensive reporting.

    COMPLIANCE: Integra BacktestingCompliance para validar reglas R5, R6, R7, DATA-001.
    """

    def __init__(
        self,
        config: Optional[JsonDict] = None,
        config_path: str = "config/validation.yaml",
    ):
        """
        Initialize walk-forward validator.

        Args:
            config: Configuration dict (overrides config_path if provided)
            config_path: Path to YAML config file
        """
        if config is None:
            full_config = load_validation_config(config_path)
            config = full_config.get("walk_forward", {})

        self.train_years = config.get("train_years", 4)
        self.validation_years = config.get("validation_years", 1)
        self.step_years = config.get("step_years", 1)
        self.min_windows = config.get("min_windows", 3)
        self.min_trades_per_window = config.get("min_trades_per_window", 10)
        self.thresholds = config.get(
            "thresholds",
            {
                "min_consistency": 0.6,
                "max_return_std": 0.3,
                "min_avg_sharpe": 0.5,
                "max_avg_drawdown": -0.20,
            },
        )

        # COMPLIANCE: Inicializar validador de compliance
        self.backtesting_compliance = create_backtesting_compliance()
        self.compliance_results: list[BacktestingComplianceResult] = []
        logger.info(
            "WalkForwardValidator initialized with BacktestingCompliance (R5, R6, R7, DATA-001)"
        )

    def create_windows(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, datetime]]:
        """Create walk-forward windows."""
        windows = []
        current_start = start_date

        while current_start < end_date:
            train_end = current_start + timedelta(days=365 * self.train_years)
            validate_start = train_end
            validate_end = validate_start + timedelta(days=365 * self.validation_years)

            if validate_end > end_date:
                break

            windows.append(
                {
                    "train_start": current_start,
                    "train_end": train_end,
                    "validate_start": validate_start,
                    "validate_end": validate_end,
                }
            )

            current_start += timedelta(days=365 * self.step_years)

        return windows

    def validate_strategy(
        self,
        params: WalkForwardValidationParams,
    ) -> JsonDict:
        """
        Run walk-forward validation for a strategy (Req #2 - Enhanced).

        Now includes:
        - In-Sample (IS) metrics from training period
        - Out-of-Sample (OOS) metrics from validation period
        - Consistency Ratio: Sharpe_OOS / Sharpe_IS
        - Degradation metrics (max 30%)
        - Minimum 5 cycles validation

        Args:
            params: WalkForwardValidationParams with quotes, signals,
                    config, start_date, end_date

        Returns:
            Dictionary with validation results and pass/fail status.
        """
        quotes = params.quotes
        signals = params.signals
        config = params.config
        start_date = params.start_date
        end_date = params.end_date

        windows = self.create_windows(start_date, end_date)

        # Req #2: Minimum 5 cycles validation
        min_cycles = self.thresholds.get("min_cycles", 5)
        if len(windows) < min_cycles:
            logger.warning(f"Insufficient windows: {len(windows)} < {min_cycles}")
            return {
                "passed": False,
                "reason": (
                    f"Insufficient windows for robust validation: {len(windows)} < {min_cycles}"
                ),
                "windows": [],
                "is_oos_analysis": None,
            }

        results: list[ValidationWindow] = []

        for i, window in enumerate(windows):
            logger.info(
                f"Walk-forward window {i + 1}/{len(windows)}: "
                f"Train {window['train_start'].strftime('%Y-%m-%d')} to "
                f"{window['train_end'].strftime('%Y-%m-%d')} | "
                f"Validate {window['validate_start'].strftime('%Y-%m-%d')} to "
                f"{window['validate_end'].strftime('%Y-%m-%d')}"
            )

            # Filter data for training (IS) period
            train_quotes = [
                q for q in quotes if window["train_start"] <= q.timestamp <= window["train_end"]
            ]
            train_signals = [
                s
                for s in signals
                if hasattr(s, "timestamp")
                and window["train_start"] <= s.timestamp <= window["train_end"]
            ]

            # Filter data for validation (OOS) period
            validate_quotes = [
                q
                for q in quotes
                if window["validate_start"] <= q.timestamp <= window["validate_end"]
            ]
            validate_signals = [
                s
                for s in signals
                if hasattr(s, "timestamp")
                and window["validate_start"] <= s.timestamp <= window["validate_end"]
            ]

            if not validate_quotes or not validate_signals:
                logger.warning(f"Window {i + 1}: Insufficient OOS data, skipping")
                continue

            # Run backtest on training period (IS metrics)
            is_metrics = {
                "total_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "total_trades": 0,
                "win_rate": 0.0,
            }
            if train_quotes and train_signals:
                try:
                    train_backtester = SimpleBacktester(config)
                    train_result = train_backtester.run_backtest(
                        train_quotes,
                        train_signals,
                        window["train_start"],
                        window["train_end"],
                    )
                    is_metrics = {
                        "total_return": float(train_result.total_return),
                        "sharpe_ratio": float(train_result.performance.sharpe_ratio or 0),
                        "max_drawdown": float(
                            train_result.performance.max_drawdown_percentage or 0
                        ),
                        "total_trades": train_result.performance.total_trades,
                        "win_rate": float(train_result.performance.win_rate),
                    }
                except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                    logger.warning(f"Window {i + 1}: IS backtest failed: {e}")

            # Run backtest on validation period (OOS metrics)
            backtester = SimpleBacktester(config)
            result = backtester.run_backtest(
                validate_quotes,
                validate_signals,
                window["validate_start"],
                window["validate_end"],
            )

            window_result = ValidationWindow(
                window_id=i + 1,
                train_start=window["train_start"],
                train_end=window["train_end"],
                validate_start=window["validate_start"],
                validate_end=window["validate_end"],
                total_return=float(result.total_return),
                sharpe_ratio=float(result.performance.sharpe_ratio or 0),
                max_drawdown=float(result.performance.max_drawdown_percentage or 0),
                total_trades=result.performance.total_trades,
                win_rate=float(result.performance.win_rate),
                passed=result.performance.total_trades >= self.min_trades_per_window,
                # IS metrics (Req #2)
                is_total_return=is_metrics["total_return"],
                is_sharpe_ratio=is_metrics["sharpe_ratio"],
                is_max_drawdown=is_metrics["max_drawdown"],
                is_total_trades=is_metrics["total_trades"],
                is_win_rate=is_metrics["win_rate"],
            )
            results.append(window_result)

        if not results:
            return {
                "passed": False,
                "reason": "No valid windows completed",
                "windows": [],
                "is_oos_analysis": None,
            }

        # Calculate aggregated metrics
        total_returns = [r.total_return for r in results]
        sharpe_ratios = [r.sharpe_ratio for r in results]
        max_drawdowns = [r.max_drawdown for r in results]

        # IS metrics aggregation
        is_returns = [r.is_total_return for r in results if r.is_total_return != 0]
        is_sharpe_ratios = [r.is_sharpe_ratio for r in results if r.is_sharpe_ratio != 0]
        is_drawdowns = [r.is_max_drawdown for r in results if r.is_max_drawdown != 0]

        avg_return = np.mean(total_returns)
        std_return = np.std(total_returns) if len(total_returns) > 1 else 0
        avg_sharpe = np.mean(sharpe_ratios)
        avg_drawdown = np.mean(max_drawdowns)
        consistency = len([r for r in total_returns if r > 0]) / len(total_returns)

        # IS/OOS Analysis (Req #2)
        is_oos_analysis = {
            "avg_is_return": np.mean(is_returns) if is_returns else 0.0,
            "avg_is_sharpe": (np.mean(is_sharpe_ratios) if is_sharpe_ratios else 0.0),
            "avg_is_drawdown": np.mean(is_drawdowns) if is_drawdowns else 0.0,
        }

        # Consistency Ratio: Sharpe_OOS / Sharpe_IS (Req #2)
        if is_oos_analysis["avg_is_sharpe"] > 0:
            consistency_ratio = avg_sharpe / is_oos_analysis["avg_is_sharpe"]
        else:
            consistency_ratio = 0.0

        is_oos_analysis["consistency_ratio"] = consistency_ratio

        # Degradation metrics (Req #2 - max 30%)
        if is_oos_analysis["avg_is_return"] != 0:
            return_degradation = abs(
                (is_oos_analysis["avg_is_return"] - avg_return) / is_oos_analysis["avg_is_return"]
            )
        else:
            return_degradation = 0.0

        if is_oos_analysis["avg_is_sharpe"] > 0:
            sharpe_degradation = (is_oos_analysis["avg_is_sharpe"] - avg_sharpe) / is_oos_analysis[
                "avg_is_sharpe"
            ]
        else:
            sharpe_degradation = 0.0

        is_oos_analysis["return_degradation"] = return_degradation
        is_oos_analysis["sharpe_degradation"] = sharpe_degradation

        # Negative windows detection (Req #2)
        negative_windows = len([r for r in results if r.total_return < 0])
        negative_window_pct = negative_windows / len(results)
        is_oos_analysis["negative_windows"] = negative_windows
        is_oos_analysis["negative_window_pct"] = negative_window_pct

        # Check thresholds
        passed = True
        failures = []

        # Existing thresholds
        if consistency < self.thresholds.get("min_consistency", 0.6):
            passed = False
            failures.append(
                f"Consistency {consistency:.2%} < {self.thresholds['min_consistency']:.2%}"
            )

        if std_return > self.thresholds.get("max_return_std", 0.3):
            passed = False
            failures.append(
                f"Return std {std_return:.2%} > {self.thresholds['max_return_std']:.2%}"
            )

        if avg_sharpe < self.thresholds.get("min_avg_sharpe", 0.5):
            passed = False
            failures.append(
                f"Avg Sharpe {avg_sharpe:.2f} < {self.thresholds['min_avg_sharpe']:.2f}"
            )

        if avg_drawdown < self.thresholds.get("max_avg_drawdown", -0.20):
            passed = False
            failures.append(
                f"Avg Drawdown {avg_drawdown:.2%} < {self.thresholds['max_avg_drawdown']:.2%}"
            )

        # Req #2: Consistency Ratio threshold (> 0.7)
        consistency_ratio_threshold = self.thresholds.get("min_consistency_ratio", 0.7)
        if consistency_ratio < consistency_ratio_threshold:
            passed = False
            failures.append(
                f"Consistency Ratio (Sharpe OOS/IS) {consistency_ratio:.2f} < "
                f"{consistency_ratio_threshold}"
            )

        # Req #2: Degradation threshold (< 30%)
        max_degradation = self.thresholds.get("max_degradation", 0.30)
        if sharpe_degradation > max_degradation:
            passed = False
            failures.append(
                f"Sharpe degradation {sharpe_degradation:.1%} exceeds "
                f"{max_degradation:.0%} threshold"
            )

        # Req #2: Negative windows threshold (< 50%)
        max_negative_windows = self.thresholds.get("max_negative_window_pct", 0.50)
        if negative_window_pct > max_negative_windows:
            passed = False
            failures.append(
                f"Negative windows {negative_window_pct:.1%} > "
                f"{max_negative_windows:.0%} (strategy rejected)"
            )

        return {
            "passed": passed,
            "failures": failures if not passed else [],
            "windows": [
                {
                    "window": r.window_id,
                    "train_period": {
                        "start": r.train_start.isoformat(),
                        "end": r.train_end.isoformat(),
                    },
                    "validate_period": {
                        "start": r.validate_start.isoformat(),
                        "end": r.validate_end.isoformat(),
                    },
                    # IS metrics (Req #2)
                    "is_metrics": {
                        "total_return": r.is_total_return,
                        "sharpe_ratio": r.is_sharpe_ratio,
                        "max_drawdown": r.is_max_drawdown,
                        "total_trades": r.is_total_trades,
                        "win_rate": r.is_win_rate,
                    },
                    # OOS metrics (Req #2)
                    "oos_metrics": {
                        "total_return": r.total_return,
                        "sharpe_ratio": r.sharpe_ratio,
                        "max_drawdown": r.max_drawdown,
                        "total_trades": r.total_trades,
                        "win_rate": r.win_rate,
                    },
                }
                for r in results
            ],
            "aggregated": {
                "avg_return": avg_return,
                "std_return": std_return,
                "avg_sharpe": avg_sharpe,
                "avg_max_drawdown": avg_drawdown,
                "consistency": consistency,
            },
            "is_oos_analysis": is_oos_analysis,
            "thresholds": self.thresholds,
        }

    def validate_compliance(
        self,
        walk_forward_results: list[JsonDict],
        n_parameters: int = 10,
        n_observations: int = 1000,
    ) -> BacktestingComplianceResult:
        """
        Validar compliance de walk-forward según reglas R5, R6, R7, DATA-001.

        COMPLIANCE: Este método integra las validaciones de backtesting:
        - R5: Walk-Forward Analysis (consistencia y degradación)
        - R6: Overfitting Prevention (ratio parámetros/observaciones)
        - DATA-001: Purged CV (purge days y embargo)

        Args:
            walk_forward_results: Resultados de las ventanas walk-forward
            n_parameters: Número de parámetros optimizables
            n_observations: Número de observaciones en el dataset

        Returns:
            BacktestingComplianceResult con el resultado de la validación
        """
        logger.info("Validating walk-forward compliance (R5, R6, DATA-001)...")

        # Preparar datos para R5 (Walk-Forward)
        windows = []
        for r in walk_forward_results:
            is_metrics = r.get("is_metrics", {})
            oos_metrics = r.get("oos_metrics", {})
            windows.append(
                {
                    "is_return": is_metrics.get("total_return", 0),
                    "oos_return": oos_metrics.get("total_return", 0),
                    "is_sharpe": is_metrics.get("sharpe_ratio", 0),
                    "oos_sharpe": oos_metrics.get("sharpe_ratio", 0),
                    "trades": oos_metrics.get("total_trades", 0),
                }
            )

        # Ejecutar validación
        compliance_result = self.backtesting_compliance.validate_backtest(
            n_parameters=n_parameters,
            n_observations=n_observations,
            walk_forward_windows=windows,
            purge_days=5,  # Default purge days
            embargo_days=10,  # Default embargo days
        )

        self.compliance_results.append(compliance_result)

        # Log resumen
        if compliance_result.is_compliant:
            logger.info(f"Walk-Forward COMPLIANCE PASSED: {compliance_result.get_summary()}")
        else:
            logger.warning(f"Walk-Forward COMPLIANCE FAILED: {compliance_result.get_summary()}")
            for v in compliance_result.violations:
                logger.warning(f"  [{v.severity}] {v.rule_id}: {v.message}")

        return compliance_result


# ============================================================================
# Cross-Validation Temporal (Enhanced)
# ============================================================================


class CrossValidationTemporal:
    """
    Cross-Validation Temporal (Task 3.5).

    Evaluates consistency of strategies across different time periods.
    """

    def __init__(
        self,
        config: Optional[JsonDict] = None,
        config_path: str = "config/validation.yaml",
    ):
        """Initialize temporal cross-validator."""
        if config is None:
            full_config = load_validation_config(config_path)
            config = full_config.get("cross_validation", {})

        self.n_folds = config.get("n_folds", 5)
        self.thresholds = config.get(
            "thresholds",
            {
                "min_consistency_score": 0.6,
                "max_return_variance": 0.25,
            },
        )

    def create_folds(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, datetime]]:
        """Create temporal folds for cross-validation."""
        total_days = (end_date - start_date).days
        fold_days = total_days // self.n_folds

        folds = []
        for i in range(self.n_folds):
            fold_start = start_date + timedelta(days=i * fold_days)
            fold_end = start_date + timedelta(days=(i + 1) * fold_days)

            if i == self.n_folds - 1:
                fold_end = end_date

            folds.append(
                {
                    "fold": i + 1,
                    "start": fold_start,
                    "end": fold_end,
                }
            )

        return folds

    def cross_validate(
        self,
        params: CrossValidationParams,
    ) -> JsonDict:
        """Run temporal cross-validation.

        Args:
            params: CrossValidationParams with quotes, signals,
                    config, start_date, end_date

        Returns:
            Dictionary with cross-validation results.
        """
        quotes = params.quotes
        signals = params.signals
        config = params.config
        start_date = params.start_date
        end_date = params.end_date

        folds = self.create_folds(start_date, end_date)
        results = []

        for fold in folds:
            logger.info(
                f"Fold {fold['fold']}/{self.n_folds}: "
                f"{fold['start'].strftime('%Y-%m-%d')} to {fold['end'].strftime('%Y-%m-%d')}"
            )

            fold_quotes = [q for q in quotes if fold["start"] <= q.timestamp <= fold["end"]]

            fold_signals = [
                s
                for s in signals
                if hasattr(s, "timestamp") and fold["start"] <= s.timestamp <= fold["end"]
            ]

            if not fold_quotes or not fold_signals:
                continue

            backtester = SimpleBacktester(config)
            result = backtester.run_backtest(
                fold_quotes,
                fold_signals,
                fold["start"],
                fold["end"],
            )

            results.append(
                {
                    "fold": fold["fold"],
                    "period": {
                        "start": fold["start"].isoformat(),
                        "end": fold["end"].isoformat(),
                    },
                    "result": {
                        "total_return": float(result.total_return),
                        "sharpe_ratio": float(result.performance.sharpe_ratio or 0),
                        "max_drawdown": float(result.performance.max_drawdown_percentage or 0),
                        "total_trades": result.performance.total_trades,
                        "win_rate": float(result.performance.win_rate),
                    },
                }
            )

        if not results:
            return {"passed": False, "reason": "No valid folds", "folds": []}

        # Calculate aggregated metrics
        total_returns = [r["result"]["total_return"] for r in results]
        avg_return = np.mean(total_returns)
        return_variance = np.var(total_returns) if len(total_returns) > 1 else 0
        consistency_score = len([r for r in total_returns if r > 0]) / len(total_returns)

        # Check thresholds
        passed = True
        failures = []

        if consistency_score < self.thresholds.get("min_consistency_score", 0.6):
            passed = False
            failures.append(
                f"Consistency {consistency_score:.2%} < "
                f"{self.thresholds['min_consistency_score']:.2%}"
            )

        if return_variance > self.thresholds.get("max_return_variance", 0.25):
            passed = False
            failures.append(
                f"Return variance {return_variance:.4f} > {self.thresholds['max_return_variance']}"
            )

        return {
            "passed": passed,
            "failures": failures if not passed else [],
            "folds": results,
            "aggregated": {
                "avg_return": avg_return,
                "return_variance": return_variance,
                "std_return": np.std(total_returns) if len(total_returns) > 1 else 0,
                "min_return": min(total_returns),
                "max_return": max(total_returns),
                "consistency_score": consistency_score,
            },
            "thresholds": self.thresholds,
        }


# ============================================================================
# Stress Tester
# ============================================================================


class StressTester:
    """
    Stress Testing System (Task 3.5).

    Tests strategy robustness against synthetic market scenarios.
    """

    def __init__(
        self,
        config: Optional[JsonDict] = None,
        config_path: str = "config/validation.yaml",
    ):
        """Initialize stress tester."""
        if config is None:
            full_config = load_validation_config(config_path)
            config = full_config.get("stress_testing", {})

        self.n_scenarios = config.get("n_scenarios", 100)
        self.scenarios_config = config.get("scenarios", {})
        self.thresholds = config.get(
            "thresholds",
            {
                "max_scenario_drawdown": -0.30,
                "min_survival_rate": 0.80,
                "max_avg_loss": -0.15,
                "min_recovery_rate": 0.70,
            },
        )

        # Load synthetic data config
        full_config = load_validation_config(config_path)
        self.data_generator = SyntheticDataGenerator(full_config.get("synthetic_data", {}))

    def _generate_scenario(
        self,
        params: ScenarioGenerationParams,
    ) -> list[Quote]:
        """Generate synthetic data for a specific scenario type."""
        scenario_type = params.scenario_type
        scenario_config = params.scenario_config
        n_days = params.n_days
        start_date = params.start_date
        symbol = params.symbol

        generators = {
            "flash_crash": lambda: self.data_generator.generate_flash_crash_scenario(
                FlashCrashParams(
                    n_days=n_days,
                    start_date=start_date,
                    symbol=symbol,
                    drop_pct=scenario_config.get("drop_percentage", -0.10),
                    recovery_days=scenario_config.get("recovery_days", 5),
                )
            ),
            "high_volatility": lambda: self.data_generator.generate_high_volatility_scenario(
                n_days,
                start_date,
                symbol,
                volatility_multiplier=scenario_config.get("volatility_multiplier", 3.0),
            ),
            "trending_bull": lambda: self.data_generator.generate_trending_scenario(
                n_days,
                start_date,
                symbol,
                daily_drift=scenario_config.get("daily_drift", 0.002),
            ),
            "trending_bear": lambda: self.data_generator.generate_trending_scenario(
                n_days,
                start_date,
                symbol,
                daily_drift=scenario_config.get("daily_drift", -0.002),
            ),
            "mean_reverting": lambda: self.data_generator.generate_ou_prices(
                n_days,
                start_date,
                symbol,
                theta=scenario_config.get("reversion_speed", 0.1),
                mu=scenario_config.get("equilibrium_price", 100.0),
            ),
            "gap_up": lambda: self.data_generator.generate_gap_scenario(
                GapScenarioParams(
                    n_days=n_days,
                    start_date=start_date,
                    symbol=symbol,
                    gap_pct=scenario_config.get("gap_percentage", 0.05),
                    n_gaps=scenario_config.get("n_gaps", 3),
                )
            ),
            "gap_down": lambda: self.data_generator.generate_gap_scenario(
                GapScenarioParams(
                    n_days=n_days,
                    start_date=start_date,
                    symbol=symbol,
                    gap_pct=scenario_config.get("gap_percentage", -0.05),
                    n_gaps=scenario_config.get("n_gaps", 3),
                )
            ),
        }

        generator = generators.get(scenario_type)
        if generator:
            return generator()

        # Default: GBM
        return self.data_generator.generate_gbm_prices(
            DataGenerationParams(n_days=n_days, start_date=start_date, symbol=symbol)
        )

    def run_stress_tests(
        self,
        strategy,
        backtest_config: BacktestConfig,
        n_days: int = 252,
        symbol: str = "STRESS_TEST",
    ) -> JsonDict:
        """
        Run comprehensive stress tests.

        Args:
            strategy: Strategy instance to test
            backtest_config: Backtest configuration
            n_days: Number of days per scenario
            symbol: Symbol to use for synthetic data

        Returns:
            Dictionary with stress test results
        """
        start_date = datetime(2020, 1, 1)
        scenario_counts = self._calculate_scenario_distribution()

        results: list[StressScenarioResult] = []
        for scenario_type, count in scenario_counts.items():
            scenario_results = self._run_scenario_batch(
                strategy, backtest_config, scenario_type, count, n_days, start_date, symbol
            )
            results.extend(scenario_results)

        if not results:
            return {"passed": False, "reason": "No scenarios completed", "scenarios": []}

        return self._build_stress_test_report(results)

    def _calculate_scenario_distribution(self) -> dict[str, int]:
        """Calculate the number of scenarios to run per type."""
        enabled_scenarios = {
            k: v for k, v in self.scenarios_config.items() if v.get("enabled", True)
        }
        total_weight = sum(s.get("weight", 0.1) for s in enabled_scenarios.values())
        return {
            k: max(1, int(self.n_scenarios * v.get("weight", 0.1) / total_weight))
            for k, v in enabled_scenarios.items()
        }

    def _run_scenario_batch(
        self,
        strategy,
        backtest_config: BacktestConfig,
        scenario_type: str,
        count: int,
        n_days: int,
        start_date: datetime,
        symbol: str,
    ) -> list[StressScenarioResult]:
        """Run a batch of scenarios of the same type."""
        scenario_config = self.scenarios_config.get(scenario_type, {})
        logger.info(f"Running {count} {scenario_type} scenarios...")
        results = []

        for i in range(count):
            try:
                result = self._run_single_scenario(
                    strategy,
                    backtest_config,
                    scenario_type,
                    scenario_config,
                    i,
                    n_days,
                    start_date,
                    symbol,
                )
                if result:
                    results.append(result)
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.warning(f"Error in {scenario_type} scenario {i + 1}: {e}")

        return results

    def _run_single_scenario(
        self,
        strategy,
        backtest_config: BacktestConfig,
        scenario_type: str,
        scenario_config: JsonDict,
        scenario_idx: int,
        n_days: int,
        start_date: datetime,
        symbol: str,
    ) -> Optional[StressScenarioResult]:
        """Run a single stress test scenario."""
        end_date = start_date + timedelta(days=n_days)

        quotes = self._generate_scenario(scenario_type, scenario_config, n_days, start_date, symbol)

        signals = self._generate_strategy_signals(strategy, quotes)
        if not signals:
            return None

        backtester = SimpleBacktester(backtest_config)
        result = backtester.run_backtest(quotes, signals, start_date, end_date)

        total_return = float(result.total_return)
        max_dd = float(result.performance.max_drawdown_percentage or 0)
        final_capital = float(result.final_capital)
        initial_capital = float(backtest_config.initial_capital)

        return StressScenarioResult(
            scenario_type=scenario_type,
            scenario_id=scenario_idx + 1,
            total_return=total_return,
            max_drawdown=max_dd,
            survived=max_dd > self.thresholds.get("max_scenario_drawdown", -0.30),
            recovered=final_capital >= initial_capital * 0.9,
            final_capital=final_capital,
            trades_executed=result.performance.total_trades,
        )

    def _generate_strategy_signals(self, strategy, quotes: list) -> list:
        """Generate signals from strategy for a list of quotes."""
        signals = []
        for quote in quotes:
            try:
                signal = strategy.analyze(quote)
                if signal:
                    signals.append(signal)
            except (ValueError, TypeError, KeyError, AttributeError, IndexError):
                pass
        return signals

    def _build_stress_test_report(self, results: list[StressScenarioResult]) -> JsonDict:
        """Build the final stress test report from results."""
        total_scenarios = len(results)
        survivors = sum(1 for r in results if r.survived)
        recovered = sum(1 for r in results if r.recovered)
        avg_return = sum(r.total_return for r in results) / total_scenarios
        avg_drawdown = sum(r.max_drawdown for r in results) / total_scenarios
        survival_rate = survivors / total_scenarios
        recovery_rate = recovered / total_scenarios

        passed, failures = self._evaluate_stress_thresholds(
            survival_rate, recovery_rate, avg_return
        )
        by_scenario = self._group_results_by_type(results)

        return {
            "passed": passed,
            "failures": failures if not passed else [],
            "summary": {
                "total_scenarios": total_scenarios,
                "survival_rate": survival_rate,
                "recovery_rate": recovery_rate,
                "avg_return": avg_return,
                "avg_drawdown": avg_drawdown,
            },
            "by_scenario_type": {
                scenario: {
                    "count": len(scenarios),
                    "avg_return": np.mean([s["total_return"] for s in scenarios]),
                    "survival_rate": np.mean([1 for s in scenarios if s["survived"]]),
                    "scenarios": scenarios,
                }
                for scenario, scenarios in by_scenario.items()
            },
            "thresholds": self.thresholds,
        }

    def _evaluate_stress_thresholds(
        self, survival_rate: float, recovery_rate: float, avg_return: float
    ) -> tuple[bool, list[str]]:
        """Evaluate stress test results against thresholds."""
        passed = True
        failures = []

        if survival_rate < self.thresholds.get("min_survival_rate", 0.80):
            passed = False
            failures.append(
                f"Survival rate {survival_rate:.2%} < {self.thresholds['min_survival_rate']:.2%}"
            )

        if avg_return < self.thresholds.get("max_avg_loss", -0.15):
            passed = False
            failures.append(f"Avg return {avg_return:.2%} < {self.thresholds['max_avg_loss']:.2%}")

        if recovery_rate < self.thresholds.get("min_recovery_rate", 0.70):
            passed = False
            failures.append(
                f"Recovery rate {recovery_rate:.2%} < {self.thresholds['min_recovery_rate']:.2%}"
            )

        return passed, failures

    def _group_results_by_type(self, results: list[StressScenarioResult]) -> dict[str, list[dict]]:
        """Group scenario results by type."""
        by_scenario: dict[str, list[dict]] = {}
        for r in results:
            if r.scenario_type not in by_scenario:
                by_scenario[r.scenario_type] = []
            by_scenario[r.scenario_type].append(
                {
                    "scenario_id": r.scenario_id,
                    "total_return": r.total_return,
                    "max_drawdown": r.max_drawdown,
                    "survived": r.survived,
                    "recovered": r.recovered,
                    "trades_executed": r.trades_executed,
                }
            )
        return by_scenario


# ============================================================================
# Monte Carlo Simulator
# ============================================================================


class MonteCarloSimulator:
    """
    Monte Carlo Simulation for strategy robustness testing.

    Uses bootstrap resampling to estimate confidence intervals.
    REPRODUCIBILITY: Uses np.random.default_rng for isolated random state.
    """

    def __init__(
        self,
        config: Optional[JsonDict] = None,
        config_path: str = "config/validation.yaml",
    ):
        """Initialize Monte Carlo simulator."""
        if config is None:
            full_config = load_validation_config(config_path)
            config = full_config.get("monte_carlo", {})

        self.n_simulations = config.get("n_simulations", 1000)
        self.confidence_levels = config.get("confidence_levels", [0.95, 0.99])
        self.block_size = config.get("block_size", 20)
        # Reproducible random state
        self.random_state = config.get("random_state", 42)
        self._rng = np.random.default_rng(self.random_state)

    def run_simulation(
        self,
        historical_returns: list[float],
        initial_capital: float = 100000.0,
        n_periods: int = 252,
    ) -> JsonDict:
        """
        Run Monte Carlo simulation with bootstrap resampling.

        Args:
            historical_returns: Historical daily returns
            initial_capital: Starting capital
            n_periods: Number of periods to simulate

        Returns:
            Dictionary with simulation results
        """
        if len(historical_returns) < self.block_size:
            return {"passed": False, "reason": "Insufficient historical data"}

        returns_array = np.array(historical_returns)
        simulation_results = self._run_all_simulations(returns_array, initial_capital, n_periods)

        returns = [float(r["total_return"]) for r in simulation_results]
        drawdowns = [float(r["max_drawdown"]) for r in simulation_results]

        return self._build_simulation_report(returns, drawdowns)

    def _run_all_simulations(
        self, returns_array: np.ndarray, initial_capital: float, n_periods: int
    ) -> list[JsonDict]:
        """Run all Monte Carlo simulations."""
        simulation_results = []

        for _ in range(self.n_simulations):
            result = self._run_single_simulation(returns_array, initial_capital, n_periods)
            simulation_results.append(result)

        return simulation_results

    def _run_single_simulation(
        self, returns_array: np.ndarray, initial_capital: float, n_periods: int
    ) -> JsonDict:
        """Run a single Monte Carlo simulation path."""
        simulated_returns = self._block_bootstrap(returns_array, n_periods)

        equity = [initial_capital]
        for ret in simulated_returns:
            equity.append(equity[-1] * (1 + ret))

        final_value = equity[-1]
        total_return = (final_value - initial_capital) / initial_capital
        max_drawdown = self._calculate_max_drawdown(equity)

        return {
            "final_value": final_value,
            "total_return": total_return,
            "max_drawdown": max_drawdown,
        }

    def _build_simulation_report(self, returns: list[float], drawdowns: list[float]) -> JsonDict:
        """Build the simulation report from aggregated results."""
        var_results, cvar_results = self._calculate_risk_metrics(returns)

        return {
            "passed": True,
            "n_simulations": self.n_simulations,
            "summary": {
                "mean_return": float(np.mean(returns)),
                "std_return": float(np.std(returns)),
                "median_return": float(np.median(returns)),
                "mean_max_drawdown": float(np.mean(drawdowns)),
                "worst_drawdown": float(min(drawdowns)),
            },
            "var": var_results,
            "cvar": cvar_results,
            "percentiles": {
                "p5": float(np.percentile(returns, 5)),
                "p25": float(np.percentile(returns, 25)),
                "p50": float(np.percentile(returns, 50)),
                "p75": float(np.percentile(returns, 75)),
                "p95": float(np.percentile(returns, 95)),
            },
            "drawdown_distribution": {
                "p5": float(np.percentile(drawdowns, 5)),
                "p50": float(np.percentile(drawdowns, 50)),
                "p95": float(np.percentile(drawdowns, 95)),
            },
        }

    def _calculate_risk_metrics(
        self, returns: list[float]
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Calculate VaR and CVaR for all confidence levels."""
        var_results = {}
        cvar_results = {}

        for conf in self.confidence_levels:
            percentile = (1 - conf) * 100
            var_results[f"VaR_{conf}"] = float(np.percentile(returns, percentile))
            var_threshold = np.percentile(returns, percentile)
            cvar_results[f"CVaR_{conf}"] = float(
                np.mean([r for r in returns if r <= var_threshold])
            )

        return var_results, cvar_results

    def _block_bootstrap(self, returns: np.ndarray, n_periods: int) -> np.ndarray:
        """Perform block bootstrap resampling with reproducible random state."""
        n_blocks = int(np.ceil(n_periods / self.block_size))
        max_start = len(returns) - self.block_size + 1

        # Pre-generate all random indices for reproducibility
        start_indices = self._rng.integers(0, max_start, size=n_blocks)

        # Vectorized block collection
        sampled = np.concatenate([returns[idx : idx + self.block_size] for idx in start_indices])

        return sampled[:n_periods]

    def _calculate_max_drawdown(self, equity: list[float]) -> float:
        """Calculate maximum drawdown from equity curve."""
        peak = equity[0]
        max_dd = 0

        for value in equity[1:]:
            if value > peak:
                peak = value
            dd = (value - peak) / peak
            if dd < max_dd:
                max_dd = dd

        return max_dd


# ============================================================================
# Comprehensive Validator (Facade)
# ============================================================================


class ComprehensiveValidator:
    """
    Facade class that combines all validation methods.

    Provides a single interface for running complete validation suite.
    """

    def __init__(self, config_path: str = "config/validation.yaml"):
        """Initialize comprehensive validator."""
        self.config = load_validation_config(config_path)
        self.config_path = config_path

        self.walk_forward = WalkForwardValidator(config_path=config_path)
        self.cross_validation = CrossValidationTemporal(config_path=config_path)
        self.stress_tester = StressTester(config_path=config_path)
        self.monte_carlo = MonteCarloSimulator(config_path=config_path)

    def run_full_validation(
        self,
        params: FullValidationParams,
    ) -> ValidationReport:
        """
        Run complete validation suite.

        Args:
            params: FullValidationParams with strategy, strategy_name, quotes,
                    signals, backtest_config, start_date, end_date

        Returns:
            Complete ValidationReport
        """
        strategy = params.strategy
        strategy_name = params.strategy_name
        quotes = params.quotes
        signals = params.signals
        backtest_config = params.backtest_config
        start_date = params.start_date
        end_date = params.end_date

        report = ValidationReport(
            strategy_name=strategy_name,
            timestamp=datetime.now(),
        )

        all_passed = True

        # 1. Walk-Forward Validation
        if self.config.get("walk_forward", {}).get("enabled", True):
            logger.info("Running walk-forward validation...")
            report.walk_forward_results = self.walk_forward.validate_strategy(
                WalkForwardValidationParams(
                    quotes=quotes,
                    signals=signals,
                    config=backtest_config,
                    start_date=start_date,
                    end_date=end_date,
                )
            )
            if not report.walk_forward_results.get("passed", False):
                all_passed = False

        # 2. Cross-Validation
        if self.config.get("cross_validation", {}).get("enabled", True):
            logger.info("Running cross-validation...")
            report.cross_validation_results = self.cross_validation.cross_validate(
                CrossValidationParams(
                    quotes=quotes,
                    signals=signals,
                    config=backtest_config,
                    start_date=start_date,
                    end_date=end_date,
                )
            )
            if not report.cross_validation_results.get("passed", False):
                all_passed = False

        # 3. Stress Testing
        if self.config.get("stress_testing", {}).get("enabled", True):
            logger.info("Running stress tests...")
            report.stress_test_results = self.stress_tester.run_stress_tests(
                strategy, backtest_config
            )
            if not report.stress_test_results.get("passed", False):
                all_passed = False

        # 4. Monte Carlo Simulation
        if self.config.get("monte_carlo", {}).get("enabled", True):
            logger.info("Running Monte Carlo simulation...")
            # Extract returns from signals/trades
            returns = self._extract_returns(quotes)
            if returns:
                report.monte_carlo_results = self.monte_carlo.run_simulation(
                    returns,
                    initial_capital=float(backtest_config.initial_capital),
                )

        report.overall_passed = all_passed
        report.summary = {
            "walk_forward_passed": (
                report.walk_forward_results.get("passed") if report.walk_forward_results else None
            ),
            "cross_validation_passed": (
                report.cross_validation_results.get("passed")
                if report.cross_validation_results
                else None
            ),
            "stress_test_passed": (
                report.stress_test_results.get("passed") if report.stress_test_results else None
            ),
            "monte_carlo_completed": report.monte_carlo_results is not None,
            "overall_passed": all_passed,
        }

        return report

    def _extract_returns(self, quotes: list[Quote]) -> list[float]:
        """Extract daily returns from quotes."""
        if len(quotes) < 2:
            return []

        sorted_quotes = sorted(quotes, key=lambda q: q.timestamp)
        returns = []

        for i in range(1, len(sorted_quotes)):
            prev_close = float(sorted_quotes[i - 1].close or sorted_quotes[i - 1].last)
            curr_close = float(sorted_quotes[i].close or sorted_quotes[i].last)
            if prev_close > 0:
                returns.append((curr_close - prev_close) / prev_close)

        return returns

    def save_report(self, report: ValidationReport, output_path: Optional[str] = None) -> str:
        """Save validation report to JSON file."""
        if output_path is None:
            output_dir = Path(
                self.config.get("reporting", {}).get("output_directory", "reports/validation")
            )
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
            output_path = str(output_dir / f"validation_{report.strategy_name}_{timestamp}.json")

        report_dict = {
            "strategy_name": report.strategy_name,
            "timestamp": report.timestamp.isoformat(),
            "overall_passed": report.overall_passed,
            "summary": report.summary,
            "walk_forward_results": report.walk_forward_results,
            "cross_validation_results": report.cross_validation_results,
            "stress_test_results": report.stress_test_results,
            "monte_carlo_results": report.monte_carlo_results,
        }

        with open(output_path, "w") as f:
            json.dump(report_dict, f, indent=2, default=str)

        logger.info(f"Validation report saved to {output_path}")
        return output_path
