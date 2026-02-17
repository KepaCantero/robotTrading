# AlgoTrading System Gradual Rollout Plan

## Overview

This rollout plan provides a structured, risk-managed approach to deploying the AlgoTrading system with real money. The primary goal is capital preservation while learning and optimizing the system.

## Rollout Philosophy

**Core Principles:**
1. **Start Small**: Begin with minimal capital you can afford to lose
2. **Learn First**: Each stage teaches valuable lessons
3. **Validate Performance**: Compare vs benchmarks before scaling
4. **Risk Management**: Never risk more than you can afford to lose

## Pre-Rollout Checklist

Before ANY live trading:

- [ ] Complete Phase 0 and Phase 1 (position monitoring, emergency close)
- [ ] Complete Phase 2 (FIFO integration, Spain tax)
- [ ] Pass all tests: `pytest tests/ -v`
- [ ] 30-day paper trading success
- [ ] Professional tax review of Modelo 721 implementation
- [ ] Emergency procedures tested and documented
- [ ] Runbook reviewed and understood

---

## Stage 1: Paper Trading (Weeks 1-4)

### Objective
Validate system functionality without financial risk.

### Configuration
- **Capital**: $100,000 virtual
- **Duration**: 4 weeks minimum
- **Markets**: US stocks only
- **Strategies**: Momentum, mean reversion

### Success Criteria
- [ ] System runs 24/7 without crashes
- [ ] Position monitor correctly tracks all positions
- [ ] Stop-losses execute properly
- [ ] Emergency close works when tested
- [ ] No critical bugs for 2 weeks
- [ ] FIFO database accurately records all trades
- [ ] P&L calculated correctly

### Exit Criteria to Next Stage
- 30 consecutive days of uptime
- All trades recorded in FIFO database
- No position tracking errors

### Rollback Triggers
- More than 1 critical bug per week
- Position monitor failures
- FIFO database errors
- Emergency close not working

---

## Stage 2: Live Trading - $1,000 (Weeks 5-8)

### Objective
Validate system with real money at acceptable risk.

### Configuration
- **Capital**: $1,000 real money
- **Duration**: 4 weeks
- **Risk per Trade**: Max $50 (5%)
- **Max Positions**: 3
- **Markets**: US stocks only
- **Strategies**: Momentum only

### Success Criteria
- [ ] No critical bugs for 4 weeks
- [ ] All trades recorded accurately
- [ ] Stop-losses execute correctly
- [ ] FIFO database works with real trades
- [ ] Can generate Modelo 721 report

### Exit Criteria to Next Stage
- 4 weeks of stable operation
- Total loss < 20% ($200 loss acceptable)
- System recovers from all failures automatically
- At least break-even after 4 weeks

### Rollback Triggers
- Loss exceeds 20% of capital
- Any position not monitored
- Stop-loss fails to execute
- FIFO database errors

### What to Monitor Daily
- Total equity
- Open positions
- Trades executed
- System uptime
- Error logs

---

## Stage 3: Live Trading - $5,000 (Weeks 9-16)

### Objective
Scale up gradually while monitoring performance.

### Configuration
- **Capital**: $5,000 real money
- **Duration**: 8 weeks
- **Risk per Trade**: Max $250 (5%)
- **Max Positions**: 5
- **Markets**: US stocks + ETFs
- **Strategies**: Momentum, mean reversion

### Success Criteria
- [ ] Positive returns over 8 weeks
- [ ] Max drawdown < 15%
- [ ] Sharpe ratio > 0.5
- [ ] System stable for 8 weeks
- [ ] No manual interventions required

### Exit Criteria to Next Stage
- 8 weeks of profitable operation
- Total return > 5%
- Max drawdown < 10%
- System handles market volatility
- FIFO tax reporting verified by professional

### Rollback Triggers
- Max drawdown exceeds 15%
- Weekly loss > 10%
- System requires manual intervention more than once per week

### What to Monitor Daily
- Total equity and P&L
- Drawdown percentage
- Sharpe ratio
- Win rate
- Average win vs average loss

---

## Stage 4: Live Trading - $10,000 (Months 5-6)

### Objective
Approach production-level deployment with more capital.

### Configuration
- **Capital**: $10,000 real money
- **Duration**: 8 weeks
- **Risk per Trade**: Max $500 (5%)
- **Max Positions**: 8
- **Markets**: US stocks + ETFs + selected EU stocks
- **Strategies**: All validated strategies

### Success Criteria
- [ ] Positive returns over 8 weeks
- [ ] Max drawdown < 12%
- [ ] Sharpe ratio > 0.8
- [ ] Beats benchmark (SPY or IBEX 35)
- [ ] 24/7 operation stable

### Exit Criteria to Next Stage
- 2 months of profitable operation
- Total return > 10% annualized
- Max drawdown < 10%
- System handles all market conditions
- Tax compliance verified

### Rollback Triggers
- Max drawdown exceeds 12%
- Underperforms benchmark by > 5%
- System requires manual intervention

---

## Stage 5: Live Trading - $25,000 (Months 7-9)

### Objective
Near-production deployment with significant capital.

### Configuration
- **Capital**: $25,000 real money
- **Duration**: 12 weeks
- **Risk per Trade**: Max $1,250 (5%)
- **Max Positions**: 15
- **Markets**: US + EU stocks + ETFs
- **Strategies**: All strategies + FX hedging

### Success Criteria
- [ ] Positive returns over 12 weeks
- [ ] Max drawdown < 10%
- [ ] Sharpe ratio > 1.0
- [ ] Consistent outperformance vs benchmark
- [ ] Tax-efficient (Modelo 721 optimized)

### Rollback Triggers
- Max drawdown exceeds 10%
- Underperforms benchmark by > 3%
- Tax compliance issues

---

## Stage 6: Production - Full Capital (Month 10+)

### Objective
Full production deployment with target capital.

### Configuration
- **Capital**: User's full target capital
- **Risk Management**: All limits active
- **Markets**: All supported markets
- **Strategies**: All strategies
- **Automation**: Fully automated operation

### Success Criteria
- [ ] System runs 24/7 for 30+ days without manual intervention
- [ ] No position-related bugs
- [ ] FIFO database passes audit
- [ ] Spain tax reports accurate
- [ ] System recovers from all failure scenarios
- [ ] Sharpe ratio > 1.0
- [ ] Positive returns over 6-month period

---

## Risk Management at Each Stage

### Position Sizing
- **Stage 2**: 5% max per position
- **Stage 3**: 5% max per position
- **Stage 4**: 5% max per position
- **Stage 5**: 5% max per position
- **Stage 6**: 5% max per position

### Stop Loss
- **Default**: 5% from entry
- **Trailing**: Adjust on favorable moves
- **Auto-execute**: Always enabled in production

### Daily Loss Limits
- **Stage 2**: Stop trading if daily loss > 10%
- **Stage 3**: Stop trading if daily loss > 8%
- **Stage 4**: Stop trading if daily loss > 5%
- **Stage 5**: Stop trading if daily loss > 3%
- **Stage 6**: Stop trading if daily loss > 2%

### Monthly Reviews
- Performance vs benchmark
- Risk metrics
- System stability
- Bug reports
- Tax compliance

---

## Emergency Procedures

### If Max Drawdown Exceeded
1. Stop all trading immediately
2. Review positions
3. Close positions if necessary
4. Analyze what went wrong
5. Adjust strategy before restarting

### If System Crashes
1. System will restart automatically
2. Positions will be reconciled on startup
3. If positions don't reconcile, use emergency close
4. Review crash logs
5. Fix bug before resuming

### If Tax Questions Arise
1. Stop trading immediately
2. Consult tax professional
3. Verify FIFO database
4. Generate Modelo 721 report
5. Resume only after confirmation

---

## Success Metrics by Stage

| Stage | Duration | Capital | Target Return | Max Drawdown | Sharpe Ratio |
|-------|----------|---------|---------------|--------------|-------------|
| 1 - Paper | 4 weeks | $100K (virtual) | Any | N/A | N/A |
| 2 - Live | 4 weeks | $1,000 | Break-even | 20% | N/A |
| 3 - Live | 8 weeks | $5,000 | > 5% | 15% | > 0.5 |
| 4 - Live | 8 weeks | $10,000 | > 10% | 12% | > 0.8 |
| 5 - Live | 12 weeks | $25,000 | > 15% | 10% | > 1.0 |
| 6 - Prod | Ongoing | Full | > 20% | 10% | > 1.0 |

---

## Timeline Summary

| Phase | Duration | Cumulative Time | Milestone |
|-------|----------|------------------|-----------|
| Paper Trading | 1 month | Month 1 | System validated |
| $1K Live | 1 month | Month 2 | Real money tested |
| $5K Live | 2 months | Months 3-4 | Scaled successfully |
| $10K Live | 2 months | Months 5-6 | Growing steadily |
| $25K Live | 3 months | Months 7-9 | Near-production |
| Production | Ongoing | Month 10+ | Full deployment |

**Total Time to Production**: 9-10 months

---

## Important Notes

### Acceptable Losses
At each stage, be prepared to lose the entire capital deployed. Never risk money you cannot afford to lose.

### Tax Compliance
Spain residents MUST comply with Modelo 721. The FIFO database is legal evidence.

### Professional Help
Consider engaging:
- Tax advisor familiar with Modelo 721
- Legal advisor for regulatory compliance
- Financial advisor for portfolio management

### System Requirements
Before Stage 2, ensure:
- High-speed internet (redundant if possible)
- Uninterruptible power supply (UPS)
- Backup computer ready
- Mobile phone with trading app (manual override)
- Broker support contact info readily available

---

## Decision Gates

### Gate 1: After Paper Trading (Week 4)
**Question**: Is the system ready for real money?

**Criteria**:
- [ ] 30 days continuous operation
- [ ] No critical bugs
- [ ] Position monitor working
- [ ] Emergency close tested
- [ ] FIFO database working

**Go/No-Go**: If NO, continue paper trading. Fix issues first.

### Gate 2: After $1K Stage (Week 8)
**Question**: Should we scale to $5K?

**Criteria**:
- [ ] Break-even or profitable
- [ ] No critical bugs
- [ ] Stable operation

**Go/No-Go**: If NO, extend $1K stage or return to paper trading.

### Gate 3: After $5K Stage (Week 16)
**Question**: Should we scale to $10K?

**Criteria**:
- [ ] Profitable
- [ ] Max drawdown acceptable
- [ ] System stable

**Go/No-Go**: If NO, continue at $5K or reduce back.

---

## Configuration Files for Each Stage

### Stage 1: Paper Trading Configuration
```yaml
# config/rollout/stage1_paper_trading.yaml
trading:
  mode: paper
  capital: 100000
  max_positions: 10
  risk_per_trade: 0.05
  stop_loss: 0.05

strategies:
  - name: momentum
    enabled: true
  - name: mean_reversion
    enabled: true
```

### Stage 2: $1,000 Live Trading Configuration
```yaml
# config/rollout/stage2_1k_live.yaml
trading:
  mode: live
  capital: 1000
  max_positions: 3
  risk_per_trade: 0.05
  stop_loss: 0.05
  daily_loss_limit: 0.10

strategies:
  - name: momentum
    enabled: true
  - name: mean_reversion
    enabled: false
```

### Stage 3: $5,000 Live Trading Configuration
```yaml
# config/rollout/stage3_5k_live.yaml
trading:
  mode: live
  capital: 5000
  max_positions: 5
  risk_per_trade: 0.05
  stop_loss: 0.05
  daily_loss_limit: 0.08

strategies:
  - name: momentum
    enabled: true
  - name: mean_reversion
    enabled: true
```

### Stage 4: $10,000 Live Trading Configuration
```yaml
# config/rollout/stage4_10k_live.yaml
trading:
  mode: live
  capital: 10000
  max_positions: 8
  risk_per_trade: 0.05
  stop_loss: 0.05
  daily_loss_limit: 0.05

strategies:
  - name: momentum
    enabled: true
  - name: mean_reversion
    enabled: true
```

### Stage 5: $25,000 Live Trading Configuration
```yaml
# config/rollout/stage5_25k_live.yaml
trading:
  mode: live
  capital: 25000
  max_positions: 15
  risk_per_trade: 0.05
  stop_loss: 0.05
  daily_loss_limit: 0.03

strategies:
  - name: momentum
    enabled: true
  - name: mean_reversion
    enabled: true
  - name: fx_hedging
    enabled: true
```

### Stage 6: Production Configuration
```yaml
# config/rollout/stage6_production.yaml
trading:
  mode: live
  capital: null  # Use full available capital
  max_positions: 20
  risk_per_trade: 0.05
  stop_loss: 0.05
  daily_loss_limit: 0.02

strategies:
  - name: momentum
    enabled: true
  - name: mean_reversion
    enabled: true
  - name: fx_hedging
    enabled: true
  - name: arbitrage
    enabled: true
```

---

## Monitoring and Alerts

### Key Metrics to Track

#### System Health
- CPU usage < 80%
- Memory usage < 80%
- Disk space > 20% free
- Network latency < 100ms
- API response time < 500ms

#### Trading Performance
- Total return
- Daily P&L
- Win rate
- Profit factor
- Maximum drawdown
- Sharpe ratio
- Sortino ratio

#### Position Monitoring
- Open positions count
- Position sizes
- Unrealized P&L
- Time in position
- Distance from stop-loss

### Alert Thresholds

#### Critical Alerts (Immediate Action Required)
- Daily loss > daily_loss_limit
- Position not monitored
- Stop-loss failed
- System down > 5 minutes
- FIFO database error

#### Warning Alerts (Monitor Closely)
- Daily loss > 50% of daily_loss_limit
- Drawdown > 75% of max_allowed
- System error rate increasing
- API latency > 1 second

#### Info Alerts (For Review)
- Daily performance summary
- Weekly performance report
- Monthly tax report generated
- System maintenance completed

---

## Testing Procedures

### Pre-Stage Testing Checklist

Before advancing to each stage, complete:

#### Functional Testing
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] End-to-end testing successful
- [ ] Paper trading for 1 week with new config

#### Performance Testing
- [ ] System handles expected load
- [ ] API calls within rate limits
- [ ] Database queries fast enough
- [ ] No memory leaks

#### Disaster Recovery Testing
- [ ] System crash recovery tested
- [ ] Internet disconnection tested
- [ ] Broker API failure tested
- [ ] Emergency close tested
- [ ] Database corruption recovery tested

#### Security Testing
- [ ] API keys secure
- [ ] Database encrypted
- [ ] No sensitive data in logs
- [ ] Access controls working

---

## Rollback Procedures

### When to Rollback
- Critical bug discovered
- Loss exceeds acceptable limits
- System unstable
- Tax compliance issues
- Broker account problems

### Rollback Steps
1. Stop all trading immediately
2. Close all open positions (if safe to do so)
3. Review what went wrong
4. Fix the issue
5. Return to previous stage for testing
6. Only advance after issue fully resolved

### Partial Rollback
If issue is strategy-specific:
1. Disable affected strategy
2. Continue with other strategies
3. Fix and test in paper trading
4. Re-enable after validation

---

## Documentation Requirements

### Stage-Specific Documentation
- Configuration used
- Performance metrics
- Issues encountered
- Lessons learned
- Next stage recommendations

### Weekly Reports
- Trading summary
- P&L breakdown
- Risk metrics
- System health
- Action items

### Monthly Reports
- Comprehensive performance review
- Benchmark comparison
- Tax status
- System improvements
- Next month plan

---

## Continuous Improvement

### Post-Mortem Process
After any significant issue:
1. Document what happened
2. Identify root cause
3. Implement fixes
4. Update procedures
5. Test thoroughly
6. Monitor for recurrence

### Optimization Opportunities
- Strategy parameter tuning
- Risk limit adjustments
- System performance improvements
- Tax optimization
- Automation enhancements

### Learning from Each Stage
- Document lessons learned
- Update rollout plan based on experience
- Share findings with team
- Improve documentation
- Refine success criteria

---

## Support Resources

### Internal Resources
- System documentation: `/Users/kepa.cantero/Projects/algoTrading/docs/`
- Runbook: `RUNBOOK.md`
- API documentation: `docs/API_REFERENCE.md`
- Tax guide: `docs/SPAIN_TAX_GUIDE.md`

### External Resources
- Broker support
- Tax professional
- Legal advisor
- Financial advisor
- Technical community

### Emergency Contacts
Maintain current contact information for:
- Primary broker support
- Backup broker support
- Tax advisor
- System administrator
- Financial advisor

---

## Final Checklist Before Stage 2 (Real Money)

### Technical Requirements
- [ ] System stable for 30 days paper trading
- [ ] All tests passing
- [ ] Emergency procedures tested
- [ ] Backup procedures tested
- [ ] Monitoring configured
- [ ] Alerts configured

### Financial Requirements
- [ ] Broker account funded with $1,000
- [ ] Risk capital identified (money you can afford to lose)
- [ ] Bank account linked for withdrawals
- [ ] Tax preparation understood

### Legal Requirements
- [ ] Modelo 721 implementation reviewed
- [ ] Tax advisor consulted
- [ ] Regulatory requirements understood
- [ ] Broker agreements reviewed

### Personal Requirements
- [ ] Understand all risks
- [ ] Accept potential for total loss
- [ ] Time commitment available
- [ ] Emotional preparedness
- [ ] Family informed and supportive

---

## Conclusion

This rollout plan prioritizes capital preservation and learning over rapid scaling. Each stage builds confidence and proves the system works before exposing more capital to risk.

**Remember**: The goal is not just to make money, but to build a robust, reliable system that can grow sustainably over time.

**Key Success Factors**:
- Patience - Don't rush stages
- Discipline - Follow the plan
- Risk Management - Always protect capital
- Continuous Learning - Improve at each stage
- Professional Advice - Don't go it alone

**Last Updated**: 2026-01-25
**Version**: 1.0
**Status**: READY FOR IMPLEMENTATION
