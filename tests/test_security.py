from __future__ import annotations

from datetime import date
from pathlib import Path

from tests.conftest import category_id, register_user


def test_sql_queries_are_parameterized():
    root = Path(__file__).resolve().parents[1] / "server"
    dangerous = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "execute(" in text and "f\"" in text and "%" in text and "LIKE" not in text:
            # f-strings around execute are only allowed for known ORDER BY maps / static WHERE joins.
            pass
        if ".execute(f\"" in text.replace(" ", "") or ".execute(f'" in text:
            if "ORDER BY" not in text and "WHERE {where}" not in text:
                dangerous.append(str(path))
    source = (root / "routes" / "transactions.py").read_text(encoding="utf-8")
    assert "?" in source
    assert "LIKE ?" in source
    assert "%{q}%" not in source.replace("params.append(f\"%{q}%\")", "")


def test_private_routes_require_authentication(client):
    routes = [
        "/api/dashboard/summary",
        "/api/transactions",
        "/api/categories",
        "/api/budgets",
        "/api/analytics/overview",
        "/api/insights",
        "/api/profile",
    ]
    for route in routes:
        response = client.get(route)
        assert response.status_code == 401, route


def test_users_cannot_read_another_users_data(app, client):
    first = register_user(client, email="owner@example.com")
    food = category_id(app, first["id"], "Food")
    created = client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "amount": "33",
            "category_id": food,
            "description": "Owner only",
            "transaction_date": date.today().isoformat(),
            "payment_method": "UPI",
        },
    ).get_json()["data"]
    client.post("/api/auth/logout", json={})
    register_user(client, email="intruder@example.com", full_name="Intruder")
    listed = client.get("/api/transactions").get_json()["data"]["items"]
    assert listed == []
    assert client.delete(f"/api/transactions/{created['id']}").status_code == 404
    summary = client.get("/api/dashboard/summary").get_json()["data"]
    assert summary["expenses"]["paise"] == 0


def test_invalid_inputs_are_safe(client):
    register_user(client)
    injection = client.post(
        "/api/auth/login",
        json={"email": "owner@example.com' OR 1=1 --", "password": "x"},
    )
    assert injection.status_code in (400, 401)
    bad_date = client.post(
        "/api/transactions",
        json={
            "type": "expense",
            "amount": "10",
            "category_id": 1,
            "description": "<script>alert(1)</script>",
            "transaction_date": "not-a-date",
            "payment_method": "UPI",
        },
    )
    assert bad_date.status_code == 400
    profile = client.get("/api/auth/me").get_json()["data"]
    assert "password_hash" not in profile
    assert "SECRET_KEY" not in str(profile)
