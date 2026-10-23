let categories = [];

function period() {
  return App.parseMonthInput(document.getElementById("month-picker").value);
}

async function load() {
  const { year, month } = period();
  const data = await Api.get(`/api/budgets?year=${year}&month=${month}`);
  const host = document.getElementById("budget-list");
  host.replaceChildren();
  App.show(document.getElementById("budget-empty"), data.items.length === 0);
  data.items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "panel";
    const title = document.createElement("h2");
    title.textContent = item.category_name;
    const meta = document.createElement("p");
    meta.textContent = `${item.spent.formatted} spent · ${item.remaining.formatted} remaining · ${item.utilization_percent}%`;
    const bar = document.createElement("div");
    bar.className = `progress ${item.status}`;
    const fill = document.createElement("span");
    fill.style.width = `${Math.min(item.utilization_percent, 100)}%`;
    bar.appendChild(fill);
    const actions = document.createElement("div");
    actions.style.marginTop = "12px";
    const edit = document.createElement("button");
    edit.className = "btn btn-sm btn-secondary";
    edit.type = "button";
    edit.textContent = "Edit";
    edit.addEventListener("click", () => openForm(item));
    const del = document.createElement("button");
    del.className = "btn btn-sm btn-danger";
    del.type = "button";
    del.textContent = "Delete";
    del.addEventListener("click", async () => {
      if (!window.confirm("Delete this budget?")) return;
      try {
        await Api.del(`/api/budgets/${item.id}`);
        App.toast("Budget deleted.", "success");
        await load();
      } catch (error) {
        App.toast(error.message, "error");
      }
    });
    actions.append(edit, del);
    card.append(title, meta, bar, actions);
    host.appendChild(card);
  });
}

function openForm(item) {
  const form = document.getElementById("budget-form");
  document.getElementById("budget-title").textContent = item ? "Edit budget" : "Add budget";
  App.field(form, "id").value = item ? item.id : "";
  App.fillSelect(form.category_id, categories.filter((cat) => cat.type === "expense"), "id", "name", "Select category");
  form.category_id.value = item ? item.category_id : "";
  form.monthly_limit.value = item ? item.limit.rupees : "";
  App.openModal("budget-modal");
}

document.addEventListener("DOMContentLoaded", async () => {
  const user = await App.requireUser();
  if (!user) return;
  App.bindLayout(user);
  const picker = document.getElementById("month-picker");
  picker.value = App.currentMonthValue();
  picker.addEventListener("change", () => load().catch((error) => App.toast(error.message, "error")));
  document.getElementById("add-budget").addEventListener("click", () => openForm(null));
  document.getElementById("budget-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    const { year, month } = period();
    const payload = {
      category_id: Number(form.category_id.value),
      monthly_limit: form.monthly_limit.value,
      month,
      year,
    };
    const button = form.querySelector("button[type=submit]");
    App.setBusy(button, true, "Saving…");
    try {
      const budgetId = App.field(form, "id").value;
      if (budgetId) {
        await Api.put(`/api/budgets/${budgetId}`, payload);
      } else {
        await Api.post("/api/budgets", payload);
      }
      App.closeModal("budget-modal");
      App.toast("Budget saved.", "success");
      await load();
    } catch (error) {
      App.toast(error.message, "error");
    } finally {
      App.setBusy(button, false);
    }
  });
  try {
    categories = await Api.get("/api/categories");
    await load();
  } catch (error) {
    App.toast(error.message, "error");
  }
});
