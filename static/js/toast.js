(() => {
  const AUTO_CLOSE_MS = 2600;   // duración en pantalla
  const ANIM_MS = 220;

  function closeToast(el) {
    if (!el || el.dataset.closing === "1") return;
    el.dataset.closing = "1";
    el.classList.add("hide");
    setTimeout(() => el.remove(), ANIM_MS);
  }

  function scheduleAll() {
    // Agarra cualquier toast de tu sistema
    const toasts = document.querySelectorAll(".fs-toast, .toast, [data-toast]");
    if (!toasts.length) return;

    toasts.forEach((el, i) => {
      setTimeout(() => closeToast(el), AUTO_CLOSE_MS + i * 120);
    });
  }

  // Cerrar al click
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-toast-close]");
    if (btn) {
      const toast = btn.closest(".fs-toast, .toast, [data-toast]");
      closeToast(toast);
    }
  });

  // Cuando carga la página
  document.addEventListener("DOMContentLoaded", scheduleAll);

  // Si Django renderiza mensajes y luego cambia por navegación, igual los cierra
  setTimeout(scheduleAll, 100);
})();
