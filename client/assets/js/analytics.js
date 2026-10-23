let trendChart;
let catChart;
let dailyChart;

function destroy(chart) {
  if (chart) chart.destroy();
}

function monthStart() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

async function load() {
  const form = document.getElementById("range-form");
  const overview = await Api.get(`/api/analytics/overview?start=${form.start.value}&end=${form.end.value}`);
  const trends = await Api.get("/api/analytics/monthly-trends");
  App.setText(document.getElementById("a-income"), overview.income.formatted);
  App.setText(document.getElementById("a-expense"), overview.expenses.formatted);
  App.setText(document.getElementById("a-net"), overview.net.formatted);
  const empty = overview.income.paise === 0 && overview.expenses.paise === 0;
  App.show(document.getElementById("a-empty"), empty);

  destroy(trendChart);
  destroy(catChart);
  destroy(dailyChart);
  trendChart = new Chart(document.getElementById("trend-chart"), {
    type: "line",
    data: {
      labels: trends.map((item) => item.label),
      datasets: [
        { label: "Income", data: trends.map((item) => item.income.rupees), borderColor: "#0F766E", tension: 0.2 },
        { label: "Expenses", data: trends.map((item) => item.expenses.rupees), borderColor: "#B42318", tension: 0.2 },
        { label: "Net", data: trends.map((item) => item.net.rupees), borderColor: "#1D4ED8", tension: 0.2 },
      ],
    },
    options: { responsive: true, plugins: { legend: { position: "bottom" } } },
  });
  catChart = new Chart(document.getElementById("cat-chart"), {
    type: "bar",
    data: {
      labels: overview.category_breakdown.length ? overview.category_breakdown.map((item) => item.name) : ["No data"],
      datasets: [{
        label: "Expenses",
        data: overview.category_breakdown.length ? overview.category_breakdown.map((item) => item.total.rupees) : [0],
        backgroundColor: overview.category_breakdown.length ? overview.category_breakdown.map((item) => item.color) : ["#E4DDD0"],
      }],
    },
    options: { indexAxis: "y", responsive: true, plugins: { legend: { display: false } } },
  });
  dailyChart = new Chart(document.getElementById("daily-chart"), {
    type: "bar",
    data: {
      labels: overview.daily_expenses.length ? overview.daily_expenses.map((item) => item.date) : ["No data"],
      datasets: [{
        label: "Daily expenses",
        data: overview.daily_expenses.length ? overview.daily_expenses.map((item) => item.total.rupees) : [0],
        backgroundColor: "#0F766E",
      }],
    },
    options: { responsive: true, plugins: { legend: { display: false } } },
  });

  const top = document.getElementById("top-cats");
  top.replaceChildren();
  if (!overview.category_breakdown.length) {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "No category totals for this range.";
    top.appendChild(p);
  } else {
    overview.category_breakdown.slice(0, 5).forEach((item) => {
      const p = document.createElement("p");
      p.textContent = `${item.name}: ${item.total.formatted}`;
      top.appendChild(p);
    });
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const user = await App.requireUser();
  if (!user) return;
  App.bindLayout(user);
  const form = document.getElementById("range-form");
  form.start.value = monthStart();
  form.end.value = today();
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    load().catch((error) => App.toast(error.message, "error"));
  });
  try {
    await load();
  } catch (error) {
    App.toast(error.message, "error");
  }
});
