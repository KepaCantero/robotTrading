# Data Sources

## Historical Market Data

### Source: Stooq

**URL**: https://stooq.com/

**Format**: CSV

**Columns**:
- `Date`: YYYY-MM-DD format
- `Open`: Opening price
- `High`: Highest price
- `Low`: Lowest price
- `Close`: Closing price
- `Volume`: Trading volume

**Storage**: `data/historical/{SYMBOL}.csv`

**Example**: `data/historical/AAPL.csv`

### Data Quality

- **Coverage**: 1984-present for major symbols
- **Frequency**: Daily
- **Missing Data**: Handled by forward-fill
- **Outliers**: Filtered by data loader

## Data Loading Process

### Automatic Loading

1. Check `data/historical/{SYMBOL}.csv`
2. If exists, load from CSV
3. If not, try yfinance (not recommended due to rate limits)
4. Cache loaded data in memory

### Validation

- Date format consistency
- Price values > 0
- Volume >= 0
- No duplicate timestamps
- Sequential date ordering

## Usage

```python
from app.backtesting.data_loader import DataLoader

loader = DataLoader()

# Load historical data
quotes = loader.load_market_data(
    symbol="AAPL",
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2024, 12, 31)
)
```

## Data Provenance

### Audit Trail

Every backtest execution records:
- Data source (filename or API)
- Load timestamp
- Data hash (for integrity verification)
- Symbol and date range
- Quote count

### Example

```json
{
  "data_source": "data/historical/AAPL.csv",
  "symbol": "AAPL",
  "start_date": "2023-01-01",
  "end_date": "2024-12-31",
  "quote_count": 502,
  "data_hash": "sha256:abc123...",
  "load_timestamp": "2025-10-26T10:30:00Z"
}
```

## Future Data Sources

### Planned Integrations

- **Alpha Vantage**: Higher frequency data
- **IEX Cloud**: Real-time quotes
- **Yahoo Finance API**: Alternative backup
- **Custom CSV**: User-provided data

### AWS Data Lake

Future: `s3://algo-trading-data/{symbol}/{date}/`

## Data Privacy

- Market data is publicly available (not PII)
- No sensitive user data stored
- Compliance with data retention policies

