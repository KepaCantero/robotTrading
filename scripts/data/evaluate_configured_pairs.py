#!/usr/bin/env python3
"""
Evaluate Configured Pairs Trading Candidates

Evaluates the pairs already defined in config/strategies/pairs_trading.yaml
and shows their actual metrics.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
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

# Pairs from config - Updated with best found pairs
CONFIGURED_PAIRS = [
    ["KO", "SRE"],     # Utilities (Score: 0.7000, Corr: 0.893, p-value: <0.01)
    ["AEP", "SRE"],    # Utilities (Score: 0.6997, Corr: 0.897, p-value: <0.01)
    ["DUK", "KO"],     # Utilities (Score: 0.6996, Corr: 0.915, p-value: <0.01)
    ["JPM", "WMT"],    # Cross-sector (Score: 0.6990, Corr: 0.959, p-value: <0.01)
    ["NEE", "PLD"],    # Utilities/REIT (Score: 0.6990, Corr: 0.920, p-value: <0.01)
    ["AAPL", "MSFT"],  # Technology (Score: 0.6979, Corr: 0.977, p-value: 0.0061)
]


def calculate_half_life(residuals: pd.Series) -> float:
    """Calculate half-life of mean reversion from residuals."""
    try:
        # O-U model: dX = -theta * (X - mu) * dt + sigma * dW
        # Estimate theta using linear regression
        x = residuals.iloc[:-1].values
        y = np.diff(residuals.values)
        
        if len(x) < 2:
            return None
        
        # Linear regression: y = alpha + theta * x
        coeffs = np.polyfit(x, y, 1)
        theta = -coeffs[0]
        
        if theta <= 0:
            return None
        
        half_life = np.log(2) / theta
        return float(half_life)
    except (ValueError, TypeError, KeyError, AttributeError):
        return None


def evaluate_pair(symbol1: str, symbol2: str, historical_data: dict) -> dict:
    """Evaluate a single pair - calculates directly."""
    if symbol1 not in historical_data or symbol2 not in historical_data:
        return {
            "error": f"Missing data: {symbol1 if symbol1 not in historical_data else symbol2}"
        }
    
    if not STATSMODELS_AVAILABLE:
        return {"rejected": True, "reason": "statsmodels not available"}
    
    data1 = historical_data[symbol1]
    data2 = historical_data[symbol2]
    
    try:
        min_len = min(len(data1), len(data2))
        if min_len < 250:
            return {"rejected": True, "reason": f"Insufficient data: {min_len} < 250"}
        
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
        
        # ADF test
        adf_result = adfuller(residuals, autolag='AIC')
        adf_pvalue = adf_result[1]
        cointegration_score = 1.0 - adf_pvalue
        
        # Calculate half-life
        residual_series = pd.Series(residuals)
        half_life = calculate_half_life(residual_series)
        
        # Simple score
        score = cointegration_score * abs(correlation) * 0.5
        
        rejected = adf_pvalue >= 0.01  # Strict threshold
        reason = "" if not rejected else f"ADF p-value {adf_pvalue:.4f} >= 0.01"
        
        return {
            "score": float(score),
            "correlation": float(correlation),
            "cointegration_score": cointegration_score,
            "half_life": half_life,
            "hedge_ratio": hedge_ratio,
            "adf_pvalue": float(adf_pvalue),
            "rejected": rejected,
            "reason": reason
        }
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        return {"rejected": True, "reason": f"Error: {str(e)}"}


def main():
    """Main function."""
    print("=" * 80)
    print("📊 Evaluating Configured Pairs Trading Candidates")
    print("=" * 80)
    print(f"Pairs from config: {len(CONFIGURED_PAIRS)}")
    print("=" * 80)
    
    # Load historical data
    data_dir = project_root / "data" / "historical"
    historical_data = load_all_csv_data(data_dir=data_dir, min_days=250)
    
    if len(historical_data) < 2:
        logger.error(f"Need at least 2 symbols. Found: {len(historical_data)}")
        return 1
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"{'Pair':<15} {'Status':<12} {'Corr':<7} {'Coint-P':<8} {'Half-Life':<10} {'Score':<8} {'Notes'}")
    print("-" * 80)
    
    results = []
    
    for pair in CONFIGURED_PAIRS:
        symbol1, symbol2 = pair
        pair_name = f"{symbol1}-{symbol2}"
        
        result = evaluate_pair(symbol1, symbol2, historical_data)
        
        if "error" in result:
            print(f"{pair_name:<15} {'ERROR':<12} {'N/A':<7} {'N/A':<8} {'N/A':<10} {'N/A':<8} {result['error']}")
            continue
        
        rejected = result.get('rejected', False)
        status = "❌ REJECTED" if rejected else "✅ VALID"
        correlation = result.get('correlation', 0.0)
        cointegration_score = result.get('cointegration_score', 0.0)
        adf_pvalue = result.get('adf_pvalue', 1.0)
        half_life = result.get('half_life', None)
        score = result.get('score', 0.0)
        reason = result.get('reason', '')
        
        half_life_str = f"{half_life:.1f}d" if half_life else "N/A"
        pvalue_str = f"{adf_pvalue:.4f}" if adf_pvalue < 1.0 else "N/A"
        
        notes = []
        if rejected:
            notes.append(reason)
        else:
            # Check against strict criteria
            if correlation < 0.85:
                notes.append(f"Corr {correlation:.3f} < 0.85")
            if adf_pvalue >= 0.01:
                notes.append(f"p-value {adf_pvalue:.4f} >= 0.01")
            if half_life and half_life > 15.0:
                notes.append(f"Half-life {half_life:.1f} > 15d")
        
        notes_str = ", ".join(notes) if notes else "Passes all criteria"
        
        print(f"{pair_name:<15} {status:<12} {correlation:<7.3f} {pvalue_str:<8} {half_life_str:<10} {score:<8.4f} {notes_str}")
        
        results.append({
            'pair': pair_name,
            'status': status,
            'correlation': correlation,
            'pvalue': adf_pvalue,
            'half_life': half_life,
            'score': score,
            'rejected': rejected,
            'reason': reason,
            'notes': notes
        })
    
    print("=" * 80)
    
    # Summary
    valid_count = sum(1 for r in results if not r.get('rejected', True))
    rejected_count = len(results) - valid_count
    
    print(f"\n📈 Summary:")
    print(f"  ✅ Valid pairs: {valid_count}/{len(results)}")
    print(f"  ❌ Rejected pairs: {rejected_count}/{len(results)}")
    
    if valid_count == 0:
        print("\n💡 Recommendations:")
        print("  - All configured pairs failed the strict criteria")
        print("  - Consider relaxing:")
        print("    * cointegration_threshold: 0.01 → 0.05")
        print("    * min_correlation: 0.85 → 0.80")
        print("    * max_pair_half_life_days: 15 → 30")
        print("  - Or find new pairs using: python scripts/find_best_pairs_trading.py")
    else:
        print(f"\n✅ Best pairs to use:")
        valid_results = sorted([r for r in results if not r.get('rejected', True)], key=lambda x: x['score'], reverse=True)
        for r in valid_results[:5]:
            print(f"  - {r['pair']}: Score={r['score']:.4f}, Corr={r['correlation']:.3f}, p-value={r['pvalue']:.4f}")
    
    print("\n" + "=" * 80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())