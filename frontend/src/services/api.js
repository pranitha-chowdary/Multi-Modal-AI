/**
 * Thin fetch wrapper for the ADIS backend. Uses the Vite dev-server proxy
 * (/api -> http://localhost:8000, prefix stripped) so no CORS setup is needed.
 */
export async function runAnalysis(scenario) {
  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(scenario),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Analysis request failed (${response.status}): ${detail}`);
  }
  return response.json();
}

/**
 * Marks an action item as sent to its responder team. The backend broadcasts
 * this over /ws/alerts so every connected dashboard (and, in a real
 * deployment, the responders' own devices) sees it live.
 */
export async function notifyTeam(locationId) {
  const response = await fetch(`/api/dispatch/${encodeURIComponent(locationId)}/notify`, {
    method: "POST",
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Notify request failed (${response.status}): ${detail}`);
  }
  return response.json();
}

/**
 * Public read-only lookup used by the shareable community alert page
 * (/share/{locationId}) -- no auth, just the current known action item.
 */
export async function getDispatchItem(locationId) {
  const response = await fetch(`/api/dispatch/${encodeURIComponent(locationId)}`);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Lookup failed (${response.status}): ${detail}`);
  }
  return response.json();
}
