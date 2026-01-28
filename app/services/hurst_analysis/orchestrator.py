"""
Hurst Exponent Analyzer - Main Orchestrator.

This module implements the main orchestrator that coordinates all components
for Hurst exponent analysis. It follows SOLID principles:

- Single Responsibility: Only orchestrates, doesn't implement business logic
- Open/Closed: Extensible through dependency injection
- Liskov Substitution: Any calculator/classifier/recommender can be substituted
- Interface Segregation: Depends only on needed protocols
- Dependency Inversion: Depends on abstractions, not concrete implementations
"""

import logging
from datetime import datetime

import pandas as pd

from app.services.hurst_analysis import utils
from app.services.hurst_analysis.models import HurstResult, RegimeChange
from app.services.hurst_analysis.protocols import (
    ChangeDetectorProtocol,
    ConfidenceCalculatorProtocol,
    HistoricalTrackerProtocol,
    HurstCalculator,
    RegimeClassifierProtocol,
    StrategyRecommenderProtocol,
)

logger = logging.getLogger(__name__)


class HurstExponentAnalyzer:
    """
    Main orchestrator for Hurst exponent analysis.

    Coordinates all components through dependency injection.
    Follows the Dependency Inversion Principle - depends on abstractions
    (protocols) rather than concrete implementations.

    Example:
        >>> analyzer = create_default_analyzer()
        >>> result = analyzer.analyze(price_series, symbol="AAPL")
        >>> print(f"Hurst: {result.hurst_exponent:.3f}")
    """

    def __init__(
        self,
        calculator: HurstCalculator,
        classifier: RegimeClassifierProtocol,
        recommender: StrategyRecommenderProtocol,
        confidence_calc: ConfidenceCalculatorProtocol,
        historian: HistoricalTrackerProtocol,
        change_detector: ChangeDetectorProtocol,
        use_returns: bool = True,
    ) -> None:
        """
        Initialize Hurst exponent analyzer with all dependencies.

        Uses dependency injection for all components following DIP.
        """
        self.calculator = calculator
        self.classifier = classifier
        self.recommender = recommender
        self.confidence_calc = confidence_calc
        self.historian = historian
        self.change_detector = change_detector
        self.use_returns = use_returns

    def analyze(
        self,
        series: pd.Series | list[float] | object,
        symbol: str | None = None,
        timestamp: datetime | None = None,
    ) -> HurstResult:
        """
        Analyze a time series and calculate Hurst Exponent.

        Main entry point that orchestrates all components.
        """
        series_array = utils.to_numpy_array(series)
        series_clean = utils.clean_and_validate_series(series_array)

        if series_clean is None:
            return utils.create_default_result("unknown")

        if self.use_returns:
            analysis_series = utils.calculate_log_returns(series_clean)
            if analysis_series is None or len(analysis_series) < 10:
                logger.warning("Failed to calculate log returns, using original")
                analysis_series = series_clean
        else:
            analysis_series = series_clean

        try:
            hurst, rs_values, window_sizes = self.calculator.calculate(analysis_series)
            method_name = self.calculator.__class__.__name__
        except Exception as e:
            logger.error(f"Error calculating Hurst: {e}")
            return utils.create_default_result("unknown")

        regime = self.classifier.classify(hurst)
        strategy = self.recommender.recommend(regime, hurst)
        confidence = self.confidence_calc.calculate_confidence(analysis_series, hurst)

        result = HurstResult(
            hurst_exponent=float(hurst),
            regime=regime,
            strategy=strategy,
            confidence=confidence,
            method=method_name,
            rs_values=rs_values,
            window_sizes=window_sizes,
        )

        if symbol and timestamp:
            self.historian.store(symbol, timestamp, hurst)

        logger.info(
            f"Hurst analysis complete: H={hurst:.4f}, "
            f"regime={regime.value}, strategy={strategy.value}, "
            f"confidence={confidence:.2f}"
        )

        return result

    def detect_regime_change(self, symbol: str, lookback_periods: int = 10) -> RegimeChange | None:
        """Detect regime change for a symbol."""
        return self.change_detector.detect_change(
            symbol, self.historian.get_history, lookback_periods
        )

    def monitor_multiple_symbols(
        self, data: dict[str, object], detect_changes: bool = True
    ) -> dict[str, HurstResult]:
        """Analyze Hurst exponent for multiple symbols."""
        results = {}
        timestamp = datetime.now()

        for symbol, series in data.items():
            try:
                result = self.analyze(series, symbol=symbol, timestamp=timestamp)
                results[symbol] = result

                if detect_changes:
                    change = self.detect_regime_change(symbol)
                    if change:
                        logger.info(f"Regime change for {symbol}: {change}")

            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                continue

        return results

    def get_historical_hurst(self, symbol: str) -> list[tuple[datetime, float]]:
        """Get historical Hurst values for a symbol."""
        return self.historian.get_history(symbol)
