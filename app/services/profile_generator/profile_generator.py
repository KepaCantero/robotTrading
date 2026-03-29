"""
T2.1: ProfileGenerator - Maps user input to investment profiles

Generates complete investment profiles based on user capital, objective, and risk tolerance.
Uses configuration templates to create objective-aware parameter sets.
Integrates MAESTRO PHASE 1 for absolute return optimization and feasibility validation.
"""

import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

import yaml

from app.application.orchestration.target_optimization.absolute_return_optimizer import (
    CapacityFadeAnalyzer,
    FeasibilityValidator,
    ParameterOptimizer,
    TargetAlphaCalculator,
)
from app.application.orchestration.target_optimization.capital_tier_selector import (
    CapitalTierSelector,
)
from app.application.orchestration.target_optimization.models import AbsoluteReturnTarget

from .models import (
    CapitalTier,
    InvestmentObjective,
    InvestmentProfile,
    ModuleConfig,
    ProfileGenerationRequest,
    ProfileGenerationResult,
    RiskProfile,
)

logger = logging.getLogger(__name__)


class ProfileGenerator:
    """
    Generates investment profiles from user input.

    Features:
    - Capital tier classification (micro, small, medium, large)
    - Objective-aware module selection
    - Risk-aware parameter configuration
    - Automatic leverage and position sizing
    - Validation against constraints
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize profile generator.

        Args:
            config_path: Path to investment_profiles.yaml config file
        """
        self.generation_history: list[ProfileGenerationResult] = []
        self.profile_cache: dict[str, InvestmentProfile] = {}

        # Load profile configuration
        if config_path is None:
            config_path = (
                Path(__file__).parent.parent.parent.parent / "config" / "investment_profiles.yaml"
            )

        self.config_path = Path(config_path)
        self.profile_templates = self._load_profile_templates()

        # Initialize MAESTRO PHASE 1 components
        self.tier_selector = CapitalTierSelector()
        self.alpha_calculator = TargetAlphaCalculator()
        self.fade_analyzer = CapacityFadeAnalyzer()
        self.param_optimizer = ParameterOptimizer()
        self.feasibility_validator = FeasibilityValidator()

        logger.info("✅ ProfileGenerator initialized with MAESTRO PHASE 1 integration")

    def _load_profile_templates(self) -> dict:
        """Load investment profile templates from YAML."""
        try:
            if not self.config_path.exists():
                logger.warning(
                    f"⚠️  Config not found at {self.config_path}, using default templates"
                )
                return self._get_default_templates()

            with open(self.config_path) as f:
                templates = yaml.safe_load(f)
            logger.info(f"✅ Loaded {len(templates)} profile templates")
            return templates
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"❌ Error loading templates: {e}")
            return self._get_default_templates()

    def _get_default_templates(self) -> dict:
        """Get default profile templates."""
        return {
            "maximizar_capital": {
                "micro": {
                    "risk": "aggressive",
                    "max_leverage": 1.0,
                    "modules": ["momentum", "ml_basic"],
                    "max_position_size": 10.0,
                    "rebalance_days": 30,
                },
                "small": {
                    "risk": "aggressive",
                    "max_leverage": 1.5,
                    "modules": ["momentum", "ml_basic", "transformer"],
                    "max_position_size": 8.0,
                    "rebalance_days": 30,
                },
                "medium": {
                    "risk": "moderate",
                    "max_leverage": 2.0,
                    "modules": ["momentum", "ml_basic", "transformer", "deep_learning"],
                    "max_position_size": 5.0,
                    "rebalance_days": 14,
                },
                "large": {
                    "risk": "moderate",
                    "max_leverage": 2.5,
                    "modules": [
                        "momentum",
                        "ml_basic",
                        "transformer",
                        "deep_learning",
                        "reinforcement_learning",
                    ],
                    "max_position_size": 3.0,
                    "rebalance_days": 7,
                },
            },
            "maximizar_dividendos": {
                "micro": {
                    "risk": "conservative",
                    "max_leverage": 1.0,
                    "modules": ["dividend_tracking"],
                    "max_position_size": 10.0,
                    "rebalance_days": 60,
                },
                "small": {
                    "risk": "conservative",
                    "max_leverage": 1.2,
                    "modules": ["dividend_tracking", "ml_basic"],
                    "max_position_size": 8.0,
                    "rebalance_days": 60,
                },
                "medium": {
                    "risk": "moderate",
                    "max_leverage": 1.5,
                    "modules": ["dividend_tracking", "ml_basic", "income_optimizer"],
                    "max_position_size": 5.0,
                    "rebalance_days": 30,
                },
                "large": {
                    "risk": "moderate",
                    "max_leverage": 2.0,
                    "modules": [
                        "dividend_tracking",
                        "ml_basic",
                        "income_optimizer",
                        "tax_optimizer",
                    ],
                    "max_position_size": 3.0,
                    "rebalance_days": 30,
                },
            },
            "capital_preservation": {
                "micro": {
                    "risk": "conservative",
                    "max_leverage": 1.0,
                    "modules": ["risk_monitor"],
                    "max_position_size": 5.0,
                    "rebalance_days": 30,
                },
                "small": {
                    "risk": "conservative",
                    "max_leverage": 1.0,
                    "modules": ["risk_monitor", "stop_loss"],
                    "max_position_size": 5.0,
                    "rebalance_days": 30,
                },
                "medium": {
                    "risk": "conservative",
                    "max_leverage": 1.0,
                    "modules": ["risk_monitor", "stop_loss", "drawdown_guard"],
                    "max_position_size": 3.0,
                    "rebalance_days": 14,
                },
                "large": {
                    "risk": "conservative",
                    "max_leverage": 1.0,
                    "modules": ["risk_monitor", "stop_loss", "drawdown_guard", "portfolio_hedging"],
                    "max_position_size": 2.0,
                    "rebalance_days": 7,
                },
            },
            "balanced_growth": {
                "micro": {
                    "risk": "moderate",
                    "max_leverage": 1.0,
                    "modules": ["momentum", "risk_monitor"],
                    "max_position_size": 8.0,
                    "rebalance_days": 30,
                },
                "small": {
                    "risk": "moderate",
                    "max_leverage": 1.2,
                    "modules": ["momentum", "ml_basic", "risk_monitor"],
                    "max_position_size": 6.0,
                    "rebalance_days": 30,
                },
                "medium": {
                    "risk": "moderate",
                    "max_leverage": 1.5,
                    "modules": ["momentum", "ml_basic", "transformer", "risk_monitor"],
                    "max_position_size": 4.0,
                    "rebalance_days": 14,
                },
                "large": {
                    "risk": "moderate",
                    "max_leverage": 2.0,
                    "modules": [
                        "momentum",
                        "ml_basic",
                        "transformer",
                        "deep_learning",
                        "risk_monitor",
                    ],
                    "max_position_size": 2.0,
                    "rebalance_days": 7,
                },
            },
            "income_generation": {
                "micro": {
                    "risk": "conservative",
                    "max_leverage": 1.0,
                    "modules": ["dividend_tracking", "income_optimizer"],
                    "max_position_size": 8.0,
                    "rebalance_days": 60,
                },
                "small": {
                    "risk": "conservative",
                    "max_leverage": 1.1,
                    "modules": ["dividend_tracking", "income_optimizer", "risk_monitor"],
                    "max_position_size": 6.0,
                    "rebalance_days": 60,
                },
                "medium": {
                    "risk": "moderate",
                    "max_leverage": 1.3,
                    "modules": [
                        "dividend_tracking",
                        "income_optimizer",
                        "ml_basic",
                        "risk_monitor",
                    ],
                    "max_position_size": 4.0,
                    "rebalance_days": 30,
                },
                "large": {
                    "risk": "moderate",
                    "max_leverage": 1.5,
                    "modules": [
                        "dividend_tracking",
                        "income_optimizer",
                        "ml_basic",
                        "transformer",
                        "risk_monitor",
                    ],
                    "max_position_size": 2.0,
                    "rebalance_days": 30,
                },
            },
        }

    async def generate(
        self,
        request: ProfileGenerationRequest,
    ) -> ProfileGenerationResult:
        """
        Generate investment profile from user request.

        Args:
            request: ProfileGenerationRequest with user inputs

        Returns:
            ProfileGenerationResult with generated profile or error
        """
        start_time = datetime.utcnow()

        try:
            # Step 1: Determine capital tier using MAESTRO PHASE 1
            capital_tier_enum = self.tier_selector.detect_tier(request.capital_initial)
            # Map MAESTRO tier to local CapitalTier
            tier_map = {
                "micro": CapitalTier.MICRO,
                "small": CapitalTier.SMALL,
                "medium": CapitalTier.MEDIUM,
                "large": CapitalTier.LARGE,
            }
            capital_tier = tier_map.get(capital_tier_enum.value, CapitalTier.MICRO)

            # Step 2: Get objective template
            objective = InvestmentObjective(request.objective.value)
            risk_profile = RiskProfile(request.risk_tolerance.value)

            # Step 3: Load profile configuration
            template = self._get_profile_template(objective, capital_tier)
            if template is None:
                return ProfileGenerationResult(
                    success=False,
                    error_message=f"No template found for {objective.value} / {capital_tier.value}",
                )

            # Step 4: Create investment profile with MAESTRO PHASE 1 integration
            profile = self._create_profile_from_template(
                request, capital_tier, objective, risk_profile, template
            )

            # Step 5: Enhance profile with MAESTRO PHASE 1 analysis (absolute return optimization)
            self._integrate_maestro_phase_1(profile, request)

            # Step 6: Validate profile
            warnings = self._validate_profile(profile, request)

            # Create result
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            result = ProfileGenerationResult(
                success=True,
                profile=profile,
                warnings=warnings,
                generation_time_ms=elapsed_ms,
            )

            # Store in history and cache
            self.generation_history.append(result)
            self.profile_cache[profile.profile_id] = profile

            logger.info(
                f"✅ Generated profile {profile.profile_id} for {objective.value} "
                f"({capital_tier.value} tier, {len(profile.enabled_modules)} modules)"
            )
            return result

        except OSError as e:
            logger.error(f"❌ Error generating profile: {e}")
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return ProfileGenerationResult(
                success=False,
                error_message=str(e),
                generation_time_ms=elapsed_ms,
            )

    def _determine_capital_tier(self, capital: Decimal) -> CapitalTier:
        """Determine capital tier based on amount."""
        if capital < Decimal("25000"):
            return CapitalTier.MICRO
        elif capital < Decimal("100000"):
            return CapitalTier.SMALL
        elif capital < Decimal("500000"):
            return CapitalTier.MEDIUM
        else:
            return CapitalTier.LARGE

    def _get_profile_template(
        self, objective: InvestmentObjective, tier: CapitalTier
    ) -> Optional[dict]:
        """Get profile template for objective and tier."""
        try:
            obj_key = objective.value
            tier_key = tier.value

            # Handle both flat and nested YAML structures
            if "profiles" in self.profile_templates:
                # Nested structure with 'profiles' key
                return self.profile_templates["profiles"].get(obj_key, {}).get(tier_key)
            else:
                # Flat structure
                return self.profile_templates.get(obj_key, {}).get(tier_key)
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"❌ Error getting template: {e}")
            return None

    def _create_profile_from_template(
        self,
        request: ProfileGenerationRequest,
        tier: CapitalTier,
        objective: InvestmentObjective,
        risk_profile: RiskProfile,
        template: dict,
    ) -> InvestmentProfile:
        """Create investment profile from template."""
        # Handle None or empty template
        if not template:
            template = {}

        # Parse template values with fallbacks
        leverage_raw = template.get("max_leverage", template.get("leverage", 1.0))
        max_leverage = Decimal(str(max(leverage_raw, 1.0)))  # Ensure minimum leverage of 1.0
        modules_list = template.get("modules", template.get("enabled_modules", []))
        max_position_size = Decimal(str(template.get("max_position_size", 5.0)))
        rebalance_days = template.get("rebalance_days", 30)

        # Create module configurations
        enabled_modules = [
            ModuleConfig(
                name=module,
                enabled=True,
                priority=idx,
                cost_estimate_usd=Decimal("100"),  # Default estimate
                estimated_improvement_pct=Decimal("2.5"),  # Default estimate
            )
            for idx, module in enumerate(modules_list)
        ]

        # Adjust risk profile if conservative
        if risk_profile == RiskProfile.CONSERVATIVE:
            max_leverage = min(max_leverage, Decimal("1.0"))
            max_position_size = min(max_position_size, Decimal("5.0"))

        # Create profile
        profile = InvestmentProfile(
            input_id=request.input_id,
            capital_tier=tier,
            initial_capital=request.capital_initial,
            min_monthly_return_eur=request.target_monthly_return_eur,
            objective=objective,
            risk_profile=risk_profile,
            time_horizon_months=request.time_horizon_months,
            enabled_modules=enabled_modules,
            max_leverage=max_leverage,
            max_position_size_pct=max_position_size,
            max_daily_loss_pct=(
                Decimal("1.0") if risk_profile == RiskProfile.AGGRESSIVE else Decimal("0.5")
            ),
            rebalance_frequency_days=rebalance_days,
            risk_scaling_enabled=(tier in [CapitalTier.MEDIUM, CapitalTier.LARGE]),
            adaptive_position_sizing=True,
        )

        return profile

    def _validate_profile(
        self, profile: InvestmentProfile, request: ProfileGenerationRequest
    ) -> list[str]:
        """Validate generated profile and return warnings."""
        warnings = []

        # Check monthly return is achievable
        required_annual_pct = (
            (request.target_monthly_return_eur / request.capital_initial) * 12 * Decimal("100")
        )
        if required_annual_pct > Decimal("50"):
            warnings.append(
                f"⚠️  Target return {required_annual_pct:.1f}% annually is very aggressive for {profile.capital_tier.value} capital"
            )

        # Check module count
        if len(profile.enabled_modules) == 0:
            warnings.append("⚠️  No modules enabled - profile may not be functional")
        elif len(profile.enabled_modules) > 8:
            warnings.append(
                f"⚠️  Many modules enabled ({len(profile.enabled_modules)}) - may increase computation time"
            )

        # Check leverage appropriateness
        if (
            profile.max_leverage > Decimal("2.0")
            and profile.risk_profile == RiskProfile.CONSERVATIVE
        ):
            warnings.append("⚠️  High leverage with conservative risk profile - conflict detected")

        return warnings

    def _integrate_maestro_phase_1(
        self, profile: InvestmentProfile, request: ProfileGenerationRequest
    ) -> None:
        """
        Enhance profile with MAESTRO PHASE 1 absolute return optimization.

        Calculates:
        - required_annual_return_pct (from EUR targets)
        - required_alpha_pct (accounting for taxes and commissions)
        - capacity_fade_adjusted_alpha (estimated alpha at this capital scale)
        - position_size_pct (optimized for target)
        - concurrent_positions (diversification count)
        - feasibility_validation (from FeasibilityValidator)
        """
        try:
            # Create AbsoluteReturnTarget for MAESTRO analysis
            target = AbsoluteReturnTarget(
                target_euros_monthly=request.target_monthly_return_eur,
                capital=request.capital_initial,
                time_horizon_months=request.time_horizon_months,
                tax_rate=Decimal("0.19"),  # Standard EU tax rate
                commission_per_trade=Decimal("10"),  # EUR per trade
                expected_trades_per_month=10,  # Standard assumption
            )

            # Step 1: Calculate required annual return percentage
            annual_target = request.target_monthly_return_eur * 12
            profile.required_annual_return_pct = (
                annual_target / request.capital_initial * 100
            ).quantize(Decimal("0.01"))

            # Step 2: Calculate required alpha percentage
            profile.required_alpha_pct = self.alpha_calculator.calculate_required_alpha(target)

            # Step 3: Estimate capacity fade adjusted alpha
            # Use realistic alpha benchmarks (from PHASE 1 research)
            strategy_type_map = {
                "micro": "CONSERVATIVE",
                "small": "BALANCED",
                "medium": "BALANCED",
                "large": "AGGRESSIVE",
            }
            strategy_type = strategy_type_map.get(profile.capital_tier.value, "BALANCED")

            # Get realistic alpha range for this tier
            realistic_alpha_ranges = {
                "CONSERVATIVE": (Decimal("2"), Decimal("5")),
                "BALANCED": (Decimal("3"), Decimal("8")),
                "AGGRESSIVE": (Decimal("4"), Decimal("12")),
            }
            _min_realistic, max_realistic = realistic_alpha_ranges.get(
                strategy_type, (Decimal("3"), Decimal("8"))
            )
            profile.capacity_fade_adjusted_alpha = self.fade_analyzer.estimate_capacity_fade(
                request.capital_initial, max_realistic
            )

            # Step 4: Optimize position sizing and concurrent positions
            position_params = self.param_optimizer.optimize_position_sizing(
                capital=request.capital_initial,
                target_alpha_pct=profile.required_alpha_pct,
                expected_signal_return_pct=Decimal("2.0"),  # Standard assumption from backtests
            )
            profile.position_size_pct = position_params.get("position_size_pct")
            profile.concurrent_positions = int(position_params.get("num_concurrent_positions", 1))

            # Step 5: Validate feasibility and store validation result
            validation_result = self.feasibility_validator.validate_target(target)
            profile.feasibility_validation = {
                "is_feasible": validation_result.is_feasible,
                "confidence_level": validation_result.confidence_level,
                "recommendation": validation_result.recommendation,
                "monthly_costs": {k: str(v) for k, v in validation_result.monthly_costs.items()},
            }

            logger.info(
                "📊 MAESTRO PHASE 1 Integration Complete:\n"
                f"  Required Alpha: {profile.required_alpha_pct}%\n"
                f"  Capacity Fade Adjusted: {profile.capacity_fade_adjusted_alpha}%\n"
                f"  Position Size: {profile.position_size_pct}%\n"
                f"  Concurrent Positions: {profile.concurrent_positions}\n"
                f"  Feasibility: {validation_result.confidence_level}"
            )

        except OSError as e:
            logger.error(f"❌ Error integrating MAESTRO PHASE 1: {e}", exc_info=True)
            # Don't raise - allow profile generation to continue with partial data

    async def get_profile(self, profile_id: str) -> Optional[InvestmentProfile]:
        """Get cached profile by ID."""
        return self.profile_cache.get(profile_id)

    async def get_generation_history(
        self, limit: Optional[int] = None
    ) -> list[ProfileGenerationResult]:
        """Get profile generation history."""
        results = self.generation_history
        if limit:
            results = results[-limit:]
        return results

    def get_generator_status(self) -> dict:
        """Get generator operational status."""
        return {
            "total_profiles_generated": len(self.generation_history),
            "profiles_cached": len(self.profile_cache),
            "success_rate": sum(1 for r in self.generation_history if r.success)
            / max(1, len(self.generation_history)),
        }


# Singleton
_generator: Optional[ProfileGenerator] = None


def get_profile_generator(config_path: Optional[str] = None) -> ProfileGenerator:
    """Get or create singleton ProfileGenerator."""
    global _generator
    if _generator is None:
        _generator = ProfileGenerator()

    return _generator
