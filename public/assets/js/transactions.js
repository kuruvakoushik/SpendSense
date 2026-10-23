let page = 1;
let categories = [];
let pendingDeleteId = null;

async function refreshCategories() {
  categories = await Api.get("/api/categories");
  const filter = document.getElementById("filter-category");
  App.fillSelect(filter, categories, "id", "name", "All categories");
  refreshFormCategories();
}

function refreshFormCategories() {
  const form = document.getElementById("tx-form");
  App.fillSelect(
    form.category_id,
    categories.filter((item) => item.type === form.type.value),
    "id",
    "name",
    "Select category"
  );
}

function queryString() {
  const form = document.getElementById("filter-form");
  const params = new URLSearchParams();
  if (form.type.value) params.set("type", form.type.value);
  if (form.category_id.value) params.set("category_id", form.category_id.value);
  if (form.start.value) params.set("start", form.start.value);
  if (form.end.value) params.set("end", form.end.value);
  if (form.q.value) params.set("q", form.q.value);
  params.set("sort", form.sort.value);
  params.set("page", String(page));
  params.set("per_page", "10");
  return params.toString();
}

async function loadTransactions() {
  const data = await Api.get(`/api/transactions?${queryString()}`);
  App.setText(document.getElementById("filtered-total"), data.filtered_total.formatted);
  App.setText(document.getElementById("page-label"), `Page ${data.page}`);
  const tbody = document.getElementById("tx-body");
  tbody.replaceChildren();
  App.show(document.getElementById("tx-empty"), data.items.length === 0);
  data.items.forEach((item) => {
    const row = document.createElement("tr");
    const cells = [
      item.transaction_date,
      item.type,
      item.category_name,
      item.description || "—",
      item.payment_method,
      item.amount.formatted,
    ];
    cells.forEach((value, index) => {
      const td = document.createElement("td");
      if (index === 1) {
        const badge = document.createElement("span");
        badge.className = `badge badge-${item.type}`;
        badge.textContent = item.type;
        td.appendChild(badge);
      } else {
        td.textContent = value;
      }
      row.appendChild(td);
    });
    const actions = document.createElement("td");
    const edit = document.createElement("button");
    edit.className = "btn btn-sm btn-secondary";
    edit.type = "button";
    edit.textContent = "Edit";
    edit.addEventListener("click", () => openEdit(item));
    const del = document.createElement("button");
    del.className = "btn btn-sm btn-danger";
    del.type = "button";
    del.textContent = "Delete";
    del.addEventListener("click", () => {
      pendingDeleteId = item.id;
      App.openModal("delete-modal");
    });
    actions.append(edit, del);
    row.appendChild(actions);
    tbody.appendChild(row);
  });
  document.getElementById("prev-page").disabled = data.page <= 1;
  document.getElementById("next-page").disabled = data.page * data.per_page >= data.total_count;
}

function openEdit(item) {
  const form = document.getElementById("tx-form");
  document.getElementById("tx-modal-title").textContent = item ? "Edit transaction" : "Add transaction";
  App.field(form, "id").value = item ? item.id : "";
  form.type.value = item ? item.type : "expense";
  refreshFormCategories();
  form.amount.value = item ? item.amount.rupees : "";
  form.category_id.value = item ? item.category_id : "";
  form.payment_method.value = item ? item.payment_method : "UPI";
  form.transaction_date.value = item ? item.transaction_date : App.localISODate();
  form.description.value = item ? item.description : "";
  App.openModal("tx-modal");
}

document.addEventListener("DOMContentLoaded", async () => {
  const user = await App.requireUser();
  if (!user) return;
  App.bindLayout(user);
  const form = document.getElementById("tx-form");
  App.fillSelect(form.payment_method, App.paymentMethods().map((name) => ({ id: name, name })), "id", "name");
  form.type.addEventListener("change", refreshFormCategories);
  document.getElementById("add-tx").addEventListener("click", () => openEdit(null));
  document.getElementById("filter-form").addEventListener("submit", (event) => {
    event.preventDefault();
    page = 1;
    loadTransactions().catch((error) => App.toast(error.message, "error"));
  });
  document.getElementById("prev-page").addEventListener("click", () => {
    page = Math.max(1, page - 1);
    loadTransactions().catch((error) => App.toast(error.message, "error"));
  });
  document.getElementById("next-page").addEventListener("click", () => {
    page += 1;
    loadTransactions().catch((error) => App.toast(error.message, "error"));
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    const payload = {
      type: form.type.value,
      amount: form.amount.value,
      category_id: Number(form.category_id.value),
      description: form.description.value,
      transaction_date: form.transaction_date.value,
      payment_method: form.payment_method.value,
    };
    App.setBusy(button, true, "Saving…");
    try {
      const transactionId = App.field(form, "id").value;
      if (transactionId) {
        await Api.put(`/api/transactions/${transactionId}`, payload);
      } else {
        await Api.post("/api/transactions", payload);
      }
      App.closeModal("tx-modal");
      App.toast("Transaction saved.", "success");
      await loadTransactions();
    } catch (error) {
      App.toast(error.message, "error");
    } finally {
      App.setBusy(button, false);
    }
  });
  document.getElementById("confirm-delete").addEventListener("click", async () => {
    if (!pendingDeleteId) return;
    try {
      await Api.del(`/api/transactions/${pendingDeleteId}`);
      pendingDeleteId = null;
      App.closeModal("delete-modal");
      App.toast("Transaction deleted.", "success");
      await loadTransactions();
    } catch (error) {
      App.toast(error.message, "error");
    }
  });
  try {
    await refreshCategories();
    await loadTransactions();
  } catch (error) {
    App.toast(error.message, "error");
  }
});
