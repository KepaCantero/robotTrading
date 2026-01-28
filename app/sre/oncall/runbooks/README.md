# On-Call Runbooks

Comprehensive library of operational procedures for on-call incident response.

## Runbook Categories

### Risk Management
- `01_high_drawdown_alert.yaml` - Respond to portfolio drawdown exceeding 15%
- `02_circuit_breaker_triggered.yaml` - Handle automatic trading halt triggers
- `03_var_breach.yaml` - Address Value at Risk limit violations

### Trading Operations
- `06_broker_api_failure.yaml` - Manage broker API unavailability
- `07_position_sync_issue.yaml` - Resolve position record mismatches
- `11_order_execution_failure.yaml` - Handle failed trade orders
- `12_trading_halt.yaml` - Execute emergency trading stops

### Market Data
- `05_market_data_quality_issue.yaml` - Address data quality problems

### Infrastructure
- `09_service_restarted_unexpectedly.yaml` - Investigate service crashes
- `10_database_slow.yaml` - Resolve database performance issues
- `13_high_memory_usage.yaml` - Manage memory exhaustion risks
- `14_disk_space_low.yaml` - Handle storage capacity issues
- `15_network_connectivity_issue.yaml` - Resolve network problems

### Application
- `04_api_latency_spike.yaml` - Address API performance degradation
- `08_strategy_drift_detected.yaml` - Handle strategy performance decline
- `18_high_error_rate.yaml` - Respond to elevated error rates

### Deployment
- `17_deployment_rollback.yaml` - Execute deployment rollbacks
- `20_configuration_drift.yaml` - Resolve configuration inconsistencies

### Monitoring & SRE
- `16_alert_fatigue_detected.yaml` - Address excessive alert volume
- `19_oncall_handover_required.yaml` - Execute on-call shift transitions

## Runbook Structure

Each runbook follows a consistent structure:

```yaml
---
name: "Incident Name"
severity: critical|high|medium|low
trigger: "alert_condition"
category: "risk|trading|infrastructure|application|deployment|monitoring|oncall"
tags: ["tag1", "tag2"]
estimated_duration_minutes: 15
last_updated: "2026-01-28"
version: "1.0"

description: |
  Detailed description of the incident and runbook purpose.

prerequisites:
  - Required access and tools
  - Knowledge requirements

steps:
  - title: "Step Title"
    description: "What this step accomplishes"
    commands:
      - "Specific command or action"
    expected_outcome: "What success looks like"
    decision_point:
      condition: "condition_to_check"
      true_branch: "Action if true"
      false_branch: "Action if false"

post_actions:
  - Follow-up actions after incident resolution

rollback_actions:
  - title: "Rollback Title"
    description: "When to rollback"

related_runbooks:
  - "related_runbook1.yaml"
  - "related_runbook2.yaml"

metrics_to_track:
  - "metric1"
  - "metric2"

success_criteria:
  - "Criteria 1"
  - "Criteria 2"

escalation_path: "path_name"
owner: "team-name"
review_frequency: "monthly|quarterly|as_needed"
```

## Using Runbooks

### During an Incident

1. **Identify the incident type** from alerts or symptoms
2. **Locate the appropriate runbook** from this directory
3. **Follow steps sequentially** - don't skip steps
4. **Document deviations** - note any steps you modify or skip
5. **Update runbook** after incident with lessons learned

### Finding Runbooks

Runbooks are organized by:
- **Severity** - Critical incidents first
- **Category** - Functional area
- **Trigger** - Alert condition

Search by:
```bash
# Find runbooks by severity
grep -l "severity: critical" *.yaml

# Find runbooks by category
grep -l "category: risk" *.yaml

# Find runbooks by trigger
grep -l "drawdown" *.yaml
```

### Executing Runbooks

1. **Read the entire runbook first** - understand the full procedure
2. **Check prerequisites** - ensure you have required access
3. **Follow steps in order** - each step builds on previous
4. **Use decision points** - follow conditional logic
5. **Document everything** - note what you did and why
6. **Verify success** - confirm success criteria met
7. **Complete post-actions** - don't skip follow-up tasks

### Decision Points

Many runbooks include decision points that branch based on conditions:

```yaml
decision_point:
  condition: "drawdown > 20%"
  true_branch: "Halt trading immediately"
  false_branch: "Monitor and prepare reduction plan"
```

Evaluate the condition honestly - don't assume the less severe branch.

## Contributing to Runbooks

### After an Incident

1. **Update the runbook** with what you learned
2. **Add missing steps** if anything was unclear
3. **Improve descriptions** if something was confusing
4. **Add new runbooks** for new incident types
5. **Update success criteria** based on real experience

### Runbook Quality Standards

- **Clear descriptions** - each step should be unambiguous
- **Specific commands** - include exact commands to run
- **Expected outcomes** - define what success looks like
- **Decision criteria** - make conditions measurable
- **Related runbooks** - link to related procedures
- **Metrics to track** - include relevant metrics
- **Success criteria** - define completion clearly

### Version Control

All runbooks are versioned:
- Update `version` when making changes
- Update `last_updated` timestamp
- Document changes in commit messages
- Tag major runbook rewrites

## Runbook Maintenance

### Regular Reviews

Runbooks are reviewed on different schedules based on `review_frequency`:
- **Monthly** - High-frequency incidents (performance, errors)
- **Quarterly** - Medium-frequency incidents (risk, infrastructure)
- **As Needed** - Low-frequency incidents (emergency procedures)
- **Weekly** - On-call procedures

### Review Checklist

During reviews, check:
- [ ] Triggers are still accurate
- [ ] Steps are still relevant
- [ ] Commands still work
- [ ] Contacts are current
- [ ] Success criteria appropriate
- [ ] Metrics still tracked
- [ ] Related runbooks linked
- [ ] Lessons learned incorporated

## Escalation Paths

Runbooks reference escalation paths defined in the escalation system:

- `trading_critical` - SEV1 trading issues
- `risk_management` - Risk limit violations
- `performance` - Performance degradation
- `trading_ops` - Trading operations issues
- `infrastructure` - Infrastructure problems
- `strategy` - Strategy performance issues
- `data_operations` - Data quality issues
- `platform` - Platform and deployment issues
- `sre` - SRE practices and monitoring
- `oncall` - On-call procedures

## Metrics and Monitoring

Runbooks reference specific metrics that should be tracked:

- **Risk Metrics**: drawdown_percentage, var_percentage, circuit_breaker_status
- **Trading Metrics**: order_success_rate, execution_latency_p99
- **Performance Metrics**: api_latency_p99, database_latency_p99
- **Infrastructure Metrics**: memory_usage_percentage, disk_usage_percentage
- **Application Metrics**: error_rate_percentage, alert_volume_per_day
- **On-Call Metrics**: handover_quality_score, oncall_burden_score

## Training

### New On-Call Engineers

1. **Read all runbooks** - familiarize yourself with procedures
2. **Simulate incidents** - practice using runbooks in simulation mode
3. **Shadow experienced engineers** - learn from real incidents
4. **Start with low-severity** - handle less critical incidents first
5. **Debrief after incidents** - discuss what went well and what didn't

### Ongoing Training

- **Quarterly drills** - practice common incidents
- **Post-incident reviews** - learn from real incidents
- **Runbook updates** - stay current with procedures
- **Cross-training** - learn other team's runbooks

## Support

### Questions About Runbooks

- Check with your team lead
- Consult the SRE team
- Review incident history
- Check related runbooks

### Runbook Issues

If you find problems with a runbook:
1. Note the issue during the incident
2. Document what was wrong
3. Propose improvements
4. Update the runbook
5. Share with the team

## Best Practices

### During Incidents

- **Stay calm** - follow the runbook step by step
- **Communicate** - keep stakeholders informed
- **Document** - record everything you do
- **Verify** - confirm each step's outcome
- **Ask for help** - escalate if needed

### After Incidents

- **Update runbooks** - incorporate lessons learned
- **Share knowledge** - tell the team what happened
- **Improve monitoring** - add alerts for similar issues
- **Prevent recurrence** - address root causes

### Always

- **Prioritize safety** - protect the system and data
- **Be honest** - accurately report conditions
- **Learn continuously** - improve procedures constantly
- **Support each other** - help your on-call colleagues

## Additional Resources

- [SRE On-Call Procedures](../README.md)
- [Escalation Policies](../escalation.py)
- [Handoff Procedures](../handoff.py)
- [Rotation Management](../rotation.py)
- [On-Call Dashboard](../dashboard.py)

## Contact

For questions about runbooks or on-call procedures:
- **SRE Team**: sre@example.com
- **On-Call Slack**: #oncall
- **Emergency**: +1-555-ONCALL

---

Remember: Runbooks are living documents. They improve with every incident.
Keep them current, and they'll keep you prepared.
