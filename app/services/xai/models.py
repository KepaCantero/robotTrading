"""
FASE 6.1: XAI Models - Data structures for explainability results

Defines Pydantic models for SHAP, LIME, and feature importance explanations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ============================================================================
# SHAP Explanation Models
# ============================================================================


class SHAPValue(BaseModel):
    """Individual SHAP value for a feature."""

    feature_name: str = Field(..., description="Name of the feature")
    feature_value: float = Field(..., description="Original feature value")
    shap_value: float = Field(..., description="SHAP value (contribution to prediction)")
    base_value: float = Field(..., description="Model's base prediction (average)")


class SHAPExplanation(BaseModel):
    """Complete SHAP explanation for a single prediction."""

    prediction_id: str = Field(..., description="Unique ID for this prediction")
    predicted_value: float = Field(..., description="Model's prediction")
    base_value: float = Field(..., description="Base value (model average)")
    shap_values: list[SHAPValue] = Field(..., description="List of SHAP values")
    timestamp: datetime = Field(default_factory=datetime.now)
    model_name: Optional[str] = Field(None, description="Name of the model")

    class Config:
        json_encoders: ClassVar[dict] = {datetime: lambda v: v.isoformat()}

    def get_top_features(self, n: int = 5) -> list[SHAPValue]:
        """Get top n most important features by absolute SHAP value."""
        logger.debug(
            "Getting top SHAP features",
            extra={
                "prediction_id": self.prediction_id,
                "num_features_requested": n,
                "total_features": len(self.shap_values),
            },
        )
        sorted_values = sorted(self.shap_values, key=lambda x: abs(x.shap_value), reverse=True)
        top_features = sorted_values[:n]
        logger.debug(
            "Top SHAP features retrieved",
            extra={
                "prediction_id": self.prediction_id,
                "num_features_returned": len(top_features),
                "top_feature_names": [f.feature_name for f in top_features],
            },
        )
        return top_features


class SHAPSummaryPlot(BaseModel):
    """SHAP summary statistics."""

    feature_importance: dict[str, float] = Field(
        ..., description="Average absolute SHAP values per feature"
    )
    mean_prediction: float = Field(..., description="Mean prediction value")
    std_prediction: float = Field(..., description="Std deviation of predictions")
    num_samples: int = Field(..., description="Number of samples analyzed")


# ============================================================================
# LIME Explanation Models
# ============================================================================


class LIMEFeature(BaseModel):
    """Individual feature contribution in LIME explanation."""

    feature_name: str = Field(..., description="Name of the feature")
    feature_range: Optional[str] = Field(None, description="Feature value range")
    contribution: float = Field(..., description="Contribution to prediction")
    is_positive: bool = Field(..., description="Whether contribution is positive")


class LIMEExplanation(BaseModel):
    """LIME explanation for a single prediction."""

    prediction_id: str = Field(..., description="Unique ID for this prediction")
    predicted_class: str = Field(..., description="Predicted class/value")
    predicted_probability: float = Field(..., description="Confidence score")
    explanation: list[LIMEFeature] = Field(..., description="Feature contributions")
    num_features_used: int = Field(..., description="Number of features in explanation")
    intercept: float = Field(..., description="Intercept of local linear model")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders: ClassVar[dict] = {datetime: lambda v: v.isoformat()}


# ============================================================================
# Feature Importance Models
# ============================================================================


class FeatureImportance(BaseModel):
    """Feature importance metrics."""

    feature_name: str = Field(..., description="Name of the feature")
    importance_score: float = Field(..., description="Importance score (0-1 or 0-100)")
    method: str = Field(..., description="Method used (shap, permutation, gain, cover, etc.)")
    rank: Optional[int] = Field(None, description="Ranking among all features")


class FeatureImportanceReport(BaseModel):
    """Complete feature importance report."""

    model_name: str = Field(..., description="Name of the model")
    timestamp: datetime = Field(default_factory=datetime.now)
    features: list[FeatureImportance] = Field(..., description="All features with importance")
    method: str = Field(..., description="Method used for computation")
    total_features: int = Field(..., description="Total number of features")

    class Config:
        json_encoders: ClassVar[dict] = {datetime: lambda v: v.isoformat()}

    def get_top_features(self, n: int = 10) -> list[FeatureImportance]:
        """Get top n most important features."""
        logger.debug(
            "Getting top important features",
            extra={
                "model_name": self.model_name,
                "method": self.method,
                "num_features_requested": n,
                "total_features": self.total_features,
            },
        )
        sorted_features = sorted(self.features, key=lambda x: x.importance_score, reverse=True)
        top_features = sorted_features[:n]
        logger.info(
            "Top features retrieved",
            extra={
                "model_name": self.model_name,
                "num_features_returned": len(top_features),
                "top_feature_names": [f.feature_name for f in top_features[:5]],
            },
        )
        return top_features


# ============================================================================
# Prediction Explanation Models
# ============================================================================


class PredictionExplanation(BaseModel):
    """Complete explanation for a single prediction."""

    prediction_id: str = Field(..., description="Unique prediction ID")
    prediction_value: float = Field(..., description="The prediction")
    actual_value: Optional[float] = Field(None, description="Actual value if available")
    prediction_confidence: float = Field(..., description="Confidence score (0-1)")

    # SHAP explanation
    shap_explanation: Optional[SHAPExplanation] = Field(None, description="SHAP explanation")

    # LIME explanation
    lime_explanation: Optional[LIMEExplanation] = Field(None, description="LIME explanation")

    # Feature importance
    feature_importance: Optional[list[FeatureImportance]] = Field(
        None, description="Feature importance scores"
    )

    timestamp: datetime = Field(default_factory=datetime.now)
    model_name: Optional[str] = Field(None, description="Name of the model")

    class Config:
        json_encoders: ClassVar[dict] = {datetime: lambda v: v.isoformat()}


# ============================================================================
# Model Interpretation Models
# ============================================================================


class PartialDependence(BaseModel):
    """Partial dependence of prediction on a feature."""

    feature_name: str = Field(..., description="Feature name")
    feature_values: list[float] = Field(..., description="Feature values tested")
    predictions: list[float] = Field(..., description="Corresponding predictions")


class PDPExplanation(BaseModel):
    """Partial Dependence Plot (PDP) data."""

    model_name: str = Field(..., description="Model name")
    partial_dependences: list[PartialDependence] = Field(..., description="PDP for each feature")


class ICEExplanation(BaseModel):
    """Individual Conditional Expectation (ICE) plot data."""

    model_name: str = Field(..., description="Model name")
    feature_name: str = Field(..., description="Feature name")
    sample_ids: list[str] = Field(..., description="Sample IDs")
    feature_values: list[float] = Field(..., description="Feature values")
    predictions: list[list[float]] = Field(..., description="Predictions per sample")


# ============================================================================
# Interpretation Report Models
# ============================================================================


class InterpretationReport(BaseModel):
    """Comprehensive interpretation report for a model."""

    model_name: str = Field(..., description="Model name")
    report_date: datetime = Field(default_factory=datetime.now)
    num_samples_analyzed: int = Field(..., description="Number of samples")

    # Feature importance
    feature_importance: Optional[FeatureImportanceReport] = Field(
        None, description="Overall feature importance"
    )

    # Example predictions with explanations
    sample_explanations: list[PredictionExplanation] = Field(
        default_factory=list, description="Sample predictions with explanations"
    )

    # Model insights
    insights: dict[str, Any] = Field(
        default_factory=dict, description="Key insights about model behavior"
    )

    # Recommendations
    recommendations: list[str] = Field(
        default_factory=list, description="Recommendations based on interpretation"
    )

    class Config:
        json_encoders: ClassVar[dict] = {datetime: lambda v: v.isoformat()}


@dataclass
class ExplainabilityConfig:
    """Configuration for explainability analysis."""

    # SHAP configuration
    shap_enabled: bool = True
    shap_num_samples: int = 100
    shap_method: str = "permutation"  # Or "kernel", "sampling", "tree"

    # LIME configuration
    lime_enabled: bool = True
    lime_num_samples: int = 1000
    lime_num_features: int = 10

    # Feature importance configuration
    feature_importance_enabled: bool = True
    feature_importance_method: str = "permutation"  # Or "gain", "cover", "shap"

    # PDP/ICE configuration
    pdp_enabled: bool = False
    ice_enabled: bool = False
    num_grid_points: int = 20

    # Report configuration
    num_sample_explanations: int = 5
    include_insights: bool = True
    include_recommendations: bool = True

    # Performance optimization
    parallel: bool = True
    num_workers: int = 4
    batch_size: int = 32
