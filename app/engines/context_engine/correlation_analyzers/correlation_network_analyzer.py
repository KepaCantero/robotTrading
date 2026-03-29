"""
CorrelationNetworkAnalyzer - Network analysis de correlaciones.

Usa teoría de grafos para analizar correlaciones entre activos.
"""

import logging
from typing import Any, Optional

# REQUIRED: networkx is REQUIRED - NO FALLBACKS
import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


class CorrelationNetworkAnalyzer:
    """Analizador de red de correlaciones."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        config = config or {}
        self.threshold = config.get("threshold", 0.5)

    def analyze_network(self, correlation_matrix: np.ndarray, symbols: list[str]) -> dict[str, Any]:
        """
        Analizar red de correlaciones.

        Args:
            correlation_matrix: Matriz de correlación
            symbols: Lista de símbolos

        Returns:
            Dict con métricas de red
        """
        try:
            # Crear grafo
            G = nx.Graph()

            # Agregar nodos
            G.add_nodes_from(symbols)

            # Agregar edges basados en correlación
            for i, sym1 in enumerate(symbols):
                for j, sym2 in enumerate(symbols):
                    if i < j and correlation_matrix[i, j] > self.threshold:
                        G.add_edge(sym1, sym2, weight=correlation_matrix[i, j])

            # Calcular centralidad
            centrality = nx.degree_centrality(G)

            # Detectar clusters
            clusters = list(nx.community.greedy_modularity_communities(G))

            return {
                "centrality": centrality,
                "clusters": [list(c) for c in clusters],
                "num_nodes": G.number_of_nodes(),
                "num_edges": G.number_of_edges(),
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error analizando red: {e}")
            return {"centrality": {}, "clusters": [], "error": str(e)}
