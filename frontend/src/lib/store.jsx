"use client";
import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { fetchApi } from "./api";

const Ctx = createContext(null);

export function FamsProvider({ children }) {
  const [user, setUser] = useState(null); // The current user object
  const [role, setRole] = useState(null); // "SERVICE_CENTER_MANAGER", "CHIEF_AGRONOMIST", etc.
  const [advisories, setAdvisories] = useState([]);
  const [requests, setRequests] = useState([]);
  const [farms, setFarms] = useState([]);
  const [broadcasts, setBroadcasts] = useState([]);
  const [loading, setLoading] = useState(true);

  // Initial load
  const loadMe = useCallback(async () => {
    try {
      if (typeof window !== "undefined" && localStorage.getItem("fams_token")) {
        const me = await fetchApi("/auth/me");
        setUser(me);
        setRole(me.role);
      }
    } catch (e) {
      console.warn("Not logged in");
      setUser(null);
      setRole(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  const refreshData = useCallback(async () => {
    if (!user) return;
    try {
      const centerId = user.serviceCenterId || 1;

      // Advisories
      const advRes = await fetchApi(`/advisory-case?limit=100&serviceCenterId=${centerId}`);
      // Since our API maps state to strings in upper case e.g. "PENDING_VERIFICATION", convert them to lowercase to match the UI, or let the UI handle it. 
      // The UI expects lowercase like "pending_verification". We'll map it here to avoid changing all UI files.
      const mappedAdvisories = (advRes.data || []).map(a => ({
        ...a,
        state: a.state ? a.state.toLowerCase() : null,
        issueType: a.issueType ? a.issueType.toLowerCase() : null,
      }));
      setAdvisories(mappedAdvisories);
      
      // Requests
      const reqRes = await fetchApi(`/service/requests/service-center/${centerId}`);
      const mappedReqs = (reqRes || []).map(r => ({
        ...r,
        state: r.status ? r.status.toLowerCase() : null,
        farmer: r.farm?.farmer,
        service: r.service?.name,
        type: r.service?.name?.toLowerCase().includes("drone") ? "drone" : "implement",
        petrol: r.petrolCost,
        total: r.totalCost,
      }));
      setRequests(mappedReqs);

      // Farms
      const scRes = await fetchApi(`/service-center/${centerId}`);
      setFarms(scRes.farms || []);

      // Broadcasts (General Advisories)
      const bRes = await fetchApi(`/broadcast`);
      setBroadcasts(bRes || []);
    } catch (e) {
      console.error(e);
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      refreshData();
      
      // Auto-refresh every 1 hour (3600000 ms)
      const interval = setInterval(() => {
        refreshData();
      }, 3600000);
      return () => clearInterval(interval);
    }
  }, [user, refreshData]);

  const api = {
    user,
    role,
    loading,
    advisories,
    requests,
    farms,
    broadcasts,

    login: async (email, password) => {
      const res = await fetchApi("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem("fams_token", res.accessToken);
      localStorage.setItem("fams_refresh_token", res.refreshToken);
      await loadMe();
      return res.user;
    },

    logout: () => {
      localStorage.removeItem("fams_token");
      localStorage.removeItem("fams_refresh_token");
      setUser(null);
      setRole(null);
      setAdvisories([]);
      setRequests([]);
    },

    assignAgent: async (id, agentId) => {
      await fetchApi(`/advisory-case/${id}/assign`, {
        method: "PATCH",
        body: JSON.stringify({ agentId }),
      });
      await refreshData();
    },

    recordVerification: async (id, payload) => {
      // 1. Submit Verification
      await fetchApi(`/advisory-case/${id}/verification`, {
        method: "POST",
        body: JSON.stringify({
          outcome: payload.outcome, // "CONFIRMED" or "NOT_FOUND"
          observations: payload.observations,
        }),
      });
      // 2. Submit Feedback
      await fetchApi(`/advisory-case/${id}/feedback`, {
        method: "POST",
        body: JSON.stringify({
          explanation: payload.explanation,
          falsePositiveReason: payload.falsePositiveReason,
        }),
      });
      await refreshData();
    },

    forward: async (id, annotatedText) => {
      await fetchApi(`/advisory-case/${id}/forward`, {
        method: "POST",
        body: JSON.stringify({ annotatedText }),
      });
      await refreshData();
    },

    close: async (id, reason) => {
      await fetchApi(`/advisory-case/${id}/close`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
      await refreshData();
    },

    reqAction: async (id, action, payload) => {
      if (action === "schedule") {
        await fetchApi(`/service/${id}/schedule`, {
          method: "PATCH",
          body: JSON.stringify({ scheduledFor: payload?.date || new Date().toISOString(), handledById: user.id }),
        });
      } else if (action === "petrol") {
        await fetchApi(`/service/${id}/cost`, {
          method: "PATCH",
          body: JSON.stringify({ petrolCost: payload }),
        });
      } else if (action === "complete") {
        await fetchApi(`/service/${id}/complete`, { method: "PATCH" });
      } else if (action === "decline") {
        await fetchApi(`/service/${id}/decline`, {
          method: "PATCH",
          body: JSON.stringify({ declineReason: payload || "Not available" }),
        });
      }
      await refreshData();
    },

    syncAgriverse: async () => {
      await fetchApi("/sync/trigger", { method: "POST" });
      await refreshData();
    },
  };

  return <Ctx.Provider value={api}>{children}</Ctx.Provider>;
}

export const useFams = () => useContext(Ctx);
