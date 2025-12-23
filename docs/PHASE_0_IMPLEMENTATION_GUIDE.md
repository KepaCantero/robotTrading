# PHASE 0: Capital Viability & Integration Audit - Implementation Guide

**Quick Reference for Developers**
**Status**: 🔴 NOT STARTED
**Timeline**: 2-3 weeks (MANDATORY BEFORE LIVE TRADING)
**Severity**: CRITICAL - Blocks all live deployment on accounts < $30k

---

## 🎯 Mission Statement

Prevent capital loss caused by:
1. Chasing mathematically impossible profit goals
2. Trading when commission/slippage > alpha
3. Enabling expensive features (learning, synthetic data) on accounts too small to justify them
4. Joint strategy interactions that amplify costs unexpectedly
5. Data staleness or regime shifts degrading learning engines

**Success Metric**: System correctly **refuses to trade** when objective is unreachable or cost-prohibitive.

---

## 📊 Gap Summary (What's Missing)

| Gap | Impact | Modules | Priority |
|-----|--------|---------|----------|
| **GAP-1.1** | Learning activates on $15k capital, cost > alpha | Strategy→Learning | P0 |
| **GAP-1.2** | Multi-strategy execution costs compound unexpectedly | Portfolio→Execution | P0 |
| **GAP-1.3** | Commission/slippage domination undetected | Execution→Risk | P0 |
| **GAP-1.4** | Stale data + learning = silent model degradation | Data→Learning | P1 |
| **GAP-1.5** | Risk escalation doesn't reject all pending signals atomically | Risk→Execution | P1 |
| **GAP-1.6** | Rebalancing + pending trades creates unhedged positions | Portfolio→Execution | P1 |
| **GAP-2.1** | System trades even when profit goal unreachable | Core Config→Risk | P0 |
| **GAP-2.2** | No detection of "passive > active return" inflection | Strategy→Execution | P0 |
| **GAP-2.3** | Learning damage during regime shift not prevented | Learning→Drift | P0 |
| **GAP-2.4** | Partial allocation strategies become untradeably small | Portfolio→Execution | P1 |
| **GAP-2.5** | Currency hedging cost > alpha (undetected) | Portfolio→Risk | P1 |
| **GAP-2.6** | Account crosses zero with leverage (margin) | Core→Risk | P0 |

---

## ✅ Tasks to Implement (22 Days of Work)

### PHASE 0.1: Fail-Fast Gates (Days 1-8)

#### T0.1.1: Unreachable Profit Goal Detection [Days 1-3]

**File**: `app/services/capital_viability_gate.py`

**What it does**:
- Checks if `monthly_profit_goal` is achievable given capital, tax rate, and execution costs
- If unreachable, system disables trading and recommends action

**Implementation**:
```python
from decimal import Decimal
from typing import Tuple

class CapitalViabilityValidator:
    """Validates if profit goal is achievable"""

    ALPHA_THRESHOLD = Decimal("0.10")  # 10% = unreachable for most strategies

    @staticmethod
    def validate_profit_goal(
        capital: Decimal,
        monthly_goal: Decimal,
        tax_rate: Decimal,
        commission_per_trade: Decimal,
        expected_trades_per_month: int,
        expected_alpha_per_trade: Decimal
    ) -> dict:
        """
        Calculate if profit goal is viable.

        Returns: {
            'is_viable': bool,
            'required_alpha_pct': Decimal,
            'achievable_alpha_pct': Decimal,
            'reason': str,
            'recommendation': str
        }
        """

        # Gross goal needed to meet net goal after tax
        gross_goal = monthly_goal / (1 - tax_rate)

        # Total commission cost per month
        total_commission = commission_per_trade * Decimal(expected_trades_per_month)

        # Total alpha needed to cover goal + costs
        required_alpha = gross_goal + total_commission

        # Alpha as percentage of capital
        required_alpha_pct = required_alpha / capital

        # Achievable alpha (from strategy testing, typically 2-3% monthly on good months)
        achievable_alpha_pct = expected_alpha_per_trade * Decimal(expected_trades_per_month)

        is_viable = required_alpha_pct <= CapitalViabilityValidator.ALPHA_THRESHOLD

        if not is_viable:
            reason = (
                f"Goal requires {required_alpha_pct:.1%} monthly alpha "
                f"(typical max: 3-5% on large capital, <1% on {capital:,.0f}); "
                f"achievable: {achievable_alpha_pct:.1%}"
            )
            recommendation = "INCREASE_CAPITAL or REDUCE_GOAL"
        else:
            reason = f"Goal is viable (requires {required_alpha_pct:.1%} alpha, achievable {achievable_alpha_pct:.1%})"
            recommendation = "PROCEED"

        return {
            'is_viable': is_viable,
            'required_alpha_pct': required_alpha_pct,
            'achievable_alpha_pct': achievable_alpha_pct,
            'reason': reason,
            'recommendation': recommendation
        }
```

**Tests**:
```python
def test_unreachable_goal_10k_capital_500_monthly():
    result = CapitalViabilityValidator.validate_profit_goal(
        capital=Decimal("10000"),
        monthly_goal=Decimal("500"),
        tax_rate=Decimal("0.40"),
        commission_per_trade=Decimal("15"),
        expected_trades_per_month=10,
        expected_alpha_per_trade=Decimal("0.01")  # 1% per trade
    )
    assert result['is_viable'] == False
    assert "REDUCE_GOAL" in result['recommendation']

def test_reachable_goal_100k_capital_500_monthly():
    result = CapitalViabilityValidator.validate_profit_goal(
        capital=Decimal("100000"),
        monthly_goal=Decimal("500"),
        tax_rate=Decimal("0.40"),
        commission_per_trade=Decimal("15"),
        expected_trades_per_month=10,
        expected_alpha_per_trade=Decimal("0.01")
    )
    assert result['is_viable'] == True
```

**Where to call it**:
- `app/core/deployment_gates.py` before initializing ExecutionEngine
- Log result to audit trail regardless of outcome

---

#### T0.1.2: Commission Dominance Detection [Days 4-6]

**File**: `app/services/execution_cost_analyzer.py`

**What it does**:
- Monitors real slippage (rolling 30-day history)
- Detects when slippage regime changes (volatility-triggered)
- Rejects trades when cost > 50% of expected alpha

**Implementation**:
```python
from decimal import Decimal
from collections import deque
from typing import Optional

class ExecutionCostAnalyzer:
    """Monitors execution costs and rejects trades when uneconomical"""

    def __init__(self, lookback_days: int = 30, max_cost_ratio: Decimal = Decimal("0.50")):
        self.slippage_history = deque(maxlen=lookback_days)
        self.max_cost_ratio = max_cost_ratio  # Cost can be max 50% of alpha
        self.base_slippage = Decimal("0.001")  # 0.1% base
        self.commission_per_trade = Decimal("15")

    def add_trade_slippage(self, slippage_pct: Decimal):
        """Record actual slippage from recent trade"""
        self.slippage_history.append(slippage_pct)

    def get_current_slippage_estimate(self, volatility_percentile: int) -> Decimal:
        """
        Calculate current slippage estimate based on volatility.
        volatility_percentile: 0-100 (0=lowest, 100=highest)
        """
        if len(self.slippage_history) == 0:
            # Use base slippage if no history
            return self._volatility_adjusted_slippage(volatility_percentile)

        # Use average of recent trades, adjusted for volatility
        avg_slippage = sum(self.slippage_history) / len(self.slippage_history)
        vol_adjustment = Decimal(volatility_percentile) / Decimal("50")  # Scale 0-2x

        return avg_slippage * vol_adjustment

    def _volatility_adjusted_slippage(self, volatility_percentile: int) -> Decimal:
        """
        Map volatility to slippage multiplier.
        Low vol (0-25%): 0.5x base
        Normal vol (25-75%): 1x base
        High vol (75-100%): 4x base
        """
        if volatility_percentile < 25:
            return self.base_slippage * Decimal("0.5")
        elif volatility_percentile < 75:
            return self.base_slippage * Decimal("1.0")
        else:
            return self.base_slippage * Decimal("4.0")

    def should_execute_trade(
        self,
        position_size: Decimal,
        expected_alpha: Decimal,
        volatility_percentile: int
    ) -> Tuple[bool, str]:
        """
        Determine if trade is economical.

        Returns: (should_execute, reason)
        """

        current_slippage = self.get_current_slippage_estimate(volatility_percentile)
        slippage_cost = position_size * current_slippage
        total_cost = slippage_cost + self.commission_per_trade

        cost_ratio = total_cost / expected_alpha if expected_alpha > 0 else Decimal("999")

        if cost_ratio > self.max_cost_ratio:
            reason = (
                f"Cost ${total_cost:.2f} ({cost_ratio:.0%} of alpha ${expected_alpha:.2f}) "
                f"exceeds threshold {self.max_cost_ratio:.0%}; rejecting trade"
            )
            return False, reason
        else:
            reason = f"Cost ${total_cost:.2f} ({cost_ratio:.0%} of alpha); acceptable"
            return True, reason
```

**Tests**:
```python
def test_trade_accepted_normal_conditions():
    analyzer = ExecutionCostAnalyzer()
    should_execute, reason = analyzer.should_execute_trade(
        position_size=Decimal("10000"),  # $10k position
        expected_alpha=Decimal("100"),   # $100 expected profit
        volatility_percentile=50         # Normal vol
    )
    # Cost: $10k * 0.1% + $15 = $25 = 25% of alpha
    assert should_execute == True

def test_trade_rejected_high_volatility():
    analyzer = ExecutionCostAnalyzer()
    analyzer.add_trade_slippage(Decimal("0.004"))  # Recent trades at 0.4%

    should_execute, reason = analyzer.should_execute_trade(
        position_size=Decimal("10000"),
        expected_alpha=Decimal("100"),
        volatility_percentile=90  # High vol
    )
    # Cost: $10k * 0.4% + $15 = $55 = 55% of alpha > threshold
    assert should_execute == False
```

**Where to call it**:
- `app/strategies/execution_engine.py` before executing each trade
- Log each rejection to audit trail with "Cost regime detected" note

---

#### T0.1.3: Opportunity Cost Validator [Days 7-8]

**File**: `app/services/opportunity_cost_validator.py`

**What it does**:
- Compares: active trading alpha vs. passive (risk-free rate)
- Recommends "hold cash" if passive > active

**Implementation**:
```python
from decimal import Decimal

class OpportunityCostValidator:
    """Determines if active trading is worth it vs passive"""

    @staticmethod
    def is_active_trading_worthwhile(
        capital: Decimal,
        monthly_risk_free_rate: Decimal,  # e.g., 0.04 for 4% annual
        expected_monthly_alpha: Decimal,
        expected_trades_per_month: int,
        commission_per_trade: Decimal
    ) -> Tuple[bool, str]:
        """
        Compare passive (hold cash at risk-free rate) vs active trading.

        Returns: (should_trade, reason)
        """

        # Passive income: risk-free rate applied to capital
        passive_monthly = capital * (monthly_risk_free_rate / 12)

        # Active income: expected alpha minus commissions
        total_commissions = commission_per_trade * Decimal(expected_trades_per_month)
        active_monthly = expected_monthly_alpha - total_commissions

        should_trade = active_monthly > passive_monthly

        if not should_trade:
            reason = (
                f"Passive return ${passive_monthly:.2f}/mo > "
                f"active return ${active_monthly:.2f}/mo; recommend HOLD_CASH"
            )
        else:
            margin = active_monthly - passive_monthly
            reason = f"Active beats passive by ${margin:.2f}/mo; recommend TRADE"

        return should_trade, reason
```

**Where to call it**:
- Before strategy signal generation loop
- If returns False, set `trading_enabled = False` for this cycle
- Log decision

---

### PHASE 0.2: Capital-Constrained Module Gating (Days 9-13)

#### T0.2.1: Learning Engine Capital Gate [Days 9-11]

**File**: `app/strategies/momentum_modular/learning/learning_capital_gate.py`

**What it does**:
- Prevents learning engine initialization on small accounts
- Estimates learning cost vs benefit
- Disables retraining when capital too low

**Implementation**:
```python
from decimal import Decimal
from typing import Tuple

class LearningCapitalGate:
    """Gate that controls learning engine based on capital"""

    MIN_CAPITAL_FOR_LEARNING = Decimal("25000")  # $25k minimum
    LEARNING_COST_PER_MONTH = Decimal("50")      # Estimated cost
    COST_BENEFIT_THRESHOLD = Decimal("0.30")     # Cost can be max 30% of alpha

    @staticmethod
    def should_enable_learning(
        capital: Decimal,
        expected_monthly_alpha: Decimal
    ) -> Tuple[bool, str]:
        """
        Determine if learning should be enabled.

        Returns: (should_enable, reason)
        """

        if capital < LearningCapitalGate.MIN_CAPITAL_FOR_LEARNING:
            reason = (
                f"Learning disabled: capital ${capital:,.0f} < "
                f"minimum ${LearningCapitalGate.MIN_CAPITAL_FOR_LEARNING:,.0f}"
            )
            return False, reason

        # Cost-benefit analysis
        cost_ratio = LearningCapitalGate.LEARNING_COST_PER_MONTH / expected_monthly_alpha

        if cost_ratio > LearningCapitalGate.COST_BENEFIT_THRESHOLD:
            reason = (
                f"Learning disabled: cost ${LearningCapitalGate.LEARNING_COST_PER_MONTH:.0f}/mo "
                f"is {cost_ratio:.0%} of alpha ${expected_monthly_alpha:.0f}/mo "
                f"(exceeds {LearningCapitalGate.COST_BENEFIT_THRESHOLD:.0%} threshold)"
            )
            return False, reason

        reason = f"Learning enabled: capital sufficient and cost-effective"
        return True, reason

    @staticmethod
    def should_disable_learning_due_to_drift(
        capital: Decimal,
        drift_severity: str  # "low" | "medium" | "high" | "critical"
    ) -> Tuple[bool, str]:
        """
        Override learning enablement if drift is severe and capital is low.
        """

        if drift_severity == "critical":
            reason = f"Learning disabled: critical drift detected on ${capital:,.0f} capital"
            return True, reason

        if drift_severity == "high" and capital < Decimal("30000"):
            reason = f"Learning disabled: high drift + insufficient capital"
            return True, reason

        return False, ""
```

**Where to apply**:
1. **ModularMomentumStrategy.__init__()**: Check gate before lazy-loading learning
   ```python
   if config.get("adaptive_learning", {}).get("enabled", False):
       can_enable, reason = LearningCapitalGate.should_enable_learning(
           capital, expected_monthly_alpha
       )
       if not can_enable:
           logger.warning(f"Learning gate: {reason}")
           config["adaptive_learning"]["enabled"] = False
   ```

2. **DriftDetector.check()**: Return disable recommendation if needed
   ```python
   if drift_detected:
       should_disable, reason = LearningCapitalGate.should_disable_learning_due_to_drift(
           capital, drift_severity
       )
       if should_disable:
           return {
               'degradation_detected': True,
               'recommendation': 'disable',  # Not 'retrain'
               'reason': reason
           }
   ```

**Tests**:
```python
def test_learning_disabled_capital_15k():
    can_enable, reason = LearningCapitalGate.should_enable_learning(
        capital=Decimal("15000"),
        expected_monthly_alpha=Decimal("100")
    )
    assert can_enable == False
    assert "minimum" in reason.lower()

def test_learning_enabled_capital_30k():
    can_enable, reason = LearningCapitalGate.should_enable_learning(
        capital=Decimal("30000"),
        expected_monthly_alpha=Decimal("200")
    )
    assert can_enable == True
```

---

#### T0.2.2: Expensive Module Disabling [Days 12-13]

**File**: `app/services/expensive_module_gate.py`

```python
class ExpensiveModuleGate:
    """Disables expensive features on small accounts"""

    MIN_CAPITAL_FOR_SYNTHETIC = Decimal("30000")
    MIN_CAPITAL_FOR_LLM = Decimal("50000")

    @staticmethod
    def should_enable_synthetic_data(capital: Decimal) -> bool:
        """Synthetic data generation is computationally expensive"""
        return capital >= ExpensiveModuleGate.MIN_CAPITAL_FOR_SYNTHETIC

    @staticmethod
    def should_enable_llm_signals(capital: Decimal) -> bool:
        """LLM API calls cost money"""
        return capital >= ExpensiveModuleGate.MIN_CAPITAL_FOR_LLM
```

---

### PHASE 0.3: Integration Tests (Days 14-17)

#### T0.3.1: Joint Strategy Execution Test
**File**: `tests/integration/validation/test_capital_stress_joint_strategy.py`

Tests that multiple strategies executing simultaneously don't create unexpectedly high slippage costs.

#### T0.3.2: Data Staleness + Learning Test
**File**: `tests/integration/validation/test_integration_stale_data_learning_damage.py`

Tests that stale data prevents learning engine from being used.

#### T0.3.3: Risk Escalation Atomicity Test
**File**: `tests/integration/validation/test_integration_risk_escalation_signal_atomicity.py`

Tests that risk level escalation rejects ALL pending signals, not partial.

#### T0.3.4: Rebalancing + Trades Test
**File**: `tests/integration/validation/test_integration_rebalancing_pending_trades.py`

Tests that rebalancing doesn't create unhedged positions with pending trades.

#### T0.3.5: Hedging Cost > Alpha Test
**File**: `tests/integration/validation/test_integration_currency_hedging_cost_dominance.py`

Tests that currency hedging is disabled when cost > alpha.

---

### PHASE 0.4: Deployment Guards (Days 18-21)

#### Add Deployment Gate

**File**: `app/core/deployment_gates.py` (NEW)

Master gate that checks all PHASE 0 conditions before allowing live trading.

#### Update Audit Trail

- All gate decisions logged with timestamp and reason
- Queryable by account and date
- Exportable for compliance

#### Config Templates

Create config templates for different capital sizes:
- `config/capital_tiers/micro_10k.yaml` (not recommended)
- `config/capital_tiers/small_25k.yaml` (learning disabled)
- `config/capital_tiers/medium_50k.yaml` (all features enabled)

---

### Day 22: Validation & Sign-Off

- Run full test suite: 100% passing
- Manual deploy test on paper trading account
- Audit trail verification
- Documentation review

---

## 📋 Checklist for Implementation

```
PHASE 0 DELIVERABLES
====================

[ ] T0.1.1: capital_viability_gate.py
    [ ] CapitalViabilityValidator class
    [ ] Formula implementation
    [ ] 3 unit tests passing

[ ] T0.1.2: execution_cost_analyzer.py
    [ ] ExecutionCostAnalyzer class
    [ ] Slippage tracking
    [ ] Volatility adjustment logic
    [ ] 5 unit tests passing

[ ] T0.1.3: opportunity_cost_validator.py
    [ ] OpportunityCostValidator class
    [ ] Passive vs active comparison
    [ ] 3 unit tests passing

[ ] T0.2.1: learning_capital_gate.py
    [ ] LearningCapitalGate class
    [ ] Integration with ModularMomentumStrategy.__init__()
    [ ] Integration with DriftDetector
    [ ] 4 unit tests passing

[ ] T0.2.2: expensive_module_gate.py
    [ ] ExpensiveModuleGate class
    [ ] Synthetic data gating
    [ ] LLM gating
    [ ] 2 unit tests passing

[ ] T0.3.1: test_capital_stress_joint_strategy.py
    [ ] Test passing

[ ] T0.3.2: test_integration_stale_data_learning_damage.py
    [ ] Test passing

[ ] T0.3.3: test_integration_risk_escalation_signal_atomicity.py
    [ ] Test passing

[ ] T0.3.4: test_integration_rebalancing_pending_trades.py
    [ ] Test passing

[ ] T0.3.5: test_integration_currency_hedging_cost_dominance.py
    [ ] Test passing

[ ] T0.4: Deployment guards
    [ ] deployment_gates.py created
    [ ] Audit trail updated
    [ ] Config templates created
    [ ] Documentation complete

[ ] FULL TEST SUITE
    [ ] pytest tests/integration/validation/ -v (100% pass)
    [ ] pytest tests/unit/ -v (no regressions)
    [ ] Coverage report generated
```

---

## 🚀 How to Start

1. **Week 1: Read & Plan**
   - Read this guide
   - Read PLAN_MAESTRO_NEXT_LEVEL.md PHASE 0 section
   - Estimate effort per task
   - Create JIRA tickets if applicable

2. **Week 2-3: Implement**
   - Follow task order: T0.1.1 → T0.1.3 → T0.2.1 → T0.2.2 → T0.3.x → T0.4
   - Commit daily
   - Run tests after each implementation
   - Keep audit trail up to date

3. **Week 4: Validation**
   - Run full test suite
   - Paper trade validation
   - Operator training
   - Live deployment authorization

---

**Questions?** Refer back to PLAN_MAESTRO_NEXT_LEVEL.md for full context on each task.
