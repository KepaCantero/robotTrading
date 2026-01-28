# AlgoTrading System - Quick Start Guide

**Last Updated:** 2026-01-28
**Estimated Time:** 15-30 minutes

---

## Prerequisites

- Python 3.9-3.13 installed
- Internet connection
- 10GB free disk space

---

## Installation (3 Steps)

### Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/algoTrading.git
cd algoTrading

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

**Note:** This will take 10-30 minutes depending on your internet speed.

### Step 3: Verify Installation

```bash
# Run verification script
python verify_dependencies.py
```

Expected output:
```
RESULT: SUCCESS - All dependencies verified
```

---

## Run the Application

### Start API Server

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Access API documentation at: http://localhost:8000/docs

### Start Dashboard

```bash
streamlit run app/dashboard/main.py
```

Access dashboard at: http://localhost:8501

---

## Common Issues

### Issue 1: NumPy Version Error

**Error:** `numpy version 2.0.0 required but...`

**Solution:**
```bash
pip install "numpy<2.0.0"
pip install --force-reinstall stable-baselines3
```

### Issue 2: Numba Compilation Failed

**Error:** `LLVM not found`

**Solution:**
```bash
# Ubuntu/Debian
sudo apt install llvm-11-dev

# macOS
brew install llvm@11

# Then reinstall
pip install --force-reinstall llvmlite numba
```

### Issue 3: Missing PostgreSQL

**Error:** `libpq-fe.h: No such file or directory`

**Solution:**
```bash
# Ubuntu/Debian
sudo apt install libpq-dev

# macOS
brew install postgresql

# Then reinstall
pip install --force-reinstall psycopg2-binary
```

---

## Next Steps

1. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

2. **Initialize Database**
   ```bash
   alembic upgrade head
   ```

3. **Run Tests**
   ```bash
   pytest tests/
   ```

4. **Read Documentation**
   - `INSTALLATION_GUIDE.md` - Detailed installation
   - `DEPENDENCIES_SUMMARY.md` - All dependencies
   - `README.md` - Project overview

---

## Verification Checklist

- [ ] Python 3.9-3.13 installed
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] verify_dependencies.py passes
- [ ] API server starts
- [ ] Dashboard loads
- [ ] Tests pass

---

## Need Help?

1. Check `INSTALLATION_GUIDE.md` for detailed troubleshooting
2. Check `INSTALLATION_TEST_REPORT.md` for known issues
3. Run `python verify_dependencies.py` for diagnostics
4. Search GitHub Issues
5. Create new issue with:

   ```bash
   python --version
   pip list
   python verify_dependencies.py > verification_output.txt
   ```

---

**Remember:** "If it's in the code, it's REQUIRED. No optional dependencies."

---

*Installation time: 15-30 minutes*
*Total dependencies: ~75 packages*
*Disk space: ~5GB*
