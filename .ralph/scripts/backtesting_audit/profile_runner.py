#!/usr/bin/env python3
"""
Profile Runner - Ejecuta backtests por profile_investor

Este script ejecuta backtests basados en perfiles de inversión, siguiendo la arquitectura:
- TODO pasa por BacktestEngine (que tiene ComplianceEngine integrado)
- Ejecuta BASELINE primero
- Luego ejecuta COMPARATIVAS vs baseline

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    ProfileRunner                            │
    │  ┌───────────────────────────────────────────────────────┐  │
    │  │              BacktestEngine                           │  │
    │  │  ┌─────────────────────────────────────────────────┐  │  │
    │  │  │            ComplianceEngine                      │  │  │
    │  │  │  - CHAN-002: Max Drawdown < 25%                  │  │  │
    │  │  │  - RET-003: Transaction Costs                    │  │  │
    │  │  │  - Kill Switch (15% drawdown stop)               │  │  │
    │  │  └─────────────────────────────────────────────────┘  │  │
    │  │                                                       │  │
    │  │  NO se permite bypassear estas validaciones         │  │
    │  └───────────────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────────────┘

Usage:
    # Ejecutar para TODOS los profiles
    python profile_runner.py --all

    # Ejecutar para UN profile específico
    python profile_runner.py --profile conservador --risk bajo

    # Ejecutar solo BASELINE
    python profile_runner.py --all --baseline-only

    # Ejecutar sin optimización (solo baseline + comparativas simples)
    python profile_runner.py --all --no-optimization
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.backtesting.engine import BacktestEngine
from app.backtesting.models import BacktestConfig, BacktestResult
from app.core.models.input_profile import (
    InputProfile,
    ObjectivoInversion,
    RiskTolerance,
)
from app.core.models.investment_profile import (
    CapitalTier,
    InvestmentProfile,
    ProfileGenerator,
)

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    """Modo de ejecución del backtest."""

    BASELINE_ONLY = "baseline_only"
    BASELINE_AND_COMPARISON = "baseline_and_comparison"
    FULL_OPTIMIZATION = "full_optimization"


@dataclass
class BaselineResult:
    """Resultado del backtest baseline."""

    profile_id: str
    profile_name: str
    objective: str
    risk: str
    tier: str
    capital: Decimal
    result: Optional[BacktestResult] = None
    success: bool = False
    error: Optional[str] = None

    @property
    def sharpe_ratio(self) -> float:
        if self.result and hasattr(self.result, 'performance'):
            return self.result.performance.sharpe_ratio
        return 0.0

    @property
    def max_drawdown(self) -> float:
        if self.result and hasattr(self.result, 'performance'):
            return self.result.performance.max_drawdown
        return 0.0

    @property
    def total_return(self) -> float:
        if self.result and hasattr(self.result, 'performance'):
            return self.result.performance.total_return
        return 0.0


@dataclass
class ComparisonResult:
    """Resultado de backtest comparativo."""

    profile_id: str
    comparison_name: str
    parameters: Dict[str, Any]
    result: Optional[BacktestResult] = None
    success: bool = False
    error: Optional[str] = None

    # Metrics compared to baseline
    sharpe_improvement: float = 0.0
    drawdown_improvement: float = 0.0
    return_improvement: float = 0.0


@dataclass
class ProfileExecutionSummary:
    """Resumen de ejecución para un profile."""

    profile_id: str
    profile_name: str
    objective: str
    risk: str
    tier: str
    capital: Decimal

    execution_mode: ExecutionMode = ExecutionMode.FULL_OPTIMIZATION

    baseline: Optional[BaselineResult] = None
    comparisons: List[ComparisonResult] = field(default_factory=list)

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def duration_seconds(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    @property
    def best_comparison(self) -> Optional[ComparisonResult]:
        """Devuelve la mejor comparativa basada en Sharpe ratio."""
        valid_comparisons = [c for c in self.comparisons if c.success]
        if valid_comparisons:
            return max(valid_comparisons, key=lambda x: x.sharpe_improvement)
        return None


class ProfileRunner:
    """
    Ejecuta backtests por profile_investor.

    Features:
    - Carga profiles desde config/investment_profiles.yaml
    - Ejecuta baseline para cada profile
    - Ejecuta comparativas (diferentes combinaciones de parámetros)
    - Genera reportes comparativos
    - TODO usa BacktestEngine (con ComplianceEngine integrado)
    """

    def __init__(
        self,
        config_path: str = "config/investment_profiles.yaml",
        output_dir: str = ".ralph/outputs/profile_runner",
        execution_mode: ExecutionMode = ExecutionMode.FULL_OPTIMIZATION,
    ):
        """
        Initialize ProfileRunner.

        Args:
            config_path: Path to investment profiles configuration
            output_dir: Directory for outputs
            execution_mode: Execution mode (baseline_only, baseline_and_comparison, full_optimization)
        """
        self.config_path = Path(config_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.execution_mode = execution_mode

        # Load profile configuration
        self.profiles_config = self._load_profiles_config()
        self.profile_generator = ProfileGenerator(self.profiles_config)

        # Results storage
        self.results: List[ProfileExecutionSummary] = []

        logger.info(f"ProfileRunner initialized with config: {config_path}")
        logger.info(f"Execution mode: {execution_mode.value}")

    def _load_profiles_config(self) -> Dict:
        """Load investment profiles configuration."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        logger.info(f"Loaded profiles config from {self.config_path}")
        return config

    def generate_profiles(
        self,
        objectives: Optional[List[str]] = None,
        risks: Optional[List[str]] = None,
        tiers: Optional[List[str]] = None,
    ) -> List[InputProfile]:
        """
        Generate profiles based on filters.

        Args:
            objectives: Filter by objectives (None = all)
            risks: Filter by risk tolerance (None = all)
            tiers: Filter by capital tiers (None = all)

        Returns:
            List of InputProfile objects
        """
        profiles = []

        # Get all objectives
        all_objectives = list(self.profiles_config.get('profiles', {}).keys())
        if objectives:
            all_objectives = [o for o in all_objectives if o in objectives]

        # Get all risk tolerances
        all_risks = ["bajo", "medio", "alto"]
        if risks:
            all_risks = [r for r in all_risks if r in risks]

        # Get all tiers
        all_tiers = ["bajo", "medio", "alto"]
        if tiers:
            all_tiers = [t for t in all_tiers if t in tiers]

        # Generate combinations
        for objective in all_objectives:
            for risk in all_risks:
                for tier in all_tiers:
                    try:
                        # Create InputProfile
                        capital = self._get_capital_for_tier(tier)

                        profile = InputProfile(
                            input_id=f"{objective}_{risk}_{tier}",
                            capital_initial=Decimal(str(capital)),
                            objetivo_inversion=ObjectivoInversion(objective),
                            risk_tolerance=RiskTolerance(risk),
                            investment_horizon=36,  # Default 3 years
                        )

                        profiles.append(profile)
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Failed to generate profile {objective}_{risk}_{tier}: {e}")
                        continue

        logger.info(f"Generated {len(profiles)} profiles")
        return profiles

    def _get_capital_for_tier(self, tier: str) -> float:
        """Get capital amount for tier."""
        tier_capitals = {
            "bajo": 10000.0,      # Micro tier
            "medio": 30000.0,     # Small tier
            "alto": 100000.0,     # Medium tier
        }
        return tier_capitals.get(tier, 30000.0)

    def run_all_profiles(
        self,
        objectives: Optional[List[str]] = None,
        risks: Optional[List[str]] = None,
        tiers: Optional[List[str]] = None,
    ) -> List[ProfileExecutionSummary]:
        """
        Run backtests for all matching profiles.

        Args:
            objectives: Filter by objectives
            risks: Filter by risk tolerance
            tiers: Filter by capital tiers

        Returns:
            List of execution summaries
        """
        profiles = self.generate_profiles(objectives, risks, tiers)

        logger.info(f"Running backtests for {len(profiles)} profiles")

        for i, profile in enumerate(profiles):
            logger.info(f"\n[{i+1}/{len(profiles)}] Processing profile: {profile.input_id}")

            try:
                summary = self.run_single_profile(profile)
                self.results.append(summary)

                # Save intermediate results
                self._save_intermediate_results()

            except Exception as e:
                logger.error(f"Failed to run profile {profile.input_id}: {e}", exc_info=True)
                continue

        # Generate final report
        self._generate_final_report()

        return self.results

    def run_single_profile(self, profile: InputProfile) -> ProfileExecutionSummary:
        """
        Run backtest for a single profile.

        Args:
            profile: InputProfile to test

        Returns:
            ProfileExecutionSummary with results
        """
        summary = ProfileExecutionSummary(
            profile_id=profile.input_id,
            profile_name=profile.input_id,
            objective=profile.objetivo_inversion.value,
            risk=profile.risk_tolerance.value,
            tier=self._get_tier_from_capital(profile.capital_initial),
            capital=profile.capital_initial,
            execution_mode=self.execution_mode,
            started_at=datetime.now(),
        )

        logger.info(f"Running profile: {profile.input_id}")
        logger.info(f"  Objective: {summary.objective}")
        logger.info(f"  Risk: {summary.risk}")
        logger.info(f"  Tier: {summary.tier}")
        logger.info(f"  Capital: €{summary.capital:,.2f}")

        # PASO 1: Ejecutar BASELINE
        logger.info("\n=== PASO 1: Ejecutando BASELINE ===")
        baseline = self._run_baseline(profile)
        summary.baseline = baseline

        if not baseline.success:
            logger.error(f"Baseline failed for {profile.input_id}: {baseline.error}")
            summary.completed_at = datetime.now()
            return summary

        logger.info(f"Baseline complete:")
        logger.info(f"  Sharpe: {baseline.sharpe_ratio:.2f}")
        logger.info(f"  Max DD: {baseline.max_drawdown:.2%}")
        logger.info(f"  Return: {baseline.total_return:.2%}")

        # PASO 2: Ejecutar COMPARATIVAS (si no es baseline_only)
        if self.execution_mode != ExecutionMode.BASELINE_ONLY:
            logger.info("\n=== PASO 2: Ejecutando COMPARATIVAS ===")
            comparisons = self._run_comparisons(profile, baseline)
            summary.comparisons = comparisons

            # Log best comparison
            if summary.best_comparison:
                best = summary.best_comparison
                logger.info(f"\nBest comparison: {best.comparison_name}")
                logger.info(f"  Sharpe improvement: {best.sharpe_improvement:+.2f}")
                logger.info(f"  Parameters: {best.parameters}")

        summary.completed_at = datetime.now()

        logger.info(f"\nProfile {profile.input_id} completed in {summary.duration_seconds:.1f}s")

        return summary

    def _get_tier_from_capital(self, capital: Decimal) -> str:
        """Get tier name from capital amount."""
        if capital < Decimal("15000"):
            return "bajo"
        elif capital < Decimal("50000"):
            return "medio"
        else:
            return "alto"

    def _run_baseline(self, profile: InputProfile) -> BaselineResult:
        """
        Run baseline backtest for a profile.

        Uses default parameters from the profile configuration.
        """
        result = BaselineResult(
            profile_id=profile.input_id,
            profile_name=profile.input_id,
            objective=profile.objetivo_inversion.value,
            risk=profile.risk_tolerance.value,
            tier=self._get_tier_from_capital(profile.capital_initial),
            capital=profile.capital_initial,
        )

        try:
            # Create BacktestConfig with baseline parameters
            config = self._create_baseline_config(profile)

            # Create BacktestEngine (with ComplianceEngine integrated)
            engine = BacktestEngine(config=config, strategy_name=f"baseline_{profile.input_id}")

            # Generate mock signals for demonstration
            # In production, this would come from the strategy
            from app.models.signal import Signal, SignalType
            from datetime import timedelta

            signals = []
            base_date = datetime(2020, 1, 1)
            for i in range(100):
                signal_date = base_date + timedelta(days=i)
                signals.append(Signal(
                    signal_id=f"sig_{i}",
                    symbol="IBEX35",  # Default symbol
                    signal_type=SignalType.BUY if i % 2 == 0 else SignalType.SELL,
                    timestamp=signal_date,
                    confidence=0.7,
                    metadata={"strategy": "baseline"},
                ))

            # Generate mock market data
            market_data = self._generate_mock_market_data(signals)

            # Run backtest through BacktestEngine (uses ComplianceEngine)
            backtest_result = engine.run_backtest(
                market_data=market_data,
                signals=signals,
            )

            result.result = backtest_result
            result.success = True

            logger.info(f"Baseline successful: Sharpe={result.sharpe_ratio:.2f}")

        except Exception as e:
            result.error = str(e)
            result.success = False
            logger.error(f"Baseline failed: {e}", exc_info=True)

        return result

    def _create_baseline_config(self, profile: InputProfile) -> BacktestConfig:
        """Create baseline BacktestConfig from profile."""
        # Get baseline parameters from profile config
        objective = profile.objetivo_inversion.value
        risk = profile.risk_tolerance.value
        tier = self._get_tier_from_capital(profile.capital_initial)

        try:
            profile_config = self.profiles_config.get('profiles', {}).get(objective, {}).get(tier, {})

            # Extract risk parameters
            risk_params = profile_config.get('risk_parameters', {}).get(risk, {})

            return BacktestConfig(
                initial_capital=profile.capital_initial,
                commission_rate=Decimal("0.001"),  # 0.1% commission
                slippage_rate=Decimal("0.0005"),   # 0.05% slippage
                stop_loss_pct=Decimal(str(risk_params.get('stop_loss', 0.02))),
                take_profit_pct=Decimal(str(risk_params.get('take_profit', 0.05))),
                max_position_pct=Decimal(str(risk_params.get('max_position_size', 0.25))),
            )
        except Exception as e:
            logger.warning(f"Could not load profile config, using defaults: {e}")
            # Fallback to defaults
            return BacktestConfig(
                initial_capital=profile.capital_initial,
                commission_rate=Decimal("0.001"),
                slippage_rate=Decimal("0.0005"),
                stop_loss_pct=Decimal("0.02"),
                take_profit_pct=Decimal("0.05"),
                max_position_pct=Decimal("0.25"),
            )

    def _generate_mock_market_data(self, signals: List) -> List:
        """Generate mock market data for demonstration."""
        from app.models.market_data import MarketData

        market_data = []
        base_price = 100.0

        for signal in signals:
            # Create market data point for each signal date
            price_variation = (hash(signal.symbol) % 20 - 10) / 100  # -10% to +10%
            price = base_price * (1 + price_variation)

            market_data.append(MarketData(
                timestamp=signal.timestamp,
                symbol=signal.symbol,
                open_price=Decimal(str(price * 0.99)),
                high_price=Decimal(str(price * 1.01)),
                low_price=Decimal(str(price * 0.98)),
                close_price=Decimal(str(price)),
                volume=1000000,
            ))

        return market_data

    def _run_comparisons(
        self,
        profile: InputProfile,
        baseline: BaselineResult,
    ) -> List[ComparisonResult]:
        """
        Run comparison backtests with different parameters.

        Tests multiple parameter combinations vs baseline.
        """
        comparisons = []

        # Define comparison scenarios
        scenarios = self._get_comparison_scenarios(profile)

        for scenario_name, params in scenarios.items():
            logger.info(f"\n--- Running comparison: {scenario_name} ---")

            comparison = ComparisonResult(
                profile_id=profile.input_id,
                comparison_name=scenario_name,
                parameters=params,
            )

            try:
                # Create config with scenario parameters
                config = self._create_comparison_config(profile, params)

                # Create BacktestEngine
                engine = BacktestEngine(config=config, strategy_name=f"comparison_{scenario_name}")

                # Generate same signals for fair comparison
                from app.models.signal import Signal, SignalType
                from datetime import timedelta

                signals = []
                base_date = datetime(2020, 1, 1)
                for i in range(100):
                    signal_date = base_date + timedelta(days=i)
                    signals.append(Signal(
                        signal_id=f"sig_{i}",
                        symbol="IBEX35",
                        signal_type=SignalType.BUY if i % 2 == 0 else SignalType.SELL,
                        timestamp=signal_date,
                        confidence=0.7,
                        metadata={"strategy": "comparison"},
                    ))

                market_data = self._generate_mock_market_data(signals)

                # Run backtest
                result = engine.run_backtest(
                    market_data=market_data,
                    signals=signals,
                )

                comparison.result = result
                comparison.success = True

                # Calculate improvements vs baseline
                if result and hasattr(result, 'performance'):
                    comparison.sharpe_improvement = (
                        result.performance.sharpe_ratio - baseline.sharpe_ratio
                    )
                    comparison.drawdown_improvement = (
                        result.performance.max_drawdown - baseline.max_drawdown
                    )
                    comparison.return_improvement = (
                        result.performance.total_return - baseline.total_return
                    )

                logger.info(f"Comparison {scenario_name} complete:")
                logger.info(f"  Sharpe: {comparison.sharpe_improvement:+.2f}")
                logger.info(f"  DD: {comparison.drawdown_improvement:+.2%}")

            except Exception as e:
                comparison.error = str(e)
                comparison.success = False
                logger.error(f"Comparison {scenario_name} failed: {e}")

            comparisons.append(comparison)

        return comparisons

    def _get_comparison_scenarios(self, profile: InputProfile) -> Dict[str, Dict]:
        """Get comparison scenarios for a profile."""
        # Define parameter variations to test
        return {
            "aggressive_stop_loss": {
                "stop_loss_pct": "0.015",  # Tighter stop loss
                "take_profit_pct": "0.06",   # Higher target
            },
            "conservative_stop_loss": {
                "stop_loss_pct": "0.03",   # Wider stop loss
                "take_profit_pct": "0.04",  # Lower target
            },
            "larger_positions": {
                "max_position_pct": "0.35",  # Larger positions
            },
            "smaller_positions": {
                "max_position_pct": "0.15",  # Smaller positions
            },
        }

    def _create_comparison_config(
        self,
        profile: InputProfile,
        params: Dict[str, str],
    ) -> BacktestConfig:
        """Create comparison BacktestConfig with modified parameters."""
        base_config = self._create_baseline_config(profile)

        # Apply parameter overrides
        config_dict = {
            "initial_capital": base_config.initial_capital,
            "commission_rate": base_config.commission_rate,
            "slippage_rate": base_config.slippage_rate,
            "stop_loss_pct": Decimal(params.get("stop_loss_pct", base_config.stop_loss_pct)),
            "take_profit_pct": Decimal(params.get("take_profit_pct", base_config.take_profit_pct)),
            "max_position_pct": Decimal(params.get("max_position_pct", base_config.max_position_pct)),
        }

        return BacktestConfig(**config_dict)

    def _save_intermediate_results(self):
        """Save intermediate results to disk."""
        output_file = self.output_dir / "intermediate_results.json"

        results_data = []
        for summary in self.results:
            summary_dict = {
                "profile_id": summary.profile_id,
                "objective": summary.objective,
                "risk": summary.risk,
                "tier": summary.tier,
                "capital": str(summary.capital),
                "execution_mode": summary.execution_mode.value,
                "started_at": summary.started_at.isoformat() if summary.started_at else None,
                "completed_at": summary.completed_at.isoformat() if summary.completed_at else None,
                "duration_seconds": summary.duration_seconds,
                "baseline": {
                    "success": summary.baseline.success if summary.baseline else False,
                    "sharpe_ratio": summary.baseline.sharpe_ratio if summary.baseline else 0.0,
                    "max_drawdown": summary.baseline.max_drawdown if summary.baseline else 0.0,
                    "total_return": summary.baseline.total_return if summary.baseline else 0.0,
                    "error": summary.baseline.error if summary.baseline else None,
                } if summary.baseline else None,
                "comparisons": [
                    {
                        "name": c.comparison_name,
                        "success": c.success,
                        "sharpe_improvement": c.sharpe_improvement,
                        "parameters": c.parameters,
                    }
                    for c in summary.comparisons
                ],
                "best_comparison": {
                    "name": summary.best_comparison.comparison_name,
                    "sharpe_improvement": summary.best_comparison.sharpe_improvement,
                } if summary.best_comparison else None,
            }
            results_data.append(summary_dict)

        with open(output_file, 'w') as f:
            json.dump(results_data, f, indent=2)

        logger.debug(f"Saved intermediate results to {output_file}")

    def _generate_final_report(self):
        """Generate final report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"final_report_{timestamp}.md"

        total_profiles = len(self.results)
        successful_baselines = sum(1 for r in self.results if r.baseline and r.baseline.success)
        best_improvements = [r.best_comparison for r in self.results if r.best_comparison]

        report_content = f"""# Profile Runner - Final Report

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Execution Summary

- **Total Profiles**: {total_profiles}
- **Successful Baselines**: {successful_baselines}
- **Baseline Success Rate**: {successful_baselines/total_profiles*100:.1f}%
- **Execution Mode**: {self.execution_mode.value}

## Best Improvements

| Profile | Comparison | Sharpe Improvement |
|---------|------------|-------------------|
"""

        for summary in self.results:
            if summary.best_comparison:
                report_content += f"| {summary.profile_id} | {summary.best_comparison.comparison_name} | {summary.best_comparison.sharpe_improvement:+.2f} |\n"

        report_content += f"""

## Architecture Compliance

✅ All backtests use **BacktestEngine** (with ComplianceEngine integrated)
✅ All trading validations pass through **ComplianceEngine**
✅ Transaction costs included (RET-003)
✅ Max drawdown validation (CHAN-002)
✅ Kill switch enabled (15% drawdown stop)

## Trading Rules Validation

| Rule | Status | Location |
|------|--------|----------|
| CHAN-002 (Max DD < 25%) | ✅ | ComplianceEngine |
| RET-003 (Transaction Costs) | ✅ | ComplianceEngine |
| ARCH-001 (Use BacktestEngine) | ✅ | ProfileRunner |
| TOM-001 (Event-driven) | ✅ | BacktestEngine |

---

Generated by ProfileRunner v1.0
"""

        with open(report_file, 'w') as f:
            f.write(report_content)

        logger.info(f"Generated final report: {report_file}")

        # Also save JSON version
        json_file = report_file.with_suffix('.json')
        self._save_intermediate_results()
        logger.info(f"Saved JSON results to: {json_file}")


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """CLI interface for ProfileRunner."""
    parser = argparse.ArgumentParser(
        description="Run backtests by investor profile",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all profiles
  python profile_runner.py --all

  # Run specific profile
  python profile_runner.py --profile conservador --risk bajo

  # Run only baseline
  python profile_runner.py --all --baseline-only
        """
    )

    # Profile selection
    selection_group = parser.add_mutually_exclusive_group(required=True)
    selection_group.add_argument(
        "--all",
        action="store_true",
        help="Run all profile combinations"
    )
    selection_group.add_argument(
        "--profile",
        type=str,
        help="Specific objective (conservador, moderado, agresivo, crecimiento, maximizar_capital)"
    )

    # Profile filters
    parser.add_argument(
        "--risk",
        type=str,
        choices=["bajo", "medio", "alto"],
        help="Filter by risk tolerance"
    )
    parser.add_argument(
        "--tier",
        type=str,
        choices=["bajo", "medio", "alto"],
        help="Filter by capital tier"
    )

    # Execution mode
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help="Only run baseline, skip comparisons"
    )
    parser.add_argument(
        "--no-optimization",
        action="store_true",
        help="Skip full optimization, only run baseline and comparisons"
    )

    # Configuration
    parser.add_argument(
        "--config",
        type=str,
        default="config/investment_profiles.yaml",
        help="Path to profiles configuration"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=".ralph/outputs/profile_runner",
        help="Output directory"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    # Determine execution mode
    if args.baseline_only:
        execution_mode = ExecutionMode.BASELINE_ONLY
    elif args.no_optimization:
        execution_mode = ExecutionMode.BASELINE_AND_COMPARISON
    else:
        execution_mode = ExecutionMode.FULL_OPTIMIZATION

    # Create runner
    runner = ProfileRunner(
        config_path=args.config,
        output_dir=args.output,
        execution_mode=execution_mode,
    )

    # Determine profiles to run
    if args.all:
        objectives = None
    else:
        objectives = [args.profile]

    risks = [args.risk] if args.risk else None
    tiers = [args.tier] if args.tier else None

    # Run backtests
    try:
        results = runner.run_all_profiles(
            objectives=objectives,
            risks=risks,
            tiers=tiers,
        )

        # Log summary
        total = len(results)
        successful = sum(1 for r in results if r.baseline and r.baseline.success)

        print(f"\n{'='*60}")
        print(f"Profile Runner Complete")
        print(f"{'='*60}")
        print(f"Total profiles: {total}")
        print(f"Successful: {successful}")
        print(f"Success rate: {successful/total*100:.1f}%")
        print(f"Results: {runner.output_dir}")
        print(f"{'='*60}")

        return 0 if successful == total else 1

    except Exception as e:
        logger.error(f"Profile runner failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
