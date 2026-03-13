document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("activity-module");
  if (!root) return;

  const urls = {
    list: root.dataset.listUrl,
    users: root.dataset.usersUrl,
    detailBase: root.dataset.detailBaseUrl,
  };

  const els = {
    dateFrom: document.getElementById("activity-date-from"),
    dateTo: document.getElementById("activity-date-to"),
    user: document.getElementById("activity-user"),
    module: document.getElementById("activity-module-filter"),
    level: document.getElementById("activity-level-filter"),
    apply: document.getElementById("activity-apply-filters"),
    clear: document.getElementById("activity-clear-filters"),
    feedback: document.getElementById("activity-feedback"),
    tableBody: document.getElementById("activity-table-body"),
    detail: document.getElementById("activity-detail"),
  };

  let selectedLogId = null;

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function moduleLabel(module) {
    const labels = {
      auth: "Auth",
      quality: "Quality",
      packaging: "Packaging",
      reports: "Reports",
      settings: "Settings",
    };
    return labels[module] || module || "—";
  }

  function levelBadge(level) {
    const styles = {
      info: "bg-slate-100 text-slate-700 border-slate-200",
      success: "bg-emerald-100 text-emerald-700 border-emerald-200",
      warning: "bg-amber-100 text-amber-700 border-amber-200",
      error: "bg-rose-100 text-rose-700 border-rose-200",
    };

    const labels = {
      info: "Info",
      success: "Success",
      warning: "Warning",
      error: "Error",
    };

    const cls = styles[level] || styles.info;
    const text = labels[level] || "Info";

    return `
      <span class="inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${cls}">
        ${text}
      </span>
    `;
  }

  function buildQueryParams() {
    const params = new URLSearchParams();

    const dateFrom = els.dateFrom.value.trim();
    const dateTo = els.dateTo.value.trim();
    const user = els.user.value.trim();
    const module = els.module.value.trim();
    const level = els.level.value.trim();

    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    if (user) params.set("user", user);
    if (module) params.set("module", module);
    if (level) params.set("level", level);

    return params;
  }

  async function fetchUsers() {
    try {
      const res = await fetch(urls.users, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });

      if (!res.ok) throw new Error("No se pudieron cargar los usuarios.");

      const data = await res.json();
      const results = Array.isArray(data.results) ? data.results : [];

      els.user.innerHTML = `<option value="">Todos</option>`;

      results.forEach((item) => {
        const option = document.createElement("option");
        option.value = item.id;
        option.textContent = item.username;
        els.user.appendChild(option);
      });
    } catch (error) {
      console.error(error);
    }
  }

  function renderEmptyTable(message) {
    els.tableBody.innerHTML = `
      <tr>
        <td colspan="5" class="px-6 py-10 text-center text-[#7b6a58]">
          ${escapeHtml(message)}
        </td>
      </tr>
    `;
  }

  function renderTable(results) {
    if (!results.length) {
      renderEmptyTable("No se encontraron logs con los filtros seleccionados.");
      return;
    }

    els.tableBody.innerHTML = results.map((log) => {
      const isActive = Number(log.id) === Number(selectedLogId);

      return `
        <tr
          class="cursor-pointer transition ${isActive ? "bg-[#f8f3ed]" : "hover:bg-[#fcfaf7]"}"
          data-log-id="${log.id}"
        >
          <td class="px-6 py-4 whitespace-nowrap text-[#2b1d16] font-medium">
            ${escapeHtml(log.created_at)}
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-[#5f4a3a]">
            ${escapeHtml(log.user || "Sistema")}
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-[#5f4a3a]">
            ${escapeHtml(moduleLabel(log.module))}
          </td>
          <td class="px-6 py-4 whitespace-nowrap">
            ${levelBadge(log.level)}
          </td>
          <td class="px-6 py-4 text-[#2b1d16]">
            <div class="font-medium">${escapeHtml(log.description || "—")}</div>
            ${
              log.object_label
                ? `<div class="mt-1 text-xs text-[#8a7663]">Relacionado: ${escapeHtml(log.object_label)}</div>`
                : ""
            }
          </td>
        </tr>
      `;
    }).join("");

    els.tableBody.querySelectorAll("tr[data-log-id]").forEach((row) => {
      row.addEventListener("click", () => {
        const { logId } = row.dataset;
        selectedLogId = Number(logId);
        highlightSelectedRow();
        fetchDetail(logId);
      });
    });
  }

  function highlightSelectedRow() {
    els.tableBody.querySelectorAll("tr[data-log-id]").forEach((row) => {
      const isActive = Number(row.dataset.logId) === Number(selectedLogId);
      row.classList.toggle("bg-[#f8f3ed]", isActive);
    });
  }

  function renderDetailEmpty(message = "Aún no has seleccionado ningún log.") {
    els.detail.innerHTML = `
      <div class="rounded-2xl border border-dashed border-[#dccbbd] bg-[#fcfaf7] px-5 py-8 text-center text-sm text-[#7b6a58]">
        ${escapeHtml(message)}
      </div>
    `;
  }

  function renderDetail(data) {
    els.detail.innerHTML = `
      <div class="space-y-5">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-xs font-semibold uppercase tracking-wide text-[#8a7663]">Evento</p>
            <h4 class="mt-1 text-lg font-semibold text-[#2b1d16]">
              ${escapeHtml(data.description || "Sin descripción")}
            </h4>
          </div>
          <div>${levelBadge(data.level)}</div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="rounded-xl bg-[#fcfaf7] border border-[#f1e7de] p-4">
            <p class="text-xs uppercase tracking-wide font-semibold text-[#8a7663]">Fecha</p>
            <p class="mt-1 text-sm font-medium text-[#2b1d16]">${escapeHtml(data.created_at || "—")}</p>
          </div>

          <div class="rounded-xl bg-[#fcfaf7] border border-[#f1e7de] p-4">
            <p class="text-xs uppercase tracking-wide font-semibold text-[#8a7663]">Usuario</p>
            <p class="mt-1 text-sm font-medium text-[#2b1d16]">${escapeHtml(data.user || "Sistema")}</p>
          </div>

          <div class="rounded-xl bg-[#fcfaf7] border border-[#f1e7de] p-4">
            <p class="text-xs uppercase tracking-wide font-semibold text-[#8a7663]">Módulo</p>
            <p class="mt-1 text-sm font-medium text-[#2b1d16]">${escapeHtml(moduleLabel(data.module))}</p>
          </div>

          <div class="rounded-xl bg-[#fcfaf7] border border-[#f1e7de] p-4">
            <p class="text-xs uppercase tracking-wide font-semibold text-[#8a7663]">Acción interna</p>
            <p class="mt-1 text-sm font-medium text-[#2b1d16]">${escapeHtml(data.action || "—")}</p>
          </div>

          <div class="rounded-xl bg-[#fcfaf7] border border-[#f1e7de] p-4 sm:col-span-2">
            <p class="text-xs uppercase tracking-wide font-semibold text-[#8a7663]">Relacionado</p>
            <p class="mt-1 text-sm font-medium text-[#2b1d16]">${escapeHtml(data.object_label || "—")}</p>
          </div>
        </div>
      </div>
    `;
  }

  async function fetchLogs() {
    const params = buildQueryParams();
    const query = params.toString();
    const url = query ? `${urls.list}?${query}` : urls.list;

    els.feedback.textContent = "Cargando logs...";
    renderEmptyTable("Cargando logs...");

    if (!selectedLogId) {
      renderDetailEmpty();
    }

    try {
      const res = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });

      if (!res.ok) throw new Error("No se pudo cargar el listado de logs.");

      const data = await res.json();
      const results = Array.isArray(data.results) ? data.results : [];

      renderTable(results);
      els.feedback.textContent = `${results.length} registro(s) encontrado(s).`;

      if (selectedLogId) {
        const stillExists = results.some((item) => Number(item.id) === Number(selectedLogId));
        if (!stillExists) {
          selectedLogId = null;
          renderDetailEmpty("Selecciona un log para ver su detalle.");
        }
      }
    } catch (error) {
      console.error(error);
      els.feedback.textContent = "Ocurrió un error al cargar los logs.";
      renderEmptyTable("No fue posible cargar los logs.");
      renderDetailEmpty("No fue posible cargar el detalle.");
    }
  }

  async function fetchDetail(logId) {
    const detailUrl = urls.detailBase.replace(/0\/?$/, `${logId}/`);

    els.detail.innerHTML = `
      <div class="rounded-2xl border border-dashed border-[#dccbbd] bg-[#fcfaf7] px-5 py-8 text-center text-sm text-[#7b6a58]">
        Cargando detalle...
      </div>
    `;

    try {
      const res = await fetch(detailUrl, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });

      if (!res.ok) throw new Error("No se pudo cargar el detalle del log.");

      const data = await res.json();
      renderDetail(data);
    } catch (error) {
      console.error(error);
      renderDetailEmpty("No fue posible cargar el detalle del log.");
    }
  }

  function clearFilters() {
    els.dateFrom.value = "";
    els.dateTo.value = "";
    els.user.value = "";
    els.module.value = "";
    els.level.value = "";
    selectedLogId = null;
    renderDetailEmpty();
    fetchLogs();
  }

  els.apply.addEventListener("click", fetchLogs);
  els.clear.addEventListener("click", clearFilters);

  [els.dateFrom, els.dateTo, els.user, els.module, els.level].forEach((el) => {
    el.addEventListener("change", fetchLogs);
  });

  fetchUsers();
  fetchLogs();
});
