# Compliance Engine Risk Validations - Quick Reference

**File:** `/app/core/compliance_engine.py`
**Method:** `_handle_risk_engine()`
**Lines:** 570-708

---

## Quick Summary

The compliance engine now has **REAL validation logic** instead of placeholders. All trades are validated against:

1. ✅ **Position Limits** - Max 10% of portfolio per trade
2. ✅ **Drawdown Limits** - Max 25% from peak
3. ✅ **Leverage Limits** - Max 2.0x gross exposure
4. ✅ **Data Quality** - Min 80% quality score
5. ✅ **Portfolio VaR** - Volatility risk monitoring

---

## Validation Thresholds

| Check | Limit | Action on Violation |
|-------|-------|-------------------|
| Position Size | ≤ 10% of portfolio | Block trade, 30% confidence |
| Drawdown | ≤ 25% from peak | Block trade, 20% confidence |
| Leverage Ratio | ≤ 2.0x | Block trade, 40% confidence |
| Data Quality | ≥ 80% | Block trade, 50% confidence |
| Portfolio VaR | ≤ 30% annual vol | Reduce confidence 15% |

---

**Last Updated:** 2026-01-28
**Status:** ✅ Production Ready
