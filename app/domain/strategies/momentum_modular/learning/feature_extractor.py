"""
Feature Extractor Module

Re-exports FeatureExtractor from the main learning package for backward compatibility.
"""

from app.domain.strategies.learning.feature_extractor import FeatureExtractor

__all__ = ["FeatureExtractor"]
