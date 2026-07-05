(() => {
  const key = "ai-manager-theme";
  const saved = localStorage.getItem(key);
  if (saved) {
    document.documentElement.setAttribute("data-bs-theme", saved);
  }
  const button = document.getElementById("theme-toggle");
  if (!button) {
    return;
  }
  button.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-bs-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-bs-theme", next);
    localStorage.setItem(key, next);
  });
})();

