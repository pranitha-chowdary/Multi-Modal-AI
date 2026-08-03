"""Builds and maintains the live disaster knowledge graph.

- Intersections/road segments are represented as edges between intersection
  nodes.
- Buildings/hospitals/shelters are nodes attached to their nearest
  intersection via a near-zero-cost edge.
- Every road edge and facility node is registered under a `location_id` so
  VerifiedEvidence (keyed by location_id) can be applied without the caller
  needing to know graph internals.

`from_osm()` builds the graph from real, live OpenStreetMap data (via osmnx)
for a named place - the primary way to construct a real-world graph.
`add_road`/`add_facility` remain available for manually specifying
real-world data you already have (e.g. a curated AP regional road list) or
for tests - they take real coordinates/lengths supplied by the caller, not
fabricated ones.
"""
from __future__ import annotations

import networkx as nx

from adis.fusion.verifier import VerifiedEvidence
from adis.knowledge_graph.schema import FacilityStatus, NodeType, RoadStatus
from adis.utils.logging import get_logger

logger = get_logger(__name__)


class KnowledgeGraphBuilder:
    def __init__(self) -> None:
        self.graph = nx.Graph()
        self._edge_by_location: dict[str, tuple[str, str]] = {}
        self._node_by_location: dict[str, str] = {}

    def add_intersection(self, node_id: str) -> None:
        self.graph.add_node(node_id, node_type=NodeType.INTERSECTION)

    def add_facility(
        self,
        location_id: str,
        node_type: NodeType,
        name: str,
        nearest_intersection: str,
        capacity: int | None = None,
    ) -> None:
        self.graph.add_node(
            location_id,
            node_type=node_type,
            name=name,
            status=FacilityStatus.UNKNOWN,
            capacity=capacity,
            confidence=0.0,
        )
        self.graph.add_edge(
            location_id, nearest_intersection, length_km=0.05, status=RoadStatus.CLEAR, confidence=1.0
        )
        self._node_by_location[location_id] = location_id

    def add_road(self, location_id: str, node_a: str, node_b: str, length_km: float) -> None:
        self.graph.add_edge(
            node_a, node_b, length_km=length_km, status=RoadStatus.UNKNOWN, confidence=0.0, location_id=location_id
        )
        self._edge_by_location[location_id] = (node_a, node_b)

    def apply_evidence(self, evidence: VerifiedEvidence) -> None:
        """Update the graph edge/node matching evidence.location_id."""
        status = {
            "clear": RoadStatus.CLEAR,
            "blocked": RoadStatus.BLOCKED,
        }.get(evidence.road_status, RoadStatus.UNKNOWN)

        if evidence.location_id in self._edge_by_location:
            edge = self._edge_by_location[evidence.location_id]
            self.graph.edges[edge]["status"] = status
            self.graph.edges[edge]["confidence"] = evidence.confidence

        if evidence.location_id in self._node_by_location:
            node_data = self.graph.nodes[evidence.location_id]
            facility_status = (
                FacilityStatus.NON_FUNCTIONAL if status == RoadStatus.BLOCKED else FacilityStatus.FUNCTIONAL
            )
            node_data["status"] = facility_status
            node_data["confidence"] = evidence.confidence

    @classmethod
    def from_osm(
        cls,
        place_name: str,
        hospital_tags: dict | None = None,
        shelter_tags: dict | None = None,
        network_type: str = "drive",
    ) -> "KnowledgeGraphBuilder":
        """Build a knowledge graph from real, live OpenStreetMap data.

        Queries the OSM Overpass API (via osmnx) for the real road network and
        real-world hospital/shelter locations of `place_name` (e.g.
        "Vijayawada, Andhra Pradesh, India"). Requires network access. No
        synthetic/mocked road or facility data is generated here.
        """
        import osmnx as ox

        hospital_tags = hospital_tags or {"amenity": "hospital"}
        shelter_tags = shelter_tags or {"amenity": "shelter", "emergency": "shelter"}

        road_graph = ox.graph_from_place(place_name, network_type=network_type)
        builder = cls()

        for node_id in road_graph.nodes:
            builder.add_intersection(str(node_id))

        for u, v, key, data in road_graph.edges(keys=True, data=True):
            length_km = data.get("length", 0.0) / 1000.0
            location_id = f"road_{u}_{v}_{key}"
            builder.add_road(location_id, str(u), str(v), length_km)

        for facility_kind, tags in ((NodeType.HOSPITAL, hospital_tags), (NodeType.SHELTER, shelter_tags)):
            try:
                features = ox.features_from_place(place_name, tags=tags)
            except Exception as exc:  # osmnx raises when a region has no matching tagged features
                logger.warning("No %s features found for %s: %s", facility_kind.value, place_name, exc)
                continue
            for idx, row in features.iterrows():
                centroid = row.geometry.centroid
                nearest = ox.distance.nearest_nodes(road_graph, centroid.x, centroid.y)
                builder.add_facility(
                    location_id=f"{facility_kind.value}_{idx}",
                    node_type=facility_kind,
                    name=row.get("name") or f"{facility_kind.value}_{idx}",
                    nearest_intersection=str(nearest),
                )

        return builder
