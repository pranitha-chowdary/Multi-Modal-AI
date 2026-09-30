"""FastAPI service exposing the ADIS end-to-end pipeline.

POST /analyze accepts a scenario (intersections, roads, facilities, and raw
vision/text inputs) and returns a prioritized action plan. Each request
builds a fresh in-memory knowledge graph; Phase 4 (see PLAN.md) will add a
persistent, incrementally-updated graph plus streaming ingestion instead of
one-shot requests.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from adis.knowledge_graph.builder import KnowledgeGraphBuilder
from adis.knowledge_graph.schema import NodeType
from adis.orchestrator.pipeline import ADISPipeline
from adis.perception.text.model import TextTriageAgent
from adis.perception.vision.model import VisionDamageAgent
from adis.utils.ws_manager import ConnectionManager

app = FastAPI(title="ADIS", description="Autonomous Disaster Intelligence System")

# Real models are loaded once at process startup (not per-request) since
# constructing them triggers real weight loading/downloads.
_vision_agent = VisionDamageAgent()
_text_agent = TextTriageAgent()

# Shared broadcast hub: pushes action-plan updates and alerts to every
# connected dashboard over /ws/alerts, no polling required.
_alert_manager = ConnectionManager()

# Latest known action item per location_id, across all /analyze calls -- lets
# the dashboard show a persistent common operating picture (map + dispatch
# board) instead of losing state when a newer scenario is run, and lets
# /dispatch/{location_id}/notify mark a specific item as sent to responders.
_latest_items: dict[str, dict] = {}


class RoadIn(BaseModel):
    location_id: str
    node_a: str
    node_b: str
    length_km: float


class FacilityIn(BaseModel):
    location_id: str
    node_type: NodeType
    name: str
    nearest_intersection: str
    capacity: int | None = None
    lat: float | None = None
    lon: float | None = None


class VisionInputIn(BaseModel):
    image_path: str
    location_id: str
    source: str = "satellite"


class TextInputIn(BaseModel):
    text: str
    location_id: str
    source: str = "social-media"


class AnalyzeRequest(BaseModel):
    hq_node: str
    intersections: list[str] = []
    intersection_coords: dict[str, list[float]] = {}  # node_id -> [lat, lon], optional
    roads: list[RoadIn] = []
    facilities: list[FacilityIn] = []
    vision_inputs: list[VisionInputIn] = []
    text_inputs: list[TextInputIn] = []


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(request: AnalyzeRequest) -> dict:
    kg_builder = KnowledgeGraphBuilder()
    for node_id in request.intersections:
        coords = request.intersection_coords.get(node_id)
        kg_builder.add_intersection(node_id, lat=coords[0] if coords else None, lon=coords[1] if coords else None)
    for road in request.roads:
        kg_builder.add_road(road.location_id, road.node_a, road.node_b, road.length_km)
    for facility in request.facilities:
        kg_builder.add_facility(
            facility.location_id,
            facility.node_type,
            facility.name,
            facility.nearest_intersection,
            facility.capacity,
            facility.lat,
            facility.lon,
        )

    pipeline = ADISPipeline(
        kg_builder, hq_node=request.hq_node, vision_agent=_vision_agent, text_agent=_text_agent
    )
    plan = pipeline.run(
        vision_inputs=[(v.image_path, v.location_id, v.source) for v in request.vision_inputs],
        text_inputs=[(t.text, t.location_id, t.source) for t in request.text_inputs],
    )
    for item in plan.items:
        _latest_items[item.location_id] = {**item.__dict__, "notified": False}

    dispatch = {
        team: [_latest_items[item.location_id] for item in items]
        for team, items in plan.dispatch_by_team().items()
    }
    result = {
        "action_plan_text": plan.as_text(),
        "items": [_latest_items[item.location_id] for item in plan.items],
        "dispatch": dispatch,
    }

    # Push the freshly computed plan to every connected dashboard in real time,
    # including the per-responder-team breakdown ("tie to responders").
    await _alert_manager.broadcast(
        {
            "type": "action_plan",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **result,
        }
    )
    return result


@app.get("/dispatch/{location_id}")
def get_dispatch_item(location_id: str) -> dict:
    """Public read-only lookup for a single location's current action item --
    backs the shareable community alert page (/share/{location_id}) so people
    in the affected locality can see the plan/route without needing dashboard
    access.
    """
    item = _latest_items.get(location_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Unknown location_id: {location_id}")
    return item


@app.post("/dispatch/{location_id}/notify")
async def notify_responders(location_id: str) -> dict:
    """Marks an action item as sent to its responder team and broadcasts the
    update to every connected dashboard -- the actual "make responders aware
    of it" step, not just a locally-displayed action plan.
    """
    item = _latest_items.get(location_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Unknown location_id: {location_id}")

    item["notified"] = True
    item["notified_at"] = datetime.now(timezone.utc).isoformat()

    await _alert_manager.broadcast(
        {
            "type": "dispatch_notification",
            "timestamp": item["notified_at"],
            "item": item,
        }
    )
    return item


@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket) -> None:
    """Streams real-time JSON alerts (action plans, ad-hoc alerts) to the
    React dashboard. Clients only receive messages - this endpoint doesn't
    expect any inbound payloads, but keeps reading to detect disconnects.
    """
    await _alert_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _alert_manager.disconnect(websocket)
