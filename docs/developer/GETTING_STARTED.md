# Getting Started Guide

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.9 or higher**
- **Git**
- **Virtual Environment Tool** (venv or conda)
- **PostgreSQL** (optional, for production database)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/algoTrading.git
cd algoTrading
```

### 2. Create Virtual Environment

**Using venv:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

**Using conda:**
```bash
conda create -n algotrading python=3.9
conda activate algotrading
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Copy the example environment file:

```bash
cp env.example .env
```

Edit `.env` with your configuration:

```bash
# Application
DEBUG=true
APP_NAME="AlgoTrading MVP"
SECRET_KEY="your-secret-key-change-in-production"

# Database
DATABASE_URL="sqlite:///./data/trading.db"

# Trading APIs (Optional for development)
ALPACA_API_KEY="your-alpaca-key"
ALPACA_API_SECRET="your-alpaca-secret"
```

### 5. Initialize Database

```bash
# Run migrations
alembic upgrade head

# Or create fresh database
python -c "from app.core.database import init_db; init_db()"
```

### 6. Verify Installation

```bash
# Run tests
pytest

# Start API server
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` to see the API documentation.

---

## Quick Start

### 1. Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 2. Run a Simple Backtest

```python
from app.backtesting.engine import BacktestEngine
from app.strategies.momentum import MomentumStrategy
import pandas as pd

# Initialize backtest engine
engine = BacktestEngine(
    initial_capital=100000,
    strategy=MomentumStrategy()
)

# Load data
data = pd.read_csv('data/AAPL.csv', parse_dates=['date'])

# Run backtest
results = engine.run(data)

# Print results
print(f"Total Return: {results['total_return']:.2%}")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {results['max_drawdown']:.2%}")
```

### 3. Generate Trading Signals

```python
from app.services.market_data_service import MarketDataService
from app.strategies.momentum import MomentumStrategy

# Initialize services
data_service = MarketDataService()
strategy = MomentumStrategy()

# Fetch data
data = await data_service.get_data('AAPL', period='1y')

# Generate signals
signals = strategy.generate_signals(data)

for signal in signals:
    print(f"{signal['date']}: {signal['action']} {signal['symbol']}")
```

---

## Project Structure

```
algoTrading/
├── app/                          # Main application code
│   ├── api/                      # API endpoints
│   ├── backtesting/              # Backtesting engine
│   ├── core/                     # Core functionality
│   ├── data/                     # Data management
│   ├── engines/                  # Trading engines
│   ├── models/                   # Data models
│   ├── services/                 # Business logic
│   ├── strategies/               # Trading strategies
│   └── main.py                   # Application entry point
├── tests/                        # Test suite
├── docs/                         # Documentation
├── scripts/                      # Utility scripts
├── data/                         # Data files
├── requirements.txt              # Dependencies
├── .env                          # Environment variables
└── README.md                     # This file
```

---

## Development Workflow

### 1. Feature Development

```bash
# Create feature branch
git checkout -b feature/my-new-feature

# Make changes
# ... (code changes)

# Run tests
pytest

# Commit changes
git add .
git commit -m "Add my new feature"

# Push to remote
git push origin feature/my-new-feature
```

### 2. Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_backtesting.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_backtesting.py::test_backtest_engine

# Run with verbose output
pytest -v
```

### 3. Code Formatting

```bash
# Format code with black
black app/ tests/

# Sort imports with isort
isort app/ tests/

# Check linting
flake8 app/ tests/

# Type checking
mypy app/
```

---

## Configuration

### Environment Variables

Key environment variables in `.env`:

```bash
# Application
DEBUG=true                    # Debug mode
LOG_LEVEL=INFO               # Logging level
APP_NAME="AlgoTrading MVP"   # Application name

# API
API_PREFIX="/api"            # API URL prefix
CORS_ORIGINS=["*"]           # CORS allowed origins

# Database
DATABASE_URL="sqlite:///./data/trading.db"  # Database URL

# Trading APIs
ALPACA_API_KEY=""            # Alpaca API key
ALPACA_API_SECRET=""         # Alpaca API secret
ALPACA_BASE_URL="https://paper-api.alpaca.markets"  # Alpaca base URL

# Alpha Vantage
ALPHA_VANTAGE_API_KEY=""     # Alpha Vantage API key

# Cache
REDIS_URL="redis://localhost:6379/0"  # Redis URL
```

### Strategy Configuration

Configure strategies in YAML files:

```yaml
# config/strategies/momentum.yaml
strategy:
  name: "momentum"
  parameters:
    lookback_period: 20
    threshold: 0.02
    stop_loss: 0.05
    take_profit: 0.10

risk:
  max_position_size: 0.05
  max_daily_loss: 0.02
```

---

## Common Tasks

### Adding a New Strategy

1. Create strategy file:

```python
# app/strategies/my_strategy.py
from app.strategies.base import BaseStrategy

class MyStrategy(BaseStrategy):
    def generate_signals(self, data):
        # Your logic here
        pass
```

2. Register strategy:

```python
# app/strategies/registry.py
from app.strategies.my_strategy import MyStrategy

register_strategy("my_strategy", MyStrategy)
```

3. Add configuration:

```yaml
# config/strategies/my_strategy.yaml
strategy:
  name: "my_strategy"
  parameters:
    param1: 10
    param2: 0.05
```

### Adding a New API Endpoint

1. Create router file:

```python
# app/api/my_endpoints.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/my-endpoint", tags=["my-endpoint"])

class MyRequest(BaseModel):
    param1: str
    param2: int

@router.post("/")
async def my_endpoint(request: MyRequest):
    # Your logic here
    return {"status": "success"}
```

2. Register router:

```python
# app/main.py
from app.api.my_endpoints import router as my_router

app.include_router(my_router)
```

### Adding Database Models

1. Create model:

```python
# app/database/models/my_model.py
from sqlalchemy import Column, Integer, String
from app.database.base import Base

class MyModel(Base):
    __tablename__ = "my_table"

    id = Column(Integer, primary_key=True)
    name = Column(String)
```

2. Create migration:

```bash
alembic revision --autogenerate -m "Add my_model"
alembic upgrade head
```

---

## Testing

### Writing Tests

```python
# tests/test_my_feature.py
import pytest
from app.services.my_service import MyService

def test_my_service():
    service = MyService()
    result = service.do_something()
    assert result == expected_value

@pytest.mark.asyncio
async def test_async_service():
    service = MyService()
    result = await service.do_something_async()
    assert result == expected_value
```

### Test Fixtures

```python
# tests/conftest.py
import pytest
from app.main import app
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_data():
    return {
        "symbol": "AAPL",
        "price": 150.0
    }
```

---

## Debugging

### Enable Debug Mode

Set in `.env`:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

### Using Python Debugger

```python
import pdb; pdb.set_trace()

# Or using ipdb (if installed)
import ipdb; ipdb.set_trace()
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

---

## Performance Optimization

### Profiling

```python
import cProfile
import pstats

def profile_function():
    pr = cProfile.Profile()
    pr.enable()

    # Your code here
    result = my_function()

    pr.disable()
    stats = pstats.Stats(pr)
    stats.sort_stats('cumulative')
    stats.print_stats(10)

    return result
```

### Database Optimization

1. Use indexes:
```python
class MyModel(Base):
    __tablename__ = "my_table"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True)  # Add index
    timestamp = Column(DateTime, index=True)  # Add index
```

2. Use connection pooling:
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)
```

---

## Troubleshooting

### Common Issues

**Issue**: ModuleNotFoundError

**Solution**:
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Issue**: Port already in use

**Solution**:
```bash
# Use different port
uvicorn app.main:app --port 8001

# Or kill existing process
lsof -ti:8000 | xargs kill -9
```

**Issue**: Database connection error

**Solution**:
```bash
# Check database file exists
ls -la data/trading.db

# Reinitialize database
python -c "from app.core.database import init_db; init_db()"
```

---

## Next Steps

1. **Read the documentation**:
   - [API Reference](./api/API_REFERENCE.md)
   - [Architecture](./developer/ARCHITECTURE.md)

2. **Explore examples**:
   - `examples/` directory

3. **Run the tutorials**:
   - [Tutorial 1: Your First Strategy](./tutorials/tutorial_01.md)
   - [Tutorial 2: Backtesting](./tutorials/tutorial_02.md)

4. **Join the community**:
   - GitHub Discussions
   - Discord server

---

## Getting Help

- **Documentation**: See `docs/` directory
- **API Docs**: http://localhost:8000/docs
- **Issues**: GitHub Issues
- **Email**: support@algotrading.com

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Python Documentation](https://docs.python.org/3/)
- [pandas Documentation](https://pandas.pydata.org/docs/)
- [pytest Documentation](https://docs.pytest.org/)

Happy trading! 🚀
