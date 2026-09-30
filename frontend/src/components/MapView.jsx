import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";

const DEFAULT_CENTER = [17.6868, 83.2185]; // Visakhapatnam, AP - default demo region

const TEAM_COLORS = {
  rescue: "#f08c8c",
  logistics: "#f0c26a",
  field_verification: "#9fa8ff",
  monitoring: "#63e08a",
};

/**
 * Plots verified locations from incoming action-plan alerts on a live map,
 * colored by which responder team the item was dispatched to. Location
 * coordinates are optional in the current alert payload; markers only
 * render for items that carry a lat/lon (see PLAN.md Phase 3 for real
 * KG-backed coordinates).
 */
export default function MapView({ items }) {
  const withCoords = items.filter((item) => item.lat != null && item.lon != null);

  return (
    <MapContainer center={DEFAULT_CENTER} zoom={12} style={{ height: "100%", width: "100%" }}>
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {withCoords.map((item) => (
        <CircleMarker
          key={item.location_id}
          center={[item.lat, item.lon]}
          radius={10}
          pathOptions={{ color: TEAM_COLORS[item.responder_team] ?? "#9fd3ff", fillOpacity: 0.8 }}
        >
          <Popup>
            <strong>{item.location_id}</strong>
            <br />
            [P{item.priority}] {item.action}
            <br />
            {item.rationale}
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
