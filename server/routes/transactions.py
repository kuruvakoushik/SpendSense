"""Transaction CRUD API."""

from __future__ import annotations

from flask import Blueprint, g, request

from server.auth import login_required
from server.database import get_db
from server.http import fail, ok
from server.services.finance import category_owned, serialize_transaction
from server.validators import (
    MAX_DESCRIPTION_LEN,
    ValidationError,
    clamp_limit,
    format_inr_from_paise,
    parse_amount_to_paise,
    parse_iso_date,
    parse_payment_method,
    parse_positive_int,
    parse_type,
    require_str,
)

bp = Blueprint("transactions_api", __name__)


def _row(tx_id: int):
    db = get_db()
    return db.execute(
        """
        SELECT t.*, c.name AS category_name, c.color AS category_color, c.icon AS category_icon
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE t.id = ? AND t.user_id = ?
        """,
        (tx_id, g.user["id"]),
    ).fetchone()


def _payload_to_record(payload: dict, *, partial: bool = False, existing=None) -> dict:
    data = {}
    if not partial or "type" in payload:
        data["type"] = parse_type(payload.get("type"))
    else:
        data["type"] = existing["type"]

    if not partial or "amount" in payload:
        data["amount_paise"] = parse_amount_to_paise(payload.get("amount"))
    else:
        data["amount_paise"] = existing["amount_paise"]

    if not partial or "category_id" in payload:
        data["category_id"] = parse_positive_int(payload.get("category_id"), "category_id")
    else:
        data["category_id"] = existing["category_id"]

    if not partial or "description" in payload:
        data["description"] = require_str(payload, "description", max_len=MAX_DESCRIPTION_LEN, required=False)
    else:
        data["description"] = existing["description"]

    if not partial or "transaction_date" in payload:
        data["transaction_date"] = parse_iso_date(payload.get("transaction_date", ""))
    else:
        data["transaction_date"] = existing["transaction_date"]

    if not partial or "payment_method" in payload:
        data["payment_method"] = parse_payment_method(payload.get("payment_method"))
    else:
        data["payment_method"] = existing["payment_method"]

    category = category_owned(g.user["id"], data["category_id"], data["type"])
    if category is None:
        raise ValidationError("Category not found or does not match the transaction type.", "category_id")
    return data


@bp.get("")
@login_required
def list_transactions():
    db = get_db()
    page = clamp_limit(request.args.get("page"), 1, 10000)
    per_page = clamp_limit(request.args.get("per_page"), 10, 50)
    tx_type = request.args.get("type")
    category_id = request.args.get("category_id")
    q = (request.args.get("q") or "").strip()
    start = request.args.get("start")
    end = request.args.get("end")
    sort = request.args.get("sort", "date_desc")

    if tx_type and tx_type not in ("income", "expense"):
        return fail("Type filter must be income or expense.", 400, "validation_error")
    if len(q) > 80:
        return fail("Search text is too long.", 400, "validation_error")
    if sort not in {"date_desc", "date_asc", "amount_desc", "amount_asc"}:
        return fail("Select a valid sort order.", 400, "validation_error")

    order = {
        "date_desc": "t.transaction_date DESC, t.id DESC",
        "date_asc": "t.transaction_date ASC, t.id ASC",
        "amount_desc": "t.amount_paise DESC, t.id DESC",
        "amount_asc": "t.amount_paise ASC, t.id ASC",
    }.get(sort, "t.transaction_date DESC, t.id DESC")

    clauses = ["t.user_id = ?"]
    params: list = [g.user["id"]]
    if tx_type in ("income", "expense"):
        clauses.append("t.type = ?")
        params.append(tx_type)
    if category_id:
        try:
            clauses.append("t.category_id = ?")
            params.append(int(category_id))
        except ValueError:
            return fail("Invalid category filter.", 400)
    if start:
        try:
            parse_iso_date(start, "start")
        except ValidationError as exc:
            return fail(exc.message)
        clauses.append("t.transaction_date >= ?")
        params.append(start)
    if end:
        try:
            parse_iso_date(end, "end")
        except ValidationError as exc:
            return fail(exc.message)
        clauses.append("t.transaction_date <= ?")
        params.append(end)
    if start and end and start > end:
        return fail("Start date must be on or before the end date.", 400, "validation_error")
    if q:
        clauses.append("t.description LIKE ?")
        params.append(f"%{q}%")

    where = " AND ".join(clauses)
    total_row = db.execute(
        f"SELECT COUNT(*) AS n, COALESCE(SUM(t.amount_paise), 0) AS total FROM transactions t WHERE {where}",
        params,
    ).fetchone()
    offset = (page - 1) * per_page
    rows = db.execute(
        f"""
        SELECT t.*, c.name AS category_name, c.color AS category_color, c.icon AS category_icon
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE {where}
        ORDER BY {order}
        LIMIT ? OFFSET ?
        """,
        [*params, per_page, offset],
    ).fetchall()
    return ok(
        {
            "items": [serialize_transaction(row) for row in rows],
            "page": page,
            "per_page": per_page,
            "total_count": total_row["n"],
            "filtered_total": {
                "paise": int(total_row["total"]),
                "formatted": format_inr_from_paise(int(total_row["total"])),
            },
        }
    )


@bp.post("")
@login_required
def create_transaction():
    payload = request.get_json(silent=True) or {}
    db = get_db()
    try:
        data = _payload_to_record(payload)
        cursor = db.execute(
            """
            INSERT INTO transactions (
                user_id, category_id, type, amount_paise, description, transaction_date, payment_method
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                g.user["id"],
                data["category_id"],
                data["type"],
                data["amount_paise"],
                data["description"],
                data["transaction_date"],
                data["payment_method"],
            ),
        )
        db.commit()
        return ok(serialize_transaction(_row(cursor.lastrowid)), 201)
    except ValidationError as exc:
        db.rollback()
        return fail(exc.message, 400, "validation_error")


@bp.get("/<int:tx_id>")
@login_required
def get_transaction(tx_id: int):
    row = _row(tx_id)
    if row is None:
        return fail("Transaction not found.", 404, "not_found")
    return ok(serialize_transaction(row))


@bp.put("/<int:tx_id>")
@bp.patch("/<int:tx_id>")
@login_required
def update_transaction(tx_id: int):
    existing = _row(tx_id)
    if existing is None:
        return fail("Transaction not found.", 404, "not_found")
    payload = request.get_json(silent=True) or {}
    db = get_db()
    try:
        data = _payload_to_record(payload, partial=True, existing=existing)
        db.execute(
            """
            UPDATE transactions
            SET category_id = ?, type = ?, amount_paise = ?, description = ?,
                transaction_date = ?, payment_method = ?, updated_at = datetime('now')
            WHERE id = ? AND user_id = ?
            """,
            (
                data["category_id"],
                data["type"],
                data["amount_paise"],
                data["description"],
                data["transaction_date"],
                data["payment_method"],
                tx_id,
                g.user["id"],
            ),
        )
        db.commit()
        return ok(serialize_transaction(_row(tx_id)))
    except ValidationError as exc:
        db.rollback()
        return fail(exc.message, 400, "validation_error")


@bp.delete("/<int:tx_id>")
@login_required
def delete_transaction(tx_id: int):
    existing = _row(tx_id)
    if existing is None:
        return fail("Transaction not found.", 404, "not_found")
    db = get_db()
    db.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (tx_id, g.user["id"]))
    db.commit()
    return ok({"deleted": True, "id": tx_id})
