import { useState } from "react";
import { runAnalysis } from "../services/api.js";

const NODE_TYPES = ["hospital", "shelter", "building"];

const EXAMPLE_SCENARIO = {
  hqNode: "HQ",
  intersections: "HQ, N1, N2, N3",
  intersectionCoords: {
    HQ: [17.6868, 83.2185],
    N1: [17.692, 83.219],
    N2: [17.698, 83.22],
    N3: [17.689, 83.235],
  },
  roads: [
    { location_id: "road_hq_n1", node_a: "HQ", node_b: "N1", length_km: "2.0" },
    { location_id: "road_n1_n2", node_a: "N1", node_b: "N2", length_km: "1.5" },
    { location_id: "road_n1_n3", node_a: "N1", node_b: "N3", length_km: "3.0" },
  ],
  facilities: [
    { location_id: "hospital_1", node_type: "hospital", name: "City Hospital", nearest_intersection: "N2", capacity: "", lat: "17.6980", lon: "83.2200" },
    { location_id: "shelter_1", node_type: "shelter", name: "Community Shelter", nearest_intersection: "N3", capacity: "", lat: "17.6890", lon: "83.2350" },
  ],
  visionInputs: [{ image_path: "data/raw/image.png", location_id: "hospital_1", source: "satellite" }],
  textInputs: [
    { text: "People trapped, need rescue near hospital", location_id: "hospital_1", source: "emergency-call" },
  ],
};

// Second demo case: blocked road + an unreachable facility (no road edge to N4
// at all) - shows the "reroute supplies" action and the "no safe route found"
// degraded-but-safe fallback in the rationale, without crashing.
const BLOCKED_ROUTE_SCENARIO = {
  hqNode: "HQ",
  intersections: "HQ, N1, N2, N3, N4",
  intersectionCoords: {
    HQ: [17.6868, 83.2185],
    N1: [17.692, 83.219],
    N2: [17.698, 83.22],
    N3: [17.689, 83.235],
    N4: [17.705, 83.245],
  },
  roads: [
    { location_id: "road_hq_n1", node_a: "HQ", node_b: "N1", length_km: "2.0" },
    { location_id: "road_n1_n2", node_a: "N1", node_b: "N2", length_km: "1.5" },
    { location_id: "road_n1_n3", node_a: "N1", node_b: "N3", length_km: "3.0" },
  ],
  facilities: [
    { location_id: "shelter_1", node_type: "shelter", name: "Community Shelter", nearest_intersection: "N3", capacity: "", lat: "17.6890", lon: "83.2350" },
    { location_id: "clinic_1", node_type: "building", name: "Isolated Clinic", nearest_intersection: "N4", capacity: "", lat: "17.7050", lon: "83.2450" },
  ],
  visionInputs: [],
  textInputs: [
    { text: "Main road to the shelter is completely blocked by fallen debris", location_id: "shelter_1", source: "field-report" },
    { text: "Clinic staff need supplies, road access unclear", location_id: "clinic_1", source: "radio" },
  ],
};

function emptyRoad() {
  return { location_id: "", node_a: "", node_b: "", length_km: "" };
}
function emptyFacility() {
  return { location_id: "", node_type: "hospital", name: "", nearest_intersection: "", capacity: "", lat: "", lon: "" };
}
function emptyVisionInput() {
  return { image_path: "", location_id: "", source: "satellite" };
}
function emptyTextInput() {
  return { text: "", location_id: "", source: "social-media" };
}

function updateRow(list, setList, idx, field, value) {
  setList(list.map((row, i) => (i === idx ? { ...row, [field]: value } : row)));
}

// Converts a small km offset to a lat/lon degree offset near the given
// latitude (good enough for placing demo nodes a few hundred meters/km
// apart around a real GPS fix - not for long-distance navigation).
function offsetCoords(lat, lon, dNorthKm, dEastKm) {
  const dLat = dNorthKm / 111;
  const dLon = dEastKm / (111 * Math.cos((lat * Math.PI) / 180));
  return [lat + dLat, lon + dLon];
}

// Builds a small synthetic local road network anchored at the user's real
// device location - there's no live OSM road network loaded in this manual
// scenario mode (see KnowledgeGraphBuilder.from_osm for the real-network
// path), so this places HQ/intersections/facilities relative to the actual
// GPS fix rather than a hardcoded demo city.
function buildLiveLocationScenario(lat, lon) {
  const n1 = offsetCoords(lat, lon, 0.8, 0);
  const n2 = offsetCoords(lat, lon, 1.2, 1.0);
  const n3 = offsetCoords(lat, lon, -0.6, 1.3);
  return {
    hqNode: "HQ",
    intersections: "HQ, N1, N2, N3",
    intersectionCoords: { HQ: [lat, lon], N1: n1, N2: n2, N3: n3 },
    roads: [
      { location_id: "road_hq_n1", node_a: "HQ", node_b: "N1", length_km: "0.8" },
      { location_id: "road_n1_n2", node_a: "N1", node_b: "N2", length_km: "0.6" },
      { location_id: "road_n1_n3", node_a: "N1", node_b: "N3", length_km: "1.4" },
    ],
    facilities: [
      {
        location_id: "hospital_1",
        node_type: "hospital",
        name: "Nearest Hospital",
        nearest_intersection: "N2",
        capacity: "",
        lat: String(n2[0]),
        lon: String(n2[1]),
      },
      {
        location_id: "shelter_1",
        node_type: "shelter",
        name: "Nearest Shelter",
        nearest_intersection: "N3",
        capacity: "",
        lat: String(n3[0]),
        lon: String(n3[1]),
      },
    ],
    visionInputs: [{ image_path: "data/raw/image.png", location_id: "hospital_1", source: "satellite" }],
    textInputs: [
      { text: "People trapped, need rescue near hospital", location_id: "hospital_1", source: "emergency-call" },
    ],
  };
}

export default function ScenarioForm({ onResult }) {
  const [hqNode, setHqNode] = useState("HQ");
  const [intersections, setIntersections] = useState("HQ, N1, N2, N3");
  const [intersectionCoords, setIntersectionCoords] = useState({});
  const [roads, setRoads] = useState([emptyRoad()]);
  const [facilities, setFacilities] = useState([emptyFacility()]);
  const [visionInputs, setVisionInputs] = useState([emptyVisionInput()]);
  const [textInputs, setTextInputs] = useState([emptyTextInput()]);
  const [submitting, setSubmitting] = useState(false);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState(null);

  const loadScenario = (scenario) => {
    setHqNode(scenario.hqNode);
    setIntersections(scenario.intersections);
    setIntersectionCoords(scenario.intersectionCoords ?? {});
    setRoads(scenario.roads);
    setFacilities(scenario.facilities);
    setVisionInputs(scenario.visionInputs.length ? scenario.visionInputs : [emptyVisionInput()]);
    setTextInputs(scenario.textInputs);
    setError(null);
  };

  const useMyLocation = () => {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by this browser.");
      return;
    }
    setLocating(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        loadScenario(buildLiveLocationScenario(position.coords.latitude, position.coords.longitude));
        setLocating(false);
      },
      (err) => {
        setError(`Could not get your location: ${err.message}`);
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        hq_node: hqNode,
        intersections: intersections
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        intersection_coords: intersectionCoords,
        roads: roads
          .filter((r) => r.location_id && r.node_a && r.node_b)
          .map((r) => ({ ...r, length_km: parseFloat(r.length_km) || 0 })),
        facilities: facilities
          .filter((f) => f.location_id && f.nearest_intersection)
          .map((f) => ({
            ...f,
            capacity: f.capacity ? parseInt(f.capacity, 10) : null,
            lat: f.lat ? parseFloat(f.lat) : null,
            lon: f.lon ? parseFloat(f.lon) : null,
          })),
        vision_inputs: visionInputs.filter((v) => v.image_path && v.location_id),
        text_inputs: textInputs.filter((t) => t.text && t.location_id),
      };
      const result = await runAnalysis(payload);
      onResult?.(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="scenario-form" onSubmit={handleSubmit}>
      <div className="scenario-form-toolbar">
        <h2>Run a Scenario</h2>
        <button type="button" className="secondary" onClick={useMyLocation} disabled={locating}>
          {locating ? "Locating..." : "\ud83d\udccd Use My Location"}
        </button>
        <button type="button" className="secondary" onClick={() => loadScenario(EXAMPLE_SCENARIO)}>
          Load Example: Rescue
        </button>
        <button type="button" className="secondary" onClick={() => loadScenario(BLOCKED_ROUTE_SCENARIO)}>
          Load Example: Blocked Road
        </button>
      </div>

      <label>
        HQ node
        <input value={hqNode} onChange={(e) => setHqNode(e.target.value)} required />
      </label>

      <label>
        Intersections (comma-separated)
        <input value={intersections} onChange={(e) => setIntersections(e.target.value)} />
      </label>

      <fieldset>
        <legend>Roads</legend>
        {roads.map((road, idx) => (
          <div className="form-row" key={idx}>
            <input
              placeholder="location_id"
              value={road.location_id}
              onChange={(e) => updateRow(roads, setRoads, idx, "location_id", e.target.value)}
            />
            <input
              placeholder="node_a"
              value={road.node_a}
              onChange={(e) => updateRow(roads, setRoads, idx, "node_a", e.target.value)}
            />
            <input
              placeholder="node_b"
              value={road.node_b}
              onChange={(e) => updateRow(roads, setRoads, idx, "node_b", e.target.value)}
            />
            <input
              placeholder="length_km"
              type="number"
              step="0.1"
              value={road.length_km}
              onChange={(e) => updateRow(roads, setRoads, idx, "length_km", e.target.value)}
            />
            <button type="button" className="remove" onClick={() => setRoads(roads.filter((_, i) => i !== idx))}>
              ✕
            </button>
          </div>
        ))}
        <button type="button" className="secondary" onClick={() => setRoads([...roads, emptyRoad()])}>
          + Add road
        </button>
      </fieldset>

      <fieldset>
        <legend>Facilities</legend>
        {facilities.map((facility, idx) => (
          <div className="form-row" key={idx}>
            <input
              placeholder="location_id"
              value={facility.location_id}
              onChange={(e) => updateRow(facilities, setFacilities, idx, "location_id", e.target.value)}
            />
            <select
              value={facility.node_type}
              onChange={(e) => updateRow(facilities, setFacilities, idx, "node_type", e.target.value)}
            >
              {NODE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <input
              placeholder="name"
              value={facility.name}
              onChange={(e) => updateRow(facilities, setFacilities, idx, "name", e.target.value)}
            />
            <input
              placeholder="nearest_intersection"
              value={facility.nearest_intersection}
              onChange={(e) => updateRow(facilities, setFacilities, idx, "nearest_intersection", e.target.value)}
            />
            <input
              placeholder="lat (optional, for map)"
              value={facility.lat}
              onChange={(e) => updateRow(facilities, setFacilities, idx, "lat", e.target.value)}
            />
            <input
              placeholder="lon (optional, for map)"
              value={facility.lon}
              onChange={(e) => updateRow(facilities, setFacilities, idx, "lon", e.target.value)}
            />
            <button
              type="button"
              className="remove"
              onClick={() => setFacilities(facilities.filter((_, i) => i !== idx))}
            >
              ✕
            </button>
          </div>
        ))}
        <button type="button" className="secondary" onClick={() => setFacilities([...facilities, emptyFacility()])}>
          + Add facility
        </button>
      </fieldset>

      <fieldset>
        <legend>Vision inputs (server-side image paths)</legend>
        {visionInputs.map((input, idx) => (
          <div className="form-row" key={idx}>
            <input
              placeholder="image_path e.g. data/raw/image.png"
              value={input.image_path}
              onChange={(e) => updateRow(visionInputs, setVisionInputs, idx, "image_path", e.target.value)}
            />
            <input
              placeholder="location_id"
              value={input.location_id}
              onChange={(e) => updateRow(visionInputs, setVisionInputs, idx, "location_id", e.target.value)}
            />
            <input
              placeholder="source"
              value={input.source}
              onChange={(e) => updateRow(visionInputs, setVisionInputs, idx, "source", e.target.value)}
            />
            <button
              type="button"
              className="remove"
              onClick={() => setVisionInputs(visionInputs.filter((_, i) => i !== idx))}
            >
              ✕
            </button>
          </div>
        ))}
        <button type="button" className="secondary" onClick={() => setVisionInputs([...visionInputs, emptyVisionInput()])}>
          + Add vision input
        </button>
      </fieldset>

      <fieldset>
        <legend>Text inputs</legend>
        {textInputs.map((input, idx) => (
          <div className="form-row" key={idx}>
            <input
              placeholder="raw text"
              value={input.text}
              onChange={(e) => updateRow(textInputs, setTextInputs, idx, "text", e.target.value)}
            />
            <input
              placeholder="location_id"
              value={input.location_id}
              onChange={(e) => updateRow(textInputs, setTextInputs, idx, "location_id", e.target.value)}
            />
            <input
              placeholder="source"
              value={input.source}
              onChange={(e) => updateRow(textInputs, setTextInputs, idx, "source", e.target.value)}
            />
            <button
              type="button"
              className="remove"
              onClick={() => setTextInputs(textInputs.filter((_, i) => i !== idx))}
            >
              ✕
            </button>
          </div>
        ))}
        <button type="button" className="secondary" onClick={() => setTextInputs([...textInputs, emptyTextInput()])}>
          + Add text input
        </button>
      </fieldset>

      {error && <p className="form-error">{error}</p>}

      <button type="submit" className="primary" disabled={submitting}>
        {submitting ? "Running pipeline..." : "Run Analysis"}
      </button>
    </form>
  );
}
