"""Category API routes."""

from __future__ import annotations

from flask import Blueprint, g, request

from server.auth import login_required
from server.database import get_db
from server.http import fail, ok
from server.services.finance import serialize_category
from server.validators import (
    MAX_NAME_LEN,
    ValidationError,
    parse_color,
    parse_icon,
    parse_type,
    require_str,
)

bp = Blueprint("categories_api", __name__)


@bp.get("")
@login_required
def list_categories():
    db = get_db()
    rows = db.execute(
        """
        SELECT c.*,
               (SELECT COUNT(*) FROM transactions t WHERE t.category_id = c.id) AS usage_count
        FROM categories c
        WHERE c.user_id = ?
        ORDER BY c.type, c.name
        """,
        (g.user["id"],),
    ).fetchall()
    items = []
    for row in rows:
        item = serialize_category(row)
        item["usage_count"] = row["usage_count"]
        items.append(item)
    return ok(items)


@bp.post("")
@login_required
def create_category():
    payload = request.get_json(silent=True) or {}
    db = get_db()
    try:
        name = require_str(payload, "name", max_len=MAX_NAME_LEN)
        type_ = parse_type(payload.get("type"))
        color = parse_color(payload.get("color", "#0F766E"))
        icon = parse_icon(payload.get("icon", "other"))
        existing = db.execute(
            "SELECT id FROM categories WHERE user_id = ? AND name = ? AND type = ?",
            (g.user["id"], name, type_),
        ).fetchone()
        if existing:
            raise ValidationError("A category with this name already exists for this type.", "name")
        cursor = db.execute(
            """
            INSERT INTO categories (user_id, name, type, color, icon, is_system)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (g.user["id"], name, type_, color, icon),
        )
        db.commit()
        row = db.execute("SELECT * FROM categories WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return ok(serialize_category(row), 201)
    except ValidationError as exc:
        db.rollback()
        return fail(exc.message, 400, "validation_error")


@bp.put("/<int:category_id>")
@login_required
def update_category(category_id: int):
    db = get_db()
    row = db.execute(
        "SELECT * FROM categories WHERE id = ? AND user_id = ?",
        (category_id, g.user["id"]),
    ).fetchone()
    if row is None:
        return fail("Category not found.", 404, "not_found")
    payload = request.get_json(silent=True) or {}
    try:
        name = require_str(payload, "name", max_len=MAX_NAME_LEN) if "name" in payload else row["name"]
        color = parse_color(payload["color"]) if "color" in payload else row["color"]
        icon = parse_icon(payload.get("icon", row["icon"]))
        if row["is_system"] and "type" in payload and payload["type"] != row["type"]:
            raise ValidationError("System category types cannot be changed.", "type")
        type_ = row["type"]
        if not row["is_system"] and "type" in payload:
            type_ = parse_type(payload.get("type"))
            used = db.execute(
                "SELECT COUNT(*) AS n FROM transactions WHERE category_id = ?",
                (category_id,),
            ).fetchone()["n"]
            if used and type_ != row["type"]:
                raise ValidationError("Cannot change type while transactions use this category.", "type")
        duplicate = db.execute(
            "SELECT id FROM categories WHERE user_id = ? AND name = ? AND type = ? AND id != ?",
            (g.user["id"], name, type_, category_id),
        ).fetchone()
        if duplicate:
            raise ValidationError("A category with this name already exists for this type.", "name")
        db.execute(
            """
            UPDATE categories SET name = ?, type = ?, color = ?, icon = ?
            WHERE id = ? AND user_id = ?
            """,
            (name, type_, color, icon, category_id, g.user["id"]),
        )
        db.commit()
        updated = db.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
        return ok(serialize_category(updated))
    except ValidationError as exc:
        db.rollback()
        return fail(exc.message, 400, "validation_error")


@bp.delete("/<int:category_id>")
@login_required
def delete_category(category_id: int):
    db = get_db()
    row = db.execute(
        "SELECT * FROM categories WHERE id = ? AND user_id = ?",
        (category_id, g.user["id"]),
    ).fetchone()
    if row is None:
        return fail("Category not found.", 404, "not_found")
    if row["is_system"]:
        return fail("Default categories cannot be deleted.", 400, "system_category")
    used = db.execute(
        "SELECT COUNT(*) AS n FROM transactions WHERE category_id = ?",
        (category_id,),
    ).fetchone()["n"]
    if used:
        return fail(
            "This category still has transactions. Reassign or delete those transactions first.",
            409,
            "category_in_use",
        )
    budgeted = db.execute(
        "SELECT COUNT(*) AS n FROM budgets WHERE category_id = ?",
        (category_id,),
    ).fetchone()["n"]
    if budgeted:
        return fail("This category still has budgets. Remove those budgets first.", 409, "category_in_use")
    db.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (category_id, g.user["id"]))
    db.commit()
    return ok({"deleted": True, "id": category_id})
