/**
 * Local-only demo mode footer.
 */
(function () {
  async function initDemoFooter() {
    const res = await fetch("/api/demo-mode", { credentials: "include" });
    if (!res.ok) return;
    const state = await res.json();
    if (!state.available) return;

    document.body.classList.add("has-demo-footer");

    const footer = document.createElement("aside");
    footer.className = "demo-mode-footer";
    footer.setAttribute("aria-label", "Demo data mode");

    const enabled = Boolean(state.enabled);
    const copy = enabled
      ? "Synthetic fixtures are loaded for quick UI validation."
      : "Live persistence only - toggle on to explore sample sites, charts, and events.";

    const csrfRes = await fetch("/api/auth/csrf", { credentials: "include" });
    if (!csrfRes.ok) return;
    const csrfData = await csrfRes.json();
    const csrfToken = csrfData.csrf_token || "";

    footer.innerHTML = `
      <div class="demo-mode-footer-inner">
        <div class="demo-mode-copy">
          <strong>Demo data</strong>
          <span>${copy}</span>
        </div>
        <form class="demo-mode-form" method="post" action="/demo-mode">
          <input type="hidden" name="redirect" value="${location.pathname}">
          <input type="hidden" name="csrf_token" value="${csrfToken}">
          <button
            class="btn ${enabled ? "" : "btn-primary"}"
            type="submit"
            name="enabled"
            value="${enabled ? "0" : "1"}"
          >${enabled ? "Turn off" : "Turn on"}</button>
        </form>
      </div>
    `;

    document.body.appendChild(footer);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initDemoFooter);
  } else {
    initDemoFooter();
  }
})();
