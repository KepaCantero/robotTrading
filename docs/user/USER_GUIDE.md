# User Guide

## Welcome to AlgoTrading

AlgoTrading is a powerful algorithmic trading platform that enables you to develop, test, and deploy automated trading strategies. This guide will help you get started and make the most of the platform.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Dashboard](#dashboard)
3. [Portfolio Management](#portfolio-management)
4. [Strategy Development](#strategy-development)
5. [Backtesting](#backtesting)
6. [Paper Trading](#paper-trading)
7. [Live Trading](#live-trading)
8. [Monitoring & Alerts](#monitoring--alerts)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Start the Application

```bash
# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Start the API server
uvicorn app.main:app --reload

# In another terminal, start the dashboard
python app/dashboard/main.py
```

### 2. Access the Platform

- **API Documentation**: http://localhost:8000/docs
- **Interactive Dashboard**: http://localhost:8503
- **Health Check**: http://localhost:8000/health

### 3. Your First Trade

1. Navigate to the dashboard
2. Go to "Paper Trading"
3. Select a strategy (e.g., "Momentum")
4. Choose symbols (e.g., AAPL, GOOGL)
5. Set initial capital (e.g., $100,000)
6. Click "Start Paper Trading"

---

## Dashboard

### Overview

The dashboard provides a comprehensive view of your trading activities:

**Main Features**:
- Real-time portfolio monitoring
- Live market data display
- Strategy performance tracking
- Trade execution interface
- Risk management tools

### Navigation

**Left Sidebar**:
- **Dashboard**: Overview and key metrics
- **Portfolio**: Current positions and allocation
- **Strategies**: Available trading strategies
- **Backtesting**: Historical simulation tools
- **Paper Trading**: Practice trading environment
- **Live Trading**: Real trading operations
- **Settings**: Configuration and preferences

### Key Metrics

**Portfolio Metrics**:
- Total Equity
- Daily P&L
- Unrealized P&L
- Win Rate
- Sharpe Ratio
- Max Drawdown

**Strategy Metrics**:
- Total Return
- Win Rate
- Average Win/Loss
- Profit Factor
- Maximum Consecutive Losses

---

## Portfolio Management

### Viewing Your Portfolio

1. Navigate to **Portfolio** in the sidebar
2. View your current positions
3. See portfolio allocation by asset
4. Check performance metrics

### Portfolio Metrics Explained

**Total Equity**: Total value of your portfolio (cash + positions)

**Cash Balance**: Available cash for trading

**Unrealized P&L**: Profit or loss on open positions

**Realized P&L**: Profit or loss from closed positions

**Win Rate**: Percentage of profitable trades

**Sharpe Ratio**: Risk-adjusted return measure

**Max Drawdown**: Largest peak-to-trough decline

### Managing Positions

**View Position Details**:
```bash
# Via API
curl http://localhost:8000/portfolio/positions/AAPL

# Via Dashboard
Click on a position symbol to see details
```

**Simulate a Trade**:
```bash
# Via API
curl -X POST http://localhost:8000/portfolio/simulate-trade \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "quantity": 10,
    "price": 150.00
  }'
```

---

## Strategy Development

### Available Strategies

The platform comes with several pre-built strategies:

1. **Momentum Strategy**
   - Identifies trending stocks
   - Buys when price breaks above resistance
   - Sells when momentum reverses

2. **Mean Reversion Strategy**
   - Identifies overbought/oversold conditions
   - Buys when price is below mean
   - Sells when price returns to mean

3. **Pairs Trading Strategy**
   - Identifies correlated stock pairs
   - Trades the spread between pairs
   - Market-neutral approach

4. **Breakout Strategy**
   - Detects price breakouts
   - Trades momentum continuation
   - Uses volatility filters

### Strategy Parameters

Each strategy has configurable parameters:

**Momentum Strategy**:
- `lookback_period`: Period for momentum calculation (default: 20)
- `threshold`: Minimum price change % (default: 0.02)
- `stop_loss`: Stop loss % (default: 0.05)
- `take_profit`: Take profit % (default: 0.10)

**Mean Reversion Strategy**:
- `lookback_period`: Period for mean calculation (default: 20)
- `std_threshold`: Standard deviation threshold (default: 2.0)
- `entry_threshold`: Entry signal threshold (default: 0.05)

### Creating Custom Strategies

1. **Create Strategy File**:
```python
# app/strategies/my_strategy.py
from app.strategies.base import BaseStrategy
from typing import List, Dict
import pandas as pd

class MyCustomStrategy(BaseStrategy):
    """
    My custom trading strategy.
    """

    def __init__(self, param1: int = 10, param2: float = 0.05):
        self.param1 = param1
        self.param2 = param2

    def generate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """
        Generate trading signals.

        Args:
            data: Historical price data

        Returns:
            List of trading signals
        """
        signals = []

        # Your strategy logic here
        # Example: Buy when price increases by param2%
        for i in range(self.param1, len(data)):
            if data['close'].iloc[i] > data['close'].iloc[i-self.param1] * (1 + self.param2):
                signals.append({
                    'date': data.index[i],
                    'symbol': data['symbol'].iloc[0],
                    'action': 'buy',
                    'price': data['close'].iloc[i],
                    'confidence': 0.8
                })

        return signals
```

2. **Register Strategy**:
```python
# app/strategies/registry.py
from app.strategies.my_strategy import MyCustomStrategy

register_strategy("my_custom", MyCustomStrategy)
```

3. **Create Configuration**:
```yaml
# config/strategies/my_custom.yaml
strategy:
  name: "my_custom"
  parameters:
    param1: 10
    param2: 0.05

risk:
  max_position_size: 0.05
  stop_loss: 0.03
```

---

## Backtesting

### Running a Backtest

**Via Dashboard**:
1. Navigate to **Backtesting**
2. Select strategy
3. Choose symbols
4. Set date range
5. Configure parameters
6. Click "Run Backtest"

**Via API**:
```bash
curl -X POST http://localhost:8000/backtesting/run \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "momentum",
    "symbols": ["AAPL", "GOOGL"],
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "initial_capital": 100000,
    "parameters": {
      "lookback_period": 20,
      "threshold": 0.02
    }
  }'
```

**Via Python**:
```python
from app.backtesting.engine import BacktestEngine
from app.strategies.momentum import MomentumStrategy
import pandas as pd

# Initialize
engine = BacktestEngine(
    initial_capital=100000,
    strategy=MomentumStrategy()
)

# Load data
data = pd.read_csv('data/AAPL.csv', parse_dates=['date'])

# Run backtest
results = engine.run(data)

# View results
print(f"Total Return: {results['total_return']:.2%}")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {results['max_drawdown']:.2%}")
```

### Understanding Backtest Results

**Performance Metrics**:

- **Total Return**: Overall profit/loss percentage
- **Annual Return**: Return annualized
- **Sharpe Ratio**: Risk-adjusted return (higher is better)
- **Sortino Ratio**: Downside risk-adjusted return
- **Max Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of winning trades
- **Profit Factor**: Gross wins / Gross losses
- **Average Trade**: Average profit/loss per trade

**Trade Analysis**:
- Total trades executed
- Winning vs losing trades
- Average holding period
- Best and worst trades

### Backtesting Best Practices

1. **Use Sufficient Data**: At least 2-3 years of historical data
2. **Account for Costs**: Include commissions and slippage
3. **Avoid Overfitting**: Don't optimize too much on historical data
4. **Walk-Forward Testing**: Use out-of-sample testing
5. **Multiple Markets**: Test across different market conditions

---

## Paper Trading

### What is Paper Trading?

Paper trading allows you to test strategies in a simulated environment without real money. It's essential for:
- Testing new strategies
- Building confidence
- Understanding platform features
- Validating backtest results

### Starting a Paper Trading Session

**Via Dashboard**:
1. Navigate to **Paper Trading**
2. Click "New Session"
3. Configure:
   - Initial capital
   - Strategy
   - Symbols
   - Risk parameters
4. Click "Start"

**Via API**:
```bash
curl -X POST http://localhost:8000/paper-trading/start \
  -H "Content-Type: application/json" \
  -d '{
    "initial_capital": 100000,
    "strategy": "momentum",
    "symbols": ["AAPL", "GOOGL", "MSFT"]
  }'
```

### Monitoring Paper Trading

**Real-Time Metrics**:
- Current portfolio value
- Open positions
- Realized P&L
- Win rate
- Number of trades

**Trade Log**:
- All executed trades
- Entry/exit prices
- Trade duration
- Profit/loss per trade

### Stopping Paper Trading

**Via Dashboard**: Click "Stop Session"

**Via API**:
```bash
curl -X POST http://localhost:8000/paper-trading/stop \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "paper_20240101_120000"
  }'
```

### Paper Trading Tips

1. **Trade Seriously**: Treat it like real money
2. **Follow Your Rules**: Stick to your strategy
3. **Track Everything**: Keep detailed records
4. **Review Regularly**: Analyze your performance
5. **Test Long Enough**: At least 1-2 months of paper trading

---

## Live Trading

### Pre-Live Trading Checklist

Before going live, ensure:

- [ ] Strategy thoroughly backtested
- [ ] Paper trading profitable for 1-2 months
- [ ] Risk parameters properly configured
- [ ] Broker account funded and connected
- [ ] Emergency procedures in place
- [ ] Monitoring alerts configured

### Connecting Your Broker

**Supported Brokers**:
- Alpaca (US stocks)
- Interactive Brokers (Global markets)
- More coming soon

**Alpaca Setup**:
```bash
# Set environment variables
ALPACA_API_KEY="your-api-key"
ALPACA_API_SECRET="your-api-secret"
ALPACA_BASE_URL="https://api.alpaca.markets"  # or paper-api for testing
```

### Starting Live Trading

**Via Dashboard**:
1. Navigate to **Live Trading**
2. Review pre-flight checklist
3. Configure:
   - Strategy
   - Symbols
   - Risk parameters
   - Position sizing
4. Click "Start Live Trading"

**Via API**:
```bash
curl -X POST http://localhost:8000/live-trading/start \
  -H "Content-Type: application/json" \
  -d '{
    "broker": "alpaca",
    "strategy": "momentum",
    "symbols": ["AAPL", "GOOGL"],
    "risk_parameters": {
      "max_position_size": 0.05,
      "max_daily_loss": 0.02,
      "stop_loss": 0.03
    }
  }'
```

### Live Trading Risk Management

**Essential Risk Controls**:

1. **Max Position Size**: Limit per position (e.g., 5% of portfolio)
2. **Max Daily Loss**: Stop trading if loss exceeded (e.g., 2%)
3. **Stop Loss**: Automatic exit if price moves against you (e.g., 3%)
4. **Max Open Positions**: Limit number of concurrent positions
5. **Drawdown Limit**: Reduce sizing if drawdown exceeded

### Emergency Procedures

**Stop All Trading Immediately**:
```bash
# Via API
curl -X POST http://localhost:8000/live-trading/emergency-stop

# Via Dashboard
Click "EMERGENCY STOP" button
```

**Close All Positions**:
```bash
curl -X POST http://localhost:8000/live-trading/close-all-positions
```

---

## Monitoring & Alerts

### Setting Up Alerts

**Via Dashboard**:
1. Navigate to **Settings** → **Alerts**
2. Click "Add Alert"
3. Configure:
   - Alert type (price, portfolio, trade)
   - Condition (e.g., price > $150)
   - Notification method (email, webhook)
4. Save

**Alert Types**:
- **Price Alerts**: When stock hits target price
- **Portfolio Alerts**: When portfolio value changes by X%
- **Trade Alerts**: When trades are executed
- **Risk Alerts**: When risk limits approached
- **System Alerts**: When system issues occur

### Monitoring Metrics

**Real-Time Dashboard**:
- Portfolio value
- Open positions
- Daily P&L
- Active trades
- System health

**Performance Reports**:
- Daily/weekly/monthly summaries
- Trade-by-trade analysis
- Strategy performance
- Risk metrics

### Exporting Data

**Export Trades**:
```bash
curl http://localhost:8000/portfolio/trades/export?format=csv
```

**Export Performance**:
```bash
curl http://localhost:8000/portfolio/performance/export?format=json
```

---

## Best Practices

### Strategy Development

1. **Start Simple**: Begin with basic strategies
2. **Test Thoroughly**: Backtest and paper trade extensively
3. **Risk First**: Always prioritize risk management
4. **Keep Records**: Document all decisions and results
5. **Review Regularly**: Analyze performance and improve

### Risk Management

1. **Never Risk More Than You Can Afford to Lose**
2. **Use Stop Losses**: Always have exit points
3. **Diversify**: Don't put all eggs in one basket
4. **Position Sizing**: Risk small percentage per trade (1-2%)
5. **Monitor Daily**: Check positions and system daily

### Trading Psychology

1. **Stay Disciplined**: Follow your rules
2. **Control Emotions**: Don't let fear/greed drive decisions
3. **Accept Losses**: Losses are part of trading
4. **Keep Learning**: Continuously improve
5. **Take Breaks**: Step away when needed

---

## Troubleshooting

### Common Issues

**Issue**: Dashboard not loading

**Solution**:
```bash
# Check if server is running
curl http://localhost:8000/health

# Restart dashboard
python app/dashboard/main.py
```

**Issue**: No trading signals generated

**Solution**:
- Check market data is current
- Verify strategy parameters
- Review signal generation conditions
- Check logs for errors

**Issue**: Paper trading not executing trades

**Solution**:
- Verify sufficient capital
- Check risk parameters
- Review circuit breaker status
- Check logs for errors

**Issue**: Live trading stopped unexpectedly

**Solution**:
- Check broker connection
- Review system logs
- Verify API credentials
- Check circuit breakers

### Getting Help

**Documentation**: See `docs/` directory

**API Docs**: http://localhost:8000/docs

**Logs**: Check `logs/` directory

**Support**:
- Email: support@algotrading.com
- GitHub Issues: github.com/algotrading/issues
- Discord: discord.gg/algotrading

---

## Glossary

- **Ask**: Lowest price a seller is willing to accept
- **Bid**: Highest price a buyer is willing to pay
- **Drawdown**: Peak-to-trough decline in portfolio value
- **Equity**: Total value of portfolio (cash + positions)
- **Long**: Buying a security expecting price to rise
- **Margin**: Borrowed money to trade
- **P&L**: Profit and Loss
- **Position**: Ownership of a security
- **Short**: Selling a security expecting price to fall
- **Spread**: Difference between bid and ask
- **Volatility**: Rate of price change
- **Volume**: Number of shares traded

---

## FAQ

**Q: Minimum capital to start?**
A: For paper trading, any amount. For live trading, minimum $25,000 for pattern day trading in the US.

**Q: How long to learn?**
A: Basic usage: 1-2 weeks. Profitable trading: 6-12 months of consistent learning and practice.

**Q: Can I use multiple strategies?**
A: Yes! You can run multiple strategies simultaneously with proper capital allocation.

**Q: What markets can I trade?**
A: Currently US stocks via Alpaca. More markets coming soon.

**Q: Is my data secure?**
A: Yes, we use encryption and follow security best practices. Your API keys are encrypted at rest.

---

## Next Steps

1. **Complete the tutorials**
2. **Practice with paper trading**
3. **Join our community**
4. **Share your strategies**
5. **Continuous learning**

Happy trading! 📈
