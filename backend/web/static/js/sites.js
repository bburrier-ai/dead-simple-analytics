function parseDomains(raw) {
  return raw.split(/[\s,]+/).filter(Boolean);
}

function inputCell(value, field, className = "") {
  const td = document.createElement("td");
  const input = document.createElement("input");
  input.type = "text";
  input.className = `site-edit-input${className ? ` ${className}` : ""}`;
  input.dataset.field = field;
  input.value = value;
  input.required = true;
  td.appendChild(input);
  return td;
}

function enterEditMode(row) {
  const { siteId, siteName, siteDomains, siteKey } = row.dataset;
  hideCurlPopover();
  row.classList.add("site-row--editing");
  row.replaceChildren(
    inputCell(siteName, "name"),
    inputCell(siteDomains, "domains"),
    inputCell(siteKey, "site_key", "mono"),
    (() => {
      const td = document.createElement("td");
      td.colSpan = 2;
      td.className = "site-edit-actions";
      td.innerHTML = `
        <button type="button" class="btn btn-primary" data-save-site>Save</button>
        <button type="button" class="btn" data-cancel-site>Cancel</button>
      `;
      row.dataset.siteId = siteId;
      return td;
    })()
  );
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

function hideCurlPopover() {
  if (curlPopoverEl) {
    curlPopoverEl.remove();
    curlPopoverEl = null;
  }
  curlPopoverAnchor = null;
}

function showCurlPopover(anchor, curl) {
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

  const rect = anchor.getBoundingClientRect();
  const pad = 8;
  const width = Math.min(420, window.innerWidth - pad * 2);
  let left = rect.left;
  if (left + width > window.innerWidth - pad) {
    left = Math.max(pad, window.innerWidth - width - pad);
  }
  let top = rect.bottom + 6;
  pop.style.width = `${width}px`;
  pop.style.left = `${left}px`;
  pop.style.top = `${top}px`;

  const popHeight = pop.getBoundingClientRect().height;
  if (top + popHeight > window.innerHeight - pad && rect.top > popHeight + pad) {
    pop.style.top = `${rect.top - popHeight - 6}px`;
  }

  curlPopoverEl = pop;
  curlPopoverAnchor = anchor;
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
    const copyBtn = e.target.closest("[data-copy-snippet]");
    if (copyBtn) {
      hideCurlPopover();
      navigator.clipboard.writeText(copyBtn.getAttribute("data-copy-snippet") || "");
      copyBtn.textContent = "Copied!";
      setTimeout(() => {
        copyBtn.textContent = "Copy tag";
      }, 1500);
      return;
    }

    const curlBtn = e.target.closest("[data-curl-test]");
    if (curlBtn) {
      e.stopPropagation();
      if (curlPopoverEl && curlPopoverAnchor === curlBtn) {
        hideCurlPopover();
        return;
      }
      const curl = curlBtn.getAttribute("data-curl-test") || "";
      try {
        await navigator.clipboard.writeText(curl);
      } catch {
        /* still show popover so the command is visible */
      }
      showCurlPopover(curlBtn, curl);
      return;
    }

    if (e.target.closest(".curl-popover")) {
      return;
    }
    hideCurlPopover();

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

  await refreshSitesTable();
};

async function refreshSitesTable() {
  hideCurlPopover();
  const tbody = document.getElementById("sites-body");
  if (!tbody) return;
  const html = await fetch("/partials/sites-table", { credentials: "include" }).then((r) =>
    r.text()
  );
  tbody.innerHTML = html;
}
