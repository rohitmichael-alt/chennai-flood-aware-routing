"""Dijkstra routing helpers for Stage 1."""

from __future__ import annotations

import networkx as nx


def shortest_path(graph: nx.MultiDiGraph, origin: int, destination: int, *, weight: str) -> list[int]:
    """Compute a shortest path using NetworkX Dijkstra."""

    return nx.shortest_path(graph, origin, destination, weight=weight, method="dijkstra")


def path_cost(graph: nx.MultiDiGraph, path: list[int], *, weight: str) -> float:
    """Return the minimum parallel-edge cost along a node path."""

    total = 0.0
    for u, v in zip(path[:-1], path[1:]):
        edge_options = graph.get_edge_data(u, v)
        if not edge_options:
            raise ValueError(f"Path contains non-edge step: {u} -> {v}")
        costs = []
        for data in edge_options.values():
            if weight not in data:
                raise ValueError(f"Edge {u}->{v} is missing weight attribute {weight!r}.")
            costs.append(data[weight])
        total += min(costs)
    return total
