"use client";
// The morning dashboard — DRD §5. KPI tiles, farm map with switchable views
// (farm-level / weather / general) + a matching side panel, trend charts.
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import TopNav from "@/components/TopNav";
import { AdvisoryBadge, SeverityBadge, ConditionBadge } from "@/components/badges";
import { useFams } from "@/lib/store";

// Static mock data for charts (since DB is only seeded with 1 cycle)
const CYCLE = { number: 42, day: 4, length: 5 };
const earningsTrend = [
  { month: "Feb", implements: 45000 },
  { month: "Mar", implements: 52000 },
  { month: "Apr", implements: 61000 },
  { month: "May", implements: 58000 },
  { month: "Jun", implements: 76000 },
  { month: "Jul", implements: 81000 },
];
const cycleBars = [
  { day: 1, farm: 12, general: 2, weather: 0 },
  { day: 2, farm: 18, general: 1, weather: 4 },
  { day: 3, farm: 14, general: 0, weather: 2 },
  { day: 4, farm: 11, general: 1, weather: 0 },
  { day: 5, farm: 0, general: 0, weather: 0 },
];

function fmtRs(val) { return `Rs. ${val?.toLocaleString()}`; }
function farmWeather(f) { return { key: "clear", label: "Clear", icon: "/weather-icons/clear-day.svg", advisory: "Optimal conditions for spraying." }; }
function farmStatus(f, adv) { return adv ? (adv.severity === "high" ? "critical" : "warning") : "healthy"; }
const STATUS_COLORS = { healthy: "#4caf50", warning: "#f59e0b", critical: "#e24b4a", unknown: "#9ca3af" };

const farmById = {}; // We will build this dynamically in the component


const FarmMap = dynamic(() => import("@/components/FarmMap"), { ssr: false });

const tooltipStyle = {
  background: "var(--surface-5)", border: "1px solid var(--border-default)",
  borderRadius: 8, fontSize: 12, color: "var(--text-primary)",
};

function Tile({ title, value, sub, accent, onClick, icon, iconColor = "var(--text-accent)", iconBg = "var(--accent-muted)" }) {
  return (
    <div className="card" style={{ cursor: "pointer", flex: 1, position: "relative" }} onClick={onClick}>
      <div style={{
        position: "absolute", top: 14, right: 14, width: 40, height: 40, borderRadius: 10,
        background: iconBg, color: iconColor, display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        {icon}
      </div>
      <div className="card-title" style={{ paddingRight: 52 }}>{title}</div>
      <div className="kpi-value" style={accent ? { color: accent } : undefined}>{value}</div>
      <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 6, lineHeight: 1.5 }}>{sub}</div>
    </div>
  );
}

const ICONS = {
  farms: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22V12" /><path d="M12 12c0-3-2.5-5-5.5-5C6.5 10 9 12 12 12z" /><path d="M12 12c0-3 2.5-5 5.5-5C17.5 10 15 12 12 12z" /><path d="M12 7c0-2.5-1.5-4-3.5-5C8.5 4.5 10 6.5 12 7z" /><path d="M12 7c0-2.5 1.5-4 3.5-5C15.5 4.5 14 6.5 12 7z" /><path d="M5 22h14" />
    </svg>
  ),
  advisories: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="5" y="4" width="14" height="17" rx="2" /><path d="M9 4a3 3 0 0 1 6 0" /><path d="M9 10h6M9 14h6M9 18h3" />
    </svg>
  ),
  verify: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2l8 3v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5z" /><path d="M8.5 12l2.5 2.5 4.5-5" />
    </svg>
  ),
  tractor: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="7" cy="17" r="4" /><circle cx="18" cy="18" r="2.5" /><path d="M11 15h4.5" /><path d="M4 13V8h7l2 5" /><path d="M13 8h3l2 5.5" /><path d="M7 8V5h4" />
    </svg>
  ),
};

export default function Dashboard() {
  const { advisories, requests, farms, broadcasts } = useFams();
  const router = useRouter();

  // Dynamically build farmById
  const farmById = useMemo(() => {
    const map = {};
    farms.forEach((f) => { map[f.id] = f; });
    return map;
  }, [farms]);

  const farmAdvToday = advisories.length;
  const toVerify = advisories.filter((a) => a.state === "received" || a.state === "pending_verification").length;
  const pending = advisories.filter((a) => a.state !== "closed").length;
  const verified = advisories.filter((a) => a.verification).length;
  const forwarded = advisories.filter((a) => a.forwarding).length;
  const falsePos = advisories.filter((a) => a.verification?.outcome === "not_found").length;
  const totalAcres = Math.round(farms.reduce((s, f) => s + f.acres, 0));

  const openReqs = requests.filter((r) => ["pending", "scheduled", "in_progress"].includes(r.state));
  const doneReqs = requests.filter((r) => r.state === "completed");
  const earned = doneReqs.reduce((s, r) => s + r.total, 0);
  const pipeline = openReqs.reduce((s, r) => s + r.total, 0);

  // ---- map views: farm-level advisory / weather / general ----
  const [view, setView] = useState("farm");
  const [selFarmId, setSelFarmId] = useState(null);
  const [fq, setFq] = useState("");
  const [wq, setWq] = useState("");
  const [wSort, setWSort] = useState(["name", 1]);
  const [wFilter, setWFilter] = useState("all");

  const pinFarms = useMemo(() => {
    if (view === "weather")
      return farms.map((f) => {
        const w = farmWeather(f);
        return { ...f, pinIcon: w.icon, tipSub: w.label };
      });
    if (view === "general")
      return farms.map((f) => ({ ...f, pinColor: "#2dd4bf", tipSub: `${broadcasts.length} general advisories today` }));
    return farms.map((f) => {
      const adv = advisories.find((a) => a.farmId === f.id && a.state !== "closed");
      return { ...f, pinColor: STATUS_COLORS[farmStatus(f, adv)] };
    });
  }, [view, advisories, farms, broadcasts]);

  const queue = useMemo(() => {
    const items = [
      ...advisories
        .filter((a) => a.state === "received" || a.state === "pending_verification")
        .map((a) => ({
          id: `adv-${a.id}`, color: "var(--warning)",
          farmer: farmById[a.farmId]?.farmer || "Unknown Farmer",
          sub: `Verify: ${a.issueType} · due day 4 of cycle`,
          to: `/advisories/${a.farmId}`,
        })),
      ...openReqs.map((r) => ({
        id: `req-${r.id}`, color: "var(--info)",
        farmer: r.farmer,
        sub: `${r.service} · ${r.petrol != null ? fmtRs(r.total) : fmtRs(r.basePrice) + " + petrol"}`,
        to: "/services",
      })),
    ];
    if (!fq) return items;
    const s = fq.toLowerCase();
    return items.filter((i) => i.farmer.toLowerCase().includes(s));
  }, [advisories, requests, fq, farmById, openReqs]);

  const weatherRows = useMemo(() => {
    let list = farms.map((f) => ({ farm: f, w: farmWeather(f) }));
    if (wq) {
      const s = wq.toLowerCase();
      list = list.filter((r) => r.farm.farmer.toLowerCase().includes(s) || r.farm.village.toLowerCase().includes(s));
    }
    if (wFilter !== "all") list = list.filter((r) => r.w.key === wFilter);
    const [key, dir] = wSort;
    list.sort((a, b) => {
      const va = key === "area" ? a.farm.acres : key === "weather" ? a.w.label : a.farm.farmer;
      const vb = key === "area" ? b.farm.acres : key === "weather" ? b.w.label : b.farm.farmer;
      return (va > vb ? 1 : va < vb ? -1 : 0) * dir;
    });
    return list;
  }, [wq, wSort, wFilter]);

  const VIEWS = [
    { id: "farm", label: "Farm-level", icon: <span style={{ display: "inline-flex", gap: 2 }}><span style={{ width: 7, height: 7, borderRadius: 99, background: "#e24b4a" }} /><span style={{ width: 7, height: 7, borderRadius: 99, background: "#f59e0b" }} /><span style={{ width: 7, height: 7, borderRadius: 99, background: "#4caf50" }} /></span> },
    { id: "weather", label: "Weather", icon: <img src="/weather-icons/clear-day.svg" alt="" width={16} height={16} /> },
    { id: "general", label: "General", icon: <span style={{ width: 8, height: 8, borderRadius: 99, background: "#2dd4bf", display: "inline-block" }} /> },
  ];

  return (
    <div>
      <TopNav />
      <main style={{ padding: 20, maxWidth: 1280, margin: "0 auto", display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-bright)" }}>Good morning, Ayesha</h1>
          <span className="badge badge-green">Cycle {CYCLE.number} · Day {CYCLE.day} of {CYCLE.length}</span>
          <span style={{ marginLeft: "auto", fontSize: 12.5, color: "var(--text-muted)" }}>Friday, 17 July 2026</span>
        </div>

        <div style={{ display: "flex", gap: 14 }}>
          <Tile
            title="Farms"
            value={farms.length}
            icon={ICONS.farms}
            sub={<>Layyah Center · {totalAcres.toLocaleString()} acres under monitoring</>}
            onClick={() => router.push("/advisories")}
          />
          <Tile
            title="Today's advisories"
            value={farmAdvToday + broadcasts.length}
            icon={ICONS.advisories}
            iconColor="var(--warning)"
            iconBg="var(--warning-muted)"
            sub={<>{farmAdvToday} farm-level · {broadcasts.length} general · <span style={{ color: "var(--warning)" }}>{toVerify} to verify</span> · <span style={{ color: "var(--danger)" }}>{pending} pending</span></>}
            onClick={() => router.push("/advisories")}
          />
          <Tile
            title="Verification progress"
            value={<>{verified}<span style={{ fontSize: 13, color: "var(--text-muted)", fontWeight: 500 }}> / {farmAdvToday} verified</span></>}
            icon={ICONS.verify}
            iconColor="#2dd4bf"
            iconBg="rgba(45,212,191,0.14)"
            sub={<><span style={{ color: "var(--success)" }}>{forwarded} forwarded</span> · {falsePos} false positive{falsePos === 1 ? "" : "s"} · feedback returned to Agrobot</>}
            onClick={() => router.push("/advisories")}
          />
          <Tile
            title="Implement requests"
            value={<>{openReqs.length}<span style={{ fontSize: 13, color: "var(--warning)", fontWeight: 600 }}> open</span></>}
            icon={ICONS.tractor}
            iconColor="var(--gold-light)"
            iconBg="var(--gold-muted)"
            sub={<>{doneReqs.length} completed · <span style={{ color: "var(--gold-light)" }}>{fmtRs(earned)} earned</span> · {fmtRs(pipeline)} pipeline</>}
            onClick={() => router.push("/services")}
          />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1.9fr 1fr", gap: 14 }}>
          <div className="card" style={{ height: 400, overflow: "hidden" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10, flexWrap: "nowrap", overflow: "hidden", height: 28 }}>
              <div className="card-title" style={{ marginBottom: 0, flexShrink: 0 }}>Farm map — {farms.length} farms</div>
              <div style={{ display: "flex", gap: 6, marginLeft: 6 }}>
                {VIEWS.map((v) => (
                  <button
                    key={v.id}
                    className="btn btn-sm"
                    style={view === v.id ? { background: "var(--accent-muted)", borderColor: "var(--accent-border)", color: "var(--text-accent)" } : undefined}
                    onClick={() => setView(v.id)}
                  >
                    {v.icon} {v.label}
                  </button>
                ))}
              </div>
              <div style={{ fontSize: 11.5, color: "var(--text-muted)", display: "flex", gap: 12, marginLeft: "auto", flexShrink: 1, overflow: "hidden", whiteSpace: "nowrap" }}>
                {view === "farm" && (
                  <>
                    <span><span style={{ color: "#e24b4a" }}>●</span> problem</span>
                    <span><span style={{ color: "#f59e0b" }}>●</span> moderate</span>
                    <span><span style={{ color: "#4caf50" }}>●</span> healthy</span>
                  </>
                )}
                {view === "weather" && <span>hover a farm for its weather advisory</span>}
                {view === "general" && <span><span style={{ color: "#2dd4bf" }}>●</span> broadcast reaches every farm</span>}
              </div>
            </div>
            <FarmMap key={view} farms={pinFarms} mode="pins" height={330} onSelect={(id) => setSelFarmId(id)} />
          </div>

          <div className="card" style={{ display: "flex", flexDirection: "column", height: 400, overflow: "hidden" }}>
            {selFarmId && (() => {
              const f = farmById[selFarmId];
              const adv = advisories.find((a) => a.farmId === f.id) || null;
              const w = farmWeather(f);
              return (
                <>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                    <div style={{ fontSize: 14.5, fontWeight: 700, color: "var(--text-bright)", flex: 1, minWidth: 0, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {f.farmer}&apos;s Farm
                    </div>
                    <ConditionBadge condition={f.condition} />
                    <button className="btn btn-sm" aria-label="Close" onClick={() => setSelFarmId(null)}>✕</button>
                  </div>
                  <div style={{ overflowY: "auto", flex: 1, minHeight: 0 }}>
                    <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginBottom: 8 }}>
                      {f.village} · {f.phone || "no phone"}
                    </div>
                    <div className="kv"><span className="k">Crop</span><span className="v">{f.crop} {f.variety ? `(${f.variety})` : ""}</span></div>
                    <div className="kv"><span className="k">Area</span><span className="v">{f.acres} acres</span></div>
                    <div className="kv"><span className="k">Irrigation</span><span className="v">{f.irrigation.join(", ")}</span></div>
                    <div className="kv"><span className="k">Sown</span><span className="v">{f.sowDate || "—"}</span></div>
                    <div className="kv"><span className="k">Expected harvest</span><span className="v">{f.harvestDate || "—"}</span></div>
                    <div className="kv"><span className="k">Expected yield</span><span className="v">{f.yieldExpected ?? "—"} mounds</span></div>
                    <div style={{ background: "var(--surface-3)", borderRadius: 8, padding: "8px 10px", margin: "10px 0" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                        <span style={{ fontSize: 10.5, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Latest advisory</span>
                        {adv && <SeverityBadge severity={adv.severity} />}
                        {adv ? <AdvisoryBadge adv={adv} /> : <span className="badge badge-green">None</span>}
                      </div>
                      {adv ? (
                        <div style={{ fontSize: 11.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                          <b style={{ color: "var(--text-primary)" }}>{adv.issueType}:</b> {adv.text}
                        </div>
                      ) : (
                        <div style={{ fontSize: 11.5, color: "var(--text-secondary)" }}>No advisory for this farm in the current cycle.</div>
                      )}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, background: "var(--surface-3)", borderRadius: 8, padding: "7px 10px" }}>
                      <img src={w.icon} alt={w.label} width={24} height={24} />
                      <div style={{ fontSize: 11.5, color: "var(--text-secondary)", lineHeight: 1.4 }}>{w.advisory}</div>
                    </div>
                  </div>
                  <button className="btn btn-primary" style={{ marginTop: 10 }} onClick={() => router.push(`/advisories/${f.id}`)}>
                    View full details →
                  </button>
                </>
              );
            })()}

            {!selFarmId && view === "farm" && (
              <>
                <div className="card-title">Action queue — {queue.length} items</div>
                <input
                  className="input"
                  style={{ padding: "5px 10px", fontSize: 12, marginBottom: 8 }}
                  placeholder="Search farmer…"
                  value={fq}
                  onChange={(e) => setFq(e.target.value)}
                />
                <div style={{ overflowY: "auto", flex: 1, minHeight: 0, display: "flex", flexDirection: "column", gap: 8 }}>
                  {queue.map((q) => (
                    <div
                      key={q.id}
                      onClick={() => router.push(q.to)}
                      style={{
                        borderLeft: `3px solid ${q.color}`, background: "var(--surface-3)",
                        padding: "8px 12px", borderRadius: "0 8px 8px 0", cursor: "pointer",
                      }}
                    >
                      <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{q.farmer}</div>
                      <div style={{ fontSize: 11.5, color: "var(--text-muted)" }}>{q.sub}</div>
                    </div>
                  ))}
                  {queue.length === 0 && (
                    <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
                      {fq ? "No queue items match that farmer." : "All clear — nothing waiting on you."}
                    </div>
                  )}
                </div>
              </>
            )}

            {!selFarmId && view === "weather" && (
              <>
                <div className="card-title">Weather advisories — {weatherRows.length} farms</div>
                <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
                  <input className="input" style={{ flex: 1, padding: "5px 10px", fontSize: 12 }} placeholder="Search farm…" value={wq} onChange={(e) => setWq(e.target.value)} />
                  <select className="input" style={{ padding: "5px 8px", fontSize: 12 }} value={wFilter} onChange={(e) => setWFilter(e.target.value)}>
                    <option value="all">All weather</option>
                    {[...new Set(farms.map((f) => farmWeather(f).key))].map((k) => {
                      const w = farms.map(farmWeather).find((x) => x.key === k);
                      return <option key={k} value={k}>{w.label}</option>;
                    })}
                  </select>
                </div>
                <div style={{ display: "flex", gap: 6, marginBottom: 6, alignItems: "center" }}>
                  <span style={{ fontSize: 10.5, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Sort</span>
                  {[
                    ["name", "Sort by farmer name", <svg key="i" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 4-6 8-6s8 2 8 6" /></svg>],
                    ["area", "Sort by area (acres)", <svg key="i" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="4" width="16" height="16" rx="1" /><path d="M4 10h16M10 4v16" /></svg>],
                    ["weather", "Sort by weather", <svg key="i" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.5 18a4.5 4.5 0 0 0 0-9 6 6 0 0 0-11.3 2A4 4 0 0 0 7 18z" /></svg>],
                  ].map(([k, title, icon]) => (
                    <button
                      key={k}
                      className="btn btn-sm"
                      title={title}
                      aria-label={title}
                      style={{
                        padding: "4px 8px",
                        ...(wSort[0] === k ? { background: "var(--accent-muted)", borderColor: "var(--accent-border)", color: "var(--text-accent)" } : {}),
                      }}
                      onClick={() => setWSort(([ck, d]) => [k, ck === k ? -d : 1])}
                    >
                      {icon}
                      {wSort[0] === k && (
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ transform: wSort[1] > 0 ? "none" : "rotate(180deg)" }}>
                          <path d="M12 19V5M5 12l7-7 7 7" />
                        </svg>
                      )}
                    </button>
                  ))}
                </div>
                <div style={{ overflowY: "auto", flex: 1, minHeight: 0, display: "flex", flexDirection: "column", gap: 6 }}>
                  {weatherRows.map(({ farm: f, w }) => (
                    <div key={f.id} style={{ display: "flex", alignItems: "center", gap: 8, background: "var(--surface-3)", borderRadius: 8, padding: "7px 10px" }}>
                      <img src={w.icon} alt={w.label} width={26} height={26} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)" }}>
                          {f.farmer} <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>· {f.acres} ac</span>
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{f.phone || "no phone"}</div>
                        <div style={{ fontSize: 11.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>{w.advisory}</div>
                      </div>
                      <button className="btn btn-sm" style={{ flexShrink: 0 }} onClick={() => router.push(`/advisories/${f.id}`)}>Details</button>
                    </div>
                  ))}
                  {weatherRows.length === 0 && <div style={{ fontSize: 12.5, color: "var(--text-muted)" }}>No farms match.</div>}
                </div>
              </>
            )}

            {!selFarmId && view === "general" && (
              <>
                <div className="card-title">General advisories today — {broadcasts.length}</div>
                <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginBottom: 8 }}>
                  Broadcast to all {farms.length} farms via the Farmer App — no verification needed.
                </div>
                <div style={{ overflowY: "auto", flex: 1, minHeight: 0, display: "flex", flexDirection: "column", gap: 8 }}>
                  {broadcasts.map((g) => (
                    <div key={g.id} style={{ borderLeft: "3px solid #2dd4bf", background: "var(--surface-3)", padding: "8px 12px", borderRadius: "0 8px 8px 0" }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: "#2dd4bf" }}>{g.title}</div>
                      <div style={{ fontSize: 11.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>{g.text}</div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <div className="card">
            <div className="card-title">Advisories this cycle — farm-level · general · weather</div>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={cycleBars} barSize={26}>
                <XAxis dataKey="day" stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} width={24} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="farm" name="Farm-level" stackId="a" fill="#4caf50" radius={[0, 0, 0, 0]} />
                <Bar dataKey="general" name="General" stackId="a" fill="#2dd4bf" radius={[0, 0, 0, 0]} />
                <Bar dataKey="weather" name="Weather" stackId="a" fill="#60a5fa" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="card">
            <div className="card-title">Implement earnings — last 6 months (Rs.)</div>
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={earningsTrend}>
                <XAxis dataKey="month" stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} width={44} tickFormatter={(v) => (v / 1000) + "k"} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v) => fmtRs(v)} />
                <Line type="monotone" dataKey="implements" name="Implement earnings" stroke="#60a5fa" strokeWidth={2.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </main>
    </div>
  );
}
