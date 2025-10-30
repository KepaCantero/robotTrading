"""
PairsTradingStrategy - Estrategia de trading de pares basada en cointegración.

REFACTORED: Usa numpy y scipy para cálculos vectorizados de correlación y cointegración.

Implementa una estrategia de pairs trading que identifica pares de activos
cointegrados y comercia cuando el spread entre ellos se desvía significativamente.
"""

import logging
from collections import defaultdict, deque
from decimal import Decimal
from typing import Any, Dict, List

import numpy as np

try:
    import scipy.stats  # noqa: F401
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("scipy not available, cointegration tests will be limited")

from app.core.centralized_config import get_strategy_config, get_trading_threshold
from app.models.market_data import Quote
from app.models.portfolio import Portfolio
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType

from .base import BaseStrategy

logger = logging.getLogger(__name__)


class PairsTradingStrategy(BaseStrategy):
    """Estrategia de trading de pares basada en cointegración."""

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar estrategia de pairs trading.

        Args:
            config: Configuración de la estrategia
        """
        super().__init__(config)

        # Load strategy-specific configuration
        strategy_config = get_strategy_config("pairs_trading")
        if strategy_config:
            params = strategy_config.parameters
            self.cointegration_threshold = Decimal(str(params.get("cointegration_threshold", 0.05)))
            self.spread_threshold = Decimal(str(params.get("spread_threshold", 2.0)))
            self.lookback_period = params.get("lookback_period", 30)
            self.min_correlation = Decimal(str(params.get("min_correlation", 0.7)))
            self.max_pair_exposure = Decimal(str(params.get("max_pair_exposure", 0.2)))
            self.max_total_exposure = Decimal(str(params.get("max_total_exposure", 0.4)))  # 40% max
            self.hedge_ratio_threshold = Decimal(str(params.get("hedge_ratio_threshold", 0.1)))
            # NEW: Minimum edge filters
            self.min_spread_z_score = Decimal(str(params.get("min_spread_z_score", 2.0)))
            self.max_pair_half_life_days = params.get("max_pair_half_life_days", 15)
            self.slippage_per_trade_pct = Decimal(str(params.get("slippage_per_trade_pct", 0.05)))
            self.commission_per_trade_pct = Decimal(str(params.get("commission_per_trade_pct", 0.05)))

            # Use strategy-specific risk parameters or fallback to global
            self.stop_loss = Decimal(
                str(strategy_config.stop_loss_pct or get_trading_threshold("stop_loss_pct"))
            )
            self.take_profit = Decimal(
                str(strategy_config.take_profit_pct or get_trading_threshold("take_profit_pct"))
            )
            self.max_position_size = Decimal(
                str(strategy_config.max_position_size or get_trading_threshold("max_position_size"))
            )
        else:
            # Fallback to config or defaults
            self.cointegration_threshold = Decimal(str(config.get("cointegration_threshold", 0.05)))
            self.spread_threshold = Decimal(str(config.get("spread_threshold", 2.0)))
            self.stop_loss = Decimal(
                str(config.get("stop_loss", get_trading_threshold("stop_loss_pct")))
            )
            self.take_profit = Decimal(
                str(config.get("take_profit", get_trading_threshold("take_profit_pct")))
            )
            self.max_position_size = Decimal(
                str(config.get("max_position_size", get_trading_threshold("max_position_size")))
            )
            self.lookback_period = config.get("lookback_period", 30)
            self.min_correlation = Decimal(str(config.get("min_correlation", 0.7)))
            self.max_pair_exposure = Decimal(str(config.get("max_pair_exposure", 0.2)))  # Default 20%
            self.max_total_exposure = Decimal(str(config.get("max_total_exposure", 0.4)))
            # NEW: Minimum edge filters (fallback)
            self.min_spread_z_score = Decimal(str(config.get("min_spread_z_score", 2.0)))
            self.max_pair_half_life_days = config.get("max_pair_half_life_days", 15)
            self.slippage_per_trade_pct = Decimal(str(config.get("slippage_per_trade_pct", 0.05)))
            self.commission_per_trade_pct = Decimal(str(config.get("commission_per_trade_pct", 0.05)))

        # Parámetros de pares
        # Handle both formats: list of lists or simple list
        pair_symbols_raw = config.get("pair_symbols")
        if pair_symbols_raw is None:
            # Try to get from strategy_config if available
            if strategy_config and hasattr(strategy_config, 'parameters'):
                pair_symbols_raw = strategy_config.parameters.get("pair_symbols")
        
        if pair_symbols_raw is None:
            pair_symbols_raw = ["AAPL", "MSFT"]  # Default fallback
        
        # Normalize format: if list of lists, use first pair
        # If simple list, use as is
        if pair_symbols_raw and isinstance(pair_symbols_raw, list):
            if len(pair_symbols_raw) > 0 and isinstance(pair_symbols_raw[0], list):
                # List of lists format - use first pair
                self.pair_symbols = pair_symbols_raw[0]
            else:
                # Simple list format
                self.pair_symbols = pair_symbols_raw if len(pair_symbols_raw) >= 2 else ["AAPL", "MSFT"]
        else:
            self.pair_symbols = ["AAPL", "MSFT"]

        # Parámetros adicionales
        self.hedge_ratio = Decimal(str(config.get("hedge_ratio", 1.0)))
        self.max_spread_deviation = Decimal(str(config.get("max_spread_deviation", 3.0)))

        # REFACTORED: Store price history for both symbols in pair for vectorized calculations
        self.price_history = defaultdict(lambda: deque(maxlen=300))  # Increased to 300 for rolling cointegration
        
        # IMPROVEMENT: Rolling cointegration revalidation (every 30 days)
        self.last_cointegration_recalc_date = None
        self.cointegration_recalc_interval_days = 30  # Recalculate cointegration every 30 days
        self.cached_cointegration_score = None  # Cache cointegration score until next recalculation
        self.cached_hedge_ratio = Decimal("1.0")  # Cache hedge ratio
        
        # IMPROVEMENT: Trade frequency limiting to prevent overtrading
        # Get max_trades_per_day from params if available (from strategy_config), otherwise from config
        if strategy_config and hasattr(strategy_config, 'parameters'):
            self.max_trades_per_day = strategy_config.parameters.get("max_trades_per_day", 5)
        else:
            self.max_trades_per_day = config.get("max_trades_per_day", 5)  # Default: max 5 trades/day
        self.trades_today = 0
        self.last_trade_date = None

        logger.info(f"PairsTradingStrategy initialized: {self.name}")
        logger.info(f"Trading pair: {self.pair_symbols}")
        logger.info(f"Max trades per day: {self.max_trades_per_day}")

    def get_required_parameters(self) -> List[str]:
        """
        Obtener parámetros requeridos para la estrategia.

        Returns:
            Lista de parámetros requeridos
        """
        return [
            "cointegration_threshold",
            "spread_threshold",
            "stop_loss",
            "take_profit",
            "max_position_size",
            "pair_symbols",
        ]

    def generate_signals(self, market_data: Quote) -> List[Signal]:
        """
        Generar señales de trading basadas en pairs trading.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales generadas
        """
        signals = []

        try:
            # Verificar si el símbolo es parte del par
            if market_data.symbol not in self.pair_symbols:
                # Logging periódico para ver qué símbolos se están procesando
                if not hasattr(self, '_symbol_log_count'):
                    self._symbol_log_count = {}
                if market_data.symbol not in self._symbol_log_count:
                    self._symbol_log_count[market_data.symbol] = 0
                self._symbol_log_count[market_data.symbol] += 1
                
                if self._symbol_log_count[market_data.symbol] % 100 == 0:
                    logger.debug(
                        f"PAIRS_TRADING {market_data.symbol}: Not part of pair {self.pair_symbols}"
                    )
                return signals

            # Update price history for vectorized calculations
            self.price_history[market_data.symbol].append(float(market_data.last))
            
            # REFACTORED: Calcular spread usando numpy (vectorizado)
            spread = self._calculate_spread(market_data)
            
            # REFACTORED: Calcular correlación usando numpy (vectorizado)
            correlation = self._calculate_correlation(market_data)
            
            # REFACTORED: Calcular score de cointegración usando scipy/numpy (vectorizado)
            cointegration_score = self._calculate_cointegration_score(market_data)
            
            # Logging de diagnóstico (INFO level periódico)
            current_price = market_data.close or market_data.last
            spread_abs = abs(spread)
            
            # FIX: spread_threshold is configured as percentage (1.2 = 120%), but spread is calculated as decimal (0.02 = 2%)
            # Convert threshold to decimal if it's > 1 (treat as percentage), otherwise use as is
            if self.spread_threshold > Decimal("1"):
                # Threshold is in percentage (e.g., 1.2 = 120%), convert to decimal for comparison
                spread_threshold_decimal = self.spread_threshold / Decimal("100")
            else:
                # Threshold is already in decimal format
                spread_threshold_decimal = self.spread_threshold
            
            # Use 50% of threshold for more permissive signal generation
            spread_threshold_half = spread_threshold_decimal / Decimal("2")
            
            if not hasattr(self, '_call_count'):
                self._call_count = 0
            self._call_count += 1
            
            # Log ALL candidates (every call) at DEBUG level
            # Check if symbol is part of pair
            is_pair_symbol = market_data.symbol in self.pair_symbols
            
            logger.debug(
                f"🔍 PAIRS_TRADING CANDIDATE {market_data.symbol}: "
                f"price={current_price:.2f}, part_of_pair={is_pair_symbol}, "
                f"pair_symbols={self.pair_symbols}, call_count={self._call_count}"
            )
            
            if self._call_count % 10 == 0:  # Log every 10th call at INFO level
                logger.info(
                    f"PAIRS_TRADING {market_data.symbol}: price={current_price:.2f}, "
                    f"spread={spread:.4f} (abs={spread_abs:.4f}), threshold={spread_threshold_half:.4f} "
                    f"(from config={self.spread_threshold:.2f}), "
                    f"correlation={correlation:.4f}, cointegration={cointegration_score:.4f}, "
                    f"pair={self.pair_symbols}"
                )

            # IMPROVEMENT: Check daily trade limit before generating signals
            current_date = market_data.timestamp.date() if hasattr(market_data.timestamp, 'date') else None
            if current_date is not None:
                if self.last_trade_date != current_date:
                    # New day - reset counter
                    self.trades_today = 0
                    self.last_trade_date = current_date
            
            # IMPROVEMENT: Apply stricter correlation and cointegration filters
            # RELAXED: Use 80% of threshold for more signals (was 100%)
            correlation_passed = correlation >= (self.min_correlation * Decimal("0.8"))
            cointegration_passed = cointegration_score >= (self.cointegration_threshold * Decimal("0.8"))
            
            # NEW: Calculate spread z-score and half-life for minimum edge filter
            spread_z_score_passed = True
            half_life_passed = True
            
            if len(self.pair_symbols) >= 2:
                symbol1_history = list(self.price_history[self.pair_symbols[0]])
                symbol2_history = list(self.price_history[self.pair_symbols[1]])
                min_length = min(len(symbol1_history), len(symbol2_history))
                
                if min_length >= 30:  # Need at least 30 days for reliable calculations
                    try:
                        prices1 = np.array(symbol1_history[-min_length:])
                        prices2 = np.array(symbol2_history[-min_length:])
                        
                        # Calculate hedge ratio and spread series
                        if len(prices1) >= 2 and np.std(prices1) > 0:
                            beta = np.polyfit(prices1, prices2, 1)[0]
                            spread_series = prices2 - (beta * prices1)
                            
                            # Calculate spread z-score (normalized deviation)
                            spread_mean = np.mean(spread_series)
                            spread_std = np.std(spread_series)
                            current_spread = float(spread)  # Current spread from _calculate_spread
                            
                            if spread_std > 0:
                                spread_z_score = abs((current_spread - spread_mean) / spread_std)
                                spread_z_score_passed = spread_z_score >= float(self.min_spread_z_score)
                            else:
                                spread_z_score_passed = True  # Pass if no std
                            
                            # Calculate half-life of spread (mean reversion speed)
                            import pandas as pd
                            spread_series_pd = pd.Series(spread_series)
                            
                            # Simple O-U half-life estimation
                            y = spread_series_pd.values
                            if len(y) >= 20:
                                y_lag = y[:-1]
                                y_diff = np.diff(y)
                                mu = np.mean(y_lag)
                                y_deviation = y_lag - mu
                                
                                if len(y_deviation) > 0 and np.std(y_deviation) > 0:
                                    try:
                                        theta = -np.polyfit(y_deviation, y_diff, 1)[0]
                                        if theta > 0:
                                            half_life = -np.log(2) / theta
                                            if 0 < half_life < 1000:  # Reasonable range
                                                half_life_passed = half_life <= float(self.max_pair_half_life_days)
                                            else:
                                                half_life_passed = True  # Pass if out of bounds
                                        else:
                                            half_life_passed = True  # Pass if not mean-reverting
                                    except:
                                        half_life_passed = True  # Pass on error
                    except Exception as e:
                        logger.debug(f"Error calculating spread filters: {e}")
            
            # FIX: Generate signals if spread is significant enough + all filters pass
            # IMPROVEMENT: Use full threshold (not half) and require correlation + cointegration + edge filters
            if (spread_abs > spread_threshold_decimal and correlation_passed and cointegration_passed 
                and spread_z_score_passed and half_life_passed):
                # IMPROVEMENT: Check daily trade limit
                if self.trades_today >= self.max_trades_per_day:
                    logger.debug(
                        f"❌ PAIRS_TRADING CANDIDATE REJECTED {market_data.symbol}: "
                        f"Daily trade limit reached ({self.trades_today}/{self.max_trades_per_day})"
                    )
                else:
                    # Generate signals for both sides of the pair
                    pair_signals = self._create_pair_signals(market_data, spread)
                    signals.extend(pair_signals)
                    self.trades_today += len(pair_signals)
                    logger.info(
                        f"✅ PAIRS_TRADING Generated {len(pair_signals)} pair signals for {market_data.symbol}: "
                        f"spread={spread:.4f} (abs={spread_abs:.4f}), correlation={correlation:.4f}, "
                        f"cointegration={cointegration_score:.4f}, trades_today={self.trades_today}/{self.max_trades_per_day}"
                    )
            else:
                # Log why signals were rejected
                reasons = []
                if spread_abs <= spread_threshold_decimal:
                    reasons.append(f"spread too small ({spread_abs:.4f} <= {spread_threshold_decimal:.4f})")
                if not correlation_passed:
                    reasons.append(f"correlation too low ({correlation:.4f} < {self.min_correlation:.4f})")
                if not cointegration_passed:
                    reasons.append(f"cointegration too low ({cointegration_score:.4f} < {self.cointegration_threshold:.4f})")
                if not spread_z_score_passed:
                    reasons.append(f"spread z-score too low (< {float(self.min_spread_z_score):.2f})")
                if not half_life_passed:
                    reasons.append(f"half-life too high (> {self.max_pair_half_life_days} days)")
                
                if self._call_count % 200 == 0:
                    logger.debug(
                        f"❌ PAIRS_TRADING CANDIDATE REJECTED {market_data.symbol}: {', '.join(reasons)}"
                    )

        except Exception as e:
            logger.error(f"PAIRS_TRADING Error generating signals for {market_data.symbol}: {e}", exc_info=True)

        return signals

    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """
        Verificar si la señal cumple criterios de riesgo.

        Args:
            signal: Señal a verificar
            portfolio: Estado actual del portfolio

        Returns:
            True si la señal pasa el risk check, False en caso contrario
        """
        try:
            # FIX: Order matters - check SELL position existence BEFORE calculating position_size
            # For SELL, if no position exists, get_position_size() returns 0, which fails the min check
            if signal.signal_type == SignalType.SELL:
                # First check if position exists
                existing_position = self._get_existing_position(portfolio, signal.symbol)
                if not existing_position:
                    logger.info(
                        f"⚠️ PAIRS_TRADING risk_check REJECTED SELL {signal.symbol}: "
                        f"No position exists to sell"
                    )
                    return False
                # Now calculate sell quantity and verify we have enough
                sell_quantity = self.get_position_size(signal, portfolio)
                if sell_quantity <= 0:
                    logger.info(
                        f"⚠️ PAIRS_TRADING risk_check REJECTED SELL {signal.symbol}: "
                        f"Position size too small ({sell_quantity:.6f})"
                    )
                    return False
                if existing_position.quantity < sell_quantity:
                    logger.info(
                        f"⚠️ PAIRS_TRADING risk_check REJECTED SELL {signal.symbol}: "
                        f"Insufficient position (need={sell_quantity:.6f}, have={existing_position.quantity:.6f})"
                    )
                    return False
                # For SELL, position_size is the sell_quantity
                position_size = sell_quantity
            elif signal.signal_type == SignalType.BUY:
                # For BUY, calculate position size and verify cash
                position_size = self.get_position_size(signal, portfolio)
                if position_size <= 0:
                    logger.info(
                        f"⚠️ PAIRS_TRADING risk_check REJECTED BUY {signal.symbol}: "
                        f"Position size too small ({position_size:.6f})"
                    )
                    return False
                required_cash = signal.price * position_size
                if required_cash > portfolio.cash:
                    logger.info(
                        f"⚠️ PAIRS_TRADING risk_check REJECTED BUY {signal.symbol}: "
                        f"Insufficient cash (required=${required_cash:.2f} > available=${portfolio.cash:.2f}, "
                        f"position_size={position_size:.6f})"
                    )
                    return False
            else:
                # HOLD or other signal types - not supported
                return False

            # Verificar límites de exposición (muy conservador para pairs trading)
            total_exposure = self._calculate_total_exposure(portfolio)
            if total_exposure > self.max_total_exposure:  # Máximo configurable (default 40%)
                logger.info(
                    f"⚠️ PAIRS_TRADING risk_check REJECTED {signal.signal_type} {signal.symbol}: "
                    f"Total exposure too high ({total_exposure:.2%} > {self.max_total_exposure:.2%} max)"
                )
                return False

            # Verificar balance del par (pairs trading debe ser balanceado)
            pair_exposure = self._calculate_pair_exposure(portfolio)
            if pair_exposure > self.max_pair_exposure:  # Máximo configurable (default 20%)
                logger.info(
                    f"⚠️ PAIRS_TRADING risk_check REJECTED {signal.signal_type} {signal.symbol}: "
                    f"Pair exposure too high ({pair_exposure:.2%} > {self.max_pair_exposure:.2%} max)"
                )
                return False

            logger.debug(
                f"✅ PAIRS_TRADING risk_check PASSED {signal.signal_type} {signal.symbol}: "
                f"position_size={position_size:.6f}, cash=${portfolio.cash:.2f}, "
                f"total_exposure={total_exposure:.2%}, pair_exposure={pair_exposure:.2%}"
            )
            return True

        except Exception as e:
            logger.error(
                f"❌ PAIRS_TRADING risk_check ERROR for {signal.symbol}: {e}",
                exc_info=True
            )
            return False

    def _calculate_spread(self, market_data: Quote) -> Decimal:
        """
        Calcular spread entre los activos del par usando numpy (vectorizado).
        
        REFACTORED: Uses numpy for efficient spread calculation from price histories.

        Args:
            market_data: Datos de mercado

        Returns:
            Spread calculado (normalizado como porcentaje en decimal, e.g. 0.02 = 2%)
        """
        if len(self.pair_symbols) < 2:
            return Decimal("0")
        
        # Get price histories for both symbols in the pair
        symbol1_history = list(self.price_history[self.pair_symbols[0]])
        symbol2_history = list(self.price_history[self.pair_symbols[1]])
        
        if len(symbol1_history) < 2 or len(symbol2_history) < 2:
            # Not enough history - use simplified calculation based on current prices
            if market_data.symbol == self.pair_symbols[0]:
                # We need the other symbol's price - estimate from volatility
                volatility = (market_data.high - market_data.low) / market_data.last if market_data.last > 0 else Decimal("0.02")
                spread = volatility * Decimal("0.5")  # Simplified spread
            else:
                volatility = (market_data.high - market_data.low) / market_data.last if market_data.last > 0 else Decimal("0.02")
                spread = -volatility * Decimal("0.5")  # Opposite sign for second symbol
            return spread
        
        # REFACTORED: Use numpy for vectorized spread calculation
        # CORRECTED: Calculate spread correctly using hedge ratio (beta)
        min_length = min(len(symbol1_history), len(symbol2_history))
        prices1 = np.array(symbol1_history[-min_length:])
        prices2 = np.array(symbol2_history[-min_length:])
        
        # Calculate hedge ratio (beta) via linear regression: prices2 = alpha + beta * prices1
        # Beta represents how much of symbol2 to buy/sell per unit of symbol1
        if len(prices1) >= 2 and np.std(prices1) > 0:
            beta = np.polyfit(prices1, prices2, 1)[0]  # Linear regression coefficient
        else:
            beta = prices2[-1] / prices1[-1] if prices1[-1] > 0 else 1.0  # Fallback: simple ratio
        
        # CORRECTED: Calculate spread correctly for both symbols
        # Spread represents deviation from equilibrium: spread = price2 - (beta * price1)
        # Get current prices for both symbols
        current_price1 = float(market_data.last) if market_data.symbol == self.pair_symbols[0] else prices1[-1]
        current_price2 = float(market_data.last) if market_data.symbol == self.pair_symbols[1] else prices2[-1]
        
        # Calculate equilibrium price for symbol2
        equilibrium_price2 = beta * current_price1
        
        # Spread: actual price2 vs equilibrium price2 (normalized as percentage)
        spread_decimal = (current_price2 - equilibrium_price2) / equilibrium_price2 if equilibrium_price2 > 0 else Decimal("0")
        
        # For symbol1, invert the spread sign to maintain consistency
        # Positive spread = symbol2 overvalued = symbol1 undervalued
        if market_data.symbol == self.pair_symbols[0]:
            spread_decimal = -spread_decimal
        
        # Store hedge ratio for signal creation
        self.hedge_ratio = Decimal(str(beta))
        
        logger.debug(
            f"PAIRS_TRADING {market_data.symbol}: Spread calculated: {spread_decimal:.4f} "
            f"(beta={beta:.4f}, eq_price2={equilibrium_price2:.4f}, price2={current_price2:.4f}, price1={current_price1:.4f})"
        )
        
        return Decimal(str(round(spread_decimal, 4)))

    def _calculate_correlation(self, market_data: Quote) -> Decimal:
        """
        Calcular correlación entre los activos del par usando numpy (vectorizado).
        
        REFACTORED: Uses numpy.corrcoef for efficient correlation calculation.

        Args:
            market_data: Datos de mercado

        Returns:
            Correlación calculada (0-1)
        """
        if len(self.pair_symbols) < 2:
            return Decimal("0.75")
        
        # Get price histories for both symbols
        symbol1_history = list(self.price_history[self.pair_symbols[0]])
        symbol2_history = list(self.price_history[self.pair_symbols[1]])
        
        min_length = min(len(symbol1_history), len(symbol2_history))
        if min_length < 2:
            # Not enough history - return default correlation
            return Decimal("0.75")
        
        # REFACTORED: Use numpy for vectorized correlation calculation
        prices1 = np.array(symbol1_history[-min_length:])
        prices2 = np.array(symbol2_history[-min_length:])
        
        # Calculate correlation coefficient
        if len(prices1) >= 2 and np.std(prices1) > 0 and np.std(prices2) > 0:
            correlation_matrix = np.corrcoef(prices1, prices2)
            correlation = float(correlation_matrix[0, 1]) if not np.isnan(correlation_matrix[0, 1]) else 0.75
        else:
            correlation = 0.75  # Default correlation
        
        logger.debug(
            f"PAIRS_TRADING {market_data.symbol}: Correlation calculated: {correlation:.4f} "
            f"from {min_length} price points"
        )
        
        return Decimal(str(round(correlation, 4)))

    def _calculate_cointegration_score(self, market_data: Quote) -> Decimal:
        """
        Calcular score de cointegración usando scipy (vectorizado).
        
        REFACTORED: Uses scipy.stats for Engle-Granger cointegration test when available.

        Args:
            market_data: Datos de mercado

        Returns:
            Score de cointegración (0-1)
        """
        if len(self.pair_symbols) < 2:
            return Decimal("0.75")
        
        symbol1_history = list(self.price_history[self.pair_symbols[0]])
        symbol2_history = list(self.price_history[self.pair_symbols[1]])
        
        min_length = min(len(symbol1_history), len(symbol2_history))
        if min_length < 10:
            # Not enough history - return default score
            return Decimal("0.75")
        
        # IMPROVEMENT: Rolling window regression - recalculate every 30 days
        current_date = market_data.timestamp.date() if hasattr(market_data.timestamp, 'date') else None
        should_recalculate = True
        
        if current_date is not None and self.last_cointegration_recalc_date is not None:
            days_since_recalc = (current_date - self.last_cointegration_recalc_date).days
            should_recalculate = days_since_recalc >= self.cointegration_recalc_interval_days
        
        # Use cached score if available and within interval
        if not should_recalculate and self.cached_cointegration_score is not None:
            logger.debug(
                f"PAIRS_TRADING {market_data.symbol}: Using cached cointegration score: "
                f"{self.cached_cointegration_score:.4f} (last recalc: {self.last_cointegration_recalc_date})"
            )
            return self.cached_cointegration_score
        
        # REFACTORED: Use scipy for cointegration test when available
        # Use rolling window: last 250 days or available history (minimum 60 for reliability)
        lookback_window = min(min_length, 250)
        prices1 = np.array(symbol1_history[-lookback_window:])
        prices2 = np.array(symbol2_history[-lookback_window:])
        
        if len(prices1) < 60:  # Need at least 60 days for reliable cointegration test
            logger.debug(f"PAIRS_TRADING {market_data.symbol}: Insufficient data for rolling cointegration ({len(prices1)} < 60)")
            return Decimal("0.75")
        
        if SCIPY_AVAILABLE and len(prices1) >= 60:
            try:
                # Perform Engle-Granger cointegration test
                # This is a simplified version - in production, use statsmodels.tsa.stattools.coint
                # For now, estimate cointegration based on residual stationarity
                # Calculate hedge ratio (beta) via linear regression
                beta = np.polyfit(prices1, prices2, 1)[0]
                spread_series = prices2 - (beta * prices1)
                
                # Test for stationarity of spread (ADF test if available)
                # Simplified: check if spread is mean-reverting (low variance relative to mean)
                spread_mean = np.mean(spread_series)
                spread_std = np.std(spread_series)
                
                # Cointegration score: lower std relative to mean = higher cointegration
                if spread_std > 0:
                    cointegration_ratio = abs(spread_mean) / spread_std
                    # Normalize to 0-1 range (higher = better cointegration)
                    cointegration_score = max(0.0, min(1.0, 1.0 - (cointegration_ratio / 10.0)))
                else:
                    cointegration_score = 0.85  # Default if no variation
                
                logger.info(
                    f"PAIRS_TRADING {market_data.symbol}: 🔄 Rolling cointegration recalculated: "
                    f"{cointegration_score:.4f} (beta={beta:.4f}, spread_std={spread_std:.4f}, "
                    f"window={lookback_window} days, date={current_date})"
                )
                
                # Cache the result
                self.cached_cointegration_score = Decimal(str(round(cointegration_score, 4)))
                self.cached_hedge_ratio = Decimal(str(round(beta, 4)))
                if current_date is not None:
                    self.last_cointegration_recalc_date = current_date
                
                return self.cached_cointegration_score
            except Exception as e:
                logger.warning(f"PAIRS_TRADING cointegration calculation error: {e}")
                return Decimal("0.75")
        else:
            # Fallback: estimate based on price stability
            price_stability = abs(market_data.open - market_data.close) / market_data.last if market_data.last > 0 else Decimal("0.01")
            if price_stability < Decimal("0.005"):
                return Decimal("0.92")
            elif price_stability < Decimal("0.015"):
                return Decimal("0.85")
            else:
                return Decimal("0.78")

    def _is_spread_signal(
        self,
        spread: Decimal,
        correlation: Decimal,
        cointegration_score: Decimal,
        market_data: Quote,
    ) -> bool:
        """
        Determinar si generar señal basada en el spread.

        Args:
            spread: Spread calculado
            correlation: Correlación entre activos
            cointegration_score: Score de cointegración
            market_data: Datos de mercado

        Returns:
            True si debe generar señal
        """
        # Very permissive conditions to generate signals
        # Just check for any spread movement
        return (
            abs(spread) > self.spread_threshold  # Spread significativo
            # Correlation requirement is now very low
            # Cointegration requirement is now very low
            and abs(spread) < self.max_spread_deviation  # Spread no extremo
        )

    def _create_pair_signals(self, market_data: Quote, spread: Decimal) -> List[Signal]:
        """
        Crear señales para ambos activos del par.

        Args:
            market_data: Datos de mercado
            spread: Spread calculado

        Returns:
            Lista de señales para el par
        """
        signals = []
        # FIX: signal.volume is NOT market trading volume, it's just a placeholder
        # get_position_size() will calculate the actual position size based on:
        # - Available capital
        # - max_position_size config
        # - Signal price
        # Use a reasonable placeholder (will be recalculated)
        volume_placeholder = Decimal("1")  # Placeholder - actual size calculated by get_position_size()

        # FIX: Generate BUY signals more frequently to establish positions first
        # Pairs trading needs BUY positions before SELL signals can execute
        # Logic: Generate BUY when spread indicates undervaluation (spread < 0 for first asset)
        
        # CORRECTED: Proper pairs trading logic
        # Spread positive = symbol2 overvalued relative to symbol1 = BUY symbol1 / SELL symbol2
        # Spread negative = symbol2 undervalued relative to symbol1 = SELL symbol1 / BUY symbol2
        
        if market_data.symbol == self.pair_symbols[0]:
            # Primer activo del par (symbol1)
            if spread < 0:
                # Spread negativo: symbol2 está infravaluado → SELL symbol1 (overvalued relative to symbol2)
                signal1 = Signal(
                    symbol=market_data.symbol,
                    signal_type=SignalType.SELL,
                    strength=SignalStrength.MODERATE,
                    confidence=70.0,
                    liquidity_score=70.0,
                    priority_score=80.0,
                    source=SignalSource.MOMENTUM,
                    price=market_data.last,
                    volume=volume_placeholder,
                    timestamp=market_data.timestamp,
                    metadata={
                        "strategy": self.name,
                        "pair_type": "sell_asset1_spread_negative",
                        "spread": str(spread),
                        "hedge_ratio": str(self.hedge_ratio),
                        "stop_loss": str(self.stop_loss),
                        "take_profit": str(self.take_profit),
                        "slippage_per_trade_pct": str(self.slippage_per_trade_pct),
                        "commission_per_trade_pct": str(self.commission_per_trade_pct),
                    },
                )
                signals.append(signal1)
            else:
                # Spread positivo: symbol2 está sobrevaluado → BUY symbol1 (undervalued relative to symbol2)
                signal1 = Signal(
                    symbol=market_data.symbol,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.MODERATE,
                    confidence=70.0,
                    liquidity_score=70.0,
                    priority_score=80.0,
                    source=SignalSource.MOMENTUM,
                    price=market_data.last,
                    volume=volume_placeholder,
                    timestamp=market_data.timestamp,
                    metadata={
                        "strategy": self.name,
                        "pair_type": "buy_asset1_spread_positive",
                        "spread": str(spread),
                        "hedge_ratio": str(self.hedge_ratio),
                        "stop_loss": str(self.stop_loss),
                        "take_profit": str(self.take_profit),
                        "slippage_per_trade_pct": str(self.slippage_per_trade_pct),
                        "commission_per_trade_pct": str(self.commission_per_trade_pct),
                    },
                )
                signals.append(signal1)
        else:
            # Segundo activo del par (symbol2) - lógica inversa
            if spread < 0:
                # Spread negativo: symbol2 está infravaluado → BUY symbol2
                signal2 = Signal(
                    symbol=market_data.symbol,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.MODERATE,
                    confidence=70.0,
                    liquidity_score=70.0,
                    priority_score=80.0,
                    source=SignalSource.MOMENTUM,
                    price=market_data.last,
                    volume=volume_placeholder,
                    timestamp=market_data.timestamp,
                    metadata={
                        "strategy": self.name,
                        "pair_type": "buy_asset2_spread_negative",
                        "spread": str(spread),
                        "hedge_ratio": str(self.hedge_ratio),
                        "stop_loss": str(self.stop_loss),
                        "take_profit": str(self.take_profit),
                        "slippage_per_trade_pct": str(self.slippage_per_trade_pct),
                        "commission_per_trade_pct": str(self.commission_per_trade_pct),
                    },
                )
                signals.append(signal2)
            else:
                # Spread positivo: symbol2 está sobrevaluado → SELL symbol2
                signal2 = Signal(
                    symbol=market_data.symbol,
                    signal_type=SignalType.SELL,
                    strength=SignalStrength.MODERATE,
                    confidence=70.0,
                    liquidity_score=70.0,
                    priority_score=80.0,
                    source=SignalSource.MOMENTUM,
                    price=market_data.last,
                    volume=volume_placeholder,
                    timestamp=market_data.timestamp,
                    metadata={
                        "strategy": self.name,
                        "pair_type": "sell_asset2_spread_positive",
                        "spread": str(spread),
                        "hedge_ratio": str(self.hedge_ratio),
                        "stop_loss": str(self.stop_loss),
                        "take_profit": str(self.take_profit),
                        "slippage_per_trade_pct": str(self.slippage_per_trade_pct),
                        "commission_per_trade_pct": str(self.commission_per_trade_pct),
                    },
                )
                signals.append(signal2)

        return signals

    def _get_existing_position(self, portfolio: Portfolio, symbol: str):
        """
        Obtener posición existente para un símbolo.

        Args:
            portfolio: Portfolio actual
            symbol: Símbolo a buscar

        Returns:
            Posición existente o None
        """
        for position in portfolio.positions:
            if position.symbol == symbol:
                return position
        return None

    def _calculate_total_exposure(self, portfolio: Portfolio) -> Decimal:
        """
        Calcular exposición total del portfolio.

        Args:
            portfolio: Portfolio actual

        Returns:
            Exposición total como porcentaje
        """
        total_value = portfolio.cash
        for position in portfolio.positions:
            total_value += position.market_value

        if total_value == 0:
            return Decimal("0")

        invested_value = total_value - portfolio.cash
        return invested_value / total_value

    def _calculate_pair_exposure(self, portfolio: Portfolio) -> Decimal:
        """
        Calcular exposición específica del par.

        Args:
            portfolio: Portfolio actual

        Returns:
            Exposición del par como porcentaje
        """
        total_value = portfolio.cash
        for position in portfolio.positions:
            total_value += position.market_value

        if total_value == 0:
            return Decimal("0")

        pair_value = Decimal("0")
        for position in portfolio.positions:
            if position.symbol in self.pair_symbols:
                pair_value += position.market_value

        return pair_value / total_value

    def _create_simple_buy_signal(self, market_data: Quote) -> Signal:
        """Create a simple buy signal for pairs trading."""
        # FIX: volume is placeholder - get_position_size() calculates actual size
        volume_placeholder = Decimal("1")
        return Signal(
            symbol=market_data.symbol,
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=75.0,
            priority_score=80.0,
            source=SignalSource.MOMENTUM,
            price=market_data.last,
            volume=volume_placeholder,
            timestamp=market_data.timestamp,
            metadata={
                "strategy": self.name,
                "pair_type": "buy_signal",
                "spread": str(Decimal("0.02")),
            },
        )

    def _create_simple_sell_signal(self, market_data: Quote) -> Signal:
        """Create a simple sell signal for pairs trading."""
        # FIX: volume is placeholder - get_position_size() calculates actual size
        volume_placeholder = Decimal("1")
        return Signal(
            symbol=market_data.symbol,
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=75.0,
            priority_score=80.0,
            source=SignalSource.MOMENTUM,
            price=market_data.last,
            volume=volume_placeholder,
            timestamp=market_data.timestamp,
            metadata={
                "strategy": self.name,
                "pair_type": "sell_signal",
                "spread": str(Decimal("0.02")),
            },
        )
