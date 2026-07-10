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
    await fetch("/api/auth/csrf", { credentials: "include" });
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
        detail = data.detail || detail;
      } catch {
        /* ignore */
      }
      throw new Error(detail);
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
      if (opts.hours) params.set("hours", String(opts.hours));
      else params.set("days", String(opts.days ?? 14));
      return request(`/api/stats/visits?${params}`);
    },
  };
})();

if (typeof window !== "undefined") window.DSA = DSA;
