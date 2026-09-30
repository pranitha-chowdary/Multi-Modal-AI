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
