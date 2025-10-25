"""
Refactored Portfolio Service - TASK-15: Refactorización de Servicios

Este módulo implementa el servicio de portafolio refactorizado,
utilizando el gestor centralizado de circuit breakers y el gestor de riesgos.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from app.models.portfolio import (
    Portfolio, Position, AssetUniverse, MarketRegimeData,
    CircuitBreaker, CircuitBreakerState, PortfolioProvider
)
from app.services.circuit_breaker_manager import CircuitBreakerManager, CircuitBreakerType
from app.services.portfolio_risk_manager import PortfolioRiskManager
from app.providers.paper_trading import PaperTradingPortfolioProvider

logger = logging.getLogger(__name__)


class PortfolioService:
    """Servicio de portafolio refactorizado con gestión centralizada de riesgos."""
    
    def __init__(self, provider: PortfolioProvider):
        """Inicializar servicio refactorizado."""
        self.provider = provider
        
        # Gestores especializados
        self.circuit_breaker_manager = CircuitBreakerManager()
        self.risk_manager = PortfolioRiskManager()
        
        # Métricas de rendimiento
        self.operations_count = 0
        self.successful_operations = 0
        self.failed_operations = 0
        self.last_operation_time: Optional[datetime] = None
    
    async def get_portfolio(self) -> Optional[Portfolio]:
        """Obtener portafolio con protección de circuit breaker."""
        try:
            # Verificar circuit breaker de API
            if self.circuit_breaker_manager.is_breaker_open(CircuitBreakerType.API_ERRORS.value):
                logger.warning("API circuit breaker is open, skipping portfolio fetch")
                return None
            
            # Obtener portafolio del provider
            portfolio = await self.provider.get_portfolio()
            
            if portfolio:
                # Registrar éxito
                self.circuit_breaker_manager.record_success(CircuitBreakerType.API_ERRORS.value)
                self.successful_operations += 1
                
                # Evaluar riesgo del portafolio
                risk_assessment = self.risk_manager.assess_portfolio_risk(portfolio)
                
                logger.debug(f"Portfolio retrieved: {portfolio.portfolio_id}, risk level: {risk_assessment['risk_level']}")
            else:
                logger.warning("Provider returned None portfolio")
            
            self.operations_count += 1
            self.last_operation_time = datetime.utcnow()
            
            return portfolio
            
        except Exception as e:
            # Registrar error en circuit breaker
            self.circuit_breaker_manager.record_error(
                CircuitBreakerType.API_ERRORS.value, 
                str(e)
            )
            self.failed_operations += 1
            
            logger.error(f"Error getting portfolio: {e}")
            return None
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Obtener posición con protección de circuit breaker."""
        try:
            if self.circuit_breaker_manager.is_breaker_open(CircuitBreakerType.API_ERRORS.value):
                return None
            
            position = await self.provider.get_position(symbol)
            
            if position:
                self.circuit_breaker_manager.record_success(CircuitBreakerType.API_ERRORS.value)
                self.successful_operations += 1
            else:
                self.failed_operations += 1
            
            self.operations_count += 1
            return position
            
        except Exception as e:
            self.circuit_breaker_manager.record_error(
                CircuitBreakerType.API_ERRORS.value, 
                str(e)
            )
            self.failed_operations += 1
            
            logger.error(f"Error getting position {symbol}: {e}")
            return None
    
    async def add_position(self, position: Position) -> bool:
        """Agregar posición al portafolio con evaluación de riesgo."""
        try:
            # Obtener portafolio actual
            portfolio = await self.get_portfolio()
            if not portfolio:
                logger.warning("No portfolio available for adding position")
                return False
            
            # Evaluar riesgo con nueva posición
            risk_assessment = self.risk_manager.assess_portfolio_risk(portfolio, position)
            
            # Verificar si hay violaciones críticas
            critical_violations = [
                v for v in risk_assessment["violations"] 
                if v["severity"] == "critical"
            ]
            
            if critical_violations:
                logger.warning(f"Cannot add position {position.symbol}: critical risk violations detected")
                return False
            
            # Agregar posición
            success = await self.provider.add_position(position)
            
            if success:
                self.successful_operations += 1
                logger.info(f"Position added: {position.symbol}")
            else:
                self.failed_operations += 1
            
            self.operations_count += 1
            return success
            
        except Exception as e:
            self.failed_operations += 1
            logger.error(f"Error adding position {position.symbol}: {e}")
            return False
    
    async def update_position(self, position: Position) -> bool:
        """Actualizar posición con evaluación de riesgo."""
        try:
            # Obtener portafolio actual
            portfolio = await self.get_portfolio()
            if not portfolio:
                logger.warning("No portfolio available for updating position")
                return False
            
            # Evaluar riesgo con posición actualizada
            risk_assessment = self.risk_manager.assess_portfolio_risk(portfolio, position)
            
            # Verificar violaciones críticas
            critical_violations = [
                v for v in risk_assessment["violations"] 
                if v["severity"] == "critical"
            ]
            
            if critical_violations:
                logger.warning(f"Cannot update position {position.symbol}: critical risk violations detected")
                return False
            
            # Actualizar posición
            success = await self.provider.update_position(position)
            
            if success:
                self.successful_operations += 1
                logger.info(f"Position updated: {position.symbol}")
            else:
                self.failed_operations += 1
            
            self.operations_count += 1
            return success
            
        except Exception as e:
            self.failed_operations += 1
            logger.error(f"Error updating position {position.symbol}: {e}")
            return False
    
    async def remove_position(self, symbol: str) -> bool:
        """Remover posición del portafolio."""
        try:
            success = await self.provider.remove_position(symbol)
            
            if success:
                self.successful_operations += 1
                logger.info(f"Position removed: {symbol}")
            else:
                self.failed_operations += 1
            
            self.operations_count += 1
            return success
            
        except Exception as e:
            self.failed_operations += 1
            logger.error(f"Error removing position {symbol}: {e}")
            return False
    
    async def simulate_trade(
        self, 
        symbol: str, 
        quantity: Decimal, 
        price: Decimal
    ) -> bool:
        """Simular trade con evaluación de riesgo."""
        try:
            # Crear posición temporal para evaluación
            temp_position = Position(
                symbol=symbol,
                quantity=quantity,
                market_value=quantity * price,
                cost_basis=price,
                unrealized_pnl=Decimal("0")
            )
            
            # Obtener portafolio actual
            portfolio = await self.get_portfolio()
            if not portfolio:
                logger.warning("No portfolio available for trade simulation")
                return False
            
            # Evaluar riesgo con nueva posición
            risk_assessment = self.risk_manager.assess_portfolio_risk(portfolio, temp_position)
            
            # Verificar violaciones críticas
            critical_violations = [
                v for v in risk_assessment["violations"] 
                if v["severity"] == "critical"
            ]
            
            if critical_violations:
                logger.warning(f"Cannot execute trade for {symbol}: critical risk violations detected")
                return False
            
            # Simular trade
            success = await self.provider.simulate_trade(symbol, quantity, price)
            
            if success:
                self.successful_operations += 1
                logger.info(f"Trade simulated: {symbol} {quantity} @ {price}")
            else:
                self.failed_operations += 1
            
            self.operations_count += 1
            return success
            
        except Exception as e:
            self.failed_operations += 1
            logger.error(f"Error simulating trade for {symbol}: {e}")
            return False
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del servicio."""
        # Estadísticas del servicio principal
        service_stats = {
            "operations_count": self.operations_count,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "success_rate": (
                self.successful_operations / self.operations_count 
                if self.operations_count > 0 else 0.0
            ),
            "last_operation_time": self.last_operation_time
        }
        
        # Estadísticas de los gestores
        circuit_breaker_stats = self.circuit_breaker_manager.get_manager_statistics()
        risk_stats = self.risk_manager.get_risk_statistics()
        
        return {
            "service": service_stats,
            "circuit_breaker_manager": circuit_breaker_stats,
            "risk_manager": risk_stats
        }
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Obtener estado de circuit breakers."""
        return self.circuit_breaker_manager.get_all_breaker_statuses()
    
    def get_risk_assessment(self, portfolio: Portfolio) -> Dict[str, Any]:
        """Obtener evaluación de riesgo del portafolio."""
        return self.risk_manager.assess_portfolio_risk(portfolio)
    
    def reset_circuit_breakers(self) -> None:
        """Resetear circuit breakers."""
        self.circuit_breaker_manager.reset_all_breakers()
        logger.info("Reset all circuit breakers")
    
    def reset_statistics(self) -> None:
        """Resetear estadísticas."""
        self.operations_count = 0
        self.successful_operations = 0
        self.failed_operations = 0
        self.last_operation_time = None
        
        # Resetear gestores
        self.circuit_breaker_manager.clear_history()
        self.risk_manager.clear_history()
        
        logger.info("Reset portfolio service statistics")