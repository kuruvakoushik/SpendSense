"""Authentication API routes."""

from __future__ import annotations

from flask import Blueprint, g, request, session
from flask_wtf.csrf import generate_csrf

from server.auth import (
    hash_password,
    login_required,
    login_user,
    logout_user,
    seed_default_categories,
    verify_password,
)
from server.database import get_db
from server.http import fail, ok
from server.validators import (
    ValidationError,
    normalize_email,
    require_str,
    validate_full_name,
    validate_password,
)

bp = Blueprint("auth_api", __name__)


@bp.get("/csrf")
def csrf_token():
    return ok({"csrf_token": generate_csrf()})


@bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    try:
        full_name = validate_full_name(require_str(payload, "full_name", max_len=80))
        email = normalize_email(require_str(payload, "email", max_len=254))
        password = validate_password(payload.get("password", ""))
        confirm = payload.get("confirm_password", "")
        if password != confirm:
            raise ValidationError("Passwords do not match.", "confirm_password")
    except ValidationError as exc:
        return fail(exc.message, 400, "validation_error")

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        return fail("An account with this email already exists.", 409, "duplicate_email")

    try:
        cursor = db.execute(
            "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
            (full_name, email, hash_password(password)),
        )
        user_id = cursor.lastrowid
        seed_default_categories(user_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    login_user(user_id)
    user = db.execute(
        "SELECT id, full_name, email, currency, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return ok(dict(user), 201)


@bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    try:
        email = normalize_email(require_str(payload, "email", max_len=254))
        password = payload.get("password", "")
        if not isinstance(password, str) or not password:
            raise ValidationError("Password is required.", "password")
    except ValidationError as exc:
        return fail(exc.message, 400, "validation_error")

    db = get_db()
    user = db.execute(
        "SELECT id, full_name, email, password_hash, currency FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    if user is None or not verify_password(user["password_hash"], password):
        return fail("Email or password is incorrect.", 401, "invalid_credentials")

    login_user(user["id"])
    return ok(
        {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "currency": user["currency"],
        }
    )


@bp.post("/logout")
def logout():
    logout_user()
    return ok({"logged_out": True})


@bp.get("/me")
def me():
    if g.user is None:
        return fail("Please sign in to continue.", 401, "unauthenticated")
    return ok(
        {
            "id": g.user["id"],
            "full_name": g.user["full_name"],
            "email": g.user["email"],
            "currency": g.user["currency"],
            "csrf_token": generate_csrf(),
        }
    )


@bp.post("/change-password")
@login_required
def change_password():
    payload = request.get_json(silent=True) or {}
    current = payload.get("current_password", "")
    try:
        new_password = validate_password(payload.get("new_password", ""), field="new_password")
        confirm = payload.get("confirm_password", "")
        if new_password != confirm:
            raise ValidationError("Passwords do not match.", "confirm_password")
    except ValidationError as exc:
        return fail(exc.message, 400, "validation_error")

    db = get_db()
    row = db.execute("SELECT password_hash FROM users WHERE id = ?", (g.user["id"],)).fetchone()
    if not verify_password(row["password_hash"], current):
        return fail("Current password is incorrect.", 400, "invalid_password")
    if verify_password(row["password_hash"], new_password):
        return fail("Choose a password that is different from the current one.", 400, "validation_error")

    db.execute(
        "UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?",
        (hash_password(new_password), g.user["id"]),
    )
    db.commit()
    session.modified = True
    return ok({"updated": True})
