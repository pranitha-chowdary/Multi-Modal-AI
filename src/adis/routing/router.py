"""Damage-aware evacuation routing.

Baseline (Phase 0-2): Dijkstra shortest path over the knowledge graph, with
edge weights penalized by road status (blocked roads get an effectively
infinite cost, so they're never selected).

Phase 3 (see PLAN.md) replaces/augments this with a trained GNN (e.g.
GraphSAGE/GAT via PyTorch Geometric) that predicts edge traversal cost and
node risk directly from the graph + verified-evidence embeddings, enabling
learned rerouting under partial/uncertain damage information. Keep this
Dijkstra baseline as the always-available fallback and as an ablation.
"""
from __future__ import annotations

import math

import networkx as nx

from adis.knowledge_graph.schema import RoadStatus


class EvacuationRouter:
    def __init__(self, graph: nx.Graph):
        self.graph = graph

    def edge_cost(self, data: dict) -> float:
        length = data.get("length_km", 1.0)
        status = data.get("status", RoadStatus.UNKNOWN)
        if status == RoadStatus.BLOCKED:
            return math.inf
        if status == RoadStatus.PARTIAL:
            return length * 3
        if status == RoadStatus.UNKNOWN:
            return length * 1.5
        return length

    def shortest_safe_path(self, source: str, target: str) -> tuple[list[str], float] | None:
        weighted = nx.Graph()
        weighted.add_nodes_from(self.graph.nodes(data=True))
        for u, v, data in self.graph.edges(data=True):
            cost = self.edge_cost(data)
            if math.isfinite(cost):
                weighted.add_edge(u, v, weight=cost)
        try:
            path = nx.shortest_path(weighted, source, target, weight="weight")
            length = nx.shortest_path_length(weighted, source, target, weight="weight")
            return path, length
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def rank_facilities_by_reachability(self, source: str, node_type_filter=None) -> list[dict]:
        results = []
        for node_id, data in self.graph.nodes(data=True):
            if node_type_filter and data.get("node_type") != node_type_filter:
                continue
            route = self.shortest_safe_path(source, node_id)
            if route:
                path, length = route
                results.append(
                    {"location_id": node_id, "path": path, "distance_km": length, "status": data.get("status")}
                )
        return sorted(results, key=lambda r: r["distance_km"])
