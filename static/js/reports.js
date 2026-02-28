(function () {
  const root = document.getElementById("reportsRoot");
  if (!root) return;

  // ----- ELEMENTOS -----
  const typeSel = document.getElementById("reportType");

  const batchSel = document.getElementById("batchSelect");
  const yearSel = document.getElementById("yearSelect");
  const monthSel = document.getElementById("monthSelect");
  const providerSel = document.getElementById("providerSelect");

  const blockLote = document.getElementById("blockLote");
  const blockMonth = document.getElementById("blockMonth");
  const blockProvider = document.getElementById("blockProvider");

  const preview = document.getElementById("previewBox");
  const status = document.getElementById("previewStatus");
  const helper = document.getElementById("helperText");

  const btnPdf = document.getElementById("btnPdf");
  const btnCsv = document.getElementById("btnCsv");

  // ----- URLS DESDE DATASET -----
  const apiLoteBase = root.dataset.apiLote;                 // .../api/reports/lote/0/
  const apiProviderBase = root.dataset.apiProvider;         // .../api/reports/provider/0/
  const apiMonth = root.dataset.apiMonth;                   // .../api/reports/month/
  const apiGlobal = root.dataset.apiGlobal;                 // .../api/reports/global/

  const pdfMonth = root.dataset.pdfMonth;
  const csvMonth = root.dataset.csvMonth;
  const pdfGlobal = root.dataset.pdfGlobal;
  const csvGlobal = root.dataset.csvGlobal;

  const pdfLoteBase = root.dataset.pdfLoteBase;             // .../reports/lote/999999/pdf/
  const csvLoteBase = root.dataset.csvLoteBase;             // .../reports/lote/999999/csv/
  const pdfProviderBase = root.dataset.pdfProviderBase;     // .../reports/provider/999999/pdf/
  const csvProviderBase = root.dataset.csvProviderBase;     // .../reports/provider/999999/csv/

  const PLACEHOLDER = "999999";

  // ----- HELPERS -----
  const isValidId = (id) => {
    const n = Number(id);
    return Number.isFinite(n) && n > 0;
  };

  const replaceId = (base, id) => {
    if (!base) return "#";
    const sid = String(id).trim();

    // Caso recomendado: base trae 999999
    if (base.includes(PLACEHOLDER)) {
      return base.replaceAll(PLACEHOLDER, sid);
    }

    // Caso alterno: base trae /0/
    if (base.includes("/0/")) {
      return base.replaceAll("/0/", `/${sid}/`);
    }

    // Último intento
    return base.replace(/\/(\d+)\//, `/${sid}/`);
  };

  const $safeFirst = (sel) => {
    if (!sel) return null;
    for (let i = 0; i < sel.options.length; i++) {
      const opt = sel.options[i];
      if (!opt.disabled && opt.value) {
        sel.selectedIndex = i;
        return opt.value;
      }
    }
    return null;
  };

  function setButtons(enabled, pdfHref = "#", csvHref = "#") {
    if (btnPdf) btnPdf.href = pdfHref;
    if (btnCsv) btnCsv.href = csvHref;

    btnPdf?.classList.toggle("pointer-events-none", !enabled);
    btnPdf?.classList.toggle("opacity-50", !enabled);
    btnCsv?.classList.toggle("pointer-events-none", !enabled);
    btnCsv?.classList.toggle("opacity-50", !enabled);
  }

  function setMode(mode) {
    blockLote?.classList.toggle("hidden", mode !== "lote");
    blockMonth?.classList.toggle("hidden", mode !== "month");
    blockProvider?.classList.toggle("hidden", mode !== "provider");

    status.textContent = "—";
    preview.textContent = "Configura el tipo de reporte y selecciona un parámetro.";
    setButtons(false);

    if (mode === "lote") helper.textContent = "Selecciona un lote evaluado para habilitar descargas.";
    if (mode === "month") helper.textContent = "Selecciona año ≥2024 y mes para generar el reporte.";
    if (mode === "provider") helper.textContent = "Selecciona un proveedor para habilitar descargas.";
    if (mode === "global") helper.textContent = "Reporte global de todos los lotes evaluados.";
  }

  async function fetchJson(url) {
    status.textContent = "Cargando…";
    const res = await fetch(url, { credentials: "include" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) throw new Error(data.error || "No se pudo cargar.");
    return data;
  }

  function renderSummaryCard(title, summary) {
    const topP = summary?.top_defects?.primary || {};
    const topS = summary?.top_defects?.secondary || {};

    const list = (obj) => {
      const entries = Object.entries(obj || {});
      if (!entries.length) return `<div class="text-xs text-zinc-500">Sin datos.</div>`;
      return `
        <ul class="mt-2 space-y-1">
          ${entries.map(([k, v]) =>
            `<li class="flex justify-between gap-4"><span class="capitalize">${k}</span><span class="font-semibold text-zinc-800">${v}</span></li>`
          ).join("")}
        </ul>
      `;
    };

    preview.innerHTML = `
      <div class="rounded-2xl border border-zinc-200 bg-white/80 p-4">
        <div class="text-sm font-semibold text-zinc-900">${title}</div>

        <div class="mt-3 grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div class="rounded-xl border border-zinc-200 bg-white/80 p-3">
            <div class="text-xs uppercase text-zinc-500">Lotes</div>
            <div class="mt-1 text-xl font-semibold text-zinc-900">${summary.total_lots ?? 0}</div>
          </div>
          <div class="rounded-xl border border-zinc-200 bg-white/80 p-3">
            <div class="text-xs uppercase text-zinc-500">KG</div>
            <div class="mt-1 text-xl font-semibold text-zinc-900">${Number(summary.total_kg ?? 0).toFixed(3)}</div>
          </div>
          <div class="rounded-xl border border-zinc-200 bg-white/80 p-3">
            <div class="text-xs uppercase text-zinc-500">Calidad</div>
            <div class="mt-1 text-xl font-semibold text-zinc-900">${Number(summary.quality_pct ?? 0).toFixed(2)}%</div>
          </div>
          <div class="rounded-xl border border-zinc-200 bg-white/80 p-3">
            <div class="text-xs uppercase text-zinc-500">Rechazo</div>
            <div class="mt-1 text-xl font-semibold text-zinc-900">${Number(summary.reject_pct ?? 0).toFixed(2)}%</div>
          </div>
        </div>

        <div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="rounded-xl border border-zinc-200 bg-white/80 p-3">
            <div class="text-sm font-semibold text-zinc-900">Defectos Primarios</div>
            ${list(topP)}
          </div>
          <div class="rounded-xl border border-zinc-200 bg-white/80 p-3">
            <div class="text-sm font-semibold text-zinc-900">Defectos Secundarios</div>
            ${list(topS)}
          </div>
        </div>
      </div>
    `;
  }

  function renderDefectListsFromCounts(counts) {
    const p = counts?.primary || {};
    const s = counts?.secondary || {};

    const list = (obj) => {
      const entries = Object.entries(obj || {});
      if (!entries.length) return `<div class="text-xs text-zinc-500">Sin datos.</div>`;
      return `
        <ul class="mt-2 space-y-1">
          ${entries.map(([k, v]) => `
            <li class="flex justify-between gap-4">
              <span class="capitalize">${k}</span>
              <span class="font-semibold text-zinc-800">${v}</span>
            </li>
          `).join("")}
        </ul>
      `;
    };

    return `
      <div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="rounded-xl border border-zinc-200 bg-white/80 p-3">
          <div class="text-sm font-semibold text-zinc-900">Defectos Primarios</div>
          ${list(p)}
        </div>
        <div class="rounded-xl border border-zinc-200 bg-white/80 p-3">
          <div class="text-sm font-semibold text-zinc-900">Defectos Secundarios</div>
          ${list(s)}
        </div>
      </div>
    `;
  }

  // ----- LOADERS -----
  async function loadLote(id) {
    if (!isValidId(id)) {
      status.textContent = "—";
      preview.textContent = "Selecciona un lote válido.";
      setButtons(false);
      return;
    }

    const data = await fetchJson(replaceId(apiLoteBase, id));

    if (!data.has_data) {
      status.textContent = "Sin datos";
      preview.textContent = data.error || "Este lote no tiene evaluación.";
      setButtons(false);
      return;
    }

    const b = data.batch;
    const e = data.evaluation;

    const counts = e?.counts || { primary: {}, secondary: {} };

    preview.innerHTML = `
      <div class="rounded-2xl border border-zinc-200 bg-white/80 p-4">
        <div class="text-sm font-semibold text-zinc-900">Reporte por lote: ${b.code}</div>
        <div class="mt-2 text-sm text-zinc-700">
          Proveedor: <span class="font-semibold">${b.provider?.name ?? "—"}</span>
          · Peso: <span class="font-semibold">${Number(b.weight_kg ?? 0).toFixed(3)} kg</span>
        </div>

        <div class="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div class="rounded-xl border border-zinc-200 bg-white/80 p-3">
            <div class="text-xs uppercase text-zinc-500">Grado</div>
            <div class="mt-1 text-xl font-semibold text-zinc-900">${e.grade ?? "—"}</div>
          </div>
          <div class="rounded-xl border border-zinc-200 bg-white/80 p-3">
            <div class="text-xs uppercase text-zinc-500">Score</div>
            <div class="mt-1 text-xl font-semibold text-zinc-900">${e.score ?? "—"}</div>
          </div>
          <div class="rounded-xl border border-zinc-200 bg-white/80 p-3">
            <div class="text-xs uppercase text-zinc-500">Total defectos</div>
            <div class="mt-1 text-xl font-semibold text-zinc-900">${e.defects_total ?? 0}</div>
          </div>
        </div>

        ${renderDefectListsFromCounts(counts)}
      </div>
    `;

    status.textContent = "Listo";
    setButtons(true,
      replaceId(pdfLoteBase, id),
      replaceId(csvLoteBase, id)
    );
  }

  async function loadMonth(year, month) {
    if (Number(year) < 2024) throw new Error("El año mínimo permitido es 2024.");

    const url = `${apiMonth}?year=${encodeURIComponent(year)}&month=${encodeURIComponent(month)}`;
    const data = await fetchJson(url);

    if (!data.has_data) {
      status.textContent = "Sin datos";
      preview.textContent = "No hay evaluaciones para ese periodo.";
      setButtons(false);
      return;
    }

    renderSummaryCard(`Reporte mensual: ${data.period?.label ?? ""}`, data.summary);
    status.textContent = "Listo";

    setButtons(true,
      `${pdfMonth}?year=${year}&month=${month}`,
      `${csvMonth}?year=${year}&month=${month}`
    );
  }

  async function loadProvider(id) {
    if (!isValidId(id)) {
      status.textContent = "—";
      preview.textContent = "Selecciona un proveedor válido.";
      setButtons(false);
      return;
    }

    const data = await fetchJson(replaceId(apiProviderBase, id));

    if (!data.has_data) {
      status.textContent = "Sin datos";
      preview.textContent = "Este proveedor no tiene evaluaciones registradas.";
      setButtons(false);
      return;
    }

    renderSummaryCard(`Reporte por proveedor: ${data.provider?.name ?? "—"}`, data.summary);
    status.textContent = "Listo";

    setButtons(true,
      replaceId(pdfProviderBase, id),
      replaceId(csvProviderBase, id)
    );
  }

  async function loadGlobal() {
    const data = await fetchJson(apiGlobal);

    if (!data.has_data) {
      status.textContent = "Sin datos";
      preview.textContent = "No hay evaluaciones registradas.";
      setButtons(false);
      return;
    }

    renderSummaryCard("Reporte global de todos los lotes", data.summary);
    status.textContent = "Listo";
    setButtons(true, pdfGlobal, csvGlobal);
  }

  // ----- REFRESH -----
  async function refresh() {
    try {
      const mode = typeSel.value;

      if (mode === "lote") {
        const id = batchSel?.value || $safeFirst(batchSel);
        return await loadLote(id);
      }

      if (mode === "month") {
        return await loadMonth(yearSel?.value, monthSel?.value);
      }

      if (mode === "provider") {
        const id = providerSel?.value || $safeFirst(providerSel);
        return await loadProvider(id);
      }

      if (mode === "global") {
        return await loadGlobal();
      }
    } catch (e) {
      console.error(e);
      status.textContent = "Error";
      preview.textContent = e.message || "Error";
      setButtons(false);
    }
  }

  // ----- INIT + EVENTS -----
  setMode(typeSel.value);

  // Selección inicial inteligente
  if (typeSel.value === "lote" && batchSel && !batchSel.value) $safeFirst(batchSel);
  if (typeSel.value === "provider" && providerSel && !providerSel.value) $safeFirst(providerSel);

  refresh();

  typeSel.addEventListener("change", () => {
    setMode(typeSel.value);

    if (typeSel.value === "lote" && batchSel && !batchSel.value) $safeFirst(batchSel);
    if (typeSel.value === "provider" && providerSel && !providerSel.value) $safeFirst(providerSel);

    refresh();
  });

  batchSel?.addEventListener("change", refresh);
  yearSel?.addEventListener("change", refresh);
  monthSel?.addEventListener("change", refresh);
  providerSel?.addEventListener("change", refresh);
})();
