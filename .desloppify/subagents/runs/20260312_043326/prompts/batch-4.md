You are a focused subagent reviewer for a single holistic investigation batch.

Repository root: /Users/kepa.cantero/Projects/algoTrading
Blind packet: /Users/kepa.cantero/Projects/algoTrading/.desloppify/review_packet_blind.json
Batch index: 4
Batch name: error_consistency
Batch rationale: seed files for error_consistency review

DIMENSION TO EVALUATE:

## error_consistency
Consistent error strategies, preserved context, predictable failure modes
Look for:
- Mixed error strategies: some functions throw, others return null, others use Result types
- Error context lost at boundaries: catch-and-rethrow without wrapping original
- Inconsistent error types: custom error classes in some modules, bare strings in others
- Silent error swallowing: catches that log but don't propagate or recover
- Missing error handling on I/O boundaries (file, network, parse operations)
Skip:
- Intentional error boundaries at top-level handlers
- Different strategies for different layers (e.g. Result in core, throw in CLI)

YOUR TASK: Read the code for this batch's dimension. Judge how well the codebase serves a developer from that perspective. The dimension rubric above defines what good looks like. Cite specific observations that explain your judgment.

Mechanical scan evidence — navigation aid, not scoring evidence:
The blind packet contains `holistic_context.scan_evidence` with aggregated signals from all mechanical detectors — including complexity hotspots, error hotspots, signal density index, boundary violations, and systemic patterns. Use these as starting points for where to look beyond the seed files.

Seed files (start here):
- app/application/orchestration/target_optimization/absolute_return_optimizer.py
- app/application/orchestration/target_optimization/capital_tier_selector.py
- app/application/reporting/quantstats_integration.py
- app/application/reporting/report_templates.py
- app/application/services/portfolio_service_v2.py
- app/application/services/tax_optimizer.py
- app/application/use_cases/analyze_backtest_results_use_case.py
- app/application/use_cases/create_portfolio_use_case.py
- app/application/use_cases/rebalance_portfolio_use_case.py
- app/application/use_cases/run_backtest_use_case.py
- app/application/use_cases/execute_strategy_use_case.py
- app/application/use_cases/select_strategy.py
- app/backtesting/acceptance/models.py
- app/backtesting/constants.py
- app/backtesting/liquidity_validator.py
- app/backtesting/numba_metrics.py
- app/backtesting/models.py
- app/backtesting/acceptance_criteria.py
- app/backtesting/advanced_metrics.py
- app/backtesting/advanced_visualizations.py
- app/backtesting/awesome_quant_integrator.py
- app/backtesting/report_generator.py
- app/backtesting/backtest_multi_strategy.py
- app/backtesting/backtest_regime.py
- app/backtesting/backtest_validator.py
- app/backtesting/clustering_analyzer.py
- app/backtesting/config_loader.py
- app/backtesting/data_split.py
- app/backtesting/parallel_executor.py
- app/backtesting/realistic_data_generator.py
- app/backtesting/regime_analyzer.py
- app/backtesting/survivorship_bias_corrector.py
- app/backtesting/backtesting_compliance.py
- app/backtesting/base_engine.py
- app/backtesting/data_loader.py
- app/backtesting/engine.py
- app/backtesting/financial_ml.py
- app/backtesting/point_in_time_database.py
- app/backtesting/professional_reporter.py
- app/backtesting/profile_batch_backtester.py
- app/backtesting/robustness_tester.py
- app/backtesting/seasonality_analyzer.py
- app/backtesting/signal_diagnostic_logger.py
- app/backtesting/successful_configs.py
- app/backtesting/universe_manager.py
- app/backtesting/core/error_handling.py
- app/backtesting/core/memory_manager.py
- app/backtesting/engines/factory.py
- app/backtesting/engines/execution_engine.py
- app/backtesting/engines/standard_engine.py
- app/backtesting/engines/multi_strategy_engine.py
- app/backtesting/engines/robust_engine.py
- app/backtesting/execution/backtest_config_loader.py
- app/backtesting/execution/backtest_orchestrator.py
- app/backtesting/execution/backtest_results_processor.py
- app/backtesting/execution/models.py
- app/backtesting/execution/slippage_model.py
- app/backtesting/feature_engineering/fracdiff_visualizations.py
- app/backtesting/feature_engineering/fractional_differentiation.py
- app/backtesting/labeling/triple_barrier.py
- app/backtesting/labeling/bet_sizing.py
- app/backtesting/meta_analyzer/integration.py
- app/backtesting/profile_batch/bayesian_optimizer.py
- app/backtesting/profile_batch/optimization_pipeline.py
- app/backtesting/profile_batch/optimization_validators.py
- app/backtesting/profile_batch/report_generator.py
- app/backtesting/profile_batch/result_aggregator.py
- app/backtesting/robust_engine/look_ahead_validator.py
- app/backtesting/robust_engine/dividend_handler.py
- app/backtesting/robust_engine/models.py
- app/backtesting/robust_engine/pit_database.py
- app/backtesting/runners/regime_analyzer.py
- app/backtesting/runners/monte_carlo_simulator.py
- app/backtesting/services/fallback_tracker.py
- app/backtesting/services/performance_calculator.py
- app/backtesting/services/trade_executor.py
- app/backtesting/services/batch_execution_service.py
- app/backtesting/services/database_service.py
- app/backtesting/services/equity_tracker.py
- app/backtesting/services/exit_monitor.py

RELEVANT FINDINGS — explore with CLI:
These detectors found patterns related to this dimension. Explore the findings,
then read the actual source code.

  desloppify show security --no-budget      # 459 findings
  desloppify show smells --no-budget      # 1124 findings

Report actionable issues in issues[]. Use concern_verdict and concern_fingerprint
for findings you want to confirm or dismiss.

Task requirements:
1. Read the blind packet's `system_prompt` — it contains scoring rules and calibration.
2. Start from the seed files, then freely explore the repository to build your understanding.
3. Keep issues and scoring scoped to this batch's dimension.
4. Respect scope controls: do not include files/directories marked by `exclude`, `suppress`, or non-production zone overrides.
5. Return 0-10 issues for this batch (empty array allowed).
6. For error_consistency, use evidence from `holistic_context.errors.exception_hotspots` — files with concentrated exception handling issues. Investigate whether error handling is designed or accidental. Check for broad catches masking specific failure modes.
7. Complete `dimension_judgment` for your dimension — all three fields (strengths, issue_character, score_rationale) are required. Write the judgment BEFORE setting the score.
8. Do not edit repository files.
9. Return ONLY valid JSON, no markdown fences.

Scope enums:
- impact_scope: "local" | "module" | "subsystem" | "codebase"
- fix_scope: "single_edit" | "multi_file_refactor" | "architectural_change"

Output schema:
{
  "batch": "error_consistency",
  "batch_index": 4,
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
