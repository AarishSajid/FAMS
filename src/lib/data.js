// FAMS_v2 mock domain data, derived deterministically from the real field-survey
// registry (farms.json, 120 surveyed fields — Sheikhupura & Layyah districts).
import rawFarms from "./farms.json";

export const TODAY = "2026-07-17";
export const CYCLE = { number: 42, day: 2, length: 5, start: "2026-07-16", end: "2026-07-20" };

export const CENTERS = [
  { id: "sc-1", name: "Layyah Center", region: "Punjab — Layyah", manager: "Ayesha Khan" },
  { id: "sc-2", name: "Sheikhupura Center", region: "Punjab — Sheikhupura", manager: "Bilal Chaudhry" },
  { id: "sc-3", name: "Muridke Center", region: "Punjab — Muridke", manager: "Sana Tariq" },
];

export const AGENTS = [
  { id: "ag-1", name: "Mustafa Kamal", phone: "0301-2234501", status: "Available" },
  { id: "ag-2", name: "Tariq Jamil", phone: "0300-1234567", status: "Busy" },
  { id: "ag-3", name: "Usman Khawaja", phone: "0333-5555555", status: "Available" },
  { id: "ag-4", name: "Kamran Akmal", phone: "0321-9876543", status: "Available" },
];

const ISSUE_DEFS = {
  "Pest Infestation": { index: "NDVI", color: "#e24b4a", label: "Pest risk detected" },
  "Water Stress": { index: "NDMI", color: "#ea580c", label: "Moisture stress" },
  "Low Vigour": { index: "NDVI", color: "#ca8a04", label: "Low crop vigour" },
  "Nitrogen Deficiency": { index: "NDRE", color: "#9333ea", label: "Nitrogen status low" },
  "Moisture Excess": { index: "NDWI", color: "#2563eb", label: "Excess surface water" },
};

export const INDICES = ["NDVI", "NDMI", "EVI", "MSAVI", "NDRE", "NDWI", "NBR"];

export const IMAGERY_DATES = [
  "2026-05-30", "2026-06-04", "2026-06-09", "2026-06-14", "2026-06-19",
  "2026-06-24", "2026-06-29", "2026-07-04", "2026-07-09", "2026-07-14",
];

// ---- farms enriched ----
// District from plot location: the survey covers two clusters —
// Layyah (~70.9°E) and Sheikhupura (~74.25°E).
export const allFarms = rawFarms.map((f) => {
  const district = f.lon && f.lon < 72.5 ? "Layyah" : "Sheikhupura";
  const centerId = district === "Layyah" ? "sc-1" : f.sNo % 2 === 0 ? "sc-2" : "sc-3";
  return { ...f, district, centerId };
});

// The manager's working set: Layyah Center only (keeps the demo readable).
export const farms = allFarms.filter((f) => f.district === "Layyah");

export const farmById = Object.fromEntries(allFarms.map((f) => [f.id, f]));

// ---- advisory generation ----
function issueFor(f) {
  if (f.disease.outbreak && (f.disease.severity ?? 0) >= 40) return "Pest Infestation";
  if (f.disease.issues && f.disease.outbreak) return "Pest Infestation";
  if (f.condition !== "Good") return "Low Vigour";
  if (f.irrigation.length === 1 && f.irrigation[0] === "Tubewell" && f.sNo % 3 === 0) return "Water Stress";
  if (f.crop === "Sugarcane" && f.sNo % 2 === 0) return "Nitrogen Deficiency";
  if (f.sNo % 7 === 0) return "Water Stress";
  return null;
}

function advisoryText(issue, f) {
  switch (issue) {
    case "Pest Infestation":
      return `Vegetation anomaly consistent with pest activity (${f.disease.issues || "jassid"}) detected in the ${f.sNo % 2 ? "north-east" : "south-west"} section of the ${f.crop.toLowerCase()} field. Recommend scouting and targeted spray within 3 days.`;
    case "Water Stress":
      return `Moderate moisture stress detected across ${Math.max(10, (f.sNo * 7) % 40)}% of the field on the NDMI layer. Irrigation recommended within 48 hours to avoid yield loss.`;
    case "Low Vigour":
      return `Crop vigour below reference for this stage in scattered patches. Verify establishment and consider a nitrogen top-dress if confirmed.`;
    case "Nitrogen Deficiency":
      return `NDRE indicates chlorophyll/nitrogen status below reference in the central strip. Recommend 1 bag urea per acre after field confirmation.`;
    default:
      return "Anomaly detected; field verification recommended.";
  }
}

const sevOf = (f) => ((f.disease.severity ?? 0) >= 50 ? "High" : f.sNo % 3 === 0 ? "Medium" : f.sNo % 2 === 0 ? "High" : "Low");

// Farms with an issue, ordered
const flagged = farms.filter((f) => issueFor(f));

// Today's farm-level advisories: first 9 flagged farms
const todaysFarms = flagged.slice(0, 9);

function mkTimeline(adv, f) {
  const ev = [{ at: `${TODAY}T06:10`, actor: "Agrobot", label: "Advisory received", detail: `Cycle ${CYCLE.number} · ${adv.indexLayer} analysis` }];
  if (adv.assignedAgentId) {
    const ag = AGENTS.find((a) => a.id === adv.assignedAgentId);
    ev.push({ at: `${TODAY}T08:3${f.sNo % 10}`, actor: "Ayesha Khan", label: `Field agent assigned — ${ag.name}` });
  }
  if (adv.verification) {
    ev.push({ at: `${TODAY}T11:0${f.sNo % 10}`, actor: adv.verification.agentName, label: adv.verification.outcome === "confirmed" ? "Verified — issue confirmed" : "Verified — issue not found", detail: adv.verification.observations });
    ev.push({ at: `${TODAY}T11:2${f.sNo % 10}`, actor: "Ayesha Khan", label: "Feedback recorded", detail: adv.feedback.explanation });
    ev.push({ at: `${TODAY}T11:2${f.sNo % 10}`, actor: "FAMS", label: "Feedback returned to Agrobot" });
  }
  if (adv.forwarding) ev.push({ at: `${TODAY}T12:00`, actor: "Ayesha Khan", label: "Forwarded to farmer via Farmer App" });
  if (adv.closure) ev.push({ at: `${TODAY}T12:05`, actor: "Ayesha Khan", label: "Closed — not forwarded", detail: adv.closure.reason });
  return ev;
}

export function buildInitialAdvisories() {
  const list = todaysFarms.map((f, i) => {
    const issueType = issueFor(f);
    const def = ISSUE_DEFS[issueType];
    const adv = {
      id: `adv-${CYCLE.number}-${f.sNo}`,
      farmId: f.id,
      cycle: CYCLE.number,
      date: TODAY,
      kind: "farm",
      issueType,
      indexLayer: def.index,
      severity: sevOf(f),
      text: advisoryText(issueType, f),
      affectedArea: `${Math.max(8, (f.sNo * 7) % 45)}% of field`,
      state: "received",
      assignedAgentId: null,
      verification: null,
      feedback: null,
      forwarding: null,
      closure: null,
    };
    if (i >= 3 && i < 6) {
      adv.state = "pending_verification";
      adv.assignedAgentId = AGENTS[i % AGENTS.length].id;
    }
    if (i === 6 || i === 7) {
      const confirmed = i === 6;
      adv.state = "verified";
      adv.assignedAgentId = AGENTS[i % AGENTS.length].id;
      adv.verification = {
        outcome: confirmed ? "confirmed" : "not_found",
        agentName: AGENTS[i % AGENTS.length].name,
        visitDate: TODAY,
        observations: confirmed
          ? "Visible stress in the flagged section; matches the analysis."
          : "Flagged patch was recently harvested strip, crop healthy elsewhere.",
      };
      adv.feedback = {
        outcome: adv.verification.outcome,
        explanation: confirmed ? "Issue confirmed on ground; advisory accurate." : "False positive — harvested area misread as stress.",
        falsePositiveReason: confirmed ? null : "Recently harvested area misread as stress",
        recordedBy: "Ayesha Khan",
        recordedAt: TODAY,
        returnedToAgrobot: true,
      };
    }
    if (i === 8) {
      adv.state = "closed";
      adv.assignedAgentId = AGENTS[0].id;
      adv.verification = { outcome: "confirmed", agentName: AGENTS[0].name, visitDate: TODAY, observations: "Confirmed moisture stress in NE quadrant." };
      adv.feedback = { outcome: "confirmed", explanation: "Confirmed; forwarded with local irrigation note.", falsePositiveReason: null, recordedBy: "Ayesha Khan", recordedAt: TODAY, returnedToAgrobot: true };
      adv.forwarding = { forwardedBy: "Ayesha Khan", forwardedAt: TODAY, delivered: true, annotatedText: null };
    }
    adv.events = mkTimeline(adv, f);
    return adv;
  });
  return list;
}

// Past-cycle history advisories (read-only)
export const historyAdvisories = flagged.slice(0, 30).flatMap((f) => {
  const n = (f.sNo % 3) + 1;
  return Array.from({ length: n }, (_, k) => {
    const cyc = CYCLE.number - 1 - k;
    const confirmed = (f.sNo + k) % 4 !== 0;
    const issue = k % 2 === 0 ? issueFor(f) : "Water Stress";
    return {
      id: `adv-${cyc}-${f.sNo}`,
      farmId: f.id,
      cycle: cyc,
      date: `2026-0${7 - Math.floor((k + 1) / 4)}-${String(16 - 5 * (k + 1)).padStart(2, "0")}`,
      kind: "farm",
      issueType: issue,
      indexLayer: ISSUE_DEFS[issue].index,
      severity: (f.sNo + k) % 2 ? "Medium" : "High",
      text: advisoryText(issue, f),
      state: "closed",
      verification: { outcome: confirmed ? "confirmed" : "not_found", agentName: AGENTS[(f.sNo + k) % 4].name },
      forwarding: confirmed ? { forwardedAt: "", delivered: true } : null,
      closure: confirmed ? null : { reason: "False positive" },
    };
  });
});

export const generalAdvisories = [
  { id: "gen-1", kind: "general", date: TODAY, title: "Heat advisory", text: "Daytime highs of 39–41°C expected through Sunday. Irrigate rice in the evening; avoid midday spraying." },
  { id: "gen-2", kind: "general", date: TODAY, title: "Rain outlook", text: "35% chance of scattered showers Monday. Plan fertilizer application accordingly." },
  { id: "gen-3", kind: "general", date: TODAY, title: "Jassid alert — district", text: "Elevated jassid pressure reported across Layyah tehsil. Scout cotton and rice borders." },
  { id: "gen-4", kind: "general", date: TODAY, title: "Canal closure notice", text: "Canal maintenance 20–22 Jul. Tubewell owners unaffected." },
  { id: "gen-5", kind: "general", date: TODAY, title: "Mandi prices", text: "Rice (Basmati 1847): Rs. 3,650/mound at Layyah mandi, up 2.1% this week." },
];

// ---- service requests (implements & drones) ----
const REQ_DEFS = [
  ["Tractor + Rotavator", "implement", 2500, 800],
  ["Laser Land Leveler", "implement", 4500, 1200],
  ["Drone Spraying", "drone", 1800, 400],
  ["Drone Field Survey", "drone", 2000, 500],
  ["Combine Harvester", "implement", 6000, 1500],
  ["Seed Drill", "implement", 2200, 600],
];

export function buildInitialRequests() {
  const states = ["received", "received", "received", "scheduled", "scheduled", "in_progress", "completed", "completed", "completed", "declined"];
  const pick = farms.filter((f) => f.sNo % 4 === 3).slice(0, 10);
  return pick.map((f, i) => {
    const [name, type, base, petrolBase] = REQ_DEFS[i % REQ_DEFS.length];
    const basePrice = base + Math.round(f.acres) * 100;
    const state = states[i];
    // Petrol/transport is entered by the manager per request; only requests the
    // manager has already actioned carry a petrol figure.
    const petrol = state === "received" ? null : petrolBase + (f.sNo % 4) * 50;
    return {
      id: `req-${100 + i}`,
      farmId: f.id,
      farmer: f.farmer,
      service: name,
      type,
      basePrice,
      petrol,
      total: basePrice + (petrol ?? 0),
      requestedAt: i < 6 ? TODAY : "2026-07-1" + ((i % 5) + 0),
      state,
      scheduledFor: state === "scheduled" || state === "in_progress" ? "2026-07-19" : null,
      completedAt: state === "completed" ? "2026-07-1" + ((i % 6) + 1) : null,
      declineReason: state === "declined" ? "Harvester unavailable this week; offered next slot" : null,
    };
  });
}

// ---- implement earnings trend (advisories carry no charges) ----
export const earningsTrend = [
  { month: "Feb", implements: 21500 },
  { month: "Mar", implements: 26800 },
  { month: "Apr", implements: 24200 },
  { month: "May", implements: 31600 },
  { month: "Jun", implements: 35400 },
  { month: "Jul", implements: 41200 },
];

export const cycleBars = [
  { day: "D1", farm: 5, general: 3, weather: 2 },
  { day: "D2", farm: 4, general: 2, weather: 3 },
  { day: "D3", farm: 0, general: 0, weather: 0 },
  { day: "D4", farm: 0, general: 0, weather: 0 },
  { day: "D5", farm: 0, general: 0, weather: 0 },
];

export const weather = {
  temp: 38, low: 31, wind: 8, humidity: 48, rain: 15,
  forecast: [
    { day: "Fri", hi: 39, lo: 31, rain: 0 },
    { day: "Sat", hi: 39, lo: 31, rain: 5 },
    { day: "Sun", hi: 39, lo: 30, rain: 20 },
    { day: "Mon", hi: 35, lo: 28, rain: 35 },
    { day: "Tue", hi: 36, lo: 29, rain: 10 },
    { day: "Wed", hi: 38, lo: 30, rain: 0 },
  ],
};

// ---- per-farm satellite chart series (deterministic) ----
export const STAGES = ["Seedling", "Tillering", "Panicle Init.", "Heading", "Grain Filling", "Dough", "Maturity"];

export function indexSeries(farm, index = "NDVI") {
  const seed = farm.sNo;
  const bump = (i) => Math.sin((seed % 7) + i * 0.9) * 0.06;
  const refBase = [0.18, 0.35, 0.52, 0.68, 0.62, 0.48, 0.35];
  const scale = { NDVI: 1, NDMI: 0.8, EVI: 0.9, MSAVI: 0.85, NDRE: 0.7, NDWI: 0.5, NBR: 0.6 }[index] ?? 1;
  const penalty = farm.disease.outbreak ? 0.12 : farm.condition !== "Good" ? 0.08 : 0.02;
  return STAGES.map((stage, i) => ({
    stage,
    reference: +(refBase[i] * scale).toFixed(2),
    actual: +Math.max(0.05, refBase[i] * scale - penalty + bump(i)).toFixed(2),
  }));
}

export function classification(farm) {
  const s = farm.sNo;
  const stressed = farm.disease.outbreak || farm.condition !== "Good";
  return [
    { name: "Open Soil", value: stressed ? 4 + (s % 3) : 1 + (s % 2), fill: "#e24b4a" },
    { name: "Sparse", value: stressed ? 3 + (s % 2) : 2, fill: "#f59e0b" },
    { name: "Moderate", value: 2 + (s % 3), fill: "#a3e635" },
    { name: "Dense", value: stressed ? 1 : 3 + (s % 3), fill: "#16a34a" },
  ];
}

export const fmtRs = (n) => "Rs. " + Math.round(n).toLocaleString("en-PK");

// ---- per-farm weather (deterministic; icons from Agriverse /weather-icons) ----
export const WEATHER_TYPES = [
  { key: "sunny", label: "Sunny", icon: "/weather-icons/clear-day.svg", advisory: "Clear, 39°C — irrigate in the evening, avoid midday spraying." },
  { key: "partly", label: "Partly cloudy", icon: "/weather-icons/cloudy-1-day.svg", advisory: "Partly cloudy, 37°C — good window for field operations." },
  { key: "mostly", label: "Mostly cloudy", icon: "/weather-icons/cloudy-2-day.svg", advisory: "Mostly cloudy, 36°C — favourable for transplanting and field work." },
  { key: "overcast", label: "Overcast", icon: "/weather-icons/cloudy.svg", advisory: "Overcast, 35°C — favourable spray window before noon." },
  { key: "clearnight", label: "Clear night", icon: "/weather-icons/clear-night.svg", advisory: "Clear night, low 28°C — good conditions for night irrigation turns." },
  { key: "partlynight", label: "Partly cloudy night", icon: "/weather-icons/cloudy-1-night.svg", advisory: "Partly cloudy night — no frost or dew risk expected." },
  { key: "mostlynight", label: "Mostly cloudy night", icon: "/weather-icons/cloudy-2-night.svg", advisory: "Cloudy night, humid — monitor for fungal disease pressure." },
];

export function farmWeather(f) {
  return WEATHER_TYPES[(f.sNo * 3) % WEATHER_TYPES.length];
}

// Farm-level advisory status for the map: red = problem, orange = moderate, green = healthy.
export function farmStatus(f, advisory) {
  if (advisory && advisory.state !== "closed") {
    if (advisory.severity === "High" || (f.disease.severity ?? 0) >= 50) return "problem";
    return "moderate";
  }
  if (f.condition !== "Good") return "moderate";
  return "healthy";
}

export const STATUS_COLORS = { problem: "#e24b4a", moderate: "#f59e0b", healthy: "#4caf50" };
