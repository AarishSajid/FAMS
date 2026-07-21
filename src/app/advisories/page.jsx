"use client";
// Advisories page — DRD §6.1: farms table with farmer, area, advisory type,
// total advisories, recent advisory + status, and View. General advisories strip on top.
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import TopNav from "@/components/TopNav";
import { AdvisoryBadge } from "@/components/badges";
import { useFams } from "@/lib/store";
import { farms, generalAdvisories, historyAdvisories } from "@/lib/data";

export default function Advisories() {
  const { advisories } = useFams();
  const router = useRouter();
  const [q, setQ] = useState("");
  const [stateFilter, setStateFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [sort, setSort] = useState(["advisories", -1]);
  const [showGeneral, setShowGeneral] = useState(true);

  const rows = useMemo(() => {
    const historyCount = {};
    for (const h of historyAdvisories) historyCount[h.farmId] = (historyCount[h.farmId] || 0) + 1;

    let list = farms.map((f) => {
      const current = advisories.filter((a) => a.farmId === f.id);
      const recent = current[0] || null;
      const total = current.length + (historyCount[f.id] || 0);
      return {
        farm: f,
        recent,
        total,
        advType: total > 0 ? "farm" : "general",
      };
    });

    if (q) {
      const s = q.toLowerCase();
      list = list.filter((r) => r.farm.farmer.toLowerCase().includes(s) || r.farm.village.toLowerCase().includes(s));
    }
    if (typeFilter !== "all") list = list.filter((r) => r.advType === typeFilter);
    if (stateFilter !== "all") {
      if (stateFilter === "active") list = list.filter((r) => r.recent && r.recent.state !== "closed");
      else list = list.filter((r) => r.recent && r.recent.state === stateFilter);
    }

    const [key, dir] = sort;
    list.sort((a, b) => {
      const va = key === "farmer" ? a.farm.farmer : key === "area" ? a.farm.acres : a.total;
      const vb = key === "farmer" ? b.farm.farmer : key === "area" ? b.farm.acres : b.total;
      return (va > vb ? 1 : va < vb ? -1 : 0) * dir;
    });
    return list;
  }, [advisories, q, stateFilter, typeFilter, sort]);

  const th = (label, key) => (
    <th onClick={() => setSort(([k, d]) => [key, k === key ? -d : -1])}>
      {label} {sort[0] === key ? (sort[1] > 0 ? "↑" : "↓") : ""}
    </th>
  );

  return (
    <div>
      <TopNav />
      <main style={{ padding: 20, maxWidth: 1280, margin: "0 auto", display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-bright)" }}>Advisories</h1>
          <span style={{ fontSize: 12.5, color: "var(--text-muted)" }}>{rows.length} farms</span>
          <div style={{ marginLeft: "auto", display: "flex", gap: 10 }}>
            <input className="input" placeholder="Search farmer or village…" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: 220 }} />
            <select className="input" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
              <option value="all">All types</option>
              <option value="farm">Farm-level</option>
              <option value="general">General only</option>
            </select>
            <select className="input" value={stateFilter} onChange={(e) => setStateFilter(e.target.value)}>
              <option value="all">All states</option>
              <option value="active">Needs action</option>
              <option value="received">Received</option>
              <option value="pending_verification">Pending verification</option>
              <option value="verified">Verified</option>
              <option value="closed">Closed</option>
            </select>
          </div>
        </div>

        <div className="card" style={{ padding: 12 }}>
          <div style={{ display: "flex", alignItems: "center", cursor: "pointer" }} onClick={() => setShowGeneral(!showGeneral)}>
            <div className="card-title" style={{ marginBottom: 0 }}>
              General advisories today ({generalAdvisories.length}) — broadcast to all farms
            </div>
            <span style={{ marginLeft: "auto", color: "var(--text-muted)", fontSize: 12 }}>{showGeneral ? "hide ▲" : "show ▼"}</span>
          </div>
          {showGeneral && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10, marginTop: 12 }}>
              {generalAdvisories.map((g) => (
                <div key={g.id} style={{ background: "var(--surface-3)", borderRadius: 8, padding: 10, border: "1px solid var(--border-subtle)" }}>
                  <div style={{ fontSize: 12.5, fontWeight: 700, color: "#2dd4bf", marginBottom: 4 }}>{g.title}</div>
                  <div style={{ fontSize: 11.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>{g.text}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ maxHeight: 560, overflowY: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  {th("Farmer", "farmer")}
                  <th>Village</th>
                  {th("Area", "area")}
                  <th>Advisory type</th>
                  {th("Total advisories", "advisories")}
                  <th>Recent advisory</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {rows.map(({ farm: f, recent, total, advType }) => (
                  <tr key={f.id} style={recent && recent.state !== "closed" ? { boxShadow: "inset 3px 0 0 var(--warning)" } : undefined}>
                    <td style={{ fontWeight: 600, color: "var(--text-bright)" }}>{f.farmer}</td>
                    <td style={{ color: "var(--text-secondary)" }}>{f.village}</td>
                    <td>{f.acres} ac</td>
                    <td>
                      {advType === "farm"
                        ? <span className="badge badge-teal">Farm-level</span>
                        : <span className="badge badge-neutral">General only</span>}
                    </td>
                    <td style={{ textAlign: "center" }}>{total}</td>
                    <td style={{ maxWidth: 220 }}>
                      {recent
                        ? <span style={{ fontSize: 12.5 }}>{recent.issueType}</span>
                        : <span style={{ color: "var(--text-muted)", fontSize: 12 }}>—</span>}
                    </td>
                    <td>{recent ? <AdvisoryBadge adv={recent} /> : <span className="badge badge-green">No issues</span>}</td>
                    <td>
                      <button className="btn btn-sm" onClick={() => router.push(`/advisories/${f.id}`)}>View</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
