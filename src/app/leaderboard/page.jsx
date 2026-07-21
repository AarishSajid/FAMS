"use client";
// Leader Board — farmer performance comparison at three levels:
// Farmers (ranked table + podium), Villages (aggregate), Crops (head-to-head).
// Score blends yield efficiency, crop condition, satellite health, and
// advisory response — derived from the survey registry with deterministic fill.
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, Legend,
} from "recharts";
import TopNav from "@/components/TopNav";
import { farms, indexSeries, fmtRs } from "@/lib/data";

const tooltipStyle = {
  background: "var(--surface-5)", border: "1px solid var(--border-default)",
  borderRadius: 8, fontSize: 12, color: "var(--text-primary)",
};

// ---- scoring ----
function farmScore(f) {
  // yield efficiency: actual/expected mounds (deterministic fill when missing)
  const exp = f.yieldExpected ?? 30 + (f.sNo % 5) * 5;
  const act = f.yieldActual ?? Math.round(exp * (0.75 + ((f.sNo * 13) % 40) / 100));
  const yieldEff = Math.min(1.25, act / Math.max(1, exp));
  // satellite health: mean NDVI actual vs reference across stages
  const s = indexSeries(f, "NDVI");
  const ndvi = s.reduce((t, d) => t + d.actual, 0) / s.length;
  const ndviRef = s.reduce((t, d) => t + d.reference, 0) / s.length;
  const health = Math.min(1.15, ndvi / ndviRef);
  const condition = f.condition === "Good" ? 1 : f.condition === "Average" ? 0.7 : 0.4;
  // advisory response: how quickly this farmer acts on advisories (synthetic)
  const response = 0.6 + ((f.sNo * 7) % 40) / 100;
  const score = Math.round((yieldEff * 0.4 + health * 0.25 + condition * 0.2 + response * 0.15) * 100);
  return {
    score,
    yieldEff: Math.round(yieldEff * 100),
    ndvi: +ndvi.toFixed(2),
    response: Math.round(response * 100),
    expYield: exp,
    actYield: act,
    yieldPerAcre: +(act / Math.max(1, f.acres)).toFixed(1),
  };
}

const RANK_STYLE = [
  { bg: "var(--gold-muted)", border: "var(--gold-border)", color: "var(--gold-light)", label: "1st" },
  { bg: "rgba(203,213,225,0.12)", border: "rgba(203,213,225,0.35)", color: "#cbd5e1", label: "2nd" },
  { bg: "rgba(217,119,6,0.14)", border: "rgba(217,119,6,0.4)", color: "#e8965a", label: "3rd" },
];

export default function Leaderboard() {
  const router = useRouter();
  const [level, setLevel] = useState("farmers"); // farmers | villages | crops
  const [cropFilter, setCropFilter] = useState("all");
  const [q, setQ] = useState("");

  const scored = useMemo(
    () => farms.map((f) => ({ farm: f, ...farmScore(f) })).sort((a, b) => b.score - a.score),
    []
  );

  const rows = useMemo(() => {
    let list = scored;
    if (cropFilter !== "all") list = list.filter((r) => r.farm.crop === cropFilter);
    if (q) {
      const s = q.toLowerCase();
      list = list.filter((r) => r.farm.farmer.toLowerCase().includes(s) || r.farm.village.toLowerCase().includes(s));
    }
    return list;
  }, [scored, cropFilter, q]);

  const villages = useMemo(() => {
    const map = {};
    for (const r of scored) {
      const v = r.farm.village || "Unknown";
      (map[v] ||= []).push(r);
    }
    return Object.entries(map)
      .map(([name, list]) => ({
        name,
        farms: list.length,
        acres: Math.round(list.reduce((s, r) => s + r.farm.acres, 0)),
        avgScore: Math.round(list.reduce((s, r) => s + r.score, 0) / list.length),
        avgYieldEff: Math.round(list.reduce((s, r) => s + r.yieldEff, 0) / list.length),
        best: list[0],
      }))
      .filter((v) => v.farms >= 2)
      .sort((a, b) => b.avgScore - a.avgScore);
  }, [scored]);

  const crops = useMemo(() => {
    const map = {};
    for (const r of scored) (map[r.farm.crop] ||= []).push(r);
    return Object.entries(map).map(([name, list]) => ({
      name,
      farms: list.length,
      acres: Math.round(list.reduce((s, r) => s + r.farm.acres, 0)),
      avgScore: Math.round(list.reduce((s, r) => s + r.score, 0) / list.length),
      avgYieldEff: Math.round(list.reduce((s, r) => s + r.yieldEff, 0) / list.length),
      avgNdvi: +(list.reduce((s, r) => s + r.ndvi, 0) / list.length).toFixed(2),
      yieldPerAcre: +(list.reduce((s, r) => s + r.yieldPerAcre, 0) / list.length).toFixed(1),
      best: list[0],
    })).sort((a, b) => b.avgScore - a.avgScore);
  }, [scored]);

  const podium = rows.slice(0, 3);
  const cropOptions = [...new Set(farms.map((f) => f.crop))];

  return (
    <div>
      <TopNav />
      <main style={{ padding: 20, maxWidth: 1280, margin: "0 auto", display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-bright)" }}>Leader Board</h1>
          <span style={{ fontSize: 12.5, color: "var(--text-muted)" }}>
            performance score = 40% yield efficiency · 25% satellite health · 20% crop condition · 15% advisory response
          </span>
          <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            {[["farmers", "Farmers"], ["villages", "Villages"], ["crops", "Crops"]].map(([id, label]) => (
              <button
                key={id}
                className="btn btn-sm"
                style={level === id ? { background: "var(--accent-muted)", borderColor: "var(--accent-border)", color: "var(--text-accent)" } : undefined}
                onClick={() => setLevel(id)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {level === "farmers" && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
              {podium.map((r, i) => (
                <div key={r.farm.id} className="card" style={{ borderColor: RANK_STYLE[i].border, background: "var(--surface-4)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span className="badge" style={{ background: RANK_STYLE[i].bg, border: `1px solid ${RANK_STYLE[i].border}`, color: RANK_STYLE[i].color, fontSize: 13 }}>
                      {RANK_STYLE[i].label}
                    </span>
                    <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-bright)" }}>{r.farm.farmer}</div>
                    <span style={{ marginLeft: "auto", fontSize: 24, fontWeight: 700, color: RANK_STYLE[i].color }}>{r.score}</span>
                  </div>
                  <div style={{ fontSize: 11.5, color: "var(--text-muted)", margin: "4px 0 8px" }}>
                    {r.farm.village} · {r.farm.crop} · {r.farm.acres} acres
                  </div>
                  <div style={{ display: "flex", gap: 12, fontSize: 11.5, color: "var(--text-secondary)" }}>
                    <span>Yield {r.yieldEff}%</span>
                    <span>NDVI {r.ndvi}</span>
                    <span>Response {r.response}%</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
              <div style={{ display: "flex", gap: 10, padding: "12px 12px 0" }}>
                <input className="input" style={{ width: 240 }} placeholder="Search farmer or village…" value={q} onChange={(e) => setQ(e.target.value)} />
                <select className="input" value={cropFilter} onChange={(e) => setCropFilter(e.target.value)}>
                  <option value="all">All crops</option>
                  {cropOptions.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--text-muted)", alignSelf: "center", paddingRight: 12 }}>{rows.length} farmers</span>
              </div>
              <div style={{ maxHeight: 420, overflowY: "auto", marginTop: 10 }}>
                <table className="tbl">
                  <thead>
                    <tr>
                      <th style={{ width: 60 }}>Rank</th><th>Farmer</th><th>Village</th><th>Crop</th><th>Acres</th>
                      <th>Yield eff.</th><th>Yield / acre</th><th>NDVI</th><th>Response</th><th>Score</th><th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r, i) => (
                      <tr key={r.farm.id}>
                        <td style={{ fontWeight: 700, color: i < 3 ? RANK_STYLE[i]?.color : "var(--text-secondary)" }}>#{i + 1}</td>
                        <td style={{ fontWeight: 600, color: "var(--text-bright)" }}>{r.farm.farmer}</td>
                        <td style={{ color: "var(--text-secondary)" }}>{r.farm.village}</td>
                        <td>{r.farm.crop}</td>
                        <td>{r.farm.acres}</td>
                        <td>
                          <span className={`badge ${r.yieldEff >= 95 ? "badge-green" : r.yieldEff >= 80 ? "badge-amber" : "badge-red"}`}>{r.yieldEff}%</span>
                        </td>
                        <td>{r.yieldPerAcre} md</td>
                        <td>{r.ndvi}</td>
                        <td>{r.response}%</td>
                        <td style={{ fontWeight: 700, color: "var(--text-bright)" }}>{r.score}</td>
                        <td><button className="btn btn-sm" onClick={() => router.push(`/advisories/${r.farm.id}`)}>View</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {level === "villages" && (
          <>
            <div className="card">
              <div className="card-title">Average performance score by village (2+ farms)</div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={villages} barSize={26}>
                  <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={10} tickLine={false} axisLine={false} interval={0} angle={-30} height={60} textAnchor="end" />
                  <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} width={30} domain={[0, 110]} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                  <Bar dataKey="avgScore" name="Avg score" radius={[4, 4, 0, 0]}>
                    {villages.map((v, i) => <Cell key={v.name} fill={i === 0 ? "#d4a843" : "#4caf50"} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
              <table className="tbl">
                <thead>
                  <tr><th style={{ width: 60 }}>Rank</th><th>Village</th><th>Farms</th><th>Acres</th><th>Avg yield eff.</th><th>Avg score</th><th>Top farmer</th></tr>
                </thead>
                <tbody>
                  {villages.map((v, i) => (
                    <tr key={v.name}>
                      <td style={{ fontWeight: 700, color: i < 3 ? RANK_STYLE[i]?.color : "var(--text-secondary)" }}>#{i + 1}</td>
                      <td style={{ fontWeight: 600, color: "var(--text-bright)" }}>{v.name}</td>
                      <td>{v.farms}</td>
                      <td>{v.acres}</td>
                      <td>{v.avgYieldEff}%</td>
                      <td style={{ fontWeight: 700, color: "var(--text-bright)" }}>{v.avgScore}</td>
                      <td style={{ color: "var(--text-secondary)" }}>{v.best.farm.farmer} ({v.best.score})</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {level === "crops" && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.max(2, crops.length)}, 1fr)`, gap: 14 }}>
              {crops.map((c, i) => (
                <div key={c.name} className="card" style={i === 0 ? { borderColor: "var(--gold-border)" } : undefined}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-bright)" }}>{c.name}</div>
                    {i === 0 && <span className="badge badge-gold">Best performing</span>}
                    <span style={{ marginLeft: "auto", fontSize: 26, fontWeight: 700, color: i === 0 ? "var(--gold-light)" : "var(--text-bright)" }}>{c.avgScore}</span>
                  </div>
                  <div style={{ fontSize: 11.5, color: "var(--text-muted)", margin: "4px 0 10px" }}>{c.farms} farms · {c.acres} acres</div>
                  <div className="kv"><span className="k">Avg yield efficiency</span><span className="v">{c.avgYieldEff}%</span></div>
                  <div className="kv"><span className="k">Avg yield per acre</span><span className="v">{c.yieldPerAcre} mounds</span></div>
                  <div className="kv"><span className="k">Avg NDVI (season)</span><span className="v">{c.avgNdvi}</span></div>
                  <div className="kv"><span className="k">Top farmer</span><span className="v">{c.best.farm.farmer} ({c.best.score})</span></div>
                </div>
              ))}
            </div>
            <div className="card">
              <div className="card-title">Crop comparison — yield efficiency vs satellite health</div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={crops} barSize={30}>
                  <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} width={30} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="avgYieldEff" name="Yield efficiency %" fill="#4caf50" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="avgScore" name="Overall score" fill="#d4a843" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
