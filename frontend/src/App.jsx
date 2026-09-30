import { useMemo, useState } from "react";
import { useAlertsSocket } from "./hooks/useAlertsSocket";
import MapView from "./components/MapView.jsx";
import AlertFeed from "./components/AlertFeed.jsx";
import PipelineStages from "./components/PipelineStages.jsx";
import ResponderBoard from "./components/ResponderBoard.jsx";
import ScenarioForm from "./components/ScenarioForm.jsx";
import { notifyTeam } from "./services/api.js";

const TABS = [
  { id: "alerts", label: "Live Alerts" },
  { id: "dispatch", label: "Responder Dispatch" },
];

export default function App() {
  const { alerts, connected } = useAlertsSocket();
  const [activeTab, setActiveTab] = useState("alerts");
  const [formOpen, setFormOpen] = useState(true);

  // Common operating picture: every location ADIS has ever assessed, keyed by
  // location_id, updated in place by newer `action_plan` alerts and by
  // `dispatch_notification` events -- so the map/board persist and stay
  // "replicated" instead of only reflecting the single most recent alert.
  const locationsById = useMemo(() => {
    const merged = new Map();
    // Walk oldest -> newest so later alerts overwrite earlier state per location.
    for (const alert of [...alerts].reverse()) {
      if (alert.type === "action_plan") {
        for (const item of alert.items ?? []) merged.set(item.location_id, item);
      } else if (alert.type === "dispatch_notification" && alert.item) {
        merged.set(alert.item.location_id, alert.item);
      }
    }
    return merged;
  }, [alerts]);

  const latestItems = useMemo(() => Array.from(locationsById.values()), [locationsById]);
  const latestDispatch = useMemo(() => {
    const grouped = {};
    for (const item of latestItems) {
      grouped[item.responder_team] = grouped[item.responder_team] ?? [];
      grouped[item.responder_team].push(item);
    }
    return grouped;
  }, [latestItems]);

  const handleNotify = (locationId) => {
    notifyTeam(locationId).catch((err) => console.error("Notify failed:", err));
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>ADIS — Autonomous Disaster Intelligence System</h1>
        <span className={`status ${connected ? "online" : "offline"}`}>
          {connected ? "Live" : "Reconnecting..."}
        </span>
      </header>

      <PipelineStages items={latestItems} />

      <main className="app-body">
        <section className="left-panel">
          <details className="scenario-form-wrapper" open={formOpen} onToggle={(e) => setFormOpen(e.target.open)}>
            <summary>Run a Scenario</summary>
            <ScenarioForm onResult={() => setActiveTab("dispatch")} />
          </details>
          <div className="map-panel">
            <MapView items={latestItems} />
          </div>
        </section>

        <aside className="feed-panel">
          <div className="tabs">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                className={`tab ${activeTab === tab.id ? "active" : ""}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
          {activeTab === "alerts" && <AlertFeed alerts={alerts} onNotify={handleNotify} />}
          {activeTab === "dispatch" && <ResponderBoard dispatch={latestDispatch} onNotify={handleNotify} />}
        </aside>
      </main>
    </div>
  );
}

