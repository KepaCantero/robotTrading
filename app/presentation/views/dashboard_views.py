"""
Dashboard Views - Dashboard UI components
"""

from typing import Dict, List


class DashboardViews:
    """Dashboard view components."""

    @staticmethod
    def render_portfolio_summary(portfolio_data: Dict) -> str:
        """Render portfolio summary view."""
        return f"Portfolio: {portfolio_data.get('portfolio_id', 'N/A')}"

    @staticmethod
    def render_strategy_signals(signals: List[Dict]) -> str:
        """Render strategy signals view."""
        return f"Signals: {len(signals)}"

    @staticmethod
    def render_risk_metrics(risk_data: Dict) -> str:
        """Render risk metrics view."""
        return f"VaR: {risk_data.get('var', 'N/A')}"
