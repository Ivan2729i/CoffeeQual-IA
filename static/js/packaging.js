document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("packaging-module");
  if (!root) return;

  const urls = {
    summary: root.dataset.summaryUrl,
    list: root.dataset.listUrl,
    detailBase: root.dataset.detailBaseUrl,
    updateBase: root.dataset.updateBaseUrl,
  };

  const state = {
    activeTab: "pending",
    rows: [],
    selectedBatchId: null,
  };

  const els = {
    kpiPendingLots: document.getElementById("pk-kpi-pending-lots"),
    kpiPackedToday: document.getElementById("pk-kpi-packed-today"),
    kpiPendingKg: document.getElementById("pk-kpi-pending-kg"),
    kpiPackedKg: document.getElementById("pk-kpi-packed-kg"),

    list: document.getElementById("pk-list"),
    detail: document.getElementById("pk-detail"),

    pendingCount: document.getElementById("pk-pending-count"),
    packedCount: document.getElementById("pk-packed-count"),
    sentCount: document.getElementById("pk-sent-count"),

    tabButtons: document.querySelectorAll(".pk-tab-btn"),
  };

  init();

  function init() {
    bindEvents();
    loadSummary();
    loadList();
  }

  function bindEvents() {
    els.tabButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        state.activeTab = btn.dataset.status;
        state.selectedBatchId = null;
        updateTabs();
        renderActiveList();
        clearDetailPanel();
      });
    });
  }

  async function loadSummary() {
    try {
      const res = await fetch(urls.summary, {
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });

      const data = await res.json();
      if (!data.success) return;

      const s = data.summary || {};
      els.kpiPendingLots.textContent = s.pending_lots ?? 0;
      els.kpiPackedToday.textContent = s.packed_today ?? 0;
      els.kpiPendingKg.textContent = formatNumber(s.pending_kg ?? 0);
      els.kpiPackedKg.textContent = formatNumber(s.packed_kg ?? 0);
    } catch (err) {
      console.error("Error cargando resumen:", err);
    }
  }

  async function loadList() {
    els.list.innerHTML = `
      <div class="rounded-xl border border-dashed border-[#e8ddd4] bg-[#fcf8f5] px-4 py-8 text-center text-sm text-[#7c5e4f]">
        Cargando lotes...
      </div>
    `;

    try {
      const res = await fetch(urls.list, {
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });

      const data = await res.json();

      if (!data.success) {
        els.list.innerHTML = `
          <div class="rounded-xl border border-red-200 bg-red-50 px-4 py-8 text-center text-sm text-red-600">
            No se pudo cargar la lista.
          </div>
        `;
        return;
      }

      state.rows = data.results || [];
      updateCountersFromRows();
      updateTabs();
      renderActiveList();
    } catch (err) {
      console.error("Error cargando lista:", err);
      els.list.innerHTML = `
        <div class="rounded-xl border border-red-200 bg-red-50 px-4 py-8 text-center text-sm text-red-600">
          Error al cargar lotes.
        </div>
      `;
    }
  }

  function updateCountersFromRows() {
    const pending = state.rows.filter(r => r.packing_status === "pending").length;
    const packed = state.rows.filter(r => r.packing_status === "packed").length;
    const sent = state.rows.filter(r => r.packing_status === "sent").length;

    els.pendingCount.textContent = pending;
    els.packedCount.textContent = packed;
    els.sentCount.textContent = sent;
  }

  function renderActiveList() {
    const filtered = state.rows.filter(row => row.packing_status === state.activeTab);

    if (!filtered.length) {
      const emptyText = {
        pending: "No hay lotes pendientes.",
        packed: "No hay lotes empacados.",
        sent: "No hay lotes enviados."
      };

      els.list.innerHTML = `
        <div class="rounded-xl border border-dashed border-[#e8ddd4] bg-[#fcf8f5] px-4 py-8 text-center text-sm text-[#7c5e4f]">
          ${emptyText[state.activeTab] || "No hay lotes."}
        </div>
      `;
      return;
    }

    els.list.innerHTML = filtered.map((row) => {
      const selected = String(state.selectedBatchId) === String(row.batch_id);
      const cardTheme = getCardThemeClasses(state.activeTab, selected);
      const pendingChip = renderPendingChip(row);

      return `
        <button
          type="button"
          class="btn-shine pk-open w-full text-left rounded-2xl border p-4 transition ${cardTheme}"
          data-batch-id="${row.batch_id}"
        >
          <div class="flex items-start justify-between gap-4">
            <div>
              <div class="text-base font-semibold text-[#2b1d16]">${escapeHtml(row.code)}</div>
              <div class="mt-1 text-sm text-[#6b4b3e]">${escapeHtml(row.provider?.name || "—")}</div>
            </div>
            ${badge(row.packing_status_label, row.packing_status)}
          </div>

          ${pendingChip}

          <div class="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div class="rounded-xl bg-[#f8f3ee] px-3 py-2">
              <div class="text-[11px] uppercase tracking-wide text-[#8a6a5a]">Peso</div>
              <div class="mt-1 font-semibold text-[#2b1d16]">${formatNumber(row.weight_kg)} kg</div>
            </div>

            <div class="rounded-xl bg-[#f8f3ee] px-3 py-2">
              <div class="text-[11px] uppercase tracking-wide text-[#8a6a5a]">Grado</div>
              <div class="mt-1 font-semibold text-[#2b1d16]">${row.grade ? `Grado ${row.grade}` : "—"}</div>
            </div>

            <div class="rounded-xl bg-[#f8f3ee] px-3 py-2">
              <div class="text-[11px] uppercase tracking-wide text-[#8a6a5a]">Fecha lote</div>
              <div class="mt-1 font-semibold text-[#2b1d16]">${escapeHtml(row.created_date || "—")}</div>
            </div>

            <div class="rounded-xl bg-[#f8f3ee] px-3 py-2">
              <div class="text-[11px] uppercase tracking-wide text-[#8a6a5a]">Empaque</div>
              <div class="mt-1 font-semibold text-[#2b1d16]">${row.packed_at || "—"}</div>
            </div>
          </div>
        </button>
      `;
    }).join("");

    document.querySelectorAll(".pk-open").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.selectedBatchId = btn.dataset.batchId;
        renderActiveList();
        openDetail(btn.dataset.batchId);
      });
    });
  }

  async function openDetail(batchId) {
    els.detail.innerHTML = `
      <div class="rounded-xl border border-dashed border-[#e8ddd4] bg-[#fcf8f5] px-4 py-8 text-center text-sm text-[#7c5e4f]">
        Cargando detalle...
      </div>
    `;

    try {
      const res = await fetch(itemUrl(urls.detailBase, batchId), {
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });

      const data = await res.json();
      if (!data.success) {
        els.detail.innerHTML = `
          <div class="rounded-xl border border-red-200 bg-red-50 px-4 py-8 text-center text-sm text-red-600">
            ${escapeHtml(data.message || "No se pudo cargar el detalle.")}
          </div>
        `;
        return;
      }

      renderDetail(data.detail);
    } catch (err) {
      console.error("Error cargando detalle:", err);
      els.detail.innerHTML = `
        <div class="rounded-xl border border-red-200 bg-red-50 px-4 py-8 text-center text-sm text-red-600">
          Error al cargar el detalle.
        </div>
      `;
    }
  }

  function renderDetail(detail) {
    const batch = detail.batch || {};
    const provider = detail.provider || {};
    const evaluation = detail.evaluation || {};
    const packing = detail.packing || {};

    els.detail.innerHTML = `
      <div class="space-y-4">
        <div class="rounded-2xl border border-[#eadfd7] bg-[#fcf8f5] p-4">
          <div class="text-base font-semibold text-[#2b1d16]">Información general</div>

          <div class="mt-4 space-y-2 text-sm">
            <div><span class="text-[#6b4b3e]">Código:</span> <span class="font-semibold text-[#2b1d16]">${escapeHtml(batch.code || "—")}</span></div>
            <div><span class="text-[#6b4b3e]">Proveedor:</span> <span class="font-semibold text-[#2b1d16]">${escapeHtml(provider.name || "—")}</span></div>
            <div><span class="text-[#6b4b3e]">Peso:</span> <span class="font-semibold text-[#2b1d16]">${formatNumber(batch.weight_kg || 0)} kg</span></div>
            <div><span class="text-[#6b4b3e]">Fecha:</span> <span class="font-semibold text-[#2b1d16]">${escapeHtml(batch.created_at || "—")}</span></div>
            <div><span class="text-[#6b4b3e]">Grado:</span> <span class="font-semibold text-[#2b1d16]">${evaluation.grade ? `Grado ${evaluation.grade}` : "—"}</span></div>
            <div><span class="text-[#6b4b3e]">Método:</span> <span class="font-semibold text-[#2b1d16]">${escapeHtml(evaluation.method_label || "—")}</span></div>
          </div>
        </div>

        <form id="pk-form" class="space-y-4">
          <input type="hidden" id="pk-batch-id" value="${batch.id || ""}" />

          <div>
            <label class="block text-xs font-semibold text-[#6b4b3e] mb-1">Estado de packing</label>
            <select id="pk-detail-status"
                    class="w-full rounded-lg px-3 py-2 bg-white border border-[#eadfd7] text-[#111]
                           focus:outline-none focus:ring-2 focus:ring-[#c9a893]">
              <option value="pending" ${packing.status === "pending" ? "selected" : ""}>Pendiente</option>
              <option value="packed" ${packing.status === "packed" ? "selected" : ""}>Empacado</option>
              <option value="sent" ${packing.status === "sent" ? "selected" : ""}>Enviado</option>
            </select>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div class="rounded-xl bg-[#f8f3ee] px-3 py-3">
              <div class="text-[11px] uppercase tracking-wide text-[#8a6a5a]">Fecha de empaque</div>
              <div class="mt-1 font-semibold text-[#2b1d16]">${packing.packed_at || "Se asigna automáticamente"}</div>
            </div>

            <div class="rounded-xl bg-[#f8f3ee] px-3 py-3">
              <div class="text-[11px] uppercase tracking-wide text-[#8a6a5a]">Fecha de envío</div>
              <div class="mt-1 font-semibold text-[#2b1d16]">${packing.sent_at || "Se asigna automáticamente"}</div>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-[#6b4b3e] mb-1">Observaciones</label>
            <textarea id="pk-detail-notes"
                      rows="4"
                      class="w-full rounded-lg px-3 py-2 bg-white border border-[#eadfd7] text-[#111]
                             focus:outline-none focus:ring-2 focus:ring-[#c9a893]"
                      placeholder="Observaciones opcionales...">${escapeHtml(packing.notes || "")}</textarea>
          </div>

          <div class="flex items-center gap-3">
            <button type="submit"
                    class="btn-shine px-4 py-2 rounded-lg bg-[#2b1d16] text-[#fbf7f2] font-semibold hover:opacity-95 transition">
              Guardar
            </button>

            <div id="pk-feedback" class="text-sm text-[#6b4b3e]"></div>
          </div>
        </form>
      </div>
    `;

    const form = document.getElementById("pk-form");

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      await saveDetail();
    });
  }

  async function saveDetail() {
    const batchId = document.getElementById("pk-batch-id")?.value;
    const feedback = document.getElementById("pk-feedback");

    if (!batchId) {
      const msg = "No se encontró el lote seleccionado.";
      if (feedback) {
        feedback.textContent = msg;
        feedback.className = "text-sm text-red-600";
      }
      if (window.fsToast) window.fsToast(msg, "error");
      return;
    }

    const statusEl = document.getElementById("pk-detail-status");
    const notesEl = document.getElementById("pk-detail-notes");

    const payload = {
      status: statusEl?.value || "pending",
      notes: notesEl?.value?.trim() || "",
    };

    const batchCodeText =
      document.querySelector("#pk-detail .font-semibold.text-\\[\\#2b1d16\\]")?.textContent?.trim() ||
      `#${batchId}`;

    if (feedback) {
      feedback.textContent = "Guardando...";
      feedback.className = "text-sm text-[#6b4b3e]";
    }

    try {
      const res = await fetch(itemUrl(urls.updateBase, batchId), {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
          "X-Requested-With": "XMLHttpRequest"
        },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        const msg = data.message || "No se pudo guardar.";
        if (feedback) {
          feedback.textContent = msg;
          feedback.className = "text-sm text-red-600";
        }
        if (window.fsToast) window.fsToast(msg, "error");
        return;
      }

      const successMsg = data.message || "Guardado correctamente.";
      if (feedback) {
        feedback.textContent = successMsg;
        feedback.className = "text-sm text-green-600";
      }

      const savedStatus = data.packing?.status || payload.status;
      let toastMsg = successMsg;

      if (savedStatus === "packed") {
        toastMsg = `Se empaquetó correctamente el lote ${batchCodeText}.`;
      } else if (savedStatus === "sent") {
        toastMsg = `Se envió correctamente el lote ${batchCodeText}.`;
      } else if (savedStatus === "pending") {
        toastMsg = `El lote ${batchCodeText} volvió a estado pendiente.`;
      }

      if (window.fsToast) window.fsToast(toastMsg, "success");

      animateCardExit(batchId);

      setTimeout(async () => {
        state.activeTab = savedStatus;
        state.selectedBatchId = null;
        updateTabs();
        clearDetailPanel();

        await loadSummary();
        await loadList();
        renderActiveList();
      }, 220);

    } catch (err) {
      console.error("Error guardando detalle:", err);
      const msg = "Error al guardar.";
      if (feedback) {
        feedback.textContent = msg;
        feedback.className = "text-sm text-red-600";
      }
      if (window.fsToast) window.fsToast(msg, "error");
    }
  }

  function animateCardExit(batchId) {
    const card = document.querySelector(`.pk-open[data-batch-id="${batchId}"]`);
    if (!card) return;

    card.style.transition = "opacity 0.22s ease, transform 0.22s ease";
    card.style.opacity = "0";
    card.style.transform = "translateX(12px) scale(0.98)";
  }

  function clearDetailPanel() {
    els.detail.innerHTML = `
      <div class="min-h-[220px] rounded-2xl border border-dashed border-[#e5d8cf] bg-[#fcf8f5]
                  flex items-center justify-center text-center px-6 text-sm text-[#7c5e4f]">
        Selecciona un lote de la lista.
      </div>
    `;
  }

  function updateTabs() {
    els.tabButtons.forEach((btn) => {
      const isActive = btn.dataset.status === state.activeTab;
      btn.classList.toggle("bg-[#2b1d16]", isActive);
      btn.classList.toggle("text-white", isActive);
      btn.classList.toggle("text-[#2b1d16]", !isActive);
    });
  }

  function getCardThemeClasses(status, selected = false) {
    let classes = "border-[#eadfd7] bg-[#fffdfb] hover:bg-[#fcf7f2]";

    if (status === "pending") {
      classes = "border-[#eadfd7] bg-[#fffdfb] hover:bg-[#fdf7ef]";
    } else if (status === "packed") {
      classes = "border-[#dce9dc] bg-[#fbfffb] hover:bg-[#f1fbf1]";
    } else if (status === "sent") {
      classes = "border-[#dbe6f3] bg-[#fbfdff] hover:bg-[#f2f7fd]";
    }

    if (selected) {
      if (status === "pending") {
        classes += " ring-2 ring-[#d7b892] shadow-[0_10px_28px_rgba(133,94,66,0.12)]";
      } else if (status === "packed") {
        classes += " ring-2 ring-[#9fd1a5] shadow-[0_10px_28px_rgba(80,130,90,0.12)]";
      } else if (status === "sent") {
        classes += " ring-2 ring-[#9db9e7] shadow-[0_10px_28px_rgba(70,110,180,0.12)]";
      }
    }

    return classes;
  }

  function renderPendingChip(row) {
    if (row.packing_status !== "pending" || row.pending_days === null) return "";

    let chipClasses = "bg-[#fff7ed] border-[#f0dcc2] text-[#9a6b2d]";

    if (row.pending_days >= 8) {
      chipClasses = "bg-[#fff1f2] border-[#f2c7cc] text-[#b54a57]";
    } else if (row.pending_days >= 3) {
      chipClasses = "bg-[#fff8e8] border-[#efd9a7] text-[#a1741d]";
    }

    return `
      <div class="mt-3 inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${chipClasses}">
        ${row.pending_days} día${row.pending_days === 1 ? "" : "s"} en pendiente
      </div>
    `;
  }

  function badge(label, status = "") {
    let classes = "bg-[#f6eee7] border-[#eadfd7] text-[#7a5645]";

    if (status === "packed") {
      classes = "bg-[#edf8ef] border-[#d7e9db] text-[#356846]";
    } else if (status === "sent") {
      classes = "bg-[#eef4fd] border-[#d8e4f5] text-[#446799]";
    }

    return `<span class="inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${classes}">${escapeHtml(label || "—")}</span>`;
  }

  function itemUrl(base, id) {
    return base.replace("/0/", `/${id}/`);
  }

  function formatNumber(value) {
    return new Intl.NumberFormat("es-MX", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 3
    }).format(Number(value || 0));
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function getCookie(name) {
    const cookieValue = document.cookie
      .split("; ")
      .find(row => row.startsWith(name + "="));
    return cookieValue ? decodeURIComponent(cookieValue.split("=")[1]) : null;
  }
});
