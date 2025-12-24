"""
T11.1: Unit Tests for ConfigurationPersistence

Tests cover:
- Save/load configurations
- Different configuration types
- Metadata handling
- Error handling
- Storage statistics
"""

from decimal import Decimal
from datetime import datetime

import pytest

from app.services.configuration_persistence import ConfigurationRepository


@pytest.fixture
def repository():
    """Create ConfigurationRepository instance."""
    return ConfigurationRepository()


@pytest.fixture
def sample_investment_profile_dict():
    """Sample investment profile data."""
    return {
        "profile_id": "test_profile_001",
        "capital_initial": "50000",
        "capital_tier": "small",
        "objetivo_inversion": "maximizar_capital",
        "risk_profile": 3,
        "enabled_modules": ["momentum_modular", "mean_reversion_modular"],
    }


@pytest.fixture
def sample_backtest_config_dict():
    """Sample backtest configuration."""
    return {
        "strategy_name": "test_strategy",
        "initial_capital": "50000",
        "commission_per_trade": "10.0",
        "slippage_percentage": "0.1",
        "max_position_size": "0.10",
    }


@pytest.fixture
def sample_backtest_result_dict():
    """Sample backtest result."""
    return {
        "strategy_name": "test_strategy",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "final_capital": "62500",
        "total_return": "25.0",
        "annualized_return": "25.0",
        "feasibility_ratio": "1.30",
        "viability_status": "APPROVED",
    }


@pytest.fixture
def sample_validation_report_dict():
    """Sample validation report."""
    return {
        "overall_status": "APPROVED",
        "passed_gates": 6,
        "total_gates": 6,
        "critical_failures": [],
        "warnings": [],
    }


@pytest.fixture
def sample_deployment_decision_dict():
    """Sample deployment decision."""
    return {
        "status": "APPROVED",
        "feasibility_ratio": "1.30",
        "confidence_level": "HIGH",
        "reasons": ["All gates passed", "Strong feasibility"],
    }


class TestSaveInvestmentProfile:
    """Test saving investment profiles."""

    @pytest.mark.asyncio
    async def test_save_investment_profile(self, repository, sample_investment_profile_dict):
        """Test saving investment profile."""
        profile_id = await repository.save_investment_profile(
            profile_id="test_profile_001",
            profile_data=sample_investment_profile_dict,
        )

        assert profile_id == "test_profile_001"

    @pytest.mark.asyncio
    async def test_save_profile_with_metadata(
        self, repository, sample_investment_profile_dict
    ):
        """Test saving profile with metadata."""
        metadata = {"user_id": "user_123", "session_id": "session_456"}

        profile_id = await repository.save_investment_profile(
            profile_id="test_profile_002",
            profile_data=sample_investment_profile_dict,
            metadata=metadata,
        )

        assert profile_id == "test_profile_002"
        config = await repository.load_configuration("test_profile_002")
        assert config.metadata == metadata


class TestSaveBacktestConfig:
    """Test saving backtest configurations."""

    @pytest.mark.asyncio
    async def test_save_backtest_config(self, repository, sample_backtest_config_dict):
        """Test saving backtest config."""
        config_id = await repository.save_backtest_config(
            config_id="backtest_config_001",
            config_data=sample_backtest_config_dict,
        )

        assert config_id == "backtest_config_001"

    @pytest.mark.asyncio
    async def test_save_multiple_configs(self, repository, sample_backtest_config_dict):
        """Test saving multiple configs."""
        ids = []
        for i in range(3):
            config_id = await repository.save_backtest_config(
                config_id=f"backtest_config_{i:03d}",
                config_data={**sample_backtest_config_dict, "initial_capital": str(50000 * (i + 1))},
            )
            ids.append(config_id)

        assert len(ids) == 3
        assert ids[0] == "backtest_config_000"


class TestSaveBacktestResult:
    """Test saving backtest results."""

    @pytest.mark.asyncio
    async def test_save_backtest_result(self, repository, sample_backtest_result_dict):
        """Test saving backtest result."""
        result_id = await repository.save_backtest_result(
            result_id="backtest_result_001",
            result_data=sample_backtest_result_dict,
        )

        assert result_id == "backtest_result_001"


class TestSaveValidationReport:
    """Test saving validation reports."""

    @pytest.mark.asyncio
    async def test_save_validation_report(self, repository, sample_validation_report_dict):
        """Test saving validation report."""
        report_id = await repository.save_validation_report(
            report_id="validation_report_001",
            report_data=sample_validation_report_dict,
        )

        assert report_id == "validation_report_001"


class TestSaveDeploymentDecision:
    """Test saving deployment decisions."""

    @pytest.mark.asyncio
    async def test_save_deployment_decision(
        self, repository, sample_deployment_decision_dict
    ):
        """Test saving deployment decision."""
        decision_id = await repository.save_deployment_decision(
            decision_id="deployment_decision_001",
            decision_data=sample_deployment_decision_dict,
        )

        assert decision_id == "deployment_decision_001"


class TestLoadConfiguration:
    """Test loading configurations."""

    @pytest.mark.asyncio
    async def test_load_saved_config(self, repository, sample_investment_profile_dict):
        """Test loading previously saved config."""
        profile_id = "test_profile_003"
        await repository.save_investment_profile(
            profile_id=profile_id,
            profile_data=sample_investment_profile_dict,
        )

        loaded = await repository.load_configuration(profile_id)
        assert loaded is not None
        assert loaded.config_id == profile_id
        assert loaded.config_type == "investment_profile"
        assert loaded.data == sample_investment_profile_dict

    @pytest.mark.asyncio
    async def test_load_nonexistent_config(self, repository):
        """Test loading nonexistent configuration."""
        loaded = await repository.load_configuration("nonexistent_123")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_load_has_timestamps(self, repository, sample_investment_profile_dict):
        """Test loaded config has timestamps."""
        profile_id = "test_profile_004"
        await repository.save_investment_profile(
            profile_id=profile_id,
            profile_data=sample_investment_profile_dict,
        )

        loaded = await repository.load_configuration(profile_id)
        assert loaded.created_at is not None
        assert loaded.updated_at is not None


class TestLoadByType:
    """Test loading configurations by type."""

    @pytest.mark.asyncio
    async def test_load_by_type_investment_profile(
        self, repository, sample_investment_profile_dict
    ):
        """Test loading all investment profiles."""
        for i in range(2):
            await repository.save_investment_profile(
                profile_id=f"profile_{i}",
                profile_data=sample_investment_profile_dict,
            )

        profiles = await repository.load_by_type("investment_profile")
        assert len(profiles) == 2

    @pytest.mark.asyncio
    async def test_load_by_type_mixed(
        self,
        repository,
        sample_investment_profile_dict,
        sample_backtest_config_dict,
    ):
        """Test loading specific type from mixed storage."""
        await repository.save_investment_profile(
            profile_id="profile_001",
            profile_data=sample_investment_profile_dict,
        )
        await repository.save_backtest_config(
            config_id="config_001",
            config_data=sample_backtest_config_dict,
        )

        profiles = await repository.load_by_type("investment_profile")
        assert len(profiles) == 1
        assert profiles[0].config_type == "investment_profile"


class TestListAll:
    """Test listing all configurations."""

    @pytest.mark.asyncio
    async def test_list_all_empty(self, repository):
        """Test listing from empty repository."""
        all_configs = await repository.list_all()
        assert len(all_configs) == 0

    @pytest.mark.asyncio
    async def test_list_all_multiple(
        self,
        repository,
        sample_investment_profile_dict,
        sample_backtest_config_dict,
    ):
        """Test listing multiple configs."""
        await repository.save_investment_profile(
            profile_id="profile_001",
            profile_data=sample_investment_profile_dict,
        )
        await repository.save_backtest_config(
            config_id="config_001",
            config_data=sample_backtest_config_dict,
        )

        all_configs = await repository.list_all()
        assert len(all_configs) == 2


class TestDeleteConfiguration:
    """Test deleting configurations."""

    @pytest.mark.asyncio
    async def test_delete_existing_config(
        self, repository, sample_investment_profile_dict
    ):
        """Test deleting existing configuration."""
        profile_id = "profile_to_delete"
        await repository.save_investment_profile(
            profile_id=profile_id,
            profile_data=sample_investment_profile_dict,
        )

        deleted = await repository.delete_configuration(profile_id)
        assert deleted is True

        loaded = await repository.load_configuration(profile_id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_config(self, repository):
        """Test deleting nonexistent configuration."""
        deleted = await repository.delete_configuration("nonexistent_123")
        assert deleted is False


class TestStorageStats:
    """Test storage statistics."""

    @pytest.mark.asyncio
    async def test_storage_stats_empty(self, repository):
        """Test stats for empty repository."""
        stats = repository.get_storage_stats()
        assert stats["total_configs"] == 0

    @pytest.mark.asyncio
    async def test_storage_stats_multiple_types(
        self,
        repository,
        sample_investment_profile_dict,
        sample_backtest_config_dict,
        sample_backtest_result_dict,
    ):
        """Test stats with multiple configuration types."""
        await repository.save_investment_profile(
            profile_id="profile_001",
            profile_data=sample_investment_profile_dict,
        )
        await repository.save_backtest_config(
            config_id="config_001",
            config_data=sample_backtest_config_dict,
        )
        await repository.save_backtest_result(
            result_id="result_001",
            result_data=sample_backtest_result_dict,
        )

        stats = repository.get_storage_stats()
        assert stats["total_configs"] == 3
        assert stats["by_type"]["investment_profile"] == 1
        assert stats["by_type"]["backtest_config"] == 1
        assert stats["by_type"]["backtest_result"] == 1


class TestUpdateConfiguration:
    """Test updating configurations."""

    @pytest.mark.asyncio
    async def test_update_preserves_created_at(
        self, repository, sample_investment_profile_dict
    ):
        """Test update preserves created_at timestamp."""
        profile_id = "profile_update"
        await repository.save_investment_profile(
            profile_id=profile_id,
            profile_data=sample_investment_profile_dict,
        )

        first_load = await repository.load_configuration(profile_id)
        created_at_1 = first_load.created_at

        # Update the configuration
        updated_data = {**sample_investment_profile_dict, "risk_profile": 4}
        await repository.save_investment_profile(
            profile_id=profile_id,
            profile_data=updated_data,
        )

        second_load = await repository.load_configuration(profile_id)
        assert second_load.created_at == created_at_1
        assert second_load.updated_at >= first_load.updated_at
        assert second_load.data["risk_profile"] == 4


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_load_from_empty_storage(self, repository):
        """Test loading from empty storage doesn't raise error."""
        result = await repository.load_configuration("any_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_from_empty_storage(self, repository):
        """Test deleting from empty storage doesn't raise error."""
        result = await repository.delete_configuration("any_id")
        assert result is False
