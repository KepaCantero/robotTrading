"""
PHASE 0 - Expensive Module Gate (T0.2.2)

Prevents initialization of computationally expensive modules on small accounts
where their cost exceeds the value they generate.

Expensive modules include:
- DeepLearningEngine: Full neural networks (GPU memory intensive)
- TransformerEngine: Sequence models with attention (very large models)
- ReinforcementLearningEngine: Environment simulation and training
- MultiTaskLearningEngine: Multiple models trained simultaneously
- Transfer Learning: Pre-trained model management and fine-tuning
- Hyperparameter Optimizer: Extensive parameter search
- Feature Importance Analysis: SHAP, permutation, correlation analysis

This gate enforces:
1. Minimum capital thresholds for different module categories
2. Disabling expensive modules on small accounts
3. Module recommendations by capital tier
4. Cost efficiency scoring
5. Graceful fallback to simpler alternatives

Economics:
Expensive modules require significant computational infrastructure (GPU/CPU time,
memory, storage) that may not be justified on accounts with low trading volume
or expected returns. Better to use simple, deterministic strategies on small
accounts and upgrade modules only when capital and trading volume increase.
"""

import logging
from decimal import Decimal
from enum import Enum
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class ExpenseLevelEnum(str, Enum):
    """Cost classification for modules"""

    CHEAP = "cheap"  # <0.1% of capital per month
    MODERATE = "moderate"  # 0.1-0.5% of capital per month
    EXPENSIVE = "expensive"  # 0.5-2% of capital per month
    VERY_EXPENSIVE = "very_expensive"  # >2% of capital per month


class ExpensiveModuleGate:
    """
    Gates expensive computational modules based on account capital and
    expected cost-benefit ratio.

    Modules are classified by computational expense:
    - DeepLearningEngine: EXPENSIVE (requires GPU/CPU, model storage)
    - TransformerEngine: VERY_EXPENSIVE (large models, attention mechanism)
    - ReinforcementLearningEngine: EXPENSIVE (environment simulation)
    - MultiTaskLearningEngine: EXPENSIVE (multiple models)
    - TransferLearning: MODERATE-EXPENSIVE (model retrieval, fine-tuning)
    - HyperparameterOptimizer: EXPENSIVE (many training iterations)
    - FeatureImportance: MODERATE (SHAP, permutation analysis)
    """

    # Module definitions with cost estimates
    MODULES = {
        "transformer_engine": {
            "expense_level": ExpenseLevelEnum.VERY_EXPENSIVE,
            "monthly_cost_pct": Decimal("0.02"),  # 2% of capital
            "min_capital": Decimal("100000"),  # Only justified for $100k+
            "description": "Transformer-based sequence models with attention mechanism",
            "benefits": "Captures complex temporal patterns in price/volume sequences",
            "fallback": "supervised_learning_engine",
        },
        "deep_learning_engine": {
            "expense_level": ExpenseLevelEnum.EXPENSIVE,
            "monthly_cost_pct": Decimal("0.01"),  # 1% of capital
            "min_capital": Decimal("50000"),  # Justified for $50k+
            "description": "Deep neural networks for non-linear relationships",
            "benefits": "Learns complex multi-layer feature interactions",
            "fallback": "supervised_learning_engine",
        },
        "reinforcement_learning_engine": {
            "expense_level": ExpenseLevelEnum.EXPENSIVE,
            "monthly_cost_pct": Decimal("0.01"),  # 1% of capital
            "min_capital": Decimal("50000"),
            "description": "Reinforcement learning with environment simulation",
            "benefits": "Learns optimal action sequences through trial-and-error",
            "fallback": "supervised_learning_engine",
        },
        "multitask_learning_engine": {
            "expense_level": ExpenseLevelEnum.EXPENSIVE,
            "monthly_cost_pct": Decimal("0.01"),  # 1% of capital
            "min_capital": Decimal("50000"),
            "description": "Multiple models trained on related tasks",
            "benefits": "Improved generalization through shared representations",
            "fallback": "supervised_learning_engine",
        },
        "transfer_learning": {
            "expense_level": ExpenseLevelEnum.MODERATE,
            "monthly_cost_pct": Decimal("0.005"),  # 0.5% of capital
            "min_capital": Decimal("25000"),
            "description": "Fine-tuning pre-trained models for specific regime",
            "benefits": "Faster training, better generalization from pre-trained weights",
            "fallback": "none",  # Can be disabled gracefully
        },
        "hyperparameter_optimizer": {
            "expense_level": ExpenseLevelEnum.EXPENSIVE,
            "monthly_cost_pct": Decimal("0.01"),  # 1% of capital
            "min_capital": Decimal("50000"),
            "description": "Extensive hyperparameter search (Bayesian optimization)",
            "benefits": "Optimal model configuration through systematic search",
            "fallback": "default_hyperparameters",
        },
        "feature_importance_analysis": {
            "expense_level": ExpenseLevelEnum.MODERATE,
            "monthly_cost_pct": Decimal("0.005"),  # 0.5% of capital
            "min_capital": Decimal("25000"),
            "description": "SHAP, permutation, and correlation-based feature analysis",
            "benefits": "Interpretability and feature engineering guidance",
            "fallback": "none",  # Can be disabled
        },
    }

    @staticmethod
    def should_enable_module(
        module_name: str,
        capital: Decimal,
        expected_monthly_alpha: Decimal = Decimal("100"),
        enforce_strict_cost_ratio: bool = False,
    ) -> Tuple[bool, Dict]:
        """
        Determine if an expensive module should be enabled for this account.

        Args:
            module_name: Name of module (e.g., "transformer_engine")
            capital: Account capital in dollars
            expected_monthly_alpha: Expected monthly alpha from strategy
            enforce_strict_cost_ratio: If True, enforce <30% cost ratio (default is min capital)

        Returns:
            (should_enable: bool, analysis: Dict)

        Dict contains:
            - enabled: bool
            - reason: str
            - recommendation: str - ENABLE | DISABLE | NOT_FOUND
            - cost_estimate_monthly: Decimal
            - cost_ratio: Decimal
            - capital_tier: str
        """

        # Validate inputs
        if capital <= Decimal("0"):
            return False, {
                "enabled": False,
                "reason": "Capital must be positive",
                "recommendation": "INCREASE_CAPITAL",
                "cost_estimate_monthly": Decimal("0"),
                "cost_ratio": Decimal("999"),
                "capital_tier": "invalid",
            }

        if module_name not in ExpensiveModuleGate.MODULES:
            return False, {
                "enabled": False,
                "reason": f"Module '{module_name}' not found in expensive modules registry",
                "recommendation": "NOT_FOUND",
                "cost_estimate_monthly": Decimal("0"),
                "cost_ratio": Decimal("0"),
                "capital_tier": ExpensiveModuleGate._get_capital_tier(capital),
            }

        # Get module definition
        module = ExpensiveModuleGate.MODULES[module_name]
        min_capital = module["min_capital"]
        cost_pct = module["monthly_cost_pct"]
        cost_monthly = capital * cost_pct

        capital_tier = ExpensiveModuleGate._get_capital_tier(capital)

        # === DECISION LOGIC ===

        if enforce_strict_cost_ratio and expected_monthly_alpha > Decimal("0"):
            # Enforce cost-benefit ratio (cost must be <30% of alpha)
            cost_ratio = cost_monthly / expected_monthly_alpha
            if cost_ratio > Decimal("0.30"):
                return False, {
                    "enabled": False,
                    "reason": (
                        f"Module cost ${cost_monthly:.2f}/mo ({cost_ratio:.0%} of alpha ${expected_monthly_alpha:.2f}/mo) "
                        "exceeds acceptable threshold (30%). Not economically justified."
                    ),
                    "recommendation": "DISABLE",
                    "cost_estimate_monthly": cost_monthly,
                    "cost_ratio": cost_ratio,
                    "capital_tier": capital_tier,
                    "module_name": module_name,
                    "fallback": module.get("fallback", "none"),
                }
        else:
            # Enforce minimum capital threshold
            if capital < min_capital:
                shortfall = min_capital - capital
                return False, {
                    "enabled": False,
                    "reason": (
                        f"Capital ${capital:,.0f} is below minimum viability threshold ${min_capital:,.0f} "
                        f"(shortfall: ${shortfall:,.0f}). {module['description']} cost (${cost_monthly:.2f}/mo) "
                        f"not economically justified. Use {module['fallback']} instead."
                    ),
                    "recommendation": "DISABLE",
                    "cost_estimate_monthly": cost_monthly,
                    "cost_ratio": (
                        (cost_monthly / expected_monthly_alpha)
                        if expected_monthly_alpha > Decimal("0")
                        else Decimal("999")
                    ),
                    "capital_tier": capital_tier,
                    "module_name": module_name,
                    "fallback": module.get("fallback", "none"),
                }

        # Module is viable
        return True, {
            "enabled": True,
            "reason": (
                f"Module '{module_name}' is enabled for ${capital:,.0f} capital ({capital_tier} tier). "
                f"Estimated cost: ${cost_monthly:.2f}/mo ({cost_pct:.2%} of capital). "
                f"Benefits: {module['benefits']}"
            ),
            "recommendation": "ENABLE",
            "cost_estimate_monthly": cost_monthly,
            "cost_ratio": (
                (cost_monthly / expected_monthly_alpha)
                if expected_monthly_alpha > Decimal("0")
                else Decimal("999")
            ),
            "capital_tier": capital_tier,
            "module_name": module_name,
            "expense_level": module["expense_level"].value,
        }

    @staticmethod
    def get_enabled_modules(
        capital: Decimal,
        expected_monthly_alpha: Decimal = Decimal("100"),
        enforce_strict_cost_ratio: bool = False,
    ) -> Tuple[Dict[str, bool], Dict[str, Dict]]:
        """
        Determine which expensive modules should be enabled for this account.

        Returns:
            (enabled_modules: Dict[module_name -> bool], analysis: Dict[module_name -> analysis])
        """
        enabled_modules = {}
        analysis = {}

        for module_name in ExpensiveModuleGate.MODULES.keys():
            should_enable, module_analysis = ExpensiveModuleGate.should_enable_module(
                module_name=module_name,
                capital=capital,
                expected_monthly_alpha=expected_monthly_alpha,
                enforce_strict_cost_ratio=enforce_strict_cost_ratio,
            )
            enabled_modules[module_name] = should_enable
            analysis[module_name] = module_analysis

        return enabled_modules, analysis

    @staticmethod
    def get_recommended_modules(capital: Decimal) -> Dict[str, bool]:
        """
        Get recommended module configuration for the given capital tier.

        Returns:
            Dict with module_name -> recommended (bool)
        """
        capital_tier = ExpensiveModuleGate._get_capital_tier(capital)

        recommendations = {
            "transformer_engine": False,
            "deep_learning_engine": False,
            "reinforcement_learning_engine": False,
            "multitask_learning_engine": False,
            "transfer_learning": False,
            "hyperparameter_optimizer": False,
            "feature_importance_analysis": False,
        }

        if capital_tier == "micro":  # < $15k
            # Disable all expensive modules
            pass
        elif capital_tier == "small":  # $15k-$50k
            # Enable only cheap modules
            recommendations["transfer_learning"] = False
            recommendations["feature_importance_analysis"] = False
        elif capital_tier == "medium":  # $50k-$250k
            # Enable moderate modules, disable very expensive
            recommendations["transfer_learning"] = True
            recommendations["feature_importance_analysis"] = True
            recommendations["hyperparameter_optimizer"] = True
            recommendations["deep_learning_engine"] = True
        elif capital_tier == "large":  # $250k+
            # Enable all modules
            for module_name in recommendations.keys():
                recommendations[module_name] = True

        return recommendations

    @staticmethod
    def _get_capital_tier(capital: Decimal) -> str:
        """Classify capital into tiers (same as LearningCapitalGate)"""
        if capital < Decimal("15000"):
            return "micro"
        elif capital < Decimal("50000"):
            return "small"
        elif capital < Decimal("250000"):
            return "medium"
        else:
            return "large"

    @staticmethod
    def get_total_expensive_module_cost(
        capital: Decimal,
        enabled_modules: Dict[str, bool],
    ) -> Decimal:
        """
        Calculate total estimated monthly cost of all enabled expensive modules.

        Args:
            capital: Account capital
            enabled_modules: Dict of module_name -> bool

        Returns:
            Total monthly cost in dollars
        """
        total_cost = Decimal("0")

        for module_name, enabled in enabled_modules.items():
            if enabled and module_name in ExpensiveModuleGate.MODULES:
                cost_pct = ExpensiveModuleGate.MODULES[module_name]["monthly_cost_pct"]
                total_cost += capital * cost_pct

        return total_cost

    @staticmethod
    def log_module_decision(
        module_name: str,
        capital: Decimal,
        analysis: Dict,
        account_id: str = None,
    ) -> str:
        """Log module enable/disable decision for audit trail"""

        status = "✅ ENABLE" if analysis["enabled"] else "❌ DISABLE"
        log_msg = (
            f"{status} | Module: {module_name} | Capital: ${capital:,.0f} ({analysis['capital_tier']}) | "
            f"Cost: ${analysis['cost_estimate_monthly']:.2f}/mo | "
            f"Recommendation: {analysis['recommendation']}"
        )

        if account_id:
            log_msg = f"[{account_id}] {log_msg}"

        if analysis["enabled"]:
            logger.info(log_msg)
        else:
            logger.warning(log_msg)

        logger.debug(f"Reason: {analysis['reason']}")

        return log_msg

    @staticmethod
    def get_cost_summary(
        capital: Decimal,
        enabled_modules: Dict[str, bool],
        expected_monthly_alpha: Decimal = Decimal("100"),
    ) -> Dict:
        """
        Get cost summary for all enabled expensive modules.

        Returns:
            Dict with total costs and ratios
        """
        total_cost = ExpensiveModuleGate.get_total_expensive_module_cost(capital, enabled_modules)

        cost_ratio = (
            total_cost / expected_monthly_alpha
            if expected_monthly_alpha > Decimal("0")
            else Decimal("999")
        )

        enabled_count = sum(1 for enabled in enabled_modules.values() if enabled)

        return {
            "total_cost_monthly": total_cost,
            "total_cost_pct_of_capital": (
                (total_cost / capital * 100) if capital > Decimal("0") else Decimal("0")
            ),
            "cost_ratio_of_alpha": cost_ratio,
            "enabled_module_count": enabled_count,
            "total_module_count": len(enabled_modules),
            "recommendation": (
                "COST_ACCEPTABLE"
                if cost_ratio < Decimal("0.50")
                else "COST_HIGH"
                if cost_ratio < Decimal("1.0")
                else "COST_CRITICAL"
            ),
        }
