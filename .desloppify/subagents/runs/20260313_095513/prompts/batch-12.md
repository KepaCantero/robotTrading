You are a focused subagent reviewer for a single holistic investigation batch.

Repository root: /Users/kepa.cantero/Projects/algoTrading
Blind packet: /Users/kepa.cantero/Projects/algoTrading/.desloppify/review_packet_blind.json
Batch index: 12
Batch name: authorization_consistency
Batch rationale: seed files for authorization_consistency review

DIMENSION TO EVALUATE:

## authorization_consistency
Auth/permission patterns consistently applied across the codebase
Look for:
- Route handlers with auth decorators/middleware on some siblings but not others
- RLS enabled on some tables but not siblings in the same domain
- Permission strings as magic literals instead of shared constants
- Mixed trust boundaries: some endpoints validate user input, siblings don't
- Service role / admin bypass without audit logging or access control
Skip:
- Public routes explicitly documented as unauthenticated (health checks, login, webhooks)
- Internal service-to-service calls behind network-level auth
- Dev/test endpoints behind feature flags or environment checks

YOUR TASK: Read the code for this batch's dimension. Judge how well the codebase serves a developer from that perspective. The dimension rubric above defines what good looks like. Cite specific observations that explain your judgment.

Mechanical scan evidence — navigation aid, not scoring evidence:
The blind packet contains `holistic_context.scan_evidence` with aggregated signals from all mechanical detectors — including complexity hotspots, error hotspots, signal density index, boundary violations, and systemic patterns. Use these as starting points for where to look beyond the seed files.

Seed files (start here):
- app/api/cost_analysis.py
- app/infrastructure/middleware/rate_limit.py
- app/infrastructure/persistence/database.py
- app/main.py
- app/presentation/api/assets.py
- app/presentation/api/capa2_endpoints.py
- app/presentation/api/deployment.py
- app/presentation/api/health.py
- app/presentation/api/live_trading.py
- app/presentation/api/logging_utils.py
- app/presentation/api/logging_utils_examples.py
- app/presentation/api/market_data.py
- app/presentation/api/momentum.py
- app/presentation/api/optimization.py
- app/presentation/api/paper_trading.py
- app/presentation/api/portfolio.py
- app/presentation/api/portfolio_analytics.py
- app/presentation/api/profitability_validation.py
- app/presentation/api/security.py
- app/presentation/api/signals.py
- app/presentation/api/strategies.py
- app/presentation/api/trading_error_handler.py
- app/presentation/controllers/assets.py
- app/presentation/controllers/capa2_endpoints.py
- app/presentation/controllers/cost_analysis.py
- app/presentation/controllers/dashboard_controller.py
- app/presentation/controllers/deployment.py
- app/presentation/controllers/health.py
- app/presentation/controllers/live_trading.py
- app/presentation/controllers/market_data.py
- app/presentation/controllers/momentum.py
- app/presentation/controllers/optimization.py
- app/presentation/controllers/paper_trading.py
- app/presentation/controllers/portfolio.py
- app/presentation/controllers/portfolio_analytics.py
- app/presentation/controllers/portfolio_controller.py
- app/presentation/controllers/profitability_validation.py
- app/presentation/controllers/signals.py
- app/presentation/controllers/strategies.py
- app/presentation/controllers/strategy_controller.py
- app/presentation/controllers/trading_error_handler.py
- app/presentation/dashboard/api_router.py
- app/security/__init__.py
- app/security/auth.py
- app/shared/config/di_container.py
- app/sre/error_budgets/integration.py
- app/sre/alert_fatigue_prevention/alert_fatigue_preventer.py
- app/sre/dead_mans_switch/external_monitor.py
- app/services/live_trading/trading_audit_trail.py
- app/sre/data_integrity/sanity_layer.py
- app/sre/chaos_engine/blast_radius.py
- app/sre/error_budgets/error_budget_manager.py
- app/sre/canary_deployment/canary_deployment.py
- app/sre/chaos_engine/chaos_orchestrator.py
- app/sre/chaos_engine/hypothesis.py
- app/sre/oncall/handoff.py
- app/sre/oncall/escalation.py
- app/sre/oncall/dashboard.py
- app/presentation/dashboard/main.py
- app/sre/oncall/rotation.py
- app/services/live_trading/order_persistence.py
- app/sre/chaos_engine/game_days.py
- app/sre/monitoring/golden_signals.py
- app/sre/dead_mans_switch/dead_mans_switch.py
- app/services/metrics_database/questdb_connector.py
- app/sre/monitoring/trading_metrics.py
- app/sre/state_machine/wal_persistence.py
- app/sre/error_budgets/slo_tracker.py
- app/sre/canary_deployment/traffic_splitter.py
- app/sre/chaos_engine/stress_tester.py
- app/services/task_queue/persistent_queue.py
- app/sre/automation/toil_tracker.py

Task requirements:
1. Read the blind packet's `system_prompt` — it contains scoring rules and calibration.
2. Start from the seed files, then freely explore the repository to build your understanding.
3. Keep issues and scoring scoped to this batch's dimension.
4. Respect scope controls: do not include files/directories marked by `exclude`, `suppress`, or non-production zone overrides.
5. Return 0-10 issues for this batch (empty array allowed).
6. Complete `dimension_judgment` for your dimension — all three fields (strengths, issue_character, score_rationale) are required. Write the judgment BEFORE setting the score.
7. Do not edit repository files.
8. Return ONLY valid JSON, no markdown fences.

Scope enums:
- impact_scope: "local" | "module" | "subsystem" | "codebase"
- fix_scope: "single_edit" | "multi_file_refactor" | "architectural_change"

Output schema:
{
  "batch": "authorization_consistency",
  "batch_index": 12,
  "assessments": {"<dimension>": <0-100 with one decimal place>},
  "dimension_notes": {
    "<dimension>": {
      "evidence": ["specific code observations"],
      "impact_scope": "local|module|subsystem|codebase",
      "fix_scope": "single_edit|multi_file_refactor|architectural_change",
      "confidence": "high|medium|low",
      "issues_preventing_higher_score": "required when score >85.0",
      "sub_axes": {"abstraction_leverage": 0-100, "indirection_cost": 0-100, "interface_honesty": 0-100, "delegation_density": 0-100, "definition_directness": 0-100, "type_discipline": 0-100}  // required for abstraction_fitness when evidence supports it; all one decimal place
    }
  },
  "dimension_judgment": {
    "<dimension>": {
      "strengths": ["0-5 specific things the codebase does well from this dimension's perspective"],
      "issue_character": "one sentence characterizing the nature/pattern of issues from this dimension's perspective",
      "score_rationale": "2-3 sentences explaining the score from this dimension's perspective, referencing global anchors"
    }  // required for every assessed dimension; do not omit
  },
  "issues": [{
    "dimension": "<dimension>",
    "identifier": "short_id",
    "summary": "one-line defect summary",
    "related_files": ["relative/path.py"],
    "evidence": ["specific code observation"],
    "suggestion": "concrete fix recommendation",
    "confidence": "high|medium|low",
    "impact_scope": "local|module|subsystem|codebase",
    "fix_scope": "single_edit|multi_file_refactor|architectural_change",
    "root_cause_cluster": "optional_cluster_name_when_supported_by_history",
    "concern_verdict": "confirmed|dismissed  // for concern signals only",
    "concern_fingerprint": "abc123  // required when dismissed; copy from signal fingerprint",
    "reasoning": "why dismissed  // optional, for dismissed only"
  }],
  "retrospective": {
    "root_causes": ["optional: concise root-cause hypotheses"],
    "likely_symptoms": ["optional: identifiers that look symptom-level"],
    "possible_false_positives": ["optional: prior concept keys likely mis-scoped"]
  }
}
