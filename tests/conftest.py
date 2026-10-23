from __future__ import annotations

import pytest

from server.app import create_app
from server.config import TestConfig
from server.database import get_db


@pytest.fixture
def app(tmp_path):
    class LocalTestConfig(TestConfig):
        DATABASE_PATH = str(tmp_path / "spendsense-test.db")

    application = create_app(LocalTestConfig)
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


def register_user(client, email="alex@example.com", password="Secret123", full_name="Alex Kumar"):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": full_name,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["data"]


def category_id(app, user_id, name):
    with app.app_context():
        row = get_db().execute(
            "SELECT id FROM categories WHERE user_id = ? AND name = ?",
            (user_id, name),
        ).fetchone()
        return row["id"]
