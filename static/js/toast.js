(() => {
  const AUTO_CLOSE_MS = 2600;
  const ANIM_MS = 220;

  function closeToast(el) {
    if (!el || el.dataset.closing === "1") return;
    el.dataset.closing = "1";
    el.classList.add("hide");
    setTimeout(() => el.remove(), ANIM_MS);
  }

  function scheduleAll() {
    const toasts = document.querySelectorAll(".fs-toast, .toast, [data-toast]");
    if (!toasts.length) return;

    toasts.forEach((el, i) => {
      setTimeout(() => closeToast(el), AUTO_CLOSE_MS + i * 120);
    });
  }

  function ensureToastRoot() {
    let root = document.getElementById("fs-toast-root");

    if (!root) {
      root = document.createElement("div");
      root.id = "fs-toast-root";
      root.className = "fixed inset-0 pointer-events-none z-[9999] grid place-items-start px-4 pt-6";

      const stack = document.createElement("div");
      stack.className = "w-full max-w-md space-y-3 pointer-events-auto";

      root.appendChild(stack);
      document.body.appendChild(root);
    }

    let stack = root.firstElementChild;
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "w-full max-w-md space-y-3 pointer-events-auto";
      root.appendChild(stack);
    }

    return stack;
  }

  function getToastMeta(type) {
    if (type === "success") return { title: "Éxito", color: "#22c55e" };
    if (type === "error") return { title: "Error", color: "#ef4444" };
    if (type === "warning") return { title: "Aviso", color: "#f59e0b" };
    return { title: "Info", color: "#60a5fa" };
  }

  function showToast(message, type = "info") {
    const stack = ensureToastRoot();
    const meta = getToastMeta(type);

    const toast = document.createElement("div");
    toast.className = "fs-toast card-fs px-4 py-3 border border-card-border";
    toast.setAttribute("data-toast", "1");

    toast.innerHTML = `
      <div class="flex items-start gap-3">
        <div class="mt-1 h-2.5 w-2.5 rounded-full" style="background:${meta.color};"></div>
        <div class="text-sm flex-1">
          <div class="font-semibold">${meta.title}</div>
          <div class="text-text-muted">${escapeHtml(message)}</div>
        </div>
        <button type="button" data-toast-close class="ml-2 text-xs opacity-70 hover:opacity-100">✕</button>
      </div>
    `;

    stack.appendChild(toast);
    setTimeout(() => closeToast(toast), AUTO_CLOSE_MS);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  window.fsToast = showToast;

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-toast-close]");
    if (btn) {
      const toast = btn.closest(".fs-toast, .toast, [data-toast]");
      closeToast(toast);
    }
  });

  document.addEventListener("DOMContentLoaded", scheduleAll);
  setTimeout(scheduleAll, 100);
})();