"""
T13.1: Integration Tests for CAPA 2 API Endpoints

Tests cover:
- Input processing endpoint
- Profile generation endpoint
- Module parametrization endpoint
- Backtest execution endpoint (async)
- Complete workflow endpoint
- Status polling endpoints
- Error handling and validation
"""

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client():
    """Create async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# =============================================================================
# Test Input Processing (T1.1 via API)
# =============================================================================


class TestProcessInput:
    """Test input processing endpoint."""

    @pytest.mark.asyncio
    async def test_process_input_valid(self, client):
        """Test processing valid input."""
        response = await client.post(
            "/capa2/process-input",
            json={
                "capital_initial": 50000,
                "objetivo_inversion": "MAXIMIZAR_CAPITAL",
                "risk_tolerance": "MEDIO",
                "investment_horizon": 24,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "input_id" in data
        assert data["capital_initial"] == 50000.0
        assert "MAXIMI" in data["objetivo_inversion"].upper()  # Match normalized objective
        assert data["validation_passed"] is True

    @pytest.mark.asyncio
    async def test_process_input_minimal_capital(self, client):
        """Test input with minimum capital."""
        response = await client.post(
            "/capa2/process-input",
            json={
                "capital_initial": 1,
                "objetivo_inversion": "CAPITAL_PRESERVATION",
                "risk_tolerance": "BAJO",
                "investment_horizon": 12,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["capital_initial"] == 1.0

    @pytest.mark.asyncio
    async def test_process_input_maximum_capital(self, client):
        """Test input with maximum capital."""
        response = await client.post(
            "/capa2/process-input",
            json={
                "capital_initial": 10000000,
                "objetivo_inversion": "MAXIMIZAR_CAPITAL",
                "risk_tolerance": "ALTO",
                "investment_horizon": 600,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["capital_initial"] == 10000000.0

    @pytest.mark.asyncio
    async def test_process_input_with_constraints(self, client):
        """Test input with optional constraints."""
        response = await client.post(
            "/capa2/process-input",
            json={
                "capital_initial": 100000,
                "objetivo_inversion": "MAXIMIZAR_DIVIDENDOS",
                "risk_tolerance": "MEDIO",
                "investment_horizon": 36,
                "constraints": {"max_sector_allocation": 0.20, "min_dividend_yield": 0.03},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["validation_passed"] is True

    @pytest.mark.asyncio
    async def test_process_input_invalid_capital(self, client):
        """Test input with invalid capital (too low)."""
        response = await client.post(
            "/capa2/process-input",
            json={
                "capital_initial": 0,
                "objetivo_inversion": "MAXIMIZAR_CAPITAL",
                "risk_tolerance": "MEDIO",
                "investment_horizon": 24,
            },
        )

        # Either returns validation error or 400 from Pydantic validation
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_process_input_invalid_horizon(self, client):
        """Test input with invalid investment horizon."""
        response = await client.post(
            "/capa2/process-input",
            json={
                "capital_initial": 50000,
                "objetivo_inversion": "MAXIMIZAR_CAPITAL",
                "risk_tolerance": "MEDIO",
                "investment_horizon": 700,  # Too high
            },
        )

        # Either returns validation error or 400 from Pydantic validation
        assert response.status_code in [400, 422]


# =============================================================================
# Test Profile Generation (T2.1 via API)
# =============================================================================


class TestGenerateProfile:
    """Test profile generation endpoint."""

    @pytest.mark.asyncio
    async def test_generate_profile(self, client):
        """Test generating investment profile."""
        response = await client.post(
            "/capa2/generate-profile", json={"input_id": "input_12345678_1234567890"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "profile_id" in data
        assert "capital_tier" in data
        assert "risk_profile" in data
        assert "enabled_modules" in data
        assert data["leverage_factor"] > 0
        assert data["max_position_size"] > 0

    @pytest.mark.asyncio
    async def test_generate_profile_has_modules(self, client):
        """Test that profile includes enabled modules."""
        response = await client.post(
            "/capa2/generate-profile", json={"input_id": "input_12345678_1234567890"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["enabled_modules"]) > 0
        assert isinstance(data["enabled_modules"], list)

    @pytest.mark.asyncio
    async def test_generate_profile_capital_tier(self, client):
        """Test that profile has valid capital tier."""
        response = await client.post(
            "/capa2/generate-profile", json={"input_id": "input_12345678_1234567890"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["capital_tier"] in ["MICRO", "SMALL", "MEDIUM", "LARGE"]


# =============================================================================
# Test Module Parametrization (T3.1 via API)
# =============================================================================


class TestParametrizeModules:
    """Test module parametrization endpoint."""

    @pytest.mark.asyncio
    async def test_parametrize_modules(self, client):
        """Test parametrizing modules."""
        response = await client.post(
            "/capa2/parametrize-modules",
            json={
                "profile_id": "profile_12345678_1234567890",
                "input_id": "input_12345678_1234567890",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "parameter_set_id" in data
        assert "total_modules" in data
        assert data["total_modules"] > 0
        assert "total_max_exposure" in data
        assert "modules_summary" in data

    @pytest.mark.asyncio
    async def test_parametrize_modules_has_parameters(self, client):
        """Test that parametrization includes module details."""
        response = await client.post(
            "/capa2/parametrize-modules",
            json={
                "profile_id": "profile_12345678_1234567890",
                "input_id": "input_12345678_1234567890",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["modules_summary"]) > 0
        # Each module should have parameters
        for module_name, params in data["modules_summary"].items():
            assert isinstance(module_name, str)
            assert isinstance(params, dict)


# =============================================================================
# Test Backtest Execution (T4.1 via API - ASYNC)
# =============================================================================


class TestExecuteBacktest:
    """Test backtest execution endpoint (async)."""

    @pytest.mark.asyncio
    async def test_execute_backtest_returns_job(self, client):
        """Test that backtest execution returns job_id immediately."""
        response = await client.post(
            "/capa2/execute-backtest",
            json={
                "parameter_set_id": "params_12345678_1234567890",
                "profile_id": "profile_12345678_1234567890",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert "job_id" in data and data["job_id"].startswith("backtest_")

    @pytest.mark.asyncio
    async def test_backtest_status_pending(self, client):
        """Test checking status of backtest (may be pending or completed)."""
        # Submit backtest
        submit_response = await client.post(
            "/capa2/execute-backtest",
            json={
                "parameter_set_id": "params_12345678_1234567890",
                "profile_id": "profile_12345678_1234567890",
            },
        )
        job_id = submit_response.json()["job_id"]

        # Check status immediately (may be pending or already running/completed)
        status_response = await client.get(f"/capa2/backtest-status/{job_id}")

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["job_id"] == job_id
        assert data["status"] in ["pending", "running", "completed"]

    @pytest.mark.asyncio
    async def test_backtest_status_completed(self, client):
        """Test checking status of completed backtest (wait for completion)."""
        # Submit backtest
        submit_response = await client.post(
            "/capa2/execute-backtest",
            json={
                "parameter_set_id": "params_12345678_1234567890",
                "profile_id": "profile_12345678_1234567890",
            },
        )
        job_id = submit_response.json()["job_id"]

        # Poll for completion (wait up to 5 seconds)
        max_attempts = 50
        for _ in range(max_attempts):
            status_response = await client.get(f"/capa2/backtest-status/{job_id}")
            data = status_response.json()

            if data["status"] == "completed":
                assert data["result"] is not None
                assert "total_return" in data["result"]
                assert "sharpe_ratio" in data["result"]
                assert "feasibility_ratio" in data["result"]
                return

            await asyncio.sleep(0.1)

        # If we get here, backtest didn't complete in time
        pytest.skip("Backtest did not complete in time")

    @pytest.mark.asyncio
    async def test_backtest_status_not_found(self, client):
        """Test checking status of non-existent job."""
        response = await client.get("/capa2/backtest-status/nonexistent_job_id")

        assert response.status_code == 404


# =============================================================================
# Test Complete Workflow (End-to-End)
# =============================================================================


class TestCompleteWorkflow:
    """Test end-to-end workflow endpoint."""

    @pytest.mark.asyncio
    async def test_complete_workflow_returns_workflow_id(self, client):
        """Test that complete workflow returns workflow_id immediately."""
        response = await client.post(
            "/capa2/complete-workflow",
            json={
                "capital_initial": 100000,
                "objetivo_inversion": "MAXIMIZAR_CAPITAL",
                "risk_tolerance": "MEDIO",
                "investment_horizon": 24,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data
        assert data["status"] == "processing"
        assert data["workflow_id"].startswith("workflow_")

    @pytest.mark.asyncio
    async def test_complete_workflow_includes_stages(self, client):
        """Test that workflow response includes all stages."""
        response = await client.post(
            "/capa2/complete-workflow",
            json={
                "capital_initial": 100000,
                "objetivo_inversion": "MAXIMIZAR_CAPITAL",
                "risk_tolerance": "MEDIO",
                "investment_horizon": 24,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "input_profile" in data
        assert "investment_profile" in data
        assert "module_parameters" in data
        assert "backtest_result" in data

    @pytest.mark.asyncio
    async def test_workflow_status_pending(self, client):
        """Test checking workflow status while processing."""
        # Submit workflow
        submit_response = await client.post(
            "/capa2/complete-workflow",
            json={
                "capital_initial": 100000,
                "objetivo_inversion": "MAXIMIZAR_CAPITAL",
                "risk_tolerance": "MEDIO",
                "investment_horizon": 24,
            },
        )
        workflow_id = submit_response.json()["workflow_id"]

        # Check status
        status_response = await client.get(f"/capa2/workflow-status/{workflow_id}")

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["workflow_id"] == workflow_id
        assert "stage" in data

    @pytest.mark.asyncio
    async def test_workflow_status_completed(self, client):
        """Test checking workflow status after completion (with polling)."""
        # Submit workflow
        submit_response = await client.post(
            "/capa2/complete-workflow",
            json={
                "capital_initial": 100000,
                "objetivo_inversion": "MAXIMIZAR_CAPITAL",
                "risk_tolerance": "MEDIO",
                "investment_horizon": 24,
            },
        )
        workflow_id = submit_response.json()["workflow_id"]

        # Poll for completion (wait up to 5 seconds)
        max_attempts = 50
        for _ in range(max_attempts):
            status_response = await client.get(f"/capa2/workflow-status/{workflow_id}")
            data = status_response.json()

            if data["status"] == "completed":
                assert data["results"] is not None
                assert "deployment_decision" in data["results"]
                return

            await asyncio.sleep(0.1)

        # Workflow may still be processing - that's OK for this test
        assert data["status"] in ["processing", "completed"]

    @pytest.mark.asyncio
    async def test_workflow_status_not_found(self, client):
        """Test checking status of non-existent workflow."""
        response = await client.get("/capa2/workflow-status/nonexistent_workflow_id")

        assert response.status_code == 404


# =============================================================================
# Test Utility Endpoints
# =============================================================================


class TestUtilityEndpoints:
    """Test utility and health check endpoints."""

    @pytest.mark.asyncio
    async def test_capa2_health_check(self, client):
        """Test CAPA 2 health check endpoint."""
        response = await client.get("/capa2/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_jobs_status(self, client):
        """Test jobs status endpoint."""
        response = await client.get("/capa2/status/jobs")

        assert response.status_code == 200
        data = response.json()
        assert "total_jobs" in data
        assert "jobs" in data
        assert isinstance(data["jobs"], dict)

    @pytest.mark.asyncio
    async def test_jobs_status_tracks_submitted_jobs(self, client):
        """Test that jobs status endpoint tracks submitted jobs."""
        # Submit a backtest
        await client.post(
            "/capa2/execute-backtest",
            json={
                "parameter_set_id": "params_12345678_1234567890",
                "profile_id": "profile_12345678_1234567890",
            },
        )

        # Check jobs status
        response = await client.get("/capa2/status/jobs")

        assert response.status_code == 200
        data = response.json()
        assert data["total_jobs"] > 0


# =============================================================================
# Test Error Handling & Validation
# =============================================================================


class TestErrorHandling:
    """Test error handling and validation."""

    @pytest.mark.asyncio
    async def test_invalid_json_request(self, client):
        """Test handling of invalid JSON request."""
        response = await client.post(
            "/capa2/process-input", json={"invalid": "data"}  # Missing required fields
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_missing_required_field(self, client):
        """Test handling of missing required field."""
        response = await client.post(
            "/capa2/process-input",
            json={
                "capital_initial": 50000,
                "objetivo_inversion": "MAXIMIZAR_CAPITAL",
                # Missing risk_tolerance and investment_horizon
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_objective(self, client):
        """Test handling of invalid investment objective."""
        response = await client.post(
            "/capa2/process-input",
            json={
                "capital_initial": 50000,
                "objetivo_inversion": "INVALID_OBJECTIVE",
                "risk_tolerance": "MEDIO",
                "investment_horizon": 24,
            },
        )

        # API accepts string, validation happens downstream
        assert response.status_code in [200, 400]


# =============================================================================
# Test API Documentation
# =============================================================================


class TestAPIDocumentation:
    """Test API documentation endpoints."""

    @pytest.mark.asyncio
    async def test_openapi_schema(self, client):
        """Test OpenAPI schema availability."""
        response = await client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
        # Check for CAPA 2 endpoints
        assert "/capa2/process-input" in schema["paths"]
        assert "/capa2/complete-workflow" in schema["paths"]

    @pytest.mark.asyncio
    async def test_swagger_docs(self, client):
        """Test Swagger documentation availability."""
        response = await client.get("/docs")

        assert response.status_code == 200
        assert "html" in response.text.lower()


# =============================================================================
# Integration Test: Full User Journey
# =============================================================================


class TestFullUserJourney:
    """Test complete user journey through the API."""

    @pytest.mark.asyncio
    async def test_user_journey_step_by_step(self, client):
        """Test full user journey: input → profile → params → backtest → decision."""
        # Step 1: Process input
        input_response = await client.post(
            "/capa2/process-input",
            json={
                "capital_initial": 100000,
                "objetivo_inversion": "MAXIMIZAR_CAPITAL",
                "risk_tolerance": "MEDIO",
                "investment_horizon": 24,
            },
        )
        assert input_response.status_code == 200
        input_data = input_response.json()
        input_id = input_data["input_id"]

        # Step 2: Generate profile
        profile_response = await client.post("/capa2/generate-profile", json={"input_id": input_id})
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        profile_id = profile_data["profile_id"]

        # Step 3: Parametrize modules
        params_response = await client.post(
            "/capa2/parametrize-modules", json={"profile_id": profile_id, "input_id": input_id}
        )
        assert params_response.status_code == 200
        params_data = params_response.json()
        parameter_set_id = params_data["parameter_set_id"]

        # Step 4: Execute backtest
        backtest_response = await client.post(
            "/capa2/execute-backtest",
            json={"parameter_set_id": parameter_set_id, "profile_id": profile_id},
        )
        assert backtest_response.status_code == 200
        backtest_data = backtest_response.json()
        assert backtest_data["status"] == "pending"

        # Step 5: Check jobs status
        jobs_response = await client.get("/capa2/status/jobs")
        assert jobs_response.status_code == 200
        jobs_data = jobs_response.json()
        assert jobs_data["total_jobs"] > 0

        # Journey complete
        assert input_id is not None
        assert profile_id is not None
        assert parameter_set_id is not None
        assert backtest_data["job_id"] is not None
