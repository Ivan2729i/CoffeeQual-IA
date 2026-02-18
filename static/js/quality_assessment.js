(function () {
  const marker = document.getElementById("qualityHomeMarker");
  if (!marker) return;

  const form = document.getElementById("qaForm");
  if (!form) return;

  const fileInput = document.getElementById("qaFile");
  const btn = document.getElementById("qaBtn");
  const status = document.getElementById("qaStatus");
  const result = document.getElementById("qaResult");

  const gradeEl = document.getElementById("qaGrade");
  const scoreEl = document.getElementById("qaScore");
  const primaryEl = document.getElementById("qaPrimary");
  const secondaryEl = document.getElementById("qaSecondary");
  const totalEl = document.getElementById("qaTotal");
  const countsEl = document.getElementById("qaCounts");
  const qaUrlInput = document.getElementById("qaUrl");

  if (!fileInput || !btn || !status || !result || !countsEl) return;

  function getCSRFToken() {
    const inp = form.querySelector('input[name="csrfmiddlewaretoken"]');
    return inp ? inp.value : "";
  }

  function showStatus(msg, isError = false) {
    status.textContent = msg;
    status.classList.remove("hidden");
    status.classList.toggle("text-red-600", isError);
    status.classList.toggle("text-gray-700", !isError);
  }

  function hideStatus() {
    status.classList.add("hidden");
  }

  function clearResult() {
    result.classList.add("hidden");
    countsEl.innerHTML = "";
  }

  function safeNum(x) {
    const n = Number(x);
    return Number.isFinite(n) ? n : 0;
  }

  function flattenCounts(counts) {
    const p = (counts && counts.primary) ? counts.primary : {};
    const s = (counts && counts.secondary) ? counts.secondary : {};

    const all = [];
    for (const [k, v] of Object.entries(p)) all.push({ group: "Primario", name: k, qty: safeNum(v) });
    for (const [k, v] of Object.entries(s)) all.push({ group: "Secundario", name: k, qty: safeNum(v) });

    return all.sort((a, b) => b.qty - a.qty);
  }

  function renderCounts(counts) {
    const items = flattenCounts(counts);

    if (!items.length) {
      countsEl.innerHTML = `
        <div class="col-span-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-500">
          Sin defectos detectados.
        </div>
      `;
      return;
    }

    countsEl.innerHTML = items.map((it) => `
      <div class="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-3 py-2">
        <div class="min-w-0">
          <p class="text-[11px] text-gray-500">${it.group}</p>
          <p class="text-sm text-gray-700 truncate">${it.name}</p>
        </div>
        <span class="text-sm font-semibold text-gray-900">${it.qty}</span>
      </div>
    `).join("");
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearResult();

    const f = fileInput.files?.[0];
    if (!f) {
      showStatus("Selecciona una imagen primero.", true);
      return;
    }

    btn.disabled = true;
    showStatus("Analizando...", false);

    const fd = new FormData();
    fd.append("image", f);

    try {
      const qaUrl = qaUrlInput?.value || "/dashboard/quality/evaluate/";

      const res = await fetch(qaUrl, {
        method: "POST",
        headers: { "X-CSRFToken": getCSRFToken() },
        body: fd,
        credentials: "same-origin",
      });

      const contentType = res.headers.get("content-type") || "";
      const raw = await res.text();

      if (!contentType.includes("application/json")) {
        throw new Error(`No es JSON. Status ${res.status}. Empieza con: ${raw.slice(0, 80)}`);
      }

      const data = JSON.parse(raw);
      if (!res.ok || !data.ok) throw new Error(data.error || "Error al evaluar.");

      const counts = data.counts || { primary: {}, secondary: {} };

      gradeEl.textContent = data.grade ?? "-";
      scoreEl.textContent = data.score ?? "-";
      primaryEl.textContent = data.primary_total ?? 0;
      secondaryEl.textContent = data.secondary_total ?? 0;
      totalEl.textContent = data.defects_total ?? (safeNum(data.primary_total) + safeNum(data.secondary_total));

      renderCounts(counts);

      hideStatus();
      result.classList.remove("hidden");
    } catch (err) {
      showStatus(err?.message || "Error desconocido.", true);
    } finally {
      btn.disabled = false;
    }
  });
})();
