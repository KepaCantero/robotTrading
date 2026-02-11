"""
Dividend Portfolio Constructor - Construcción de Portafolio Optimizado

Implementa construcción de portafolio de dividendos con:
- Diversificación sectorial
- Optimización de pesos
- Respeto a límites de concentración
- Maximización de yield ajustado por riesgo

SOLID Principles:
- Single Responsibility: Solo construcción de portafolios
- Open/Closed: Extensible con nuevos métodos de optimización
- Dependency Inversion: Depende de abstracciones (models)
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List

from .models import DividendStock, DividendStrategyConfig

logger = logging.getLogger(__name__)


@dataclass
class DividendPortfolioConfig:
    """
    Configuración de construcción de portafolio.

    Attributes:
        target_size: Tamaño objetivo del portafolio
        max_sector_weight: Peso máximo por sector
        max_single_weight: Peso máximo por acción
        min_single_weight: Peso mínimo por acción
        rebalance_threshold: Umbral para rebalanceo
        optimization_method: Método de optimización
    """

    target_size: int
    max_sector_weight: Decimal
    max_single_weight: Decimal
    min_single_weight: Decimal
    rebalance_threshold: Decimal
    optimization_method: str = "equal_weight"  # or "max_yield", "max_quality", "mean_variance"


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
        annual_income: Ingreso anual por dividendos estimado
        yield_on_cost: Yield sobre costo
    """

    symbol: str
    weight: Decimal
    shares: int
    avg_cost: Decimal
    current_value: Decimal
    annual_income: Decimal
    yield_on_cost: Decimal


@dataclass
class DividendPortfolio:
    """
    Portafolio de dividendos construido.

    Attributes:
        positions: Lista de posiciones
        total_value: Valor total del portafolio
        annual_income: Ingreso anual total por dividendos
        portfolio_yield: Yield del portafolio (%)
        sector_weights: Pesos por sector
        expected_monthly_income: Ingreso mensual esperado
        construction_metadata: Metadatos de construcción
    """

    positions: List[PortfolioPosition]
    total_value: Decimal
    annual_income: Decimal
    portfolio_yield: Decimal
    sector_weights: Dict[str, Decimal]
    expected_monthly_income: Decimal
    construction_metadata: Dict[str, Any]


class DividendPortfolioConstructor:
    """
    Constructor de portafolios de dividendos.

    Construye portafolios optimizados maximizando yield
    mientras mantiene diversificación y control de riesgo.

    Attributes:
        config: Configuración de la estrategia
    """

    def __init__(self, config: DividendStrategyConfig):
        """
        Inicializar constructor.

        Args:
            config: Configuración de la estrategia
        """
        self.config = config
        self.portfolio_config = DividendPortfolioConfig(
            target_size=config.portfolio_size,
            max_sector_weight=config.max_sector_weight,
            max_single_weight=config.max_single_position,
            min_single_weight=Decimal("0.01"),  # 1% mínimo
            rebalance_threshold=config.rebalance_threshold,
            optimization_method="equal_weight",
        )

    def construct_portfolio(
        self,
        stocks: List[DividendStock],
        total_capital: Decimal,
    ) -> DividendPortfolio:
        """
        Construir portafolio óptimo desde lista de acciones.

        Args:
            stocks: Lista de acciones clasificadas
            total_capital: Capital total a invertir

        Returns:
            Portafolio de dividendos construido
        """
        logger.info(
            f"Construyendo portafolio con {len(stocks)} acciones "
            f"y capital ${total_capital:,.2f}"
        )

        # 1. Seleccionar top N acciones
        selected = self._select_top_stocks(stocks)

        # 2. Agrupar por sector
        sector_groups = self._group_by_sector(selected)

        # 3. Calcular pesos optimizados
        weights = self._calculate_weights(selected, sector_groups)

        # 4. Crear posiciones
        positions = self._create_positions(selected, weights, total_capital)

        # 5. Calcular métricas del portafolio
        portfolio = self._build_portfolio_result(positions, selected)

        logger.info(
            f"Portafolio construido: {len(portfolio.positions)} posiciones, "
            f"yield {portfolio.portfolio_yield:.2f}%, "
            f"ingreso anual ${portfolio.annual_income:,.2f}"
        )

        return portfolio

    def _select_top_stocks(self, stocks: List[DividendStock]) -> List[DividendStock]:
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

    def _group_by_sector(self, stocks: List[DividendStock]) -> Dict[str, List[DividendStock]]:
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

    def _calculate_weights(
        self,
        stocks: List[DividendStock],
        sector_groups: Dict[str, List[DividendStock]],
    ) -> Dict[str, Decimal]:
        """
        Calcular pesos óptimos del portafolio.

        Implementa equal weight con restricciones sectoriales.

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

        # Iteratively enforce constraints until convergence or max iterations
        max_iterations = 10
        for iteration in range(max_iterations):
            old_weights = weights.copy()

            # Aplicar límites sectoriales iterativamente
            weights = self._enforce_sector_limits(weights, sector_groups)

            # Aplicar límites de posición
            weights = self._enforce_position_limits(weights)

            # Normalizar para que sumen 1, pero solo si no violamos límites
            weights = self._normalize_weights_respecting_limits(weights, sector_groups)

            # Check convergence
            if all(
                abs(weights.get(k, Decimal("0")) - old_weights.get(k, Decimal("0")))
                < Decimal("0.0001")
                for k in set(list(weights.keys()) + list(old_weights.keys()))
            ):
                break

        return weights

    def _enforce_sector_limits(
        self,
        weights: Dict[str, Decimal],
        sector_groups: Dict[str, List[DividendStock]],
    ) -> Dict[str, Decimal]:
        """
        Aplicar límites de peso por sector.

        Args:
            weights: Pesos actuales
            sector_groups: Grupos por sector (symbol -> sector mapping for simplicity)

        Returns:
            Pesos ajustados
        """
        max_sector = self.portfolio_config.max_sector_weight
        adjusted = weights.copy()

        # Create symbol to sector mapping
        symbol_to_sector = {}
        for sector, stocks in sector_groups.items():
            for stock in stocks:
                symbol_to_sector[stock.profile.symbol] = sector

        # Iterar hasta que todos los sectores cumplan
        max_iterations = 10
        for _ in range(max_iterations):
            # Calcular peso por sector
            sector_weights = defaultdict(Decimal)

            for symbol, weight in adjusted.items():
                sector = symbol_to_sector.get(symbol)
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
                for symbol in adjusted:
                    if symbol_to_sector.get(symbol) == sector:
                        adjusted[symbol] *= reduction_factor

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
            # Limitar peso máximo - esta es la parte clave
            if weight > max_pos:
                adjusted[symbol] = max_pos
            # Limitar peso mínimo (si es significativo)
            elif weight < min_pos and weight > 0:
                # Si está por encima de min_pos, mantener
                # Si está por debajo, posiblemente eliminar
                adjusted[symbol] = weight if weight >= min_pos * Decimal("0.5") else Decimal("0")
            else:
                adjusted[symbol] = weight

        return adjusted

    def _normalize_weights_respecting_limits(
        self, weights: Dict[str, Decimal], sector_groups: Dict[str, List[DividendStock]]
    ) -> Dict[str, Decimal]:
        """
        Normalizar pesos respetando los límites máximos de posición y sectoriales.

        Si al normalizar, alguna posición excedería max_single_position
        o algún sector excedería max_sector_weight,
        no se normaliza y se deja el peso total menor a 1.

        Args:
            weights: Pesos a normalizar
            sector_groups: Grupos por sector

        Returns:
            Pesos normalizados o pesos originales si la normalización violaría límites
        """
        total = sum(weights.values())

        if total == 0 or total == Decimal("1"):
            return weights

        max_pos = self.portfolio_config.max_single_weight
        max_sector = self.portfolio_config.max_sector_weight

        # Check if any position would exceed max_pos after normalization
        would_violate_position = any((weight / total) > max_pos for weight in weights.values())

        # Check if any sector would exceed max_sector after normalization
        symbol_to_sector = {}
        for sector, stocks in sector_groups.items():
            for stock in stocks:
                symbol_to_sector[stock.profile.symbol] = sector

        sector_sums = defaultdict(Decimal)
        for symbol, weight in weights.items():
            sector = symbol_to_sector.get(symbol)
            if sector:
                sector_sums[sector] += weight

        would_violate_sector = any(
            (sector_weight / total) > max_sector for sector_weight in sector_sums.values()
        )

        if would_violate_position or would_violate_sector:
            # Don't normalize - return weights as-is (they won't sum to 1.0)
            # This is correct behavior: if limits are hit, we can't invest all capital
            return weights
        else:
            # Safe to normalize
            return {symbol: weight / total for symbol, weight in weights.items()}

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
        stocks: List[DividendStock],
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

            # Ingreso anual estimado
            annual_income = stock.profile.dividend_data.annual_dividend * Decimal(str(shares))

            # Yield on cost (igual al yield actual al inicio)
            yield_on_cost = stock.profile.dividend_data.dividend_yield

            position = PortfolioPosition(
                symbol=symbol,
                weight=weight,
                shares=shares,
                avg_cost=price,
                current_value=current_value,
                annual_income=annual_income,
                yield_on_cost=yield_on_cost,
            )

            positions.append(position)

        return positions

    def _build_portfolio_result(
        self,
        positions: List[PortfolioPosition],
        stocks: List[DividendStock],
    ) -> DividendPortfolio:
        """
        Construir resultado del portafolio.

        Args:
            positions: Lista de posiciones
            stocks: Lista de acciones seleccionadas

        Returns:
            Objeto DividendPortfolio
        """
        # Calcular valores totales
        total_value = sum(pos.current_value for pos in positions)
        annual_income = sum(pos.annual_income for pos in positions)

        # Portfolio yield ponderado
        if total_value > 0:
            portfolio_yield = (annual_income / total_value) * 100
        else:
            portfolio_yield = Decimal("0")

        # Calcular pesos por sector
        sector_weights = self._calculate_sector_weights(positions, stocks)

        # Ingreso mensual esperado
        expected_monthly_income = annual_income / 12

        # Metadatos
        construction_metadata = {
            "num_positions": len(positions),
            "target_size": self.portfolio_config.target_size,
            "optimization_method": self.portfolio_config.optimization_method,
            "construction_time": "now",  # NOTE: Add actual timestamp
        }

        return DividendPortfolio(
            positions=positions,
            total_value=total_value,
            annual_income=annual_income,
            portfolio_yield=portfolio_yield,
            sector_weights=sector_weights,
            expected_monthly_income=expected_monthly_income,
            construction_metadata=construction_metadata,
        )

    def _calculate_sector_weights(
        self,
        positions: List[PortfolioPosition],
        stocks: List[DividendStock],
    ) -> Dict[str, Decimal]:
        """
        Calcular pesos por sector.

        Args:
            positions: Lista de posiciones
            stocks: Lista de acciones

        Returns:
            Dict sector -> peso (proporción del portafolio, 0-1)
        """
        # Crear mapping symbol -> sector
        symbol_to_sector = {
            stock.profile.symbol: stock.profile.sector or "Unknown" for stock in stocks
        }

        # Sumar pesos por sector usando pos.weight
        # pos.weight ya está expresado como proporción del capital total (0-1)
        # No necesitamos normalizar de nuevo
        sector_weights = defaultdict(Decimal)

        for pos in positions:
            sector = symbol_to_sector.get(pos.symbol, "Unknown")
            sector_weights[sector] += pos.weight

        return dict(sector_weights)

    def rebalance(
        self,
        current_portfolio: DividendPortfolio,
        new_stocks: List[DividendStock],
        total_capital: Decimal,
    ) -> DividendPortfolio:
        """
        Rebalancear portafolio existente.

        Args:
            current_portfolio: Portafolio actual
            new_stocks: Nueva lista de acciones clasificadas
            total_capital: Capital actual

        Returns:
            Portafolio rebalanceado
        """
        logger.info("Rebalanceando portafolio existente")

        # Construir nuevo portafolio
        new_portfolio = self.construct_portfolio(new_stocks, total_capital)

        # Identificar cambios
        current_symbols = {pos.symbol for pos in current_portfolio.positions}
        new_symbols = {pos.symbol for pos in new_portfolio.positions}

        to_add = new_symbols - current_symbols
        to_remove = current_symbols - new_symbols

        logger.debug(f"Rebalanceo: agregar {len(to_add)}, eliminar {len(to_remove)}")

        return new_portfolio

    def analyze_drift(
        self,
        portfolio: DividendPortfolio,
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
            )  # Simplificado

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
