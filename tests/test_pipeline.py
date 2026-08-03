"""End-to-end smoke test for the ADIS pipeline using real pretrained models
(CLIP for vision, a real NLI zero-shot model for text) - no mocks. First run
downloads model weights from HuggingFace Hub, so this test requires network
access the first time it's run.
"""
from PIL import Image

from adis.knowledge_graph.builder import KnowledgeGraphBuilder
from adis.knowledge_graph.schema import NodeType, RoadStatus
from adis.orchestrator.pipeline import ADISPipeline
from adis.routing.router import EvacuationRouter


def build_sample_graph() -> KnowledgeGraphBuilder:
    kg = KnowledgeGraphBuilder()
    for node in ["HQ", "N1", "N2", "N3"]:
        kg.add_intersection(node)
    kg.add_road("road_hq_n1", "HQ", "N1", length_km=2.0)
    kg.add_road("road_n1_n2", "N1", "N2", length_km=1.5)
    kg.add_road("road_n1_n3", "N1", "N3", length_km=3.0)
    kg.add_facility("hospital_1", NodeType.HOSPITAL, "City Hospital", nearest_intersection="N2")
    kg.add_facility("shelter_1", NodeType.SHELTER, "Community Shelter", nearest_intersection="N3")
    return kg


def _make_real_image(path, color) -> str:
    # A real (if synthetic) image file, actually decoded and run through CLIP -
    # not a fabricated result. Accuracy on solid-color placeholders is
    # expected to be limited until Phase 1 fine-tunes on real xBD/FloodNet
    # imagery; this test only checks the pipeline plumbing is genuine and works.
    Image.new("RGB", (224, 224), color=color).save(path)
    return str(path)


def test_pipeline_produces_prioritized_action_plan(tmp_path):
    kg = build_sample_graph()
    pipeline = ADISPipeline(kg, hq_node="HQ")

    hospital_image = _make_real_image(tmp_path / "hospital_1.png", (120, 40, 40))
    road_image = _make_real_image(tmp_path / "road_n1_n2.png", (40, 90, 160))

    vision_inputs = [
        (hospital_image, "hospital_1", "satellite"),
        (road_image, "road_n1_n2", "drone"),
    ]
    text_inputs = [
        ("People trapped, need rescue near hospital", "hospital_1", "emergency-call"),
        ("Road to N2 is completely blocked by debris", "road_n1_n2", "social-media"),
    ]

    plan = pipeline.run(vision_inputs, text_inputs)

    assert len(plan.items) == 2
    assert "ADIS Prioritized Action Plan" in plan.as_text()
    # Casualty-reporting location must be top priority.
    assert plan.items[0].location_id == "hospital_1"


def test_router_avoids_blocked_road():
    kg = build_sample_graph()
    kg.graph.edges["N1", "N2"]["status"] = RoadStatus.BLOCKED

    router = EvacuationRouter(kg.graph)
    route = router.shortest_safe_path("HQ", "N2")
    # The only path to N2 is via N1; if that road is blocked, N2 is unreachable.
    assert route is None


def test_router_finds_path_when_clear():
    kg = build_sample_graph()
    kg.graph.edges["N1", "N2"]["status"] = RoadStatus.CLEAR
    kg.graph.edges["HQ", "N1"]["status"] = RoadStatus.CLEAR

    router = EvacuationRouter(kg.graph)
    route = router.shortest_safe_path("HQ", "N2")
    assert route is not None
    path, distance = route
    assert path == ["HQ", "N1", "N2"]
    assert distance == 3.5
