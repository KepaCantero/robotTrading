# AlgoTrading System - Dependencies Summary

**Last Updated:** 2026-01-28
**Principle:** "If it's in the code, it's REQUIRED. No optional dependencies."

---

## Quick Reference

### Installation Commands

```bash
# Production installation
pip install -r requirements.txt

# Development installation
pip install -r requirements-dev.txt

# Verify installation
python verify_dependencies.py
```

### File Locations

- **Production Dependencies:** `/requirements.txt`
- **Development Dependencies:** `/requirements-dev.txt`
- **Installation Guide:** `/INSTALLATION_GUIDE.md`
- **Verification Script:** `/verify_dependencies.py`
- **Test Report:** `/INSTALLATION_TEST_REPORT.md`

---

## Dependency Categories

### 1. Core Web Framework (7 packages)
- fastapi, uvicorn, starlette, pydantic, pydantic-settings, python-multipart

### 2. Database & Persistence (6 packages)
- sqlalchemy, alembic, psycopg2-binary, aiosqlite, asyncpg, greenlet

### 3. Data Processing (3 packages)
- **pandas** (2.0.0-3.0.0)
- **numpy** (1.24.0-1.27.0) - <2.0 REQUIRED for compatibility
- **scipy** (1.11.0-2.0.0)

### 4. Statistical Modeling (3 packages)
- **statsmodels** (0.14.0-1.0.0) - Cointegration tests
- **arch** (6.0.0-8.0.0) - GARCH volatility
- **hmmlearn** (0.9.0-1.0.0) - Regime detection

### 5. Performance Acceleration (2 packages) - CRITICAL
- **numba** (0.59.0-1.0.0) - NO FALLBACKS, MANDATORY
- **llvmlite** (0.40.0-1.0.0) - Required for Numba

### 6. Technical Analysis (2 packages)
- **pandas-ta-classic** (0.3.36-1.0.0)
- **pandas-ta** (0.3.14-1.0.0)

### 7. Machine Learning (5 packages)
- **scikit-learn** (1.3.0-2.0.0)
- **xgboost** (2.0.0-3.0.0)
- **lightgbm** (4.0.0-5.0.0)
- **catboost** (1.2.0-2.0.0)
- **shap** (0.42.0-1.0.0)

### 8. Deep Learning (3 packages)
- **torch** (2.0.0-3.0.0)
- **torchvision** (0.15.0-1.0.0)
- **tensorflow** (2.13.0-3.0.0)

### 9. Reinforcement Learning (3 packages)
- **stable-baselines3** (2.0.0-3.0.0)
- **gym** (0.26.0-1.0.0)
- **gymnasium** (0.29.0-1.0.0)

### 10. Optimization (3 packages)
- **optuna** (3.4.0-4.0.0)
- **pypfopt** (1.3.0-2.0.0)
- **cvxpy** (1.4.0-2.0.0)

### 11. Market Data (3 packages)
- **yfinance** (0.2.28-1.0.0)
- **yahoo-fin** (0.8.9-1.0.0)
- **requests-html** (0.10.0-1.0.0)

### 12. HTTP Clients (5 packages)
- **httpx** (0.25.0-0.28.0)
- **requests** (2.31.0-3.0.0)
- **aiohttp** (3.8.0-4.0.0)
- **websockets** (10.0-13.0)
- **aiofiles** (23.0.0-24.0.0)

### 13. Broker APIs (3 packages)
- **alpaca-trade-api** (3.0.0-4.0.0)
- **alpaca-py** (0.8.0-1.0.0)
- **ib-insync** (0.5.0-1.0.0)

### 14. Caching & Messaging (2 packages)
- **redis** (5.0.0-6.0.0)
- **pyzmq** (25.0.0-26.0.0)

### 15. Configuration (3 packages)
- **pyyaml** (6.0-7.0.0)
- **python-dotenv** (1.0.0-2.0.0)
- **jinja2** (3.1.0-4.0.0)

### 16. Serialization (2 packages)
- **msgpack** (1.0.0-2.0.0)
- **joblib** (1.3.0-2.0.0)

### 17. Logging (2 packages)
- **python-json-logger** (2.0.0-3.0.0)
- **structlog** (23.0.0-24.0.0)

### 18. Monitoring (4 packages)
- **psutil** (5.9.0-6.0.0)
- **ntplib** (0.4.0-1.0.0)
- **tenacity** (8.2.0-9.0.0)
- **tqdm** (4.66.0-5.0.0)

### 19. Notifications (1 package)
- **aiosmtplib** (3.0.0-4.0.0)

### 20. Security (2 packages)
- **cryptography** (41.0.0-43.0.0)
- **pynacl** (1.5.0-2.0.0)

### 21. Analytics (3 packages)
- **quantstats** (0.0.62-1.0.0)
- **empyrical-reloaded** (0.5.0-1.0.0)
- **pyfolio-reloaded** (0.9.5-1.0.0)

### 22. Visualization (4 packages)
- **matplotlib** (3.7.0-4.0.0)
- **seaborn** (0.13.0-1.0.0)
- **plotly** (5.18.0-6.0.0)
- **networkx** (3.2.0-4.0.0)

### 23. Dashboard (1 package)
- **streamlit** (1.31.0-2.0.0)

### 24. Time & Timezone (3 packages)
- **pytz** (2023.3-2025.0)
- **tzlocal** (5.0-6.0)
- **nest-asyncio** (1.5.0-2.0.0)

### 25. Cloud Storage (2 packages)
- **boto3** (1.28.0-2.0.0)
- **botocore** (1.31.0-2.0.0)

### 26. Time-Series Database (1 package)
- **questdb** (1.2.0-2.0.0)

### 27. External Integrations (2 packages)
- **tweepy** (4.14.0-5.0.0)
- **beautifulsoup4** (4.12.0-5.0.0)

---

## Total Count

- **Production Dependencies:** ~75 packages
- **Development Dependencies:** ~50 packages
- **Total Unique Packages:** ~125 packages

---

## Critical Dependencies (System Will NOT Work Without These)

1. **Python** 3.9-3.13
2. **NumPy** <2.0.0 (for compatibility)
3. **Pandas** 2.0.0+
4. **Numba** 0.59.0+ (MANDATORY - NO FALLBACKS)
5. **SciPy** 1.11.0+
6. **scikit-learn** 1.3.0+

---

## Known Compatibility Issues

### 1. NumPy 2.x Incompatibility
- **Affected:** stable-baselines3, pandas-ta
- **Solution:** Pin NumPy to <2.0.0
- **Status:** ✅ FIXED in requirements.txt

### 2. PyTorch CUDA Versions
- **Issue:** CUDA version must match PyTorch version
- **Solution:** Install specific PyTorch wheel for your CUDA version
- **Status:** ✅ Documented in INSTALLATION_GUIDE.md

### 3. TensorFlow Size
- **Issue:** TensorFlow is ~500MB
- **Solution:** Use tensorflow-cpu for smaller installation
- **Status:** ✅ Documented in INSTALLATION_GUIDE.md

---

## Installation Verification

### Run the verification script:
```bash
python verify_dependencies.py
```

### Expected output:
```
RESULT: SUCCESS - All dependencies verified
```

### If errors occur:
1. Check INSTALLATION_GUIDE.md for troubleshooting
2. Check INSTALLATION_TEST_REPORT.md for known issues
3. Run with verbose output: `python verify_dependencies.py -v`

---

## Development Setup

### Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

### Install pre-commit hooks:
```bash
pre-commit install
```

### Run tests:
```bash
pytest tests/
```

### Run linting:
```bash
ruff check app/
black app/
mypy app/
```

---

## Update Policy

### Version Updates
- **Monthly:** Check for security updates
- **Quarterly:** Review all dependency updates
- **Annually:** Major version upgrades

### Update Process
1. Test updates in development environment
2. Run verify_dependencies.py
3. Run full test suite
4. Update requirements.txt
5. Document changes in DEPENDENCIES_SUMMARY.md

---

## Support

### Documentation Files
- `requirements.txt` - Production dependencies
- `requirements-dev.txt` - Development dependencies
- `INSTALLATION_GUIDE.md` - Step-by-step installation
- `INSTALLATION_TEST_REPORT.md` - Test results
- `DEPENDENCIES_SUMMARY.md` - This file

### Getting Help
1. Check INSTALLATION_GUIDE.md for common issues
2. Run verify_dependencies.py for diagnostics
3. Check GitHub Issues for known problems
4. Create new issue with details

---

## Best Practices

1. **Always use virtual environments**
2. **Never mix Python versions**
3. **Pin dependency versions**
4. **Verify after installation**
5. **Update regularly**
6. **Test thoroughly**
7. **Document changes**

---

**Remember:** "If it's in the code, it's REQUIRED. No optional dependencies."

---

*Last Updated: 2026-01-28*
*Maintained by: AlgoTrading System Team*
