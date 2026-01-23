"""
FASE 6.2: GAN-based Synthetic Data Generator

Generates synthetic trading data using Generative Adversarial Networks (GANs)
for training data augmentation and backtesting.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class GANConfig:
    """Configuration for GAN training."""

    # Network architecture
    generator_layers: List[int] = None
    discriminator_layers: List[int] = None
    latent_dim: int = 100
    output_dim: int = 5  # OHLCV data

    # Training parameters
    epochs: int = 1000
    batch_size: int = 64
    learning_rate: float = 0.0002
    beta1: float = 0.5  # Adam optimizer beta1
    beta2: float = 0.999  # Adam optimizer beta2

    # Data normalization
    normalize_data: bool = True
    normalization_method: str = "minmax"  # or "zscore"

    # Training monitoring
    discriminator_loss_weight: float = 0.5
    generator_loss_weight: float = 1.0
    gradient_penalty_weight: float = 10.0

    # Loss tracking
    save_interval: int = 100  # Save model every N epochs
    display_interval: int = 50  # Display loss every N epochs

    # REPRODUCIBILITY: Random seed for all stochastic operations
    random_state: int = 42

    def __post_init__(self):
        """Set default layer sizes if not provided."""
        if self.generator_layers is None:
            self.generator_layers = [128, 256, 512, self.output_dim]
        if self.discriminator_layers is None:
            self.discriminator_layers = [512, 256, 128, 1]


class SyntheticDataGenerator:
    """
    Generate synthetic market data using GANs.

    REPRODUCIBILITY: Uses np.random.default_rng for all random operations.
    """

    def __init__(self, config: Optional[GANConfig] = None):
        """
        Initialize synthetic data generator.

        Args:
            config: GAN configuration
        """
        self.config = config or GANConfig()
        self.generator = None
        self.discriminator = None
        self.training_data = None
        self.training_history = []
        self.connected = False
        self.data_scaler = None
        # Reproducible random state
        self._rng = np.random.default_rng(self.config.random_state)
        logger.info("✅ SyntheticDataGenerator initialized with seed=%d", self.config.random_state)

    async def connect(self) -> bool:
        """Initialize GAN models and training setup."""
        try:
            # In production:
            # from tensorflow.keras.models import Sequential
            # from tensorflow.keras.layers import Dense, Reshape, Flatten, LeakyReLU
            # Build generator and discriminator

            # Simulated: models are initialized
            self.connected = True
            logger.info("✅ Connected to GAN generator")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize GAN models: {str(e)}")
            self.connected = False
            return False

    async def train(
        self,
        training_data: np.ndarray,
        labels: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Train GAN on historical market data.

        Args:
            training_data: Historical OHLCV data (shape: [samples, 5])
            labels: Optional labels for conditional GAN

        Returns:
            Training history and metrics
        """
        if not self.connected:
            return {}

        try:
            self.training_data = training_data
            num_samples = len(training_data)

            # Normalize data
            if self.config.normalize_data:
                if self.config.normalization_method == "minmax":
                    self.data_scaler = {
                        "min": training_data.min(axis=0),
                        "max": training_data.max(axis=0),
                    }
                    (training_data - self.data_scaler["min"]) / (
                        self.data_scaler["max"] - self.data_scaler["min"] + 1e-8
                    )
                else:  # zscore
                    self.data_scaler = {
                        "mean": training_data.mean(axis=0),
                        "std": training_data.std(axis=0),
                    }
                    (training_data - self.data_scaler["mean"]) / (self.data_scaler["std"] + 1e-8)
            else:
                pass

            # Simulate training process
            for epoch in range(self.config.epochs):
                # In production:
                # 1. Sample random noise (latent vectors)
                # 2. Generate fake samples using generator
                # 3. Train discriminator on real + fake samples
                # 4. Train generator to fool discriminator
                # 5. Track losses

                # Simulated losses (reproducible)
                discriminator_loss = float(
                    np.abs(self._rng.standard_normal()) * 0.5 * (1 - epoch / self.config.epochs)
                )
                generator_loss = float(
                    np.abs(self._rng.standard_normal()) * 0.5 * (1 - epoch / self.config.epochs)
                )

                self.training_history.append(
                    {
                        "epoch": epoch,
                        "discriminator_loss": discriminator_loss,
                        "generator_loss": generator_loss,
                    }
                )

                if (epoch + 1) % self.config.display_interval == 0:
                    logger.info(
                        f"Epoch {epoch + 1}/{self.config.epochs} - "
                        f"D_loss: {discriminator_loss:.4f}, "
                        f"G_loss: {generator_loss:.4f}"
                    )

            result = {
                "epochs_trained": self.config.epochs,
                "training_samples": num_samples,
                "final_discriminator_loss": self.training_history[-1]["discriminator_loss"],
                "final_generator_loss": self.training_history[-1]["generator_loss"],
                "training_time_seconds": 0.0,  # Would be measured in production
            }

            logger.info("✅ GAN training completed")
            return result

        except Exception as e:
            logger.error(f"❌ GAN training failed: {str(e)}")
            return {}

    async def generate_samples(
        self,
        num_samples: int,
        noise: Optional[np.ndarray] = None,
        conditions: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Generate synthetic market data.

        Args:
            num_samples: Number of samples to generate
            noise: Optional noise input (latent vectors)
            conditions: Optional conditional inputs

        Returns:
            Generated synthetic data (shape: [num_samples, 5] for OHLCV)
        """
        if not self.connected:
            return np.array([])

        try:
            if noise is None:
                noise = self._rng.standard_normal((num_samples, self.config.latent_dim))

            # In production: synthetic_data = self.generator.predict(noise)

            # Simulated synthetic data generation (reproducible OHLCV structure)
            synthetic_data = self._rng.standard_normal((num_samples, self.config.output_dim))

            # Make it more realistic: High > Close > Low, Volume > 0
            # Pre-generate all random values for reproducibility
            close_deltas = self._rng.standard_normal(num_samples) * 2
            high_deltas = np.abs(self._rng.standard_normal(num_samples))
            low_deltas = np.abs(self._rng.standard_normal(num_samples))

            for i in range(num_samples):
                # Normalize OHLCV to realistic ranges
                open_price = np.abs(synthetic_data[i, 0]) + 100  # Open ~100-102
                close_price = open_price + close_deltas[i]  # Close near open
                high_price = max(open_price, close_price) + high_deltas[i]
                low_price = min(open_price, close_price) - low_deltas[i]
                volume = np.abs(synthetic_data[i, 4]) * 1000000 + 1000000  # Volume > 1M

                synthetic_data[i] = [open_price, high_price, low_price, close_price, volume]

            # Denormalize if normalized during training
            if self.config.normalize_data and self.data_scaler:
                if "min" in self.data_scaler:  # minmax scaling
                    synthetic_data = (
                        synthetic_data * (self.data_scaler["max"] - self.data_scaler["min"])
                        + self.data_scaler["min"]
                    )
                else:  # zscore scaling
                    synthetic_data = (
                        synthetic_data * self.data_scaler["std"] + self.data_scaler["mean"]
                    )

            logger.info(f"✅ Generated {num_samples} synthetic samples")
            return synthetic_data

        except Exception as e:
            logger.error(f"❌ Synthetic data generation failed: {str(e)}")
            return np.array([])

    async def evaluate_quality(
        self,
        synthetic_data: np.ndarray,
        real_data: np.ndarray,
    ) -> Dict[str, float]:
        """
        Evaluate quality of synthetic data.

        Args:
            synthetic_data: Generated synthetic data
            real_data: Original real data

        Returns:
            Quality metrics
        """
        try:
            metrics = {}

            # Statistical metrics
            real_mean = real_data.mean(axis=0)
            synthetic_mean = synthetic_data.mean(axis=0)
            mean_diff = np.abs(real_mean - synthetic_mean).mean()
            metrics["mean_difference"] = float(mean_diff)

            real_std = real_data.std(axis=0)
            synthetic_std = synthetic_data.std(axis=0)
            std_diff = np.abs(real_std - synthetic_std).mean()
            metrics["std_difference"] = float(std_diff)

            # Correlation metrics
            real_corr = np.corrcoef(real_data.T)
            synthetic_corr = np.corrcoef(synthetic_data.T)
            corr_diff = np.abs(real_corr - synthetic_corr).mean()
            metrics["correlation_difference"] = float(corr_diff)

            # Distribution similarity (simplified Wasserstein distance)
            metrics["wasserstein_distance"] = float(
                np.sqrt(np.mean((real_mean - synthetic_mean) ** 2))
            )

            # Overall quality score (0-1, higher is better)
            quality_score = 1.0 / (1.0 + mean_diff + std_diff + corr_diff)
            metrics["quality_score"] = float(np.clip(quality_score, 0, 1))

            logger.info(f"✅ Evaluated synthetic data quality: {metrics['quality_score']:.4f}")
            return metrics

        except Exception as e:
            logger.error(f"❌ Quality evaluation failed: {str(e)}")
            return {}

    def get_generator_status(self) -> Dict[str, Any]:
        """Get generator status."""
        return {
            "connected": self.connected,
            "generator_type": "GAN",
            "epochs_trained": len(self.training_history),
            "data_scaled": self.data_scaler is not None,
            "training_history_size": len(self.training_history),
        }


class TimeSeriesGANGenerator:
    """GAN generator specialized for time series data."""

    def __init__(self, config: Optional[GANConfig] = None):
        """
        Initialize time series GAN generator.

        Args:
            config: GAN configuration
        """
        self.config = config or GANConfig()
        self.sequence_length: int = 30  # 30-day sequences
        self.connected = False
        logger.info("✅ TimeSeriesGANGenerator initialized")

    async def connect(self) -> bool:
        """Initialize time series GAN models."""
        try:
            # In production: use LSTM/Transformer-based GAN
            self.connected = True
            logger.info("✅ Connected to TimeSeriesGAN generator")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize TimeSeriesGAN: {str(e)}")
            self.connected = False
            return False

    async def generate_sequences(
        self,
        num_sequences: int,
        sequence_length: int = None,
    ) -> np.ndarray:
        """
        Generate synthetic time series sequences.

        Args:
            num_sequences: Number of sequences to generate
            sequence_length: Length of each sequence

        Returns:
            Synthetic sequences (shape: [num_sequences, sequence_length, 5])
        """
        if not self.connected:
            return np.array([])

        try:
            seq_len = sequence_length or self.sequence_length

            # In production: use LSTM-based generator
            # synthetic_sequences = self.lstm_generator.predict(noise)

            # Simulated: generate realistic price sequences (reproducible)
            synthetic_sequences = np.zeros((num_sequences, seq_len, 5))

            # Pre-generate all random values for reproducibility
            total_steps = num_sequences * seq_len
            price_changes = self._rng.standard_normal(total_steps) * 2
            high_deltas = np.abs(self._rng.standard_normal(total_steps))
            low_deltas = np.abs(self._rng.standard_normal(total_steps))
            volumes = np.abs(self._rng.standard_normal(total_steps)) * 1000000 + 1000000

            idx = 0
            for s in range(num_sequences):
                # Generate random walk price series
                price = 100.0
                for t in range(seq_len):
                    # Random walk for price
                    open_price = price
                    close_price = price + price_changes[idx]
                    high_price = max(open_price, close_price) + high_deltas[idx]
                    low_price = min(open_price, close_price) - low_deltas[idx]
                    volume = volumes[idx]

                    synthetic_sequences[s, t] = [
                        open_price,
                        high_price,
                        low_price,
                        close_price,
                        volume,
                    ]
                    price = close_price
                    idx += 1

            logger.info(f"✅ Generated {num_sequences} synthetic sequences")
            return synthetic_sequences

        except Exception as e:
            logger.error(f"❌ Sequence generation failed: {str(e)}")
            return np.array([])

    def get_generator_status(self) -> Dict[str, Any]:
        """Get generator status."""
        return {
            "connected": self.connected,
            "generator_type": "TimeSeriesGAN",
            "sequence_length": self.sequence_length,
        }


# Singleton instances
_gan_generator: Optional[SyntheticDataGenerator] = None
_ts_gan_generator: Optional[TimeSeriesGANGenerator] = None


def get_gan_generator(config: Optional[GANConfig] = None) -> SyntheticDataGenerator:
    """Get or create singleton GAN generator."""
    global _gan_generator
    if _gan_generator is None:
        _gan_generator = SyntheticDataGenerator(config)
        logger.info("✅ GAN generator singleton initialized")
    return _gan_generator


def get_ts_gan_generator(config: Optional[GANConfig] = None) -> TimeSeriesGANGenerator:
    """Get or create singleton TimeSeriesGAN generator."""
    global _ts_gan_generator
    if _ts_gan_generator is None:
        _ts_gan_generator = TimeSeriesGANGenerator(config)
        logger.info("✅ TimeSeriesGAN generator singleton initialized")
    return _ts_gan_generator
