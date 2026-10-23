let trendChart;
let catChart;
let categories = [];

function destroyChart(chart) {
  if (chart) chart.destroy();
}

async function loadDashboard() {
  const picker = document.getElementById("month-picker");
  const { year, month } = App.parseMonthInput(picker.value);
  const summary = await Api.get(`/api/dashboard/summary?year=${year}&month=${month}`);
  const recent = await Api.get("/api/dashboard/recent-transactions");

  App.setText(document.getElementById("stat-income"), summary.income.formatted);
  App.setText(document.getElementById("stat-expense"), summary.expenses.formatted);
  App.setText(document.getElementById("stat-net"), summary.net.formatted);
  App.setText(
    document.getElementById("stat-save"),
    summary.savings_rate == null ? "—" : `${summary.savings_rate}%`
  );
  App.show(document.getElementById("empty-state"), !summary.has_transactions);

  const tbody = document.getElementById("recent-body");
  tbody.replaceChildren();
  if (!recent.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 3;
    cell.textContent = "No transactions yet.";
    row.appendChild(cell);
    tbody.appendChild(row);
  } else {
    recent.forEach((item) => {
      const row = document.createElement("tr");
      const dateCell = document.createElement("td");
      dateCell.textContent = item.transaction_date;
      const details = document.createElement("td");
      details.textContent = `${item.category_name} · ${item.description || item.payment_method}`;
      const amount = document.createElement("td");
      amount.textContent = `${item.type === "income" ? "+" : "−"} ${item.amount.formatted}`;
      row.append(dateCell, details, amount);
      tbody.appendChild(row);
    });
  }

  const budgetBox = document.getElementById("budget-overview");
  budgetBox.replaceChildren();
  if (!summary.budgets.length) {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "No budgets this month.";
    budgetBox.appendChild(p);
  } else {
    summary.budgets.forEach((budget) => {
      const wrap = document.createElement("div");
      wrap.style.marginBottom = "12px";
      const title = document.createElement("div");
      title.textContent = `${budget.category_name}: ${budget.spent.formatted} of ${budget.limit.formatted}`;
      const bar = document.createElement("div");
      bar.className = `progress ${budget.status}`;
      const fill = document.createElement("span");
      fill.style.width = `${Math.min(budget.utilization_percent, 100)}%`;
      bar.appendChild(fill);
      wrap.append(title, bar);
      budgetBox.appendChild(wrap);
    });
  }

  destroyChart(trendChart);
  destroyChart(catChart);
  const trendCtx = document.getElementById("trend-chart");
  trendChart = new Chart(trendCtx, {
    type: "bar",
    data: {
      labels: summary.trends.map((item) => item.label),
      datasets: [
        { label: "Income", data: summary.trends.map((item) => item.income.rupees), backgroundColor: "#0F766E" },
        { label: "Expenses", data: summary.trends.map((item) => item.expenses.rupees), backgroundColor: "#B42318" },
      ],
    },
    options: { responsive: true, plugins: { legend: { position: "bottom" } } },
  });

  const labels = summary.expense_breakdown.map((item) => item.name);
  catChart = new Chart(document.getElementById("cat-chart"), {
    type: "doughnut",
    data: {
      labels: labels.length ? labels : ["No expenses"],
      datasets: [{
        data: labels.length ? summary.expense_breakdown.map((item) => item.total.rupees) : [1],
        backgroundColor: labels.length ? summary.expense_breakdown.map((item) => item.color) : ["#E4DDD0"],
      }],
    },
    options: { responsive: true, plugins: { legend: { position: "bottom" } } },
  });
}

async function loadCategories() {
  categories = await Api.get("/api/categories");
  refreshCategorySelect(document.querySelector("#quick-form [name=category_id]"), document.querySelector("#quick-form [name=type]").value);
}

function refreshCategorySelect(select, type) {
  App.fillSelect(
    select,
    categories.filter((item) => item.type === type),
    "id",
    "name",
    "Select category"
  );
}

document.addEventListener("DOMContentLoaded", async () => {
  const user = await App.requireUser();
  if (!user) return;
  App.bindLayout(user);
  const picker = document.getElementById("month-picker");
  picker.value = App.currentMonthValue();
  picker.addEventListener("change", () => loadDashboard().catch((error) => App.toast(error.message, "error")));
  const methodSelect = document.querySelector("#quick-form [name=payment_method]");
  App.fillSelect(methodSelect, App.paymentMethods().map((name) => ({ id: name, name })), "id", "name");
  document.querySelector("#quick-form [name=transaction_date]").value = App.localISODate();
  document.querySelector("#quick-form [name=type]").addEventListener("change", (event) => {
    refreshCategorySelect(document.querySelector("#quick-form [name=category_id]"), event.target.value);
  });
  document.getElementById("quick-add").addEventListener("click", async () => {
    await loadCategories();
    App.openModal("tx-modal");
  });
  document.getElementById("load-demo").addEventListener("click", async () => {
    if (!window.confirm("Add labeled sample income, expenses, and two budgets for this month?")) return;
    try {
      await Api.post("/api/dashboard/demo-data", { confirm: true });
      App.toast("Demo data added.", "success");
      await loadDashboard();
    } catch (error) {
      App.toast(error.message, "error");
    }
  });
  document.getElementById("quick-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    const button = form.querySelector("button[type=submit]");
    App.setBusy(button, true, "Saving…");
    try {
      await Api.post("/api/transactions", {
        type: form.type.value,
        amount: form.amount.value,
        category_id: Number(form.category_id.value),
        description: form.description.value,
        transaction_date: form.transaction_date.value,
        payment_method: form.payment_method.value,
      });
      App.closeModal("tx-modal");
      form.reset();
      form.transaction_date.value = App.localISODate();
      App.toast("Transaction saved.", "success");
      await loadDashboard();
    } catch (error) {
      App.toast(error.message, "error");
    } finally {
      App.setBusy(button, false);
    }
  });
  try {
    await loadCategories();
    await loadDashboard();
  } catch (error) {
    App.toast(error.message, "error");
  }
});
