import { useEffect, useState } from "react";
import { MapContainer, CircleMarker, Polyline, Popup, TileLayer } from "react-leaflet";
import { getDispatchItem } from "../services/api.js";

const REFRESH_MS = 8000;

/**
 * Public, read-only community alert page for a single location -- no
 * dashboard/login needed. Meant to be shared (link, QR code, SMS) with
 * people in the affected locality so they can see the current guidance and
 * follow the same route responders are using to relocate to safety.
 */
export default function ShareView({ locationId }) {
  const [item, setItem] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      getDispatchItem(locationId)
        .then((data) => !cancelled && setItem(data))
        .catch((err) => !cancelled && setError(err.message));
    };
    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [locationId]);

  if (error) {
    return (
      <div className="share-view">
        <h1>ADIS Community Safety Alert</h1>
        <p className="form-error">No active alert found for "{locationId}". Ask a responder for a fresh link.</p>
      </div>
    );
  }

  if (!item) {
    return (
      <div className="share-view">
        <h1>ADIS Community Safety Alert</h1>
        <p>Loading...</p>
      </div>
    );
  }

  const hasCoords = item.lat != null && item.lon != null;

  return (
    <div className="share-view">
      <h1>ADIS Community Safety Alert</h1>
      <div className="share-card">
        <div className="share-location">{item.location_id}</div>
        <div className="share-action">{item.action}</div>
        <div className="share-rationale">{item.rationale}</div>
        <div className={`gate gate-${item.status}`}>
          {item.status === "dispatch" ? "Confirmed" : item.status === "verify" ? "Being verified" : "Under review"}
        </div>
      </div>

      {hasCoords && (
        <div className="share-map">
          <MapContainer center={[item.lat, item.lon]} zoom={14} style={{ height: "100%", width: "100%" }}>
            <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            {item.route_coords?.length > 1 && (
              <Polyline positions={item.route_coords} pathOptions={{ color: "#4a90ff", weight: 4, opacity: 0.8 }} />
            )}
            <CircleMarker center={[item.lat, item.lon]} radius={12} pathOptions={{ color: "#f08c8c", fillOpacity: 0.9 }}>
              <Popup>{item.location_id}: {item.action}</Popup>
            </CircleMarker>
          </MapContainer>
        </div>
      )}

      <p className="share-footer">This page refreshes automatically. Follow the route shown to reach safety.</p>
    </div>
  );
}
