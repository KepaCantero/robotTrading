"""
Tests for GAN-based Synthetic Data Generator
"""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock

from app.services.synthetic_data.gan_generator import (
    GANConfig,
    SyntheticDataGenerator,
    TimeSeriesGANGenerator,
    get_gan_generator,
    get_ts_gan_generator,
)


@pytest.fixture
def gan_config():
    """Create GAN configuration."""
    return GANConfig(
        epochs=10,
        batch_size=32,
        latent_dim=50,
        output_dim=5,
    )


@pytest.fixture
def sample_market_data():
    """Create sample OHLCV market data."""
    np.random.seed(42)
    # Shape: [100, 5] for 100 samples of OHLCV
    data = np.zeros((100, 5))
    for i in range(100):
        open_price = 100 + np.random.randn() * 5
        close_price = open_price + np.random.randn() * 3
        high_price = max(open_price, close_price) + np.abs(np.random.randn() * 2)
        low_price = min(open_price, close_price) - np.abs(np.random.randn() * 2)
        volume = np.abs(np.random.randn()) * 1000000 + 1000000
        data[i] = [open_price, high_price, low_price, close_price, volume]
    return data


class TestGANConfig:
    """Test GAN configuration."""

    def test_config_initialization(self):
        """Test GAN config initialization."""
        config = GANConfig(epochs=100, learning_rate=0.001)
        assert config.epochs == 100
        assert config.learning_rate == 0.001
        assert config.latent_dim == 100

    def test_config_default_layers(self):
        """Test default layer sizes."""
        config = GANConfig()
        assert config.generator_layers is not None
        assert config.discriminator_layers is not None
        assert config.output_dim == 5

    def test_config_custom_layers(self):
        """Test custom layer sizes."""
        custom_gen = [64, 128, 256, 5]
        custom_disc = [256, 128, 64, 1]
        config = GANConfig(
            generator_layers=custom_gen,
            discriminator_layers=custom_disc,
        )
        assert config.generator_layers == custom_gen
        assert config.discriminator_layers == custom_disc


class TestSyntheticDataGenerator:
    """Test synthetic data generator."""

    @pytest.mark.asyncio
    async def test_initialization(self, gan_config):
        """Test generator initialization."""
        gen = SyntheticDataGenerator(gan_config)
        assert gen.connected is False
        assert gen.training_data is None

    @pytest.mark.asyncio
    async def test_connect(self, gan_config):
        """Test generator connection."""
        gen = SyntheticDataGenerator(gan_config)
        result = await gen.connect()
        assert result is True
        assert gen.connected is True

    @pytest.mark.asyncio
    async def test_train(self, gan_config, sample_market_data):
        """Test GAN training."""
        gen = SyntheticDataGenerator(gan_config)
        await gen.connect()

        result = await gen.train(sample_market_data)

        assert "epochs_trained" in result
        assert result["epochs_trained"] == gan_config.epochs
        assert "training_samples" in result
        assert result["training_samples"] == len(sample_market_data)
        assert "final_discriminator_loss" in result
        assert "final_generator_loss" in result

    @pytest.mark.asyncio
    async def test_train_history(self, gan_config, sample_market_data):
        """Test training history tracking."""
        gen = SyntheticDataGenerator(gan_config)
        await gen.connect()

        await gen.train(sample_market_data)

        assert len(gen.training_history) == gan_config.epochs
        for entry in gen.training_history:
            assert "epoch" in entry
            assert "discriminator_loss" in entry
            assert "generator_loss" in entry

    @pytest.mark.asyncio
    async def test_generate_samples_without_training(self, gan_config):
        """Test sample generation without connection."""
        gen = SyntheticDataGenerator(gan_config)
        samples = await gen.generate_samples(10)
        assert len(samples) == 0

    @pytest.mark.asyncio
    async def test_generate_samples(self, gan_config, sample_market_data):
        """Test synthetic sample generation."""
        gen = SyntheticDataGenerator(gan_config)
        await gen.connect()
        await gen.train(sample_market_data)

        samples = await gen.generate_samples(20)

        assert len(samples) == 20
        assert samples.shape[1] == 5  # OHLCV
        # Check realistic OHLCV structure
        for sample in samples:
            assert sample[1] > sample[2]  # High > Low
            assert sample[4] > 0  # Volume > 0

    @pytest.mark.asyncio
    async def test_generate_samples_with_noise(self, gan_config, sample_market_data):
        """Test sample generation with custom noise."""
        gen = SyntheticDataGenerator(gan_config)
        await gen.connect()
        await gen.train(sample_market_data)

        custom_noise = np.random.randn(10, gan_config.latent_dim)
        samples = await gen.generate_samples(10, noise=custom_noise)

        assert len(samples) == 10

    @pytest.mark.asyncio
    async def test_evaluate_quality(self, gan_config, sample_market_data):
        """Test synthetic data quality evaluation."""
        gen = SyntheticDataGenerator(gan_config)
        await gen.connect()
        await gen.train(sample_market_data)

        synthetic = await gen.generate_samples(50)
        metrics = await gen.evaluate_quality(synthetic, sample_market_data)

        assert "mean_difference" in metrics
        assert "std_difference" in metrics
        assert "correlation_difference" in metrics
        assert "wasserstein_distance" in metrics
        assert "quality_score" in metrics
        assert 0 <= metrics["quality_score"] <= 1

    @pytest.mark.asyncio
    async def test_evaluate_quality_similar_data(self):
        """Test quality evaluation with identical data."""
        gen = SyntheticDataGenerator()
        data = np.random.randn(50, 5)
        metrics = await gen.evaluate_quality(data, data)

        # Quality should be high (nearly 1) for identical data
        assert metrics["quality_score"] > 0.8

    @pytest.mark.asyncio
    async def test_normalization_minmax(self, gan_config, sample_market_data):
        """Test min-max normalization during training."""
        config = GANConfig(
            epochs=5,
            normalize_data=True,
            normalization_method="minmax",
        )
        gen = SyntheticDataGenerator(config)
        await gen.connect()
        await gen.train(sample_market_data)

        assert gen.data_scaler is not None
        assert "min" in gen.data_scaler
        assert "max" in gen.data_scaler

    @pytest.mark.asyncio
    async def test_normalization_zscore(self, gan_config, sample_market_data):
        """Test z-score normalization during training."""
        config = GANConfig(
            epochs=5,
            normalize_data=True,
            normalization_method="zscore",
        )
        gen = SyntheticDataGenerator(config)
        await gen.connect()
        await gen.train(sample_market_data)

        assert gen.data_scaler is not None
        assert "mean" in gen.data_scaler
        assert "std" in gen.data_scaler

    def test_get_generator_status(self, gan_config):
        """Test getting generator status."""
        gen = SyntheticDataGenerator(gan_config)
        status = gen.get_generator_status()
        assert status["connected"] is False
        assert status["generator_type"] == "GAN"
        assert status["data_scaled"] is False


class TestTimeSeriesGANGenerator:
    """Test time series GAN generator."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test time series GAN initialization."""
        gen = TimeSeriesGANGenerator()
        assert gen.connected is False
        assert gen.sequence_length == 30

    @pytest.mark.asyncio
    async def test_connect(self):
        """Test time series GAN connection."""
        gen = TimeSeriesGANGenerator()
        result = await gen.connect()
        assert result is True
        assert gen.connected is True

    @pytest.mark.asyncio
    async def test_generate_sequences(self):
        """Test sequence generation."""
        gen = TimeSeriesGANGenerator()
        await gen.connect()

        sequences = await gen.generate_sequences(5)

        assert sequences.shape[0] == 5
        assert sequences.shape[1] == 30  # Default sequence length
        assert sequences.shape[2] == 5  # OHLCV

    @pytest.mark.asyncio
    async def test_generate_sequences_custom_length(self):
        """Test sequence generation with custom length."""
        gen = TimeSeriesGANGenerator()
        await gen.connect()

        sequences = await gen.generate_sequences(3, sequence_length=20)

        assert sequences.shape[1] == 20

    @pytest.mark.asyncio
    async def test_sequences_realistic_structure(self):
        """Test sequences have realistic OHLCV structure."""
        gen = TimeSeriesGANGenerator()
        await gen.connect()

        sequences = await gen.generate_sequences(2)

        for seq in sequences:
            for t in range(len(seq)):
                open_p, high_p, low_p, close_p, volume = seq[t]
                # High should be >= Open and Close
                assert high_p >= min(open_p, close_p)
                # Low should be <= Open and Close
                assert low_p <= max(open_p, close_p)
                # Volume should be positive
                assert volume > 0

    def test_get_generator_status(self):
        """Test getting generator status."""
        gen = TimeSeriesGANGenerator()
        status = gen.get_generator_status()
        assert status["connected"] is False
        assert status["generator_type"] == "TimeSeriesGAN"
        assert status["sequence_length"] == 30


class TestGANSingletons:
    """Test singleton pattern for GAN generators."""

    @pytest.mark.asyncio
    async def test_gan_generator_singleton(self, gan_config):
        """Test GAN generator singleton."""
        gen1 = get_gan_generator(gan_config)
        gen2 = get_gan_generator(gan_config)
        assert gen1 is gen2

    @pytest.mark.asyncio
    async def test_ts_gan_generator_singleton(self):
        """Test TimeSeriesGAN generator singleton."""
        gen1 = get_ts_gan_generator()
        gen2 = get_ts_gan_generator()
        assert gen1 is gen2
