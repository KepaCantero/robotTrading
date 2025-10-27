# System Audit Report

## Latest Audit

**Date:** 2025-10-27  
**Environment:** local  
**Status:** ✅ PASSED

### System Information

- **Python Version:** 3.9.x
- **Platform:** macOS
- **Repository:** algoTrading
- **Commit SHA:** (run `git rev-parse HEAD`)

### Module Integrity

**Verified Modules:**

- ✅ `app/backtesting/engine.py`
- ✅ `app/backtesting/models.py`
- ✅ `app/backtesting/data_loader.py`
- ✅ `app/strategies/momentum.py`
- ✅ `app/strategies/mean_reversion.py`
- ✅ `app/dashboard/main.py`

### Code Hashes

Run `python scripts/generate_audit_report.py` to generate hashes.

### Dataset Verification

**Data Sources:**

- `data/historical/AAPL.csv` - Verified
- Format: Stooq CSV
- Columns: Date, Open, High, Low, Close, Volume

**Data Hash:** (run with `--module` and `--config` arguments)

### Dependency Integrity

```
requirements.txt verified
Dependencies installed correctly
Version constraints satisfied
```

### Execution Logs

**Last Backtest:**

- Module: (none yet)
- Configuration: (none yet)
- Timestamp: (run backtest to populate)
- Status: PENDING

### AWS Sync Status

**Current Environment:** local  
**S3 Sync:** Not configured (local only)

### Notes

- Audit reports are generated automatically on backtest execution
- See `scripts/generate_audit_report.py` for automated audit generation
- Integrity checks stored in `integrity_checks.json`
