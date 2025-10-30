#!/usr/bin/env python3
"""
Find Best Pairs Trading Candidates

Scans all available historical data and identifies the best cointegrated pairs
according to strict criteria (p-value < 0.01, correlation > 0.85, half-life < 15 days).
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from app.services.strategy_stock_allocator import StrategyStockAllocator
from app.core.centralized_config import StockAllocationSettings
from tests.integration.test_data_loader import load_all_csv_data

try:
    from statsmodels.tsa.stattools import adfuller
    from statsmodels.regression.linear_model import OLS
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _score_pair_relaxed(pair: Tuple[str, str], data1: pd.DataFrame, data2: pd.DataFrame, 
                        allocator: StrategyStockAllocator, coint_threshold: float) -> Dict:
    """
    Score a pair with relaxed cointegration threshold (for discovery purposes only).
    This bypasses the strict allocator threshold temporarily.
    """
    ticker1, ticker2 = pair
    if not STATSMODELS_AVAILABLE:
        return {"score": 0.0, "rejected": True, "reason": "statsmodels required"}
    
    try:
        min_len = min(len(data1), len(data2))
        min_lookback = 250
        if min_len < min_lookback:
            return {"score": 0.0, "rejected": True, "reason": f"Insufficient lookback: {min_len} < {min_lookback}"}
        
        prices1 = data1['close'].values[-min_len:]
        prices2 = data2['close'].values[-min_len:]
        
        # Correlation
        correlation = np.corrcoef(prices1, prices2)[0, 1]
        if np.isnan(correlation):
            correlation = 0.0
        
        # OLS regression
        model = OLS(prices2, prices1).fit()
        hedge_ratio = float(model.params[0])
        residuals = model.resid
        
        # ADF test with relaxed threshold
        adf_result = adfuller(residuals, autolag='AIC')
        adf_pvalue = adf_result[1]
        
        if adf_pvalue >= coint_threshold:
            return {"score": 0.0, "rejected": True, "correlation": float(correlation), 
                    "cointegration_score": 1.0 - adf_pvalue, "reason": f"Cointegration p={adf_pvalue:.4f}>={coint_threshold}"}
        
        # Calculate half-life
        residual_series = pd.Series(residuals)
        half_life = allocator.calculate_half_life(residual_series)
        
        # Basic score
        cointegration_score = 1.0 - adf_pvalue
        score = cointegration_score * abs(correlation) * 0.5  # Simple scoring for discovery
        
        return {
            "score": float(score),
            "correlation": float(correlation),
            "cointegration_score": cointegration_score,
            "half_life": half_life,
            "hedge_ratio": hedge_ratio,
            "adf_pvalue": float(adf_pvalue),
            "rejected": False
        }
    except Exception as e:
        logger.debug(f"Error scoring pair {ticker1}-{ticker2} (relaxed): {e}")
        return {"score": 0.0, "rejected": True, "reason": str(e)}


def find_best_pairs(
    historical_data: Dict[str, pd.DataFrame],
    min_correlation: float = 0.85,
    max_half_life_days: float = 15.0,
    max_pairs: int = 10,
    relax_cointegration: bool = False
) -> List[Tuple[str, str, Dict]]:
    """
    Find best cointegrated pairs from historical data.
    
    Args:
        historical_data: Dictionary of symbol -> DataFrame with OHLCV data
        min_correlation: Minimum correlation threshold (default: 0.85)
        max_half_life_days: Maximum half-life in days (default: 15.0)
        max_pairs: Maximum number of pairs to return (default: 10)
    
    Returns:
        List of tuples (symbol1, symbol2, metrics_dict) sorted by score (best first)
    """
    logger.info("=" * 80)
    logger.info("🔍 Finding Best Pairs Trading Candidates")
    logger.info("=" * 80)
    logger.info(f"Available symbols: {len(historical_data)}")
    logger.info(f"Criteria:")
    coint_threshold = 0.05 if relax_cointegration else 0.01
    logger.info(f"  - Cointegration p-value < {coint_threshold} {'(RELAXED)' if relax_cointegration else '(STRICT)'}")
    logger.info(f"  - Correlation >= {min_correlation}")
    logger.info(f"  - Half-life <= {max_half_life_days} days")
    logger.info(f"  - Minimum lookback: 250 days")
    logger.info("=" * 80)
    
    # Initialize allocator
    allocator = StrategyStockAllocator(StockAllocationSettings())
    
    symbols = sorted(historical_data.keys())
    total_pairs = len(symbols) * (len(symbols) - 1) // 2
    logger.info(f"\nEvaluating {total_pairs} possible pairs...\n")
    
    valid_pairs = []
    evaluated = 0
    
    # Evaluate all pairs
    for i, symbol1 in enumerate(symbols):
        for symbol2 in symbols[i+1:]:
            evaluated += 1
            if evaluated % 50 == 0:
                logger.info(f"Progress: {evaluated}/{total_pairs} pairs evaluated ({evaluated*100/total_pairs:.1f}%)")
            
            try:
                data1 = historical_data[symbol1]
                data2 = historical_data[symbol2]
                
                # Score the pair (with relaxed cointegration if requested)
                if relax_cointegration:
                    score_result = _score_pair_relaxed((symbol1, symbol2), data1, data2, allocator, coint_threshold)
                else:
                    score_result = allocator.score_pairs_trading(
                        (symbol1, symbol2),
                        data1,
                        data2
                    )
                
                # Check if pair passed all criteria
                if score_result.get('rejected', False):
                    continue
                
                correlation = score_result.get('correlation', 0.0)
                half_life = score_result.get('half_life')
                cointegration_score = score_result.get('cointegration_score', 0.0)
                score = score_result.get('score', 0.0)
                
                # Store all pairs that passed cointegration (even if they fail other filters)
                # We'll filter and rank them later
                valid_pairs.append((symbol1, symbol2, score_result))
                
            except Exception as e:
                logger.debug(f"Error evaluating pair {symbol1}-{symbol2}: {e}")
                continue
    
    logger.info(f"\n✅ Evaluated {evaluated} pairs")
    logger.info(f"✅ Found {len(valid_pairs)} pairs passing cointegration test\n")
    
    # Filter and categorize pairs
    fully_valid = []
    partially_valid = []
    
    for pair_tuple in valid_pairs:
        symbol1, symbol2, metrics = pair_tuple
        correlation = metrics.get('correlation', 0.0)
        half_life = metrics.get('half_life')
        
        issues = []
        if abs(correlation) < min_correlation:
            issues.append(f"Corr={correlation:.3f}<{min_correlation}")
        if half_life is not None and half_life > max_half_life_days:
            issues.append(f"HalfLife={half_life:.1f}>{max_half_life_days}")
        
        if not issues:
            fully_valid.append(pair_tuple)
        else:
            # Store issues in metrics for reporting
            metrics['_issues'] = issues
            partially_valid.append(pair_tuple)
    
    # Sort by score (best first)
    fully_valid.sort(key=lambda x: x[2].get('score', 0.0), reverse=True)
    partially_valid.sort(key=lambda x: x[2].get('score', 0.0), reverse=True)
    
    logger.info(f"  ✅ Fully valid (all criteria): {len(fully_valid)}")
    logger.info(f"  ⚠️  Partially valid (cointegration passed): {len(partially_valid)}\n")
    
    # Return fully valid first, then best partially valid up to max_pairs
    result = fully_valid[:max_pairs]
    remaining_slots = max_pairs - len(result)
    if remaining_slots > 0:
        result.extend(partially_valid[:remaining_slots])
    
    return result


def print_pairs_report(pairs: List[Tuple[str, str, Dict]]):
    """Print a formatted report of the best pairs."""
    if not pairs:
        logger.warning("⚠️  No valid pairs found matching the strict criteria!")
        logger.info("\n💡 Suggestions:")
        logger.info("  - Relax correlation threshold (currently 0.85)")
        logger.info("  - Relax half-life threshold (currently 15 days)")
        logger.info("  - Check that all symbols have at least 250 days of data")
        logger.info("  - Verify cointegration p-value threshold (currently < 0.01)")
        return
    
    print("\n" + "=" * 80)
    print("📊 TOP PAIRS TRADING CANDIDATES")
    print("=" * 80)
    print(f"{'Rank':<6} {'Pair':<15} {'Score':<8} {'Corr':<7} {'Coint':<7} {'Half-Life':<10} {'Details'}")
    print("-" * 80)
    
    for rank, (symbol1, symbol2, metrics) in enumerate(pairs, 1):
        score = metrics.get('score', 0.0)
        correlation = metrics.get('correlation', 0.0)
        cointegration = metrics.get('cointegration_score', 0.0)
        half_life = metrics.get('half_life', None)
        spread_z = metrics.get('spread_z_score', None)
        hedge_ratio = metrics.get('hedge_ratio', 1.0)
        
        pair_name = f"{symbol1}-{symbol2}"
        half_life_str = f"{half_life:.1f}d" if half_life else "N/A"
        spread_z_str = f"z={spread_z:.2f}" if spread_z else ""
        
        reason = f"Hedge={hedge_ratio:.3f}"
        if spread_z_str:
            reason += f", {spread_z_str}"
        
        # Add issues if any
        issues = metrics.get('_issues', [])
        if issues:
            reason += f" ⚠️ {', '.join(issues)}"
        
        print(
            f"{rank:<6} {pair_name:<15} {score:<8.4f} {correlation:<7.3f} "
            f"{cointegration:<7.3f} {half_life_str:<10} {reason}"
        )
    
    print("=" * 80)
    
    # Summary statistics
    avg_score = sum(m[2].get('score', 0.0) for m in pairs) / len(pairs)
    avg_corr = sum(abs(m[2].get('correlation', 0.0)) for m in pairs) / len(pairs)
    avg_half_life = sum(m[2].get('half_life', 0.0) for m in pairs if m[2].get('half_life')) / max(1, len([m for m in pairs if m[2].get('half_life')]))
    
    print(f"\n📈 Summary Statistics:")
    print(f"  Average Score: {avg_score:.4f}")
    print(f"  Average Correlation: {avg_corr:.3f}")
    print(f"  Average Half-Life: {avg_half_life:.1f} days")


def generate_config_snippet(pairs: List[Tuple[str, str, Dict]]) -> str:
    """Generate YAML configuration snippet for the best pairs."""
    if not pairs:
        return ""
    
    lines = ["  pair_symbols:"]
    for symbol1, symbol2, _ in pairs:
        lines.append(f"    - [{symbol1}, {symbol2}]")
    
    return "\n".join(lines)


def main():
    """Main function."""
    # Load historical data
    data_dir = project_root / "data" / "historical"
    logger.info(f"Loading data from: {data_dir}")
    
    historical_data = load_all_csv_data(data_dir=data_dir, min_days=250)  # Need 250+ days for cointegration
    
    if len(historical_data) < 2:
        logger.error(f"Need at least 2 symbols with 250+ days of data. Found: {len(historical_data)}")
        return 1
    
    logger.info(f"✅ Loaded {len(historical_data)} symbols with sufficient data\n")
    
    # Find best pairs (first try strict, then relaxed if needed)
    best_pairs = find_best_pairs(
        historical_data,
        min_correlation=0.85,  # From config
        max_half_life_days=15.0,  # From config
        max_pairs=15,  # Show top 15
        relax_cointegration=False  # Start with strict
    )
    
    # If no pairs found, try with relaxed cointegration
    if not best_pairs:
        logger.info("\n⚠️  No pairs found with STRICT criteria. Trying RELAXED criteria (p-value < 0.05)...\n")
        best_pairs = find_best_pairs(
            historical_data,
            min_correlation=0.80,  # Slightly relaxed
            max_half_life_days=30.0,  # More relaxed
            max_pairs=20,  # Show more
            relax_cointegration=True  # Use relaxed cointegration
        )
    
    # Print report
    print_pairs_report(best_pairs)
    
    # Generate config snippet
    if best_pairs:
        print("\n" + "=" * 80)
        print("📝 YAML Configuration Snippet")
        print("=" * 80)
        print("Add this to config/strategies/pairs_trading.yaml:\n")
        print(generate_config_snippet(best_pairs[:10]))  # Top 10 for config
        print("\n" + "=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
