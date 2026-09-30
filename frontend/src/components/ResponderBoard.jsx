const TEAM_LABELS = {
  rescue: "Rescue",
  logistics: "Logistics / Road Clearance",
  monitoring: "Monitoring",
  field_verification: "Field Verification",
};

const TEAM_ORDER = ["rescue", "logistics", "field_verification", "monitoring"];

/**
 * Kanban-style board of the "tie to responders" pipeline stage: one column
 * per responder team, populated from the latest alert's `dispatch` map
 * (see ActionPlan.dispatch_by_team on the backend).
 */
export default function ResponderBoard({ dispatch, onNotify }) {
  const teams = TEAM_ORDER.filter((team) => dispatch[team]?.length);

  if (teams.length === 0) {
    return <p className="empty">No responder dispatch yet — run an analysis to populate this board.</p>;
  }

  return (
    <div className="responder-board">
      {teams.map((team) => (
        <div key={team} className={`responder-column team-${team}`}>
          <h3>{TEAM_LABELS[team] ?? team}</h3>
          {dispatch[team].map((item) => (
            <div key={item.location_id} className="responder-card">
              <div className="responder-card-header">
                <span className={`priority p${item.priority}`}>P{item.priority}</span>
                <span className="location">{item.location_id}</span>
              </div>
              <div className="action">{item.action}</div>
              <div className="rationale">{item.rationale}</div>
              {item.notified ? (
                <div className="notified-badge">✓ Team notified</div>
              ) : (
                <button type="button" className="notify-btn" onClick={() => onNotify?.(item.location_id)}>
                  Notify {TEAM_LABELS[team] ?? team}
                </button>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
