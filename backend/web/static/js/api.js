const DSA = (() => {
  const CSRF_COOKIE = "dsa_csrf";

  function csrfToken() {
    const prefix = `${CSRF_COOKIE}=`;
    const parts = document.cookie.split(";").map((part) => part.trim());
    const match = parts.find((part) => part.startsWith(prefix));
    return match ? decodeURIComponent(match.slice(prefix.length)) : "";
  }

  async function ensureCsrf() {
    if (csrfToken()) return;
    const res = await fetch("/api/auth/csrf", { credentials: "include" });
    if (!res.ok) {
      throw new Error("Could not initialize login session");
    }
  }

  function errorMessage(detail, fallback) {
    if (typeof detail === "string" && detail.trim()) return detail;
    if (Array.isArray(detail)) {
      const parts = detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object" && typeof item.msg === "string") {
            return item.msg;
          }
          return "";
        })
        .map((part) => part.trim())
        .filter(Boolean);
      if (parts.length) return parts.join("; ");
    }
    if (detail && typeof detail === "object" && typeof detail.msg === "string") {
      const msg = detail.msg.trim();
      if (msg) return msg;
    }
    return fallback || "Request failed";
  }

  async function request(path, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    if (method !== "GET" && method !== "HEAD" && method !== "OPTIONS") {
      await ensureCsrf();
    }

    const headers = { ...(options.headers || {}) };
    if (options.body && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
    const token = csrfToken();
    if (token && method !== "GET" && method !== "HEAD" && method !== "OPTIONS") {
      headers["X-CSRF-Token"] = token;
    }

    const res = await fetch(path, {
      credentials: "include",
      ...options,
      headers,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const data = await res.json();
        detail = errorMessage(data.detail, detail);
      } catch {
        /* ignore */
      }
      throw new Error(typeof detail === "string" ? detail : "Request failed");
    }
    if (res.status === 204) return null;
    return res.json();
  }

  return {
    session: () => request("/api/auth/session"),
    login: (username, password) =>
      request("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      }),
    logout: () => request("/api/auth/logout", { method: "POST" }),
    listSites: () => request("/api/sites"),
    createSite: (payload) =>
      request("/api/sites", { method: "POST", body: JSON.stringify(payload) }),
    updateSite: (siteId, payload) =>
      request(`/api/sites/${siteId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    visits: (siteId, opts = {}) => {
      const params = new URLSearchParams({ site_id: siteId });
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (tz) params.set("tz", tz);
      if (opts.hours) params.set("hours", String(opts.hours));
      else params.set("days", String(opts.days ?? 14));
      return request(`/api/stats/visits?${params}`);
    },
  };
})();

if (typeof window !== "undefined") window.DSA = DSA;
