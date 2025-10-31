"""
DeepLearningEngine - Det parte patrones complejos con LSTM, GRU o Transformers.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from .base_learning_engine import BaseLearningEngine

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False
    logger.warning("PyTorch no disponible. DeepLearningEngine requiere PyTorch.")

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    logger.warning("TensorFlow no disponible. DeepLearningEngine requiere PyTorch o TensorFlow.")


# TimeSeriesDataset solo se define si PyTorch está disponible
if PYTORCH_AVAILABLE:
    class TimeSeriesDataset(Dataset):
        """Dataset para series de tiempo."""
        
        def __init__(self, sequences, labels):
            self.sequences = torch.FloatTensor(sequences)
            self.labels = torch.FloatTensor(labels) if labels is not None else None
        
        def __len__(self):
            return len(self.sequences)
        
        def __getitem__(self, idx):
            if self.labels is not None:
                return self.sequences[idx], self.labels[idx]
            return self.sequences[idx]
else:
    # Placeholder si PyTorch no está disponible
    class TimeSeriesDataset:
        """Dataset placeholder cuando PyTorch no está disponible."""
        
        def __init__(self, sequences, labels):
            raise ImportError("PyTorch required for TimeSeriesDataset")


# LSTMModel y GRUModel solo disponibles si PyTorch está instalado
if PYTORCH_AVAILABLE:
    class LSTMModel(nn.Module):
        """Modelo LSTM para predicción de series de tiempo."""
        
        def __init__(self, input_size, hidden_size, num_layers, output_size, dropout=0.2):
            super(LSTMModel, self).__init__()
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            
            self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
            self.fc = nn.Linear(hidden_size, output_size)
            self.sigmoid = nn.Sigmoid()
        
        def forward(self, x):
            h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
            c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
            
            out, _ = self.lstm(x, (h0, c0))
            out = self.fc(out[:, -1, :])
            out = self.sigmoid(out)
            return out
    
    class GRUModel(nn.Module):
        """Modelo GRU para predicción de series de tiempo."""
        
        def __init__(self, input_size, hidden_size, num_layers, output_size, dropout=0.2):
            super(GRUModel, self).__init__()
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            
            self.gru = nn.GRU(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
            self.fc = nn.Linear(hidden_size, output_size)
            self.sigmoid = nn.Sigmoid()
        
        def forward(self, x):
            h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
            out, _ = self.gru(x, h0)
            out = self.fc(out[:, -1, :])
            out = self.sigmoid(out)
            return out
else:
    # Placeholders si PyTorch no está disponible
    class LSTMModel:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyTorch required for LSTMModel")
    
    class GRUModel:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyTorch required for GRUModel")


class DeepLearningEngine(BaseLearningEngine):
    """
    Motor de Deep Learning para detectar patrones complejos en series de tiempo.
    
    Arquitecturas soportadas:
    - LSTM: Para dependencias de largo plazo
    - GRU: Similar a LSTM, más eficiente
    - Transformer: Para capturar relaciones complejas (futuro)
    
    Predice movimientos de mercado y ajusta parámetros dinámicos de filtros.
    """
    
    def __init__(self, config: Dict):
        """Inicializar motor de deep learning."""
        super().__init__("deep_learning", config)
        
        if not PYTORCH_AVAILABLE and not TENSORFLOW_AVAILABLE:
            raise ImportError(
                "PyTorch o TensorFlow requeridos para DeepLearningEngine. "
                "Instala con: pip install torch>=2.0.0 o pip install tensorflow>=2.13.0"
            )
        
        self.architecture = config.get("architecture", "lstm")  # lstm, gru, transformer
        self.backend = config.get("backend", "pytorch")  # pytorch, tensorflow
        
        # Hyperparámetros
        self.sequence_length = config.get("sequence_length", 60)  # Ventana de tiempo
        self.hidden_size = config.get("hidden_size", 64)
        self.num_layers = config.get("num_layers", 2)
        self.dropout = config.get("dropout", 0.2)
        self.learning_rate = config.get("learning_rate", 0.001)
        self.batch_size = config.get("batch_size", 32)
        self.epochs = config.get("epochs", 50)
        
        # Features
        self.feature_columns = config.get("feature_columns", [
            'price', 'volume', 'rsi', 'ema_fast', 'ema_slow', 'momentum', 'atr'
        ])
        
        self.scaler = None  # Para normalizar datos
    
    def train(
        self,
        training_data: Dict[str, Any],
        validation_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Entrenar modelo de deep learning.
        
        Args:
            training_data: {
                'sequences': np.array shape (n_samples, sequence_length, n_features),
                'labels': np.array shape (n_samples,),  # Precio futuro, dirección, etc.
                'raw_data': pd.DataFrame  # Datos originales (opcional)
            }
        """
        if not PYTORCH_AVAILABLE and not TENSORFLOW_AVAILABLE:
            raise ImportError("PyTorch o TensorFlow requeridos")
        
        sequences = training_data['sequences']
        labels = training_data['labels']
        
        # Normalizar datos
        sequences, labels, scaler = self._normalize_data(sequences, labels)
        self.scaler = scaler
        
        input_size = sequences.shape[2]
        output_size = 1 if labels.ndim == 1 else labels.shape[1]
        
        # Preparar datasets
        train_dataset = TimeSeriesDataset(sequences, labels)
        train_loader = DataLoader(train_dataset, batch_size=self.batch_size, shuffle=True)
        
        val_loader = None
        if validation_data:
            val_sequences = validation_data['sequences']
            val_labels = validation_data['labels']
            val_sequences, val_labels, _ = self._normalize_data(val_sequences, val_labels)
            val_dataset = TimeSeriesDataset(val_sequences, val_labels)
            val_loader = DataLoader(val_dataset, batch_size=self.batch_size)
        
        # Crear modelo
        if not PYTORCH_AVAILABLE:
            raise ImportError("PyTorch requerido para entrenar modelos Deep Learning")
        
        if self.architecture == "lstm":
            self.model = LSTMModel(input_size, self.hidden_size, self.num_layers, output_size, self.dropout)
        elif self.architecture == "gru":
            self.model = GRUModel(input_size, self.hidden_size, self.num_layers, output_size, self.dropout)
        else:
            raise ValueError(f"Arquitectura {self.architecture} no soportada aún")
        
        # Entrenar
        criterion = nn.BCELoss() if output_size == 1 else nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)
        
        metrics = {'train_loss': [], 'val_loss': []}
        
        for epoch in range(self.epochs):
            # Training
            train_loss = 0.0
            self.model.train()
            for batch_x, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = self.model(batch_x)
                loss = criterion(outputs, batch_y.unsqueeze(1) if batch_y.ndim == 1 else batch_y)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()
            
            train_loss /= len(train_loader)
            metrics['train_loss'].append(train_loss)
            
            # Validation
            if val_loader:
                val_loss = 0.0
                self.model.eval()
                with torch.no_grad():
                    for batch_x, batch_y in val_loader:
                        outputs = self.model(batch_x)
                        loss = criterion(outputs, batch_y.unsqueeze(1) if batch_y.ndim == 1 else batch_y)
                        val_loss += loss.item()
                
                val_loss /= len(val_loader)
                metrics['val_loss'].append(val_loss)
            
            if (epoch + 1) % 10 == 0:
                logger.info(f"Epoch {epoch+1}/{self.epochs}, Train Loss: {train_loss:.4f}, Val Loss: {val_loss if val_loader else 'N/A'}")
        
        self.is_trained = True
        return {
            'final_train_loss': metrics['train_loss'][-1],
            'final_val_loss': metrics['val_loss'][-1] if metrics['val_loss'] else None,
            'min_val_loss': min(metrics['val_loss']) if metrics['val_loss'] else None
        }
    
    def _normalize_data(self, sequences, labels):
        """Normalizar secuencias y labels."""
        # Normalizar por feature
        sequences_norm = sequences.copy()
        for i in range(sequences.shape[2]):
            feature_data = sequences[:, :, i]
            mean = feature_data.mean()
            std = feature_data.std() + 1e-8
            sequences_norm[:, :, i] = (feature_data - mean) / std
        
        # Normalizar labels si son continuos
        if labels is not None and labels.dtype in [np.float32, np.float64]:
            label_mean = labels.mean()
            label_std = labels.std() + 1e-8
            labels_norm = (labels - label_mean) / label_std
            scaler = {'mean': label_mean, 'std': label_std}
        else:
            labels_norm = labels
            scaler = None
        
        return sequences_norm, labels_norm, scaler
    
    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predecir movimiento futuro.
        
        Args:
            features: {
                'sequence': np.array shape (sequence_length, n_features),  # Última ventana de tiempo
                'market_context': Dict
            }
        
        Returns:
            {
                'predicted_direction': float,  # 0=bajista, 1=alcista
                'predicted_price_change': float,  # Cambio porcentual predicho
                'confidence': float,
                'filter_adjustments': Dict  # Ajustes sugeridos para filtros
            }
        """
        if not self.is_ready():
            return {'predicted_direction': 0.5, 'predicted_price_change': 0.0, 'confidence': 0.0}
        
        sequence = features['sequence']
        
        # Normalizar
        if self.scaler:
            sequence_norm, _, _ = self._normalize_data(
                sequence.reshape(1, *sequence.shape), None
            )
            sequence = sequence_norm[0]
        
        # Predecir
        self.model.eval()
        with torch.no_grad():
            sequence_t = torch.FloatTensor([sequence])
            prediction = self.model(sequence_t).item()
        
        # Desnormalizar si es necesario
        if self.scaler and 'mean' in self.scaler:
            prediction = prediction * self.scaler['std'] + self.scaler['mean']
        
        # Generar ajustes de filtros basados en predicción
        filter_adjustments = self._suggest_filter_adjustments(prediction)
        
        return {
            'predicted_direction': float(prediction),
            'predicted_price_change': float(prediction - 0.5) * 2,  # Normalizar a -1 a 1
            'confidence': abs(prediction - 0.5) * 2,
            'filter_adjustments': filter_adjustments
        }
    
    def _suggest_filter_adjustments(self, prediction: float) -> Dict[str, float]:
        """Sugerir ajustes de filtros basados en predicción."""
        adjustments = {}
        
        # Si predicción es muy alcista, relajar filtros de compra
        if prediction > 0.7:
            adjustments['rsi_buy_min'] = -5  # Reducir threshold
            adjustments['momentum_threshold'] = -0.005  # Reducir
        elif prediction < 0.3:
            adjustments['rsi_buy_min'] = +5  # Aumentar threshold (ser más estricto)
            adjustments['momentum_threshold'] = +0.005
        
        return adjustments
    
    def evaluate(self, test_data: Dict[str, Any]) -> Dict[str, float]:
        """Evaluar modelo en datos de prueba."""
        sequences = test_data['sequences']
        labels = test_data['labels']
        
        sequences, labels, _ = self._normalize_data(sequences, labels)
        dataset = TimeSeriesDataset(sequences, labels)
        loader = DataLoader(dataset, batch_size=self.batch_size)
        
        self.model.eval()
        predictions = []
        true_labels = []
        
        with torch.no_grad():
            for batch_x, batch_y in loader:
                outputs = self.model(batch_x)
                predictions.extend(outputs.cpu().numpy().flatten())
                true_labels.extend(batch_y.cpu().numpy().flatten())
        
        # Calcular métricas
        predictions = np.array(predictions)
        true_labels = np.array(true_labels)
        
        # RMSE para regresión
        rmse = np.sqrt(np.mean((predictions - true_labels) ** 2))
        
        # Accuracy para clasificación (si labels son binarios)
        if len(np.unique(true_labels)) <= 2:
            pred_binary = (predictions >= 0.5).astype(int)
            accuracy = np.mean(pred_binary == true_labels)
            return {'rmse': float(rmse), 'accuracy': float(accuracy)}
        
        return {'rmse': float(rmse)}

