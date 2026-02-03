# GAP Audit Summary Report

Generated: 2026-02-02T16:53:15Z
Repository: /Users/kepa.cantero/Projects/algoTrading

## Summary

| Metric | Count |
|--------|-------|
| Files with GAPs | 99 |
| Total GAP violations | 182 |

## Files with GAP Violations

### P0 Priority (18 violations)

- `app/application/services/input_profile_router.py.py` - **CC-006**: No explicit validation
- `app/application/services/portfolio_service_v2.py.py` - **CC-006**: Catches Exception too broadly
- `app/application/services/risk_configurator.py.py` - **CC-006**: Minimal validation
- `app/application/services/tax_optimizer.py.py` - **CC-006**: Minimal validation
- `app/application/use_cases/run_backtest_use_case.py.py` - **CC-006**: Generic Exception catch in execute_batch
- `app/backtesting/core/facade.py.py` - **CC-006**: Generic exception handling, could be more specific
- `app/backtesting/execution/backtest_config_loader.py.py` - **CC-006**: Bare except Exception in _load_config
- `app/backtesting/labeling/bet_sizing_meta.py.py` - **CC-006**: Missing ValueError in _calculate_bet_sizes
- `app/backtesting/labeling/meta_labeling.py.py` - **CC-006**: Generic ValueError without context in some places
- `app/backtesting/labeling/meta_labeling.py.py` - **TRD-001**: No validation that bet_sizes sum doesn't exceed capital
- `app/backtesting/meta_analyzer/integration.py.py` - **CC-006**: Generic exception catching
- `app/backtesting/robust_engine/models.py` - **TRD-001**: No field validators in dataclasses
- `app/core/database.py.py` - **SEC-003**: SQLite used, no TLS
- `app/market_microstructure/ofi/ofi_calculator.py.py` - **TRD-005**: mid_price checked for zero but not negative/NaN
- `app/market_microstructure/ofi/ofi_predictor.py.py` - **CC-006**: Generic Exception catching
- `app/market_microstructure/ofi/ofi_signals.py.py` - **CC-006**: Generic Exception catching
- `app/market_microstructure/ofi/tick_processor.py.py` - **TRD-005**: No price validation in OrderBookState methods
- `app/microstructure/price_discovery.py` - **CC-006**: Generic Exception catch

### P1 Priority (36 violations)

- `app/backtesting/awesome_quant_integrator.py` - **TRD-007**: Uses 252 without constant
- `app/backtesting/bias_correctors.py.py` - **LOG-004**: Error logging without exc_info=True
- `app/backtesting/core/error_handling.py.py` - **LOG-001**: Uses f-strings with emoji, not structured logging
- `app/backtesting/core/error_handling.py.py` - **LOG-004**: Line 175, 241, 319 missing exc_info=True (only 242 has it)
- `app/backtesting/core/executor.py.py` - **LOG-001**: Uses f-strings, not structured logging with context
- `app/backtesting/core/executor.py.py` - **LOG-004**: Missing exc_info=True in error log line 282
- `app/backtesting/core/executor.py.py` - **TRD-004**: No audit logging for backtest execution
- `app/backtesting/core/facade.py.py` - **LOG-004**: Missing exc_info=True in exception handlers
- `app/backtesting/core/memory_manager.py.py` - **LOG-001**: Uses emoji + f-strings, not structured logging
- `app/backtesting/core/memory_manager.py.py` - **LOG-004**: Line 214 missing exc_info=True
- `app/backtesting/core/orchestrator.py.py` - **LOG-001**: Uses basic logger, not structured logging
- `app/backtesting/data_loader.py.py` - **LOG-004**: Missing exc_info=True in some error handlers
- `app/backtesting/execution/backtest_config_loader.py.py` - **LOG-004**: Generic Exception caught without logging stack trace
- `app/backtesting/labeling/bet_sizing_meta.py.py` - **TRD-004**: No logging of bet sizing decisions
- `app/backtesting/labeling/concurrent_training.py.py` - **LOG-004**: Exception logging missing stack traces in line 268
- `app/backtesting/labeling/meta_labeling.py.py` - **LOG-004**: Error logging in _create_model missing stack traces
- `app/backtesting/models.py.py` - **LOG-004**: No logging in validators
- `app/backtesting/profile_batch/report_generator.py.py` - **LOG-001**: Uses basic logging, not structlog
- `app/core/config_loader.py.py` - **LOG-004**: Some error handlers use logger.error without exc_info
- `app/core/messaging.py.py` - **LOG-004**: Should log transport failures
- `app/core/secure_serialization.py.py` - **LOG-004**: Missing exc_info in error handlers (lines 274, 278, 342, 346, 350)
- `app/ensemble/correlation_analyzer.py.py` - **LOG-004**: Silent fallbacks, no logging
- `app/ensemble/ensemble.py.py` - **LOG-004**: No structured logging for exceptions
- `app/ensemble/pareto.py.py` - **LOG-004**: Logs generation errors without stack traces
- `app/ensemble/strategy_combiner.py.py` - **LOG-004**: Silent fallbacks, no logging
- `app/market_microstructure/ofi/ofi_predictor.py.py` - **LOG-001**: Uses f-strings instead of extra dict
- `app/market_microstructure/ofi/ofi_predictor.py.py` - **LOG-004**: Missing exc_info=True
- `app/market_microstructure/ofi/ofi_signals.py.py` - **LOG-001**: Uses f-strings instead of extra dict
- `app/market_microstructure/ofi/ofi_signals.py.py` - **LOG-004**: Missing exc_info=True
- `app/market_microstructure/ofi/tick_processor.py.py` - **LOG-001**: Line 214 uses f-string
- `app/microstructure/liquidity.py` - **SEC-007**: No validation on order_book structure
- `app/microstructure/models.py` - **SEC-007**: No validation
- `app/microstructure/order_flow.py` - **TRD-004**: No audit logging
- `app/microstructure/order_flow.py` - **SEC-007**: No column validation
- `app/microstructure/price_discovery.py` - **SEC-007**: No column validation
- `app/strategies/base.py.py` - **LOG-004**: No logging in base class (subclasses should implement)

### P2 Priority (46 violations)

- `app/backtesting/acceptance_criteria.py.py` - **ARCH-004**: validate_strategy is 184 lines
- `app/backtesting/advanced_visualizations.py` - **TYP-003**: Uses `Optional[Any]` return types
- `app/backtesting/awesome_quant_integrator.py` - **TYP-003**: Uses `Dict[str, Any]` in return
- `app/backtesting/bias_correctors.py.py` - **ARCH-004**: validate_backtest is 75 lines
- `app/backtesting/capital_scale_analyzer.py` - **TYP-001**: Some Any types
- `app/backtesting/capital_scale_analyzer.py.py` - **ARCH-004**: simulate_single_capital_level 92 lines
- `app/backtesting/chan_metrics.py.py` - **ARCH-004**: Many functions exceed 20 lines
- `app/backtesting/constants.py` - **TYP-003**: Uses `Dict[str, Any]` in COMMISSION_MODELS
- `app/backtesting/constants.py` - **ARCH-006**: dataclass not frozen
- `app/backtesting/core/error_handling.py.py` - **TYP-003**: Any used for strategy (could use Protocol for LearningEngine)
- `app/backtesting/core/executor.py.py` - **TYP-003**: StrategyType, QuotesType, SignalsType are Any (duck typing acceptable but could use Protocol)
- `app/backtesting/core/facade.py.py` - **TYP-001**: Many methods missing return type annotations (Optional, List, etc. implied but not explicit)
- `app/backtesting/core/facade.py.py` - **TYP-003**: List[Any], Dict[str, Any], Any used (strategy_factory could use Callable Protocol)
- `app/backtesting/core/facade.py.py` - **ARCH-004**: Some methods > 20 lines (run_baseline, run_strategy_test, run_parameter_sweep, _result_to_dict)
- `app/backtesting/core/memory_manager.py.py` - **TYP-003**: Dict[str, Any] used (acceptable for flexible result dicts but could specify schema)
- `app/backtesting/core/orchestrator.py.py` - **TYP-001**: Missing return types for some methods, TYPE_CHECKING used but incomplete
- `app/backtesting/core/orchestrator.py.py` - **TYP-003**: List[Any], Dict[str, Any], Any used throughout (could use Protocol for duck typing)
- `app/backtesting/core/orchestrator.py.py` - **ARCH-006**: BacktestDefaults should be frozen dataclass or use Constants
- `app/backtesting/data_loader.py.py` - **ARCH-004**: _convert_dataframe_to_quotes is 66 lines
- `app/backtesting/drift_detection/overfitting_detector.py.py` - **ARCH-004**: detect_from_results is 108 lines
- `app/backtesting/engine.py.py` - **ARCH-004**: 
- `app/backtesting/ensemble_methods.py.py` - **ARCH-004**: Many exceed
- `app/backtesting/execution/market_impact.py.py` - **ARCH-006**: dataclass not frozen
- `app/backtesting/execution/models.py.py` - **ARCH-006**: dataclass not frozen
- `app/backtesting/execution/order_fill_simulator.py.py` - **ARCH-006**: dataclass not frozen
- `app/backtesting/execution/slippage_model.py.py` - **ARCH-006**: dataclass not frozen
- `app/backtesting/execution/transaction_cost.py.py` - **ARCH-006**: dataclass not frozen
- `app/backtesting/labeling/bet_sizing_meta.py.py` - **ARCH-004**: _meta_kelly_sizing has loop that could be vectorized
- `app/backtesting/labeling/concurrent_training.py.py` - **ARCH-004**: _ensemble_predict is 58 lines
- `app/backtesting/labeling/meta_labeling_cv.py.py` - **ARCH-004**: _apply_label_purge is 47 lines
- `app/backtesting/labeling/triple_barrier.py.py` - **ARCH-004**: calculate_sample_weights_uniqueness is 90 lines
- `app/backtesting/liquidity_validator.py` - **TYP-001**: current_bar param not typed
- `app/backtesting/meta_analyzer/integration.py.py` - **TYP-001**: Missing type hints for runner parameter
- `app/backtesting/point_in_time_database.py.py` - **ARCH-006**: dataclass not frozen
- `app/backtesting/professional_reporter.py` - **TYP-003**: Uses `Dict[str, Any]` in charts and metrics
- `app/backtesting/report_generator.py` - **TYP-003**: Uses `Dict[str, Any]` in `_extract_detailed_metrics`
- `app/backtesting/report_generator.py.py` - **TYP-001**: Missing return type on _generate_executive_summary
- `app/backtesting/robust_engine/robust_backtester.py.py` - **ARCH-004**: Some methods exceed 20 lines (e.g., run_backtest ~90 lines)
- `app/backtesting/successful_configs.py` - **TYP-001**: Some Any types
- `app/backtesting/validation/walk_forward_validator_enhanced.py.py` - **ARCH-006**: Uses @dataclass without frozen=True
- `app/domain/services/portfolio_optimization/nco.py.py` - **ARCH-004**: Several methods exceed 20 lines: `_maximize_sharpe` (32 lines), `optimize` (130 lines)
- `app/ensemble/ensemble.py.py` - **ARCH-004**: Several methods exceed 20 lines (_weighted_voting, _soft_voting, _performance_weighted)
- `app/market_microstructure/ofi/models.py.py` - **ARCH-006**: dataclass mutable, BaseModel immutable
- `app/microstructure/liquidity.py` - **CC-002**: depth_slope calc duplicated in _calculate_depth_slope
- `app/microstructure/models.py` - **CC-002**: Similar to_dict() across dataclasses
- `app/microstructure/order_flow.py` - **CC-002**: _generate_recommendations similar across modules

### P3 Priority (82 violations)

- `app/api/assets.py.py` - **API-006**: No evidence of tests
- `app/api/assets.py.py` - **API-007**: No correlation IDs
- `app/api/assets.py.py` - **API-008**: No rate limiting visible
- `app/api/assets.py.py` - **API-010**: No explicit timeout configuration
- `app/api/capa2_endpoints.py.py` - **API-005**: No test evidence
- `app/api/capa2_endpoints.py.py` - **API-006**: No correlation IDs
- `app/api/capa2_endpoints.py.py` - **API-009**: No timeout configuration
- `app/api/capa2_endpoints.py.py` - **API-010**: Basic error logging only
- `app/api/cost_analysis.py.py` - **API-004**: No test evidence
- `app/api/cost_analysis.py.py` - **API-005**: No rate limiting
- `app/api/cost_analysis.py.py` - **API-006**: No audit logging
- `app/api/deployment.py.py` - **API-004**: No test evidence
- `app/api/deployment.py.py` - **API-005**: No audit logging
- `app/api/deployment.py.py` - **API-006**: No auth visible
- `app/api/market_data.py.py` - **API-004**: No test evidence
- `app/api/market_data.py.py` - **API-005**: No request logging
- `app/api/momentum.py.py` - **API-004**: No test evidence
- `app/api/momentum.py.py` - **API-009**: No request logging
- `app/api/optimization.py.py` - **API-004**: No test evidence
- `app/api/optimization.py.py` - **API-005**: No auth visible
- `app/api/optimization.py.py` - **API-009**: No audit logging
- `app/api/paper_trading.py.py` - **API-004**: No test evidence
- `app/api/paper_trading.py.py` - **API-005**: No auth visible
- `app/api/paper_trading.py.py` - **API-009**: No audit logging
- `app/api/portfolio.py.py` - **API-004**: No test evidence
- `app/api/portfolio.py.py` - **API-009**: No CB logging
- `app/api/portfolio_analytics.py.py` - **API-004**: No test evidence
- `app/api/portfolio_analytics.py.py` - **API-005**: No rate limiting
- `app/api/portfolio_analytics.py.py` - **API-009**: No request logging
- `app/api/profitability_validation.py.py` - **API-004**: No test evidence
- `app/api/signals.py.py` - **API-004**: No test evidence
- `app/api/signals.py.py` - **API-005**: No rate limiting
- `app/api/strategies.py.py` - **API-004**: No test evidence
- `app/api/strategies.py.py` - **API-005**: No auth visible
- `app/api/trading_error_handler.py.py` - **API-004**: No test evidence
- `app/api/trading_error_handler.py.py` - **API-005**: No auth visible
- `app/backtesting/acceptance_criteria.py.py` - **SOL-001**: Validates 5+ criteria in one function
- `app/backtesting/awesome_quant_integrator.py.py` - **TST-005**: No test file found
- `app/backtesting/capital_scale_analyzer.py.py` - **SOL-001**: Does backtest + metrics + ADV + commission
- `app/backtesting/config_loader.py.py` - **CFG-001**: Uses plain dict instead of Pydantic
- `app/backtesting/config_loader.py.py` - **CFG-003**: No validation on load
- `app/backtesting/config_loader.py.py` - **CFG-004**: No schema validation
- `app/backtesting/core/error_handling.py` - **ERR-007**: is_mutex_error doesn't validate exception is Exception
- `app/backtesting/core/orchestrator.py` - **ORCH-007**: No validation of data splits
- `app/backtesting/cost_calculator.py.py` - **TST-005**: No test file found
- `app/backtesting/data_loader.py` - **FMT-001**: Some lines exceed 100 chars
- `app/backtesting/data_split.py.py` - **TST-005**: No test file found
- `app/backtesting/drift_detection/drift_detectors.py.py` - **PERF-005**: MMD calculation has nested loops, could use Numba
- `app/backtesting/engine.py.py` - **SOL-001**: 
- `app/backtesting/engine.py.py` - **TST-005**: No test file found
- `app/backtesting/ensemble_methods.py.py` - **TST-005**: No test file found
- `app/backtesting/execution/backtest_config_loader.py.py` - **CFG-001**: Uses raw dict instead of Pydantic
- `app/backtesting/execution/order_fill_simulator.py.py` - **ASYNC-002**: No async calls to await
- `app/backtesting/labeling/bet_sizing_meta.py.py` - **PERF-001**: Uses explicit loops instead of vectorized operations
- `app/backtesting/labeling/concurrent_training.py.py` - **ASYNC-001**: Uses ProcessPoolExecutor instead of async/await
- `app/backtesting/profile_batch/report_generator.py.py` - **CC-007**: _get_html_template() is 147 lines (inline HTML)
- `app/backtesting/profile_batch_backtester.py.py` - **TST-004**: Tests mock ComprehensiveBacktestRunner?
- `app/backtesting/report_generator.py` - **LOG-006**: Missing timing logs
- `app/backtesting/reports/baseline_optimization_reporter.py.py` - **TST-005**: Need test coverage metrics
- `app/backtesting/robust_engine/corporate_actions.py.py` - **PERF-002**: Could use generators in load_actions_from_csv
- `app/backtesting/robust_engine/dividend_handler.py.py` - **PERF-002**: Could use generator in process_dividend_stream
- `app/backtesting/robust_engine/robust_backtester.py.py` - **QL-007**: run_backtest has 4 parameters (OK), but _process_chunk has 4 (OK)
- `app/backtesting/robust_engine/survivorship_adjuster.py.py` - **PERF-002**: Uses itertuples (good) but could use generators more
- `app/backtesting/successful_configs.py` - **LOG-005**: May log API keys in config
- `app/backtesting/walk_forward_validator_enhanced.py.py` - **PERF-006**: Not using async (sync is OK for this use case)
- `app/core/compliance_engine.py` - **SOL-001**: analysis below) - Intentional design for unified entry point
- `app/core/compliance_engine.py` - **SOL-002**: analysis below)
- `app/core/compliance_engine.py` - **ASYNC-001**: analysis below)
- `app/core/compliance_engine.py` - **DP-004**: analysis below)
- `app/core/compliance_engine.py.py` - **SOL-001**: analysis)
- `app/core/compliance_engine.py.py` - **SOL-002**: analysis)
- `app/core/compliance_engine.py.py` - **ASYNC-001**: analysis)
- `app/core/compliance_engine.py.py` - **ASYNC-005**: analysis)
- `app/core/compliance_engine.py.py` - **DP-004**: analysis)
- `app/core/messaging.py.py` - **ASYNC-005**: No timeout configuration
- `app/core/numba_accelerators.py.py` - **PERF-004**: Should benchmark
- `app/core/rate_limit_governor.py.py` - **ASYNC-004**: wait_if_needed blocks
- `app/domain/strategies/pairs_trading.py.py` - **ARCH-003**: Imports scipy, statsmodels (scientific libs OK but should be abstracted)
- `app/domain/strategies/statistical_arbitrage.py.py` - **ARCH-003**: Imports scipy, statsmodels (scientific libs OK but should be abstracted)
- `app/ensemble/ensemble.py.py` - **FMT-001**: Multiple lines exceed 100 chars (lines 175-181, 237-241)
- `app/microstructure/price_discovery.py` - **TRD-003**: No validation of normality
- `app/strategies/momentum.py.py` - **LOG-003**: Mixes DEBUG/INFO for similar diagnostics

## Summary by Priority

| Priority | Count |
|----------|-------|
| P0 (Critical) | 18 |
| P1 (High) | 36 |
| P2 (Medium) | 46 |
| P3 (Low) | 82 |

## Next Steps

1. Call @agent-tech-lead-orchestrator with this summary
2. The orchestrator will coordinate the workflow:
   - @agent-requirement-expert (if requirements missing)
   - @agent-python-expert (to implement fixes)
   - @agent-python-testing-expert (to create tests)
   - @agent-code-reviewer (to review and QA)
   - @agent-code-auditor (to audit requirements compliance)
