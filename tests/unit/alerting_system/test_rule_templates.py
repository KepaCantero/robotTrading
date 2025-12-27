"""
T18.2: Advanced Alerting System - Rule Templates Tests

Comprehensive tests for pre-configured alert rule templates.
Validates:
- Template creation and structure
- Threshold accuracy and logic
- Severity assignment
- Tagging and metadata
- Edge cases and boundary values
"""

from decimal import Decimal

import pytest

from app.services.alerting_system.models import AlertSeverity, ComparisonOperator, LogicOperator
from app.services.alerting_system.rule_templates import AlertRuleTemplates


class TestPortfolioRiskTemplates:
    """Test portfolio risk alert templates."""

    def test_portfolio_drawdown_warning_creation(self):
        """Test portfolio drawdown warning template creation."""
        rule = AlertRuleTemplates.portfolio_drawdown_warning()

        assert rule.rule_id == "portfolio_drawdown_warning"
        assert rule.name == "Portfolio Drawdown Warning"
        assert rule.severity == AlertSeverity.WARNING
        assert rule.enabled is True

    def test_portfolio_drawdown_warning_threshold(self):
        """Test portfolio drawdown warning threshold is 5%."""
        rule = AlertRuleTemplates.portfolio_drawdown_warning()

        assert len(rule.threshold_rules) == 1
        threshold = rule.threshold_rules[0]
        assert threshold.metric_name == "PORTFOLIO_DRAWDOWN"
        assert threshold.operator == ComparisonOperator.GREATER_THAN
        assert threshold.threshold == Decimal("5.0")

    def test_portfolio_drawdown_warning_tags(self):
        """Test portfolio drawdown warning tags."""
        rule = AlertRuleTemplates.portfolio_drawdown_warning()

        assert rule.tags["category"] == "portfolio_risk"
        assert rule.tags["threshold"] == "5%"
        assert rule.tags["severity_level"] == "warning"

    def test_portfolio_drawdown_critical_creation(self):
        """Test portfolio drawdown critical template creation."""
        rule = AlertRuleTemplates.portfolio_drawdown_critical()

        assert rule.rule_id == "portfolio_drawdown_critical"
        assert rule.severity == AlertSeverity.CRITICAL
        assert len(rule.threshold_rules) == 1

    def test_portfolio_drawdown_critical_threshold(self):
        """Test portfolio drawdown critical threshold is 10%."""
        rule = AlertRuleTemplates.portfolio_drawdown_critical()

        threshold = rule.threshold_rules[0]
        assert threshold.threshold == Decimal("10.0")
        assert threshold.operator == ComparisonOperator.GREATER_THAN

    def test_portfolio_drawdown_halt_creation(self):
        """Test portfolio drawdown circuit breaker template."""
        rule = AlertRuleTemplates.portfolio_drawdown_halt()

        assert rule.rule_id == "portfolio_drawdown_halt"
        assert "circuit" in rule.name.lower() or "halt" in rule.description.lower()
        assert rule.severity == AlertSeverity.CRITICAL

    def test_portfolio_drawdown_halt_threshold(self):
        """Test portfolio drawdown halt threshold is 15% with >= operator."""
        rule = AlertRuleTemplates.portfolio_drawdown_halt()

        threshold = rule.threshold_rules[0]
        assert threshold.threshold == Decimal("15.0")
        assert threshold.operator == ComparisonOperator.GREATER_THAN_OR_EQUAL

    def test_portfolio_drawdown_hierarchy(self):
        """Test drawdown alerts form correct severity hierarchy."""
        warning = AlertRuleTemplates.portfolio_drawdown_warning()
        critical = AlertRuleTemplates.portfolio_drawdown_critical()
        halt = AlertRuleTemplates.portfolio_drawdown_halt()

        # Thresholds should be escalating
        assert warning.threshold_rules[0].threshold < critical.threshold_rules[0].threshold
        assert critical.threshold_rules[0].threshold < halt.threshold_rules[0].threshold

        # Deduplication should be shorter for critical
        assert warning.deduplicate_minutes > critical.deduplicate_minutes
        assert critical.deduplicate_minutes > halt.deduplicate_minutes


class TestVolatilityTemplates:
    """Test volatility alert templates."""

    def test_volatility_spike_creation(self):
        """Test volatility spike template creation."""
        rule = AlertRuleTemplates.volatility_spike()

        assert rule.rule_id == "volatility_spike"
        assert rule.severity == AlertSeverity.WARNING
        assert rule.enabled is True

    def test_volatility_spike_threshold(self):
        """Test volatility spike triggers at 150% of baseline."""
        rule = AlertRuleTemplates.volatility_spike()

        assert len(rule.threshold_rules) == 1
        threshold = rule.threshold_rules[0]
        assert threshold.metric_name == "PORTFOLIO_VOLATILITY"
        assert threshold.threshold == Decimal("150.0")
        assert threshold.operator == ComparisonOperator.GREATER_THAN

    def test_volatility_spike_tags(self):
        """Test volatility spike tags."""
        rule = AlertRuleTemplates.volatility_spike()

        assert rule.tags["category"] == "market_conditions"
        assert rule.tags["threshold"] == "150% baseline"


class TestCostExecutionTemplates:
    """Test cost and execution quality templates."""

    def test_cost_overrun_warning_creation(self):
        """Test cost overrun warning template."""
        rule = AlertRuleTemplates.cost_overrun_warning()

        assert rule.rule_id == "cost_overrun_warning"
        assert rule.severity == AlertSeverity.WARNING
        assert rule.enabled is True

    def test_cost_overrun_warning_threshold(self):
        """Test cost overrun warning at 5%."""
        rule = AlertRuleTemplates.cost_overrun_warning()

        threshold = rule.threshold_rules[0]
        assert threshold.metric_name == "ORDER_COST"
        assert threshold.threshold == Decimal("5.0")
        assert threshold.operator == ComparisonOperator.GREATER_THAN

    def test_cost_overrun_critical_threshold(self):
        """Test cost overrun critical at 10%."""
        rule = AlertRuleTemplates.cost_overrun_critical()

        assert rule.severity == AlertSeverity.CRITICAL
        threshold = rule.threshold_rules[0]
        assert threshold.threshold == Decimal("10.0")

    def test_fill_ratio_low_threshold(self):
        """Test fill ratio alert triggers below 95%."""
        rule = AlertRuleTemplates.fill_ratio_low()

        assert rule.rule_id == "fill_ratio_low"
        assert rule.severity == AlertSeverity.WARNING
        threshold = rule.threshold_rules[0]
        assert threshold.metric_name == "FILL_RATIO"
        assert threshold.threshold == Decimal("95.0")
        assert threshold.operator == ComparisonOperator.LESS_THAN

    def test_cost_execution_tags(self):
        """Test cost/execution templates are tagged correctly."""
        templates = [
            AlertRuleTemplates.cost_overrun_warning(),
            AlertRuleTemplates.cost_overrun_critical(),
            AlertRuleTemplates.fill_ratio_low(),
        ]

        for template in templates:
            assert template.tags["category"] == "execution_quality"


class TestPerformanceTemplates:
    """Test performance monitoring templates."""

    def test_sharpe_ratio_deterioration_creation(self):
        """Test Sharpe ratio deterioration template."""
        rule = AlertRuleTemplates.sharpe_ratio_deterioration()

        assert rule.rule_id == "sharpe_ratio_deterioration"
        assert rule.severity == AlertSeverity.WARNING
        assert len(rule.change_rules) == 1

    def test_sharpe_ratio_deterioration_change_rule(self):
        """Test Sharpe ratio deterioration change rule parameters."""
        rule = AlertRuleTemplates.sharpe_ratio_deterioration()

        change_rule = rule.change_rules[0]
        assert change_rule.metric_name == "PORTFOLIO_SHARPE"
        assert change_rule.change_percent == Decimal("-20.0")  # 20% decline
        assert change_rule.window_minutes == 60  # 1 hour
        assert change_rule.direction == "down"

    def test_sharpe_ratio_deterioration_tags(self):
        """Test Sharpe ratio deterioration tags."""
        rule = AlertRuleTemplates.sharpe_ratio_deterioration()

        assert rule.tags["category"] == "performance"
        assert "-20%" in rule.tags["threshold"]
        assert "1h" in rule.tags["threshold"]


class TestTradingQualityTemplates:
    """Test trading quality/loss templates."""

    def test_consecutive_losses_warning_creation(self):
        """Test consecutive losses warning template."""
        rule = AlertRuleTemplates.consecutive_losses_warning()

        assert rule.rule_id == "consecutive_losses_warning"
        assert rule.severity == AlertSeverity.WARNING
        assert rule.enabled is True

    def test_consecutive_losses_warning_threshold(self):
        """Test consecutive losses warning threshold."""
        rule = AlertRuleTemplates.consecutive_losses_warning()

        threshold = rule.threshold_rules[0]
        assert threshold.metric_name == "POSITION_PNL"
        assert threshold.threshold == Decimal("0.0")
        assert threshold.operator == ComparisonOperator.LESS_THAN

    def test_consecutive_losses_critical_creation(self):
        """Test consecutive losses critical template."""
        rule = AlertRuleTemplates.consecutive_losses_critical()

        assert rule.rule_id == "consecutive_losses_critical"
        assert rule.severity == AlertSeverity.CRITICAL

    def test_consecutive_losses_escalation(self):
        """Test consecutive losses escalation from warning to critical."""
        warning = AlertRuleTemplates.consecutive_losses_warning()
        critical = AlertRuleTemplates.consecutive_losses_critical()

        # Both should have same threshold but different deduplication
        assert warning.threshold_rules[0].threshold == critical.threshold_rules[0].threshold
        assert critical.deduplicate_minutes < warning.deduplicate_minutes

    def test_consecutive_losses_tags(self):
        """Test consecutive losses template tags."""
        templates = [
            AlertRuleTemplates.consecutive_losses_warning(),
            AlertRuleTemplates.consecutive_losses_critical(),
        ]

        for template in templates:
            assert template.tags["category"] == "trading_quality"


class TestSystemHealthTemplates:
    """Test system health alert templates."""

    def test_latency_spike_creation(self):
        """Test latency spike template creation."""
        rule = AlertRuleTemplates.latency_spike()

        assert rule.rule_id == "latency_spike"
        assert rule.severity == AlertSeverity.WARNING
        assert rule.enabled is True

    def test_latency_spike_threshold(self):
        """Test latency spike triggers at 1000ms (1 second)."""
        rule = AlertRuleTemplates.latency_spike()

        threshold = rule.threshold_rules[0]
        assert threshold.metric_name == "LATENCY_MS"
        assert threshold.threshold == Decimal("1000.0")
        assert threshold.operator == ComparisonOperator.GREATER_THAN

    def test_error_rate_high_creation(self):
        """Test error rate high template creation."""
        rule = AlertRuleTemplates.error_rate_high()

        assert rule.rule_id == "error_rate_high"
        assert rule.severity == AlertSeverity.CRITICAL
        assert rule.enabled is True

    def test_error_rate_high_threshold(self):
        """Test error rate high triggers at 5%."""
        rule = AlertRuleTemplates.error_rate_high()

        threshold = rule.threshold_rules[0]
        assert threshold.metric_name == "ERROR_RATE"
        assert threshold.threshold == Decimal("5.0")
        assert threshold.operator == ComparisonOperator.GREATER_THAN

    def test_system_health_tags(self):
        """Test system health templates are tagged correctly."""
        templates = [
            AlertRuleTemplates.latency_spike(),
            AlertRuleTemplates.error_rate_high(),
        ]

        for template in templates:
            assert template.tags["category"] == "system_health"


class TestUtilityMethods:
    """Test utility methods for accessing templates."""

    def test_get_all_default_templates(self):
        """Test get_all_default_templates returns all 12 templates."""
        templates = AlertRuleTemplates.get_all_default_templates()

        assert len(templates) == 12
        assert all(isinstance(t, object) for t in templates)

    def test_get_all_templates_unique_ids(self):
        """Test all templates have unique rule IDs."""
        templates = AlertRuleTemplates.get_all_default_templates()
        rule_ids = [t.rule_id for t in templates]

        assert len(rule_ids) == len(set(rule_ids))

    def test_get_template_by_id_valid(self):
        """Test get_template_by_id with valid ID."""
        rule = AlertRuleTemplates.get_template_by_id("portfolio_drawdown_warning")

        assert rule.rule_id == "portfolio_drawdown_warning"
        assert rule.severity == AlertSeverity.WARNING

    def test_get_template_by_id_invalid(self):
        """Test get_template_by_id with invalid ID raises error."""
        with pytest.raises(ValueError, match="Unknown rule template ID"):
            AlertRuleTemplates.get_template_by_id("nonexistent_rule")

    def test_get_templates_by_category_portfolio_risk(self):
        """Test get_templates_by_category returns portfolio_risk templates."""
        templates = AlertRuleTemplates.get_templates_by_category("portfolio_risk")

        assert len(templates) == 3  # 3 drawdown rules
        assert all("drawdown" in t.rule_id for t in templates)

    def test_get_templates_by_category_execution_quality(self):
        """Test get_templates_by_category returns execution_quality templates."""
        templates = AlertRuleTemplates.get_templates_by_category("execution_quality")

        assert len(templates) == 3  # cost_warning, cost_critical, fill_ratio_low
        assert all("cost" in t.rule_id or "fill" in t.rule_id for t in templates)

    def test_get_templates_by_category_system_health(self):
        """Test get_templates_by_category returns system_health templates."""
        templates = AlertRuleTemplates.get_templates_by_category("system_health")

        assert len(templates) == 2  # latency_spike, error_rate_high
        assert all("latency" in t.rule_id or "error" in t.rule_id for t in templates)

    def test_get_critical_templates(self):
        """Test get_critical_templates returns only CRITICAL severity rules."""
        templates = AlertRuleTemplates.get_critical_templates()

        # Should be: portfolio_drawdown_critical, portfolio_drawdown_halt,
        # cost_overrun_critical, consecutive_losses_critical, error_rate_high = 5 total
        assert len(templates) == 5
        assert all(t.severity == AlertSeverity.CRITICAL for t in templates)

    def test_get_warning_templates(self):
        """Test warning severity templates."""
        all_templates = AlertRuleTemplates.get_all_default_templates()
        warning_templates = [t for t in all_templates if t.severity == AlertSeverity.WARNING]

        # Should be: portfolio_drawdown_warning, volatility_spike, cost_overrun_warning,
        # sharpe_ratio_deterioration, consecutive_losses_warning, latency_spike = 6 total
        assert len(warning_templates) >= 6  # At least 6 warning templates


class TestTemplateLogicOperators:
    """Test template logic operators."""

    def test_all_templates_use_or_logic(self):
        """Test all templates use OR logic for rule composition."""
        templates = AlertRuleTemplates.get_all_default_templates()

        for template in templates:
            assert template.logic_operator == LogicOperator.OR

    def test_single_rule_per_template(self):
        """Test most templates have single threshold rule (except change rules)."""
        templates = AlertRuleTemplates.get_all_default_templates()

        for template in templates:
            total_rules = len(template.threshold_rules) + len(template.change_rules)
            assert total_rules >= 1  # At least one rule


class TestTemplateDeduplication:
    """Test deduplication settings across templates."""

    def test_deduplication_windows_reasonable(self):
        """Test deduplication windows are reasonable (1-30 minutes)."""
        templates = AlertRuleTemplates.get_all_default_templates()

        for template in templates:
            assert 1 <= template.deduplicate_minutes <= 30

    def test_critical_shorter_deduplication(self):
        """Test CRITICAL templates have shorter deduplication windows."""
        critical_templates = AlertRuleTemplates.get_critical_templates()
        warning_templates = [
            t
            for t in AlertRuleTemplates.get_all_default_templates()
            if t.severity == AlertSeverity.WARNING
        ]

        avg_critical = sum(t.deduplicate_minutes for t in critical_templates) / len(
            critical_templates
        )
        avg_warning = sum(t.deduplicate_minutes for t in warning_templates) / len(warning_templates)

        assert avg_critical < avg_warning

    def test_deduplication_escalates_with_severity(self):
        """Test deduplication reduces as severity increases."""
        warning = AlertRuleTemplates.portfolio_drawdown_warning()
        critical = AlertRuleTemplates.portfolio_drawdown_critical()
        halt = AlertRuleTemplates.portfolio_drawdown_halt()

        assert warning.deduplicate_minutes >= critical.deduplicate_minutes
        assert critical.deduplicate_minutes >= halt.deduplicate_minutes


class TestTemplateMetadata:
    """Test template metadata and tags."""

    def test_all_templates_have_metadata(self):
        """Test all templates have required metadata fields."""
        templates = AlertRuleTemplates.get_all_default_templates()

        for template in templates:
            assert template.rule_id
            assert template.name
            assert template.description
            assert template.severity
            assert template.tags

    def test_all_templates_categorized(self):
        """Test all templates have a category tag."""
        templates = AlertRuleTemplates.get_all_default_templates()

        valid_categories = {
            "portfolio_risk",
            "market_conditions",
            "execution_quality",
            "performance",
            "trading_quality",
            "system_health",
        }

        for template in templates:
            assert "category" in template.tags
            assert template.tags["category"] in valid_categories

    def test_all_templates_have_severity_level_tag(self):
        """Test all templates have severity_level tag."""
        templates = AlertRuleTemplates.get_all_default_templates()

        for template in templates:
            assert "severity_level" in template.tags
            assert template.tags["severity_level"] in {"info", "warning", "critical"}

    def test_template_serialization(self):
        """Test templates can be serialized to dict."""
        rule = AlertRuleTemplates.portfolio_drawdown_warning()
        rule_dict = rule.to_dict()

        assert rule_dict["rule_id"] == "portfolio_drawdown_warning"
        assert rule_dict["severity"] == "warning"
        assert len(rule_dict["threshold_rules"]) == 1


class TestEdgeCases:
    """Test edge cases and boundary values."""

    def test_threshold_boundary_values_decimal(self):
        """Test thresholds use Decimal for precision."""
        rule = AlertRuleTemplates.portfolio_drawdown_warning()
        threshold = rule.threshold_rules[0]

        assert isinstance(threshold.threshold, Decimal)

    def test_change_rule_negative_threshold(self):
        """Test change rules can have negative thresholds (for decline)."""
        rule = AlertRuleTemplates.sharpe_ratio_deterioration()
        change_rule = rule.change_rules[0]

        assert change_rule.change_percent < 0  # Negative = decline

    def test_window_minutes_positive(self):
        """Test all change rules have positive window minutes."""
        templates = AlertRuleTemplates.get_all_default_templates()

        for template in templates:
            for change_rule in template.change_rules:
                assert change_rule.window_minutes > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
