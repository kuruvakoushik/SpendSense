from __future__ import annotations

from datetime import date

from tests.conftest import category_id, register_user


def test_create_update_and_duplicate_budget(app, client):
    user = register_user(client)
    food = category_id(app, user["id"], "Food")
    today = date.today()
    created = client.post(
        "/api/budgets",
        json={"category_id": food, "monthly_limit": "8000", "month": today.month, "year": today.year},
    )
    assert created.status_code == 201
    duplicate = client.post(
        "/api/budgets",
        json={"category_id": food, "monthly_limit": "9000", "month": today.month, "year": today.year},
    )
    assert duplicate.status_code == 400
    budget_id = created.get_json()["data"]["id"]
    updated = client.put(f"/api/budgets/{budget_id}", json={"monthly_limit": "8500"})
    assert updated.status_code == 200
    assert updated.get_json()["data"]["limit"]["paise"] == 850000


def test_budget_spent_recalculates(app, client):
    user = register_user(client)
    food = category_id(app, user["id"], "Food")
    today = date.today()
    client.post(
        "/api/budgets",
        json={"category_id": food, "monthly_limit": "1000", "month": today.month, "year": today.year},
    )
    client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "amount": "250.00",
            "category_id": food,
            "description": "Groceries",
            "transaction_date": today.isoformat(),
            "payment_method": "UPI",
        },
    )
    listed = client.get(f"/api/budgets?month={today.month}&year={today.year}")
    item = listed.get_json()["data"]["items"][0]
    assert item["spent"]["paise"] == 25000
    assert item["remaining"]["paise"] == 75000
    assert item["utilization_percent"] == 25.0
    tx = client.get("/api/transactions").get_json()["data"]["items"][0]
    client.delete(f"/api/transactions/{tx['id']}")
    listed = client.get(f"/api/budgets?month={today.month}&year={today.year}")
    item = listed.get_json()["data"]["items"][0]
    assert item["spent"]["paise"] == 0
    assert item["remaining"]["paise"] == 100000
