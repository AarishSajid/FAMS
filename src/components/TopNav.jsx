"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useFams } from "@/lib/store";

const MANAGER_LINKS = [
  ["/dashboard", "Dashboard"],
  ["/advisories", "Advisories"],
  ["/services", "Services"],
  ["/agents", "Field Agents"],
  ["/leaderboard", "Leader Board"],
];

export default function TopNav() {
  const { role, logout } = useFams();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!role) router.replace("/login");
  }, [role, router]);

  const links = role === "chief" ? [["/overview", "Overview"]] : MANAGER_LINKS;

  return (
    <nav
      style={{
        display: "flex", alignItems: "center", gap: 28, padding: "0 24px", height: 56,
        background: "var(--surface-3)", borderBottom: "1px solid var(--border-subtle)",
        position: "sticky", top: 0, zIndex: 40,
      }}
    >
      <div style={{ fontSize: 20, fontWeight: 700, color: "var(--text-bright)" }}>
        <span style={{ color: "var(--accent)" }}>FAMS</span>
        <span style={{ fontSize: 11, fontWeight: 500, color: "var(--text-muted)", marginLeft: 10 }}>
          an agriverse component
        </span>
      </div>
      <div style={{ display: "flex", gap: 4 }}>
        {links.map(([href, label]) => (
          <Link
            key={href}
            href={href}
            style={{
              padding: "6px 14px", borderRadius: 8, fontSize: 13.5, fontWeight: 600,
              color: pathname.startsWith(href) ? "var(--text-accent)" : "var(--text-secondary)",
              background: pathname.startsWith(href) ? "var(--accent-muted)" : "transparent",
            }}
          >
            {label}
          </Link>
        ))}
      </div>
      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 14 }}>
        <span style={{ fontSize: 12.5, color: "var(--text-secondary)" }}>
          {role === "chief" ? "Dr. Imran Sethi — Chief Agronomist" : "Ayesha Khan — Layyah Center"}
        </span>
        <button className="btn btn-sm btn-danger" onClick={() => { logout(); router.push("/login"); }}>
          Logout
        </button>
      </div>
    </nav>
  );
}
