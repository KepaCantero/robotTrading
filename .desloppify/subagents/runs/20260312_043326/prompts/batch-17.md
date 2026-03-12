You are a focused subagent reviewer for a single holistic investigation batch.

Repository root: /Users/kepa.cantero/Projects/algoTrading
Blind packet: /Users/kepa.cantero/Projects/algoTrading/.desloppify/review_packet_blind.json
Batch index: 17
Batch name: design_coherence
Batch rationale: seed files for design_coherence review

DIMENSION TO EVALUATE:

## design_coherence
Are structural design decisions sound — functions focused, abstractions earned, patterns consistent?
Look for:
- Functions doing too many things — multiple distinct responsibilities in one body
- Parameter lists that should be config/context objects — many related params passed together
- Files accumulating issues across many dimensions — likely mixing unrelated concerns
- Deep nesting that could be flattened with early returns or extraction
- Repeated structural patterns that should be data-driven
Skip:
- Functions that are long but have a single coherent responsibility
- Parameter lists where grouping would obscure meaning — do NOT recommend config/context objects or dependency injection wrappers just to reduce parameter count; only group when the grouping has independent semantic meaning
- Files that are large because their domain is genuinely complex, not because they mix concerns
- Nesting that is inherent to the problem (e.g., recursive tree processing)
- Do NOT recommend extracting callable parameters or injecting dependencies for 'testability' — direct function calls are simpler and preferred unless there is a concrete decoupling need

YOUR TASK: Read the code for this batch's dimension. Judge how well the codebase serves a developer from that perspective. The dimension rubric above defines what good looks like. Cite specific observations that explain your judgment.

Mechanical scan evidence — navigation aid, not scoring evidence:
The blind packet contains `holistic_context.scan_evidence` with aggregated signals from all mechanical detectors — including complexity hotspots, error hotspots, signal density index, boundary violations, and systemic patterns. Use these as starting points for where to look beyond the seed files.

Seed files (start here):
- app/shared/config/di_container.py
- app/domain/market_analysis/microstructure/models.py
- app/domain/market_analysis/microstructure/trading_mechanisms.py
- app/presentation/api/capa2_endpoints.py
- app/presentation/controllers/capa2_endpoints.py
- app/presentation/controllers/strategies.py
- app/engines/execution_engine/microstructure/adverse_selection_detector.py
- app/services/xai/explainer.py
- app/domain/market_analysis/microstructure/liquidity.py
- app/domain/market_analysis/microstructure/order_flow.py
- app/domain/market_analysis/microstructure/price_discovery.py
- app/infrastructure/persistence/database.py
- app/security/csrf_protection.py
- app/services/live_trading/trading_audit_trail.py
- app/services/multi_strategy_allocation.py
- app/services/synthetic_data/gan_generator.py
- app/__init__.py
- app/application/reporting/reporting_orchestrator.py
- app/backtesting/config_loader.py
- app/domain/services/compliance/compliance_integration.py
- app/presentation/dashboard/advanced_dashboard.py
- app/backtesting/comprehensive_backtest_runner.py
- app/application/use_cases/select_strategy.py
- examples/harris_trading_example.py
- app/domain/strategies/modules/filters/rsi_filter.py
- app/domain/strategies/strategy.py
- scripts/run_full_backtest_suite.py
- app/backtesting/engine.py
- app/domain/services/compliance/compliance_engine.py
- app/domain/strategies/momentum.py
- app/domain/services/metrics/performance_metrics.py
- app/domain/strategies/learning/subprocess_engine_wrapper.py
- app/domain/strategies/roll_analyzer.py
- scripts/backtesting/simple/run_progressive_backtest.py
- app/presentation/api/live_trading.py
- app/presentation/api/strategies.py
- app/presentation/api/momentum.py
- app/presentation/api/optimization.py
- scripts/backtesting/simple/run_comprehensive_regime_backtest.py
- app/services/live_trading/broker_adapters/ib_adapter.py
- app/sre/oncall/dashboard.py
- alembic/env.py
- app/application/alerting/alerting_orchestrator.py
- app/application/orchestration/target_optimization/absolute_return_optimizer.py
- app/application/orchestration/target_optimization/capital_tier_selector.py
- app/application/scheduling/examples.py
- app/application/scheduling/market_scheduler.py
- app/application/services/risk_configurator.py
- app/application/use_cases/execute_strategy_use_case.py
- app/application/use_cases/run_backtest_use_case.py
- app/backtesting/acceptance_criteria.py
- app/backtesting/advanced_visualizations.py
- app/backtesting/bias_correctors.py
- app/backtesting/capital_scale_analyzer.py
- app/backtesting/clustering_analyzer.py
- app/backtesting/core/error_handling.py
- app/backtesting/core/facade.py
- app/backtesting/core/memory_manager.py
- app/backtesting/drift_detection/drift_detectors.py
- app/backtesting/engines/execution_engine.py
- app/backtesting/engines/factory.py
- app/backtesting/engines/standard_engine.py
- app/backtesting/execution/backtest_config_loader.py
- app/backtesting/execution/models.py
- app/backtesting/execution/transaction_cost.py
- app/backtesting/feature_engineering/feature_importance_uniqueness.py
- app/backtesting/feature_engineering/fracdiff_visualizations.py
- app/backtesting/labeling/bet_sizing_meta.py
- app/backtesting/labeling/meta_labeling.py
- app/backtesting/liquidity_validator.py
- app/backtesting/meta_analyzer/audit_trail.py
- app/backtesting/meta_analyzer/integration.py
- app/backtesting/meta_analyzer/learning_storage.py
- app/backtesting/professional_reporter.py
- app/backtesting/profile_batch/bayesian_optimizer.py
- app/backtesting/profile_batch/profile_generator.py
- app/backtesting/realistic_data_generator.py
- app/backtesting/report_generator.py
- app/backtesting/robust_engine/corporate_actions.py
- app/backtesting/robust_engine/look_ahead_validator.py
- app/backtesting/robust_engine/pit_database.py
- app/backtesting/robust_engine/survivorship_adjuster.py
- app/backtesting/robustness_tester.py
- app/backtesting/runners/result_aggregator.py
- app/backtesting/seasonality_analyzer.py
- app/backtesting/services/trade_executor.py
- app/backtesting/services/transaction_cost_model.py
- app/backtesting/shared/temp_config.py
- app/backtesting/shared/trade_utils.py
- app/backtesting/signal_diagnostic_logger.py
- app/backtesting/successful_configs.py
- app/backtesting/validation/drawdown_validator.py
- app/backtesting/validation/purged_kfold.py
- app/domain/analysis/fundamental_law/models.py
- app/domain/analysis/vectorization/benchmark.py
- app/domain/analysis/vectorization/demo.py
- app/domain/analysis/vectorization/models.py
- app/domain/analysis/vectorization/patterns.py
- app/domain/analysis/vectorization/vectorization_auditor.py
- app/domain/engines/rebalance_engine.py
- app/domain/ensemble/ensemble.py
- app/domain/ensemble/models.py
- app/domain/ensemble/pareto.py
- app/domain/entities/order.py
- app/domain/entities/position.py
- app/domain/entities/trade.py
- app/domain/market_analysis/microstructure/ofi/ofi_calculator.py
- app/domain/market_analysis/microstructure/ofi/ofi_signals.py
- app/domain/market_analysis/microstructure/ofi/tick_processor.py
- app/domain/models/assets.py
- app/domain/models/investment_profile.py
- app/domain/models/optimization.py
- app/domain/models/portfolio.py
- app/domain/models/profitability_validation.py
- app/domain/optimization/momentum_auto_optimizer.py
- app/domain/optimization/multi_strategy_optimizer_v2.py
- app/domain/optimization/parameter/bayesian_optimizer.py
- app/domain/optimization/parameter/models.py
- app/domain/optimization/parameter/multi_objective.py
- app/domain/optimization/parameter/random_search.py

Mechanical concern signals — investigate and adjudicate:
Overview (680 signals):
  design_concern: 347 — alembic/env.py, app/__init__.py, ...
  mixed_responsibilities: 247 — app/api/cost_analysis.py, app/application/reporting/reporting_orchestrator.py, ...
  duplication_design: 46 — app.py, app/backtesting/profile_batch/optimization_pipeline.py, ...
  structural_complexity: 30 — app/application/services/input_profile_router.py, app/backtesting/constants.py, ...
  interface_design: 10 — app/backtesting/execution/slippage_model.py, app/domain/services/compliance/system_bus_extracted.py, ...

For each concern, read the source code and report your verdict in issues[]:
  - Confirm → full issue object with concern_verdict: "confirmed"
  - Dismiss → minimal object: {concern_verdict: "dismissed", concern_fingerprint: "<hash>"}
    (only these 2 fields required — add optional reasoning/concern_type/concern_file)
  - Unsure → skip it (will be re-evaluated next review)

  - [design_concern] alembic/env.py
    summary: Design signals from smells
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells
    evidence: [smells] 2x Loose type annotation — use specific types
    fingerprint: 3f1bc4a1af68b307
  - [design_concern] app/__init__.py
    summary: Design signals from global_mutable_config, smells
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: global_mutable_config, smells
    evidence: [smells] 1x Global keyword usage
    fingerprint: f3b634b3084a6d73
  - [design_concern] app/application/alerting/alerting_orchestrator.py
    summary: Design signals from signature, smells
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: signature, smells
    evidence: [signature] 'resolve_alert' has 4 different signatures across 7 files
    fingerprint: a2deae3ac6899ed2
  - [design_concern] app/application/orchestration/target_optimization/absolute_return_optimizer.py
    summary: Design signals from signature, smells
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: signature, smells
    evidence: [signature] 'calculate_required_alpha' has 3 different signatures across 3 files
    fingerprint: 2a44daac14b69cb9
  - [design_concern] app/application/orchestration/target_optimization/capital_tier_selector.py
    summary: Design signals from smells
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells
    evidence: [smells] 1x Loose type annotation — use specific types
    fingerprint: 73510cd72fa3a8f5
  - [design_concern] app/application/scheduling/examples.py
    summary: Design signals from smells
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells
    evidence: [smells] 9x Loose type annotation — use specific types
    fingerprint: 4ec769777851d8c5
  - [design_concern] app/application/scheduling/market_scheduler.py
    summary: Design signals from smells, structural
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells, structural
    evidence: File size: 696 lines
    fingerprint: 07631a6a72386d17
  - [design_concern] app/application/services/risk_configurator.py
    summary: Design signals from signature, structural
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: signature, structural
    evidence: File size: 509 lines
    fingerprint: a87994366922839f
  - [design_concern] app/application/use_cases/execute_strategy_use_case.py
    summary: Design signals from smells
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells
    evidence: [smells] 1x High cyclomatic complexity (>12 decision points)
    fingerprint: bb488943cc44d405
  - [design_concern] app/application/use_cases/run_backtest_use_case.py
    summary: Design signals from signature, smells
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: signature, smells
    evidence: [signature] 'execute_batch' has 3 different signatures across 3 files
    fingerprint: 14bf9fccf131c9e5
  - [design_concern] app/backtesting/acceptance_criteria.py
    summary: Design signals from signature, smells
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: signature, smells
    evidence: [signature] 'validate_strategy' has 7 different signatures across 7 files
    fingerprint: 88d22ccc69153212
  - [design_concern] app/backtesting/advanced_visualizations.py
    summary: Design signals from smells, structural
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells, structural
    evidence: File size: 782 lines
    fingerprint: 1f68a83d13f72319
  - [design_concern] app/backtesting/bias_correctors.py
    summary: Design signals from smells, structural
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells, structural
    evidence: File size: 677 lines
    fingerprint: 60cb9cfa197b7416
  - [design_concern] app/backtesting/capital_scale_analyzer.py
    summary: Design signals from smells, structural
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells, structural
    evidence: File size: 567 lines
    fingerprint: 75c10d989c33337e
  - [design_concern] app/backtesting/clustering_analyzer.py
    summary: Design signals from smells, structural
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells, structural
    evidence: File size: 517 lines
    fingerprint: 0eb8d967b54464e4
  - [design_concern] app/backtesting/core/error_handling.py
    summary: Design signals from smells, structural
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells, structural
    evidence: File size: 503 lines
    fingerprint: f076913ab44d5357
  - [design_concern] app/backtesting/core/facade.py
    summary: Design signals from smells, structural
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells, structural
    evidence: File size: 575 lines
    fingerprint: 9cfdf168cc8b789f
  - [design_concern] app/backtesting/core/memory_manager.py
    summary: Design signals from smells
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells
    evidence: [smells] 1x Loose type annotation — use specific types
    fingerprint: 0f2e41484d71069a
  - [design_concern] app/backtesting/drift_detection/drift_detectors.py
    summary: Design signals from signature
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: signature
    evidence: [signature] 'detect' has 13 different signatures across 12 files
    fingerprint: f749cafdbf1316d8
  - [design_concern] app/backtesting/engines/execution_engine.py
    summary: Design signals from smells, structural
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells, structural
    evidence: File size: 629 lines
    fingerprint: 61afc665b20aed6d
  - [design_concern] app/backtesting/engines/factory.py
    summary: Design signals from smells
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells
    evidence: [smells] 8x Except handler silently suppresses error (pass/continue, no log)
    fingerprint: 1f165d48d7f8a6ac
  - [design_concern] app/backtesting/engines/standard_engine.py
    summary: Design signals from smells, structural
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells, structural
    evidence: File size: 927 lines
    fingerprint: 56b66ee9901f2ac5
  - [design_concern] app/backtesting/execution/backtest_config_loader.py
    summary: Design signals from smells
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells
    evidence: [smells] 1x Catch block that only logs (swallowed error)
    fingerprint: ceac8e83fb9cd41b
  - [design_concern] app/backtesting/execution/models.py
    summary: Design signals from smells, structural
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells, structural
    evidence: File size: 596 lines
    fingerprint: facbc34c5e54d2de
  - [design_concern] app/backtesting/execution/transaction_cost.py
    summary: Design signals from structural
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: structural
    evidence: File size: 615 lines
    fingerprint: ce13429cbcdcbac4
  - [design_concern] app/backtesting/feature_engineering/feature_importance_uniqueness.py
    summary: Design signals from structural
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: structural
    evidence: File size: 789 lines
    fingerprint: be03e4e774413bf4
  - [design_concern] app/backtesting/feature_engineering/fracdiff_visualizations.py
    summary: Design signals from structural
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: structural
    evidence: File size: 636 lines
    fingerprint: 5e83abd04ba38d08
  - [design_concern] app/backtesting/labeling/bet_sizing_meta.py
    summary: Design signals from smells, structural
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: smells, structural
    evidence: File size: 880 lines
    fingerprint: c19918533953fff8
  - [design_concern] app/backtesting/labeling/meta_labeling.py
    summary: Design signals from structural
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: structural
    evidence: File size: 646 lines
    fingerprint: dcf2b73803c3de5f
  - [design_concern] app/backtesting/liquidity_validator.py
    summary: Design signals from signature, smells
    question: Review the flagged patterns — are they design problems that need addressing, or acceptable given the file's role?
    evidence: Flagged by: signature, smells
    evidence: [signature] 'get_liquidity_metrics' has 4 different signatures across 4 files
    fingerprint: 7c2e503fca8e04b2
  (+650 more — use `desloppify show <detector> --no-budget` to explore)

RELEVANT FINDINGS — explore with CLI:
These detectors found patterns related to this dimension. Explore the findings,
then read the actual source code.

  desloppify show boilerplate_duplication --no-budget      # 346 findings
  desloppify show cycles --no-budget      # 1 findings
  desloppify show dict_keys --no-budget      # 414 findings
  desloppify show dupes --no-budget      # 264 findings
  desloppify show facade --no-budget      # 3 findings
  desloppify show global_mutable_config --no-budget      # 185 findings
  desloppify show props --no-budget      # 6 findings
  desloppify show responsibility_cohesion --no-budget      # 36 findings
  desloppify show signature --no-budget      # 228 findings
  desloppify show single_use --no-budget      # 1 findings
  desloppify show smells --no-budget      # 1118 findings
  desloppify show structural --no-budget      # 466 findings
  desloppify show uncalled_functions --no-budget      # 19 findings
  desloppify show unused --no-budget      # 512 findings
  desloppify show unused_enums --no-budget      # 57 findings

Report actionable issues in issues[]. Use concern_verdict and concern_fingerprint
for findings you want to confirm or dismiss.

Task requirements:
1. Read the blind packet's `system_prompt` — it contains scoring rules and calibration.
2. Start from the seed files, then freely explore the repository to build your understanding.
3. Keep issues and scoring scoped to this batch's dimension.
4. Respect scope controls: do not include files/directories marked by `exclude`, `suppress`, or non-production zone overrides.
5. Return 0-10 issues for this batch (empty array allowed).
6. For design_coherence, use evidence from `holistic_context.scan_evidence.signal_density` — files where multiple mechanical detectors fired. Investigate what design change would address multiple signals simultaneously. Check `scan_evidence.complexity_hotspots` for files with high responsibility cluster counts.
7. Workflow integrity checks: when reviewing orchestration/queue/review flows,
8. xplicitly look for loop-prone patterns and blind spots:
9. - repeated stale/reopen churn without clear exit criteria or gating,
10. - packet/batch data being generated but dropped before prompt execution,
11. - ranking/triage logic that can starve target-improving work,
12. - reruns happening before existing open review work is drained.
13. If found, propose concrete guardrails and where to implement them.
14. Complete `dimension_judgment` for your dimension — all three fields (strengths, issue_character, score_rationale) are required. Write the judgment BEFORE setting the score.
15. Do not edit repository files.
16. Return ONLY valid JSON, no markdown fences.

Scope enums:
- impact_scope: "local" | "module" | "subsystem" | "codebase"
- fix_scope: "single_edit" | "multi_file_refactor" | "architectural_change"

Output schema:
{
  "batch": "design_coherence",
  "batch_index": 17,
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
