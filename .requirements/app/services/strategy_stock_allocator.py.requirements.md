# Requirements: app/services/strategy_stock_allocator.py

**Last Updated:** 2026-02-07
**Status:** AUDIT_PASSED
**Audit Date:** 2026-02-07

---

## Overview

This module implements the StrategyStockAllocator - a professional, verifiable, and auditable stock allocation system. It handles stock filtering, statistical classification, scoring engines, WCM (Weighted Scoring Model), and ERC/Risk Parity optimization for capital allocation.

**References:**
- See ../../../BASE_RULES.md for universal rules

---

## Module-Specific Requirements

### SSA-001: Data Validation - Filter Stocks
**Priority:** P0
**Rule:** Must filter out invalid stocks before processing

**Acceptance Criteria:**
- Empty or None DataFrame rejection
- Missing required columns (OHLCV) check
- Insufficient historical data validation
- NaN value detection
- Time gap analysis (allow up to 30%)
- Price consistency validation (high >= low)
- Zero/negative price detection
- Volatility validation (0 < vol < 0.5)
- Liquidity threshold (2% of MIN_LIQUIDITY_USD)

**Status:** PASS - Comprehensive validation in `filter_stocks()`

---

### SSA-002: Hurst Exponent Calculation
**Priority:** P1
**Rule:** Must calculate Hurst exponent using R/S method

**Interpretation:**
- H > 0.55: Momentum/trending
- H < 0.45: Mean reverting
- H ≈ 0.5: Random walk

**Status:** PASS - R/S method with proper validation

---

### SSA-003: Stationarity Testing (ADF + KPSS)
**Priority:** P1
**Rule:** Must perform dual stationarity tests

**Status:** PASS - Both tests with classification:
- strict_stationary: both agree
- trend_stationary: ADF stationary, KPSS not
- non_stationary: ADF not stationary

---

### SSA-004: Half-Life Calculation (Ornstein-Uhlenbeck)
**Priority:** P0
**Rule:** Must calculate half-life from O-U model

**Formula:** τ = -ln(2) / θ
**Validation:** 0 < τ < 1000 days

**Status:** PASS - OLS with numpy.polyfit

---

### SSA-005: Sortino Ratio (Downside Deviation)
**Priority:** P1
**Rule:** Must use downside deviation, not standard deviation

**Status:** PASS - Uses negative returns only

---

### SSA-006: GARCH Volatility with EWMA Fallback
**Priority:** P1
**Rule:** Must fall back to EWMA if arch unavailable

**Status:** PASS - EWMA fallback when ARCH_AVAILABLE is False

---

### SSA-007: Dynamic Window Selection for Momentum
**Priority:** P2
**Rule:** Should optimize slope/ROC windows using MSE

**Status:** PASS - Dynamic window selection implemented

---

### SSA-008: Pairs Trading Cointegration
**Priority:** P0
**Rule:** Must use Engle-Granger cointegration test

**Strict:** p < 0.01 (ADF_P_VALUE_THRESHOLD)
**GARCH Normalization:** z-score normalized by GARCH volatility

**Status:** PASS - Full implementation with fallbacks

---

### SSA-009: WCM Score Calculation
**Priority:** P1
**Formula:** SPS_{i,k} = Σ(W_{k,j} × Score_{i,j}^{Norm})

**Status:** PASS - Weighted Scoring Model in `calculate_wcm_scores()`

---

### SSA-010: ERC (Equal Risk Contribution) Allocation
**Priority:** P0
**Rule:** Must allocate capital using ERC/Risk Parity

**Objective:** Minimize variance of risk contributions
**Constraints:** Weights sum to 1.0, 0 <= weight <= MAX_STRATEGY_EXPOSURE

**Status:** PASS - scipy.optimize.minimize with equal weight fallback

---

### SSA-011: Strategy Assignment
**Priority:** P0
**Rule:** Must assign strategies based on scores

**Priority:** Pairs > Momentum/MeanReversion (higher score)
**Balancing:** Ensure each strategy has at least 1 ticker

**Status:** PASS - Strategy assignment with balancing

---

### SSA-012: Capital Redistribution
**Priority:** P0
**Rule:** Must redistribute unused capital respecting limits

**Status:** PASS - Two-pass redistribution with limit checks

---

### SSA-013: Allocation Validation
**Priority:** P0
**Checks:**
- Total capital match
- Individual limits
- Strategy-level limits
- No strategy overlap

**Status:** PASS - Comprehensive validation

---

### SSA-014: Configured Pairs Support
**Priority:** P2
**Status:** PASS - Supports list of lists and simple list

---

### SSA-015: Relaxed Filtering for Testing
**Priority:** P2
**Settings:**
- Min days: max(40, min(LOOKBACK_MAX_DAYS, 126))
- Liquidity: 2% of MIN_LIQUIDITY_USD
- Gaps: 30% allowed

**Status:** PASS - Configurable for development

---

## Trading-Specific Compliance

| Rule ID | Rule | Status |
|---------|------|--------|
| TRD-001 | Input validation | PASS |
| TRD-002 | Risk validation | PASS |
| TRD-003 | Position limits | PASS |
| TRD-004 | Audit logging | PASS |
| TRD-005 | Price validation | PASS |
| TRD-007 | Annualization (252 days) | PASS |

---

## Code Quality Compliance

| Rule ID | Rule | Status | Notes |
|---------|------|--------|-------|
| CC-001 | Descriptive names | PASS | Clear naming |
| CC-002 | DRY | PASS | Minimal duplication |
| CC-005 | Early returns | PASS | Guard clauses |
| CC-006 | Explicit error handling | PASS | Specific exceptions |
| LOG-004 | Error logging | PASS | All errors logged |

---

## Architecture Compliance

| Rule ID | Rule | Status | Notes |
|---------|------|--------|-------|
| ARCH-001 | Layered architecture | PASS | Application layer |
| ARCH-004 | Small functions | PASS | Most < 50 lines |
| ARCH-006 | Value objects | PASS | Pydantic models |
| SOL-001 | SRP | PASS | Single responsibility |

---

## GAPS Identified

**NONE** - All requirements met.

---

## Audit Summary

**Status:** PASSED
**Critical Violations:** 0
**High Priority Violations:** 0
**Medium Priority Violations:** 0
**Low Priority Violations:** 0

**Strengths:**
- Comprehensive validation framework
- Proper statistical methods
- Robust ERC optimization
- Excellent error handling
- Clear separation of concerns

**Notes:** Production-ready, follows all BASE_RULES.
