from __future__ import annotations

from datetime import date

from tests.conftest import category_id, register_user


def test_create_transaction(app, client):
    user = register_user(client)
    food = category_id(app, user["id"], "Food")
    response = client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "amount": "120.50",
            "category_id": food,
            "description": "Lunch",
            "transaction_date": date.today().isoformat(),
            "payment_method": "UPI",
        },
    )
    assert response.status_code == 201
    body = response.get_json()["data"]
    assert body["amount"]["paise"] == 12050
    assert body["amount"]["formatted"].startswith("₹")


def test_reject_invalid_amount(app, client):
    user = register_user(client)
    food = category_id(app, user["id"], "Food")
    response = client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "amount": "0",
            "category_id": food,
            "description": "Bad",
            "transaction_date": date.today().isoformat(),
            "payment_method": "UPI",
        },
    )
    assert response.status_code == 400


def test_edit_and_delete_transaction(app, client):
    user = register_user(client)
    food = category_id(app, user["id"], "Food")
    created = client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "amount": "80",
            "category_id": food,
            "description": "Snack",
            "transaction_date": date.today().isoformat(),
            "payment_method": "Cash",
        },
    ).get_json()["data"]
    updated = client.put(
        f"/api/transactions/{created['id']}",
        json={"amount": "90.25", "description": "Evening snack"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["data"]["amount"]["paise"] == 9025
    deleted = client.delete(f"/api/transactions/{created['id']}")
    assert deleted.status_code == 200
    missing = client.get(f"/api/transactions/{created['id']}")
    assert missing.status_code == 404


def test_filter_transactions(app, client):
    user = register_user(client)
    food = category_id(app, user["id"], "Food")
    salary = category_id(app, user["id"], "Salary")
    client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "amount": "50",
            "category_id": food,
            "description": "Coffee",
            "transaction_date": date.today().isoformat(),
            "payment_method": "UPI",
        },
    )
    client.post(
        "/api/transactions",
        json={
            "type": "income",
            "amount": "1000",
            "category_id": salary,
            "description": "Stipend",
            "transaction_date": date.today().isoformat(),
            "payment_method": "UPI",
        },
    )
    filtered = client.get("/api/transactions?type=expense&q=Coffee")
    assert filtered.status_code == 200
    items = filtered.get_json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["description"] == "Coffee"


def test_reject_invalid_filters(app, client):
    register_user(client)
    assert client.get("/api/transactions?type=transfer").status_code == 400
    assert client.get("/api/transactions?sort=raw_sql").status_code == 400
    assert client.get("/api/transactions?start=2026-05-01&end=2026-04-01").status_code == 400


def test_reject_other_user_transaction(app, client):
    first = register_user(client, email="one@example.com")
    food = category_id(app, first["id"], "Food")
    created = client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "amount": "40",
            "category_id": food,
            "description": "Private",
            "transaction_date": date.today().isoformat(),
            "payment_method": "UPI",
        },
    ).get_json()["data"]
    client.post("/api/auth/logout", json={})
    register_user(client, email="two@example.com", full_name="Sam Rao")
    response = client.get(f"/api/transactions/{created['id']}")
    assert response.status_code == 404
    update = client.put(f"/api/transactions/{created['id']}", json={"amount": "1"})
    assert update.status_code == 404


def test_prevent_category_type_mismatch(app, client):
    user = register_user(client)
    salary = category_id(app, user["id"], "Salary")
    response = client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "amount": "10",
            "category_id": salary,
            "description": "Mismatch",
            "transaction_date": date.today().isoformat(),
            "payment_method": "UPI",
        },
    )
    assert response.status_code == 400
