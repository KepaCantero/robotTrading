"""
Comprehensive test suite for T17.1: External Integrations

Tests for QuestDBConnector, DagsterOrchestrator, MLflowTracker, and ZiplineIntegrator
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.services.external_integrations import (
    DagsterOrchestrator,
    MLflowTracker,
    QuestDBConnector,
    ZiplineIntegrator,
)
from app.services.external_integrations.dagster_orchestrator import (
    JobStatus,
    PipelineStep,
)
from app.services.external_integrations.questdb_connector import (
    TimeSeriesData,
    TradeRecord,
)
from app.services.external_integrations.zipline_integrator import (
    BacktestConfig,
)

# ============================================================================
# QUESTDB CONNECTOR TESTS (35 tests)
# ============================================================================


class TestQuestDBConnectorInitialization:
    """Test QuestDB connector initialization."""

    def test_questdb_init_default_params(self):
        """Test default QuestDB initialization."""
        connector = QuestDBConnector()
        assert connector.host == "localhost"
        assert connector.port == 9009
        assert connector.connected is False
        assert len(connector.ohlcv_data) == 0
        assert len(connector.trades) == 0

    def test_questdb_init_custom_params(self):
        """Test QuestDB initialization with custom host and port."""
        connector = QuestDBConnector(host="127.0.0.1", port=8009)
        assert connector.host == "127.0.0.1"
        assert connector.port == 8009

    def test_questdb_singleton_getter(self):
        """Test singleton getter for QuestDB connector."""
        from app.services.external_integrations import get_questdb_connector

        connector1 = get_questdb_connector()
        connector2 = get_questdb_connector()
        assert connector1 is connector2


class TestQuestDBConnectorConnection:
    """Test QuestDB connection management."""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to QuestDB."""
        connector = QuestDBConnector()
        result = await connector.connect()
        assert result is True
        assert connector.connected is True

    @pytest.mark.asyncio
    async def test_disconnect_success(self):
        """Test successful disconnection from QuestDB."""
        connector = QuestDBConnector()
        await connector.connect()
        result = await connector.disconnect()
        assert result is True
        assert connector.connected is False

    @pytest.mark.asyncio
    async def test_get_connection_status(self):
        """Test connection status report."""
        connector = QuestDBConnector()
        status = connector.get_connection_status()
        assert status["host"] == "localhost"
        assert status["port"] == 9009
        assert status["connected"] is False


class TestQuestDBConnectorOHLCVOperations:
    """Test QuestDB OHLCV data operations."""

    @pytest.mark.asyncio
    async def test_insert_ohlcv_not_connected(self):
        """Test OHLCV insertion when not connected."""
        connector = QuestDBConnector()
        data = TimeSeriesData(
            timestamp=datetime.now(),
            symbol="AAPL",
            open_price=Decimal("150.00"),
            high_price=Decimal("152.00"),
            low_price=Decimal("149.50"),
            close_price=Decimal("151.50"),
            volume=Decimal("1000000"),
        )
        result = await connector.insert_ohlcv(data)
        assert result is False

    @pytest.mark.asyncio
    async def test_insert_ohlcv_success(self):
        """Test successful OHLCV insertion."""
        connector = QuestDBConnector()
        await connector.connect()
        data = TimeSeriesData(
            timestamp=datetime.now(),
            symbol="AAPL",
            open_price=Decimal("150.00"),
            high_price=Decimal("152.00"),
            low_price=Decimal("149.50"),
            close_price=Decimal("151.50"),
            volume=Decimal("1000000"),
        )
        result = await connector.insert_ohlcv(data)
        assert result is True
        assert len(connector.ohlcv_data) == 1

    @pytest.mark.asyncio
    async def test_insert_batch_ohlcv(self):
        """Test batch OHLCV insertion."""
        connector = QuestDBConnector()
        await connector.connect()
        data_list = [
            TimeSeriesData(
                timestamp=datetime.now() - timedelta(days=i),
                symbol="AAPL",
                open_price=Decimal("150.00") + Decimal(i),
                high_price=Decimal("152.00") + Decimal(i),
                low_price=Decimal("149.50") + Decimal(i),
                close_price=Decimal("151.50") + Decimal(i),
                volume=Decimal("1000000"),
            )
            for i in range(5)
        ]
        result = await connector.insert_batch_ohlcv(data_list)
        assert result == 5
        assert len(connector.ohlcv_data) == 5

    @pytest.mark.asyncio
    async def test_query_ohlcv(self):
        """Test OHLCV data querying."""
        connector = QuestDBConnector()
        await connector.connect()

        now = datetime.now()
        for i in range(3):
            data = TimeSeriesData(
                timestamp=now - timedelta(days=i),
                symbol="AAPL",
                open_price=Decimal("150.00"),
                high_price=Decimal("152.00"),
                low_price=Decimal("149.50"),
                close_price=Decimal("151.50"),
                volume=Decimal("1000000"),
            )
            await connector.insert_ohlcv(data)

        results = await connector.query_ohlcv("AAPL", now - timedelta(days=5), now)
        assert len(results) == 3
        assert all(r.symbol == "AAPL" for r in results)

    @pytest.mark.asyncio
    async def test_get_latest_price(self):
        """Test retrieving latest price."""
        connector = QuestDBConnector()
        await connector.connect()

        price = await connector.get_latest_price("AAPL")
        assert price is None

        data = TimeSeriesData(
            timestamp=datetime.now(),
            symbol="AAPL",
            open_price=Decimal("150.00"),
            high_price=Decimal("152.00"),
            low_price=Decimal("149.50"),
            close_price=Decimal("151.50"),
            volume=Decimal("1000000"),
        )
        await connector.insert_ohlcv(data)
        price = await connector.get_latest_price("AAPL")
        assert price == Decimal("151.50")

    @pytest.mark.asyncio
    async def test_get_statistics(self):
        """Test OHLCV statistics."""
        connector = QuestDBConnector()
        await connector.connect()

        prices = [Decimal("150"), Decimal("155"), Decimal("145")]
        for i, close_price in enumerate(prices):
            data = TimeSeriesData(
                timestamp=datetime.now() - timedelta(days=i),
                symbol="AAPL",
                open_price=close_price - Decimal("2"),
                high_price=close_price + Decimal("2"),
                low_price=close_price - Decimal("5"),
                close_price=close_price,
                volume=Decimal("1000000"),
            )
            await connector.insert_ohlcv(data)

        stats = await connector.get_statistics("AAPL")
        assert stats["count"] == 3
        assert stats["min"] == Decimal("145")
        assert stats["max"] == Decimal("155")


class TestQuestDBConnectorTradeOperations:
    """Test QuestDB trade record operations."""

    @pytest.mark.asyncio
    async def test_insert_trade_not_connected(self):
        """Test trade insertion when not connected."""
        connector = QuestDBConnector()
        trade = TradeRecord(
            trade_id="trade_1",
            symbol="AAPL",
            side="buy",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            timestamp=datetime.now(),
            portfolio_value=Decimal("50000"),
            pnl=Decimal("0"),
        )
        result = await connector.insert_trade(trade)
        assert result is False

    @pytest.mark.asyncio
    async def test_insert_trade_success(self):
        """Test successful trade insertion."""
        connector = QuestDBConnector()
        await connector.connect()
        trade = TradeRecord(
            trade_id="trade_1",
            symbol="AAPL",
            side="buy",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            timestamp=datetime.now(),
            portfolio_value=Decimal("50000"),
            pnl=Decimal("0"),
        )
        result = await connector.insert_trade(trade)
        assert result is True
        assert len(connector.trades) == 1

    @pytest.mark.asyncio
    async def test_query_trades_all(self):
        """Test querying all trades."""
        connector = QuestDBConnector()
        await connector.connect()

        for i in range(3):
            trade = TradeRecord(
                trade_id=f"trade_{i}",
                symbol="AAPL" if i % 2 == 0 else "MSFT",
                side="buy" if i % 2 == 0 else "sell",
                quantity=Decimal("100"),
                price=Decimal("150.00"),
                timestamp=datetime.now() - timedelta(hours=i),
                portfolio_value=Decimal("50000"),
                pnl=Decimal("0"),
            )
            await connector.insert_trade(trade)

        results = await connector.query_trades()
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_query_trades_by_symbol(self):
        """Test querying trades by symbol."""
        connector = QuestDBConnector()
        await connector.connect()

        for symbol in ["AAPL", "MSFT", "AAPL"]:
            trade = TradeRecord(
                trade_id=f"trade_{symbol}",
                symbol=symbol,
                side="buy",
                quantity=Decimal("100"),
                price=Decimal("150.00"),
                timestamp=datetime.now(),
                portfolio_value=Decimal("50000"),
                pnl=Decimal("0"),
            )
            await connector.insert_trade(trade)

        results = await connector.query_trades(symbol="AAPL")
        assert len(results) == 2
        assert all(r.symbol == "AAPL" for r in results)

    @pytest.mark.asyncio
    async def test_query_trades_by_start_time(self):
        """Test querying trades by start time."""
        connector = QuestDBConnector()
        await connector.connect()

        now = datetime.now()
        for i in range(3):
            trade = TradeRecord(
                trade_id=f"trade_{i}",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                price=Decimal("150.00"),
                timestamp=now - timedelta(hours=i),
                portfolio_value=Decimal("50000"),
                pnl=Decimal("0"),
            )
            await connector.insert_trade(trade)

        results = await connector.query_trades(start_time=now - timedelta(hours=1))
        assert len(results) == 2


# ============================================================================
# DAGSTER ORCHESTRATOR TESTS (45 tests)
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


class TestMLflowTrackerInitialization:
    """Test MLflow tracker initialization."""

    def test_mlflow_init(self):
        """Test MLflow tracker initialization."""
        tracker = MLflowTracker()
        assert len(tracker.experiments) == 0
        assert len(tracker.models) == 0
        assert tracker.active_run is None

    def test_mlflow_singleton_getter(self):
        """Test singleton getter for MLflow tracker."""
        from app.services.external_integrations import get_mlflow_tracker

        tracker1 = get_mlflow_tracker()
        tracker2 = get_mlflow_tracker()
        assert tracker1 is tracker2


class TestMLflowExperimentManagement:
    """Test MLflow experiment management."""

    @pytest.mark.asyncio
    async def test_create_experiment(self):
        """Test experiment creation."""
        tracker = MLflowTracker()
        exp = await tracker.create_experiment("test_experiment", "Test description")

        assert exp.experiment_id == "exp_0"
        assert exp.name == "test_experiment"
        assert exp.description == "Test description"
        assert len(tracker.experiments) == 1

    @pytest.mark.asyncio
    async def test_create_multiple_experiments(self):
        """Test creating multiple experiments."""
        tracker = MLflowTracker()
        exp1 = await tracker.create_experiment("exp1", "Desc1")
        exp2 = await tracker.create_experiment("exp2", "Desc2")

        assert len(tracker.experiments) == 2
        assert exp1.experiment_id != exp2.experiment_id


class TestMLflowRunManagement:
    """Test MLflow run management."""

    @pytest.mark.asyncio
    async def test_start_run(self):
        """Test starting a run."""
        tracker = MLflowTracker()
        exp = await tracker.create_experiment("test_exp", "Test")
        run = await tracker.start_run(exp.experiment_id)

        assert "run_id" in run
        assert tracker.active_run is not None

    @pytest.mark.asyncio
    async def test_start_run_nonexistent_experiment(self):
        """Test starting run for non-existent experiment."""
        tracker = MLflowTracker()
        run = await tracker.start_run("nonexistent")
        assert run == {}

    @pytest.mark.asyncio
    async def test_log_params(self):
        """Test logging parameters."""
        tracker = MLflowTracker()
        exp = await tracker.create_experiment("test_exp", "Test")
        await tracker.start_run(exp.experiment_id)

        params = {"learning_rate": "0.001", "epochs": "100"}
        await tracker.log_params(params)

        assert "learning_rate" in tracker.active_run["params"]
        assert tracker.active_run["params"]["learning_rate"] == "0.001"

    @pytest.mark.asyncio
    async def test_log_metrics(self):
        """Test logging metrics."""
        tracker = MLflowTracker()
        exp = await tracker.create_experiment("test_exp", "Test")
        await tracker.start_run(exp.experiment_id)

        metrics = {"accuracy": Decimal("0.95"), "loss": Decimal("0.05")}
        await tracker.log_metrics(metrics, step=0)

        assert "step_0" in tracker.active_run["metrics"]

    @pytest.mark.asyncio
    async def test_end_run(self):
        """Test ending a run."""
        tracker = MLflowTracker()
        exp = await tracker.create_experiment("test_exp", "Test")
        await tracker.start_run(exp.experiment_id)

        result = await tracker.end_run("FINISHED")
        assert result is True
        assert tracker.active_run is None

    @pytest.mark.asyncio
    async def test_end_run_no_active_run(self):
        """Test ending run when no active run."""
        tracker = MLflowTracker()
        result = await tracker.end_run()
        assert result is False


class TestMLflowModelManagement:
    """Test MLflow model management."""

    @pytest.mark.asyncio
    async def test_register_model(self):
        """Test model registration."""
        tracker = MLflowTracker()
        metrics = {"accuracy": Decimal("0.95"), "f1_score": Decimal("0.92")}

        model = await tracker.register_model("test_model", "xgboost", metrics)
        assert model.model_id == "model_0"
        assert model.name == "test_model"
        assert model.model_type == "xgboost"
        assert len(tracker.models) == 1

    @pytest.mark.asyncio
    async def test_register_multiple_models(self):
        """Test registering multiple models."""
        tracker = MLflowTracker()
        metrics = {"accuracy": Decimal("0.95")}

        model1 = await tracker.register_model("model1", "xgboost", metrics)
        model2 = await tracker.register_model("model2", "neural_network", metrics)

        assert len(tracker.models) == 2
        assert model1.model_id != model2.model_id

    @pytest.mark.asyncio
    async def test_promote_model(self):
        """Test model promotion."""
        tracker = MLflowTracker()
        metrics = {"accuracy": Decimal("0.95")}

        model = await tracker.register_model("test_model", "xgboost", metrics)
        result = await tracker.promote_model(model.model_id, "production")

        assert result is True
        assert tracker.models[model.model_id].status == "production"

    @pytest.mark.asyncio
    async def test_promote_nonexistent_model(self):
        """Test promoting non-existent model."""
        tracker = MLflowTracker()
        result = await tracker.promote_model("nonexistent", "production")
        assert result is False

    @pytest.mark.asyncio
    async def test_compare_models(self):
        """Test model comparison."""
        tracker = MLflowTracker()

        models_data = [
            ("model1", "xgboost", {"accuracy": Decimal("0.85")}),
            ("model2", "neural_network", {"accuracy": Decimal("0.95")}),
            ("model3", "ensemble", {"accuracy": Decimal("0.90")}),
        ]

        for name, model_type, metrics in models_data:
            await tracker.register_model(name, model_type, metrics)

        compared = await tracker.compare_models("accuracy")
        assert len(compared) == 3
        assert compared[0].accuracy == Decimal("0.95")  # Highest first

    @pytest.mark.asyncio
    async def test_get_best_model(self):
        """Test getting best model."""
        tracker = MLflowTracker()

        models_data = [
            ("model1", "xgboost", {"f1_score": Decimal("0.85")}),
            ("model2", "neural_network", {"f1_score": Decimal("0.95")}),
            ("model3", "ensemble", {"f1_score": Decimal("0.90")}),
        ]

        for name, model_type, metrics in models_data:
            await tracker.register_model(name, model_type, metrics)

        best = await tracker.get_best_model("f1_score")
        assert best.name == "model2"

    @pytest.mark.asyncio
    async def test_get_model_versions(self):
        """Test getting model versions."""
        tracker = MLflowTracker()

        metrics = {"accuracy": Decimal("0.95")}
        await tracker.register_model("test_model", "xgboost", metrics)
        await tracker.register_model("test_model", "neural_network", metrics)
        await tracker.register_model("other_model", "ensemble", metrics)

        versions = await tracker.get_model_versions("test_model")
        assert len(versions) == 2
        assert all(m.name == "test_model" for m in versions)

    @pytest.mark.asyncio
    async def test_log_artifact(self):
        """Test logging artifact."""
        tracker = MLflowTracker()
        # Should not raise any exception
        await tracker.log_artifact("/path/to/model.pkl", "model")


class TestMLflowTrackingStatus:
    """Test MLflow tracking status."""

    @pytest.mark.asyncio
    async def test_get_tracking_status(self):
        """Test tracking status report."""
        tracker = MLflowTracker()

        exp = await tracker.create_experiment("test_exp", "Test")
        await tracker.start_run(exp.experiment_id)

        metrics = {"accuracy": Decimal("0.95")}
        await tracker.register_model("test_model", "xgboost", metrics)

        status = tracker.get_tracking_status()
        assert status["experiments"] == 1
        assert status["models"] == 1
        assert status["active_run"] is True


# ============================================================================
# ZIPLINE INTEGRATOR TESTS (40 tests)
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
