function parseDomains(raw) {
  return raw.split(/[\s,]+/).filter(Boolean);
}

function editField(label, value, field, className = "") {
  const wrap = document.createElement("label");
  wrap.className = "site-edit-field";
  const caption = document.createElement("span");
  caption.textContent = label;
  const input = document.createElement("input");
  input.type = "text";
  input.className = `site-edit-input${className ? ` ${className}` : ""}`;
  input.dataset.field = field;
  input.value = value;
  input.required = true;
  wrap.append(caption, input);
  return wrap;
}

function enterEditMode(row) {
  const { siteId, siteName, siteDomains, siteKey } = row.dataset;
  hideCurlPopover();
  hideSiteMenu();
  row.classList.add("site-row--editing");

  const td = document.createElement("td");
  td.colSpan = 5;
  td.className = "site-edit-panel";

  const grid = document.createElement("div");
  grid.className = "site-edit-grid";
  grid.append(
    editField("Name", siteName, "name"),
    editField("Domains", siteDomains, "domains"),
    editField("Site key", siteKey, "site_key", "mono")
  );

  const actions = document.createElement("div");
  actions.className = "site-edit-actions";
  actions.innerHTML = `
    <button type="button" class="btn btn-primary" data-save-site>Save</button>
    <button type="button" class="btn" data-cancel-site>Cancel</button>
  `;
  grid.appendChild(actions);
  td.appendChild(grid);

  row.dataset.siteId = siteId;
  row.replaceChildren(td);
}

function readEditRow(row) {
  const fields = {};
  row.querySelectorAll("[data-field]").forEach((input) => {
    fields[input.dataset.field] = input.value.trim();
  });
  return {
    name: fields.name,
    allowed_domains: parseDomains(fields.domains),
    site_key: fields.site_key,
  };
}

let curlPopoverEl = null;
let curlPopoverAnchor = null;
let siteMenuPopoverEl = null;
let siteMenuAnchorBtn = null;

function hideCurlPopover() {
  if (curlPopoverEl) {
    curlPopoverEl.remove();
    curlPopoverEl = null;
  }
  curlPopoverAnchor = null;
}

function hideSiteMenu() {
  if (siteMenuPopoverEl) {
    siteMenuPopoverEl.remove();
    siteMenuPopoverEl = null;
  }
  if (siteMenuAnchorBtn) {
    siteMenuAnchorBtn.setAttribute("aria-expanded", "false");
    siteMenuAnchorBtn = null;
  }
}

function placeFixedPopover(el, anchorRect) {
  const pad = 8;
  el.hidden = false;
  const width = el.getBoundingClientRect().width;
  const height = el.getBoundingClientRect().height;
  let left = anchorRect.right - width;
  let top = anchorRect.bottom + 4;
  if (left < pad) left = pad;
  if (left + width > window.innerWidth - pad) {
    left = Math.max(pad, window.innerWidth - width - pad);
  }
  if (top + height > window.innerHeight - pad && anchorRect.top > height + pad) {
    top = anchorRect.top - height - 4;
  }
  el.style.left = `${left}px`;
  el.style.top = `${top}px`;
}

function showSiteMenu(menuBtn) {
  if (siteMenuAnchorBtn === menuBtn && siteMenuPopoverEl) {
    hideSiteMenu();
    return;
  }
  hideSiteMenu();
  hideCurlPopover();

  const snippet = menuBtn.getAttribute("data-copy-snippet") || "";
  const curl = menuBtn.getAttribute("data-curl-test") || "";
  const pop = document.createElement("div");
  pop.className = "site-menu-popover";
  pop.setAttribute("role", "menu");
  pop.innerHTML = `
    <button type="button" class="site-menu-item" role="menuitem" data-copy-snippet=""></button>
    <button type="button" class="site-menu-item" role="menuitem" data-curl-test=""></button>
  `;
  const copyBtn = pop.querySelector("[data-copy-snippet]");
  const curlBtn = pop.querySelector("[data-curl-test]");
  copyBtn.setAttribute("data-copy-snippet", snippet);
  copyBtn.textContent = "Copy tag";
  curlBtn.setAttribute("data-curl-test", curl);
  curlBtn.textContent = "Test w/curl";
  document.body.appendChild(pop);

  siteMenuPopoverEl = pop;
  siteMenuAnchorBtn = menuBtn;
  menuBtn.setAttribute("aria-expanded", "true");
  placeFixedPopover(pop, menuBtn.getBoundingClientRect());
}

function showCurlPopoverAt(anchorRect, curl) {
  hideCurlPopover();
  const pop = document.createElement("div");
  pop.className = "curl-popover";
  pop.setAttribute("role", "dialog");
  pop.setAttribute("aria-label", "curl command");
  pop.innerHTML = `
    <span class="curl-popover-label">Copied to clipboard</span>
    <code class="curl-popover-preview"></code>
  `;
  pop.querySelector(".curl-popover-preview").textContent = curl;
  document.body.appendChild(pop);

  const pad = 8;
  const width = Math.min(420, window.innerWidth - pad * 2);
  pop.style.width = `${width}px`;
  pop.style.left = "0px";
  pop.style.top = "0px";

  const popHeight = pop.getBoundingClientRect().height;
  let left = anchorRect.left;
  if (left + width > window.innerWidth - pad) {
    left = Math.max(pad, window.innerWidth - width - pad);
  }
  if (left < pad) left = pad;
  let top = anchorRect.bottom + 6;
  if (top + popHeight > window.innerHeight - pad && anchorRect.top > popHeight + pad) {
    top = anchorRect.top - popHeight - 6;
  }
  pop.style.left = `${left}px`;
  pop.style.top = `${top}px`;

  curlPopoverEl = pop;
  curlPopoverAnchor = null;
}

function showCurlPopover(anchor, curl) {
  showCurlPopoverAt(anchor.getBoundingClientRect(), curl);
}

window.initSitesPage = async function initSitesPage() {
  document.getElementById("site-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("site-name").value.trim();
    const domainsRaw = document.getElementById("site-domains").value.trim();
    const allowed_domains = parseDomains(domainsRaw);
    const err = document.getElementById("site-error");
    err.hidden = true;
    try {
      await DSA.createSite({ name, allowed_domains });
      document.getElementById("site-form").reset();
      await refreshSitesTable();
      await renderShell({ page: "sites" });
    } catch (ex) {
      err.textContent = ex.message || "Could not create site";
      err.hidden = false;
    }
  });

  document.body.addEventListener("click", async (e) => {
    const menuBtn = e.target.closest("[data-site-menu]");
    if (menuBtn) {
      e.preventDefault();
      e.stopPropagation();
      showSiteMenu(menuBtn);
      return;
    }

    const copyBtn = e.target.closest(".site-menu-popover [data-copy-snippet]");
    if (copyBtn) {
      e.stopPropagation();
      navigator.clipboard.writeText(copyBtn.getAttribute("data-copy-snippet") || "");
      copyBtn.textContent = "Copied!";
      setTimeout(() => {
        if (copyBtn.isConnected) copyBtn.textContent = "Copy tag";
      }, 1200);
      return;
    }

    const curlBtn = e.target.closest(".site-menu-popover [data-curl-test]");
    if (curlBtn) {
      e.stopPropagation();
      const curl = curlBtn.getAttribute("data-curl-test") || "";
      const anchorRect = (
        siteMenuAnchorBtn || curlBtn
      ).getBoundingClientRect();
      hideSiteMenu();
      try {
        await navigator.clipboard.writeText(curl);
      } catch {
        /* still show popover so the command is visible */
      }
      showCurlPopoverAt(anchorRect, curl);
      return;
    }

    if (e.target.closest(".curl-popover")) {
      return;
    }
    hideCurlPopover();
    hideSiteMenu();

    const editBtn = e.target.closest("[data-edit-site]");
    if (editBtn) {
      const row = editBtn.closest(".site-row");
      if (row) enterEditMode(row);
      return;
    }

    const cancelBtn = e.target.closest("[data-cancel-site]");
    if (cancelBtn) {
      await refreshSitesTable();
      return;
    }

    const saveBtn = e.target.closest("[data-save-site]");
    if (!saveBtn) return;

    const row = saveBtn.closest(".site-row");
    const err = document.getElementById("site-error");
    if (!row?.dataset.siteId) return;

    err.hidden = true;
    const payload = readEditRow(row);
    try {
      await DSA.updateSite(row.dataset.siteId, payload);
      await refreshSitesTable();
      await renderShell({ page: "sites" });
    } catch (ex) {
      err.textContent = ex.message || "Could not update site";
      err.hidden = false;
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      hideSiteMenu();
      hideCurlPopover();
    }
  });
  window.addEventListener("resize", () => {
    hideSiteMenu();
    hideCurlPopover();
  });
  document.addEventListener(
    "scroll",
    () => {
      hideSiteMenu();
      hideCurlPopover();
    },
    true
  );

  await refreshSitesTable();
};

async function refreshSitesTable() {
  hideCurlPopover();
  hideSiteMenu();
  const tbody = document.getElementById("sites-body");
  if (!tbody) return;
  const html = await fetch("/partials/sites-table", { credentials: "include" }).then((r) =>
    r.text()
  );
  tbody.innerHTML = html;
}
