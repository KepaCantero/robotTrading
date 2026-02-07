"""
Tests for Toil Tracker.

Comprehensive tests for the toil tracking system following Google SRE principles.
"""

import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, '/Users/kepa.cantero/Projects/algoTrading')

from app.sre.automation.toil_tracker import (
    AutomationOpportunity,
    AutomationPotential,
    ToilCategory,
    ToilConfig,
    ToilEntry,
    ToilMetrics,
    ToilReport,
    ToilTracker,
    get_toil_tracker,
)


class TestToilEntry:
    """Test ToilEntry data class."""

    def test_create_toil_entry(self):
        """Test creating a basic toil entry."""
        entry = ToilEntry(
            timestamp=datetime.utcnow(),
            task="Manual deployment",
            category=ToilCategory.DEPLOYMENT,
            duration_minutes=45,
            automated=False,
            assignable=True,
        )

        assert entry.task == "Manual deployment"
        assert entry.category == ToilCategory.DEPLOYMENT
        assert entry.duration_minutes == 45
        assert entry.is_toil is True  # Not automated = toil
        assert entry.assignable is True

    def test_automated_entry_not_toil(self):
        """Test that automated entries are not considered toil."""
        entry = ToilEntry(
            timestamp=datetime.utcnow(),
            task="Automated deployment",
            category=ToilCategory.DEPLOYMENT,
            duration_minutes=5,
            automated=True,
            assignable=True,
        )

        assert entry.is_toil is False  # Automated = not toil

    def test_toil_entry_to_dict(self):
        """Test converting toil entry to dictionary."""
        entry = ToilEntry(
            timestamp=datetime.utcnow(),
            task="Manual deployment",
            category=ToilCategory.DEPLOYMENT,
            duration_minutes=45,
            automated=False,
            engineer="john",
            tags=["production", "urgent"],
        )

        entry_dict = entry.to_dict()

        assert entry_dict["task"] == "Manual deployment"
        assert entry_dict["category"] == "deployment"
        assert entry_dict["duration_minutes"] == 45
        assert entry_dict["engineer"] == "john"
        assert entry_dict["tags"] == ["production", "urgent"]

    def test_invalid_duration_raises_error(self):
        """Test that negative duration raises error."""
        with pytest.raises(ValueError):
            ToilEntry(
                timestamp=datetime.utcnow(),
                task="Task",
                category=ToilCategory.OTHER,
                duration_minutes=-10,
            )


class TestToilTracker:
    """Test ToilTracker class."""

    @pytest.fixture
    async def tracker(self):
        """Create a test toil tracker with temp database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_toil.db"
            config = ToilConfig(db_path=str(db_path))

            tracker = ToilTracker("test_service", config)
            await tracker.initialize()

            yield tracker

    @pytest.mark.asyncio
    async def test_initialize(self, tracker):
        """Test tracker initialization."""
        assert tracker.service_name == "test_service"
        assert tracker.config.toil_warning_threshold == 50.0
        assert tracker.config.toil_critical_threshold == 70.0

    def test_log_work(self, tracker):
        """Test logging work entries."""
        entry = tracker.log_work(
            task="Manual deployment",
            category="deployment",
            duration=45,
            automated=False,
        )

        assert entry.task == "Manual deployment"
        assert entry.category == ToilCategory.DEPLOYMENT
        assert entry.duration_minutes == 45
        assert entry.is_toil is True

    def test_log_automated_work(self, tracker):
        """Test logging automated work."""
        entry = tracker.log_work(
            task="Automated deployment",
            category="deployment",
            duration=5,
            automated=True,
        )

        assert entry.is_toil is False  # Automated is not toil

    def test_calculate_toil_percentage(self, tracker):
        """Test calculating toil percentage."""
        # Log some work: 60 min toil, 40 min engineering
        tracker.log_work("Manual deployment", "deployment", 60, automated=False)
        tracker.log_work("Code review", "review", 40, automated=False)

        toil_pct = tracker.calculate_toil_percentage(days=30)

        # Should be 60% (60/(60+40))
        assert toil_pct == 60.0

    def test_calculate_toil_percentage_with_automated(self, tracker):
        """Test toil percentage with automated work."""
        # 30 min toil, 20 min automated (not toil), 50 min engineering
        tracker.log_work("Manual fix", "troubleshooting", 30, automated=False)
        tracker.log_work("Auto deploy", "deployment", 20, automated=True)
        tracker.log_work("Feature work", "other", 50, automated=False)

        toil_pct = tracker.calculate_toil_percentage(days=30)

        # Should be 30% (30/(30+20+50))
        assert toil_pct == 30.0

    def test_calculate_toil_percentage_empty(self, tracker):
        """Test toil percentage with no entries."""
        toil_pct = tracker.calculate_toil_percentage(days=30)
        assert toil_pct == 0.0

    def test_get_top_toil_sources(self, tracker):
        """Test getting top toil sources."""
        # Add various toil entries
        tracker.log_work("Deployment 1", "deployment", 30, automated=False)
        tracker.log_work("Deployment 2", "deployment", 20, automated=False)
        tracker.log_work("Incident response", "incident_response", 45, automated=False)
        tracker.log_work("Monitoring", "monitoring", 15, automated=False)

        top_sources = tracker.get_top_toil_sources(days=30, limit=5)

        # Deployment should be top with 50 minutes
        assert top_sources[0][0] == "deployment"
        assert top_sources[0][1] == 50

        # Incident response should be second with 45 minutes
        assert top_sources[1][0] == "incident_response"
        assert top_sources[1][1] == 45

    def test_get_top_toil_tasks(self, tracker):
        """Test getting top individual toil tasks."""
        # Log same task multiple times
        tracker.log_work("Manual deployment", "deployment", 30, automated=False)
        tracker.log_work("Manual deployment", "deployment", 20, automated=False)
        tracker.log_work("Server reboot", "maintenance", 45, automated=False)

        top_tasks = tracker.get_top_toil_tasks(days=30, limit=5)

        # Manual deployment should be top with 50 minutes
        assert top_tasks[0][0] == "Manual deployment"
        assert top_tasks[0][1] == 50

    def test_generate_automation_opportunities(self, tracker):
        """Test generating automation opportunities."""
        # Add recurring toil
        tracker.log_work(
            "Manual deployment",
            "deployment",
            30,
            automated=False,
            automation_potential="high",
        )
        tracker.log_work(
            "Manual deployment",
            "deployment",
            30,
            automated=False,
            automation_potential="high",
        )
        tracker.log_work(
            "Manual deployment",
            "deployment",
            30,
            automated=False,
            automation_potential="high",
        )

        opportunities = tracker.generate_automation_opportunities(days=30)

        assert len(opportunities) > 0
        assert opportunities[0].task_pattern == "Manual deployment"
        assert opportunities[0].category == ToilCategory.DEPLOYMENT
        assert opportunities[0].total_toil_minutes == 90
        assert opportunities[0].automation_potential == AutomationPotential.HIGH

    def test_get_engineer_breakdown(self, tracker):
        """Test breakdown by engineer."""
        # Log work for different engineers
        tracker.log_work(
            "Task 1",
            "deployment",
            30,
            automated=False,
            engineer="alice",
        )
        tracker.log_work(
            "Task 2",
            "deployment",
            20,
            automated=False,
            engineer="alice",
        )
        tracker.log_work(
            "Task 3",
            "incident_response",
            40,
            automated=False,
            engineer="bob",
        )

        breakdown = tracker.get_engineer_breakdown(days=30)

        assert "alice" in breakdown
        assert "bob" in breakdown

        # Alice: 50 min total (all toil), 100% toil
        assert breakdown["alice"].total_minutes == 50
        assert breakdown["alice"].toil_percentage == 100.0

        # Bob: 40 min total (all toil), 100% toil
        assert breakdown["bob"].total_minutes == 40
        assert breakdown["bob"].toil_percentage == 100.0

    def test_get_trend_data(self, tracker):
        """Test getting trend data."""
        # Add entries over time
        now = datetime.utcnow()

        # Manually create entries with different timestamps
        tracker._entries = [
            ToilEntry(
                timestamp=now - timedelta(days=1),
                task="Task 1",
                category=ToilCategory.DEPLOYMENT,
                duration_minutes=30,
                automated=False,
            ),
            ToilEntry(
                timestamp=now - timedelta(days=10),
                task="Task 2",
                category=ToilCategory.DEPLOYMENT,
                duration_minutes=40,
                automated=False,
            ),
        ]

        trends = tracker.get_trend_data(days=30, bucket_days=7)

        assert len(trends) > 0
        assert "period_start" in trends[0]
        assert "metrics" in trends[0]

    @pytest.mark.asyncio
    async def test_generate_report(self, tracker):
        """Test generating comprehensive report."""
        # Add sample data
        tracker.log_work("Manual deployment", "deployment", 45, automated=False)
        tracker.log_work("Incident fix", "incident_response", 60, automated=False)
        tracker.log_work("Feature work", "other", 120, automated=False)

        report = await tracker.generate_report(days=30)

        assert isinstance(report, ToilReport)
        assert report.metrics.total_minutes == 225
        assert len(report.top_toil_sources) > 0
        assert len(report.recommendations) > 0

    def test_export_to_json(self, tracker):
        """Test exporting toil data to JSON."""
        # Add sample data
        tracker.log_work("Manual deployment", "deployment", 45, automated=False)

        json_str = tracker.export_to_json(days=30)

        data = json.loads(json_str)

        assert data["service_name"] == "test_service"
        assert len(data["entries"]) == 1
        assert data["entries"][0]["task"] == "Manual deployment"
        assert "metrics" in data
        assert "top_sources" in data

    def test_detect_category(self, tracker):
        """Test automatic category detection."""
        # Should detect incident-related keywords
        category = tracker._detect_category("Investigate sev2 incident")
        assert category == ToilCategory.INCIDENT_RESPONSE

        # Should detect deployment-related keywords
        category = tracker._detect_category("Deploy to production")
        assert category == ToilCategory.DEPLOYMENT

        # Should default to OTHER for unknown
        category = tracker._detect_category("Random task")
        assert category == ToilCategory.OTHER

    def test_threshold_alerts(self, tracker):
        """Test threshold alerting."""
        # Log work that exceeds warning threshold
        # 70 min toil, 30 min engineering = 70% toil
        tracker.log_work("Toil task", "deployment", 70, automated=False)
        tracker.log_work("Engineering", "other", 30, automated=False)

        # Should log warning (check logs)
        toil_pct = tracker.calculate_toil_percentage(days=30)
        assert toil_pct == 70.0


class TestToilMetrics:
    """Test ToilMetrics data class."""

    def test_toil_metrics_calculation(self):
        """Test metrics calculation."""
        metrics = ToilMetrics(
            total_minutes=100,
            toil_minutes=40,
            engineering_minutes=60,
            toil_percentage=40.0,
            engineering_percentage=60.0,
            automated_minutes=20,
            automation_coverage=20.0,
        )

        assert metrics.total_minutes == 100
        assert metrics.toil_percentage == 40.0
        assert metrics.automation_coverage == 20.0

    def test_toil_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = ToilMetrics(
            total_minutes=100,
            toil_minutes=40,
            engineering_minutes=60,
            toil_percentage=40.0,
            engineering_percentage=60.0,
            automated_minutes=20,
            automation_coverage=20.0,
        )

        metrics_dict = metrics.to_dict()

        assert metrics_dict["total_minutes"] == 100
        assert metrics_dict["toil_percentage"] == 40.0
        assert metrics_dict["automation_coverage"] == 20.0


class TestAutomationOpportunity:
    """Test AutomationOpportunity data class."""

    def test_automation_opportunity_creation(self):
        """Test creating automation opportunity."""
        opp = AutomationOpportunity(
            category=ToilCategory.DEPLOYMENT,
            task_pattern="Manual deployment",
            frequency=10,
            avg_duration_minutes=30,
            total_toil_minutes=300,
            automation_potential=AutomationPotential.HIGH,
            estimated_savings_hours=4.0,
            implementation_effort="LOW",
            priority=90,
        )

        assert opp.category == ToilCategory.DEPLOYMENT
        assert opp.task_pattern == "Manual deployment"
        assert opp.frequency == 10
        assert opp.priority == 90

    def test_automation_opportunity_to_dict(self):
        """Test converting opportunity to dictionary."""
        opp = AutomationOpportunity(
            category=ToilCategory.DEPLOYMENT,
            task_pattern="Manual deployment",
            frequency=10,
            avg_duration_minutes=30,
            total_toil_minutes=300,
            automation_potential=AutomationPotential.HIGH,
            estimated_savings_hours=4.0,
            implementation_effort="LOW",
            priority=90,
        )

        opp_dict = opp.to_dict()

        assert opp_dict["category"] == "deployment"
        assert opp_dict["task_pattern"] == "Manual deployment"
        assert opp_dict["frequency"] == 10
        assert opp_dict["priority"] == 90


class TestSingleton:
    """Test singleton pattern."""

    def test_get_toil_tracker_singleton(self):
        """Test that get_toil_tracker returns singleton."""
        tracker1 = get_toil_tracker("test_singleton")
        tracker2 = get_toil_tracker("test_singleton")

        assert tracker1 is tracker2

    def test_get_toil_tracker_different_services(self):
        """Test that different services get different trackers."""
        tracker1 = get_toil_tracker("service1")
        tracker2 = get_toil_tracker("service2")

        assert tracker1 is not tracker2
        assert tracker1.service_name == "service1"
        assert tracker2.service_name == "service2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
