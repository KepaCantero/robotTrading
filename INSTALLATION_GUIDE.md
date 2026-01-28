# AlgoTrading System - Installation Guide

**Last Updated:** 2026-01-28
**Python Version:** >= 3.9, < 3.14
**Principle:** "If it's in the code, it's REQUIRED. No optional dependencies."

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Quick Start Installation](#quick-start-installation)
3. [Detailed Installation Steps](#detailed-installation-steps)
4. [Platform-Specific Instructions](#platform-specific-instructions)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)
7. [Development Setup](#development-setup)

---

## System Requirements

### Hardware Requirements

- **RAM:** Minimum 8GB, Recommended 16GB+ (ML/DL workloads need more)
- **Storage:** Minimum 10GB free space (for models and data)
- **CPU:** Any modern 64-bit processor (AVX2+ recommended for Numba)

### Software Requirements

- **Python:** 3.9, 3.10, 3.11, 3.12, or 3.13 (NOT 3.14+)
- **pip:** Latest version (upgrade with `python -m pip install --upgrade pip`)
- **git:** For cloning the repository
- **Virtual Environment:** Strongly recommended (venv or conda)

### Operating System Support

- **Linux:** Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+
- **macOS:** 10.15+ (Catalina or later)
- **Windows:** Windows 10/11 with WSL2 (native Windows NOT recommended)

---

## Quick Start Installation

### For Production (Minimal)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/algoTrading.git
cd algoTrading

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Upgrade pip
python -m pip install --upgrade pip

# 4. Install dependencies
pip install -r requirements.txt

# 5. Verify installation
python verify_dependencies.py
```

### For Development

```bash
# Follow steps 1-4 above, then:
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

---

## Detailed Installation Steps

### Step 1: Install Python

#### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip
```

#### macOS

```bash
# Using Homebrew
brew install python@3.11
```

#### Windows (WSL2)

```bash
# Enable WSL2 in PowerShell (Admin)
wsl --install

# Then in WSL Ubuntu:
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip
```

### Step 2: Install System Dependencies

#### Linux (Ubuntu/Debian)

```bash
# PostgreSQL client library (required for psycopg2)
sudo apt install -y libpq-dev

# LLVM for Numba compilation
sudo apt install -y llvm-11-dev

# Build essentials
sudo apt install -y build-essential

# For TensorFlow (optional)
sudo apt install -y libcudnn8 libcudnn8-dev

# For PyTorch (optional)
sudo apt install -y libtorch-dev
```

#### macOS

```bash
# Install Xcode Command Line Tools
xcode-select --install

# Install LLVM for Numba
brew install llvm@11

# Install PostgreSQL client
brew install postgresql
```

### Step 3: Create and Activate Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### Step 4: Upgrade pip and Install Wheel

```bash
python -m pip install --upgrade pip setuptools wheel
```

### Step 5: Install Production Dependencies

```bash
pip install -r requirements.txt
```

**Note:** This may take 10-30 minutes depending on your internet connection and system. PyTorch and TensorFlow are large packages.

### Step 6: Verify Installation

```bash
python verify_dependencies.py
```

Expected output:
```
RESULT: SUCCESS - All dependencies verified
```

---

## Platform-Specific Instructions

### Linux (Ubuntu/Debian)

#### PostgreSQL Setup

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql
CREATE DATABASE algotrading;
CREATE USER algotrading WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE algotrading TO algotrading;
\q
```

#### Redis Setup

```bash
# Install Redis
sudo apt install -y redis-server

# Start service
sudo systemctl start redis
sudo systemctl enable redis
```

#### QuestDB Setup (Optional, for metrics)

```bash
# Download and install QuestDB
curl -O https://github.com/questdb/questdb/releases/latest/download/questdb-7.3.1-linux-x64.tar.gz
tar -xzf questdb-7.3.1-linux-x64.tar.gz
cd questdb-7.3.1-linux-x64
./bin/questdb.sh start
```

### macOS

#### PostgreSQL Setup

```bash
# Install PostgreSQL
brew install postgresql@15

# Start service
brew services start postgresql@15

# Create database
createdb algotrading
```

#### Redis Setup

```bash
# Install Redis
brew install redis

# Start service
brew services start redis
```

### Windows (WSL2)

Follow Linux instructions above within WSL2.

---

## Verification

### Basic Verification

```bash
# Run the verification script
python verify_dependencies.py
```

### Manual Verification

```bash
# Test Python version
python --version  # Should be 3.9-3.13

# Test critical packages
python -c "import numpy; print(f'NumPy: {numpy.__version__}')"
python -c "import pandas; print(f'Pandas: {pandas.__version__}')"
python -c "import numba; print(f'Numba: {numba.__version__}')"

# Test Numba compilation
python -c "
from numba import njit
import numpy as np

@njit
def test(x):
    return x * 2

print('Numba JIT: OK')
result = test(np.array([1, 2, 3]))
print(f'Result: {result}')
"

# Test core imports
python -c "from app.core.numba_accelerators import calculate_rsi; print('Core accelerators: OK')"
python -c "from app.services.momentum_analysis import MomentumAnalysis; print('Momentum analysis: OK')"
```

### Test Database Connection

```bash
# Test PostgreSQL connection
python -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql://user:password@localhost:5432/algotrading')
conn = engine.connect()
print('PostgreSQL: OK')
conn.close()
"

# Test Redis connection
python -c "
import redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)
r.ping()
print('Redis: OK')
"
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: NumPy Version Conflicts

**Error:** `ImportError: numpy version X.Y.Z required, but Z.Y.X is installed`

**Solution:**
```bash
pip install --upgrade numpy
pip install --no-deps numba  # Reinstall numba without dependencies
```

#### Issue 2: Numba Compilation Fails

**Error:** `LLVM not found` or `numba.core.errors.TypingError`

**Solution:**
```bash
# Ubuntu/Debian
sudo apt install llvm-11-dev

# macOS
brew install llvm@11

# Then reinstall numba
pip uninstall llvmlite numba
pip install llvmlite numba
```

#### Issue 3: PostgreSQL Client Library Not Found

**Error:** `libpq-fe.h: No such file or directory`

**Solution:**
```bash
# Ubuntu/Debian
sudo apt install libpq-dev

# macOS
brew install postgresql

# Then reinstall psycopg2
pip uninstall psycopg2-binary
pip install psycopg2-binary
```

#### Issue 4: PyTorch/TensorFlow Installation Fails

**Error:** `Out of memory` or `Installation failed`

**Solution:**
```bash
# Install CPU-only versions (smaller, faster to install)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install tensorflow-cpu

# Or install specific versions that match your CUDA version
# See: https://pytorch.org/get-started/locally/
```

#### Issue 5: Permission Denied

**Error:** `Permission denied` when installing packages

**Solution:**
```bash
# NEVER use sudo pip install
# Instead, use a virtual environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Issue 6: SSL Certificate Errors

**Error:** `SSL: CERTIFICATE_VERIFY_FAILED`

**Solution:**
```bash
# Upgrade pip and certificates
pip install --upgrade pip certifi

# Or use trusted hosts (not recommended for production)
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### Getting Help

If you encounter issues not covered here:

1. Check the [GitHub Issues](https://github.com/your-org/algoTrading/issues)
2. Search the error message in the codebase
3. Run with verbose logging: `python -v your_script.py`
4. Check dependency versions: `pip list`

---

## Development Setup

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Install Pre-commit Hooks

```bash
pre-commit install
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/backtesting/test_fractional_differentiation.py

# Run with verbose output
pytest -v
```

### Code Quality Checks

```bash
# Type checking
mypy app/

# Linting
ruff check app/

# Formatting
black app/

# Import sorting
isort app/

# Security scan
bandit -r app/
```

### Running the Application

```bash
# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Dashboard
streamlit run app/dashboard/main.py
```

---

## Environment Configuration

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/algotrading

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys (if using live trading)
ALPACA_API_KEY=your_api_key
ALPACA_API_SECRET=your_api_secret
IB_HOST=localhost
IB_PORT=7497

# Time Series Database (optional)
QUESTDB_HOST=localhost
QUESTDB_PORT=8812

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/algotrading.log
```

---

## Performance Optimization

### Numba Compilation Cache

Numba caches compiled functions to speed up subsequent runs:

```bash
# Cache location
export NUMBA_CACHE_DIR=/tmp/numba_cache

# Pre-compile critical functions
python -c "from app.core.numba_accelerators import *"
```

### Memory Management

For large datasets, consider:

```bash
# Limit memory usage
export MALLOC_ARENA_MAX=2

# Use memory-mapped files for data
export NUMPY_MMAP=1
```

---

## Updating Dependencies

### Update Production Dependencies

```bash
# Check for updates
pip list --outdated

# Update specific package
pip install --upgrade package_name

# Update all (caution)
pip install --upgrade -r requirements.txt

# Verify after update
python verify_dependencies.py
```

### Update Development Dependencies

```bash
pip install --upgrade -r requirements-dev.txt
```

---

## Uninstallation

### Remove Virtual Environment

```bash
deactivate  # Exit virtual environment first
rm -rf venv
```

### Remove System Packages

```bash
# Ubuntu/Debian
sudo apt remove python3.11 python3.11-venv

# macOS
brew uninstall python@3.11
```

---

## Best Practices

1. **Always use virtual environments** - Never install packages globally
2. **Pin dependency versions** - Use the exact versions specified in requirements.txt
3. **Verify after installation** - Always run `verify_dependencies.py`
4. **Keep dependencies updated** - But test thoroughly before updating in production
5. **Use specific versions for deep learning** - PyTorch and TensorFlow versions matter
6. **Monitor for security updates** - Run `pip-audit` regularly
7. **Document custom installations** - Keep notes of any workarounds

---

## Additional Resources

- [Python Packaging User Guide](https://packaging.python.org/)
- [Virtual Environment Guide](https://docs.python.org/3/tutorial/venv.html)
- [Numba Installation Guide](https://numba.readthedocs.io/en/stable/user/installing.html)
- [PyTorch Installation](https://pytorch.org/get-started/locally/)
- [TensorFlow Installation](https://www.tensorflow.org/install)

---

## Support

For issues specific to this installation guide, please:

1. Check existing GitHub issues
2. Create a new issue with:
   - Python version
   - Operating system
   - Error message
   - Steps to reproduce
   - Output of `verify_dependencies.py`

---

**Remember:** "If it's in the code, it's REQUIRED. No optional dependencies."
