#!/usr/bin/env python3
"""Live-feed connector: polls three free, no-API-key-required real-time feeds
for a real OpenStreetMap area - NASA EONET (floods, storms, wildfires,
landslides), USGS (earthquakes), and Open-Meteo (current severe weather) -
snaps each event to the nearest road segment in that area's knowledge graph,
and POSTs it to the ADIS `/analyze` endpoint as a real text_input -
triggering genuine text-agent inference and a WebSocket broadcast to the
dashboard.

This is real external data, not a simulator - but note the current
`/analyze` endpoint is stateless per-request (see PLAN.md Phase 4), so this
script resends the full graph structure on every poll alongside any newly
seen events.

Usage:
    python scripts/live_feed_connector.py --place "Vijayawada, Andhra Pradesh, India"

Requires network access and: pip install -r requirements.txt requests
"""
from __future__ import annotations

import argparse
import math
import time
from datetime import datetime, timedelta, timezone

import requests

from adis.knowledge_graph.builder import KnowledgeGraphBuilder
from adis.knowledge_graph.schema import NodeType

EONET_EVENTS_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"
# EONET category ids relevant to ADIS's flood/structural-damage focus.
_RELEVANT_CATEGORIES = "floods,severeStorms,wildfires,landslides,volcanoes"

USGS_QUERY_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
# WMO weather codes considered "severe" for alerting purposes (freezing rain,
# heavy rain/showers, heavy snow, thunderstorms - see open-meteo.com/en/docs).
_SEVERE_WEATHER_CODES = {56, 57, 65, 67, 75, 82, 86, 95, 96, 99}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def build_local_graph(place: str, network_type: str) -> KnowledgeGraphBuilder:
    print(f"Building real OSM graph for '{place}' (this hits the OSM Overpass API)...")
    builder = KnowledgeGraphBuilder.from_osm(place, network_type=network_type)
    n_nodes = builder.graph.number_of_nodes()
    n_edges = builder.graph.number_of_edges()
    print(f"  -> {n_nodes} nodes, {n_edges} edges")
    if n_nodes > 2000:
        print("  WARNING: large graph - every poll resends this full structure to /analyze. "
              "Pick a smaller place (a town/neighborhood, not a whole city) for a cheap demo.")
    return builder


def nearest_road_location_id(builder: KnowledgeGraphBuilder, lat: float, lon: float) -> str | None:
    """Snap an external (lat, lon) event to the nearest road edge's location_id."""
    best_node, best_dist = None, float("inf")
    for node_id, data in builder.graph.nodes(data=True):
        if data.get("node_type") != NodeType.INTERSECTION:
            continue
        node_lat, node_lon = data.get("lat"), data.get("lon")
        if node_lat is None or node_lon is None:
            continue
        dist = _haversine_km(lat, lon, node_lat, node_lon)
        if dist < best_dist:
            best_node, best_dist = node_id, dist

    if best_node is None:
        return None
    for _, _, data in builder.graph.edges(best_node, data=True):
        if "location_id" in data:
            return data["location_id"]
    return None


def graph_payload(builder: KnowledgeGraphBuilder) -> dict:
    intersections, roads, facilities = [], [], []
    seen_edges = set()
    for node_id, data in builder.graph.nodes(data=True):
        node_type = data.get("node_type")
        if node_type == NodeType.INTERSECTION:
            intersections.append(node_id)
        elif node_type in (NodeType.HOSPITAL, NodeType.SHELTER, NodeType.BUILDING):
            nearest = next(iter(builder.graph.neighbors(node_id)), None)
            facilities.append(
                {
                    "location_id": node_id,
                    "node_type": node_type.value,
                    "name": data.get("name") or node_id,
                    "nearest_intersection": nearest,
                    "capacity": data.get("capacity"),
                }
            )
    for u, v, data in builder.graph.edges(data=True):
        location_id = data.get("location_id")
        if not location_id or location_id in seen_edges:
            continue
        seen_edges.add(location_id)
        roads.append({"location_id": location_id, "node_a": u, "node_b": v, "length_km": data.get("length_km", 0.0)})
    return {"intersections": intersections, "roads": roads, "facilities": facilities}


def fetch_eonet_events(bbox: tuple[float, float, float, float], days: int) -> list[dict]:
    min_lon, min_lat, max_lon, max_lat = bbox
    params = {
        "category": _RELEVANT_CATEGORIES,
        "status": "open",
        "days": days,
        "bbox": f"{min_lon},{max_lat},{max_lon},{min_lat}",
    }
    resp = requests.get(EONET_EVENTS_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("events", [])


def bbox_from_graph(builder: KnowledgeGraphBuilder) -> tuple[float, float, float, float]:
    lats = [d["lat"] for _, d in builder.graph.nodes(data=True) if d.get("lat") is not None]
    lons = [d["lon"] for _, d in builder.graph.nodes(data=True) if d.get("lon") is not None]
    return min(lons), min(lats), max(lons), max(lats)


def fetch_usgs_earthquakes(bbox: tuple[float, float, float, float], days: int, min_magnitude: float) -> list[dict]:
    min_lon, min_lat, max_lon, max_lat = bbox
    params = {
        "format": "geojson",
        "starttime": (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d"),
        "minlatitude": min_lat,
        "maxlatitude": max_lat,
        "minlongitude": min_lon,
        "maxlongitude": max_lon,
        "minmagnitude": min_magnitude,
    }
    resp = requests.get(USGS_QUERY_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("features", [])


def fetch_openmeteo_current(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "precipitation,weather_code,wind_speed_10m,wind_gusts_10m",
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("current", {})


def severe_weather_text(current: dict) -> str | None:
    """Return an alert string if current conditions cross severe thresholds, else None."""
    code = current.get("weather_code")
    gusts = current.get("wind_gusts_10m") or 0
    precip = current.get("precipitation") or 0
    if code in _SEVERE_WEATHER_CODES:
        return f"Severe weather alert: condition code {code}, {precip}mm precipitation, {gusts}km/h gusts"
    if gusts >= 60:
        return f"High wind alert: gusts of {gusts}km/h"
    return None


def run(args: argparse.Namespace) -> None:
    builder = build_local_graph(args.place, args.network_type)
    bbox = bbox_from_graph(builder)
    base_payload = graph_payload(builder)
    hq_node = args.hqx_node or base_payload["intersections"][0]
    centroid_lat = (bbox[1] + bbox[3]) / 2
    centroid_lon = (bbox[0] + bbox[2]) / 2
    centroid_location_id = nearest_road_location_id(builder, centroid_lat, centroid_lon)
    print(f"Using hq_node={hq_node}. Polling EONET/USGS/Open-Meteo every {args.interval}s for bbox={bbox}")

    seen_event_ids: set[str] = set()
    last_weather_alert: str | None = None
    while True:
        new_text_inputs = []

        try:
            events = fetch_eonet_events(bbox, args.days)
        except requests.RequestException as exc:
            print(f"EONET fetch failed: {exc}")
            events = []

        for event in events:
            if event["id"] in seen_event_ids:
                continue
            seen_event_ids.add(event["id"])

            geometries = event.get("geometry", [])
            if not geometries:
                continue
            coords = geometries[-1].get("coordinates")
            if not coords or geometries[-1].get("type") != "Point":
                continue
            lon, lat = coords[0], coords[1]

            location_id = nearest_road_location_id(builder, lat, lon)
            if not location_id:
                continue

            text = event["title"] + (f" - {event['description']}" if event.get("description") else "")
            new_text_inputs.append({"text": text, "location_id": location_id, "source": "nasa-eonet"})
            print(f"  new event -> {location_id}: {text}")

        if args.enable_usgs:
            try:
                quakes = fetch_usgs_earthquakes(bbox, args.days, args.min_magnitude)
            except requests.RequestException as exc:
                print(f"USGS fetch failed: {exc}")
                quakes = []

            for quake in quakes:
                quake_id = quake.get("id")
                if not quake_id or quake_id in seen_event_ids:
                    continue
                seen_event_ids.add(quake_id)

                lon, lat = quake["geometry"]["coordinates"][:2]
                location_id = nearest_road_location_id(builder, lat, lon)
                if not location_id:
                    continue

                text = f"Earthquake M{quake['properties']['mag']} - {quake['properties']['place']}"
                new_text_inputs.append({"text": text, "location_id": location_id, "source": "usgs"})
                print(f"  new event -> {location_id}: {text}")

        if args.enable_weather and centroid_location_id:
            try:
                current = fetch_openmeteo_current(centroid_lat, centroid_lon)
                alert_text = severe_weather_text(current)
            except requests.RequestException as exc:
                print(f"Open-Meteo fetch failed: {exc}")
                alert_text = None

            if alert_text and alert_text != last_weather_alert:
                last_weather_alert = alert_text
                new_text_inputs.append(
                    {"text": alert_text, "location_id": centroid_location_id, "source": "open-meteo"}
                )
                print(f"  new event -> {centroid_location_id}: {alert_text}")
            elif not alert_text:
                last_weather_alert = None

        if new_text_inputs:
            payload = {"hq_node": hq_node, **base_payload, "text_inputs": new_text_inputs}
            try:
                resp = requests.post(f"{args.backend_url}/analyze", json=payload, timeout=60)
                resp.raise_for_status()
                print(f"  posted {len(new_text_inputs)} event(s) -> /analyze ({resp.status_code})")
            except requests.RequestException as exc:
                print(f"  /analyze POST failed: {exc}")
        else:
            print("  no new events this poll")

        time.sleep(args.interval)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--place", default="Vijayawada, Andhra Pradesh, India", help="OSM place name (keep small)")
    parser.add_argument("--network-type", default="drive")
    parser.add_argument("--backend-url", default="http://localhost:8000")
    parser.add_argument("--hq-node", default=None, help="Defaults to the first intersection node")
    parser.add_argument("--interval", type=int, default=120, help="Poll interval in seconds")
    parser.add_argument("--days", type=int, default=7, help="EONET/USGS lookback window in days")
    parser.add_argument("--min-magnitude", type=float, default=4.0, help="Minimum USGS earthquake magnitude")
    parser.add_argument("--enable-usgs", action=argparse.BooleanOptionalAction, default=True, help="Poll USGS earthquakes")
    parser.add_argument("--enable-weather", action=argparse.BooleanOptionalAction, default=True, help="Poll Open-Meteo severe weather")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
