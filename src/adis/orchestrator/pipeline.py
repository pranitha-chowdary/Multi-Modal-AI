"""End-to-end ADIS pipeline orchestrator.

Stage sequence (this is the contract the pipeline must honor end-to-end):
  perception (vision + text agents)
  -> cross-modal verification (CrossModalVerifier.verify)
  -> confidence/consistency gate (VerifiedEvidence.verification_status)
  -> knowledge graph update (KnowledgeGraphBuilder.apply_evidence)
  -> routing / plan of action (EvacuationRouter; Dijkstra baseline today,
     Phase 3 swaps in a trained GNN edge-cost model per PLAN.md -- the
     interface (`shortest_safe_path`) stays the same either way)
  -> tie to responders (ActionPlan.dispatch_by_team, broadcast over
     /ws/alerts and returned by POST /analyze)

Baseline (Phase 0-3): a deterministic function-pipeline, not yet an
autonomous multi-agent graph. Phase 4 (see PLAN.md) upgrades the
orchestration layer itself to a graph-guided multi-agent framework (e.g.
LangGraph) where each stage is an autonomous agent capable of re-planning,
tool use, and iterative refinement instead of a single fixed function-call
chain.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from adis.fusion.verifier import CrossModalVerifier, VerifiedEvidence
from adis.knowledge_graph.builder import KnowledgeGraphBuilder
from adis.perception.text.model import TextTriageAgent, TriageReport
from adis.perception.vision.model import DamageAssessment, VisionDamageAgent
from adis.routing.router import EvacuationRouter



@dataclass
class ActionItem:
    priority: int
    location_id: str
    action: str
    rationale: str
    status: str  # "dispatch" | "review" | "verify" -- confidence/consistency gate outcome
    responder_team: str  # "rescue" | "logistics" | "monitoring" | "field_verification"
    lat: float | None = None
    lon: float | None = None
    route_path: list[str] | None = None  # node ids from HQ to this location, in order
    route_coords: list[list[float]] | None = None  # [lat, lon] pairs, present only if every node on the path has coordinates


@dataclass
class ActionPlan:
    items: list[ActionItem] = field(default_factory=list)

    def as_text(self) -> str:
        lines = ["ADIS Prioritized Action Plan", "=" * 30]
        for item in self.items:
            lines.append(f"[P{item.priority}] {item.location_id}: {item.action} -- {item.rationale}")
        return "\n".join(lines)

    def dispatch_by_team(self) -> dict[str, list[ActionItem]]:
        """Group action items by responder team -- the "tie to responders" step."""
        grouped: dict[str, list[ActionItem]] = {}
        for item in self.items:
            grouped.setdefault(item.responder_team, []).append(item)
        return grouped


class ADISPipeline:
    def __init__(
        self,
        kg_builder: KnowledgeGraphBuilder,
        hq_node: str,
        vision_agent: VisionDamageAgent | None = None,
        text_agent: TextTriageAgent | None = None,
    ):
        # Real models are expensive to load (weight download + init), so accept
        # shared instances from the caller (e.g. the API's module-level
        # singletons) instead of constructing new ones per pipeline/request.
        self.vision_agent = vision_agent or VisionDamageAgent()
        self.text_agent = text_agent or TextTriageAgent()
        self.verifier = CrossModalVerifier()
        self.kg_builder = kg_builder
        self.hq_node = hq_node

    def run(
        self,
        vision_inputs: list[tuple[str, str, str]],  # (image_path, location_id, source)
        text_inputs: list[tuple[str, str, str]],  # (text, location_id, source)
    ) -> ActionPlan:
        vision_by_location: dict[str, list[DamageAssessment]] = {}
        for image_path, location_id, source in vision_inputs:
            result = self.vision_agent.infer(image_path, location_id, source)
            vision_by_location.setdefault(location_id, []).append(result)

        text_by_location: dict[str, list[TriageReport]] = {}
        for text, location_id, source in text_inputs:
            result = self.text_agent.infer(text, location_id, source)
            text_by_location.setdefault(location_id, []).append(result)

        all_locations = set(vision_by_location) | set(text_by_location)
        verified: list[VerifiedEvidence] = []
        for location_id in all_locations:
            v = self.verifier.verify(
                location_id,
                vision_by_location.get(location_id, []),
                text_by_location.get(location_id, []),
            )
            verified.append(v)
            self.kg_builder.apply_evidence(v)

        router = EvacuationRouter(self.kg_builder.graph)
        return self._build_action_plan(verified, router)

    def _build_action_plan(self, verified: list[VerifiedEvidence], router: EvacuationRouter) -> ActionPlan:
        scored = []
        for v in verified:
            severity_score = (2 if v.casualty_reported else 0) + (1 if v.road_status == "blocked" else 0)
            scored.append((severity_score, v))
        scored.sort(key=lambda pair: (-pair[0], -pair[1].confidence))

        items = []
        for priority, (_score, v) in enumerate(scored, start=1):
            route = router.shortest_safe_path(self.hq_node, v.location_id)
            node_data = self.kg_builder.graph.nodes.get(v.location_id, {})
            lat, lon = node_data.get("lat"), node_data.get("lon")
            route_path: list[str] | None = None
            route_coords: list[list[float]] | None = None

            # Confidence/consistency gate result (from CrossModalVerifier) decides
            # whether this item is auto-dispatched, sent for human sign-off, or
            # held back for field verification instead of acted on blindly.
            if v.verification_status == "low_confidence":
                status = "verify"
                responder_team = "field_verification"
                action = "Verify on ground before dispatch (evidence below confidence threshold)"
            elif v.casualty_reported:
                status = "review" if v.verification_status == "needs_review" else "dispatch"
                responder_team = "rescue"
                action = "Dispatch rescue team immediately"
            elif v.road_status == "blocked":
                status = "review" if v.verification_status == "needs_review" else "dispatch"
                responder_team = "logistics"
                action = "Reroute supplies / clear road"
            else:
                status = "review" if v.verification_status == "needs_review" else "dispatch"
                responder_team = "monitoring"
                action = "Monitor"

            rationale_parts = [f"confidence={v.confidence}", f"gate={v.verification_status}"]
            if v.contradiction:
                rationale_parts.append("cross-modal contradiction resolved")
            if route:
                path, dist = route
                rationale_parts.append(f"route via {len(path)} nodes, {dist:.2f}km")
                route_path = path
                coords = [
                    [self.kg_builder.graph.nodes[n]["lat"], self.kg_builder.graph.nodes[n]["lon"]]
                    for n in path
                    if self.kg_builder.graph.nodes[n].get("lat") is not None
                    and self.kg_builder.graph.nodes[n].get("lon") is not None
                ]
                # Only expose a polyline if every node on the path has real
                # coordinates -- a partial line (missing intermediate hops)
                # would misrepresent the route on the map.
                route_coords = coords if len(coords) == len(path) else None
            else:
                rationale_parts.append("no safe route found")

            items.append(
                ActionItem(
                    priority=priority,
                    location_id=v.location_id,
                    action=action,
                    rationale=", ".join(rationale_parts),
                    status=status,
                    responder_team=responder_team,
                    lat=lat,
                    lon=lon,
                    route_path=route_path,
                    route_coords=route_coords,
                )
            )
        return ActionPlan(items=items)
