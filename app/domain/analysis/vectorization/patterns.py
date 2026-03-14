"""
Common vectorization patterns and solutions.

This module provides a library of common anti-patterns found in numerical
computing code and their vectorized alternatives. It serves as both a
reference and a suggestion generator for the vectorization auditor.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class VectorizationPatterns:
    """
    Common vectorization patterns and solutions.

    This class documents common anti-patterns in numerical computing and provides
    vectorized alternatives using NumPy and Pandas. Each pattern includes:
    - Description of the anti-pattern
    - Code example of the non-vectorized approach
    - Code example of the vectorized approach
    - Performance characteristics
    - Usage context in trading systems

    Examples:
        Get the element-wise operation pattern:
        >>> pattern = VectorizationPatterns.elementwise_operation()

        Get all available patterns:
        >>> all_patterns = VectorizationPatterns().get_all_patterns()
    """

    @staticmethod
    def elementwise_operation() -> str:
        """Pattern: Element-wise arithmetic operations.

        Common in trading for: price adjustments, returns calculation, scaling.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: Element-wise Operations
# ❌ Non-vectorized (SLOW)
result = np.zeros_like(arr)
for i in range(len(arr)):
    result[i] = arr[i] * 2 + 1

# ✅ Vectorized (FAST)
result = arr * 2 + 1

# Performance: ~100x speedup for large arrays
# Use case: Computing net returns from gross returns
"""

    @staticmethod
    def filtering() -> str:
        """Pattern: Filtering with boolean conditions.

        Common in trading for: signal filtering, price threshold checks,
        volume filtering.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: Filtering with Conditions
# ❌ Non-vectorized (SLOW)
result = []
for x in arr:
    if x > 0:
        result.append(x * 2)

# ✅ Vectorized (FAST)
mask = arr > 0
result = arr[mask] * 2

# Alternative with np.where:
result = np.where(arr > 0, arr * 2, arr)

# Performance: ~50x speedup
# Use case: Filtering stocks by market cap, price thresholds
"""

    @staticmethod
    def rolling_calculation() -> str:
        """Pattern: Rolling window calculations.

        Critical in trading for: moving averages, rolling volatility,
        momentum indicators.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: Rolling Window Calculations
# ❌ Non-vectorized (VERY SLOW)
result = []
for i in range(window, len(series)):
    result.append(series[i-window:i].mean())

# ✅ Vectorized with Pandas (FAST)
result = series.rolling(window).mean()

# For multiple rolling statistics:
rolling = series.rolling(window)
df['rolling_mean'] = rolling.mean()
df['rolling_std'] = rolling.std()
df['rolling_min'] = rolling.min()
df['rolling_max'] = rolling.max()

# Performance: ~200x speedup
# Use case: Moving averages, Bollinger Bands, momentum indicators
"""

    @staticmethod
    def groupby_aggregation() -> str:
        """Pattern: Group-by operations.

        Common in trading for: sector analysis, portfolio attribution,
        cross-sectional analysis.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: Group-By Aggregations
# ❌ Non-vectorized (SLOW)
result = {}
for key in df['sector'].unique():
    subset = df[df['sector'] == key]
    result[key] = subset['returns'].mean()

# ✅ Vectorized (FAST)
result = df.groupby('sector')['returns'].mean()

# Multiple aggregations:
result = df.groupby('sector')['returns'].agg(['mean', 'std', 'count'])

# Performance: ~100x speedup
# Use case: Sector returns, portfolio attribution, cross-sectional ranks
"""

    @staticmethod
    def correlation_matrix() -> str:
        """Pattern: Correlation matrix calculation.

        Essential in trading for: portfolio optimization, risk management,
        factor analysis.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: Correlation Matrix
# ❌ Non-vectorized (EXTREMELY SLOW)
n = len(columns)
corr = np.zeros((n, n))
for i in range(n):
    for j in range(n):
        corr[i,j] = np.corrcoef(data[:,i], data[:,j])[0,1]

# ✅ Vectorized (FAST)
corr = np.corrcoef(data, rowvar=False)

# With Pandas:
corr = df[columns].corr()

# Performance: ~1000x speedup for 100 assets
# Use case: Portfolio optimization, risk clustering, factor analysis
"""

    @staticmethod
    def conditional_assignment() -> str:
        """Pattern: Conditional assignment with np.where.

        Common in trading for: signal generation, position sizing,
        threshold-based logic.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: Conditional Assignment
# ❌ Non-vectorized (SLOW)
result = np.zeros_like(arr)
for i in range(len(arr)):
    if arr[i] > 0:
        result[i] = 1
    else:
        result[i] = -1

# ✅ Vectorized (FAST)
result = np.where(arr > 0, 1, -1)

# Multiple conditions:
result = np.select(
    [arr > 0.5, arr > 0, arr > -0.5],
    [2, 1, -1],
    default=-2
)

# Performance: ~100x speedup
# Use case: Signal generation, entry/exit conditions, position sizing
"""

    @staticmethod
    def exponential_weighted() -> str:
        """Pattern: Exponentially weighted calculations.

        Critical in trading for: EMA, EWMA volatility, risk metrics.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: Exponentially Weighted Moving Average
# ❌ Non-vectorized (SLOW)
alpha = 2 / (span + 1)
result = np.zeros_like(series)
result[0] = series[0]
for i in range(1, len(series)):
    result[i] = alpha * series[i] + (1 - alpha) * result[i-1]

# ✅ Vectorized with Pandas (FAST)
result = series.ewm(span=span).mean()

# Multiple EWMA statistics:
ewm = series.ewm(span=span)
df['ewm_mean'] = ewm.mean()
df['ewm_std'] = ewm.std()

# Performance: ~150x speedup
# Use case: EMA indicators, EWMA volatility, decay factors
"""

    @staticmethod
    def percentage_change() -> str:
        """Pattern: Percentage change calculation.

        Essential in trading for: returns computation, price changes,
        performance metrics.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: Percentage Change
# ❌ Non-vectorized (SLOW)
returns = np.zeros(len(prices))
for i in range(1, len(prices)):
    returns[i] = (prices[i] - prices[i-1]) / prices[i-1]

# ✅ Vectorized with Pandas (FAST)
returns = prices.pct_change()

# With NumPy:
returns = np.diff(prices) / prices[:-1]
returns = np.insert(returns, 0, np.nan)

# Performance: ~80x speedup
# Use case: Return calculation, price change, performance metrics
"""

    @staticmethod
    def cumulative_operations() -> str:
        """Pattern: Cumulative operations.

        Common in trading for: cumulative returns, drawdown calculation,
        PnL tracking.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: Cumulative Operations
# ❌ Non-vectorized (SLOW)
cumsum = np.zeros_like(returns)
cumsum[0] = returns[0]
for i in range(1, len(returns)):
    cumsum[i] = cumsum[i-1] + returns[i]

# ✅ Vectorized (FAST)
cumsum = np.cumsum(returns)

# For cumulative returns:
cumret = (1 + returns).cumprod()

# For cumulative max (for drawdown):
cummax = prices.cummax()
drawdown = (prices - cummax) / cummax

# Performance: ~200x speedup
# Use case: Cumulative returns, drawdown, PnL tracking
"""

    @staticmethod
    def shift_lag() -> str:
        """Pattern: Shifting/lagging operations.

        Critical in trading for: lookback periods, lagged features,
        time-series alignment.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: Shift/Lag Operations
# ❌ Non-vectorized (SLOW)
lagged = np.zeros_like(series)
lagged[1:] = series[:-1]  # Lag by 1

# ✅ Vectorized with Pandas (FAST)
lagged = series.shift(1)

# Multiple lags:
for lag in [1, 5, 10, 20]:
    df[f'lag_{lag}'] = df['price'].shift(lag)

# Forward shift (lead):
lead = series.shift(-1)

# Performance: ~50x speedup
# Use case: Lagged returns, lookback features, time-series alignment
"""

    @staticmethod
    def rank_percentile() -> str:
        """Pattern: Ranking and percentile calculations.

        Essential in trading for: cross-sectional ranks, percentiles,
        quantile-based strategies.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: Ranking and Percentiles
# ❌ Non-vectorized (SLOW)
ranks = np.zeros_like(values)
for i, val in enumerate(values):
    ranks[i] = sum(values < val)

# ✅ Vectorized (FAST)
ranks = pd.Series(values).rank()

# Percentiles:
percentiles = pd.Series(values).rank(pct=True)

# Quantile bins:
bins = pd.qcut(values, q=5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])

# Performance: ~100x speedup
# Use case: Cross-sectional ranks, quantile strategies, factor scoring
"""

    @staticmethod
    def distance_matrix() -> str:
        """Pattern: Distance matrix calculation.

        Used in trading for: clustering, similarity analysis, correlation
        distance matrices.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: Distance Matrix
# ❌ Non-vectorized (VERY SLOW)
n = len(points)
dist = np.zeros((n, n))
for i in range(n):
    for j in range(n):
        dist[i,j] = np.linalg.norm(points[i] - points[j])

# ✅ Vectorized with Broadcasting (FAST)
# Using scipy:
from scipy.spatial.distance import pdist, squareform
dist = squareform(pdist(points, metric='euclidean'))

# Using pure NumPy broadcasting:
diff = points[:, np.newaxis, :] - points[np.newaxis, :, :]
dist = np.sqrt(np.sum(diff ** 2, axis=-1))

# Performance: ~500x speedup
# Use case: Clustering, similarity analysis, correlation distance
"""

    @staticmethod
    def interpolation() -> str:
        """Pattern: Interpolation and filling missing values.

        Common in trading for: forward-filling prices, interpolation of
        missing data points.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: Interpolation
# ❌ Non-vectorized (SLOW)
for i in range(1, len(series)):
    if pd.isna(series[i]) and not pd.isna(series[i-1]):
        series[i] = series[i-1]

# ✅ Vectorized with Pandas (FAST)
# Forward fill:
filled = series.ffill()

# Backward fill:
filled = series.bfill()

# Interpolation:
filled = series.interpolate(method='linear')

# Performance: ~100x speedup
# Use case: Missing price data, forward-filling, data cleaning
"""

    @staticmethod
    def difference_operations() -> str:
        """Pattern: Difference operations.

        Essential in trading for: first differences, stationarity
        transformations, time series differencing.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: Difference Operations
# ❌ Non-vectorized (SLOW)
diff = np.zeros_like(series)
for i in range(1, len(series)):
    diff[i] = series[i] - series[i-1]

# ✅ Vectorized (FAST)
# First difference:
diff = np.diff(series)

# With Pandas (preserves index):
diff = series.diff()

# N-th order difference:
diff_n = series.diff(periods=n)

# Performance: ~80x speedup
# Use case: Stationarity transformations, change detection, returns
"""

    @staticmethod
    def value_counts_mode() -> str:
        """Pattern: Value counting and mode calculation.

        Used in trading for: most common values, frequency analysis,
        category distribution.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: Value Counts and Mode
# ❌ Non-vectorized (SLOW)
counts = {}
for val in series:
    counts[val] = counts.get(val, 0) + 1
mode_val = max(counts, key=counts.get)

# ✅ Vectorized with Pandas (FAST)
counts = series.value_counts()
mode_val = series.mode()[0]

# Normalized value counts:
freq = series.value_counts(normalize=True)

# Performance: ~50x speedup
# Use case: Category frequency, mode calculation, distribution analysis
"""

    @staticmethod
    def outer_product() -> str:
        """Pattern: Outer product and broadcasting.

        Used in trading for: interaction terms, portfolio weight
        calculations, covariance operations.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: Outer Product
# ❌ Non-vectorized (SLOW)
n, m = len(vec1), len(vec2)
result = np.zeros((n, m))
for i in range(n):
    for j in range(m):
        result[i,j] = vec1[i] * vec2[j]

# ✅ Vectorized with Broadcasting (FAST)
result = vec1[:, np.newaxis] * vec2[np.newaxis, :]

# Or using np.outer:
result = np.outer(vec1, vec2)

# Performance: ~200x speedup
# Use case: Interaction terms, portfolio weights, covariance calculations
"""

    @staticmethod
    def datetime_operations() -> str:
        """Pattern: DateTime operations.

        Critical in trading for: time features, trading hours, date
        filtering.

        Returns:
            Pattern documentation with before/after examples.
        """
        return """
# Pattern: DateTime Operations
# ❌ Non-vectorized (SLOW)
is_trading_day = []
for date in dates:
    is_trading_day.append(date.weekday() < 5)  # Mon-Fri

# ✅ Vectorized with Pandas (FAST)
dates = pd.to_datetime(dates)
is_trading_day = dates.dayofweek < 5  # Mon=0, Fri=4

# Extract time components:
df['hour'] = df.index.hour
df['day_of_week'] = df.index.dayofweek
df['month'] = df.index.month

# Filter by time:
trading_hours = df.between_time('09:30', '16:00')

# Performance: ~100x speedup
# Use case: Trading hours, time features, date filtering
"""

    @classmethod
    def get_all_patterns(cls) -> dict[str, str]:
        """Get all documented vectorization patterns.

        Returns:
            Dictionary mapping pattern names to their documentation.
        """
        logger.debug(
            "Retrieving all vectorization patterns",
            extra={
                "pattern_count": len(
                    [
                        cls.elementwise_operation,
                        cls.filtering,
                        cls.rolling_calculation,
                        cls.groupby_aggregation,
                        cls.correlation_matrix,
                        cls.conditional_assignment,
                        cls.exponential_weighted,
                        cls.percentage_change,
                        cls.cumulative_operations,
                        cls.shift_lag,
                        cls.rank_percentile,
                        cls.distance_matrix,
                        cls.interpolation,
                        cls.difference_operations,
                        cls.value_counts_mode,
                        cls.outer_product,
                        cls.datetime_operations,
                    ]
                )
            },
        )
        methods = [
            cls.elementwise_operation,
            cls.filtering,
            cls.rolling_calculation,
            cls.groupby_aggregation,
            cls.correlation_matrix,
            cls.conditional_assignment,
            cls.exponential_weighted,
            cls.percentage_change,
            cls.cumulative_operations,
            cls.shift_lag,
            cls.rank_percentile,
            cls.distance_matrix,
            cls.interpolation,
            cls.difference_operations,
            cls.value_counts_mode,
            cls.outer_product,
            cls.datetime_operations,
        ]

        patterns: dict[str, str] = {}
        for method in methods:
            pattern_name = method.__name__.replace("_", " ").title()
            patterns[pattern_name] = method()

        logger.debug(
            "All vectorization patterns retrieved successfully",
            extra={"pattern_names": list(patterns.keys())},
        )

        return patterns

    @classmethod
    def get_suggestion_for_issue(cls, issue_type: str) -> str:
        """Get a vectorization suggestion for a specific issue type.

        Args:
            issue_type: The type of issue (e.g., "for_loop", "apply").

        Returns:
            Suggested pattern documentation.
        """
        logger.debug("Getting vectorization suggestion for issue", extra={"issue_type": issue_type})
        suggestions: dict[str, str] = {
            "for_loop": cls.elementwise_operation(),
            "list_comp": cls.elementwise_operation(),
            "apply": cls.groupby_aggregation(),
            "iterrows": cls.rolling_calculation(),
            "itertuples": cls.rolling_calculation(),
            "enumerate": cls.elementwise_operation(),
            "range_len": cls.elementwise_operation(),
            "while_loop": cls.elementwise_operation(),
            "nested_loop": cls.correlation_matrix(),
        }

        suggestion = suggestions.get(issue_type, cls.elementwise_operation())
        logger.debug(
            "Vectorization suggestion found",
            extra={"issue_type": issue_type, "has_suggestion": issue_type in suggestions},
        )

        return suggestion

    @classmethod
    def get_trading_specific_examples(cls) -> dict[str, str]:
        """Get trading-specific vectorization examples.

        Returns:
            Dictionary mapping trading concepts to vectorized implementations.
        """
        logger.debug(
            "Retrieving trading-specific vectorization examples",
            extra={
                "example_types": [
                    "simple_returns",
                    "log_returns",
                    "moving_average",
                    "volatility",
                    "sharpe_ratio",
                    "bollinger_bands",
                    "rsi",
                ]
            },
        )
        return {
            "simple_returns": """
# Simple Returns Calculation
# ❌ Non-vectorized
returns = np.zeros(len(prices) - 1)
for i in range(1, len(prices)):
    returns[i-1] = (prices[i] - prices[i-1]) / prices[i-1]

# ✅ Vectorized
returns = prices.pct_change().dropna()
# Or: returns = np.diff(prices) / prices[:-1]
""",
            "log_returns": """
# Log Returns Calculation
# ❌ Non-vectorized
log_returns = np.zeros(len(prices) - 1)
for i in range(1, len(prices)):
    log_returns[i-1] = np.log(prices[i] / prices[i-1])

# ✅ Vectorized
log_returns = np.diff(np.log(prices))
# Or: log_returns = np.log(prices / prices.shift(1))
""",
            "moving_average": """
# Moving Average (SMA)
# ❌ Non-vectorized
sma = np.zeros(len(prices) - window + 1)
for i in range(window - 1, len(prices)):
    sma[i - window + 1] = np.mean(prices[i-window+1:i+1])

# ✅ Vectorized
sma = prices.rolling(window).mean()
""",
            "volatility": """
# Rolling Volatility (Standard Deviation)
# ❌ Non-vectorized
volatility = np.zeros(len(returns) - window + 1)
for i in range(window - 1, len(returns)):
    volatility[i - window + 1] = np.std(returns[i-window+1:i+1])

# ✅ Vectorized
volatility = returns.rolling(window).std()

# Annualized (assuming daily returns):
volatility_annual = returns.rolling(window).std() * np.sqrt(252)
""",
            "sharpe_ratio": """
# Rolling Sharpe Ratio
# ❌ Non-vectorized
sharpe = np.zeros(len(returns) - window + 1)
risk_free = getattr(config.trading, 'max_risk_per_trade', 0.02) / 252  # Daily risk-free rate
for i in range(window - 1, len(returns)):
    excess_returns = returns[i-window+1:i+1] - risk_free
    sharpe[i - window + 1] = np.mean(excess_returns) / np.std(excess_returns)

# ✅ Vectorized
risk_free = getattr(config.trading, 'max_risk_per_trade', 0.02) / 252
excess_returns = returns - risk_free
sharpe = excess_returns.rolling(window).mean() / excess_returns.rolling(window).std()

# Annualized:
sharpe_annual = sharpe * np.sqrt(252)
""",
            "bollinger_bands": """
# Bollinger Bands
# ❌ Non-vectorized
upper_band = np.zeros(len(prices) - window + 1)
lower_band = np.zeros(len(prices) - window + 1)
sma = prices.rolling(window).mean()
std = prices.rolling(window).std()
for i in range(len(sma)):
    upper_band[i] = sma[i] + 2 * std[i]
    lower_band[i] = sma[i] - 2 * std[i]

# ✅ Vectorized
sma = prices.rolling(window).mean()
std = prices.rolling(window).std()
upper_band = sma + 2 * std
lower_band = sma - 2 * std
""",
            "rsi": """
# Relative Strength Index (RSI)
# ❌ Non-vectorized
delta = prices.diff()
gain = np.zeros_like(delta)
loss = np.zeros_like(delta)
for i in range(len(delta)):
    if delta[i] > 0:
        gain[i] = delta[i]
    else:
        loss[i] = -delta[i]

# ✅ Vectorized
delta = prices.diff()
gain = (delta.where(delta > 0, 0))
loss = (-delta.where(delta < 0, 0))

avg_gain = gain.rolling(window).mean()
avg_loss = loss.rolling(window).mean()
rs = avg_gain / avg_loss
rsi = 100 - (100 / (1 + rs))
""",
        }

    @classmethod
    def get_performance_comparison(cls) -> dict[str, tuple[str, str]]:
        """Get performance comparisons for common operations.

        Returns:
            Dictionary mapping operations to (non_vectorized, vectorized) time estimates.
        """
        logger.debug("Retrieving performance comparison data", extra={"operation_count": 7})
        return {
            "Sum 1M elements": ("~100ms", "~1ms"),
            "Mean 1M elements": ("~100ms", "~1ms"),
            "Rolling mean 50k": ("~5000ms", "~25ms"),
            "Correlation 100x100": ("~10000ms", "~10ms"),
            "Groupby mean 100k": ("~5000ms", "~50ms"),
            "Conditional assign 1M": ("~200ms", "~2ms"),
            "Distance matrix 1000": ("~100000ms", "~200ms"),
        }
