"use client";
// Farm detail view — DRD §6.2. Fams-prototype layout, Agriverse visual language.
import { useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, Cell,
} from "recharts";
import TopNav from "@/components/TopNav";
import { AdvisoryBadge, SeverityBadge, ConditionBadge } from "@/components/badges";
import { useFams } from "@/lib/store";
import {
  farmById, historyAdvisories, indexSeries, classification, INDICES, IMAGERY_DATES,
  weather, STAGES,
} from "@/lib/data";

const FarmMap = dynamic(() => import("@/components/FarmMap"), { ssr: false });

const tooltipStyle = {
  background: "var(--surface-5)", border: "1px solid var(--border-default)",
  borderRadius: 8, fontSize: 12, color: "var(--text-primary)",
};

function Modal({ title, children, onClose }) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 60, display: "flex", alignItems: "center", justifyContent: "center" }} onClick={onClose}>
      <div className="card" style={{ width: 480, maxWidth: "92%", background: "var(--surface-4)" }} onClick={(e) => e.stopPropagation()}>
        <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-bright)", marginBottom: 14 }}>{title}</div>
        {children}
      </div>
    </div>
  );
}

export default function FarmDetail() {
  const { farmId } = useParams();
  const router = useRouter();
  const { advisories, fieldAgents, assignAgent, recordVerification, forward, close } = useFams();

  const farm = farmById[farmId];
  const [index, setIndex] = useState(null);
  const [imgDate, setImgDate] = useState(IMAGERY_DATES[IMAGERY_DATES.length - 1]);
  const [modal, setModal] = useState(null); // "assign" | "verify" | "forward" | "close"
  const [form, setForm] = useState({});

  const adv = advisories.find((a) => a.farmId === farmId) || null;
  const activeIndex = index || adv?.indexLayer || "NDVI";
  const history = useMemo(() => historyAdvisories.filter((h) => h.farmId === farmId), [farmId]);
  const series = useMemo(() => (farm ? indexSeries(farm, activeIndex) : []), [farm, activeIndex]);
  const classes = useMemo(() => (farm ? classification(farm) : []), [farm]);

  if (!farm) {
    return (
      <div><TopNav /><main style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>Farm not found.</main></div>
    );
  }

  const canForward = adv && adv.verification && adv.feedback && adv.state === "verified" && adv.verification.outcome === "confirmed";
  const canClose = adv && adv.feedback && adv.state === "verified";

  return (
    <div>
      <TopNav />
      <main style={{ padding: 20, maxWidth: 1280, margin: "0 auto", display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <button className="btn btn-sm" onClick={() => router.push("/advisories")}>← Back</button>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-bright)" }}>{farm.farmer}&apos;s Farm</h1>
          <ConditionBadge condition={farm.condition} />
          <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--text-muted)" }}>
            Surveyed {farm.surveyDate} by {farm.surveyor}
          </span>
        </div>

        <div className="card" style={{ padding: 12 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 10, flexWrap: "wrap" }}>
            <div className="card-title" style={{ marginBottom: 0 }}>Satellite analysis</div>
            <div style={{ display: "flex", gap: 6, marginLeft: 10 }}>
              {INDICES.map((ix) => (
                <button
                  key={ix}
                  className="btn btn-sm"
                  style={ix === activeIndex ? { background: "var(--accent-muted)", borderColor: "var(--accent-border)", color: "var(--text-accent)" } : undefined}
                  onClick={() => setIndex(ix)}
                >
                  {ix}
                </button>
              ))}
            </div>
            <span style={{ marginLeft: "auto", fontSize: 11.5, color: "var(--text-muted)" }}>
              <span style={{ color: "#e24b4a" }}>■</span> flagged stress area · boundary from field survey
            </span>
          </div>
          <FarmMap farms={[farm]} mode="field" index={activeIndex} height={340} />
          <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 10, overflowX: "auto" }}>
            <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", flexShrink: 0 }}>Imagery date:</span>
            {IMAGERY_DATES.map((d) => (
              <button
                key={d}
                className="btn btn-sm"
                style={d === imgDate ? { background: "var(--accent)", borderColor: "var(--accent)", color: "#06210a", flexShrink: 0 } : { flexShrink: 0 }}
                onClick={() => setImgDate(d)}
              >
                {d.slice(5)}{d === IMAGERY_DATES[IMAGERY_DATES.length - 1] ? " (latest)" : ""}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr 1fr", gap: 14 }}>
          <div className="card">
            <div className="card-title">Farm & crop profile</div>
            {[
              ["Farmer", farm.farmer], ["Phone", farm.phone || "—"], ["Village", farm.village],
              ["Area", `${farm.acres} acres`], ["Irrigation", farm.irrigation.join(", ")],
              ["Crop", farm.crop.toUpperCase()], ["Variety", farm.variety || "—"],
              ["Sown", farm.sowDate || "—"], ["Expected harvest", farm.harvestDate || "—"],
              ["Yield (exp / act)", `${farm.yieldExpected ?? "—"} / ${farm.yieldActual ?? "—"} mounds`],
              ["Next crop", farm.nextCrop ? `${farm.nextCrop} (${farm.nextSowDate || "TBD"})` : "—"],
            ].map(([k, v]) => (
              <div className="kv" key={k}><span className="k">{k}</span><span className="v">{v}</span></div>
            ))}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="card" style={{ borderColor: adv && adv.state !== "closed" ? "var(--warning-border)" : "var(--border-subtle)" }}>
              <div style={{ display: "flex", alignItems: "center", marginBottom: 10 }}>
                <div className="card-title" style={{ marginBottom: 0 }}>Latest advisory</div>
                <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
                  {adv && <SeverityBadge severity={adv.severity} />}
                  {adv ? <AdvisoryBadge adv={adv} /> : <span className="badge badge-green">No active advisory</span>}
                </div>
              </div>
              {adv ? (
                <>
                  <div style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-primary)" }}>
                    <b style={{ color: "var(--text-bright)" }}>{adv.issueType}:</b> {adv.text}
                  </div>
                  <div style={{ fontSize: 11.5, color: "var(--text-muted)", margin: "8px 0" }}>
                    Cycle {adv.cycle} · {adv.indexLayer} layer · affected {adv.affectedArea} · generated {adv.date}, 06:10
                  </div>
                  {adv.assignedAgentId && (
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 8 }}>
                      Field agent: <b>{fieldAgents.find((a) => a.id === adv.assignedAgentId)?.name || adv.assignedAgent?.firstName || "—"}</b>
                    </div>
                  )}
                  {adv.verification && (
                    <div style={{ background: adv.verification.outcome === "confirmed" ? "var(--success-muted)" : "var(--danger-muted)", border: `1px solid ${adv.verification.outcome === "confirmed" ? "var(--success-border)" : "var(--danger-border)"}`, borderRadius: 8, padding: 10, fontSize: 12, marginBottom: 8 }}>
                      <b>{adv.verification.outcome === "confirmed" ? "✓ Issue confirmed" : "✗ Issue not found"}</b> by {adv.verification.agentName} · {adv.verification.observations}
                      <div style={{ color: "var(--text-secondary)", marginTop: 4 }}>Feedback: {adv.feedback.explanation}</div>
                      {adv.feedback.returnedToAgrobot && <span className="badge badge-teal" style={{ marginTop: 6 }}>Feedback returned to Agrobot</span>}
                    </div>
                  )}
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {adv.state === "received" && (
                      <button className="btn btn-primary" onClick={() => { setForm({ agentId: fieldAgents[0]?.id || "" }); setModal("assign"); }}>Send to Field Agent</button>
                    )}
                    {adv.state === "pending_verification" && (
                      <button className="btn btn-primary" onClick={() => { setForm({ outcome: "confirmed", observations: "", explanation: "" }); setModal("verify"); }}>Record Verification & Feedback</button>
                    )}
                    {adv.state === "verified" && (
                      <>
                        <button className="btn btn-primary" disabled={!canForward} title={!canForward ? "BR-1/BR-4: only confirmed, verified advisories can be forwarded" : ""} onClick={() => { setForm({ note: "" }); setModal("forward"); }}>
                          Forward to Farmer
                        </button>
                        <button className="btn btn-danger" disabled={!canClose} onClick={() => { setForm({ reason: adv.feedback?.falsePositiveReason || "" }); setModal("close"); }}>
                          Close — Do Not Forward
                        </button>
                      </>
                    )}
                    {adv.state === "closed" && (
                      <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                        Terminal state — {adv.forwarding ? "delivered to the farmer via Farmer App" : "closed with feedback, never sent"}.
                      </span>
                    )}
                  </div>
                  {adv.state === "received" && (
                    <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 8 }}>
                      BR-1: forwarding is locked until a field agent verifies this advisory on the ground.
                    </div>
                  )}
                </>
              ) : (
                <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>No advisory generated for this farm in cycle 42. General advisories still reach the farmer.</div>
              )}
            </div>

            <div className="card">
              <div className="card-title">Inputs & risks</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div style={{ background: "var(--surface-3)", borderRadius: 8, padding: 10 }}>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>FERTILIZER</div>
                  <div style={{ fontSize: 12.5 }}>{farm.fertilizer.name || "—"} {farm.fertilizer.qty ? `· ${farm.fertilizer.qty}` : ""}</div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{farm.fertilizer.date || ""}</div>
                </div>
                <div style={{ background: "var(--surface-3)", borderRadius: 8, padding: 10 }}>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>PESTICIDE</div>
                  <div style={{ fontSize: 12.5 }}>{farm.pesticide.name || "None"} {farm.pesticide.qty ? `· ${farm.pesticide.qty}` : ""}</div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{farm.pesticide.date || ""}</div>
                </div>
              </div>
              <div style={{ marginTop: 10, background: farm.disease.outbreak ? "var(--danger-muted)" : "var(--success-muted)", border: `1px solid ${farm.disease.outbreak ? "var(--danger-border)" : "var(--success-border)"}`, borderRadius: 8, padding: 10 }}>
                <div style={{ fontSize: 12.5, fontWeight: 700, color: farm.disease.outbreak ? "var(--danger)" : "var(--success)" }}>
                  {farm.disease.outbreak ? "⚠ Disease outbreak" : "✓ No outbreak reported"}
                </div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
                  {farm.disease.issues ? `Issues: ${farm.disease.issues}` : "No pest/disease issues recorded"}
                  {farm.disease.severity ? ` · severity ${farm.disease.severity}%` : ""}
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div className="card-title" style={{ marginBottom: 0 }}>Today&apos;s weather</div>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{farm.district}</span>
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 10, margin: "8px 0" }}>
                <span style={{ fontSize: 30, fontWeight: 700, color: "var(--text-bright)" }}>{weather.temp}°C</span>
                <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Low {weather.low}°C</span>
              </div>
              <div style={{ display: "flex", gap: 14, fontSize: 11.5, color: "var(--text-secondary)" }}>
                <span>Wind {weather.wind} km/h</span><span>Humidity {weather.humidity}%</span><span>Rain {weather.rain}%</span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 6, marginTop: 12 }}>
                {weather.forecast.map((d) => (
                  <div key={d.day} style={{ background: "var(--surface-3)", borderRadius: 8, padding: "8px 4px", textAlign: "center" }}>
                    <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{d.day}</div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-bright)" }}>{d.hi}°</div>
                    <div style={{ fontSize: 10.5, color: "var(--info)" }}>{d.rain}%</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="card" style={{ flex: 1 }}>
              <div className="card-title">Advisory history</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10, maxHeight: 260, overflowY: "auto" }}>
                {history.length === 0 && <div style={{ fontSize: 12.5, color: "var(--text-muted)" }}>No past advisories for this farm.</div>}
                {history.map((h) => (
                  <div key={h.id} style={{ borderBottom: "1px solid var(--border-subtle)", paddingBottom: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)" }}>{h.issueType}</span>
                      <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Cycle {h.cycle}</span>
                    </div>
                    <div style={{ fontSize: 11.5, color: "var(--text-secondary)", margin: "3px 0" }}>{h.text.slice(0, 90)}…</div>
                    <span className={`badge ${h.forwarding ? "badge-green" : "badge-neutral"}`} style={{ fontSize: 10 }}>
                      {h.forwarding ? "Forwarded" : "Closed — false positive"}
                    </span>
                    <span style={{ fontSize: 10.5, color: "var(--text-muted)", marginLeft: 8 }}>Verified by {h.verification.agentName}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr", gap: 14 }}>
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <div className="card-title" style={{ marginBottom: 0 }}>{activeIndex} values by stage</div>
              <span style={{ fontSize: 11.5, color: "var(--text-muted)" }}>{farm.crop.toUpperCase()} — sown {farm.sowDate}</span>
            </div>
            <ResponsiveContainer width="100%" height={190}>
              <LineChart data={series}>
                <XAxis dataKey="stage" stroke="var(--text-muted)" fontSize={10} tickLine={false} axisLine={false} interval={0} angle={-25} height={50} textAnchor="end" />
                <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} width={30} domain={[0, 1]} />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="actual" name="Actual" stroke="#e24b4a" strokeWidth={2.5} dot={{ r: 3.5, fill: "#e24b4a", stroke: "#fff", strokeWidth: 1 }} />
                <Line type="monotone" dataKey="reference" name="Reference" stroke="#4caf50" strokeWidth={2.5} dot={{ r: 3.5, fill: "#4caf50", stroke: "#fff", strokeWidth: 1 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="card">
            <div className="card-title">{activeIndex} classification</div>
            <ResponsiveContainer width="100%" height={190}>
              <BarChart data={classes} barSize={30}>
                <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={10.5} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} width={24} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {classes.map((c) => <Cell key={c.name} fill={c.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="card">
            <div className="card-title">Audit timeline</div>
            <div style={{ maxHeight: 190, overflowY: "auto", display: "flex", flexDirection: "column", gap: 0 }}>
              {(adv?.events || []).map((e, i) => (
                <div key={i} style={{ display: "flex", gap: 10 }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <div style={{ width: 8, height: 8, borderRadius: 99, background: "var(--accent)", marginTop: 5 }} />
                    {i < adv.events.length - 1 && <div style={{ width: 2, flex: 1, background: "var(--border-default)" }} />}
                  </div>
                  <div style={{ paddingBottom: 12 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>{e.label}</div>
                    <div style={{ fontSize: 10.5, color: "var(--text-muted)" }}>{e.actor} · {e.at.replace("T", " ")}</div>
                    {e.detail && <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{e.detail}</div>}
                  </div>
                </div>
              ))}
              {!adv && <div style={{ fontSize: 12.5, color: "var(--text-muted)" }}>No activity this cycle.</div>}
            </div>
          </div>
        </div>
      </main>

      {modal === "assign" && (
        <Modal title="Assign field agent" onClose={() => setModal(null)}>
          <div style={{ fontSize: 12.5, color: "var(--text-secondary)", marginBottom: 12 }}>
            The agent visits the farm to establish ground truth before anything reaches the farmer (BR-1).
          </div>
          <select className="input" style={{ width: "100%", marginBottom: 14 }} value={form.agentId} onChange={(e) => setForm({ ...form, agentId: e.target.value })}>
            {fieldAgents.length === 0 && <option value="">No field agents available</option>}
            {fieldAgents.map((a) => <option key={a.id} value={a.id}>{a.name} — {a.status}</option>)}
          </select>
          <button className="btn btn-primary" style={{ width: "100%" }} disabled={!form.agentId} onClick={() => { assignAgent(adv.id, form.agentId); setModal(null); }}>
            Assign & mark Pending Verification
          </button>
        </Modal>
      )}

      {modal === "verify" && (
        <Modal title="Record verification & mandatory feedback" onClose={() => setModal(null)}>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            {["confirmed", "not_found"].map((o) => (
              <button key={o} className="btn" style={{ flex: 1, ...(form.outcome === o ? { background: o === "confirmed" ? "var(--success-muted)" : "var(--danger-muted)", borderColor: o === "confirmed" ? "var(--success-border)" : "var(--danger-border)", color: o === "confirmed" ? "var(--success)" : "var(--danger)" } : {}) }} onClick={() => setForm({ ...form, outcome: o })}>
                {o === "confirmed" ? "✓ Issue confirmed" : "✗ Issue not found"}
              </button>
            ))}
          </div>
          <textarea className="input" style={{ width: "100%", minHeight: 60, marginBottom: 10 }} placeholder="Agent's field observations…" value={form.observations} onChange={(e) => setForm({ ...form, observations: e.target.value })} />
          <textarea className="input" style={{ width: "100%", minHeight: 60, marginBottom: 10 }} placeholder="Mandatory feedback / explanation (BR-2)…" value={form.explanation} onChange={(e) => setForm({ ...form, explanation: e.target.value })} />
          {form.outcome === "not_found" && (
            <input className="input" style={{ width: "100%", marginBottom: 10 }} placeholder="Why was the analysis wrong? (e.g., recently harvested patch)" value={form.reason || ""} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
          )}
          <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginBottom: 12 }}>
            Feedback is required in all cases and is returned to Agrobot automatically (BR-2, BR-6).
          </div>
          <button
            className="btn btn-primary" style={{ width: "100%" }}
            disabled={!form.observations || !form.explanation}
            onClick={() => {
              recordVerification(adv.id, { outcome: form.outcome, observations: form.observations, explanation: form.explanation, falsePositiveReason: form.reason });
              setModal(null);
            }}
          >
            Save verification & feedback
          </button>
        </Modal>
      )}

      {modal === "forward" && (
        <Modal title="Forward to farmer via Farmer App" onClose={() => setModal(null)}>
          <div style={{ fontSize: 12.5, color: "var(--text-secondary)", marginBottom: 10 }}>
            Optionally annotate the advisory with local context from the field visit (FR-15).
          </div>
          <textarea className="input" style={{ width: "100%", minHeight: 70, marginBottom: 12 }} placeholder="Optional annotation…" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={() => { forward(adv.id, form.note); setModal(null); }}>
            Send to {farm.farmer}
          </button>
        </Modal>
      )}

      {modal === "close" && (
        <Modal title="Close advisory — do not forward" onClose={() => setModal(null)}>
          <div style={{ fontSize: 12.5, color: "var(--text-secondary)", marginBottom: 10 }}>
            A closed advisory can never be sent to the farmer (BR-4). Its feedback is retained and returned to Agrobot.
          </div>
          <input className="input" style={{ width: "100%", marginBottom: 12 }} placeholder="Closure reason…" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
          <button className="btn btn-danger" style={{ width: "100%" }} disabled={!form.reason} onClick={() => { close(adv.id, form.reason); setModal(null); }}>
            Close advisory
          </button>
        </Modal>
      )}
    </div>
  );
}
