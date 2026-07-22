"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useFams } from "@/lib/store";

export default function Login() {
  const { login } = useFams();
  const router = useRouter();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) return;
    
    setLoading(true);
    setError(null);
    try {
      const user = await login(email, password);
      // Route dynamically based on role
      if (user.role === "CHIEF_AGRONOMIST") {
        router.push("/overview");
      } else {
        router.push("/dashboard");
      }
    } catch (err) {
      setError(err.message || "Invalid credentials");
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "radial-gradient(1200px 600px at 70% -10%, rgba(76,175,80,0.12), transparent), var(--surface-1)", padding: 24 }}>
      <div className="card" style={{ width: 400, maxWidth: "100%", padding: 32 }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div style={{ fontSize: 34, fontWeight: 700, color: "var(--text-bright)" }}>
            <span style={{ color: "var(--accent)" }}>FAMS</span>
          </div>
          <div style={{ fontSize: 14, color: "var(--text-secondary)", marginTop: 6 }}>
            Farmer Advisory Management System
          </div>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
            Sign in to your account
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {error && (
            <div style={{ background: "rgba(220, 38, 38, 0.1)", color: "#ef4444", padding: "10px 14px", borderRadius: 6, fontSize: 13, border: "1px solid rgba(220, 38, 38, 0.2)" }}>
              {error}
            </div>
          )}
          
          <div>
            <label style={{ display: "block", fontSize: 13, color: "var(--text-secondary)", marginBottom: 6 }}>Email address</label>
            <input 
              type="email" 
              className="input" 
              style={{ width: "100%" }}
              placeholder="e.g. ayesha.khan@agriverse.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
            />
          </div>
          
          <div>
            <label style={{ display: "block", fontSize: 13, color: "var(--text-secondary)", marginBottom: 6 }}>Password</label>
            <input 
              type="password" 
              className="input" 
              style={{ width: "100%" }}
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
          </div>
          
          <button 
            type="submit" 
            className="btn btn-primary" 
            style={{ width: "100%", marginTop: 8, height: 40 }}
            disabled={loading || !email || !password}
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
        
        <div style={{ marginTop: 24, fontSize: 12, color: "var(--text-muted)", textAlign: "center", borderTop: "1px solid var(--border-subtle)", paddingTop: 16 }}>
          <div style={{ marginBottom: 4 }}>Default Credentials:</div>
          <div>Manager: <span style={{ color: "var(--text-secondary)" }}>ayesha.khan@agriverse.com / password</span></div>
          <div style={{ marginTop: 2 }}>Chief: <span style={{ color: "var(--text-secondary)" }}>chief@agriverse.com / password</span></div>
        </div>
      </div>
    </div>
  );
}
