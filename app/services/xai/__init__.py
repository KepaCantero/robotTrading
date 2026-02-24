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
    # Explainers
    "SHAPExplainer",
    "LIMEExplainer",
    "FeatureImportanceCalculator",
    # Models
    "SHAPValue",
    "SHAPExplanation",
    "SHAPSummaryPlot",
    "LIMEFeature",
    "LIMEExplanation",
    "FeatureImportance",
    "FeatureImportanceReport",
    "PredictionExplanation",
    "PartialDependence",
    "PDPExplanation",
    "ICEExplanation",
    "InterpretationReport",
    "ExplainabilityConfig",
    # Singletons
    "get_shap_explainer",
    "get_lime_explainer",
    "get_importance_calculator",
]
