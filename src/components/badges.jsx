export const ADV_STATE = {
  received: { label: "Received", cls: "badge-neutral" },
  pending_verification: { label: "Pending Verification", cls: "badge-amber" },
  verified: { label: "Verified", cls: "badge-teal" },
  closed: { label: "Closed", cls: "badge-neutral" },
};

export function AdvisoryBadge({ adv }) {
  if (adv.state === "closed" && adv.forwarding)
    return <span className="badge badge-green">Forwarded to Farmer</span>;
  if (adv.state === "closed")
    return <span className="badge badge-neutral">Closed · Not Forwarded</span>;
  const s = ADV_STATE[adv.state] || ADV_STATE.received;
  return <span className={`badge ${s.cls}`}>{s.label}</span>;
}

export function SeverityBadge({ severity }) {
  const cls = severity === "High" ? "badge-red" : severity === "Medium" ? "badge-amber" : "badge-neutral";
  return <span className={`badge ${cls}`}>{severity}</span>;
}

const REQ_STATE = {
  received: { label: "Received", cls: "badge-neutral" },
  scheduled: { label: "Accepted · Scheduled", cls: "badge-blue" },
  in_progress: { label: "In Progress", cls: "badge-amber" },
  completed: { label: "Completed", cls: "badge-green" },
  declined: { label: "Declined", cls: "badge-red" },
};

export function RequestBadge({ state }) {
  const s = REQ_STATE[state] || REQ_STATE.received;
  return <span className={`badge ${s.cls}`}>{s.label}</span>;
}

export function ConditionBadge({ condition }) {
  const cls = condition === "Good" ? "badge-green" : condition === "Average" ? "badge-amber" : "badge-red";
  return <span className={`badge ${cls}`}>{condition.toUpperCase()}</span>;
}
