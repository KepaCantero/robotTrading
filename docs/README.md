# 📊 AlgoTrading Documentation & Audit System

## 🎯 Purpose

This documentation and auditing system provides comprehensive tracking, reproducibility, and verification capabilities for the AlgoTrading modular platform.

## 🏗️ System Overview

The AlgoTrading system is a modular algorithmic trading platform with:
- **Backtesting Engine**: Historical simulation and performance evaluation
- **Dashboard**: Interactive visualization and module comparison
- **Trading Modules**: Signal generators, risk managers, execution engines
- **Audit Layer**: Integrity verification and reproducibility tracking

## 📁 Directory Structure

```
/docs
├── README.md                      # This file - overview
├── SYSTEM_OVERVIEW.md             # Architecture details
├── MODULES/                       # Module documentation
│   ├── module_momentum.md
│   ├── module_momentum_parameters.json
│   └── ...
├── BACKTEST_RESULTS/              # Backtest documentation
│   ├── summary_index.md
│   └── {module_name}/
│       ├── config_{name}_report.md
│       ├── trade_log.csv
│       ├── metrics.json
│       └── equity_curve.png
├── AUDIT_LOGS/                   # Audit trails
│   ├── system_audit.md
│   ├── integrity_checks.json
│   └── reproducibility_tests.md
├── VERSION_HISTORY.md             # Version changes
└── DATA_SOURCES.md                # Data provenance
```

## 🚀 Quick Start

### Running Backtests

```bash
# Via dashboard
./run_dashboard.py

# Via script
python scripts/run_backtest.py --module momentum --config moderate
```

### Viewing Results

- **Dashboard**: http://localhost:8503
- **Results**: `docs/BACKTEST_RESULTS/`
- **Audit Logs**: `docs/AUDIT_LOGS/`

## 📖 Documentation Sections

1. **[SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)**: Architecture and components
2. **[MODULES/](./MODULES/)**: Individual module documentation
3. **[BACKTEST_RESULTS/](./BACKTEST_RESULTS/)**: Backtest reports and data
4. **[AUDIT_LOGS/](./AUDIT_LOGS/)**: Integrity verification and audit trails

## 🔍 Audit & Reproducibility

Every backtest execution:
- ✅ Generates SHA256 hashes of code
- ✅ Records exact parameters and versions
- ✅ Saves complete trade logs and metrics
- ✅ Enables full reproducibility

See [AUDIT_LOGS/](./AUDIT_LOGS/) for detailed audit information.

## 📞 Support

For questions about:
- **Module functionality**: See `MODULES/`
- **Backtest results**: See `BACKTEST_RESULTS/`
- **System integrity**: See `AUDIT_LOGS/`
- **Architecture**: See `SYSTEM_OVERVIEW.md`

