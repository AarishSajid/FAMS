"use client";
// Services page — FAMS_Final design: request queue + manage sheet, base + petrol pricing.
import { useMemo, useState } from "react";
import TopNav from "@/components/TopNav";
import { RequestBadge } from "@/components/badges";
import { useFams } from "@/lib/store";
import { farmById, fmtRs } from "@/lib/data";

export default function Services() {
  const { requests, reqAction } = useFams();
  const [filter, setFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [selected, setSelected] = useState(null);
  const [declineReason, setDeclineReason] = useState("");
  const [schedDate, setSchedDate] = useState("2026-07-19");
  const [petrolInput, setPetrolInput] = useState("");

  const list = useMemo(() => {
    let l = requests;
    if (filter !== "all") l = l.filter((r) => r.state === filter);
    if (typeFilter !== "all") l = l.filter((r) => r.type === typeFilter);
    return l;
  }, [requests, filter, typeFilter]);

  const sel = requests.find((r) => r.id === selected) || null;
  const open = requests.filter((r) => ["received", "scheduled", "in_progress"].includes(r.state));
  const done = requests.filter((r) => r.state === "completed");
  const earned = done.reduce((s, r) => s + r.total, 0);
  const pipeline = open.reduce((s, r) => s + r.total, 0);

  return (
    <div>
      <TopNav />
      <main style={{ padding: 20, maxWidth: 1280, margin: "0 auto", display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-bright)" }}>Service Requests</h1>
          <span style={{ fontSize: 12.5, color: "var(--text-muted)" }}>drones & implements raised from the Farmer App</span>
          <div style={{ marginLeft: "auto", display: "flex", gap: 10 }}>
            <select className="input" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
              <option value="all">All services</option>
              <option value="drone">Drone</option>
              <option value="implement">Implements</option>
            </select>
            <select className="input" value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="all">All states</option>
              <option value="received">Received</option>
              <option value="scheduled">Scheduled</option>
              <option value="in_progress">In progress</option>
              <option value="completed">Completed</option>
              <option value="declined">Declined</option>
            </select>
          </div>
        </div>

        <div style={{ display: "flex", gap: 14 }}>
          {[
            ["Open requests", open.length, null],
            ["Completed this month", done.length, null],
            ["Earned (completed)", fmtRs(earned), "var(--gold-light)"],
            ["Pipeline (open value)", fmtRs(pipeline), null],
          ].map(([t, v, c]) => (
            <div className="card" style={{ flex: 1 }} key={t}>
              <div className="card-title">{t}</div>
              <div className="kpi-value" style={{ fontSize: 22, color: c || "var(--text-bright)" }}>{v}</div>
            </div>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: sel ? "1.7fr 1fr" : "1fr", gap: 14 }}>
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Farmer</th><th>Service</th><th>Type</th><th>Requested</th>
                  <th>Base</th><th>Petrol</th><th>Total</th><th>Status</th><th></th>
                </tr>
              </thead>
              <tbody>
                {list.map((r) => (
                  <tr key={r.id} style={selected === r.id ? { background: "var(--surface-5)" } : undefined}>
                    <td style={{ fontWeight: 600, color: "var(--text-bright)" }}>{r.farmer}
                      <div style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 400 }}>{farmById[r.farmId]?.village}</div>
                    </td>
                    <td>{r.service}</td>
                    <td><span className={`badge ${r.type === "drone" ? "badge-blue" : "badge-neutral"}`}>{r.type}</span></td>
                    <td style={{ color: "var(--text-secondary)" }}>{r.requestedAt}</td>
                    <td>{fmtRs(r.basePrice)}</td>
                    <td>{r.petrol != null ? fmtRs(r.petrol) : <span style={{ color: "var(--text-muted)", fontSize: 11.5 }}>to be added</span>}</td>
                    <td style={{ fontWeight: 600, color: "var(--gold-light)" }}>{r.petrol != null ? fmtRs(r.total) : fmtRs(r.basePrice) + " +"}</td>
                    <td><RequestBadge state={r.state} /></td>
                    <td><button className="btn btn-sm" onClick={() => setSelected(r.id === selected ? null : r.id)}>Manage</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {sel && (
            <div className="card" style={{ alignSelf: "start", position: "sticky", top: 72 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <div className="card-title" style={{ marginBottom: 0 }}>Manage request {sel.id}</div>
                <button className="btn btn-sm" onClick={() => setSelected(null)}>✕</button>
              </div>
              <div className="kv"><span className="k">Farmer</span><span className="v">{sel.farmer}</span></div>
              <div className="kv"><span className="k">Service</span><span className="v">{sel.service}</span></div>
              <div className="kv"><span className="k">Base price (standard)</span><span className="v">{fmtRs(sel.basePrice)}</span></div>
              <div className="kv"><span className="k">Petrol / transport</span><span className="v">{sel.petrol != null ? fmtRs(sel.petrol) : "not set"}</span></div>
              <div className="kv" style={{ borderTop: "1px solid var(--border-default)", marginTop: 4, paddingTop: 8 }}>
                <span className="k">Total</span>
                <span className="v" style={{ color: "var(--gold-light)" }}>{sel.petrol != null ? fmtRs(sel.total) : fmtRs(sel.basePrice) + " + petrol"}</span>
              </div>
              <div className="kv"><span className="k">Status</span><span className="v"><RequestBadge state={sel.state} /></span></div>
              {sel.scheduledFor && <div className="kv"><span className="k">Scheduled for</span><span className="v">{sel.scheduledFor}</span></div>}
              {sel.declineReason && <div className="kv"><span className="k">Decline reason</span><span className="v">{sel.declineReason}</span></div>}

              <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 14 }}>
                {sel.state === "received" && (
                  <>
                    <div style={{ display: "flex", gap: 8 }}>
                      <input
                        type="number" min="0" className="input" style={{ flex: 1 }}
                        placeholder="Petrol / transport cost (Rs.)…"
                        value={petrolInput}
                        onChange={(e) => setPetrolInput(e.target.value)}
                      />
                      <input type="date" className="input" style={{ flex: 1 }} value={schedDate} onChange={(e) => setSchedDate(e.target.value)} />
                    </div>
                    <button
                      className="btn btn-primary"
                      disabled={petrolInput === "" || Number(petrolInput) < 0}
                      title={petrolInput === "" ? "Add the petrol/transport cost for this request first" : ""}
                      onClick={() => { reqAction(sel.id, "schedule", { date: schedDate, petrol: Number(petrolInput) }); setPetrolInput(""); }}
                    >
                      Accept & schedule
                    </button>
                    <div style={{ display: "flex", gap: 8 }}>
                      <input className="input" style={{ flex: 1 }} placeholder="Decline reason…" value={declineReason} onChange={(e) => setDeclineReason(e.target.value)} />
                      <button className="btn btn-danger" disabled={!declineReason} onClick={() => { reqAction(sel.id, "decline", declineReason); setDeclineReason(""); }}>Decline</button>
                    </div>
                  </>
                )}
                {(sel.state === "scheduled" || sel.state === "in_progress") && (
                  <div style={{ display: "flex", gap: 8 }}>
                    <input
                      type="number" min="0" className="input" style={{ flex: 1 }}
                      placeholder={`Petrol (now ${sel.petrol != null ? fmtRs(sel.petrol) : "unset"})…`}
                      value={petrolInput}
                      onChange={(e) => setPetrolInput(e.target.value)}
                    />
                    <button className="btn btn-sm" disabled={petrolInput === ""} onClick={() => { reqAction(sel.id, "petrol", Number(petrolInput)); setPetrolInput(""); }}>
                      Update petrol
                    </button>
                  </div>
                )}
                {sel.state === "scheduled" && (
                  <button className="btn btn-primary" onClick={() => reqAction(sel.id, "start")}>Mark In Progress</button>
                )}
                {sel.state === "in_progress" && (
                  <button className="btn btn-primary" onClick={() => reqAction(sel.id, "complete")}>Mark Completed</button>
                )}
                {(sel.state === "completed" || sel.state === "declined") && (
                  <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Terminal state — the farmer has been notified via the Farmer App (FR-26).</div>
                )}
              </div>
              <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 12 }}>
                Every status change is pushed back to the farmer through the Farmer App.
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
