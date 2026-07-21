"use client";
import { useRouter } from "next/navigation";
import { useFams } from "@/lib/store";

const ROLES = [
  {
    id: "manager",
    title: "Service Center Manager",
    who: "Ayesha Khan — Layyah Center",
    desc: "Review advisories, arrange field verification, record feedback, forward to farmers, and manage implement requests.",
    to: "/dashboard",
  },
  {
    id: "chief",
    title: "Chief Agronomist",
    who: "Dr. Imran Sethi",
    desc: "Read-only oversight of advisory and service-request performance across all service centers.",
    to: "/overview",
  },
];

export default function Login() {
  const { login } = useFams();
  const router = useRouter();

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "radial-gradient(1200px 600px at 70% -10%, rgba(76,175,80,0.12), transparent), var(--surface-1)", padding: 24 }}>
      <div style={{ width: 720, maxWidth: "100%" }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div style={{ fontSize: 34, fontWeight: 700, color: "var(--text-bright)" }}>
            <span style={{ color: "var(--accent)" }}>FAMS</span>
          </div>
          <div style={{ fontSize: 14, color: "var(--text-secondary)", marginTop: 6 }}>
            Farmer Advisory Management System — an <span style={{ color: "var(--text-accent)" }}>agriverse</span> component
          </div>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
            Prototype — pick a role to continue, no password required
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          {ROLES.map((r) => (
            <button
              key={r.id}
              onClick={() => { login(r.id); router.push(r.to); }}
              className="card"
              style={{ textAlign: "left", cursor: "pointer", transition: "border-color .15s", display: "block" }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--accent-border)")}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
            >
              <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-bright)" }}>{r.title}</div>
              <div style={{ fontSize: 12.5, color: "var(--text-accent)", margin: "4px 0 10px" }}>{r.who}</div>
              <div style={{ fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.55 }}>{r.desc}</div>
              <div className="btn btn-primary btn-sm" style={{ marginTop: 14 }}>Continue →</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
