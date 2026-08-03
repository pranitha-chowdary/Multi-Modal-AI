"""End-to-end ADIS pipeline orchestrator.

Baseline (Phase 0-3): a deterministic function-pipeline that wires
perception -> fusion -> knowledge graph -> routing -> action plan.

Phase 4 (see PLAN.md) upgrades the orchestration layer itself to a
graph-guided multi-agent framework (e.g. LangGraph) where each stage is an
autonomous agent capable of re-planning, tool use, and iterative refinement
instead of a single fixed function-call chain.
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


@dataclass
class ActionPlan:
    items: list[ActionItem] = field(default_factory=list)

    def as_text(self) -> str:
        lines = ["ADIS Prioritized Action Plan", "=" * 30]
        for item in self.items:
            lines.append(f"[P{item.priority}] {item.location_id}: {item.action} -- {item.rationale}")
        return "\n".join(lines)


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
            if v.casualty_reported:
                action = "Dispatch rescue team immediately"
            elif v.road_status == "blocked":
                action = "Reroute supplies / clear road"
            else:
                action = "Monitor"

            rationale_parts = [f"confidence={v.confidence}"]
            if v.contradiction:
                rationale_parts.append("cross-modal contradiction resolved")
            if route:
                path, dist = route
                rationale_parts.append(f"route via {len(path)} nodes, {dist:.2f}km")
            else:
                rationale_parts.append("no safe route found")

            items.append(
                ActionItem(
                    priority=priority,
                    location_id=v.location_id,
                    action=action,
                    rationale=", ".join(rationale_parts),
                )
            )
        return ActionPlan(items=items)
