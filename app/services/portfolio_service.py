"""
Refactored Portfolio Service - TASK-15: Refactorización de Servicios

Este módulo implementa el servicio de portafolio refactorizado,
utilizando el gestor centralizado de circuit breakers y el gestor de riesgos.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.shared.config.centralized_config import get_config
from app.domain.models.portfolio import (
    AssetClass,
    AssetUniverse,
    MarketRegime,
    MarketRegimeData,
    Portfolio,
    PortfolioProvider,
    Position,
)
from app.services.api_circuit_breaker import (
    CircuitBreakerManager,
    CircuitBreakerType,
)
from app.services.country_diversification_validator import CountryDiversificationValidator
from app.services.currency_hedging_engine import CurrencyHedgingEngine
from app.services.portfolio_risk_manager import PortfolioRiskManager
from app.services.sector_diversification_validator import SectorDiversificationValidator

logger = logging.getLogger(__name__)


class PortfolioService:
    """Servicio de portafolio refactorizado con gestión centralizada de riesgos."""

    def __init__(self, provider: PortfolioProvider):
        """Inicializar servicio refactorizado."""
        self.provider = provider

        # Gestores especializados
        self.circuit_breaker_manager = CircuitBreakerManager()
        self.risk_manager = PortfolioRiskManager()
        self.hedging_engine = CurrencyHedgingEngine()  # [TASK-5.5]

        # Validators [TASK-5.6]
        config = get_config()
        self.sector_validator = SectorDiversificationValidator(config.diversification)
        self.country_validator = CountryDiversificationValidator(config.diversification)

        # Acceso directo a circuit breakers para compatibilidad con tests
        self.circuit_breakers = self.circuit_breaker_manager.circuit_breakers

        # Métricas de rendimiento
        self.operations_count = 0
        self.successful_operations = 0
        self.failed_operations = 0
        self.last_operation_time: Optional[datetime] = None

        # Hedging tracking [TASK-5.5]
        self.total_hedges_created = 0
        self.total_hedge_cost = Decimal("0")

        # Diversification tracking [TASK-5.6]
        self.diversification_breaches = 0
        self.rebalancing_actions = 0

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

                logger.debug(
                    f"Portfolio retrieved: {portfolio.portfolio_id}, risk level: {risk_assessment['risk_level']}"
                )
            else:
                logger.warning("Provider returned None portfolio")

            self.operations_count += 1
            self.last_operation_time = datetime.utcnow()

            return portfolio

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            # Registrar error en circuit breaker
            self.circuit_breaker_manager.record_error(CircuitBreakerType.API_ERRORS.value, str(e))
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

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            self.circuit_breaker_manager.record_error(CircuitBreakerType.API_ERRORS.value, str(e))
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
                v for v in risk_assessment["violations"] if v["severity"] == "critical"
            ]

            if critical_violations:
                logger.warning(
                    f"Cannot add position {position.symbol}: critical risk violations detected"
                )
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

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
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
                v for v in risk_assessment["violations"] if v["severity"] == "critical"
            ]

            if critical_violations:
                logger.warning(
                    f"Cannot update position {position.symbol}: critical risk violations detected"
                )
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

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
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

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            self.failed_operations += 1
            logger.error(f"Error removing position {symbol}: {e}")
            return False

    async def simulate_trade(self, symbol: str, quantity: Decimal, price: Decimal) -> bool:
        """Simular trade con evaluación de riesgo."""
        try:
            # Crear posición temporal para evaluación
            temp_position = Position(
                symbol=symbol,
                asset_class=self._get_asset_class(symbol),
                quantity=quantity,
                avg_price=price,
                market_price=price,
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                currency="USD",
                broker="paper_trading",
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
                v for v in risk_assessment["violations"] if v["severity"] == "critical"
            ]

            if critical_violations:
                logger.warning(
                    f"Cannot execute trade for {symbol}: critical risk violations detected"
                )
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

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
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
                if self.operations_count > 0
                else 0.0
            ),
            "last_operation_time": self.last_operation_time,
        }

        # Estadísticas de los gestores
        circuit_breaker_stats = self.circuit_breaker_manager.get_manager_statistics()
        risk_stats = self.risk_manager.get_risk_statistics()

        return {
            "service": service_stats,
            "circuit_breaker_manager": circuit_breaker_stats,
            "risk_manager": risk_stats,
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

    def reset_circuit_breaker(self, breaker_name: str) -> bool:
        """Resetear un circuit breaker específico."""
        return self.circuit_breaker_manager.reset_breaker(breaker_name)

    def get_portfolio_summary(self, portfolio: Portfolio) -> Dict[str, Any]:
        """Obtener resumen del portafolio."""
        return {
            "portfolio_id": portfolio.portfolio_id,
            "total_value": portfolio.total_value,
            "cash": portfolio.cash,
            "positions_count": len(portfolio.positions),
            "total_pnl": portfolio.total_pnl,
            "total_pnl_percentage": portfolio.total_pnl_percentage,
            "timestamp": portfolio.timestamp,
            "broker": portfolio.broker,
            "currency": portfolio.currency,
        }

    async def get_asset_universe(self) -> List[AssetUniverse]:
        """Obtener universo de activos soportados."""
        # Get asset universe configuration from config
        config = get_config()
        tt = config.trading

        equity_max_spread = Decimal(str(getattr(
            tt, 'asset_universe_equity_max_spread', 0.01
        )))
        equity_min_volume = Decimal(str(getattr(
            tt, 'asset_universe_equity_min_volume', 1000000
        )))
        crypto_max_spread = Decimal(str(getattr(
            tt, 'asset_universe_crypto_max_spread', 0.005
        )))
        crypto_min_volume = Decimal(str(getattr(
            tt, 'asset_universe_crypto_min_volume', 10000000
        )))

        # Mock data para testing - en producción vendría de una fuente real
        return [
            AssetUniverse(
                broker="paper_trading",
                asset_class=AssetClass.EQUITY,
                symbols=["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"],
                min_volume=equity_min_volume,
                max_spread=equity_max_spread,
            ),
            AssetUniverse(
                broker="paper_trading",
                asset_class=AssetClass.CRYPTO,
                symbols=["BTCUSDT", "ETHUSDT", "ADAUSDT"],
                min_volume=crypto_min_volume,
                max_spread=crypto_max_spread,
            ),
        ]

    async def get_market_regime(self, symbol: str) -> Optional[MarketRegimeData]:
        """Obtener datos de régimen de mercado para un símbolo."""
        # Lista de símbolos soportados para testing
        supported_symbols = [
            "AAPL",
            "GOOGL",
            "MSFT",
            "TSLA",
            "AMZN",
            "BTCUSDT",
            "ETHUSDT",
        ]

        if symbol.upper() not in supported_symbols:
            return None

        # Get market regime defaults from config
        config = get_config()
        tt = config.trading

        default_confidence = getattr(tt, 'market_regime_default_confidence', 0.75)
        default_atr_ratio = getattr(tt, 'market_regime_default_atr_ratio', 0.02)
        default_trend_strength = getattr(tt, 'market_regime_default_trend_strength', 0.3)
        default_volatility_level = getattr(tt, 'market_regime_default_volatility_level', 0.25)

        # Mock data para testing - en producción vendría de análisis real
        return MarketRegimeData(
            regime=MarketRegime.RANGING,
            confidence=default_confidence,
            atr_ratio=default_atr_ratio,
            trend_strength=default_trend_strength,
            volatility_level=default_volatility_level,
            timestamp=datetime.now(),
        )

    def get_unhedged_currency_exposure(self, portfolio: Portfolio) -> Dict[str, Decimal]:
        """
        Get current unhedged currency exposure [TASK-5.5].

        Returns:
            Dict[currency, exposure_amount]: Unhedged exposure per currency
        """
        try:
            currency_exp = self.hedging_engine.calculate_currency_exposure(portfolio)
            logger.debug(f"Unhedged FX exposure: {currency_exp}")
            return currency_exp
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.warning(f"Failed to calculate currency exposure: {e}")
            return {}

    def get_hedging_statistics(self) -> Dict[str, Any]:
        """Get hedging statistics [TASK-5.5]."""
        return {
            "total_hedges_created": self.total_hedges_created,
            "total_hedge_cost_bps": float(self.total_hedge_cost),
            "hedging_engine_stats": self.hedging_engine.get_statistics(),
        }

    async def apply_auto_hedging(self, portfolio: Portfolio) -> Dict[str, Any]:
        """
        Apply automatic hedging to portfolio [TASK-5.5].

        Returns:
            Dict with hedging results (recommendations, created hedges, etc.)
        """
        try:
            # Get hedge recommendations
            recommendations = self.hedging_engine.calculate_hedge_recommendations(portfolio)

            logger.info(f"Generated {len(recommendations)} hedge recommendations")

            # Track statistics
            for rec in recommendations:
                self.total_hedges_created += 1
                self.total_hedge_cost += rec.estimated_cost_bps

            return {
                "success": True,
                "recommendations_count": len(recommendations),
                "recommendations": [r.model_dump() for r in recommendations],
                "total_cost_bps": float(sum(r.estimated_cost_bps for r in recommendations)),
            }
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Failed to apply auto-hedging: {e}")
            return {
                "success": False,
                "error": str(e),
                "recommendations_count": 0,
            }

    def get_sector_allocation(self) -> Dict[str, Decimal]:
        """Get current sector allocation [TASK-5.6]."""
        # This would be called with current portfolio
        # For now, return empty dict as it requires current portfolio instance
        return {}

    def get_country_allocation(self) -> Dict[str, Decimal]:
        """Get current country allocation [TASK-5.6]."""
        # This would be called with current portfolio
        # For now, return empty dict as it requires current portfolio instance
        return {}

    def get_diversification_status(self, portfolio: Portfolio) -> Dict[str, Any]:
        """Get sector and country diversification status [TASK-5.6]."""
        sector_stats = self.sector_validator.get_sector_statistics(portfolio)
        country_stats = self.country_validator.get_country_statistics(portfolio)

        return {
            "sectors": sector_stats,
            "countries": country_stats,
            "total_diversification_breaches": self.diversification_breaches,
            "rebalancing_actions_taken": self.rebalancing_actions,
        }

    def suggest_rebalancing(self, portfolio: Portfolio) -> Dict[str, List]:
        """Get sector and country rebalancing suggestions [TASK-5.6]."""
        sector_suggestions = self.sector_validator.get_sector_rebalancing_suggestions(portfolio)
        country_suggestions = self.country_validator.get_country_rebalancing_suggestions(portfolio)

        return {
            "sector_suggestions": sector_suggestions,
            "country_suggestions": country_suggestions,
            "total_suggestions": len(sector_suggestions) + len(country_suggestions),
        }

    def _get_asset_class(self, symbol: str) -> AssetClass:
        """Determine asset class based on symbol."""
        if symbol.endswith("USDT") or symbol.endswith("BTC") or symbol.endswith("ETH"):
            return AssetClass.CRYPTO
        else:
            return AssetClass.EQUITY
