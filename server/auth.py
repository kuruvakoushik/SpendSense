"""Authentication helpers and default-category seeding."""

from __future__ import annotations

from functools import wraps

from flask import g, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash

from server.database import get_db

DEFAULT_CATEGORIES = (
    ("Food", "expense", "#0F766E", "food"),
    ("Transport", "expense", "#1D4ED8", "transport"),
    ("Education", "expense", "#7C3AED", "education"),
    ("Shopping", "expense", "#C2410C", "shopping"),
    ("Healthcare", "expense", "#BE123C", "health"),
    ("Entertainment", "expense", "#A21CAF", "entertainment"),
    ("Bills", "expense", "#B45309", "bills"),
    ("Housing", "expense", "#334155", "housing"),
    ("Travel", "expense", "#0E7490", "travel"),
    ("Other", "expense", "#475569", "other"),
    ("Salary", "income", "#15803D", "salary"),
    ("Freelance", "income", "#047857", "freelance"),
    ("Other Income", "income", "#0F766E", "wallet"),
)


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def login_user(user_id: int) -> None:
    session.clear()
    session["user_id"] = user_id
    session.permanent = True


def logout_user() -> None:
    session.clear()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    db = get_db()
    return db.execute(
        "SELECT id, full_name, email, currency, created_at, updated_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()


def seed_default_categories(user_id: int) -> None:
    db = get_db()
    db.executemany(
        """
        INSERT INTO categories (user_id, name, type, color, icon, is_system)
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        [(user_id, name, type_, color, icon) for name, type_, color, icon in DEFAULT_CATEGORIES],
    )


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "data": None,
                        "error": {"code": "unauthenticated", "message": "Please sign in to continue."},
                    }
                ),
                401,
            )
        return view(*args, **kwargs)

    return wrapped
