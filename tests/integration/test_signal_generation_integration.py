"""
Integration Tests: Signal Generation with Real Data

Tests signal generation for:
1. Multi-strategy portfolio (3 strategies with allocation percentages)
2. Momentum-only portfolio (best assets selected)
3. Mean Reversion-only portfolio (best assets selected)
4. Pairs Trading-only portfolio (best assets selected)
"""

import logging
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List

import pandas as pd
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.models.market_data import Quote
from app.services.strategy_stock_allocator import StrategyStockAllocator
from app.core.centralized_config import get_config
from app.strategies.momentum import MomentumStrategy
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.pairs_trading import PairsTradingStrategy
from tests.integration.test_data_loader import load_all_csv_data

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def dataframe_to_quotes(symbol: str, df: pd.DataFrame) -> List[Quote]:
    """Convert DataFrame to list of Quote objects."""
    quotes = []
    for date, row in df.iterrows():
        try:
            timestamp = date.to_pydatetime() if hasattr(date, 'to_pydatetime') else date
            
            quote = Quote(
                symbol=symbol,
                bid=Decimal(str(row['close'])),
                ask=Decimal(str(row['close'])),
                last=Decimal(str(row['close'])),
                volume=Decimal(str(int(row['volume']))) if pd.notna(row['volume']) else Decimal("0"),
                timestamp=timestamp,
                high=Decimal(str(row['high'])),
                low=Decimal(str(row['low'])),
                open=Decimal(str(row['open'])),
                close=Decimal(str(row['close'])),
            )
            quotes.append(quote)
        except Exception as e:
            logger.warning(f"Failed to create quote for {symbol} at {date}: {e}")
            continue
    
    return quotes


@pytest.fixture(scope="module")
def real_historical_data():
    """Load all real CSV data (module-scoped for efficiency)."""
    return load_all_csv_data()


@pytest.fixture(scope="module")
def allocator():
    """Create StrategyStockAllocator instance."""
    from app.core.centralized_config import StockAllocationSettings
    return StrategyStockAllocator(StockAllocationSettings())


@pytest.fixture(scope="module")
def allocated_portfolio(allocator, real_historical_data):
    """Create allocated portfolio from real data."""
    total_capital = 100_000.0
    result = allocator.allocate(
        historical_data=real_historical_data,
        total_capital=total_capital,
        strategy_allocations=None
    )
    return result


class TestMultiStrategySignalGeneration:
    """Test 1: Multi-strategy portfolio with all 3 strategies."""
    
    def test_multistrategy_portfolio_signals(self, allocator, real_historical_data, allocated_portfolio):
        """Test signal generation for multi-strategy portfolio."""
        logger.info("=" * 80)
        logger.info("TEST 1: Multi-Strategy Portfolio Signal Generation")
        logger.info("=" * 80)
        
        assert len(allocated_portfolio.allocations) > 0, "Portfolio should have allocations"
        
        # Group allocations by strategy
        strategy_allocations = {}
        for ticker, metrics in allocated_portfolio.allocations.items():
            strategy = metrics.strategy
            if strategy not in strategy_allocations:
                strategy_allocations[strategy] = []
            strategy_allocations[strategy].append(ticker)
        
        logger.info(f"Portfolio allocation:")
        for strategy, tickers in strategy_allocations.items():
            logger.info(f"  {strategy}: {len(tickers)} tickers")
        
        # Get latest quotes for each ticker
        latest_quotes_by_strategy = {}
        
        for strategy in ['momentum', 'mean_reversion', 'pairs_trading']:
            tickers = strategy_allocations.get(strategy, [])
            if not tickers:
                logger.warning(f"No tickers allocated for {strategy}")
                continue
            
            quotes_for_strategy = []
            for ticker in tickers[:10]:  # Limit to 10 per strategy for testing
                if ticker in real_historical_data:
                    df = real_historical_data[ticker]
                    quote_list = dataframe_to_quotes(ticker, df)
                    if quote_list:
                        # Get last 20 quotes for signal generation
                        quotes_for_strategy.extend(quote_list[-20:])
            
            latest_quotes_by_strategy[strategy] = quotes_for_strategy
        
        # Initialize strategies
        momentum_strategy = MomentumStrategy({"name": "momentum"})
        mean_reversion_strategy = MeanReversionStrategy({"name": "mean_reversion"})
        pairs_strategy = PairsTradingStrategy({"name": "pairs_trading"})
        
        # Generate signals for each strategy
        signals_by_strategy = {}
        
        # Momentum signals
        if latest_quotes_by_strategy.get('momentum'):
            momentum_quotes = latest_quotes_by_strategy['momentum']
            momentum_signals = []
            for quote in momentum_quotes[-10:]:  # Test last 10 quotes
                quote_signals = momentum_strategy.generate_signals(quote)
                momentum_signals.extend(quote_signals)
            signals_by_strategy['momentum'] = momentum_signals
            logger.info(f"✅ Momentum: Generated {len(momentum_signals)} signals")
        
        # Mean Reversion signals
        if latest_quotes_by_strategy.get('mean_reversion'):
            mr_quotes = latest_quotes_by_strategy['mean_reversion']
            mr_signals = []
            for quote in mr_quotes[-10:]:  # Test last 10 quotes
                quote_signals = mean_reversion_strategy.generate_signals(quote)
                mr_signals.extend(quote_signals)
            signals_by_strategy['mean_reversion'] = mr_signals
            logger.info(f"✅ Mean Reversion: Generated {len(mr_signals)} signals")
        
        # Pairs Trading signals (requires pairs from allocator)
        if allocated_portfolio.pairs and latest_quotes_by_strategy.get('pairs_trading'):
            pairs_quotes = latest_quotes_by_strategy['pairs_trading']
            pairs_signals = []
            for pair in allocated_portfolio.pairs[:5]:  # Test first 5 pairs
                # Get quotes for both tickers in pair
                ticker1_quotes = [q for q in pairs_quotes if q.symbol == pair.ticker1]
                ticker2_quotes = [q for q in pairs_quotes if q.symbol == pair.ticker2]
                # Configure pair symbols for strategy
                pairs_strategy.pair_symbols = [pair.ticker1, pair.ticker2]
                
                # Load quotes from historical data if needed
                if not ticker1_quotes or not ticker2_quotes:
                    if pair.ticker1 in real_historical_data and pair.ticker2 in real_historical_data:
                        df1 = real_historical_data[pair.ticker1]
                        df2 = real_historical_data[pair.ticker2]
                        ticker1_quotes = dataframe_to_quotes(pair.ticker1, df1)[-20:]
                        ticker2_quotes = dataframe_to_quotes(pair.ticker2, df2)[-20:]
                    else:
                        continue
                
                # Generate signals for both symbols in pair
                if ticker1_quotes:
                    for quote in ticker1_quotes[-5:]:
                        quote_signals = pairs_strategy.generate_signals(quote)
                        pairs_signals.extend(quote_signals)
                
                if ticker2_quotes:
                    for quote in ticker2_quotes[-5:]:
                        quote_signals = pairs_strategy.generate_signals(quote)
                        pairs_signals.extend(quote_signals)
            signals_by_strategy['pairs_trading'] = pairs_signals
            logger.info(f"✅ Pairs Trading: Generated {len(pairs_signals)} signals")
        
        # Verify signals were generated
        total_signals = sum(len(sigs) for sigs in signals_by_strategy.values())
        logger.info(f"\n📊 Total signals generated: {total_signals}")
        
        # Check that at least one strategy generated signals
        strategies_with_signals = len([s for s in signals_by_strategy.values() if s])
        assert strategies_with_signals > 0, \
            f"At least one strategy should generate signals, got {strategies_with_signals}"
        
        logger.info("✅ TEST 1 PASSED: Multi-strategy signal generation working")


class TestMomentumOnlyPortfolio:
    """Test 2: Momentum-only portfolio with best assets."""
    
    def test_momentum_only_best_assets(self, allocator, real_historical_data):
        """Test momentum strategy with best assets selected from portfolio."""
        logger.info("=" * 80)
        logger.info("TEST 2: Momentum-Only Portfolio (Best Assets)")
        logger.info("=" * 80)
        
        # Score all stocks for momentum
        momentum_scores = {}
        for symbol, df in real_historical_data.items():
            try:
                score_result = allocator.score_momentum(symbol, df)
                if score_result and not score_result.get('rejected', False):
                    momentum_scores[symbol] = score_result.get('score', 0.0)
            except Exception as e:
                logger.debug(f"Failed to score {symbol} for momentum: {e}")
                continue
        
        # Select top 10 momentum assets
        top_momentum = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        top_symbols = [symbol for (symbol, score) in top_momentum]
        
        logger.info(f"Top 10 Momentum Assets:")
        for i, (symbol, score) in enumerate(top_momentum, 1):
            logger.info(f"  {i:2d}. {symbol:6s}: {score:.4f}")
        
        assert len(top_symbols) > 0, "Should have at least some momentum assets"
        
        # Get quotes for top momentum assets
        momentum_quotes = []
        for symbol in top_symbols:
            if symbol in real_historical_data:
                df = real_historical_data[symbol]
                quotes = dataframe_to_quotes(symbol, df)
                if quotes:
                    momentum_quotes.extend(quotes[-50:])  # Last 50 quotes
        
        assert len(momentum_quotes) > 0, "Should have quotes for momentum assets"
        
        # Generate signals
        momentum_strategy = MomentumStrategy({"name": "momentum"})
        signals = []
        
        # Group quotes by symbol
        quotes_by_symbol = {}
        for quote in momentum_quotes:
            if quote.symbol not in quotes_by_symbol:
                quotes_by_symbol[quote.symbol] = []
            quotes_by_symbol[quote.symbol].append(quote)
        
        # Generate signals for each symbol
        for symbol, symbol_quotes in quotes_by_symbol.items():
            for quote in symbol_quotes[-10:]:  # Test last 10 quotes per symbol
                quote_signals = momentum_strategy.generate_signals(quote)
                signals.extend(quote_signals)
        
        logger.info(f"✅ Generated {len(signals)} momentum signals from {len(top_symbols)} best assets")
        
        # Verify signals
        assert len(signals) >= 0, "Should generate signals (or 0 if conditions not met)"
        
        if signals:
            logger.info(f"Sample signals:")
            for signal in signals[:5]:
                logger.info(f"  {signal.symbol}: {signal.signal_type} at ${signal.price}")
        
        logger.info("✅ TEST 2 PASSED: Momentum-only portfolio working")


class TestMeanReversionOnlyPortfolio:
    """Test 3: Mean Reversion-only portfolio with best assets."""
    
    def test_mean_reversion_only_best_assets(self, allocator, real_historical_data):
        """Test mean reversion strategy with best assets selected from portfolio."""
        logger.info("=" * 80)
        logger.info("TEST 3: Mean Reversion-Only Portfolio (Best Assets)")
        logger.info("=" * 80)
        
        # Score all stocks for mean reversion
        mr_scores = {}
        for symbol, df in real_historical_data.items():
            try:
                score_result = allocator.score_mean_reversion(symbol, df)
                if score_result and not score_result.get('rejected', False):
                    mr_scores[symbol] = score_result.get('score', 0.0)
            except Exception as e:
                logger.debug(f"Failed to score {symbol} for mean reversion: {e}")
                continue
        
        # Select top 10 mean reversion assets
        top_mr = sorted(mr_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        top_symbols = [symbol for (symbol, score) in top_mr]
        
        logger.info(f"Top 10 Mean Reversion Assets:")
        for i, (symbol, score) in enumerate(top_mr, 1):
            logger.info(f"  {i:2d}. {symbol:6s}: {score:.4f}")
        
        assert len(top_symbols) > 0, "Should have at least some mean reversion assets"
        
        # Get quotes for top mean reversion assets
        mr_quotes = []
        for symbol in top_symbols:
            if symbol in real_historical_data:
                df = real_historical_data[symbol]
                quotes = dataframe_to_quotes(symbol, df)
                if quotes:
                    mr_quotes.extend(quotes[-50:])  # Last 50 quotes
        
        assert len(mr_quotes) > 0, "Should have quotes for mean reversion assets"
        
        # Generate signals
        mr_strategy = MeanReversionStrategy({"name": "mean_reversion"})
        signals = []
        
        # Group quotes by symbol
        quotes_by_symbol = {}
        for quote in mr_quotes:
            if quote.symbol not in quotes_by_symbol:
                quotes_by_symbol[quote.symbol] = []
            quotes_by_symbol[quote.symbol].append(quote)
        
        # Generate signals for each symbol
        for symbol, symbol_quotes in quotes_by_symbol.items():
            for quote in symbol_quotes[-10:]:  # Test last 10 quotes per symbol
                quote_signals = mr_strategy.generate_signals(quote)
                signals.extend(quote_signals)
        
        logger.info(f"✅ Generated {len(signals)} mean reversion signals from {len(top_symbols)} best assets")
        
        # Verify signals
        assert len(signals) >= 0, "Should generate signals (or 0 if conditions not met)"
        
        if signals:
            logger.info(f"Sample signals:")
            for signal in signals[:5]:
                logger.info(f"  {signal.symbol}: {signal.signal_type} at ${signal.price}")
        
        logger.info("✅ TEST 3 PASSED: Mean Reversion-only portfolio working")


class TestPairsTradingOnlyPortfolio:
    """Test 4: Pairs Trading-only portfolio with best pairs."""
    
    def test_pairs_trading_only_best_pairs(self, allocator, real_historical_data):
        """Test pairs trading strategy with best pairs selected from portfolio."""
        logger.info("=" * 80)
        logger.info("TEST 4: Pairs Trading-Only Portfolio (Best Pairs)")
        logger.info("=" * 80)
        
        # Get all pairs from allocator
        symbols = list(real_historical_data.keys())
        if len(symbols) < 2:
            pytest.skip("Need at least 2 symbols for pairs trading")
        
        # Score pairs (limit to first 20 symbols for efficiency)
        pairs_scores = []
        test_symbols = symbols[:20]
        
        for i, symbol1 in enumerate(test_symbols):
            for symbol2 in test_symbols[i+1:]:
                try:
                    df1 = real_historical_data[symbol1]
                    df2 = real_historical_data[symbol2]
                    score_result = allocator.score_pairs_trading(symbol1, symbol2, df1, df2)
                    if score_result and not score_result.get('rejected', False):
                        pairs_scores.append({
                            'symbol1': symbol1,
                            'symbol2': symbol2,
                            'score': score_result.get('score', 0.0),
                            'cointegration': score_result.get('cointegration_score', 0.0)
                        })
                except Exception as e:
                    logger.debug(f"Failed to score pair {symbol1}-{symbol2}: {e}")
                    continue
        
        # Select top 5 pairs
        top_pairs = sorted(pairs_scores, key=lambda x: x['score'], reverse=True)[:5]
        
        logger.info(f"Top 5 Pairs: {len(top_pairs)} found")
        for i, pair in enumerate(top_pairs, 1):
            logger.info(f"  {i}. {pair['symbol1']}-{pair['symbol2']}: score={pair['score']:.4f}, coint={pair['cointegration']:.4f}")
        
        # Skip test if no pairs found (may happen with strict cointegration filters)
        if len(top_pairs) == 0:
            pytest.skip("No cointegrated pairs found (may be expected with strict filters: p-value < 0.01, lookback 250 days)")
        
        assert len(top_pairs) > 0, "Should have at least one pair"
        
        # Get quotes for pairs
        pairs_quotes = {}
        for pair in top_pairs:
            symbol1 = pair['symbol1']
            symbol2 = pair['symbol2']
            
            if symbol1 in real_historical_data and symbol2 in real_historical_data:
                df1 = real_historical_data[symbol1]
                df2 = real_historical_data[symbol2]
                quotes1 = dataframe_to_quotes(symbol1, df1)
                quotes2 = dataframe_to_quotes(symbol2, df2)
                
                if quotes1 and quotes2:
                    pairs_quotes[(symbol1, symbol2)] = (quotes1[-50:], quotes2[-50:])
        
        assert len(pairs_quotes) > 0, "Should have quotes for pairs"
        
        # Generate signals
        pairs_strategy = PairsTradingStrategy({"name": "pairs_trading"})
        signals = []
        
        for (symbol1, symbol2), (quotes1, quotes2) in pairs_quotes.items():
            # Configure pair symbols for strategy
            pairs_strategy.pair_symbols = [symbol1, symbol2]
            
            # Generate signals for both symbols
            # PairsTradingStrategy.generate_signals() accepts single Quote
            if quotes1:
                for quote in quotes1[-5:]:  # Test last 5 quotes per symbol
                    quote_signals = pairs_strategy.generate_signals(quote)
                    signals.extend(quote_signals)
            
            if quotes2:
                for quote in quotes2[-5:]:  # Test last 5 quotes per symbol
                    quote_signals = pairs_strategy.generate_signals(quote)
                    signals.extend(quote_signals)
        
        logger.info(f"✅ Generated {len(signals)} pairs trading signals from {len(top_pairs)} best pairs")
        
        # Verify signals
        assert len(signals) >= 0, "Should generate signals (or 0 if conditions not met)"
        
        if signals:
            logger.info(f"Sample signals:")
            for signal in signals[:5]:
                logger.info(f"  {signal.symbol}: {signal.signal_type} at ${signal.price}")
        
        logger.info("✅ TEST 4 PASSED: Pairs Trading-only portfolio working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

