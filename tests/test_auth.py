from __future__ import annotations

from server.database import get_db
from tests.conftest import register_user


def test_register_success(client):
    data = register_user(client)
    assert data["email"] == "alex@example.com"
    assert "password" not in data
    assert "password_hash" not in data


def test_duplicate_registration_rejected(client):
    register_user(client)
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Alex Kumar",
            "email": "alex@example.com",
            "password": "Secret123",
            "confirm_password": "Secret123",
        },
    )
    assert response.status_code == 409


def test_login_success_and_me(client):
    register_user(client)
    client.post("/api/auth/logout", json={})
    response = client.post(
        "/api/auth/login",
        json={"email": "alex@example.com", "password": "Secret123"},
    )
    assert response.status_code == 200
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.get_json()["data"]["email"] == "alex@example.com"


def test_invalid_password_rejected(client):
    register_user(client)
    client.post("/api/auth/logout", json={})
    response = client.post(
        "/api/auth/login",
        json={"email": "alex@example.com", "password": "Wrong999"},
    )
    assert response.status_code == 401
    assert "incorrect" in response.get_json()["error"]["message"].lower()


def test_logout_clears_session(client):
    register_user(client)
    client.post("/api/auth/logout", json={})
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_protected_route_requires_auth(client):
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 401


def test_password_is_hashed(app, client):
    user = register_user(client)
    with app.app_context():
        row = get_db().execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (user["id"],),
        ).fetchone()
        assert row["password_hash"] != "Secret123"
        assert row["password_hash"].startswith("scrypt:") or row["password_hash"].startswith("pbkdf2:")
