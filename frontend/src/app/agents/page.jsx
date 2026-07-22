"use client";
// Field agents page — carried over from the Fams prototype: agents table with
// expandable task rows. Tasks derive from advisory assignments.
import { useState } from "react";
import { useRouter } from "next/navigation";
import TopNav from "@/components/TopNav";
import { useFams } from "@/lib/store";
import { farmById } from "@/lib/data";

const TASK_BADGE = {
  pending_verification: ["Pending visit", "badge-amber"],
  verified: ["Completed", "badge-green"],
  closed: ["Completed", "badge-green"],
};

export default function Agents() {
  const { advisories, fieldAgents } = useFams();
  const router = useRouter();
  const [openId, setOpenId] = useState(null);

  const tasksFor = (agentId) =>
    advisories
      .filter((a) => a.assignedAgentId === agentId)
      .map((a) => ({
        id: a.id,
        farmId: a.farmId,
        farm: `${farmById[a.farmId]?.farmer || "Unknown"}'s Farm`,
        issue: `${a.issueType} verification`,
        state: a.state,
        done: !!a.verification,
      }));

  return (
    <div>
      <TopNav />
      <main style={{ padding: 20, maxWidth: 1080, margin: "0 auto", display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-bright)" }}>Field Agents</h1>
          <span style={{ fontSize: 12.5, color: "var(--text-muted)" }}>
            ground-truth verification team — findings are entered by the manager (SRS OQ-1)
          </span>
        </div>

        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="tbl">
            <thead>
              <tr><th style={{ width: 40 }}></th><th>Agent</th><th>Phone</th><th>Availability</th><th>Active tasks</th><th>Completed today</th></tr>
            </thead>
            <tbody>
              {fieldAgents.map((ag) => {
                const tasks = tasksFor(ag.id);
                const active = tasks.filter((t) => !t.done).length;
                const doneCount = tasks.filter((t) => t.done).length;
                const isOpen = openId === ag.id;
                return [
                  <tr key={ag.id} onClick={() => setOpenId(isOpen ? null : ag.id)} style={{ cursor: "pointer" }}>
                    <td style={{ color: "var(--text-muted)" }}>{isOpen ? "▾" : "▸"}</td>
                    <td style={{ fontWeight: 600, color: "var(--text-bright)" }}>{ag.name}</td>
                    <td style={{ color: "var(--text-secondary)" }}>{ag.phone}</td>
                    <td>
                      <span className={`badge ${active > 0 ? "badge-amber" : "badge-green"}`}>
                        {active > 0 ? "On assignment" : "Available"}
                      </span>
                    </td>
                    <td style={{ textAlign: "center" }}>{active}</td>
                    <td style={{ textAlign: "center" }}>{doneCount}</td>
                  </tr>,
                  isOpen && (
                    <tr key={ag.id + "-tasks"}>
                      <td colSpan={6} style={{ background: "var(--surface-3)", padding: "12px 20px" }}>
                        {tasks.length === 0 ? (
                          <span style={{ fontSize: 12.5, color: "var(--text-muted)" }}>No tasks assigned this cycle.</span>
                        ) : (
                          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                            {tasks.map((t) => {
                              const [label, cls] = t.done ? TASK_BADGE.verified : TASK_BADGE.pending_verification;
                              return (
                                <div key={t.id} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                                  <span className={`badge ${cls}`}>{label}</span>
                                  <span style={{ fontSize: 13, fontWeight: 600 }}>{t.farm}</span>
                                  <span style={{ fontSize: 12.5, color: "var(--text-secondary)" }}>{t.issue}</span>
                                  <button className="btn btn-sm" style={{ marginLeft: "auto" }} onClick={() => router.push(`/advisories/${t.farmId}`)}>
                                    Open advisory
                                  </button>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </td>
                    </tr>
                  ),
                ];
              })}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
