"""
StrategyConfigLoader - Cargador de configuración de estrategias.

Permite cargar configuración de estrategias desde archivos YAML/JSON,
validar la configuración y proporcionar acceso a parámetros específicos.
"""

import yaml
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class StrategyConfigLoader:
    """Cargador de configuración de estrategias."""
    
    def __init__(self, config_path: str = "config/trading_strategies.yaml"):
        """
        Inicializar cargador de configuración.
        
        Args:
            config_path: Ruta al archivo de configuración
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.last_loaded: Optional[datetime] = None
        self._validate_config_path()
    
    def _validate_config_path(self) -> None:
        """Validar que la ruta de configuración sea válida."""
        if not self.config_path.parent.exists():
            logger.warning(f"Config directory does not exist: {self.config_path.parent}")
            logger.info(f"Creating config directory: {self.config_path.parent}")
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> Dict[str, Any]:
        """
        Cargar configuración desde archivo.
        
        Returns:
            Diccionario con la configuración cargada
            
        Raises:
            FileNotFoundError: Si el archivo no existe
            ValueError: Si el formato del archivo no es soportado
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        try:
            if self.config_path.suffix in ['.yaml', '.yml']:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
            elif self.config_path.suffix == '.json':
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {self.config_path.suffix}")
            
            self.last_loaded = datetime.utcnow()
            logger.info(f"Loaded config from: {self.config_path}")
            
            # Validar configuración básica
            if not self.validate_config():
                logger.warning("Config validation failed, but continuing...")
            
            return self.config
            
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {str(e)}")
            raise
    
    def save_config(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Guardar configuración en archivo.
        
        Args:
            config: Configuración a guardar (usa self.config si no se proporciona)
        """
        if config is None:
            config = self.config
        
        try:
            if self.config_path.suffix in ['.yaml', '.yml']:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, indent=2)
            elif self.config_path.suffix == '.json':
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
            
            logger.info(f"Saved config to: {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {str(e)}")
            raise
    
    def get_active_strategies(self) -> List[str]:
        """
        Obtener estrategias activas.
        
        Returns:
            Lista de nombres de estrategias activas
        """
        return self.config.get("active_strategies", [])
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """
        Obtener configuración de estrategia específica.
        
        Args:
            strategy_name: Nombre de la estrategia
            
        Returns:
            Configuración de la estrategia
            
        Raises:
            ValueError: Si la estrategia no existe en la configuración
        """
        strategies = self.config.get("strategies", {})
        if strategy_name not in strategies:
            available = list(strategies.keys())
            raise ValueError(f"Strategy '{strategy_name}' not found in config. Available: {available}")
        
        return strategies[strategy_name]
    
    def get_backtesting_strategies(self) -> List[str]:
        """
        Obtener estrategias para backtesting.
        
        Returns:
            Lista de nombres de estrategias para backtesting
        """
        return self.config.get("backtesting_strategies", [])
    
    def get_paper_trading_strategy(self) -> str:
        """
        Obtener estrategia para paper trading.
        
        Returns:
            Nombre de la estrategia para paper trading
        """
        return self.config.get("paper_trading_strategy", "")
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Obtener configuración de logging.
        
        Returns:
            Configuración de logging
        """
        return self.config.get("logging", {
            "level": "INFO",
            "log_path": "logs/strategy_logs.json",
            "max_log_size": "10MB",
            "backup_count": 5
        })
    
    def validate_config(self) -> bool:
        """
        Validar configuración.
        
        Returns:
            True si la configuración es válida, False en caso contrario
        """
        required_keys = ["strategies"]
        
        # Verificar claves requeridas
        if not all(key in self.config for key in required_keys):
            logger.error(f"Missing required config keys: {required_keys}")
            return False
        
        # Verificar que strategies sea un diccionario
        if not isinstance(self.config["strategies"], dict):
            logger.error("'strategies' must be a dictionary")
            return False
        
        # Verificar cada estrategia
        for strategy_name, strategy_config in self.config["strategies"].items():
            if not isinstance(strategy_config, dict):
                logger.error(f"Strategy '{strategy_name}' config must be a dictionary")
                return False
            
            # Verificar configuración mínima de estrategia
            if "config" not in strategy_config:
                logger.error(f"Strategy '{strategy_name}' missing 'config' section")
                return False
        
        logger.info("Config validation passed")
        return True
    
    def add_strategy_config(self, strategy_name: str, strategy_config: Dict[str, Any]) -> None:
        """
        Añadir configuración de estrategia.
        
        Args:
            strategy_name: Nombre de la estrategia
            strategy_config: Configuración de la estrategia
        """
        if "strategies" not in self.config:
            self.config["strategies"] = {}
        
        self.config["strategies"][strategy_name] = strategy_config
        logger.info(f"Added strategy config: {strategy_name}")
    
    def remove_strategy_config(self, strategy_name: str) -> None:
        """
        Remover configuración de estrategia.
        
        Args:
            strategy_name: Nombre de la estrategia a remover
        """
        if "strategies" in self.config and strategy_name in self.config["strategies"]:
            del self.config["strategies"][strategy_name]
            logger.info(f"Removed strategy config: {strategy_name}")
        else:
            logger.warning(f"Strategy config not found: {strategy_name}")
    
    def update_strategy_config(self, strategy_name: str, updates: Dict[str, Any]) -> None:
        """
        Actualizar configuración de estrategia.
        
        Args:
            strategy_name: Nombre de la estrategia
            updates: Actualizaciones a aplicar
        """
        if strategy_name not in self.config.get("strategies", {}):
            raise ValueError(f"Strategy '{strategy_name}' not found in config")
        
        # Actualizar configuración
        strategy_config = self.config["strategies"][strategy_name]
        if "config" in strategy_config:
            strategy_config["config"].update(updates)
        else:
            strategy_config["config"] = updates
        
        logger.info(f"Updated strategy config: {strategy_name}")
    
    def reload_config(self) -> Dict[str, Any]:
        """
        Recargar configuración desde archivo.
        
        Returns:
            Configuración recargada
        """
        logger.info("Reloading config...")
        return self.load_config()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Obtener resumen de la configuración.
        
        Returns:
            Resumen de la configuración
        """
        strategies = self.config.get("strategies", {})
        
        return {
            "config_path": str(self.config_path),
            "last_loaded": self.last_loaded.isoformat() if self.last_loaded else None,
            "total_strategies": len(strategies),
            "strategy_names": list(strategies.keys()),
            "active_strategies": self.get_active_strategies(),
            "backtesting_strategies": self.get_backtesting_strategies(),
            "paper_trading_strategy": self.get_paper_trading_strategy(),
            "is_valid": self.validate_config()
        }
    
    def __str__(self) -> str:
        """Representación string del loader."""
        return f"StrategyConfigLoader(path={self.config_path})"
    
    def __repr__(self) -> str:
        """Representación detallada del loader."""
        return (f"StrategyConfigLoader("
                f"path={self.config_path}, "
                f"loaded={self.last_loaded is not None}, "
                f"strategies={len(self.config.get('strategies', {}))})")
