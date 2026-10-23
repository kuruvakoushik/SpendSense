"""Profile API routes."""

from __future__ import annotations

from flask import Blueprint, g, request

from server.auth import login_required
from server.database import get_db
from server.http import fail, ok
from server.validators import ValidationError, require_str, validate_full_name

bp = Blueprint("profile_api", __name__)


@bp.get("")
@login_required
def get_profile():
    return ok(
        {
            "id": g.user["id"],
            "full_name": g.user["full_name"],
            "email": g.user["email"],
            "currency": g.user["currency"],
            "created_at": g.user["created_at"],
            "updated_at": g.user["updated_at"],
        }
    )


@bp.put("")
@login_required
def update_profile():
    payload = request.get_json(silent=True) or {}
    db = get_db()
    try:
        full_name = validate_full_name(require_str(payload, "full_name", max_len=80))
        db.execute(
            "UPDATE users SET full_name = ?, updated_at = datetime('now') WHERE id = ?",
            (full_name, g.user["id"]),
        )
        db.commit()
        row = db.execute(
            "SELECT id, full_name, email, currency, created_at, updated_at FROM users WHERE id = ?",
            (g.user["id"],),
        ).fetchone()
        return ok(dict(row))
    except ValidationError as exc:
        db.rollback()
        return fail(exc.message, 400, "validation_error")
