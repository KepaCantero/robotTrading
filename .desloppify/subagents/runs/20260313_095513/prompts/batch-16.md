You are a focused subagent reviewer for a single holistic investigation batch.

Repository root: /Users/kepa.cantero/Projects/algoTrading
Blind packet: /Users/kepa.cantero/Projects/algoTrading/.desloppify/review_packet_blind.json
Batch index: 16
Batch name: initialization_coupling
Batch rationale: seed files for initialization_coupling review

DIMENSION TO EVALUATE:

## initialization_coupling
Boot-order dependencies, import-time side effects, global singletons
Look for:
- Module-level code that depends on another module having been imported first
- Import-time side effects: DB connections, file I/O, network calls at module scope
- Global singletons where creation order matters across modules
- Environment variable reads at import time (fragile in testing)
- Circular init dependencies hidden behind conditional or lazy imports
- Module-level constants computed at import time alongside a dynamic getter function — consumers referencing the stale snapshot instead of calling the getter
Skip:
- Standard library initialization (logging.basicConfig)
- Framework bootstrap (app.configure, server.listen)

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
- app/presentation/api/strategies.py
- app/presentation/api/optimization.py
- app/presentation/api/live_trading.py
- app/presentation/api/paper_trading.py
- app/presentation/api/signals.py
- app/presentation/api/momentum.py
- app/presentation/api/portfolio_analytics.py
- alembic/env.py
- app/application/alerting/alerting_orchestrator.py
- app/application/orchestration/target_optimization/absolute_return_optimizer.py
- app/application/scheduling/examples.py
- app/application/scheduling/market_scheduler.py
- app/application/services/risk_configurator.py
- app/application/use_cases/run_backtest_use_case.py
- app/backtesting/acceptance_criteria.py
- app/backtesting/advanced_visualizations.py
- app/backtesting/bias_correctors.py
- app/backtesting/capital_scale_analyzer.py
- app/backtesting/clustering_analyzer.py
- app/backtesting/core/error_handling.py
- app/backtesting/core/facade.py
- app/backtesting/core/memory_manager.py
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
- app/backtesting/successful_configs.py
- app/backtesting/validation/drawdown_validator.py
- app/backtesting/validation/purged_kfold.py
- app/domain/analysis/fundamental_law/models.py
- app/domain/analysis/vectorization/benchmark.py
- app/domain/analysis/vectorization/demo.py
- app/domain/analysis/vectorization/models.py
- app/domain/analysis/vectorization/patterns.py
- app/domain/analysis/vectorization/vectorization_auditor.py
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
- app/domain/optimization/parameter/bayesian_optimizer.py
- app/domain/optimization/parameter/models.py
- app/domain/optimization/parameter/multi_objective.py
- app/domain/optimization/parameter/random_search.py
- app/domain/optimization/parameter/trial.py
- app/domain/optimization/sensitivity_analyzer.py
- app/domain/portfolio/multi_asset/allocation.py
- app/domain/portfolio/multi_asset/models.py
- app/domain/portfolio/multi_asset/rebalancer.py
- app/domain/portfolio_optimization/mean_variance_optimizer.py
- app/domain/portfolio_optimization/nested_clustered_optimization.py

RELEVANT FINDINGS — explore with CLI:
These detectors found patterns related to this dimension. Explore the findings,
then read the actual source code.

  desloppify show global_mutable_config --no-budget      # 188 findings

Report actionable issues in issues[]. Use concern_verdict and concern_fingerprint
for findings you want to confirm or dismiss.

Task requirements:
1. Read the blind packet's `system_prompt` — it contains scoring rules and calibration.
2. Start from the seed files, then freely explore the repository to build your understanding.
3. Keep issues and scoring scoped to this batch's dimension.
4. Respect scope controls: do not include files/directories marked by `exclude`, `suppress`, or non-production zone overrides.
5. Return 0-10 issues for this batch (empty array allowed).
6. For initialization_coupling, use evidence from `holistic_context.scan_evidence.mutable_globals` and `holistic_context.errors.mutable_globals`. Investigate initialization ordering dependencies, coupling through shared mutable state, and whether state should be encapsulated behind a proper registry/context manager.
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
  "batch": "initialization_coupling",
  "batch_index": 16,
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
