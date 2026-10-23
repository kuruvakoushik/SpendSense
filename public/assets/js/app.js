const App = (() => {
  function qs(selector, root = document) {
    return root.querySelector(selector);
  }

  function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function toast(message, type = "info") {
    let host = qs("#toast-host");
    if (!host) {
      host = document.createElement("div");
      host.id = "toast-host";
      host.className = "toast-host";
      document.body.appendChild(host);
    }
    const item = document.createElement("div");
    item.className = `toast toast-${type}`;
    item.setAttribute("role", "status");
    item.textContent = message;
    host.appendChild(item);
    setTimeout(() => item.classList.add("show"), 10);
    setTimeout(() => {
      item.classList.remove("show");
      setTimeout(() => item.remove(), 250);
    }, 3600);
  }

  function setText(el, value) {
    if (el) el.textContent = value == null ? "" : String(value);
  }

  function show(el, visible) {
    if (!el) return;
    el.hidden = !visible;
  }

  function monthInputValue(year, month) {
    return `${year}-${String(month).padStart(2, "0")}`;
  }

  function parseMonthInput(value) {
    const [year, month] = (value || "").split("-").map(Number);
    return { year, month };
  }

  function currentMonthValue() {
    const now = new Date();
    return monthInputValue(now.getFullYear(), now.getMonth() + 1);
  }

  function localISODate(value = new Date()) {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, "0");
    const day = String(value.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function field(form, name) {
    return form.elements.namedItem(name);
  }

  function setBusy(button, busy, label) {
    if (!button) return;
    if (busy) {
      button.dataset.label = button.textContent;
      button.disabled = true;
      button.textContent = label || "Please wait…";
    } else {
      button.disabled = false;
      button.textContent = button.dataset.label || button.textContent;
    }
  }

  async function requireUser() {
    try {
      return await Api.get("/api/auth/me");
    } catch (_error) {
      return null;
    }
  }

  async function logout() {
    try {
      await Api.post("/api/auth/logout", {});
    } catch (_error) {
      /* still leave the session on the client */
    }
    Api.clearCsrf();
    window.location.href = "/login";
  }

  function bindLayout(user) {
    qsa("[data-user-name]").forEach((el) => setText(el, user?.full_name || "Account"));
    qsa("[data-user-email]").forEach((el) => setText(el, user?.email || ""));
    const path = window.location.pathname.replace(/\.html$/, "");
    qsa(".nav-link").forEach((link) => {
      const href = link.getAttribute("href");
      if (href && (path === href || path === `${href}.html` || (path === "/" && href === "/dashboard"))) {
        link.classList.add("active");
        link.setAttribute("aria-current", "page");
      }
    });
    const toggle = qs("[data-nav-toggle]");
    const sidebar = qs("#sidebar");
    if (toggle && sidebar) {
      toggle.addEventListener("click", () => {
        sidebar.classList.toggle("open");
      });
    }
    qsa("[data-logout]").forEach((el) => el.addEventListener("click", (event) => {
      event.preventDefault();
      logout();
    }));
  }

  function paymentMethods() {
    return ["UPI", "Cash", "Card", "Net Banking", "Wallet", "Other"];
  }

  function fillSelect(select, items, valueKey, labelKey, placeholder) {
    if (!select) return;
    select.innerHTML = "";
    if (placeholder) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = placeholder;
      select.appendChild(option);
    }
    items.forEach((item) => {
      const option = document.createElement("option");
      option.value = item[valueKey];
      option.textContent = item[labelKey];
      select.appendChild(option);
    });
  }

  function openModal(id) {
    const modal = qs(`#${id}`);
    if (!modal) return;
    modal.hidden = false;
    const focusable = modal.querySelector("input, select, button, textarea");
    if (focusable) focusable.focus();
  }

  function closeModal(id) {
    const modal = qs(`#${id}`);
    if (modal) modal.hidden = true;
  }

  document.addEventListener("click", (event) => {
    const closer = event.target.closest("[data-close-modal]");
    if (closer) {
      closeModal(closer.getAttribute("data-close-modal"));
    }
  });

  return {
    qs,
    qsa,
    toast,
    setText,
    show,
    monthInputValue,
    parseMonthInput,
    currentMonthValue,
    localISODate,
    field,
    setBusy,
    requireUser,
    logout,
    bindLayout,
    paymentMethods,
    fillSelect,
    openModal,
    closeModal,
  };
})();
