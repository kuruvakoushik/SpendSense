"""Budget API routes."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, g, request

from server.auth import login_required
from server.database import get_db
from server.http import fail, ok
from server.services.finance import budget_spent, category_owned, serialize_budget
from server.validators import ValidationError, parse_amount_to_paise, parse_month_year, parse_positive_int

bp = Blueprint("budgets_api", __name__)


def _period():
    today = date.today()
    month = request.args.get("month", today.month)
    year = request.args.get("year", today.year)
    return parse_month_year(month, year)


@bp.get("")
@login_required
def list_budgets():
    try:
        month, year = _period()
    except ValidationError as exc:
        return fail(exc.message, 400, "validation_error")
    db = get_db()
    rows = db.execute(
        """
        SELECT b.*, c.name AS category_name, c.color AS category_color
        FROM budgets b
        JOIN categories c ON c.id = b.category_id
        WHERE b.user_id = ? AND b.month = ? AND b.year = ?
        ORDER BY c.name
        """,
        (g.user["id"], month, year),
    ).fetchall()
    items = [
        serialize_budget(row, budget_spent(g.user["id"], row["category_id"], year, month))
        for row in rows
    ]
    return ok({"month": month, "year": year, "items": items})


@bp.post("")
@login_required
def create_budget():
    payload = request.get_json(silent=True) or {}
    db = get_db()
    try:
        category_id = parse_positive_int(payload.get("category_id"), "category_id")
        month, year = parse_month_year(payload.get("month"), payload.get("year"))
        limit_paise = parse_amount_to_paise(payload.get("monthly_limit"))
        category = category_owned(g.user["id"], category_id, "expense")
        if category is None:
            raise ValidationError("Select an expense category you own.", "category_id")
        duplicate = db.execute(
            """
            SELECT id FROM budgets
            WHERE user_id = ? AND category_id = ? AND month = ? AND year = ?
            """,
            (g.user["id"], category_id, month, year),
        ).fetchone()
        if duplicate:
            raise ValidationError("A budget already exists for this category and month.", "category_id")
        cursor = db.execute(
            """
            INSERT INTO budgets (user_id, category_id, monthly_limit_paise, month, year)
            VALUES (?, ?, ?, ?, ?)
            """,
            (g.user["id"], category_id, limit_paise, month, year),
        )
        db.commit()
        row = db.execute(
            """
            SELECT b.*, c.name AS category_name, c.color AS category_color
            FROM budgets b JOIN categories c ON c.id = b.category_id
            WHERE b.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
        return ok(serialize_budget(row, budget_spent(g.user["id"], category_id, year, month)), 201)
    except ValidationError as exc:
        db.rollback()
        return fail(exc.message, 400, "validation_error")


@bp.put("/<int:budget_id>")
@login_required
def update_budget(budget_id: int):
    db = get_db()
    row = db.execute(
        """
        SELECT b.*, c.name AS category_name, c.color AS category_color
        FROM budgets b JOIN categories c ON c.id = b.category_id
        WHERE b.id = ? AND b.user_id = ?
        """,
        (budget_id, g.user["id"]),
    ).fetchone()
    if row is None:
        return fail("Budget not found.", 404, "not_found")
    payload = request.get_json(silent=True) or {}
    try:
        limit_paise = (
            parse_amount_to_paise(payload.get("monthly_limit"))
            if "monthly_limit" in payload
            else row["monthly_limit_paise"]
        )
        month, year = (
            parse_month_year(payload.get("month"), payload.get("year"))
            if "month" in payload or "year" in payload
            else (row["month"], row["year"])
        )
        category_id = (
            parse_positive_int(payload.get("category_id"), "category_id")
            if "category_id" in payload
            else row["category_id"]
        )
        if category_owned(g.user["id"], category_id, "expense") is None:
            raise ValidationError("Select an expense category you own.", "category_id")
        duplicate = db.execute(
            """
            SELECT id FROM budgets
            WHERE user_id = ? AND category_id = ? AND month = ? AND year = ? AND id != ?
            """,
            (g.user["id"], category_id, month, year, budget_id),
        ).fetchone()
        if duplicate:
            raise ValidationError("A budget already exists for this category and month.", "category_id")
        db.execute(
            """
            UPDATE budgets
            SET category_id = ?, monthly_limit_paise = ?, month = ?, year = ?, updated_at = datetime('now')
            WHERE id = ? AND user_id = ?
            """,
            (category_id, limit_paise, month, year, budget_id, g.user["id"]),
        )
        db.commit()
        updated = db.execute(
            """
            SELECT b.*, c.name AS category_name, c.color AS category_color
            FROM budgets b JOIN categories c ON c.id = b.category_id
            WHERE b.id = ?
            """,
            (budget_id,),
        ).fetchone()
        return ok(serialize_budget(updated, budget_spent(g.user["id"], category_id, year, month)))
    except ValidationError as exc:
        db.rollback()
        return fail(exc.message, 400, "validation_error")


@bp.delete("/<int:budget_id>")
@login_required
def delete_budget(budget_id: int):
    db = get_db()
    row = db.execute(
        "SELECT id FROM budgets WHERE id = ? AND user_id = ?",
        (budget_id, g.user["id"]),
    ).fetchone()
    if row is None:
        return fail("Budget not found.", 404, "not_found")
    db.execute("DELETE FROM budgets WHERE id = ? AND user_id = ?", (budget_id, g.user["id"]))
    db.commit()
    return ok({"deleted": True, "id": budget_id})
