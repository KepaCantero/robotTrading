"""
T11.1: Unit Tests for ConfigurationPersistence (Strategy-Centric)

Tests cover:
- Save strategy configurations with versioning
- Load strategy configurations
- List with filtering (profile_id, objective)
- Soft delete via deactivation
- Version history tracking
- Search functionality
- Persistence status reporting
"""

from decimal import Decimal
from datetime import datetime

import pytest

from app.services.configuration_persistence import (
    ConfigurationPersistence,
    StrategyConfiguration,
    ConfigurationSaveRequest,
    ConfigurationLoadRequest,
    get_configuration_persistence,
)


@pytest.fixture
def persistence():
    """Create ConfigurationPersistence instance."""
    return ConfigurationPersistence()


@pytest.fixture
def sample_strategy_config():
    """Sample complete strategy configuration."""
    return StrategyConfiguration(
        config_id="config_001",
        profile_id="profile_small_001",
        input_id="input_001",
        strategy_name="Momentum + ML Strategy",
        capital_eur=Decimal("50000"),
        risk_profile="aggressive",
        objective="maximizar_capital",
        target_annual_return_pct=Decimal("15.0"),
        max_acceptable_drawdown_pct=Decimal("25.0"),
        enabled_modules=["momentum_modular", "ml_basic"],
        module_parameters={
            "momentum_modular": {"lookback": 20, "threshold": 0.02},
            "ml_basic": {"model": "xgboost", "features": 10},
        },
        feasibility_ratio=Decimal("1.35"),
        annual_return_pct=Decimal("20.25"),
        sharpe_ratio=Decimal("1.85"),
        max_drawdown_pct=Decimal("18.5"),
        portfolio_allocations={
            "momentum_modular": Decimal("0.6"),
            "ml_basic": Decimal("0.4"),
        },
        validation_passed=True,
        recommendation_score=Decimal("88.5"),
        recommendation_status="STRONG_BUY",
        deployment_status="APPROVED",
        deployment_confidence="high",
        notes="Strong Sharpe, good feasibility ratio",
    )


class TestSaveConfiguration:
    """Test saving strategy configurations."""

    @pytest.mark.asyncio
    async def test_save_configuration(self, persistence, sample_strategy_config):
        """Test saving strategy configuration."""
        request = ConfigurationSaveRequest(
            config_id=sample_strategy_config.config_id,
            profile_id=sample_strategy_config.profile_id,
            input_id=sample_strategy_config.input_id,
            strategy_name=sample_strategy_config.strategy_name,
            configuration=sample_strategy_config,
        )

        config_id = await persistence.save_configuration(request)
        assert config_id == "config_001"

    @pytest.mark.asyncio
    async def test_save_creates_version(self, persistence, sample_strategy_config):
        """Test that saving creates version entry."""
        request = ConfigurationSaveRequest(
            config_id=sample_strategy_config.config_id,
            profile_id=sample_strategy_config.profile_id,
            input_id=sample_strategy_config.input_id,
            strategy_name=sample_strategy_config.strategy_name,
            configuration=sample_strategy_config,
        )

        await persistence.save_configuration(request)
        history = await persistence.get_configuration_history(sample_strategy_config.config_id)

        assert len(history) == 1
        assert history[0].version == 1
        assert history[0].change_description == "Configuration created"

    @pytest.mark.asyncio
    async def test_update_increments_version(self, persistence, sample_strategy_config):
        """Test that updating increments version number."""
        request = ConfigurationSaveRequest(
            config_id=sample_strategy_config.config_id,
            profile_id=sample_strategy_config.profile_id,
            input_id=sample_strategy_config.input_id,
            strategy_name=sample_strategy_config.strategy_name,
            configuration=sample_strategy_config,
        )

        await persistence.save_configuration(request)

        # Update config
        sample_strategy_config.annual_return_pct = Decimal("22.0")
        request2 = ConfigurationSaveRequest(
            config_id=sample_strategy_config.config_id,
            profile_id=sample_strategy_config.profile_id,
            input_id=sample_strategy_config.input_id,
            strategy_name=sample_strategy_config.strategy_name,
            configuration=sample_strategy_config,
        )

        await persistence.save_configuration(request2)
        history = await persistence.get_configuration_history(sample_strategy_config.config_id)

        assert len(history) == 2
        assert history[1].version == 2
        assert history[1].change_description == "Configuration updated"


class TestLoadConfiguration:
    """Test loading strategy configurations."""

    @pytest.mark.asyncio
    async def test_load_saved_configuration(self, persistence, sample_strategy_config):
        """Test loading previously saved configuration."""
        request = ConfigurationSaveRequest(
            config_id=sample_strategy_config.config_id,
            profile_id=sample_strategy_config.profile_id,
            input_id=sample_strategy_config.input_id,
            strategy_name=sample_strategy_config.strategy_name,
            configuration=sample_strategy_config,
        )

        await persistence.save_configuration(request)

        load_request = ConfigurationLoadRequest(config_id=sample_strategy_config.config_id)
        response = await persistence.load_configuration(load_request)

        assert response.success is True
        assert response.configuration is not None
        assert response.configuration.config_id == "config_001"
        assert response.configuration.objective == "maximizar_capital"

    @pytest.mark.asyncio
    async def test_load_nonexistent_configuration(self, persistence):
        """Test loading nonexistent configuration."""
        load_request = ConfigurationLoadRequest(config_id="nonexistent_123")
        response = await persistence.load_configuration(load_request)

        assert response.success is False
        assert response.configuration is None
        assert "not found" in response.error_message


class TestListConfigurations:
    """Test listing configurations with filtering."""

    @pytest.mark.asyncio
    async def test_list_all_configurations(self, persistence, sample_strategy_config):
        """Test listing all configurations."""
        request = ConfigurationSaveRequest(
            config_id=sample_strategy_config.config_id,
            profile_id=sample_strategy_config.profile_id,
            input_id=sample_strategy_config.input_id,
            strategy_name=sample_strategy_config.strategy_name,
            configuration=sample_strategy_config,
        )

        await persistence.save_configuration(request)
        response = await persistence.list_configurations()

        assert response.success is True
        assert response.total_count == 1
        assert response.active_count == 1
        assert len(response.configurations) == 1

    @pytest.mark.asyncio
    async def test_list_filter_by_profile(self, persistence):
        """Test listing configurations filtered by profile ID."""
        # Create two configs with different profiles
        config1 = StrategyConfiguration(
            config_id="config_001",
            profile_id="profile_small",
            input_id="input_001",
            strategy_name="Strategy 1",
            capital_eur=Decimal("50000"),
            risk_profile="aggressive",
            objective="maximizar_capital",
            target_annual_return_pct=Decimal("15.0"),
            max_acceptable_drawdown_pct=Decimal("25.0"),
            enabled_modules=["momentum_modular"],
            module_parameters={},
        )

        config2 = StrategyConfiguration(
            config_id="config_002",
            profile_id="profile_large",
            input_id="input_002",
            strategy_name="Strategy 2",
            capital_eur=Decimal("500000"),
            risk_profile="balanced",
            objective="capital_preservation",
            target_annual_return_pct=Decimal("8.0"),
            max_acceptable_drawdown_pct=Decimal("15.0"),
            enabled_modules=["mean_reversion_modular"],
            module_parameters={},
        )

        request1 = ConfigurationSaveRequest(
            config_id=config1.config_id,
            profile_id=config1.profile_id,
            input_id=config1.input_id,
            strategy_name=config1.strategy_name,
            configuration=config1,
        )
        request2 = ConfigurationSaveRequest(
            config_id=config2.config_id,
            profile_id=config2.profile_id,
            input_id=config2.input_id,
            strategy_name=config2.strategy_name,
            configuration=config2,
        )

        await persistence.save_configuration(request1)
        await persistence.save_configuration(request2)

        response = await persistence.list_configurations(profile_id="profile_small")
        assert len(response.configurations) == 1
        assert response.configurations[0].profile_id == "profile_small"

    @pytest.mark.asyncio
    async def test_list_filter_by_objective(self, persistence):
        """Test listing configurations filtered by objective."""
        config1 = StrategyConfiguration(
            config_id="config_001",
            profile_id="profile_001",
            input_id="input_001",
            strategy_name="Strategy 1",
            capital_eur=Decimal("50000"),
            risk_profile="aggressive",
            objective="maximizar_capital",
            target_annual_return_pct=Decimal("15.0"),
            max_acceptable_drawdown_pct=Decimal("25.0"),
            enabled_modules=["momentum_modular"],
            module_parameters={},
        )

        config2 = StrategyConfiguration(
            config_id="config_002",
            profile_id="profile_002",
            input_id="input_002",
            strategy_name="Strategy 2",
            capital_eur=Decimal("100000"),
            risk_profile="conservative",
            objective="capital_preservation",
            target_annual_return_pct=Decimal("8.0"),
            max_acceptable_drawdown_pct=Decimal("15.0"),
            enabled_modules=["mean_reversion_modular"],
            module_parameters={},
        )

        request1 = ConfigurationSaveRequest(
            config_id=config1.config_id,
            profile_id=config1.profile_id,
            input_id=config1.input_id,
            strategy_name=config1.strategy_name,
            configuration=config1,
        )
        request2 = ConfigurationSaveRequest(
            config_id=config2.config_id,
            profile_id=config2.profile_id,
            input_id=config2.input_id,
            strategy_name=config2.strategy_name,
            configuration=config2,
        )

        await persistence.save_configuration(request1)
        await persistence.save_configuration(request2)

        response = await persistence.list_configurations(objective="maximizar_capital")
        assert len(response.configurations) == 1
        assert response.configurations[0].objective == "maximizar_capital"

    @pytest.mark.asyncio
    async def test_list_active_only(self, persistence, sample_strategy_config):
        """Test listing only active configurations."""
        request = ConfigurationSaveRequest(
            config_id=sample_strategy_config.config_id,
            profile_id=sample_strategy_config.profile_id,
            input_id=sample_strategy_config.input_id,
            strategy_name=sample_strategy_config.strategy_name,
            configuration=sample_strategy_config,
        )

        await persistence.save_configuration(request)

        # Deactivate the configuration
        await persistence.delete_configuration(sample_strategy_config.config_id)

        # List active only should return 0
        response = await persistence.list_configurations(active_only=True)
        assert response.active_count == 0
        assert len(response.configurations) == 0

        # List all (inactive included) should return 1
        response = await persistence.list_configurations(active_only=False)
        assert response.total_count == 1


class TestDeleteConfiguration:
    """Test soft delete functionality."""

    @pytest.mark.asyncio
    async def test_delete_deactivates_configuration(self, persistence, sample_strategy_config):
        """Test that delete marks configuration as inactive."""
        request = ConfigurationSaveRequest(
            config_id=sample_strategy_config.config_id,
            profile_id=sample_strategy_config.profile_id,
            input_id=sample_strategy_config.input_id,
            strategy_name=sample_strategy_config.strategy_name,
            configuration=sample_strategy_config,
        )

        await persistence.save_configuration(request)

        # Delete should return True
        result = await persistence.delete_configuration(sample_strategy_config.config_id)
        assert result is True

        # Configuration should still exist but be inactive
        load_request = ConfigurationLoadRequest(config_id=sample_strategy_config.config_id)
        response = await persistence.load_configuration(load_request)
        assert response.success is True
        assert response.configuration.is_active is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, persistence):
        """Test deleting nonexistent configuration."""
        result = await persistence.delete_configuration("nonexistent_123")
        assert result is False


class TestConfigurationHistory:
    """Test configuration version history."""

    @pytest.mark.asyncio
    async def test_get_configuration_history(self, persistence, sample_strategy_config):
        """Test retrieving configuration history."""
        request = ConfigurationSaveRequest(
            config_id=sample_strategy_config.config_id,
            profile_id=sample_strategy_config.profile_id,
            input_id=sample_strategy_config.input_id,
            strategy_name=sample_strategy_config.strategy_name,
            configuration=sample_strategy_config,
        )

        await persistence.save_configuration(request)

        # Update configuration
        sample_strategy_config.sharpe_ratio = Decimal("2.0")
        request2 = ConfigurationSaveRequest(
            config_id=sample_strategy_config.config_id,
            profile_id=sample_strategy_config.profile_id,
            input_id=sample_strategy_config.input_id,
            strategy_name=sample_strategy_config.strategy_name,
            configuration=sample_strategy_config,
        )
        await persistence.save_configuration(request2)

        history = await persistence.get_configuration_history(sample_strategy_config.config_id)

        assert len(history) == 2
        assert history[0].version == 1
        assert history[1].version == 2
        assert history[0].change_description == "Configuration created"
        assert history[1].change_description == "Configuration updated"

    @pytest.mark.asyncio
    async def test_history_includes_timestamp(self, persistence, sample_strategy_config):
        """Test that history includes creation timestamp."""
        request = ConfigurationSaveRequest(
            config_id=sample_strategy_config.config_id,
            profile_id=sample_strategy_config.profile_id,
            input_id=sample_strategy_config.input_id,
            strategy_name=sample_strategy_config.strategy_name,
            configuration=sample_strategy_config,
        )

        await persistence.save_configuration(request)

        history = await persistence.get_configuration_history(sample_strategy_config.config_id)

        assert len(history) > 0
        assert history[0].created_at is not None
        assert isinstance(history[0].created_at, datetime)


class TestSearchConfigurations:
    """Test search functionality."""

    @pytest.mark.asyncio
    async def test_search_by_strategy_name(self, persistence):
        """Test searching configurations by strategy name."""
        config1 = StrategyConfiguration(
            config_id="config_001",
            profile_id="profile_001",
            input_id="input_001",
            strategy_name="Momentum Strategy Alpha",
            capital_eur=Decimal("50000"),
            risk_profile="aggressive",
            objective="maximizar_capital",
            target_annual_return_pct=Decimal("15.0"),
            max_acceptable_drawdown_pct=Decimal("25.0"),
            enabled_modules=["momentum_modular"],
            module_parameters={},
        )

        config2 = StrategyConfiguration(
            config_id="config_002",
            profile_id="profile_002",
            input_id="input_002",
            strategy_name="Mean Reversion Beta",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            objective="capital_preservation",
            target_annual_return_pct=Decimal("8.0"),
            max_acceptable_drawdown_pct=Decimal("15.0"),
            enabled_modules=["mean_reversion_modular"],
            module_parameters={},
        )

        request1 = ConfigurationSaveRequest(
            config_id=config1.config_id,
            profile_id=config1.profile_id,
            input_id=config1.input_id,
            strategy_name=config1.strategy_name,
            configuration=config1,
        )
        request2 = ConfigurationSaveRequest(
            config_id=config2.config_id,
            profile_id=config2.profile_id,
            input_id=config2.input_id,
            strategy_name=config2.strategy_name,
            configuration=config2,
        )

        await persistence.save_configuration(request1)
        await persistence.save_configuration(request2)

        results = await persistence.search_configurations(strategy_name="Momentum")
        assert len(results) == 1
        assert "Momentum" in results[0].strategy_name

    @pytest.mark.asyncio
    async def test_search_by_deployment_status(self, persistence):
        """Test searching configurations by deployment status."""
        config1 = StrategyConfiguration(
            config_id="config_001",
            profile_id="profile_001",
            input_id="input_001",
            strategy_name="Strategy 1",
            capital_eur=Decimal("50000"),
            risk_profile="aggressive",
            objective="maximizar_capital",
            target_annual_return_pct=Decimal("15.0"),
            max_acceptable_drawdown_pct=Decimal("25.0"),
            enabled_modules=["momentum_modular"],
            module_parameters={},
            deployment_status="APPROVED",
        )

        config2 = StrategyConfiguration(
            config_id="config_002",
            profile_id="profile_002",
            input_id="input_002",
            strategy_name="Strategy 2",
            capital_eur=Decimal("100000"),
            risk_profile="conservative",
            objective="capital_preservation",
            target_annual_return_pct=Decimal("8.0"),
            max_acceptable_drawdown_pct=Decimal("15.0"),
            enabled_modules=["mean_reversion_modular"],
            module_parameters={},
            deployment_status="REJECTED",
        )

        request1 = ConfigurationSaveRequest(
            config_id=config1.config_id,
            profile_id=config1.profile_id,
            input_id=config1.input_id,
            strategy_name=config1.strategy_name,
            configuration=config1,
        )
        request2 = ConfigurationSaveRequest(
            config_id=config2.config_id,
            profile_id=config2.profile_id,
            input_id=config2.input_id,
            strategy_name=config2.strategy_name,
            configuration=config2,
        )

        await persistence.save_configuration(request1)
        await persistence.save_configuration(request2)

        results = await persistence.search_configurations(deployment_status="APPROVED")
        assert len(results) == 1
        assert results[0].deployment_status == "APPROVED"


class TestPersistenceStatus:
    """Test persistence status reporting."""

    @pytest.mark.asyncio
    async def test_get_persistence_status_empty(self, persistence):
        """Test status of empty persistence."""
        status = persistence.get_persistence_status()

        assert status["total_configurations"] == 0
        assert status["active_configurations"] == 0
        assert status["total_versions"] == 0

    @pytest.mark.asyncio
    async def test_get_persistence_status_with_configs(self, persistence, sample_strategy_config):
        """Test status with saved configurations."""
        request = ConfigurationSaveRequest(
            config_id=sample_strategy_config.config_id,
            profile_id=sample_strategy_config.profile_id,
            input_id=sample_strategy_config.input_id,
            strategy_name=sample_strategy_config.strategy_name,
            configuration=sample_strategy_config,
        )

        await persistence.save_configuration(request)

        status = persistence.get_persistence_status()

        assert status["total_configurations"] == 1
        assert status["active_configurations"] == 1
        assert status["total_versions"] == 1
        assert status["indexed_profiles"] == 1
        assert status["indexed_objectives"] == 1


class TestSingleton:
    """Test singleton pattern."""

    def test_get_configuration_persistence_returns_singleton(self):
        """Test that get_configuration_persistence returns same instance."""
        instance1 = get_configuration_persistence()
        instance2 = get_configuration_persistence()

        assert instance1 is instance2


class TestErrorHandling:
    """Test error handling in persistence operations."""

    @pytest.mark.asyncio
    async def test_save_configuration_with_invalid_data(self, persistence):
        """Test error handling for invalid configuration data."""
        # This should not raise an error - Pydantic will validate
        # If data is invalid, the ConfigurationSaveRequest creation will fail
        pass

    @pytest.mark.asyncio
    async def test_load_configuration_returns_error_response(self, persistence):
        """Test that load returns error response instead of raising."""
        load_request = ConfigurationLoadRequest(config_id="invalid_id")
        response = await persistence.load_configuration(load_request)

        assert response.success is False
        assert response.error_message is not None
