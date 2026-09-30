const GATE_LABELS = {
  dispatch: "confirmed",
  review: "needs review",
  verify: "low confidence",
};

export default function AlertFeed({ alerts, onNotify }) {
  return (
    <div className="alert-feed">
      <h2>Live Alerts</h2>
      {alerts.length === 0 && <p className="empty">Waiting for incoming action plans...</p>}
      <ul>
        {alerts.map((alert, idx) => (
          <li key={idx} className="alert-card">
            <div className="alert-header">
              <span className="alert-type">{alert.type ?? "alert"}</span>
              <span className="alert-time">{alert.timestamp}</span>
            </div>

            {alert.type === "dispatch_notification" && alert.item && (
              <div className="alert-item">
                <span className="notified-badge">✓ Notified</span>
                <span className="location">{alert.item.location_id}</span>
                <span className="action">{alert.item.action}</span>
              </div>
            )}

            {alert.items?.map((item) => (
              <div key={item.location_id} className="alert-item">
                <span className={`priority p${item.priority}`}>P{item.priority}</span>
                <span className="location">{item.location_id}</span>
                <span className="action">{item.action}</span>
                <span className={`gate gate-${item.status}`}>{GATE_LABELS[item.status] ?? item.status}</span>
                <span className="team">{item.responder_team}</span>
                {item.notified ? (
                  <span className="notified-badge">✓ notified</span>
                ) : (
                  <button type="button" className="notify-btn" onClick={() => onNotify?.(item.location_id)}>
                    Notify
                  </button>
                )}
              </div>
            ))}
          </li>
        ))}
      </ul>
    </div>
  );
}
