"""
BaseStrategy - Clase base abstracta para todas las estrategias de trading.

Implementa la interfaz común que todas las estrategias deben seguir,
permitiendo hot-swapping y gestión dinámica de estrategias.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime

from app.models.market_data import Quote
from app.models.signal import Signal
from app.models.portfolio import Portfolio


class BaseStrategy(ABC):
    """Clase base abstracta para todas las estrategias de trading."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar estrategia con configuración.
        
        Args:
            config: Diccionario con parámetros de configuración
        """
        self.config = config
        self.name = config.get("name", self.__class__.__name__)
        self.description = config.get("description", "")
        self.version = config.get("version", "1.0.0")
        self.is_active = False
        self.created_at = datetime.utcnow()
        
    @abstractmethod
    def generate_signals(self, market_data: Quote) -> List[Signal]:
        """
        Genera señales de trading basadas en datos del mercado.
        
        Args:
            market_data: Datos de mercado actuales
            
        Returns:
            Lista de señales generadas
        """
        pass
    
    @abstractmethod
    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """
        Verifica si la señal cumple criterios de riesgo.
        
        Args:
            signal: Señal a verificar
            portfolio: Estado actual del portfolio
            
        Returns:
            True si la señal pasa el risk check, False en caso contrario
        """
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        Obtener parámetros actuales de la estrategia.
        
        Returns:
            Copia del diccionario de configuración
        """
        return self.config.copy()
    
    def update_parameters(self, params: Dict[str, Any]) -> None:
        """
        Actualizar parámetros dinámicamente.
        
        Args:
            params: Nuevos parámetros a aplicar
        """
        self.config.update(params)
    
    def validate_config(self) -> bool:
        """
        Validar configuración de la estrategia.
        
        Returns:
            True si la configuración es válida, False en caso contrario
        """
        required_params = self.get_required_parameters()
        return all(param in self.config for param in required_params)
    
    @abstractmethod
    def get_required_parameters(self) -> List[str]:
        """
        Obtener parámetros requeridos para la estrategia.
        
        Returns:
            Lista de nombres de parámetros requeridos
        """
        pass
    
    def get_position_size(self, signal: Signal, portfolio: Portfolio) -> Decimal:
        """
        Calcular tamaño de posición basado en la señal y portfolio.
        
        Args:
            signal: Señal de trading
            portfolio: Estado del portfolio
            
        Returns:
            Tamaño de posición calculado
        """
        max_position_size = Decimal(str(self.config.get("max_position_size", 0.1)))
        available_cash = portfolio.cash
        
        if signal.direction == "buy":
            # Para compras, limitar por cash disponible
            max_shares = available_cash / signal.price
            return min(signal.quantity, max_shares * max_position_size)
        else:
            # Para ventas, usar cantidad de la señal
            return signal.quantity
    
    def get_stop_loss_price(self, signal: Signal) -> Optional[Decimal]:
        """
        Calcular precio de stop loss.
        
        Args:
            signal: Señal de trading
            
        Returns:
            Precio de stop loss o None si no aplica
        """
        stop_loss_pct = Decimal(str(self.config.get("stop_loss", 0.05)))
        
        if signal.direction == "buy":
            return signal.price * (1 - stop_loss_pct)
        elif signal.direction == "sell":
            return signal.price * (1 + stop_loss_pct)
        
        return None
    
    def get_take_profit_price(self, signal: Signal) -> Optional[Decimal]:
        """
        Calcular precio de take profit.
        
        Args:
            signal: Señal de trading
            
        Returns:
            Precio de take profit o None si no aplica
        """
        take_profit_pct = Decimal(str(self.config.get("take_profit", 0.10)))
        
        if signal.direction == "buy":
            return signal.price * (1 + take_profit_pct)
        elif signal.direction == "sell":
            return signal.price * (1 - take_profit_pct)
        
        return None
    
    def __str__(self) -> str:
        """Representación string de la estrategia."""
        return f"{self.__class__.__name__}(name={self.name}, active={self.is_active})"
    
    def __repr__(self) -> str:
        """Representación detallada de la estrategia."""
        return (f"{self.__class__.__name__}("
                f"name='{self.name}', "
                f"version='{self.version}', "
                f"active={self.is_active}, "
                f"created_at={self.created_at})")
