// ---- Tema claro/oscuro ----
(function () {
  let t = "light";
  try { t = localStorage.getItem("tema") || "light"; } catch (e) {}
  document.documentElement.setAttribute("data-bs-theme", t);
})();

function actualizarIconoTema() {
  const dark = document.documentElement.getAttribute("data-bs-theme") === "dark";
  document.querySelectorAll(".theme-toggle i").forEach(i => {
    i.className = dark ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
  });
}

document.addEventListener("DOMContentLoaded", () => {
  actualizarIconoTema();
  document.querySelectorAll(".theme-toggle").forEach(b => b.addEventListener("click", () => {
    const next = document.documentElement.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-bs-theme", next);
    try { localStorage.setItem("tema", next); } catch (e) {}
    actualizarIconoTema();
    document.dispatchEvent(new Event("tema-cambiado"));
  }));

  // Menú móvil
  const side = document.getElementById("sidebar");
  document.querySelectorAll(".menu-toggle").forEach(b => b.addEventListener("click", () => side.classList.toggle("open")));

  // Toasts
  document.querySelectorAll(".toast").forEach(el => new bootstrap.Toast(el).show());

  // Confirmaciones con modal
  const modalEl = document.getElementById("confirmModal");
  const modal = new bootstrap.Modal(modalEl);
  let pendiente = null;
  document.addEventListener("click", e => {
    const el = e.target.closest("button[data-confirm], a[data-confirm]");
    if (!el || el.dataset.ok) return;
    e.preventDefault();
    abrirConfirmacion(el.dataset.confirm, () => {
      el.dataset.ok = "1";
      if (el.tagName === "A") location.href = el.href; else if (el.form) el.form.requestSubmit(el);
    });
  });
  document.addEventListener("submit", e => {
    const f = e.target;
    if (f.dataset.confirm && !f.dataset.ok) {
      e.preventDefault();
      abrirConfirmacion(f.dataset.confirm, () => { f.dataset.ok = "1"; f.requestSubmit(e.submitter || undefined); });
      return;
    }
    if (f.method.toLowerCase() === "post" && !f.hasAttribute("data-no-overlay")) {
      document.getElementById("overlay").classList.add("show");
    }
  }, true);
  function abrirConfirmacion(texto, cb) {
    document.getElementById("confirmText").textContent = texto;
    pendiente = cb;
    modal.show();
  }
  document.getElementById("confirmOk").addEventListener("click", () => {
    modal.hide();
    if (pendiente) pendiente();
  });
  window.addEventListener("pageshow", () => document.getElementById("overlay").classList.remove("show"));
});
