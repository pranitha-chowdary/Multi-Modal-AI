import { useMemo, useState } from "react";
import { useAlertsSocket } from "./hooks/useAlertsSocket";
import MapView from "./components/MapView.jsx";
import AlertFeed from "./components/AlertFeed.jsx";
import PipelineStages from "./components/PipelineStages.jsx";
import ResponderBoard from "./components/ResponderBoard.jsx";
import ScenarioForm from "./components/ScenarioForm.jsx";

const TABS = [
  { id: "alerts", label: "Live Alerts" },
  { id: "dispatch", label: "Responder Dispatch" },
];

export default function App() {
  const { alerts, connected } = useAlertsSocket();
  const [activeTab, setActiveTab] = useState("alerts");
  const [formOpen, setFormOpen] = useState(true);

  const latestAlert = alerts[0];
  const latestItems = useMemo(() => latestAlert?.items ?? [], [latestAlert]);
  const latestDispatch = useMemo(() => latestAlert?.dispatch ?? {}, [latestAlert]);

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
          {activeTab === "alerts" && <AlertFeed alerts={alerts} />}
          {activeTab === "dispatch" && <ResponderBoard dispatch={latestDispatch} />}
        </aside>
      </main>
    </div>
  );
}

