"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Default configuration for local development."""

    IS_VERCEL = os.environ.get("VERCEL") == "1"
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-secret-change-me")
    APP_ENV = os.environ.get("APP_ENV", "production" if IS_VERCEL else "development").strip().lower()
    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH",
        "/tmp/spendsense.db" if IS_VERCEL else "instance/spendsense.db",
    )
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get(
        "SESSION_COOKIE_SECURE", "1" if IS_VERCEL else "0"
    ) == "1"
    SESSION_COOKIE_NAME = "spendsense_session"
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    WTF_CSRF_HEADERS = ["X-CSRFToken", "X-CSRF-Token"]
    JSON_SORT_KEYS = False


class TestConfig(Config):
    """Isolated configuration used by pytest."""

    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key-not-for-production"
    SESSION_COOKIE_SECURE = False


def resolve_database_path(raw_path: str) -> Path:
    """Resolve a database path relative to the project root when needed."""
    path = Path(raw_path)
    if not path.is_absolute():
        path = BASE_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

