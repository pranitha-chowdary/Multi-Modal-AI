import { useEffect } from "react";
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from "react-leaflet";

const DEFAULT_CENTER = [17.6868, 83.2185]; // Visakhapatnam, AP - fallback center until real markers arrive

const TEAM_COLORS = {
  rescue: "#f08c8c",
  logistics: "#f0c26a",
  field_verification: "#9fa8ff",
  monitoring: "#63e08a",
};

const ROUTE_COLOR = "#4a90ff"; // Google/Apple-Maps-style blue route line

/**
 * Re-centers/zooms the map to fit every known marker whenever the item set
 * changes - so the view follows wherever the scenario is anchored (a fixed
 * demo city, or the user's real device location) instead of staying pinned
 * to a hardcoded default center.
 */
function FitToMarkers({ points }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 0) return;
    if (points.length === 1) {
      map.setView(points[0], 14);
    } else {
      map.fitBounds(points, { padding: [40, 40] });
    }
  }, [map, points]);
  return null;
}

/**
 * Plots verified locations from incoming action-plan alerts on a live map,
 * colored by which responder team the item was dispatched to, and draws the
 * HQ -> location route (from EvacuationRouter.shortest_safe_path) as a blue
 * polyline when every node on that path has known coordinates.
 */
export default function MapView({ items }) {
  const withCoords = items.filter((item) => item.lat != null && item.lon != null);
  const allPoints = withCoords.map((item) => [item.lat, item.lon]);

  return (
    <MapContainer center={DEFAULT_CENTER} zoom={12} style={{ height: "100%", width: "100%" }}>
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitToMarkers points={allPoints} />
      {withCoords.map(
        (item) =>
          item.route_coords?.length > 1 && (
            <Polyline
              key={`route-${item.location_id}`}
              positions={item.route_coords}
              pathOptions={{ color: ROUTE_COLOR, weight: 4, opacity: 0.8 }}
            />
          )
      )}
      {withCoords.map((item) => (
        <CircleMarker
          key={item.location_id}
          center={[item.lat, item.lon]}
          radius={item.notified ? 12 : 10}
          pathOptions={{
            color: TEAM_COLORS[item.responder_team] ?? "#9fd3ff",
            fillOpacity: item.notified ? 0.95 : 0.6,
            weight: item.notified ? 3 : 1,
          }}
        >
          <Popup>
            <strong>{item.location_id}</strong>
            <br />
            [P{item.priority}] {item.action}
            <br />
            {item.rationale}
            <br />
            {item.notified ? "✓ Responder team notified" : "Not yet notified"}
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
