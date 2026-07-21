"use client";
// Chief Agronomist portal — DRD §10. Read-only, organisation-wide oversight:
// KPI tiles → sortable center comparison table with drill-down → trend charts.
import { useMemo, useState } from "react";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import TopNav from "@/components/TopNav";
import { useFams } from "@/lib/store";
import { allFarms, CENTERS, fmtRs, CYCLE } from "@/lib/data";

const tooltipStyle = {
  background: "var(--surface-5)", border: "1px solid var(--border-default)",
  borderRadius: 8, fontSize: 12, color: "var(--text-primary)",
};

const fpTrend = [
  { cycle: "C37", org: 34, best: 22 },
  { cycle: "C38", org: 31, best: 20 },
  { cycle: "C39", org: 27, best: 18 },
  { cycle: "C40", org: 24, best: 15 },
  { cycle: "C41", org: 21, best: 14 },
  { cycle: "C42", org: 18, best: 11 },
];

const implByCenter = [
  { month: "Feb", "Layyah": 21500, "Sheikhupura": 18200, "Muridke": 14100 },
  { month: "Mar", "Layyah": 26800, "Sheikhupura": 19900, "Muridke": 15800 },
  { month: "Apr", "Layyah": 24200, "Sheikhupura": 22400, "Muridke": 17300 },
  { month: "May", "Layyah": 31600, "Sheikhupura": 24900, "Muridke": 18800 },
  { month: "Jun", "Layyah": 35400, "Sheikhupura": 27300, "Muridke": 21200 },
  { month: "Jul", "Layyah": 41200, "Sheikhupura": 29500, "Muridke": 23600 },
];

const turnaround = [
  { type: "Drone spraying", days: 1.8 },
  { type: "Drone survey", days: 2.4 },
  { type: "Tractor", days: 3.1 },
  { type: "Harvester", days: 4.6 },
  { type: "Leveler", days: 3.8 },
];

export default function Overview() {
  const { advisories, requests } = useFams();
  const [sort, setSort] = useState(["revenue", -1]);
  const [selected, setSelected] = useState(null);

  const centers = useMemo(() => {
    return CENTERS.map((c, i) => {
      const cf = allFarms.filter((f) => f.centerId === c.id);
      // sc-1 uses live advisory/request state; others are representative
      const live = i === 0;
      const adv = live
        ? {
            received: advisories.length,
            verified: advisories.filter((a) => a.verification).length,
            forwarded: advisories.filter((a) => a.forwarding).length,
            overdue: advisories.filter((a) => a.state === "received").length,
            fpRate: 18,
          }
        : i === 1
          ? { received: 11, verified: 8, forwarded: 6, overdue: 1, fpRate: 25 }
          : { received: 8, verified: 4, forwarded: 3, overdue: 3, fpRate: 31 };
      const reqs = live
        ? {
            open: requests.filter((r) => ["received", "scheduled", "in_progress"].includes(r.state)).length,
            done: requests.filter((r) => r.state === "completed").length,
            turnaround: 2.6,
          }
        : i === 1
          ? { open: 4, done: 9, turnaround: 3.2 }
          : { open: 6, done: 5, turnaround: 4.5 };
      const implEarnings = i === 0
        ? requests.filter((r) => r.state === "completed").reduce((s, r) => s + r.total, 0)
        : i === 1 ? 29500 : 23600;
      return {
        ...c,
        farms: cf.length,
        acres: Math.round(cf.reduce((s, f) => s + f.acres, 0)),
        revenue: implEarnings,
        verifyRate: Math.round((adv.verified / Math.max(1, adv.received)) * 100),
        ...adv,
        req: reqs,
      };
    });
  }, [advisories, requests]);

  const sorted = useMemo(() => {
    const [key, dir] = sort;
    return [...centers].sort((a, b) => {
      const va = key === "req" ? a.req.open : a[key];
      const vb = key === "req" ? b.req.open : b[key];
      return (va > vb ? 1 : -1) * dir;
    });
  }, [centers, sort]);

  const totals = centers.reduce(
    (t, c) => ({
      farms: t.farms + c.farms,
      received: t.received + c.received,
      verified: t.verified + c.verified,
      forwarded: t.forwarded + c.forwarded,
      overdue: t.overdue + c.overdue,
      revenue: t.revenue + c.revenue,
      open: t.open + c.req.open,
      done: t.done + c.req.done,
    }),
    { farms: 0, received: 0, verified: 0, forwarded: 0, overdue: 0, revenue: 0, open: 0, done: 0 }
  );

  const sel = selected ? centers.find((c) => c.id === selected) : null;
  const selFarms = sel ? allFarms.filter((f) => f.centerId === sel.id).slice(0, 8) : [];

  const th = (label, key) => (
    <th onClick={() => setSort(([k, d]) => [key, k === key ? -d : -1])}>
      {label} {sort[0] === key ? (sort[1] > 0 ? "↑" : "↓") : ""}
    </th>
  );

  return (
    <div>
      <TopNav />
      <main style={{ padding: 20, maxWidth: 1280, margin: "0 auto", display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-bright)" }}>Organisation Overview</h1>
          <span className="badge badge-green">Cycle {CYCLE.number} · Day {CYCLE.day} of {CYCLE.length}</span>
          <span className="badge badge-neutral">Read-only oversight</span>
          <span style={{ marginLeft: "auto", fontSize: 12.5, color: "var(--text-muted)" }}>All service centers · Friday, 17 July 2026</span>
        </div>

        <div style={{ display: "flex", gap: 14 }}>
          <div className="card" style={{ flex: 1 }}>
            <div className="card-title">Centers & farms</div>
            <div className="kpi-value">{CENTERS.length} <span style={{ fontSize: 14, color: "var(--text-muted)" }}>centers</span></div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 6 }}>{totals.farms} farms · {centers.reduce((s, c) => s + c.acres, 0).toLocaleString()} total acres</div>
          </div>
          <div className="card" style={{ flex: 1 }}>
            <div className="card-title">Advisories this cycle</div>
            <div className="kpi-value">{totals.received}</div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 6 }}>
              {totals.verified} verified · {totals.forwarded} forwarded · <span style={{ color: "var(--danger)" }}>{totals.overdue} overdue</span>
            </div>
          </div>
          <div className="card" style={{ flex: 1 }}>
            <div className="card-title">Implement earnings (month)</div>
            <div className="kpi-value" style={{ color: "var(--gold-light)" }}>{fmtRs(totals.revenue)}</div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 6 }}>completed service requests, all centers</div>
          </div>
          <div className="card" style={{ flex: 1 }}>
            <div className="card-title">Service requests</div>
            <div className="kpi-value">{totals.open} <span style={{ fontSize: 14, color: "var(--warning)" }}>open</span></div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 6 }}>{totals.done} completed · avg turnaround 3.4 days</div>
          </div>
        </div>

        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="tbl">
            <thead>
              <tr>
                <th>Service center</th>
                {th("Farms", "farms")}
                {th("Advisories", "received")}
                {th("Verify rate", "verifyRate")}
                {th("False +", "fpRate")}
                {th("Overdue", "overdue")}
                {th("Requests open", "req")}
                {th("Impl. earnings", "revenue")}
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((c) => (
                <tr key={c.id} style={selected === c.id ? { background: "var(--surface-5)" } : undefined}>
                  <td>
                    <div style={{ fontWeight: 600, color: "var(--text-bright)" }}>{c.name}</div>
                    <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{c.manager}</div>
                  </td>
                  <td>{c.farms}</td>
                  <td>{c.received} <span style={{ color: "var(--text-muted)", fontSize: 11 }}>({c.forwarded} fwd)</span></td>
                  <td>
                    <span className={`badge ${c.verifyRate >= 60 ? "badge-green" : c.verifyRate >= 40 ? "badge-amber" : "badge-red"}`}>{c.verifyRate}%</span>
                  </td>
                  <td>
                    <span className={`badge ${c.fpRate <= 20 ? "badge-green" : c.fpRate <= 28 ? "badge-amber" : "badge-red"}`}>{c.fpRate}%</span>
                  </td>
                  <td style={{ color: c.overdue > 2 ? "var(--danger)" : "var(--text-primary)", fontWeight: c.overdue > 2 ? 700 : 400 }}>{c.overdue}</td>
                  <td>{c.req.open} <span style={{ color: "var(--text-muted)", fontSize: 11 }}>· {c.req.done} done</span></td>
                  <td style={{ color: "var(--gold-light)", fontWeight: 600 }}>{fmtRs(c.revenue)}</td>
                  <td><button className="btn btn-sm" onClick={() => setSelected(selected === c.id ? null : c.id)}>{selected === c.id ? "Hide" : "Drill down"}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {sel && (
          <div className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <div className="card-title" style={{ marginBottom: 0 }}>{sel.name} — farm drill-down (top farms by area)</div>
              <span style={{ fontSize: 11.5, color: "var(--text-muted)" }}>{sel.region} · manager {sel.manager}</span>
            </div>
            <table className="tbl">
              <thead><tr><th>Farmer</th><th>Village</th><th>Acres</th><th>Crop</th><th>Condition</th></tr></thead>
              <tbody>
                {selFarms.sort((a, b) => b.acres - a.acres).map((f) => (
                  <tr key={f.id}>
                    <td style={{ fontWeight: 600 }}>{f.farmer}</td>
                    <td style={{ color: "var(--text-secondary)" }}>{f.village}</td>
                    <td>{f.acres}</td>
                    <td>{f.crop}</td>
                    <td>{f.condition}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
          <div className="card">
            <div className="card-title">False-positive rate per cycle — is Agrobot learning?</div>
            <ResponsiveContainer width="100%" height={170}>
              <LineChart data={fpTrend}>
                <XAxis dataKey="cycle" stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} width={30} unit="%" />
                <Tooltip contentStyle={tooltipStyle} formatter={(v) => v + "%"} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="org" name="Org-wide" stroke="#e24b4a" strokeWidth={2.5} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="best" name="Best center" stroke="#4caf50" strokeWidth={2.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="card">
            <div className="card-title">Implement earnings per center — 6 months (Rs.)</div>
            <ResponsiveContainer width="100%" height={170}>
              <LineChart data={implByCenter}>
                <XAxis dataKey="month" stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} width={40} tickFormatter={(v) => v / 1000 + "k"} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v) => fmtRs(v)} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="Layyah" stroke="#d4a843" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="Sheikhupura" stroke="#60a5fa" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="Muridke" stroke="#2dd4bf" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="card">
            <div className="card-title">Avg request turnaround by service (days)</div>
            <ResponsiveContainer width="100%" height={170}>
              <BarChart data={turnaround} layout="vertical" barSize={14}>
                <XAxis type="number" stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="type" stroke="var(--text-muted)" fontSize={10.5} tickLine={false} axisLine={false} width={92} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v) => v + " days"} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                <Bar dataKey="days" fill="#60a5fa" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </main>
    </div>
  );
}
