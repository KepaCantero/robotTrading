"""
Unit tests for service_registry.py
===================================

Tests for compliance service registry.
"""

import threading

from app.domain.services.compliance.service_registry import (
    ComplianceServiceRegistry,
    get_service,
    get_service_registry,
)


class TestComplianceServiceRegistry:
    """Tests for ComplianceServiceRegistry class."""

    def test_singleton_pattern(self):
        """Test that getInstance returns same instance."""
        # Reset instance for clean test
        ComplianceServiceRegistry.reset_instance()

        registry1 = ComplianceServiceRegistry.get_instance()
        registry2 = ComplianceServiceRegistry.get_instance()

        assert registry1 is registry2
        assert id(registry1) == id(registry2)

    def test_reset_instance(self):
        """Test resetting singleton instance."""
        ComplianceServiceRegistry.reset_instance()
        registry1 = ComplianceServiceRegistry.get_instance()

        ComplianceServiceRegistry.reset_instance()
        registry2 = ComplianceServiceRegistry.get_instance()

        # Should be different instances after reset
        assert registry1 is not registry2

    def test_register_service_factory(self):
        """Test registering a service factory."""
        ComplianceServiceRegistry.reset_instance()
        registry = ComplianceServiceRegistry.get_instance()

        def mock_factory() -> str:
            return "mock_service"

        registry.register_service("mock_service", mock_factory)

        # Factory should be registered
        assert "mock_service" in registry._factories

    def test_get_service_lazy_initialization(self):
        """Test lazy service initialization."""
        ComplianceServiceRegistry.reset_instance()
        registry = ComplianceServiceRegistry.get_instance()

        call_count = [0]

        def mock_factory():
            call_count[0] += 1
            return "mock_service"

        registry.register_service("mock_lazy", mock_factory)

        # Service not created yet
        assert call_count[0] == 0

        # First access creates service
        service = registry.get_service("mock_lazy")
        assert call_count[0] == 1
        assert service == "mock_service"

        # Second access returns cached service
        service2 = registry.get_service("mock_lazy")
        assert call_count[0] == 1  # Not incremented
        assert service2 is service

    def test_get_service_not_found(self):
        """Test getting non-existent service returns None."""
        ComplianceServiceRegistry.reset_instance()
        registry = ComplianceServiceRegistry.get_instance()

        service = registry.get_service("non_existent")
        assert service is None

    def test_get_service_factory_failure(self):
        """Test that factory failures are handled gracefully."""
        ComplianceServiceRegistry.reset_instance()
        registry = ComplianceServiceRegistry.get_instance()

        def failing_factory():
            raise RuntimeError("Factory failed")

        registry.register_service("failing_service", failing_factory)

        service = registry.get_service("failing_service")
        assert service is None
        assert registry.is_available("failing_service") is False

    def test_is_available(self):
        """Test checking service availability."""
        ComplianceServiceRegistry.reset_instance()
        registry = ComplianceServiceRegistry.get_instance()

        def mock_factory():
            return "available_service"

        registry.register_service("available", mock_factory)

        # Before access, availability is unknown
        # After access, should be available
        registry.get_service("available")
        assert registry.is_available("available") is True

    def test_get_all_services(self):
        """Test getting all registered services."""
        ComplianceServiceRegistry.reset_instance()
        registry = ComplianceServiceRegistry.get_instance()

        registry.register_service("service1", lambda: "s1")
        registry.register_service("service2", lambda: "s2")

        # Get all services (lazy initialization)
        services = registry.get_all_services()

        assert "service1" in services
        assert "service2" in services
        assert len(services) >= 2

    def test_get_availability_report(self):
        """Test getting availability status of all services."""
        ComplianceServiceRegistry.reset_instance()
        registry = ComplianceServiceRegistry.get_instance()

        registry.register_service("available", lambda: "avail")
        registry.register_service("failing", lambda: (_ for _ in ()).throw(RuntimeError()))

        report = registry.get_availability_report()

        assert "available" in report
        assert "failing" in report

    def test_thread_safe_singleton(self):
        """Test that singleton is thread-safe."""
        ComplianceServiceRegistry.reset_instance()

        instances = []

        def get_instance():
            instance = ComplianceServiceRegistry.get_instance()
            instances.append(instance)

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get the same instance
        assert all(id(inst) == id(instances[0]) for inst in instances)


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_service_registry(self):
        """Test get_service_registry returns singleton."""
        ComplianceServiceRegistry.reset_instance()

        registry = get_service_registry()
        assert isinstance(registry, ComplianceServiceRegistry)

        # Should return same instance
        registry2 = get_service_registry()
        assert registry is registry2

    def test_get_service(self):
        """Test get_service convenience function."""
        ComplianceServiceRegistry.reset_instance()
        registry = get_service_registry()

        def mock_factory():
            return "test_service"

        registry.register_service("test", mock_factory)

        service = get_service("test")
        assert service == "test_service"


class TestServiceFactories:
    """Tests for built-in service factories."""

    def test_regime_detector_factory_exists(self):
        """Test that regime detector factory is registered."""
        ComplianceServiceRegistry.reset_instance()
        registry = ComplianceServiceRegistry.get_instance()

        assert "regime_detector" in registry._factories

    def test_alpha_model_factory_exists(self):
        """Test that alpha model factory is registered."""
        ComplianceServiceRegistry.reset_instance()
        registry = ComplianceServiceRegistry.get_instance()

        assert "alpha_model" in registry._factories

    def test_harris_integrator_factory_exists(self):
        """Test that Harris integrator factory is registered."""
        ComplianceServiceRegistry.reset_instance()
        registry = ComplianceServiceRegistry.get_instance()

        assert "harris_integrator" in registry._factories

    def test_all_expected_factories_registered(self):
        """Test that all expected factories are registered."""
        ComplianceServiceRegistry.reset_instance()
        registry = ComplianceServiceRegistry.get_instance()

        expected_factories = [
            "regime_detector",
            "vwap_executor",
            "alpha_model",
            "risk_model",
            "harris_integrator",
            "liquidity_analyzer",
            "var_calculator",
            "golden_signals",
        ]

        for factory_name in expected_factories:
            assert factory_name in registry._factories, f"Missing factory: {factory_name}"
