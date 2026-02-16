(() => {
  const btn = document.getElementById("profileMenuBtn");
  const menu = document.getElementById("profileMenu");
  if (!btn || !menu) return;

  const closeMenu = () => menu.classList.add("hidden");
  const toggleMenu = () => menu.classList.toggle("hidden");

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleMenu();
  });

  // click fuera
  document.addEventListener("click", () => closeMenu());

  // ESC
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeMenu();
  });
})();
