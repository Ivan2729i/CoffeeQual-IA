(() => {
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-pw-toggle]");
    if (!btn) return;

    const targetId = btn.getAttribute("data-target");
    const input = document.getElementById(targetId);
    if (!input) return;

    const openIcon = btn.querySelector("[data-icon='open']");
    const closedIcon = btn.querySelector("[data-icon='closed']");

    const isPassword = input.type === "password";
    input.type = isPassword ? "text" : "password";

    if (openIcon && closedIcon) {
      openIcon.classList.toggle("hidden", !isPassword);
      closedIcon.classList.toggle("hidden", isPassword);
    }

    btn.setAttribute("aria-label", isPassword ? "Ocultar contraseña" : "Mostrar contraseña");
  });
})();
