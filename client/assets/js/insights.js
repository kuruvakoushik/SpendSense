async function load() {
  const { year, month } = App.parseMonthInput(document.getElementById("month-picker").value);
  const [insights, forecast, anomalies] = await Promise.all([
    Api.get(`/api/insights?year=${year}&month=${month}`),
    Api.get(`/api/insights/forecast?year=${year}&month=${month}`),
    Api.get("/api/insights/anomalies"),
  ]);

  const list = document.getElementById("insight-list");
  list.replaceChildren();
  insights.forEach((item) => {
    const card = document.createElement("article");
    card.className = `insight ${item.severity}`;
    const title = document.createElement("strong");
    title.textContent = item.title;
    const detail = document.createElement("p");
    detail.textContent = item.detail;
    card.append(title, detail);
    list.appendChild(card);
  });

  const box = document.getElementById("forecast-box");
  box.replaceChildren();
  if (!forecast.sufficient_data) {
    const p = document.createElement("p");
    p.textContent = forecast.message;
    box.appendChild(p);
  } else {
    const lines = [
      `Spent so far: ${forecast.spent_so_far.formatted}`,
      `Average daily: ${forecast.average_daily.formatted}`,
      `Elapsed days: ${forecast.elapsed_days} of ${forecast.days_in_month}`,
      `Run-rate estimate: ${forecast.projected_month_end.formatted}`,
    ];
    if (forecast.blended_estimate) {
      lines.push(`Blended estimate: ${forecast.blended_estimate.formatted}`);
    }
    lines.forEach((text) => {
      const p = document.createElement("p");
      p.textContent = text;
      box.appendChild(p);
    });
    const explain = document.createElement("p");
    explain.className = "footnote";
    explain.textContent = forecast.explanation;
    const disclaimer = document.createElement("p");
    disclaimer.className = "footnote";
    disclaimer.textContent = forecast.disclaimer;
    box.append(explain, disclaimer);
  }

  const anomalyHost = document.getElementById("anomaly-list");
  anomalyHost.replaceChildren();
  const note = document.createElement("p");
  note.className = "footnote";
  note.textContent = anomalies.disclaimer;
  anomalyHost.appendChild(note);
  if (anomalies.insufficient_history_note) {
    const extra = document.createElement("p");
    extra.className = "muted";
    extra.textContent = anomalies.insufficient_history_note;
    anomalyHost.appendChild(extra);
  }
  if (!anomalies.flagged.length) {
    const p = document.createElement("p");
    p.textContent = "No unusual expenses were flagged with the current history.";
    anomalyHost.appendChild(p);
  } else {
    anomalies.flagged.forEach((item) => {
      const card = document.createElement("article");
      card.className = "insight warning";
      const title = document.createElement("strong");
      title.textContent = `${item.amount.formatted} · ${item.category_name} · ${item.transaction_date}`;
      const detail = document.createElement("p");
      detail.textContent = item.reason;
      card.append(title, detail);
      anomalyHost.appendChild(card);
    });
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const user = await App.requireUser();
  if (!user) return;
  App.bindLayout(user);
  const picker = document.getElementById("month-picker");
  picker.value = App.currentMonthValue();
  picker.addEventListener("change", () => load().catch((error) => App.toast(error.message, "error")));
  try {
    await load();
  } catch (error) {
    App.toast(error.message, "error");
  }
});
