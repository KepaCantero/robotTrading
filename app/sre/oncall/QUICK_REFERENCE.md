# On-Call Quick Reference Card

**Last Updated:** 2026-01-28
**Version:** 1.0

## 🚨 Immediate Actions (First 5 Minutes)

### 1. Acknowledge Alert
- Check notification channel (Slack/PagerDuty)
- Acknowledge in alerting system
- Set status to "Investigating"

### 2. Assess Severity
- **SEV1**: Critical - Business impact, trading halted
- **SEV2**: High - Major degradation
- **SEV3**: Medium - Service degradation
- **SEV4**: Low - Minor issue

### 3. Find Runbook
```bash
cd /Users/kepa.cantero/Projects/algoTrading/app/sre/oncall/runbooks
grep -l "KEYWORD" *.yaml
```

### 4. Communicate
- SEV1/SEV2: Page on-call, notify team immediately
- SEV3/SEV4: Update status dashboard, send to Slack

## 📋 Most Common Runbooks (Top 10)

| # | Runbook | Trigger | Severity | Duration |
|---|---------|---------|----------|----------|
| 1 | High Drawdown Alert | drawdown > 15% | Critical | 15 min |
| 2 | Circuit Breaker Triggered | auto-halt activated | Critical | 20 min |
| 3 | Broker API Failure | API unavailable | Critical | 30 min |
| 4 | Trading Halt | emergency halt | Critical | 10 min |
| 5 | Position Sync Issue | position mismatch | High | 25 min |
| 6 | API Latency Spike | p99 > 1000ms | Medium | 15 min |
| 7 | Database Slow | query > 500ms | Medium | 20 min |
| 8 | High Memory Usage | memory > 85% | High | 15 min |
| 9 | High Error Rate | errors > 1% | High | 20 min |
|10 | Strategy Drift | performance degraded | Medium | 30 min |

## 🔄 Escalation Paths

### Trading Critical (SEV1)
- **15 min**: Primary on-call
- **30 min**: Trading lead
- **45 min**: Engineering manager
- **60 min**: CTO

### Risk Management
- **30 min**: Primary on-call
- **60 min**: Risk manager
- **90 min**: Director

### Infrastructure
- **30 min**: Primary on-call
- **60 min**: Platform lead
- **90 min**: Engineering manager

## 📊 Quick Dashboard Commands

### Check Current Status
```python
from app.sre.oncall import OncallManager

manager = OncallManager()
await manager.initialize()

# Current on-call
current = await manager.get_current_oncall()

# Dashboard overview
dashboard = await manager.dashboard.get_dashboard_view()
```

### System Health Check
```bash
# Golden Signals
curl http://localhost:8000/api/health/golden-signals

# Error Budget
curl http://localhost:8000/api/sre/error-budget

# Risk Status
curl http://localhost:8000/api/risk/status
```

## 🚨 Critical Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Drawdown | > 10% | > 15% | Consider halt |
| VaR Breach | > threshold | > 20% over | Reduce exposure |
| API Latency p99 | > 500ms | > 1000ms | Investigate |
| Error Rate | > 0.5% | > 1% | Check logs |
| Memory Usage | > 75% | > 85% | Scale up |
| Disk Usage | > 80% | > 90% | Clean up |

## 📞 Important Contacts

| Role | Name | Contact |
|------|------|---------|
| On-Call (Current) | See dashboard | +1-555-ONCALL |
| Trading Lead | trading-lead | #trading |
| Risk Manager | risk-manager | #risk |
| Platform Lead | platform-lead | #platform |
| Engineering Manager | eng-manager | #engineering |
| SRE Team | sre-team | #sre |

## 🔧 Common Commands

### Check Service Status
```bash
# All services
systemctl status trading-*

# Specific service
systemctl status trading-engine

# Logs
journalctl -u trading-engine -f
```

### Database Queries
```bash
# Connect
psql -U user -d trading_db

# Check positions
SELECT * FROM positions ORDER BY updated_at DESC LIMIT 10;

# Check recent trades
SELECT * FROM trades ORDER BY executed_at DESC LIMIT 20;
```

### Restart Services
```bash
# Graceful restart
systemctl restart trading-engine

# Force kill
systemctl kill -s SIGKILL trading-engine

# Check after restart
systemctl status trading-engine
```

## 📈 Handoff Checklist

When handing off to next on-call:

- [ ] Review active incidents
- [ ] Review system status
- [ ] Discuss outstanding tasks
- [ ] Share recent learnings
- [ ] Update documentation
- [ ] Sign off handoff

**Estimated time:** 30 minutes
**Quality target:** > 70%

## 🎯 Success Criteria

Incident is resolved when:
- ✅ Service metrics back to normal
- ✅ Root cause identified
- ✅ Fix implemented and verified
- ✅ Runbook updated (if needed)
- ✅ Stakeholders notified
- ✅ Incident documented

## 📝 Post-Incident Actions

1. **Immediate** (within 1 hour)
   - Document incident
   - Update status dashboard
   - Notify stakeholders

2. **Same day**
   - Write postmortem (SEV1/SEV2)
   - Update runbooks
   - Create follow-up tasks

3. **Within 1 week**
   - Review postmortem
   - Implement preventive measures
   - Train team on lessons learned

## 🆘 Getting Help

### I'm stuck!
1. **Re-read the runbook** - You might have missed something
2. **Check logs** - `journalctl -f`, application logs
3. **Search similar incidents** - History often repeats
4. **Ask in #oncall** - Others may have seen this
5. **Escalate** - Better to escalate early than late

### Escalation is NOT failure
- Escalate if: unsure, stuck, or incident is worsening
- Document why you're escalating
- Stay involved - you still have context

## 💡 Pro Tips

### Before Your Shift
- Review recent incidents
- Check system status
- Read any updated runbooks
- Verify your access works

### During Your Shift
- Keep notes in a shared doc
- Document everything you do
- Take breaks when possible
- Ask for help early

### After Your Shift
- Complete handoff thoroughly
- Document any issues
- Update runbooks if needed
- Get some rest! 🛌

## 📱 Mobile Access

### Key Dashboards (Mobile Friendly)
- Status: `https://status.example.com`
- Metrics: `https://metrics.example.com`
- Runbooks: `https://docs.example.com/runbooks`

### Alert Response on Mobile
1. Acknowledge in alerting app
2. Open runbook (save offline!)
3. Join war room call
4. Document in shared doc

## 🔐 Security Reminders

- Never share credentials via chat
- Use secure channels for sensitive data
- Verify identity before sharing info
- Report security incidents immediately
- Follow access control procedures

---

## 🎓 Training Resources

- **New On-Call Guide**: `/app/sre/oncall/runbooks/README.md`
- **Runbook Library**: `/app/sre/oncall/runbooks/`
- **SRE Documentation**: `/docs/sre/`
- **Incident History**: Check internal wiki

## 📞 Emergency Contacts

**Life-Threatening Emergency**: Call 911
**Security Incident**: security@example.com
**Legal Issue**: legal@example.com

---

**Remember**: You're not alone. The whole team is here to support you.
When in doubt, ask for help. That's what we're here for. 💪

**Last Updated**: 2026-01-28
**Next Review**: 2026-02-28
