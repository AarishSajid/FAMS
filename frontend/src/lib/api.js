// Utility for making authenticated API calls to the FastAPI backend

const BASE_URL = "/api";

export async function fetchApi(endpoint, options = {}) {
  let token = typeof window !== "undefined" ? localStorage.getItem("fams_token") : null;
  
  const getHeaders = (t) => ({
    "Content-Type": "application/json",
    ...(options.headers || {}),
    ...(t ? { "Authorization": `Bearer ${t}` } : {})
  });

  let response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: getHeaders(token),
  });

  // Handle unauthorized (e.g. token expired)
  if (response.status === 401 && typeof window !== "undefined") {
    const refreshToken = localStorage.getItem("fams_refresh_token");
    if (refreshToken && endpoint !== "/auth/refresh") {
      try {
        const refreshRes = await fetch(`${BASE_URL}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refreshToken })
        });
        
        if (refreshRes.ok) {
          const newTokens = await refreshRes.json();
          localStorage.setItem("fams_token", newTokens.accessToken);
          localStorage.setItem("fams_refresh_token", newTokens.refreshToken);
          token = newTokens.accessToken;
          
          // Retry the original request
          response = await fetch(`${BASE_URL}${endpoint}`, {
            ...options,
            headers: getHeaders(token),
          });
        } else {
          // Refresh failed, clear tokens
          localStorage.removeItem("fams_token");
          localStorage.removeItem("fams_refresh_token");
        }
      } catch (err) {
        localStorage.removeItem("fams_token");
        localStorage.removeItem("fams_refresh_token");
      }
    } else {
      localStorage.removeItem("fams_token");
      localStorage.removeItem("fams_refresh_token");
    }
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    let errorMsg = response.statusText;
    if (data?.detail) {
      errorMsg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    }
    throw new Error(errorMsg);
  }

  return data;
}
