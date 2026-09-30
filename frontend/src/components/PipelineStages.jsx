/**
 * Static visualization of the ADIS execution plan's stage sequence
 * (see src/adis/orchestrator/pipeline.py docstring), with live counts
 * derived from the most recent action-plan alert.
 */
const GATE_LABELS = {
  dispatch: "confirmed",
  review: "needs review",
  verify: "low confidence",
};

function countBy(items, keyFn) {
  const counts = {};
  for (const item of items) {
    const key = keyFn(item);
    counts[key] = (counts[key] ?? 0) + 1;
  }
  return counts;
}

export default function PipelineStages({ items }) {
  const gateCounts = countBy(items, (item) => item.status);
  const teamCounts = countBy(items, (item) => item.responder_team);
  const routedCount = items.filter((item) => item.rationale?.includes("route via")).length;
  const contradictionCount = items.filter((item) => item.rationale?.includes("contradiction")).length;

  const stages = [
    {
      name: "Perception",
      detail: items.length ? `${items.length} location(s) processed` : "waiting for input",
    },
    {
      name: "Cross-Modal Verification",
      detail: items.length ? `${contradictionCount} contradiction(s) resolved` : "\u2014",
    },
    {
      name: "Confidence / Consistency Gate",
      detail: items.length
        ? Object.entries(gateCounts)
            .map(([status, count]) => `${count} ${GATE_LABELS[status] ?? status}`)
            .join(", ")
        : "\u2014",
    },
    {
      name: "Routing / Plan of Action",
      detail: items.length ? `${routedCount}/${items.length} route(s) found` : "\u2014",
    },
    {
      name: "Responder Dispatch",
      detail: items.length
        ? Object.entries(teamCounts)
            .map(([team, count]) => `${team}: ${count}`)
            .join(", ")
        : "\u2014",
    },
  ];

  return (
    <ol className="pipeline-stages">
      {stages.map((stage, idx) => (
        <li key={stage.name} className="pipeline-stage">
          <span className="pipeline-stage-index">{idx + 1}</span>
          <div>
            <div className="pipeline-stage-name">{stage.name}</div>
            <div className="pipeline-stage-detail">{stage.detail}</div>
          </div>
        </li>
      ))}
    </ol>
  );
}
