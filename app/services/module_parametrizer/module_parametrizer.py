"""
T3.1: ModuleParametrizer - Parametrizes trading modules for strategies

Applies investment profile parameters to 17+ trading modules based on:
- Capital tier (micro, small, medium, large)
- Investment objective (5 types)
- Risk profile (conservative, moderate, aggressive)

Implements capital-tier-aware gating to disable expensive/complex modules
for accounts with insufficient capital.
"""

import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .models import (
    ModuleParameterConfig,
    ModuleParameterSet,
    ParameterizationPreset,
    ParameterizationRequest,
    ParameterizationResult,
)

logger = logging.getLogger(__name__)


class ModuleParametrizer:
    """
    Parametrizes trading modules for a given investment profile.

    Features:
    - Loads module parameters from YAML configuration
    - Applies capital-tier-aware gating (minimum capital for certain modules)
    - Generates parameters for all enabled modules
    - Validates and aggregates module parameters
    - Tracks module priorities and costs
    """

    # Capital-tier minimum thresholds for expensive/complex modules
    CAPITAL_GATES = {
        "ml_ensemble": Decimal("500000"),  # Large accounts only
        "transformer_learning": Decimal("250000"),  # Medium+ accounts
        "deep_learning_engine": Decimal("100000"),  # Small+ accounts
        "reinforcement_learning": Decimal("250000"),  # Large+ accounts
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize module parametrizer.

        Args:
            config_path: Path to module_parameters.yaml config file
        """
        self.parametrization_history: List[ParameterizationResult] = []

        # Load module configuration
        if config_path is None:
            config_path = (
                Path(__file__).parent.parent.parent.parent / "config" / "module_parameters.yaml"
            )

        self.config_path = Path(config_path)
        self.module_templates = self._load_module_templates()
        logger.info("✅ ModuleParametrizer initialized")

    def _load_module_templates(self) -> Dict:
        """Load module parameter templates from YAML."""
        try:
            if not self.config_path.exists():
                logger.warning(
                    f"⚠️  Module config not found at {self.config_path}, using empty templates"
                )
                return {"modules": {}}

            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            modules_config = config.get("modules", {})
            logger.info(f"✅ Loaded parameters for {len(modules_config)} modules")
            return {"modules": modules_config}
        except Exception as e:
            logger.error(f"❌ Error loading module templates: {e}")
            return {"modules": {}}

    async def parametrize(
        self,
        request: ParameterizationRequest,
    ) -> ParameterizationResult:
        """
        Generate parameters for all enabled modules.

        Args:
            request: ParameterizationRequest with profile and module list

        Returns:
            ParameterizationResult with parameter set or error
        """
        start_time = datetime.utcnow()

        try:
            # Step 1: Apply capital-tier gating to enabled modules
            gated_modules, disabled_modules = self._apply_capital_gating(
                request.enabled_modules, request.initial_capital
            )

            # Step 2: Generate parameters for each enabled module
            module_parameters = {}
            for idx, module_name in enumerate(gated_modules):
                module_config = self._parametrize_module(
                    module_name,
                    request.capital_tier,
                    request.risk_profile,
                    idx,
                )
                if module_config:
                    module_parameters[module_name] = module_config

            # Step 3: Create parameter set
            parameter_set = self._create_parameter_set(
                request,
                module_parameters,
                disabled_modules,
            )

            # Step 4: Validate parameter set
            warnings = self._validate_parameter_set(parameter_set)

            # Create result
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            result = ParameterizationResult(
                success=True,
                parameter_set=parameter_set,
                warnings=warnings,
                disabled_modules=disabled_modules,
                parametrization_time_ms=elapsed_ms,
            )

            # Store in history
            self.parametrization_history.append(result)

            logger.info(
                f"✅ Parametrized {len(gated_modules)} modules for {request.capital_tier} tier "
                f"({len(disabled_modules)} disabled due to capital gate)"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Error parametrizing modules: {e}")
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return ParameterizationResult(
                success=False,
                error_message=str(e),
                parametrization_time_ms=elapsed_ms,
            )

    def _apply_capital_gating(
        self,
        enabled_modules: List[str],
        initial_capital: Decimal,
    ) -> tuple[List[str], List[str]]:
        """
        Filter modules based on capital tier.

        Certain modules require minimum capital to operate effectively.
        This prevents expensive/complex modules from being used on small accounts.

        Returns:
            Tuple of (gated_modules, disabled_modules)
        """
        gated_modules = []
        disabled_modules = []

        for module_name in enabled_modules:
            # Check if module has capital gate
            if module_name in self.CAPITAL_GATES:
                min_capital = self.CAPITAL_GATES[module_name]
                if initial_capital < min_capital:
                    logger.warning(
                        f"⚠️  Module '{module_name}' requires €{min_capital} minimum capital, "
                        f"but account has €{initial_capital}. Disabling module."
                    )
                    disabled_modules.append(module_name)
                    continue

            gated_modules.append(module_name)

        return gated_modules, disabled_modules

    def _parametrize_module(
        self,
        module_name: str,
        capital_tier: str,
        risk_profile: str,
        priority: int,
    ) -> Optional[ModuleParameterConfig]:
        """
        Generate parameters for a single module.

        Loads tier-specific parameters from YAML and applies risk adjustments.
        """
        try:
            modules = self.module_templates.get("modules", {})
            module_template = modules.get(module_name)

            if not module_template:
                logger.warning(f"⚠️  No template found for module '{module_name}'")
                return self._create_default_module_config(module_name, priority)

            # Get tier-specific configuration
            tier_config = module_template.get("tiers", {}).get(capital_tier, {})
            base_config = module_template.get("base", {})

            # Check if module is explicitly disabled for this tier
            if tier_config.get("enabled") is False:
                logger.warning(f"⚠️  Module '{module_name}' disabled for {capital_tier} tier")
                return None

            # Merge base and tier-specific configs
            merged_config = {**base_config, **tier_config}

            # Extract common parameters
            max_position_size = Decimal(str(merged_config.get("max_position_size", "0.10")))
            stop_loss_pct = Decimal(str(merged_config.get("stop_loss_pct", "0.03")))
            take_profit_pct = Decimal(str(merged_config.get("take_profit_pct", "0.08")))
            max_exposure = Decimal(str(merged_config.get("max_exposure", "0.25")))
            max_positions = int(merged_config.get("max_positions", 5))
            risk_adjustment = Decimal(str(merged_config.get("risk_adjustment", "1.0")))

            # Get module-specific parameters
            module_specific = merged_config.get("module_specific", {})

            # Get preset
            preset_str = merged_config.get("preset", "balanced")
            try:
                preset = ParameterizationPreset(preset_str)
            except ValueError:
                preset = ParameterizationPreset.BALANCED

            # Create config
            config = ModuleParameterConfig(
                module_name=module_name,
                enabled=True,
                priority=priority,
                max_position_size=max_position_size,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
                max_exposure=max_exposure,
                max_positions=max_positions,
                risk_adjustment=risk_adjustment,
                module_specific=module_specific,
                preset=preset,
                description=module_template.get("description", ""),
            )

            return config

        except Exception as e:
            logger.error(f"❌ Error parametrizing module '{module_name}': {e}")
            return None

    def _create_default_module_config(
        self,
        module_name: str,
        priority: int,
    ) -> ModuleParameterConfig:
        """Create default configuration for unknown modules."""
        return ModuleParameterConfig(
            module_name=module_name,
            enabled=True,
            priority=priority,
            max_position_size=Decimal("0.10"),
            stop_loss_pct=Decimal("0.03"),
            take_profit_pct=Decimal("0.08"),
            max_exposure=Decimal("0.25"),
            max_positions=5,
            risk_adjustment=Decimal("1.0"),
            module_specific={},
            preset=ParameterizationPreset.BALANCED,
            description="Default configuration (module template not found)",
        )

    def _create_parameter_set(
        self,
        request: ParameterizationRequest,
        module_parameters: Dict[str, ModuleParameterConfig],
        disabled_modules: List[str],
    ) -> ModuleParameterSet:
        """Create ModuleParameterSet from parametrized modules."""
        # Categorize modules by priority
        high_priority = [m for m, c in module_parameters.items() if c.priority <= 2]
        medium_priority = [m for m, c in module_parameters.items() if 3 <= c.priority <= 6]
        low_priority = [m for m, c in module_parameters.items() if c.priority >= 7]

        # Calculate aggregate metrics
        total_max_exposure = sum(config.max_exposure for config in module_parameters.values())
        total_cost = sum(config.cost_estimate_usd for config in module_parameters.values())
        avg_improvement = sum(
            config.estimated_improvement_pct for config in module_parameters.values()
        ) / max(1, len(module_parameters))

        parameter_set = ModuleParameterSet(
            profile_id=request.profile_id,
            input_id=request.input_id,
            module_parameters=module_parameters,
            total_modules_enabled=len(module_parameters),
            high_priority_modules=high_priority,
            medium_priority_modules=medium_priority,
            low_priority_modules=low_priority,
            capital_tier=request.capital_tier,
            objective=request.objective,
            risk_profile=request.risk_profile,
            total_max_exposure=total_max_exposure,
            total_estimated_cost_usd=total_cost,
            total_estimated_improvement_pct=avg_improvement,
        )

        return parameter_set

    def _validate_parameter_set(
        self,
        parameter_set: ModuleParameterSet,
    ) -> List[str]:
        """Validate generated parameter set and return warnings."""
        warnings = []

        # Check if any modules are enabled
        if parameter_set.total_modules_enabled == 0:
            warnings.append(
                "⚠️  No modules enabled after parametrization - profile may not be functional"
            )

        # Check total exposure (should not exceed reasonable limits)
        if parameter_set.total_max_exposure > Decimal("1.5"):
            warnings.append(
                f"⚠️  Total max exposure {parameter_set.total_max_exposure} > 1.5 - "
                "may indicate excessive portfolio exposure"
            )

        # Check if high-priority modules are disabled
        if (
            parameter_set.total_modules_enabled > 0
            and len(parameter_set.high_priority_modules) == 0
        ):
            warnings.append(
                "⚠️  No high-priority modules enabled - may affect strategy consistency"
            )

        # Check estimated cost
        if parameter_set.total_estimated_cost_usd > Decimal("1000"):
            warnings.append(
                f"⚠️  Estimated infrastructure cost ${parameter_set.total_estimated_cost_usd:.0f} "
                "- verify budget before deployment"
            )

        return warnings

    async def get_parametrization_history(
        self,
        limit: Optional[int] = None,
    ) -> List[ParameterizationResult]:
        """Get parametrization history."""
        results = self.parametrization_history
        if limit:
            results = results[-limit:]
        return results

    def get_parametrizer_status(self) -> Dict:
        """Get parametrizer operational status."""
        return {
            "total_parametrizations": len(self.parametrization_history),
            "successful_parametrizations": sum(
                1 for r in self.parametrization_history if r.success
            ),
            "success_rate": sum(1 for r in self.parametrization_history if r.success)
            / max(1, len(self.parametrization_history)),
            "total_modules_available": len(self.module_templates.get("modules", {})),
        }


# Singleton
_parametrizer: Optional[ModuleParametrizer] = None


def get_module_parametrizer(config_path: Optional[str] = None) -> ModuleParametrizer:
    """Get or create singleton ModuleParametrizer."""
    global _parametrizer
    if _parametrizer is None:

    return _parametrizer
