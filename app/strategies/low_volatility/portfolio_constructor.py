"""
Low Volatility Portfolio Constructor - Construcción de Portafolio Optimizado

Implementa construcción de portafolio de baja volatilidad con:
- Diversificación sectorial
- Optimización de varianza mínima
- Respeto a límites de concentración
- Minimización de volatilidad del portafolio

SOLID Principles:
- Single Responsibility: Solo construcción de portafolios
- Open/Closed: Extensible con nuevos métodos de optimización
- Dependency Inversion: Depende de abstracciones (models)
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np
from scipy.optimize import minimize

from .models import LowVolatilityStock, LowVolatilityStrategyConfig

logger = logging.getLogger(__name__)


@dataclass
class LowVolatilityPortfolioConfig:
    """
    Configuración de construcción de portafolio.

    Attributes:
        target_size: Tamaño objetivo del portafolio
        max_sector_weight: Peso máximo por sector
        max_single_weight: Peso máximo por acción
        min_single_weight: Peso mínimo por acción
        rebalance_threshold: Umbral para rebalanceo
        optimization_method: Método de optimización
        target_volatility: Volatilidad objetivo (opcional)
    """

    target_size: int
    max_sector_weight: Decimal
    max_single_weight: Decimal
    min_single_weight: Decimal
    rebalance_threshold: Decimal
    optimization_method: str  # min_variance, equal_weight, risk_parity
    target_volatility: Optional[Decimal]


@dataclass
class PortfolioPosition:
    """
    Posición del portafolio.

    Attributes:
        symbol: Símbolo de la acción
        weight: Peso en el portafolio (0-1)
        shares: Número de acciones
        avg_cost: Costo promedio por acción
        current_value: Valor actual de la posición
        expected_volatility: Volatilidad esperada de la posición
        beta: Beta de la posición
    """

    symbol: str
    weight: Decimal
    shares: int
    avg_cost: Decimal
    current_value: Decimal
    expected_volatility: Decimal
    beta: Decimal


@dataclass
class LowVolatilityPortfolio:
    """
    Portafolio de baja volatilidad construido.

    Attributes:
        positions: Lista de posiciones
        total_value: Valor total del portafolio
        expected_volatility: Volatilidad esperada del portafolio (%)
        sector_weights: Pesos por sector
        portfolio_beta: Beta del portafolio
        construction_metadata: Metadatos de construcción
    """

    positions: List[PortfolioPosition]
    total_value: Decimal
    expected_volatility: Decimal
    sector_weights: Dict[str, Decimal]
    portfolio_beta: Decimal
    construction_metadata: Dict[str, Any]


class LowVolatilityPortfolioConstructor:
    """
    Constructor de portafolios de baja volatilidad.

    Construye portafolios optimizados minimizando la volatilidad
    mientras mantiene diversificación y control de riesgo.

    Attributes:
        config: Configuración de la estrategia
    """

    def __init__(self, config: LowVolatilityStrategyConfig):
        """
        Inicializar constructor.

        Args:
            config: Configuración de la estrategia
        """
        self.config = config
        self.portfolio_config = LowVolatilityPortfolioConfig(
            target_size=config.portfolio_size,
            max_sector_weight=config.max_sector_weight,
            max_single_weight=config.max_single_position,
            min_single_weight=Decimal("0.01"),  # 1% mínimo
            rebalance_threshold=config.rebalance_threshold,
            optimization_method=config.optimization_method,
            target_volatility=config.target_volatility,
        )

    def construct_portfolio(
        self,
        stocks: List[LowVolatilityStock],
        total_capital: Decimal,
        returns_matrix: Optional[np.ndarray] = None,
    ) -> LowVolatilityPortfolio:
        """
        Construir portafolio óptimo desde lista de acciones.

        Args:
            stocks: Lista de acciones clasificadas
            total_capital: Capital total a invertir
            returns_matrix: Matriz de retornos para optimización (opcional)

        Returns:
            Portafolio de baja volatilidad construido
        """
        logger.info(
            f"Construyendo portafolio de baja volatilidad con {len(stocks)} acciones "
            f"y capital ${total_capital:,.2f}"
        )

        # 1. Seleccionar top N acciones
        selected = self._select_top_stocks(stocks)

        # 2. Agrupar por sector
        sector_groups = self._group_by_sector(selected)

        # 3. Calcular pesos optimizados
        if (
            returns_matrix is not None
            and self.portfolio_config.optimization_method == "min_variance"
        ):
            weights = self._calculate_min_variance_weights(selected, returns_matrix, sector_groups)
        elif self.portfolio_config.optimization_method == "risk_parity":
            weights = self._calculate_risk_parity_weights(selected, sector_groups)
        else:
            weights = self._calculate_equal_weights(selected, sector_groups)

        # 4. Crear posiciones
        positions = self._create_positions(selected, weights, total_capital)

        # 5. Calcular métricas del portafolio
        portfolio = self._build_portfolio_result(positions, selected, returns_matrix)

        logger.info(
            f"Portafolio construido: {len(portfolio.positions)} posiciones, "
            f"volatilidad esperada {portfolio.expected_volatility:.2f}%, "
            f"beta {portfolio.portfolio_beta:.2f}"
        )

        return portfolio

    def _select_top_stocks(self, stocks: List[LowVolatilityStock]) -> List[LowVolatilityStock]:
        """
        Seleccionar top N acciones por score de decisión.

        Args:
            stocks: Lista completa de acciones

        Returns:
            Top N acciones
        """
        # Ordenar por decision_score descendente
        sorted_stocks = sorted(stocks, key=lambda s: float(s.decision_score), reverse=True)

        # Tomar top N o todas si hay menos
        target_size = self.portfolio_config.target_size
        selected = sorted_stocks[:target_size]

        logger.debug(
            f"Seleccionadas {len(selected)} acciones de {len(stocks)} "
            f"(scores: {float(selected[0].decision_score):.1f} - "
            f"{float(selected[-1].decision_score):.1f})"
        )

        return selected

    def _group_by_sector(
        self, stocks: List[LowVolatilityStock]
    ) -> Dict[str, List[LowVolatilityStock]]:
        """
        Agrupar acciones por sector.

        Args:
            stocks: Lista de acciones

        Returns:
            Dict sector -> lista de acciones
        """
        groups = defaultdict(list)

        for stock in stocks:
            sector = stock.profile.sector or "Unknown"
            groups[sector].append(stock)

        logger.debug(f"Acciones agrupadas en {len(groups)} sectores")

        return dict(groups)

    def _calculate_equal_weights(
        self,
        stocks: List[LowVolatilityStock],
        sector_groups: Dict[str, List[LowVolatilityStock]],
    ) -> Dict[str, Decimal]:
        """
        Calcular pesos equal-weight con restricciones sectoriales.

        Args:
            stocks: Lista de acciones seleccionadas
            sector_groups: Grupos por sector

        Returns:
            Dict symbol -> peso (0-1)
        """
        n_stocks = len(stocks)
        if n_stocks == 0:
            return {}

        # Peso base equal-weight
        base_weight = Decimal("1.0") / Decimal(str(n_stocks))

        weights = {stock.profile.symbol: base_weight for stock in stocks}

        # Aplicar límites sectoriales iterativamente
        weights = self._enforce_sector_limits(weights, sector_groups)

        # Aplicar límites de posición
        weights = self._enforce_position_limits(weights)

        # Normalizar para que sumen 1
        weights = self._normalize_weights(weights)

        return weights

    def _calculate_min_variance_weights(
        self,
        stocks: List[LowVolatilityStock],
        returns_matrix: np.ndarray,
        sector_groups: Dict[str, List[LowVolatilityStock]],
    ) -> Dict[str, Decimal]:
        """
        Calcular pesos de varianza mínima.

        Resuelve: min w'Σw sujeto a restricciones

        Args:
            stocks: Lista de acciones
            returns_matrix: Matriz de retornos
            sector_groups: Grupos por sector

        Returns:
            Dict symbol -> peso (0-1)
        """
        n_assets = len(stocks)

        if returns_matrix is None or returns_matrix.shape[0] < 2:
            logger.warning("No returns matrix, falling back to equal weights")
            return self._calculate_equal_weights(stocks, sector_groups)

        try:
            # Matriz de covarianza
            cov_matrix = np.cov(returns_matrix)

            # Función objetivo: varianza del portafolio
            def portfolio_variance(weights):
                return np.dot(weights.T, np.dot(cov_matrix, weights))

            # Restricciones
            constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]  # Pesos suman 1

            # Límites
            min_w = float(self.portfolio_config.min_single_weight)
            max_w = float(self.portfolio_config.max_single_weight)
            bounds = [(min_w, max_w) for _ in range(n_assets)]

            # Peso inicial (equal weight)
            x0 = np.array([1.0 / n_assets] * n_assets)

            # Optimizar
            result = minimize(
                portfolio_variance,
                x0,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
            )

            if result.success:
                # Crear dict de pesos
                weights = {
                    stocks[i].profile.symbol: Decimal(str(result.x[i])) for i in range(n_assets)
                }

                # Aplicar límites sectoriales
                weights = self._enforce_sector_limits(weights, sector_groups)

                # Normalizar
                weights = self._normalize_weights(weights)

                return weights
            else:
                logger.warning(f"Optimization failed: {result.message}, using equal weights")
                return self._calculate_equal_weights(stocks, sector_groups)

        except Exception as e:
            logger.error(f"Error in min variance optimization: {e}, using equal weights")
            return self._calculate_equal_weights(stocks, sector_groups)

    def _calculate_risk_parity_weights(
        self,
        stocks: List[LowVolatilityStock],
        sector_groups: Dict[str, List[LowVolatilityStock]],
    ) -> Dict[str, Decimal]:
        """
        Calcular pesos de risk parity.

        Cada acción contribuye igualmente al riesgo del portafolio.

        Args:
            stocks: Lista de acciones
            sector_groups: Grupos por sector

        Returns:
            Dict symbol -> peso (0-1)
        """
        n_stocks = len(stocks)
        if n_stocks == 0:
            return {}

        # Obtener volatilidades
        volatilities = []
        for stock in stocks:
            vol = stock.profile.volatility_metrics.average_volatility or 20
            volatilities.append(float(vol))

        # Risk parity: wi ∝ 1/σi
        inv_vols = [1.0 / v if v > 0 else 1.0 for v in volatilities]
        total_inv_vol = sum(inv_vols)

        weights = {
            stocks[i].profile.symbol: Decimal(str(inv_vols[i] / total_inv_vol))
            for i in range(n_stocks)
        }

        # Aplicar límites
        weights = self._enforce_sector_limits(weights, sector_groups)
        weights = self._enforce_position_limits(weights)
        weights = self._normalize_weights(weights)

        return weights

    def _enforce_sector_limits(
        self,
        weights: Dict[str, Decimal],
        sector_groups: Dict[str, List[LowVolatilityStock]],
    ) -> Dict[str, Decimal]:
        """
        Aplicar límites de peso por sector.

        Args:
            weights: Pesos actuales
            sector_groups: Grupos por sector

        Returns:
            Pesos ajustados
        """
        max_sector = self.portfolio_config.max_sector_weight
        adjusted = weights.copy()

        # Iterar hasta que todos los sectores cumplan
        max_iterations = 10
        for _ in range(max_iterations):
            # Calcular peso por sector
            sector_weights = defaultdict(Decimal)

            for symbol, weight in adjusted.items():
                # Encontrar sector de este symbol
                sector = None
                for s, stocks_in_sector in sector_groups.items():
                    if any(s.profile.symbol == symbol for s in stocks_in_sector):
                        sector = s
                        break

                if sector:
                    sector_weights[sector] += weight

            # Verificar si algún sector excede el límite
            violations = [
                (sector, weight) for sector, weight in sector_weights.items() if weight > max_sector
            ]

            if not violations:
                break

            # Ajustar sectores que exceden
            for sector, total_weight in violations:
                # Calcular factor de reducción
                reduction_factor = max_sector / total_weight

                # Aplicar a acciones del sector
                for symbol in adjusted.keys():
                    for s in sector_groups.get(sector, []):
                        if s.profile.symbol == symbol:
                            adjusted[symbol] *= reduction_factor
                            break

        return adjusted

    def _enforce_position_limits(self, weights: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """
        Aplicar límites de peso por posición.

        Args:
            weights: Pesos actuales

        Returns:
            Pesos ajustados
        """
        max_pos = self.portfolio_config.max_single_weight
        min_pos = self.portfolio_config.min_single_weight

        adjusted = {}
        for symbol, weight in weights.items():
            # Limitar peso máximo
            if weight > max_pos:
                adjusted[symbol] = max_pos
            # Limitar peso mínimo
            elif weight < min_pos and weight > 0:
                adjusted[symbol] = weight if weight >= min_pos * Decimal("0.5") else Decimal("0")
            else:
                adjusted[symbol] = weight

        return adjusted

    def _normalize_weights(self, weights: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """
        Normalizar pesos para que sumen 1.

        Args:
            weights: Pesos a normalizar

        Returns:
            Pesos normalizados
        """
        total = sum(weights.values())

        if total == 0:
            return weights

        return {symbol: weight / total for symbol, weight in weights.items()}

    def _create_positions(
        self,
        stocks: List[LowVolatilityStock],
        weights: Dict[str, Decimal],
        total_capital: Decimal,
    ) -> List[PortfolioPosition]:
        """
        Crear posiciones del portafolio.

        Args:
            stocks: Lista de acciones
            weights: Pesos calculados
            total_capital: Capital total

        Returns:
            Lista de posiciones
        """
        positions = []

        for stock in stocks:
            symbol = stock.profile.symbol
            weight = weights.get(symbol, Decimal("0"))

            if weight == 0:
                continue

            # Valor de la posición
            position_value = total_capital * weight

            # Número de acciones (redondear hacia abajo)
            price = stock.profile.current_price
            shares = int(position_value / price)

            if shares == 0:
                continue

            # Valor actual de la posición
            current_value = price * Decimal(str(shares))

            # Volatilidad esperada
            expected_vol = stock.profile.volatility_metrics.average_volatility or Decimal("20")

            # Beta
            beta = stock.profile.volatility_metrics.beta or Decimal("1.0")

            position = PortfolioPosition(
                symbol=symbol,
                weight=weight,
                shares=shares,
                avg_cost=price,
                current_value=current_value,
                expected_volatility=expected_vol,
                beta=beta,
            )

            positions.append(position)

        return positions

    def _build_portfolio_result(
        self,
        positions: List[PortfolioPosition],
        stocks: List[LowVolatilityStock],
        returns_matrix: Optional[np.ndarray],
    ) -> LowVolatilityPortfolio:
        """
        Construir resultado del portafolio.

        Args:
            positions: Lista de posiciones
            stocks: Lista de acciones seleccionadas
            returns_matrix: Matriz de retornos (opcional)

        Returns:
            Objeto LowVolatilityPortfolio
        """
        # Calcular valores totales
        total_value = sum(pos.current_value for pos in positions)

        # Calcular volatilidad esperada del portafolio
        if returns_matrix is not None and len(positions) > 1:
            expected_vol = self._calculate_portfolio_volatility(positions, stocks, returns_matrix)
        else:
            # Aproximación: promedio ponderado de volatilidades
            if total_value > 0:
                expected_vol = sum(
                    pos.expected_volatility * (pos.current_value / total_value) for pos in positions
                )
            else:
                expected_vol = Decimal("20")

        # Calcular beta del portafolio
        if total_value > 0:
            portfolio_beta = sum(pos.beta * (pos.current_value / total_value) for pos in positions)
        else:
            portfolio_beta = Decimal("1.0")

        # Calcular pesos por sector
        sector_weights = self._calculate_sector_weights(positions, stocks)

        # Metadatos
        construction_metadata = {
            "num_positions": len(positions),
            "target_size": self.portfolio_config.target_size,
            "optimization_method": self.portfolio_config.optimization_method,
            "construction_time": "now",
        }

        return LowVolatilityPortfolio(
            positions=positions,
            total_value=total_value,
            expected_volatility=expected_vol.quantize(Decimal("0.01")),
            sector_weights=sector_weights,
            portfolio_beta=portfolio_beta.quantize(Decimal("0.01")),
            construction_metadata=construction_metadata,
        )

    def _calculate_portfolio_volatility(
        self,
        positions: List[PortfolioPosition],
        stocks: List[LowVolatilityStock],
        returns_matrix: np.ndarray,
    ) -> Decimal:
        """
        Calcular volatilidad del portafolio desde matriz de retornos.

        Args:
            positions: Lista de posiciones
            stocks: Lista de acciones
            returns_matrix: Matriz de retornos

        Returns:
            Volatilidad anualizada (%)
        """
        if len(positions) < 2:
            return positions[0].expected_volatility if positions else Decimal("20")

        # Mapear símbolos a índices
        symbol_to_idx = {stock.profile.symbol: i for i, stock in enumerate(stocks)}

        # Obtener pesos y retornos correspondientes
        weights = []
        returns_subset = []

        for pos in positions:
            if pos.symbol in symbol_to_idx:
                idx = symbol_to_idx[pos.symbol]
                weights.append(float(pos.weight))
                returns_subset.append(returns_matrix[idx])

        if not weights:
            return Decimal("20")

        weights_array = np.array(weights)
        returns_array = np.array(returns_subset)

        # Matriz de covarianza
        cov_matrix = np.cov(returns_array)

        # Volatilidad del portafolio
        portfolio_variance = np.dot(weights_array.T, np.dot(cov_matrix, weights_array))
        portfolio_vol = np.sqrt(portfolio_variance)

        # Anualizar y convertir a porcentaje
        annualized_vol = portfolio_vol * np.sqrt(252) * 100

        return Decimal(str(annualized_vol)).quantize(Decimal("0.01"))

    def _calculate_sector_weights(
        self,
        positions: List[PortfolioPosition],
        stocks: List[LowVolatilityStock],
    ) -> Dict[str, Decimal]:
        """
        Calcular pesos por sector.

        Args:
            positions: Lista de posiciones
            stocks: Lista de acciones

        Returns:
            Dict sector -> peso
        """
        # Crear mapping symbol -> sector
        symbol_to_sector = {
            stock.profile.symbol: stock.profile.sector or "Unknown" for stock in stocks
        }

        # Sumar pesos por sector
        sector_weights = defaultdict(Decimal)
        total_value = sum(pos.current_value for pos in positions)

        if total_value == 0:
            return {}

        for pos in positions:
            sector = symbol_to_sector.get(pos.symbol, "Unknown")
            sector_weights[sector] += pos.current_value

        # Convertir a porcentaje
        sector_weights = {sector: (value / total_value) for sector, value in sector_weights.items()}

        return dict(sector_weights)

    def rebalance(
        self,
        current_portfolio: LowVolatilityPortfolio,
        new_stocks: List[LowVolatilityStock],
        total_capital: Decimal,
        returns_matrix: Optional[np.ndarray] = None,
    ) -> LowVolatilityPortfolio:
        """
        Rebalancear portafolio existente.

        Args:
            current_portfolio: Portafolio actual
            new_stocks: Nueva lista de acciones clasificadas
            total_capital: Capital actual
            returns_matrix: Matriz de retornos (opcional)

        Returns:
            Portafolio rebalanceado
        """
        logger.info("Rebalanceando portafolio existente")

        # Construir nuevo portafolio
        new_portfolio = self.construct_portfolio(new_stocks, total_capital, returns_matrix)

        # Identificar cambios
        current_symbols = {pos.symbol for pos in current_portfolio.positions}
        new_symbols = {pos.symbol for pos in new_portfolio.positions}

        to_add = new_symbols - current_symbols
        to_remove = current_symbols - new_symbols

        logger.debug(f"Rebalanceo: agregar {len(to_add)}, eliminar {len(to_remove)}")

        return new_portfolio

    def analyze_drift(
        self,
        portfolio: LowVolatilityPortfolio,
    ) -> Dict[str, Any]:
        """
        Analizar drift del portafolio.

        Args:
            portfolio: Portafolio a analizar

        Returns:
            Dict con análisis de drift
        """
        threshold = self.portfolio_config.rebalance_threshold

        # Calcular pesos actuales
        total_value = portfolio.total_value
        current_weights = {
            pos.symbol: (pos.current_value / total_value) if total_value > 0 else Decimal("0")
            for pos in portfolio.positions
        }

        # Detectar drift significativo
        drifted_positions = []

        for pos in portfolio.positions:
            drift = abs(pos.weight - current_weights.get(pos.symbol, Decimal("0")))

            if drift > threshold:
                drifted_positions.append(
                    {
                        "symbol": pos.symbol,
                        "target_weight": float(pos.weight),
                        "current_weight": float(current_weights.get(pos.symbol, Decimal("0"))),
                        "drift": float(drift),
                    }
                )

        # Detectar drift sectorial
        sector_drift = {}
        for sector, target_weight in portfolio.sector_weights.items():
            # Calcular peso actual del sector
            current_sector_weight = sum(
                current_weights.get(pos.symbol, Decimal("0"))
                for pos in portfolio.positions
                if pos.symbol in current_weights
            )

            sector_drift[sector] = {
                "target": float(target_weight),
                "current": float(current_sector_weight),
                "drift": abs(float(target_weight) - float(current_sector_weight)),
            }

        return {
            "needs_rebalance": len(drifted_positions) > 0,
            "drifted_positions": drifted_positions,
            "sector_drift": sector_drift,
            "max_position_drift": max((p["drift"] for p in drifted_positions), default=0),
        }
