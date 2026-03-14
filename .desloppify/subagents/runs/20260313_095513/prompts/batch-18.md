You are a focused subagent reviewer for a single holistic investigation batch.

Repository root: /Users/kepa.cantero/Projects/algoTrading
Blind packet: /Users/kepa.cantero/Projects/algoTrading/.desloppify/review_packet_blind.json
Batch index: 18
Batch name: contract_coherence
Batch rationale: seed files for contract_coherence review

DIMENSION TO EVALUATE:

## contract_coherence
Functions and modules that honor their stated contracts
Look for:
- Return type annotation lies: declared type doesn't match all return paths
- Docstring/signature divergence: params described in docs but not in function signature
- Functions named getX that mutate state (side effect hidden behind getter name)
- Module-level API inconsistency: some exports follow a pattern, one doesn't
- Error contracts: function says it throws but silently returns None, or vice versa
Skip:
- Protocol/interface stubs (abstract methods with placeholder returns)
- Test helpers where loose typing is intentional
- Overloaded functions with multiple valid return types

YOUR TASK: Read the code for this batch's dimension. Judge how well the codebase serves a developer from that perspective. The dimension rubric above defines what good looks like. Cite specific observations that explain your judgment.

Mechanical scan evidence — navigation aid, not scoring evidence:
The blind packet contains `holistic_context.scan_evidence` with aggregated signals from all mechanical detectors — including complexity hotspots, error hotspots, signal density index, boundary violations, and systemic patterns. Use these as starting points for where to look beyond the seed files.

Seed files (start here):
- app/presentation/api/utils.py
- scripts/utils.py
- app/services/hurst_analysis/utils.py
- app/services/alerting_system/rule_templates.py
- app/engines/strategy_engines/trend_following_engine.py
- app/domain/value_objects/symbol.py
- app/domain/entities/portfolio.py
- app/domain/value_objects/percentage.py
- app/backtesting/chan_metrics.py
- app/backtesting/constants.py
- app/presentation/api/strategies.py
- app/services/portfolio_construction_narang.py
- app/shared/config/centralized_config.py
- app/sre/error_budgets/slo_tracker.py
- app/backtesting/ensemble_methods.py
- app/backtesting/lopez_de_prado_metrics.py
- app/backtesting/profile_batch/optimization_validators.py
- app/domain/contracts.py
- app/domain/ensemble/ensemble.py
- app/domain/optimization/factory.py
- app/domain/portfolio/multi_asset/asset_class.py
- app/domain/portfolio/multi_asset/rebalancer.py
- app/domain/strategies/learning/deep_learning_engine.py
- app/domain/services/compliance/compliance_engine.py
- app/backtesting/engines/standard_engine.py
- app/backtesting/engine.py
- app/domain/market_analysis/microstructure/ofi/ofi_predictor.py
- app/domain/strategies/learning/supervised_learning_engine.py
- app/domain/market_analysis/microstructure/ofi/ofi_calculator.py
- app/domain/market_analysis/microstructure/ofi/tick_processor.py
- app/engines/strategy_engines/modular_momentum_engine.py
- app/domain/market_analysis/microstructure/ofi/ofi_signals.py
- app/domain/strategies/automated_backtest.py
- app/domain/trading/market_making/avellaneda_stoikov/inventory_manager.py
- app/domain/trading/market_making/avellaneda_stoikov/quote_generator.py
- app/domain/strategies/momentum_modular/modules/filters/__init__.py
- app/domain/market_analysis/microstructure/ofi/__init__.py
- app/domain/strategies/learning/training_data_preparator.py
- app/domain/trading/market_making/avellaneda_stoikov/__init__.py
- app/services/risk/__init__.py
- app/services/risk/validators/__init__.py
- app/domain/trading/market_making/avellaneda_stoikov/as_model.py
- app/domain/services/compliance/system_bus_extracted.py
- app/domain/services/indicators/factory.py
- app/shared/audit.py
- app/domain/services/indicators/technical_indicators.py
- app/engines/portfolio_engine/rebalancers/rebalancers.py
- app/engines/risk_engine/greeks_calculator.py
- app/domain/services/backtesting/slippage.py
- app/backtesting/validation/purged_kfold.py
- app/domain/services/analysis/momentum.py
- app/backtesting/feature_engineering/feature_importance_uniqueness.py
- app/backtesting/services/signal_processor.py
- app/shared/performance/statsmodels_fallback.py
- app/presentation/api/live_trading.py
- app/presentation/controllers/live_trading.py
- app/backtesting/validation/cross_validation_methods.py
- app/domain/services/metrics/risk_metrics.py
- app/shared/utils/decimal_utils.py
- app/domain/strategies/learning/regularization.py
- app/services/regime_detection_chan.py
- app/shared/config/profile_config_loader.py
- app/backtesting/services/configuration_service.py
- app/simulation/exchange.py
- app/backtesting/core/config_loader.py
- app/application/orchestration/target_optimization/__init__.py
- app/application/scheduling/__init__.py
- app/application/use_cases/__init__.py
- app/backtesting/__init__.py
- app/backtesting/acceptance/__init__.py
- app/backtesting/core/__init__.py
- app/backtesting/engines/__init__.py
- app/backtesting/execution/__init__.py
- app/backtesting/feature_engineering/__init__.py
- app/backtesting/labeling/__init__.py
- app/backtesting/meta_analyzer/__init__.py
- app/backtesting/profile_batch/__init__.py
- app/backtesting/robust_engine/__init__.py
- app/backtesting/runners/__init__.py
- app/backtesting/services/__init__.py

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
  "batch": "contract_coherence",
  "batch_index": 18,
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
