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
      navigator.clipboard.writeText(copyBtn.getAttribute("data-copy-snippet") || "");
      copyBtn.textContent = "Copied!";
      setTimeout(() => {
        copyBtn.textContent = "Copy tag";
      }, 1500);
      return;
    }

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
  const tbody = document.getElementById("sites-body");
  if (!tbody) return;
  const html = await fetch("/partials/sites-table", { credentials: "include" }).then((r) =>
    r.text()
  );
  tbody.innerHTML = html;
}
