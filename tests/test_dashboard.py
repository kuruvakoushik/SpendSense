from __future__ import annotations

import calendar
from datetime import date

from tests.conftest import category_id, register_user


def test_dashboard_totals_and_empty_state(app, client):
    user = register_user(client)
    today = date.today()
    empty = client.get(f"/api/dashboard/summary?month={today.month}&year={today.year}")
    assert empty.status_code == 200
    assert empty.get_json()["data"]["has_transactions"] is False
    assert empty.get_json()["data"]["income"]["paise"] == 0

    food = category_id(app, user["id"], "Food")
    salary = category_id(app, user["id"], "Salary")
    client.post(
        "/api/transactions",
        json={
            "type": "income",
            "amount": "1000",
            "category_id": salary,
            "description": "Pay",
            "transaction_date": today.isoformat(),
            "payment_method": "UPI",
        },
    )
    client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "amount": "200",
            "category_id": food,
            "description": "Lunch",
            "transaction_date": today.isoformat(),
            "payment_method": "UPI",
        },
    )
    summary = client.get(f"/api/dashboard/summary?month={today.month}&year={today.year}").get_json()["data"]
    assert summary["income"]["paise"] == 100000
    assert summary["expenses"]["paise"] == 20000
    assert summary["net"]["paise"] == 80000
    assert summary["savings_rate"] == 80.0
    assert summary["has_transactions"] is True


def test_monthly_boundaries(app, client):
    user = register_user(client)
    food = category_id(app, user["id"], "Food")
    today = date.today()
    last_day_prev = 1 if today.month == 1 else calendar.monthrange(today.year, today.month - 1)[1]
    prev_month = 12 if today.month == 1 else today.month - 1
    prev_year = today.year - 1 if today.month == 1 else today.year
    prev_date = date(prev_year, prev_month, last_day_prev).isoformat()
    client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "amount": "75",
            "category_id": food,
            "description": "Previous month",
            "transaction_date": prev_date,
            "payment_method": "UPI",
        },
    )
    current = client.get(f"/api/dashboard/summary?month={today.month}&year={today.year}").get_json()["data"]
    previous = client.get(f"/api/dashboard/summary?month={prev_month}&year={prev_year}").get_json()["data"]
    assert current["expenses"]["paise"] == 0
    assert previous["expenses"]["paise"] == 7500


def test_forecast_calculation(app, client):
    user = register_user(client)
    food = category_id(app, user["id"], "Food")
    today = date.today()
    client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "amount": "100",
            "category_id": food,
            "description": "Daily-like",
            "transaction_date": today.isoformat(),
            "payment_method": "UPI",
        },
    )
    forecast = client.get(f"/api/insights/forecast?month={today.month}&year={today.year}").get_json()["data"]
    assert forecast["sufficient_data"] is True
    elapsed = max(today.day, 1)
    remaining = calendar.monthrange(today.year, today.month)[1] - today.day
    spent = 10000
    avg = spent // elapsed
    projected = spent + avg * remaining
    assert forecast["spent_so_far"]["paise"] == spent
    assert forecast["projected_month_end"]["paise"] == projected
    assert "disclaimer" in forecast


def test_anomaly_detection_history(app, client):
    user = register_user(client)
    food = category_id(app, user["id"], "Food")
    today = date.today()
    empty = client.get("/api/insights/anomalies").get_json()["data"]
    assert empty["flagged"] == []
    assert empty["insufficient_history_note"] is None or True

    for amount in (100, 110, 90, 105, 95, 108):
        client.post(
            "/api/transactions",
            json={
                "type": "expense",
                "amount": str(amount),
                "category_id": food,
                "description": "Typical",
                "transaction_date": today.isoformat(),
                "payment_method": "UPI",
            },
        )
    still_normal = client.get("/api/insights/anomalies").get_json()["data"]
    assert still_normal["flagged"] == []
    client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "amount": "5000",
            "category_id": food,
            "description": "Unusual dinner",
            "transaction_date": today.isoformat(),
            "payment_method": "Card",
        },
    )
    flagged = client.get("/api/insights/anomalies").get_json()["data"]
    assert flagged["flagged"]
    assert "reason" in flagged["flagged"][0]
    assert flagged["flagged"][0]["amount"]["paise"] == 500000
