function renderList(targetId, items) {
  const host = document.getElementById(targetId);
  host.replaceChildren();
  items.forEach((item) => {
    const row = document.createElement("div");
    row.style.cssText = "display:flex;justify-content:space-between;align-items:center;gap:8px;padding:10px 0;border-bottom:1px solid var(--line)";
    const left = document.createElement("div");
    const swatch = document.createElement("span");
    swatch.className = "cat-swatch";
    swatch.style.background = item.color;
    const name = document.createElement("strong");
    name.textContent = item.name;
    const meta = document.createElement("div");
    meta.className = "muted";
    meta.textContent = item.is_system ? `Default · ${item.usage_count} transactions` : `Custom · ${item.usage_count} transactions`;
    left.append(swatch, name, meta);
    const actions = document.createElement("div");
    const edit = document.createElement("button");
    edit.className = "btn btn-sm btn-secondary";
    edit.type = "button";
    edit.textContent = "Edit";
    edit.addEventListener("click", () => openForm(item));
    actions.appendChild(edit);
    if (!item.is_system) {
      const del = document.createElement("button");
      del.className = "btn btn-sm btn-danger";
      del.type = "button";
      del.textContent = "Delete";
      del.addEventListener("click", () => deleteCategory(item));
      actions.appendChild(del);
    }
    row.append(left, actions);
    host.appendChild(row);
  });
}

function openForm(item) {
  const form = document.getElementById("cat-form");
  document.getElementById("cat-title").textContent = item ? "Edit category" : "Add category";
  App.field(form, "id").value = item ? item.id : "";
  App.field(form, "name").value = item ? item.name : "";
  form.type.value = item ? item.type : "expense";
  form.color.value = item ? item.color : "#0F766E";
  form.icon.value = item ? item.icon : "other";
  form.type.disabled = Boolean(item && item.is_system);
  App.openModal("cat-modal");
}

async function deleteCategory(item) {
  if (!window.confirm(`Delete category “${item.name}”?`)) return;
  try {
    await Api.del(`/api/categories/${item.id}`);
    App.toast("Category deleted.", "success");
    await load();
  } catch (error) {
    App.toast(error.message, "error");
  }
}

async function load() {
  const items = await Api.get("/api/categories");
  renderList("expense-cats", items.filter((item) => item.type === "expense"));
  renderList("income-cats", items.filter((item) => item.type === "income"));
}

document.addEventListener("DOMContentLoaded", async () => {
  const user = await App.requireUser();
  if (!user) return;
  App.bindLayout(user);
  document.getElementById("add-cat").addEventListener("click", () => openForm(null));
  document.getElementById("cat-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    const payload = {
      name: App.field(form, "name").value,
      type: form.type.value,
      color: form.color.value,
      icon: form.icon.value,
    };
    const button = form.querySelector("button[type=submit]");
    App.setBusy(button, true, "Saving…");
    try {
      const categoryId = App.field(form, "id").value;
      if (categoryId) {
        await Api.put(`/api/categories/${categoryId}`, payload);
      } else {
        await Api.post("/api/categories", payload);
      }
      App.closeModal("cat-modal");
      App.toast("Category saved.", "success");
      await load();
    } catch (error) {
      App.toast(error.message, "error");
    } finally {
      App.setBusy(button, false);
      form.type.disabled = false;
    }
  });
  try {
    await load();
  } catch (error) {
    App.toast(error.message, "error");
  }
});
