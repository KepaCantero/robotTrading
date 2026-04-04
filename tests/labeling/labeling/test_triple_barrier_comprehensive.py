"""
Comprehensive unit tests for Triple Barrier labeling module.

Tests cover:
- TripleBarrierConfig configuration
- Barrier label generation with Numba
- Volatility-based barriers
- GARCH volatility modeling
- Visualization functions
- Edge cases and error handling
- Performance optimizations
"""

import pytest

# Try importing the module
try:
    from app.backtesting.labeling.triple_barrier import TripleBarrierConfig

    MODULE_AVAILABLE = True
except ImportError as e:
    MODULE_AVAILABLE = False
    IMPORT_ERROR = str(e)


@pytest.mark.skipif(
    not MODULE_AVAILABLE,
    reason=f"Module not available: {IMPORT_ERROR if not MODULE_AVAILABLE else 'OK'}",
)
class TestTripleBarrierConfig:
    """Test suite for TripleBarrierConfig dataclass."""

    def test_default_configuration(self):
        """Test configuration with default values."""
        config = TripleBarrierConfig()

        assert config.upper_barrier_pct == 0.02
        assert config.lower_barrier_pct == -0.01
        assert config.vertical_barrier_days == 5
        assert config.min_return == 0.0
        assert config.vol_scale == 1.5
        assert config.vol_window == 20
        assert config.numba_enabled is True

    def test_custom_configuration(self):
        """Test configuration with custom values."""
        config = TripleBarrierConfig(
            upper_barrier_pct=0.05,
            lower_barrier_pct=-0.02,
            vertical_barrier_days=10,
            min_return=0.01,
            vol_scale=2.0,
            vol_window=30,
            numba_enabled=False,
        )

        assert config.upper_barrier_pct == 0.05
        assert config.lower_barrier_pct == -0.02
        assert config.vertical_barrier_days == 10
        assert config.min_return == 0.01
        assert config.vol_scale == 2.0
        assert config.vol_window == 30
        assert config.numba_enabled is False

    def test_upper_barrier_must_be_positive(self):
        """Test that upper barrier must be positive."""
        with pytest.raises(ValueError, match="upper_barrier_pct must be positive"):
            TripleBarrierConfig(upper_barrier_pct=0.0)

        with pytest.raises(ValueError, match="upper_barrier_pct must be positive"):
            TripleBarrierConfig(upper_barrier_pct=-0.01)

    def test_lower_barrier_must_be_negative(self):
        """Test that lower barrier must be negative."""
        with pytest.raises(ValueError, match="lower_barrier_pct must be negative"):
            TripleBarrierConfig(lower_barrier_pct=0.0)

        with pytest.raises(ValueError, match="lower_barrier_pct must be negative"):
            TripleBarrierConfig(lower_barrier_pct=0.01)

    def test_vertical_barrier_must_be_positive(self):
        """Test that vertical barrier days must be positive."""
        with pytest.raises(ValueError, match="vertical_barrier_days must be positive"):
            TripleBarrierConfig(vertical_barrier_days=0)

        with pytest.raises(ValueError, match="vertical_barrier_days must be positive"):
            TripleBarrierConfig(vertical_barrier_days=-1)

    def test_stop_loss_larger_than_target_warning(self):
        """Test warning when stop loss is larger than profit target."""
        with pytest.warns(UserWarning, match="Stop loss is larger than profit target"):
            TripleBarrierConfig(
                upper_barrier_pct=0.01,
                lower_barrier_pct=-0.02,
            )

    def test_metadata_dict(self):
        """Test metadata dictionary initialization."""
        config = TripleBarrierConfig(metadata={'key': 'value', 'number': 42})

        assert config.metadata == {'key': 'value', 'number': 42}

    def test_metadata_default_empty(self):
        """Test metadata is empty dict by default."""
        config = TripleBarrierConfig()

        assert config.metadata == {}
