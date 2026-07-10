(function () {
  const script = document.currentScript;
  if (!script) return;

  const siteKey = (script.getAttribute("data-site") || "").trim();
  if (!siteKey) return;

  const scriptUrl = script.src || "";
  const defaultEndpoint = scriptUrl ? new URL("/collect", scriptUrl).href : "/collect";
  const endpoint = (script.getAttribute("data-endpoint") || defaultEndpoint).trim();

  const VISITOR_KEY = "dsa-visitor";
  const VISITOR_HASH_KEY = "dsa-visitor-hash";
  const CONSENT_KEY = "dsa-consent";
  const SESSION_KEY = "dsa-session";
  const SESSION_TS_KEY = "dsa-session-ts";
  const SESSION_IDLE_MS = 30 * 60 * 1000;
  const hovered = new Set();

  let persistenceEnabled = false;
  let cachedVisitorHash = "";

  function privacyOptOut() {
    if (navigator.globalPrivacyControl === true) return true;
    const dnt = navigator.doNotTrack || window.doNotTrack || navigator.msDoNotTrack;
    return dnt === "1" || dnt === "yes";
  }

  function consentGranted() {
    if ((script.getAttribute("data-consent") || "").trim().toLowerCase() === "granted") {
      return true;
    }
    try {
      return localStorage.getItem(CONSENT_KEY) === "1";
    } catch {
      return false;
    }
  }

  function shouldCollect() {
    return !privacyOptOut();
  }

  function persistenceAllowed() {
    return shouldCollect() && consentGranted();
  }

  function clearPersistentIdentity() {
    try {
      localStorage.removeItem(VISITOR_KEY);
      localStorage.removeItem(VISITOR_HASH_KEY);
      localStorage.removeItem(CONSENT_KEY);
    } catch {
      /* ignore */
    }
    cachedVisitorHash = "";
    persistenceEnabled = false;
  }

  function uuid() {
    if (crypto.randomUUID) return crypto.randomUUID();
    return "v_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
  }

  function persistentVisitorId() {
    try {
      let id = localStorage.getItem(VISITOR_KEY);
      if (!id) {
        id = uuid();
        localStorage.setItem(VISITOR_KEY, id);
      }
      return id;
    } catch {
      return "";
    }
  }

  function sessionId() {
    try {
      const now = Date.now();
      const last = Number(sessionStorage.getItem(SESSION_TS_KEY) || 0);
      let id = sessionStorage.getItem(SESSION_KEY);
      if (!id || now - last > SESSION_IDLE_MS) {
        id = uuid();
        sessionStorage.setItem(SESSION_KEY, id);
      }
      sessionStorage.setItem(SESSION_TS_KEY, String(now));
      return id;
    } catch {
      return uuid();
    }
  }

  function fingerprintParts() {
    const screenObj = window.screen || {};
    return [
      navigator.userAgent || "",
      navigator.language || "",
      (navigator.languages || []).join(","),
      screenObj.width || 0,
      screenObj.height || 0,
      screenObj.colorDepth || 0,
      window.devicePixelRatio || 1,
      new Date().getTimezoneOffset(),
      navigator.hardwareConcurrency || 0,
      navigator.maxTouchPoints || 0,
      navigator.platform || "",
      navigator.cookieEnabled ? "1" : "0",
    ].join("|");
  }

  function fallbackHash(input) {
    let hash = 5381;
    for (let i = 0; i < input.length; i += 1) {
      hash = (hash * 33) ^ input.charCodeAt(i);
    }
    return "f_" + (hash >>> 0).toString(16);
  }

  async function sha256Hex(input) {
    const bytes = new TextEncoder().encode(input);
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  async function computeVisitorHash() {
    try {
      const stored = localStorage.getItem(VISITOR_HASH_KEY);
      if (stored) return stored;

      const raw = fingerprintParts();
      const hash =
        window.crypto && crypto.subtle ? await sha256Hex(raw) : fallbackHash(raw);
      localStorage.setItem(VISITOR_HASH_KEY, hash);
      return hash;
    } catch {
      return "";
    }
  }

  async function resolveIdentity() {
    persistenceEnabled = persistenceAllowed();
    if (!persistenceEnabled) {
      cachedVisitorHash = "";
      return { visitor_id: "", visitor_hash: "" };
    }

    if (!cachedVisitorHash) {
      cachedVisitorHash = await computeVisitorHash();
    }

    return {
      visitor_id: persistentVisitorId(),
      visitor_hash: cachedVisitorHash,
    };
  }

  function payload(type, trackId, identity) {
    return {
      event_id: uuid(),
      site_key: siteKey,
      type,
      path: location.pathname + location.search,
      title: document.title || "",
      referrer: document.referrer || "",
      visitor_id: identity.visitor_id,
      visitor_hash: identity.visitor_hash,
      session_id: sessionId(),
      track_id: trackId || null,
      screen_w: window.screen ? window.screen.width : null,
      screen_h: window.screen ? window.screen.height : null,
      language: navigator.language || "",
    };
  }

  function send(type, trackId, identity) {
    const body = JSON.stringify(payload(type, trackId, identity));
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: "application/json" });
      if (navigator.sendBeacon(endpoint, blob)) return;
    }
    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
      mode: "cors",
    }).catch(function () {});
  }

  function trackIdFromTarget(target) {
    const el = target && target.closest ? target.closest("[data-track-id]") : null;
    return el ? el.getAttribute("data-track-id") : null;
  }

  async function boot() {
    if (!shouldCollect()) return;

    const identity = await resolveIdentity();
    send("pageview", null, identity);

    document.addEventListener(
      "click",
      function (e) {
        resolveIdentity().then(function (id) {
          const trackId = trackIdFromTarget(e.target);
          if (trackId) send("click", trackId, id);
        });
      },
      true
    );

    document.addEventListener(
      "mouseenter",
      function (e) {
        const trackId = trackIdFromTarget(e.target);
        if (!trackId || hovered.has(trackId)) return;
        hovered.add(trackId);
        resolveIdentity().then(function (id) {
          send("hover", trackId, id);
        });
      },
      true
    );
  }

  const api = {
    grantConsent() {
      if (!shouldCollect()) return false;
      try {
        localStorage.setItem(CONSENT_KEY, "1");
      } catch {
        return false;
      }
      persistenceEnabled = true;
      return true;
    },
    revokeConsent() {
      clearPersistentIdentity();
    },
    hasConsent() {
      return consentGranted();
    },
    privacyOptOut() {
      return privacyOptOut();
    },
  };

  if (typeof window !== "undefined") {
    window.DSA = Object.assign(window.DSA || {}, api);
  }

  boot();
})();
