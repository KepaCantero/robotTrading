"""
Comprehensive test suite for T17.1: External Integrations

Tests for DagsterOrchestrator and ZiplineIntegrator (QuestDB/MLflow removed from the stack)
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.services.external_integrations import DagsterOrchestrator, ZiplineIntegrator
from app.services.external_integrations.dagster_orchestrator import JobStatus, PipelineStep
from app.services.external_integrations.zipline_integrator import BacktestConfig

# ============================================================================
# QUESTDB CONNECTOR TESTS (35 tests)
# ============================================================================


class TestDagsterOrchestratorInitialization:
    """Test Dagster orchestrator initialization."""

    def test_dagster_init(self):
        """Test Dagster orchestrator initialization."""
        orchestrator = DagsterOrchestrator()
        assert len(orchestrator.jobs) == 0
        assert len(orchestrator.pipelines) == 0
        assert len(orchestrator.job_history) == 0

    def test_dagster_singleton_getter(self):
        """Test singleton getter for Dagster orchestrator."""
        from app.services.external_integrations import get_dagster_orchestrator

        orch1 = get_dagster_orchestrator()
        orch2 = get_dagster_orchestrator()
        assert orch1 is orch2


class TestDagsterJobManagement:
    """Test Dagster job lifecycle management."""

    @pytest.mark.asyncio
    async def test_create_job(self):
        """Test job creation."""
        orchestrator = DagsterOrchestrator()
        job = await orchestrator.create_job("backtest_aapl", "backtest")
        assert job.job_id == "job_0"
        assert job.name == "backtest_aapl"
        assert job.job_type == "backtest"
        assert job.status == JobStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_multiple_jobs(self):
        """Test creating multiple jobs."""
        orchestrator = DagsterOrchestrator()
        job1 = await orchestrator.create_job("job1", "backtest")
        job2 = await orchestrator.create_job("job2", "data_fetch")
        job3 = await orchestrator.create_job("job3", "train_model")

        assert len(orchestrator.jobs) == 3
        assert job1.job_id != job2.job_id != job3.job_id

    @pytest.mark.asyncio
    async def test_execute_job(self):
        """Test job execution."""
        orchestrator = DagsterOrchestrator()
        job = await orchestrator.create_job("test_job", "backtest")
        result = await orchestrator.execute_job(job.job_id)

        assert result is True
        assert orchestrator.jobs[job.job_id].status == JobStatus.RUNNING
        assert orchestrator.jobs[job.job_id].run_count == 1

    @pytest.mark.asyncio
    async def test_execute_nonexistent_job(self):
        """Test executing non-existent job."""
        orchestrator = DagsterOrchestrator()
        result = await orchestrator.execute_job("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_complete_job(self):
        """Test job completion."""
        orchestrator = DagsterOrchestrator()
        job = await orchestrator.create_job("test_job", "backtest")
        await orchestrator.execute_job(job.job_id)

        result = await orchestrator.complete_job(job.job_id, result={"return": "0.15"})
        assert result is True
        assert orchestrator.jobs[job.job_id].status == JobStatus.SUCCESS
        assert len(orchestrator.job_history) == 1

    @pytest.mark.asyncio
    async def test_fail_job(self):
        """Test job failure."""
        orchestrator = DagsterOrchestrator()
        job = await orchestrator.create_job("test_job", "backtest")
        await orchestrator.execute_job(job.job_id)

        result = await orchestrator.fail_job(job.job_id, "Connection timeout")
        assert result is True
        assert orchestrator.jobs[job.job_id].status == JobStatus.FAILED
        assert orchestrator.jobs[job.job_id].error_message == "Connection timeout"
        assert len(orchestrator.job_history) == 1

    @pytest.mark.asyncio
    async def test_get_job_status(self):
        """Test retrieving job status."""
        orchestrator = DagsterOrchestrator()
        job = await orchestrator.create_job("test_job", "backtest")

        status = await orchestrator.get_job_status(job.job_id)
        assert status == JobStatus.PENDING

        await orchestrator.execute_job(job.job_id)
        status = await orchestrator.get_job_status(job.job_id)
        assert status == JobStatus.RUNNING

    @pytest.mark.asyncio
    async def test_get_job_result(self):
        """Test retrieving job result."""
        orchestrator = DagsterOrchestrator()
        job = await orchestrator.create_job("test_job", "backtest")

        result = await orchestrator.get_job_result(job.job_id)
        assert result is None

        await orchestrator.execute_job(job.job_id)
        await orchestrator.complete_job(job.job_id, result={"return": "0.15"})

        result = await orchestrator.get_job_result(job.job_id)
        assert result == {"return": "0.15"}

    @pytest.mark.asyncio
    async def test_list_jobs(self):
        """Test listing jobs."""
        orchestrator = DagsterOrchestrator()
        await orchestrator.create_job("job1", "backtest")
        await orchestrator.create_job("job2", "data_fetch")

        jobs = await orchestrator.list_jobs()
        assert len(jobs) == 2

    @pytest.mark.asyncio
    async def test_list_jobs_by_status(self):
        """Test listing jobs filtered by status."""
        orchestrator = DagsterOrchestrator()
        job1 = await orchestrator.create_job("job1", "backtest")
        await orchestrator.create_job("job2", "data_fetch")

        await orchestrator.execute_job(job1.job_id)
        await orchestrator.complete_job(job1.job_id)

        running_jobs = await orchestrator.list_jobs(status=JobStatus.SUCCESS)
        assert len(running_jobs) == 1
        assert running_jobs[0].job_id == job1.job_id

    @pytest.mark.asyncio
    async def test_retry_job(self):
        """Test job retry."""
        orchestrator = DagsterOrchestrator()
        job = await orchestrator.create_job("test_job", "backtest")
        await orchestrator.execute_job(job.job_id)

        result = await orchestrator.retry_job(job.job_id)
        assert result is True
        assert orchestrator.jobs[job.job_id].run_count == 2

    @pytest.mark.asyncio
    async def test_retry_job_max_retries(self):
        """Test retry with max retries exceeded."""
        orchestrator = DagsterOrchestrator()
        job = await orchestrator.create_job("test_job", "backtest")

        # Simulate 3 runs
        for _ in range(3):
            await orchestrator.execute_job(job.job_id)

        result = await orchestrator.retry_job(job.job_id, max_retries=3)
        assert result is False


class TestDagsterScheduling:
    """Test Dagster job scheduling."""

    @pytest.mark.asyncio
    async def test_schedule_job(self):
        """Test job scheduling."""
        orchestrator = DagsterOrchestrator()
        schedule_id = await orchestrator.schedule_job("daily_backtest", "backtest", "0 0 * * *")
        assert "schedule_" in schedule_id

    @pytest.mark.asyncio
    async def test_schedule_job_various_frequencies(self):
        """Test scheduling jobs with various frequencies."""
        orchestrator = DagsterOrchestrator()

        schedules = {
            "hourly": "0 * * * *",
            "daily": "0 0 * * *",
            "weekly": "0 0 * * 0",
            "monthly": "0 0 1 * *",
        }

        for name, cron in schedules.items():
            schedule_id = await orchestrator.schedule_job(f"{name}_job", "backtest", cron)
            assert "schedule_" in schedule_id


class TestDagsterPipelineManagement:
    """Test Dagster pipeline management."""

    @pytest.mark.asyncio
    async def test_create_pipeline(self):
        """Test pipeline creation."""
        orchestrator = DagsterOrchestrator()
        steps = [
            PipelineStep("step_1", "fetch_data", "data_fetch"),
            PipelineStep("step_2", "run_backtest", "backtest"),
            PipelineStep("step_3", "analyze_results", "analysis"),
        ]

        pipeline_id = await orchestrator.create_pipeline("backtest_pipeline", steps)
        assert pipeline_id == "pipeline_0"
        assert len(orchestrator.pipelines) == 1

    @pytest.mark.asyncio
    async def test_create_pipeline_with_dependencies(self):
        """Test pipeline creation with step dependencies."""
        orchestrator = DagsterOrchestrator()
        steps = [
            PipelineStep("step_1", "fetch_data", "data_fetch"),
            PipelineStep("step_2", "run_backtest", "backtest", depends_on=["step_1"]),
            PipelineStep("step_3", "analyze", "analysis", depends_on=["step_2"]),
        ]

        pipeline_id = await orchestrator.create_pipeline("complex_pipeline", steps)
        assert len(orchestrator.pipelines[pipeline_id]) == 3

    @pytest.mark.asyncio
    async def test_execute_pipeline(self):
        """Test pipeline execution."""
        orchestrator = DagsterOrchestrator()
        steps = [
            PipelineStep("step_1", "fetch_data", "data_fetch"),
            PipelineStep("step_2", "run_backtest", "backtest"),
        ]

        pipeline_id = await orchestrator.create_pipeline("test_pipeline", steps)
        result = await orchestrator.execute_pipeline(pipeline_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_nonexistent_pipeline(self):
        """Test executing non-existent pipeline."""
        orchestrator = DagsterOrchestrator()
        result = await orchestrator.execute_pipeline("nonexistent")
        assert result is False


class TestDagsterOrchestrationStatus:
    """Test Dagster orchestration status."""

    @pytest.mark.asyncio
    async def test_get_orchestration_status(self):
        """Test orchestration status report."""
        orchestrator = DagsterOrchestrator()
        job1 = await orchestrator.create_job("job1", "backtest")
        await orchestrator.create_job("job2", "data_fetch")

        await orchestrator.execute_job(job1.job_id)
        await orchestrator.complete_job(job1.job_id)

        status = orchestrator.get_orchestration_status()
        assert status["total_jobs"] == 2
        assert status["running"] == 0
        assert status["succeeded"] == 1
        assert status["failed"] == 0

    @pytest.mark.asyncio
    async def test_orchestration_status_with_failed(self):
        """Test status report with failed jobs."""
        orchestrator = DagsterOrchestrator()
        job1 = await orchestrator.create_job("job1", "backtest")

        await orchestrator.execute_job(job1.job_id)
        await orchestrator.fail_job(job1.job_id, "Error")

        status = orchestrator.get_orchestration_status()
        assert status["failed"] == 1


# ============================================================================
# MLFLOW TRACKER TESTS (35 tests)
# ============================================================================


class TestZiplineIntegratorInitialization:
    """Test Zipline integrator initialization."""

    def test_zipline_init(self):
        """Test Zipline integrator initialization."""
        integrator = ZiplineIntegrator()
        assert len(integrator.backtests) == 0
        assert len(integrator.orders) == 0
        assert integrator.active_backtest is None

    def test_zipline_singleton_getter(self):
        """Test singleton getter for Zipline integrator."""
        from app.services.external_integrations import get_zipline_integrator

        integrator1 = get_zipline_integrator()
        integrator2 = get_zipline_integrator()
        assert integrator1 is integrator2


class TestZiplineBacktestCreation:
    """Test Zipline backtest creation."""

    @pytest.mark.asyncio
    async def test_create_backtest(self):
        """Test backtest creation."""
        integrator = ZiplineIntegrator()
        config = BacktestConfig(
            strategy_name="momentum_strategy",
            capital=Decimal("100000"),
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )

        backtest_id = await integrator.create_backtest(config)
        assert backtest_id == "bt_0"
        assert len(integrator.backtests) == 1

    @pytest.mark.asyncio
    async def test_create_backtest_with_config(self):
        """Test backtest creation with custom configuration."""
        integrator = ZiplineIntegrator()
        config = BacktestConfig(
            strategy_name="test_strategy",
            capital=Decimal("250000"),
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            commission=Decimal("0.002"),
            slippage=Decimal("0.001"),
            use_leverage=True,
            max_leverage=Decimal("2.0"),
        )

        backtest_id = await integrator.create_backtest(config)
        result = integrator.backtests[backtest_id]
        assert result.strategy_name == "test_strategy"

    @pytest.mark.asyncio
    async def test_create_multiple_backtests(self):
        """Test creating multiple backtests."""
        integrator = ZiplineIntegrator()

        for i in range(3):
            config = BacktestConfig(
                strategy_name=f"strategy_{i}",
                capital=Decimal("100000"),
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31),
            )
            await integrator.create_backtest(config)

        assert len(integrator.backtests) == 3


class TestZiplineOrderManagement:
    """Test Zipline order management."""

    @pytest.mark.asyncio
    async def test_place_order(self):
        """Test placing an order."""
        integrator = ZiplineIntegrator()
        config = BacktestConfig(
            strategy_name="test",
            capital=Decimal("100000"),
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )
        backtest_id = await integrator.create_backtest(config)

        order = await integrator.place_order(
            backtest_id,
            "AAPL",
            100,
            order_type="market",
        )

        assert order.symbol == "AAPL"
        assert order.amount == 100
        assert len(integrator.orders[backtest_id]) == 1

    @pytest.mark.asyncio
    async def test_place_limit_order(self):
        """Test placing a limit order."""
        integrator = ZiplineIntegrator()
        config = BacktestConfig(
            strategy_name="test",
            capital=Decimal("100000"),
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )
        backtest_id = await integrator.create_backtest(config)

        order = await integrator.place_order(
            backtest_id,
            "AAPL",
            100,
            order_type="limit",
            limit_price=Decimal("150.00"),
        )

        assert order.order_type == "limit"
        assert order.limit_price == Decimal("150.00")

    @pytest.mark.asyncio
    async def test_place_multiple_orders(self):
        """Test placing multiple orders."""
        integrator = ZiplineIntegrator()
        config = BacktestConfig(
            strategy_name="test",
            capital=Decimal("100000"),
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )
        backtest_id = await integrator.create_backtest(config)

        for i in range(5):
            await integrator.place_order(
                backtest_id,
                f"STOCK_{i}",
                100 * (i + 1),
            )

        assert len(integrator.orders[backtest_id]) == 5

    @pytest.mark.asyncio
    async def test_get_backtest_trades(self):
        """Test retrieving trades from backtest."""
        integrator = ZiplineIntegrator()
        config = BacktestConfig(
            strategy_name="test",
            capital=Decimal("100000"),
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )
        backtest_id = await integrator.create_backtest(config)

        for i in range(3):
            await integrator.place_order(backtest_id, f"STOCK_{i}", 100)

        trades = await integrator.get_backtest_trades(backtest_id)
        assert len(trades) == 3


class TestZiplineBacktestExecution:
    """Test Zipline backtest execution."""

    @pytest.mark.asyncio
    async def test_execute_backtest(self):
        """Test backtest execution."""
        integrator = ZiplineIntegrator()
        config = BacktestConfig(
            strategy_name="test",
            capital=Decimal("100000"),
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )
        backtest_id = await integrator.create_backtest(config)

        result = await integrator.execute_backtest(backtest_id)
        assert result.backtest_id == backtest_id
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_execute_backtest_nonexistent(self):
        """Test executing non-existent backtest."""
        integrator = ZiplineIntegrator()
        result = await integrator.execute_backtest("nonexistent")
        assert result.backtest_id == "nonexistent"
        assert result.strategy_name == "unknown"

    @pytest.mark.asyncio
    async def test_backtest_metrics(self):
        """Test backtest metrics calculation."""
        integrator = ZiplineIntegrator()
        config = BacktestConfig(
            strategy_name="test",
            capital=Decimal("100000"),
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )
        backtest_id = await integrator.create_backtest(config)
        await integrator.place_order(backtest_id, "AAPL", 100)

        result = await integrator.execute_backtest(backtest_id)
        assert result.total_return > Decimal("0")
        assert result.sharpe_ratio > Decimal("0")

    @pytest.mark.asyncio
    async def test_get_backtest_result(self):
        """Test retrieving backtest result."""
        integrator = ZiplineIntegrator()
        config = BacktestConfig(
            strategy_name="test",
            capital=Decimal("100000"),
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )
        backtest_id = await integrator.create_backtest(config)

        result = await integrator.get_backtest_result(backtest_id)
        assert result is not None
        assert result.backtest_id == backtest_id


class TestZiplineAnalysis:
    """Test Zipline analysis capabilities."""

    @pytest.mark.asyncio
    async def test_analyze_backtest(self):
        """Test backtest analysis."""
        integrator = ZiplineIntegrator()
        config = BacktestConfig(
            strategy_name="test",
            capital=Decimal("100000"),
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )
        backtest_id = await integrator.create_backtest(config)
        await integrator.place_order(backtest_id, "AAPL", 100)

        analysis = await integrator.analyze_backtest(backtest_id)
        assert "total_return" in analysis
        assert "sharpe_ratio" in analysis
        assert "max_drawdown" in analysis

    @pytest.mark.asyncio
    async def test_compare_backtests(self):
        """Test comparing backtests."""
        integrator = ZiplineIntegrator()

        backtest_ids = []
        for i in range(3):
            config = BacktestConfig(
                strategy_name=f"strategy_{i}",
                capital=Decimal("100000"),
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31),
            )
            backtest_id = await integrator.create_backtest(config)
            backtest_ids.append(backtest_id)

        compared = await integrator.compare_backtests(backtest_ids, metric="sharpe_ratio")
        assert len(compared) == 3

    @pytest.mark.asyncio
    async def test_optimize_parameters(self):
        """Test parameter optimization."""
        integrator = ZiplineIntegrator()
        param_grid = {
            "lookback_period": [20, 30, 40],
            "rebalance_frequency": ["daily", "weekly"],
        }

        result = await integrator.optimize_parameters(param_grid, lambda x: x)
        assert "best_params" in result
        assert "best_return" in result


class TestZiplineIntegrationStatus:
    """Test Zipline integration status."""

    @pytest.mark.asyncio
    async def test_get_integration_status(self):
        """Test integration status report."""
        integrator = ZiplineIntegrator()
        config = BacktestConfig(
            strategy_name="test",
            capital=Decimal("100000"),
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )
        backtest_id = await integrator.create_backtest(config)

        for i in range(3):
            await integrator.place_order(backtest_id, f"STOCK_{i}", 100)

        status = integrator.get_integration_status()
        assert status["backtests"] == 1
        assert status["orders"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
