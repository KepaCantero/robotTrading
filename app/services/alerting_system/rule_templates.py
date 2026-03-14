"""
T18.2: Advanced Alerting System - Rule Templates

Pre-configured alert rule templates for common monitoring scenarios.
These templates provide sensible defaults for:
- Portfolio risk thresholds
- Execution quality metrics
- System performance
- Market regime alerts
"""

import logging
from decimal import Decimal
from typing import List

from app.services.alerting_system.models import (
    AlertRule,
    AlertSeverity,
    ChangeRule,
    ComparisonOperator,
    LogicOperator,
    ThresholdRule,
)

logger = logging.getLogger(__name__)


class AlertRuleTemplates:
    """Factory for creating pre-configured alert rules."""

    # ==================== Portfolio Risk Alerts ====================

    @staticmethod
    def portfolio_drawdown_warning() -> AlertRule:
        """Alert when portfolio drawdown exceeds 5% (WARNING level)."""
        return AlertRule(
            rule_id="portfolio_drawdown_warning",
            name="Portfolio Drawdown Warning",
            description="Alert when portfolio drawdown exceeds 5%",
            severity=AlertSeverity.WARNING,
            enabled=True,
            threshold_rules=[
                ThresholdRule(
                    metric_name="PORTFOLIO_DRAWDOWN",
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=Decimal("5.0"),
                )
            ],
            logic_operator=LogicOperator.OR,
            deduplicate_minutes=10,
            tags={
                "category": "portfolio_risk",
                "threshold": "5%",
                "severity_level": "warning",
            },
        )

    @staticmethod
    def portfolio_drawdown_critical() -> AlertRule:
        """Alert when portfolio drawdown exceeds 10% (CRITICAL level)."""
        return AlertRule(
            rule_id="portfolio_drawdown_critical",
            name="Portfolio Drawdown Critical",
            description="Alert when portfolio drawdown exceeds 10%",
            severity=AlertSeverity.CRITICAL,
            enabled=True,
            threshold_rules=[
                ThresholdRule(
                    metric_name="PORTFOLIO_DRAWDOWN",
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=Decimal("10.0"),
                )
            ],
            logic_operator=LogicOperator.OR,
            deduplicate_minutes=5,
            tags={
                "category": "portfolio_risk",
                "threshold": "10%",
                "severity_level": "critical",
            },
        )

    @staticmethod
    def portfolio_drawdown_halt() -> AlertRule:
        """Alert when portfolio drawdown exceeds 15% (circuit breaker)."""
        return AlertRule(
            rule_id="portfolio_drawdown_halt",
            name="Portfolio Drawdown Circuit Breaker",
            description="Alert when portfolio drawdown exceeds 15% (halt trading)",
            severity=AlertSeverity.CRITICAL,
            enabled=True,
            threshold_rules=[
                ThresholdRule(
                    metric_name="PORTFOLIO_DRAWDOWN",
                    operator=ComparisonOperator.GREATER_THAN_OR_EQUAL,
                    threshold=Decimal("15.0"),
                )
            ],
            logic_operator=LogicOperator.OR,
            deduplicate_minutes=1,
            tags={
                "category": "portfolio_risk",
                "threshold": "15%",
                "severity_level": "critical",
                "action": "halt_trading",
            },
        )

    # ==================== Volatility Alerts ====================

    @staticmethod
    def volatility_spike() -> AlertRule:
        """Alert when portfolio volatility exceeds 150% of baseline."""
        return AlertRule(
            rule_id="volatility_spike",
            name="Volatility Spike Alert",
            description="Alert when portfolio volatility exceeds 150% of baseline",
            severity=AlertSeverity.WARNING,
            enabled=True,
            threshold_rules=[
                ThresholdRule(
                    metric_name="PORTFOLIO_VOLATILITY",
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=Decimal("150.0"),  # 150% of baseline
                )
            ],
            logic_operator=LogicOperator.OR,
            deduplicate_minutes=15,
            tags={
                "category": "market_conditions",
                "threshold": "150% baseline",
                "severity_level": "warning",
            },
        )

    # ==================== Cost & Execution Alerts ====================

    @staticmethod
    def cost_overrun_warning() -> AlertRule:
        """Alert when execution cost overruns exceed 5% of budget."""
        return AlertRule(
            rule_id="cost_overrun_warning",
            name="Cost Overrun Warning",
            description="Alert when execution cost overruns exceed 5% of budget",
            severity=AlertSeverity.WARNING,
            enabled=True,
            threshold_rules=[
                ThresholdRule(
                    metric_name="ORDER_COST",
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=Decimal("5.0"),  # 5% overrun
                )
            ],
            logic_operator=LogicOperator.OR,
            deduplicate_minutes=10,
            tags={
                "category": "execution_quality",
                "threshold": "5% overrun",
                "severity_level": "warning",
            },
        )

    @staticmethod
    def cost_overrun_critical() -> AlertRule:
        """Alert when execution cost overruns exceed 10% of budget."""
        return AlertRule(
            rule_id="cost_overrun_critical",
            name="Cost Overrun Critical",
            description="Alert when execution cost overruns exceed 10% of budget",
            severity=AlertSeverity.CRITICAL,
            enabled=True,
            threshold_rules=[
                ThresholdRule(
                    metric_name="ORDER_COST",
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=Decimal("10.0"),  # 10% overrun
                )
            ],
            logic_operator=LogicOperator.OR,
            deduplicate_minutes=5,
            tags={
                "category": "execution_quality",
                "threshold": "10% overrun",
                "severity_level": "critical",
            },
        )

    @staticmethod
    def fill_ratio_low() -> AlertRule:
        """Alert when execution fill ratio drops below 95%."""
        return AlertRule(
            rule_id="fill_ratio_low",
            name="Fill Ratio Low",
            description="Alert when execution fill ratio drops below 95%",
            severity=AlertSeverity.WARNING,
            enabled=True,
            threshold_rules=[
                ThresholdRule(
                    metric_name="FILL_RATIO",
                    operator=ComparisonOperator.LESS_THAN,
                    threshold=Decimal("95.0"),  # 95% threshold
                )
            ],
            logic_operator=LogicOperator.OR,
            deduplicate_minutes=15,
            tags={
                "category": "execution_quality",
                "threshold": "<95%",
                "severity_level": "warning",
            },
        )

    # ==================== Performance Alerts ====================

    @staticmethod
    def sharpe_ratio_deterioration() -> AlertRule:
        """Alert when Sharpe ratio declines by >20% in 1 hour."""
        return AlertRule(
            rule_id="sharpe_ratio_deterioration",
            name="Sharpe Ratio Deterioration",
            description="Alert when Sharpe ratio declines by >20% in 1 hour",
            severity=AlertSeverity.WARNING,
            enabled=True,
            change_rules=[
                ChangeRule(
                    metric_name="PORTFOLIO_SHARPE",
                    change_percent=Decimal("-20.0"),  # 20% decline
                    window_minutes=60,  # 1 hour window
                    direction="down",
                )
            ],
            logic_operator=LogicOperator.OR,
            deduplicate_minutes=30,
            tags={
                "category": "performance",
                "threshold": "-20% in 1h",
                "severity_level": "warning",
            },
        )

    # ==================== Loss & Drawdown Alerts ====================

    @staticmethod
    def consecutive_losses_warning() -> AlertRule:
        """Alert after 2 consecutive losing trades."""
        return AlertRule(
            rule_id="consecutive_losses_warning",
            name="Consecutive Losses Warning",
            description="Alert after 2 consecutive losing trades",
            severity=AlertSeverity.WARNING,
            enabled=True,
            threshold_rules=[
                ThresholdRule(
                    metric_name="POSITION_PNL",
                    operator=ComparisonOperator.LESS_THAN,
                    threshold=Decimal("0.0"),
                )
            ],
            logic_operator=LogicOperator.OR,
            deduplicate_minutes=20,
            tags={
                "category": "trading_quality",
                "threshold": "2 consecutive losses",
                "severity_level": "warning",
            },
        )

    @staticmethod
    def consecutive_losses_critical() -> AlertRule:
        """Alert after 4 consecutive losing trades."""
        return AlertRule(
            rule_id="consecutive_losses_critical",
            name="Consecutive Losses Critical",
            description="Alert after 4 consecutive losing trades (reduce position)",
            severity=AlertSeverity.CRITICAL,
            enabled=True,
            threshold_rules=[
                ThresholdRule(
                    metric_name="POSITION_PNL",
                    operator=ComparisonOperator.LESS_THAN,
                    threshold=Decimal("0.0"),
                )
            ],
            logic_operator=LogicOperator.OR,
            deduplicate_minutes=10,
            tags={
                "category": "trading_quality",
                "threshold": "4 consecutive losses",
                "severity_level": "critical",
                "action": "reduce_position",
            },
        )

    # ==================== System Health Alerts ====================

    @staticmethod
    def latency_spike() -> AlertRule:
        """Alert when system latency exceeds 1000ms."""
        return AlertRule(
            rule_id="latency_spike",
            name="System Latency Spike",
            description="Alert when system latency exceeds 1000ms",
            severity=AlertSeverity.WARNING,
            enabled=True,
            threshold_rules=[
                ThresholdRule(
                    metric_name="LATENCY_MS",
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=Decimal("1000.0"),  # 1 second
                )
            ],
            logic_operator=LogicOperator.OR,
            deduplicate_minutes=15,
            tags={
                "category": "system_health",
                "threshold": ">1000ms",
                "severity_level": "warning",
            },
        )

    @staticmethod
    def error_rate_high() -> AlertRule:
        """Alert when system error rate exceeds 5%."""
        return AlertRule(
            rule_id="error_rate_high",
            name="System Error Rate High",
            description="Alert when system error rate exceeds 5%",
            severity=AlertSeverity.CRITICAL,
            enabled=True,
            threshold_rules=[
                ThresholdRule(
                    metric_name="ERROR_RATE",
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=Decimal("5.0"),  # 5% error rate
                )
            ],
            logic_operator=LogicOperator.OR,
            deduplicate_minutes=5,
            tags={
                "category": "system_health",
                "threshold": ">5%",
                "severity_level": "critical",
            },
        )

    # ==================== Utility Methods ====================

    @staticmethod
    def get_all_default_templates() -> List[AlertRule]:
        """Return all default alert rule templates."""
        logger.debug("Loading all default alert rule templates")

        templates = [
            # Portfolio Risk (3 rules)
            AlertRuleTemplates.portfolio_drawdown_warning(),
            AlertRuleTemplates.portfolio_drawdown_critical(),
            AlertRuleTemplates.portfolio_drawdown_halt(),
            # Volatility (1 rule)
            AlertRuleTemplates.volatility_spike(),
            # Cost & Execution (3 rules)
            AlertRuleTemplates.cost_overrun_warning(),
            AlertRuleTemplates.cost_overrun_critical(),
            AlertRuleTemplates.fill_ratio_low(),
            # Performance (1 rule)
            AlertRuleTemplates.sharpe_ratio_deterioration(),
            # Trading Quality (2 rules)
            AlertRuleTemplates.consecutive_losses_warning(),
            AlertRuleTemplates.consecutive_losses_critical(),
            # System Health (2 rules)
            AlertRuleTemplates.latency_spike(),
            AlertRuleTemplates.error_rate_high(),
        ]

        logger.info(
            "Default alert templates loaded",
            extra={
                "total_templates": len(templates),
                "categories": [
                    "portfolio_risk",
                    "market_conditions",
                    "execution_quality",
                    "performance",
                    "trading_quality",
                    "system_health",
                ],
            },
        )

        return templates

    @staticmethod
    def get_template_by_id(rule_id: str) -> AlertRule:
        """Get a specific template by rule ID."""
        logger.debug("Looking up alert template by ID", extra={"rule_id": rule_id})

        templates = {
            # Portfolio Risk
            "portfolio_drawdown_warning": AlertRuleTemplates.portfolio_drawdown_warning(),
            "portfolio_drawdown_critical": AlertRuleTemplates.portfolio_drawdown_critical(),
            "portfolio_drawdown_halt": AlertRuleTemplates.portfolio_drawdown_halt(),
            # Volatility
            "volatility_spike": AlertRuleTemplates.volatility_spike(),
            # Cost & Execution
            "cost_overrun_warning": AlertRuleTemplates.cost_overrun_warning(),
            "cost_overrun_critical": AlertRuleTemplates.cost_overrun_critical(),
            "fill_ratio_low": AlertRuleTemplates.fill_ratio_low(),
            # Performance
            "sharpe_ratio_deterioration": AlertRuleTemplates.sharpe_ratio_deterioration(),
            # Trading Quality
            "consecutive_losses_warning": AlertRuleTemplates.consecutive_losses_warning(),
            "consecutive_losses_critical": AlertRuleTemplates.consecutive_losses_critical(),
            # System Health
            "latency_spike": AlertRuleTemplates.latency_spike(),
            "error_rate_high": AlertRuleTemplates.error_rate_high(),
        }
        if rule_id not in templates:
            logger.error(
                "Alert template not found",
                extra={
                    "rule_id": rule_id,
                    "available_templates": list(templates.keys()),
                },
            )
            raise ValueError(f"Unknown rule template ID: {rule_id}")

        logger.info(
            "Alert template retrieved",
            extra={
                "rule_id": rule_id,
                "rule_name": templates[rule_id].name,
                "severity": templates[rule_id].severity.value,
            },
        )
        return templates[rule_id]

    @staticmethod
    def get_templates_by_category(category: str) -> List[AlertRule]:
        """Get all templates for a specific category."""
        logger.debug("Fetching templates by category", extra={"category": category})

        all_templates = AlertRuleTemplates.get_all_default_templates()
        filtered = [t for t in all_templates if t.tags.get("category") == category]

        logger.info(
            "Templates filtered by category",
            extra={
                "category": category,
                "templates_found": len(filtered),
            },
        )
        return filtered

    @staticmethod
    def get_critical_templates() -> List[AlertRule]:
        """Get all CRITICAL severity templates."""
        logger.debug("Fetching all CRITICAL severity templates")

        all_templates = AlertRuleTemplates.get_all_default_templates()
        critical = [t for t in all_templates if t.severity == AlertSeverity.CRITICAL]

        logger.info(
            "Critical templates retrieved",
            extra={
                "critical_count": len(critical),
                "rule_ids": [t.rule_id for t in critical],
            },
        )
        return critical
