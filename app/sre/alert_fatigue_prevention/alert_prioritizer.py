"""
Alert Prioritizer - Prioritizes alerts based on impact and urgency.

Part of Alert Fatigue Prevention (SRE Rule 20.11).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class PriorityScore:
    """A calculated priority score for an alert."""

    score: float
    factors: Dict[str, float] = field(default_factory=dict)
    calculated_at: datetime = field(default_factory=datetime.utcnow)
    explanation: str = ""


class AlertPrioritizer:
    """
    Calculates priority scores for alerts.

    Considers multiple factors including severity, business impact,
    time sensitivity, and historical patterns.
    """

    def __init__(self):
        """Initialize the alert prioritizer."""
        self._priority_weights = {
            "severity": 0.4,
            "business_impact": 0.3,
            "time_sensitivity": 0.2,
            "historical_frequency": 0.1,
        }

    def calculate_priority(self, alert: Dict[str, Any]) -> PriorityScore:
        """Calculate priority score for an alert."""
        factors = {}

        # Severity factor
        severity_map = {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.2}
        severity = alert.get("severity", "medium").lower()
        factors["severity"] = severity_map.get(severity, 0.5)

        # Business impact factor
        business_impact = alert.get("business_impact", 0.5)
        factors["business_impact"] = float(business_impact) if business_impact else 0.5

        # Time sensitivity
        time_sensitive = alert.get("time_sensitive", False)
        factors["time_sensitivity"] = 1.0 if time_sensitive else 0.5

        # Historical frequency (lower = higher priority)
        freq = alert.get("historical_frequency", 0.5)
        factors["historical_frequency"] = 1.0 - min(float(freq), 1.0)

        # Calculate weighted score
        score = sum(factors.get(k, 0.5) * v for k, v in self._priority_weights.items())

        return PriorityScore(
            score=score,
            factors=factors,
            explanation=self._generate_explanation(factors, score),
        )

    def _generate_explanation(self, factors: Dict[str, float], score: float) -> str:
        """Generate human-readable explanation of priority score."""
        level = "high" if score > 0.7 else "medium" if score > 0.4 else "low"
        return f"Priority is {level} (score: {score:.2f}) based on severity={factors['severity']:.1f}, impact={factors['business_impact']:.1f}"

    def prioritize_batch(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize a batch of alerts, returning them sorted by priority."""
        prioritized = []
        for alert in alerts:
            priority = self.calculate_priority(alert)
            alert_copy = alert.copy()
            alert_copy["priority_score"] = priority.score
            alert_copy["priority_explanation"] = priority.explanation
            prioritized.append(alert_copy)

        return sorted(prioritized, key=lambda a: a.get("priority_score", 0), reverse=True)
