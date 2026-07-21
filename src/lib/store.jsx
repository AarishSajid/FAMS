"use client";
// Client-side state: role/session, advisory workflow, service-request workflow.
// Business rules BR-1..BR-6 are enforced here and reflected in the UI.
import { createContext, useContext, useMemo, useState } from "react";
import { AGENTS, TODAY, buildInitialAdvisories, buildInitialRequests } from "./data";

const Ctx = createContext(null);

export function FamsProvider({ children }) {
  const [role, setRole] = useState(null); // "manager" | "chief"
  const [advisories, setAdvisories] = useState(buildInitialAdvisories);
  const [requests, setRequests] = useState(buildInitialRequests);

  const api = useMemo(() => {
    const update = (id, fn) =>
      setAdvisories((list) => list.map((a) => (a.id === id ? fn({ ...a, events: [...a.events] }) : a)));

    const push = (a, label, detail, actor = "Ayesha Khan") =>
      a.events.push({ at: `${TODAY}T${new Date().toTimeString().slice(0, 5)}`, actor, label, detail });

    return {
      role,
      login: setRole,
      logout: () => setRole(null),
      advisories,
      requests,

      assignAgent: (id, agentId) =>
        update(id, (a) => {
          const ag = AGENTS.find((x) => x.id === agentId);
          a.assignedAgentId = agentId;
          a.state = "pending_verification";
          push(a, `Field agent assigned — ${ag.name}`);
          return a;
        }),

      // Verification outcome + mandatory feedback in one step (BR-2);
      // feedback auto-returned to Agrobot (BR-6).
      recordVerification: (id, { outcome, observations, explanation, falsePositiveReason }) =>
        update(id, (a) => {
          const ag = AGENTS.find((x) => x.id === a.assignedAgentId) || AGENTS[0];
          a.verification = { outcome, agentName: ag.name, visitDate: TODAY, observations };
          a.feedback = {
            outcome, explanation, falsePositiveReason: falsePositiveReason || null,
            recordedBy: "Ayesha Khan", recordedAt: TODAY, returnedToAgrobot: true,
          };
          a.state = "verified";
          push(a, outcome === "confirmed" ? "Verified — issue confirmed" : "Verified — issue not found", observations, ag.name);
          push(a, "Feedback recorded", explanation);
          push(a, "Feedback returned to Agrobot", null, "FAMS");
          return a;
        }),

      // BR-1 + BR-2: only verified advisories with feedback can be forwarded.
      forward: (id, annotatedText) =>
        update(id, (a) => {
          if (!a.verification || !a.feedback) return a;
          a.forwarding = { forwardedBy: "Ayesha Khan", forwardedAt: TODAY, delivered: true, annotatedText: annotatedText || null };
          a.state = "closed";
          push(a, "Forwarded to farmer via Farmer App", annotatedText);
          return a;
        }),

      // BR-4: closed-not-forwarded is terminal, never sendable.
      close: (id, reason) =>
        update(id, (a) => {
          if (!a.feedback) return a;
          a.closure = { reason, closedBy: "Ayesha Khan", closedAt: TODAY };
          a.state = "closed";
          push(a, "Closed — not forwarded", reason);
          return a;
        }),

      reqAction: (id, action, payload) =>
        setRequests((list) =>
          list.map((r) => {
            if (r.id !== id) return r;
            const n = { ...r };
            if (action === "schedule") {
              n.state = "scheduled";
              n.scheduledFor = payload?.date || "2026-07-19";
              if (payload?.petrol != null) n.petrol = payload.petrol;
            }
            if (action === "petrol") n.petrol = payload;
            if (action === "start") n.state = "in_progress";
            if (action === "complete") { n.state = "completed"; n.completedAt = TODAY; }
            if (action === "decline") { n.state = "declined"; n.declineReason = payload || "Not available"; }
            n.total = n.basePrice + (n.petrol ?? 0);
            return n;
          })
        ),
    };
  }, [role, advisories, requests]);

  return <Ctx.Provider value={api}>{children}</Ctx.Provider>;
}

export const useFams = () => useContext(Ctx);
