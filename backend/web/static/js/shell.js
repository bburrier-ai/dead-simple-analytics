/**
 * Shared app chrome - uses components user-avatar-menu + app nav.
 */
const SHELL_PAGES = [
  { id: "dashboard", label: "Dashboard", href: "/" },
  { id: "sites", label: "Sites", href: "/sites" },
];

const ACTIVE_SITE_KEY = "dsa-active-site-id";
let cachedSites = [];

function navLinkHtml(page, current) {
  return SHELL_PAGES.map(
    (p) => `<a href="${p.href}"${p.id === current ? ' class="active"' : ""}><span>${p.label}</span></a>`
  ).join("");
}

function userFromSession(user) {
  const username = (user?.username || "admin").trim();
  return { username, displayName: username };
}

function getActiveSiteId() {
  const stored = localStorage.getItem(ACTIVE_SITE_KEY);
  if (stored && cachedSites.some((s) => s.id === stored)) return stored;
  return cachedSites[0]?.id || "";
}

function siteContextConfig() {
  return {
    key: "site",
    label: "Site",
    activeId: getActiveSiteId(),
    items: cachedSites.map((s) => ({ id: s.id, name: s.name })),
  };
}

async function ensureAuth() {
  const session = await DSA.session();
  if (!session.user) {
    window.location.href = "/login";
    return null;
  }
  return session.user;
}

async function renderShell(options = {}) {
  const { page = "" } = options;
  const user = await ensureAuth();
  if (!user) return;

  const sitesData = await DSA.listSites();
  cachedSites = sitesData.items || [];

  document.body.classList.add("has-app-header");
  const headerEl = document.getElementById("app-header");
  if (!headerEl) return;

  const identity = userFromSession(user);

  headerEl.innerHTML = `
    <div class="app-header-inner">
      <div class="app-header-start">
        <h1 class="app-title"><a href="/" class="app-title-link app-brand">
          <img src="/static/img/logo.png" alt="" class="app-logo" width="50" height="28" />
          <span>Dead Simple Analytics</span>
        </a></h1>
      </div>
      <nav class="app-nav app-nav--desktop" aria-label="Main">${navLinkHtml(page, page)}</nav>
      ${UserAvatarMenu.menuHtml({
        username: identity.username,
        displayName: identity.displayName,
        contexts: cachedSites.length ? siteContextConfig() : null,
      })}
    </div>
  `;

  UserAvatarMenu.apply({
    username: identity.username,
    displayName: identity.displayName,
    contexts: cachedSites.length ? siteContextConfig() : null,
    onContextChange: (key, item) => {
      if (key !== "site") return;
      localStorage.setItem(ACTIVE_SITE_KEY, item.id);
      document.dispatchEvent(new CustomEvent("site-changed", { detail: { siteId: item.id } }));
    },
    onSignOut: async () => {
      await DSA.logout();
      window.location.href = "/login";
    },
  });

  if (getActiveSiteId()) {
    document.dispatchEvent(
      new CustomEvent("site-changed", { detail: { siteId: getActiveSiteId() } })
    );
  }
}

window.renderShell = renderShell;
window.getActiveSiteId = getActiveSiteId;
