"""FASE 6.1: Explainable AI (XAI) - SHAP, LIME, Feature Importance."""

from .explainer import (
    FeatureImportanceCalculator,
    LIMEExplainer,
    SHAPExplainer,
    get_importance_calculator,
    get_lime_explainer,
    get_shap_explainer,
)
from .models import (
    ExplainabilityConfig,
    FeatureImportance,
    FeatureImportanceReport,
    ICEExplanation,
    InterpretationReport,
    LIMEExplanation,
    LIMEFeature,
    PartialDependence,
    PDPExplanation,
    PredictionExplanation,
    SHAPExplanation,
    SHAPSummaryPlot,
    SHAPValue,
)

__all__ = [
    "ExplainabilityConfig",
    "FeatureImportance",
    "FeatureImportanceCalculator",
    "FeatureImportanceReport",
    "ICEExplanation",
    "InterpretationReport",
    "LIMEExplainer",
    "LIMEExplanation",
    "LIMEFeature",
    "PDPExplanation",
    "PartialDependence",
    "PredictionExplanation",
    # Explainers
    "SHAPExplainer",
    "SHAPExplanation",
    "SHAPSummaryPlot",
    # Models
    "SHAPValue",
    "get_importance_calculator",
    "get_lime_explainer",
    # Singletons
    "get_shap_explainer",
]
