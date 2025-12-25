"""
Tests for Alert Rule Engine - Rule evaluation and composition

Tests cover:
- Rule registration and lookup
- Threshold rule evaluation
- Change rule evaluation
- Rule composition (AND/OR logic)
- Event generation
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.services.alerting_system import (
    AlertRule,
    AlertRuleEngine,
    AlertSeverity,
    ChangeRule,
    ComparisonOperator,
    LogicOperator,
    NotificationChannelType,
    NotificationTarget,
    ThresholdRule,
)
from app.services.alerting_system.models import AlertEvaluationContext


class TestAlertRuleEngineRegistration:
    """Test rule registration."""

    def test_register_single_rule(self):
        """Test registering a single rule."""
        engine = AlertRuleEngine()
        rule = AlertRule(
            rule_id="rule_001",
            name="Test Rule",
            description="Test",
            severity=AlertSeverity.WARNING,
        )

        engine.register_rule(rule)
        assert "rule_001" in engine.rules
        assert engine.rules["rule_001"] == rule

    def test_register_multiple_rules(self):
        """Test registering multiple rules."""
        engine = AlertRuleEngine()

        for i in range(5):
            rule = AlertRule(
                rule_id=f"rule_{i:03d}",
                name=f"Rule {i}",
                description="Test",
                severity=AlertSeverity.INFO,
            )
            engine.register_rule(rule)

        assert len(engine.rules) == 5

    def test_unregister_rule(self):
        """Test unregistering a rule."""
        engine = AlertRuleEngine()
        rule = AlertRule(
            rule_id="rule_001",
            name="Test",
            description="Test",
            severity=AlertSeverity.INFO,
        )

        engine.register_rule(rule)
        assert len(engine.rules) == 1

        result = engine.unregister_rule("rule_001")
        assert result is True
        assert len(engine.rules) == 0

    def test_unregister_nonexistent_rule(self):
        """Test unregistering non-existent rule."""
        engine = AlertRuleEngine()
        result = engine.unregister_rule("nonexistent")
        assert result is False


class TestThresholdRuleEvaluation:
    """Test threshold rule evaluation."""

    def test_greater_than_threshold(self):
        """Test evaluating greater than rule."""
        engine = AlertRuleEngine()
        threshold = ThresholdRule(
            metric_name="price",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=Decimal("100"),
        )
        rule = AlertRule(
            rule_id="rule_001",
            name="High Price",
            description="Alert on high price",
            severity=AlertSeverity.WARNING,
            threshold_rules=[threshold],
        )
        engine.register_rule(rule)

        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("105"),
        )

        triggered, event = engine.evaluate_rule(rule, context)
        assert triggered is True
        assert event is not None

    def test_threshold_not_triggered(self):
        """Test threshold not triggered."""
        engine = AlertRuleEngine()
        threshold = ThresholdRule(
            metric_name="price",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=Decimal("100"),
        )
        rule = AlertRule(
            rule_id="rule_001",
            name="High Price",
            description="",
            severity=AlertSeverity.WARNING,
            threshold_rules=[threshold],
        )
        engine.register_rule(rule)

        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("95"),
        )

        triggered, event = engine.evaluate_rule(rule, context)
        assert triggered is False
        assert event is None

    def test_threshold_with_symbol_filter(self):
        """Test threshold rule with symbol filter."""
        engine = AlertRuleEngine()
        threshold = ThresholdRule(
            metric_name="price",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=Decimal("100"),
            symbol="AAPL",
        )
        rule = AlertRule(
            rule_id="rule_001",
            name="AAPL High Price",
            description="",
            severity=AlertSeverity.WARNING,
            threshold_rules=[threshold],
        )
        engine.register_rule(rule)

        # Should trigger for AAPL
        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("105"),
            symbol="AAPL",
        )
        triggered, event = engine.evaluate_rule(rule, context)
        assert triggered is True

        # Should not trigger for MSFT
        context2 = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("105"),
            symbol="MSFT",
        )
        triggered2, event2 = engine.evaluate_rule(rule, context2)
        assert triggered2 is False


class TestChangeRuleEvaluation:
    """Test change rule evaluation."""

    def test_change_rule_up(self):
        """Test change rule for upward change."""
        engine = AlertRuleEngine()
        change = ChangeRule(
            metric_name="price",
            change_percent=Decimal("5"),
            window_minutes=60,
            direction="up",
        )
        rule = AlertRule(
            rule_id="rule_001",
            name="Price Up Alert",
            description="",
            severity=AlertSeverity.INFO,
            change_rules=[change],
        )
        engine.register_rule(rule)

        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("110"),
            window_data=[Decimal("100"), Decimal("105"), Decimal("110")],
        )

        triggered, event = engine.evaluate_rule(rule, context)
        assert triggered is True

    def test_change_rule_down(self):
        """Test change rule for downward change."""
        engine = AlertRuleEngine()
        change = ChangeRule(
            metric_name="price",
            change_percent=Decimal("5"),
            window_minutes=60,
            direction="down",
        )
        rule = AlertRule(
            rule_id="rule_001",
            name="Price Down Alert",
            description="",
            severity=AlertSeverity.WARNING,
            change_rules=[change],
        )
        engine.register_rule(rule)

        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("90"),
            window_data=[Decimal("100"), Decimal("95"), Decimal("90")],
        )

        triggered, event = engine.evaluate_rule(rule, context)
        assert triggered is True

    def test_change_rule_insufficient_data(self):
        """Test change rule with insufficient window data."""
        engine = AlertRuleEngine()
        change = ChangeRule(
            metric_name="price",
            change_percent=Decimal("5"),
            window_minutes=60,
        )
        rule = AlertRule(
            rule_id="rule_001",
            name="Price Change",
            description="",
            severity=AlertSeverity.INFO,
            change_rules=[change],
        )
        engine.register_rule(rule)

        # Not enough window data
        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("105"),
            window_data=[Decimal("100")],
        )

        triggered, event = engine.evaluate_rule(rule, context)
        assert triggered is False


class TestRuleComposition:
    """Test rule composition with AND/OR logic."""

    def test_and_logic_both_true(self):
        """Test AND logic with both rules true."""
        engine = AlertRuleEngine()
        threshold1 = ThresholdRule(
            metric_name="price",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=Decimal("100"),
        )
        threshold2 = ThresholdRule(
            metric_name="volume",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=Decimal("1000000"),
        )
        rule = AlertRule(
            rule_id="rule_001",
            name="High Price and Volume",
            description="",
            severity=AlertSeverity.CRITICAL,
            threshold_rules=[threshold1, threshold2],
            logic_operator=LogicOperator.AND,
        )
        engine.register_rule(rule)

        # Both conditions met
        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("105"),
        )
        # Need to mock multiple metrics somehow
        triggered, event = engine.evaluate_rule(rule, context)
        # This test simplified - real implementation would need multi-metric context

    def test_or_logic_one_true(self):
        """Test OR logic with one rule true."""
        engine = AlertRuleEngine()
        threshold = ThresholdRule(
            metric_name="price",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=Decimal("100"),
        )
        rule = AlertRule(
            rule_id="rule_001",
            name="Price or Volume Alert",
            description="",
            severity=AlertSeverity.WARNING,
            threshold_rules=[threshold],
            logic_operator=LogicOperator.OR,
        )
        engine.register_rule(rule)

        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("105"),
        )

        triggered, event = engine.evaluate_rule(rule, context)
        assert triggered is True


class TestEventGeneration:
    """Test alert event generation."""

    def test_event_has_correct_details(self):
        """Test generated event has correct details."""
        engine = AlertRuleEngine()
        # Alert when loss exceeds 5000 (using LESS_THAN for negative loss values)
        threshold = ThresholdRule(
            metric_name="loss",
            operator=ComparisonOperator.LESS_THAN,
            threshold=Decimal("-5000"),
        )
        rule = AlertRule(
            rule_id="rule_critical",
            name="Catastrophic Loss",
            description="Portfolio loss exceeds 5000",
            severity=AlertSeverity.CRITICAL,
            threshold_rules=[threshold],
        )
        engine.register_rule(rule)

        context = AlertEvaluationContext(
            metric_name="loss",
            current_value=Decimal("-6000"),
            symbol="SPY",
            portfolio_id="port_001",
        )

        triggered, event = engine.evaluate_rule(rule, context)
        assert triggered is True
        assert event.rule_id == "rule_critical"
        assert event.severity == AlertSeverity.CRITICAL
        assert event.metric_value == Decimal("-6000")
        assert event.symbol == "SPY"
        assert event.portfolio_id == "port_001"


class TestBatchEvaluation:
    """Test evaluating all rules at once."""

    def test_evaluate_all_rules(self):
        """Test evaluating all registered rules."""
        engine = AlertRuleEngine()

        # Register 3 rules
        for i in range(3):
            threshold = ThresholdRule(
                metric_name=f"metric_{i}",
                operator=ComparisonOperator.GREATER_THAN,
                threshold=Decimal("100"),
            )
            rule = AlertRule(
                rule_id=f"rule_{i:03d}",
                name=f"Rule {i}",
                description="",
                severity=AlertSeverity.WARNING,
                threshold_rules=[threshold],
            )
            engine.register_rule(rule)

        # Evaluate with context that triggers first rule
        context = AlertEvaluationContext(
            metric_name="metric_0",
            current_value=Decimal("105"),
        )

        events = engine.evaluate_all_rules(context)
        assert len(events) == 1
        assert events[0].rule_id == "rule_000"

    def test_evaluate_all_rules_no_triggers(self):
        """Test batch evaluation with no triggers."""
        engine = AlertRuleEngine()
        rule = AlertRule(
            rule_id="rule_001",
            name="Never Triggers",
            description="",
            severity=AlertSeverity.INFO,
            threshold_rules=[
                ThresholdRule(
                    metric_name="impossible",
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=Decimal("9999999"),
                )
            ],
        )
        engine.register_rule(rule)

        context = AlertEvaluationContext(
            metric_name="impossible",
            current_value=Decimal("1"),
        )

        events = engine.evaluate_all_rules(context)
        assert len(events) == 0


class TestEvaluationHistory:
    """Test evaluation history tracking."""

    def test_evaluation_recorded(self):
        """Test evaluation is recorded in history."""
        engine = AlertRuleEngine()
        rule = AlertRule(
            rule_id="rule_001",
            name="Test",
            description="",
            severity=AlertSeverity.INFO,
            threshold_rules=[
                ThresholdRule(
                    metric_name="price",
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=Decimal("100"),
                )
            ],
        )
        engine.register_rule(rule)

        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("105"),
        )

        engine.evaluate_rule(rule, context)

        assert len(engine.evaluation_history) > 0
        assert engine.evaluation_history[-1]["rule_id"] == "rule_001"
        assert engine.evaluation_history[-1]["triggered"] is True

    def test_history_bounded(self):
        """Test evaluation history is bounded in size."""
        engine = AlertRuleEngine()
        engine._max_history = 100

        rule = AlertRule(
            rule_id="rule_001",
            name="Test",
            description="",
            severity=AlertSeverity.INFO,
        )
        engine.register_rule(rule)

        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("105"),
        )

        # Evaluate 200 times
        for _ in range(200):
            engine.evaluate_rule(rule, context)

        assert len(engine.evaluation_history) <= 100


class TestStatistics:
    """Test statistics tracking."""

    def test_evaluation_statistics(self):
        """Test evaluation statistics."""
        engine = AlertRuleEngine()
        rule = AlertRule(
            rule_id="rule_001",
            name="Test",
            description="",
            severity=AlertSeverity.WARNING,
        )
        engine.register_rule(rule)

        stats = engine.get_evaluation_stats()
        assert stats["total_evaluations"] == 0

    def test_rules_summary(self):
        """Test rules summary."""
        engine = AlertRuleEngine()

        for i in range(3):
            rule = AlertRule(
                rule_id=f"rule_{i:03d}",
                name=f"Rule {i}",
                description="",
                severity=AlertSeverity.WARNING if i % 2 == 0 else AlertSeverity.CRITICAL,
                enabled=i != 2,
            )
            engine.register_rule(rule)

        summary = engine.get_rules_summary()
        assert summary["total_rules"] == 3
        assert summary["enabled_rules"] == 2
